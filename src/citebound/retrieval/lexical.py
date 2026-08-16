"""Búsqueda léxica sobre el índice activo · la pata de palabras del híbrido.

**Por qué hace falta además del vectorial.** Un embedding entiende *sentido* y se pierde con
lo que no lo tiene: un número («1,5 metros», «60 km/h»), una referencia («artículo 82.2») o
un término que aparece dos veces en todo el corpus. El léxico casa esos literales y no
entiende nada más. Cada uno encuentra lo que al otro se le escapa, y por eso `fusion` no
descarta lo que aparece en una sola lista.

**Se llama `ts_rank_cd` y no BM25** mientras no haya extensión real instalada (`CLAUDE.md`,
invariante 7). El SQL lo construye `query_builder`, que se prueba sin base de datos; aquí solo
queda ejecutarlo y traducir filas a `Recuperado`.

`RULES` §3 lo clasifica como **se mide, no se testea unitariamente**: su calidad es una
distribución sobre un corpus, no un booleano, y quien la juzga es `make eval-retrieval`.
"""

from __future__ import annotations

from typing import Any, Protocol

from citebound.domain.legalref import parse
from citebound.retrieval.query_builder import busqueda_lexica
from citebound.retrieval.vector import Recuperado

__all__ = ["buscar"]


class _Cursor(Protocol):
    def execute(self, query: str, params: Any = ..., /) -> Any: ...
    def fetchall(self) -> list[Any]: ...


def buscar(
    cur: _Cursor, pregunta: str, *, k: int = 30, materia: str | None = None
) -> tuple[Recuperado, ...]:
    """Los `k` chunks que mejor casan léxicamente, el mejor primero.

    Devuelve el mismo `Recuperado` que el canal vectorial **a propósito**: `fusion` trabaja
    sobre identificadores y no debe saber de qué pata viene cada resultado. Si los dos canales
    devolvieran tipos distintos, la fusión tendría que conocerlos a los dos y dejaría de ser
    una función pura de listas.

    El campo `distancia` se rellena con `1 - rango`: el vectorial ordena por distancia
    ascendente y aquí el rango es mejor cuanto mayor, así que se invierte para que el mismo
    tipo signifique lo mismo en los dos casos. El orden final no depende de este número —lo
    fija el `ORDER BY` de la consulta— pero un campo que significara cosas opuestas según el
    canal sería una trampa esperando a que alguien ordene por él.
    """
    consulta = busqueda_lexica(pregunta, k=k, materia=materia)
    cur.execute(consulta.sql, consulta.parametros)
    return tuple(
        Recuperado(
            ref=parse(legal_ref),
            content=content,
            distancia=1.0 - float(rango),
            titulo=titulo,
            id_norma_version=id_norma or "",
        )
        for legal_ref, content, rango, titulo, id_norma in cur.fetchall()
    )
