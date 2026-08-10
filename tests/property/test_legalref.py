"""Hypothesis properties for `citebound.domain.legalref`.

The three properties below are **required** by RULES §3.2. Their absence is a gate
failure, not an omission. They exist because example-based tests only prove the cases
somebody thought of, and `LegalRef` is the type every metric in the project is anchored
on: a hole here is a hole in `G-RECALL5`, `G-CITA-PRECISION` and `G-HALLUC` at once.
"""

from __future__ import annotations

from hypothesis import assume, given
from hypothesis import strategies as st

from citebound.domain.legalref import (
    LegalRef,
    MatchLevel,
    format_ref,
    matches,
    normalize,
    parse,
)

# --------------------------------------------------------------------------------------
# Strategies · shaped after what the frozen corpus actually contains (ADR-001)
# --------------------------------------------------------------------------------------

normas = st.sampled_from(["RD-1428/2003", "RDLeg-6/2015", "RD-818/2009"])

articulos = st.one_of(
    st.integers(min_value=1, max_value=225).map(str),  # Reglamento articles 1..N
    st.integers(min_value=1, max_value=225).map(lambda n: f"{n}bis"),  # "Artículo 14 bis"
    st.sampled_from(["unico", "ddunica", "dfprimera", "dfquinta", "anexoi", "anexoxi"]),
)

apartados = st.one_of(
    st.integers(min_value=1, max_value=12).map(str),
    st.integers(min_value=1, max_value=12).flatmap(
        lambda n: st.sampled_from("abcdefgh").map(lambda c: f"{n}.{c}")
    ),
)


@st.composite
def legal_refs(draw: st.DrawFn) -> LegalRef:
    """A well-formed reference at any of the three precision levels."""
    norma = draw(normas)
    articulo = draw(st.one_of(st.none(), articulos))
    apartado = draw(st.one_of(st.none(), apartados)) if articulo is not None else None
    return LegalRef(norma, articulo, apartado)


LEVELS = [MatchLevel.NORMA, MatchLevel.ARTICULO, MatchLevel.APARTADO]


def _reaches(ref: LegalRef, level: MatchLevel) -> bool:
    return LEVELS.index(ref.level) >= LEVELS.index(level)


# --------------------------------------------------------------------------------------
# Property 1 · format(parse(s)) == normalize(s)          [RULES §3.2, required]
# --------------------------------------------------------------------------------------


@given(legal_refs())
def test_formatting_a_parsed_reference_yields_its_normalized_text(ref: LegalRef) -> None:
    raw = format_ref(ref)
    assert format_ref(parse(raw)) == normalize(raw)


@given(legal_refs())
def test_parsing_a_formatted_reference_gives_back_the_same_value(ref: LegalRef) -> None:
    """The round trip closes in the other direction too: no component is lost or invented."""
    assert parse(format_ref(ref)) == ref


@given(legal_refs())
def test_canonical_text_is_a_fixed_point_of_normalize(ref: LegalRef) -> None:
    raw = format_ref(ref)
    assert normalize(raw) == raw


@given(legal_refs(), st.integers(min_value=0, max_value=3))
def test_normalize_absorbs_surrounding_whitespace(ref: LegalRef, pad: int) -> None:
    raw = format_ref(ref)
    assert normalize(" " * pad + raw + " " * pad) == raw


# --------------------------------------------------------------------------------------
# Property 2 · matches is reflexive                       [RULES §3.2, required]
# --------------------------------------------------------------------------------------


@given(legal_refs(), st.sampled_from(LEVELS))
def test_matches_is_reflexive(ref: LegalRef, level: MatchLevel) -> None:
    assume(_reaches(ref, level))
    assert matches(ref, ref, level)


@given(legal_refs(), legal_refs(), st.sampled_from(LEVELS))
def test_matches_is_symmetric(a: LegalRef, b: LegalRef, level: MatchLevel) -> None:
    assert matches(a, b, level) == matches(b, a, level)


# --------------------------------------------------------------------------------------
# Property 3 · APARTADO implies ARTICULO, never the reverse   [RULES §3.2, required]
# --------------------------------------------------------------------------------------


@given(legal_refs(), legal_refs())
def test_matching_at_apartado_implies_matching_at_articulo(a: LegalRef, b: LegalRef) -> None:
    assume(matches(a, b, MatchLevel.APARTADO))
    assert matches(a, b, MatchLevel.ARTICULO)


@given(legal_refs(), legal_refs())
def test_matching_at_articulo_implies_matching_at_norma(a: LegalRef, b: LegalRef) -> None:
    assume(matches(a, b, MatchLevel.ARTICULO))
    assert matches(a, b, MatchLevel.NORMA)


@given(normas, articulos, apartados, apartados)
def test_the_implication_does_not_hold_in_reverse(
    norma: str, articulo: str, ap1: str, ap2: str
) -> None:
    """Two apartados of the same article match at ARTICULO and must NOT match at
    APARTADO. If this ever passes, citing `art21` when the golden set says `art21.1`
    would start counting as correct and `G-CITA-PRECISION` would silently inflate."""
    assume(ap1 != ap2)
    a = LegalRef(norma, articulo, ap1)
    b = LegalRef(norma, articulo, ap2)
    assert matches(a, b, MatchLevel.ARTICULO)
    assert not matches(a, b, MatchLevel.APARTADO)


# --------------------------------------------------------------------------------------
# Invariants that keep the type usable as a set element and a database value
# --------------------------------------------------------------------------------------


@given(legal_refs())
def test_a_reference_is_hashable_and_equal_to_its_own_reparse(ref: LegalRef) -> None:
    """`recall@k` compares SETS of legal references (retrieval-metrics.md §2), so hashing
    and equality have to agree with the textual form."""
    again = parse(format_ref(ref))
    assert ref == again
    assert hash(ref) == hash(again)
    assert len({ref, again}) == 1


@given(legal_refs())
def test_the_formatted_form_never_contains_a_chunk_id(ref: LegalRef) -> None:
    """R1: no citation is ever identified by `chunk_id`. This is the type-level guard;
    `scripts/check_no_chunk_ids.py` is the repository-level one."""
    assert "chunk_id" not in format_ref(ref)
