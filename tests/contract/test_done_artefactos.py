"""Contract tests: el gate tiene que saber leer los artefactos que `GOALS.yaml` declara.

**El defecto que estos tests cierran.** `_leer_artefacto` sabía leer exactamente dos cosas:
`eval-latest.json` para cualquier métrica, y `gate-status.json` **solo** para `G-SECRETS`.
Todo lo demás devolvía `None`, y un `None` es rojo. Consecuencia medida el 2026-08-13:
`make done MILESTONE=1` no podía ponerse verde **jamás**, ni con el golden set perfecto,
porque `G-COV-FUNC` y `G-GOLDEN-VALID` no encontraban su número. Peor que roja: la condición
4 ejecutaba el comprobador y **pasaba**, así que la misma verdad daba verde por un camino y
rojo por el otro.

`GOALS.yaml` escribe sus artefactos con una sintaxis, `fichero :: ruta.punteada`, y el gate
tiene que entenderla entera en vez de llevar un `if` por meta. Hoy hay cuatro rutas que
apuntan a `gate-status.json` y dos formas distintas de selector; mañana habrá más, y una
meta cuyo artefacto nadie sabe leer es una meta que no existe.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from scripts import done

RAIZ = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------------------
# La sintaxis de `artefacto`, tal como la escribe GOALS.yaml
# --------------------------------------------------------------------------------------


def test_una_ruta_punteada_llega_al_valor_anidado() -> None:
    datos = {"coverage": {"functions_without_test": 3}}
    assert done.seleccionar(datos, "coverage.functions_without_test") == 3


def test_una_clave_de_primer_nivel_tambien_vale() -> None:
    assert done.seleccionar({"errores": 0}, "errores") == 0


def test_un_selector_de_metrica_por_id_encuentra_la_suya() -> None:
    """La forma `metrics[id=X].value` es la que usan las once metas que leen un informe."""
    datos = {"metrics": [{"id": "G-RECALL5", "value": 0.91}, {"id": "G-RECALL30", "value": 0.98}]}
    assert done.seleccionar(datos, "metrics[id=G-RECALL30].value") == 0.98


def test_una_clave_que_no_esta_devuelve_none_y_no_revienta() -> None:
    """`None` es rojo, que es lo correcto. Un `KeyError` a mitad del gate deja las
    condiciones siguientes sin evaluar y esconde el resto de los problemas."""
    assert done.seleccionar({"a": 1}, "b.c") is None
    assert done.seleccionar({"metrics": []}, "metrics[id=G-NO-EXISTE].value") is None


def test_el_parentesis_explicativo_no_forma_parte_del_selector() -> None:
    """Dos artefactos de `GOALS.yaml` llevan una aclaración entre paréntesis —
    `totals.percent_covered (filtrado a [tool.gate].testable)` y `kappa (con ci95)`— que es
    para quien lee, no para el que busca la clave."""
    ruta, selector = done.partir_artefacto("coverage.json :: totals.percent_covered (filtrado a X)")
    assert ruta == "coverage.json"
    assert selector == "totals.percent_covered"


def test_partir_separa_fichero_y_selector() -> None:
    ruta, selector = done.partir_artefacto("evals/golden/VALIDATION.json :: errores")
    assert ruta == "evals/golden/VALIDATION.json"
    assert selector == "errores"


def test_un_artefacto_que_no_es_json_se_reconoce_como_tal() -> None:
    """`G-REVERSION` apunta a `docs/JOURNAL.md` más `.snapshots/`: no hay selector que
    valga. Tiene su propio comando y el lector genérico no debe fingir que lo entiende."""
    assert done.partir_artefacto("docs/JOURNAL.md (marca <!-- reversion -->) + .snapshots/") is None


# --------------------------------------------------------------------------------------
# Lo que el gate mide en esta misma corrida, no en la anterior
# --------------------------------------------------------------------------------------


def test_lo_medido_en_esta_corrida_gana_al_fichero_del_disco() -> None:
    """**El orden importa y es la razón de que esto no se lea del fichero.** La condición 7
    corre ANTES de que se escriba `gate-status.json`, así que leer el fichero daría el
    número de la corrida ANTERIOR — el gate se aprobaría a sí mismo con datos viejos, que
    es la misma familia de fallo que `G-MUT` leyendo su caché."""
    done.MEDIDO.clear()
    done.MEDIDO["coverage.functions_without_test"] = 0
    assert (
        done.leer_artefacto_ruta(
            ".claude/state/gate-status.json", "coverage.functions_without_test"
        )
        == 0
    )


def test_un_valor_no_medido_todavia_es_none_y_por_tanto_rojo() -> None:
    done.MEDIDO.clear()
    assert done.leer_artefacto_ruta(".claude/state/gate-status.json", "eval_determinista") is None


def test_lo_medido_acaba_escrito_en_el_estado_con_la_forma_que_goals_espera() -> None:
    """`secrets.new_findings` y `coverage.functions_without_test` son rutas punteadas: en el
    fichero tienen que ser objetos anidados, no claves con un punto en el nombre."""
    done.MEDIDO.clear()
    done.MEDIDO["secrets.new_findings"] = 0
    done.MEDIDO["coverage.functions_without_test"] = 2
    estado = done.medido_anidado()
    assert estado == {"secrets": {"new_findings": 0}, "coverage": {"functions_without_test": 2}}


# --------------------------------------------------------------------------------------
# Contra el GOALS.yaml de verdad, que es lo que de verdad hay que saber leer
# --------------------------------------------------------------------------------------


def test_el_gate_sabe_partir_el_artefacto_de_todas_las_metas_bloqueantes() -> None:
    """Una meta cuyo artefacto nadie sabe leer es una meta que no existe. `G-REVERSION` es
    la única excepción legítima, y por eso se nombra aquí en vez de dejarse pasar."""
    metas = yaml.safe_load((RAIZ / "docs" / "GOALS.yaml").read_text(encoding="utf-8"))["metas"]
    bloqueantes = [m for m in metas if m["bloqueante_desde_fase"] is not None]
    sin_lector = [
        m["id"] for m in bloqueantes if done.partir_artefacto(str(m["artefacto"])) is None
    ]
    assert sin_lector == ["G-REVERSION"]


@pytest.mark.parametrize("meta_id", ["G-GOLDEN-VALID", "G-COV-FUNC", "G-COV-LINE", "G-MUT"])
def test_las_metas_que_bloquean_en_la_fase_1_apuntan_a_algo_legible(meta_id: str) -> None:
    """Las cuatro que han dejado —o iban a dejar— un `make done` en rojo perpetuo por
    fontanería: `G-GOLDEN-VALID` y `G-COV-FUNC` en la fase 1, `G-COV-LINE` en la 2, y `G-MUT`
    que habría esperado a la 3 para descubrirse."""
    metas = yaml.safe_load((RAIZ / "docs" / "GOALS.yaml").read_text(encoding="utf-8"))["metas"]
    meta = next(m for m in metas if m["id"] == meta_id)
    partido = done.partir_artefacto(str(meta["artefacto"]))
    assert partido is not None
    ruta, selector = partido
    assert ruta and selector


def test_un_informe_real_en_disco_se_lee_por_su_ruta(tmp_path: Path) -> None:
    fichero = tmp_path / "VALIDATION.json"
    fichero.write_text(json.dumps({"errores": 0, "n": 190}), encoding="utf-8")
    assert done.leer_artefacto_ruta(str(fichero), "errores") == 0


def test_un_fichero_que_no_existe_es_none_no_una_excepcion() -> None:
    assert done.leer_artefacto_ruta("evals/reports/no-existe.json", "lo.que.sea") is None


def test_un_artefacto_que_calcula_esta_corrida_gana_al_disco() -> None:
    """`G-COV-LINE` dejaba `make done MILESTONE=2` en rojo perpetuo por fontanería, igual que
    antes `G-GOLDEN-VALID` y `G-COV-FUNC`.

    Su artefacto es `coverage.json :: totals.percent_covered (filtrado a [tool.gate].testable)`,
    y el paréntesis es la instrucción, no un adorno: el `totals` del fichero mide
    `src/citebound` entero —`api/`, `db/` y `providers/` incluidos, que están excluidos a
    propósito— así que **el número del fichero no es el de la meta**. La condición 5 calcula el
    bueno; esto es lo que hace que la 7 lea ese y no otro.
    """
    done.CALCULADO.clear()
    try:
        assert done.leer_artefacto_ruta("coverage.json", "totals.percent_covered") is None
        done.CALCULADO[("coverage.json", "totals.percent_covered")] = 100
        assert done.leer_artefacto_ruta("coverage.json", "totals.percent_covered") == 100
    finally:
        done.CALCULADO.clear()


def test_la_meta_de_cobertura_de_linea_apunta_a_algo_que_el_gate_sabe_leer() -> None:
    """El otro lado del mismo fallo: que la clave con la que la condición 5 publica sea
    exactamente la que `GOALS.yaml` nombra. Si una de las dos se moviera, el gate volvería a
    quedarse sin número y `G-COV-LINE` sería roja para siempre sin que nada dijera por qué."""
    metas = yaml.safe_load((RAIZ / "docs" / "GOALS.yaml").read_text(encoding="utf-8"))["metas"]
    meta = next(m for m in metas if m["id"] == "G-COV-LINE")
    assert done.partir_artefacto(str(meta["artefacto"])) == (
        "coverage.json",
        "totals.percent_covered",
    )


# --------------------------------------------------------------------------------------
# G-MUT: una medida caducada no se da por buena
# --------------------------------------------------------------------------------------


def test_sin_ninguna_corrida_de_mutacion_la_medida_esta_caducada(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """«Una condición que no se puede comprobar es roja, nunca verde»."""
    monkeypatch.setattr(done, "RAIZ", Path("/no/existe/en/ningun/sitio"))
    assert done.mutacion_caducada() == "no hay ninguna corrida de mutación"


def test_un_test_mas_nuevo_que_la_mutacion_caduca_la_medida(tmp_path: Path) -> None:
    """El defecto exacto que esto cierra: mutmut invalida su caché al cambiar `src/`, pero
    **no** al cambiar los tests. El gate llevaba desde el 10 de agosto publicando un
    `587/588` calculado sobre un código que ya no existía."""
    (tmp_path / "mutants").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    reciente = tmp_path / "tests" / "test_algo.py"
    reciente.write_text("# escrito después de medir\n", encoding="utf-8")
    import os

    marca = (tmp_path / "mutants").stat().st_mtime
    os.utime(reciente, (marca + 60, marca + 60))

    original = done.RAIZ
    try:
        done.RAIZ = tmp_path  # type: ignore[misc]
        assert done.mutacion_caducada() == "tests/test_algo.py es más nuevo que la última mutación"
    finally:
        done.RAIZ = original  # type: ignore[misc]


def test_con_todo_anterior_a_la_mutacion_la_medida_vale(tmp_path: Path) -> None:
    import os

    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    viejo = tmp_path / "src" / "cosa.py"
    viejo.write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "mutants").mkdir()
    marca = viejo.stat().st_mtime
    os.utime(tmp_path / "mutants", (marca + 60, marca + 60))

    original = done.RAIZ
    try:
        done.RAIZ = tmp_path  # type: ignore[misc]
        assert done.mutacion_caducada() is None
    finally:
        done.RAIZ = original  # type: ignore[misc]
