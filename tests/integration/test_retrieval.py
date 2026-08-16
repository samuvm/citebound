"""Integración: el recuperador híbrido contra un Postgres real, con datos sembrados.

`docs/PLAN.md` fase 2 lo pide por su nombre: *«integración con datos sembrados de resultado
conocido»*. Aquí no se mide recall — eso es `make eval-retrieval` contra el golden set —, sino
que **cada pata encuentra lo que le toca** y que la fusión no se come a ninguna.

Lo que hace útiles estos casos es que están construidos para que un canal falle y el otro no:

  · un **número** («1,5 metros») lo casa el léxico y el vectorial lo diluye, porque un
    embedding entiende sentido y una cifra no lo tiene;
  · una **paráfrasis sin palabras en común** la encuentra el vectorial y el léxico ni la ve.

Si el híbrido estuviera mal cableado —una pata apagada, un filtro de más, una fusión que
descarta lo que aparece en una sola lista— estos dos casos lo dicen. Un test de recall
agregado, no: bajaría unos puntos y el diagnóstico apuntaría al troceado.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from citebound.db.schema import aplicar_esquema, registrar_index_version
from citebound.retrieval import lexical, pipeline
from citebound.retrieval.vector import Recuperado

pytestmark = pytest.mark.integration

IMAGEN = "pgvector/pgvector@sha256:691673308c99d2161ba298736f3147f1f22d79de2fb7ec93ae9b4afcab870b62"
NORMA = "RD-1428/2003"
DIM = 1024
INDEX_ID = "v1-bgem3-1024"

# Tres artículos inventados con una propiedad cada uno. El contenido es corto a propósito:
# lo que se prueba es el cableado, no el corpus.
SEMILLA = [
    # léxico puro: la cifra es literal y no tiene sentido que un embedding pueda captar
    ("85", "1", "El conductor guardará una anchura de seguridad de al menos 1,5 metros."),
    # vectorial puro: habla de lo mismo que la pregunta sin compartir una palabra con ella
    ("46", "1", "Se circulará a velocidad moderada cuando haya menores en la calzada."),
    # ruido: existe para que la lista no sea trivial
    ("173", "2", "V-2. Vehículos para obras o servicios y demás vehículos especiales."),
]


def _vector(semilla: int) -> list[float]:
    """Vectores deterministas y separados: el que corresponde a cada artículo se parece a su
    propia consulta y no a las otras. No hay modelo aquí — se prueba el cableado."""
    return [1.0 if i % 3 == semilla % 3 else 0.0 for i in range(DIM)]


class _EmbedderFalso:
    """Devuelve el vector del artículo que la pregunta debería encontrar.

    Un embedder de verdad aquí probaría el modelo, que no es lo que se está probando, y
    ataría el test a que Ollama esté levantado.
    """

    def __init__(self, semilla: int) -> None:
        self._semilla = semilla

    @property
    def model(self) -> str:
        return "falso"

    @property
    def dim(self) -> int:
        return DIM

    def embed(self, textos: object) -> tuple[tuple[float, ...], ...]:
        return (tuple(_vector(self._semilla)),)


@pytest.fixture(scope="module")
def conexion() -> Iterator[object]:
    psycopg = pytest.importorskip("psycopg")
    contenedores = pytest.importorskip("testcontainers.community.postgres")

    with (
        contenedores.PostgresContainer(IMAGEN, driver=None) as pg,
        psycopg.connect(pg.get_connection_url()) as conn,
    ):
        with conn.cursor() as cur:
            aplicar_esquema(cur)
            registrar_index_version(
                cur,
                index_id=INDEX_ID,
                embedding_model="falso",
                dim=DIM,
                chunker_id="articulo-v1",
                corpus_snapshot="2026-07-31",
            )
            for i, (articulo, apartado, contenido) in enumerate(SEMILLA):
                cur.execute(
                    """
                    INSERT INTO chunk_v1 (chunk_id, index_version, content, content_hash,
                                          embedding, ref, norma, articulo, apartado,
                                          titulo, materia, doc_id, ordinal, occurrence)
                    VALUES (%s, %s, %s, %s, %s::vector, %s, %s, %s, %s, %s, %s, %s, %s, 0)
                    """,
                    (
                        f"seed-{i:04d}",
                        INDEX_ID,
                        contenido,
                        f"hash-{i}",
                        "[" + ",".join(str(v) for v in _vector(i)) + "]",
                        f"{NORMA}#art{articulo}.{apartado}",
                        NORMA,
                        articulo,
                        apartado,
                        "TÍTULO II",
                        "materia-de-prueba",
                        "doc-seed",
                        i,
                    ),
                )
        conn.commit()
        yield conn


def _refs(resultados: tuple[Recuperado, ...]) -> list[str]:
    return [str(r.ref) for r in resultados]


# --------------------------------------------------------------------------------------
# cada pata encuentra lo suyo
# --------------------------------------------------------------------------------------


def test_el_lexico_encuentra_una_cifra_que_el_vectorial_diluiria(conexion: object) -> None:
    """«1,5 metros» es el caso de manual: un embedding entiende sentido y una cifra no lo
    tiene, así que el vectorial la reparte entre todo lo que hable de adelantar. El léxico la
    casa literalmente. Es la mitad del argumento para tener híbrido."""
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        encontrados = lexical.buscar(cur, "1,5 metros de anchura de seguridad", k=5)
    assert f"{NORMA}#art85.1" in _refs(encontrados)


def test_el_lexico_no_inventa_cuando_no_hay_nada_que_casar(conexion: object) -> None:
    """Una pregunta sin ningún término del corpus devuelve la lista vacía, y eso **no es un
    error**: es la señal de que este canal no aporta y de que manda el vectorial."""
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        assert lexical.buscar(cur, "zzzz qwerty inexistente", k=5) == ()


def test_el_lexico_respeta_el_filtro_de_materia(conexion: object) -> None:
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        assert lexical.buscar(cur, "metros", k=5, materia="no-existe") == ()
        assert lexical.buscar(cur, "metros", k=5, materia="materia-de-prueba")


# --------------------------------------------------------------------------------------
# el híbrido junta sin perder
# --------------------------------------------------------------------------------------


def test_el_hibrido_recupera_lo_que_solo_ve_el_vectorial(conexion: object) -> None:
    """La pregunta habla de «niños» y el artículo dice «menores»: cero palabras en común, así
    que el léxico no lo trae. Si el híbrido exigiera acuerdo entre las dos patas, este caso se
    perdería — y es justo el que justifica tener un canal semántico."""
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        encontrados = pipeline.recuperar(
            cur, "niños cruzando la vía", embedder=_EmbedderFalso(1), k=3, k_canal=5
        )
    assert f"{NORMA}#art46.1" in _refs(encontrados)


def test_el_hibrido_no_pierde_lo_que_solo_ve_el_lexico(conexion: object) -> None:
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        encontrados = pipeline.recuperar(
            cur, "1,5 metros", embedder=_EmbedderFalso(1), k=3, k_canal=5
        )
    assert f"{NORMA}#art85.1" in _refs(encontrados)


def test_el_hibrido_devuelve_como_mucho_k_resultados(conexion: object) -> None:
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        encontrados = pipeline.recuperar(
            cur, "velocidad metros vehículos", embedder=_EmbedderFalso(0), k=2, k_canal=5
        )
    assert len(encontrados) <= 2


def test_ninguna_referencia_sale_repetida_del_hibrido(conexion: object) -> None:
    """Dos chunks del mismo artículo colapsan en una `legal_ref`. Contarla dos veces inflaría
    su puntuación en la fusión y, después, el recall."""
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        encontrados = pipeline.recuperar(
            cur, "metros menores vehículos", embedder=_EmbedderFalso(0), k=5, k_canal=10
        )
    refs = _refs(encontrados)
    assert len(refs) == len(set(refs))


def test_el_reordenador_manda_sobre_el_orden_de_la_fusion(conexion: object) -> None:
    """El puerto se prueba con un doble que invierte: si el pipeline ignorara al reordenador,
    este test no lo distinguiría de no tenerlo."""

    class DelReves:
        def reordenar(self, pregunta: str, candidatos: list[Recuperado]) -> list[Recuperado]:
            return list(reversed(candidatos))

    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        sin = pipeline.recuperar(
            cur, "metros menores vehículos", embedder=_EmbedderFalso(0), k=3, k_canal=10
        )
        con = pipeline.recuperar(
            cur,
            "metros menores vehículos",
            embedder=_EmbedderFalso(0),
            k=3,
            k_canal=10,
            reordenador=DelReves(),
        )
    assert _refs(sin) != _refs(con)
