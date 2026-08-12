"""`make typecheck` · mypy --strict sobre `[tool.gate].testable`, derivado y no copiado.

El comentario de `[tool.mypy].files` prometía exactamente esto «en 0.7» y no se cumplió: la
lista se quedó escrita a mano con `domain` e `ingest`, así que `evals/` —que **sí** está en
`testable`— no pasaba por `--strict` y nadie se enteraba. Es literalmente el fallo de «dos
listas que divergen en silencio» contra el que avisaba ese mismo comentario.

Ahora hay una sola lista, la de `[tool.gate]`, y este script la lee. Las rutas que aún no
existen se saltan **diciéndolo**: un comprobador que omite en silencio es uno que un día no
comprueba nada.
"""

from __future__ import annotations

import subprocess  # nosec B404 — lista fija de argumentos, sin shell
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def main() -> int:
    gate = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["gate"]
    rutas = [r for r in gate["testable"] if (RAIZ / r).exists()]
    pendientes = [r for r in gate["testable"] if not (RAIZ / r).exists()]

    if pendientes:
        print(
            f"  ({len(pendientes)} rutas de [tool.gate].testable aún no existen: "
            f"{', '.join(pendientes)})"
        )
    if not rutas:
        print("no hay ninguna ruta testable todavía")
        return 0

    print(f"  mypy --strict sobre {len(rutas)} rutas derivadas de [tool.gate].testable")
    return subprocess.run(  # noqa: S603  # nosec B603
        [sys.executable, "-m", "mypy", "--strict", *rutas], cwd=RAIZ, check=False
    ).returncode


if __name__ == "__main__":
    sys.exit(main())
