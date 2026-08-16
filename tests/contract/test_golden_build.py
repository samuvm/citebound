"""Contract tests for `scripts/golden_build.py` — el montaje de `v1.jsonl` (fase `1d`).

Este script convierte tres ficheros de trabajo —la cola, las propuestas y los veredictos de
Samuel— en el único artefacto que el resto del proyecto consume. A partir de aquí, **todas**
las métricas del proyecto se miden contra lo que salga de aquí: recall, precisión de cita,
alucinación y abstención se anclan en estas referencias.

Por eso lo que se fija no es «que junte los ficheros», sino **qué se niega a montar**:

  · un caso descartado por Samuel no entra, y no hay forma de que entre por descuido;
  · un negativo que él marcó como respondible entra como POSITIVO, no como negativo — es el
    hallazgo de `1b` y perderlo aquí invertiría `G-ABST-FN`;
  · nada entra sin revisor y sin fecha, que es la regla dura nº 3 del contrato;
  · el conjunto se sella con su sha256, o el informe diría «0 errores» sobre un fichero que
    nadie sabe cuál era.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts import golden_build

RAIZ = Path(__file__).resolve().parents[2]
NORMA = "RD-1428/2003"


def caso(
    ident: str, *, tipo: str = "positivo", tema: str = "06 Adelantamientos"
) -> dict[str, object]:
    return {
        "id": ident,
        "source_id": f"s-{ident}",
        "pregunta": f"¿Pregunta {ident}?",
        "opciones": ["a", "b", "c"],
        "respuesta_correcta": "La correcta.",
        "tema": tema,
        "subtema": "un subtema",
        "pct_fallo": 12.5,
        "tipo": tipo,
        "a_ciegas": False,
    }


def ver(ident: str, *, que: str = "ok", ref: str | None = None) -> dict[str, object]:
    return {"id": ident, "veredicto": que, "ref": ref}


# --------------------------------------------------------------------------------------
# Qué NO entra
# --------------------------------------------------------------------------------------


def test_un_caso_descartado_no_entra() -> None:
    casos = golden_build.montar(
        [caso("gs-0001"), caso("gs-0002")],
        {"gs-0001": {"ref": f"{NORMA}#art82.2"}, "gs-0002": {"ref": f"{NORMA}#art83.1"}},
        [ver("gs-0001"), ver("gs-0002", que="descartar")],
        revisor="samuel",
    )
    assert [c.id for c in casos] == ["gs-0001"]


def test_un_caso_sin_veredicto_no_entra() -> None:
    """Regla dura nº 3 del contrato: ningún caso entra sin revisión humana. Un caso que Samuel
    no llegó a ver no es un caso revisado, por mucho que tenga propuesta."""
    casos = golden_build.montar(
        [caso("gs-0001"), caso("gs-0002")],
        {"gs-0001": {"ref": f"{NORMA}#art82.2"}, "gs-0002": {"ref": f"{NORMA}#art83.1"}},
        [ver("gs-0001")],
        revisor="samuel",
    )
    assert [c.id for c in casos] == ["gs-0001"]


def test_un_caso_saltado_tampoco_entra() -> None:
    casos = golden_build.montar(
        [caso("gs-0001")],
        {"gs-0001": {"ref": f"{NORMA}#art82.2"}},
        [ver("gs-0001", que="saltar")],
        revisor="samuel",
    )
    assert casos == []


def test_montar_sin_revisor_es_un_error() -> None:
    """El revisor no se deduce ni se deja en blanco: es el único punto donde el criterio de
    dominio de Samuel es insustituible, y el tipo lo exige."""
    with pytest.raises(ValueError, match=r"revisor"):
        golden_build.montar([caso("gs-0001")], {}, [ver("gs-0001")], revisor="")


# --------------------------------------------------------------------------------------
# El falso negativo que cambia de bando
# --------------------------------------------------------------------------------------


def test_un_negativo_que_el_corpus_si_responde_entra_como_positivo() -> None:
    """Seis de los 64 negativos resultaron ser respondibles (alcohol, drogas, deber de auxilio).
    Si entraran como negativos, `G-ABST-FN` contaría como fallo cada vez que el sistema
    respondiera bien: la métrica premiaría callarse justo donde hay que hablar."""
    casos = golden_build.montar(
        [caso("gs-0280", tipo="negativo")],
        {"gs-0280": {"negativo": False, "responde": f"{NORMA}#art129.3"}},
        [ver("gs-0280")],
        revisor="samuel",
    )
    assert casos[0].tipo.value == "positivo"
    assert str(casos[0].refs[0]) == f"{NORMA}#art129.3"
    assert casos[0].respuesta_referencia


def test_un_negativo_confirmado_entra_sin_referencias() -> None:
    casos = golden_build.montar(
        [caso("gs-0290", tipo="negativo")],
        {"gs-0290": {"negativo": True, "responde": None}},
        [ver("gs-0290")],
        revisor="samuel",
    )
    assert casos[0].tipo.value == "negativo"
    assert casos[0].refs == []
    assert casos[0].respuesta_referencia is None


# --------------------------------------------------------------------------------------
# La referencia que manda es la de Samuel
# --------------------------------------------------------------------------------------


def test_una_correccion_gana_a_la_propuesta_del_agente() -> None:
    casos = golden_build.montar(
        [caso("gs-0286")],
        {"gs-0286": {"ref": f"{NORMA}#art129.2"}},
        [ver("gs-0286", que="corregir", ref=f"{NORMA}#art129.2.f")],
        revisor="samuel",
    )
    assert str(casos[0].refs[0]) == f"{NORMA}#art129.2.f"


def test_un_ok_conserva_la_propuesta_del_agente() -> None:
    casos = golden_build.montar(
        [caso("gs-0001")],
        {"gs-0001": {"ref": f"{NORMA}#art82.2"}},
        [ver("gs-0001")],
        revisor="samuel",
    )
    assert str(casos[0].refs[0]) == f"{NORMA}#art82.2"


# --------------------------------------------------------------------------------------
# Los campos que el contrato exige
# --------------------------------------------------------------------------------------


def test_todo_caso_sale_con_revisor_fecha_y_procedencia() -> None:
    casos = golden_build.montar(
        [caso("gs-0001")],
        {"gs-0001": {"ref": f"{NORMA}#art82.2"}},
        [ver("gs-0001")],
        revisor="samuel",
    )
    c = casos[0]
    assert c.revisado_por == "samuel"
    assert c.revisado_en is not None
    assert c.provenance.value == "llm_generado_revisado_humano"


def test_la_dificultad_sale_del_porcentaje_de_fallo_real() -> None:
    """El contrato pide el campo `dificultad`, que es un juicio. El banco trae `pct_fallo`,
    medido sobre miles de intentos. Se deriva del dato en vez de inventarlo, y los dos viajan
    juntos: el contrato se cumple y la realidad se conserva."""
    assert golden_build.dificultad_de(3.0).value == "facil"
    assert golden_build.dificultad_de(12.0).value == "media"
    assert golden_build.dificultad_de(40.0).value == "dificil"


def test_el_orden_de_los_casos_es_estable() -> None:
    """El sha256 del conjunto tiene que ser reproducible: si el orden bailara, el sello
    cambiaría sin que cambiara ni un caso."""
    entrada = (
        [caso("gs-0002"), caso("gs-0001")],
        {"gs-0001": {"ref": f"{NORMA}#art82.2"}, "gs-0002": {"ref": f"{NORMA}#art83.1"}},
        [ver("gs-0001"), ver("gs-0002")],
    )
    uno = golden_build.montar(*entrada, revisor="samuel")
    dos = golden_build.montar(*entrada, revisor="samuel")
    assert [c.id for c in uno] == [c.id for c in dos] == ["gs-0001", "gs-0002"]


# --------------------------------------------------------------------------------------
# El sello y el desglose
# --------------------------------------------------------------------------------------


def test_el_jsonl_se_sella_con_su_sha256(tmp_path: Path) -> None:
    casos = golden_build.montar(
        [caso("gs-0001")],
        {"gs-0001": {"ref": f"{NORMA}#art82.2"}},
        [ver("gs-0001")],
        revisor="samuel",
    )
    destino = tmp_path / "v1.jsonl"
    sello = golden_build.escribir(casos, destino)
    assert len(sello) == 64
    assert destino.is_file()
    # El sello es del fichero, no de la lista en memoria: si no, no sirve para verificar nada.
    import hashlib

    assert sello == hashlib.sha256(destino.read_bytes()).hexdigest()


def test_cada_linea_del_jsonl_vuelve_a_validar_contra_el_esquema(tmp_path: Path) -> None:
    """Ida y vuelta: lo escrito se puede releer como `CasoGolden`. Sin esto, `golden-validate`
    fallaría el día del cierre y no el día de la construcción."""
    from citebound.evals.schema import CasoGolden

    casos = golden_build.montar(
        [caso("gs-0001")],
        {"gs-0001": {"ref": f"{NORMA}#art82.2"}},
        [ver("gs-0001")],
        revisor="samuel",
    )
    destino = tmp_path / "v1.jsonl"
    golden_build.escribir(casos, destino)
    for linea in destino.read_text(encoding="utf-8").splitlines():
        CasoGolden.model_validate(json.loads(linea))


def test_el_desglose_por_materia_cuenta_lo_que_el_gate_va_a_mirar() -> None:
    casos = golden_build.montar(
        [caso(f"gs-{i:04d}", tema="A" if i < 3 else "B") for i in range(5)],
        {f"gs-{i:04d}": {"ref": f"{NORMA}#art82.2"} for i in range(5)},
        [ver(f"gs-{i:04d}") for i in range(5)],
        revisor="samuel",
    )
    estratos = golden_build.estratos(casos)
    assert estratos["por_materia"]["A"] == 3
    assert estratos["positivos"] == 5
