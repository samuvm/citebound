"""El camino servido, y **que coincide con el evaluado**.

Hay dos caminos: `agent.graph` es el que mide `make eval` y `agent.servir` el que responde a un
usuario. El test que de verdad importa aquí es el que los enfrenta: si divergieran, `make eval`
estaría midiendo un sistema que nadie ejecuta.

Este proyecto ya tiene cicatriz de eso. Q-019 planteó exactamente el mismo problema en la fase 2
—publicar un `G-RECALL5` medido con un reordenador que el producto no iba a ejecutar— y costó
reabrir una decisión. Que aquí haya un test es la consecuencia de haberlo vivido.
"""

from __future__ import annotations

import pytest

from citebound.agent.graph import NO_PUEDO_RESPONDER, Resultado, construir, responder
from citebound.agent.servir import Trozo, servir
from citebound.domain.citation import Fuente, Motivo
from citebound.domain.legalref import parse
from citebound.domain.retry import MAX_REINTENTOS, Salida
from citebound.providers.chat import RecordedGenerador, Respuesta

NORMA = "RD-1428/2003"
ART34 = Fuente(
    ref=parse(f"{NORMA}#art34"),
    texto="Artículo 34. Cómputo de carriles.\n1. Se contará de derecha a izquierda.",
)
PLANTILLA = "PREGUNTA\n{pregunta}\n\nARTICULOS\n{fuentes}\n"

BUENO = "Se cuentan así [[REF:1]].\n\nCITAS\n[[REF:1]] «Se contará de derecha a izquierda»\n"
QUOTE_MALO = "Mal [[REF:1]].\n\nCITAS\n[[REF:1]] «esto no está en el artículo»\n"
FUERA = "Según [[REF:9]] sí, y sigo escribiendo mucho más texto después del hueco malo."


def grabado(*textos: str) -> RecordedGenerador:
    return RecordedGenerador([Respuesta(t, "grabado", "", 10) for t in textos])


def sirve(*textos: str, fuentes=(ART34,)):
    return list(
        servir(
            "¿y esto?",
            recuperador=lambda _: fuentes,
            generador=grabado(*textos),
            plantilla=PLANTILLA,
        )
    )


def por_el_grafo(*textos: str, fuentes=(ART34,)) -> Resultado:
    g = grabado(*textos)
    grafo = construir(
        recuperador=lambda _: fuentes,
        generador=lambda prompt: g.completar(prompt).texto,
        plantilla=PLANTILLA,
    )
    return responder(grafo, "¿y esto?")


# --------------------------------------------------------------------------------------
# El test que importa: los dos caminos deciden lo mismo
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "textos",
    [
        (BUENO,),
        (QUOTE_MALO, BUENO),
        (QUOTE_MALO, QUOTE_MALO, QUOTE_MALO),
        (f"{NO_PUEDO_RESPONDER}.",),
    ],
    ids=["responde", "reintenta-y-sale", "agota-y-se-abstiene", "el-modelo-se-abstiene"],
)
def test_servir_y_el_grafo_llegan_al_mismo_veredicto(textos: tuple[str, ...]) -> None:
    """**Si esto falla, `make eval` mide un sistema que nadie ejecuta.**"""
    final = sirve(*textos)[-1]
    assert isinstance(final, Resultado)
    del_grafo = por_el_grafo(*textos)
    assert final.curso.salida is del_grafo.curso.salida
    assert final.curso.refs == del_grafo.curso.refs
    assert final.curso.reintentos == del_grafo.curso.reintentos


# --------------------------------------------------------------------------------------
# Lo que solo se ve por el camino servido
# --------------------------------------------------------------------------------------


def test_los_trozos_salen_antes_del_resultado() -> None:
    """Es el punto entero del streaming: el usuario lee mientras el modelo escribe."""
    salida = sirve(BUENO)
    assert isinstance(salida[0], Trozo)
    assert isinstance(salida[-1], Resultado)


def test_los_trozos_reconstruyen_lo_emitido() -> None:
    salida = sirve(BUENO)
    trozos = "".join(t.texto for t in salida if isinstance(t, Trozo))
    assert "[[REF:1]]" in trozos
    assert "CITAS" in trozos


def test_un_hueco_fuera_de_rango_corta_y_no_llega_a_salir() -> None:
    """**La diferencia con un filtro final.** El marcador malo no se emite, y el texto que el
    modelo escribió después tampoco: el corte es en el token."""
    salida = sirve(FUERA, BUENO)
    trozos = [t for t in salida if isinstance(t, Trozo)]
    emitido_primer_intento = "".join(t.texto for t in trozos if t.intento == 0)
    assert "[[REF:9]]" not in emitido_primer_intento
    assert "sigo escribiendo" not in emitido_primer_intento
    assert any(t.retractado for t in trozos)


def test_tras_retractar_se_reintenta_y_el_segundo_sale() -> None:
    final = sirve(FUERA, BUENO)[-1]
    assert isinstance(final, Resultado)
    assert final.curso.salida is Salida.RESPONDER
    assert final.curso.reintentos == 1


def test_agotado_el_presupuesto_no_sale_ningun_borrador() -> None:
    final = sirve(QUOTE_MALO, QUOTE_MALO, QUOTE_MALO)[-1]
    assert isinstance(final, Resultado)
    assert final.curso.salida is Salida.ABSTENERSE
    assert final.curso.motivo is Motivo.QUOTE_NO_LITERAL
    assert final.respuesta == ""
    assert len(final.borradores) == MAX_REINTENTOS + 1


def test_sin_fuentes_se_abstiene_sin_reintentar() -> None:
    final = sirve("Lo que sea.", fuentes=())[-1]
    assert isinstance(final, Resultado)
    assert final.curso.salida is Salida.ABSTENERSE


def test_los_dos_caminos_numeran_las_fuentes_exactamente_igual() -> None:
    """Si numeraran distinto, el mismo borrador significaría cosas distintas según por dónde se
    sirviera, y `make eval` mediría un sistema que nadie ejecuta. Comparten función, y esto
    comprueba que la siguen compartiendo."""
    from citebound.agent.graph import CARACTERES_POR_FUENTE, bloques_de

    largo = Fuente(ref=parse(f"{NORMA}#art9"), texto="Artículo 9. " + "x" * 4000)
    bloques = bloques_de([ART34, largo])
    assert bloques.startswith("[1] ")
    assert "\n\n[2] " in bloques
    assert len(bloques.split("\n\n[2] ")[1]) == CARACTERES_POR_FUENTE


def test_el_texto_se_trunca_en_el_prompt_pero_no_al_verificar() -> None:
    """**La razón de que truncar sea seguro.** El verificador coteja contra el texto completo de
    la fuente, no contra lo que vio el modelo: truncar reduce de dónde puede citar, nunca
    convierte una cita buena en no literal."""
    from citebound.agent.graph import CARACTERES_POR_FUENTE

    cola = "esta frase está más allá del corte y sigue siendo del artículo"
    largo = Fuente(ref=parse(f"{NORMA}#art9"), texto="A" * CARACTERES_POR_FUENTE + " " + cola)
    borrador = f"CITAS\n[[REF:1]] «{cola}»\n\nRESPUESTA\nSí [[REF:1]].\n"
    final = list(
        servir(
            "¿y?",
            recuperador=lambda _: (largo,),
            generador=grabado(borrador),
            plantilla=PLANTILLA,
        )
    )[-1]
    assert isinstance(final, Resultado)
    assert final.curso.salida is Salida.RESPONDER
