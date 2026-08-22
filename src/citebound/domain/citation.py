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
    "MARCA_CITAS",
    "MARCA_RESPUESTA",
    "MAX_CARACTERES_TRAMO",
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
    "segmentar",
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

MAX_CARACTERES_TRAMO = 300
"""Tope de un tramo citable, y **tiene que vivir aquí y no en el prompt**.

`agent.graph` enseña los tramos al modelo y `citation` los copia: si el tope viviera en el lado
que los enseña, un tramo largo se vería recortado y se copiaría entero, y saldría publicado un
fragmento que el modelo nunca leyó. Con el tope dentro de `segmentar`, los dos lados parten por
el mismo sitio porque llaman a la misma función.

Un artículo del BOE con una frase de 800 caracteres existe —las enumeraciones largas— y sin
tope sería un solo tramo imposible de señalar con precisión."""

_ESPACIOS = re.compile(r"\s+")

MARCA_RESPUESTA = "RESPUESTA"
"""Abre la prosa cuando el bloque de citas va primero, que es el orden del prompt v2."""

MARCA_CITAS = "CITAS"
"""La línea que separa la respuesta de sus citas. Va en el prompt y se lee aquí, y tenerla en
una constante es lo que impide que las dos se separen sin que nadie lo note."""

_LINEA_CITA = re.compile(r"\[\[REF:(\d+)\]\]\s*(.*)$")

_TRAMO = re.compile(r"^[\u00a7S]\s*(\d+)\s*$")
"""`§3`, y también `S3`: hay modelos que no emiten el signo de sección y escupen la letra. El
prompt pide `§`; aceptar las dos formas cuesta un carácter en la expresión y evita una
abstención por tipografía, que es el mismo criterio que ya rige para las comillas."""

_FIN_DE_FRASE = re.compile(
    r"(?<=[.:;])(?<![0-9][.:;])\s+(?=[\u00bf\u00a1\"\u00abA-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1\d])|\n+"
)
"""Dónde corta `segmentar`, y **la mitad del trabajo está en dónde NO corta**.

El texto legal numera con punto —«Artículo 34. Cómputo», «1. Se contará», «1.500»— así que
cortar tras cualquier punto seguido de mayúscula parte el encabezado del artículo en dos y deja
tramos que no son frases. Medido en el primer intento: `segmentar` daba seis tramos donde hay
tres. Por eso el punto precedido de dígito no corta."""

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
    SEGMENTO_FUERA_DE_RANGO = "segmento_fuera_de_rango"
    SIN_RELEVANCIA = "sin_relevancia"
    """Lo recuperado no viene a cuento. **Es distinto de `QUOTE_NO_LITERAL`** y la diferencia
    importa: este dice «el corpus no lo responde» y aquel dice «el modelo lo escribió mal».
    Confundirlos manda a arreglar lo que no está roto."""


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
    segmento: int | None = None


@dataclass(frozen=True, slots=True)
class Veredicto:
    """`ok` con las refs resueltas, o el motivo por el que la respuesta no sale."""

    ok: bool
    refs: tuple[LegalRef, ...] = ()
    motivo: Motivo | None = None


def segmentar(texto: str) -> tuple[str, ...]:
    """El texto de una fuente partido en tramos citables, **y es contrato con el modelo**.

    El generador señala un tramo por su número, así que este troceado es tan parte del
    protocolo como `[[REF:n]]`: si cambia, el `§2` de una respuesta grabada deja de significar
    lo mismo y `make eval` mediría otra cosa con la misma caché.

    Se parte por final de frase y por salto de línea, que es la estructura que trae el BOE: el
    encabezado del artículo en su línea y cada apartado empezando por su número. Un punto que
    no va seguido de espacio y mayúscula no corta —«art. 34», «1.500»— porque partir ahí daría
    tramos que no son frases y el modelo tendría que elegir entre pedazos.

    **La propiedad que hace que todo esto valga**: cada tramo es un trozo literal del original.
    Sin eso, copiar el tramo no garantizaría nada.
    """
    frases = (t for trozo in _FIN_DE_FRASE.split(texto) if (t := trozo.strip()))
    return _juntar_los_cortos([pedazo for frase in frases for pedazo in _acotar(frase)])


def _juntar_los_cortos(tramos: list[str]) -> tuple[str, ...]:
    """Pega al siguiente los tramos que no llegan a `MIN_CARACTERES_QUOTE`.

    **No puede existir un tramo que el modelo puede señalar y el verificador tiene que
    rechazar.** El troceador daba pedazos como «2.» o «a) Sí.» —los ordinales del BOE— y
    salían catorce abstenciones por `QUOTE_DEMASIADO_CORTO` sobre los 274 casos.

    El arreglo va aquí y no en el mínimo: bajarlo dejaría pasar citas de dos letras por la
    puerta del formato viejo, donde el fragmento lo escribe el modelo y donde ese mínimo es lo
    único que impide sostener `G-QUOTE-LIT` —umbral `== 1,00`, sin propuesta admisible— con
    coincidencias.
    """
    juntados: list[str] = []
    for tramo in tramos:
        if juntados and len(juntados[-1]) < MIN_CARACTERES_QUOTE:
            juntados[-1] = f"{juntados[-1]} {tramo}"
        else:
            juntados.append(tramo)
    # El último puede seguir siendo corto si el texto entero lo es; se pega hacia atrás.
    #
    # El `pop` va en su propia línea a propósito: escrito como `juntados[-2] = f"...{pop()}"`,
    # Python evalúa la derecha primero y el índice -2 ya no existe cuando asigna. Lo encontró
    # la propiedad de Hypothesis con el texto vacío, no una revisión.
    if len(juntados) > 1 and len(juntados[-1]) < MIN_CARACTERES_QUOTE:
        cola = juntados.pop()
        juntados[-1] = f"{juntados[-1]} {cola}"
    return tuple(juntados)


def _acotar(frase: str) -> list[str]:
    """Una frase demasiado larga, partida por palabras. Cada pedazo sigue siendo literal."""
    if len(frase) <= MAX_CARACTERES_TRAMO:
        return [frase]
    pedazos, actual = [], ""
    for palabra in _palabras(frase):
        if actual and len(actual) + 1 + len(palabra) > MAX_CARACTERES_TRAMO:
            pedazos.append(actual)
            actual = palabra
        else:
            actual = f"{actual} {palabra}" if actual else palabra
    return [*pedazos, actual] if actual else pedazos


def _palabras(frase: str) -> list[str]:
    """Las palabras, y las larguísimas partidas en seco.

    Una «palabra» de 4.000 caracteres no es prosa —una URL, una tabla del BOE sin espacios—
    pero existe, y sin partirla el tope de tramo no se cumple y el bloque del prompt se
    dispara. Lo encontró un test con `"x" * 4000`, no una lectura.
    """
    sueltas: list[str] = []
    for palabra in frase.split(" "):
        sueltas.extend(
            palabra[i : i + MAX_CARACTERES_TRAMO]
            for i in range(0, len(palabra), MAX_CARACTERES_TRAMO)
        ) if len(palabra) > MAX_CARACTERES_TRAMO else sueltas.append(palabra)
    return sueltas


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

        # El tramo se comprueba antes que el quote y con su propio motivo: un `§9` en un
        # artículo de tres frases es un fallo de SELECCIÓN, y decirle `QUOTE_VACIO` mandaría a
        # buscar el fallo en la transcripción, que es justo donde ya no puede estar.
        if cita.segmento is not None and not 1 <= cita.segmento <= len(
            segmentar(fuentes[cita.n - 1].texto)
        ):
            return Veredicto(ok=False, motivo=Motivo.SEGMENTO_FUERA_DE_RANGO)

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


def parsear_borrador(borrador: str, fuentes: Sequence[Fuente] = ()) -> tuple[str, tuple[Cita, ...]]:
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

    # Los dos órdenes. Con `RESPUESTA` detrás de `CITAS`, la prosa es lo que va después; sin
    # él, lo que va antes. Aceptar ambos cuesta tres líneas y evita que un cambio de prompt
    # rompa el parseo de todo lo grabado hasta ahora.
    fin = next(
        (i for i, x in enumerate(lineas[corte + 1 :], corte + 1) if x.strip() == MARCA_RESPUESTA),
        None,
    )
    zona_citas = lineas[corte + 1 : fin] if fin is not None else lineas[corte + 1 :]
    prosa = lineas[fin + 1 :] if fin is not None else lineas[:corte]

    citas = [
        _cita_de(int(encontrado.group(1)), encontrado.group(2).strip(), fuentes)
        for linea in zona_citas
        if (encontrado := _LINEA_CITA.match(linea.strip())) is not None
    ]
    return "\n".join(prosa).strip(), tuple(citas)


def _cita_de(n: int, cola: str, fuentes: Sequence[Fuente]) -> Cita:
    """La línea de cita, en sus dos formas. **La nueva no deja escribir el fragmento.**

    Con `§m` el `quote` sale de la fuente y por construcción es literal; con comillas sale del
    modelo y hay que verificarlo. Se aceptan las dos porque hay 274 respuestas grabadas con el
    formato viejo: si dejaran de parsearse, `make eval` mediría un sistema distinto del que
    produjo la caché.

    Sin fuentes —hay sitios que parsean antes de tenerlas— el `quote` sale vacío en vez de
    inventado. Vacío es un veredicto; inventado sería exactamente lo que este proyecto no hace.
    """
    if (tramo := _TRAMO.match(cola)) is None:
        return Cita(n=n, quote=_desentrecomillar(cola))
    m = int(tramo.group(1))
    if not fuentes or not 1 <= n <= len(fuentes):
        return Cita(n=n, quote="", segmento=m)
    trozos = segmentar(fuentes[n - 1].texto)
    quote = trozos[m - 1] if 1 <= m <= len(trozos) else ""
    return Cita(n=n, quote=quote, segmento=m)


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
