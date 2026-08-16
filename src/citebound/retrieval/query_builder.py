"""Constructor del SQL de búsqueda léxica. FASE ROJA de la fase 2 — sin comportamiento."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CONFIG_TS", "Consulta", "busqueda_lexica"]

CONFIG_TS = "spanish_unaccent"


@dataclass(frozen=True, slots=True)
class Consulta:
    """SQL y parámetros, siempre separados."""

    sql: str
    parametros: tuple[object, ...]


def busqueda_lexica(pregunta: str, *, k: int, materia: str | None = None) -> Consulta:
    return Consulta("", ())  # RED
