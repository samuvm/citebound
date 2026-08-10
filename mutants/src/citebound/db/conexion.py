"""Where the database lives, read from the environment and nowhere else."""

from __future__ import annotations

import os

__all__ = ["PUERTO_POR_DEFECTO", "dsn"]

PUERTO_POR_DEFECTO = "5434"


def _dsn_local(puerto: str) -> str:
    return f"postgresql://citebound:citebound@localhost:{puerto}/citebound"


def dsn() -> str:
    """`CITEBOUND_DSN`, or the one `compose.yaml` publishes on `CITEBOUND_PG_PORT`.

    The port is a variable and not an edit. D-03 says this machine hosts five projects,
    and on 2026-08-10 both 5432 and 5433 were already taken by other work of Samuel's.
    Hard-coding a port that turns out to be busy costs an afternoon and teaches nothing;
    5434 is only the default.
    """
    if (completo := os.environ.get("CITEBOUND_DSN")) is not None:
        return completo
    return _dsn_local(os.environ.get("CITEBOUND_PG_PORT", PUERTO_POR_DEFECTO))
