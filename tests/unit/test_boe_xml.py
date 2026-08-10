"""Unit tests for `citebound.ingest.boe_xml`.

The parser turns the BOE's consolidated XML into `Precepto` values carrying a
`LegalRef`. It is the riskiest piece of phase 0, and ADR-001 says why: the apartado —
the granularity `G-CITA-PRECISION` and `G-QUOTE-LIT` depend on — **is not a node in the
tree**. It arrives as a `"1. "` prefix inside `<p class="parrafo">`.

`tests/fixtures/boe-fragmento.xml` is **nine blocks lifted whole** out of
`corpus/raw/BOE-A-2003-23514.xml` (sha256 `1105a26b…40072`, 2026-08-10). Not
paraphrased, not shortened: `test_the_fixture_is_verbatim_from_the_frozen_corpus` fails
if a single one drifts. Four of them encode traps that a parser written from
imagination walks straight into:

  * **A block can hold several `<version>` elements, and the current one is the LAST.**
    78 of the 335 blocks do, one holds four. Reading the first would serve superseded
    wording for a quarter of the corpus — a citation that is literal, verifiable and
    wrong, which is worse than one that is obviously wrong.
  * **`Artículo 14 bis` lives in a block whose id is `a1-3`.** The BOE mints internal
    ids for inserted articles, so the id is useless as a designator.
  * **A repealed article keeps an editorial note** in `<blockquote class="soloTexto">`
    after the `(Derogado)` marker. That is commentary, not article text.
  * **`ANEXO I` is `tipo="encabezado"`, not `tipo="precepto"`.** Filtering on `precepto`
    alone drops the whole sign catalogue, which is a materia of the golden set.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from citebound.domain.legalref import LegalRef
from citebound.ingest.boe_xml import (
    Apartado,
    BoeXmlError,
    Precepto,
    PreceptoTipo,
    parse_norma,
    split_apartados,
)

NORMA = "RD-1428/2003"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CORPUS = Path(__file__).resolve().parents[2] / "corpus" / "raw" / "BOE-A-2003-23514.xml"
FIXTURE = (FIXTURES / "boe-fragmento.xml").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def preceptos() -> tuple[Precepto, ...]:
    return parse_norma(FIXTURE, norma=NORMA)


def _by_ref(preceptos: tuple[Precepto, ...], ref: str) -> Precepto:
    match = [p for p in preceptos if str(p.ref) == ref]
    assert len(match) == 1, f"{ref} aparece {len(match)} veces"
    return match[0]


# --------------------------------------------------------------------------------------
# the fixture is not fiction
# --------------------------------------------------------------------------------------


def test_the_fixture_is_verbatim_from_the_frozen_corpus() -> None:
    """Every `<bloque>` of the fixture appears character for character in the corpus. A
    fixture that drifts from its source stops testing the parser and starts testing a
    memory of it, which is how a suite quietly becomes decorative."""
    corpus = CORPUS.read_text(encoding="utf-8")
    bloques = re.findall(r"<bloque .*?</bloque>", FIXTURE, re.S)
    assert len(bloques) == 9
    for bloque in bloques:
        bid = re.search(r'id="([^"]+)"', bloque)
        assert bid is not None
        assert bloque in corpus, f"el bloque {bid.group(1)} ya no está en el corpus tal cual"


# --------------------------------------------------------------------------------------
# what comes out at all
# --------------------------------------------------------------------------------------


def test_headings_that_carry_only_hierarchy_are_not_citable(
    preceptos: tuple[Precepto, ...],
) -> None:
    """`TÍTULO PRELIMINAR` and `CAPÍTULO I` place the articles that follow; they hold no
    text to cite. An `ANEXO` is also a heading block but it *does* hold text, so the
    rule cannot be "skip every encabezado"."""
    refs = {str(p.ref) for p in preceptos}
    assert "RD-1428/2003#arttpreliminar" not in refs
    assert "RD-1428/2003#artci" not in refs


def test_the_seven_citable_units_of_the_fixture_are_found_in_document_order(
    preceptos: tuple[Precepto, ...],
) -> None:
    """Order is what `ordinal` will be built from in `chunking`, and what the no-loss
    property of the chunker depends on."""
    assert [str(p.ref) for p in preceptos] == [
        "RD-1428/2003#art3",
        "RD-1428/2003#art34",
        "RD-1428/2003#art14bis",
        "RD-1428/2003#art135",
        "RD-1428/2003#art51",
        "RD-1428/2003#artdaprimera",
        "RD-1428/2003#artanexoi",
    ]


def test_every_precepto_carries_a_resolvable_legalref(preceptos: tuple[Precepto, ...]) -> None:
    """A precepto whose ref does not resolve breaks `G-HALLUC` at ingest time, before a
    single question has been asked."""
    for p in preceptos:
        assert isinstance(p.ref, LegalRef)
        assert p.ref.norma == NORMA
        assert p.ref.articulo


def test_the_three_kinds_of_citable_unit_are_told_apart(
    preceptos: tuple[Precepto, ...],
) -> None:
    assert _by_ref(preceptos, "RD-1428/2003#art3").tipo is PreceptoTipo.ARTICULO
    assert _by_ref(preceptos, "RD-1428/2003#artdaprimera").tipo is PreceptoTipo.DISPOSICION
    assert _by_ref(preceptos, "RD-1428/2003#artanexoi").tipo is PreceptoTipo.ANEXO


# --------------------------------------------------------------------------------------
# trap 1 · several <version> per block, and the one in force is the LAST
# --------------------------------------------------------------------------------------


def test_the_last_version_of_a_block_is_the_one_in_force(
    preceptos: tuple[Precepto, ...],
) -> None:
    """Article 135 carries two versions: the 2003 original and the 2025 rewording. 78 of
    the 335 blocks of this corpus are like that, so reading the first is not an edge
    case — it is a quarter of the text served as if it were current."""
    a135 = _by_ref(preceptos, "RD-1428/2003#art135")
    assert a135.id_norma_version == "BOE-A-2025-12199"
    assert a135.fecha_vigencia == "20250701"


def test_superseded_wording_never_reaches_the_text(preceptos: tuple[Precepto, ...]) -> None:
    """The wording that *was* in force stays in the document, in the earlier
    `<version>`. Quoting it satisfies `G-QUOTE-LIT` — the fragment really is in the
    file — while telling the user law that no longer applies."""
    bloque = re.search(r'<bloque id="a135".*?</bloque>', FIXTURE, re.S)
    assert bloque is not None
    anterior = bloque.group(0)[: bloque.group(0).rfind("<version ")]
    viejas = [t.strip() for t in re.findall(r'<p class="parrafo">([^<]{40,})</p>', anterior)]
    assert viejas, "el fixture debería traer texto de la versión anterior"

    vigente = " ".join(a.texto for a in _by_ref(preceptos, "RD-1428/2003#art135").apartados)
    for frase in viejas:
        assert frase not in vigente


def test_a_repealed_article_is_marked_and_its_editorial_note_is_not_quotable(
    preceptos: tuple[Precepto, ...],
) -> None:
    """Article 51 was repealed in 2021. Its last version is the `(Derogado)` marker plus
    a `<blockquote class="soloTexto">` that explains the repeal — commentary about the
    norm, not the norm."""
    a51 = _by_ref(preceptos, "RD-1428/2003#art51")
    assert a51.vigente is False
    texto = " ".join(a.texto for a in a51.apartados)
    assert "Téngase en cuenta" not in texto
    assert "BOE-A-2021-21006" not in texto


def test_articles_still_in_force_are_marked_as_such(preceptos: tuple[Precepto, ...]) -> None:
    assert _by_ref(preceptos, "RD-1428/2003#art3").vigente is True
    assert _by_ref(preceptos, "RD-1428/2003#art135").vigente is True


# --------------------------------------------------------------------------------------
# trap 2 · the block id is not the designator
# --------------------------------------------------------------------------------------


def test_the_designator_comes_from_the_title_and_never_from_the_block_id(
    preceptos: tuple[Precepto, ...],
) -> None:
    """`Artículo 14 bis` sits in a block whose id is `a1-3`. The obvious shortcut —
    strip the leading `a` off the id — yields `1-3`, which is not an article, and the
    reference would point nowhere while looking perfectly well formed."""
    bis = _by_ref(preceptos, "RD-1428/2003#art14bis")
    assert bis.ref.articulo == "14bis"
    assert "1-3" not in str(bis.ref)


def test_an_inserted_article_keeps_the_provenance_of_the_norm_that_created_it(
    preceptos: tuple[Precepto, ...],
) -> None:
    """The consolidated XML carries this per article. It costs nothing to keep and lets
    an answer say which reform it is quoting."""
    bis = _by_ref(preceptos, "RD-1428/2003#art14bis")
    assert bis.id_norma_version == "BOE-A-2026-12035"
    assert bis.fecha_vigencia == "20260606"


# --------------------------------------------------------------------------------------
# trap 3 · the annex is a heading block that does hold text
# --------------------------------------------------------------------------------------


def test_an_annex_is_captured_even_though_it_is_a_heading_block(
    preceptos: tuple[Precepto, ...],
) -> None:
    anexo = _by_ref(preceptos, "RD-1428/2003#artanexoi")
    assert anexo.tipo is PreceptoTipo.ANEXO
    assert anexo.apartados, "el anexo tiene texto y no puede quedarse vacío"


# --------------------------------------------------------------------------------------
# apartados · the granularity that is not in the tree
# --------------------------------------------------------------------------------------


def test_numbered_apartados_are_recovered_from_the_paragraph_text(
    preceptos: tuple[Precepto, ...],
) -> None:
    a3 = _by_ref(preceptos, "RD-1428/2003#art3")
    assert [a.numero for a in a3.apartados] == ["1", "2"]
    assert a3.apartados[0].texto.startswith("Se deberá conducir con la diligencia")


def test_the_apartado_number_is_stripped_from_its_own_text(
    preceptos: tuple[Precepto, ...],
) -> None:
    """`G-QUOTE-LIT` compares a quote against the text of its ref. Leaving the `"1. "`
    inside would make every quote that starts at the top of an apartado fail."""
    assert not _by_ref(preceptos, "RD-1428/2003#art3").apartados[0].texto.startswith("1.")


def test_an_article_with_one_unnumbered_paragraph_gets_one_apartado_with_no_number(
    preceptos: tuple[Precepto, ...],
) -> None:
    """Article 34 is exactly this shape in the real corpus. Inventing an apartado `1`
    would mint the reference `art34.1`, which does not exist — precisely the
    hallucination `G-HALLUC` is built to make impossible."""
    a34 = _by_ref(preceptos, "RD-1428/2003#art34")
    assert [a.numero for a in a34.apartados] == [None]
    assert "Cómputo de carriles" not in a34.apartados[0].texto


def test_the_rubric_is_separated_from_the_designator_and_from_the_body(
    preceptos: tuple[Precepto, ...],
) -> None:
    a3 = _by_ref(preceptos, "RD-1428/2003#art3")
    assert a3.rubrica == "Conductores."
    assert all("Artículo 3." not in a.texto for a in a3.apartados)
    assert _by_ref(preceptos, "RD-1428/2003#art34").rubrica == "Cómputo de carriles."


def test_the_structural_hierarchy_is_carried_down_to_each_precepto(
    preceptos: tuple[Precepto, ...],
) -> None:
    """Hierarchy is what the materia filter of phase 2 uses. A heading applies to every
    precepto after it until the next heading of the same rank."""
    a3 = _by_ref(preceptos, "RD-1428/2003#art3")
    assert a3.titulo == "TÍTULO PRELIMINAR"
    assert a3.capitulo == "CAPÍTULO I"
    assert a3.seccion is None


# --------------------------------------------------------------------------------------
# split_apartados · the risky function, tested on its own
# --------------------------------------------------------------------------------------

SPLIT_CASES: list[tuple[list[str], list[tuple[str | None, str]]]] = [
    (["1. Uno.", "2. Dos."], [("1", "Uno."), ("2", "Dos.")]),
    (["Un único párrafo."], [(None, "Un único párrafo.")]),
    # a continuation paragraph belongs to the apartado above it, not to a new one
    (["1. Uno.", "Sigue el uno.", "2. Dos."], [("1", "Uno.\nSigue el uno."), ("2", "Dos.")]),
    # lettered items hang off their apartado: the contract writes them as the compound
    # apartado `2.a`, so carving them out here would double-count the reference
    (["1. Uno.", "a) Letra a.", "b) Letra b."], [("1", "Uno.\na) Letra a.\nb) Letra b.")]),
    (["10. Diez.", "11. Once."], [("10", "Diez."), ("11", "Once.")]),
    # a paragraph that merely starts with a digit is not a numbered apartado
    (["30 km/h es el límite."], [(None, "30 km/h es el límite.")]),
    (["Preámbulo del artículo.", "1. Uno."], [(None, "Preámbulo del artículo."), ("1", "Uno.")]),
]


@pytest.mark.parametrize(("parrafos", "expected"), SPLIT_CASES)
def test_split_apartados(parrafos: list[str], expected: list[tuple[str | None, str]]) -> None:
    assert split_apartados(parrafos) == tuple(Apartado(n, t) for n, t in expected)


def test_split_apartados_on_no_paragraphs_yields_nothing() -> None:
    assert split_apartados([]) == ()


# --------------------------------------------------------------------------------------
# refusal
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("xml", ["", "no es xml", "<response><data/></response>"])
def test_unparseable_input_raises_instead_of_returning_nothing(xml: str) -> None:
    """Returning an empty tuple on a broken download would ingest an empty corpus in
    silence, and `make smoke-f0` would fail three steps later with no clue why."""
    with pytest.raises(BoeXmlError):
        parse_norma(xml, norma=NORMA)


def test_a_norma_that_is_not_a_legal_reference_is_refused() -> None:
    with pytest.raises(BoeXmlError):
        parse_norma(FIXTURE, norma="chunk_id:a1b2c3")


# --------------------------------------------------------------------------------------
# the whole frozen corpus, not just nine blocks of it
# --------------------------------------------------------------------------------------


def test_the_real_frozen_corpus_parses_to_the_counts_recorded_in_the_manifest() -> None:
    """Nine hand-picked blocks prove the parser handles the shapes somebody remembered.
    This proves it handles the document. Counts from `corpus/MANIFEST.yaml ::
    estructura_observada`, measured on 2026-08-10."""
    preceptos = parse_norma(CORPUS.read_text(encoding="utf-8"), norma=NORMA)
    articulos = [p for p in preceptos if p.tipo is PreceptoTipo.ARTICULO]
    assert len(articulos) == 217
    assert all(p.apartados for p in preceptos), "ningún precepto puede quedarse sin texto"
    assert len({str(p.ref) for p in preceptos}) == len(preceptos), "refs duplicadas"


def test_the_real_corpus_still_contains_the_edge_cases_the_fixture_claims() -> None:
    refs = {str(p.ref) for p in parse_norma(CORPUS.read_text(encoding="utf-8"), norma=NORMA)}
    assert {"RD-1428/2003#art14bis", "RD-1428/2003#art51", "RD-1428/2003#artanexoi"} <= refs
