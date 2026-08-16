"""Reciprocal Rank Fusion. FASE ROJA de la fase 2 — sin comportamiento."""

from __future__ import annotations

from collections.abc import Sequence

__all__ = ["K_RRF", "fusionar"]

K_RRF = 60


def fusionar(
    listas: Sequence[Sequence[str]], *, k: int = K_RRF, tope: int | None = None
) -> list[str]:
    return []  # RED
