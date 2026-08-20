"""FastAPI · dos endpoints y una diferencia que conviene entender antes de elegir.

`POST /ask` es el de la fase 0 y **no genera nada**: recupera y devuelve el texto del artículo
con su `LegalRef`. Sigue ahí porque es útil —es el buscador desnudo— y porque su honestidad es
parte del proyecto: no hay generador, así que no hay nada que pueda alucinar, y decirlo importa
más que un número que luce bien por el motivo equivocado.

`POST /ask/stream` es el de la fase 3 y es el producto: el agente entero por SSE, con el
contrato de `docs/RULES.md` §2.2. Los tokens salen mientras el modelo escribe y las **citas
verificadas** salen al final; lo que hace segura esa concesión es que un marcador fuera de rango
corta en el token en que aparece, no al terminar.

**La frontera es única y es esta.** `ui/` habla con la API HTTP y nunca con el motor (ADR-019),
así que lo que no esté aquí no existe para el producto.

TDD prohibido en `api/` (`RULES` §3.1): la forma la fija FastAPI, no un test escrito antes. Lo
que lo sustituye es el snapshot de OpenAPI y el del contrato SSE, los dos en `tests/contract/`.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from citebound.agent.graph import Resultado
from citebound.agent.servir import Trozo, servir
from citebound.api.sse import Evento, Latencias, eventos, formatear
from citebound.db.conexion import dsn
from citebound.domain.citation import MAX_FUENTES, Fuente
from citebound.providers.chat import ChatError, generador_por_defecto
from citebound.providers.embeddings import EmbeddingError
from citebound.providers.reranker import reordenador_por_defecto
from citebound.retrieval import pipeline
from citebound.retrieval.vector import buscar, embedder_del_indice, indice_activo

__all__ = ["PROMPT_RESPONDER", "Cita", "Respuesta", "crear_app"]

PROMPT_RESPONDER = "responder"
PROMPT_RESPONDER_VERSION = 6
"""Viajan en el evento `done`. Sin ellos, dos trazas de dos versiones del prompt serían
indistinguibles y una regresión de calidad no se podría atribuir."""


class Cita(BaseModel):
    """A citation, identified by its stable legal reference and by nothing else (R1).

    The identifier a chunker mints is deliberately absent from this model and from the
    whole OpenAPI. It is not a style preference: anchoring evaluation on it would
    invalidate the golden set the moment the chunking strategy changes, which is exactly
    what phase 2 does on purpose. RULES R1 enforces it, and its checker runs in the gate.
    """

    legal_ref: str = Field(examples=["RD-1428/2003#art34.1"])
    texto: str
    titulo: str | None = None
    id_norma_version: str = Field(
        default="",
        description="Norma que dio su redacción vigente a este precepto",
    )
    distancia: float


class Respuesta(BaseModel):
    """Phase 0 answers with the retrieved text itself, and says so."""

    pregunta: str
    respuesta: str
    citas: list[Cita]
    index_version: str = Field(description="Destino físico resuelto, nunca el alias")
    physical_table: str
    generado_por: str = Field(
        default="retrieval-only",
        description="Fase 0: no hay generador. El texto es el del artículo recuperado",
    )


def crear_app() -> FastAPI:
    app = FastAPI(
        title="Citebound",
        version="0.1.0",
        summary="Tutor de normativa de circulación con cita cerrada",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"estado": "ok", "fase": "0"}

    @app.post("/ask", response_model=Respuesta)
    def ask(
        pregunta: Annotated[str, Query(min_length=3, max_length=500)],
        k: Annotated[int, Query(ge=1, le=20)] = 5,
    ) -> Respuesta:
        import psycopg

        try:
            with psycopg.connect(dsn()) as conn, conn.cursor() as cur:
                index_version, physical_table = indice_activo(cur)
                recuperados = buscar(cur, pregunta, embedder=embedder_del_indice(cur), k=k)
        except LookupError as err:
            raise HTTPException(status_code=503, detail=str(err)) from err
        except EmbeddingError as err:
            raise HTTPException(status_code=502, detail=str(err)) from err

        if not recuperados:
            raise HTTPException(status_code=404, detail="el índice no devolvió nada")

        return Respuesta(
            pregunta=pregunta,
            respuesta=recuperados[0].content,
            citas=[
                Cita(
                    legal_ref=str(r.ref),
                    texto=r.content,
                    titulo=r.titulo,
                    id_norma_version=r.id_norma_version,
                    distancia=r.distancia,
                )
                for r in recuperados
            ],
            index_version=index_version,
            physical_table=physical_table,
        )

    @app.post("/ask/stream")
    def ask_stream(
        pregunta: Annotated[str, Query(min_length=3, max_length=500)],
        k: Annotated[int, Query(ge=1, le=20)] = MAX_FUENTES,
    ) -> StreamingResponse:
        """El agente entero por SSE. El contrato está en `docs/RULES.md` §2.2.

        `media_type` es `text/event-stream` y `X-Accel-Buffering: no` porque un proxy que
        acumule la respuesta convertiría el streaming en una entrega al final — y con él, el
        `TTFT` medido en un número que no tiene nada que ver con lo que vive el usuario.
        """
        return StreamingResponse(
            _emitir(pregunta, k),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


def _emitir(pregunta: str, k: int) -> Iterator[str]:
    """Orquesta la petición y va midiendo. Las latencias se toman **aquí**, que es donde el
    usuario las siente, y no dentro del agente."""
    import time

    import psycopg

    arranque = time.monotonic()
    marcas: dict[str, float] = {}
    ttfs = ttft = 0.0

    try:
        with psycopg.connect(dsn()) as conn, conn.cursor() as cur:
            index_version, physical_table = indice_activo(cur)
            generador = generador_por_defecto()
            corriente = servir(
                pregunta,
                recuperador=lambda q: _fuentes(cur, q, k, marcas, arranque),
                generador=generador,
                plantilla=_plantilla_responder(),
            )
            primero = True
            resultado: Resultado | None = None
            for pieza in corriente:
                if isinstance(pieza, Trozo):
                    if primero:
                        ttft = (time.monotonic() - arranque) * 1000
                        primero = False
                    continue
                resultado = pieza
    except (LookupError, EmbeddingError, ChatError) as err:
        yield formatear(Evento.ERROR, {"detalle": str(err)})
        return

    ttfs = marcas.get("sources_ms", 0.0)
    if resultado is None:  # pragma: no cover - `servir` siempre termina con un Resultado
        yield formatear(Evento.ERROR, {"detalle": "el agente no produjo resultado"})
        return

    for evento, datos in eventos(
        resultado,
        latencias=Latencias(ttfs_ms=ttfs, ttft_ms=ttft, por_etapa=dict(marcas)),
        index_version=index_version,
        physical_table=physical_table,
        modelo=generador.model,
        prompt_id=PROMPT_RESPONDER,
        prompt_version=PROMPT_RESPONDER_VERSION,
    ):
        yield formatear(evento, datos)


def _fuentes(
    cur: Any, pregunta: str, k: int, marcas: dict[str, float], arranque: float
) -> list[Fuente]:
    """Recupera y anota cuándo estuvo listo. `sources` es lo primero que el usuario ve."""
    import time

    # **La tubería entera, no solo el canal vectorial.** Estaba llamando a `buscar`, que es
    # el vectorial desnudo: el endpoint servido se saltaba la fusión y el reordenador, es
    # decir, todo el trabajo de la fase 2. Lo que se sirve tiene que ser lo que se mide.
    recuperados = pipeline.recuperar(
        cur, pregunta, embedder=embedder_del_indice(cur), k=k, reordenador=reordenador_por_defecto()
    )
    marcas["sources_ms"] = (time.monotonic() - arranque) * 1000
    return [Fuente(ref=r.ref, texto=r.content) for r in recuperados]


def _plantilla_responder() -> str:
    """El cuerpo del prompt, sin frontmatter (R5)."""
    ruta = Path(__file__).resolve().parents[3] / "prompts" / f"{PROMPT_RESPONDER}.md"
    texto = ruta.read_text(encoding="utf-8")
    return texto.split("\n---\n", 1)[1].lstrip("\n") if texto.startswith("---\n") else texto


def openapi() -> dict[str, Any]:
    """The snapshot the contract test compares against."""
    return crear_app().openapi()
