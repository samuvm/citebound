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

from citebound.domain.citation import (
    MAX_FUENTES,
    Cita,
    CitaError,
    Fuente,
    Motivo,
    Veredicto,
    normalizar_para_cotejo,
    resolver,
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
