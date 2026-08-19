"""`R7` · `langchain*` no entra en `pyproject.toml`. LangGraph sí, y solo como máquina de estados.

**Por qué la distinción importa.** LangGraph aporta una cosa concreta: un grafo con estado,
reintentos y *timeouts* por nodo. LangChain aporta abstracciones sobre el retrieval y sobre el
LLM, y las dos son justo lo que este proyecto tiene escrito a mano **a propósito**: el retrieval
es SQL propio porque la fusión y el `ts_rank_cd` son la mitad de la tesis, y el LLM pasa por un
puerto propio porque la cita cerrada exige controlar el stream token a token.

Un `langchain` en las dependencias no rompe nada el día que entra. Rompe el día que alguien
resuelve un problema con su abstracción y el proyecto deja de poder explicar cómo recupera.

La comprobación es sobre `pyproject.toml` y no sobre el entorno: lo que se declara es lo que
otro se instalará. Una dependencia transitiva que arrastre `langchain` se vería en `uv.lock` y
es otra conversación — esta regla es sobre lo que este repositorio pide.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

__all__ = ["PROHIBIDOS", "raiz_del_paquete", "revisar"]

RAIZ = Path(__file__).resolve().parents[1]
PROHIBIDOS = ("langchain",)
"""Prefijos vetados. `langgraph` **no** está: es la máquina de estados y está pinada."""

_NOMBRE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def raiz_del_paquete(requisito: str) -> str:
    """`"langchain-core>=0.3"` → `"langchain-core"`. Sin versión, sin extras, sin marcadores."""
    encontrado = _NOMBRE.match(requisito.split(";")[0].split("[")[0])
    return encontrado.group(1).lower().replace("_", "-") if encontrado else ""


def revisar(pyproject: dict[str, object]) -> list[str]:
    """Los requisitos declarados que empiezan por un prefijo vetado."""
    proyecto = pyproject.get("project", {})
    declarados: list[str] = list(proyecto.get("dependencies", []))  # type: ignore[union-attr,arg-type]
    for extra in (proyecto.get("optional-dependencies") or {}).values():  # type: ignore[union-attr]
        declarados += list(extra)
    grupos = (pyproject.get("dependency-groups") or {}).values()  # type: ignore[union-attr]
    for grupo in grupos:
        declarados += [x for x in grupo if isinstance(x, str)]

    return [
        req for req in declarados if any(raiz_del_paquete(req).startswith(p) for p in PROHIBIDOS)
    ]


def main() -> int:
    datos = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    culpables = revisar(datos)
    if culpables:
        for req in culpables:
            print(f"  {req} · prohibido por R7")
        print(
            "R7 roja · LangGraph se usa SOLO como máquina de estados: el retrieval es SQL "
            "propio y el LLM pasa por un puerto propio, y las dos cosas son la tesis"
        )
        return 1
    n = len(datos.get("project", {}).get("dependencies", []))  # type: ignore[union-attr]
    print(f"R7 ok · {n} dependencias declaradas, ninguna de la familia langchain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
