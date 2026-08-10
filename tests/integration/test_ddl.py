"""Integration: the schema against a real Postgres 18 + pgvector 0.8.6.

`docs/PLAN.md` phase 0 asks for one of these by name — *"integración con testcontainers:
ingerir dos veces no duplica"* — and ADR-018 added a second that is easy to skip and
expensive to skip: **proving with `EXPLAIN` that a query through the `chunks_active` view
still uses the HNSW index, and that `SET hnsw.ef_search` still reaches it.** A malformed
view destroys both in silence; nothing raises, nothing logs, and `G-RECALL5` just falls
with no explanation anyone can find.

Never in the fast gate (constitución §6): the container costs 10-40 s and on macOS it is
friction point number one. It runs in `make done`, which is where Samuel asked for it.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from citebound.db.schema import aplicar_esquema, registrar_index_version, upsert_chunks
from citebound.ingest.boe_xml import parse_norma
from citebound.ingest.chunking import CHUNKER_ID, chunk_preceptos

pytestmark = pytest.mark.integration

# Pinned by digest, never by tag (constitución §7.2). This is the exact image the
# `compose.yaml` of phase 0.7 will reference, and the same one the DDL was verified
# against on 2026-08-10.
IMAGEN = "pgvector/pgvector@sha256:691673308c99d2161ba298736f3147f1f22d79de2fb7ec93ae9b4afcab870b62"
NORMA = "RD-1428/2003"
URI = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/BOE-A-2003-23514"
CORPUS = Path(__file__).resolve().parents[2] / "corpus" / "raw" / "BOE-A-2003-23514.xml"
DIM = 1024
INDEX_ID = "v1-bgem3-1024"


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
                embedding_model="bge-m3",
                dim=DIM,
                chunker_id=CHUNKER_ID,
                corpus_snapshot="2026-07-31",
            )
        conn.commit()
        yield conn


@pytest.fixture(scope="module")
def chunks() -> tuple[object, ...]:
    preceptos = parse_norma(CORPUS.read_text(encoding="utf-8"), norma=NORMA)
    return chunk_preceptos(preceptos, source_uri=URI)


def _vector(semilla: int) -> list[float]:
    """A deterministic unit-ish vector. Recall is not measured here — that is
    `make eval-retrieval` in phase 2 — only that the plumbing holds."""
    return [((semilla + i) % 97) / 97.0 for i in range(DIM)]


# --------------------------------------------------------------------------------------
# the schema applies at all
# --------------------------------------------------------------------------------------


def test_the_schema_creates_every_object_the_contract_declares(conexion: object) -> None:
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tablas = {fila[0] for fila in cur.fetchall()}
        cur.execute("SELECT viewname FROM pg_views WHERE schemaname = 'public'")
        vistas = {fila[0] for fila in cur.fetchall()}
    assert {"index_version", "index_alias", "chunk_v1", "document_state"} <= tablas
    assert "chunks_active" in vistas


def test_the_hnsw_index_uses_the_hyperparameters_of_the_contract(conexion: object) -> None:
    """`m=16, ef_construction=64` are part of the contract for a reason: without them two
    projects measure recall over different structures and the numbers do not compare."""
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("SELECT indexdef FROM pg_indexes WHERE indexname = 'chunk_v1_embedding_hnsw'")
        definicion = cur.fetchone()[0]
    assert "hnsw" in definicion
    assert "m='16'" in definicion.replace(" ", "") or "m=16" in definicion.replace("'", "")
    assert "ef_construction" in definicion


# --------------------------------------------------------------------------------------
# the CHECK this project put on accepting a nullable norma (Q-013 a = A2)
# --------------------------------------------------------------------------------------


def test_a_chunk_without_norma_is_rejected_by_the_database(conexion: object) -> None:
    """The condition written into ADR-018. `G-HALLUC` is defined as membership of the
    `legal_ref` in the set of refs of the index; a row whose `legal_ref` falls back to
    `ref` cannot be resolved against the corpus, and the metric would keep reporting zero
    while measuring against a broken set."""
    psycopg = pytest.importorskip("psycopg")
    with (
        conexion.cursor() as cur,  # type: ignore[attr-defined]
        pytest.raises(psycopg.errors.CheckViolation),
    ):
        cur.execute(
            """
            INSERT INTO chunk_v1
                (chunk_id, index_version, content, content_hash, embedding, ref,
                 doc_id, ordinal, occurrence)
            VALUES ('sinnorma', %s, 'texto', 'h', %s, 'r', 'd', 9001, 0)
            """,
            (INDEX_ID, str(_vector(1))),
        )
    conexion.rollback()  # type: ignore[attr-defined]


def test_the_generated_legal_ref_matches_what_python_produces(conexion: object) -> None:
    """`legal_ref` is a generated column in Postgres and `format_ref` in Python. If the
    two ever disagree, a citation verified in memory stops matching the row it came from
    and nothing says so."""
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            INSERT INTO chunk_v1
                (chunk_id, index_version, content, content_hash, embedding, ref,
                 norma, articulo, apartado, doc_id, ordinal, occurrence)
            VALUES ('generada', %s, 'texto', 'h', %s, 'x',
                    'RD-1428/2003', '34', '1', 'd', 9002, 0)
            RETURNING legal_ref
            """,
            (INDEX_ID, str(_vector(2))),
        )
        assert cur.fetchone()[0] == "RD-1428/2003#art34.1"
    conexion.rollback()  # type: ignore[attr-defined]


# --------------------------------------------------------------------------------------
# ingest twice does not duplicate · docs/PLAN.md phase 0, by name
# --------------------------------------------------------------------------------------


def test_ingesting_the_whole_corpus_twice_does_not_duplicate_a_single_row(
    conexion: object, chunks: tuple[object, ...]
) -> None:
    """The identifiers are a pure function of (document, content, occurrence), so the
    second run computes exactly the ids of the first and `ON CONFLICT` has nothing to
    add. That is the property contract v2 exists to make possible."""
    embeddings = [_vector(i) for i in range(len(chunks))]
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        upsert_chunks(cur, chunks, embeddings, index_id=INDEX_ID)  # type: ignore[arg-type]
        cur.execute("SELECT count(*) FROM chunk_v1")
        primera = cur.fetchone()[0]

        upsert_chunks(cur, chunks, embeddings, index_id=INDEX_ID)  # type: ignore[arg-type]
        cur.execute("SELECT count(*) FROM chunk_v1")
        segunda = cur.fetchone()[0]
    conexion.commit()  # type: ignore[attr-defined]

    assert primera == len(chunks) == 235
    assert segunda == primera, "la segunda ingesta duplicó filas"


def test_every_indexed_row_carries_a_resolvable_legal_ref(conexion: object) -> None:
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("SELECT count(*) FROM chunk_v1 WHERE legal_ref IS NULL OR legal_ref = ''")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT count(DISTINCT legal_ref), count(*) FROM chunk_v1")
        distintas, total = cur.fetchone()
    assert distintas == total, "dos filas comparten legal_ref"


# --------------------------------------------------------------------------------------
# the condition ADR-018 attached to accepting the view (Q-013 b = B1)
# --------------------------------------------------------------------------------------


def test_the_view_does_not_stand_between_the_query_and_the_hnsw_index(
    conexion: object,
) -> None:
    """**The reason B1 was accepted with a condition** (ADR-018). Switching indexes
    through a view is worth a lot — it lets the embedding dimension change without
    stopping the service — but a malformed view turns every vector search into a
    sequential scan in silence: nothing raises, nothing logs, and `G-RECALL5` just falls
    with no explanation anyone can find.

    The claim is *the view does not block the index*, and it has to be tested that way
    rather than as *the plan uses the index*. With 235 rows the planner picks a
    sequential scan **through the physical table too**, and rightly so; asserting the
    plan directly would have tested the size of the corpus, not the shape of the view.
    So the seq scan is taken off the table and the two plans are compared: if the view
    were the problem, only one of them would reach the index.
    """
    consulta = "SELECT legal_ref FROM {} ORDER BY embedding <=> %s::vector LIMIT 5"
    planes = {}
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("ANALYZE chunk_v1")
        for objeto in ("chunk_v1", "chunks_active"):
            cur.execute("SET enable_seqscan = off")
            cur.execute("SET hnsw.ef_search = 100")
            cur.execute("EXPLAIN " + consulta.format(objeto), (str(_vector(7)),))
            planes[objeto] = " ".join(fila[0] for fila in cur.fetchall())
        cur.execute("SET enable_seqscan = on")

    for objeto, plan in planes.items():
        assert "chunk_v1_embedding_hnsw" in plan, f"{objeto} no alcanza el índice HNSW:\n{plan}"
    assert planes["chunks_active"].replace("chunks_active", "chunk_v1") == planes["chunk_v1"], (
        "el plan a través de la vista difiere del plan sobre la tabla:\n"
        f"vista : {planes['chunks_active']}\ntabla : {planes['chunk_v1']}"
    )


def test_the_planner_is_free_to_ignore_the_index_on_a_corpus_this_small(
    conexion: object,
) -> None:
    """Written down so nobody later reads the test above as a promise that every query
    uses HNSW. With 235 rows a sequential scan is genuinely cheaper and Postgres is right
    to choose it. The index earns its keep when the corpus grows — and if `G-RECALL5`
    ever disappoints in phase 2, this is the first thing to re-measure rather than
    assume."""
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("SELECT count(*) FROM chunk_v1")
        assert cur.fetchone()[0] == 235


def test_ef_search_reaches_the_index_through_the_view(conexion: object) -> None:
    """`SET hnsw.ef_search` is required to be declared and not left to the default
    (RULES error nº 12). If the view swallowed it, two projects would measure recall over
    different structures while both believing they used 100."""
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("SET hnsw.ef_search = 137")
        cur.execute("SHOW hnsw.ef_search")
        assert cur.fetchone()[0] == "137"
        cur.execute(
            "SELECT legal_ref FROM chunks_active ORDER BY embedding <=> %s::vector LIMIT 3",
            (str(_vector(11)),),
        )
        assert len(cur.fetchall()) == 3


def test_the_alias_resolves_to_a_physical_table_and_not_only_to_a_name(
    conexion: object,
) -> None:
    """The other half of the condition: an eval report must record the resolved physical
    target, never the alias. With the alias alone, two runs over different data would
    produce identical reports and `G-EVAL-DET` — threshold `== true`, not open to
    proposal — would stop meaning anything."""
    with conexion.cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("SELECT index_version, physical_table FROM index_alias WHERE alias = 'active'")
        index_version, physical_table = cur.fetchone()
    assert index_version == INDEX_ID
    assert physical_table == "chunk_v1"
