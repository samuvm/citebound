"""Guardia del stream · esqueleto. El rojo se compromete antes que el verde."""

from __future__ import annotations

import re
from enum import StrEnum

__all__ = ["Estado", "StreamGuard", "trocear_en_tokens"]


class Estado(StrEnum):
    ABIERTO = "abierto"
    RETRACTADO = "retractado"


def trocear_en_tokens(texto: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\S+\s*|\s+", texto))


class StreamGuard:
    def __init__(self, max_fuentes: int) -> None:
        self.max_fuentes = max_fuentes
        self.estado = Estado.ABIERTO
        self.emitido = ""
        self.huecos: tuple[int, ...] = ()

    def consumir(self, token: str) -> Estado:
        return self.estado
