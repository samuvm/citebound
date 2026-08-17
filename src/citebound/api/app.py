"""FastAPI. Phase 0 has **no streaming and no agent** — that is phase 3.

`docs/RULES.md` §2.2 fixes the SSE contract for when it arrives (`sources` first, then
`token`, then verified `citations`), and none of it is faked here. What this exposes is
the honest skeleton: retrieve, and answer with the text of what was retrieved plus its
`LegalRef`. No generation at all, which is why `G-HALLUC` is trivially zero today —
and saying that out loud matters more than a number that looks good for the wrong reason.

TDD is prohibited in `api/` (RULES §3): the shape is fixed by FastAPI, not by a test
written first. What replaces it is the OpenAPI snapshot in `tests/contract/`.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from citebound.db.conexion import dsn
from citebound.providers.embeddings import EmbeddingError
from citebound.retrieval.vector import buscar, embedder_del_indice, indice_activo

__all__ = ["Cita", "Respuesta", "crear_app"]


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

    return app


def openapi() -> dict[str, Any]:
    """The snapshot the contract test compares against."""
    return crear_app().openapi()
