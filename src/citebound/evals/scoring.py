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


def cita_pertenece(cita: LegalRef, relevantes: Sequence[LegalRef]) -> bool:
    """¿La cita está «en `R(q)`» con la granularidad que el caso exige?

    **El nivel exigido no es un campo del golden set: se deriva de la propia referencia.**
    Si el caso dice `art34.1`, la cita tiene que llegar al apartado y `art34` es fallo. Si el
    caso dice `art34`, citar `art34.1` es correcto — ser más preciso que lo pedido no puede
    penalizar. La asimetría va en un solo sentido y es la de `MatchLevel`.
    """
    return any(matches(cita, r, r.level) for r in relevantes)


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


def abstencion_incorrecta(casos: Sequence[CasoGolden], pred: Sequence[Prediccion]) -> Metrica:
    """`casos_abstenidos_con_R(q)_no_vacío / casos_con_R(q)_no_vacío`. Se calló habiendo
    respuesta: un sistema inútil pero prudente."""
    con_respuesta = [(c, p) for c, p in _emparejar(casos, pred) if c.refs]
    if not con_respuesta:
        return Metrica("G-ABST-FP", None, 0)
    callados = sum(1 for _, p in con_respuesta if p.abstenida)
    return Metrica("G-ABST-FP", callados / len(con_respuesta), len(con_respuesta))


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
