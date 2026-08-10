"""Stable legal reference: the unit of truth of the whole project.

FASE ROJA DE TDD — `docs/PARA-SAMUEL.md` 0.2. Los tipos y las firmas son diseño; el
COMPORTAMIENTO está deliberadamente sin implementar, para que la suite falle por la
aserción y no por un `ImportError`, que no es rojo sino ruido (constitución §4.1).
Cada `# RED` de abajo desaparece en el turno verde.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LegalRefError(ValueError):
    """A string that does not denote a resolvable legal reference."""


class MatchLevel(StrEnum):
    """How precise a comparison between two references is."""

    NORMA = "norma"
    ARTICULO = "articulo"
    APARTADO = "apartado"


@dataclass(frozen=True, slots=True)
class LegalRef:
    """`norma#artNN.apartado` — never a `chunk_id` (RULES R1)."""

    norma: str
    articulo: str | None = None
    apartado: str | None = None

    @property
    def level(self) -> MatchLevel:
        return MatchLevel.NORMA  # RED

    def __str__(self) -> str:
        return format_ref(self)


def normalize(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text."""
    return raw  # RED


def parse(raw: str) -> LegalRef:
    """Canonical text (or anything `normalize` accepts) into a `LegalRef`."""
    return LegalRef("")  # RED


def try_parse(raw: str) -> LegalRef | None:
    """`parse`, returning `None` instead of raising."""
    return LegalRef("")  # RED


def format_ref(ref: LegalRef) -> str:
    """A `LegalRef` back into its canonical text."""
    return ""  # RED


def matches(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
    """Do two references agree down to `level`? APARTADO implies ARTICULO, not the reverse."""
    return False  # RED
