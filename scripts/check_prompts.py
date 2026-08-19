"""`R5` · los prompts viven en `prompts/*.md` con frontmatter, nunca dentro del código.

**Por qué es una regla y no una preferencia.** Un prompt inline no tiene versión, así que un
informe de eval no puede decir con cuál se midió; no tiene `cambios`, así que una regresión de
calidad no se puede atribuir; y no se puede difundir, así que dos sitios acaban con dos
variantes. `docs/CONTRACTS/eval-report.schema.json` pide `prompt_id` y `version` en el informe:
sin fichero no hay nada que poner ahí.

Tres comprobaciones, las que `docs/RULES.md` R5 escribe:

  **(a)** ningún literal de cadena en `src/` de más de `LARGO_SOSPECHOSO` caracteres que
  contenga `\\n\\n` — la firma de un prompt con párrafos;
  **(b)** todo `prompts/*.md` trae `id`, `version`, `modelo_destino`, `temperatura` y `cambios`;
  **(c)** todo `prompt_id` referenciado en el código existe como fichero.

**La distinción que hace útil a (a)** es entre un literal *asignado o pasado* —que es un prompt—
y una cadena que es un enunciado por sí sola: docstrings de módulo, de función, y los de
atributo que este repositorio usa para documentar constantes. Sin esa distinción el
comprobador marcaría toda la documentación del proyecto y se acabaría desactivando, que es
justo el fallo contra el que existe.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

__all__ = ["FRONTMATTER_OBLIGATORIO", "LARGO_SOSPECHOSO", "cadenas_sospechosas", "frontmatter"]

RAIZ = Path(__file__).resolve().parents[1]
PROMPTS = RAIZ / "prompts"
LARGO_SOSPECHOSO = 200
FRONTMATTER_OBLIGATORIO = ("id", "version", "modelo_destino", "temperatura", "cambios")

_PROMPT_ID = re.compile(r"""prompt_id\s*=\s*["']([\w./-]+)["']""")


def _enunciados(arbol: ast.AST) -> set[int]:
    """Los literales que **son** un enunciado: docstrings y docstrings de atributo.

    Python solo reconoce como docstring el primer literal de un módulo, clase o función. Este
    repositorio usa además el literal que sigue a una asignación para documentar constantes
    —`MAX_FUENTES = 5` y debajo su explicación—, que es documentación igual y no un prompt.
    """
    vistos: set[int] = set()
    for nodo in ast.walk(arbol):
        cuerpo = getattr(nodo, "body", None)
        if not isinstance(cuerpo, list):
            continue
        for sentencia in cuerpo:
            if (
                isinstance(sentencia, ast.Expr)
                and isinstance(sentencia.value, ast.Constant)
                and isinstance(sentencia.value.value, str)
            ):
                vistos.add(id(sentencia.value))
    return vistos


def cadenas_sospechosas(fuente: str) -> list[tuple[int, int]]:
    """`(línea, longitud)` de cada literal que parece un prompt metido en el código."""
    arbol = ast.parse(fuente)
    enunciados = _enunciados(arbol)
    return [
        (nodo.lineno, len(nodo.value))
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant)
        and isinstance(nodo.value, str)
        and len(nodo.value) > LARGO_SOSPECHOSO
        and "\n\n" in nodo.value
        and id(nodo) not in enunciados
    ]


def frontmatter(texto: str) -> dict[str, str]:
    """Las claves del bloque `---` inicial. Vacío si no lo hay: eso ya es el fallo."""
    if not texto.startswith("---\n"):
        return {}
    cierre = texto.find("\n---", 4)
    if cierre == -1:
        return {}
    campos: dict[str, str] = {}
    for linea in texto[4:cierre].splitlines():
        if ":" in linea and not linea.startswith((" ", "-", "#")):
            clave, _, valor = linea.partition(":")
            campos[clave.strip()] = valor.strip()
    return campos


def main() -> int:
    fallos: list[str] = []

    for fichero in sorted(RAIZ.joinpath("src").rglob("*.py")):
        for linea, largo in cadenas_sospechosas(fichero.read_text(encoding="utf-8")):
            fallos.append(
                f"{fichero.relative_to(RAIZ)}:{linea} · literal de {largo} caracteres con "
                "párrafos: parece un prompt. Va en `prompts/*.md` con su frontmatter (R5)"
            )

    ids: set[str] = set()
    for fichero in sorted(PROMPTS.glob("*.md")) if PROMPTS.is_dir() else []:
        campos = frontmatter(fichero.read_text(encoding="utf-8"))
        faltan = [c for c in FRONTMATTER_OBLIGATORIO if c not in campos]
        if faltan:
            fallos.append(
                f"{fichero.relative_to(RAIZ)} · sin {', '.join(faltan)} en el frontmatter"
            )
        if "id" in campos:
            ids.add(campos["id"])

    for fichero in sorted(RAIZ.joinpath("src").rglob("*.py")):
        for referido in _PROMPT_ID.findall(fichero.read_text(encoding="utf-8")):
            if referido not in ids:
                fallos.append(
                    f"{fichero.relative_to(RAIZ)} · referencia el prompt {referido!r} y no "
                    f"existe ninguno con ese `id`. Hay: {sorted(ids) or 'ninguno'}"
                )

    for fallo in fallos:
        print(f"  {fallo}")
    if fallos:
        print(f"R5 roja · {len(fallos)} incumplimientos")
        return 1
    print(f"R5 ok · prompts fuera del código, {len(ids)} con frontmatter completo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
