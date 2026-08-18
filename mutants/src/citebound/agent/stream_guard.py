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


from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated, MutantDict


class Estado(StrEnum):
    """`RETRACTADO` es absorbente: si un token posterior pudiera reabrirlo, la respuesta
    saldría con el hueco malo dentro."""

    ABIERTO = "abierto"
    RETRACTADO = "retractado"
mutants_x_trocear_en_tokens__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_trocear_en_tokens__mutmut)
def trocear_en_tokens(texto: str) -> tuple[str, ...]:
    """Parte el texto como llegaría por SSE: trozos que al concatenarse lo reproducen.

    No pretende imitar el tokenizador del modelo —eso dependería del modelo— sino dar al
    guardia una entrada troceada de forma realista. Lo que el guardia garantiza no depende de
    dónde caigan los cortes, y esa es justamente la propiedad que se comprueba con Hypothesis.
    """
    return tuple(re.findall(r"\S+\s*|\s+", texto))


def x_trocear_en_tokens__mutmut_orig(texto: str) -> tuple[str, ...]:
    """Parte el texto como llegaría por SSE: trozos que al concatenarse lo reproducen.

    No pretende imitar el tokenizador del modelo —eso dependería del modelo— sino dar al
    guardia una entrada troceada de forma realista. Lo que el guardia garantiza no depende de
    dónde caigan los cortes, y esa es justamente la propiedad que se comprueba con Hypothesis.
    """
    return tuple(re.findall(r"\S+\s*|\s+", texto))


def x_trocear_en_tokens__mutmut_1(texto: str) -> tuple[str, ...]:
    """Parte el texto como llegaría por SSE: trozos que al concatenarse lo reproducen.

    No pretende imitar el tokenizador del modelo —eso dependería del modelo— sino dar al
    guardia una entrada troceada de forma realista. Lo que el guardia garantiza no depende de
    dónde caigan los cortes, y esa es justamente la propiedad que se comprueba con Hypothesis.
    """
    return tuple(None)


def x_trocear_en_tokens__mutmut_2(texto: str) -> tuple[str, ...]:
    """Parte el texto como llegaría por SSE: trozos que al concatenarse lo reproducen.

    No pretende imitar el tokenizador del modelo —eso dependería del modelo— sino dar al
    guardia una entrada troceada de forma realista. Lo que el guardia garantiza no depende de
    dónde caigan los cortes, y esa es justamente la propiedad que se comprueba con Hypothesis.
    """
    return tuple(re.findall(None, texto))


def x_trocear_en_tokens__mutmut_3(texto: str) -> tuple[str, ...]:
    """Parte el texto como llegaría por SSE: trozos que al concatenarse lo reproducen.

    No pretende imitar el tokenizador del modelo —eso dependería del modelo— sino dar al
    guardia una entrada troceada de forma realista. Lo que el guardia garantiza no depende de
    dónde caigan los cortes, y esa es justamente la propiedad que se comprueba con Hypothesis.
    """
    return tuple(re.findall(r"\S+\s*|\s+", None))


def x_trocear_en_tokens__mutmut_4(texto: str) -> tuple[str, ...]:
    """Parte el texto como llegaría por SSE: trozos que al concatenarse lo reproducen.

    No pretende imitar el tokenizador del modelo —eso dependería del modelo— sino dar al
    guardia una entrada troceada de forma realista. Lo que el guardia garantiza no depende de
    dónde caigan los cortes, y esa es justamente la propiedad que se comprueba con Hypothesis.
    """
    return tuple(re.findall(texto))


def x_trocear_en_tokens__mutmut_5(texto: str) -> tuple[str, ...]:
    """Parte el texto como llegaría por SSE: trozos que al concatenarse lo reproducen.

    No pretende imitar el tokenizador del modelo —eso dependería del modelo— sino dar al
    guardia una entrada troceada de forma realista. Lo que el guardia garantiza no depende de
    dónde caigan los cortes, y esa es justamente la propiedad que se comprueba con Hypothesis.
    """
    return tuple(re.findall(r"\S+\s*|\s+", ))


def x_trocear_en_tokens__mutmut_6(texto: str) -> tuple[str, ...]:
    """Parte el texto como llegaría por SSE: trozos que al concatenarse lo reproducen.

    No pretende imitar el tokenizador del modelo —eso dependería del modelo— sino dar al
    guardia una entrada troceada de forma realista. Lo que el guardia garantiza no depende de
    dónde caigan los cortes, y esa es justamente la propiedad que se comprueba con Hypothesis.
    """
    return tuple(re.findall(r"XX\S+\s*|\s+XX", texto))

mutants_x_trocear_en_tokens__mutmut['_mutmut_orig'] = x_trocear_en_tokens__mutmut_orig # type: ignore # mutmut generated
mutants_x_trocear_en_tokens__mutmut['x_trocear_en_tokens__mutmut_1'] = x_trocear_en_tokens__mutmut_1 # type: ignore # mutmut generated
mutants_x_trocear_en_tokens__mutmut['x_trocear_en_tokens__mutmut_2'] = x_trocear_en_tokens__mutmut_2 # type: ignore # mutmut generated
mutants_x_trocear_en_tokens__mutmut['x_trocear_en_tokens__mutmut_3'] = x_trocear_en_tokens__mutmut_3 # type: ignore # mutmut generated
mutants_x_trocear_en_tokens__mutmut['x_trocear_en_tokens__mutmut_4'] = x_trocear_en_tokens__mutmut_4 # type: ignore # mutmut generated
mutants_x_trocear_en_tokens__mutmut['x_trocear_en_tokens__mutmut_5'] = x_trocear_en_tokens__mutmut_5 # type: ignore # mutmut generated
mutants_x_trocear_en_tokens__mutmut['x_trocear_en_tokens__mutmut_6'] = x_trocear_en_tokens__mutmut_6 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁ__init____mutmut: MutantDict = {}  # type: ignore
mutants_xǁStreamGuardǁconsumir__mutmut: MutantDict = {}  # type: ignore


class StreamGuard:
    """Consume tokens y decide, en cada uno, si la respuesta sigue viva.

    Guarda además lo emitido y los huecos vistos, y las dos cosas se usan: el nodo de reintento
    necesita saber qué se había dicho para no repetirlo, y el verificador necesita los huecos en
    orden para no tener que parsear el texto por segunda vez.
    """

    @_mutmut_mutated(mutants_xǁStreamGuardǁ__init____mutmut)
    def __init__(self, max_fuentes: int) -> None:
        self.max_fuentes = max_fuentes
        self.estado = Estado.ABIERTO
        self.emitido = ""
        self.huecos: tuple[int, ...] = ()
        self._buffer = ""

    def xǁStreamGuardǁ__init____mutmut_orig(self, max_fuentes: int) -> None:
        self.max_fuentes = max_fuentes
        self.estado = Estado.ABIERTO
        self.emitido = ""
        self.huecos: tuple[int, ...] = ()
        self._buffer = ""

    def xǁStreamGuardǁ__init____mutmut_1(self, max_fuentes: int) -> None:
        self.max_fuentes = None
        self.estado = Estado.ABIERTO
        self.emitido = ""
        self.huecos: tuple[int, ...] = ()
        self._buffer = ""

    def xǁStreamGuardǁ__init____mutmut_2(self, max_fuentes: int) -> None:
        self.max_fuentes = max_fuentes
        self.estado = None
        self.emitido = ""
        self.huecos: tuple[int, ...] = ()
        self._buffer = ""

    def xǁStreamGuardǁ__init____mutmut_3(self, max_fuentes: int) -> None:
        self.max_fuentes = max_fuentes
        self.estado = Estado.ABIERTO
        self.emitido = None
        self.huecos: tuple[int, ...] = ()
        self._buffer = ""

    def xǁStreamGuardǁ__init____mutmut_4(self, max_fuentes: int) -> None:
        self.max_fuentes = max_fuentes
        self.estado = Estado.ABIERTO
        self.emitido = "XXXX"
        self.huecos: tuple[int, ...] = ()
        self._buffer = ""

    def xǁStreamGuardǁ__init____mutmut_5(self, max_fuentes: int) -> None:
        self.max_fuentes = max_fuentes
        self.estado = Estado.ABIERTO
        self.emitido = ""
        self.huecos: tuple[int, ...] = None
        self._buffer = ""

    def xǁStreamGuardǁ__init____mutmut_6(self, max_fuentes: int) -> None:
        self.max_fuentes = max_fuentes
        self.estado = Estado.ABIERTO
        self.emitido = ""
        self.huecos: tuple[int, ...] = ()
        self._buffer = None

    def xǁStreamGuardǁ__init____mutmut_7(self, max_fuentes: int) -> None:
        self.max_fuentes = max_fuentes
        self.estado = Estado.ABIERTO
        self.emitido = ""
        self.huecos: tuple[int, ...] = ()
        self._buffer = "XXXX"

    @property
    def pendiente(self) -> str:
        """Lo que el guardia retiene sin soltar, a la espera del token siguiente.

        Es siempre un prefijo dudoso de hueco —`[[RE`, `[[REF:1`— y nunca texto normal, porque
        retener texto que ya no puede ser un hueco sería un token que el usuario no ve sin
        motivo. **Tras retractar tiene que estar vacío**: si quedara algo pendiente, existiría
        un camino por el que el hueco malo o su cola llegan a salir.
        """
        return self._buffer

    @_mutmut_mutated(mutants_xǁStreamGuardǁconsumir__mutmut)
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

    def xǁStreamGuardǁconsumir__mutmut_orig(self, token: str) -> Estado:
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

    def xǁStreamGuardǁconsumir__mutmut_1(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is not Estado.RETRACTADO:
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

    def xǁStreamGuardǁconsumir__mutmut_2(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer = token
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

    def xǁStreamGuardǁconsumir__mutmut_3(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer -= token
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

    def xǁStreamGuardǁconsumir__mutmut_4(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while False:
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

    def xǁStreamGuardǁconsumir__mutmut_5(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while True:
            encontrado = None
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

    def xǁStreamGuardǁconsumir__mutmut_6(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while True:
            encontrado = _HUECO.search(None)
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

    def xǁStreamGuardǁconsumir__mutmut_7(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while True:
            encontrado = _HUECO.search(self._buffer)
            if encontrado is not None:
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

    def xǁStreamGuardǁconsumir__mutmut_8(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while True:
            encontrado = _HUECO.search(self._buffer)
            if encontrado is None:
                return
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

    def xǁStreamGuardǁconsumir__mutmut_9(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while True:
            encontrado = _HUECO.search(self._buffer)
            if encontrado is None:
                break
            n = None
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

    def xǁStreamGuardǁconsumir__mutmut_10(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while True:
            encontrado = _HUECO.search(self._buffer)
            if encontrado is None:
                break
            n = int(None)
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

    def xǁStreamGuardǁconsumir__mutmut_11(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while True:
            encontrado = _HUECO.search(self._buffer)
            if encontrado is None:
                break
            n = int(encontrado.group(None))
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

    def xǁStreamGuardǁconsumir__mutmut_12(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while True:
            encontrado = _HUECO.search(self._buffer)
            if encontrado is None:
                break
            n = int(encontrado.group(2))
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

    def xǁStreamGuardǁconsumir__mutmut_13(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while True:
            encontrado = _HUECO.search(self._buffer)
            if encontrado is None:
                break
            n = int(encontrado.group(1))
            if 1 <= n <= self.max_fuentes:
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

    def xǁStreamGuardǁconsumir__mutmut_14(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while True:
            encontrado = _HUECO.search(self._buffer)
            if encontrado is None:
                break
            n = int(encontrado.group(1))
            if not 2 <= n <= self.max_fuentes:
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

    def xǁStreamGuardǁconsumir__mutmut_15(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while True:
            encontrado = _HUECO.search(self._buffer)
            if encontrado is None:
                break
            n = int(encontrado.group(1))
            if not 1 < n <= self.max_fuentes:
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

    def xǁStreamGuardǁconsumir__mutmut_16(self, token: str) -> Estado:
        """Devuelve el estado tras este token. Una vez `RETRACTADO`, ya no cambia."""
        if self.estado is Estado.RETRACTADO:
            return self.estado

        self._buffer += token
        while True:
            encontrado = _HUECO.search(self._buffer)
            if encontrado is None:
                break
            n = int(encontrado.group(1))
            if not 1 <= n < self.max_fuentes:
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

    def xǁStreamGuardǁconsumir__mutmut_17(self, token: str) -> Estado:
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
                self.emitido = self._buffer[: encontrado.start()]
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

    def xǁStreamGuardǁconsumir__mutmut_18(self, token: str) -> Estado:
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
                self.emitido -= self._buffer[: encontrado.start()]
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

    def xǁStreamGuardǁconsumir__mutmut_19(self, token: str) -> Estado:
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
                self._buffer = None
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

    def xǁStreamGuardǁconsumir__mutmut_20(self, token: str) -> Estado:
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
                self._buffer = "XXXX"
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

    def xǁStreamGuardǁconsumir__mutmut_21(self, token: str) -> Estado:
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
                self.estado = None
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

    def xǁStreamGuardǁconsumir__mutmut_22(self, token: str) -> Estado:
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
            self.huecos = None
            self.emitido += self._buffer[: encontrado.end()]
            self._buffer = self._buffer[encontrado.end() :]

        # Se suelta todo lo que ya no puede ser el principio de un hueco. Lo que queda en el
        # buffer es exactamente el prefijo dudoso, que se resolverá con el token siguiente.
        parcial = _PARCIAL.search(self._buffer)
        corte = parcial.start() if parcial else len(self._buffer)
        self.emitido += self._buffer[:corte]
        self._buffer = self._buffer[corte:]
        return self.estado

    def xǁStreamGuardǁconsumir__mutmut_23(self, token: str) -> Estado:
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
            self.emitido = self._buffer[: encontrado.end()]
            self._buffer = self._buffer[encontrado.end() :]

        # Se suelta todo lo que ya no puede ser el principio de un hueco. Lo que queda en el
        # buffer es exactamente el prefijo dudoso, que se resolverá con el token siguiente.
        parcial = _PARCIAL.search(self._buffer)
        corte = parcial.start() if parcial else len(self._buffer)
        self.emitido += self._buffer[:corte]
        self._buffer = self._buffer[corte:]
        return self.estado

    def xǁStreamGuardǁconsumir__mutmut_24(self, token: str) -> Estado:
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
            self.emitido -= self._buffer[: encontrado.end()]
            self._buffer = self._buffer[encontrado.end() :]

        # Se suelta todo lo que ya no puede ser el principio de un hueco. Lo que queda en el
        # buffer es exactamente el prefijo dudoso, que se resolverá con el token siguiente.
        parcial = _PARCIAL.search(self._buffer)
        corte = parcial.start() if parcial else len(self._buffer)
        self.emitido += self._buffer[:corte]
        self._buffer = self._buffer[corte:]
        return self.estado

    def xǁStreamGuardǁconsumir__mutmut_25(self, token: str) -> Estado:
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
            self._buffer = None

        # Se suelta todo lo que ya no puede ser el principio de un hueco. Lo que queda en el
        # buffer es exactamente el prefijo dudoso, que se resolverá con el token siguiente.
        parcial = _PARCIAL.search(self._buffer)
        corte = parcial.start() if parcial else len(self._buffer)
        self.emitido += self._buffer[:corte]
        self._buffer = self._buffer[corte:]
        return self.estado

    def xǁStreamGuardǁconsumir__mutmut_26(self, token: str) -> Estado:
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
        parcial = None
        corte = parcial.start() if parcial else len(self._buffer)
        self.emitido += self._buffer[:corte]
        self._buffer = self._buffer[corte:]
        return self.estado

    def xǁStreamGuardǁconsumir__mutmut_27(self, token: str) -> Estado:
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
        parcial = _PARCIAL.search(None)
        corte = parcial.start() if parcial else len(self._buffer)
        self.emitido += self._buffer[:corte]
        self._buffer = self._buffer[corte:]
        return self.estado

    def xǁStreamGuardǁconsumir__mutmut_28(self, token: str) -> Estado:
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
        corte = None
        self.emitido += self._buffer[:corte]
        self._buffer = self._buffer[corte:]
        return self.estado

    def xǁStreamGuardǁconsumir__mutmut_29(self, token: str) -> Estado:
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
        self.emitido = self._buffer[:corte]
        self._buffer = self._buffer[corte:]
        return self.estado

    def xǁStreamGuardǁconsumir__mutmut_30(self, token: str) -> Estado:
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
        self.emitido -= self._buffer[:corte]
        self._buffer = self._buffer[corte:]
        return self.estado

    def xǁStreamGuardǁconsumir__mutmut_31(self, token: str) -> Estado:
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
        self._buffer = None
        return self.estado

mutants_xǁStreamGuardǁ__init____mutmut['_mutmut_orig'] = StreamGuard.xǁStreamGuardǁ__init____mutmut_orig # type: ignore # mutmut generated
mutants_xǁStreamGuardǁ__init____mutmut['xǁStreamGuardǁ__init____mutmut_1'] = StreamGuard.xǁStreamGuardǁ__init____mutmut_1 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁ__init____mutmut['xǁStreamGuardǁ__init____mutmut_2'] = StreamGuard.xǁStreamGuardǁ__init____mutmut_2 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁ__init____mutmut['xǁStreamGuardǁ__init____mutmut_3'] = StreamGuard.xǁStreamGuardǁ__init____mutmut_3 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁ__init____mutmut['xǁStreamGuardǁ__init____mutmut_4'] = StreamGuard.xǁStreamGuardǁ__init____mutmut_4 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁ__init____mutmut['xǁStreamGuardǁ__init____mutmut_5'] = StreamGuard.xǁStreamGuardǁ__init____mutmut_5 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁ__init____mutmut['xǁStreamGuardǁ__init____mutmut_6'] = StreamGuard.xǁStreamGuardǁ__init____mutmut_6 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁ__init____mutmut['xǁStreamGuardǁ__init____mutmut_7'] = StreamGuard.xǁStreamGuardǁ__init____mutmut_7 # type: ignore # mutmut generated

mutants_xǁStreamGuardǁconsumir__mutmut['_mutmut_orig'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_orig # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_1'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_1 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_2'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_2 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_3'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_3 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_4'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_4 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_5'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_5 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_6'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_6 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_7'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_7 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_8'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_8 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_9'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_9 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_10'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_10 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_11'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_11 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_12'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_12 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_13'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_13 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_14'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_14 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_15'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_15 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_16'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_16 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_17'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_17 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_18'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_18 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_19'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_19 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_20'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_20 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_21'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_21 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_22'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_22 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_23'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_23 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_24'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_24 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_25'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_25 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_26'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_26 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_27'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_27 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_28'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_28 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_29'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_29 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_30'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_30 # type: ignore # mutmut generated
mutants_xǁStreamGuardǁconsumir__mutmut['xǁStreamGuardǁconsumir__mutmut_31'] = StreamGuard.xǁStreamGuardǁconsumir__mutmut_31 # type: ignore # mutmut generated
