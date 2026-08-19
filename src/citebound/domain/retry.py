"""Reintento acotado · esqueleto. El rojo se compromete antes que el verde."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from citebound.domain.citation import Motivo, Veredicto
from citebound.domain.legalref import LegalRef

__all__ = ["MAX_REINTENTOS", "Curso", "Salida", "decidir", "resolver_curso"]

MAX_REINTENTOS = 2


class Salida(StrEnum):
    RESPONDER = "responder"
    REINTENTAR = "reintentar"
    ABSTENERSE = "abstenerse"


@dataclass(frozen=True, slots=True)
class Curso:
    salida: Salida
    reintentos: int = 0
    refs: tuple[LegalRef, ...] = ()
    motivo: Motivo | None = None


def decidir(veredicto: Veredicto, *, reintentos_hechos: int, hay_fuentes: bool) -> Salida:
    return Salida.RESPONDER


def resolver_curso(intentos: Sequence[Veredicto], *, hay_fuentes: bool = True) -> Curso:
    return Curso(salida=Salida.RESPONDER)
