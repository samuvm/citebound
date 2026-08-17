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
from collections import Counter
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
    "exigir_ids_unicos",
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


def exigir_ids_unicos(chunks: Sequence[Chunk]) -> None:
    """Revienta si dos chunks comparten `chunk_id`. Se comprueba en vez de confiar.

    Cada troceador cuenta sus `occurrence` por su cuenta, así que al juntar dos niveles un
    contenido repetido da el **mismo** identificador — y `chunk_id` es la clave primaria, de
    modo que una fila se comería a la otra en el `ON CONFLICT` **sin decir nada**. El síntoma
    aparecería mucho más lejos, como un recall peor sin causa aparente.

    Saltó de verdad el 2026-08-17 con 94 repetidos en el corpus real, y la causa era semántica
    y no aritmética: los 94 artículos que no numeran sus párrafos, donde el nivel fino ya
    devuelve el artículo entero. El arreglo fue no añadirlo dos veces; esto se queda como
    red, porque comprobar cuesta una línea.
    """
    repetidos = sorted(
        {c.chunk_id for c in chunks if [x.chunk_id for x in chunks].count(c.chunk_id) > 1}
    )
    if repetidos:
        raise ChunkingError(
            f"dos niveles produjeron el mismo chunk_id ({len(repetidos)}): "
            f"la ingesta perdería una fila sin avisar. Primero: {repetidos[0]}"
        )


def chunk_multinivel(preceptos: Sequence[Precepto], source_uri: str) -> tuple[Chunk, ...]:
    """El artículo entero **y además** cada uno de sus apartados, en el mismo índice.

    **Por qué existen los tres troceados y no uno.** Medido el 2026-08-17 sobre los mismos
    216 casos, cada uno gana en una cosa distinta:

    | troceado | recall@5 de artículo, con reordenador | recall@5 estricto |
    |---|---:|---:|
    | `articulo-v1` | **0,847** | 0,093 |
    | `apartado-v1` | 0,806 | **0,500** |

    El artículo entero recupera mejor —su embedding tiene contexto— y el apartado cita mejor
    —su referencia es la que pide el golden set—. Indexar los dos da al recuperador dos formas
    de encontrar el mismo artículo, y al colapso por artículo de `retrieval.pipeline` le toca
    quedarse con la que mejor haya salido.

    **Un artículo de un solo apartado no se indexa dos veces**: ahí el artículo *es* el
    apartado, los dos trozos tendrían el mismo texto, y dos filas idénticas gastan plaza en
    el top-30 sin añadir nada. Es el mismo desperdicio que el colapso existe para quitar.
    """
    apartados = chunk_por_apartado(preceptos, source_uri)
    # Cuántos trozos produjo el nivel fino para cada artículo. Solo se añade el artículo
    # entero cuando ahí hubo de verdad una partición: si el artículo no numera sus párrafos
    # —94 del corpus— el nivel fino ya devolvió el artículo completo, y añadirlo otra vez
    # sería la misma fila dos veces. Con el mismo texto sale el mismo `chunk_id`, así que una
    # se comería a la otra en el `ON CONFLICT` sin decir nada.
    troceados = Counter(f"{c.ref.norma}#art{c.ref.articulo}" for c in apartados)
    articulos = [
        c
        for c in chunk_preceptos(preceptos, source_uri)
        if troceados[f"{c.ref.norma}#art{c.ref.articulo}"] > 1
    ]
    juntos = [*articulos, *apartados]
    exigir_ids_unicos(juntos)
    return tuple(
        replace(chunk, ordinal=i, chunker_id=CHUNKER_MULTINIVEL_ID)
        for i, chunk in enumerate(juntos)
    )
