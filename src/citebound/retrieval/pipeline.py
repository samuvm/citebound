"""El punto de reunión del recuperador híbrido.

Junta las dos patas —léxica y vectorial— con RRF y, opcionalmente, reordena el resultado.
`docs/PLAN.md` dice que este fichero lo escribe **un solo agente**: es donde los tres canales
dejan de ser independientes y donde un descuido se paga en las dos métricas a la vez.

**Qué se recupera y cuánto.** Cada canal trae `k_canal` candidatos (30 por defecto, el mismo
número que mide `G-RECALL30`) y la fusión recorta al final. Traer menos por canal ahorra
milisegundos y cuesta recall justo donde se mide; traer más no ayuda, porque lo que no está en
los 30 de ninguno de los dos no lo va a rescatar el reranker.

**El orden importa y es el del contrato:** recuperar ancho → fusionar → reordenar estrecho.
Reordenar antes de fusionar obligaría a pasar el reranker dos veces, que es la parte cara.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from citebound.providers.embeddings import Embedder
from citebound.retrieval import lexical, vector
from citebound.retrieval.fusion import fusionar
from citebound.retrieval.vector import Recuperado

__all__ = ["K_CANAL", "Reordenador", "recuperar"]

K_CANAL = 30
"""Candidatos por canal. Es el mismo 30 de `G-RECALL30` y no una casualidad: esa meta existe
para saber si un `G-RECALL5` bajo es culpa del recuperador o del reordenador, y solo lo
distingue si el recuperador trae exactamente lo que ella mide."""


class _Cursor(Protocol):
    def execute(self, query: str, params: Any = ..., /) -> Any: ...
    def fetchall(self) -> list[Any]: ...
    def fetchone(self) -> Any: ...


class Reordenador(Protocol):
    """El puerto del reranker. Vive aquí y no en `rerank` para que el pipeline no importe
    `sentence-transformers`: así se puede probar con una grabación y sin cargar un modelo."""

    def reordenar(self, pregunta: str, candidatos: Sequence[Recuperado]) -> list[Recuperado]: ...


def recuperar(
    cur: _Cursor,
    pregunta: str,
    *,
    embedder: Embedder,
    k: int = 5,
    k_canal: int = K_CANAL,
    materia: str | None = None,
    reordenador: Reordenador | None = None,
) -> tuple[Recuperado, ...]:
    """Los `k` mejores chunks para la pregunta, por acuerdo de los dos canales.

    Sin `reordenador` el resultado es el híbrido puro, que es lo que hay que medir primero:
    sin ese número no se puede decir cuánto aporta el reranker, y «mejoró» sin línea base es
    una opinión.

    Un canal que no devuelve nada **no es un error**. Una pregunta sin ningún término del
    corpus deja la lista léxica vacía y el vectorial sigue trayendo sus `k`; RRF ya trata la
    lista vacía como lo que es, una lista que no aporta.
    """
    lexicos = lexical.buscar(cur, pregunta, k=k_canal, materia=materia)
    vectoriales = vector.buscar(cur, pregunta, embedder=embedder, k=k_canal)

    # Se fusiona por `legal_ref`, que es la unidad de verdad (R1). Dos chunks distintos del
    # mismo artículo colapsan en uno, y eso es lo correcto: lo que se cita y se mide es el
    # artículo, así que contarlo dos veces inflaría su puntuación en la fusión.
    por_ref: dict[str, Recuperado] = {}
    for recuperado in (*vectoriales, *lexicos):
        por_ref.setdefault(str(recuperado.ref), recuperado)

    orden = fusionar(
        [[str(r.ref) for r in lexicos], [str(r.ref) for r in vectoriales]],
        tope=None if reordenador else k,
    )
    candidatos = [por_ref[ref] for ref in orden]
    if reordenador is None:
        return tuple(candidatos)
    return tuple(reordenador.reordenar(pregunta, candidatos)[:k])
