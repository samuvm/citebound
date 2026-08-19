"""El grafo por su **comportamiento observable**, con dobles grabados.

`docs/RULES.md` §3.1 pone `agent/graph.py` en TDD **prohibido** y dice con qué se sustituye:
integración determinista. La forma de un grafo la fija la librería; lo que hay que probar es que
el sistema reintenta cuando debe, se abstiene cuando debe, y **nunca emite algo que no verificó**.

`docs/PLAN.md` nombra los casos uno a uno y están todos abajo: reintento exitoso, reintento
agotado, error del proveedor, y corpus sin resultados.

Sin marca `integration` a propósito: no hay contenedor ni red, solo dobles. Es rápido y
determinista, así que puede vivir en el gate de turno.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from citebound.agent.graph import NO_PUEDO_RESPONDER, construir, responder
from citebound.domain.citation import Fuente, Motivo
from citebound.domain.legalref import parse
from citebound.domain.retry import MAX_REINTENTOS, Salida

NORMA = "RD-1428/2003"
ART34 = Fuente(
    ref=parse(f"{NORMA}#art34"),
    texto=(
        "Artículo 34. Cómputo de carriles.\n"
        "1. El número de carriles se contará de derecha a izquierda."
    ),
)
ART35 = Fuente(
    ref=parse(f"{NORMA}#art35"),
    texto="Artículo 35. Separación lateral.\n1. Se deberá guardar la separación necesaria.",
)
PLANTILLA = "PREGUNTA\n{pregunta}\n\nARTICULOS\n{fuentes}\n"

BUENO = (
    "Se cuentan de derecha a izquierda [[REF:1]].\n\n"
    "CITAS\n[[REF:1]] «El número de carriles se contará de derecha a izquierda»\n"
)
QUOTE_MALO = "Se cuentan al revés [[REF:1]].\n\nCITAS\n[[REF:1]] «esto no está en el artículo»\n"
FUERA_DE_RANGO = "Según [[REF:9]] sí.\n\nCITAS\n[[REF:9]] «El número de carriles»\n"
SIN_CITAS = "Se cuentan de derecha a izquierda, sin citar nada."


class Guion:
    """Un generador que devuelve lo que se le diga, en orden, y cuenta las llamadas."""

    def __init__(self, *borradores: str) -> None:
        self._borradores = list(borradores)
        self.llamadas = 0
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.llamadas += 1
        self.prompts.append(prompt)
        if not self._borradores:
            raise AssertionError("el grafo pidió más borradores de los grabados")
        return self._borradores.pop(0)


def corre(generador: Guion, fuentes: Sequence[Fuente] = (ART34, ART35)):
    grafo = construir(recuperador=lambda _: fuentes, generador=generador, plantilla=PLANTILLA)
    return responder(grafo, "¿Cómo se computan los carriles?")


# --------------------------------------------------------------------------------------
# El camino feliz, y lo que significa
# --------------------------------------------------------------------------------------


def test_un_borrador_verificado_sale_con_su_referencia_resuelta() -> None:
    resultado = corre(Guion(BUENO))
    assert resultado.curso.salida is Salida.RESPONDER
    assert resultado.curso.refs == (ART34.ref,)
    assert "[[REF:1]]" in resultado.respuesta
    assert resultado.curso.reintentos == 0


def test_la_referencia_la_resuelve_el_codigo_y_no_aparece_en_el_borrador() -> None:
    """**La tesis, comprobada de punta a punta.** El modelo escribió `[[REF:1]]` y en ningún
    momento `RD-1428/2003#art34`; la referencia sale de la fuente recuperada."""
    resultado = corre(Guion(BUENO))
    assert str(ART34.ref) not in resultado.borradores[0]
    assert resultado.curso.refs == (ART34.ref,)


def test_al_modelo_no_se_le_ensena_ningun_numero_de_articulo() -> None:
    """Si el prompt llevara «Artículo 34» junto a su marcador, el modelo tendría delante la
    forma de escribir una referencia. Ve `[1]` y el texto, y el texto es el del BOE."""
    generador = Guion(BUENO)
    corre(generador)
    prompt = generador.prompts[0]
    assert "[1]" in prompt and "[2]" in prompt
    assert str(ART34.ref) not in prompt


# --------------------------------------------------------------------------------------
# Reintento · los dos finales
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("malo", [QUOTE_MALO, FUERA_DE_RANGO, SIN_CITAS])
def test_un_borrador_malo_se_reintenta_y_el_segundo_sale(malo: str) -> None:
    generador = Guion(malo, BUENO)
    resultado = corre(generador)
    assert generador.llamadas == 2
    assert resultado.curso.salida is Salida.RESPONDER
    assert resultado.curso.reintentos == 1


def test_agotado_el_presupuesto_se_abstiene_y_no_emite_el_ultimo_borrador() -> None:
    """**El test que sostiene la tesis en el grafo.** Hay tres borradores escritos y ninguno
    sale, porque ninguno verificó. Emitir el último «porque es lo que hay» es exactamente lo
    que este proyecto no hace."""
    generador = Guion(QUOTE_MALO, QUOTE_MALO, QUOTE_MALO)
    resultado = corre(generador)
    assert generador.llamadas == MAX_REINTENTOS + 1
    assert resultado.curso.salida is Salida.ABSTENERSE
    assert resultado.curso.motivo is Motivo.QUOTE_NO_LITERAL
    assert resultado.respuesta == ""
    assert len(resultado.borradores) == 3


def test_nunca_se_llama_al_modelo_mas_de_tres_veces() -> None:
    """El tope vive en `domain.retry` y esto comprueba que el grafo lo respeta. Cada llamada
    de más es latencia dentro del presupuesto de `G-TTFT`."""
    generador = Guion(*[QUOTE_MALO] * 9)
    corre(generador)
    assert generador.llamadas == MAX_REINTENTOS + 1


# --------------------------------------------------------------------------------------
# Abstención · las dos formas
# --------------------------------------------------------------------------------------


def test_sin_fuentes_se_abstiene_sin_llamar_al_modelo_dos_veces() -> None:
    """Corpus sin resultados. El modelo no puede citar lo que no existe, así que reintentar es
    pagar latencia por un resultado ya conocido."""
    generador = Guion(SIN_CITAS)
    resultado = corre(generador, fuentes=())
    assert generador.llamadas == 1
    assert resultado.curso.salida is Salida.ABSTENERSE


def test_si_el_modelo_dice_que_no_puede_se_le_cree_a_la_primera() -> None:
    """Es la única forma que tiene de abstenerse por sí mismo. Insistir sería empujarle a
    inventar, que es justo lo contrario de lo que se le pide."""
    generador = Guion(f"{NO_PUEDO_RESPONDER}.")
    resultado = corre(generador)
    assert generador.llamadas == 1
    assert resultado.curso.salida is Salida.ABSTENERSE
    assert resultado.respuesta == ""


# --------------------------------------------------------------------------------------
# Cuando algo se rompe
# --------------------------------------------------------------------------------------


def test_un_error_del_proveedor_sale_como_error_y_no_como_abstencion() -> None:
    """Una abstención dice «el corpus no lo responde» y un error dice «el sistema falló».
    Confundirlos haría que `G-ABST-FP` contara caídas del proveedor como decisiones."""

    def revienta(prompt: str) -> str:
        raise RuntimeError("el proveedor no respondió")

    grafo = construir(recuperador=lambda _: (ART34,), generador=revienta, plantilla=PLANTILLA)
    with pytest.raises(RuntimeError, match="no respondió"):
        responder(grafo, "¿y esto?")


def test_un_error_del_recuperador_tampoco_se_disfraza() -> None:
    def revienta(pregunta: str):
        raise RuntimeError("la base no respondió")

    grafo = construir(recuperador=revienta, generador=Guion(BUENO), plantilla=PLANTILLA)
    with pytest.raises(RuntimeError, match="no respondió"):
        responder(grafo, "¿y esto?")
