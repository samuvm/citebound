"""`ui/` habla con el motor **solo** por HTTP, y esto lo comprueba.

ADR-019 lo decide y da el motivo: si `ui/` importara el dominio, o metes la interfaz en
`[tool.gate].testable` y persigues cobertura en botones, o la excluyes y creas un agujero por
donde se cuela lógica sin test. La línea existe para que no haya que elegir.

**Una frontera sin comprobación es una intención.** Cruzarla una vez —un import «temporal» para
salir del paso— y deja de existir, porque el segundo ya no parece grave.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from ui.cliente import Cita, leer_sse

RAIZ = Path(__file__).resolve().parents[2]


def sse(*eventos: tuple[str, dict]) -> list[str]:
    lineas: list[str] = []
    for nombre, datos in eventos:
        lineas += [f"event: {nombre}", f"data: {json.dumps(datos, ensure_ascii=False)}", ""]
    return lineas


# --------------------------------------------------------------------------------------
# La frontera
# --------------------------------------------------------------------------------------


def test_ui_no_importa_el_motor_en_ningun_fichero() -> None:
    """**El test que sostiene ADR-019.** Si esto falla, la separación deja de ser cierta y el
    régimen de pruebas del motor se contamina."""
    culpables: list[str] = []
    for fichero in sorted((RAIZ / "ui").rglob("*.py")):
        arbol = ast.parse(fichero.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                culpables += [
                    f"{fichero.name}:{nodo.lineno} {a.name}"
                    for a in nodo.names
                    if a.name.startswith("citebound")
                ]
            elif isinstance(nodo, ast.ImportFrom) and (nodo.module or "").startswith("citebound"):
                culpables.append(f"{fichero.name}:{nodo.lineno} {nodo.module}")
    assert culpables == [], (
        f"`ui/` importa el motor: {culpables}. Si necesita algo que la API no da, lo correcto "
        "es ampliar la API (ADR-019)"
    )


def test_la_ui_solo_habla_con_el_endpoint_que_existe() -> None:
    """Que la frontera sea real exige que el camino que usa esté en el contrato publicado."""
    snapshot = json.loads((RAIZ / "tests" / "contract" / "openapi.snapshot.json").read_text())
    fuente = (RAIZ / "ui" / "cliente.py").read_text(encoding="utf-8")
    assert "/ask/stream" in fuente
    assert "/ask/stream" in snapshot["paths"]


# --------------------------------------------------------------------------------------
# Leer el flujo
# --------------------------------------------------------------------------------------


def test_una_respuesta_completa_se_lee_entera() -> None:
    r = leer_sse(
        iter(
            sse(
                ("sources", {"fuentes": [{"n": 1, "legal_ref": "RD-1428/2003#art34"}]}),
                ("token", {"texto": "Se cuentan así [[REF:1]]."}),
                (
                    "citations",
                    {"citas": [{"n": 1, "legal_ref": "RD-1428/2003#art34", "quote": "x"}]},
                ),
                ("done", {"latencias_ms": {"ttft": 1187.9}}),
            )
        )
    )
    assert r.abstenida is False
    assert r.citas == [Cita(legal_ref="RD-1428/2003#art34", quote="x")]
    assert r.latencias_ms["ttft"] == 1187.9
    assert len(r.fuentes) == 1


def test_una_abstencion_se_lee_como_abstencion_y_no_como_vacio() -> None:
    """**Lo que la interfaz no puede hacer es disimularla.** Un hueco vacío convertiría una
    decisión del sistema en un fallo aparente."""
    r = leer_sse(iter(sse(("abstain", {"motivo": "quote_no_literal", "reintentos": 2}))))
    assert r.abstenida is True
    assert r.motivo == "quote_no_literal"
    assert r.texto == ""


def test_un_error_del_motor_no_se_confunde_con_una_abstencion() -> None:
    """Se marca igual para que la UI no pinte una respuesta, pero el motivo lo distingue: una
    abstención dice «el corpus no lo responde» y un error dice «el sistema falló»."""
    r = leer_sse(iter(sse(("error", {"detalle": "la base no respondió"}))))
    assert r.abstenida is True
    assert r.motivo.startswith("error:")


def test_los_tokens_se_acumulan_en_orden() -> None:
    r = leer_sse(iter(sse(("token", {"texto": "uno "}), ("token", {"texto": "dos"}))))
    assert r.texto == "uno dos"


def test_un_flujo_vacio_no_revienta() -> None:
    assert leer_sse(iter([])).texto == ""
