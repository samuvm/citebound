"""Embeddings behind a port, with a recorded double for tests.

TDD is **prohibited** here (RULES §3.1), and the reason is worth restating because it is
counter-intuitive: a test written before you have seen the provider's real response
encodes an *imagined* API, and the green test then certifies the imagination. It is the
exact mechanism by which a suite becomes an obstacle and gets switched off. The order is
inverted — **record first, write the test against the recording** — and the recording is
versioned in the repo, so from that moment the test is deterministic, free and exercises
the real shape.

The adapter is `OpenAICompatEmbedder` and **not** `OllamaEmbedder`, deliberately
(`docs/STACK.md` §2.1). Ollama, llama.cpp server, vLLM and LM Studio all expose
`/v1/embeddings`; one adapter covers the four and swapping runtime is an environment
variable. Ollama 0.32 is pivoting towards a consumer product, and this is cheap insurance.

The reranker does **not** live here and never will: there is no `/api/rerank`, in any
version. It runs in-process on MPS behind its own port (R8).
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = [
    "DIM_CONTRATO",
    "Embedder",
    "EmbeddingError",
    "OpenAICompatEmbedder",
    "RecordedEmbedder",
    "clave_de",
    "embedder_para",
    "embedder_por_defecto",
]

# `chunk_v1.embedding` is `vector(1024)` in the shared contract, and Postgres does not
# allow a variable dimension in a column. A model with another width is not a swap, it is
# a new table and a re-index (see the note in `chunks-ddl.sql`).
DIM_CONTRATO = 1024

_MODELO_POR_DEFECTO = "bge-m3"
_BASE_POR_DEFECTO = "http://localhost:11434/v1"


class EmbeddingError(RuntimeError):
    """The embeddings could not be obtained, or came back the wrong shape."""


@runtime_checkable
class Embedder(Protocol):
    """The port. `domain/` never sees an implementation of this (R6)."""

    @property
    def model(self) -> str: ...

    @property
    def dim(self) -> int: ...

    def embed(self, textos: Sequence[str]) -> tuple[tuple[float, ...], ...]: ...


def clave_de(model: str, texto: str) -> str:
    """The key a recording is stored under: a pure function of (model, text).

    `\\x00` separates the two so that no pair of (model, text) can be confused with
    another by concatenation.
    """
    return hashlib.sha256(f"{model}\x00{texto}".encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class OpenAICompatEmbedder:
    """Talks `/v1/embeddings` to whatever is serving it."""

    base_url: str = _BASE_POR_DEFECTO
    model: str = _MODELO_POR_DEFECTO
    dim: int = DIM_CONTRATO
    timeout_s: float = 120.0

    def embed(self, textos: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        if not textos:
            return ()
        import httpx

        try:
            respuesta = httpx.post(
                f"{self.base_url.rstrip('/')}/embeddings",
                json={"model": self.model, "input": list(textos)},
                timeout=self.timeout_s,
            )
            respuesta.raise_for_status()
            cuerpo = respuesta.json()
        except httpx.HTTPError as err:
            raise EmbeddingError(
                f"{self.model} en {self.base_url} no respondió: {err}. "
                "Ollama corre en el HOST, no en compose (R9): comprueba `ollama ps`."
            ) from err

        return _vectores(cuerpo, esperados=len(textos), dim=self.dim, model=self.model)


@dataclass(frozen=True, slots=True)
class RecordedEmbedder:
    """Replays a recording. Deterministic, free, and it never invents a vector.

    A miss raises instead of returning something plausible. A double that fabricates on a
    miss is worse than no double at all: the suite goes green over numbers nobody
    produced, and the first place it shows up is a recall figure that cannot be explained.
    """

    grabacion: Mapping[str, Sequence[float]]
    model: str = _MODELO_POR_DEFECTO
    dim: int = DIM_CONTRATO

    def embed(self, textos: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        salida: list[tuple[float, ...]] = []
        for texto in textos:
            clave = clave_de(self.model, texto)
            if clave not in self.grabacion:
                raise EmbeddingError(
                    f"no hay grabación para {clave[:12]}… ({self.model}, {texto[:50]!r}). "
                    "Regrábala con `python scripts/record_embeddings.py`; "
                    "inventar el vector aquí haría verde una suite sobre números "
                    "que nadie ha producido."
                )
            vector = tuple(float(x) for x in self.grabacion[clave])
            if len(vector) != self.dim:
                raise EmbeddingError(
                    f"la grabación de {clave[:12]}… trae {len(vector)} dimensiones "
                    f"y el contrato fija {self.dim}"
                )
            salida.append(vector)
        return tuple(salida)

    @classmethod
    def desde_fichero(cls, ruta: Path) -> RecordedEmbedder:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        return cls(
            grabacion=datos["vectores"],
            model=datos["model"],
            dim=datos["dim"],
        )


def embedder_por_defecto() -> Embedder:
    """The real one, configured from the environment.

    Read here and nowhere deeper: `domain/` may not touch `os.environ` (R6), and the
    whole point of the port is that swapping runtime is a variable rather than an edit.

    **Es el embedder de quien CONSTRUYE el índice**, es decir la ingesta. Quien consulta usa
    `retrieval.vector.embedder_del_indice`, que lee el modelo de la base: si la consulta se
    vectorizara con un modelo y el índice con otro, la búsqueda no fallaría — devolvería 30
    filas mal ordenadas y en silencio.
    """
    return embedder_para(model=os.environ.get("CITEBOUND_EMBEDDING_MODEL", _MODELO_POR_DEFECTO))


def embedder_para(*, model: str, dim: int = DIM_CONTRATO) -> Embedder:
    """El mismo transporte, con el modelo que se le diga.

    El `base_url` se resuelve aquí y en un solo sitio: dos lecturas de `OPENAI_BASE_URL` son
    dos sitios donde apuntar a servidores distintos sin enterarse.
    """
    return OpenAICompatEmbedder(
        base_url=os.environ.get("OPENAI_BASE_URL", _BASE_POR_DEFECTO), model=model, dim=dim
    )


def _vectores(
    cuerpo: object, *, esperados: int, dim: int, model: str
) -> tuple[tuple[float, ...], ...]:
    """Validate the response instead of trusting it.

    A provider that returns the wrong number of vectors, or the wrong width, would put
    embeddings against the wrong chunks — and nothing downstream could tell, because the
    index would be perfectly well formed and simply wrong.
    """
    if not isinstance(cuerpo, dict) or "data" not in cuerpo:
        raise EmbeddingError(f"respuesta sin `data` de {model}: {str(cuerpo)[:120]}")
    datos = cuerpo["data"]
    if not isinstance(datos, list) or len(datos) != esperados:
        raise EmbeddingError(
            f"{model} devolvió {len(datos) if isinstance(datos, list) else '?'} vectores "
            f"para {esperados} textos"
        )
    vectores: list[tuple[float, ...]] = []
    for i, item in enumerate(datos):
        vector = item.get("embedding") if isinstance(item, dict) else None
        if not isinstance(vector, list):
            raise EmbeddingError(f"el vector {i} de {model} no es una lista")
        if len(vector) != dim:
            raise EmbeddingError(
                f"{model} devolvió {len(vector)} dimensiones y el contrato fija {dim}. "
                "Cambiar de ancho no es un cambio de modelo: es una tabla nueva y "
                "reindexar (chunks-ddl.sql)."
            )
        vectores.append(tuple(float(x) for x in vector))
    return tuple(vectores)
