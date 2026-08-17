"""Turn preceptos into the rows of `chunk_v1`.

The identifier contract is **not this project's to invent**: it is
`docs/CONTRACTS/chunks-ddl.sql` v2, shared with `indexkeeper-04`, and it is implemented
here literally::

    doc_id       = sha256(source_uri)[:16]
    content_hash = sha256(normalize(content))     NFC + colapso de espacios + strip
    occurrence   = índice 0-based de esta aparición de content_hash en el documento
    chunk_id     = blake2b(doc_id ‖ content_hash ‖ str(occurrence), digest_size=16)

**The position is not in the hash, and that is the whole point of v2** (ADR-018). With
the ordinal inside, inserting one paragraph renamed every chunk below it and forced a
full re-embed, which made `G-INCR-2` of `indexkeeper-04` unreachable by construction
rather than by implementation. Taking it out means identical text inside one document
needs something else to tell the copies apart — hence `occurrence`, and in legal text
that is not a hypothetical: short apartados repeat verbatim.

Phase 0 makes **one chunk per article**, deliberately (`docs/PLAN.md`: *"una norma,
1 artículo = 1 chunk, solo vectorial"*). The strategy carries a name because
`index_version.chunker_id` is a column of the shared contract, and because phase 2
exists to compare strategies against the golden set — a comparison whose strategy is
not recorded next to the numbers is an anecdote.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, replace

from citebound.domain.legalref import LegalRef
from citebound.ingest.boe_xml import Precepto

__all__ = [
    "CHUNKER_APARTADO_ID",
    "CHUNKER_ID",
    "CHUNKER_MULTINIVEL_ID",
    "Chunk",
    "ChunkingError",
    "chunk_id_de",
    "chunk_multinivel",
    "chunk_por_apartado",
    "chunk_preceptos",
    "content_hash_de",
    "doc_id_de",
    "normalizar_contenido",
]

CHUNKER_ID = "articulo-v1"
CHUNKER_APARTADO_ID = "apartado-v1"
CHUNKER_MULTINIVEL_ID = "multinivel-v1"

_ESPACIOS = re.compile(r"\s+")


class ChunkingError(ValueError):
    """The preceptos cannot be turned into indexable rows."""


@dataclass(frozen=True, slots=True)
class Chunk:
    """One row of `chunk_v1`, as the shared contract defines it."""

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
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub(" ", unicodedata.normalize("NFC", texto)).strip()


def doc_id_de(source_uri: str) -> str:
    """`sha256(source_uri)[:16]`."""
    return hashlib.sha256(source_uri.encode("utf-8")).hexdigest()[:16]


def content_hash_de(contenido: str) -> str:
    """`sha256(normalize(content))`."""
    return hashlib.sha256(normalizar_contenido(contenido).encode("utf-8")).hexdigest()


def chunk_id_de(doc_id: str, content_hash: str, occurrence: int) -> str:
    """`blake2b(doc_id ‖ content_hash ‖ occurrence, digest_size=16)` — no position.

    A pure function of (document, content, occurrence): no timestamps, no random UUIDs,
    no process counters. That is what lets two runs produce the same sequence of ids,
    which is invariant A of the contract.
    """
    semilla = f"{doc_id}{content_hash}{occurrence}".encode()
    return hashlib.blake2b(semilla, digest_size=16).hexdigest()


def chunk_preceptos(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
    """One chunk per article, in document order.

    Repealed preceptos are left out: indexing them would let the system retrieve and
    quote an article that no longer applies — literal, verifiable and wrong, which is
    the failure mode nothing downstream can catch.
    """
    if not preceptos:
        return ()
    if not source_uri.strip():
        raise ChunkingError("source_uri vacío: todos los documentos compartirían doc_id")

    doc_id = doc_id_de(source_uri)
    vistos: dict[str, int] = {}
    chunks: list[Chunk] = []

    for precepto in preceptos:
        if not precepto.vigente:
            continue
        if not precepto.apartados:
            raise ChunkingError(f"{precepto.ref} no tiene texto que indexar")

        content = _contenido(precepto)
        content_hash = content_hash_de(content)
        occurrence = vistos.get(content_hash, 0)
        vistos[content_hash] = occurrence + 1

        chunks.append(
            Chunk(
                chunk_id=chunk_id_de(doc_id, content_hash, occurrence),
                doc_id=doc_id,
                ordinal=len(chunks),
                occurrence=occurrence,
                content=content,
                content_hash=content_hash,
                ref=precepto.ref,
                chunker_id=CHUNKER_ID,
                titulo=precepto.titulo,
                capitulo=precepto.capitulo,
                seccion=precepto.seccion,
                id_norma_version=precepto.id_norma_version,
                fecha_vigencia=precepto.fecha_vigencia,
            )
        )

    return tuple(chunks)


def _contenido(precepto: Precepto) -> str:
    """The rubric on its own line, then the apartados with their numbering restored.

    Leading with `"Artículo 34. Cómputo de carriles."` is the cheapest thing that moves
    recall in a corpus this repetitive: an apartado retrieved on its own reads as an
    orphan sentence, and the embedding has nothing to tell it apart from the fifty other
    paragraphs that also say "se estará a lo dispuesto en el artículo anterior".

    The numbering goes back in because the chunk is what `G-QUOTE-LIT` verifies a quote
    against, and a user reading the answer needs to see which apartado it came from.
    """
    cuerpo = "\n".join(
        f"{a.numero}. {a.texto}" if a.numero is not None else a.texto for a in precepto.apartados
    )
    return f"{precepto.rotulo}. {precepto.rubrica}\n{cuerpo}"


def chunk_por_apartado(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
    """Un chunk por apartado, y uno por artículo cuando el artículo no numera sus párrafos.

    **Por qué existe, medido.** Con `articulo-v1` el artículo entero es un solo embedding
    para varios temas, y los fallos de recall del 2026-08-17 eran confusiones dentro de un
    grupo: los artículos 74, 108, 109 y 110 hablan todos de señalizar maniobras y el
    recuperador elegía mal entre ellos. Un apartado dice una cosa sola.

    **La regla que no se negocia** está en el `if` de abajo: si el apartado no tiene número,
    el chunk se queda a nivel de artículo. Inventar un `1` acuñaría `art34.1`, una referencia
    que **no existe** — la alucinación que `G-HALLUC` está construido para hacer imposible,
    entrando por la puerta de atrás del troceador.

    Cuál de los dos troceados se usa lo decide el número de `make eval-retrieval`, no esta
    docstring; los dos conviven y `chunker_id` dice cuál produjo cada índice.
    """
    if not preceptos:
        return ()
    if not source_uri.strip():
        raise ChunkingError("source_uri vacío: todos los documentos compartirían doc_id")

    doc_id = doc_id_de(source_uri)
    vistos: dict[str, int] = {}
    chunks: list[Chunk] = []

    for precepto in preceptos:
        if not precepto.vigente:
            continue
        if not precepto.apartados:
            raise ChunkingError(f"{precepto.ref} no tiene texto que indexar")

        numerados = [a for a in precepto.apartados if a.numero is not None]
        # Todo o nada por artículo: mezclar un chunk por apartado con otro para los párrafos
        # sueltos partiría el texto de un mismo artículo entre dos referencias distintas, y
        # `G-QUOTE-LIT` verifica cada cita contra UN chunk.
        piezas: list[tuple[LegalRef, str]] = (
            [
                (
                    replace(precepto.ref, apartado=a.numero),
                    f"{precepto.rotulo}. {precepto.rubrica}\n{a.numero}. {a.texto}",
                )
                for a in numerados
            ]
            if len(numerados) == len(precepto.apartados)
            else [(precepto.ref, _contenido(precepto))]
        )

        for ref, content in piezas:
            content_hash = content_hash_de(content)
            occurrence = vistos.get(content_hash, 0)
            vistos[content_hash] = occurrence + 1
            chunks.append(
                Chunk(
                    chunk_id=chunk_id_de(doc_id, content_hash, occurrence),
                    doc_id=doc_id,
                    ordinal=len(chunks),
                    occurrence=occurrence,
                    content=content,
                    content_hash=content_hash,
                    ref=ref,
                    chunker_id=CHUNKER_APARTADO_ID,
                    titulo=precepto.titulo,
                    capitulo=precepto.capitulo,
                    seccion=precepto.seccion,
                    id_norma_version=precepto.id_norma_version,
                    fecha_vigencia=precepto.fecha_vigencia,
                )
            )

    return tuple(chunks)


def chunk_multinivel(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
    """Sin implementar todavía: el rojo se compromete antes que el verde."""
    return ()
