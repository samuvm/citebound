"""Cita cerrada · esqueleto. El rojo se compromete antes que el verde."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from citebound.domain.legalref import LegalRef

__all__ = [
    "MAX_FUENTES",
    "Cita",
    "CitaInvalida",
    "Fuente",
    "Motivo",
    "Veredicto",
    "normalizar_para_cotejo",
    "resolver",
    "verificar",
]

MAX_FUENTES = 5


class CitaInvalida(ValueError):
    """El hueco no se puede resolver a ninguna referencia recuperada."""


class Motivo(StrEnum):
    FUERA_DE_RANGO = "fuera_de_rango"
    QUOTE_NO_LITERAL = "quote_no_literal"
    QUOTE_VACIO = "quote_vacio"
    QUOTE_DEMASIADO_CORTO = "quote_demasiado_corto"
    SIN_CITAS = "sin_citas"


@dataclass(frozen=True, slots=True)
class Fuente:
    ref: LegalRef
    texto: str


@dataclass(frozen=True, slots=True)
class Cita:
    n: int
    quote: str


@dataclass(frozen=True, slots=True)
class Veredicto:
    ok: bool
    refs: tuple[LegalRef, ...] = ()
    motivo: Motivo | None = None


def normalizar_para_cotejo(texto: str) -> str:
    return texto


def resolver(cita: Cita, fuentes: Sequence[Fuente]) -> LegalRef:
    return fuentes[0].ref


def verificar(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    return Veredicto(ok=False)
