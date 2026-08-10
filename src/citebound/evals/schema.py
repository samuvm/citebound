"""Esquema del golden set. FASE ROJA de la tarea 1a — sin comportamiento."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel

from citebound.domain.legalref import LegalRef

__all__ = ["CasoGolden", "Dificultad", "Provenance", "Tipo"]


class Tipo(StrEnum):
    POSITIVO = "positivo"
    NEGATIVO = "negativo"


class Dificultad(StrEnum):
    FACIL = "facil"
    MEDIA = "media"
    DIFICIL = "dificil"


class Provenance(StrEnum):
    HUMANO = "humano"
    LLM_GENERADO_REVISADO_HUMANO = "llm_generado_revisado_humano"
    LLM_GENERADO = "llm_generado"


class CasoGolden(BaseModel):
    """Un caso del golden set, tal como lo fija `retrieval-metrics.md` §3."""

    id: str
    version: int
    pregunta: str
    respuesta_referencia: str | None
    refs: list[LegalRef]
    materia: str
    dificultad: Dificultad
    pct_fallo: float
    tipo: Tipo
    provenance: Provenance
    revisado_por: str | None
    revisado_en: date | None
    notas: str = ""
