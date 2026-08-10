"""Contract tests for the schema. No database needed — these read files.

TDD is prohibited in `db/` (RULES §3): the shape of a schema is fixed by the engine and
by a contract, not by a test written first. What replaces it is this — a snapshot of what
must not drift — plus integration against a real Postgres in `tests/integration/`.

Two different things are guarded here, and conflating them is how a shared contract rots:

  * **`docs/CONTRACTS/chunks-ddl.sql` must stay byte-identical to `_comun/`.** CLAUDE.md
    says it in one line: *un `diff` contra el original es un test*. If this fails, either
    somebody edited a copy instead of the original, or the contract moved to v3 and this
    repo has not been told.
  * **This project's own DDL may only ADD.** The moment it can `CREATE` or `DROP`, the
    two projects stop sharing a schema and the whole point of the contract is gone.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from citebound.db.schema import (
    CONTRATO_VERSION,
    SchemaError,
    contrato_path,
    ddl_propio_path,
    esquema_sql,
)

RAIZ = Path(__file__).resolve().parents[2]
COMUN = Path("/Users/samuelviciana/Documents/day-300/_comun/CONTRACTS/chunks-ddl.sql")


# --------------------------------------------------------------------------------------
# the shared contract has not drifted
# --------------------------------------------------------------------------------------


@pytest.mark.skipif(not COMUN.is_file(), reason="_comun/ no está presente (repo suelto)")
def test_the_contract_copy_is_byte_identical_to_the_original() -> None:
    """`docs/CONTRACTS/` are literal copies of `_comun/CONTRACTS/`. A diff is a test.

    Skipped when `_comun/` is absent, which is what a cloned repo looks like: the
    scaffolding of the process is not part of the deliverable (constitución §7.8).
    """
    aqui = hashlib.sha256(contrato_path().read_bytes()).hexdigest()
    original = hashlib.sha256(COMUN.read_bytes()).hexdigest()
    assert aqui == original, (
        "la copia de docs/CONTRACTS/ y el original de _comun/ han divergido. "
        "Un contrato compartido se cambia en _comun/ y se propaga a los DOS repos."
    )


def test_the_contract_in_use_is_version_two() -> None:
    """Version 1 put the ordinal inside `chunk_id`, which made `G-INCR-2` of
    `indexkeeper-04` unreachable by construction (ADR-018). If this ever reads v1 again,
    somebody restored an old copy."""
    texto = contrato_path().read_text(encoding="utf-8")
    assert f"Version del contrato: {CONTRATO_VERSION}" in texto
    assert "occurrence" in texto
    assert "chunks_active" in texto


def test_the_contract_no_longer_switches_indexes_with_a_boolean() -> None:
    """Q-013 (b) = B1: `index_version.is_active` is gone, the alias table is in. The word
    may only survive in the comment that explains its removal."""
    lineas = [
        línea
        for línea in contrato_path().read_text(encoding="utf-8").splitlines()
        if "is_active" in línea and not línea.lstrip().startswith("--")
    ]
    assert lineas == [], f"is_active sigue vivo en el DDL: {lineas}"


# --------------------------------------------------------------------------------------
# this project's own DDL may only ADD
# --------------------------------------------------------------------------------------


def test_the_project_ddl_only_alters_and_never_creates_or_drops() -> None:
    """The one rule that keeps two projects on one schema. `ALTER … ADD CONSTRAINT` is a
    condition on top; `CREATE TABLE` would be a second, silently divergent schema."""
    sentencias = _sentencias(ddl_propio_path().read_text(encoding="utf-8"))
    assert sentencias, "el DDL propio no puede estar vacío: la condición de Q-013 es obligatoria"
    for sentencia in sentencias:
        assert sentencia.upper().startswith("ALTER TABLE"), (
            f"el DDL propio solo puede añadir condiciones, y esto no lo es: {sentencia[:60]}…"
        )
        assert " ADD CONSTRAINT " in sentencia.upper()


def test_the_norma_check_demanded_by_q013_is_present() -> None:
    """The condition this project put on accepting A2. Without it a chunk with no norma
    yields a `legal_ref` that falls back to `ref` and cannot be resolved against the
    corpus — and `G-HALLUC`, threshold `== 0` and not open to proposal, would be
    measuring against a broken set while still reporting zero."""
    propio = ddl_propio_path().read_text(encoding="utf-8").upper()
    assert "CHECK (NORMA IS NOT NULL)" in propio


def test_the_contract_itself_still_allows_a_null_norma() -> None:
    """The mirror of the test above, and the reason it has to exist here rather than in
    `_comun/`: the shared contract stays general so `indexkeeper-04` can use it with a
    corpus that is not legislation. The strictness is ours and lives in our file."""
    contrato = contrato_path().read_text(encoding="utf-8")
    declaracion = re.search(r"^\s*norma\s+TEXT[^,\n]*", contrato, re.M | re.I)
    assert declaracion is not None
    assert "NOT NULL" not in declaracion.group(0).upper()


# --------------------------------------------------------------------------------------
# how the two are assembled
# --------------------------------------------------------------------------------------


def test_the_schema_is_the_contract_first_and_our_constraints_after() -> None:
    """Order is load-bearing: our file only `ALTER`s tables the contract created."""
    sql = esquema_sql()
    assert sql.index("CREATE TABLE chunk_v1") < sql.index("chunk_v1_norma_obligatoria")


def test_the_schema_contains_both_files_whole() -> None:
    sql = esquema_sql()
    assert contrato_path().read_text(encoding="utf-8") in sql
    assert ddl_propio_path().read_text(encoding="utf-8") in sql


def test_assembling_the_schema_is_deterministic() -> None:
    assert esquema_sql() == esquema_sql()


def test_a_missing_file_is_reported_instead_of_producing_half_a_schema() -> None:
    """Half a schema applied without complaint is an index that looks fine and answers
    wrong."""
    with pytest.raises(SchemaError, match="falta"):
        from citebound.db import schema

        original = schema._RAIZ
        try:
            schema._RAIZ = RAIZ / "no-existe"
            schema.esquema_sql()
        finally:
            schema._RAIZ = original


def _sentencias(sql: str) -> list[str]:
    """Statements, with comments and blank lines removed."""
    sin_comentarios = "\n".join(
        línea for línea in sql.splitlines() if not línea.lstrip().startswith("--")
    )
    return [s.strip().replace("\n", " ") for s in sin_comentarios.split(";") if s.strip()]
