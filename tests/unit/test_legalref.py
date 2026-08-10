"""Unit tests for `citebound.domain.legalref`.

`LegalRef` is the unit of truth of the whole project: the golden set, recall, citation
precision and the verifier are all anchored on it, never on `chunk_id` (RULES R1).
Getting this type wrong is getting everything wrong, so it is written test-first.

Edge cases below are not hypothetical — every one of them was observed in the frozen
corpus `corpus/raw/BOE-A-2003-23514.xml` on 2026-08-10 (see ADR-001):

  * `Artículo 14 bis` exists.
  * The document holds TWO numbering spaces: the Royal Decree has a single
    `Artículo único`, and the annexed Reglamento numbers its own articles 1..N.
    `LegalRef` numbers the Reglamento's; the Decree's own article is `unico`.
  * `Disposición derogatoria única` and five `Disposición final` blocks.
  * The apartado is NOT a structural element in the BOE XML: it is a `"1. "` prefix
    inside `<p class="parrafo">`, so it reaches this type as a plain string.
"""

from __future__ import annotations

import pytest

from citebound.domain.legalref import (
    LegalRef,
    LegalRefError,
    MatchLevel,
    format_ref,
    matches,
    normalize,
    parse,
    try_parse,
)

# --------------------------------------------------------------------------------------
# parse: the shapes that actually occur in the corpus
# --------------------------------------------------------------------------------------

PARSE_CASES: list[tuple[str, LegalRef]] = [
    # norma only — a whole-norm reference
    ("RD-1428/2003", LegalRef("RD-1428/2003")),
    # article, no apartado
    ("RD-1428/2003#art34", LegalRef("RD-1428/2003", "34")),
    # article + numeric apartado, the common case
    ("RD-1428/2003#art34.1", LegalRef("RD-1428/2003", "34", "1")),
    # apartado with a letter: the contract writes it "2.a", so everything after the
    # FIRST dot belongs to the apartado
    ("RD-1428/2003#art65.5.c", LegalRef("RD-1428/2003", "65", "5.c")),
    # article bis — observed literally as "Artículo 14 bis"
    ("RD-1428/2003#art14bis", LegalRef("RD-1428/2003", "14bis")),
    ("RD-1428/2003#art14bis.2", LegalRef("RD-1428/2003", "14bis", "2")),
    # the Royal Decree's own single article, distinct from Reglamento article 1
    ("RD-1428/2003#artunico", LegalRef("RD-1428/2003", "unico")),
    # disposiciones and anexos: non-numeric designators, so they can never collide
    ("RD-1428/2003#artddunica", LegalRef("RD-1428/2003", "ddunica")),
    ("RD-1428/2003#artdfprimera", LegalRef("RD-1428/2003", "dfprimera")),
    # The canonical designator is lowercase, roman numerals included: `ART34`, `Art.34`
    # and `art34` have to be one reference, and a designator that keeps its case would
    # break that. The uppercase spelling is a NORMALIZE case, not a canonical one, and
    # lives below.
    ("RD-1428/2003#artanexoi", LegalRef("RD-1428/2003", "anexoi")),
    # a second norma, for when the corpus grows (Q-001 options B and C)
    ("RDLeg-6/2015#art77.d", LegalRef("RDLeg-6/2015", "77", "d")),
]


@pytest.mark.parametrize(("raw", "expected"), PARSE_CASES)
def test_parse_returns_the_expected_components(raw: str, expected: LegalRef) -> None:
    assert parse(raw) == expected


@pytest.mark.parametrize(("raw", "expected"), PARSE_CASES)
def test_parse_then_format_is_the_identity_on_canonical_input(raw: str, expected: LegalRef) -> None:
    """Canonical input survives a round trip untouched. This is the contract that lets
    `legal_ref` be a Postgres generated column and a Python value at the same time."""
    assert format_ref(parse(raw)) == raw
    assert str(expected) == raw


# --------------------------------------------------------------------------------------
# normalize: what a human, an LLM or a stray copy-paste may write
# --------------------------------------------------------------------------------------

NORMALIZE_CASES: list[tuple[str, str]] = [
    # already canonical
    ("RD-1428/2003#art34.1", "RD-1428/2003#art34.1"),
    # surrounding and internal whitespace
    ("  RD-1428/2003#art34.1  ", "RD-1428/2003#art34.1"),
    ("RD-1428/2003 # art 34 . 1", "RD-1428/2003#art34.1"),
    # the many ways of writing "artículo"
    ("RD-1428/2003#artículo34", "RD-1428/2003#art34"),
    ("RD-1428/2003#articulo34", "RD-1428/2003#art34"),
    ("RD-1428/2003#Art.34", "RD-1428/2003#art34"),
    ("RD-1428/2003#ART34", "RD-1428/2003#art34"),
    # norma written with a space instead of a hyphen
    ("RD 1428/2003#art34", "RD-1428/2003#art34"),
    # "bis" written apart, and in caps
    ("RD-1428/2003#art14 BIS", "RD-1428/2003#art14bis"),
    # a roman numeral written the way the BOE prints it, "ANEXO XI"
    ("RD-1428/2003#art ANEXO XI", "RD-1428/2003#artanexoxi"),
    # NFKC: a full-width digit and a non-breaking space must fold to the plain forms.
    # El `noqa` es deliberado y por linea, nunca por regla: RUF001 marca Unicode ambiguo,
    # que es justo lo que se quiere en todo el repo — `G-INJECT` prueba ataques con
    # homoglifos —, pero aqui el caracter ambiguo ES el dato de prueba.
    ("RD-1428/2003#art3 4", "RD-1428/2003#art34"),  # noqa: RUF001
    ("RD-1428/2003#art３４", "RD-1428/2003#art34"),  # noqa: RUF001
    # Unicode hyphens in the norma fold to the plain "-"
    ("RD‑1428/2003", "RD-1428/2003"),  # noqa: RUF001
]


@pytest.mark.parametrize(("raw", "expected"), NORMALIZE_CASES)
def test_normalize_folds_the_variants_to_one_canonical_form(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


@pytest.mark.parametrize(("raw", "expected"), NORMALIZE_CASES)
def test_normalize_is_idempotent(raw: str, expected: str) -> None:
    assert normalize(normalize(raw)) == expected


@pytest.mark.parametrize(("raw", "_expected"), NORMALIZE_CASES)
def test_parse_accepts_anything_normalize_accepts(raw: str, _expected: str) -> None:
    """The core invariant of the module, stated once here and again as a Hypothesis
    property: formatting a parsed reference yields exactly its normalized text."""
    assert format_ref(parse(raw)) == normalize(raw)


# --------------------------------------------------------------------------------------
# rejection: a malformed reference must never silently become a valid one
# --------------------------------------------------------------------------------------

REJECTED: list[str] = [
    "",  # empty
    "   ",  # whitespace only
    "#art34",  # article with no norma
    "#art34.1",  # same, with apartado
    "RD-1428/2003#",  # dangling separator
    "RD-1428/2003#art",  # marker with no designator
    "RD-1428/2003#art.",  # marker, dot, nothing
    "RD-1428/2003#art34.",  # trailing dot: an empty apartado is not an apartado
    "RD-1428/2003#34",  # article without the "art" marker
    "RD-1428/2003#art34#art35",  # two references glued together
    "chunk_id:a1b2c3",  # a chunk id must NEVER parse as a legal reference (R1)
]


@pytest.mark.parametrize("raw", REJECTED)
def test_parse_rejects_malformed_references(raw: str) -> None:
    with pytest.raises(LegalRefError):
        parse(raw)


@pytest.mark.parametrize("raw", REJECTED)
def test_try_parse_returns_none_instead_of_raising(raw: str) -> None:
    assert try_parse(raw) is None


def test_try_parse_returns_the_reference_when_it_is_valid() -> None:
    assert try_parse("RD-1428/2003#art34.1") == LegalRef("RD-1428/2003", "34", "1")


# --------------------------------------------------------------------------------------
# level: how precise a reference is
# --------------------------------------------------------------------------------------


def test_level_is_norma_when_only_the_norma_is_given() -> None:
    assert LegalRef("RD-1428/2003").level is MatchLevel.NORMA


def test_level_is_articulo_when_there_is_no_apartado() -> None:
    assert LegalRef("RD-1428/2003", "34").level is MatchLevel.ARTICULO


def test_level_is_apartado_when_the_apartado_is_given() -> None:
    assert LegalRef("RD-1428/2003", "34", "1").level is MatchLevel.APARTADO


def test_an_apartado_without_an_articulo_is_rejected_at_construction() -> None:
    """`legal_ref` is a generated column built left to right; an apartado hanging off no
    article would produce a reference that cannot be resolved against the corpus, and
    `G-HALLUC` would be measuring against a broken set."""
    with pytest.raises(LegalRefError):
        LegalRef("RD-1428/2003", None, "1")


# --------------------------------------------------------------------------------------
# matches: the asymmetry that the whole scoring rests on (RULES §3.2)
# --------------------------------------------------------------------------------------

A34_1 = LegalRef("RD-1428/2003", "34", "1")
A34_2 = LegalRef("RD-1428/2003", "34", "2")
A34 = LegalRef("RD-1428/2003", "34")
A35 = LegalRef("RD-1428/2003", "35")
OTRA = LegalRef("RDLeg-6/2015", "34", "1")


@pytest.mark.parametrize("level", list(MatchLevel))
@pytest.mark.parametrize("ref", [A34_1, A34, LegalRef("RD-1428/2003")])
def test_matches_is_reflexive_at_every_level_the_reference_reaches(
    ref: LegalRef, level: MatchLevel
) -> None:
    if _reaches(ref, level):
        assert matches(ref, ref, level)


def test_same_apartado_matches_at_apartado_level() -> None:
    assert matches(A34_1, LegalRef("RD-1428/2003", "34", "1"), MatchLevel.APARTADO)


def test_different_apartado_of_the_same_article_does_not_match_at_apartado_level() -> None:
    assert not matches(A34_1, A34_2, MatchLevel.APARTADO)


def test_different_apartado_of_the_same_article_does_match_at_articulo_level() -> None:
    """This is the asymmetry: APARTADO implies ARTICULO, never the other way round."""
    assert matches(A34_1, A34_2, MatchLevel.ARTICULO)


def test_matching_at_apartado_implies_matching_at_articulo() -> None:
    assert matches(A34_1, A34_1, MatchLevel.APARTADO)
    assert matches(A34_1, A34_1, MatchLevel.ARTICULO)


def test_matching_at_articulo_does_not_imply_matching_at_apartado() -> None:
    assert matches(A34_1, A34_2, MatchLevel.ARTICULO)
    assert not matches(A34_1, A34_2, MatchLevel.APARTADO)


def test_different_articles_do_not_match_at_articulo_level() -> None:
    assert not matches(A34, A35, MatchLevel.ARTICULO)


def test_different_articles_still_match_at_norma_level() -> None:
    assert matches(A34, A35, MatchLevel.NORMA)


def test_the_same_article_number_in_a_different_norma_never_matches() -> None:
    """The adjacent-article trap, but across norms: article 34 of the Reglamento and
    article 34 of the LSV are unrelated texts."""
    assert not matches(A34_1, OTRA, MatchLevel.NORMA)
    assert not matches(A34_1, OTRA, MatchLevel.ARTICULO)
    assert not matches(A34_1, OTRA, MatchLevel.APARTADO)


def test_a_reference_without_apartado_cannot_match_at_apartado_level() -> None:
    """Asking for apartado precision from a reference that has none is a miss, not a
    match by default. `retrieval-metrics.md` §2: citing `art21` when the golden set says
    `art21.1` is a failure."""
    assert not matches(A34, A34_1, MatchLevel.APARTADO)
    assert not matches(A34_1, A34, MatchLevel.APARTADO)


def test_the_decree_single_article_never_matches_reglamento_article_one() -> None:
    """The two numbering spaces of ADR-001 must not collide."""
    assert not matches(
        LegalRef("RD-1428/2003", "unico"),
        LegalRef("RD-1428/2003", "1"),
        MatchLevel.ARTICULO,
    )


def _reaches(ref: LegalRef, level: MatchLevel) -> bool:
    order = [MatchLevel.NORMA, MatchLevel.ARTICULO, MatchLevel.APARTADO]
    return order.index(ref.level) >= order.index(level)


# --------------------------------------------------------------------------------------
# the type itself
# --------------------------------------------------------------------------------------


def test_legalref_is_hashable_so_it_can_live_in_the_sets_recall_is_computed_over() -> None:
    """`recall@k` is a set operation over legal references (retrieval-metrics.md §2)."""
    assert len({A34_1, LegalRef("RD-1428/2003", "34", "1"), A34_2}) == 2


def test_legalref_is_immutable() -> None:
    with pytest.raises((AttributeError, TypeError)):
        A34_1.articulo = "99"  # type: ignore[misc]


# --------------------------------------------------------------------------------------
# the construction guards · the four branches that stop a malformed reference existing
# --------------------------------------------------------------------------------------

BAD_CONSTRUCTIONS: list[tuple[str, str | None, str | None]] = [
    # the norma is validated on the way in: a permissive shape would let a chunk id
    # become a legal reference, which is the failure R1 exists to prevent
    ("no-es-una-norma", None, None),
    ("chunk_id:a1b2c3", None, None),
    ("RD-1428/2003", "34BIS", None),  # designador sin canonizar: la caja alta importa
    ("RD-1428/2003", "34 bis", None),  # espacio interior
    ("RD-1428/2003", "34", "1 a"),  # espacio en el apartado
    ("RD-1428/2003", "34", "1..2"),  # punto suelto
]


@pytest.mark.parametrize(("norma", "articulo", "apartado"), BAD_CONSTRUCTIONS)
def test_the_constructor_rejects_anything_not_already_canonical(
    norma: str, articulo: str | None, apartado: str | None
) -> None:
    """`LegalRef` validates and refuses; it never repairs. Text from outside goes
    through `parse`, which is the only place that knows how to canonicalise."""
    with pytest.raises(LegalRefError):
        LegalRef(norma, articulo, apartado)


def test_parse_rejects_an_empty_article_before_a_present_apartado() -> None:
    """`art..1` survives normalisation as a designator starting with a dot. Without this
    guard it would produce a reference with no article and an apartado hanging off
    nothing, which cannot be resolved against the corpus."""
    with pytest.raises(LegalRefError):
        parse("RD-1428/2003#art..1")


# --------------------------------------------------------------------------------------
# containers · one document, three numbering spaces (ADR-020)
# --------------------------------------------------------------------------------------

# Built lazily inside the test: constructing a `LegalRef` at module level would raise
# during collection, and a collection error is not a red — it is noise.
CONTAINER_CASES: list[tuple[str, tuple[str, str | None]]] = [
    # the Reglamento is the default container and takes no prefix: it is what the
    # contract's own example cites, and what most of the golden set will point at
    ("RD-1428/2003#art34.1", ("34", "1")),
    # the Royal Decree's own seven preceptos, which live before the Reglamento starts
    ("RD-1428/2003#artrd-unico", ("rd-unico", None)),
    ("RD-1428/2003#artrd-dfprimera", ("rd-dfprimera", None)),
    # an article of the sign catalogue, which numbers from 1 again inside ANEXO I
    ("RD-1428/2003#artanexoi-1", ("anexoi-1", None)),
    ("RD-1428/2003#artanexoi-1.2", ("anexoi-1", "2")),
]


@pytest.mark.parametrize(("raw", "partes"), CONTAINER_CASES)
def test_a_container_prefixed_designator_round_trips(
    raw: str, partes: tuple[str, str | None]
) -> None:
    """`RD-1428/2003` holds three numbering spaces that all restart at 1: the Royal
    Decree's own preceptos, the annexed Reglamento, and the articulado inside each
    ANEXO. Without a prefix, 47 references of the frozen corpus collide — measured, not
    feared — and `recall@k`, a set operation over references, would count two different
    articles as one."""
    articulo, apartado = partes
    assert parse(raw) == LegalRef("RD-1428/2003", articulo, apartado)
    assert format_ref(parse(raw)) == raw


def test_articles_from_different_containers_never_match() -> None:
    cuerpo = LegalRef("RD-1428/2003", "1")
    anexo = LegalRef("RD-1428/2003", "anexoi-1")
    decreto = LegalRef("RD-1428/2003", "rd-unico")
    assert not matches(cuerpo, anexo, MatchLevel.ARTICULO)
    assert not matches(cuerpo, decreto, MatchLevel.ARTICULO)
    assert not matches(anexo, decreto, MatchLevel.ARTICULO)


@pytest.mark.parametrize("malo", ["-1", "1-", "a--b", "anexoi-"])
def test_a_hyphen_may_join_segments_but_never_dangle(malo: str) -> None:
    """`anexoi-1` is two segments joined; `1-` is a typo that would resolve to nothing."""
    with pytest.raises(LegalRefError):
        LegalRef("RD-1428/2003", malo)
