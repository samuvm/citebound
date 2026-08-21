"""El cliente HTTP del motor. **La única puerta**, y por eso está en un fichero solo.

ADR-019 fija que `ui/` habla con el motor **exclusivamente** por la API HTTP. Tener toda esa
conversación en un módulo hace que cruzar la línea sea visible en un `git diff`: si algún día
aparece un `from citebound...` en `ui/`, está en un sitio donde se ve.

Este módulo no interpreta lo que el motor responde. Traduce eventos SSE a estructuras y ya; si
el motor se abstuvo, lo dice, y no inventa una respuesta «por si acaso».
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field

__all__ = ["Cita", "Respuesta", "leer_sse", "preguntar"]

BASE_POR_DEFECTO = "http://localhost:8000"


@dataclass(frozen=True, slots=True)
class Cita:
    """Una cita ya verificada por el motor. La UI no la comprueba: no le toca y no podría."""

    legal_ref: str
    quote: str


@dataclass(slots=True)
class Respuesta:
    """Lo que la UI necesita para pintar. `abstenida` es un estado de primera clase.

    Si el motor se abstuvo, la interfaz **lo dice y dice por qué**. Enseñar un hueco vacío o
    un «no se ha encontrado nada» genérico convertiría una decisión del sistema en un fallo
    aparente, y es justo lo contrario de lo que el proyecto quiere enseñar.
    """

    texto: str = ""
    citas: list[Cita] = field(default_factory=list)
    fuentes: list[dict[str, object]] = field(default_factory=list)
    abstenida: bool = False
    motivo: str = ""
    latencias_ms: dict[str, float] = field(default_factory=dict)


def leer_sse(lineas: Iterator[str]) -> Respuesta:
    """De un flujo SSE a una `Respuesta`. Pura: se puede probar sin servidor ni red."""
    respuesta = Respuesta()
    evento = ""
    for linea in lineas:
        linea = linea.rstrip("\n")
        if linea.startswith("event:"):
            evento = linea[6:].strip()
        elif linea.startswith("data:"):
            datos = json.loads(linea[5:].strip())
            if evento == "sources":
                respuesta.fuentes = list(datos.get("fuentes") or [])
            elif evento == "token":
                respuesta.texto += str(datos.get("texto") or "")
            elif evento == "citations":
                respuesta.citas = [
                    Cita(legal_ref=str(c["legal_ref"]), quote=str(c["quote"]))
                    for c in datos.get("citas") or []
                ]
            elif evento == "abstain":
                respuesta.abstenida = True
                respuesta.motivo = str(datos.get("motivo") or "")
            elif evento == "done":
                respuesta.latencias_ms = dict(datos.get("latencias_ms") or {})
            elif evento == "error":
                respuesta.abstenida = True
                respuesta.motivo = f"error: {datos.get('detalle', '')}"
    return respuesta


def preguntar(pregunta: str, *, base: str = BASE_POR_DEFECTO, timeout: float = 120.0) -> Respuesta:
    """Una pregunta al motor por `POST /ask/stream`."""
    import httpx

    with httpx.stream(
        "POST", f"{base.rstrip('/')}/ask/stream", params={"pregunta": pregunta}, timeout=timeout
    ) as flujo:
        flujo.raise_for_status()
        return leer_sse(iter(flujo.iter_lines()))
