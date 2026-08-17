"""Las listas del gate viven en dos ficheros, y este test las obliga a decir lo mismo.

`docs/RULES.md` §4 es de solo lectura y manda; `pyproject.toml` es lo que leen las
herramientas. Que las dos existan es inevitable —ruff, mypy y mutmut no leen Markdown— pero
que **diverjan** ya ha pasado **tres veces** en este repositorio, siempre igual de callado:

  · `scoring.py` estaba en `tdd_obligatorio` desde el primer día y fuera de `[tool.mutmut]`:
    `G-MUT` medía sobre 3 de los 4 ficheros que le tocaban y salía verde.
  · `bootstrap.py`, lo mismo, hasta Q-014.
  · `retrieval/fusion.py`, lo mismo, hasta hoy (2026-08-17).

Ninguna de las tres dio un error. La meta seguía en verde **midiendo menos cosas**, que es el
peor modo de fallo posible para un gate: el número existe, es alto, y no significa lo que dice.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _lista_de_rules(nombre: str) -> list[str]:
    """La lista tal cual la declara `docs/RULES.md` §4, que es la que manda.

    Se lee del Markdown a propósito: copiarla aquí crearía una cuarta copia, y este fichero
    existe justo para que no haya copias que puedan discrepar.
    """
    texto = (RAIZ / "docs" / "RULES.md").read_text(encoding="utf-8")
    bloque = re.search(rf"^{nombre}\s*=\s*\[(.*?)\]", texto, re.DOTALL | re.MULTILINE)
    assert bloque is not None, f"`{nombre}` ya no está en docs/RULES.md §4 con esa forma"
    return re.findall(r'"([^"]+)"', bloque.group(1))


def _pyproject() -> dict[str, object]:
    return tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))


def test_todo_lo_que_existe_y_exige_tdd_se_muta() -> None:
    """**El test que este fichero existe para tener.**

    Un fichero con TDD obligatorio y sin mutación tiene la garantía más débil de las dos: sus
    tests existen y nadie ha comprobado que comprueben algo. Que exista es la condición: una
    ruta declarada para una fase futura todavía no se puede mutar, y eso no es una divergencia.
    """
    mutados = set(_pyproject()["tool"]["mutmut"]["source_paths"])  # type: ignore[index,call-overload]
    faltan = []
    for ruta in _lista_de_rules("tdd_obligatorio"):
        destino = RAIZ / ruta
        if destino.is_file() and ruta not in mutados:
            faltan.append(ruta)
        elif destino.is_dir():
            faltan += [
                str(f.relative_to(RAIZ))
                for f in sorted(destino.rglob("*.py"))
                if f.name != "__init__.py" and str(f.relative_to(RAIZ)) not in mutados
            ]
    assert faltan == [], (
        f"con TDD obligatorio y sin mutar: {faltan}. G-MUT saldría verde midiendo menos "
        "ficheros de los que le tocan, que es como se coló tres veces ya"
    )


def test_no_se_muta_nada_que_las_reglas_no_exijan() -> None:
    """La divergencia también cuenta en el otro sentido: mutar un fichero que las reglas no
    declaran hace que `G-MUT` mida algo que nadie acordó, y su umbral deja de significar lo
    que dice `GOALS.yaml`."""
    exigidos = _lista_de_rules("tdd_obligatorio")
    for ruta in _pyproject()["tool"]["mutmut"]["source_paths"]:  # type: ignore[index,union-attr]
        assert any(ruta == e or ruta.startswith(e.rstrip("/") + "/") for e in exigidos), (
            f"{ruta} se muta y no está en `tdd_obligatorio` de docs/RULES.md §4"
        )


def test_lo_excluido_de_cobertura_no_puede_exigir_tdd_a_la_vez() -> None:
    """`api/`, `db/` y `providers/` están fuera de la cobertura a propósito. Si alguno entrara
    también en `tdd_obligatorio`, el gate estaría exigiendo y perdonando la misma ruta."""
    excluido = _lista_de_rules("excluido")
    for ruta in _lista_de_rules("tdd_obligatorio"):
        assert not any(ruta.startswith(e.rstrip("/")) for e in excluido), (
            f"{ruta} exige TDD y está excluido de cobertura: el gate se contradice"
        )
