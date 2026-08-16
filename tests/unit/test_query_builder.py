"""Unit tests for `citebound.retrieval.query_builder` · fase 2.

Construye el SQL de la búsqueda léxica. `docs/PLAN.md` pide dos cosas de él: tests sobre la
cadena generada, y **un test de que ningún parámetro se interpola por formato**.

Ese segundo es el que importa de verdad. La pregunta del usuario llega a esta función sin
filtrar, y una `f-string` con el texto dentro sería inyección de SQL directa — pero además, y
antes que eso, sería un fallo de recall silencioso: una comilla en la pregunta rompería la
consulta y el caso saldría con cero resultados sin que nada avisara.

**Se llama `ts_rank_cd` y no BM25**, mientras no haya una extensión BM25 real instalada
(`CLAUDE.md`, invariante 7). Llamarlo BM25 en el README sería mentir sobre la implementación.
"""

from __future__ import annotations

import re

import pytest

from citebound.retrieval.query_builder import CONFIG_TS, busqueda_lexica


def test_la_consulta_lleva_su_sql_y_sus_parametros_separados() -> None:
    consulta = busqueda_lexica("adelantar en curva", k=30)
    assert "SELECT" in consulta.sql
    assert consulta.parametros


def test_ningun_valor_del_usuario_aparece_en_la_cadena_sql() -> None:
    """**El test que pide `PLAN.md`.** Si el texto de la pregunta apareciera en el SQL, sería
    inyección; y antes que eso, una comilla en un enunciado del banco rompería la consulta y
    el caso saldría con cero resultados sin que nada avisara."""
    peligro = "curva'; DROP TABLE chunk_v1; --"
    consulta = busqueda_lexica(peligro, k=5)
    assert peligro not in consulta.sql
    assert "DROP" not in consulta.sql.upper()
    # Y desde el arreglo del 2026-08-17, tampoco llega entero a los parámetros: se tokeniza a
    # palabras, así que los signos con los que se construye una inyección desaparecen antes.
    assert peligro not in consulta.parametros
    assert not any(isinstance(p, str) and ("'" in p or ";" in p) for p in consulta.parametros)


def test_todos_los_huecos_del_sql_son_marcadores_de_parametro() -> None:
    """Ni `%(nombre)s` ni `{}`: solo `%s`, y tantos como parámetros."""
    consulta = busqueda_lexica("señales", k=10, materia="Velocidad")
    assert consulta.sql.count("%s") == len(consulta.parametros)
    assert "{" not in consulta.sql
    assert "%(" not in consulta.sql


def test_el_k_viaja_como_parametro_y_no_incrustado() -> None:
    """`k` es un entero y sería tentador meterlo con una f-string. Pasa por parámetro igual
    que el resto: una excepción abre la puerta a la siguiente."""
    consulta = busqueda_lexica("luces", k=30)
    assert "LIMIT %s" in consulta.sql
    assert 30 in consulta.parametros


def test_se_usa_ts_rank_cd_y_no_se_le_llama_bm25() -> None:
    """Invariante 7 de `CLAUDE.md`. `ts_rank_cd` es cobertura de densidad, no BM25: no tiene
    saturación de frecuencia ni normalización por longitud. Llamarlo BM25 en el README sería
    mentir sobre lo que corre."""
    consulta = busqueda_lexica("arcén", k=5)
    assert "ts_rank_cd" in consulta.sql
    assert "bm25" not in consulta.sql.lower()


def test_la_configuracion_de_texto_es_la_del_contrato() -> None:
    """`spanish_unaccent` la crea el DDL compartido. Si aquí se usara `spanish` a secas, la
    consulta no casaría con la columna generada `content_tsv` y el recall léxico sería cero
    sin ningún error: la columna está indexada con una configuración y se buscaría con otra."""
    assert CONFIG_TS == "spanish_unaccent"
    assert CONFIG_TS in busqueda_lexica("señal", k=5).parametros


def test_se_consulta_la_vista_activa_y_no_una_tabla_fisica() -> None:
    """`chunks_active` es el alias que resuelve ADR-018. Consultar `chunk_v1` directamente
    ataría la búsqueda a una versión del índice y rompería la conmutación."""
    consulta = busqueda_lexica("intersección", k=5)
    assert "chunks_active" in consulta.sql
    assert "chunk_v1" not in consulta.sql


def test_sin_materia_no_hay_clausula_de_filtro() -> None:
    """Filtrar de más cuesta recall. Sin materia, la consulta no debe llevar el `WHERE`."""
    consulta = busqueda_lexica("velocidad", k=5)
    assert "materia" not in consulta.sql


def test_con_materia_se_filtra_y_va_como_parametro() -> None:
    consulta = busqueda_lexica("velocidad", k=5, materia="15 Velocidad")
    assert "materia = %s" in consulta.sql
    assert "15 Velocidad" in consulta.parametros


def test_el_orden_de_los_parametros_es_el_de_los_marcadores() -> None:
    """Un desajuste aquí no da error: `psycopg` sustituye por posición, así que la materia
    acabaría de consulta de texto y la consulta de materia. Cero resultados, sin traza."""
    consulta = busqueda_lexica("adelantamiento", k=7, materia="06 Adelantamientos")
    posiciones = [m.start() for m in re.finditer(r"%s", consulta.sql)]
    assert len(posiciones) == len(consulta.parametros)
    # El texto de la pregunta va antes que el filtro, y el LIMIT siempre el último.
    assert consulta.parametros[-1] == 7
    assert consulta.parametros.index("adelantamiento") < consulta.parametros.index(
        "06 Adelantamientos"
    )


@pytest.mark.parametrize("k", [0, -1])
def test_un_k_no_positivo_es_un_error(k: int) -> None:
    with pytest.raises(ValueError, match="k"):
        busqueda_lexica("algo", k=k)


def test_una_pregunta_vacia_es_un_error() -> None:
    """Una consulta vacía casa con todo y ordena por nada. Es peor que un error: da 30
    resultados arbitrarios que parecen recall."""
    with pytest.raises(ValueError, match=r"término|termino|vac"):
        busqueda_lexica("   ", k=5)


def test_la_consulta_es_inmutable() -> None:
    """Se construye una vez y se ejecuta; nadie debe poder cambiarle el SQL después."""
    consulta = busqueda_lexica("señal", k=5)
    with pytest.raises((AttributeError, TypeError)):
        consulta.sql = "DROP TABLE chunk_v1"  # type: ignore[misc]


def test_devuelve_las_columnas_que_el_recuperador_necesita() -> None:
    """`legal_ref` es la unidad de verdad (R1): sin ella no se puede puntuar nada. El
    `chunk_id` no se selecciona **a propósito**, para que no pueda acabar en una cita."""
    consulta = busqueda_lexica("señal", k=5)
    for columna in ("legal_ref", "content", "titulo"):
        assert columna in consulta.sql
    assert "chunk_id" not in consulta.sql


# --------------------------------------------------------------------------------------
# El bug que encontró la primera medición de recall · 2026-08-17
# --------------------------------------------------------------------------------------


def test_los_terminos_se_combinan_con_or_y_no_con_and() -> None:
    """**El defecto que dejaba la pata léxica devolviendo listas vacías.**

    `websearch_to_tsquery` combina con AND: la pregunta entera exige que el artículo contenga
    *todas* sus palabras. «Al acercarse a un centro docente, ¿qué precauciones debe tomar?»
    daba **cero** chunks, aunque el 46.1.b diga literalmente «centros docentes», porque el
    artículo no dice «precauciones» ni «tomar». Con OR casan 94 y el 46 entra en el top 5.

    Con AND, el canal léxico solo acierta cuando la pregunta es un trozo literal del BOE —
    o sea, casi nunca. Y no falla ruidosamente: devuelve la lista vacía, que es exactamente
    lo que devuelve una búsqueda legítima sin resultados.
    """
    consulta = busqueda_lexica("centro docente precauciones", k=5)
    expresion = next(p for p in consulta.parametros if isinstance(p, str) and " or " in p)
    assert expresion == "centro or docente or precauciones"


def test_la_puntuacion_y_los_signos_no_llegan_al_tsquery() -> None:
    """Tokenizar por palabras deja fuera comillas, guiones y `¿?`. Es lo que hace que la carga
    de inyección quede desarmada **antes** de llegar a Postgres, y no solo parametrizada."""
    consulta = busqueda_lexica("curva'; DROP TABLE chunk_v1; --", k=5)
    expresion = next(p for p in consulta.parametros if isinstance(p, str) and " or " in p)
    assert "'" not in expresion
    assert ";" not in expresion
    assert "-" not in expresion


def test_una_pregunta_de_solo_signos_es_un_error() -> None:
    """`¿?` no deja ni un término. Sin términos no hay consulta, y una consulta vacía casa con
    todo: 30 resultados arbitrarios con pinta de recall."""
    with pytest.raises(ValueError, match=r"término|termino|vac"):
        busqueda_lexica("¿... ?", k=5)


def test_los_terminos_se_normalizan_a_minusculas() -> None:
    """El tsvector está en minúsculas por la configuración; la consulta también, para que el
    resultado no dependa de cómo escribió la pregunta quien la hizo."""
    consulta = busqueda_lexica("Velocidad MÁXIMA", k=5)
    expresion = next(p for p in consulta.parametros if isinstance(p, str) and " or " in p)
    assert expresion == expresion.lower()
