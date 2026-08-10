"""Un test por función pública, hecho ejecutable (constitución §2.6).

El encargo de Samuel decía «un test unitario por cada función». Sus documentos decían
«sin objetivo global de cobertura, perseguir el 100 % en adaptadores es ruido». Las dos
cosas son ciertas y la contradicción se resuelve con una definición, no con un porcentaje:

    toda función pública (sin `_` inicial) de un paquete de [tool.gate].testable
    tiene al menos UN contexto de test que la ejerce directamente.

`--cov-context=test` registra qué test cubrió cada línea, así que esto se mide y no se
supone. **No se mide por convención de nombres**: que exista `test_parse` no prueba que
`parse` se ejecute, y esa convención se falsea en dos minutos.

    uv run python scripts/check_function_coverage.py      # exit 0 o 1
"""

from __future__ import annotations

import ast
import json
import subprocess  # nosec B404 — se invoca pytest con lista fija, sin shell
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
COBERTURA = RAIZ / ".coverage-funciones.json"


def paquetes_testable() -> list[Path]:
    cfg = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    return [RAIZ / r for r in cfg["tool"]["gate"]["testable"]]


def excepciones() -> set[str]:
    """`sin_test_requerido`, y **cada entrada exige motivo**: el gate rechaza una sin él."""
    cfg = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    fuera: set[str] = set()
    for entrada in cfg["tool"]["gate"].get("sin_test_requerido", []):
        if not entrada.get("motivo"):
            raise SystemExit(f"excepción sin motivo en [tool.gate]: {entrada}")
        fuera.add(entrada["symbol"])
    return fuera


def funciones_publicas(fichero: Path) -> dict[str, int]:
    """`{nombre_cualificado: línea}` de cada función pública, métodos incluidos."""
    arbol = ast.parse(fichero.read_text(encoding="utf-8"))
    encontradas: dict[str, int] = {}

    def recorrer(nodo: ast.AST, prefijo: str) -> None:
        for hijo in ast.iter_child_nodes(nodo):
            if isinstance(hijo, ast.ClassDef):
                recorrer(hijo, f"{prefijo}{hijo.name}.")
            elif isinstance(hijo, ast.FunctionDef | ast.AsyncFunctionDef) and not (
                hijo.name.startswith("_")
            ):
                # La primera sentencia EJECUTABLE, saltándose el docstring. Ni la línea
                # del `def` ni la del docstring sirven: la primera se cubre con solo
                # importar el módulo y la segunda no se ejecuta nunca, así que
                # cualquiera de las dos daría un veredicto que no significa nada.
                encontradas[f"{prefijo}{hijo.name}"] = _primera_ejecutable(hijo)

    recorrer(arbol, "")
    return encontradas


def _primera_ejecutable(funcion: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    for sentencia in funcion.body:
        es_docstring = isinstance(sentencia, ast.Expr) and isinstance(sentencia.value, ast.Constant)
        if not es_docstring:
            return sentencia.lineno
    return funcion.body[-1].lineno


def main() -> int:
    subprocess.run(  # noqa: S603  # nosec B603 — lista fija, sin shell
        [
            sys.executable,
            "-m",
            "pytest",
            "tests",
            "-q",
            "-m",
            "not integration",
            "--cov=citebound",
            "--cov-context=test",
            f"--cov-report=json:{COBERTURA}",
            "-p",
            "no:randomly",
        ],
        cwd=RAIZ,
        check=True,
        capture_output=True,
    )
    datos = json.loads(COBERTURA.read_text(encoding="utf-8"))
    fuera = excepciones()
    sin_test: list[str] = []

    pendientes: list[str] = []
    for raiz in paquetes_testable():
        if not raiz.exists():
            # De una fase posterior. Se SALTA pero se DICE: un gate que omite en
            # silencio es un gate que un dia no comprueba nada y nadie se entera.
            pendientes.append(str(raiz.relative_to(RAIZ)))
            continue
        ficheros = [raiz] if raiz.suffix == ".py" else sorted(raiz.rglob("*.py"))
        for fichero in ficheros:
            if fichero.name == "__init__.py":
                continue
            relativo = str(fichero.relative_to(RAIZ))
            contextos = (datos["files"].get(relativo) or {}).get("contexts", {})
            for nombre, linea in funciones_publicas(fichero).items():
                simbolo = f"{fichero.stem}.{nombre}"
                if any(simbolo.endswith(p.lstrip("*.")) for p in fuera):
                    continue
                ejercida = [c for c in contextos.get(str(linea), []) if c]
                if not ejercida:
                    sin_test.append(f"{relativo}:{linea} {nombre}")

    if pendientes:
        print(
            f"  ({len(pendientes)} rutas de [tool.gate].testable aún no existen: "
            f"{', '.join(pendientes)})"
        )

    if sin_test:
        print(f"G-COV-FUNC roja · {len(sin_test)} funciones públicas sin un test que las ejerza:")
        for f in sin_test:
            print(f"   {f}")
        print("Excepciones solo en [tool.gate].sin_test_requerido, y con motivo escrito.")
        return 1
    print("G-COV-FUNC ok · toda función pública de [tool.gate].testable tiene su test")
    return 0


if __name__ == "__main__":
    sys.exit(main())
