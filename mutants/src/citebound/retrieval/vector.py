"""Vector search over the active index.

Phase 0 is **only** this: no lexical channel, no RRF, no reranker, no agent
(`docs/PLAN.md`). Deliberately naive — the point of the skeleton is that it walks end to
end so that everything after it is a *measured* improvement rather than an opinion.
Phase 2 adds the hybrid and compares it against the golden set with `make eval-retrieval`.

Two things are not naive even here, because getting them wrong later is expensive:

**The query goes through `chunks_active`, never through `chunk_v1`.** That is contract v2
(Q-013 b = B1): the alias is what makes it possible to change the embedding dimension
without stopping the service. Reaching past it would work today and break the switch.

**`SET hnsw.ef_search` is declared and never left to the default** (RULES, error nº 12).
Two projects that measure recall with different `ef_search` are measuring over different
structures, and the numbers do not compare — which is exactly what the shared contract
exists to prevent.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from citebound.domain.legalref import LegalRef, parse
from citebound.providers.embeddings import Embedder, embedder_para

__all__ = ["EF_SEARCH", "Recuperado", "buscar", "embedder_del_indice", "indice_activo"]

# Declared, not defaulted. The contract fixes m=16 and ef_construction=64 at build time;
# this is the search-time knob, and leaving it implicit is how two projects end up
# comparing numbers that were never comparable.
EF_SEARCH = 100


class _Cursor(Protocol):
    def execute(self, query: str, params: Any = ..., /) -> Any: ...
    def fetchall(self) -> list[Any]: ...
    def fetchone(self) -> Any: ...


@dataclass(frozen=True, slots=True)
class Recuperado:
    """One retrieved chunk, identified by its `LegalRef` and never by `chunk_id` (R1)."""

    ref: LegalRef
    content: str
    distancia: float
    titulo: str | None
    id_norma_version: str


def indice_activo(cur: _Cursor) -> tuple[str, str]:
    """The physical target the `active` alias resolves to, as `(index_version, tabla)`.

    Returned as a pair on purpose. Every eval report must record **both** and never the
    alias: with the alias alone, two runs over different data would produce identical
    normalised reports and `G-EVAL-DET` — threshold `== true`, not open to proposal —
    would stop meaning anything. It is the condition this project attached to accepting
    B1 (ADR-018).
    """
    cur.execute("SELECT index_version, physical_table FROM index_alias WHERE alias = 'active'")
    fila = cur.fetchone()
    if fila is None:
        raise LookupError(
            "no hay alias `active`: el índice no se ha registrado. "
            "Ejecuta la ingesta (`make smoke-f0` la hace) antes de consultar."
        )
    return str(fila[0]), str(fila[1])


def embedder_del_indice(cur: _Cursor) -> Embedder:
    """El embedder que declara el índice activo, no el que diga el entorno.

    **Sin esto, el fallo es mudo y total.** Los vectores del índice y el de la consulta viven
    en el mismo espacio o no significan nada, y nada en el camino lo comprueba: dimensiones
    iguales, `<=>` calcula, la búsqueda devuelve 30 filas y todas están mal. No hay excepción,
    no hay aviso, solo un recall peor sin causa aparente.

    Pasó de verdad el 2026-08-17: al reindexar con `qwen3-embedding:0.6b` la base pasó a tener
    unos vectores y `CITEBOUND_EMBEDDING_MODEL` seguía por defecto en `bge-m3`, así que
    `make eval-retrieval` sin la variable habría medido un espacio contra otro.

    La regla que lo hace imposible: **el índice es el dato y la consulta lo obedece.** Quién
    elige modelo es la ingesta, que es la que construye el índice; a partir de ahí el nombre
    viaja en `index_version` y se lee de ahí. La variable de entorno sigue existiendo, pero
    solo manda donde debe.
    """
    index_version, _ = indice_activo(cur)
    cur.execute("SELECT embedding_model, dim FROM index_version WHERE id = %s", (index_version,))
    fila = cur.fetchone()
    if fila is None:
        raise LookupError(
            f"el alias `active` apunta a {index_version!r}, que no está en `index_version`. "
            "La base está inconsistente: vuelve a ingerir."
        )
    return embedder_para(model=str(fila[0]), dim=int(fila[1]))


def buscar(
    cur: _Cursor,
    pregunta: str,
    *,
    embedder: Embedder,
    k: int = 5,
    ef_search: int = EF_SEARCH,
) -> tuple[Recuperado, ...]:
    """The `k` nearest chunks to the question, closest first.

    `k=5` is not arbitrary: it is the same 5 the closed citation will offer the generator
    as `[[REF:1..5]]` in phase 3. Keeping the number in one place means the guard that
    rejects `n` out of range and the retriever can never disagree about what the range is.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    (vector,) = embedder.embed([pregunta])

    cur.execute(f"SET hnsw.ef_search = {int(ef_search)}")
    cur.execute(
        """
        SELECT legal_ref, content, embedding <=> %s::vector AS distancia,
               titulo, metadata ->> 'id_norma_version'
          FROM chunks_active
         ORDER BY distancia
         LIMIT %s
        """,
        (_como_vector(vector), k),
    )
    return tuple(
        Recuperado(
            ref=parse(legal_ref),
            content=content,
            distancia=float(distancia),
            titulo=titulo,
            id_norma_version=id_norma or "",
        )
        for legal_ref, content, distancia, titulo, id_norma in cur.fetchall()
    )


def _como_vector(valores: Sequence[float]) -> str:
    """pgvector's literal syntax. `str(list)` happens to match it; being explicit here
    means a change in Python's repr cannot silently change what reaches the database."""
    return "[" + ",".join(repr(float(v)) for v in valores) + "]"
