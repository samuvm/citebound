"""Contract tests for `scripts/golden_sample.py` — quién entra en la cola de Samuel.

Este script no propone referencias: **decide qué preguntas ve Samuel**. Es la última pieza
barata antes de gastar sus 10-16 horas, y cada defecto aquí se paga en tiempo suyo que no se
recupera:

  · si una cuota se queda corta, la fase 1 no cierra **después** de que él haya anotado;
  · si dos preguntas casi iguales llegan a la cola y valida las dos, una hay que tirarla
    porque `G-GOLDEN-VALID` rechaza duplicados (coseno ≥ 0,95) — y se tira su tiempo, no el
    de nadie más;
  · si la muestra no es reproducible, no se puede decir de dónde salió el golden set.

**Los números no se inventan aquí.** El suelo sale de `GOALS.yaml` (`G-GOLDEN-VALID`) y el
factor de sobremuestreo de Q-004, que ratifica generar a **1,6 veces** justo para permitir
descartes. 190 filas clavadas con opción de descartar es aritméticamente inviable: un solo
descarte deja 149 positivos y la fase no cierra.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from scripts import golden_sample

RAIZ = Path(__file__).resolve().parents[2]


def fila(
    source_id: str,
    *,
    tema: str = "06 Uso de la via y Adelantamientos",
    cobertura: str = "rgc",
    imagen: str = "no",
    pregunta: str | None = None,
) -> dict[str, str]:
    return {
        "source_id": source_id,
        "pregunta": pregunta or f"¿Pregunta {source_id}?",
        "opcion_1": "a",
        "opcion_2": "b",
        "opcion_3": "c",
        "respuesta_correcta": "a",
        "tema": tema,
        "subtema": "un subtema",
        "pct_fallo": "10,5",
        "depende_imagen": imagen,
        "cobertura_rgc": cobertura,
    }


def banco(n_por_tema: int, temas: list[str], cobertura: str = "rgc") -> list[dict[str, str]]:
    return [
        fila(f"{cobertura}-{i}-{j}", tema=t, cobertura=cobertura)
        for i, t in enumerate(temas)
        for j in range(n_por_tema)
    ]


# --------------------------------------------------------------------------------------
# Quién es elegible
# --------------------------------------------------------------------------------------


def test_las_preguntas_que_necesitan_ver_la_foto_quedan_fuera() -> None:
    """193 preguntas (7,4 %) no se pueden responder sin la imagen, y las imágenes **no se
    redistribuyen** (Q-003). Una pregunta así en el golden set es un caso que el sistema
    nunca podrá acertar y que bajaría todas las métricas por una razón ajena al motor."""
    filas = [fila("a"), fila("b", imagen="si"), fila("c")]
    assert [f["source_id"] for f in golden_sample.usables(filas)] == ["a", "c"]


def test_los_positivos_salen_del_reglamento_y_los_negativos_de_fuera() -> None:
    filas = [fila("p", cobertura="rgc"), fila("n", cobertura="fuera"), fila("m", cobertura="mixto")]
    assert golden_sample.por_tipo(filas, "positivo") == [filas[0]]
    assert golden_sample.por_tipo(filas, "negativo") == [filas[1]]


def test_las_preguntas_mixtas_quedan_fuera_de_la_v1_y_no_en_silencio() -> None:
    """352 preguntas son de temas a caballo (motocicleta, transporte de personas). Meterlas
    exige clasificarlas caso a caso, que es trabajo de Samuel; quedan documentadas para una
    `v2` en vez de colarse en cualquiera de los dos montones."""
    filas = [fila("m", cobertura="mixto")]
    assert golden_sample.por_tipo(filas, "positivo") == []
    assert golden_sample.por_tipo(filas, "negativo") == []


# --------------------------------------------------------------------------------------
# Las cuotas salen de GOALS.yaml, no de aquí
# --------------------------------------------------------------------------------------


def test_el_objetivo_es_el_suelo_de_goals_por_el_factor_de_q004() -> None:
    """`G-GOLDEN-VALID` pide ≥150 positivos y ≥40 negativos; Q-004 ratifica generar a 1,6 veces
    para permitir rechazos. 150 por 1,6 = 240, y 40 por 1,6 = 64."""
    umbrales = golden_sample.umbrales()
    assert golden_sample.objetivo(umbrales.positivos_min) == 240
    assert golden_sample.objetivo(umbrales.negativos_min) == 64


def test_los_numeros_del_suelo_no_estan_escritos_en_el_script() -> None:
    """Misma lección que la semilla del bootstrap y que los umbrales de `golden_validate`:
    un 150 escrito aquí es una segunda fuente de verdad."""
    fuente = Path(golden_sample.__file__).read_text(encoding="utf-8")
    assert "150" not in fuente
    assert "240" not in fuente


def test_el_plan_reparte_el_objetivo_entre_los_temas_con_mas_material() -> None:
    """Se eligen los temas con más preguntas usables, no todos: un tema con 22 preguntas no
    puede aportar 30 casos, y forzarlo dejaría la cuota corta en silencio."""
    filas = banco(50, ["A", "B", "C"]) + banco(5, ["D"])
    plan = golden_sample.plan(filas, objetivo=60, temas_max=3)
    assert set(plan) == {"A", "B", "C"}
    assert sum(plan.values()) == 60
    assert "D" not in plan


def test_el_plan_cubre_el_minimo_de_materias_con_margen() -> None:
    """`G-GOLDEN-VALID` exige ≥6 materias con ≥20 casos **en el golden set final**, o sea
    después de los descartes de Samuel. Se muestrean más materias de las justas."""
    umbrales = golden_sample.umbrales()
    assert golden_sample.temas_objetivo(umbrales.materias_min) > umbrales.materias_min


def test_un_tema_sin_material_suficiente_se_dice_en_voz_alta() -> None:
    filas = banco(3, ["A", "B"])
    with pytest.raises(ValueError, match=r"material|suficiente"):
        golden_sample.plan(filas, objetivo=100, temas_max=2)


# --------------------------------------------------------------------------------------
# La muestra: reproducible y sin repetir
# --------------------------------------------------------------------------------------


def test_misma_semilla_misma_muestra() -> None:
    filas = banco(40, ["A", "B"])
    uno = golden_sample.muestrear(filas, plan={"A": 10, "B": 10}, tipo="positivo", semilla=7)
    dos = golden_sample.muestrear(filas, plan={"A": 10, "B": 10}, tipo="positivo", semilla=7)
    assert [c.source_id for c in uno] == [c.source_id for c in dos]


def test_semilla_distinta_muestra_distinta() -> None:
    filas = banco(40, ["A"])
    uno = golden_sample.muestrear(filas, plan={"A": 10}, tipo="positivo", semilla=1)
    dos = golden_sample.muestrear(filas, plan={"A": 10}, tipo="positivo", semilla=2)
    assert [c.source_id for c in uno] != [c.source_id for c in dos]


def test_la_muestra_respeta_la_cuota_de_cada_tema() -> None:
    filas = banco(40, ["A", "B"])
    muestra = golden_sample.muestrear(filas, plan={"A": 7, "B": 3}, tipo="positivo", semilla=1)
    assert sum(1 for c in muestra if c.tema == "A") == 7
    assert sum(1 for c in muestra if c.tema == "B") == 3


def test_ninguna_pregunta_entra_dos_veces() -> None:
    filas = banco(40, ["A", "B"])
    muestra = golden_sample.muestrear(filas, plan={"A": 20, "B": 20}, tipo="positivo", semilla=3)
    ids = [c.source_id for c in muestra]
    assert len(ids) == len(set(ids))


def test_los_identificadores_son_estables_y_ordenados() -> None:
    """El `id` viaja al golden set y de ahí a los informes. `gs-0001` no se reutiliza."""
    filas = banco(10, ["A"])
    muestra = golden_sample.muestrear(filas, plan={"A": 3}, tipo="positivo", semilla=1)
    assert [c.id for c in muestra] == ["gs-0001", "gs-0002", "gs-0003"]


def test_el_candidato_conserva_la_dificultad_empirica_y_su_procedencia() -> None:
    """`pct_fallo` es el porcentaje real de gente que falla la pregunta, medido sobre miles
    de intentos. Es mejor dato que la etiqueta `dificultad`, y viaja con el caso. El decimal
    del volcado usa coma."""
    muestra = golden_sample.muestrear(
        [fila("x", tema="A")], plan={"A": 1}, tipo="positivo", semilla=1
    )
    assert muestra[0].pct_fallo == pytest.approx(10.5)
    assert muestra[0].source_id == "x"


def test_el_negativo_no_lleva_referencia_que_proponer() -> None:
    """En un negativo la respuesta no está en el corpus: no hay artículo que proponer, y
    lo único que Samuel confirma es justamente eso."""
    filas = [fila("n", tema="A", cobertura="fuera")]
    muestra = golden_sample.muestrear(filas, plan={"A": 1}, tipo="negativo", semilla=1)
    assert muestra[0].tipo == "negativo"


# --------------------------------------------------------------------------------------
# Duplicados: se quitan ANTES de la cola, no después
# --------------------------------------------------------------------------------------


def test_dos_preguntas_casi_identicas_no_llegan_las_dos_a_la_cola() -> None:
    """`G-GOLDEN-VALID` las rechaza al final. Si llegan a la cola y Samuel valida las dos,
    una se tira **después** de haber gastado su tiempo. Se filtran antes."""
    filas = banco(3, ["A"])
    muestra = golden_sample.muestrear(filas, plan={"A": 3}, tipo="positivo", semilla=1)
    vectores = {c.id: [1.0, 0.0] for c in muestra}
    vectores[muestra[1].id] = [0.0, 1.0]  # solo el del medio es distinto
    conservados, tirados = golden_sample.deduplicar(muestra, vectores, umbral=0.95)
    assert len(conservados) == 2
    assert len(tirados) == 1


def test_deduplicar_conserva_el_primero_y_es_determinista() -> None:
    filas = banco(2, ["A"])
    muestra = golden_sample.muestrear(filas, plan={"A": 2}, tipo="positivo", semilla=1)
    vectores = {c.id: [1.0, 0.0] for c in muestra}
    conservados, _ = golden_sample.deduplicar(muestra, vectores, umbral=0.95)
    assert conservados == [muestra[0]]


def test_un_candidato_sin_vector_es_un_error_y_no_se_salta() -> None:
    filas = banco(2, ["A"])
    muestra = golden_sample.muestrear(filas, plan={"A": 2}, tipo="positivo", semilla=1)
    with pytest.raises(ValueError, match="vector"):
        golden_sample.deduplicar(muestra, {muestra[0].id: [1.0, 0.0]}, umbral=0.95)


# --------------------------------------------------------------------------------------
# El subconjunto a ciegas
# --------------------------------------------------------------------------------------


def test_se_marcan_exactamente_los_casos_a_ciegas_pedidos() -> None:
    """En estos Samuel **no ve** mi propuesta y deriva la referencia él. Mide dos cosas: mi
    tasa de acierto real y cuánto le estoy anclando al enseñarle una respuesta plausible
    antes de que piense. Un candidato malo se caza en dos segundos; uno plausible pero
    equivocado es el que se cuela con un «sí, vale»."""
    filas = banco(20, ["A", "B"])
    muestra = golden_sample.muestrear(filas, plan={"A": 10, "B": 10}, tipo="positivo", semilla=1)
    marcada = golden_sample.marcar_a_ciegas(muestra, n=4, semilla=1)
    assert sum(1 for c in marcada if c.a_ciegas) == 4


def test_los_casos_a_ciegas_no_caen_todos_en_el_mismo_tema() -> None:
    """Concentrados en un tema medirían la tasa de acierto de ese tema, no la del conjunto."""
    filas = banco(20, ["A", "B", "C", "D"])
    muestra = golden_sample.muestrear(
        filas, plan={"A": 10, "B": 10, "C": 10, "D": 10}, tipo="positivo", semilla=1
    )
    marcada = golden_sample.marcar_a_ciegas(muestra, n=8, semilla=1)
    temas = {c.tema for c in marcada if c.a_ciegas}
    assert len(temas) >= 3


def test_marcar_a_ciegas_es_reproducible() -> None:
    filas = banco(20, ["A", "B"])
    muestra = golden_sample.muestrear(filas, plan={"A": 10, "B": 10}, tipo="positivo", semilla=1)
    uno = golden_sample.marcar_a_ciegas(muestra, n=4, semilla=9)
    dos = golden_sample.marcar_a_ciegas(muestra, n=4, semilla=9)
    assert [c.a_ciegas for c in uno] == [c.a_ciegas for c in dos]


def test_no_se_pueden_marcar_mas_casos_a_ciegas_que_los_que_hay() -> None:
    filas = banco(3, ["A"])
    muestra = golden_sample.muestrear(filas, plan={"A": 3}, tipo="positivo", semilla=1)
    with pytest.raises(ValueError, match=r"a ciegas|ciegas"):
        golden_sample.marcar_a_ciegas(muestra, n=10, semilla=1)


# --------------------------------------------------------------------------------------
# Contra el banco de verdad
# --------------------------------------------------------------------------------------


def test_el_banco_real_da_para_el_objetivo_completo() -> None:
    """Si esto falla, la fase 1 no es viable con este banco y hay que saberlo **antes** de
    que Samuel reserve el calendario, no en mitad de su bloque."""
    filas = golden_sample.usables(golden_sample.leer(golden_sample.BANCO))
    umbrales = golden_sample.umbrales()
    positivos = golden_sample.por_tipo(filas, "positivo")
    negativos = golden_sample.por_tipo(filas, "negativo")

    plan_pos = golden_sample.plan(
        positivos,
        objetivo=golden_sample.objetivo(umbrales.positivos_min),
        temas_max=golden_sample.temas_objetivo(umbrales.materias_min),
    )
    plan_neg = golden_sample.plan(
        negativos, objetivo=golden_sample.objetivo(umbrales.negativos_min), temas_max=5
    )
    assert sum(plan_pos.values()) == 240
    assert sum(plan_neg.values()) == 64
    # Con los descartes de Samuel por delante, cada tema tiene que poder quedarse por encima
    # de los 20 casos que exige `materias_con_20_casos_o_mas`.
    assert min(plan_pos.values()) >= 20


def test_el_banco_real_tiene_las_columnas_que_este_script_espera() -> None:
    filas: list[dict[str, Any]] = golden_sample.leer(golden_sample.BANCO)
    assert len(filas) == 2597
    for columna in (
        "source_id",
        "pregunta",
        "tema",
        "pct_fallo",
        "depende_imagen",
        "cobertura_rgc",
    ):
        assert columna in filas[0]
