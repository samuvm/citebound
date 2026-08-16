"""Contract tests for `citebound.providers.chat`, contra una grabación real.

`RULES` §3.1 pone `providers/` en **TDD prohibido**, y el motivo está escrito: escribir el test
antes de conocer la forma real de la respuesta produce un mock que codifica una API imaginada,
y el test verde certifica la imaginación. El orden correcto es el inverso — **grabar primero**
y testear contra la grabación.

`tests/recordings/chat-qwen35-4b.json` son dos llamadas de verdad al modelo, guardadas el
2026-08-17: una con `reasoning_effort="none"` y otra sin él. La segunda es la que documenta el
fallo que casi se cuela hasta la fase 3.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from citebound.providers.chat import ChatError, RecordedGenerador, Respuesta, _leer

GRABACION = json.loads(
    (Path(__file__).resolve().parents[1] / "recordings" / "chat-qwen35-4b.json").read_text(
        encoding="utf-8"
    )
)


def test_una_respuesta_real_se_lee_entera() -> None:
    r = _leer(GRABACION["sin_razonamiento"], esperado="qwen3.5:4b-mlx")
    assert r.texto == "82,85"
    assert r.modelo
    assert r.tokens_salida > 0


def test_el_razonamiento_activado_agota_los_tokens_y_se_detecta() -> None:
    """**El fallo que este test existe para que no vuelva.**

    `qwen3.5` es un modelo de razonamiento: emite su cadena de pensamiento en un campo aparte
    y se gasta el presupuesto de tokens **antes de contestar**. La grabación lo enseña:
    `finish_reason=length`, `content` vacío y el razonamiento lleno.

    Sin este control, el síntoma aguas abajo sería una respuesta en blanco y nadie sabría por
    qué. Y con el pensamiento activado `G-TTFT ≤ 1500 ms` es inalcanzable por construcción —
    medido: 4,0 s contra 0,2 s con `reasoning_effort="none"`.
    """
    with pytest.raises(ChatError, match=r"max_tokens|reasoning_effort"):
        _leer(GRABACION["con_razonamiento"], esperado="qwen3.5:4b-mlx")


def test_la_grabacion_demuestra_que_el_modelo_razona_por_defecto() -> None:
    """No es una hipótesis del docstring: está en el fichero grabado."""
    con = GRABACION["con_razonamiento"]["choices"][0]
    assert con["finish_reason"] == "length"
    assert not (con["message"].get("content") or "").strip()
    assert len(con["message"].get("reasoning") or "") > 100


def test_una_respuesta_sin_choices_se_rechaza() -> None:
    """Validar en vez de confiar: un proveedor que devuelve otra forma produciría texto
    plausible sobre otra cosa, y nada más abajo podría notarlo."""
    with pytest.raises(ChatError, match="choices"):
        _leer({"error": "modelo no encontrado"}, esperado="x")


def test_una_respuesta_que_no_es_un_objeto_se_rechaza() -> None:
    with pytest.raises(ChatError):
        _leer("500 Internal Server Error", esperado="x")


def test_el_razonamiento_se_conserva_aunque_venga_vacio() -> None:
    """Si un día vuelve a llenarse, es la señal de que alguien reactivó el pensamiento y de
    que el presupuesto de latencia se acaba de ir. Tirarlo sería tirar el aviso."""
    r = _leer(GRABACION["sin_razonamiento"], esperado="qwen3.5:4b-mlx")
    assert r.razonamiento == ""


# --------------------------------------------------------------------------------------
# El doble grabado, que es lo que hace testeable la fase 3
# --------------------------------------------------------------------------------------


def test_el_generador_grabado_reproduce_en_orden() -> None:
    doble = RecordedGenerador([Respuesta("uno", "m", "", 1), Respuesta("dos", "m", "", 1)])
    assert doble.completar("da igual").texto == "uno"
    assert doble.completar("da igual").texto == "dos"


def test_pedirle_mas_respuestas_de_las_grabadas_es_un_error() -> None:
    """Improvisar una respuesta convertiría el doble en un mock, que es justo lo que `RULES`
    §3.1 prohíbe: el test dejaría de probar el flujo real."""
    doble = RecordedGenerador([Respuesta("uno", "m", "", 1)])
    doble.completar("x")
    with pytest.raises(ChatError, match=r"grabación|grabacion"):
        doble.completar("x")
