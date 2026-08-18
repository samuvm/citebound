"""Guardia del stream · corta **en el token en que aparece**, no al final.

**La diferencia no es de rendimiento, es de promesa.** Un filtro sobre la respuesta ya escrita
detecta exactamente lo mismo, pero para entonces el usuario lleva tres frases leídas de algo que
va a retirarse. Cortar en el token de `[[REF:9]]` es lo que permite decir que el sistema **no
puede** emitir una referencia inexistente, en lugar de que la retira deprisa. `docs/RULES.md`
§2.2 resolvió el conflicto entre *streaming* y verificación dejando salir los tokens; esto es lo
que hace que esa concesión siga siendo segura.

**Dos cosas que un `if "[[REF:" in token` se come**, y las dos pasan de verdad:

- El hueco **partido entre tokens**. Un modelo emite `[[RE`, `F:`, `9`, `]]` y el hueco no está
  entero en ninguno. Por eso el guardia acumula un buffer en vez de mirar el token suelto.
- El hueco de **dos dígitos**. `[[REF:12]]` no es `[[REF:1]]` seguido de un `2`; decidir al leer
  el primer dígito daría por bueno un 12 con cinco fuentes.

**El rango lo fija lo recuperado, no la plantilla**, igual que en `domain.citation.resolver`:
con dos fuentes, el 3 es inválido aunque el prompt permita escribir hasta el 5. Los dos leen el
mismo número porque tenerlo en dos sitios es no tenerlo en ninguno.

`RULES` §3.1 pone `agent/` en TDD **prohibido** salvo este fichero, que lo **exige**: es el único
del paquete que es lógica pura con respuesta correcta, y §3.2 le pide dos propiedades.
"""

from __future__ import annotations

import re
from enum import StrEnum

__all__ = ["ABIERTO_HUECO", "Estado", "StreamGuard", "trocear_en_tokens"]

ABIERTO_HUECO = "[[REF:"
"""Cómo se abre un hueco. Es la única forma que el generador tiene de referirse a una fuente."""

_HUECO = re.compile(r"\[\[REF:(\d+)\]\]")

# Lo que puede ser el principio de un hueco todavía incompleto. Mientras el buffer encaje aquí
# hay que esperar más tokens; en cuanto deja de encajar, ya no puede llegar a ser un hueco y se
# puede soltar. Sin esto el guardia acumularía la respuesta entera por si acaso.
_PARCIAL = re.compile(r"\[(\[(R(E(F(:(\d*)?)?)?)?)?)?$")


class Estado(StrEnum):
    """`RETRACTADO` es absorbente: si un token posterior pudiera reabrirlo, la respuesta
    saldría con el hueco malo dentro."""

    ABIERTO = "abierto"
    RETRACTADO = "retractado"


def trocear_en_tokens(texto: str) -> tuple[str, ...]:
    """Parte el texto como llegaría por SSE: trozos que al concatenarse lo reproducen.

    No pretende imitar el tokenizador del modelo —eso dependería del modelo— sino dar al
    guardia una entrada troceada de forma realista. Lo que el guardia garantiza no depende de
    dónde caigan los cortes, y esa es justamente la propiedad que se comprueba con Hypothesis.
    """
    return tuple(re.findall(r"\S+\s*|\s+", texto))


class StreamGuard:
    """Consume tokens y decide, en cada uno, si la respuesta sigue viva.

    Guarda además lo emitido y los huecos vistos, y las dos cosas se usan: el nodo de reintento
    necesita saber qué se había dicho para no repetirlo, y el verificador necesita los huecos en
    orden para no tener que parsear el texto por segunda vez.
    """

    def __init__(self, max_fuentes: int) -> None:
        self.max_fuentes = max_fuentes
        self.estado = Estado.ABIERTO
        self.emitido = ""
        self.huecos: tuple[int, ...] = ()
        self._buffer = ""

    @property
    def pendiente(self) -> str:
        """Lo que el guardia retiene sin soltar, a la espera del token siguiente.

        Es siempre un prefijo dudoso de hueco —`[[RE`, `[[REF:1`— y nunca texto normal, porque
        retener texto que ya no puede ser un hueco sería un token que el usuario no ve sin
        motivo. **Tras retractar tiene que estar vacío**: si quedara algo pendiente, existiría
        un camino por el que el hueco malo o su cola llegan a salir.
        """
        return self._buffer

    def consumir(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while True:
            encontrado = _HUECO.search(self._buffer)
            if encontrado is None:
                break
            n = int(encontrado.group(1))
            if not 1 <= n <= self.max_fuentes:
                # Se emite lo de antes del hueco y **nada más**: el hueco malo no llega al
                # usuario, y lo que ya había salido queda disponible para la traza.
                self.emitido += self._buffer[: encontrado.start()]
                self._buffer = ""
                self.estado = Estado.RETRACTADO
                return self.estado
            self.huecos = (*self.huecos, n)
            self.emitido += self._buffer[: encontrado.end()]
            self._buffer = self._buffer[encontrado.end() :]

        # Se suelta todo lo que ya no puede ser el principio de un hueco. Lo que queda en el
        # buffer es exactamente el prefijo dudoso, que se resolverá con el token siguiente.
        parcial = _PARCIAL.search(self._buffer)
        corte = parcial.start() if parcial else len(self._buffer)
        self.emitido += self._buffer[:corte]
        self._buffer = self._buffer[corte:]
        return self.estado
