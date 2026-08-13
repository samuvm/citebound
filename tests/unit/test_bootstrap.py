"""Unit tests for `citebound.evals.bootstrap`.

**Se escriben y se congelan ANTES de anotar el primer caso del golden set** (`docs/PLAN.md`
fase 1a), por la misma razón que los de `scoring`: la puerta estadística decide qué cambio
se acepta y cuál se revierte, y cambiarla después de tener números publicados es cambiar el
criterio a posteriori.

Todo lo que se afirma aquí sale de dos sitios y de ninguna invención propia:

  · `docs/CONTRACTS/retrieval-metrics.md` §4 — bootstrap **pareado** sobre los mismos casos,
    10.000 réplicas, semilla registrada, y Holm-Bonferroni cuando se vigilan más de tres
    métricas bloqueantes. El contrato es compartido con `evalgate-02` e `indexkeeper-04`.
  · `docs/GOALS.yaml` bloque `comparacion` — donde vive la semilla, con el comentario
    «vive aqui, NUNCA en el codigo». De ahí sale el test más raro de este fichero
    (`test_la_semilla_no_esta_escrita_en_el_codigo`), que lee el fuente del módulo.

**Por qué pareado.** Se remuestrean los casos, no las ejecuciones: cada réplica toma
`head - base` sobre el **mismo** subconjunto. La varianza cae mucho y detectas cambios
menores con el mismo `n` — con 190 casos, la diferencia entre una puerta que sirve y una
que no distingue una regresión real del ruido.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from citebound.evals import bootstrap as modulo
from citebound.evals.bootstrap import (
    Intervalo,
    hay_regresion,
    holm,
    ic_diferencia_pareada,
)

# `n_resamples` y `semilla` son OBLIGATORIOS en la firma: un valor por defecto en el código
# es una segunda fuente de verdad que puede divergir de GOALS.yaml en silencio, que es el
# fallo que este proyecto ya se ha comido tres veces. Aquí se pasan explícitos, y los
# valores concretos son de test, no los del contrato.
RESAMPLES = 2_000
SEMILLA = 12345


# --------------------------------------------------------------------------------------
# La semilla no vive en el código
# --------------------------------------------------------------------------------------


def test_la_semilla_no_esta_escrita_en_el_codigo() -> None:
    """`GOALS.yaml` dice de la semilla: «vive aqui, NUNCA en el codigo».

    Un `semilla=20260808` por defecto convierte el contrato en decorativo: el día que
    Samuel cambie el número en `GOALS.yaml`, el informe seguiría diciendo 20260808 y
    nadie se enteraría. Este test lee el fuente del módulo, que es la única forma de
    comprobarlo sin confiar en la buena voluntad de quien lo escriba mañana.
    """
    fuente = Path(modulo.__file__).read_text(encoding="utf-8")
    assert "20260808" not in fuente


def test_semilla_y_n_resamples_son_obligatorios() -> None:
    """Sin valor por defecto: quien llama tiene que haber leído `GOALS.yaml`."""
    with pytest.raises(TypeError):
        ic_diferencia_pareada([0.5], [0.5])  # type: ignore[call-arg]


# --------------------------------------------------------------------------------------
# El intervalo, y su procedencia
# --------------------------------------------------------------------------------------


def test_muestras_identicas_dan_intervalo_exactamente_cero() -> None:
    """Si nada cambió, el IC es [0, 0]: no hay incertidumbre que remuestrear."""
    valores = [1.0, 0.0, 1.0, 1.0, 0.0, 1.0]
    ic = ic_diferencia_pareada(valores, valores, n_resamples=RESAMPLES, semilla=SEMILLA)
    assert ic.inferior == 0.0
    assert ic.superior == 0.0
    assert ic.punto == 0.0
    assert ic.contiene(0.0)


def test_el_punto_es_la_diferencia_observada_de_medias() -> None:
    base = [0.0, 1.0, 1.0, 0.0]  # media 0,5
    head = [1.0, 1.0, 1.0, 0.0]  # media 0,75
    ic = ic_diferencia_pareada(base, head, n_resamples=RESAMPLES, semilla=SEMILLA)
    assert ic.punto == pytest.approx(0.25)


def test_el_intervalo_registra_su_procedencia() -> None:
    """El informe tiene que poder decir con qué se calculó. Un IC sin `n` ni semilla no
    es reproducible por un tercero, que es el criterio de aceptación nº 2 del proyecto."""
    base = [0.0, 1.0, 1.0, 0.0]
    head = [1.0, 1.0, 1.0, 0.0]
    ic = ic_diferencia_pareada(base, head, n_resamples=RESAMPLES, semilla=SEMILLA)
    assert isinstance(ic, Intervalo)
    assert ic.n == 4
    assert ic.n_resamples == RESAMPLES
    assert ic.semilla == SEMILLA
    assert ic.nivel == 0.95


def test_contiene_responde_sobre_los_extremos_incluidos() -> None:
    ic = Intervalo(
        punto=0.1, inferior=-0.2, superior=0.4, n=10, n_resamples=10, semilla=1, nivel=0.95
    )
    assert ic.contiene(-0.2)
    assert ic.contiene(0.4)
    assert ic.contiene(0.0)
    assert not ic.contiene(-0.3)
    assert not ic.contiene(0.5)


def test_misma_semilla_mismo_intervalo() -> None:
    base = [0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0]
    head = [1.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0]
    uno = ic_diferencia_pareada(base, head, n_resamples=RESAMPLES, semilla=SEMILLA)
    dos = ic_diferencia_pareada(base, head, n_resamples=RESAMPLES, semilla=SEMILLA)
    assert uno == dos


def test_semilla_distinta_puede_dar_intervalo_distinto() -> None:
    """No es un capricho: si la semilla no entrara en el cálculo, `G-EVAL-DET` pasaría
    por accidente y no probaría nada."""
    base = [0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0]
    head = [1.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0]
    uno = ic_diferencia_pareada(base, head, n_resamples=RESAMPLES, semilla=1)
    dos = ic_diferencia_pareada(base, head, n_resamples=RESAMPLES, semilla=2)
    assert (uno.inferior, uno.superior) != (dos.inferior, dos.superior)


def test_nivel_configurable_y_registrado() -> None:
    base = [0.0, 1.0, 1.0, 0.0, 1.0, 0.0]
    head = [1.0, 1.0, 0.0, 0.0, 1.0, 1.0]
    ic = ic_diferencia_pareada(base, head, n_resamples=RESAMPLES, semilla=SEMILLA, nivel=0.99)
    assert ic.nivel == 0.99


# --------------------------------------------------------------------------------------
# Entradas que no son comparables se rechazan en voz alta
# --------------------------------------------------------------------------------------


def test_longitudes_distintas_es_error() -> None:
    """Pareado significa **los mismos casos**. Comparar 190 contra 187 da un número
    plausible sobre dos conjuntos distintos, y eso no se detecta mirando el resultado."""
    with pytest.raises(ValueError, match=r"pareado|mismos casos|longitud"):
        ic_diferencia_pareada([0.0, 1.0], [0.0, 1.0, 1.0], n_resamples=RESAMPLES, semilla=SEMILLA)


def test_sin_casos_es_error() -> None:
    with pytest.raises(ValueError, match=r"vac|sin casos"):
        ic_diferencia_pareada([], [], n_resamples=RESAMPLES, semilla=SEMILLA)


@pytest.mark.parametrize("n_resamples", [0, -1])
def test_n_resamples_no_positivo_es_error(n_resamples: int) -> None:
    with pytest.raises(ValueError, match="n_resamples"):
        ic_diferencia_pareada([0.5], [0.5], n_resamples=n_resamples, semilla=SEMILLA)


@pytest.mark.parametrize("nivel", [0.0, 1.0, -0.1, 1.5])
def test_nivel_fuera_del_intervalo_abierto_es_error(nivel: float) -> None:
    with pytest.raises(ValueError, match="nivel"):
        ic_diferencia_pareada([0.5], [0.5], n_resamples=RESAMPLES, semilla=SEMILLA, nivel=nivel)


# --------------------------------------------------------------------------------------
# La regla de la puerta, en los dos sentidos
# --------------------------------------------------------------------------------------


def test_regresion_cuando_el_intervalo_queda_entero_bajo_cero() -> None:
    """`GOALS.yaml`: bloquea si el IC95 de la diferencia pareada queda **enteramente**
    por debajo de cero. Con head peor en todos los casos, el IC es un punto negativo."""
    base = [0.9] * 20
    head = [0.5] * 20
    ic = ic_diferencia_pareada(base, head, n_resamples=RESAMPLES, semilla=SEMILLA)
    assert ic.superior < 0
    assert hay_regresion(ic, mayor_es_mejor=True)


def test_no_hay_regresion_cuando_head_mejora() -> None:
    base = [0.5] * 20
    head = [0.9] * 20
    ic = ic_diferencia_pareada(base, head, n_resamples=RESAMPLES, semilla=SEMILLA)
    assert ic.inferior > 0
    assert not hay_regresion(ic, mayor_es_mejor=True)


def test_no_hay_regresion_cuando_el_intervalo_cruza_cero() -> None:
    """Cruzar cero es «no se puede afirmar»: la puerta no bloquea por ruido."""
    base = [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0]
    head = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
    ic = ic_diferencia_pareada(base, head, n_resamples=RESAMPLES, semilla=SEMILLA)
    assert ic.contiene(0.0)
    assert not hay_regresion(ic, mayor_es_mejor=True)


def test_en_metricas_de_menor_es_mejor_la_regresion_es_subir() -> None:
    """`G-ABST-FP`, `G-TTFT`, `G-TTVA` y `G-COLD-CACHE` llevan operador `<=`: ahí una
    diferencia positiva es **empeorar**. El contrato redacta la regla para las métricas
    de mayor-es-mejor; el sentido se deriva del `operador` de la propia meta, no se
    inventa (JOURNAL 2026-08-13)."""
    base = [100.0] * 20  # ms
    head = [150.0] * 20  # más lento = peor
    ic = ic_diferencia_pareada(base, head, n_resamples=RESAMPLES, semilla=SEMILLA)
    assert ic.inferior > 0
    assert hay_regresion(ic, mayor_es_mejor=False)
    assert not hay_regresion(ic, mayor_es_mejor=True)


# --------------------------------------------------------------------------------------
# Holm-Bonferroni
# --------------------------------------------------------------------------------------


def test_holm_sin_metricas_devuelve_vacio() -> None:
    assert holm({}) == {}


def test_holm_con_una_metrica_es_comparar_contra_alfa() -> None:
    assert holm({"G-RECALL5": 0.04}, alfa=0.05) == {"G-RECALL5": True}
    assert holm({"G-RECALL5": 0.06}, alfa=0.05) == {"G-RECALL5": False}


def test_holm_conserva_todas_las_claves() -> None:
    p = {"a": 0.001, "b": 0.5, "c": 0.9, "d": 0.02}
    assert set(holm(p)) == set(p)


def test_holm_aplica_el_descenso_escalonado() -> None:
    """Con m=4 y alfa=0,05 los umbrales son 0,0125 · 0,0167 · 0,025 · 0,05.
    `a`=0,001 pasa el primero; `d`=0,02 falla el segundo (0,0167) y **corta**: `b` y `c`
    no se rechazan aunque se los mirara por separado."""
    veredicto = holm({"a": 0.001, "d": 0.02, "b": 0.5, "c": 0.9}, alfa=0.05)
    assert veredicto == {"a": True, "d": False, "b": False, "c": False}


def test_holm_corta_de_verdad_y_no_evalua_cada_una_por_su_cuenta() -> None:
    """El fallo clásico es comparar cada p con su propio umbral sin cortar. Aquí `c`
    tiene un p menor que su umbral individual (0,025) y aun así NO se rechaza, porque
    `b` rompió la cadena antes."""
    veredicto = holm({"a": 0.001, "b": 0.9, "c": 0.02}, alfa=0.05)
    assert veredicto["a"] is True
    assert veredicto["b"] is False
    assert veredicto["c"] is False


def test_holm_con_todo_a_uno_no_rechaza_nada() -> None:
    assert holm({"a": 1.0, "b": 1.0, "c": 1.0}) == {"a": False, "b": False, "c": False}


def test_holm_es_mas_potente_que_bonferroni() -> None:
    """Es el motivo escrito en `GOALS.yaml` para preferirlo. Todo lo que Bonferroni
    rechaza, Holm lo rechaza también."""
    p = {"a": 0.001, "b": 0.011, "c": 0.02, "d": 0.3}
    alfa = 0.05
    bonferroni = {k: v <= alfa / len(p) for k, v in p.items()}
    veredicto = holm(p, alfa=alfa)
    for clave, rechazada in bonferroni.items():
        if rechazada:
            assert veredicto[clave], clave


@pytest.mark.parametrize("alfa", [0.0, 1.0, -0.1, 2.0])
def test_holm_con_alfa_invalida_es_error(alfa: float) -> None:
    with pytest.raises(ValueError, match="alfa"):
        holm({"a": 0.01}, alfa=alfa)


@pytest.mark.parametrize("p", [-0.1, 1.1])
def test_holm_con_p_fuera_de_cero_uno_es_error(p: float) -> None:
    with pytest.raises(ValueError, match=r"p-valor|pvalor"):
        holm({"a": p})


def test_holm_admite_empates_sin_colgarse() -> None:
    veredicto = holm({"a": 0.01, "b": 0.01, "c": 0.01}, alfa=0.05)
    assert set(veredicto) == {"a", "b", "c"}


def test_el_modulo_no_deja_nombres_sueltos_sin_declarar() -> None:
    """`__all__` es el contrato del módulo con el runner de evals."""
    assert set(modulo.__all__) == {
        "Intervalo",
        "hay_regresion",
        "holm",
        "ic_diferencia_pareada",
    }
    assert not re.search(r"^import random$", Path(modulo.__file__).read_text("utf-8"), re.M)
