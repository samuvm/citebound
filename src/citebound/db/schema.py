"""Apply the schema and write chunks into it.

**The schema is not defined here.** It is `docs/CONTRACTS/chunks-ddl.sql` v2, a literal
copy of `_comun/CONTRACTS/` shared with `indexkeeper-04`, and this module concatenates it
with `db/ddl.sql` — the three `CHECK` constraints that are this project's own. Nothing is
duplicated: making divergence *impossible* beats a test that catches it late.

TDD is prohibited here (RULES §3): the shape of a schema is fixed by the engine and by a
contract, not by a test written first. What is required instead is a contract snapshot
and integration against a real Postgres, and both exist.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, Protocol

from citebound.ingest.chunking import Chunk

__all__ = [
    "CONTRATO_VERSION",
    "SchemaError",
    "aplicar_esquema",
    "contrato_path",
    "ddl_propio_path",
    "esquema_sql",
    "registrar_index_version",
    "upsert_chunks",
]

CONTRATO_VERSION = 2

# The contract lives in `docs/`, outside the package, on purpose: it must stay the same
# bytes as `_comun/CONTRACTS/` so that a `diff` is a test (CLAUDE.md). Copying it into
# the package would create a third copy and a third way to drift. Packaging is a phase-5
# problem; until then this resolves from the repository root and fails loudly.
_RAIZ = Path(__file__).resolve().parents[3]


class SchemaError(RuntimeError):
    """The schema cannot be assembled or applied."""


class _Cursor(Protocol):
    def execute(self, query: str, params: Any = ..., /) -> Any: ...
    def executemany(self, query: str, params: Iterable[Any], /) -> Any: ...


def contrato_path() -> Path:
    return _RAIZ / "docs" / "CONTRACTS" / "chunks-ddl.sql"


def ddl_propio_path() -> Path:
    return Path(__file__).with_name("ddl.sql")


def esquema_sql() -> str:
    """The shared contract first, this project's constraints after.

    That order is load-bearing: `db/ddl.sql` only ever `ALTER`s tables the contract
    created, so it cannot silently redefine anything. A contract test asserts exactly
    that, which is what keeps the two projects on one schema.
    """
    contrato, propio = contrato_path(), ddl_propio_path()
    for ruta in (contrato, propio):
        if not ruta.is_file():
            raise SchemaError(f"falta {ruta}; el esquema no se puede montar")
    return (
        f"-- === {contrato.relative_to(_RAIZ)} (contrato compartido v{CONTRATO_VERSION}) ===\n"
        f"{contrato.read_text(encoding='utf-8')}\n"
        f"-- === {propio.relative_to(_RAIZ)} (propio de citebound-01) ===\n"
        f"{propio.read_text(encoding='utf-8')}"
    )


def aplicar_esquema(cur: _Cursor) -> None:
    """Create the schema on an empty database."""
    cur.execute(esquema_sql())


def registrar_index_version(
    cur: _Cursor,
    *,
    index_id: str,
    embedding_model: str,
    dim: int,
    chunker_id: str,
    corpus_snapshot: str,
    physical_table: str = "chunk_v1",
    alias: str = "active",
) -> None:
    """Register an index and point the alias at it.

    The alias is what `chunks_active` resolves to (contract v2, Q-013 b = B1). Every eval
    report must record `index_version` **and** `physical_table` — never the alias — or two
    runs over different data would produce identical reports and `G-EVAL-DET` would stop
    meaning anything.
    """
    cur.execute(
        """
        INSERT INTO index_version
            (id, embedding_model, dim, distance, chunker_id, corpus_snapshot, physical_table)
        VALUES (%s, %s, %s, 'cosine', %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
        """,
        (index_id, embedding_model, dim, chunker_id, corpus_snapshot, physical_table),
    )
    cur.execute(
        """
        INSERT INTO index_alias (alias, index_version, physical_table)
        VALUES (%s, %s, %s)
        ON CONFLICT (alias) DO UPDATE
            SET index_version = EXCLUDED.index_version,
                physical_table = EXCLUDED.physical_table,
                switched_at = now()
        """,
        (alias, index_id, physical_table),
    )


def upsert_chunks(
    cur: _Cursor,
    chunks: Sequence[Chunk],
    embeddings: Sequence[Sequence[float]],
    *,
    index_id: str,
) -> None:
    """Write chunks idempotently.

    Ingesting the same corpus twice must not duplicate a single row — required by
    `docs/PLAN.md` phase 0 and asserted in `tests/integration/`. `chunk_id` is a pure
    function of (document, content, occurrence), so `ON CONFLICT` on the primary key is
    all it takes: no timestamps and no counters means the second run computes the same
    identifiers as the first.

    **`index_version` se actualiza, y ese es el punto delicado.** Como `chunk_id` no
    depende del modelo de embedding, reindexar el mismo corpus con otro modelo de la
    misma dimensión cae en este `ON CONFLICT` y **sustituye los vectores en sitio**. Sin
    actualizar también la columna, la fila se quedaba con vectores de un modelo y el
    nombre de otro: `make eval-retrieval` publicaría una procedencia falsa y nada la
    contradiría. Ocurrió de verdad el 2026-08-17 al pasar de `bge-m3` a
    `qwen3-embedding:0.6b` — ver `docs/JOURNAL.md`.

    La consecuencia de fondo se declara en vez de disimularse: **a igual dimensión el
    reindexado es destructivo en sitio**, así que la conmutación sin parar el servicio de
    ADR-018 solo vale entre dimensiones distintas, que son las que viven en tablas
    distintas. Con dos modelos de 1024 no hay dos índices a la vez.
    """
    if len(chunks) != len(embeddings):
        raise SchemaError(f"{len(chunks)} chunks y {len(embeddings)} embeddings")
    if not chunks:
        return
    cur.executemany(
        """
        INSERT INTO chunk_v1
            (chunk_id, index_version, content, content_hash, embedding, ref,
             norma, articulo, apartado, titulo, capitulo, seccion,
             doc_id, ordinal, occurrence, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (chunk_id) DO UPDATE
            SET content       = EXCLUDED.content,
                embedding     = EXCLUDED.embedding,
                ordinal       = EXCLUDED.ordinal,
                index_version = EXCLUDED.index_version
        """,
        [
            (
                c.chunk_id,
                index_id,
                c.content,
                c.content_hash,
                list(e),
                str(c.ref),
                c.ref.norma,
                c.ref.articulo,
                c.ref.apartado,
                c.titulo,
                c.capitulo,
                c.seccion,
                c.doc_id,
                c.ordinal,
                c.occurrence,
                _metadata(c),
            )
            for c, e in zip(chunks, embeddings, strict=True)
        ],
    )


def _metadata(chunk: Chunk) -> str:
    """Provenance per article, which the consolidated XML gives away for free.

    Keeping it lets an answer say *"según la redacción dada por la reforma de 2025"*, and
    it is what `R15` will need when the eval report records where a citation came from.
    """
    import json

    return json.dumps(
        {
            "chunker_id": chunk.chunker_id,
            "id_norma_version": chunk.id_norma_version,
            "fecha_vigencia": chunk.fecha_vigencia,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
