"""Structural parser for the BOE consolidated XML.

FASE ROJA DE TDD — tarea 0.3. Los tipos y las firmas son diseño; el COMPORTAMIENTO
está deliberadamente sin implementar, para que la suite falle por la aserción y no por
un `ImportError`, que no es rojo sino ruido (constitución §4.1). Cada `# RED` de abajo
desaparece en el turno verde.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from citebound.domain.legalref import LegalRef

__all__ = [
    "Apartado",
    "BoeXmlError",
    "Precepto",
    "PreceptoTipo",
    "parse_norma",
    "split_apartados",
]


class BoeXmlError(ValueError):
    """The document is not a consolidated BOE text this parser can read."""


class PreceptoTipo(StrEnum):
    """What kind of citable unit a block holds."""

    ARTICULO = "articulo"
    DISPOSICION = "disposicion"
    ANEXO = "anexo"


@dataclass(frozen=True, slots=True)
class Apartado:
    """One numbered subdivision of a precepto. `numero` is `None` when the article
    does not number its paragraphs — inventing a `1` there would mint a reference
    that does not exist."""

    numero: str | None
    texto: str


@dataclass(frozen=True, slots=True)
class Precepto:
    """A citable unit with its `LegalRef`, its text and its place in the hierarchy."""

    ref: LegalRef
    tipo: PreceptoTipo
    rubrica: str
    apartados: tuple[Apartado, ...]
    titulo: str | None
    capitulo: str | None
    seccion: str | None
    vigente: bool
    id_norma_version: str
    fecha_vigencia: str | None


def split_apartados(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark (ADR-001)."""
    return ()  # RED


def parse_norma(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order."""
    return ()  # RED
