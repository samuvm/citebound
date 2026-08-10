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

CHUNKER_ID = "articulo-v1"

_ESPACIOS = re.compile(r"\s+")


from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated, MutantDict


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
mutants_x_normalizar_contenido__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_normalizar_contenido__mutmut)
def normalizar_contenido(texto: str) -> str:
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub(" ", unicodedata.normalize("NFC", texto)).strip()


def x_normalizar_contenido__mutmut_orig(texto: str) -> str:
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub(" ", unicodedata.normalize("NFC", texto)).strip()


def x_normalizar_contenido__mutmut_1(texto: str) -> str:
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub(None, unicodedata.normalize("NFC", texto)).strip()


def x_normalizar_contenido__mutmut_2(texto: str) -> str:
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub(" ", None).strip()


def x_normalizar_contenido__mutmut_3(texto: str) -> str:
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub(unicodedata.normalize("NFC", texto)).strip()


def x_normalizar_contenido__mutmut_4(texto: str) -> str:
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub(" ", ).strip()


def x_normalizar_contenido__mutmut_5(texto: str) -> str:
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub("XX XX", unicodedata.normalize("NFC", texto)).strip()


def x_normalizar_contenido__mutmut_6(texto: str) -> str:
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub(" ", unicodedata.normalize(None, texto)).strip()


def x_normalizar_contenido__mutmut_7(texto: str) -> str:
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub(" ", unicodedata.normalize("NFC", None)).strip()


def x_normalizar_contenido__mutmut_8(texto: str) -> str:
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub(" ", unicodedata.normalize(texto)).strip()


def x_normalizar_contenido__mutmut_9(texto: str) -> str:
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub(" ", unicodedata.normalize("NFC", )).strip()


def x_normalizar_contenido__mutmut_10(texto: str) -> str:
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub(" ", unicodedata.normalize("XXNFCXX", texto)).strip()


def x_normalizar_contenido__mutmut_11(texto: str) -> str:
    """NFC + collapsed whitespace + strip, exactly as the contract writes it.

    **NFC and not NFKC.** The quote verifier normalises with NFKC (RULES R3) because it
    compares what a model wrote against what the corpus says, and there the two must fold
    together. Here the hash *identifies* the text for another project, so folding
    compatibility characters would silently change the identity of a chunk that nobody
    edited.
    """
    return _ESPACIOS.sub(" ", unicodedata.normalize("nfc", texto)).strip()

mutants_x_normalizar_contenido__mutmut['_mutmut_orig'] = x_normalizar_contenido__mutmut_orig # type: ignore # mutmut generated
mutants_x_normalizar_contenido__mutmut['x_normalizar_contenido__mutmut_1'] = x_normalizar_contenido__mutmut_1 # type: ignore # mutmut generated
mutants_x_normalizar_contenido__mutmut['x_normalizar_contenido__mutmut_2'] = x_normalizar_contenido__mutmut_2 # type: ignore # mutmut generated
mutants_x_normalizar_contenido__mutmut['x_normalizar_contenido__mutmut_3'] = x_normalizar_contenido__mutmut_3 # type: ignore # mutmut generated
mutants_x_normalizar_contenido__mutmut['x_normalizar_contenido__mutmut_4'] = x_normalizar_contenido__mutmut_4 # type: ignore # mutmut generated
mutants_x_normalizar_contenido__mutmut['x_normalizar_contenido__mutmut_5'] = x_normalizar_contenido__mutmut_5 # type: ignore # mutmut generated
mutants_x_normalizar_contenido__mutmut['x_normalizar_contenido__mutmut_6'] = x_normalizar_contenido__mutmut_6 # type: ignore # mutmut generated
mutants_x_normalizar_contenido__mutmut['x_normalizar_contenido__mutmut_7'] = x_normalizar_contenido__mutmut_7 # type: ignore # mutmut generated
mutants_x_normalizar_contenido__mutmut['x_normalizar_contenido__mutmut_8'] = x_normalizar_contenido__mutmut_8 # type: ignore # mutmut generated
mutants_x_normalizar_contenido__mutmut['x_normalizar_contenido__mutmut_9'] = x_normalizar_contenido__mutmut_9 # type: ignore # mutmut generated
mutants_x_normalizar_contenido__mutmut['x_normalizar_contenido__mutmut_10'] = x_normalizar_contenido__mutmut_10 # type: ignore # mutmut generated
mutants_x_normalizar_contenido__mutmut['x_normalizar_contenido__mutmut_11'] = x_normalizar_contenido__mutmut_11 # type: ignore # mutmut generated
mutants_x_doc_id_de__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_doc_id_de__mutmut)
def doc_id_de(source_uri: str) -> str:
    """`sha256(source_uri)[:16]`."""
    return hashlib.sha256(source_uri.encode("utf-8")).hexdigest()[:16]


def x_doc_id_de__mutmut_orig(source_uri: str) -> str:
    """`sha256(source_uri)[:16]`."""
    return hashlib.sha256(source_uri.encode("utf-8")).hexdigest()[:16]


def x_doc_id_de__mutmut_1(source_uri: str) -> str:
    """`sha256(source_uri)[:16]`."""
    return hashlib.sha256(None).hexdigest()[:16]


def x_doc_id_de__mutmut_2(source_uri: str) -> str:
    """`sha256(source_uri)[:16]`."""
    return hashlib.sha256(source_uri.encode(None)).hexdigest()[:16]


def x_doc_id_de__mutmut_3(source_uri: str) -> str:
    """`sha256(source_uri)[:16]`."""
    return hashlib.sha256(source_uri.encode("XXutf-8XX")).hexdigest()[:16]


def x_doc_id_de__mutmut_4(source_uri: str) -> str:
    """`sha256(source_uri)[:16]`."""
    return hashlib.sha256(source_uri.encode("UTF-8")).hexdigest()[:16]


def x_doc_id_de__mutmut_5(source_uri: str) -> str:
    """`sha256(source_uri)[:16]`."""
    return hashlib.sha256(source_uri.encode("utf-8")).hexdigest()[:17]

mutants_x_doc_id_de__mutmut['_mutmut_orig'] = x_doc_id_de__mutmut_orig # type: ignore # mutmut generated
mutants_x_doc_id_de__mutmut['x_doc_id_de__mutmut_1'] = x_doc_id_de__mutmut_1 # type: ignore # mutmut generated
mutants_x_doc_id_de__mutmut['x_doc_id_de__mutmut_2'] = x_doc_id_de__mutmut_2 # type: ignore # mutmut generated
mutants_x_doc_id_de__mutmut['x_doc_id_de__mutmut_3'] = x_doc_id_de__mutmut_3 # type: ignore # mutmut generated
mutants_x_doc_id_de__mutmut['x_doc_id_de__mutmut_4'] = x_doc_id_de__mutmut_4 # type: ignore # mutmut generated
mutants_x_doc_id_de__mutmut['x_doc_id_de__mutmut_5'] = x_doc_id_de__mutmut_5 # type: ignore # mutmut generated
mutants_x_content_hash_de__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_content_hash_de__mutmut)
def content_hash_de(contenido: str) -> str:
    """`sha256(normalize(content))`."""
    return hashlib.sha256(normalizar_contenido(contenido).encode("utf-8")).hexdigest()


def x_content_hash_de__mutmut_orig(contenido: str) -> str:
    """`sha256(normalize(content))`."""
    return hashlib.sha256(normalizar_contenido(contenido).encode("utf-8")).hexdigest()


def x_content_hash_de__mutmut_1(contenido: str) -> str:
    """`sha256(normalize(content))`."""
    return hashlib.sha256(None).hexdigest()


def x_content_hash_de__mutmut_2(contenido: str) -> str:
    """`sha256(normalize(content))`."""
    return hashlib.sha256(normalizar_contenido(contenido).encode(None)).hexdigest()


def x_content_hash_de__mutmut_3(contenido: str) -> str:
    """`sha256(normalize(content))`."""
    return hashlib.sha256(normalizar_contenido(None).encode("utf-8")).hexdigest()


def x_content_hash_de__mutmut_4(contenido: str) -> str:
    """`sha256(normalize(content))`."""
    return hashlib.sha256(normalizar_contenido(contenido).encode("XXutf-8XX")).hexdigest()


def x_content_hash_de__mutmut_5(contenido: str) -> str:
    """`sha256(normalize(content))`."""
    return hashlib.sha256(normalizar_contenido(contenido).encode("UTF-8")).hexdigest()

mutants_x_content_hash_de__mutmut['_mutmut_orig'] = x_content_hash_de__mutmut_orig # type: ignore # mutmut generated
mutants_x_content_hash_de__mutmut['x_content_hash_de__mutmut_1'] = x_content_hash_de__mutmut_1 # type: ignore # mutmut generated
mutants_x_content_hash_de__mutmut['x_content_hash_de__mutmut_2'] = x_content_hash_de__mutmut_2 # type: ignore # mutmut generated
mutants_x_content_hash_de__mutmut['x_content_hash_de__mutmut_3'] = x_content_hash_de__mutmut_3 # type: ignore # mutmut generated
mutants_x_content_hash_de__mutmut['x_content_hash_de__mutmut_4'] = x_content_hash_de__mutmut_4 # type: ignore # mutmut generated
mutants_x_content_hash_de__mutmut['x_content_hash_de__mutmut_5'] = x_content_hash_de__mutmut_5 # type: ignore # mutmut generated
mutants_x_chunk_id_de__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_chunk_id_de__mutmut)
def chunk_id_de(doc_id: str, content_hash: str, occurrence: int) -> str:
    """`blake2b(doc_id ‖ content_hash ‖ occurrence, digest_size=16)` — no position.

    A pure function of (document, content, occurrence): no timestamps, no random UUIDs,
    no process counters. That is what lets two runs produce the same sequence of ids,
    which is invariant A of the contract.
    """
    semilla = f"{doc_id}{content_hash}{occurrence}".encode()
    return hashlib.blake2b(semilla, digest_size=16).hexdigest()


def x_chunk_id_de__mutmut_orig(doc_id: str, content_hash: str, occurrence: int) -> str:
    """`blake2b(doc_id ‖ content_hash ‖ occurrence, digest_size=16)` — no position.

    A pure function of (document, content, occurrence): no timestamps, no random UUIDs,
    no process counters. That is what lets two runs produce the same sequence of ids,
    which is invariant A of the contract.
    """
    semilla = f"{doc_id}{content_hash}{occurrence}".encode()
    return hashlib.blake2b(semilla, digest_size=16).hexdigest()


def x_chunk_id_de__mutmut_1(doc_id: str, content_hash: str, occurrence: int) -> str:
    """`blake2b(doc_id ‖ content_hash ‖ occurrence, digest_size=16)` — no position.

    A pure function of (document, content, occurrence): no timestamps, no random UUIDs,
    no process counters. That is what lets two runs produce the same sequence of ids,
    which is invariant A of the contract.
    """
    semilla = None
    return hashlib.blake2b(semilla, digest_size=16).hexdigest()


def x_chunk_id_de__mutmut_2(doc_id: str, content_hash: str, occurrence: int) -> str:
    """`blake2b(doc_id ‖ content_hash ‖ occurrence, digest_size=16)` — no position.

    A pure function of (document, content, occurrence): no timestamps, no random UUIDs,
    no process counters. That is what lets two runs produce the same sequence of ids,
    which is invariant A of the contract.
    """
    semilla = f"{doc_id}{content_hash}{occurrence}".encode()
    return hashlib.blake2b(None, digest_size=16).hexdigest()


def x_chunk_id_de__mutmut_3(doc_id: str, content_hash: str, occurrence: int) -> str:
    """`blake2b(doc_id ‖ content_hash ‖ occurrence, digest_size=16)` — no position.

    A pure function of (document, content, occurrence): no timestamps, no random UUIDs,
    no process counters. That is what lets two runs produce the same sequence of ids,
    which is invariant A of the contract.
    """
    semilla = f"{doc_id}{content_hash}{occurrence}".encode()
    return hashlib.blake2b(semilla, digest_size=None).hexdigest()


def x_chunk_id_de__mutmut_4(doc_id: str, content_hash: str, occurrence: int) -> str:
    """`blake2b(doc_id ‖ content_hash ‖ occurrence, digest_size=16)` — no position.

    A pure function of (document, content, occurrence): no timestamps, no random UUIDs,
    no process counters. That is what lets two runs produce the same sequence of ids,
    which is invariant A of the contract.
    """
    semilla = f"{doc_id}{content_hash}{occurrence}".encode()
    return hashlib.blake2b(digest_size=16).hexdigest()


def x_chunk_id_de__mutmut_5(doc_id: str, content_hash: str, occurrence: int) -> str:
    """`blake2b(doc_id ‖ content_hash ‖ occurrence, digest_size=16)` — no position.

    A pure function of (document, content, occurrence): no timestamps, no random UUIDs,
    no process counters. That is what lets two runs produce the same sequence of ids,
    which is invariant A of the contract.
    """
    semilla = f"{doc_id}{content_hash}{occurrence}".encode()
    return hashlib.blake2b(semilla, ).hexdigest()


def x_chunk_id_de__mutmut_6(doc_id: str, content_hash: str, occurrence: int) -> str:
    """`blake2b(doc_id ‖ content_hash ‖ occurrence, digest_size=16)` — no position.

    A pure function of (document, content, occurrence): no timestamps, no random UUIDs,
    no process counters. That is what lets two runs produce the same sequence of ids,
    which is invariant A of the contract.
    """
    semilla = f"{doc_id}{content_hash}{occurrence}".encode()
    return hashlib.blake2b(semilla, digest_size=17).hexdigest()

mutants_x_chunk_id_de__mutmut['_mutmut_orig'] = x_chunk_id_de__mutmut_orig # type: ignore # mutmut generated
mutants_x_chunk_id_de__mutmut['x_chunk_id_de__mutmut_1'] = x_chunk_id_de__mutmut_1 # type: ignore # mutmut generated
mutants_x_chunk_id_de__mutmut['x_chunk_id_de__mutmut_2'] = x_chunk_id_de__mutmut_2 # type: ignore # mutmut generated
mutants_x_chunk_id_de__mutmut['x_chunk_id_de__mutmut_3'] = x_chunk_id_de__mutmut_3 # type: ignore # mutmut generated
mutants_x_chunk_id_de__mutmut['x_chunk_id_de__mutmut_4'] = x_chunk_id_de__mutmut_4 # type: ignore # mutmut generated
mutants_x_chunk_id_de__mutmut['x_chunk_id_de__mutmut_5'] = x_chunk_id_de__mutmut_5 # type: ignore # mutmut generated
mutants_x_chunk_id_de__mutmut['x_chunk_id_de__mutmut_6'] = x_chunk_id_de__mutmut_6 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_chunk_preceptos__mutmut)
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


def x_chunk_preceptos__mutmut_orig(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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


def x_chunk_preceptos__mutmut_1(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
    """One chunk per article, in document order.

    Repealed preceptos are left out: indexing them would let the system retrieve and
    quote an article that no longer applies — literal, verifiable and wrong, which is
    the failure mode nothing downstream can catch.
    """
    if preceptos:
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


def x_chunk_preceptos__mutmut_2(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
    """One chunk per article, in document order.

    Repealed preceptos are left out: indexing them would let the system retrieve and
    quote an article that no longer applies — literal, verifiable and wrong, which is
    the failure mode nothing downstream can catch.
    """
    if not preceptos:
        return ()
    if source_uri.strip():
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


def x_chunk_preceptos__mutmut_3(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
    """One chunk per article, in document order.

    Repealed preceptos are left out: indexing them would let the system retrieve and
    quote an article that no longer applies — literal, verifiable and wrong, which is
    the failure mode nothing downstream can catch.
    """
    if not preceptos:
        return ()
    if not source_uri.strip():
        raise ChunkingError(None)

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


def x_chunk_preceptos__mutmut_4(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
    """One chunk per article, in document order.

    Repealed preceptos are left out: indexing them would let the system retrieve and
    quote an article that no longer applies — literal, verifiable and wrong, which is
    the failure mode nothing downstream can catch.
    """
    if not preceptos:
        return ()
    if not source_uri.strip():
        raise ChunkingError("XXsource_uri vacío: todos los documentos compartirían doc_idXX")

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


def x_chunk_preceptos__mutmut_5(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
    """One chunk per article, in document order.

    Repealed preceptos are left out: indexing them would let the system retrieve and
    quote an article that no longer applies — literal, verifiable and wrong, which is
    the failure mode nothing downstream can catch.
    """
    if not preceptos:
        return ()
    if not source_uri.strip():
        raise ChunkingError("SOURCE_URI VACÍO: TODOS LOS DOCUMENTOS COMPARTIRÍAN DOC_ID")

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


def x_chunk_preceptos__mutmut_6(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
    """One chunk per article, in document order.

    Repealed preceptos are left out: indexing them would let the system retrieve and
    quote an article that no longer applies — literal, verifiable and wrong, which is
    the failure mode nothing downstream can catch.
    """
    if not preceptos:
        return ()
    if not source_uri.strip():
        raise ChunkingError("source_uri vacío: todos los documentos compartirían doc_id")

    doc_id = None
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


def x_chunk_preceptos__mutmut_7(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
    """One chunk per article, in document order.

    Repealed preceptos are left out: indexing them would let the system retrieve and
    quote an article that no longer applies — literal, verifiable and wrong, which is
    the failure mode nothing downstream can catch.
    """
    if not preceptos:
        return ()
    if not source_uri.strip():
        raise ChunkingError("source_uri vacío: todos los documentos compartirían doc_id")

    doc_id = doc_id_de(None)
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


def x_chunk_preceptos__mutmut_8(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
    vistos: dict[str, int] = None
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


def x_chunk_preceptos__mutmut_9(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
    chunks: list[Chunk] = None

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


def x_chunk_preceptos__mutmut_10(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
        if precepto.vigente:
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


def x_chunk_preceptos__mutmut_11(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
            break
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


def x_chunk_preceptos__mutmut_12(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
        if precepto.apartados:
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


def x_chunk_preceptos__mutmut_13(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
            raise ChunkingError(None)

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


def x_chunk_preceptos__mutmut_14(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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

        content = None
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


def x_chunk_preceptos__mutmut_15(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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

        content = _contenido(None)
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


def x_chunk_preceptos__mutmut_16(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
        content_hash = None
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


def x_chunk_preceptos__mutmut_17(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
        content_hash = content_hash_de(None)
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


def x_chunk_preceptos__mutmut_18(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
        occurrence = None
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


def x_chunk_preceptos__mutmut_19(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
        occurrence = vistos.get(None, 0)
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


def x_chunk_preceptos__mutmut_20(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
        occurrence = vistos.get(content_hash, None)
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


def x_chunk_preceptos__mutmut_21(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
        occurrence = vistos.get(0)
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


def x_chunk_preceptos__mutmut_22(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
        occurrence = vistos.get(content_hash, )
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


def x_chunk_preceptos__mutmut_23(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
        occurrence = vistos.get(content_hash, 1)
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


def x_chunk_preceptos__mutmut_24(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
        vistos[content_hash] = None

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


def x_chunk_preceptos__mutmut_25(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
        vistos[content_hash] = occurrence - 1

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


def x_chunk_preceptos__mutmut_26(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
        vistos[content_hash] = occurrence + 2

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


def x_chunk_preceptos__mutmut_27(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
            None
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_28(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                chunk_id=None,
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


def x_chunk_preceptos__mutmut_29(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                doc_id=None,
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


def x_chunk_preceptos__mutmut_30(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                ordinal=None,
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


def x_chunk_preceptos__mutmut_31(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                occurrence=None,
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


def x_chunk_preceptos__mutmut_32(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                content=None,
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


def x_chunk_preceptos__mutmut_33(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                content_hash=None,
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


def x_chunk_preceptos__mutmut_34(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                ref=None,
                chunker_id=CHUNKER_ID,
                titulo=precepto.titulo,
                capitulo=precepto.capitulo,
                seccion=precepto.seccion,
                id_norma_version=precepto.id_norma_version,
                fecha_vigencia=precepto.fecha_vigencia,
            )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_35(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                chunker_id=None,
                titulo=precepto.titulo,
                capitulo=precepto.capitulo,
                seccion=precepto.seccion,
                id_norma_version=precepto.id_norma_version,
                fecha_vigencia=precepto.fecha_vigencia,
            )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_36(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                titulo=None,
                capitulo=precepto.capitulo,
                seccion=precepto.seccion,
                id_norma_version=precepto.id_norma_version,
                fecha_vigencia=precepto.fecha_vigencia,
            )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_37(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                capitulo=None,
                seccion=precepto.seccion,
                id_norma_version=precepto.id_norma_version,
                fecha_vigencia=precepto.fecha_vigencia,
            )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_38(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                seccion=None,
                id_norma_version=precepto.id_norma_version,
                fecha_vigencia=precepto.fecha_vigencia,
            )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_39(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                id_norma_version=None,
                fecha_vigencia=precepto.fecha_vigencia,
            )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_40(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                fecha_vigencia=None,
            )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_41(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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


def x_chunk_preceptos__mutmut_42(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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


def x_chunk_preceptos__mutmut_43(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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


def x_chunk_preceptos__mutmut_44(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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


def x_chunk_preceptos__mutmut_45(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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


def x_chunk_preceptos__mutmut_46(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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


def x_chunk_preceptos__mutmut_47(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                chunker_id=CHUNKER_ID,
                titulo=precepto.titulo,
                capitulo=precepto.capitulo,
                seccion=precepto.seccion,
                id_norma_version=precepto.id_norma_version,
                fecha_vigencia=precepto.fecha_vigencia,
            )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_48(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                titulo=precepto.titulo,
                capitulo=precepto.capitulo,
                seccion=precepto.seccion,
                id_norma_version=precepto.id_norma_version,
                fecha_vigencia=precepto.fecha_vigencia,
            )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_49(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                capitulo=precepto.capitulo,
                seccion=precepto.seccion,
                id_norma_version=precepto.id_norma_version,
                fecha_vigencia=precepto.fecha_vigencia,
            )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_50(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                seccion=precepto.seccion,
                id_norma_version=precepto.id_norma_version,
                fecha_vigencia=precepto.fecha_vigencia,
            )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_51(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                id_norma_version=precepto.id_norma_version,
                fecha_vigencia=precepto.fecha_vigencia,
            )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_52(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                fecha_vigencia=precepto.fecha_vigencia,
            )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_53(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                )
        )

    return tuple(chunks)


def x_chunk_preceptos__mutmut_54(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                chunk_id=chunk_id_de(None, content_hash, occurrence),
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


def x_chunk_preceptos__mutmut_55(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                chunk_id=chunk_id_de(doc_id, None, occurrence),
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


def x_chunk_preceptos__mutmut_56(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                chunk_id=chunk_id_de(doc_id, content_hash, None),
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


def x_chunk_preceptos__mutmut_57(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                chunk_id=chunk_id_de(content_hash, occurrence),
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


def x_chunk_preceptos__mutmut_58(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                chunk_id=chunk_id_de(doc_id, occurrence),
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


def x_chunk_preceptos__mutmut_59(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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
                chunk_id=chunk_id_de(doc_id, content_hash, ),
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


def x_chunk_preceptos__mutmut_60(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
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

    return tuple(None)

mutants_x_chunk_preceptos__mutmut['_mutmut_orig'] = x_chunk_preceptos__mutmut_orig # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_1'] = x_chunk_preceptos__mutmut_1 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_2'] = x_chunk_preceptos__mutmut_2 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_3'] = x_chunk_preceptos__mutmut_3 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_4'] = x_chunk_preceptos__mutmut_4 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_5'] = x_chunk_preceptos__mutmut_5 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_6'] = x_chunk_preceptos__mutmut_6 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_7'] = x_chunk_preceptos__mutmut_7 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_8'] = x_chunk_preceptos__mutmut_8 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_9'] = x_chunk_preceptos__mutmut_9 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_10'] = x_chunk_preceptos__mutmut_10 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_11'] = x_chunk_preceptos__mutmut_11 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_12'] = x_chunk_preceptos__mutmut_12 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_13'] = x_chunk_preceptos__mutmut_13 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_14'] = x_chunk_preceptos__mutmut_14 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_15'] = x_chunk_preceptos__mutmut_15 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_16'] = x_chunk_preceptos__mutmut_16 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_17'] = x_chunk_preceptos__mutmut_17 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_18'] = x_chunk_preceptos__mutmut_18 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_19'] = x_chunk_preceptos__mutmut_19 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_20'] = x_chunk_preceptos__mutmut_20 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_21'] = x_chunk_preceptos__mutmut_21 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_22'] = x_chunk_preceptos__mutmut_22 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_23'] = x_chunk_preceptos__mutmut_23 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_24'] = x_chunk_preceptos__mutmut_24 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_25'] = x_chunk_preceptos__mutmut_25 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_26'] = x_chunk_preceptos__mutmut_26 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_27'] = x_chunk_preceptos__mutmut_27 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_28'] = x_chunk_preceptos__mutmut_28 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_29'] = x_chunk_preceptos__mutmut_29 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_30'] = x_chunk_preceptos__mutmut_30 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_31'] = x_chunk_preceptos__mutmut_31 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_32'] = x_chunk_preceptos__mutmut_32 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_33'] = x_chunk_preceptos__mutmut_33 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_34'] = x_chunk_preceptos__mutmut_34 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_35'] = x_chunk_preceptos__mutmut_35 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_36'] = x_chunk_preceptos__mutmut_36 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_37'] = x_chunk_preceptos__mutmut_37 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_38'] = x_chunk_preceptos__mutmut_38 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_39'] = x_chunk_preceptos__mutmut_39 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_40'] = x_chunk_preceptos__mutmut_40 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_41'] = x_chunk_preceptos__mutmut_41 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_42'] = x_chunk_preceptos__mutmut_42 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_43'] = x_chunk_preceptos__mutmut_43 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_44'] = x_chunk_preceptos__mutmut_44 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_45'] = x_chunk_preceptos__mutmut_45 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_46'] = x_chunk_preceptos__mutmut_46 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_47'] = x_chunk_preceptos__mutmut_47 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_48'] = x_chunk_preceptos__mutmut_48 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_49'] = x_chunk_preceptos__mutmut_49 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_50'] = x_chunk_preceptos__mutmut_50 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_51'] = x_chunk_preceptos__mutmut_51 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_52'] = x_chunk_preceptos__mutmut_52 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_53'] = x_chunk_preceptos__mutmut_53 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_54'] = x_chunk_preceptos__mutmut_54 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_55'] = x_chunk_preceptos__mutmut_55 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_56'] = x_chunk_preceptos__mutmut_56 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_57'] = x_chunk_preceptos__mutmut_57 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_58'] = x_chunk_preceptos__mutmut_58 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_59'] = x_chunk_preceptos__mutmut_59 # type: ignore # mutmut generated
mutants_x_chunk_preceptos__mutmut['x_chunk_preceptos__mutmut_60'] = x_chunk_preceptos__mutmut_60 # type: ignore # mutmut generated
mutants_x__contenido__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x__contenido__mutmut)
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


def x__contenido__mutmut_orig(precepto: Precepto) -> str:
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


def x__contenido__mutmut_1(precepto: Precepto) -> str:
    """The rubric on its own line, then the apartados with their numbering restored.

    Leading with `"Artículo 34. Cómputo de carriles."` is the cheapest thing that moves
    recall in a corpus this repetitive: an apartado retrieved on its own reads as an
    orphan sentence, and the embedding has nothing to tell it apart from the fifty other
    paragraphs that also say "se estará a lo dispuesto en el artículo anterior".

    The numbering goes back in because the chunk is what `G-QUOTE-LIT` verifies a quote
    against, and a user reading the answer needs to see which apartado it came from.
    """
    cuerpo = None
    return f"{precepto.rotulo}. {precepto.rubrica}\n{cuerpo}"


def x__contenido__mutmut_2(precepto: Precepto) -> str:
    """The rubric on its own line, then the apartados with their numbering restored.

    Leading with `"Artículo 34. Cómputo de carriles."` is the cheapest thing that moves
    recall in a corpus this repetitive: an apartado retrieved on its own reads as an
    orphan sentence, and the embedding has nothing to tell it apart from the fifty other
    paragraphs that also say "se estará a lo dispuesto en el artículo anterior".

    The numbering goes back in because the chunk is what `G-QUOTE-LIT` verifies a quote
    against, and a user reading the answer needs to see which apartado it came from.
    """
    cuerpo = "\n".join(
        None
    )
    return f"{precepto.rotulo}. {precepto.rubrica}\n{cuerpo}"


def x__contenido__mutmut_3(precepto: Precepto) -> str:
    """The rubric on its own line, then the apartados with their numbering restored.

    Leading with `"Artículo 34. Cómputo de carriles."` is the cheapest thing that moves
    recall in a corpus this repetitive: an apartado retrieved on its own reads as an
    orphan sentence, and the embedding has nothing to tell it apart from the fifty other
    paragraphs that also say "se estará a lo dispuesto en el artículo anterior".

    The numbering goes back in because the chunk is what `G-QUOTE-LIT` verifies a quote
    against, and a user reading the answer needs to see which apartado it came from.
    """
    cuerpo = "XX\nXX".join(
        f"{a.numero}. {a.texto}" if a.numero is not None else a.texto for a in precepto.apartados
    )
    return f"{precepto.rotulo}. {precepto.rubrica}\n{cuerpo}"


def x__contenido__mutmut_4(precepto: Precepto) -> str:
    """The rubric on its own line, then the apartados with their numbering restored.

    Leading with `"Artículo 34. Cómputo de carriles."` is the cheapest thing that moves
    recall in a corpus this repetitive: an apartado retrieved on its own reads as an
    orphan sentence, and the embedding has nothing to tell it apart from the fifty other
    paragraphs that also say "se estará a lo dispuesto en el artículo anterior".

    The numbering goes back in because the chunk is what `G-QUOTE-LIT` verifies a quote
    against, and a user reading the answer needs to see which apartado it came from.
    """
    cuerpo = "\n".join(
        f"{a.numero}. {a.texto}" if a.numero is None else a.texto for a in precepto.apartados
    )
    return f"{precepto.rotulo}. {precepto.rubrica}\n{cuerpo}"

mutants_x__contenido__mutmut['_mutmut_orig'] = x__contenido__mutmut_orig # type: ignore # mutmut generated
mutants_x__contenido__mutmut['x__contenido__mutmut_1'] = x__contenido__mutmut_1 # type: ignore # mutmut generated
mutants_x__contenido__mutmut['x__contenido__mutmut_2'] = x__contenido__mutmut_2 # type: ignore # mutmut generated
mutants_x__contenido__mutmut['x__contenido__mutmut_3'] = x__contenido__mutmut_3 # type: ignore # mutmut generated
mutants_x__contenido__mutmut['x__contenido__mutmut_4'] = x__contenido__mutmut_4 # type: ignore # mutmut generated
