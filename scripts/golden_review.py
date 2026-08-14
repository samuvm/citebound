"""La cola de revisión de Samuel. FASE ROJA de `1c` — sin comportamiento."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from citebound.domain.legalref import LegalRef

__all__ = [
    "COLA",
    "PROPUESTAS",
    "TECLAS",
    "Vista",
    "alerta_de_ritmo",
    "anotar",
    "cargar_cola",
    "cargar_propuestas",
    "consolidar",
    "pendientes",
    "resumen",
    "validar_correccion",
    "vista",
]

RAIZ = Path(__file__).resolve().parents[1]
COLA = RAIZ / "evals" / "golden" / "cola" / "candidatos.jsonl"
PROPUESTAS = RAIZ / "evals" / "golden" / "propuestas"

TECLAS: Mapping[str, str] = {}


@dataclass(frozen=True, slots=True)
class Vista:
    """Lo que se le enseña a Samuel de un caso."""

    id: str
    pregunta: str
    opciones: tuple[str, ...]
    respuesta_correcta: str
    tema: str
    subtema: str
    tipo: str
    a_ciegas: bool
    ref_propuesta: str | None
    nota: str | None
    texto: str | None


def cargar_cola(ruta: Path) -> list[dict[str, object]]:
    return []  # RED


def cargar_propuestas(carpeta: Path) -> dict[str, dict[str, object]]:
    return {}  # RED


def pendientes(
    cola: Sequence[Mapping[str, object]], hechos: Sequence[Mapping[str, object]]
) -> list[Mapping[str, object]]:
    return []  # RED


def consolidar(hechos: Sequence[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    return {}  # RED


def anotar(destino: Path, veredicto: Mapping[str, object]) -> None:
    return None  # RED


def vista(
    caso: Mapping[str, object], propuesta: Mapping[str, object], texto: str | None = None
) -> Vista:
    return Vista("", "", (), "", "", "", "", False, None, None, None)  # RED


def validar_correccion(texto: str, *, indice: frozenset[str]) -> LegalRef:
    raise NotImplementedError  # RED


def alerta_de_ritmo(
    hechos: Sequence[Mapping[str, object]], *, minimo_casos: int, tope_segundos: float
) -> str | None:
    return None  # RED


def resumen(hechos: Sequence[Mapping[str, object]], pendientes: int = 0) -> dict[str, object]:
    return {}  # RED
