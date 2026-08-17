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


from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated, MutantDict
mutants_x_fusionar__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_fusionar__mutmut)
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


def x_fusionar__mutmut_orig(
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


def x_fusionar__mutmut_1(
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
    if k <= 1:
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


def x_fusionar__mutmut_2(
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
    if k < 2:
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


def x_fusionar__mutmut_3(
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
        raise ValueError(None)

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


def x_fusionar__mutmut_4(
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

    puntos: dict[str, float] = None
    for lista in listas:
        vistos: set[str] = set()
        for posicion, doc in enumerate(lista, start=1):
            if doc in vistos:
                continue
            vistos.add(doc)
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_5(
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
        vistos: set[str] = None
        for posicion, doc in enumerate(lista, start=1):
            if doc in vistos:
                continue
            vistos.add(doc)
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_6(
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
        for posicion, doc in enumerate(None, start=1):
            if doc in vistos:
                continue
            vistos.add(doc)
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_7(
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
        for posicion, doc in enumerate(lista, start=None):
            if doc in vistos:
                continue
            vistos.add(doc)
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_8(
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
        for posicion, doc in enumerate(start=1):
            if doc in vistos:
                continue
            vistos.add(doc)
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_9(
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
        for posicion, doc in enumerate(lista, ):
            if doc in vistos:
                continue
            vistos.add(doc)
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_10(
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
        for posicion, doc in enumerate(lista, start=2):
            if doc in vistos:
                continue
            vistos.add(doc)
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_11(
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
            if doc not in vistos:
                continue
            vistos.add(doc)
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_12(
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
                break
            vistos.add(doc)
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_13(
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
            vistos.add(None)
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_14(
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
            puntos[doc] = None

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_15(
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
            puntos[doc] = puntos.get(doc, 0.0) - 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_16(
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
            puntos[doc] = puntos.get(None, 0.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_17(
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
            puntos[doc] = puntos.get(doc, None) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_18(
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
            puntos[doc] = puntos.get(0.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_19(
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
            puntos[doc] = puntos.get(doc, ) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_20(
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
            puntos[doc] = puntos.get(doc, 1.0) + 1.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_21(
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
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 * (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_22(
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
            puntos[doc] = puntos.get(doc, 0.0) + 2.0 / (k + posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_23(
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
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 / (k - posicion)

    ordenada = sorted(puntos, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_24(
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

    ordenada = None
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_25(
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

    ordenada = sorted(None, key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_26(
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

    ordenada = sorted(puntos, key=None)
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_27(
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

    ordenada = sorted(key=lambda d: -puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_28(
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

    ordenada = sorted(puntos, )
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_29(
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

    ordenada = sorted(puntos, key=lambda d: None)
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_30(
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

    ordenada = sorted(puntos, key=lambda d: +puntos[d])
    return ordenada if tope is None else ordenada[:tope]


def x_fusionar__mutmut_31(
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
    return ordenada if tope is not None else ordenada[:tope]

mutants_x_fusionar__mutmut['_mutmut_orig'] = x_fusionar__mutmut_orig # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_1'] = x_fusionar__mutmut_1 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_2'] = x_fusionar__mutmut_2 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_3'] = x_fusionar__mutmut_3 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_4'] = x_fusionar__mutmut_4 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_5'] = x_fusionar__mutmut_5 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_6'] = x_fusionar__mutmut_6 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_7'] = x_fusionar__mutmut_7 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_8'] = x_fusionar__mutmut_8 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_9'] = x_fusionar__mutmut_9 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_10'] = x_fusionar__mutmut_10 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_11'] = x_fusionar__mutmut_11 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_12'] = x_fusionar__mutmut_12 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_13'] = x_fusionar__mutmut_13 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_14'] = x_fusionar__mutmut_14 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_15'] = x_fusionar__mutmut_15 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_16'] = x_fusionar__mutmut_16 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_17'] = x_fusionar__mutmut_17 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_18'] = x_fusionar__mutmut_18 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_19'] = x_fusionar__mutmut_19 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_20'] = x_fusionar__mutmut_20 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_21'] = x_fusionar__mutmut_21 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_22'] = x_fusionar__mutmut_22 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_23'] = x_fusionar__mutmut_23 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_24'] = x_fusionar__mutmut_24 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_25'] = x_fusionar__mutmut_25 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_26'] = x_fusionar__mutmut_26 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_27'] = x_fusionar__mutmut_27 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_28'] = x_fusionar__mutmut_28 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_29'] = x_fusionar__mutmut_29 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_30'] = x_fusionar__mutmut_30 # type: ignore # mutmut generated
mutants_x_fusionar__mutmut['x_fusionar__mutmut_31'] = x_fusionar__mutmut_31 # type: ignore # mutmut generated
