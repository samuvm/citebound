"""`make golden-validate` · la salida de la fase 1. FASE ROJA de `1e` — sin comportamiento."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from citebound.evals.schema import CasoGolden

__all__ = ["Umbrales", "cargar", "informe", "main", "umbrales_de_goals", "validar"]


@dataclass(frozen=True, slots=True)
class Umbrales:
    """El suelo estadístico. Sale de `GOALS.yaml`, nunca de aquí."""

    positivos_min: int
    negativos_min: int
    materias_min: int
    casos_por_materia: int
    fraccion_negativos_min: float
    coseno_duplicado: float


def umbrales_de_goals(ruta: Path) -> Umbrales:
    return Umbrales(0, 0, 0, 0, 0.0, 0.0)  # RED


def cargar(lineas: Sequence[str]) -> tuple[list[CasoGolden], list[str]]:
    return [], []  # RED


def validar(
    lineas: Sequence[str],
    *,
    refs_indice: frozenset[str],
    umbrales: Umbrales,
    vectores: Mapping[str, Sequence[float]],
) -> list[str]:
    return []  # RED


def informe(
    *, errores: Sequence[str], casos: Sequence[CasoGolden], sha256: str
) -> dict[str, object]:
    return {}  # RED


def main() -> int:
    return 1  # RED
