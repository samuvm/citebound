"""Structural parser for the BOE consolidated XML.

Turns a consolidated document into `Precepto` values carrying a `LegalRef`. Four
things about the real format drive the whole design, and none of them is guessable
from the outside — they were measured on `corpus/raw/BOE-A-2003-23514.xml` on
2026-08-10 and are recorded in ADR-001 and `corpus/MANIFEST.yaml`:

**A block can hold several `<version>`, and the one in force is the LAST.** 78 of the
335 blocks do; one holds four. Reading the first would serve superseded wording for a
quarter of the corpus, and it would be invisible: the quote is real, the reference
resolves, `G-QUOTE-LIT` stays at 1,00 and `G-HALLUC` at 0. Literal and wrong is worse
than obviously wrong, because nothing flags it.

**The block id is not the designator.** `Artículo 14 bis` lives in `<bloque id="a1-3">`;
the BOE mints internal ids for inserted articles. The designator comes from the `titulo`
attribute or from nowhere.

**The apartado is not a node.** It arrives as a `"1. "` prefix inside
`<p class="parrafo">`, so the granularity `G-CITA-PRECISION` depends on is recovered
from the text by `split_apartados`.

**An `ANEXO` is a heading block that nevertheless holds text**, while `TÍTULO` and
`CAPÍTULO` are heading blocks that only place what follows. "Skip every encabezado"
would drop the sign catalogue; "keep every encabezado" would mint references for the
table of contents.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

# Solo los TIPOS: `Element` para anotar y `ParseError` para capturar. El parseo va por
# `defusedxml`, que es lo que bandit pide y lo que B405 no sabe distinguir de un import
# que sí parsea. Por eso el `nosec` va aquí y con el motivo escrito, no como costumbre.
from xml.etree.ElementTree import Element, ParseError  # nosec B405

import defusedxml.ElementTree as DefusedET
from defusedxml.common import DefusedXmlException

from citebound.domain.legalref import LegalRef, LegalRefError

__all__ = [
    "Apartado",
    "BoeXmlError",
    "Precepto",
    "PreceptoTipo",
    "parse_norma",
    "split_apartados",
]

# `^(\d+)\.\s` and nothing looser. "30 km/h" must not become apartado 30, and the
# whitespace is consumed so that the apartado text starts where the sentence does —
# a leading "1. " inside the text would make every quote that begins at the top of an
# apartado fail `G-QUOTE-LIT`.
_APARTADO = re.compile(r"^(\d+)\.\s")

_TIT_ARTICULO = re.compile(r"^articulo\s+(.+)$")
_TIT_DISPOSICION = re.compile(r"^disposicion\s+(adicional|derogatoria|final|transitoria)\s+(.+)$")
_TIT_ANEXO = re.compile(r"^anexo\s+(.+)$")
_DEROGADO = re.compile(r"\(derogad[oa]", re.IGNORECASE)

# `<p>` classes that are structure, not body text.
_NO_ES_CUERPO = frozenset(
    {"articulo", "anexo", "titulo_num", "titulo_tit", "capitulo_num", "capitulo_tit", "firma"}
)

# Parsing goes through `defusedxml`, which refuses entity expansion — the "billion
# laughs" — outright. `xml.etree` does not defend against it and offers no switch to
# turn it on, so a hand-rolled guard was the only option until Samuel approved the
# dependency on 2026-08-10 (outside the Q-011 list, hence the asking).
#
# The prolog scan stays as a belt on top of the braces, and the reason it stays is that
# it fails with a message that says what is wrong, in Spanish, at the layer that first
# touches bytes off the network. `defusedxml` raises `EntitiesForbidden`, which is
# correct and unhelpful to whoever has to fix the download. The two are cheap and they
# fail differently, which is the point.
_PELIGROSO = ("<!doctype", "<!entity")


from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated, MutantDict


class BoeXmlError(ValueError):
    """The document is not a consolidated BOE text this parser can read."""


class PreceptoTipo(StrEnum):
    """What kind of citable unit a block holds."""

    ARTICULO = "articulo"
    DISPOSICION = "disposicion"
    ANEXO = "anexo"


@dataclass(frozen=True, slots=True)
class Apartado:
    """One subdivision of a precepto.

    `numero` is `None` when the article does not number its paragraphs. Inventing a
    `1` there would mint `art34.1`, a reference that does not exist — exactly the
    hallucination `G-HALLUC` is built to make impossible.
    """

    numero: str | None
    texto: str


@dataclass(frozen=True, slots=True)
class Precepto:
    """A citable unit with its reference, its text and its place in the hierarchy."""

    ref: LegalRef
    tipo: PreceptoTipo
    # Cómo lo llama el BOE: "Artículo 3", "Disposición adicional primera", "ANEXO I".
    # El designador de la `ref` está canonizado y no se puede revertir a algo legible
    # (`daprimera` no vuelve a ser "Disposición adicional primera"), y el troceado lo
    # necesita para encabezar el chunk con algo que un humano — y un embedding — sepa leer.
    rotulo: str
    rubrica: str
    apartados: tuple[Apartado, ...]
    titulo: str | None
    capitulo: str | None
    seccion: str | None
    vigente: bool
    id_norma_version: str
    fecha_vigencia: str | None
mutants_x_split_apartados__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_split_apartados__mutmut)
def split_apartados(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_orig(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_1(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = None
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_2(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = None
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_3(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(None)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_4(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_5(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append(None)
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_6(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(None), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_7(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(2), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_8(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = None
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_9(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[+1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_10(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-2]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_11(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = None
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_12(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[+1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_13(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-2] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_14(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append(None)
    return tuple(Apartado(numero, texto) for numero, texto in out)


def x_split_apartados__mutmut_15(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(None)


def x_split_apartados__mutmut_16(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(None, texto) for numero, texto in out)


def x_split_apartados__mutmut_17(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, None) for numero, texto in out)


def x_split_apartados__mutmut_18(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(texto) for numero, texto in out)


def x_split_apartados__mutmut_19(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, ) for numero, texto in out)

mutants_x_split_apartados__mutmut['_mutmut_orig'] = x_split_apartados__mutmut_orig # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_1'] = x_split_apartados__mutmut_1 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_2'] = x_split_apartados__mutmut_2 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_3'] = x_split_apartados__mutmut_3 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_4'] = x_split_apartados__mutmut_4 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_5'] = x_split_apartados__mutmut_5 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_6'] = x_split_apartados__mutmut_6 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_7'] = x_split_apartados__mutmut_7 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_8'] = x_split_apartados__mutmut_8 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_9'] = x_split_apartados__mutmut_9 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_10'] = x_split_apartados__mutmut_10 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_11'] = x_split_apartados__mutmut_11 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_12'] = x_split_apartados__mutmut_12 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_13'] = x_split_apartados__mutmut_13 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_14'] = x_split_apartados__mutmut_14 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_15'] = x_split_apartados__mutmut_15 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_16'] = x_split_apartados__mutmut_16 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_17'] = x_split_apartados__mutmut_17 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_18'] = x_split_apartados__mutmut_18 # type: ignore # mutmut generated
mutants_x_split_apartados__mutmut['x_split_apartados__mutmut_19'] = x_split_apartados__mutmut_19 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_parse_norma__mutmut)
def parse_norma(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_orig(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_1(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(None)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_2(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(None) from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_3(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = None
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_4(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(None)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_5(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = None
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_6(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = ""
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_7(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = None

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_8(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "XXrdXX"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_9(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "RD"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_10(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter(None):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_11(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("XXbloqueXX"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_12(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("BLOQUE"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_13(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = None

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_14(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") and "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_15(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get(None) or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_16(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("XXtituloXX") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_17(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("TITULO") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_18(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "XXXX").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_19(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = None
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_20(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(None)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_21(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_22(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango != "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_23(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "XXtituloXX":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_24(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "TITULO":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_25(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_26(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = None
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_27(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = "XXXX"
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_28(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango != "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_29(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "XXcapituloXX":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_30(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "CAPITULO":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_31(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_32(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = None
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_33(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            break

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_34(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = None
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_35(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(None, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_36(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, None, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_37(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, None, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_38(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, None, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_39(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, None, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_40(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, None, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_41(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, None)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_42(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_43(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_44(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_45(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_46(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_47(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_48(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, )
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_49(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_50(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(None)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_51(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = None
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_52(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(None, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_53(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, None, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_54(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, None)
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_55(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_56(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_57(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, )
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_58(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") and "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_59(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get(None) or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_60(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("XXtipoXX") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_61(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("TIPO") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_62(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "XXXX")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_63(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor or siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_64(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente == contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_65(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith(None):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_66(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("XXanexoXX"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_67(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("ANEXO"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_68(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = ""
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_69(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = None

    return _desambiguar(tuple(preceptos), norma)


def x_parse_norma__mutmut_70(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(None, norma)


def x_parse_norma__mutmut_71(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), None)


def x_parse_norma__mutmut_72(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(norma)


def x_parse_norma__mutmut_73(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), )


def x_parse_norma__mutmut_74(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(None), norma)

mutants_x_parse_norma__mutmut['_mutmut_orig'] = x_parse_norma__mutmut_orig # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_1'] = x_parse_norma__mutmut_1 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_2'] = x_parse_norma__mutmut_2 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_3'] = x_parse_norma__mutmut_3 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_4'] = x_parse_norma__mutmut_4 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_5'] = x_parse_norma__mutmut_5 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_6'] = x_parse_norma__mutmut_6 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_7'] = x_parse_norma__mutmut_7 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_8'] = x_parse_norma__mutmut_8 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_9'] = x_parse_norma__mutmut_9 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_10'] = x_parse_norma__mutmut_10 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_11'] = x_parse_norma__mutmut_11 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_12'] = x_parse_norma__mutmut_12 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_13'] = x_parse_norma__mutmut_13 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_14'] = x_parse_norma__mutmut_14 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_15'] = x_parse_norma__mutmut_15 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_16'] = x_parse_norma__mutmut_16 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_17'] = x_parse_norma__mutmut_17 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_18'] = x_parse_norma__mutmut_18 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_19'] = x_parse_norma__mutmut_19 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_20'] = x_parse_norma__mutmut_20 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_21'] = x_parse_norma__mutmut_21 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_22'] = x_parse_norma__mutmut_22 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_23'] = x_parse_norma__mutmut_23 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_24'] = x_parse_norma__mutmut_24 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_25'] = x_parse_norma__mutmut_25 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_26'] = x_parse_norma__mutmut_26 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_27'] = x_parse_norma__mutmut_27 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_28'] = x_parse_norma__mutmut_28 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_29'] = x_parse_norma__mutmut_29 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_30'] = x_parse_norma__mutmut_30 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_31'] = x_parse_norma__mutmut_31 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_32'] = x_parse_norma__mutmut_32 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_33'] = x_parse_norma__mutmut_33 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_34'] = x_parse_norma__mutmut_34 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_35'] = x_parse_norma__mutmut_35 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_36'] = x_parse_norma__mutmut_36 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_37'] = x_parse_norma__mutmut_37 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_38'] = x_parse_norma__mutmut_38 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_39'] = x_parse_norma__mutmut_39 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_40'] = x_parse_norma__mutmut_40 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_41'] = x_parse_norma__mutmut_41 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_42'] = x_parse_norma__mutmut_42 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_43'] = x_parse_norma__mutmut_43 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_44'] = x_parse_norma__mutmut_44 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_45'] = x_parse_norma__mutmut_45 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_46'] = x_parse_norma__mutmut_46 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_47'] = x_parse_norma__mutmut_47 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_48'] = x_parse_norma__mutmut_48 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_49'] = x_parse_norma__mutmut_49 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_50'] = x_parse_norma__mutmut_50 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_51'] = x_parse_norma__mutmut_51 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_52'] = x_parse_norma__mutmut_52 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_53'] = x_parse_norma__mutmut_53 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_54'] = x_parse_norma__mutmut_54 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_55'] = x_parse_norma__mutmut_55 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_56'] = x_parse_norma__mutmut_56 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_57'] = x_parse_norma__mutmut_57 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_58'] = x_parse_norma__mutmut_58 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_59'] = x_parse_norma__mutmut_59 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_60'] = x_parse_norma__mutmut_60 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_61'] = x_parse_norma__mutmut_61 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_62'] = x_parse_norma__mutmut_62 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_63'] = x_parse_norma__mutmut_63 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_64'] = x_parse_norma__mutmut_64 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_65'] = x_parse_norma__mutmut_65 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_66'] = x_parse_norma__mutmut_66 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_67'] = x_parse_norma__mutmut_67 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_68'] = x_parse_norma__mutmut_68 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_69'] = x_parse_norma__mutmut_69 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_70'] = x_parse_norma__mutmut_70 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_71'] = x_parse_norma__mutmut_71 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_72'] = x_parse_norma__mutmut_72 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_73'] = x_parse_norma__mutmut_73 # type: ignore # mutmut generated
mutants_x_parse_norma__mutmut['x_parse_norma__mutmut_74'] = x_parse_norma__mutmut_74 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut: MutantDict = {}  # type: ignore


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


@_mutmut_mutated(mutants_x__raiz_texto__mutmut)
def _raiz_texto(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_orig(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_1(xml: str) -> Element:
    if xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_2(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError(None)
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_3(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("XXdocumento vacíoXX")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_4(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("DOCUMENTO VACÍO")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_5(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = None
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_6(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].upper()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_7(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split(None, 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_8(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", None)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_9(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split(1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_10(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", )[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_11(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].rsplit("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_12(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split(None, 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_13(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", None)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_14(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split(1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_15(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", )[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_16(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.rsplit("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_17(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("XX<bloqueXX", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_18(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<BLOQUE", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_19(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 2)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_20(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[1].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_21(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("XX<responseXX", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_22(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<RESPONSE", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_23(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 2)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_24(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[1].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_25(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(None):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_26(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca not in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_27(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError(None)
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_28(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("XXel documento declara entidades o DTD y no se procesaXX")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_29(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o dtd y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_30(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("EL DOCUMENTO DECLARA ENTIDADES O DTD Y NO SE PROCESA")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_31(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = None
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_32(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(None)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_33(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(None) from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_34(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(None).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_35(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(None) from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_36(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = None
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_37(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(None)
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_38(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.rfind(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_39(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find("XX.//textoXX")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_40(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//TEXTO")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_41(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is not None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_42(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError(None)
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_43(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("XXel documento no trae <texto>: ¿es un consolidado del BOE?XX")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_44(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del boe?")
    return texto


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def x__raiz_texto__mutmut_45(xml: str) -> Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = DefusedET.fromstring(xml)
    except DefusedXmlException as err:
        raise BoeXmlError(f"XML defensivamente rechazado: {type(err).__name__}") from err
    except ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("EL DOCUMENTO NO TRAE <TEXTO>: ¿ES UN CONSOLIDADO DEL BOE?")
    return texto

mutants_x__raiz_texto__mutmut['_mutmut_orig'] = x__raiz_texto__mutmut_orig # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_1'] = x__raiz_texto__mutmut_1 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_2'] = x__raiz_texto__mutmut_2 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_3'] = x__raiz_texto__mutmut_3 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_4'] = x__raiz_texto__mutmut_4 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_5'] = x__raiz_texto__mutmut_5 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_6'] = x__raiz_texto__mutmut_6 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_7'] = x__raiz_texto__mutmut_7 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_8'] = x__raiz_texto__mutmut_8 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_9'] = x__raiz_texto__mutmut_9 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_10'] = x__raiz_texto__mutmut_10 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_11'] = x__raiz_texto__mutmut_11 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_12'] = x__raiz_texto__mutmut_12 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_13'] = x__raiz_texto__mutmut_13 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_14'] = x__raiz_texto__mutmut_14 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_15'] = x__raiz_texto__mutmut_15 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_16'] = x__raiz_texto__mutmut_16 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_17'] = x__raiz_texto__mutmut_17 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_18'] = x__raiz_texto__mutmut_18 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_19'] = x__raiz_texto__mutmut_19 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_20'] = x__raiz_texto__mutmut_20 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_21'] = x__raiz_texto__mutmut_21 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_22'] = x__raiz_texto__mutmut_22 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_23'] = x__raiz_texto__mutmut_23 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_24'] = x__raiz_texto__mutmut_24 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_25'] = x__raiz_texto__mutmut_25 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_26'] = x__raiz_texto__mutmut_26 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_27'] = x__raiz_texto__mutmut_27 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_28'] = x__raiz_texto__mutmut_28 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_29'] = x__raiz_texto__mutmut_29 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_30'] = x__raiz_texto__mutmut_30 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_31'] = x__raiz_texto__mutmut_31 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_32'] = x__raiz_texto__mutmut_32 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_33'] = x__raiz_texto__mutmut_33 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_34'] = x__raiz_texto__mutmut_34 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_35'] = x__raiz_texto__mutmut_35 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_36'] = x__raiz_texto__mutmut_36 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_37'] = x__raiz_texto__mutmut_37 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_38'] = x__raiz_texto__mutmut_38 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_39'] = x__raiz_texto__mutmut_39 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_40'] = x__raiz_texto__mutmut_40 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_41'] = x__raiz_texto__mutmut_41 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_42'] = x__raiz_texto__mutmut_42 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_43'] = x__raiz_texto__mutmut_43 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_44'] = x__raiz_texto__mutmut_44 # type: ignore # mutmut generated
mutants_x__raiz_texto__mutmut['x__raiz_texto__mutmut_45'] = x__raiz_texto__mutmut_45 # type: ignore # mutmut generated
mutants_x__sin_acentos__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x__sin_acentos__mutmut)
def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower().strip()


def x__sin_acentos__mutmut_orig(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower().strip()


def x__sin_acentos__mutmut_1(texto: str) -> str:
    descompuesto = None
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower().strip()


def x__sin_acentos__mutmut_2(texto: str) -> str:
    descompuesto = unicodedata.normalize(None, texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower().strip()


def x__sin_acentos__mutmut_3(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", None)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower().strip()


def x__sin_acentos__mutmut_4(texto: str) -> str:
    descompuesto = unicodedata.normalize(texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower().strip()


def x__sin_acentos__mutmut_5(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", )
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower().strip()


def x__sin_acentos__mutmut_6(texto: str) -> str:
    descompuesto = unicodedata.normalize("XXNFKDXX", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower().strip()


def x__sin_acentos__mutmut_7(texto: str) -> str:
    descompuesto = unicodedata.normalize("nfkd", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower().strip()


def x__sin_acentos__mutmut_8(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).upper().strip()


def x__sin_acentos__mutmut_9(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(None).lower().strip()


def x__sin_acentos__mutmut_10(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "XXXX".join(c for c in descompuesto if not unicodedata.combining(c)).lower().strip()


def x__sin_acentos__mutmut_11(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if unicodedata.combining(c)).lower().strip()


def x__sin_acentos__mutmut_12(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(None)).lower().strip()

mutants_x__sin_acentos__mutmut['_mutmut_orig'] = x__sin_acentos__mutmut_orig # type: ignore # mutmut generated
mutants_x__sin_acentos__mutmut['x__sin_acentos__mutmut_1'] = x__sin_acentos__mutmut_1 # type: ignore # mutmut generated
mutants_x__sin_acentos__mutmut['x__sin_acentos__mutmut_2'] = x__sin_acentos__mutmut_2 # type: ignore # mutmut generated
mutants_x__sin_acentos__mutmut['x__sin_acentos__mutmut_3'] = x__sin_acentos__mutmut_3 # type: ignore # mutmut generated
mutants_x__sin_acentos__mutmut['x__sin_acentos__mutmut_4'] = x__sin_acentos__mutmut_4 # type: ignore # mutmut generated
mutants_x__sin_acentos__mutmut['x__sin_acentos__mutmut_5'] = x__sin_acentos__mutmut_5 # type: ignore # mutmut generated
mutants_x__sin_acentos__mutmut['x__sin_acentos__mutmut_6'] = x__sin_acentos__mutmut_6 # type: ignore # mutmut generated
mutants_x__sin_acentos__mutmut['x__sin_acentos__mutmut_7'] = x__sin_acentos__mutmut_7 # type: ignore # mutmut generated
mutants_x__sin_acentos__mutmut['x__sin_acentos__mutmut_8'] = x__sin_acentos__mutmut_8 # type: ignore # mutmut generated
mutants_x__sin_acentos__mutmut['x__sin_acentos__mutmut_9'] = x__sin_acentos__mutmut_9 # type: ignore # mutmut generated
mutants_x__sin_acentos__mutmut['x__sin_acentos__mutmut_10'] = x__sin_acentos__mutmut_10 # type: ignore # mutmut generated
mutants_x__sin_acentos__mutmut['x__sin_acentos__mutmut_11'] = x__sin_acentos__mutmut_11 # type: ignore # mutmut generated
mutants_x__sin_acentos__mutmut['x__sin_acentos__mutmut_12'] = x__sin_acentos__mutmut_12 # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x__rango_de_encabezado__mutmut)
def _rango_de_encabezado(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("titulo", "capitulo", "seccion"):
        if plano.startswith(rango + " ") or plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_orig(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("titulo", "capitulo", "seccion"):
        if plano.startswith(rango + " ") or plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_1(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = None
    for rango in ("titulo", "capitulo", "seccion"):
        if plano.startswith(rango + " ") or plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_2(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(None)
    for rango in ("titulo", "capitulo", "seccion"):
        if plano.startswith(rango + " ") or plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_3(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("XXtituloXX", "capitulo", "seccion"):
        if plano.startswith(rango + " ") or plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_4(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("TITULO", "capitulo", "seccion"):
        if plano.startswith(rango + " ") or plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_5(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("titulo", "XXcapituloXX", "seccion"):
        if plano.startswith(rango + " ") or plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_6(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("titulo", "CAPITULO", "seccion"):
        if plano.startswith(rango + " ") or plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_7(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("titulo", "capitulo", "XXseccionXX"):
        if plano.startswith(rango + " ") or plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_8(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("titulo", "capitulo", "SECCION"):
        if plano.startswith(rango + " ") or plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_9(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("titulo", "capitulo", "seccion"):
        if plano.startswith(rango + " ") and plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_10(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("titulo", "capitulo", "seccion"):
        if plano.startswith(None) or plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_11(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("titulo", "capitulo", "seccion"):
        if plano.startswith(rango - " ") or plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_12(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("titulo", "capitulo", "seccion"):
        if plano.startswith(rango + "XX XX") or plano == rango:
            return rango
    return None


def x__rango_de_encabezado__mutmut_13(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("titulo", "capitulo", "seccion"):
        if plano.startswith(rango + " ") or plano != rango:
            return rango
    return None

mutants_x__rango_de_encabezado__mutmut['_mutmut_orig'] = x__rango_de_encabezado__mutmut_orig # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut['x__rango_de_encabezado__mutmut_1'] = x__rango_de_encabezado__mutmut_1 # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut['x__rango_de_encabezado__mutmut_2'] = x__rango_de_encabezado__mutmut_2 # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut['x__rango_de_encabezado__mutmut_3'] = x__rango_de_encabezado__mutmut_3 # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut['x__rango_de_encabezado__mutmut_4'] = x__rango_de_encabezado__mutmut_4 # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut['x__rango_de_encabezado__mutmut_5'] = x__rango_de_encabezado__mutmut_5 # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut['x__rango_de_encabezado__mutmut_6'] = x__rango_de_encabezado__mutmut_6 # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut['x__rango_de_encabezado__mutmut_7'] = x__rango_de_encabezado__mutmut_7 # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut['x__rango_de_encabezado__mutmut_8'] = x__rango_de_encabezado__mutmut_8 # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut['x__rango_de_encabezado__mutmut_9'] = x__rango_de_encabezado__mutmut_9 # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut['x__rango_de_encabezado__mutmut_10'] = x__rango_de_encabezado__mutmut_10 # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut['x__rango_de_encabezado__mutmut_11'] = x__rango_de_encabezado__mutmut_11 # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut['x__rango_de_encabezado__mutmut_12'] = x__rango_de_encabezado__mutmut_12 # type: ignore # mutmut generated
mutants_x__rango_de_encabezado__mutmut['x__rango_de_encabezado__mutmut_13'] = x__rango_de_encabezado__mutmut_13 # type: ignore # mutmut generated
mutants_x__designador__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x__designador__mutmut)
def _designador(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_orig(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_1(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = None

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_2(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(None)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_3(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = None
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_4(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(None)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_5(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_6(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(None, "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_7(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", None, articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_8(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", None), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_9(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub("", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_10(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_11(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", ), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_12(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"XX\s+XX", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_13(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "XXXX", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_14(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(None)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_15(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(2)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_16(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = None
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_17(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(None)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_18(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_19(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = None
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_20(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(None), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_21(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(2), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_22(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(None, "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_23(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", None, disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_24(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", None)
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_25(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub("", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_26(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_27(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", )
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_28(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"XX\s+XX", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_29(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "XXXX", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_30(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(None))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_31(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(3))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_32(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[1]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_33(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = None
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_34(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(None)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_35(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_36(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" - re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_37(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "XXanexoXX" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_38(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "ANEXO" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_39(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(None, "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_40(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", None, anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_41(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", None), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_42(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub("", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_43(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_44(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", ), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_45(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"XX\s+XX", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_46(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "XXXX", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_47(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(None)), PreceptoTipo.ANEXO

    return None


def x__designador__mutmut_48(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(2)), PreceptoTipo.ANEXO

    return None

mutants_x__designador__mutmut['_mutmut_orig'] = x__designador__mutmut_orig # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_1'] = x__designador__mutmut_1 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_2'] = x__designador__mutmut_2 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_3'] = x__designador__mutmut_3 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_4'] = x__designador__mutmut_4 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_5'] = x__designador__mutmut_5 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_6'] = x__designador__mutmut_6 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_7'] = x__designador__mutmut_7 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_8'] = x__designador__mutmut_8 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_9'] = x__designador__mutmut_9 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_10'] = x__designador__mutmut_10 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_11'] = x__designador__mutmut_11 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_12'] = x__designador__mutmut_12 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_13'] = x__designador__mutmut_13 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_14'] = x__designador__mutmut_14 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_15'] = x__designador__mutmut_15 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_16'] = x__designador__mutmut_16 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_17'] = x__designador__mutmut_17 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_18'] = x__designador__mutmut_18 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_19'] = x__designador__mutmut_19 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_20'] = x__designador__mutmut_20 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_21'] = x__designador__mutmut_21 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_22'] = x__designador__mutmut_22 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_23'] = x__designador__mutmut_23 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_24'] = x__designador__mutmut_24 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_25'] = x__designador__mutmut_25 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_26'] = x__designador__mutmut_26 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_27'] = x__designador__mutmut_27 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_28'] = x__designador__mutmut_28 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_29'] = x__designador__mutmut_29 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_30'] = x__designador__mutmut_30 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_31'] = x__designador__mutmut_31 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_32'] = x__designador__mutmut_32 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_33'] = x__designador__mutmut_33 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_34'] = x__designador__mutmut_34 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_35'] = x__designador__mutmut_35 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_36'] = x__designador__mutmut_36 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_37'] = x__designador__mutmut_37 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_38'] = x__designador__mutmut_38 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_39'] = x__designador__mutmut_39 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_40'] = x__designador__mutmut_40 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_41'] = x__designador__mutmut_41 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_42'] = x__designador__mutmut_42 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_43'] = x__designador__mutmut_43 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_44'] = x__designador__mutmut_44 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_45'] = x__designador__mutmut_45 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_46'] = x__designador__mutmut_46 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_47'] = x__designador__mutmut_47 # type: ignore # mutmut generated
mutants_x__designador__mutmut['x__designador__mutmut_48'] = x__designador__mutmut_48 # type: ignore # mutmut generated
mutants_x__ultima_version__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x__ultima_version__mutmut)
def _ultima_version(bloque: Element) -> Element | None:
    """The wording in force. **The last one, never the first.**"""
    versiones = bloque.findall("version")
    return versiones[-1] if versiones else None


def x__ultima_version__mutmut_orig(bloque: Element) -> Element | None:
    """The wording in force. **The last one, never the first.**"""
    versiones = bloque.findall("version")
    return versiones[-1] if versiones else None


def x__ultima_version__mutmut_1(bloque: Element) -> Element | None:
    """The wording in force. **The last one, never the first.**"""
    versiones = None
    return versiones[-1] if versiones else None


def x__ultima_version__mutmut_2(bloque: Element) -> Element | None:
    """The wording in force. **The last one, never the first.**"""
    versiones = bloque.findall(None)
    return versiones[-1] if versiones else None


def x__ultima_version__mutmut_3(bloque: Element) -> Element | None:
    """The wording in force. **The last one, never the first.**"""
    versiones = bloque.findall("XXversionXX")
    return versiones[-1] if versiones else None


def x__ultima_version__mutmut_4(bloque: Element) -> Element | None:
    """The wording in force. **The last one, never the first.**"""
    versiones = bloque.findall("VERSION")
    return versiones[-1] if versiones else None


def x__ultima_version__mutmut_5(bloque: Element) -> Element | None:
    """The wording in force. **The last one, never the first.**"""
    versiones = bloque.findall("version")
    return versiones[+1] if versiones else None


def x__ultima_version__mutmut_6(bloque: Element) -> Element | None:
    """The wording in force. **The last one, never the first.**"""
    versiones = bloque.findall("version")
    return versiones[-2] if versiones else None

mutants_x__ultima_version__mutmut['_mutmut_orig'] = x__ultima_version__mutmut_orig # type: ignore # mutmut generated
mutants_x__ultima_version__mutmut['x__ultima_version__mutmut_1'] = x__ultima_version__mutmut_1 # type: ignore # mutmut generated
mutants_x__ultima_version__mutmut['x__ultima_version__mutmut_2'] = x__ultima_version__mutmut_2 # type: ignore # mutmut generated
mutants_x__ultima_version__mutmut['x__ultima_version__mutmut_3'] = x__ultima_version__mutmut_3 # type: ignore # mutmut generated
mutants_x__ultima_version__mutmut['x__ultima_version__mutmut_4'] = x__ultima_version__mutmut_4 # type: ignore # mutmut generated
mutants_x__ultima_version__mutmut['x__ultima_version__mutmut_5'] = x__ultima_version__mutmut_5 # type: ignore # mutmut generated
mutants_x__ultima_version__mutmut['x__ultima_version__mutmut_6'] = x__ultima_version__mutmut_6 # type: ignore # mutmut generated
mutants_x__parrafos__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x__parrafos__mutmut)
def _parrafos(version: Element) -> Iterator[tuple[str, str]]:
    """Direct `<p>` children only, as `(clase, texto)`.

    Direct is load-bearing: the `<blockquote class="soloTexto">` that follows a
    `(Derogado)` marker is a sibling, so its paragraphs — editorial commentary about the
    repeal, not the norm — never reach the text simply by not being descended into.
    """
    for p in version.findall("p"):
        yield (p.get("class") or ""), "".join(p.itertext()).strip()


def x__parrafos__mutmut_orig(version: Element) -> Iterator[tuple[str, str]]:
    """Direct `<p>` children only, as `(clase, texto)`.

    Direct is load-bearing: the `<blockquote class="soloTexto">` that follows a
    `(Derogado)` marker is a sibling, so its paragraphs — editorial commentary about the
    repeal, not the norm — never reach the text simply by not being descended into.
    """
    for p in version.findall("p"):
        yield (p.get("class") or ""), "".join(p.itertext()).strip()


def x__parrafos__mutmut_1(version: Element) -> Iterator[tuple[str, str]]:
    """Direct `<p>` children only, as `(clase, texto)`.

    Direct is load-bearing: the `<blockquote class="soloTexto">` that follows a
    `(Derogado)` marker is a sibling, so its paragraphs — editorial commentary about the
    repeal, not the norm — never reach the text simply by not being descended into.
    """
    for p in version.findall(None):
        yield (p.get("class") or ""), "".join(p.itertext()).strip()


def x__parrafos__mutmut_2(version: Element) -> Iterator[tuple[str, str]]:
    """Direct `<p>` children only, as `(clase, texto)`.

    Direct is load-bearing: the `<blockquote class="soloTexto">` that follows a
    `(Derogado)` marker is a sibling, so its paragraphs — editorial commentary about the
    repeal, not the norm — never reach the text simply by not being descended into.
    """
    for p in version.findall("XXpXX"):
        yield (p.get("class") or ""), "".join(p.itertext()).strip()


def x__parrafos__mutmut_3(version: Element) -> Iterator[tuple[str, str]]:
    """Direct `<p>` children only, as `(clase, texto)`.

    Direct is load-bearing: the `<blockquote class="soloTexto">` that follows a
    `(Derogado)` marker is a sibling, so its paragraphs — editorial commentary about the
    repeal, not the norm — never reach the text simply by not being descended into.
    """
    for p in version.findall("P"):
        yield (p.get("class") or ""), "".join(p.itertext()).strip()


def x__parrafos__mutmut_4(version: Element) -> Iterator[tuple[str, str]]:
    """Direct `<p>` children only, as `(clase, texto)`.

    Direct is load-bearing: the `<blockquote class="soloTexto">` that follows a
    `(Derogado)` marker is a sibling, so its paragraphs — editorial commentary about the
    repeal, not the norm — never reach the text simply by not being descended into.
    """
    for p in version.findall("p"):
        yield (p.get("class") and ""), "".join(p.itertext()).strip()


def x__parrafos__mutmut_5(version: Element) -> Iterator[tuple[str, str]]:
    """Direct `<p>` children only, as `(clase, texto)`.

    Direct is load-bearing: the `<blockquote class="soloTexto">` that follows a
    `(Derogado)` marker is a sibling, so its paragraphs — editorial commentary about the
    repeal, not the norm — never reach the text simply by not being descended into.
    """
    for p in version.findall("p"):
        yield (p.get(None) or ""), "".join(p.itertext()).strip()


def x__parrafos__mutmut_6(version: Element) -> Iterator[tuple[str, str]]:
    """Direct `<p>` children only, as `(clase, texto)`.

    Direct is load-bearing: the `<blockquote class="soloTexto">` that follows a
    `(Derogado)` marker is a sibling, so its paragraphs — editorial commentary about the
    repeal, not the norm — never reach the text simply by not being descended into.
    """
    for p in version.findall("p"):
        yield (p.get("XXclassXX") or ""), "".join(p.itertext()).strip()


def x__parrafos__mutmut_7(version: Element) -> Iterator[tuple[str, str]]:
    """Direct `<p>` children only, as `(clase, texto)`.

    Direct is load-bearing: the `<blockquote class="soloTexto">` that follows a
    `(Derogado)` marker is a sibling, so its paragraphs — editorial commentary about the
    repeal, not the norm — never reach the text simply by not being descended into.
    """
    for p in version.findall("p"):
        yield (p.get("CLASS") or ""), "".join(p.itertext()).strip()


def x__parrafos__mutmut_8(version: Element) -> Iterator[tuple[str, str]]:
    """Direct `<p>` children only, as `(clase, texto)`.

    Direct is load-bearing: the `<blockquote class="soloTexto">` that follows a
    `(Derogado)` marker is a sibling, so its paragraphs — editorial commentary about the
    repeal, not the norm — never reach the text simply by not being descended into.
    """
    for p in version.findall("p"):
        yield (p.get("class") or "XXXX"), "".join(p.itertext()).strip()


def x__parrafos__mutmut_9(version: Element) -> Iterator[tuple[str, str]]:
    """Direct `<p>` children only, as `(clase, texto)`.

    Direct is load-bearing: the `<blockquote class="soloTexto">` that follows a
    `(Derogado)` marker is a sibling, so its paragraphs — editorial commentary about the
    repeal, not the norm — never reach the text simply by not being descended into.
    """
    for p in version.findall("p"):
        yield (p.get("class") or ""), "".join(None).strip()


def x__parrafos__mutmut_10(version: Element) -> Iterator[tuple[str, str]]:
    """Direct `<p>` children only, as `(clase, texto)`.

    Direct is load-bearing: the `<blockquote class="soloTexto">` that follows a
    `(Derogado)` marker is a sibling, so its paragraphs — editorial commentary about the
    repeal, not the norm — never reach the text simply by not being descended into.
    """
    for p in version.findall("p"):
        yield (p.get("class") or ""), "XXXX".join(p.itertext()).strip()

mutants_x__parrafos__mutmut['_mutmut_orig'] = x__parrafos__mutmut_orig # type: ignore # mutmut generated
mutants_x__parrafos__mutmut['x__parrafos__mutmut_1'] = x__parrafos__mutmut_1 # type: ignore # mutmut generated
mutants_x__parrafos__mutmut['x__parrafos__mutmut_2'] = x__parrafos__mutmut_2 # type: ignore # mutmut generated
mutants_x__parrafos__mutmut['x__parrafos__mutmut_3'] = x__parrafos__mutmut_3 # type: ignore # mutmut generated
mutants_x__parrafos__mutmut['x__parrafos__mutmut_4'] = x__parrafos__mutmut_4 # type: ignore # mutmut generated
mutants_x__parrafos__mutmut['x__parrafos__mutmut_5'] = x__parrafos__mutmut_5 # type: ignore # mutmut generated
mutants_x__parrafos__mutmut['x__parrafos__mutmut_6'] = x__parrafos__mutmut_6 # type: ignore # mutmut generated
mutants_x__parrafos__mutmut['x__parrafos__mutmut_7'] = x__parrafos__mutmut_7 # type: ignore # mutmut generated
mutants_x__parrafos__mutmut['x__parrafos__mutmut_8'] = x__parrafos__mutmut_8 # type: ignore # mutmut generated
mutants_x__parrafos__mutmut['x__parrafos__mutmut_9'] = x__parrafos__mutmut_9 # type: ignore # mutmut generated
mutants_x__parrafos__mutmut['x__parrafos__mutmut_10'] = x__parrafos__mutmut_10 # type: ignore # mutmut generated
mutants_x__precepto__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x__precepto__mutmut)
def _precepto(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_orig(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_1(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = None
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_2(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(None)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_3(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is not None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_4(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = None

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_5(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = None
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_6(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(None)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_7(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is not None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_8(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = None
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_9(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = "XXXX"
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_10(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = None
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_11(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(None):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_12(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase not in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_13(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"XXarticuloXX", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_14(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"ARTICULO", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_15(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "XXanexoXX"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_16(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "ANEXO"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_17(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = None
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_18(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica and _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_19(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(None, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_20(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, None)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_21(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_22(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, )
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_23(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO or texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_24(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_25(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(None)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_26(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_27(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=None,
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_28(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=None,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_29(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=None,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_30(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=None,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_31(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=None,
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_32(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=None,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_33(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=None,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_34(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=None,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_35(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=None,
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_36(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=None,
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_37(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=None,
    )


def x__precepto__mutmut_38(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_39(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_40(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_41(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_42(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_43(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_44(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_45(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_46(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_47(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_48(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        )


def x__precepto__mutmut_49(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(None, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_50(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, None),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_51(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(_con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_52(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, ),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_53(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(None, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_54(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, None, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_55(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, None)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_56(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_57(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_58(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, )),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_59(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(None),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_60(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_61(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(None),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_62(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(None) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_63(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") and "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_64(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get(None) or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_65(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("XXid_normaXX") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_66(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("ID_NORMA") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_67(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "XXXX",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def x__precepto__mutmut_68(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") and None,
    )


def x__precepto__mutmut_69(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get(None) or None,
    )


def x__precepto__mutmut_70(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("XXfecha_vigenciaXX") or None,
    )


def x__precepto__mutmut_71(
    bloque: Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("FECHA_VIGENCIA") or None,
    )

mutants_x__precepto__mutmut['_mutmut_orig'] = x__precepto__mutmut_orig # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_1'] = x__precepto__mutmut_1 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_2'] = x__precepto__mutmut_2 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_3'] = x__precepto__mutmut_3 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_4'] = x__precepto__mutmut_4 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_5'] = x__precepto__mutmut_5 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_6'] = x__precepto__mutmut_6 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_7'] = x__precepto__mutmut_7 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_8'] = x__precepto__mutmut_8 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_9'] = x__precepto__mutmut_9 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_10'] = x__precepto__mutmut_10 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_11'] = x__precepto__mutmut_11 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_12'] = x__precepto__mutmut_12 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_13'] = x__precepto__mutmut_13 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_14'] = x__precepto__mutmut_14 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_15'] = x__precepto__mutmut_15 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_16'] = x__precepto__mutmut_16 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_17'] = x__precepto__mutmut_17 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_18'] = x__precepto__mutmut_18 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_19'] = x__precepto__mutmut_19 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_20'] = x__precepto__mutmut_20 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_21'] = x__precepto__mutmut_21 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_22'] = x__precepto__mutmut_22 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_23'] = x__precepto__mutmut_23 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_24'] = x__precepto__mutmut_24 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_25'] = x__precepto__mutmut_25 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_26'] = x__precepto__mutmut_26 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_27'] = x__precepto__mutmut_27 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_28'] = x__precepto__mutmut_28 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_29'] = x__precepto__mutmut_29 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_30'] = x__precepto__mutmut_30 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_31'] = x__precepto__mutmut_31 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_32'] = x__precepto__mutmut_32 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_33'] = x__precepto__mutmut_33 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_34'] = x__precepto__mutmut_34 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_35'] = x__precepto__mutmut_35 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_36'] = x__precepto__mutmut_36 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_37'] = x__precepto__mutmut_37 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_38'] = x__precepto__mutmut_38 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_39'] = x__precepto__mutmut_39 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_40'] = x__precepto__mutmut_40 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_41'] = x__precepto__mutmut_41 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_42'] = x__precepto__mutmut_42 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_43'] = x__precepto__mutmut_43 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_44'] = x__precepto__mutmut_44 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_45'] = x__precepto__mutmut_45 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_46'] = x__precepto__mutmut_46 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_47'] = x__precepto__mutmut_47 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_48'] = x__precepto__mutmut_48 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_49'] = x__precepto__mutmut_49 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_50'] = x__precepto__mutmut_50 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_51'] = x__precepto__mutmut_51 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_52'] = x__precepto__mutmut_52 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_53'] = x__precepto__mutmut_53 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_54'] = x__precepto__mutmut_54 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_55'] = x__precepto__mutmut_55 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_56'] = x__precepto__mutmut_56 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_57'] = x__precepto__mutmut_57 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_58'] = x__precepto__mutmut_58 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_59'] = x__precepto__mutmut_59 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_60'] = x__precepto__mutmut_60 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_61'] = x__precepto__mutmut_61 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_62'] = x__precepto__mutmut_62 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_63'] = x__precepto__mutmut_63 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_64'] = x__precepto__mutmut_64 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_65'] = x__precepto__mutmut_65 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_66'] = x__precepto__mutmut_66 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_67'] = x__precepto__mutmut_67 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_68'] = x__precepto__mutmut_68 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_69'] = x__precepto__mutmut_69 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_70'] = x__precepto__mutmut_70 # type: ignore # mutmut generated
mutants_x__precepto__mutmut['x__precepto__mutmut_71'] = x__precepto__mutmut_71 # type: ignore # mutmut generated
mutants_x__rubrica__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x__rubrica__mutmut)
def _rubrica(cabecera: str, rotulo: str) -> str:
    """`"Artículo 3. Conductores."` → `"Conductores."`

    Kept out of the body on purpose: a quote that begins at the top of an article would
    otherwise have to include a heading the article does not carry at that position.
    """
    prefijo = f"{rotulo}."
    if cabecera.startswith(prefijo):
        return cabecera[len(prefijo) :].strip()
    return cabecera.strip()


def x__rubrica__mutmut_orig(cabecera: str, rotulo: str) -> str:
    """`"Artículo 3. Conductores."` → `"Conductores."`

    Kept out of the body on purpose: a quote that begins at the top of an article would
    otherwise have to include a heading the article does not carry at that position.
    """
    prefijo = f"{rotulo}."
    if cabecera.startswith(prefijo):
        return cabecera[len(prefijo) :].strip()
    return cabecera.strip()


def x__rubrica__mutmut_1(cabecera: str, rotulo: str) -> str:
    """`"Artículo 3. Conductores."` → `"Conductores."`

    Kept out of the body on purpose: a quote that begins at the top of an article would
    otherwise have to include a heading the article does not carry at that position.
    """
    prefijo = None
    if cabecera.startswith(prefijo):
        return cabecera[len(prefijo) :].strip()
    return cabecera.strip()


def x__rubrica__mutmut_2(cabecera: str, rotulo: str) -> str:
    """`"Artículo 3. Conductores."` → `"Conductores."`

    Kept out of the body on purpose: a quote that begins at the top of an article would
    otherwise have to include a heading the article does not carry at that position.
    """
    prefijo = f"{rotulo}."
    if cabecera.startswith(None):
        return cabecera[len(prefijo) :].strip()
    return cabecera.strip()

mutants_x__rubrica__mutmut['_mutmut_orig'] = x__rubrica__mutmut_orig # type: ignore # mutmut generated
mutants_x__rubrica__mutmut['x__rubrica__mutmut_1'] = x__rubrica__mutmut_1 # type: ignore # mutmut generated
mutants_x__rubrica__mutmut['x__rubrica__mutmut_2'] = x__rubrica__mutmut_2 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x__siguiente_contenedor__mutmut)
def _siguiente_contenedor(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_orig(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_1(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo == "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_2(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "XXencabezadoXX":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_3(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "ENCABEZADO":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_4(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = None
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_5(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(None)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_6(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None or designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_7(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_8(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[2] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_9(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is not PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_10(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[1]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_11(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" or _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_12(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual != "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_13(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "XXrdXX" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_14(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "RD" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_15(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(None) is None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_16(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is not None:
        return ""
    return actual


def x__siguiente_contenedor__mutmut_17(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return "XXXX"
    return actual

mutants_x__siguiente_contenedor__mutmut['_mutmut_orig'] = x__siguiente_contenedor__mutmut_orig # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_1'] = x__siguiente_contenedor__mutmut_1 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_2'] = x__siguiente_contenedor__mutmut_2 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_3'] = x__siguiente_contenedor__mutmut_3 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_4'] = x__siguiente_contenedor__mutmut_4 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_5'] = x__siguiente_contenedor__mutmut_5 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_6'] = x__siguiente_contenedor__mutmut_6 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_7'] = x__siguiente_contenedor__mutmut_7 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_8'] = x__siguiente_contenedor__mutmut_8 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_9'] = x__siguiente_contenedor__mutmut_9 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_10'] = x__siguiente_contenedor__mutmut_10 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_11'] = x__siguiente_contenedor__mutmut_11 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_12'] = x__siguiente_contenedor__mutmut_12 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_13'] = x__siguiente_contenedor__mutmut_13 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_14'] = x__siguiente_contenedor__mutmut_14 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_15'] = x__siguiente_contenedor__mutmut_15 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_16'] = x__siguiente_contenedor__mutmut_16 # type: ignore # mutmut generated
mutants_x__siguiente_contenedor__mutmut['x__siguiente_contenedor__mutmut_17'] = x__siguiente_contenedor__mutmut_17 # type: ignore # mutmut generated
mutants_x__con_contenedor__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x__con_contenedor__mutmut)
def _con_contenedor(designador: str, contenedor: str, tipo: PreceptoTipo) -> str:
    """Prefix the designator with the numbering space it belongs to.

    An ANEXO is the ROOT of its own space, so it never carries a prefix: `ANEXO II`
    reached while the parser is still inside ANEXO I would otherwise come out as
    `anexoi-anexoii`, which is not a reference to anything.
    """
    if tipo is PreceptoTipo.ANEXO or not contenedor:
        return designador
    return f"{contenedor}-{designador}"


def x__con_contenedor__mutmut_orig(designador: str, contenedor: str, tipo: PreceptoTipo) -> str:
    """Prefix the designator with the numbering space it belongs to.

    An ANEXO is the ROOT of its own space, so it never carries a prefix: `ANEXO II`
    reached while the parser is still inside ANEXO I would otherwise come out as
    `anexoi-anexoii`, which is not a reference to anything.
    """
    if tipo is PreceptoTipo.ANEXO or not contenedor:
        return designador
    return f"{contenedor}-{designador}"


def x__con_contenedor__mutmut_1(designador: str, contenedor: str, tipo: PreceptoTipo) -> str:
    """Prefix the designator with the numbering space it belongs to.

    An ANEXO is the ROOT of its own space, so it never carries a prefix: `ANEXO II`
    reached while the parser is still inside ANEXO I would otherwise come out as
    `anexoi-anexoii`, which is not a reference to anything.
    """
    if tipo is PreceptoTipo.ANEXO and not contenedor:
        return designador
    return f"{contenedor}-{designador}"


def x__con_contenedor__mutmut_2(designador: str, contenedor: str, tipo: PreceptoTipo) -> str:
    """Prefix the designator with the numbering space it belongs to.

    An ANEXO is the ROOT of its own space, so it never carries a prefix: `ANEXO II`
    reached while the parser is still inside ANEXO I would otherwise come out as
    `anexoi-anexoii`, which is not a reference to anything.
    """
    if tipo is not PreceptoTipo.ANEXO or not contenedor:
        return designador
    return f"{contenedor}-{designador}"


def x__con_contenedor__mutmut_3(designador: str, contenedor: str, tipo: PreceptoTipo) -> str:
    """Prefix the designator with the numbering space it belongs to.

    An ANEXO is the ROOT of its own space, so it never carries a prefix: `ANEXO II`
    reached while the parser is still inside ANEXO I would otherwise come out as
    `anexoi-anexoii`, which is not a reference to anything.
    """
    if tipo is PreceptoTipo.ANEXO or contenedor:
        return designador
    return f"{contenedor}-{designador}"

mutants_x__con_contenedor__mutmut['_mutmut_orig'] = x__con_contenedor__mutmut_orig # type: ignore # mutmut generated
mutants_x__con_contenedor__mutmut['x__con_contenedor__mutmut_1'] = x__con_contenedor__mutmut_1 # type: ignore # mutmut generated
mutants_x__con_contenedor__mutmut['x__con_contenedor__mutmut_2'] = x__con_contenedor__mutmut_2 # type: ignore # mutmut generated
mutants_x__con_contenedor__mutmut['x__con_contenedor__mutmut_3'] = x__con_contenedor__mutmut_3 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x__desambiguar__mutmut)
def _desambiguar(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_orig(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_1(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = None
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_2(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = None
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_3(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(None)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_4(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) - 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_5(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(None, 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_6(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), None) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_7(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_8(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), ) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_9(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(None), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_10(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 1) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_11(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 2
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_12(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(None):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_13(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n != 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_14(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 2 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_15(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = None
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_16(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 and p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_17(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(None)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_18(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] != 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_19(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 2 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_20(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is not None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_21(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(None)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_22(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            break
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_23(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = None
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_24(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix(None).strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_25(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removesuffix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_26(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(None).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_27(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("XXtituloXX").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_28(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("TITULO").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_29(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = None
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_30(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(None, '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_31(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', None, marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_32(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', None)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_33(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub('', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_34(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_35(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', )}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_36(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'XX[^a-z0-9]XX', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_37(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^A-Z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_38(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', 'XXXX', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_39(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(None)
    return tuple(resueltos)


def x__desambiguar__mutmut_40(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(None, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_41(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=None))
    return tuple(resueltos)


def x__desambiguar__mutmut_42(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_43(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ))
    return tuple(resueltos)


def x__desambiguar__mutmut_44(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(None, designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_45(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, None, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_46(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, None)))
    return tuple(resueltos)


def x__desambiguar__mutmut_47(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(designador, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_48(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, p.ref.apartado)))
    return tuple(resueltos)


def x__desambiguar__mutmut_49(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, )))
    return tuple(resueltos)


def x__desambiguar__mutmut_50(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(None)

mutants_x__desambiguar__mutmut['_mutmut_orig'] = x__desambiguar__mutmut_orig # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_1'] = x__desambiguar__mutmut_1 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_2'] = x__desambiguar__mutmut_2 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_3'] = x__desambiguar__mutmut_3 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_4'] = x__desambiguar__mutmut_4 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_5'] = x__desambiguar__mutmut_5 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_6'] = x__desambiguar__mutmut_6 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_7'] = x__desambiguar__mutmut_7 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_8'] = x__desambiguar__mutmut_8 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_9'] = x__desambiguar__mutmut_9 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_10'] = x__desambiguar__mutmut_10 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_11'] = x__desambiguar__mutmut_11 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_12'] = x__desambiguar__mutmut_12 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_13'] = x__desambiguar__mutmut_13 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_14'] = x__desambiguar__mutmut_14 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_15'] = x__desambiguar__mutmut_15 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_16'] = x__desambiguar__mutmut_16 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_17'] = x__desambiguar__mutmut_17 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_18'] = x__desambiguar__mutmut_18 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_19'] = x__desambiguar__mutmut_19 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_20'] = x__desambiguar__mutmut_20 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_21'] = x__desambiguar__mutmut_21 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_22'] = x__desambiguar__mutmut_22 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_23'] = x__desambiguar__mutmut_23 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_24'] = x__desambiguar__mutmut_24 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_25'] = x__desambiguar__mutmut_25 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_26'] = x__desambiguar__mutmut_26 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_27'] = x__desambiguar__mutmut_27 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_28'] = x__desambiguar__mutmut_28 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_29'] = x__desambiguar__mutmut_29 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_30'] = x__desambiguar__mutmut_30 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_31'] = x__desambiguar__mutmut_31 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_32'] = x__desambiguar__mutmut_32 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_33'] = x__desambiguar__mutmut_33 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_34'] = x__desambiguar__mutmut_34 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_35'] = x__desambiguar__mutmut_35 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_36'] = x__desambiguar__mutmut_36 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_37'] = x__desambiguar__mutmut_37 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_38'] = x__desambiguar__mutmut_38 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_39'] = x__desambiguar__mutmut_39 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_40'] = x__desambiguar__mutmut_40 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_41'] = x__desambiguar__mutmut_41 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_42'] = x__desambiguar__mutmut_42 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_43'] = x__desambiguar__mutmut_43 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_44'] = x__desambiguar__mutmut_44 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_45'] = x__desambiguar__mutmut_45 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_46'] = x__desambiguar__mutmut_46 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_47'] = x__desambiguar__mutmut_47 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_48'] = x__desambiguar__mutmut_48 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_49'] = x__desambiguar__mutmut_49 # type: ignore # mutmut generated
mutants_x__desambiguar__mutmut['x__desambiguar__mutmut_50'] = x__desambiguar__mutmut_50 # type: ignore # mutmut generated
