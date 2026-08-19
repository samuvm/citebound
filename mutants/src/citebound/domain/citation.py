"""Cita cerrada · la traducción de `[[REF:n]]` a `LegalRef`, y la verificación literal.

**Es la tesis del proyecto hecha código.** Un RAG normal deja que el modelo escriba la
referencia, y entonces «según el artículo 47.3» son tokens que predice igual que el resto de la
frase: si lo recuperado era el 45, nada en el sistema se entera. Aquí el modelo solo puede
escribir un hueco numerado sobre lo que la búsqueda sí trajo, y quien lo traduce es este módulo.

Tres consecuencias, y ninguna depende de que el modelo se porte bien:

**Citar un artículo inexistente es inexpresable.** La referencia sale de la fuente recuperada,
no de lo que el modelo escriba. Un apartado inventado sobre un artículo real —`art34.7` cuando
el 34 no tiene siete apartados— no se detecta: **no se puede escribir**.

**La verificación es una comparación de cadenas.** Sin LLM, sin coste, sin opinión. Un juez diría
que «se contara» y «se contará» significan lo mismo; una cita literal o lo es o no lo es, y por
eso esto no se delega (`RULES` R14: lo verificable deterministamente no va a un juez).

**Media respuesta verificada no es media respuesta buena.** Una cita correcta junto a una
inventada cuenta como fallo entero — está en `docs/CONTRACTS/retrieval-metrics.md` — porque el
usuario lee la respuesta como verificada entera.

`domain/` no importa I/O ni SDKs (R6), así que aquí no entra `Recuperado`: lo que llega es una
`Fuente`, que es una ref y su texto. Quien la construye es `agent/graph.py`.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from citebound.domain.legalref import LegalRef

__all__ = [
    "MAX_FUENTES",
    "MIN_CARACTERES_QUOTE",
    "Cita",
    "CitaError",
    "Fuente",
    "Motivo",
    "Veredicto",
    "normalizar_para_cotejo",
    "parsear_borrador",
    "resolver",
    "verificar",
]

MAX_FUENTES = 5
"""Cuántas fuentes se le ofrecen al generador, y por tanto el mayor `n` expresable.

Es el mismo 5 del `top-5` del recuperador y del `PEDIDOS` del reordenador, y tenerlo en un solo
sitio es lo que impide que el guardia del stream y el recuperador discrepen sobre cuál es el
rango. **El rango real, sin embargo, lo fija lo recuperado**: si la búsqueda trajo dos, el 3 no
existe aunque la plantilla permita escribirlo."""

MIN_CARACTERES_QUOTE = 12
"""Por debajo de esto un fragmento no cita, coincide.

«de» está literalmente en casi cualquier artículo del corpus. Sin este mínimo, `G-QUOTE-LIT`
—umbral `== 1,00`, sin propuesta admisible— se podría sostener con citas de dos letras y el 1,00
no significaría nada. Doce caracteres es corto para una cita jurídica y largo para una
coincidencia; si algún día estorba, se cambia con el número delante."""

_ESPACIOS = re.compile(r"\s+")

MARCA_CITAS = "CITAS"
"""La línea que separa la respuesta de sus citas. Va en el prompt y se lee aquí, y tenerla en
una constante es lo que impide que las dos se separen sin que nadie lo note."""

_LINEA_CITA = re.compile(r"\[\[REF:(\d+)\]\]\s*(.*)$")

# Los pares que se aceptan alrededor de un quote. El prompt pide guillemets; el modelo devuelve
# lo que le sale, y las tres formas significan lo mismo para quien lee.
_COMILLAS = (("\u00ab", "\u00bb"), ("\u201c", "\u201d"), ('"', '"'), ("'", "'"))

# Comillas y guiones que hay que plegar, **por punto de código y no por el carácter**.
#
# Es una tabla cuyo objeto es distinguir homoglifos, así que escribir el carácter la volvería
# ilegible en cualquier editor que no muestre la diferencia — y un lookalike copiado por error
# sería invisible justo aquí. El nombre va al lado para que se pueda leer.
#
# Salen de sitios reales: el BOE escribe comillas rectas y los modelos devuelven tipográficas;
# un guion largo aparece al copiar de un PDF. Sin plegarlos, `G-QUOTE-LIT` —umbral `== 1,00`,
# sin propuesta admisible— bajaría por tipografía y no por una cita falsa.
_PLIEGUES = str.maketrans(
    {
        "\u201c": '"',  # LEFT DOUBLE QUOTATION MARK
        "\u201d": '"',  # RIGHT DOUBLE QUOTATION MARK
        "\u201e": '"',  # DOUBLE LOW-9 QUOTATION MARK
        "\u00ab": '"',  # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
        "\u00bb": '"',  # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
        "\u2018": "'",  # LEFT SINGLE QUOTATION MARK
        "\u2019": "'",  # RIGHT SINGLE QUOTATION MARK
        "\u201a": "'",  # SINGLE LOW-9 QUOTATION MARK
        "\u2010": "-",  # HYPHEN
        "\u2011": "-",  # NON-BREAKING HYPHEN · sobrevive a NFKC, y por eso está aquí
        "\u2012": "-",  # FIGURE DASH
        "\u2013": "-",  # EN DASH
        "\u2014": "-",  # EM DASH
        "\u2015": "-",  # HORIZONTAL BAR
        "\u2212": "-",  # MINUS SIGN
    }
)


from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated, MutantDict


class CitaError(ValueError):
    """El hueco no se puede resolver a ninguna referencia recuperada."""


class Motivo(StrEnum):
    """Por qué se rechaza una respuesta. **El motivo importa tanto como el rechazo**: fuera de
    rango significa que el modelo se saltó el formato y se ve venir en el stream; un quote no
    literal solo se sabe al final, con el texto delante."""

    FUERA_DE_RANGO = "fuera_de_rango"
    QUOTE_NO_LITERAL = "quote_no_literal"
    QUOTE_VACIO = "quote_vacio"
    QUOTE_DEMASIADO_CORTO = "quote_demasiado_corto"
    SIN_CITAS = "sin_citas"


@dataclass(frozen=True, slots=True)
class Fuente:
    """Una de las opciones que se le ofrecen al generador: su referencia y su texto."""

    ref: LegalRef
    texto: str


@dataclass(frozen=True, slots=True)
class Cita:
    """Lo que el modelo escribe: un hueco y el fragmento que dice estar citando."""

    n: int
    quote: str


@dataclass(frozen=True, slots=True)
class Veredicto:
    """`ok` con las refs resueltas, o el motivo por el que la respuesta no sale."""

    ok: bool
    refs: tuple[LegalRef, ...] = ()
    motivo: Motivo | None = None
mutants_x_normalizar_para_cotejo__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_normalizar_para_cotejo__mutmut)
def normalizar_para_cotejo(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize("NFKC", texto).translate(_PLIEGUES)
    return _ESPACIOS.sub(" ", plegado).strip()


def x_normalizar_para_cotejo__mutmut_orig(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize("NFKC", texto).translate(_PLIEGUES)
    return _ESPACIOS.sub(" ", plegado).strip()


def x_normalizar_para_cotejo__mutmut_1(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = None
    return _ESPACIOS.sub(" ", plegado).strip()


def x_normalizar_para_cotejo__mutmut_2(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize("NFKC", texto).translate(None)
    return _ESPACIOS.sub(" ", plegado).strip()


def x_normalizar_para_cotejo__mutmut_3(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize(None, texto).translate(_PLIEGUES)
    return _ESPACIOS.sub(" ", plegado).strip()


def x_normalizar_para_cotejo__mutmut_4(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize("NFKC", None).translate(_PLIEGUES)
    return _ESPACIOS.sub(" ", plegado).strip()


def x_normalizar_para_cotejo__mutmut_5(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize(texto).translate(_PLIEGUES)
    return _ESPACIOS.sub(" ", plegado).strip()


def x_normalizar_para_cotejo__mutmut_6(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize("NFKC", ).translate(_PLIEGUES)
    return _ESPACIOS.sub(" ", plegado).strip()


def x_normalizar_para_cotejo__mutmut_7(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize("XXNFKCXX", texto).translate(_PLIEGUES)
    return _ESPACIOS.sub(" ", plegado).strip()


def x_normalizar_para_cotejo__mutmut_8(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize("nfkc", texto).translate(_PLIEGUES)
    return _ESPACIOS.sub(" ", plegado).strip()


def x_normalizar_para_cotejo__mutmut_9(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize("NFKC", texto).translate(_PLIEGUES)
    return _ESPACIOS.sub(None, plegado).strip()


def x_normalizar_para_cotejo__mutmut_10(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize("NFKC", texto).translate(_PLIEGUES)
    return _ESPACIOS.sub(" ", None).strip()


def x_normalizar_para_cotejo__mutmut_11(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize("NFKC", texto).translate(_PLIEGUES)
    return _ESPACIOS.sub(plegado).strip()


def x_normalizar_para_cotejo__mutmut_12(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize("NFKC", texto).translate(_PLIEGUES)
    return _ESPACIOS.sub(" ", ).strip()


def x_normalizar_para_cotejo__mutmut_13(texto: str) -> str:
    """La normalización declarada en `docs/GOALS.yaml`: NFKC, espacios, comillas y guiones.

    **NFKC y no NFC**, al revés que `ingest.chunking.normalizar_contenido`, y la diferencia es
    deliberada: aquí se compara **lo que escribió un modelo** contra lo que dice el corpus, y
    ahí un carácter de compatibilidad —`ﬁ` por `fi`— es el mismo texto. En el troceador el hash
    **identifica** el chunk para otro proyecto, y plegar cambiaría la identidad de algo que
    nadie ha editado.

    Idempotente, y hace falta que lo sea: verificar dos veces la misma cita no puede dar dos
    respuestas.
    """
    plegado = unicodedata.normalize("NFKC", texto).translate(_PLIEGUES)
    return _ESPACIOS.sub("XX XX", plegado).strip()

mutants_x_normalizar_para_cotejo__mutmut['_mutmut_orig'] = x_normalizar_para_cotejo__mutmut_orig # type: ignore # mutmut generated
mutants_x_normalizar_para_cotejo__mutmut['x_normalizar_para_cotejo__mutmut_1'] = x_normalizar_para_cotejo__mutmut_1 # type: ignore # mutmut generated
mutants_x_normalizar_para_cotejo__mutmut['x_normalizar_para_cotejo__mutmut_2'] = x_normalizar_para_cotejo__mutmut_2 # type: ignore # mutmut generated
mutants_x_normalizar_para_cotejo__mutmut['x_normalizar_para_cotejo__mutmut_3'] = x_normalizar_para_cotejo__mutmut_3 # type: ignore # mutmut generated
mutants_x_normalizar_para_cotejo__mutmut['x_normalizar_para_cotejo__mutmut_4'] = x_normalizar_para_cotejo__mutmut_4 # type: ignore # mutmut generated
mutants_x_normalizar_para_cotejo__mutmut['x_normalizar_para_cotejo__mutmut_5'] = x_normalizar_para_cotejo__mutmut_5 # type: ignore # mutmut generated
mutants_x_normalizar_para_cotejo__mutmut['x_normalizar_para_cotejo__mutmut_6'] = x_normalizar_para_cotejo__mutmut_6 # type: ignore # mutmut generated
mutants_x_normalizar_para_cotejo__mutmut['x_normalizar_para_cotejo__mutmut_7'] = x_normalizar_para_cotejo__mutmut_7 # type: ignore # mutmut generated
mutants_x_normalizar_para_cotejo__mutmut['x_normalizar_para_cotejo__mutmut_8'] = x_normalizar_para_cotejo__mutmut_8 # type: ignore # mutmut generated
mutants_x_normalizar_para_cotejo__mutmut['x_normalizar_para_cotejo__mutmut_9'] = x_normalizar_para_cotejo__mutmut_9 # type: ignore # mutmut generated
mutants_x_normalizar_para_cotejo__mutmut['x_normalizar_para_cotejo__mutmut_10'] = x_normalizar_para_cotejo__mutmut_10 # type: ignore # mutmut generated
mutants_x_normalizar_para_cotejo__mutmut['x_normalizar_para_cotejo__mutmut_11'] = x_normalizar_para_cotejo__mutmut_11 # type: ignore # mutmut generated
mutants_x_normalizar_para_cotejo__mutmut['x_normalizar_para_cotejo__mutmut_12'] = x_normalizar_para_cotejo__mutmut_12 # type: ignore # mutmut generated
mutants_x_normalizar_para_cotejo__mutmut['x_normalizar_para_cotejo__mutmut_13'] = x_normalizar_para_cotejo__mutmut_13 # type: ignore # mutmut generated
mutants_x_resolver__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_resolver__mutmut)
def resolver(cita: Cita, fuentes: Sequence[Fuente]) -> LegalRef:
    """`n` → la `LegalRef` de su fuente. **Aquí es donde el modelo pierde el control.**

    El rango lo fija lo recuperado y no la plantilla: con dos fuentes, el 3 es inválido aunque
    al modelo se le permita escribir hasta el 5. Y el 0 se rechaza explícitamente porque en
    Python indexaría al último elemento — un error de índice que citaría un artículo que nadie
    eligió, silenciosamente.
    """
    if not 1 <= cita.n <= len(fuentes):
        raise CitaError(
            f"[[REF:{cita.n}]] fuera de rango: se recuperaron {len(fuentes)} fuentes, "
            f"así que solo 1..{len(fuentes)} existen"
        )
    return fuentes[cita.n - 1].ref


def x_resolver__mutmut_orig(cita: Cita, fuentes: Sequence[Fuente]) -> LegalRef:
    """`n` → la `LegalRef` de su fuente. **Aquí es donde el modelo pierde el control.**

    El rango lo fija lo recuperado y no la plantilla: con dos fuentes, el 3 es inválido aunque
    al modelo se le permita escribir hasta el 5. Y el 0 se rechaza explícitamente porque en
    Python indexaría al último elemento — un error de índice que citaría un artículo que nadie
    eligió, silenciosamente.
    """
    if not 1 <= cita.n <= len(fuentes):
        raise CitaError(
            f"[[REF:{cita.n}]] fuera de rango: se recuperaron {len(fuentes)} fuentes, "
            f"así que solo 1..{len(fuentes)} existen"
        )
    return fuentes[cita.n - 1].ref


def x_resolver__mutmut_1(cita: Cita, fuentes: Sequence[Fuente]) -> LegalRef:
    """`n` → la `LegalRef` de su fuente. **Aquí es donde el modelo pierde el control.**

    El rango lo fija lo recuperado y no la plantilla: con dos fuentes, el 3 es inválido aunque
    al modelo se le permita escribir hasta el 5. Y el 0 se rechaza explícitamente porque en
    Python indexaría al último elemento — un error de índice que citaría un artículo que nadie
    eligió, silenciosamente.
    """
    if 1 <= cita.n <= len(fuentes):
        raise CitaError(
            f"[[REF:{cita.n}]] fuera de rango: se recuperaron {len(fuentes)} fuentes, "
            f"así que solo 1..{len(fuentes)} existen"
        )
    return fuentes[cita.n - 1].ref


def x_resolver__mutmut_2(cita: Cita, fuentes: Sequence[Fuente]) -> LegalRef:
    """`n` → la `LegalRef` de su fuente. **Aquí es donde el modelo pierde el control.**

    El rango lo fija lo recuperado y no la plantilla: con dos fuentes, el 3 es inválido aunque
    al modelo se le permita escribir hasta el 5. Y el 0 se rechaza explícitamente porque en
    Python indexaría al último elemento — un error de índice que citaría un artículo que nadie
    eligió, silenciosamente.
    """
    if not 2 <= cita.n <= len(fuentes):
        raise CitaError(
            f"[[REF:{cita.n}]] fuera de rango: se recuperaron {len(fuentes)} fuentes, "
            f"así que solo 1..{len(fuentes)} existen"
        )
    return fuentes[cita.n - 1].ref


def x_resolver__mutmut_3(cita: Cita, fuentes: Sequence[Fuente]) -> LegalRef:
    """`n` → la `LegalRef` de su fuente. **Aquí es donde el modelo pierde el control.**

    El rango lo fija lo recuperado y no la plantilla: con dos fuentes, el 3 es inválido aunque
    al modelo se le permita escribir hasta el 5. Y el 0 se rechaza explícitamente porque en
    Python indexaría al último elemento — un error de índice que citaría un artículo que nadie
    eligió, silenciosamente.
    """
    if not 1 < cita.n <= len(fuentes):
        raise CitaError(
            f"[[REF:{cita.n}]] fuera de rango: se recuperaron {len(fuentes)} fuentes, "
            f"así que solo 1..{len(fuentes)} existen"
        )
    return fuentes[cita.n - 1].ref


def x_resolver__mutmut_4(cita: Cita, fuentes: Sequence[Fuente]) -> LegalRef:
    """`n` → la `LegalRef` de su fuente. **Aquí es donde el modelo pierde el control.**

    El rango lo fija lo recuperado y no la plantilla: con dos fuentes, el 3 es inválido aunque
    al modelo se le permita escribir hasta el 5. Y el 0 se rechaza explícitamente porque en
    Python indexaría al último elemento — un error de índice que citaría un artículo que nadie
    eligió, silenciosamente.
    """
    if not 1 <= cita.n < len(fuentes):
        raise CitaError(
            f"[[REF:{cita.n}]] fuera de rango: se recuperaron {len(fuentes)} fuentes, "
            f"así que solo 1..{len(fuentes)} existen"
        )
    return fuentes[cita.n - 1].ref


def x_resolver__mutmut_5(cita: Cita, fuentes: Sequence[Fuente]) -> LegalRef:
    """`n` → la `LegalRef` de su fuente. **Aquí es donde el modelo pierde el control.**

    El rango lo fija lo recuperado y no la plantilla: con dos fuentes, el 3 es inválido aunque
    al modelo se le permita escribir hasta el 5. Y el 0 se rechaza explícitamente porque en
    Python indexaría al último elemento — un error de índice que citaría un artículo que nadie
    eligió, silenciosamente.
    """
    if not 1 <= cita.n <= len(fuentes):
        raise CitaError(
            None
        )
    return fuentes[cita.n - 1].ref


def x_resolver__mutmut_6(cita: Cita, fuentes: Sequence[Fuente]) -> LegalRef:
    """`n` → la `LegalRef` de su fuente. **Aquí es donde el modelo pierde el control.**

    El rango lo fija lo recuperado y no la plantilla: con dos fuentes, el 3 es inválido aunque
    al modelo se le permita escribir hasta el 5. Y el 0 se rechaza explícitamente porque en
    Python indexaría al último elemento — un error de índice que citaría un artículo que nadie
    eligió, silenciosamente.
    """
    if not 1 <= cita.n <= len(fuentes):
        raise CitaError(
            f"[[REF:{cita.n}]] fuera de rango: se recuperaron {len(fuentes)} fuentes, "
            f"así que solo 1..{len(fuentes)} existen"
        )
    return fuentes[cita.n + 1].ref


def x_resolver__mutmut_7(cita: Cita, fuentes: Sequence[Fuente]) -> LegalRef:
    """`n` → la `LegalRef` de su fuente. **Aquí es donde el modelo pierde el control.**

    El rango lo fija lo recuperado y no la plantilla: con dos fuentes, el 3 es inválido aunque
    al modelo se le permita escribir hasta el 5. Y el 0 se rechaza explícitamente porque en
    Python indexaría al último elemento — un error de índice que citaría un artículo que nadie
    eligió, silenciosamente.
    """
    if not 1 <= cita.n <= len(fuentes):
        raise CitaError(
            f"[[REF:{cita.n}]] fuera de rango: se recuperaron {len(fuentes)} fuentes, "
            f"así que solo 1..{len(fuentes)} existen"
        )
    return fuentes[cita.n - 2].ref

mutants_x_resolver__mutmut['_mutmut_orig'] = x_resolver__mutmut_orig # type: ignore # mutmut generated
mutants_x_resolver__mutmut['x_resolver__mutmut_1'] = x_resolver__mutmut_1 # type: ignore # mutmut generated
mutants_x_resolver__mutmut['x_resolver__mutmut_2'] = x_resolver__mutmut_2 # type: ignore # mutmut generated
mutants_x_resolver__mutmut['x_resolver__mutmut_3'] = x_resolver__mutmut_3 # type: ignore # mutmut generated
mutants_x_resolver__mutmut['x_resolver__mutmut_4'] = x_resolver__mutmut_4 # type: ignore # mutmut generated
mutants_x_resolver__mutmut['x_resolver__mutmut_5'] = x_resolver__mutmut_5 # type: ignore # mutmut generated
mutants_x_resolver__mutmut['x_resolver__mutmut_6'] = x_resolver__mutmut_6 # type: ignore # mutmut generated
mutants_x_resolver__mutmut['x_resolver__mutmut_7'] = x_resolver__mutmut_7 # type: ignore # mutmut generated
mutants_x_verificar__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_verificar__mutmut)
def verificar(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_orig(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_1(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_2(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=None, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_3(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=None)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_4(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_5(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, )

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_6(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=True, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_7(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = None
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_8(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = None
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_9(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(None, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_10(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, None)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_11(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_12(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, )
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_13(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=None, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_14(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=None)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_15(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_16(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, )

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_17(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=True, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_18(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = None
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_19(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(None)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_20(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_21(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=None, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_22(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=None)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_23(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_24(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, )
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_25(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=True, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_26(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) <= MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_27(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=None, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_28(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=None)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_29(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_30(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, )
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_31(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=True, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_32(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_33(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(None):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_34(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n + 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_35(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 2].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_36(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=None, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_37(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=None)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_38(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_39(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, )
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_40(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=True, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_41(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(None)

    return Veredicto(ok=True, refs=tuple(refs))


def x_verificar__mutmut_42(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=None, refs=tuple(refs))


def x_verificar__mutmut_43(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=None)


def x_verificar__mutmut_44(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(refs=tuple(refs))


def x_verificar__mutmut_45(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, )


def x_verificar__mutmut_46(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=False, refs=tuple(refs))


def x_verificar__mutmut_47(citas: Sequence[Cita], fuentes: Sequence[Fuente]) -> Veredicto:
    """El veredicto de la respuesta entera: o salen todas las citas, o no sale ninguna.

    Se para en la primera que falla y devuelve su motivo, porque la reacción depende de él:
    fuera de rango se retracta y se reintenta; sin citas se abstiene.
    """
    if not citas:
        return Veredicto(ok=False, motivo=Motivo.SIN_CITAS)

    refs: list[LegalRef] = []
    for cita in citas:
        try:
            ref = resolver(cita, fuentes)
        except CitaError:
            return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)

        quote = normalizar_para_cotejo(cita.quote)
        if not quote:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_VACIO)
        if len(quote) < MIN_CARACTERES_QUOTE:
            return Veredicto(ok=False, motivo=Motivo.QUOTE_DEMASIADO_CORTO)
        # Contra SU fuente y no contra el corpus entero: un fragmento que está en otro artículo
        # de los recuperados es una cita mal atribuida, y cotejar contra todo la daría por buena.
        if quote not in normalizar_para_cotejo(fuentes[cita.n - 1].texto):
            return Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
        refs.append(ref)

    return Veredicto(ok=True, refs=tuple(None))

mutants_x_verificar__mutmut['_mutmut_orig'] = x_verificar__mutmut_orig # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_1'] = x_verificar__mutmut_1 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_2'] = x_verificar__mutmut_2 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_3'] = x_verificar__mutmut_3 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_4'] = x_verificar__mutmut_4 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_5'] = x_verificar__mutmut_5 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_6'] = x_verificar__mutmut_6 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_7'] = x_verificar__mutmut_7 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_8'] = x_verificar__mutmut_8 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_9'] = x_verificar__mutmut_9 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_10'] = x_verificar__mutmut_10 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_11'] = x_verificar__mutmut_11 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_12'] = x_verificar__mutmut_12 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_13'] = x_verificar__mutmut_13 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_14'] = x_verificar__mutmut_14 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_15'] = x_verificar__mutmut_15 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_16'] = x_verificar__mutmut_16 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_17'] = x_verificar__mutmut_17 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_18'] = x_verificar__mutmut_18 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_19'] = x_verificar__mutmut_19 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_20'] = x_verificar__mutmut_20 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_21'] = x_verificar__mutmut_21 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_22'] = x_verificar__mutmut_22 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_23'] = x_verificar__mutmut_23 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_24'] = x_verificar__mutmut_24 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_25'] = x_verificar__mutmut_25 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_26'] = x_verificar__mutmut_26 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_27'] = x_verificar__mutmut_27 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_28'] = x_verificar__mutmut_28 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_29'] = x_verificar__mutmut_29 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_30'] = x_verificar__mutmut_30 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_31'] = x_verificar__mutmut_31 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_32'] = x_verificar__mutmut_32 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_33'] = x_verificar__mutmut_33 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_34'] = x_verificar__mutmut_34 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_35'] = x_verificar__mutmut_35 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_36'] = x_verificar__mutmut_36 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_37'] = x_verificar__mutmut_37 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_38'] = x_verificar__mutmut_38 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_39'] = x_verificar__mutmut_39 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_40'] = x_verificar__mutmut_40 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_41'] = x_verificar__mutmut_41 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_42'] = x_verificar__mutmut_42 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_43'] = x_verificar__mutmut_43 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_44'] = x_verificar__mutmut_44 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_45'] = x_verificar__mutmut_45 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_46'] = x_verificar__mutmut_46 # type: ignore # mutmut generated
mutants_x_verificar__mutmut['x_verificar__mutmut_47'] = x_verificar__mutmut_47 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_parsear_borrador__mutmut)
def parsear_borrador(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_orig(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_1(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = None
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_2(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = None
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_3(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next(None, None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_4(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next(None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_5(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), )
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_6(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(None) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_7(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() != MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_8(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is not None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_9(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = None
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_10(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=None, quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_11(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=None)
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_12(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_13(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), )
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_14(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(None), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_15(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(None)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_16(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(2)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_17(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(None))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_18(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(None)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_19(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(3)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_20(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte - 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_21(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 2 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_22(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(None)) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_23(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_24(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(None).strip(), tuple(citas)


def x_parsear_borrador__mutmut_25(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "XX\nXX".join(lineas[:corte]).strip(), tuple(citas)


def x_parsear_borrador__mutmut_26(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """`(respuesta, citas)` a partir de lo que escribió el modelo.

    **Es la frontera entre lo que el modelo escribe y lo que el verificador comprueba**, y por
    eso es tolerante en la forma y estricta en el fondo: acepta tres tipos de comillas y un
    quote sin ellas, porque pelearse con el prompt por tipografía sale más caro que aceptarla;
    pero no inventa un bloque de citas que no esté. Sin bloque salen cero citas, el verificador
    dice `SIN_CITAS` y eso dispara un reintento con el motivo delante — que es mejor que una
    abstención sin explicar.

    El marcador `CITAS` es **una línea entera y solo eso**, para que «según las CITAS del
    reglamento» dentro de la respuesta no abra el bloque.
    """
    lineas = borrador.splitlines()
    corte = next((i for i, x in enumerate(lineas) if x.strip() == MARCA_CITAS), None)
    if corte is None:
        return borrador.strip(), ()

    citas = [
        Cita(n=int(encontrado.group(1)), quote=_desentrecomillar(encontrado.group(2)))
        for linea in lineas[corte + 1 :]
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(lineas[:corte]).strip(), tuple(None)

mutants_x_parsear_borrador__mutmut['_mutmut_orig'] = x_parsear_borrador__mutmut_orig # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_1'] = x_parsear_borrador__mutmut_1 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_2'] = x_parsear_borrador__mutmut_2 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_3'] = x_parsear_borrador__mutmut_3 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_4'] = x_parsear_borrador__mutmut_4 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_5'] = x_parsear_borrador__mutmut_5 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_6'] = x_parsear_borrador__mutmut_6 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_7'] = x_parsear_borrador__mutmut_7 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_8'] = x_parsear_borrador__mutmut_8 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_9'] = x_parsear_borrador__mutmut_9 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_10'] = x_parsear_borrador__mutmut_10 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_11'] = x_parsear_borrador__mutmut_11 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_12'] = x_parsear_borrador__mutmut_12 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_13'] = x_parsear_borrador__mutmut_13 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_14'] = x_parsear_borrador__mutmut_14 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_15'] = x_parsear_borrador__mutmut_15 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_16'] = x_parsear_borrador__mutmut_16 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_17'] = x_parsear_borrador__mutmut_17 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_18'] = x_parsear_borrador__mutmut_18 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_19'] = x_parsear_borrador__mutmut_19 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_20'] = x_parsear_borrador__mutmut_20 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_21'] = x_parsear_borrador__mutmut_21 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_22'] = x_parsear_borrador__mutmut_22 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_23'] = x_parsear_borrador__mutmut_23 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_24'] = x_parsear_borrador__mutmut_24 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_25'] = x_parsear_borrador__mutmut_25 # type: ignore # mutmut generated
mutants_x_parsear_borrador__mutmut['x_parsear_borrador__mutmut_26'] = x_parsear_borrador__mutmut_26 # type: ignore # mutmut generated
mutants_x__desentrecomillar__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x__desentrecomillar__mutmut)
def _desentrecomillar(quote: str) -> str:
    """Quita el par de comillas exterior, sea cual sea. Si no lo hay, devuelve el texto tal cual.

    Tomarlo entero y dejar que decida la verificación literal es deliberado: descartar aquí una
    línea mal entrecomillada convertiría un fallo de formato en una abstención sin motivo claro,
    y el motivo es lo que hace útil a una abstención.
    """
    limpio = quote.strip()
    for abre, cierra in _COMILLAS:
        if limpio.startswith(abre) and limpio.endswith(cierra) and len(limpio) >= 2:
            return limpio[len(abre) : -len(cierra)].strip()
    return limpio


def x__desentrecomillar__mutmut_orig(quote: str) -> str:
    """Quita el par de comillas exterior, sea cual sea. Si no lo hay, devuelve el texto tal cual.

    Tomarlo entero y dejar que decida la verificación literal es deliberado: descartar aquí una
    línea mal entrecomillada convertiría un fallo de formato en una abstención sin motivo claro,
    y el motivo es lo que hace útil a una abstención.
    """
    limpio = quote.strip()
    for abre, cierra in _COMILLAS:
        if limpio.startswith(abre) and limpio.endswith(cierra) and len(limpio) >= 2:
            return limpio[len(abre) : -len(cierra)].strip()
    return limpio


def x__desentrecomillar__mutmut_1(quote: str) -> str:
    """Quita el par de comillas exterior, sea cual sea. Si no lo hay, devuelve el texto tal cual.

    Tomarlo entero y dejar que decida la verificación literal es deliberado: descartar aquí una
    línea mal entrecomillada convertiría un fallo de formato en una abstención sin motivo claro,
    y el motivo es lo que hace útil a una abstención.
    """
    limpio = None
    for abre, cierra in _COMILLAS:
        if limpio.startswith(abre) and limpio.endswith(cierra) and len(limpio) >= 2:
            return limpio[len(abre) : -len(cierra)].strip()
    return limpio


def x__desentrecomillar__mutmut_2(quote: str) -> str:
    """Quita el par de comillas exterior, sea cual sea. Si no lo hay, devuelve el texto tal cual.

    Tomarlo entero y dejar que decida la verificación literal es deliberado: descartar aquí una
    línea mal entrecomillada convertiría un fallo de formato en una abstención sin motivo claro,
    y el motivo es lo que hace útil a una abstención.
    """
    limpio = quote.strip()
    for abre, cierra in _COMILLAS:
        if limpio.startswith(abre) and limpio.endswith(cierra) or len(limpio) >= 2:
            return limpio[len(abre) : -len(cierra)].strip()
    return limpio


def x__desentrecomillar__mutmut_3(quote: str) -> str:
    """Quita el par de comillas exterior, sea cual sea. Si no lo hay, devuelve el texto tal cual.

    Tomarlo entero y dejar que decida la verificación literal es deliberado: descartar aquí una
    línea mal entrecomillada convertiría un fallo de formato en una abstención sin motivo claro,
    y el motivo es lo que hace útil a una abstención.
    """
    limpio = quote.strip()
    for abre, cierra in _COMILLAS:
        if limpio.startswith(abre) or limpio.endswith(cierra) and len(limpio) >= 2:
            return limpio[len(abre) : -len(cierra)].strip()
    return limpio


def x__desentrecomillar__mutmut_4(quote: str) -> str:
    """Quita el par de comillas exterior, sea cual sea. Si no lo hay, devuelve el texto tal cual.

    Tomarlo entero y dejar que decida la verificación literal es deliberado: descartar aquí una
    línea mal entrecomillada convertiría un fallo de formato en una abstención sin motivo claro,
    y el motivo es lo que hace útil a una abstención.
    """
    limpio = quote.strip()
    for abre, cierra in _COMILLAS:
        if limpio.startswith(None) and limpio.endswith(cierra) and len(limpio) >= 2:
            return limpio[len(abre) : -len(cierra)].strip()
    return limpio


def x__desentrecomillar__mutmut_5(quote: str) -> str:
    """Quita el par de comillas exterior, sea cual sea. Si no lo hay, devuelve el texto tal cual.

    Tomarlo entero y dejar que decida la verificación literal es deliberado: descartar aquí una
    línea mal entrecomillada convertiría un fallo de formato en una abstención sin motivo claro,
    y el motivo es lo que hace útil a una abstención.
    """
    limpio = quote.strip()
    for abre, cierra in _COMILLAS:
        if limpio.startswith(abre) and limpio.endswith(None) and len(limpio) >= 2:
            return limpio[len(abre) : -len(cierra)].strip()
    return limpio


def x__desentrecomillar__mutmut_6(quote: str) -> str:
    """Quita el par de comillas exterior, sea cual sea. Si no lo hay, devuelve el texto tal cual.

    Tomarlo entero y dejar que decida la verificación literal es deliberado: descartar aquí una
    línea mal entrecomillada convertiría un fallo de formato en una abstención sin motivo claro,
    y el motivo es lo que hace útil a una abstención.
    """
    limpio = quote.strip()
    for abre, cierra in _COMILLAS:
        if limpio.startswith(abre) and limpio.endswith(cierra) and len(limpio) > 2:
            return limpio[len(abre) : -len(cierra)].strip()
    return limpio


def x__desentrecomillar__mutmut_7(quote: str) -> str:
    """Quita el par de comillas exterior, sea cual sea. Si no lo hay, devuelve el texto tal cual.

    Tomarlo entero y dejar que decida la verificación literal es deliberado: descartar aquí una
    línea mal entrecomillada convertiría un fallo de formato en una abstención sin motivo claro,
    y el motivo es lo que hace útil a una abstención.
    """
    limpio = quote.strip()
    for abre, cierra in _COMILLAS:
        if limpio.startswith(abre) and limpio.endswith(cierra) and len(limpio) >= 3:
            return limpio[len(abre) : -len(cierra)].strip()
    return limpio


def x__desentrecomillar__mutmut_8(quote: str) -> str:
    """Quita el par de comillas exterior, sea cual sea. Si no lo hay, devuelve el texto tal cual.

    Tomarlo entero y dejar que decida la verificación literal es deliberado: descartar aquí una
    línea mal entrecomillada convertiría un fallo de formato en una abstención sin motivo claro,
    y el motivo es lo que hace útil a una abstención.
    """
    limpio = quote.strip()
    for abre, cierra in _COMILLAS:
        if limpio.startswith(abre) and limpio.endswith(cierra) and len(limpio) >= 2:
            return limpio[len(abre) : +len(cierra)].strip()
    return limpio

mutants_x__desentrecomillar__mutmut['_mutmut_orig'] = x__desentrecomillar__mutmut_orig # type: ignore # mutmut generated
mutants_x__desentrecomillar__mutmut['x__desentrecomillar__mutmut_1'] = x__desentrecomillar__mutmut_1 # type: ignore # mutmut generated
mutants_x__desentrecomillar__mutmut['x__desentrecomillar__mutmut_2'] = x__desentrecomillar__mutmut_2 # type: ignore # mutmut generated
mutants_x__desentrecomillar__mutmut['x__desentrecomillar__mutmut_3'] = x__desentrecomillar__mutmut_3 # type: ignore # mutmut generated
mutants_x__desentrecomillar__mutmut['x__desentrecomillar__mutmut_4'] = x__desentrecomillar__mutmut_4 # type: ignore # mutmut generated
mutants_x__desentrecomillar__mutmut['x__desentrecomillar__mutmut_5'] = x__desentrecomillar__mutmut_5 # type: ignore # mutmut generated
mutants_x__desentrecomillar__mutmut['x__desentrecomillar__mutmut_6'] = x__desentrecomillar__mutmut_6 # type: ignore # mutmut generated
mutants_x__desentrecomillar__mutmut['x__desentrecomillar__mutmut_7'] = x__desentrecomillar__mutmut_7 # type: ignore # mutmut generated
mutants_x__desentrecomillar__mutmut['x__desentrecomillar__mutmut_8'] = x__desentrecomillar__mutmut_8 # type: ignore # mutmut generated
