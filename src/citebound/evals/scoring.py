"""Métricas del contrato. FASE ROJA de la tarea 1a — sin comportamiento."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from citebound.domain.legalref import LegalRef
from citebound.evals.schema import CasoGolden

__all__ = [
    "Metrica",
    "Prediccion",
    "abstencion_incorrecta",
    "abstencion_indebida",
    "alucinacion",
    "cobertura",
    "precision_cita",
    "recall_at_k",
]


@dataclass(frozen=True, slots=True)
class Metrica:
    """Un valor con su denominador. `valor is None` cuando `n == 0`."""

    id: str
    valor: float | None
    n: int


@dataclass(frozen=True, slots=True)
class Prediccion:
    """Lo que el sistema respondió a un caso."""

    caso_id: str
    refs: tuple[LegalRef, ...]
    abstenida: bool = False


def precision_cita(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    return Metrica("G-CITA-PRECISION", None, 0)  # RED


def recall_at_k(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    return Metrica(f"G-RECALL{k}", None, 0)  # RED


def alucinacion(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    return Metrica("G-HALLUC", None, 0)  # RED


def cobertura(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    return Metrica("G-COBERTURA", None, 0)  # RED


def abstencion_incorrecta(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    return Metrica("G-ABST-FP", None, 0)  # RED


def abstencion_indebida(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    return Metrica("G-ABST-FN", None, 0)  # RED
