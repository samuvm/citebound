"""Puerta estadística: bootstrap pareado y corrección múltiple. FASE ROJA de `1a`."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

__all__ = ["Intervalo", "hay_regresion", "holm", "ic_diferencia_pareada"]


@dataclass(frozen=True, slots=True)
class Intervalo:
    """Un IC de la diferencia pareada `head - base`, con su procedencia."""

    punto: float
    inferior: float
    superior: float
    n: int
    n_resamples: int
    semilla: int
    nivel: float

    def contiene(self, valor: float) -> bool:
        return False  # RED


def ic_diferencia_pareada(
    base: Sequence[float],
    head: Sequence[float],
    *,
    n_resamples: int,
    semilla: int,
    nivel: float = 0.95,
) -> Intervalo:
    return Intervalo(0.0, 0.0, 0.0, 0, n_resamples, semilla, nivel)  # RED


def hay_regresion(ic: Intervalo, *, mayor_es_mejor: bool) -> bool:
    return False  # RED


def holm(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
    return {}  # RED
