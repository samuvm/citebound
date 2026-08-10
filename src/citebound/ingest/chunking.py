"""Turn preceptos into the rows of `chunk_v1`.

FASE ROJA DE TDD — tarea 0.4. Tipos y firmas son diseño; el COMPORTAMIENTO está
deliberadamente sin implementar, para que la suite falle por la aserción y no por un
`ImportError`, que no es rojo sino ruido (constitución §4.1).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from citebound.domain.legalref import LegalRef
from citebound.ingest.boe_xml import Precepto

__all__ = [
    "CHUNKER_ID",
    "Chunk",
    "ChunkingError",
    "chunk_id_de",
    "chunk_preceptos",
    "content_hash_de",
    "doc_id_de",
    "normalizar_contenido",
]

# `index_version.chunker_id` es columna del contrato compartido: la estrategia se nombra.
CHUNKER_ID = "articulo-v1"


class ChunkingError(ValueError):
    """The preceptos cannot be turned into indexable rows."""


@dataclass(frozen=True, slots=True)
class Chunk:
    """One row of `chunk_v1`, as `docs/CONTRACTS/chunks-ddl.sql` v2 defines it."""

    chunk_id: str
    doc_id: str
    ordinal: int
    occurrence: int
    content: str
    content_hash: str
    ref: LegalRef
    chunker_id: str
    titulo: str | None
    capitulo: str | None
    seccion: str | None
    id_norma_version: str
    fecha_vigencia: str | None


def normalizar_contenido(texto: str) -> str:
    """NFC + colapso de espacios + strip, literal del contrato."""
    return texto  # RED


def doc_id_de(source_uri: str) -> str:
    """`sha256(source_uri)[:16]`."""
    return ""  # RED


def content_hash_de(contenido: str) -> str:
    """`sha256(normalize(content))`."""
    return ""  # RED


def chunk_id_de(doc_id: str, content_hash: str, occurrence: int) -> str:
    """`blake2b(doc_id ‖ content_hash ‖ occurrence, digest_size=16)`. Sin la posición."""
    return ""  # RED


def chunk_preceptos(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
    """One chunk per article in phase 0 (`docs/PLAN.md`)."""
    # RED: forma correcta, valores deliberadamente equivocados. Devolver una tupla vacía
    # haría fallar los tests por `IndexError` al indexarla, y un rojo por índice no es
    # evidencia de nada: el rojo tiene que venir de la aserción (constitución §4.1).
    return tuple(
        Chunk(
            chunk_id="",
            doc_id="",
            ordinal=-1,
            occurrence=-1,
            content="",
            content_hash="",
            ref=p.ref,
            chunker_id="",
            titulo=None,
            capitulo=None,
            seccion=None,
            id_norma_version="",
            fecha_vigencia=None,
        )
        for p in preceptos
    )
