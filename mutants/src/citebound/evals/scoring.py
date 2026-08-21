"""Las métricas del contrato, calculadas como el contrato las define y no de otra manera.

`docs/CONTRACTS/retrieval-metrics.md` §2 es la única fuente de estas definiciones, y existe
porque «¿el artículo citado es el del golden set? Exacto, sí/no» **no resolvía cuatro casos
que aparecen constantemente**. Los cuatro están implementados aquí y cada uno tiene su test:
varias citas, granularidad de apartado, dos artículos que sostienen la respuesta, y
abstenciones fuera del denominador.

Dos decisiones que no son obvias y que este módulo toma explícitamente:

**Cero de cero no es 1,00.** Una métrica sin casos devuelve `valor=None`, no un número. Un
informe con un 1,00 inventado es peor que uno que dice «no medible», porque el primero se
publica sin que nadie pregunte.

**Los datos descuadrados se rechazan en voz alta.** Una predicción para un caso que no
existe, un caso sin predicción o dos predicciones para el mismo caso producen un número
perfectamente plausible sobre un conjunto que no es el golden set. Eso no se puede detectar
mirando el resultado, así que se detecta antes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from citebound.domain.legalref import LegalRef, MatchLevel, matches

from .schema import CasoGolden, Tipo

__all__ = [
    "Metrica",
    "Prediccion",
    "abstencion_incorrecta",
    "abstencion_indebida",
    "alucinacion",
    "cita_pertenece",
    "cobertura",
    "precision_cita",
    "precision_cita_articulo",
    "recall_at_k",
]


from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated, MutantDict


@dataclass(frozen=True, slots=True)
class Metrica:
    """Un valor con su denominador, siempre juntos.

    `n` no es decoración: `G-HALLUC = 0` sobre 15 referencias y sobre 2.000 son la misma
    cifra y afirmaciones muy distintas, y por eso `G-HALLUC-AMPLIO` existe. Un valor sin su
    `n` no se puede publicar.
    """

    id: str
    valor: float | None
    n: int


@dataclass(frozen=True, slots=True)
class Prediccion:
    """Lo que el sistema respondió a un caso."""

    caso_id: str
    refs: tuple[LegalRef, ...] = ()
    abstenida: bool = False

    def __post_init__(self) -> None:
        if self.abstenida and self.refs:
            raise ValueError(
                f"{self.caso_id}: abstenerse y citar a la vez no es un estado del sistema. "
                "Contarlo como cualquiera de los dos falsea las dos métricas."
            )
mutants_x_cita_pertenece__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_cita_pertenece__mutmut)
def cita_pertenece(cita: LegalRef, relevantes: Sequence[LegalRef]) -> bool:
    """¿La cita está «en `R(q)`» con la granularidad que el caso exige?

    **El nivel exigido no es un campo del golden set: se deriva de la propia referencia.**
    Si el caso dice `art34.1`, la cita tiene que llegar al apartado y `art34` es fallo. Si el
    caso dice `art34`, citar `art34.1` es correcto — ser más preciso que lo pedido no puede
    penalizar. La asimetría va en un solo sentido y es la de `MatchLevel`.
    """
    return any(matches(cita, r, r.level) for r in relevantes)


def x_cita_pertenece__mutmut_orig(cita: LegalRef, relevantes: Sequence[LegalRef]) -> bool:
    """¿La cita está «en `R(q)`» con la granularidad que el caso exige?

    **El nivel exigido no es un campo del golden set: se deriva de la propia referencia.**
    Si el caso dice `art34.1`, la cita tiene que llegar al apartado y `art34` es fallo. Si el
    caso dice `art34`, citar `art34.1` es correcto — ser más preciso que lo pedido no puede
    penalizar. La asimetría va en un solo sentido y es la de `MatchLevel`.
    """
    return any(matches(cita, r, r.level) for r in relevantes)


def x_cita_pertenece__mutmut_1(cita: LegalRef, relevantes: Sequence[LegalRef]) -> bool:
    """¿La cita está «en `R(q)`» con la granularidad que el caso exige?

    **El nivel exigido no es un campo del golden set: se deriva de la propia referencia.**
    Si el caso dice `art34.1`, la cita tiene que llegar al apartado y `art34` es fallo. Si el
    caso dice `art34`, citar `art34.1` es correcto — ser más preciso que lo pedido no puede
    penalizar. La asimetría va en un solo sentido y es la de `MatchLevel`.
    """
    return any(None)


def x_cita_pertenece__mutmut_2(cita: LegalRef, relevantes: Sequence[LegalRef]) -> bool:
    """¿La cita está «en `R(q)`» con la granularidad que el caso exige?

    **El nivel exigido no es un campo del golden set: se deriva de la propia referencia.**
    Si el caso dice `art34.1`, la cita tiene que llegar al apartado y `art34` es fallo. Si el
    caso dice `art34`, citar `art34.1` es correcto — ser más preciso que lo pedido no puede
    penalizar. La asimetría va en un solo sentido y es la de `MatchLevel`.
    """
    return any(matches(None, r, r.level) for r in relevantes)


def x_cita_pertenece__mutmut_3(cita: LegalRef, relevantes: Sequence[LegalRef]) -> bool:
    """¿La cita está «en `R(q)`» con la granularidad que el caso exige?

    **El nivel exigido no es un campo del golden set: se deriva de la propia referencia.**
    Si el caso dice `art34.1`, la cita tiene que llegar al apartado y `art34` es fallo. Si el
    caso dice `art34`, citar `art34.1` es correcto — ser más preciso que lo pedido no puede
    penalizar. La asimetría va en un solo sentido y es la de `MatchLevel`.
    """
    return any(matches(cita, None, r.level) for r in relevantes)


def x_cita_pertenece__mutmut_4(cita: LegalRef, relevantes: Sequence[LegalRef]) -> bool:
    """¿La cita está «en `R(q)`» con la granularidad que el caso exige?

    **El nivel exigido no es un campo del golden set: se deriva de la propia referencia.**
    Si el caso dice `art34.1`, la cita tiene que llegar al apartado y `art34` es fallo. Si el
    caso dice `art34`, citar `art34.1` es correcto — ser más preciso que lo pedido no puede
    penalizar. La asimetría va en un solo sentido y es la de `MatchLevel`.
    """
    return any(matches(cita, r, None) for r in relevantes)


def x_cita_pertenece__mutmut_5(cita: LegalRef, relevantes: Sequence[LegalRef]) -> bool:
    """¿La cita está «en `R(q)`» con la granularidad que el caso exige?

    **El nivel exigido no es un campo del golden set: se deriva de la propia referencia.**
    Si el caso dice `art34.1`, la cita tiene que llegar al apartado y `art34` es fallo. Si el
    caso dice `art34`, citar `art34.1` es correcto — ser más preciso que lo pedido no puede
    penalizar. La asimetría va en un solo sentido y es la de `MatchLevel`.
    """
    return any(matches(r, r.level) for r in relevantes)


def x_cita_pertenece__mutmut_6(cita: LegalRef, relevantes: Sequence[LegalRef]) -> bool:
    """¿La cita está «en `R(q)`» con la granularidad que el caso exige?

    **El nivel exigido no es un campo del golden set: se deriva de la propia referencia.**
    Si el caso dice `art34.1`, la cita tiene que llegar al apartado y `art34` es fallo. Si el
    caso dice `art34`, citar `art34.1` es correcto — ser más preciso que lo pedido no puede
    penalizar. La asimetría va en un solo sentido y es la de `MatchLevel`.
    """
    return any(matches(cita, r.level) for r in relevantes)


def x_cita_pertenece__mutmut_7(cita: LegalRef, relevantes: Sequence[LegalRef]) -> bool:
    """¿La cita está «en `R(q)`» con la granularidad que el caso exige?

    **El nivel exigido no es un campo del golden set: se deriva de la propia referencia.**
    Si el caso dice `art34.1`, la cita tiene que llegar al apartado y `art34` es fallo. Si el
    caso dice `art34`, citar `art34.1` es correcto — ser más preciso que lo pedido no puede
    penalizar. La asimetría va en un solo sentido y es la de `MatchLevel`.
    """
    return any(matches(cita, r, ) for r in relevantes)

mutants_x_cita_pertenece__mutmut['_mutmut_orig'] = x_cita_pertenece__mutmut_orig # type: ignore # mutmut generated
mutants_x_cita_pertenece__mutmut['x_cita_pertenece__mutmut_1'] = x_cita_pertenece__mutmut_1 # type: ignore # mutmut generated
mutants_x_cita_pertenece__mutmut['x_cita_pertenece__mutmut_2'] = x_cita_pertenece__mutmut_2 # type: ignore # mutmut generated
mutants_x_cita_pertenece__mutmut['x_cita_pertenece__mutmut_3'] = x_cita_pertenece__mutmut_3 # type: ignore # mutmut generated
mutants_x_cita_pertenece__mutmut['x_cita_pertenece__mutmut_4'] = x_cita_pertenece__mutmut_4 # type: ignore # mutmut generated
mutants_x_cita_pertenece__mutmut['x_cita_pertenece__mutmut_5'] = x_cita_pertenece__mutmut_5 # type: ignore # mutmut generated
mutants_x_cita_pertenece__mutmut['x_cita_pertenece__mutmut_6'] = x_cita_pertenece__mutmut_6 # type: ignore # mutmut generated
mutants_x_cita_pertenece__mutmut['x_cita_pertenece__mutmut_7'] = x_cita_pertenece__mutmut_7 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_precision_cita__mutmut)
def precision_cita(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_orig(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_1(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = None
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_2(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(None, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_3(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, None)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_4(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_5(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, )
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_6(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = None
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_7(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_8(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_9(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica(None, None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_10(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, None)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_11(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica(None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_12(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_13(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, )
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_14(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("XXG-CITA-PRECISIONXX", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_15(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("g-cita-precision", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_16(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 1)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_17(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = None
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_18(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        None
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_19(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        2
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_20(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs or all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_21(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(None)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_22(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(None, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_23(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, None) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_24(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_25(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, ) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_26(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica(None, aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_27(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", None, len(respondidos))


def x_precision_cita__mutmut_28(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), None)


def x_precision_cita__mutmut_29(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica(aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_30(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", len(respondidos))


def x_precision_cita__mutmut_31(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), )


def x_precision_cita__mutmut_32(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("XXG-CITA-PRECISIONXX", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_33(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("g-cita-precision", aciertos / len(respondidos), len(respondidos))


def x_precision_cita__mutmut_34(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`.

    **Todo o nada por caso.** Una respuesta que cita el artículo bueno y además uno que no
    viene a cuento es una respuesta en la que no se puede confiar; promediar dentro del caso
    lo escondería detrás de un 0,5 que suena aceptable.

    Pareja atómica con `cobertura` (RULES R16): el gate las evalúa como **una sola
    condición**, porque sin la pareja la forma óptima de subir esta métrica es abstenerse
    siempre.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs and all(cita_pertenece(r, caso.refs) for r in prediccion.refs)
    )
    return Metrica("G-CITA-PRECISION", aciertos * len(respondidos), len(respondidos))

mutants_x_precision_cita__mutmut['_mutmut_orig'] = x_precision_cita__mutmut_orig # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_1'] = x_precision_cita__mutmut_1 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_2'] = x_precision_cita__mutmut_2 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_3'] = x_precision_cita__mutmut_3 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_4'] = x_precision_cita__mutmut_4 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_5'] = x_precision_cita__mutmut_5 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_6'] = x_precision_cita__mutmut_6 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_7'] = x_precision_cita__mutmut_7 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_8'] = x_precision_cita__mutmut_8 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_9'] = x_precision_cita__mutmut_9 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_10'] = x_precision_cita__mutmut_10 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_11'] = x_precision_cita__mutmut_11 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_12'] = x_precision_cita__mutmut_12 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_13'] = x_precision_cita__mutmut_13 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_14'] = x_precision_cita__mutmut_14 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_15'] = x_precision_cita__mutmut_15 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_16'] = x_precision_cita__mutmut_16 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_17'] = x_precision_cita__mutmut_17 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_18'] = x_precision_cita__mutmut_18 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_19'] = x_precision_cita__mutmut_19 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_20'] = x_precision_cita__mutmut_20 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_21'] = x_precision_cita__mutmut_21 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_22'] = x_precision_cita__mutmut_22 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_23'] = x_precision_cita__mutmut_23 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_24'] = x_precision_cita__mutmut_24 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_25'] = x_precision_cita__mutmut_25 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_26'] = x_precision_cita__mutmut_26 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_27'] = x_precision_cita__mutmut_27 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_28'] = x_precision_cita__mutmut_28 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_29'] = x_precision_cita__mutmut_29 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_30'] = x_precision_cita__mutmut_30 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_31'] = x_precision_cita__mutmut_31 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_32'] = x_precision_cita__mutmut_32 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_33'] = x_precision_cita__mutmut_33 # type: ignore # mutmut generated
mutants_x_precision_cita__mutmut['x_precision_cita__mutmut_34'] = x_precision_cita__mutmut_34 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_recall_at_k__mutmut)
def recall_at_k(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_orig(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_1(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k <= 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_2(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 2:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_3(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(None)
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_4(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = None
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_5(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_6(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(None, None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_7(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, None)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_8(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_9(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_10(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, )

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_11(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 1)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_12(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = None
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_13(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 1.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_14(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_15(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(None)
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_16(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = None
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_17(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(None)[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_18(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = None
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_19(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(None)
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_20(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(2 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_21(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(None))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_22(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(None, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_23(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, None, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_24(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, None) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_25(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_26(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_27(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, ) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_28(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total = encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_29(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total -= encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_30(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas * len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_31(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(None, total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_32(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", None, len(con_respuesta))


def x_recall_at_k__mutmut_33(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), None)


def x_recall_at_k__mutmut_34(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(total / len(con_respuesta), len(con_respuesta))


def x_recall_at_k__mutmut_35(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", len(con_respuesta))


def x_recall_at_k__mutmut_36(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total / len(con_respuesta), )


def x_recall_at_k__mutmut_37(
    casos: Sequence[CasoGolden], recuperado: Mapping[str, Sequence[LegalRef]], k: int
) -> Metrica:
    """`|R(q) ∩ P_k(q)| / |R(q)|`, promediado sobre las preguntas con `R(q)` no vacío.

    Los casos negativos quedan **fuera del denominador** (contrato §2): se usan solo para
    medir abstención. Y `|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al
    mismo artículo — es correcto y deliberado, importa si la referencia está y no cuántas
    veces.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k}")
    con_respuesta = [c for c in casos if c.refs]
    if not con_respuesta:
        return Metrica(f"G-RECALL{k}", None, 0)

    total = 0.0
    for caso in con_respuesta:
        if caso.id not in recuperado:
            raise ValueError(f"{caso.id}: sin lista de recuperados y tiene R(q) no vacío")
        primeros_k = list(recuperado[caso.id])[:k]
        encontradas = sum(1 for r in caso.refs if any(matches(p, r, r.level) for p in primeros_k))
        total += encontradas / len(caso.refs)
    return Metrica(f"G-RECALL{k}", total * len(con_respuesta), len(con_respuesta))

mutants_x_recall_at_k__mutmut['_mutmut_orig'] = x_recall_at_k__mutmut_orig # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_1'] = x_recall_at_k__mutmut_1 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_2'] = x_recall_at_k__mutmut_2 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_3'] = x_recall_at_k__mutmut_3 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_4'] = x_recall_at_k__mutmut_4 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_5'] = x_recall_at_k__mutmut_5 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_6'] = x_recall_at_k__mutmut_6 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_7'] = x_recall_at_k__mutmut_7 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_8'] = x_recall_at_k__mutmut_8 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_9'] = x_recall_at_k__mutmut_9 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_10'] = x_recall_at_k__mutmut_10 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_11'] = x_recall_at_k__mutmut_11 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_12'] = x_recall_at_k__mutmut_12 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_13'] = x_recall_at_k__mutmut_13 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_14'] = x_recall_at_k__mutmut_14 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_15'] = x_recall_at_k__mutmut_15 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_16'] = x_recall_at_k__mutmut_16 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_17'] = x_recall_at_k__mutmut_17 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_18'] = x_recall_at_k__mutmut_18 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_19'] = x_recall_at_k__mutmut_19 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_20'] = x_recall_at_k__mutmut_20 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_21'] = x_recall_at_k__mutmut_21 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_22'] = x_recall_at_k__mutmut_22 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_23'] = x_recall_at_k__mutmut_23 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_24'] = x_recall_at_k__mutmut_24 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_25'] = x_recall_at_k__mutmut_25 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_26'] = x_recall_at_k__mutmut_26 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_27'] = x_recall_at_k__mutmut_27 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_28'] = x_recall_at_k__mutmut_28 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_29'] = x_recall_at_k__mutmut_29 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_30'] = x_recall_at_k__mutmut_30 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_31'] = x_recall_at_k__mutmut_31 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_32'] = x_recall_at_k__mutmut_32 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_33'] = x_recall_at_k__mutmut_33 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_34'] = x_recall_at_k__mutmut_34 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_35'] = x_recall_at_k__mutmut_35 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_36'] = x_recall_at_k__mutmut_36 # type: ignore # mutmut generated
mutants_x_recall_at_k__mutmut['x_recall_at_k__mutmut_37'] = x_recall_at_k__mutmut_37 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_alucinacion__mutmut)
def alucinacion(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_orig(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_1(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = None
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_2(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(None, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_3(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, None) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_4(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_5(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, ) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_6(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_7(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_8(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica(None, None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_9(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, None)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_10(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica(None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_11(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_12(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, )
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_13(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("XXG-HALLUCXX", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_14(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("g-halluc", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_15(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 1)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_16(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = None
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_17(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(None)
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_18(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(2 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_19(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(None))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_20(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(None) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_21(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_22(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica(None, inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_23(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", None, len(respondidos))


def x_alucinacion__mutmut_24(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), None)


def x_alucinacion__mutmut_25(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica(inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_26(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", len(respondidos))


def x_alucinacion__mutmut_27(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas / len(respondidos), )


def x_alucinacion__mutmut_28(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("XXG-HALLUCXX", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_29(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("g-halluc", inventadas / len(respondidos), len(respondidos))


def x_alucinacion__mutmut_30(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion], indice: frozenset[str]
) -> Metrica:
    """`casos_donde_alguna_cita_no_existe_en_el_corpus / casos_respondidos`.

    «No existe» es pertenencia al conjunto de refs del índice activo: determinista, barata y
    sin nada que un modelo pueda discutir. **Objetivo 0,00 y sin intervalo de confianza**;
    aquí no hay umbral estadístico que negociar.

    Ojo a la distinción que hace falta publicar: citar el artículo 35 cuando tocaba el 34
    **no es una alucinación** —el 35 existe— pero sí es un fallo de precisión de cita.
    Confundirlas haría que `G-HALLUC` absorbiera fallos que no le tocan y dejara de
    significar lo que dice.
    """
    respondidos = [p for _, p in _emparejar(casos, pred) if not p.abstenida]
    if not respondidos:
        return Metrica("G-HALLUC", None, 0)
    inventadas = sum(1 for p in respondidos if any(str(r) not in indice for r in p.refs))
    return Metrica("G-HALLUC", inventadas * len(respondidos), len(respondidos))

mutants_x_alucinacion__mutmut['_mutmut_orig'] = x_alucinacion__mutmut_orig # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_1'] = x_alucinacion__mutmut_1 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_2'] = x_alucinacion__mutmut_2 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_3'] = x_alucinacion__mutmut_3 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_4'] = x_alucinacion__mutmut_4 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_5'] = x_alucinacion__mutmut_5 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_6'] = x_alucinacion__mutmut_6 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_7'] = x_alucinacion__mutmut_7 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_8'] = x_alucinacion__mutmut_8 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_9'] = x_alucinacion__mutmut_9 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_10'] = x_alucinacion__mutmut_10 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_11'] = x_alucinacion__mutmut_11 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_12'] = x_alucinacion__mutmut_12 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_13'] = x_alucinacion__mutmut_13 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_14'] = x_alucinacion__mutmut_14 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_15'] = x_alucinacion__mutmut_15 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_16'] = x_alucinacion__mutmut_16 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_17'] = x_alucinacion__mutmut_17 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_18'] = x_alucinacion__mutmut_18 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_19'] = x_alucinacion__mutmut_19 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_20'] = x_alucinacion__mutmut_20 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_21'] = x_alucinacion__mutmut_21 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_22'] = x_alucinacion__mutmut_22 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_23'] = x_alucinacion__mutmut_23 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_24'] = x_alucinacion__mutmut_24 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_25'] = x_alucinacion__mutmut_25 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_26'] = x_alucinacion__mutmut_26 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_27'] = x_alucinacion__mutmut_27 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_28'] = x_alucinacion__mutmut_28 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_29'] = x_alucinacion__mutmut_29 # type: ignore # mutmut generated
mutants_x_alucinacion__mutmut['x_alucinacion__mutmut_30'] = x_alucinacion__mutmut_30 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_cobertura__mutmut)
def cobertura(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_orig(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_1(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = None
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_2(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(None, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_3(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, None) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_4(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_5(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, ) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_6(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_7(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica(None, None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_8(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, None)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_9(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica(None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_10(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_11(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, )
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_12(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("XXG-COBERTURAXX", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_13(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("g-cobertura", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_14(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 1)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_15(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = None
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_16(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(None)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_17(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(2 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_18(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_19(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica(None, respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_20(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", None, len(con_respuesta))


def x_cobertura__mutmut_21(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), None)


def x_cobertura__mutmut_22(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica(respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_23(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", len(con_respuesta))


def x_cobertura__mutmut_24(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos / len(con_respuesta), )


def x_cobertura__mutmut_25(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("XXG-COBERTURAXX", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_26(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("g-cobertura", respondidos / len(con_respuesta), len(con_respuesta))


def x_cobertura__mutmut_27(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos con respuesta en el corpus que el sistema **sí** respondió.

    Pareja atómica con `precision_cita`. El test que lo justifica está escrito:
    abstenerse siempre deja la precisión indefinida y esta métrica en cero, y quien mire
    solo la primera verá un sistema perfecto que no responde nada.
    """
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-COBERTURA", None, 0)
    respondidos = sum(1 for _, p in con_respuesta if not p.abstenida)
    return Metrica("G-COBERTURA", respondidos * len(con_respuesta), len(con_respuesta))

mutants_x_cobertura__mutmut['_mutmut_orig'] = x_cobertura__mutmut_orig # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_1'] = x_cobertura__mutmut_1 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_2'] = x_cobertura__mutmut_2 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_3'] = x_cobertura__mutmut_3 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_4'] = x_cobertura__mutmut_4 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_5'] = x_cobertura__mutmut_5 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_6'] = x_cobertura__mutmut_6 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_7'] = x_cobertura__mutmut_7 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_8'] = x_cobertura__mutmut_8 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_9'] = x_cobertura__mutmut_9 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_10'] = x_cobertura__mutmut_10 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_11'] = x_cobertura__mutmut_11 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_12'] = x_cobertura__mutmut_12 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_13'] = x_cobertura__mutmut_13 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_14'] = x_cobertura__mutmut_14 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_15'] = x_cobertura__mutmut_15 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_16'] = x_cobertura__mutmut_16 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_17'] = x_cobertura__mutmut_17 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_18'] = x_cobertura__mutmut_18 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_19'] = x_cobertura__mutmut_19 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_20'] = x_cobertura__mutmut_20 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_21'] = x_cobertura__mutmut_21 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_22'] = x_cobertura__mutmut_22 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_23'] = x_cobertura__mutmut_23 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_24'] = x_cobertura__mutmut_24 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_25'] = x_cobertura__mutmut_25 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_26'] = x_cobertura__mutmut_26 # type: ignore # mutmut generated
mutants_x_cobertura__mutmut['x_cobertura__mutmut_27'] = x_cobertura__mutmut_27 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_abstencion_incorrecta__mutmut)
def abstencion_incorrecta(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_orig(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_1(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = None
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_2(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(None, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_3(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, None) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_4(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_5(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, ) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_6(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_7(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica(None, None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_8(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, None)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_9(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica(None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_10(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_11(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, )
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_12(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("XXG-ABST-FPXX", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_13(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("g-abst-fp", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_14(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 1)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_15(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = None
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_16(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(None)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_17(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(2 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_18(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica(None, callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_19(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", None, len(con_respuesta))


def x_abstencion_incorrecta__mutmut_20(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), None)


def x_abstencion_incorrecta__mutmut_21(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica(callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_22(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", len(con_respuesta))


def x_abstencion_incorrecta__mutmut_23(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), )


def x_abstencion_incorrecta__mutmut_24(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("XXG-ABST-FPXX", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_25(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("g-abst-fp", callados / len(con_respuesta), len(con_respuesta))


def x_abstencion_incorrecta__mutmut_26(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados * len(con_respuesta), len(con_respuesta))

mutants_x_abstencion_incorrecta__mutmut['_mutmut_orig'] = x_abstencion_incorrecta__mutmut_orig # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_1'] = x_abstencion_incorrecta__mutmut_1 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_2'] = x_abstencion_incorrecta__mutmut_2 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_3'] = x_abstencion_incorrecta__mutmut_3 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_4'] = x_abstencion_incorrecta__mutmut_4 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_5'] = x_abstencion_incorrecta__mutmut_5 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_6'] = x_abstencion_incorrecta__mutmut_6 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_7'] = x_abstencion_incorrecta__mutmut_7 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_8'] = x_abstencion_incorrecta__mutmut_8 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_9'] = x_abstencion_incorrecta__mutmut_9 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_10'] = x_abstencion_incorrecta__mutmut_10 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_11'] = x_abstencion_incorrecta__mutmut_11 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_12'] = x_abstencion_incorrecta__mutmut_12 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_13'] = x_abstencion_incorrecta__mutmut_13 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_14'] = x_abstencion_incorrecta__mutmut_14 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_15'] = x_abstencion_incorrecta__mutmut_15 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_16'] = x_abstencion_incorrecta__mutmut_16 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_17'] = x_abstencion_incorrecta__mutmut_17 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_18'] = x_abstencion_incorrecta__mutmut_18 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_19'] = x_abstencion_incorrecta__mutmut_19 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_20'] = x_abstencion_incorrecta__mutmut_20 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_21'] = x_abstencion_incorrecta__mutmut_21 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_22'] = x_abstencion_incorrecta__mutmut_22 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_23'] = x_abstencion_incorrecta__mutmut_23 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_24'] = x_abstencion_incorrecta__mutmut_24 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_25'] = x_abstencion_incorrecta__mutmut_25 # type: ignore # mutmut generated
mutants_x_abstencion_incorrecta__mutmut['x_abstencion_incorrecta__mutmut_26'] = x_abstencion_incorrecta__mutmut_26 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_abstencion_indebida__mutmut)
def abstencion_indebida(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_orig(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_1(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = None
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_2(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(None, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_3(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, None) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_4(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_5(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, ) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_6(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is not Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_7(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_8(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica(None, None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_9(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, None)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_10(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica(None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_11(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_12(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, )
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_13(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("XXG-ABST-FNXX", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_14(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("g-abst-fn", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_15(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 1)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_16(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = None
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_17(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(None)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_18(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(2 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_19(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_20(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica(None, respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_21(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", None, len(negativos))


def x_abstencion_indebida__mutmut_22(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), None)


def x_abstencion_indebida__mutmut_23(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica(respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_24(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", len(negativos))


def x_abstencion_indebida__mutmut_25(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos / len(negativos), )


def x_abstencion_indebida__mutmut_26(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("XXG-ABST-FNXX", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_27(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("g-abst-fn", respondidos / len(negativos), len(negativos))


def x_abstencion_indebida__mutmut_28(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """Fracción de los casos **negativos** en los que el sistema respondió igualmente.

    Sin este dual, **no abstenerse nunca** sería la estrategia óptima, exactamente igual que
    con la precisión sola lo sería abstenerse siempre. Por eso el contrato mide la abstención
    en los dos sentidos y el gate los evalúa juntos.
    """
    negativos = [(c, p) for c, p in _emparejar(casos, pred) if c.tipo is Tipo.NEGATIVO]
    if not negativos:
        return Metrica("G-ABST-FN", None, 0)
    respondidos = sum(1 for _, p in negativos if not p.abstenida)
    return Metrica("G-ABST-FN", respondidos * len(negativos), len(negativos))

mutants_x_abstencion_indebida__mutmut['_mutmut_orig'] = x_abstencion_indebida__mutmut_orig # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_1'] = x_abstencion_indebida__mutmut_1 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_2'] = x_abstencion_indebida__mutmut_2 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_3'] = x_abstencion_indebida__mutmut_3 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_4'] = x_abstencion_indebida__mutmut_4 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_5'] = x_abstencion_indebida__mutmut_5 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_6'] = x_abstencion_indebida__mutmut_6 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_7'] = x_abstencion_indebida__mutmut_7 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_8'] = x_abstencion_indebida__mutmut_8 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_9'] = x_abstencion_indebida__mutmut_9 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_10'] = x_abstencion_indebida__mutmut_10 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_11'] = x_abstencion_indebida__mutmut_11 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_12'] = x_abstencion_indebida__mutmut_12 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_13'] = x_abstencion_indebida__mutmut_13 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_14'] = x_abstencion_indebida__mutmut_14 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_15'] = x_abstencion_indebida__mutmut_15 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_16'] = x_abstencion_indebida__mutmut_16 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_17'] = x_abstencion_indebida__mutmut_17 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_18'] = x_abstencion_indebida__mutmut_18 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_19'] = x_abstencion_indebida__mutmut_19 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_20'] = x_abstencion_indebida__mutmut_20 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_21'] = x_abstencion_indebida__mutmut_21 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_22'] = x_abstencion_indebida__mutmut_22 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_23'] = x_abstencion_indebida__mutmut_23 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_24'] = x_abstencion_indebida__mutmut_24 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_25'] = x_abstencion_indebida__mutmut_25 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_26'] = x_abstencion_indebida__mutmut_26 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_27'] = x_abstencion_indebida__mutmut_27 # type: ignore # mutmut generated
mutants_x_abstencion_indebida__mutmut['x_abstencion_indebida__mutmut_28'] = x_abstencion_indebida__mutmut_28 # type: ignore # mutmut generated
mutants_x__emparejar__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x__emparejar__mutmut)
def _emparejar(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = {}
    for p in pred:
        if p.caso_id in por_id:
            raise ValueError(f"{p.caso_id}: predicción duplicada")
        por_id[p.caso_id] = p

    conocidos = {c.id for c in casos}
    for caso_id in por_id:
        if caso_id not in conocidos:
            raise ValueError(f"{caso_id}: predicción para un caso que no está en el golden set")

    faltan = [c.id for c in casos if c.id not in por_id]
    if faltan:
        raise ValueError(f"casos sin predicción: {', '.join(faltan)}")

    return [(c, por_id[c.id]) for c in casos]


def x__emparejar__mutmut_orig(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = {}
    for p in pred:
        if p.caso_id in por_id:
            raise ValueError(f"{p.caso_id}: predicción duplicada")
        por_id[p.caso_id] = p

    conocidos = {c.id for c in casos}
    for caso_id in por_id:
        if caso_id not in conocidos:
            raise ValueError(f"{caso_id}: predicción para un caso que no está en el golden set")

    faltan = [c.id for c in casos if c.id not in por_id]
    if faltan:
        raise ValueError(f"casos sin predicción: {', '.join(faltan)}")

    return [(c, por_id[c.id]) for c in casos]


def x__emparejar__mutmut_1(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = None
    for p in pred:
        if p.caso_id in por_id:
            raise ValueError(f"{p.caso_id}: predicción duplicada")
        por_id[p.caso_id] = p

    conocidos = {c.id for c in casos}
    for caso_id in por_id:
        if caso_id not in conocidos:
            raise ValueError(f"{caso_id}: predicción para un caso que no está en el golden set")

    faltan = [c.id for c in casos if c.id not in por_id]
    if faltan:
        raise ValueError(f"casos sin predicción: {', '.join(faltan)}")

    return [(c, por_id[c.id]) for c in casos]


def x__emparejar__mutmut_2(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = {}
    for p in pred:
        if p.caso_id not in por_id:
            raise ValueError(f"{p.caso_id}: predicción duplicada")
        por_id[p.caso_id] = p

    conocidos = {c.id for c in casos}
    for caso_id in por_id:
        if caso_id not in conocidos:
            raise ValueError(f"{caso_id}: predicción para un caso que no está en el golden set")

    faltan = [c.id for c in casos if c.id not in por_id]
    if faltan:
        raise ValueError(f"casos sin predicción: {', '.join(faltan)}")

    return [(c, por_id[c.id]) for c in casos]


def x__emparejar__mutmut_3(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = {}
    for p in pred:
        if p.caso_id in por_id:
            raise ValueError(None)
        por_id[p.caso_id] = p

    conocidos = {c.id for c in casos}
    for caso_id in por_id:
        if caso_id not in conocidos:
            raise ValueError(f"{caso_id}: predicción para un caso que no está en el golden set")

    faltan = [c.id for c in casos if c.id not in por_id]
    if faltan:
        raise ValueError(f"casos sin predicción: {', '.join(faltan)}")

    return [(c, por_id[c.id]) for c in casos]


def x__emparejar__mutmut_4(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = {}
    for p in pred:
        if p.caso_id in por_id:
            raise ValueError(f"{p.caso_id}: predicción duplicada")
        por_id[p.caso_id] = None

    conocidos = {c.id for c in casos}
    for caso_id in por_id:
        if caso_id not in conocidos:
            raise ValueError(f"{caso_id}: predicción para un caso que no está en el golden set")

    faltan = [c.id for c in casos if c.id not in por_id]
    if faltan:
        raise ValueError(f"casos sin predicción: {', '.join(faltan)}")

    return [(c, por_id[c.id]) for c in casos]


def x__emparejar__mutmut_5(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = {}
    for p in pred:
        if p.caso_id in por_id:
            raise ValueError(f"{p.caso_id}: predicción duplicada")
        por_id[p.caso_id] = p

    conocidos = None
    for caso_id in por_id:
        if caso_id not in conocidos:
            raise ValueError(f"{caso_id}: predicción para un caso que no está en el golden set")

    faltan = [c.id for c in casos if c.id not in por_id]
    if faltan:
        raise ValueError(f"casos sin predicción: {', '.join(faltan)}")

    return [(c, por_id[c.id]) for c in casos]


def x__emparejar__mutmut_6(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = {}
    for p in pred:
        if p.caso_id in por_id:
            raise ValueError(f"{p.caso_id}: predicción duplicada")
        por_id[p.caso_id] = p

    conocidos = {c.id for c in casos}
    for caso_id in por_id:
        if caso_id in conocidos:
            raise ValueError(f"{caso_id}: predicción para un caso que no está en el golden set")

    faltan = [c.id for c in casos if c.id not in por_id]
    if faltan:
        raise ValueError(f"casos sin predicción: {', '.join(faltan)}")

    return [(c, por_id[c.id]) for c in casos]


def x__emparejar__mutmut_7(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = {}
    for p in pred:
        if p.caso_id in por_id:
            raise ValueError(f"{p.caso_id}: predicción duplicada")
        por_id[p.caso_id] = p

    conocidos = {c.id for c in casos}
    for caso_id in por_id:
        if caso_id not in conocidos:
            raise ValueError(None)

    faltan = [c.id for c in casos if c.id not in por_id]
    if faltan:
        raise ValueError(f"casos sin predicción: {', '.join(faltan)}")

    return [(c, por_id[c.id]) for c in casos]


def x__emparejar__mutmut_8(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = {}
    for p in pred:
        if p.caso_id in por_id:
            raise ValueError(f"{p.caso_id}: predicción duplicada")
        por_id[p.caso_id] = p

    conocidos = {c.id for c in casos}
    for caso_id in por_id:
        if caso_id not in conocidos:
            raise ValueError(f"{caso_id}: predicción para un caso que no está en el golden set")

    faltan = None
    if faltan:
        raise ValueError(f"casos sin predicción: {', '.join(faltan)}")

    return [(c, por_id[c.id]) for c in casos]


def x__emparejar__mutmut_9(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = {}
    for p in pred:
        if p.caso_id in por_id:
            raise ValueError(f"{p.caso_id}: predicción duplicada")
        por_id[p.caso_id] = p

    conocidos = {c.id for c in casos}
    for caso_id in por_id:
        if caso_id not in conocidos:
            raise ValueError(f"{caso_id}: predicción para un caso que no está en el golden set")

    faltan = [c.id for c in casos if c.id in por_id]
    if faltan:
        raise ValueError(f"casos sin predicción: {', '.join(faltan)}")

    return [(c, por_id[c.id]) for c in casos]


def x__emparejar__mutmut_10(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = {}
    for p in pred:
        if p.caso_id in por_id:
            raise ValueError(f"{p.caso_id}: predicción duplicada")
        por_id[p.caso_id] = p

    conocidos = {c.id for c in casos}
    for caso_id in por_id:
        if caso_id not in conocidos:
            raise ValueError(f"{caso_id}: predicción para un caso que no está en el golden set")

    faltan = [c.id for c in casos if c.id not in por_id]
    if faltan:
        raise ValueError(None)

    return [(c, por_id[c.id]) for c in casos]


def x__emparejar__mutmut_11(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = {}
    for p in pred:
        if p.caso_id in por_id:
            raise ValueError(f"{p.caso_id}: predicción duplicada")
        por_id[p.caso_id] = p

    conocidos = {c.id for c in casos}
    for caso_id in por_id:
        if caso_id not in conocidos:
            raise ValueError(f"{caso_id}: predicción para un caso que no está en el golden set")

    faltan = [c.id for c in casos if c.id not in por_id]
    if faltan:
        raise ValueError(f"casos sin predicción: {', '.join(None)}")

    return [(c, por_id[c.id]) for c in casos]


def x__emparejar__mutmut_12(
    casos: Sequence[CasoGolden], pred: Sequence[Prediccion]
) -> list[tuple[CasoGolden, Prediccion]]:
    """Casa cada caso con su predicción, o se niega a seguir.

    Un conjunto descuadrado produce un número plausible sobre algo que no es el golden set,
    y eso no se detecta mirando el resultado: el 0,87 se publica igual. Se detecta aquí.
    """
    por_id: dict[str, Prediccion] = {}
    for p in pred:
        if p.caso_id in por_id:
            raise ValueError(f"{p.caso_id}: predicción duplicada")
        por_id[p.caso_id] = p

    conocidos = {c.id for c in casos}
    for caso_id in por_id:
        if caso_id not in conocidos:
            raise ValueError(f"{caso_id}: predicción para un caso que no está en el golden set")

    faltan = [c.id for c in casos if c.id not in por_id]
    if faltan:
        raise ValueError(f"casos sin predicción: {'XX, XX'.join(faltan)}")

    return [(c, por_id[c.id]) for c in casos]

mutants_x__emparejar__mutmut['_mutmut_orig'] = x__emparejar__mutmut_orig # type: ignore # mutmut generated
mutants_x__emparejar__mutmut['x__emparejar__mutmut_1'] = x__emparejar__mutmut_1 # type: ignore # mutmut generated
mutants_x__emparejar__mutmut['x__emparejar__mutmut_2'] = x__emparejar__mutmut_2 # type: ignore # mutmut generated
mutants_x__emparejar__mutmut['x__emparejar__mutmut_3'] = x__emparejar__mutmut_3 # type: ignore # mutmut generated
mutants_x__emparejar__mutmut['x__emparejar__mutmut_4'] = x__emparejar__mutmut_4 # type: ignore # mutmut generated
mutants_x__emparejar__mutmut['x__emparejar__mutmut_5'] = x__emparejar__mutmut_5 # type: ignore # mutmut generated
mutants_x__emparejar__mutmut['x__emparejar__mutmut_6'] = x__emparejar__mutmut_6 # type: ignore # mutmut generated
mutants_x__emparejar__mutmut['x__emparejar__mutmut_7'] = x__emparejar__mutmut_7 # type: ignore # mutmut generated
mutants_x__emparejar__mutmut['x__emparejar__mutmut_8'] = x__emparejar__mutmut_8 # type: ignore # mutmut generated
mutants_x__emparejar__mutmut['x__emparejar__mutmut_9'] = x__emparejar__mutmut_9 # type: ignore # mutmut generated
mutants_x__emparejar__mutmut['x__emparejar__mutmut_10'] = x__emparejar__mutmut_10 # type: ignore # mutmut generated
mutants_x__emparejar__mutmut['x__emparejar__mutmut_11'] = x__emparejar__mutmut_11 # type: ignore # mutmut generated
mutants_x__emparejar__mutmut['x__emparejar__mutmut_12'] = x__emparejar__mutmut_12 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_precision_cita_articulo__mutmut)
def precision_cita_articulo(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_orig(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_1(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = None
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_2(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(None, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_3(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, None)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_4(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_5(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, )
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_6(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = None
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_7(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_8(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_9(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica(None, None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_10(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, None)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_11(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica(None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_12(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_13(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, )
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_14(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("XXG-CITA-PRECISIONXX", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_15(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("g-cita-precision", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_16(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 1)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_17(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = None
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_18(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        None
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_19(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        2
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_20(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs or all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_21(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            None
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_22(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(None)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_23(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(None, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_24(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, None, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_25(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, None) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_26(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_27(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_28(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, ) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_29(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica(None, aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_30(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", None, len(respondidos))


def x_precision_cita_articulo__mutmut_31(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), None)


def x_precision_cita_articulo__mutmut_32(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica(aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_33(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", len(respondidos))


def x_precision_cita_articulo__mutmut_34(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos / len(respondidos), )


def x_precision_cita_articulo__mutmut_35(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("XXG-CITA-PRECISIONXX", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_36(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("g-cita-precision", aciertos / len(respondidos), len(respondidos))


def x_precision_cita_articulo__mutmut_37(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """La misma métrica, comparando **a nivel de artículo**. Q-021, decidido por Samuel.

    **Es una divergencia declarada con `docs/CONTRACTS/retrieval-metrics.md`**, que dice que si
    el golden set especifica apartado la cita debe incluirlo. Se sostiene sobre una medida: el
    apartado exacto está entre las cinco fuentes que se le ofrecen al generador en el **39 %**
    de los casos, y entre doce sin colapsar en el **56 %**, contra un umbral de 0,85. No es que
    el generador cite mal — **es que no se le ofrece lo que se le exige citar**.

    Es además la misma lectura que Q-016 eligió para el recall, y resolver la misma pregunta
    distinto en dos sitios es lo que crea las contradicciones que este proyecto lleva dos fases
    pagando.

    **Lo que se pierde, dicho en voz alta:** con esta lectura, citar `art34.2` cuando lo
    correcto es `art34.1` cuenta como acierto. El sistema puede señalar el apartado de al lado
    y la métrica no lo verá. Por eso se publican **las dos** y el informe dice cuál se compara
    contra el umbral, igual que hace `make eval-retrieval` desde la fase 2.
    """
    emparejado = _emparejar(casos, pred)
    respondidos = [(c, p) for c, p in emparejado if not p.abstenida]
    if not respondidos:
        return Metrica("G-CITA-PRECISION", None, 0)
    aciertos = sum(
        1
        for caso, prediccion in respondidos
        if prediccion.refs
        and all(
            any(matches(cita, r, MatchLevel.ARTICULO) for r in caso.refs)
            for cita in prediccion.refs
        )
    )
    return Metrica("G-CITA-PRECISION", aciertos * len(respondidos), len(respondidos))

mutants_x_precision_cita_articulo__mutmut['_mutmut_orig'] = x_precision_cita_articulo__mutmut_orig # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_1'] = x_precision_cita_articulo__mutmut_1 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_2'] = x_precision_cita_articulo__mutmut_2 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_3'] = x_precision_cita_articulo__mutmut_3 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_4'] = x_precision_cita_articulo__mutmut_4 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_5'] = x_precision_cita_articulo__mutmut_5 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_6'] = x_precision_cita_articulo__mutmut_6 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_7'] = x_precision_cita_articulo__mutmut_7 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_8'] = x_precision_cita_articulo__mutmut_8 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_9'] = x_precision_cita_articulo__mutmut_9 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_10'] = x_precision_cita_articulo__mutmut_10 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_11'] = x_precision_cita_articulo__mutmut_11 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_12'] = x_precision_cita_articulo__mutmut_12 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_13'] = x_precision_cita_articulo__mutmut_13 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_14'] = x_precision_cita_articulo__mutmut_14 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_15'] = x_precision_cita_articulo__mutmut_15 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_16'] = x_precision_cita_articulo__mutmut_16 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_17'] = x_precision_cita_articulo__mutmut_17 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_18'] = x_precision_cita_articulo__mutmut_18 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_19'] = x_precision_cita_articulo__mutmut_19 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_20'] = x_precision_cita_articulo__mutmut_20 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_21'] = x_precision_cita_articulo__mutmut_21 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_22'] = x_precision_cita_articulo__mutmut_22 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_23'] = x_precision_cita_articulo__mutmut_23 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_24'] = x_precision_cita_articulo__mutmut_24 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_25'] = x_precision_cita_articulo__mutmut_25 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_26'] = x_precision_cita_articulo__mutmut_26 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_27'] = x_precision_cita_articulo__mutmut_27 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_28'] = x_precision_cita_articulo__mutmut_28 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_29'] = x_precision_cita_articulo__mutmut_29 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_30'] = x_precision_cita_articulo__mutmut_30 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_31'] = x_precision_cita_articulo__mutmut_31 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_32'] = x_precision_cita_articulo__mutmut_32 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_33'] = x_precision_cita_articulo__mutmut_33 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_34'] = x_precision_cita_articulo__mutmut_34 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_35'] = x_precision_cita_articulo__mutmut_35 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_36'] = x_precision_cita_articulo__mutmut_36 # type: ignore # mutmut generated
mutants_x_precision_cita_articulo__mutmut['x_precision_cita_articulo__mutmut_37'] = x_precision_cita_articulo__mutmut_37 # type: ignore # mutmut generated
