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


def parsear_borrador(borrador: str) -> tuple[str, tuple[Cita, ...]]:
    """Sin implementar todavía: el rojo se compromete antes que el verde."""
    return ("", ())
