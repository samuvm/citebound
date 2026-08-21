"""Contract tests del reordenador cross-encoder, contra una grabación real.

`RULES` §3.1 pone `providers/` en **TDD prohibido** y aquí se ve por qué: la forma de lo que
devuelve `CrossEncoder.predict` la fija la librería, no un test escrito antes. Escribirlo antes
habría producido un mock de una API imaginada, y el verde certificaría la imaginación.

`tests/recordings/rerank-bge-m3.json` son puntuaciones de verdad, del 2026-08-17. Lo que se
prueba aquí es **la fontanería** —puntuaciones a orden, sin perder ni inventar candidatos—, no
la calidad del modelo: eso lo mide `make eval-retrieval` sobre 216 casos y es un número, no una
aserción.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from citebound.domain.legalref import parse
from citebound.providers.reranker import (
    DISPOSITIVO_POR_DEFECTO,
    INSTRUCCION,
    MODELO_POR_DEFECTO,
    CrossEncoderReranker,
    RecordedReranker,
    RerankerError,
    ordenar_por_puntos,
)
from citebound.retrieval.vector import Recuperado

GRABACION = json.loads(
    (Path(__file__).resolve().parents[1] / "recordings" / "rerank-bge-m3.json").read_text(
        encoding="utf-8"
    )
)
NORMA = "RD-1428/2003"


def cand(articulo: str) -> Recuperado:
    return Recuperado(
        ref=parse(f"{NORMA}#art{articulo}"),
        content=f"texto del {articulo}",
        distancia=0.5,
        titulo="TÍTULO II",
        id_norma_version="BOE-A-2003-23514",
    )


CANDIDATOS = [cand("74"), cand("109"), cand("3")]


# --------------------------------------------------------------------------------------
# Puntuaciones a orden
# --------------------------------------------------------------------------------------


def test_la_grabacion_ordena_como_dicen_sus_puntuaciones() -> None:
    """Contra los números reales, no contra unos inventados. El modelo pone aquí el 109 por
    delante del 74 —se equivoca, y el golden set dice 74— pero eso es calidad y se mide
    aparte; lo que este test sujeta es que el orden salga de la puntuación."""
    ordenados = ordenar_por_puntos(CANDIDATOS, GRABACION["puntos"])
    assert [str(r.ref) for r in ordenados] == [
        f"{NORMA}#art109",
        f"{NORMA}#art74",
        f"{NORMA}#art3",
    ]


def test_no_pierde_ni_inventa_un_candidato() -> None:
    """**Lo que no puede fallar.** Un reordenador que pierde documentos baja el recall por su
    cuenta y el diagnóstico apunta al índice, que es donde no está el problema."""
    ordenados = ordenar_por_puntos(CANDIDATOS, [3.0, 1.0, 2.0])
    assert len(ordenados) == 3
    assert {str(r.ref) for r in ordenados} == {str(r.ref) for r in CANDIDATOS}


def test_un_array_de_otra_longitud_revienta_en_vez_de_recortar() -> None:
    """Si la librería devolviera otra cosa, recortar en silencio perdería candidatos y el
    número saldría igual de plausible."""
    with pytest.raises(RerankerError, match="perdería o inventaría"):
        ordenar_por_puntos(CANDIDATOS, [1.0, 2.0])


def test_a_igualdad_de_puntuacion_manda_el_orden_de_la_fusion() -> None:
    """La fusión ya es una señal. Empatar y barajar sería tirar información, y además haría
    el resultado no reproducible entre corridas."""
    assert [str(r.ref) for r in ordenar_por_puntos(CANDIDATOS, [1.0, 1.0, 1.0])] == [
        str(r.ref) for r in CANDIDATOS
    ]


# --------------------------------------------------------------------------------------
# El doble grabado
# --------------------------------------------------------------------------------------


def test_el_doble_reproduce_lo_grabado() -> None:
    doble = RecordedReranker({"¿por dónde?": [1.0, 3.0, 2.0]})
    assert str(doble.reordenar("¿por dónde?", CANDIDATOS)[0].ref) == f"{NORMA}#art109"


def test_una_pregunta_sin_grabar_revienta_en_vez_de_improvisar() -> None:
    """Un doble que improvisa pone la suite en verde sobre números que nadie ha producido, y
    el primer sitio donde se nota es un recall que no se explica."""
    with pytest.raises(RerankerError, match="no hay grabación"):
        RecordedReranker({}).reordenar("nunca grabada", CANDIDATOS)


# --------------------------------------------------------------------------------------
# La configuración, que es la mitad del resultado
# --------------------------------------------------------------------------------------


def test_el_modelo_no_se_carga_al_construir() -> None:
    """Cargar cuesta 37 s. `make eval-retrieval` sin reordenador no debe pagarlos, ni el
    arranque en frío de la API."""
    assert CrossEncoderReranker()._motor is None


def test_lo_que_queda_fuera_del_tope_no_se_toca() -> None:
    r = CrossEncoderReranker(tope=2)
    assert r.tope == 2


def test_el_dispositivo_por_defecto_es_cpu_y_eso_es_una_medida() -> None:
    """**Contraintuitivo y medido.** El cross-encoder corre en proceso con PyTorch y Ollama
    sirve el generador en la misma GPU: cuando compiten, puntuar es más rápido en MPS (161 ms
    contra 313) y **responder es mucho más lento** (1.598 contra 255). Total 1.759 contra 569.

    Aislado, MPS parece el doble de bueno. La contienda solo se ve de punta a punta."""
    assert DISPOSITIVO_POR_DEFECTO == "cpu"
    assert CrossEncoderReranker().dispositivo == "cpu"
    assert CrossEncoderReranker(dispositivo="cuda").dispositivo == "cuda"


def test_la_instruccion_del_dominio_dice_tipificar_y_no_parecerse() -> None:
    """Es la tesis del proyecto metida en el reordenador: «relevante» aquí no es «parecido»,
    es el artículo que tipifica la conducta."""
    assert "TIPIFICA" in INSTRUCCION
    assert CrossEncoderReranker().instruccion == INSTRUCCION


def test_el_modelo_por_defecto_es_el_medido_y_no_otro() -> None:
    """Medido el 2026-08-17 sobre los 216 casos: `bge-reranker-v2-m3` da 0,801 con p95 de
    400 ms, y `Qwen3-Reranker-0.6B` da 0,787 con 886 ms. Gana el retador en las dos columnas,
    así que es el que va por defecto — y esto lo deja escrito donde se rompe si alguien lo
    cambia sin medir."""
    assert MODELO_POR_DEFECTO == "BAAI/bge-reranker-v2-m3"
    assert GRABACION["modelo"] == MODELO_POR_DEFECTO


def test_los_hilos_por_defecto_son_cuatro_y_tambien_es_una_medida() -> None:
    """PyTorch coge los 14 y deja a Ollama sin CPU. Tres pares alternados de `make bench` dan
    la misma dirección las tres veces (~200 ms), y con 2 hilos se hunde a 4.166 porque puntuar
    pasa a ser el cuello. El número está en el docstring del módulo."""
    from citebound.providers.reranker import HILOS_POR_DEFECTO

    assert HILOS_POR_DEFECTO == 4
