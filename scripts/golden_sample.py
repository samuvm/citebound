"""Quién entra en la cola de revisión de Samuel. FASE ROJA de `1b` — sin comportamiento."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from scripts.golden_validate import Umbrales

__all__ = [
    "BANCO",
    "Candidato",
    "deduplicar",
    "leer",
    "marcar_a_ciegas",
    "muestrear",
    "objetivo",
    "plan",
    "por_tipo",
    "temas_objetivo",
    "umbrales",
    "usables",
]

RAIZ = Path(__file__).resolve().parents[1]
BANCO = RAIZ / "evals" / "golden" / "source" / "preguntas-dgt-202606.csv"


@dataclass(frozen=True, slots=True)
class Candidato:
    """Una pregunta elegida para la cola, todavía **sin** referencia legal."""

    id: str
    source_id: str
    pregunta: str
    opciones: tuple[str, ...]
    respuesta_correcta: str
    tema: str
    subtema: str
    pct_fallo: float
    tipo: str
    a_ciegas: bool = False


def leer(ruta: Path) -> list[dict[str, str]]:
    return []  # RED


def usables(filas: Sequence[Mapping[str, str]]) -> list[Mapping[str, str]]:
    return []  # RED


def por_tipo(filas: Sequence[Mapping[str, str]], tipo: str) -> list[Mapping[str, str]]:
    return []  # RED


def umbrales() -> Umbrales:
    return Umbrales(0, 0, 0, 0, 0.0, 0.0)  # RED


def objetivo(suelo: int) -> int:
    return 0  # RED


def temas_objetivo(materias_min: int) -> int:
    return 0  # RED


def plan(filas: Sequence[Mapping[str, str]], *, objetivo: int, temas_max: int) -> dict[str, int]:
    return {}  # RED


def muestrear(
    filas: Sequence[Mapping[str, str]], *, plan: Mapping[str, int], tipo: str, semilla: int
) -> list[Candidato]:
    return []  # RED


def deduplicar(
    candidatos: Sequence[Candidato],
    vectores: Mapping[str, Sequence[float]],
    *,
    umbral: float,
) -> tuple[list[Candidato], list[Candidato]]:
    return [], []  # RED


def marcar_a_ciegas(candidatos: Sequence[Candidato], *, n: int, semilla: int) -> list[Candidato]:
    return list(candidatos)  # RED
