"""La interfaz de práctica: una pregunta del banco, la opción elegida, y la explicación citada.

**Consola y no web**, y es una decisión, no una limitación: el producto de la fase 3b es
*servir una pregunta y explicarla con su artículo*, y eso se demuestra igual en un terminal.
Una web añadiría plantillas, estáticos y un segundo servidor que mantener, y ADR-019 dice
exactamente lo contrario — «son las manetas de la bici». Si algún día hace falta la web, el
cliente HTTP ya está separado y no habría que tocarlo.

**No importa `citebound`.** Todo lo que sabe del motor entra por `ui/cliente.py`.
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path

from ui.cliente import BASE_POR_DEFECTO, Respuesta, preguntar

__all__ = ["Pregunta", "cargar_banco", "formatear", "main"]

RAIZ = Path(__file__).resolve().parents[1]
BANCO = RAIZ / "evals" / "golden"


@dataclass(frozen=True, slots=True)
class Pregunta:
    """Una pregunta del banco. `respuesta` puede faltar: los negativos no la tienen."""

    ident: str
    enunciado: str
    materia: str
    respuesta: str = ""


def cargar_banco(version: str | None = None) -> list[Pregunta]:
    """Las preguntas del golden set publicado. Es el mismo fichero que evalúa el motor.

    Que la interfaz sirva **exactamente** lo que se mide no es casualidad: si practicaras con
    un banco distinto del evaluado, los números del README no dirían nada sobre lo que ves.
    """
    ficheros = sorted(BANCO.glob(version or "v*.jsonl"))
    if not ficheros:
        raise FileNotFoundError(f"no hay golden set en {BANCO}")
    return [
        Pregunta(
            ident=str(d["id"]),
            enunciado=str(d["pregunta"]),
            materia=str(d["materia"]),
            respuesta=str(d.get("respuesta_referencia") or ""),
        )
        for linea in ficheros[-1].read_text(encoding="utf-8").splitlines()
        if linea.strip()
        for d in [json.loads(linea)]
    ]


def formatear(respuesta: Respuesta) -> str:
    """Lo que se pinta. **Una abstención se enseña como tal**, con su motivo.

    Un hueco vacío o un «no se ha encontrado nada» genérico convertiría una decisión del
    sistema en un fallo aparente, que es lo contrario de lo que este proyecto quiere enseñar.
    """
    if respuesta.abstenida:
        return (
            f"  El sistema se ABSTIENE.\n"
            f"  Motivo: {respuesta.motivo or 'sin especificar'}\n"
            f"  No responde porque no ha podido verificar la cita, y prefiere callarse."
        )
    lineas = [f"  {respuesta.texto}", ""]
    for cita in respuesta.citas:
        lineas.append(f"  [{cita.legal_ref}]")
        lineas.append(f"    «{cita.quote}»")
    return "\n".join(lineas)


def main() -> int:
    banco = cargar_banco()
    pregunta = random.choice(banco)  # noqa: S311 — es práctica, no criptografía
    print(f"\n  {pregunta.materia}  ·  {pregunta.ident}")
    print(f"\n  {pregunta.enunciado}\n")
    input("  [Enter para ver la explicación citada] ")

    try:
        respuesta = preguntar(pregunta.enunciado, base=BASE_POR_DEFECTO)
    except Exception as err:
        print(f"\n  El motor no respondió: {err}")
        print("  ¿Está levantado? `uv run uvicorn citebound.api.app:crear_app --factory`")
        return 1

    print()
    print(formatear(respuesta))
    if pregunta.respuesta:
        print(f"\n  Respuesta del banco: {pregunta.respuesta}")
    if respuesta.latencias_ms:
        ttft = respuesta.latencias_ms.get("ttft", 0)
        print(f"\n  ({ttft:.0f} ms hasta el primer token)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
