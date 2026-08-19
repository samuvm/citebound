"""`R5` tiene comprobador desde la fase 3, y aquí se comprueba el comprobador.

Una regla sin comprobación mecánica es una sugerencia. Un comprobador sin tests es una
sugerencia con `exit 0`, que es peor: da confianza.

Lo que más importa de estos tests es la **distinción entre un prompt y la documentación**. Este
repositorio documenta sus constantes con literales largos justo debajo de la asignación —cientos
de ellos— y un comprobador que los marcara se desactivaría en una tarde. Esa es exactamente la
forma en que una regla se erosiona sin que nadie lo decida.
"""

from __future__ import annotations

from pathlib import Path

from scripts.check_prompts import (
    FRONTMATTER_OBLIGATORIO,
    LARGO_SOSPECHOSO,
    cadenas_sospechosas,
    frontmatter,
)

RAIZ = Path(__file__).resolve().parents[2]
LARGO = "línea de relleno para pasar del umbral. " * 8


# --------------------------------------------------------------------------------------
# (a) Un prompt inline se caza; la documentación no
# --------------------------------------------------------------------------------------


def test_un_prompt_asignado_a_una_constante_se_caza() -> None:
    fuente = f'PLANTILLA = """Pregunta: {{q}}\n\n{LARGO}"""\n'
    assert cadenas_sospechosas(fuente) != []


def test_un_prompt_pasado_directamente_en_la_llamada_se_caza() -> None:
    """Sacarlo de la constante y meterlo en el argumento es la forma obvia de esquivar el
    comprobador, así que tiene que dar igual dónde esté."""
    assert cadenas_sospechosas(f'completar("""Pregunta\n\n{LARGO}""")\n') != []


def test_el_docstring_de_un_modulo_no_se_caza() -> None:
    assert cadenas_sospechosas(f'"""Título.\n\n{LARGO}"""\nx = 1\n') == []


def test_el_docstring_de_una_funcion_no_se_caza() -> None:
    assert cadenas_sospechosas(f'def f():\n    """Título.\n\n    {LARGO}"""\n    return 1\n') == []


def test_el_docstring_de_atributo_no_se_caza() -> None:
    """**El que decide si la regla sobrevive.** `MAX_FUENTES = 5` y debajo su explicación es el
    estilo de todo el repositorio. Python no lo reconoce como docstring —es una expresión
    suelta— pero es documentación igual, y marcarla vaciaría el comprobador de sentido."""
    assert cadenas_sospechosas(f'MAX = 5\n"""Explicación.\n\n{LARGO}"""\n') == []


def test_una_cadena_larga_sin_parrafos_no_se_caza() -> None:
    """El doble salto de línea es la firma de un prompt. Un SQL largo o un mensaje de error de
    varias líneas no lo son, y marcarlos sería ruido."""
    assert cadenas_sospechosas(f'SQL = "{LARGO}"\n') == []


def test_una_cadena_con_parrafos_pero_corta_no_se_caza() -> None:
    assert cadenas_sospechosas('MSG = "hola\\n\\nadiós"\n') == []


def test_el_umbral_es_el_que_dice_la_regla() -> None:
    assert LARGO_SOSPECHOSO == 200


# --------------------------------------------------------------------------------------
# (b) El frontmatter
# --------------------------------------------------------------------------------------


def test_se_leen_las_claves_del_frontmatter() -> None:
    campos = frontmatter("---\nid: x\nversion: 2\n---\nCuerpo del prompt.\n")
    assert campos == {"id": "x", "version": "2"}


def test_un_fichero_sin_frontmatter_no_trae_claves() -> None:
    assert frontmatter("Cuerpo sin frontmatter.\n") == {}


def test_un_frontmatter_sin_cerrar_no_trae_claves() -> None:
    """Abierto y sin cerrar, el cuerpo entero se leería como metadatos."""
    assert frontmatter("---\nid: x\nCuerpo.\n") == {}


def test_las_lineas_del_cuerpo_no_se_confunden_con_claves() -> None:
    """El cuerpo de un prompt lleva dos puntos por todas partes."""
    campos = frontmatter("---\nid: x\n---\nRelevante significa: el que tipifica.\n")
    assert campos == {"id": "x"}


# --------------------------------------------------------------------------------------
# Contra los prompts de verdad
# --------------------------------------------------------------------------------------


def test_todos_los_prompts_del_repositorio_traen_su_frontmatter_completo() -> None:
    ficheros = sorted((RAIZ / "prompts").glob("*.md"))
    assert ficheros, "no hay ningún prompt: la fase 3 los necesita"
    for fichero in ficheros:
        campos = frontmatter(fichero.read_text(encoding="utf-8"))
        faltan = [c for c in FRONTMATTER_OBLIGATORIO if c not in campos]
        assert faltan == [], f"{fichero.name} sin {faltan}"


def test_ningun_modulo_de_src_lleva_un_prompt_dentro() -> None:
    """La regla contra el código de verdad. Estuvo incumplida desde la fase 2 —el prompt del
    reordenador— y nadie lo vio porque el comprobador no existía."""
    culpables = [
        f"{f.relative_to(RAIZ)}:{linea}"
        for f in sorted((RAIZ / "src").rglob("*.py"))
        for linea, _ in cadenas_sospechosas(f.read_text(encoding="utf-8"))
    ]
    assert culpables == []
