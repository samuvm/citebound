"""Reintento acotado y abstención · qué se hace cuando la verificación dice que no.

El contrato SSE (`docs/RULES.md` §2.2) fija tres salidas y solo tres: se responde, se retracta y
se reintenta —como mucho dos veces—, o se abstiene. **`abstain` es salida de primera clase**, no
un error disfrazado, y esta es la máquina de estados que elige entre las tres.

**Es puro a propósito.** La decisión de abstenerse no puede depender de si el proveedor estaba
lento o de qué hora era: si dependiera, dos ejecuciones del mismo caso podrían dar respuestas
distintas y `G-EVAL-DET` dejaría de significar nada.

**Por qué abstenerse tiene que ser barato de elegir y caro de abusar.** `G-ABST-FP` —abstenerse
habiendo respuesta, ≤ 0,05— y `G-ABST-FN` —responder sin haberla, ≤ 0,10— son una **pareja
atómica** en `docs/GOALS.yaml`. Medidas por separado, la forma óptima de aprobar cualquiera de
las dos es hacer trampa: callarse siempre da una precisión de cita de 1,00 sobre cero
respuestas, y responder siempre nunca se abstiene de más.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from citebound.domain.citation import Motivo, Veredicto
from citebound.domain.legalref import LegalRef

__all__ = [
    "MAX_REINTENTOS",
    "UMBRAL_RELEVANCIA",
    "Curso",
    "Salida",
    "decidir",
    "resolver_curso",
]

UMBRAL_RELEVANCIA = 0.10
"""Por debajo de esto, lo recuperado no viene a cuento y el sistema se calla.

**Sale de una medida, no de una intuición.** La mejor puntuación de las cinco fuentes, sobre los
274 casos del golden set: mediana **0,893** en los positivos y **0,011** en los negativos. Las
distribuciones separan mucho pero se solapan, así que no hay umbral que cumpla las dos metas de
la pareja a la vez:

| umbral | `G-ABST-FP` | `G-ABST-FN` |
|---:|---:|---:|
| sin señal | 0,259 | **0,724** |
| 0,05 | 0,065 | 0,259 |
| **0,10** | **0,088** | **0,172** |
| 0,30 | 0,171 | 0,121 |

Se elige 0,10 porque equilibra las dos violaciones relativas —1,8 y 1,7 veces su umbral— en vez de
arreglar una hundiendo la otra. `G-ABST-FP` y `G-ABST-FN` son una **pareja atómica** justamente
para que no se pueda hacer eso.

**Ajustado sobre el golden set, que es también el conjunto de evaluación.** Es sobreajuste y se
declara: el juez de verdad es `tests/holdout/`, y ahí este número no se ha tocado."""

MAX_REINTENTOS = 2
"""Dos, y el tope no es una sugerencia.

Cada reintento es una llamada más al modelo **dentro** del presupuesto de `G-TTFT`, que tiene
1.500 ms en total y 210 ms de holgura. Un tope blando aquí se convierte aguas abajo en una
petición que no contesta, que es peor que una abstención."""


from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated, MutantDict


class Salida(StrEnum):
    """Las tres del contrato SSE, y ninguna más.

    `REINTENTAR` es la única no terminal: existe para volver a `draft` con el motivo delante.
    """

    RESPONDER = "responder"
    REINTENTAR = "reintentar"
    ABSTENERSE = "abstenerse"


@dataclass(frozen=True, slots=True)
class Curso:
    """Cómo acabó la petición, con lo que el evento `done` necesita publicar.

    `reintentos` viaja aquí porque es observable y se mide: un sistema que reintenta siempre
    dos veces tiene un problema de prompt, no de verificador, y sin el número no se ve.
    """

    salida: Salida
    reintentos: int = 0
    refs: tuple[LegalRef, ...] = ()
    motivo: Motivo | None = None
mutants_x_decidir__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_decidir__mutmut)
def decidir(
    veredicto: Veredicto,
    *,
    reintentos_hechos: int,
    hay_fuentes: bool,
    relevancia: float | None = None,
) -> Salida:
    """La decisión de un solo paso. Todo lo que la determina son sus tres argumentos.

    **Sin fuentes se abstiene sin gastar un reintento.** Si la búsqueda no trajo nada, el modelo
    no puede citar lo que no existe: reintentar es pagar latencia por un resultado que ya se
    conoce. Se comprueba antes que el veredicto porque manda sobre él — un `ok` sin fuentes
    solo puede venir de una lista de citas vacía, y eso no es una respuesta citada.
    """
    if reintentos_hechos < 0:
        raise ValueError(f"reintentos hechos no puede ser negativo: {reintentos_hechos}")
    if not hay_fuentes:
        return Salida.ABSTENERSE
    # **Antes que el veredicto y antes que el reintento.** Si nada de lo recuperado viene a
    # cuento, reintentar es pedirle al modelo que lo intente otra vez con el mismo material
    # inútil, y generar es pagar latencia para acabar citando algo real que no responde — que
    # es peor que callarse, porque parece bueno. `None` es «no se midió», no «cero».
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA:
        return Salida.ABSTENERSE
    if veredicto.ok:
        return Salida.RESPONDER
    if reintentos_hechos < MAX_REINTENTOS:
        return Salida.REINTENTAR
    # **Aquí es donde se sostiene la tesis.** Lo natural sería emitir el último borrador
    # «porque es lo que hay»; eso es una respuesta que no verificó, presentada como si lo
    # hubiera hecho, que es exactamente el RAG que este proyecto no quiere ser.
    return Salida.ABSTENERSE


def x_decidir__mutmut_orig(
    veredicto: Veredicto,
    *,
    reintentos_hechos: int,
    hay_fuentes: bool,
    relevancia: float | None = None,
) -> Salida:
    """La decisión de un solo paso. Todo lo que la determina son sus tres argumentos.

    **Sin fuentes se abstiene sin gastar un reintento.** Si la búsqueda no trajo nada, el modelo
    no puede citar lo que no existe: reintentar es pagar latencia por un resultado que ya se
    conoce. Se comprueba antes que el veredicto porque manda sobre él — un `ok` sin fuentes
    solo puede venir de una lista de citas vacía, y eso no es una respuesta citada.
    """
    if reintentos_hechos < 0:
        raise ValueError(f"reintentos hechos no puede ser negativo: {reintentos_hechos}")
    if not hay_fuentes:
        return Salida.ABSTENERSE
    # **Antes que el veredicto y antes que el reintento.** Si nada de lo recuperado viene a
    # cuento, reintentar es pedirle al modelo que lo intente otra vez con el mismo material
    # inútil, y generar es pagar latencia para acabar citando algo real que no responde — que
    # es peor que callarse, porque parece bueno. `None` es «no se midió», no «cero».
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA:
        return Salida.ABSTENERSE
    if veredicto.ok:
        return Salida.RESPONDER
    if reintentos_hechos < MAX_REINTENTOS:
        return Salida.REINTENTAR
    # **Aquí es donde se sostiene la tesis.** Lo natural sería emitir el último borrador
    # «porque es lo que hay»; eso es una respuesta que no verificó, presentada como si lo
    # hubiera hecho, que es exactamente el RAG que este proyecto no quiere ser.
    return Salida.ABSTENERSE


def x_decidir__mutmut_1(
    veredicto: Veredicto,
    *,
    reintentos_hechos: int,
    hay_fuentes: bool,
    relevancia: float | None = None,
) -> Salida:
    """La decisión de un solo paso. Todo lo que la determina son sus tres argumentos.

    **Sin fuentes se abstiene sin gastar un reintento.** Si la búsqueda no trajo nada, el modelo
    no puede citar lo que no existe: reintentar es pagar latencia por un resultado que ya se
    conoce. Se comprueba antes que el veredicto porque manda sobre él — un `ok` sin fuentes
    solo puede venir de una lista de citas vacía, y eso no es una respuesta citada.
    """
    if reintentos_hechos <= 0:
        raise ValueError(f"reintentos hechos no puede ser negativo: {reintentos_hechos}")
    if not hay_fuentes:
        return Salida.ABSTENERSE
    # **Antes que el veredicto y antes que el reintento.** Si nada de lo recuperado viene a
    # cuento, reintentar es pedirle al modelo que lo intente otra vez con el mismo material
    # inútil, y generar es pagar latencia para acabar citando algo real que no responde — que
    # es peor que callarse, porque parece bueno. `None` es «no se midió», no «cero».
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA:
        return Salida.ABSTENERSE
    if veredicto.ok:
        return Salida.RESPONDER
    if reintentos_hechos < MAX_REINTENTOS:
        return Salida.REINTENTAR
    # **Aquí es donde se sostiene la tesis.** Lo natural sería emitir el último borrador
    # «porque es lo que hay»; eso es una respuesta que no verificó, presentada como si lo
    # hubiera hecho, que es exactamente el RAG que este proyecto no quiere ser.
    return Salida.ABSTENERSE


def x_decidir__mutmut_2(
    veredicto: Veredicto,
    *,
    reintentos_hechos: int,
    hay_fuentes: bool,
    relevancia: float | None = None,
) -> Salida:
    """La decisión de un solo paso. Todo lo que la determina son sus tres argumentos.

    **Sin fuentes se abstiene sin gastar un reintento.** Si la búsqueda no trajo nada, el modelo
    no puede citar lo que no existe: reintentar es pagar latencia por un resultado que ya se
    conoce. Se comprueba antes que el veredicto porque manda sobre él — un `ok` sin fuentes
    solo puede venir de una lista de citas vacía, y eso no es una respuesta citada.
    """
    if reintentos_hechos < 1:
        raise ValueError(f"reintentos hechos no puede ser negativo: {reintentos_hechos}")
    if not hay_fuentes:
        return Salida.ABSTENERSE
    # **Antes que el veredicto y antes que el reintento.** Si nada de lo recuperado viene a
    # cuento, reintentar es pedirle al modelo que lo intente otra vez con el mismo material
    # inútil, y generar es pagar latencia para acabar citando algo real que no responde — que
    # es peor que callarse, porque parece bueno. `None` es «no se midió», no «cero».
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA:
        return Salida.ABSTENERSE
    if veredicto.ok:
        return Salida.RESPONDER
    if reintentos_hechos < MAX_REINTENTOS:
        return Salida.REINTENTAR
    # **Aquí es donde se sostiene la tesis.** Lo natural sería emitir el último borrador
    # «porque es lo que hay»; eso es una respuesta que no verificó, presentada como si lo
    # hubiera hecho, que es exactamente el RAG que este proyecto no quiere ser.
    return Salida.ABSTENERSE


def x_decidir__mutmut_3(
    veredicto: Veredicto,
    *,
    reintentos_hechos: int,
    hay_fuentes: bool,
    relevancia: float | None = None,
) -> Salida:
    """La decisión de un solo paso. Todo lo que la determina son sus tres argumentos.

    **Sin fuentes se abstiene sin gastar un reintento.** Si la búsqueda no trajo nada, el modelo
    no puede citar lo que no existe: reintentar es pagar latencia por un resultado que ya se
    conoce. Se comprueba antes que el veredicto porque manda sobre él — un `ok` sin fuentes
    solo puede venir de una lista de citas vacía, y eso no es una respuesta citada.
    """
    if reintentos_hechos < 0:
        raise ValueError(None)
    if not hay_fuentes:
        return Salida.ABSTENERSE
    # **Antes que el veredicto y antes que el reintento.** Si nada de lo recuperado viene a
    # cuento, reintentar es pedirle al modelo que lo intente otra vez con el mismo material
    # inútil, y generar es pagar latencia para acabar citando algo real que no responde — que
    # es peor que callarse, porque parece bueno. `None` es «no se midió», no «cero».
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA:
        return Salida.ABSTENERSE
    if veredicto.ok:
        return Salida.RESPONDER
    if reintentos_hechos < MAX_REINTENTOS:
        return Salida.REINTENTAR
    # **Aquí es donde se sostiene la tesis.** Lo natural sería emitir el último borrador
    # «porque es lo que hay»; eso es una respuesta que no verificó, presentada como si lo
    # hubiera hecho, que es exactamente el RAG que este proyecto no quiere ser.
    return Salida.ABSTENERSE


def x_decidir__mutmut_4(
    veredicto: Veredicto,
    *,
    reintentos_hechos: int,
    hay_fuentes: bool,
    relevancia: float | None = None,
) -> Salida:
    """La decisión de un solo paso. Todo lo que la determina son sus tres argumentos.

    **Sin fuentes se abstiene sin gastar un reintento.** Si la búsqueda no trajo nada, el modelo
    no puede citar lo que no existe: reintentar es pagar latencia por un resultado que ya se
    conoce. Se comprueba antes que el veredicto porque manda sobre él — un `ok` sin fuentes
    solo puede venir de una lista de citas vacía, y eso no es una respuesta citada.
    """
    if reintentos_hechos < 0:
        raise ValueError(f"reintentos hechos no puede ser negativo: {reintentos_hechos}")
    if hay_fuentes:
        return Salida.ABSTENERSE
    # **Antes que el veredicto y antes que el reintento.** Si nada de lo recuperado viene a
    # cuento, reintentar es pedirle al modelo que lo intente otra vez con el mismo material
    # inútil, y generar es pagar latencia para acabar citando algo real que no responde — que
    # es peor que callarse, porque parece bueno. `None` es «no se midió», no «cero».
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA:
        return Salida.ABSTENERSE
    if veredicto.ok:
        return Salida.RESPONDER
    if reintentos_hechos < MAX_REINTENTOS:
        return Salida.REINTENTAR
    # **Aquí es donde se sostiene la tesis.** Lo natural sería emitir el último borrador
    # «porque es lo que hay»; eso es una respuesta que no verificó, presentada como si lo
    # hubiera hecho, que es exactamente el RAG que este proyecto no quiere ser.
    return Salida.ABSTENERSE


def x_decidir__mutmut_5(
    veredicto: Veredicto,
    *,
    reintentos_hechos: int,
    hay_fuentes: bool,
    relevancia: float | None = None,
) -> Salida:
    """La decisión de un solo paso. Todo lo que la determina son sus tres argumentos.

    **Sin fuentes se abstiene sin gastar un reintento.** Si la búsqueda no trajo nada, el modelo
    no puede citar lo que no existe: reintentar es pagar latencia por un resultado que ya se
    conoce. Se comprueba antes que el veredicto porque manda sobre él — un `ok` sin fuentes
    solo puede venir de una lista de citas vacía, y eso no es una respuesta citada.
    """
    if reintentos_hechos < 0:
        raise ValueError(f"reintentos hechos no puede ser negativo: {reintentos_hechos}")
    if not hay_fuentes:
        return Salida.ABSTENERSE
    # **Antes que el veredicto y antes que el reintento.** Si nada de lo recuperado viene a
    # cuento, reintentar es pedirle al modelo que lo intente otra vez con el mismo material
    # inútil, y generar es pagar latencia para acabar citando algo real que no responde — que
    # es peor que callarse, porque parece bueno. `None` es «no se midió», no «cero».
    if relevancia is not None or relevancia < UMBRAL_RELEVANCIA:
        return Salida.ABSTENERSE
    if veredicto.ok:
        return Salida.RESPONDER
    if reintentos_hechos < MAX_REINTENTOS:
        return Salida.REINTENTAR
    # **Aquí es donde se sostiene la tesis.** Lo natural sería emitir el último borrador
    # «porque es lo que hay»; eso es una respuesta que no verificó, presentada como si lo
    # hubiera hecho, que es exactamente el RAG que este proyecto no quiere ser.
    return Salida.ABSTENERSE


def x_decidir__mutmut_6(
    veredicto: Veredicto,
    *,
    reintentos_hechos: int,
    hay_fuentes: bool,
    relevancia: float | None = None,
) -> Salida:
    """La decisión de un solo paso. Todo lo que la determina son sus tres argumentos.

    **Sin fuentes se abstiene sin gastar un reintento.** Si la búsqueda no trajo nada, el modelo
    no puede citar lo que no existe: reintentar es pagar latencia por un resultado que ya se
    conoce. Se comprueba antes que el veredicto porque manda sobre él — un `ok` sin fuentes
    solo puede venir de una lista de citas vacía, y eso no es una respuesta citada.
    """
    if reintentos_hechos < 0:
        raise ValueError(f"reintentos hechos no puede ser negativo: {reintentos_hechos}")
    if not hay_fuentes:
        return Salida.ABSTENERSE
    # **Antes que el veredicto y antes que el reintento.** Si nada de lo recuperado viene a
    # cuento, reintentar es pedirle al modelo que lo intente otra vez con el mismo material
    # inútil, y generar es pagar latencia para acabar citando algo real que no responde — que
    # es peor que callarse, porque parece bueno. `None` es «no se midió», no «cero».
    if relevancia is None and relevancia < UMBRAL_RELEVANCIA:
        return Salida.ABSTENERSE
    if veredicto.ok:
        return Salida.RESPONDER
    if reintentos_hechos < MAX_REINTENTOS:
        return Salida.REINTENTAR
    # **Aquí es donde se sostiene la tesis.** Lo natural sería emitir el último borrador
    # «porque es lo que hay»; eso es una respuesta que no verificó, presentada como si lo
    # hubiera hecho, que es exactamente el RAG que este proyecto no quiere ser.
    return Salida.ABSTENERSE


def x_decidir__mutmut_7(
    veredicto: Veredicto,
    *,
    reintentos_hechos: int,
    hay_fuentes: bool,
    relevancia: float | None = None,
) -> Salida:
    """La decisión de un solo paso. Todo lo que la determina son sus tres argumentos.

    **Sin fuentes se abstiene sin gastar un reintento.** Si la búsqueda no trajo nada, el modelo
    no puede citar lo que no existe: reintentar es pagar latencia por un resultado que ya se
    conoce. Se comprueba antes que el veredicto porque manda sobre él — un `ok` sin fuentes
    solo puede venir de una lista de citas vacía, y eso no es una respuesta citada.
    """
    if reintentos_hechos < 0:
        raise ValueError(f"reintentos hechos no puede ser negativo: {reintentos_hechos}")
    if not hay_fuentes:
        return Salida.ABSTENERSE
    # **Antes que el veredicto y antes que el reintento.** Si nada de lo recuperado viene a
    # cuento, reintentar es pedirle al modelo que lo intente otra vez con el mismo material
    # inútil, y generar es pagar latencia para acabar citando algo real que no responde — que
    # es peor que callarse, porque parece bueno. `None` es «no se midió», no «cero».
    if relevancia is not None and relevancia <= UMBRAL_RELEVANCIA:
        return Salida.ABSTENERSE
    if veredicto.ok:
        return Salida.RESPONDER
    if reintentos_hechos < MAX_REINTENTOS:
        return Salida.REINTENTAR
    # **Aquí es donde se sostiene la tesis.** Lo natural sería emitir el último borrador
    # «porque es lo que hay»; eso es una respuesta que no verificó, presentada como si lo
    # hubiera hecho, que es exactamente el RAG que este proyecto no quiere ser.
    return Salida.ABSTENERSE


def x_decidir__mutmut_8(
    veredicto: Veredicto,
    *,
    reintentos_hechos: int,
    hay_fuentes: bool,
    relevancia: float | None = None,
) -> Salida:
    """La decisión de un solo paso. Todo lo que la determina son sus tres argumentos.

    **Sin fuentes se abstiene sin gastar un reintento.** Si la búsqueda no trajo nada, el modelo
    no puede citar lo que no existe: reintentar es pagar latencia por un resultado que ya se
    conoce. Se comprueba antes que el veredicto porque manda sobre él — un `ok` sin fuentes
    solo puede venir de una lista de citas vacía, y eso no es una respuesta citada.
    """
    if reintentos_hechos < 0:
        raise ValueError(f"reintentos hechos no puede ser negativo: {reintentos_hechos}")
    if not hay_fuentes:
        return Salida.ABSTENERSE
    # **Antes que el veredicto y antes que el reintento.** Si nada de lo recuperado viene a
    # cuento, reintentar es pedirle al modelo que lo intente otra vez con el mismo material
    # inútil, y generar es pagar latencia para acabar citando algo real que no responde — que
    # es peor que callarse, porque parece bueno. `None` es «no se midió», no «cero».
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA:
        return Salida.ABSTENERSE
    if veredicto.ok:
        return Salida.RESPONDER
    if reintentos_hechos <= MAX_REINTENTOS:
        return Salida.REINTENTAR
    # **Aquí es donde se sostiene la tesis.** Lo natural sería emitir el último borrador
    # «porque es lo que hay»; eso es una respuesta que no verificó, presentada como si lo
    # hubiera hecho, que es exactamente el RAG que este proyecto no quiere ser.
    return Salida.ABSTENERSE

mutants_x_decidir__mutmut['_mutmut_orig'] = x_decidir__mutmut_orig # type: ignore # mutmut generated
mutants_x_decidir__mutmut['x_decidir__mutmut_1'] = x_decidir__mutmut_1 # type: ignore # mutmut generated
mutants_x_decidir__mutmut['x_decidir__mutmut_2'] = x_decidir__mutmut_2 # type: ignore # mutmut generated
mutants_x_decidir__mutmut['x_decidir__mutmut_3'] = x_decidir__mutmut_3 # type: ignore # mutmut generated
mutants_x_decidir__mutmut['x_decidir__mutmut_4'] = x_decidir__mutmut_4 # type: ignore # mutmut generated
mutants_x_decidir__mutmut['x_decidir__mutmut_5'] = x_decidir__mutmut_5 # type: ignore # mutmut generated
mutants_x_decidir__mutmut['x_decidir__mutmut_6'] = x_decidir__mutmut_6 # type: ignore # mutmut generated
mutants_x_decidir__mutmut['x_decidir__mutmut_7'] = x_decidir__mutmut_7 # type: ignore # mutmut generated
mutants_x_decidir__mutmut['x_decidir__mutmut_8'] = x_decidir__mutmut_8 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_resolver_curso__mutmut)
def resolver_curso(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_orig(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_1(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = False, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_2(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA or hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_3(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None or relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_4(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_5(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia <= UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_6(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=None, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_7(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=None)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_8(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_9(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, )

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_10(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = ""
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_11(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(None):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_12(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = None
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_13(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = None
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_14(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            None, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_15(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=None, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_16(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=None, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_17(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=None
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_18(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_19(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_20(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_21(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_22(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is not Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_23(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=None, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_24(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=None, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_25(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=None)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_26(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_27(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_28(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, )
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_29(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is not Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_30(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=None, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_31(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=None, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_32(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=None)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_33(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_34(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_35(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, )

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_36(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=None,
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_37(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=None,
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_38(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        motivo=None,
    )


def x_resolver_curso__mutmut_39(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        reintentos=max(0, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_40(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_41(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 1),
        )


def x_resolver_curso__mutmut_42(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(None, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_43(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, None),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_44(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_45(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, ),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_46(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(1, len(intentos) - 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_47(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) + 1),
        motivo=ultimo.motivo if ultimo else None,
    )


def x_resolver_curso__mutmut_48(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    if relevancia is not None and relevancia < UMBRAL_RELEVANCIA and hay_fuentes:
        return Curso(salida=Salida.ABSTENERSE, motivo=Motivo.SIN_RELEVANCIA)

    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(
            veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes, relevancia=relevancia
        )
        if salida is Salida.RESPONDER:
            return Curso(salida=salida, reintentos=hechos, refs=veredicto.refs)
        if salida is Salida.ABSTENERSE:
            return Curso(salida=salida, reintentos=hechos, motivo=veredicto.motivo)

    # Se acabaron los borradores sin llegar a una salida terminal: o no hubo ninguno, o el
    # grafo dejó de reintentar antes de agotar el presupuesto. En los dos casos no hay nada
    # verificado que emitir.
    return Curso(
        salida=Salida.ABSTENERSE,
        reintentos=max(0, len(intentos) - 2),
        motivo=ultimo.motivo if ultimo else None,
    )

mutants_x_resolver_curso__mutmut['_mutmut_orig'] = x_resolver_curso__mutmut_orig # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_1'] = x_resolver_curso__mutmut_1 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_2'] = x_resolver_curso__mutmut_2 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_3'] = x_resolver_curso__mutmut_3 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_4'] = x_resolver_curso__mutmut_4 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_5'] = x_resolver_curso__mutmut_5 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_6'] = x_resolver_curso__mutmut_6 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_7'] = x_resolver_curso__mutmut_7 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_8'] = x_resolver_curso__mutmut_8 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_9'] = x_resolver_curso__mutmut_9 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_10'] = x_resolver_curso__mutmut_10 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_11'] = x_resolver_curso__mutmut_11 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_12'] = x_resolver_curso__mutmut_12 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_13'] = x_resolver_curso__mutmut_13 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_14'] = x_resolver_curso__mutmut_14 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_15'] = x_resolver_curso__mutmut_15 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_16'] = x_resolver_curso__mutmut_16 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_17'] = x_resolver_curso__mutmut_17 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_18'] = x_resolver_curso__mutmut_18 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_19'] = x_resolver_curso__mutmut_19 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_20'] = x_resolver_curso__mutmut_20 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_21'] = x_resolver_curso__mutmut_21 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_22'] = x_resolver_curso__mutmut_22 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_23'] = x_resolver_curso__mutmut_23 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_24'] = x_resolver_curso__mutmut_24 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_25'] = x_resolver_curso__mutmut_25 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_26'] = x_resolver_curso__mutmut_26 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_27'] = x_resolver_curso__mutmut_27 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_28'] = x_resolver_curso__mutmut_28 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_29'] = x_resolver_curso__mutmut_29 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_30'] = x_resolver_curso__mutmut_30 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_31'] = x_resolver_curso__mutmut_31 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_32'] = x_resolver_curso__mutmut_32 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_33'] = x_resolver_curso__mutmut_33 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_34'] = x_resolver_curso__mutmut_34 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_35'] = x_resolver_curso__mutmut_35 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_36'] = x_resolver_curso__mutmut_36 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_37'] = x_resolver_curso__mutmut_37 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_38'] = x_resolver_curso__mutmut_38 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_39'] = x_resolver_curso__mutmut_39 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_40'] = x_resolver_curso__mutmut_40 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_41'] = x_resolver_curso__mutmut_41 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_42'] = x_resolver_curso__mutmut_42 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_43'] = x_resolver_curso__mutmut_43 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_44'] = x_resolver_curso__mutmut_44 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_45'] = x_resolver_curso__mutmut_45 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_46'] = x_resolver_curso__mutmut_46 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_47'] = x_resolver_curso__mutmut_47 # type: ignore # mutmut generated
mutants_x_resolver_curso__mutmut['x_resolver_curso__mutmut_48'] = x_resolver_curso__mutmut_48 # type: ignore # mutmut generated
