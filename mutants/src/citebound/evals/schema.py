"""Esquema del golden set, literal de `docs/CONTRACTS/retrieval-metrics.md` §3.

**Se congela antes de anotar el primer caso** (`docs/PLAN.md` fase 1a). Anotar el conjunto
contra un esquema que después cambia tira las 10-16 horas que `PLAN.md` §3 y Q-004
presupuestan, y no se recuperan: los casos se anotaron respondiendo a una definición que ya
no existe.

Las tres reglas duras del contrato se validan **en el tipo y no en el proceso**. Un proceso
se salta sin querer un martes por la tarde; un tipo que no se puede construir, no.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer, model_validator

from citebound.domain.legalref import LegalRef, LegalRefError, format_ref, parse

__all__ = ["CasoGolden", "Dificultad", "Provenance", "RefLegal", "Tipo"]


class Tipo(StrEnum):
    """`positivo` = la respuesta está en el corpus. `negativo` = no está.

    Los negativos no son relleno: sin ellos `G-ABST-FP` y `G-ABST-FN` no son calculables y
    la mitad de la tesis del proyecto deja de poder medirse. El contrato exige un 15 %
    mínimo, y `G-GOLDEN-VALID` sube el suelo a 40 sobre 190.
    """

    POSITIVO = "positivo"
    NEGATIVO = "negativo"


class Dificultad(StrEnum):
    """El campo que pide el contrato. Se conserva junto a `pct_fallo`, que es el dato real."""

    FACIL = "facil"
    MEDIA = "media"
    DIFICIL = "dificil"


class Provenance(StrEnum):
    """De dónde salió el caso. Se publica en el README (contrato §3, regla dura nº 2).

    Esconder que un dato es generado «se nota y resta credibilidad», y aquí aplica igual que
    a los alumnos sintéticos que el propio `PROJECT.md` §6 manda declarar.
    """

    HUMANO = "humano"
    LLM_GENERADO_REVISADO_HUMANO = "llm_generado_revisado_humano"
    LLM_GENERADO = "llm_generado"


def _a_legalref(valor: Any) -> LegalRef:
    """Acepta una `LegalRef` ya construida o el texto canónico del JSONL."""
    if isinstance(valor, LegalRef):
        return valor
    if isinstance(valor, str):
        try:
            return parse(valor)
        except LegalRefError as err:
            raise ValueError(f"refs: {err}") from err
    raise ValueError(f"refs: {valor!r} no es una referencia legal")


RefLegal = Annotated[
    LegalRef,
    BeforeValidator(_a_legalref),
    PlainSerializer(format_ref, return_type=str),
]


class CasoGolden(BaseModel):
    """Un caso del golden set.

    Inmutable a propósito: el conjunto es append-only por versión (R12), y corregir un caso
    crea `v2` más un ADR en vez de reescribir `v1`. Un caso mutable en memoria invita
    justo a lo contrario.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    id: str
    version: int
    pregunta: str
    respuesta_referencia: str | None
    refs: list[RefLegal]
    materia: str
    dificultad: Dificultad
    pct_fallo: float
    """Porcentaje real de personas que fallan la pregunta, medido sobre miles de intentos en
    el banco de origen. Es mejor dato que `dificultad`, que es un juicio, y por eso viaja
    junto a él en vez de sustituirlo: el contrato exige el campo, la realidad da el número."""
    tipo: Tipo
    provenance: Provenance
    revisado_por: str | None
    revisado_en: date | None
    notas: str = ""

    @model_validator(mode="after")
    def _coherencia(self) -> CasoGolden:
        # `refs` vacía SI Y SOLO SI el caso es negativo. Las dos direcciones importan: un
        # positivo sin referencia no se puede puntuar, y un negativo CON referencia es una
        # contradicción — si hay artículo que responde, el corpus sí lo contiene.
        if self.tipo is Tipo.POSITIVO and not self.refs:
            raise ValueError("refs: un caso positivo necesita al menos una referencia")
        if self.tipo is Tipo.NEGATIVO and self.refs:
            raise ValueError("refs: un caso negativo no puede llevar referencias")
        if self.tipo is Tipo.POSITIVO and not self.respuesta_referencia:
            raise ValueError("respuesta_referencia: obligatoria en un caso positivo")

        # Regla dura nº 3 del contrato: generación asistida por LLM sí, aprobación
        # automática no. Es el único punto del proyecto donde el criterio de dominio de
        # Samuel es insustituible, así que lo exige el tipo y no la buena voluntad del
        # script que escriba el fichero.
        if not self.revisado_por or self.revisado_en is None:
            raise ValueError("revisado_por y revisado_en: ningún caso entra sin revisión humana")
        return self
