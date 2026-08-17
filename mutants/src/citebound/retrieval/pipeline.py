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
"""Candidatos que pide **cada canal**, antes de fusionar y de colapsar por artículo.

**Depende del troceado, y no es intuitivo.** Medido el 2026-08-17 sobre los mismos 216 casos:

| troceado | 30 por canal | 60 por canal |
|---|---:|---:|
| `articulo-v1` (el que se sirve) | **0,977** | 0,949 |
| `apartado-v1` | 0,958 | **0,968** |

Con artículos, 30 chunks **son** 30 artículos y pedir más solo mete ruido léxico en la
fusión. Con apartados dejan de serlo —varios del mismo artículo ocupan plaza sin añadir
cobertura— y hace falta pedir más para llenar el top-30 de artículos distintos.

Se subió a 60 al medir `apartado-v1` y **se quedó puesto al revertir el índice**: `G-RECALL30`
cayó de 0,977 a 0,949 y el número parecía del reordenador. Un ajuste de un experimento que
sobrevive al experimento es una regresión con coartada."""


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
        tope=None,
    )
    candidatos = _uno_por_articulo([por_ref[ref] for ref in orden])
    if reordenador is None:
        return tuple(candidatos[:k])
    return tuple(reordenador.reordenar(pregunta, candidatos)[:k])


def _uno_por_articulo(candidatos: list[Recuperado]) -> list[Recuperado]:
    """Deja el mejor colocado de cada artículo y descarta sus hermanos.

    **Solo hace algo con troceado fino**, y ahí hace mucho. Con `apartado-v1`, `art34.1`,
    `art34.2` y `art34.3` gastan tres plazas de las 30 sin añadir un artículo nuevo, y como
    lo que se mide y se cita es el artículo (R1), esas dos de más son plazas tiradas. Medido
    el 2026-08-17 sobre los 216 casos: sin colapsar `recall@30` cae a 0,940 y colapsando
    sube a 0,968.

    Se conserva el apartado del que sobrevive, no se recorta: la referencia más precisa que
    el recuperador ha sabido encontrar es información, y tirarla aquí obligaría al generador
    a redescubrirla.
    """
    salida: list[Recuperado] = []
    vistos: set[str] = set()
    for candidato in candidatos:
        articulo = f"{candidato.ref.norma}#art{candidato.ref.articulo}"
        if articulo not in vistos:
            vistos.add(articulo)
            salida.append(candidato)
    return salida
