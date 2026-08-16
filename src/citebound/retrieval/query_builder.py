"""Constructor del SQL de la búsqueda léxica · la pata de palabras del híbrido.

**Se llama `ts_rank_cd` y no BM25.** `ts_rank_cd` es cobertura de densidad: pondera los
términos por su peso y por lo juntos que aparecen, pero **no** tiene saturación de frecuencia
ni normalización por longitud del documento, que son las dos cosas que definen BM25. Mientras
no haya una extensión BM25 real instalada, llamarlo BM25 sería mentir sobre lo que corre
(`CLAUDE.md`, invariante 7).

**Aquí no se ejecuta nada.** Este módulo devuelve una cadena y unos parámetros, y por eso se
puede probar entero sin base de datos — que es lo que `docs/PLAN.md` pide para él: tests sobre
la cadena generada y un test de que ningún parámetro se interpola por formato.

Ese último importa más de lo que parece. La pregunta llega del banco sin filtrar; una
`f-string` con el texto dentro sería inyección, pero **antes** de eso sería un fallo de recall
mudo: una comilla en un enunciado rompe la consulta y el caso sale con cero resultados sin que
nada avise. Un cero por sintaxis y un cero por no encontrar nada se parecen demasiado.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CONFIG_TS", "Consulta", "busqueda_lexica"]

CONFIG_TS = "spanish_unaccent"
"""La configuración de búsqueda que crea el DDL compartido, y con la que está **generada** la
columna `content_tsv`. Buscar con `spanish` a secas daría recall cero sin ningún error: la
columna estaría indexada con una configuración y la consulta usaría otra."""

# `chunks_active` es el alias que resuelve ADR-018. Consultar `chunk_v1` directamente ataría
# la búsqueda a una versión física del índice y rompería la conmutación sin parar el servicio.
TABLA = "chunks_active"


@dataclass(frozen=True, slots=True)
class Consulta:
    """SQL y parámetros, siempre separados y siempre inmutables.

    Que sea `frozen` no es adorno: se construye una vez y se ejecuta, y nadie debe poder
    cambiarle el SQL entre una cosa y la otra.
    """

    sql: str
    parametros: tuple[object, ...]


def busqueda_lexica(pregunta: str, *, k: int, materia: str | None = None) -> Consulta:
    """Los `k` chunks que mejor casan con la pregunta, por cobertura de densidad.

    `websearch_to_tsquery` y no `plainto_tsquery`: el primero entiende comillas y `-` como lo
    hace un buscador y **nunca lanza** ante una entrada rara, mientras que `to_tsquery` exige
    sintaxis válida y reventaría con cualquier enunciado del banco.

    El orden de los parámetros es el de los marcadores, y eso hay que cuidarlo a mano: `psycopg`
    sustituye **por posición**, así que un desajuste mandaría la materia al hueco del texto y
    al revés. No daría error: daría cero resultados y ninguna traza.
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, recibido {k}")
    if not pregunta.strip():
        raise ValueError(
            "la pregunta no puede estar vacía: `websearch_to_tsquery('')` casa con todo y "
            "ordena por nada, o sea que devolvería resultados arbitrarios con pinta de recall"
        )

    parametros: list[object] = [CONFIG_TS, pregunta, CONFIG_TS, pregunta]
    filtro = ""
    if materia is not None:
        filtro = "\n           AND materia = %s"
        parametros.append(materia)
    parametros.append(k)

    # noqa/nosec con su motivo: lo unico que entra en la f-string son `TABLA` y `filtro`,
    # dos constantes de este modulo. Ni un valor del usuario toca la cadena — todos van por
    # `parametros`, y hay un test que lo comprueba con una carga de inyeccion real
    # (`test_ningun_valor_del_usuario_aparece_en_la_cadena_sql`). Se declara la excepcion en
    # vez de reestructurar para esquivar al linter: el aviso es correcto en general.
    sql = f"""
        SELECT legal_ref,
               content,
               ts_rank_cd(content_tsv, websearch_to_tsquery(%s, %s)) AS rango,
               titulo,
               metadata ->> 'id_norma_version' AS id_norma_version
          FROM {TABLA}
         WHERE content_tsv @@ websearch_to_tsquery(%s, %s){filtro}
         ORDER BY rango DESC, legal_ref ASC
         LIMIT %s
    """  # noqa: S608  # nosec B608
    return Consulta(sql, tuple(parametros))
