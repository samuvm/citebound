"""Reciprocal Rank Fusion · el punto de reunión del recuperador híbrido.

**Por qué RRF y no sumar puntuaciones.** Un `ts_rank_cd` de 0,08 y un coseno de 0,73 no son
comparables, y normalizarlos exige una calibración que cambia con el corpus y que hay que
rehacer cada vez que se reindexa. RRF solo mira **posiciones**: no hay nada que calibrar, y
por eso es lo que se usa cuando las dos patas del híbrido puntúan en escalas distintas.

    score(d) = Σ 1 / (k + rango(d, lista))

sobre las listas donde `d` aparece, con `k = 60` — el valor del paper original y el que fija
`docs/PLAN.md` para esta fase.

**Lo que hace `k`.** Amortigua la diferencia entre puestos: con `k` grande, estar el primero
pesa casi lo mismo que estar el quinto, y lo que manda es **aparecer en varias listas**. Ese
es el punto: el acuerdo entre dos recuperadores independientes es mejor señal que el primer
puesto de uno solo.

Módulo puro y sin I/O: es lo único de la fase 2 que se puede escribir y probar entero sin
corpus, sin modelo y sin base de datos.
"""

from __future__ import annotations

from collections.abc import Sequence

__all__ = ["K_RRF", "fusionar"]

K_RRF = 60
"""La constante del contrato. Con nombre y no incrustada en la fórmula: cambiarla mueve todas
las métricas de recall a la vez, así que tiene que verse en un diff."""


def fusionar(
    listas: Sequence[Sequence[str]], *, k: int = K_RRF, tope: int | None = None
) -> list[str]:
    """Funde varias listas ordenadas en una sola, por acuerdo de posiciones.

    Cada lista viene ordenada de mejor a peor. Un documento puede estar en una, en varias o
    en ninguna; los duplicados dentro de una misma lista se ignoran, porque contarlos dos
    veces inflaría su puntuación y, después, el recall.

    **El desempate es el orden de primera aparición**, y es deliberado: dos documentos con el
    mismo `score` tienen que salir siempre en el mismo orden o `G-EVAL-DET` fallaría por una
    razón que no tiene nada que ver con el modelo. `sorted` es estable, así que basta con
    construir el diccionario en orden de llegada.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, recibido {k}: con k=0 la fórmula pierde sentido")

    puntos: dict[str, float] = {}
    for lista in listas:
        vistos: set[str] = set()
        for posicion, doc in enumerate(lista, start=1):
            if doc in vistos:
                continue
            vistos.add(doc)
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]
