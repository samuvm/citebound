"""`R6` · `domain/` no importa I/O, ni SDKs, ni lee el entorno.

**No es purismo, es lo que hace verificable la tesis.** El verificador de citas y la máquina de
reintentos deciden si una respuesta sale o no sale. Si esa decisión pudiera depender de una
conexión, de una variable de entorno o de la hora, dos ejecuciones del mismo caso podrían dar
respuestas distintas — y `G-EVAL-DET`, cuyo umbral es `== true` y no admite propuesta, dejaría
de significar nada. Un `domain/` puro es lo que permite afirmar que la abstención se decidió por
el contenido y no por la red.

También es lo que hace que sus tests sean rápidos y deterministas sin dobles: `domain/` se
prueba con valores, no con *mocks*, y por eso puede llevar TDD obligatorio y Hypothesis.

Se comprueba con AST y no con `grep`: `grep` no distingue un import real de la palabra dentro de
un docstring, y este repositorio los menciona constantemente al explicar por qué NO están.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

__all__ = ["PROHIBIDOS", "RUTA_DOMINIO", "infracciones"]

RAIZ = Path(__file__).resolve().parents[1]
RUTA_DOMINIO = "src/citebound/domain"

PROHIBIDOS = frozenset(
    {
        "psycopg",
        "requests",
        "httpx",
        "ollama",
        "openai",
        "boto3",
        "langgraph",
        "fastapi",
        "sentence_transformers",
        "torch",
        "mlflow",
        # Del propio paquete: `domain/` es la capa de dentro y no puede mirar hacia fuera.
        "citebound.providers",
        "citebound.db",
        "citebound.api",
        "citebound.retrieval",
        "citebound.ingest",
    }
)


def _prohibido(modulo: str) -> str | None:
    for malo in PROHIBIDOS:
        if modulo == malo or modulo.startswith(f"{malo}."):
            return malo
    return None


def infracciones(fuente: str, nombre: str = "<memoria>") -> list[str]:
    """Importaciones vetadas y lecturas del entorno, con su línea."""
    arbol = ast.parse(fuente)
    fallos: list[str] = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if (malo := _prohibido(alias.name)) is not None:
                    fallos.append(f"{nombre}:{nodo.lineno} importa {alias.name} ({malo})")
        elif (
            isinstance(nodo, ast.ImportFrom)
            and nodo.module
            and (malo := _prohibido(nodo.module)) is not None
        ):
            fallos.append(f"{nombre}:{nodo.lineno} importa de {nodo.module} ({malo})")

        # `os.environ`, `os.getenv` y `environ[...]` en cualquiera de sus formas. Leer el
        # entorno aquí haría que la misma entrada diera dos resultados según quién la ejecute.
        if isinstance(nodo, ast.Attribute) and nodo.attr in ("environ", "getenv"):
            fallos.append(f"{nombre}:{nodo.lineno} lee el entorno con .{nodo.attr}")
        elif isinstance(nodo, ast.Name) and nodo.id in ("environ", "getenv"):
            fallos.append(f"{nombre}:{nodo.lineno} lee el entorno con {nodo.id}")

    return fallos


def main() -> int:
    carpeta = RAIZ / RUTA_DOMINIO
    if not carpeta.is_dir():
        print(f"no existe {RUTA_DOMINIO}")
        return 1

    fallos: list[str] = []
    ficheros = sorted(carpeta.rglob("*.py"))
    for fichero in ficheros:
        fallos += infracciones(fichero.read_text(encoding="utf-8"), str(fichero.relative_to(RAIZ)))

    for fallo in fallos:
        print(f"  {fallo}")
    if fallos:
        print(
            f"R6 roja · {len(fallos)} infracciones. `domain/` decide si una respuesta sale; "
            "si esa decisión dependiera de la red o del entorno, dos ejecuciones del mismo "
            "caso podrían diferir y `G-EVAL-DET` dejaría de medir nada"
        )
        return 1
    print(f"R6 ok · {len(ficheros)} módulos de dominio, sin I/O, sin SDKs y sin entorno")
    return 0


if __name__ == "__main__":
    sys.exit(main())
