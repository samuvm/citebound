"""Snapshot del OpenAPI y las dos cosas que no puede contener.

TDD prohibido en `api/` (RULES §3): la forma la fija FastAPI, no un test escrito antes.
Lo que sí se exige es que no cambie sin querer, y que R1 se cumpla en la superficie
publica — que es por donde un identificador de troceado se filtraria a un artefacto de
evaluacion sin que nadie lo viera.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from citebound.api.app import Cita, Respuesta, crear_app, openapi

SNAPSHOT = Path(__file__).with_name("openapi.snapshot.json")


def _normalizado() -> str:
    return json.dumps(openapi(), ensure_ascii=False, indent=1, sort_keys=True)


def test_the_openapi_has_not_changed_by_accident() -> None:
    """Regenerar es `make openapi`, y el diff se revisa antes de comprometerlo. Un
    contrato de API que cambia solo es lo que rompe a quien lo consume."""
    if not SNAPSHOT.is_file():
        pytest.fail(f"falta el snapshot; genéralo con `make openapi` -> {SNAPSHOT.name}")
    assert _normalizado() == SNAPSHOT.read_text(encoding="utf-8").rstrip("\n"), (
        "el OpenAPI cambió. Si es a propósito: `make openapi` y revisa el diff."
    )


def test_no_citation_is_identified_by_the_chunkers_identifier() -> None:
    """R1 sobre la superficie publica. Anclar ahi la evaluacion invalidaria el golden set
    en cuanto cambie el troceado, que es justo lo que hace la fase 2 a proposito."""
    from scripts.check_no_chunk_ids import revisar_modelo, revisar_openapi

    assert revisar_openapi() == []
    assert revisar_modelo() == []


def test_the_citation_is_identified_by_its_legal_reference() -> None:
    assert "legal_ref" in Cita.model_fields


def test_the_answer_records_the_resolved_physical_target_and_not_only_the_alias() -> None:
    """La condicion que este proyecto puso para aceptar B1 (ADR-018). Con el alias solo,
    dos ejecuciones sobre datos distintos darian informes identicos y `G-EVAL-DET`
    dejaria de significar nada."""
    assert "index_version" in Respuesta.model_fields
    assert "physical_table" in Respuesta.model_fields


def test_phase_zero_says_out_loud_that_there_is_no_generator() -> None:
    """`G-HALLUC` es cero hoy porque no hay generador, no porque el sistema sea listo.
    Publicar el numero sin decirlo seria exactamente lo que D-06 prohibe."""
    assert Respuesta.model_fields["generado_por"].default == "retrieval-only"


def test_health_answers_without_touching_the_database() -> None:
    from fastapi.testclient import TestClient

    with TestClient(crear_app()) as cliente:
        respuesta = cliente.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"
