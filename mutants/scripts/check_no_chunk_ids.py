"""R1 · ninguna cita se identifica por el id que acuña el troceador.

Se comprueban tres superficies, que son por donde ese identificador podría filtrarse a
un artefacto de evaluación:

  * el OpenAPI — nombres de propiedad y de esquema, no descripciones;
  * el modelo `Cita`, campo a campo;
  * `evals/golden/**`, donde un solo caso anclado ahí tira el conjunto entero.

Nombres de propiedad y **no** el texto entero a propósito. Una descripción que dice
«esto NO se identifica por el id del troceado» es lo contrario de una infracción, y un
`grep` a ciegas no sabe distinguirlas: la primera vez que marque algo correcto, alguien
lo desactiva. Un comprobador que grita sin motivo no sobrevive a dos semanas.

    uv run python scripts/check_no_chunk_ids.py     # exit 0 o 1
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
PROHIBIDO = "chunk_id"


def _propiedades(nodo: Any, ruta: str = "") -> list[str]:
    """Every property and schema NAME of the document, with where it was found."""
    encontrados: list[str] = []
    if isinstance(nodo, dict):
        for clave, valor in nodo.items():
            if clave in {"properties", "schemas"} and isinstance(valor, dict):
                encontrados.extend(f"{ruta}.{clave}.{nombre}" for nombre in valor)
            encontrados.extend(_propiedades(valor, f"{ruta}.{clave}"))
    elif isinstance(nodo, list):
        for i, item in enumerate(nodo):
            encontrados.extend(_propiedades(item, f"{ruta}[{i}]"))
    return encontrados


def revisar_openapi() -> list[str]:
    from citebound.api.app import openapi

    return [n for n in _propiedades(openapi()) if PROHIBIDO in n.lower()]


def revisar_modelo() -> list[str]:
    from citebound.api.app import Cita

    return [f"Cita.{c}" for c in Cita.model_fields if PROHIBIDO in c.lower()]


def revisar_golden() -> list[str]:
    fallos: list[str] = []
    for jsonl in sorted((RAIZ / "evals" / "golden").glob("v*.jsonl")):
        for n, linea in enumerate(jsonl.read_text(encoding="utf-8").splitlines(), 1):
            if not linea.strip():
                continue
            for clave in json.loads(linea):
                if PROHIBIDO in clave.lower():
                    fallos.append(f"{jsonl.name}:{n}:{clave}")
    return fallos


def main() -> int:
    fallos = revisar_openapi() + revisar_modelo() + revisar_golden()
    if fallos:
        print(f"R1 incumplida · {len(fallos)} sitios identifican una cita por el troceado:")
        for f in fallos:
            print(f"   {f}")
        print("La unidad de verdad es la LegalRef. Ver docs/CONTRACTS/retrieval-metrics.md §1.")
        return 1
    print("R1 ok · ninguna cita se identifica por el id del troceador")
    return 0


if __name__ == "__main__":
    sys.exit(main())
