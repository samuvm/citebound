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

MAX_REINTENTOS = 2
"""Dos, y el tope no es una sugerencia.

Cada reintento es una llamada más al modelo **dentro** del presupuesto de `G-TTFT`, que tiene
1.500 ms en total y 210 ms de holgura. Un tope blando aquí se convierte aguas abajo en una
petición que no contesta, que es peor que una abstención."""


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
    if veredicto.ok:
        return Salida.RESPONDER
    if reintentos_hechos < MAX_REINTENTOS:
        return Salida.REINTENTAR
    # **Aquí es donde se sostiene la tesis.** Lo natural sería emitir el último borrador
    # «porque es lo que hay»; eso es una respuesta que no verificó, presentada como si lo
    # hubiera hecho, que es exactamente el RAG que este proyecto no quiere ser.
    return Salida.ABSTENERSE


def resolver_curso(
    intentos: Sequence[Veredicto], *, hay_fuentes: bool = True, relevancia: float | None = None
) -> Curso:
    """El curso entero a partir de los veredictos de cada borrador.

    Se para en cuanto la salida es terminal y **no mira los intentos de más**: que el grafo
    respete el presupuesto es una cosa, y que este módulo lo imponga aunque no lo respeten es
    otra. El motivo que se publica es el del último intento mirado, porque es el que describe
    por qué no hay respuesta ahora.
    """
    ultimo: Veredicto | None = None
    for hechos, veredicto in enumerate(intentos):
        ultimo = veredicto
        salida = decidir(veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes)
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
