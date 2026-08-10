"""Hypothesis properties for `citebound.ingest.boe_xml`.

`ingest/chunking` is required by RULES §3.2 to prove that "the ordered concatenation of
an article's chunks reproduces its text exactly". That invariant is only worth anything
if the text handed to the chunker is itself complete, so the same no-loss property is
proved one layer earlier, here, where the apartado is carved out of the paragraph.

Losing a paragraph at this layer is the quietest failure the project can have: the
article still exists, it still has a `LegalRef`, `G-HALLUC` stays at zero and
`G-QUOTE-LIT` stays at 1,00 — the system simply never sees the sentence that answers
the question, and the only symptom is recall that nobody can explain.
"""

from __future__ import annotations

import re

from hypothesis import given
from hypothesis import strategies as st

from citebound.ingest.boe_xml import Apartado, split_apartados

# Paragraph shapes taken from the frozen corpus: numbered apartados, lettered items
# hanging off them, continuation paragraphs, and text that merely starts with a digit.
numerados = st.integers(min_value=1, max_value=40).map(lambda n: f"{n}. Texto del apartado {n}.")
letras = st.sampled_from("abcdefgh").map(lambda c: f"{c}) Punto {c} de la enumeración.")
continuaciones = st.sampled_from(
    [
        "Se entiende sin perjuicio de lo dispuesto en el artículo anterior.",
        "A estos efectos, se considerará vía urbana la definida en el anexo I.",
        "30 km/h es el límite en vías de un solo carril por sentido.",
        "(artículo 10.3 del texto articulado).",
    ]
)
parrafos = st.one_of(numerados, letras, continuaciones)


def _rejoin(apartados: tuple[Apartado, ...]) -> str:
    """Put the numbering back and glue everything, the inverse of the split."""
    partes = [f"{a.numero}. {a.texto}" if a.numero is not None else a.texto for a in apartados]
    return "\n".join(partes)


# --------------------------------------------------------------------------------------
# No loss · the property the whole ingest layer rests on
# --------------------------------------------------------------------------------------


@given(st.lists(parrafos, min_size=1, max_size=12))
def test_the_apartados_reproduce_the_paragraphs_they_came_from(ps: list[str]) -> None:
    """Nothing is dropped and nothing is invented. Splitting is a regrouping of the
    text, never a rewrite of it."""
    assert _rejoin(split_apartados(ps)) == "\n".join(ps)


@given(st.lists(parrafos, min_size=1, max_size=12))
def test_no_apartado_is_empty(ps: list[str]) -> None:
    """An empty apartado would become a chunk with no text, embed to noise, and pollute
    the index with a reference that can never legitimately be retrieved."""
    for apartado in split_apartados(ps):
        assert apartado.texto.strip()


@given(st.lists(parrafos, min_size=1, max_size=12))
def test_the_numbers_reported_are_exactly_the_markers_that_were_there(ps: list[str]) -> None:
    """No number is invented and none is dropped.

    An earlier version of this property asserted that apartado numbers never repeat.
    That is false for arbitrary input and it was **my** error, not the code's: if a
    document really prints two apartados numbered 1, the parser must report two
    apartados numbered 1. Reporting faithfully is the job; uniqueness is a property of
    the corpus, and it is asserted where it belongs — over the real frozen document,
    in `tests/unit/test_boe_xml.py`.
    """
    esperados = [m.group(1) for p in ps if (m := re.match(r"^(\d+)\.\s", p))]
    assert [a.numero for a in split_apartados(ps) if a.numero is not None] == esperados


@given(st.lists(numerados, min_size=2, max_size=10, unique=True))
def test_numbering_is_read_in_document_order(ps: list[str]) -> None:
    """The parser reports what the document says; it does not sort or renumber. If the
    BOE ever prints them out of order that is a fact about the norm, and the ADR trail
    should show it rather than have the parser quietly tidy it away."""
    esperado = [p.split(".", 1)[0] for p in ps]
    assert [a.numero for a in split_apartados(ps)] == esperado


@given(st.lists(continuaciones, min_size=1, max_size=8))
def test_paragraphs_without_a_marker_become_exactly_one_apartado(ps: list[str]) -> None:
    """With nothing to split on there is nothing to split: the paragraphs join into a
    single unnumbered apartado.

    This replaces an idempotence property that was simply false — feeding the split back
    through itself merges what the numbering had separated, because stripping the marker
    destroys the very information that caused the split. An invariant that does not hold
    is worse than no invariant: it passes only while the code is broken.
    """
    resultado = split_apartados(ps)
    assert len(resultado) == 1
    assert resultado[0].numero is None
    assert resultado[0].texto == "\n".join(ps)
