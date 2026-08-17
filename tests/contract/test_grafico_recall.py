"""El gráfico del README sale del informe medido, y estos tests lo sujetan.

Un gráfico es una **copia** del número, y las copias se quedan viejas sin que nada lo note.
Que se dibuje desde `evals/reports/retrieval-latest.json` quita el riesgo de transcripción;
lo que queda por sujetar es que la barra corresponda al valor y que el umbral que dibuja sea
el que exige `docs/GOALS.yaml` — porque una línea de umbral mal puesta enseña «casi llega»
donde el gate dice rojo, y eso es peor que no dibujar nada.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from scripts.grafico_recall import BARRA, IZQUIERDA, UMBRAL, barras

RAIZ = Path(__file__).resolve().parents[2]

POR_CANAL = {
    "solo_vectorial": {"recall5": 0.792, "recall30": 0.954},
    "solo_lexico": {"recall5": 0.370, "recall30": 0.815},
    "fusion_y_reordenador": {"recall5": 0.856, "recall30": 0.977},
}


def test_el_umbral_que_dibuja_es_el_que_exige_goals() -> None:
    """**El test que de verdad importa aquí.** Si el gráfico dibujara su propio umbral, el
    README podría enseñar una barra pasada mientras el gate la da por roja, y nadie miraría
    los dos sitios a la vez."""
    metas = yaml.safe_load((RAIZ / "docs" / "GOALS.yaml").read_text(encoding="utf-8"))["metas"]
    de_goals = {
        f"recall{m['id'].removeprefix('G-RECALL')}": float(m["umbral"]["valor"])
        for m in metas
        if m["id"] in ("G-RECALL5", "G-RECALL30")
    }
    assert de_goals == UMBRAL


def test_la_barra_es_proporcional_al_valor() -> None:
    svg = barras({"solo_vectorial": {"recall5": 0.5, "recall30": 1.0}}, 216, "v1-x")
    assert f'width="{BARRA * 0.5:.1f}"' in svg
    assert f'width="{BARRA * 1.0:.1f}"' in svg


def test_un_cero_sigue_dibujando_algo_visible() -> None:
    """Una barra de ancho 0 es indistinguible de «no se midió». Un mínimo de 1 px dice
    «se midió y salió cero», que no es lo mismo."""
    assert 'width="1.0"' in barras({"solo_lexico": {"recall5": 0.0}}, 216, "v1-x")


def test_el_valor_se_escribe_con_coma_como_todo_el_repositorio() -> None:
    assert "0,792" in barras(POR_CANAL, 216, "v1-x")


def test_marca_las_metas_que_pasan_y_no_las_que_no() -> None:
    svg = barras(POR_CANAL, 216, "v1-x")
    assert "0,977  ✓" in svg, "recall30 pasa su umbral y el gráfico debería decirlo"
    assert "0,856  ✓" not in svg, "recall5 no llega a 0,90 y el gráfico no puede sugerir que sí"


def test_el_grafico_declara_sobre_que_indice_se_midio() -> None:
    """Misma exigencia que el contrato pone al informe: sin el índice, dos gráficos sobre
    datos distintos son indistinguibles."""
    assert "v1-qwen3-embedding-0.6b-1024" in barras(POR_CANAL, 216, "v1-qwen3-embedding-0.6b-1024")
    assert "216 preguntas" in barras(POR_CANAL, 216, "v1-x")


def test_es_un_svg_bien_formado() -> None:
    import xml.etree.ElementTree as ET

    raiz = ET.fromstring(barras(POR_CANAL, 216, "v1-x"))  # noqa: S314
    assert raiz.tag.endswith("svg")
    assert IZQUIERDA > 0


def test_un_canal_que_el_informe_no_trae_simplemente_no_se_dibuja() -> None:
    """El informe sin reordenador no tiene `fusion_y_reordenador`. Eso no es un error: es
    que esa corrida no lo midió, y dibujar una barra vacía sería inventarse un cero."""
    svg = barras({"solo_vectorial": {"recall5": 0.792, "recall30": 0.954}}, 216, "v1-x")
    assert "Híbrido + reordenador" not in svg
    assert "Solo vectorial" in svg
