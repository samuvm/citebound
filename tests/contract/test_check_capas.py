"""Los comprobadores de `R6` y `R7`, que existen desde la fase 3 y no antes.

Las dos reglas llevaban escritas desde el primer día con el nombre de su script al lado, y los
scripts no existían. Una regla sin comprobación mecánica es una sugerencia — lo dice `RULES` en
su propia cabecera— y las sugerencias se erosionan.

`R6` importa más en esta fase que en ninguna: `domain/` acaba de recibir el verificador de citas
y la máquina de reintentos, que son quienes deciden si una respuesta sale. Si esa decisión
pudiera depender de la red o del entorno, dos ejecuciones del mismo caso podrían diferir.
"""

from __future__ import annotations

from scripts.check_deps import raiz_del_paquete, revisar
from scripts.check_layering import infracciones

# --------------------------------------------------------------------------------------
# R6 · las capas
# --------------------------------------------------------------------------------------


def test_un_import_de_red_en_dominio_se_caza() -> None:
    assert infracciones("import httpx\n") != []
    assert infracciones("from psycopg import connect\n") != []


def test_importar_hacia_fuera_del_dominio_se_caza() -> None:
    """`domain/` es la capa de dentro. Un import a `retrieval` invertiría la dependencia y
    haría imposible probarlo con valores."""
    assert infracciones("from citebound.retrieval.vector import Recuperado\n") != []
    assert infracciones("from citebound.providers.chat import Generador\n") != []


def test_leer_el_entorno_se_caza_en_sus_tres_formas() -> None:
    """`os.environ`, `os.getenv` y el `from os import environ`. Cerrar solo una deja las otras
    dos abiertas, y la que quede es la que alguien usará."""
    assert infracciones("import os\nx = os.environ['A']\n") != []
    assert infracciones("import os\nx = os.getenv('A')\n") != []
    assert infracciones("from os import environ\nx = environ['A']\n") != []


def test_mencionar_un_prohibido_en_un_docstring_no_se_caza() -> None:
    """**Por qué es AST y no `grep`.** Este repositorio explica constantemente por qué NO
    importa esas cosas, y un `grep` marcaría cada explicación. El comprobador se desactivaría
    en una tarde."""
    assert infracciones('"""No se importa httpx aquí: eso es os.environ de otra capa."""\n') == []


def test_lo_que_el_dominio_si_puede_importar_no_se_caza() -> None:
    fuente = "from dataclasses import dataclass\nfrom citebound.domain.legalref import LegalRef\n"
    assert infracciones(fuente) == []


def test_el_dominio_de_verdad_cumple_la_regla() -> None:
    """Contra los cuatro módulos reales, no contra un ejemplo."""
    from pathlib import Path

    from scripts.check_layering import RAIZ, RUTA_DOMINIO

    fallos = [
        f
        for fichero in sorted(Path(RAIZ / RUTA_DOMINIO).rglob("*.py"))
        for f in infracciones(fichero.read_text(encoding="utf-8"), fichero.name)
    ]
    assert fallos == []


# --------------------------------------------------------------------------------------
# R7 · las dependencias
# --------------------------------------------------------------------------------------


def test_langchain_se_caza_en_cualquiera_de_sus_formas() -> None:
    for req in ("langchain", "langchain-core>=0.3", "langchain_openai", "langchain[all]==1.0"):
        assert revisar({"project": {"dependencies": [req]}}) != [], req


def test_langgraph_no_se_caza() -> None:
    """La distinción es la regla entera: LangGraph aporta un grafo con estado y *timeouts* por
    nodo; LangChain aporta abstracciones sobre el retrieval y el LLM, que aquí están escritas a
    mano a propósito."""
    assert revisar({"project": {"dependencies": ["langgraph==1.2.10"]}}) == []


def test_tambien_se_miran_los_extras_y_los_grupos() -> None:
    """Meterlo en un grupo de desarrollo es la forma obvia de esquivar la regla, y una
    dependencia de desarrollo acaba importándose en `src/` igual."""
    assert revisar({"project": {"optional-dependencies": {"dev": ["langchain"]}}}) != []
    assert revisar({"dependency-groups": {"dev": ["langchain-core"]}}) != []


def test_la_raiz_del_paquete_ignora_version_extras_y_marcadores() -> None:
    assert raiz_del_paquete("langchain-core>=0.3,<0.4 ; python_version>='3.12'") == "langchain-core"
    assert raiz_del_paquete("Langchain_Core[all]==1.0") == "langchain-core"
