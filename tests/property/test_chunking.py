"""Hypothesis properties for `citebound.ingest.chunking`.

RULES §3.2 requires three of these by name, and their absence is a gate failure rather
than an omission: **the ordered concatenation of an article's chunks reproduces its text
exactly**, **every chunk has a non-empty ref**, and **no chunk crosses an article
boundary**. They are here because losing or duplicating text at this layer is the
quietest damage the pipeline can take — the reference still resolves, `G-HALLUC` stays
at zero and `G-QUOTE-LIT` at 1,00, and the only symptom is recall nobody can explain.

The determinism properties come from `docs/CONTRACTS/chunks-ddl.sql` v2 instead, which
states them as invariant A: the sha256 of the ordered set of
`(chunk_id, content_hash, embedding_model, dim, index_version)` must be identical across
runs, without exception.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from citebound.domain.legalref import LegalRef
from citebound.ingest.boe_xml import Apartado, Precepto, PreceptoTipo
from citebound.ingest.chunking import (
    chunk_id_de,
    chunk_preceptos,
    content_hash_de,
    doc_id_de,
    normalizar_contenido,
)

NORMA = "RD-1428/2003"
URI = "https://www.boe.es/id/BOE-A-2003-23514"

designadores = st.one_of(
    st.integers(min_value=1, max_value=225).map(str),
    st.integers(min_value=1, max_value=225).map(lambda n: f"{n}bis"),
    st.sampled_from(["unico", "ddunica", "dfprimera", "anexoi-1", "rd-unico", "tv-151"]),
)
textos = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=0x017F, exclude_categories=("Cs",)),
    min_size=1,
    max_size=120,
).filter(lambda s: s.strip())
apartados = st.one_of(st.none(), st.integers(min_value=1, max_value=12).map(str))


@st.composite
def preceptos(draw: st.DrawFn, designador: str | None = None) -> Precepto:
    return Precepto(
        ref=LegalRef(NORMA, designador or draw(designadores)),
        tipo=PreceptoTipo.ARTICULO,
        rubrica=draw(textos),
        apartados=tuple(
            Apartado(n, t)
            for n, t in draw(st.lists(st.tuples(apartados, textos), min_size=1, max_size=6))
        ),
        titulo=None,
        capitulo=None,
        seccion=None,
        vigente=True,
        id_norma_version="BOE-A-2003-23514",
        fecha_vigencia="20040123",
    )


@st.composite
def documentos(draw: st.DrawFn) -> tuple[Precepto, ...]:
    """A document with no two preceptos sharing a reference, which is what the parser
    guarantees (`ingest/boe_xml`, ADR-020) and therefore what the chunker may assume."""
    designados = draw(st.lists(designadores, min_size=1, max_size=8, unique=True))
    return tuple(draw(preceptos(d)) for d in designados)


# --------------------------------------------------------------------------------------
# No loss · required by RULES §3.2
# --------------------------------------------------------------------------------------


@given(preceptos())
def test_the_chunk_reproduces_the_text_of_the_apartados_it_came_from(p: Precepto) -> None:
    """Nothing is dropped and nothing is invented. Phase 0 makes one chunk per article,
    so "the ordered concatenation of an article's chunks" is that single chunk — and the
    property is written so that it keeps holding when phase 2 splits finer."""
    trozos = chunk_preceptos((p,), source_uri=URI)
    cuerpo = "\n".join(c.content.split("\n", 1)[1] for c in trozos)
    esperado = "\n".join(
        f"{a.numero}. {a.texto}" if a.numero is not None else a.texto for a in p.apartados
    )
    assert cuerpo == esperado


@given(documentos())
def test_every_chunk_carries_a_non_empty_reference(ps: tuple[Precepto, ...]) -> None:
    """Required by RULES §3.2. A chunk with no ref cannot be cited nor verified, and it
    pollutes `recall@k` with a row that can never be a correct answer."""
    for chunk in chunk_preceptos(ps, source_uri=URI):
        assert str(chunk.ref)
        assert chunk.ref.norma == NORMA


@given(documentos())
def test_no_chunk_crosses_an_article_boundary(ps: tuple[Precepto, ...]) -> None:
    """Required by RULES §3.2. A chunk straddling two articles would make a `quote` of
    one verifiable against the text of the other: `G-QUOTE-LIT` would stay at 1,00 while
    the citation pointed at the wrong law."""
    chunks = chunk_preceptos(ps, source_uri=URI)
    assert len(chunks) == len(ps)
    assert [str(c.ref) for c in chunks] == [str(p.ref) for p in ps]


# --------------------------------------------------------------------------------------
# Determinism · invariant A of chunks-ddl.sql v2
# --------------------------------------------------------------------------------------


@given(documentos())
def test_two_runs_produce_the_same_identifiers(ps: tuple[Precepto, ...]) -> None:
    a, b = chunk_preceptos(ps, source_uri=URI), chunk_preceptos(ps, source_uri=URI)
    assert [(c.chunk_id, c.content_hash, c.ordinal, c.occurrence) for c in a] == [
        (c.chunk_id, c.content_hash, c.ordinal, c.occurrence) for c in b
    ]


@given(documentos())
def test_chunk_ids_are_unique_within_a_document(ps: tuple[Precepto, ...]) -> None:
    """`chunk_id` is the primary key of `chunk_v1`. A collision is not a degraded index,
    it is a failed insert — or worse, a silently overwritten row."""
    ids = [c.chunk_id for c in chunk_preceptos(ps, source_uri=URI)]
    assert len(set(ids)) == len(ids)


@given(documentos())
def test_the_identifier_does_not_depend_on_the_position(ps: tuple[Precepto, ...]) -> None:
    """Contract v2 exists for this. Prepending a precepto must leave every other
    `chunk_id` untouched — that is what makes an incremental re-index possible at all,
    and it is why the ordinal came out of the hash (ADR-018)."""
    nuevo = Precepto(
        ref=LegalRef(NORMA, "dtprimera"),
        tipo=PreceptoTipo.ARTICULO,
        rubrica="Insertado.",
        apartados=(Apartado(None, "Texto que no existía antes."),),
        titulo=None,
        capitulo=None,
        seccion=None,
        vigente=True,
        id_norma_version="BOE-A-2003-23514",
        fecha_vigencia="20040123",
    )
    antes = {str(c.ref): c.chunk_id for c in chunk_preceptos(ps, source_uri=URI)}
    despues = {str(c.ref): c.chunk_id for c in chunk_preceptos((nuevo, *ps), source_uri=URI)}
    for ref, ident in antes.items():
        assert despues[ref] == ident, f"{ref} cambió de id al insertar un precepto delante"


@given(documentos())
def test_the_ordinal_is_the_position_and_nothing_else(ps: tuple[Precepto, ...]) -> None:
    assert [c.ordinal for c in chunk_preceptos(ps, source_uri=URI)] == list(range(len(ps)))


# --------------------------------------------------------------------------------------
# The identifier functions on their own
# --------------------------------------------------------------------------------------


@given(textos)
def test_normalisation_is_idempotent(texto: str) -> None:
    una = normalizar_contenido(texto)
    assert normalizar_contenido(una) == una


@given(textos)
def test_the_content_hash_only_depends_on_the_normalised_text(texto: str) -> None:
    assert content_hash_de(f"  {texto}  ") == content_hash_de(texto)


@given(st.text(min_size=1, max_size=200))
def test_doc_id_is_sixteen_hex_characters(uri: str) -> None:
    ident = doc_id_de(uri)
    assert len(ident) == 16
    assert all(c in "0123456789abcdef" for c in ident)


@given(st.integers(min_value=0, max_value=99), st.integers(min_value=0, max_value=99))
def test_a_different_occurrence_gives_a_different_chunk_id(a: int, b: int) -> None:
    doc, contenido = doc_id_de(URI), content_hash_de("mismo texto")
    if a == b:
        assert chunk_id_de(doc, contenido, a) == chunk_id_de(doc, contenido, b)
    else:
        assert chunk_id_de(doc, contenido, a) != chunk_id_de(doc, contenido, b)
