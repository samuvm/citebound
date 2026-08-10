"""Corpus -> chunks -> Postgres, and the `refs.json` the smoke test checks against.

The one place that wires the ingest layers together. Kept out of `boe_xml` and `chunking`
on purpose: those two are pure and carry TDD-obligatorio; this one touches the network,
the disk and the database, so it is exercised by integration and by `make smoke-f0`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from citebound.db.schema import registrar_index_version, upsert_chunks
from citebound.ingest.boe_xml import parse_norma
from citebound.ingest.chunking import CHUNKER_ID, Chunk, chunk_preceptos
from citebound.providers.embeddings import Embedder

__all__ = ["Ingesta", "escribir_refs", "ingerir", "refs_conocidas"]


class _Cursor(Protocol):
    def execute(self, query: str, params: Any = ..., /) -> Any: ...
    def executemany(self, query: str, params: Any, /) -> Any: ...


@dataclass(frozen=True, slots=True)
class Ingesta:
    """What one ingest produced, with everything a report needs to be reproducible."""

    index_id: str
    chunks: tuple[Chunk, ...]
    refs: tuple[str, ...]


def ingerir(
    cur: _Cursor,
    *,
    xml: str,
    norma: str,
    source_uri: str,
    embedder: Embedder,
    corpus_snapshot: str,
    index_id: str | None = None,
    lote: int = 32,
) -> Ingesta:
    """Parse, chunk, embed and write. Idempotent by construction.

    Running it twice inserts nothing new: `chunk_id` is a pure function of (document,
    content, occurrence), so the second pass computes the ids of the first and
    `ON CONFLICT` has nothing to add. That property is contract v2's whole reason to
    exist, and `tests/integration/test_ddl.py` proves it on the real corpus.
    """
    preceptos = parse_norma(xml, norma=norma)
    chunks = chunk_preceptos(preceptos, source_uri=source_uri)
    identificador = index_id or f"v1-{embedder.model.replace(':', '-')}-{embedder.dim}"

    registrar_index_version(
        cur,
        index_id=identificador,
        embedding_model=embedder.model,
        dim=embedder.dim,
        chunker_id=CHUNKER_ID,
        corpus_snapshot=corpus_snapshot,
    )

    # In batches so that a corpus larger than this one does not send a single request
    # the size of the whole document.
    for inicio in range(0, len(chunks), lote):
        trozo = chunks[inicio : inicio + lote]
        vectores = embedder.embed([c.content for c in trozo])
        upsert_chunks(cur, trozo, vectores, index_id=identificador)

    return Ingesta(
        index_id=identificador,
        chunks=chunks,
        refs=tuple(str(c.ref) for c in chunks),
    )


def escribir_refs(destino: Path, ingesta: Ingesta, *, norma: str, corpus_snapshot: str) -> None:
    """`corpus/index/refs.json`: the set `G-HALLUC` checks membership against.

    Derived and regenerable, never hand-edited (R4), which is why it lives outside git.
    It is what makes "the reference exists" a set lookup — deterministic, free, and
    impossible for a model to argue with.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(
            {
                "norma": norma,
                "index_version": ingesta.index_id,
                "chunker_id": CHUNKER_ID,
                "corpus_snapshot": corpus_snapshot,
                "n": len(ingesta.refs),
                "refs": sorted(set(ingesta.refs)),
            },
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def refs_conocidas(origen: Path) -> frozenset[str]:
    """The refs of the active index, for whoever needs to check membership."""
    if not origen.is_file():
        raise FileNotFoundError(
            f"falta {origen}: el índice no se ha generado. Ejecuta la ingesta primero."
        )
    return frozenset(json.loads(origen.read_text(encoding="utf-8"))["refs"])
