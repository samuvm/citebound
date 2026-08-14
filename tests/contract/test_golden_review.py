"""Contract tests for `scripts/golden_review.py` — la cola de revisión de Samuel.

Esto es lo único de la fase 1 que Samuel toca con las manos, y son 10-16 horas suyas. Cada
defecto aquí no cuesta un test rojo: cuesta tiempo que no se recupera. De ahí lo que se fija:

**Se guarda cada veredicto, no al final.** El fichero es JSONL append-only. Si se cierra el
portátil en el caso 137, se han perdido cero minutos y se reanuda por el 138.

**El ritmo se mide mientras se anota, no después.** Q-004 ratifica que si en los primeros
casos no se baja de 3 min/caso, el agente **para y rediseña la cola** — «es la diferencia
entre 10 h y 25 h, y hay que detectarla en el minuto 60, no en la hora 12». Una regla que
solo se comprueba al terminar no sirve para nada.

**Los casos a ciegas no enseñan la propuesta.** Miden dos cosas que no se pueden separar de
otra forma: la tasa de acierto real y cuánto ancla ver una respuesta plausible antes de
pensar.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts import golden_review

RAIZ = Path(__file__).resolve().parents[2]
NORMA = "RD-1428/2003"


def caso(ident: str, *, tipo: str = "positivo", a_ciegas: bool = False) -> dict[str, object]:
    return {
        "id": ident,
        "source_id": f"s-{ident}",
        "pregunta": f"¿Pregunta {ident}?",
        "opciones": ["a", "b", "c"],
        "respuesta_correcta": "a",
        "tema": "06 Uso de la via y Adelantamientos",
        "subtema": "un subtema",
        "pct_fallo": 10.0,
        "tipo": tipo,
        "a_ciegas": a_ciegas,
    }


def veredicto(
    ident: str, *, que: str = "ok", segundos: float = 30.0, ref: str | None = None
) -> dict[str, object]:
    return {"id": ident, "veredicto": que, "ref": ref, "segundos": segundos}


# --------------------------------------------------------------------------------------
# Reanudar sin perder trabajo
# --------------------------------------------------------------------------------------


def test_lo_ya_juzgado_no_vuelve_a_salir() -> None:
    cola = [caso("gs-0001"), caso("gs-0002"), caso("gs-0003")]
    hechos = [veredicto("gs-0001"), veredicto("gs-0003")]
    assert [c["id"] for c in golden_review.pendientes(cola, hechos)] == ["gs-0002"]


def test_sin_nada_juzgado_estan_todos_pendientes() -> None:
    cola = [caso("gs-0001"), caso("gs-0002")]
    assert len(golden_review.pendientes(cola, [])) == 2


def test_el_ultimo_veredicto_de_un_caso_es_el_que_vale() -> None:
    """El fichero es append-only: corregirse sobre la marcha no debe exigir editar a mano."""
    hechos = [veredicto("gs-0001", que="ok"), veredicto("gs-0001", que="descartar")]
    assert golden_review.consolidar(hechos)["gs-0001"]["veredicto"] == "descartar"


def test_un_veredicto_se_escribe_en_cuanto_se_emite(tmp_path: Path) -> None:
    """Nada de acumular en memoria y volcar al final: cerrar el portatil en el caso 137 no
    puede costar 137 casos."""
    destino = tmp_path / "veredictos.jsonl"
    golden_review.anotar(destino, veredicto("gs-0001"))
    golden_review.anotar(destino, veredicto("gs-0002"))
    lineas = destino.read_text(encoding="utf-8").strip().splitlines()
    assert len(lineas) == 2
    assert json.loads(lineas[0])["id"] == "gs-0001"


# --------------------------------------------------------------------------------------
# Qué se le enseña y qué no
# --------------------------------------------------------------------------------------


def test_un_caso_normal_ensena_la_propuesta() -> None:
    vista = golden_review.vista(caso("gs-0001"), {"ref": f"{NORMA}#art82.2", "nota": "porque si"})
    assert vista.ref_propuesta == f"{NORMA}#art82.2"
    assert vista.nota == "porque si"


def test_un_caso_a_ciegas_NO_ensena_la_propuesta() -> None:
    """Si se le enseña, deja de medir lo que existe para medir."""
    vista = golden_review.vista(
        caso("gs-0015", a_ciegas=True), {"ref": f"{NORMA}#art82.2", "nota": "porque si"}
    )
    assert vista.ref_propuesta is None
    assert vista.nota is None
    assert vista.a_ciegas is True


def test_un_negativo_no_lleva_referencia_que_validar() -> None:
    """En un negativo lo unico que se confirma es que el corpus no responde."""
    vista = golden_review.vista(caso("gs-0250", tipo="negativo"), {"negativo": True, "nota": ""})
    assert vista.ref_propuesta is None
    assert vista.tipo == "negativo"


def test_el_texto_del_articulo_viaja_con_la_vista() -> None:
    """Es lo que convierte 3 minutos en 20 segundos: el articulo delante, sin abrir el BOE."""
    vista = golden_review.vista(
        caso("gs-0001"), {"ref": f"{NORMA}#art82.2", "nota": ""}, texto="Por excepcion..."
    )
    assert "Por excepcion" in (vista.texto or "")


# --------------------------------------------------------------------------------------
# Veredictos válidos
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("tecla", ["a", "e", "r", "s"])
def test_las_cuatro_teclas_de_q004_estan(tecla: str) -> None:
    assert tecla in golden_review.TECLAS


def test_corregir_exige_una_referencia_que_exista() -> None:
    """Una correccion a un articulo inexistente meteria en el golden set justo la
    alucinacion que `G-HALLUC` existe para hacer imposible."""
    with pytest.raises(ValueError, match=r"no existe|indice"):
        golden_review.validar_correccion(f"{NORMA}#art999", indice=frozenset({f"{NORMA}#art82"}))


def test_corregir_admite_bajar_al_apartado() -> None:
    ref = golden_review.validar_correccion(f"{NORMA}#art82.2", indice=frozenset({f"{NORMA}#art82"}))
    assert str(ref) == f"{NORMA}#art82.2"


def test_una_correccion_que_ni_siquiera_parsea_se_rechaza() -> None:
    with pytest.raises(ValueError):
        golden_review.validar_correccion("esto no es una ref", indice=frozenset())


# --------------------------------------------------------------------------------------
# El ritmo, que es la regla de parada de Q-004
# --------------------------------------------------------------------------------------


def test_con_pocos_casos_todavia_no_se_juzga_el_ritmo() -> None:
    """Los primeros son de calibracion: ahi Samuel esta decidiendo su propio criterio."""
    hechos = [veredicto(f"gs-{i:04d}", segundos=600) for i in range(5)]
    assert golden_review.alerta_de_ritmo(hechos, minimo_casos=20, tope_segundos=180) is None


def test_un_ritmo_por_encima_del_objetivo_dispara_la_parada() -> None:
    """Q-004: «si en los primeros 20 casos no bajas de 3 min/caso, el agente para y
    rediseña la cola». Es la diferencia entre 10 h y 25 h."""
    hechos = [veredicto(f"gs-{i:04d}", segundos=300) for i in range(20)]
    alerta = golden_review.alerta_de_ritmo(hechos, minimo_casos=20, tope_segundos=180)
    assert alerta is not None
    assert "300" in alerta or "5" in alerta


def test_un_ritmo_bueno_no_dispara_nada() -> None:
    hechos = [veredicto(f"gs-{i:04d}", segundos=45) for i in range(20)]
    assert golden_review.alerta_de_ritmo(hechos, minimo_casos=20, tope_segundos=180) is None


def test_el_ritmo_se_mide_con_la_mediana_y_no_con_la_media() -> None:
    """Un cafe de 40 minutos en mitad de la sesion dispararia una media y no dice nada del
    ritmo real. La mediana aguanta esa interrupcion; el objetivo de Q-004 es el ritmo
    sostenido, no el reloj de pared."""
    hechos = [veredicto(f"gs-{i:04d}", segundos=40) for i in range(19)]
    hechos.append(veredicto("gs-0019", segundos=2400))  # se fue a comer
    assert golden_review.alerta_de_ritmo(hechos, minimo_casos=20, tope_segundos=180) is None


# --------------------------------------------------------------------------------------
# El resumen, que es el numero que se le debe a Samuel
# --------------------------------------------------------------------------------------


def test_el_resumen_da_la_tasa_de_acierto_real() -> None:
    """Es el numero que Q-004 estima sin medir desde el principio del proyecto."""
    hechos = [veredicto(f"gs-{i:04d}", que="ok") for i in range(7)]
    hechos += [veredicto(f"gs-{i:04d}", que="corregir") for i in range(7, 10)]
    r = golden_review.resumen(hechos)
    assert r["n"] == 10
    assert r["aciertos"] == 7
    assert r["tasa_acierto"] == pytest.approx(0.7)


def test_el_resumen_separa_los_casos_a_ciegas() -> None:
    """La tasa sobre los casos que Samuel vio con propuesta esta contaminada por el anclaje.
    La limpia es la de los ciegos, y por eso se publica aparte."""
    hechos = [veredicto("gs-0001", que="ok"), veredicto("gs-0002", que="corregir")]
    hechos[0]["a_ciegas"] = True
    hechos[1]["a_ciegas"] = True
    hechos.append(veredicto("gs-0003", que="ok"))
    r = golden_review.resumen(hechos)
    assert r["n_ciegas"] == 2
    assert r["tasa_acierto_ciegas"] == pytest.approx(0.5)


def test_el_resumen_proyecta_lo_que_queda() -> None:
    """Con la mediana medida y los casos pendientes, cuanto falta deja de ser una opinion."""
    hechos = [veredicto(f"gs-{i:04d}", segundos=60) for i in range(10)]
    r = golden_review.resumen(hechos, pendientes=100)
    assert r["mediana_segundos"] == pytest.approx(60)
    assert r["restante_horas"] == pytest.approx(100 * 60 / 3600)


def test_el_resumen_de_un_conjunto_vacio_no_inventa_numeros() -> None:
    """Cero de cero no es 1,00, igual que en `scoring`."""
    r = golden_review.resumen([])
    assert r["n"] == 0
    assert r["tasa_acierto"] is None


# --------------------------------------------------------------------------------------
# Contra los ficheros reales
# --------------------------------------------------------------------------------------


def test_todas_las_propuestas_reales_cubren_la_cola_real() -> None:
    """Un caso en la cola sin propuesta seria una pantalla en blanco en mitad de su bloque."""
    cola = golden_review.cargar_cola(golden_review.COLA)
    propuestas = golden_review.cargar_propuestas(golden_review.PROPUESTAS)
    sin_propuesta = [c["id"] for c in cola if c["id"] not in propuestas]
    assert sin_propuesta == []
    assert len(cola) == 304
