"""`domain/citation.py` · la cita cerrada, que es la tesis del proyecto hecha código.

Un RAG normal deja que el modelo *escriba* la referencia, y entonces «según el artículo 47.3»
son tokens que predice igual que el resto de la frase: si lo recuperado era el 45, nada se
entera. Aquí el modelo solo puede escribir un hueco numerado sobre lo que la búsqueda sí trajo,
y la traducción de ese número a una `LegalRef` la hace **este módulo**, nunca el modelo.

De ahí que los tests se lean como una lista de formas de mentir: número fuera de rango, apartado
inventado sobre un artículo real, comilla curva por comilla recta, un carácter cambiado, una
cita que cruza dos artículos. Cada una es una manera de que una respuesta parezca verificada sin
estarlo, y ninguna puede pasar.

`docs/RULES.md` §3.1 pone `domain/` en **TDD obligatorio**: este fichero se compromete en rojo
antes de que exista una línea de implementación.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from citebound.domain.citation import (
    MAX_CARACTERES_TRAMO,
    MAX_FUENTES,
    MIN_CARACTERES_QUOTE,
    Cita,
    CitaError,
    Fuente,
    Motivo,
    Veredicto,
    normalizar_para_cotejo,
    parsear_borrador,
    resolver,
    segmentar,
    verificar,
)
from citebound.domain.legalref import parse

NORMA = "RD-1428/2003"

ART34 = Fuente(
    ref=parse(f"{NORMA}#art34"),
    texto=(
        "Artículo 34. Cómputo de carriles.\n"
        "1. A efectos de este reglamento, el número de carriles de una calzada se contará "
        "de derecha a izquierda."
    ),
)
ART35 = Fuente(
    ref=parse(f"{NORMA}#art35"),
    texto="Artículo 35. Separación lateral.\n1. Se deberá guardar la separación necesaria.",
)
FUENTES = (ART34, ART35)


# ======================================================================================
# Resolver `n` → `LegalRef`. Lo que el modelo NO puede hacer
# ======================================================================================


def test_un_hueco_valido_resuelve_a_la_referencia_de_su_fuente() -> None:
    assert resolver(Cita(n=1, quote="el número de carriles"), FUENTES) == ART34.ref


def test_el_hueco_cero_se_rechaza() -> None:
    """`n` empieza en 1 porque así se le presenta al modelo. Un 0 es un error de índice
    disfrazado de cita, y resolverlo al último elemento —que es lo que haría Python— citaría
    un artículo que nadie eligió."""
    with pytest.raises(CitaError, match="fuera de rango"):
        resolver(Cita(n=0, quote="da igual"), FUENTES)


def test_un_hueco_negativo_se_rechaza() -> None:
    with pytest.raises(CitaError, match="fuera de rango"):
        resolver(Cita(n=-1, quote="da igual"), FUENTES)


def test_el_hueco_seis_se_rechaza_aunque_haya_cinco_fuentes() -> None:
    """El caso que el plan nombra: `n=6` con cinco fuentes. Es el borde exacto del rango que
    se le ofrece al modelo, y es donde un off-by-one se colaría sin que nadie lo notara."""
    cinco = tuple(
        Fuente(ref=parse(f"{NORMA}#art{i}"), texto=f"Artículo {i}. Texto.") for i in range(1, 6)
    )
    assert len(cinco) == MAX_FUENTES
    with pytest.raises(CitaError, match="fuera de rango"):
        resolver(Cita(n=6, quote="da igual"), cinco)


def test_un_hueco_dentro_del_rango_pero_sin_fuente_se_rechaza() -> None:
    """Si la búsqueda solo trajo dos, el 3 no existe **aunque** el modelo tenga permitido
    escribir hasta el 5. El rango real lo fija lo recuperado, no la plantilla."""
    with pytest.raises(CitaError, match="fuera de rango"):
        resolver(Cita(n=3, quote="da igual"), FUENTES)


def test_sin_fuentes_ningun_hueco_es_valido() -> None:
    """Corpus sin resultados: no hay nada que citar y la salida correcta es abstenerse, no
    inventar un 1."""
    with pytest.raises(CitaError, match="fuera de rango"):
        resolver(Cita(n=1, quote="da igual"), ())


# ======================================================================================
# La normalización declarada · NFKC + espacios + comillas + guiones
# ======================================================================================


def test_las_comillas_curvas_se_pliegan_sobre_las_rectas() -> None:
    """Un modelo devuelve «"texto"» donde el BOE escribe '"texto"'. Son el mismo texto para
    quien lee, y si no se pliegan `G-QUOTE-LIT` bajaría de 1,00 por tipografía."""
    assert normalizar_para_cotejo("“texto”") == normalizar_para_cotejo('"texto"')
    assert normalizar_para_cotejo("‘texto’") == normalizar_para_cotejo("'texto'")  # noqa: RUF001


def test_los_guiones_unicode_se_pliegan_sobre_el_guion_normal() -> None:
    """El guion largo, el corto y el de no ruptura salen todos del mismo sitio: un PDF, un
    copiado, un teclado distinto."""
    for guion in ("—", "–", "‑", "−"):  # noqa: RUF001
        assert normalizar_para_cotejo(f"a{guion}b") == "a-b"


def test_los_espacios_se_colapsan_y_el_salto_de_linea_cuenta_como_espacio() -> None:
    """El corpus trae saltos de línea entre apartados; el modelo cita en una sola línea."""
    assert normalizar_para_cotejo("uno\n  dos\t\ttres ") == "uno dos tres"


def test_la_normalizacion_es_nfkc_y_no_nfc() -> None:
    """NFKC porque aquí se compara **lo que un modelo escribió** contra lo que dice el corpus,
    y ahí un carácter de compatibilidad es el mismo texto. En el troceador es NFC a propósito:
    allí el hash **identifica** el texto para otro proyecto y plegar cambiaría su identidad."""
    assert normalizar_para_cotejo("ﬁn") == "fin"
    assert normalizar_para_cotejo("№ 1") == "No 1"


def test_normalizar_es_idempotente() -> None:
    """Si no lo fuera, verificar dos veces la misma cita podría dar respuestas distintas."""
    crudo = "  “Artículo 34”— el  número\tde\ncarriles ﬁnal "
    una = normalizar_para_cotejo(crudo)
    assert normalizar_para_cotejo(una) == una


# ======================================================================================
# Verificación literal · lo que separa una cita de una paráfrasis
# ======================================================================================


def test_una_cita_literal_pasa() -> None:
    assert verificar(
        [Cita(n=1, quote="el número de carriles de una calzada se contará de derecha a izquierda")],
        FUENTES,
    ) == Veredicto(ok=True, refs=(ART34.ref,))


def test_un_solo_caracter_cambiado_no_pasa() -> None:
    """**El test que define el módulo.** «se contará de derecha a izquierda» contra
    «se contara de derecha a izquierda»: una tilde. Un juez LLM diría que significan lo mismo,
    y por eso el juez no decide esto. Una cita es literal o no es una cita."""
    v = verificar([Cita(n=1, quote="el número de carriles se contara de derecha")], FUENTES)
    assert v.ok is False
    assert v.motivo is Motivo.QUOTE_NO_LITERAL


def test_una_parafrasis_fiel_tampoco_pasa() -> None:
    """Dice lo mismo con otras palabras. Es exactamente lo que el sistema no promete."""
    v = verificar([Cita(n=1, quote="los carriles se cuentan empezando por la derecha")], FUENTES)
    assert v.ok is False
    assert v.motivo is Motivo.QUOTE_NO_LITERAL


def test_un_quote_que_cruza_dos_articulos_no_pasa() -> None:
    """Pegar el final del 34 con el principio del 35 produce una frase que no está en ninguno
    de los dos. Sería una cita verificable contra el corpus entero y falsa contra su ref."""
    cruzado = "se contará de derecha a izquierda. Artículo 35. Separación lateral."
    v = verificar([Cita(n=1, quote=cruzado)], FUENTES)
    assert v.ok is False
    assert v.motivo is Motivo.QUOTE_NO_LITERAL


def test_el_quote_se_coteja_contra_su_propia_fuente_y_no_contra_las_demas() -> None:
    """Un texto que sí está en el artículo 35 pero se cita como `[[REF:1]]` es una cita mal
    atribuida. Verificar contra el corpus entero la daría por buena."""
    v = verificar([Cita(n=1, quote="Se deberá guardar la separación necesaria")], FUENTES)
    assert v.ok is False
    assert v.motivo is Motivo.QUOTE_NO_LITERAL


def test_un_quote_vacio_no_pasa() -> None:
    """La cadena vacía es subcadena de cualquier texto, así que pasaría la comprobación
    literal por accidente y no citaría nada."""
    v = verificar([Cita(n=1, quote="")], FUENTES)
    assert v.ok is False
    assert v.motivo is Motivo.QUOTE_VACIO


def test_un_quote_de_solo_espacios_no_pasa() -> None:
    v = verificar([Cita(n=1, quote="   \n ")], FUENTES)
    assert v.ok is False
    assert v.motivo is Motivo.QUOTE_VACIO


def test_un_quote_demasiado_corto_no_pasa() -> None:
    """«de» está literalmente en el artículo y no cita nada: un fragmento tan corto aparece en
    cualquier texto y convierte `G-QUOTE-LIT` en un 1,00 que no significa nada."""
    v = verificar([Cita(n=1, quote="de")], FUENTES)
    assert v.ok is False
    assert v.motivo is Motivo.QUOTE_DEMASIADO_CORTO


def test_el_borde_exacto_del_minimo_pasa_y_uno_menos_no() -> None:
    """El borde, que es donde viven los off-by-one. Un `<=` en vez de `<` rechazaría una cita
    de longitud exactamente mínima, y ningún otro test lo notaría: la diferencia es un carácter
    y el mensaje de error sería el mismo.

    El fragmento se toma **del texto de la fuente**, así que lo único que se está probando es
    la longitud y no la literalidad."""
    fuente = Fuente(ref=parse(f"{NORMA}#art9"), texto="Artículo 9. " + "abcdefghijklmnopqrst")
    justo = fuente.texto[-MIN_CARACTERES_QUOTE:]
    assert len(justo) == MIN_CARACTERES_QUOTE
    assert verificar([Cita(n=1, quote=justo)], (fuente,)).ok is True

    corto = justo[1:]
    assert len(corto) == MIN_CARACTERES_QUOTE - 1
    v = verificar([Cita(n=1, quote=corto)], (fuente,))
    assert v.ok is False
    assert v.motivo is Motivo.QUOTE_DEMASIADO_CORTO


def test_una_cita_con_tipografia_distinta_pasa_tras_normalizar() -> None:
    """Lo contrario del test del carácter cambiado, y por eso van juntos: la normalización
    tiene que ser suficiente para la tipografía y **no más** que eso."""
    v = verificar([Cita(n=1, quote="el  número   de\ncarriles de una calzada se contará")], FUENTES)
    assert v.ok is True


# ======================================================================================
# Varias citas · «una correcta más una inventada cuenta como fallo»
# ======================================================================================


def test_dos_citas_validas_devuelven_las_dos_referencias() -> None:
    v = verificar(
        [
            Cita(n=1, quote="el número de carriles de una calzada"),
            Cita(n=2, quote="Se deberá guardar la separación necesaria"),
        ],
        FUENTES,
    )
    assert v.ok is True
    assert v.refs == (ART34.ref, ART35.ref)


def test_una_valida_y_una_invalida_tumban_la_respuesta_entera() -> None:
    """Regla del contrato compartido (`retrieval-metrics.md` §«Precisión de cita»): *una cita
    correcta más una inventada cuenta como fallo*. Emitir la mitad buena sería publicar una
    respuesta que el usuario leería como verificada entera."""
    v = verificar(
        [
            Cita(n=1, quote="el número de carriles de una calzada"),
            Cita(n=2, quote="esto no está en el artículo 35 ni en ninguno"),
        ],
        FUENTES,
    )
    assert v.ok is False
    assert v.motivo is Motivo.QUOTE_NO_LITERAL


def test_una_respuesta_sin_ninguna_cita_no_pasa() -> None:
    """Sin cita no hay nada que verificar, y emitirla sería justo el RAG que este proyecto
    no quiere ser. La salida correcta es abstenerse."""
    v = verificar([], FUENTES)
    assert v.ok is False
    assert v.motivo is Motivo.SIN_CITAS


def test_el_hueco_fuera_de_rango_da_su_propio_motivo() -> None:
    """Se distingue de un quote malo porque la reacción es distinta: fuera de rango significa
    que el modelo se saltó el formato, y eso se detecta en el stream sin esperar al final."""
    v = verificar([Cita(n=9, quote="da igual")], FUENTES)
    assert v.ok is False
    assert v.motivo is Motivo.FUERA_DE_RANGO


# ======================================================================================
# El apartado inventado, que es la alucinación más difícil de ver
# ======================================================================================


def test_un_apartado_inventado_sobre_un_articulo_real_no_se_puede_expresar() -> None:
    """El plan lo nombra: `art34.7` cuando el 34 no tiene apartado 7. **No hay test que lo
    detecte porque no hay forma de escribirlo**: la ref sale de la fuente recuperada, no del
    modelo, y el modelo solo escribe un número del 1 al 5. Esto lo comprueba."""
    assert resolver(Cita(n=1, quote="el número de carriles"), FUENTES) == ART34.ref
    assert resolver(Cita(n=1, quote="el número de carriles"), FUENTES).apartado is None


# ======================================================================================
# Parseo del borrador · separar la respuesta de sus citas
# ======================================================================================
#
# El contrato SSE (`docs/RULES.md` §2.2) reparte el trabajo: los `[[REF:n]]` viajan en los
# tokens y se validan en vuelo, y las citas con su `quote` salen **al final**, ya verificadas.
# Así que el modelo tiene que producir las dos cosas, y este parseo es la frontera entre lo que
# el modelo escribe y lo que el verificador comprueba.


def test_una_respuesta_con_su_bloque_de_citas_se_separa() -> None:
    borrador = (
        "No se puede adelantar en un cambio de rasante [[REF:1]].\n"
        "\n"
        "CITAS\n"
        "[[REF:1]] «el número de carriles de una calzada»\n"
    )
    respuesta, citas = parsear_borrador(borrador)
    assert respuesta == "No se puede adelantar en un cambio de rasante [[REF:1]]."
    assert citas == (Cita(n=1, quote="el número de carriles de una calzada"),)


def test_varias_citas_salen_en_orden() -> None:
    borrador = (
        "Primero [[REF:2]] y luego [[REF:1]].\n\nCITAS\n"
        "[[REF:2]] «Se deberá guardar la separación»\n"
        "[[REF:1]] «el número de carriles»\n"
    )
    _, citas = parsear_borrador(borrador)
    assert [c.n for c in citas] == [2, 1]


def test_sin_bloque_de_citas_la_respuesta_es_todo_y_no_hay_citas() -> None:
    """El modelo se saltó el formato. No se inventa un bloque: se devuelven cero citas y el
    verificador dirá `SIN_CITAS`, que dispara reintento con el motivo delante."""
    respuesta, citas = parsear_borrador("Una respuesta sin citar nada.")
    assert respuesta == "Una respuesta sin citar nada."
    assert citas == ()


def test_las_comillas_del_quote_pueden_ser_de_cualquier_tipo() -> None:
    """Se le piden guillemets y devolverá lo que le salga. Pelearse con el prompt por esto es
    más caro que aceptar las tres formas."""
    for abre, cierra in (("«", "»"), ('"', '"'), ("“", "”")):
        _, citas = parsear_borrador(f"X [[REF:1]].\n\nCITAS\n[[REF:1]] {abre}texto{cierra}\n")
        assert citas == (Cita(n=1, quote="texto"),), (abre, cierra)


def test_un_quote_sin_comillas_se_toma_entero() -> None:
    """Mejor tomarlo y que la verificación literal decida, que descartarlo aquí: descartarlo
    convertiría un fallo de formato en una abstención sin motivo claro."""
    _, citas = parsear_borrador("X [[REF:1]].\n\nCITAS\n[[REF:1]] texto sin comillas\n")
    assert citas == (Cita(n=1, quote="texto sin comillas"),)


def test_una_linea_del_bloque_que_no_es_una_cita_se_ignora() -> None:
    """Un modelo añade «Espero que te sirva» donde no toca. Ignorar la línea es preferible a
    tomarla como cita de la anterior."""
    borrador = "X [[REF:1]].\n\nCITAS\n[[REF:1]] «texto»\nEspero que te sirva.\n"
    _, citas = parsear_borrador(borrador)
    assert citas == (Cita(n=1, quote="texto"),)


def test_el_marcador_de_citas_no_se_confunde_con_la_palabra_en_la_respuesta() -> None:
    """«…según las CITAS del reglamento…» dentro de la respuesta no abre el bloque: el
    marcador es una línea entera y solo eso."""
    borrador = "Hay CITAS en el reglamento [[REF:1]].\n\nCITAS\n[[REF:1]] «texto»\n"
    respuesta, citas = parsear_borrador(borrador)
    assert "Hay CITAS en el reglamento" in respuesta
    assert len(citas) == 1


def test_un_par_de_comillas_vacio_da_un_quote_vacio_y_no_las_comillas() -> None:
    """El borde exacto del desentrecomillado, y no es cosmético: decide **qué motivo** publica
    el verificador. Con el quote vacío dice `QUOTE_VACIO`, que es exacto; devolviendo `«»` como
    texto diría `QUOTE_NO_LITERAL`, que manda a buscar el fallo donde no está."""
    _, citas = parsear_borrador("X [[REF:1]].\n\nCITAS\n[[REF:1]] «»\n")
    assert citas == (Cita(n=1, quote=""),)
    assert verificar(list(citas), FUENTES).motivo is Motivo.QUOTE_VACIO


def test_un_borrador_vacio_no_revienta() -> None:
    assert parsear_borrador("") == ("", ())


def test_el_bloque_de_citas_puede_ir_primero() -> None:
    """**El orden que salvó nueve casos de veinticinco.** Con la respuesta delante, el modelo
    agotaba el presupuesto de tokens escribiendo prosa y no llegaba nunca a la línea `CITAS`:
    el veredicto era `SIN_CITAS` y se abstenía por truncamiento, no por no saber citar.

    Poniendo las citas primero, lo que se trunca es la prosa —recuperable— y no la parte
    verificable."""
    borrador = (
        "CITAS\n"
        "[[REF:1]] «el número de carriles de una calzada»\n"
        "\n"
        "RESPUESTA\n"
        "Se cuentan de derecha a izquierda [[REF:1]].\n"
    )
    respuesta, citas = parsear_borrador(borrador)
    assert citas == (Cita(n=1, quote="el número de carriles de una calzada"),)
    assert respuesta == "Se cuentan de derecha a izquierda [[REF:1]]."


def test_el_orden_antiguo_sigue_funcionando() -> None:
    """Sin marcador `RESPUESTA`, lo que va antes de `CITAS` es la respuesta. Aceptar los dos
    órdenes cuesta tres líneas y evita que un cambio de prompt rompa el parseo."""
    respuesta, citas = parsear_borrador("Texto [[REF:1]].\n\nCITAS\n[[REF:1]] «algo»\n")
    assert respuesta == "Texto [[REF:1]]."
    assert citas == (Cita(n=1, quote="algo"),)


def test_con_las_citas_primero_una_respuesta_truncada_conserva_sus_citas() -> None:
    """El caso real: el modelo se queda sin tokens a mitad de la prosa. Las citas ya salieron,
    así que la respuesta se puede verificar igual en vez de perderse entera."""
    _, citas = parsear_borrador("CITAS\n[[REF:1]] «algo»\n\nRESPUESTA\nSe cuentan de derec")
    assert citas == (Cita(n=1, quote="algo"),)


# ======================================================================================
# El fragmento lo copia el CÓDIGO · `[[REF:n]] §m`
#
# La tesis del proyecto, un nivel más abajo. Si el generador no escribe la referencia
# porque la resuelve el código, tampoco tiene por qué escribir el fragmento: señala el
# tramo y lo copia el código. Un quote así **no puede** no ser literal, igual que hoy una
# referencia no puede estar inventada.
#
# Lo que esto deja de medir, dicho claro: la capacidad del modelo de TRANSCRIBIR, que
# nunca fue lo que el producto promete. Lo que sigue midiéndose es su capacidad de
# ELEGIR — el ref con `G-CITA-PRECISION` y ahora el tramo, que puede equivocarse igual.
# ======================================================================================


ART34_LARGO = Fuente(
    ref=parse(f"{NORMA}#art34"),
    texto=(
        "Artículo 34. Cómputo de carriles.\n"
        "1. Se contará de derecha a izquierda. 2. Los carriles reversibles no cuentan."
    ),
)


def test_segmentar_parte_por_frases_y_por_lineas() -> None:
    """El modelo tiene que poder señalar un tramo, así que el troceado del artículo es parte
    del contrato con él: si cambia, el `§2` de una grabación deja de significar lo mismo."""
    assert segmentar(ART34_LARGO.texto) == (
        "Artículo 34. Cómputo de carriles.",
        "1. Se contará de derecha a izquierda.",
        "2. Los carriles reversibles no cuentan.",
    )


def test_un_texto_sin_finales_de_frase_es_un_solo_segmento() -> None:
    assert segmentar("solo una cosa sin punto") == ("solo una cosa sin punto",)


@given(st.text(min_size=1, max_size=400))
def test_todo_segmento_esta_literalmente_en_su_origen(texto: str) -> None:
    """**La propiedad que hace que esto valga la pena.** Si un segmento no fuera un trozo
    literal del texto, copiar el segmento no garantizaría nada y todo el diseño se cae."""
    normalizado = normalizar_para_cotejo(texto)
    for trozo in segmentar(texto):
        assert normalizar_para_cotejo(trozo) in normalizado


def test_la_cita_por_tramo_produce_el_quote_desde_la_fuente() -> None:
    """El modelo escribe `§2` y el `quote` sale del artículo, no de su teclado."""
    borrador = "Se cuentan así [[REF:1]].\n\nCITAS\n[[REF:1]] §2\n"
    _, citas = parsear_borrador(borrador, (ART34_LARGO,))
    assert citas[0].segmento == 2
    assert citas[0].quote == "1. Se contará de derecha a izquierda."


def test_un_quote_copiado_por_codigo_no_puede_fallar_la_verificacion() -> None:
    """`G-QUOTE-LIT` pasa de ser un número que se comprueba a un invariante estructural. El
    verificador se queda igualmente: defensa en profundidad, no confianza."""
    _, citas = parsear_borrador("x [[REF:1]].\n\nCITAS\n[[REF:1]] §2\n", (ART34_LARGO,))
    assert verificar(citas, (ART34_LARGO,)).ok is True


def test_un_tramo_que_no_existe_se_rechaza_con_su_propio_motivo() -> None:
    """**Distinto de `FUERA_DE_RANGO`**, que es el ref, y distinto de `QUOTE_NO_LITERAL`, que
    ya no puede pasar. Confundirlos manda a arreglar lo que no está roto."""
    _, citas = parsear_borrador("x [[REF:1]].\n\nCITAS\n[[REF:1]] §9\n", (ART34_LARGO,))
    assert verificar(citas, (ART34_LARGO,)).motivo is Motivo.SEGMENTO_FUERA_DE_RANGO


def test_el_tramo_cero_se_rechaza_como_el_ref_cero() -> None:
    """Por lo mismo que `resolver` rechaza el 0: en Python indexaría al último y citaría un
    tramo que nadie eligió, en silencio."""
    _, citas = parsear_borrador("x [[REF:1]].\n\nCITAS\n[[REF:1]] §0\n", (ART34_LARGO,))
    assert verificar(citas, (ART34_LARGO,)).motivo is Motivo.SEGMENTO_FUERA_DE_RANGO


def test_sigue_leyendo_las_citas_entrecomilladas_de_las_grabaciones() -> None:
    """Hay 274 respuestas grabadas con el formato viejo. Si dejaran de parsearse, `make eval`
    mediría un sistema distinto del que produjo la caché y el número no significaría nada."""
    viejo = "x [[REF:1]].\n\nCITAS\n[[REF:1]] «1. Se contará de derecha a izquierda.»\n"
    _, citas = parsear_borrador(viejo, (ART34_LARGO,))
    assert citas[0].quote == "1. Se contará de derecha a izquierda."
    assert citas[0].segmento is None


def test_sin_fuentes_el_tramo_no_se_puede_resolver_y_no_se_inventa() -> None:
    """`parsear_borrador` se llama en sitios donde todavía no hay fuentes. Devolver un quote
    vacío es correcto; inventarse uno sería exactamente lo que este proyecto no hace."""
    _, citas = parsear_borrador("x [[REF:1]].\n\nCITAS\n[[REF:1]] §2\n")
    assert citas[0].segmento == 2
    assert citas[0].quote == ""


def test_una_frase_larguisima_se_parte_en_tramos_senalables() -> None:
    """**El tope vive aquí y no en el prompt, y este test es por qué.** `agent.graph` enseña
    los tramos y `citation` los copia; si el tope viviera en el lado que los enseña, un tramo
    largo se vería recortado y se copiaría entero — y saldría publicado un fragmento que el
    modelo nunca leyó."""
    larga = "palabra " * 200
    tramos = segmentar(larga)
    assert len(tramos) > 1
    assert all(len(t) <= MAX_CARACTERES_TRAMO for t in tramos)
    assert all(t in larga for t in tramos)


def test_un_tramo_minusculo_se_pega_al_siguiente_en_vez_de_ser_citable() -> None:
    """**Catorce abstenciones salieron de aquí.** El troceador producía tramos como «2.» y el
    verificador los rechazaba por `QUOTE_DEMASIADO_CORTO` — con razón, porque un fragmento de
    dos caracteres no cita, coincide.

    El arreglo va en `segmentar` y no en el mínimo: bajar el mínimo dejaría pasar citas de dos
    letras por la puerta del formato viejo, donde el fragmento sí lo escribe el modelo y donde
    el mínimo es lo único que sostiene `G-QUOTE-LIT`. Lo que no puede existir es un tramo que
    el modelo puede señalar y el verificador tiene que rechazar."""
    tramos = segmentar("a) Sí.\nEsta frase sí tiene longitud de sobra para ser una cita.")
    assert all(len(t) >= MIN_CARACTERES_QUOTE for t in tramos)
    assert tramos[0].startswith("a) Sí.")
