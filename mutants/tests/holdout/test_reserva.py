"""Reserva del adversario: ataques, no confirmaciones.

Escrita contra la especificación —los contratos, los ADR y las docstrings de los módulos—
y **sin leer ni un solo test del constructor**, que es la única forma de que esta reserva
mida algo. Cuatro zonas: la referencia legal (R1), el troceado de apartados, la identidad
de los chunks (`chunks-ddl.sql` v2 / ADR-018) y el doble grabado de embeddings.

Sin red, sin base de datos, sin Docker: todo lo de aquí es determinista y puro.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from citebound.domain.legalref import (
    LegalRef,
    LegalRefError,
    MatchLevel,
    format_ref,
    matches,
    normalize,
    parse,
    try_parse,
)
from citebound.ingest.boe_xml import Apartado, Precepto, PreceptoTipo, split_apartados
from citebound.ingest.chunking import (
    Chunk,
    ChunkingError,
    chunk_id_de,
    chunk_preceptos,
    content_hash_de,
    doc_id_de,
    normalizar_contenido,
)
from citebound.providers.embeddings import (
    DIM_CONTRATO,
    EmbeddingError,
    RecordedEmbedder,
    clave_de,
)

NORMA = "RD-1428/2003"
URI = "https://www.boe.es/diario_boe/xml.php?id=BOE-A-2003-23514"
MODELO = "bge-m3"

# La regla del contrato reescrita a mano a propósito: un párrafo que abre con "N. "
# inicia apartado. Se declara aquí para no depender del regex de la implementación.
MARCA_APARTADO = re.compile(r"^\d+\.\s")


# ======================================================================================
# LegalRef: normalización, parseo de basura y la asimetría de `matches`
# ======================================================================================


def test_normalize_folds_unicode_variants_onto_the_canonical_form() -> None:
    """Si falla, un homoglifo o un guion de PDF crea una referencia paralela.

    Y dos referencias al mismo artículo que no son iguales rompen `recall@k`, que es una
    operación de conjuntos sobre `LegalRef` (`retrieval-metrics.md` §2).
    """
    # Anchos completos + guion sin ruptura (U+2011 SOBREVIVE a NFKC) + espacios sueltos.
    crudo = "\uff32\uff24\u2011\uff11\uff14\uff12\uff18/2003 # Art\u00edculo 34 . 1"
    assert normalize(crudo) == "RD-1428/2003#art34.1"

    # Toda la familia de rayas cae al guion ASCII, incluido el signo menos.
    for raya in ("\u2010", "\u2012", "\u2013", "\u2014", "\u2015", "\u2212"):
        assert normalize(f"RD{raya}1428/2003") == NORMA

    # Espacio duro dentro del marcador: NFKC lo vuelve espacio y el espacio no cuenta.
    assert normalize("RD-1428/2003 #\u00a0ART\u00a034") == "RD-1428/2003#art34"

    # El designador se pliega a minúsculas; la norma NO, porque es un id oficial del BOE.
    assert normalize("RD-1428/2003#ART\u00cdCULO 65.5.C") == "RD-1428/2003#art65.5.c"


def test_normalize_does_not_degrade_the_long_article_spelling() -> None:
    """Si falla, `articulo34` se convierte en el artículo `iculo34`, que no existe.

    Y una referencia que no resuelve contra el corpus es exactamente lo que `G-HALLUC`
    cuenta como alucinación.
    """
    assert normalize("RD-1428/2003#articulo34") == "RD-1428/2003#art34"
    assert normalize("RD-1428/2003#art\u00edculo34") == "RD-1428/2003#art34"

    # El punto opcional del marcador no se come el punto que separa el apartado.
    ref = parse("RD-1428/2003#Art.34.1")
    assert (ref.articulo, ref.apartado) == ("34", "1")

    # Un designador partido por espacios se une, no se trunca: "14 bis" es "14bis".
    assert normalize("RD-1428/2003#Art\u00edculo 14 bis") == "RD-1428/2003#art14bis"


def test_parse_refuses_text_that_is_not_a_resolvable_reference() -> None:
    """Si falla, el sistema emite citas que no apuntan a nada del corpus.

    `parse` es la única puerta entre el texto de fuera (prompt, CSV, fila de base de
    datos) y una cita: lo que cuele aquí acaba en una respuesta al usuario.
    """
    basura = [
        "",
        "   ",
        "\n\t",
        "#art34",
        "RD-1428/2003#34",  # sin marcador: inventarlo sería inventar la referencia
        "RD-1428/2003#art",  # marcador sin designador
        "RD-1428/2003#art.",
        "RD-1428/2003#art34.",  # apartado vacío
        "RD-1428/2003#art34#art35",  # dos referencias en una
        "1428/2003",
        "RD1428/2003",
        "RD-1428/20033",
        "RD-1428/2003 extra",
        "DROP TABLE chunk;--",
    ]
    for crudo in basura:
        assert try_parse(crudo) is None, f"{crudo!r} no debería parsearse"
        with pytest.raises(LegalRefError):
            parse(crudo)

    # El guion sin ruptura sí se admite AQUÍ, y a propósito: `parse` es la capa de
    # amnistía y `normalize` lo pliega antes de mirar nada. El estricto es el constructor.
    assert parse("RD\u20111428/2003") == LegalRef(NORMA)

    # Dos artículos en una sola referencia SIN segundo `#`: el espacio interior se
    # aplasta (es lo que convierte "14 bis" en "14bis"), así que sale un designador
    # que no resuelve contra el corpus. Eso es aceptable; lo que NO puede pasar es que
    # degrade a la mitad legible y se cite `art34` como si el resto no estuviera.
    confuso = parse("RD-1428/2003#art34 y art35")
    assert confuso != LegalRef(NORMA, "34")
    assert confuso != LegalRef(NORMA, "35")


def test_constructor_refuses_field_values_that_are_not_canonical() -> None:
    """Si falla, una `LegalRef` deja de ser canónica y el `legal_ref` de Postgres diverge.

    La columna generada de `chunks-ddl.sql` y el valor de Python tienen que ser la misma
    cadena byte a byte; si no, un `JOIN` entre métricas y corpus deja de casar.
    """
    no_canonicos = [
        (NORMA, "ART34", None),  # mayúsculas
        (NORMA, "art 34", None),  # espacio interior
        (NORMA, "", None),  # designador vacío
        (NORMA, "-34", None),  # guion colgando por delante
        (NORMA, "34-", None),  # y por detrás
        (NORMA, "34", ".1"),  # punto colgando
        (NORMA, "34", "1."),
        (NORMA, None, "1"),  # apartado sin artículo
        ("RD 1428/2003", None, None),  # espacio en la norma
        ("RD-1428/2003#art34", None, None),  # la cadena entera metida en la norma
        ("RD\u20111428/2003", None, None),  # homoglifo del guion
    ]
    for norma, articulo, apartado in no_canonicos:
        with pytest.raises(LegalRefError):
            LegalRef(norma, articulo, apartado)


def test_constructor_refuses_a_trailing_newline_in_any_field() -> None:
    """Si falla, `str(ref)` lleva un salto de línea y deja de ser el `legal_ref` del DDL.

    Un `\\n` final convierte la referencia en una cadena que no casa con la columna
    generada, y en un vector de inyección: `RD-1428/2003#art34\\ncualquier cosa` se
    imprime en dos líneas dentro de una respuesta citada.

    ROJO A PROPÓSITO (2026-08-10). Los tres validadores de `legalref.py` anclan con `$`,
    y en Python `$` casa también JUSTO ANTES de un salto de línea final: `_NORMA`,
    `_DESIGNADOR` y `_APARTADO` aceptan `"34\\n"`. El ancla que dice lo que la docstring
    promete es `\\Z`. No se arregla desde aquí: `src/` no lo toca el adversario.
    """
    for campos in (
        (f"{NORMA}\n", None, None),
        (NORMA, "34\n", None),
        (NORMA, "34", "1\n"),
    ):
        with pytest.raises(LegalRefError):
            LegalRef(*campos)


def test_matches_is_finer_implies_coarser_and_never_the_reverse() -> None:
    """Si falla, `G-CITA-PRECISION` premia una cita más gruesa que el golden set.

    Citar `art21` cuando el caso dice `art21.1` sería medio acierto, y la métrica insignia
    del proyecto pasaría a medir otra cosa.
    """
    fino = LegalRef(NORMA, "21", "1")
    grueso = LegalRef(NORMA, "21")
    solo_norma = LegalRef(NORMA)
    otro_apartado = LegalRef(NORMA, "21", "2")

    # Coincidir en apartado implica coincidir en artículo y en norma.
    assert matches(fino, fino, MatchLevel.APARTADO)
    assert matches(fino, fino, MatchLevel.ARTICULO)
    assert matches(fino, fino, MatchLevel.NORMA)

    # Nunca al revés: al que no llega al nivel pedido se le cuenta fallo, no empate.
    assert matches(fino, grueso, MatchLevel.ARTICULO)
    assert not matches(fino, grueso, MatchLevel.APARTADO)
    assert not matches(grueso, fino, MatchLevel.APARTADO)
    assert matches(grueso, solo_norma, MatchLevel.NORMA)
    assert not matches(grueso, solo_norma, MatchLevel.ARTICULO)
    assert not matches(fino, otro_apartado, MatchLevel.APARTADO)
    assert matches(fino, otro_apartado, MatchLevel.ARTICULO)

    # Y una norma distinta no coincide en ningún nivel, ni siquiera en el más grueso.
    ajena = LegalRef("RDL-6/2015", "21", "1")
    for nivel in MatchLevel:
        assert not matches(fino, ajena, nivel)


@st.composite
def _referencias(draw: st.DrawFn) -> LegalRef:
    """Referencias de un alfabeto pequeño, para que las colisiones sean frecuentes."""
    norma = draw(st.sampled_from(["RD-1428/2003", "RDL-6/2015"]))
    articulo = draw(st.sampled_from([None, "21", "34", "14bis", "unico", "anexoi-1"]))
    apartado = None if articulo is None else draw(st.sampled_from([None, "1", "2", "5.c"]))
    return LegalRef(norma, articulo, apartado)


@settings(max_examples=300)
@given(_referencias(), _referencias())
def test_matches_implication_holds_for_any_pair(a: LegalRef, b: LegalRef) -> None:
    """Si falla, la jerarquía de niveles tiene un agujero y las métricas no son ordenables.

    Las tres métricas de `retrieval-metrics.md` §2 asumen que APARTADO es más estricto que
    ARTICULO y este que NORMA, para cualquier par, no solo para los ejemplos del contrato.
    """
    for nivel in MatchLevel:
        assert matches(a, b, nivel) == matches(b, a, nivel), "matches debe ser simétrico"

    if matches(a, b, MatchLevel.APARTADO):
        assert matches(a, b, MatchLevel.ARTICULO)
    if matches(a, b, MatchLevel.ARTICULO):
        assert matches(a, b, MatchLevel.NORMA)

    # Reflexiva en su propio nivel: una referencia siempre coincide consigo misma.
    assert matches(a, a, a.level)


@st.composite
def _grafias(draw: st.DrawFn) -> str:
    """Grafías admitidas de una misma referencia: separadores, marcadores y espacios."""
    espacio = st.sampled_from(["", " ", "  ", "\t"])
    raya = draw(st.sampled_from(["-", "\u2010", "\u2013", "\u2014", "\u2212"]))
    marcador = draw(st.sampled_from(["art", "art.", "ART", "Art.", "art\u00edculo ", "articulo "]))
    articulo = draw(st.sampled_from(["34", "14 bis", "65"]))
    apartado = draw(st.sampled_from([None, "1", "5.c"]))
    texto = f"{draw(espacio)}RD{raya}1428/2003{draw(espacio)}#{draw(espacio)}{marcador}"
    texto += f"{draw(espacio)}{articulo}"
    if apartado is not None:
        texto += f"{draw(espacio)}.{draw(espacio)}{apartado}"
    return texto + draw(espacio)


@settings(max_examples=300)
@given(_grafias())
def test_formatting_a_parsed_reference_reproduces_normalize(crudo: str) -> None:
    """Si falla, el texto canónico y el objeto se separan y ya no hay una sola verdad.

    La docstring de `normalize` promete `format(parse(s)) == normalize(s)`; sin eso, el
    valor que se escribe en el informe y el que se compara contra el golden set pueden
    diferir sin que nada lo note.
    """
    ref = parse(crudo)
    assert format_ref(ref) == normalize(crudo)
    assert str(ref) == format_ref(ref)
    # Idempotente: normalizar lo ya normalizado no lo mueve.
    assert normalize(normalize(crudo)) == normalize(crudo)
    assert parse(format_ref(ref)) == ref


def test_a_chunk_identifier_never_parses_as_a_legal_reference() -> None:
    """Si falla, un `chunk_id` puede colarse donde debe ir una `LegalRef` y R1 se rompe.

    R1 dice que nunca se cita ni se evalúa por `chunk_id`; el día que uno de esos
    identificadores parsee, el golden set estaría midiendo troceado en vez de derecho.
    """
    doc_id = doc_id_de(URI)
    content_hash = content_hash_de("Artículo 34. Cómputo de carriles.\n1. Texto.")
    chunk_id = chunk_id_de(doc_id, content_hash, 0)

    for ident in (doc_id, content_hash, chunk_id):
        assert try_parse(ident) is None, f"{ident!r} no es una referencia legal"
        assert try_parse(f"{doc_id}:{chunk_id}") is None
        assert try_parse(f"{NORMA}#{ident}") is None
        assert try_parse(f"{NORMA}#chunk-{ident}") is None
        assert try_parse(f"chunk:{ident}") is None

    # Ni siquiera el ordinal, que es lo más parecido a un número de artículo que hay.
    assert try_parse("chunk 7") is None
    assert try_parse("ordinal-7") is None


# ======================================================================================
# split_apartados: reagrupa, no reescribe
# ======================================================================================


def test_split_apartados_never_invents_or_renumbers_an_apartado() -> None:
    """Si falla, se acuña `art34.1` en artículos que no numeran, y eso es alucinar.

    El número del apartado sale del texto del BOE o no existe: deducirlo de la posición
    crea referencias que no resuelven contra el corpus.
    """
    # Sin marca no hay número: `None`, nunca un "1" deducido de ser el primero.
    assert split_apartados(["Texto sin numerar."]) == (Apartado(None, "Texto sin numerar."),)

    # "1.500 metros" y "30 km/h" no son marcas de apartado: falta el espacio tras el punto.
    sueltos = split_apartados(["1.500 metros de visibilidad.", "30 km/h como m\u00e1ximo."])
    assert len(sueltos) == 1
    assert sueltos[0].numero is None

    # La marca solo cuenta al principio del párrafo, no en medio de una frase.
    assert split_apartados(["Lo dice el 3. apartado anterior."])[0].numero is None

    # Los números se leen del texto: ni se ordenan, ni se corrigen, ni se deduplican.
    desordenados = split_apartados(["3. tres", "1. uno", "1. otra vez uno"])
    assert [a.numero for a in desordenados] == ["3", "1", "1"]

    assert split_apartados([]) == ()


def test_split_apartados_keeps_lettered_items_inside_their_apartado() -> None:
    """Si falla, cada letra pasa a ser una referencia propia y el golden set deja de casar.

    El contrato escribe los apartados compuestos como `2.a`: las letras viven dentro de su
    apartado padre, no como apartados hermanos.
    """
    apartados = split_apartados(
        ["2. Los conductores deber\u00e1n:", "a) uno", "b) dos", "3. Otro apartado"]
    )
    assert len(apartados) == 2
    assert apartados[0].numero == "2"
    assert apartados[0].texto == "Los conductores deber\u00e1n:\na) uno\nb) dos"
    assert apartados[1] == Apartado("3", "Otro apartado")


_ALFABETO = "abc XYZ.,()0123456789"
_LINEA = st.text(alphabet=_ALFABETO, max_size=24)
_NUMERADO = st.builds(lambda n, t: f"{n}. {t}", st.integers(1, 99), _LINEA)
_CONTINUACION = _LINEA.filter(lambda t: MARCA_APARTADO.match(t) is None)


def _reconstruir(apartados: tuple[Apartado, ...]) -> list[str]:
    """Deshace el reagrupado aplicando la regla del contrato al revés."""
    parrafos: list[str] = []
    for apartado in apartados:
        lineas = apartado.texto.split("\n")
        cabeza = lineas[0] if apartado.numero is None else f"{apartado.numero}. {lineas[0]}"
        parrafos.append(cabeza)
        parrafos.extend(lineas[1:])
    return parrafos


@settings(max_examples=300)
@given(st.lists(st.one_of(_NUMERADO, _CONTINUACION), max_size=8))
def test_split_apartados_regroups_without_rewriting(parrafos: list[str]) -> None:
    """Si falla, el troceado pierde o inventa texto y `G-QUOTE-LIT` verifica contra ficción.

    Toda cita se comprueba literalmente contra el contenido del chunk: si el reagrupado
    altera un carácter, o una cita legítima se rechaza o una inventada se acepta.
    """
    apartados = split_apartados(parrafos)
    assert _reconstruir(apartados) == parrafos

    # Y nada se duplica: hay tantos apartados como marcas, salvo el arranque sin marca.
    con_marca = sum(1 for p in parrafos if MARCA_APARTADO.match(p) is not None)
    esperados = con_marca + (1 if parrafos and MARCA_APARTADO.match(parrafos[0]) is None else 0)
    assert len(apartados) == esperados


# ======================================================================================
# chunking: identidad estable, sin posición dentro del hash
# ======================================================================================


def _precepto(
    designador: str,
    *,
    rotulo: str | None = None,
    rubrica: str = "R\u00fabrica del art\u00edculo.",
    cuerpo: tuple[str, ...] = ("1. Texto del apartado primero.",),
    vigente: bool = True,
) -> Precepto:
    """Un `Precepto` mínimo, construido a mano para no depender del XML del BOE."""
    return Precepto(
        ref=LegalRef(NORMA, designador),
        tipo=PreceptoTipo.ARTICULO,
        rotulo=rotulo if rotulo is not None else f"Art\u00edculo {designador}",
        rubrica=rubrica,
        apartados=split_apartados(list(cuerpo)),
        titulo=None,
        capitulo=None,
        seccion=None,
        vigente=vigente,
        id_norma_version="BOE-A-2003-23514",
        fecha_vigencia="2004-01-24",
    )


def _por_ref(chunks: tuple[Chunk, ...]) -> dict[str, str]:
    return {str(c.ref): c.chunk_id for c in chunks}


def test_chunk_id_matches_the_contract_formula_and_two_runs_agree() -> None:
    """Si falla, el 04 y el 01 calculan identidades distintas para el mismo texto.

    `chunk_id` es de un contrato compartido (`chunks-ddl.sql` v2): la fórmula se rehace
    aquí a mano, de modo que cambiar el orden de los ingredientes o el ancho del digest
    se detecta aunque la suite del constructor solo compare consigo misma.
    """
    doc_id = doc_id_de(URI)
    assert doc_id == hashlib.sha256(URI.encode("utf-8")).hexdigest()[:16]
    assert len(doc_id) == 16

    contenido = "Art\u00edculo 34. C\u00f3mputo de carriles.\n1. Texto."
    content_hash = content_hash_de(contenido)
    assert (
        content_hash == hashlib.sha256(normalizar_contenido(contenido).encode("utf-8")).hexdigest()
    )

    for occurrence in (0, 1, 7):
        semilla = f"{doc_id}{content_hash}{occurrence}".encode()
        esperado = hashlib.blake2b(semilla, digest_size=16).hexdigest()
        assert chunk_id_de(doc_id, content_hash, occurrence) == esperado
        assert len(esperado) == 32

    # Determinista entre ejecuciones: ni reloj, ni uuid, ni contador de proceso.
    preceptos = [_precepto("3"), _precepto("34"), _precepto("65")]
    assert chunk_preceptos(preceptos, URI) == chunk_preceptos(preceptos, URI)

    # Y depende del documento: el mismo texto en otra norma no comparte identidad.
    otros = chunk_preceptos(preceptos, URI + "&otro=1")
    assert not set(_por_ref(otros).values()) & set(
        _por_ref(chunk_preceptos(preceptos, URI)).values()
    )


def test_editing_the_document_does_not_rename_the_untouched_chunks() -> None:
    """Si falla, insertar un párrafo obliga a reembeber el documento entero (ADR-018).

    La posición está fuera del hash justamente para esto: un artículo nuevo por delante,
    o uno derogado en medio, no pueden cambiar el `chunk_id` de los demás.
    """
    p3, p34, p65 = _precepto("3"), _precepto("34"), _precepto("65")

    base = chunk_preceptos([p3, p34, p65], URI)
    con_insercion = chunk_preceptos([_precepto("1"), p3, p34, p65], URI)

    for ref, chunk_id in _por_ref(base).items():
        assert _por_ref(con_insercion)[ref] == chunk_id, f"{ref} se renombró al insertar"

    # El ordinal sí se desplaza: es posición, y por eso no puede estar en el hash.
    assert [c.ordinal for c in base] == [0, 1, 2]
    assert [c.ordinal for c in con_insercion] == [0, 1, 2, 3]
    assert con_insercion[1].ordinal == base[0].ordinal + 1

    # Un derogado en medio no se indexa y no deja hueco ni desplaza identidades.
    con_derogado = chunk_preceptos([p3, _precepto("34", vigente=False), p65], URI)
    assert con_derogado == chunk_preceptos([p3, p65], URI)
    assert [str(c.ref) for c in con_derogado] == [f"{NORMA}#art3", f"{NORMA}#art65"]
    assert [c.ordinal for c in con_derogado] == [0, 1]


def test_identical_content_is_told_apart_by_occurrence() -> None:
    """Si falla, dos apartados idénticos comparten `chunk_id` y uno pisa al otro.

    En texto legal los apartados cortos se repiten literalmente; sin `occurrence` la
    tabla perdería filas por clave duplicada, silenciosamente.
    """
    gemelo_a = _precepto("34", rotulo="Art\u00edculo id\u00e9ntico")
    gemelo_b = _precepto("35", rotulo="Art\u00edculo id\u00e9ntico")
    chunks = chunk_preceptos([gemelo_a, gemelo_b], URI)

    assert chunks[0].content_hash == chunks[1].content_hash
    assert [c.occurrence for c in chunks] == [0, 1]
    assert chunks[0].chunk_id != chunks[1].chunk_id
    assert len({c.chunk_id for c in chunks}) == 2

    doc_id = doc_id_de(URI)
    assert chunk_id_de(doc_id, chunks[0].content_hash, 0) != chunk_id_de(
        doc_id, chunks[0].content_hash, 1
    )

    # Contenido distinto reinicia la cuenta: `occurrence` es por contenido, no global.
    con_tercero = chunk_preceptos([gemelo_a, _precepto("36"), gemelo_b], URI)
    assert [c.occurrence for c in con_tercero] == [0, 0, 1]


def test_content_normalisation_is_nfc_and_not_nfkc() -> None:
    """Si falla, el hash cambia de identidad para un texto que nadie ha editado.

    Aquí el hash IDENTIFICA el texto para otro proyecto; plegar compatibilidad (NFKC)
    haría que una ligadura del PDF y su expansión fueran el mismo chunk, y el 04 vería
    reindexarse documentos intactos.
    """
    ligadura = "\ufb01n de la v\u00eda"  # U+FB01 LATIN SMALL LIGATURE FI
    assert normalizar_contenido(ligadura) == ligadura
    assert normalizar_contenido(ligadura) != "fin de la v\u00eda"
    assert content_hash_de(ligadura) != content_hash_de("fin de la v\u00eda")
    assert unicodedata.normalize("NFKC", ligadura) == "fin de la v\u00eda"  # NFKC sí plegaría

    # NFC sí une el acento combinante con su letra: es la misma cadena, no otro chunk.
    assert content_hash_de("cafe\u0301") == content_hash_de("caf\u00e9")

    # Espacios colapsados y recortados: la maquetación del BOE no es identidad.
    assert normalizar_contenido("  Art\u00edculo   34.\n\n  Texto. ") == "Art\u00edculo 34. Texto."
    assert content_hash_de("a\tb") == content_hash_de("a b")


def test_chunk_preceptos_refuses_input_it_cannot_identify() -> None:
    """Si falla, dos documentos comparten `doc_id` o se indexa un artículo sin texto.

    Un `source_uri` en blanco daría el mismo `doc_id` a todo el corpus, y un precepto sin
    apartados produce un chunk que no se puede citar ni verificar.
    """
    with pytest.raises(ChunkingError):
        chunk_preceptos([_precepto("3")], "   ")
    with pytest.raises(ChunkingError):
        chunk_preceptos([_precepto("3")], "")

    vacio = Precepto(
        ref=LegalRef(NORMA, "3"),
        tipo=PreceptoTipo.ARTICULO,
        rotulo="Art\u00edculo 3",
        rubrica="Sin cuerpo.",
        apartados=(),
        titulo=None,
        capitulo=None,
        seccion=None,
        vigente=True,
        id_norma_version="BOE-A-2003-23514",
        fecha_vigencia=None,
    )
    with pytest.raises(ChunkingError):
        chunk_preceptos([vacio], URI)

    # Sin preceptos no hay chunks, y eso no es un error: es un documento sin articulado.
    assert chunk_preceptos([], URI) == ()
    # Un derogado sin cuerpo tampoco explota: se descarta antes de mirarle el texto.
    assert chunk_preceptos([_precepto("3", vigente=False)], URI) == ()


# ======================================================================================
# RecordedEmbedder: un doble que nunca inventa
# ======================================================================================


def test_recorded_embedder_never_invents_a_vector() -> None:
    """Si falla, la suite se pone verde sobre números que nadie ha producido.

    Un doble que fabrica en el fallo es peor que no tener doble: el primer sitio donde
    aparece es una cifra de recall que no se puede explicar.
    """
    vector = tuple(float(i) / 1000 for i in range(DIM_CONTRATO))
    grabacion = {clave_de(MODELO, "texto grabado"): list(vector)}
    embedder = RecordedEmbedder(grabacion=grabacion, model=MODELO)

    assert embedder.embed(["texto grabado"]) == (vector,)

    with pytest.raises(EmbeddingError):
        embedder.embed(["texto que nadie grabó"])

    # Ni siquiera parcialmente: si falta uno, no se devuelve la lista a medias.
    with pytest.raises(EmbeddingError):
        embedder.embed(["texto grabado", "texto que nadie grabó"])

    # La grabación es de un (modelo, texto): otro modelo no hereda el vector.
    otro = RecordedEmbedder(grabacion=grabacion, model="otro-modelo")
    with pytest.raises(EmbeddingError):
        otro.embed(["texto grabado"])
    assert clave_de(MODELO, "t") != clave_de("otro-modelo", "t")
    assert clave_de(MODELO, "t") != clave_de(MODELO, "u")

    # Sin textos no hay nada que inventar ni que buscar.
    assert embedder.embed([]) == ()


def test_recorded_embedder_refuses_a_recording_of_the_wrong_width() -> None:
    """Si falla, entran vectores del ancho equivocado en una columna `vector(1024)`.

    Cambiar de ancho no es cambiar de modelo: es una tabla nueva y reindexar. Detectarlo
    en el doble es lo que evita descubrirlo en un `INSERT` de producción.
    """
    corta = [0.0] * (DIM_CONTRATO - 1)
    grabacion = {clave_de(MODELO, "t"): corta}
    with pytest.raises(EmbeddingError, match="dimensiones"):
        RecordedEmbedder(grabacion=grabacion, model=MODELO).embed(["t"])

    larga = {clave_de(MODELO, "t"): [0.0] * (DIM_CONTRATO + 1)}
    with pytest.raises(EmbeddingError, match="dimensiones"):
        RecordedEmbedder(grabacion=larga, model=MODELO).embed(["t"])

    # El ancho declarado manda sobre el del contrato: un doble a 3 dimensiones es válido.
    tres = {clave_de(MODELO, "t"): [1.0, 2.0, 3.0]}
    assert RecordedEmbedder(grabacion=tres, model=MODELO, dim=3).embed(["t"]) == ((1.0, 2.0, 3.0),)


def test_recorded_embedder_replays_a_file_deterministically(tmp_path: Path) -> None:
    """Si falla, dos ejecuciones de `make eval` desde caché dan informes distintos.

    `G-EVAL-DET` compara dos informes byte a byte: la grabación tiene que replicar el
    mismo vector siempre, y traer su modelo y su ancho del fichero, no de un default.
    """
    ruta = tmp_path / "grabacion.json"
    ruta.write_text(
        json.dumps(
            {
                "model": "modelo-de-la-grabacion",
                "dim": 4,
                "vectores": {clave_de("modelo-de-la-grabacion", "hola"): [1.0, 2.0, 3.0, 4.0]},
            }
        ),
        encoding="utf-8",
    )

    embedder = RecordedEmbedder.desde_fichero(ruta)
    assert embedder.model == "modelo-de-la-grabacion"
    assert embedder.dim == 4
    assert embedder.embed(["hola"]) == ((1.0, 2.0, 3.0, 4.0),)
    assert embedder.embed(["hola"]) == embedder.embed(["hola"])

    with pytest.raises(EmbeddingError):
        embedder.embed(["adi\u00f3s"])
