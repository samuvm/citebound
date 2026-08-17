"""Unit tests for `citebound.ingest.chunking`.

Turns `Precepto` values into the rows of the `chunk_v1` table. The identifier contract
is **not this project's to invent**: it is `docs/CONTRACTS/chunks-ddl.sql` v2, shared
with `indexkeeper-04`, and every assertion about `chunk_id`, `doc_id`, `content_hash` or
`occurrence` below is that file read literally.

    doc_id       = sha256(source_uri)[:16]
    content_hash = sha256(normalize(content))     NFC + colapso de espacios + strip
    occurrence   = índice 0-based de esta aparición de content_hash dentro del documento
    chunk_id     = blake2b(doc_id ‖ content_hash ‖ str(occurrence), digest_size=16).hex()

Why v2 took the position out of the hash, and why `occurrence` had to appear in its
place, is ADR-018. The short version: with the ordinal inside, inserting one paragraph
renamed every chunk below it and made `indexkeeper-04`'s flagship metric unreachable by
construction. Taking it out means identical text inside one document needs something
else to tell the copies apart — and in legal text that is not hypothetical.

Phase 0 chunks one article per chunk, deliberately (`docs/PLAN.md`: *"una norma, 1
artículo = 1 chunk, solo vectorial"*). The strategy is named and recorded because
`index_version.chunker_id` is a column of the shared contract, and because phase 2 exists
to compare strategies against the golden set — a comparison that is only possible if the
one used is written down next to the numbers.
"""

from __future__ import annotations

import hashlib
import re

import pytest

from citebound.domain.legalref import LegalRef
from citebound.ingest.boe_xml import Apartado, Precepto, PreceptoTipo
from citebound.ingest.chunking import (
    CHUNKER_APARTADO_ID,
    CHUNKER_ID,
    CHUNKER_MULTINIVEL_ID,
    Chunk,
    ChunkingError,
    chunk_id_de,
    chunk_multinivel,
    chunk_por_apartado,
    chunk_preceptos,
    content_hash_de,
    doc_id_de,
    exigir_ids_unicos,
    normalizar_contenido,
)

NORMA = "RD-1428/2003"
URI = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/BOE-A-2003-23514"


def _precepto(
    designador: str,
    *apartados: tuple[str | None, str],
    rubrica: str = "Rúbrica.",
    tipo: PreceptoTipo = PreceptoTipo.ARTICULO,
    titulo: str | None = "TÍTULO PRELIMINAR",
    rotulo: str | None = None,
) -> Precepto:
    return Precepto(
        ref=LegalRef(NORMA, designador),
        tipo=tipo,
        rotulo=rotulo or f"Artículo {designador}",
        rubrica=rubrica,
        apartados=tuple(Apartado(n, t) for n, t in apartados),
        titulo=titulo,
        capitulo=None,
        seccion=None,
        vigente=True,
        id_norma_version="BOE-A-2003-23514",
        fecha_vigencia="20040123",
    )


ART3 = _precepto("3", ("1", "Se deberá conducir con diligencia."), ("2", "Las conductas graves."))
ART34 = _precepto("34", (None, "Para el cómputo de carriles."))


# --------------------------------------------------------------------------------------
# the identifier contract, read literally from chunks-ddl.sql v2
# --------------------------------------------------------------------------------------


def test_doc_id_is_the_first_sixteen_hex_of_the_sha256_of_the_uri() -> None:
    assert doc_id_de(URI) == hashlib.sha256(URI.encode()).hexdigest()[:16]
    assert len(doc_id_de(URI)) == 16


def test_content_hash_is_the_sha256_of_the_normalised_text() -> None:
    esperado = hashlib.sha256(b"Un texto.").hexdigest()
    assert content_hash_de("  Un    texto.  ") == esperado


def test_chunk_id_is_blake2b_of_doc_content_and_occurrence() -> None:
    doc, contenido = doc_id_de(URI), content_hash_de("Un texto.")
    esperado = hashlib.blake2b(f"{doc}{contenido}0".encode(), digest_size=16).hexdigest()
    assert chunk_id_de(doc, contenido, 0) == esperado
    assert len(chunk_id_de(doc, contenido, 0)) == 32


def test_the_chunk_id_does_not_depend_on_the_position() -> None:
    """The whole point of contract v2. With the ordinal inside the hash, inserting one
    paragraph at the top of a document renamed every chunk below it and forced a full
    re-embed — which made `G-INCR-2` of `indexkeeper-04` unreachable by construction, not
    by implementation."""
    doc, contenido = doc_id_de(URI), content_hash_de("Un texto.")
    assert chunk_id_de(doc, contenido, 0) == chunk_id_de(doc, contenido, 0)
    # el mismo contenido en dos posiciones distintas del documento conserva su id
    a = chunk_preceptos((ART3, ART34), source_uri=URI)
    b = chunk_preceptos((_precepto("9", (None, "Relleno.")), ART3, ART34), source_uri=URI)
    por_ref = {str(c.ref): c.chunk_id for c in a}
    for chunk in b:
        if str(chunk.ref) in por_ref:
            assert chunk.chunk_id == por_ref[str(chunk.ref)]


def test_the_rubric_lead_makes_two_articles_with_the_same_body_distinct() -> None:
    """Short apartados repeat verbatim all over legal text. Because the chunk opens with
    `"Artículo N. Rúbrica."`, two different articles that say the same thing still hash
    apart — which is the right outcome: they are different law and must be retrievable
    as such."""
    repetido = "Se estará a lo dispuesto en el artículo anterior."
    chunks = chunk_preceptos(
        (_precepto("7", (None, repetido)), _precepto("8", (None, repetido))), source_uri=URI
    )
    assert chunks[0].content_hash != chunks[1].content_hash
    assert chunks[0].chunk_id != chunks[1].chunk_id
    assert [c.occurrence for c in chunks] == [0, 0]


def test_the_occurrence_tells_genuinely_identical_content_apart() -> None:
    """`occurrence` is what contract v2 put in the place the ordinal used to occupy, and
    it has to work even though the article-level strategy of phase 0 rarely triggers it.
    Phase 2 splits finer, and then two apartados with the same wording under the same
    heading stop being contrived: without `occurrence` they would collide on the primary
    key of `chunk_v1`.

    The case is built here the only way phase 0 allows — two preceptos that the parser
    disambiguated by TÍTULO (ADR-020) and that carry the same rótulo, rúbrica and text."""
    mismo = ("Artículo 151", "Rúbrica.", (None, "Texto idéntico palabra por palabra."))
    a = _precepto("tv-151", mismo[2], rubrica=mismo[1], rotulo=mismo[0])
    b = _precepto("tvi-151", mismo[2], rubrica=mismo[1], rotulo=mismo[0])
    chunks = chunk_preceptos((a, b), source_uri=URI)
    assert chunks[0].content_hash == chunks[1].content_hash
    assert [c.occurrence for c in chunks] == [0, 1]
    assert chunks[0].chunk_id != chunks[1].chunk_id


def test_normalisation_is_nfc_plus_collapsed_whitespace_plus_strip() -> None:
    """Exactly what the contract writes, no more: NFC, not NFKC. Folding compatibility
    characters here would silently change the text whose hash the other project relies on."""
    assert normalizar_contenido("  hola   mundo \n ") == "hola mundo"
    assert normalizar_contenido("mañana") == "mañana"  # NFC compone la ñ
    # U+FF21 FULLWIDTH A escrito como escape: el carácter ambiguo ES el dato de prueba,
    # y así RUF001 sigue activo en todo el repo — G-INJECT prueba homoglifos.
    assert normalizar_contenido("\uff21") == "\uff21"  # NFKC lo volvería "A"; NFC no


# --------------------------------------------------------------------------------------
# determinism · the invariant the whole incremental story rests on
# --------------------------------------------------------------------------------------


def test_two_runs_over_the_same_input_produce_the_same_identifiers() -> None:
    """`chunks-ddl.sql` invariant A: the sha256 of the ordered set of
    `(chunk_id, content_hash, …)` must be identical across runs. No timestamps, no
    random UUIDs, no process counters."""
    primera = chunk_preceptos((ART3, ART34), source_uri=URI)
    segunda = chunk_preceptos((ART3, ART34), source_uri=URI)
    assert [c.chunk_id for c in primera] == [c.chunk_id for c in segunda]
    assert [c.ordinal for c in primera] == [c.ordinal for c in segunda]


def test_the_ordinal_is_the_position_in_the_document() -> None:
    chunks = chunk_preceptos((ART3, ART34, _precepto("35", (None, "Otro."))), source_uri=URI)
    assert [c.ordinal for c in chunks] == [0, 1, 2]


def test_the_chunker_is_named_because_the_contract_has_a_column_for_it() -> None:
    """`index_version.chunker_id`. Phase 2 compares chunking strategies against the
    golden set, and a comparison whose strategy is not recorded next to the numbers is
    an anecdote."""
    assert CHUNKER_ID == "articulo-v1"
    assert all(c.chunker_id == CHUNKER_ID for c in chunk_preceptos((ART3,), source_uri=URI))


# --------------------------------------------------------------------------------------
# what a chunk carries
# --------------------------------------------------------------------------------------


def test_phase_zero_makes_one_chunk_per_article() -> None:
    """`docs/PLAN.md` phase 0: *una norma, 1 artículo = 1 chunk*. Deliberately naive —
    the point of the skeleton is that it walks end to end, and phase 2 is where chunking
    is measured instead of assumed."""
    chunks = chunk_preceptos((ART3, ART34), source_uri=URI)
    assert len(chunks) == 2
    assert [str(c.ref) for c in chunks] == ["RD-1428/2003#art3", "RD-1428/2003#art34"]


def test_the_text_of_all_apartados_reaches_the_chunk() -> None:
    contenido = chunk_preceptos((ART3,), source_uri=URI)[0].content
    assert "Se deberá conducir con diligencia." in contenido
    assert "Las conductas graves." in contenido


def test_the_rubric_leads_the_chunk_so_that_a_lone_apartado_still_says_what_it_is_about() -> None:
    """An apartado retrieved on its own reads as an orphan sentence. Leading with the
    article's rubric is what lets the embedding of the chunk carry its subject, and it is
    the cheapest thing that moves recall in a corpus this repetitive."""
    contenido = chunk_preceptos((ART3,), source_uri=URI)[0].content
    assert contenido.startswith("Artículo 3. Rúbrica.")


def test_the_hierarchy_travels_with_the_chunk_for_the_materia_filter() -> None:
    chunk = chunk_preceptos((ART3,), source_uri=URI)[0]
    assert chunk.titulo == "TÍTULO PRELIMINAR"
    assert chunk.capitulo is None


def test_provenance_travels_with_the_chunk() -> None:
    chunk = chunk_preceptos((ART3,), source_uri=URI)[0]
    assert chunk.id_norma_version == "BOE-A-2003-23514"
    assert chunk.fecha_vigencia == "20040123"


def test_every_chunk_carries_a_non_empty_reference() -> None:
    """RULES §3.2, required property. A chunk without a ref cannot be cited, cannot be
    verified and pollutes `recall@k` with a row that can never be a correct answer."""
    for chunk in chunk_preceptos((ART3, ART34), source_uri=URI):
        assert isinstance(chunk.ref, LegalRef)
        assert str(chunk.ref)
        assert "chunk_id" not in str(chunk.ref)


# --------------------------------------------------------------------------------------
# refusal
# --------------------------------------------------------------------------------------


def test_a_repealed_precepto_is_not_indexed() -> None:
    """Article 51 is in the corpus and says `(Derogado)`. Indexing it would let the
    system retrieve and quote a repealed article — literal, verifiable and wrong."""
    derogado = _precepto("51", (None, "(Derogado)."))
    derogado = Precepto(
        **{  # type: ignore[misc]
            f.name: (False if f.name == "vigente" else getattr(derogado, f.name))
            for f in __import__("dataclasses").fields(derogado)
        }
    )
    assert chunk_preceptos((derogado, ART3), source_uri=URI) == (
        chunk_preceptos((ART3,), source_uri=URI)
    )


def test_a_precepto_with_no_text_is_refused_loudly() -> None:
    """Silently skipping would hide a broken ingest behind a smaller index."""
    with pytest.raises(ChunkingError):
        chunk_preceptos((_precepto("9"),), source_uri=URI)


def test_an_empty_source_uri_is_refused() -> None:
    """`doc_id` is derived from it; an empty uri gives every document the same id."""
    with pytest.raises(ChunkingError):
        chunk_preceptos((ART3,), source_uri="")


def test_chunking_nothing_yields_nothing() -> None:
    assert chunk_preceptos((), source_uri=URI) == ()


# --------------------------------------------------------------------------------------
# no loss · the property RULES §3.2 demands, stated once here and again as a property
# --------------------------------------------------------------------------------------


def test_the_chunk_text_reproduces_the_apartados_it_came_from() -> None:
    chunk = chunk_preceptos((ART3,), source_uri=URI)[0]
    partes = chunk.content.split("\n", 1)
    assert len(partes) == 2, "el chunk debe llevar la rúbrica y, tras un salto, el cuerpo"
    cuerpo = partes[1]
    assert cuerpo == "1. Se deberá conducir con diligencia.\n2. Las conductas graves."


def test_no_chunk_ever_mixes_two_articles() -> None:
    """RULES §3.2, required property. A chunk straddling an article boundary would make
    the `quote` of one article verifiable against the text of another, and
    `G-QUOTE-LIT` would keep saying 1,00 while the citation pointed at the wrong law."""
    for chunk in chunk_preceptos((ART3, ART34), source_uri=URI):
        refs = set(re.findall(r"Artículo \d+", chunk.content))
        assert len(refs) <= 1


def test_a_chunk_is_immutable_and_hashable() -> None:
    chunk = chunk_preceptos((ART3,), source_uri=URI)[0]
    assert isinstance(chunk, Chunk)
    assert len({chunk, chunk}) == 1
    with pytest.raises((AttributeError, TypeError)):
        chunk.ordinal = 99  # type: ignore[misc]


# ======================================================================================
# `apartado-v1` · el troceado fino, que es la palanca que no se había tocado
# ======================================================================================
#
# Con `articulo-v1` un artículo entero es UN embedding para varios temas, y los fallos
# medidos el 2026-08-17 eran justamente confusiones dentro de un grupo — los artículos 74,
# 108, 109 y 110 hablan todos de señalizar maniobras. Un apartado dice una cosa.
#
# Lo que estos tests sujetan no es que el recall suba —eso lo dice `make eval-retrieval`,
# no un test— sino que trocear más fino **no invente ni pierda** una sola referencia.


def test_un_articulo_numerado_da_un_chunk_por_apartado() -> None:
    chunks = chunk_por_apartado([ART3], source_uri=URI)
    assert [str(c.ref) for c in chunks] == [f"{NORMA}#art3.1", f"{NORMA}#art3.2"]


def test_un_articulo_sin_numerar_sigue_siendo_un_solo_chunk_sin_apartado() -> None:
    """**El invariante que no se negocia.** `numero is None` significa que el artículo no
    numera sus párrafos; inventar un `1` acuñaría `art34.1`, una referencia que no existe.
    Es exactamente la alucinación que `G-HALLUC` está construido para hacer imposible, y
    trocear más fino no puede abrir esa puerta por la puerta de atrás."""
    chunks = chunk_por_apartado([ART34], source_uri=URI)
    assert len(chunks) == 1
    assert str(chunks[0].ref) == f"{NORMA}#art34"
    assert chunks[0].ref.apartado is None


def test_cada_chunk_lleva_su_encabezado_de_articulo() -> None:
    """Un apartado suelto es una frase huérfana: «2. Las conductas graves.» no se distingue
    de las otras cincuenta del corpus que también empiezan por «2.». El encabezado es lo
    que le da al embedding de qué agarrarse, y es el mismo motivo por el que `articulo-v1`
    ya lo ponía."""
    for chunk in chunk_por_apartado([ART3], source_uri=URI):
        assert chunk.content.startswith("Artículo 3. Rúbrica.")


def test_el_texto_de_cada_apartado_esta_literal_en_su_chunk() -> None:
    """Precondición de `G-QUOTE-LIT`: si el troceado alterara el texto, una cita verificada
    contra el chunk dejaría de corresponder con el BOE."""
    chunks = chunk_por_apartado([ART3], source_uri=URI)
    assert "Se deberá conducir con diligencia." in chunks[0].content
    assert "Las conductas graves." in chunks[1].content


def test_no_se_pierde_ni_un_apartado() -> None:
    """Trocear fino puede perder material en silencio, y el síntoma sería un recall peor
    sin causa aparente — que es la familia de fallo de toda esta fase."""
    juntos = " ".join(c.content for c in chunk_por_apartado([ART3, ART34], source_uri=URI))
    for precepto in (ART3, ART34):
        for apartado in precepto.apartados:
            assert apartado.texto in juntos


def test_dos_apartados_de_articulos_distintos_no_colisionan_aunque_digan_lo_mismo() -> None:
    """El `chunk_id` es función del contenido, y el encabezado es lo que hace que el
    contenido difiera. Sin él, «Se prohíbe.» en dos artículos sería el MISMO chunk y uno de
    los dos artículos desaparecería del índice."""
    a = _precepto("10", ("1", "Se prohíbe."))
    b = _precepto("20", ("1", "Se prohíbe."))
    chunks = chunk_por_apartado([a, b], source_uri=URI)
    assert len({c.chunk_id for c in chunks}) == 2
    assert {str(c.ref) for c in chunks} == {f"{NORMA}#art10.1", f"{NORMA}#art20.1"}


def test_los_derogados_siguen_fuera() -> None:
    derogado = _precepto("51", ("1", "Texto derogado."))
    object.__setattr__(derogado, "vigente", False)
    assert chunk_por_apartado([derogado], source_uri=URI) == ()


def test_declara_su_propio_chunker_id() -> None:
    """Dos troceados distintos con el mismo `chunker_id` producirían dos índices que se
    dicen iguales, y `index_version` dejaría de identificar sobre qué se midió."""
    assert CHUNKER_APARTADO_ID == "apartado-v1"
    assert CHUNKER_APARTADO_ID != CHUNKER_ID
    for chunk in chunk_por_apartado([ART3], source_uri=URI):
        assert chunk.chunker_id == CHUNKER_APARTADO_ID


def test_el_ordinal_es_consecutivo_y_sin_huecos() -> None:
    """El contrato pone `UNIQUE (index_version, doc_id, ordinal)`: un hueco o un repetido
    revienta la ingesta, y hacerlo al insertar la fila 400 es el peor momento."""
    chunks = chunk_por_apartado([ART3, ART34], source_uri=URI)
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))


def test_trocear_dos_veces_da_los_mismos_identificadores() -> None:
    """Invariante A del contrato, igual que en `articulo-v1`: sin esto, reingerir duplica."""
    primera = chunk_por_apartado([ART3, ART34], source_uri=URI)
    segunda = chunk_por_apartado([ART3, ART34], source_uri=URI)
    assert [c.chunk_id for c in primera] == [c.chunk_id for c in segunda]


def test_una_source_uri_vacia_se_rechaza_igual_que_en_articulo_v1() -> None:
    with pytest.raises(ChunkingError):
        chunk_por_apartado([ART3], source_uri="  ")


# ======================================================================================
# `multinivel-v1` · los dos niveles en el mismo índice
# ======================================================================================
#
# Medido el 2026-08-17: `articulo-v1` gana en la lectura de artículo (0,847 con reordenador
# contra 0,806) y `apartado-v1` gana en la estricta por goleada (0,500 contra 0,093). Cada
# uno es mejor en una cosa distinta, así que la pregunta es si sirven los dos a la vez.


def test_indexa_el_articulo_entero_y_ademas_cada_apartado() -> None:
    refs = {str(c.ref) for c in chunk_multinivel([ART3], source_uri=URI)}
    assert refs == {f"{NORMA}#art3", f"{NORMA}#art3.1", f"{NORMA}#art3.2"}


def test_un_articulo_de_un_solo_apartado_no_se_indexa_dos_veces() -> None:
    """Con un único apartado, el artículo **es** el apartado: los dos trozos tendrían el
    mismo texto. Dos filas idénticas gastan plaza en el top-30 sin añadir nada, que es el
    mismo desperdicio que el colapso por artículo existe para quitar."""
    uno = _precepto("7", ("1", "Texto único."))
    chunks = chunk_multinivel([uno], source_uri=URI)
    assert len(chunks) == 1
    assert str(chunks[0].ref) == f"{NORMA}#art7.1"


def test_multinivel_no_acuna_un_apartado_donde_no_lo_hay() -> None:
    """El invariante de siempre: `numero is None` no puede acuñar `art34.1`."""
    chunks = chunk_multinivel([ART34], source_uri=URI)
    assert len(chunks) == 1
    assert chunks[0].ref.apartado is None


def test_ningun_chunk_id_se_repite_aunque_dos_niveles_hablen_del_mismo_articulo() -> None:
    chunks = chunk_multinivel([ART3, ART34], source_uri=URI)
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))


def test_multinivel_declara_su_propio_chunker_id() -> None:
    assert CHUNKER_MULTINIVEL_ID == "multinivel-v1"
    for chunk in chunk_multinivel([ART3], source_uri=URI):
        assert chunk.chunker_id == CHUNKER_MULTINIVEL_ID


def test_dos_chunks_con_el_mismo_id_revientan_en_vez_de_perderse() -> None:
    """**El guardián que cazó un fallo real y no tenía test.**

    `chunk_id` es la clave primaria, así que dos filas con el mismo id no dan un error: una se
    come a la otra en el `ON CONFLICT` y el síntoma aparece mucho más lejos, como un recall
    peor sin causa. Saltó el 2026-08-17 con 94 repetidos en el corpus real.

    El mensaje se comprueba desde el principio a propósito: es lo que va a leer quien se lo
    encuentre, y un gate que dice «rojo» y calla se acaba desactivando.
    """
    uno, *_ = chunk_por_apartado([ART3], source_uri=URI)
    with pytest.raises(ChunkingError, match=r"^dos niveles produjeron el mismo chunk_id \(1\)"):
        exigir_ids_unicos([uno, uno])


def test_sin_repetidos_no_dice_nada() -> None:
    exigir_ids_unicos(chunk_multinivel([ART3, ART34], source_uri=URI))


def test_cada_apartado_hereda_la_jerarquia_de_su_articulo() -> None:
    """Título, capítulo y sección viajan con el chunk, y no son adorno: son lo que permite
    filtrar por materia y lo que da contexto a la respuesta. Trocear más fino multiplica las
    filas, así que una de estas que se quedara en `None` afectaría a 569 y no a 235."""
    art = _precepto("34", ("1", "Uno."), ("2", "Dos."), titulo="TÍTULO II")
    object.__setattr__(art, "capitulo", "CAPÍTULO III")
    object.__setattr__(art, "seccion", "Sección 2.ª")
    for chunk in chunk_por_apartado([art], source_uri=URI):
        assert chunk.titulo == "TÍTULO II"
        assert chunk.capitulo == "CAPÍTULO III"
        assert chunk.seccion == "Sección 2.ª"
        assert chunk.id_norma_version == "BOE-A-2003-23514"
        assert chunk.fecha_vigencia == "20040123"


def test_dos_documentos_distintos_no_comparten_chunk_id_aunque_digan_lo_mismo() -> None:
    """El `doc_id` entra en el identificador, y hace falta: el día que el corpus tenga dos
    normas, un artículo con el mismo texto en las dos sería **un solo chunk** y una de las dos
    normas desaparecería del índice sin que nada avisara."""
    a = chunk_por_apartado([ART3], source_uri=URI)
    b = chunk_por_apartado([ART3], source_uri=URI.replace("23514", "99999"))
    assert {c.chunk_id for c in a}.isdisjoint({c.chunk_id for c in b})
    assert [c.content for c in a] == [c.content for c in b]


def test_una_lista_vacia_de_preceptos_no_da_chunks_ni_revienta() -> None:
    assert chunk_por_apartado([], source_uri=URI) == ()
    assert chunk_multinivel([], source_uri=URI) == ()


def test_un_precepto_sin_texto_se_rechaza_en_vez_de_indexarse_vacio() -> None:
    """Un chunk sin contenido produce un embedding sin significado que compite igual por una
    plaza del top-30. Reventar aquí lo deja donde se puede diagnosticar."""
    hueco = _precepto("99")
    with pytest.raises(ChunkingError, match="no tiene texto"):
        chunk_por_apartado([hueco], source_uri=URI)
