"""Contract tests for `scripts/golden_validate.py` — la salida de la fase 1.

`make golden-validate` es el **criterio de salida** de la fase entera y el comando de
`G-GOLDEN-VALID`, cuyo `propuesta_admisible` es `false`: ni siquiera se admite proponer
bajarlo. Un comprobador de esa categoría con la lógica sin testear sería el equivalente a
poner un guardia en la puerta y no comprobar si sabe leer.

**Por qué se escribe antes que `1b` y no después.** Sin el validador no hay forma de saber
si la cola de ~304 candidatos que se le da a Samuel cumple el suelo estadístico. Generar
primero y descubrir en la hora 12 que faltan negativos, o que una materia se quedó en 18
casos, es tirar horas suyas que no se recuperan.

Lo que aquí se comprueba sale de tres sitios, ninguno inventado:

  · `docs/GOALS.yaml` `G-GOLDEN-VALID` — los `adicionales` (≥150 positivos, ≥40 negativos,
    ≥6 materias con ≥20 casos) y la lista de la `nota`.
  · `docs/CONTRACTS/retrieval-metrics.md` §3 — el esquema y las **tres reglas duras**.
  · `corpus/index/refs.json` — el conjunto de referencias que existen de verdad.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import golden_validate

RAIZ = Path(__file__).resolve().parents[2]
NORMA = "RD-1428/2003"

# Un índice de juguete: tres artículos. El de verdad tiene 235 y se lee en `main()`.
INDICE = frozenset({f"{NORMA}#art34", f"{NORMA}#art35", f"{NORMA}#art36"})

UMBRALES_JUGUETE = golden_validate.Umbrales(
    positivos_min=4,
    negativos_min=2,
    materias_min=2,
    casos_por_materia=2,
    fraccion_negativos_min=0.15,
    coseno_duplicado=0.95,
)


def caso(
    ident: str,
    *,
    tipo: str = "positivo",
    materia: str = "adelantamiento",
    refs: list[str] | None = None,
    pregunta: str | None = None,
    **extra: Any,
) -> str:
    """Una línea del JSONL. Los defectos se inyectan con `extra`."""
    cuerpo: dict[str, Any] = {
        "id": ident,
        "version": 1,
        "pregunta": pregunta or f"¿Pregunta {ident}?",
        "respuesta_referencia": "Sí." if tipo == "positivo" else None,
        "refs": refs if refs is not None else ([f"{NORMA}#art34"] if tipo == "positivo" else []),
        "materia": materia,
        "dificultad": "media",
        "pct_fallo": 10.0,
        "tipo": tipo,
        "provenance": "llm_generado_revisado_humano",
        "revisado_por": "samuel",
        "revisado_en": "2026-08-20",
        "notas": "",
    }
    cuerpo.update(extra)
    return json.dumps(cuerpo, ensure_ascii=False)


def conjunto_valido() -> list[str]:
    """El mínimo que pasa `UMBRALES_JUGUETE`: 4 positivos en 2 materias + 2 negativos."""
    lineas = [caso(f"p{i}", materia="adelantamiento") for i in range(2)]
    lineas += [caso(f"q{i}", materia="velocidad", refs=[f"{NORMA}#art35"]) for i in range(2)]
    lineas += [caso(f"n{i}", tipo="negativo", materia="mecanica") for i in range(2)]
    return lineas


def vectores_distintos(lineas: list[str]) -> dict[str, list[float]]:
    """Un vector ortogonal por caso: ninguna pareja se parece."""
    ids = [json.loads(x)["id"] for x in lineas]
    return {ident: [1.0 if j == i else 0.0 for j in range(len(ids))] for i, ident in enumerate(ids)}


def errores_de(lineas: list[str], **kwargs: Any) -> list[str]:
    opciones: dict[str, Any] = {
        "refs_indice": INDICE,
        "umbrales": UMBRALES_JUGUETE,
        "vectores": vectores_distintos(lineas),
    }
    opciones.update(kwargs)
    return golden_validate.validar(lineas, **opciones)


# --------------------------------------------------------------------------------------
# El camino feliz, para que el resto de tests signifiquen algo
# --------------------------------------------------------------------------------------


def test_un_conjunto_conforme_no_da_ningun_error() -> None:
    assert errores_de(conjunto_valido()) == []


# --------------------------------------------------------------------------------------
# Esquema: el 100 % de los casos, o no es un golden set
# --------------------------------------------------------------------------------------


def test_una_linea_que_no_es_json_es_un_error_y_dice_cual() -> None:
    lineas = [*conjunto_valido(), "{esto no es json"]
    fallos = errores_de(lineas, vectores=vectores_distintos(conjunto_valido()))
    assert any("línea 7" in e for e in fallos)


def test_un_caso_que_no_valida_contra_el_esquema_es_un_error() -> None:
    """El esquema ya prohíbe un positivo sin referencia; el validador lo reporta con su id
    en vez de reventar con un traceback de Pydantic a mitad de fichero."""
    malo = caso("roto", refs=[])
    fallos = errores_de([*conjunto_valido(), malo], vectores=vectores_distintos(conjunto_valido()))
    assert any("roto" in e for e in fallos)


def test_un_caso_sin_revisor_es_un_error() -> None:
    """Regla dura nº 3 del contrato: generación asistida sí, aprobación automática no."""
    sin_revisar = caso("auto", revisado_por=None, revisado_en=None)
    fallos = errores_de(
        [*conjunto_valido(), sin_revisar], vectores=vectores_distintos(conjunto_valido())
    )
    assert any("auto" in e for e in fallos)


def test_dos_casos_con_el_mismo_id_son_un_error() -> None:
    """Los ids son la clave con la que se emparejan casos y predicciones en `scoring`.
    Duplicarlos da un número plausible sobre un conjunto que no es el golden set."""
    lineas = [*conjunto_valido(), caso("p0", materia="velocidad", refs=[f"{NORMA}#art35"])]
    fallos = errores_de(lineas, vectores=vectores_distintos(conjunto_valido()))
    assert any("p0" in e and "duplicad" in e for e in fallos)


# --------------------------------------------------------------------------------------
# Las referencias existen de verdad
# --------------------------------------------------------------------------------------


def test_una_referencia_que_no_esta_en_el_indice_es_un_error() -> None:
    """Es `G-HALLUC` aplicado al propio golden set: si el patrón oro cita un artículo que
    no existe, ninguna métrica anclada en él significa nada."""
    lineas = [*conjunto_valido()[:-1], caso("x", refs=[f"{NORMA}#art999"])]
    fallos = errores_de(lineas)
    assert any("art999" in e for e in fallos)


def test_una_referencia_con_apartado_vale_si_su_articulo_esta_en_el_indice() -> None:
    """El índice se construye por artículo (`articulo-v1`), pero el golden set cita al
    apartado cuando el caso lo exige. Comparar cadenas literales rechazaría `art34.1` por
    no estar en un índice que nunca va a contener apartados, y eso invalidaría de golpe la
    granularidad de la que dependen `G-CITA-PRECISION` y `G-QUOTE-LIT`."""
    lineas = [*conjunto_valido()[:-1], caso("x", refs=[f"{NORMA}#art34.1"])]
    assert errores_de(lineas) == []


# --------------------------------------------------------------------------------------
# El suelo estadístico. Los números salen de GOALS.yaml, no de aquí
# --------------------------------------------------------------------------------------


def test_pocos_positivos_es_un_error_que_dice_cuantos_faltan() -> None:
    lineas = [caso("p0"), caso("p1"), caso("n0", tipo="negativo"), caso("n1", tipo="negativo")]
    fallos = errores_de(lineas)
    assert any("positivo" in e and "2" in e for e in fallos)


def test_pocos_negativos_es_un_error() -> None:
    lineas = [caso(f"p{i}", materia="adelantamiento" if i < 2 else "velocidad") for i in range(4)]
    lineas.append(caso("n0", tipo="negativo"))
    fallos = errores_de(lineas)
    assert any("negativo" in e for e in fallos)


def test_menos_del_15_por_ciento_de_negativos_es_un_error() -> None:
    """Regla dura nº 1 del contrato. Es independiente del suelo absoluto: 40 negativos
    sobre 190 cumple, pero 40 sobre 400 ya no, y sin ese porcentaje `G-ABST-FP` se calcula
    sobre una muestra que no representa nada."""
    lineas = [caso(f"p{i}", materia="adelantamiento" if i % 2 else "velocidad") for i in range(40)]
    lineas += [caso("n0", tipo="negativo"), caso("n1", tipo="negativo")]
    fallos = errores_de(lineas)
    assert any("15" in e or "fracción" in e or "fraccion" in e for e in fallos)


def test_pocas_materias_con_casos_suficientes_es_un_error() -> None:
    """Sin estratificación, un recall del 0,91 puede ser 0,99 en señales y 0,40 en
    adelantamientos, y el número agregado lo esconde."""
    lineas = [caso(f"p{i}", materia="adelantamiento") for i in range(4)]
    lineas += [caso("n0", tipo="negativo"), caso("n1", tipo="negativo")]
    fallos = errores_de(lineas)
    assert any("materia" in e for e in fallos)


def test_los_umbrales_salen_de_goals_y_no_estan_escritos_en_el_script() -> None:
    """Misma lección que la semilla del bootstrap: un 150 escrito aquí es una segunda
    fuente de verdad, y el día que Samuel suba el suelo en `GOALS.yaml` este script
    seguiría validando contra el viejo sin que nadie se entere."""
    fuente = Path(golden_validate.__file__).read_text(encoding="utf-8")
    assert "150" not in fuente
    assert "40" not in fuente

    umbrales = golden_validate.umbrales_de_goals(RAIZ / "docs" / "GOALS.yaml")
    assert umbrales.positivos_min == 150
    assert umbrales.negativos_min == 40
    assert umbrales.materias_min == 6
    assert umbrales.casos_por_materia == 20


# --------------------------------------------------------------------------------------
# Preguntas casi iguales
# --------------------------------------------------------------------------------------


def test_dos_preguntas_casi_identicas_son_un_error() -> None:
    """Duplicados inflan el `n` sin aportar información: el bootstrap los cuenta como dos
    casos independientes y estrecha el intervalo de confianza sin motivo."""
    lineas = conjunto_valido()
    vectores = vectores_distintos(lineas)
    vectores["q0"] = list(vectores["p0"])  # el mismo vector: coseno 1,0
    fallos = errores_de(lineas, vectores=vectores)
    assert any("p0" in e and "q0" in e for e in fallos)


def test_un_caso_sin_vector_es_un_error_y_no_se_salta_en_silencio() -> None:
    """«Un comprobador que omite en silencio es uno que un día no comprueba nada»."""
    lineas = conjunto_valido()
    vectores = vectores_distintos(lineas)
    del vectores["p0"]
    fallos = errores_de(lineas, vectores=vectores)
    assert any("p0" in e and "vector" in e for e in fallos)


# --------------------------------------------------------------------------------------
# El artefacto que lee el gate
# --------------------------------------------------------------------------------------


def test_el_informe_lleva_errores_como_numero_no_como_lista() -> None:
    """`GOALS.yaml` apunta a `VALIDATION.json :: errores` con umbral `== 0` y unidad
    `count`. Si `errores` fuera la lista, `[] == 0` es falso y la meta nunca daría verde."""
    informe = golden_validate.informe(errores=[], casos=[], sha256="abc")
    assert informe["errores"] == 0
    assert isinstance(informe["errores"], int)


def test_el_informe_conserva_el_detalle_ademas_del_recuento() -> None:
    informe = golden_validate.informe(errores=["a", "b"], casos=[], sha256="abc")
    assert informe["errores"] == 2
    assert informe["detalle"] == ["a", "b"]


def test_el_informe_registra_el_sha256_del_conjunto_validado() -> None:
    """Sin él, el informe dice «0 errores» sobre un fichero que nadie sabe cuál era."""
    informe = golden_validate.informe(errores=[], casos=[], sha256="deadbeef")
    assert informe["sha256"] == "deadbeef"


def test_el_informe_publica_el_desglose_que_hace_falta_para_el_readme() -> None:
    """El README publica el `n` real y el efecto mínimo detectable, no solo «190 casos»."""
    casos = golden_validate.cargar(conjunto_valido())[0]
    informe = golden_validate.informe(errores=[], casos=casos, sha256="abc")
    assert informe["positivos"] == 4
    assert informe["negativos"] == 2
    assert informe["por_materia"]["adelantamiento"] == 2


@pytest.mark.parametrize("lineas_vacias", [[], ["", "  "]])
def test_un_conjunto_vacio_no_pasa_por_no_tener_errores(lineas_vacias: list[str]) -> None:
    """Cero casos da cero fallos de esquema. Si el suelo no se comprobara aparte, un
    fichero vacío pondría `G-GOLDEN-VALID` en verde."""
    fallos = golden_validate.validar(
        lineas_vacias, refs_indice=INDICE, umbrales=UMBRALES_JUGUETE, vectores={}
    )
    assert fallos != []
