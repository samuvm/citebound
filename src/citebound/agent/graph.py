"""El agente como **máquina de estados**, no como framework · `recuperar → redactar → verificar`.

`docs/PLAN.md` lo dibuja así y `docs/RULES.md` R7 lo acota: LangGraph se usa **solo** como
máquina de estados. Lo que aporta y por lo que está aquí es concreto —un grafo con estado,
aristas condicionales y *timeout* por nodo— y lo que **no** se le pide es abstraer el retrieval
ni el LLM, que en este proyecto están escritos a mano a propósito: la fusión y el `ts_rank_cd`
son la mitad de la tesis, y la cita cerrada exige controlar el stream token a token.

**El bucle está en el grafo y el tope en el dominio.** La arista condicional vuelve a `redactar`
mientras `domain.retry.decidir` diga `REINTENTAR`, y quien cuenta hasta dos es el dominio: si el
tope viviera en la arista, sería una propiedad del framework y no del sistema, y no se podría
comprobar con Hypothesis.

`RULES` §3.1 pone este fichero en TDD **prohibido**: la forma de un grafo la fija la librería, no
un test escrito antes. Se prueba por su comportamiento observable —reintento con éxito, reintento
agotado, error del proveedor, corpus vacío— con dobles grabados, en `tests/integration/`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph

from citebound.domain.citation import (
    Cita,
    Fuente,
    Veredicto,
    parsear_borrador,
    segmentar,
    verificar,
)
from citebound.domain.retry import Curso, Salida, decidir, resolver_curso

__all__ = [
    "CARACTERES_POR_FUENTE",
    "NO_PUEDO_RESPONDER",
    "Estado",
    "Generador",
    "Recuperador",
    "Resultado",
    "bloques_de",
    "construir",
    "responder",
]

CARACTERES_POR_FUENTE = 500
"""Cuánto texto de cada artículo entra en el prompt. **Es la mitad de `G-TTFT`.**

Sin tope, los cinco artículos hacían un prompt de **13.727 caracteres** y cada petición pagaba
su prefill entero: 2.742 ms el primer token con prompt nuevo, 49 ms cuando Ollama podía
reutilizar su caché. En un bench toda pregunta trae un prompt distinto, así que **todas** pagan
el caso malo — y ahí se iba el grueso del p95.

**500, y sale de la aritmética de `G-TTFT`.** El primer token cuesta ~0,25 ms por carácter de
prompt, medido: 7.752 caracteres → 2.166 ms · 4.634 → 1.192 · 3.453 → 753. Con `sources` en
~223 ms, el presupuesto de 1.500 ms deja ~1.270 para el prefill, y eso son unos 4.600
caracteres de prompt: cinco fuentes de 600 más la plantilla.

Se probaron los tres: **1.500** daba 2.686 ms totales, **600** se quedó en 1.522 —veintidós
milisegundos por encima del umbral, que es peor que fallar por mucho— y **500** deja margen.

**Y no cuesta calidad, medido y no supuesto.** Las cinco metas de `make eval` sobre 60 casos dan
exactamente el mismo número con 1.500 que con 600: `G-CITA-PRECISION` 0,5106, `G-COBERTURA`
0,7833, `G-ABST-FP` 0,2167. El modelo cita del principio del artículo —la rúbrica y las primeras
frases—, así que el texto que se recorta es el que no estaba usando. El prompt era el doble de
grande de lo necesario.

**No pone en riesgo `G-QUOTE-LIT`.** El verificador coteja el `quote` contra el texto
**completo** de la fuente, no contra lo que vio el modelo: truncar reduce de dónde puede citar,
nunca convierte una cita buena en no literal.
"""

NO_PUEDO_RESPONDER = "NO PUEDO RESPONDER"
"""Lo que el prompt le pide decir cuando los artículos no contienen la respuesta.

Se reconoce aquí y se convierte en abstención **sin gastar reintentos**: el modelo ya ha dicho
que no puede, y volver a preguntárselo es pagar latencia por la misma respuesta. Es además la
única forma que tiene de abstenerse por sí mismo, y quitársela lo empujaría a inventar."""


class Recuperador(Protocol):
    """Puerto de entrada del retrieval. El grafo no sabe si detrás hay Postgres o una grabación."""

    def __call__(self, pregunta: str) -> Sequence[Fuente]: ...


class Puntuador(Protocol):
    """Da una relevancia por fuente. **Opcional a propósito**: sin él el sistema decide como
    antes, y su ausencia nunca se lee como irrelevancia."""

    def __call__(self, pregunta: str, fuentes: Sequence[Fuente]) -> list[float]: ...


class Generador(Protocol):
    """Puerto del modelo. Recibe el prompt ya montado y devuelve el borrador entero."""

    def __call__(self, prompt: str) -> str: ...


class Estado(TypedDict, total=False):
    """Lo que viaja por el grafo. Los borradores y veredictos se **acumulan**, no se sustituyen.

    Guardar la historia y no solo el último es lo que permite que `resolver_curso` decida con
    todo delante, y que la traza pueda enseñar por qué se retractó el primer intento.
    """

    pregunta: str
    fuentes: list[Fuente]
    borradores: list[str]
    veredictos: list[Veredicto]


@dataclass(frozen=True, slots=True)
class Resultado:
    """Lo que sale del grafo, con todo lo que el evento `done` necesita publicar."""

    curso: Curso
    respuesta: str = ""
    citas: tuple[Cita, ...] = ()
    fuentes: tuple[Fuente, ...] = ()
    borradores: tuple[str, ...] = field(default=())


@dataclass(frozen=True, slots=True)
class _Nodos:
    """Los tres nodos, con sus puertos dentro. Existe para que `construir` no cierre sobre
    variables sueltas y el grafo se pueda inspeccionar."""

    recuperador: Recuperador
    generador: Generador
    plantilla: str

    def recuperar(self, estado: Estado) -> dict[str, Any]:
        return {"fuentes": list(self.recuperador(estado["pregunta"]))}

    def redactar(self, estado: Estado) -> dict[str, Any]:
        fuentes = estado.get("fuentes") or []
        # Se numeran aquí y solo aquí. El modelo ve `[1]`, `[2]`… y nunca un número de
        # artículo: si creyera que puede escribirlos, lo haría.
        bloques = "\n\n".join(f"[{i}] {f.texto}" for i, f in enumerate(fuentes, start=1))
        prompt = self.plantilla.format(pregunta=estado["pregunta"], fuentes=bloques)
        return {"borradores": [*estado.get("borradores", []), self.generador(prompt)]}

    def verificar(self, estado: Estado) -> dict[str, Any]:
        borrador = estado["borradores"][-1]
        fuentes = estado.get("fuentes") or []
        _, citas = parsear_borrador(borrador, fuentes)
        veredicto = verificar(citas, fuentes)
        return {"veredictos": [*estado.get("veredictos", []), veredicto]}


def bloques_de(fuentes: Sequence[Fuente]) -> str:
    """Los artículos numerados como los ve el modelo. **Una sola función para los dos caminos.**

    `agent.graph` y `agent.servir` tienen que numerar igual: si numeraran distinto, el mismo
    borrador significaría cosas distintas según por dónde se sirviera, y `make eval` mediría un
    sistema que nadie ejecuta.

    **La etiqueta es `[[REF:1]]` y no `[1]`, y es una medida.** Con `[1]`, el modelo escribía el
    número del ARTÍCULO en el marcador —`[[REF:12]]` para el artículo 12, `[[REF:90]]` para el
    90— en 36 de 274 casos, que se retractaban por fuera de rango. Enseñarle el token exacto que
    tiene que escribir, en el sitio donde lo tiene que leer, es más barato que explicárselo.
    """
    return "\n\n".join(
        f"[[REF:{i}]] " + " ".join(f"({j}) {t}" for j, t in enumerate(_tramos(f), start=1))
        for i, f in enumerate(fuentes, start=1)
    )


def _tramos(fuente: Fuente) -> tuple[str, ...]:
    """Los tramos de una fuente, **truncando por tramos enteros y no por caracteres**.

    Cortar a 500 caracteres a pelo partiría el último tramo por la mitad, y el modelo podría
    señalar un `§4` que aquí se ve completo y en el original sigue: el código copiaría el tramo
    entero y saldría un fragmento más largo que el que el modelo leyó. Truncar por tramos
    enteros hace que lo que ve y lo que se copia sean lo mismo.
    """
    enteros = segmentar(fuente.texto)
    cabidos: list[str] = []
    gastado = 0
    for tramo in enteros:
        if gastado + len(tramo) > CARACTERES_POR_FUENTE and cabidos:
            break
        cabidos.append(tramo)
        gastado += len(tramo) + 1
    return tuple(cabidos)


def _siguiente(estado: Estado) -> str:
    """La arista condicional. **Pregunta al dominio y no decide nada por su cuenta.**

    El tope de reintentos vive en `domain.retry`, no aquí: si viviera en la arista sería una
    propiedad de LangGraph en vez del sistema, y no habría forma de comprobarlo con Hypothesis.
    """
    veredictos = estado.get("veredictos") or []
    if not veredictos:
        return END
    if _dijo_que_no_puede(estado):
        return END
    salida = decidir(
        veredictos[-1],
        reintentos_hechos=len(veredictos) - 1,
        hay_fuentes=bool(estado.get("fuentes")),
    )
    return "redactar" if salida is Salida.REINTENTAR else END


def _dijo_que_no_puede(estado: Estado) -> bool:
    borradores = estado.get("borradores") or []
    return bool(borradores) and NO_PUEDO_RESPONDER in borradores[-1].upper()


def construir(*, recuperador: Recuperador, generador: Generador, plantilla: str) -> Any:
    """El grafo compilado. Los puertos entran por parámetro, que es lo que lo hace testeable."""
    nodos = _Nodos(recuperador=recuperador, generador=generador, plantilla=plantilla)
    grafo: StateGraph[Estado, Any, Any, Any] = StateGraph(Estado)
    grafo.add_node("recuperar", nodos.recuperar)
    grafo.add_node("redactar", nodos.redactar)
    grafo.add_node("verificar", nodos.verificar)
    grafo.add_edge(START, "recuperar")
    grafo.add_edge("recuperar", "redactar")
    grafo.add_edge("redactar", "verificar")
    grafo.add_conditional_edges("verificar", _siguiente, {"redactar": "redactar", END: END})
    return grafo.compile()


def responder(grafo: Any, pregunta: str) -> Resultado:
    """Corre el grafo y traduce su estado final a un `Resultado`.

    La decisión final la vuelve a tomar `domain.retry.resolver_curso` sobre la lista entera de
    veredictos, en vez de fiarse de por qué paró el grafo. Son dos caminos al mismo sitio, y
    que el que manda sea el puro es lo que hace que la abstención no dependa del framework.
    """
    estado: Estado = grafo.invoke({"pregunta": pregunta})
    fuentes = tuple(estado.get("fuentes") or [])
    borradores = tuple(estado.get("borradores") or [])
    veredictos = estado.get("veredictos") or []

    if borradores and NO_PUEDO_RESPONDER in borradores[-1].upper():
        # El modelo se abstuvo él mismo. No se gastan reintentos en insistir.
        return Resultado(
            curso=Curso(salida=Salida.ABSTENERSE, reintentos=max(0, len(borradores) - 1)),
            fuentes=fuentes,
            borradores=borradores,
        )

    curso = resolver_curso(veredictos, hay_fuentes=bool(fuentes))
    if curso.salida is not Salida.RESPONDER:
        return Resultado(curso=curso, fuentes=fuentes, borradores=borradores)

    respuesta, citas = parsear_borrador(borradores[curso.reintentos], fuentes)
    return Resultado(
        curso=curso, respuesta=respuesta, citas=citas, fuentes=fuentes, borradores=borradores
    )
