"""El contrato SSE de `docs/RULES.md` §2.2, y el conflicto que resuelve.

`POST /ask` promete dos cosas incompatibles: **streaming** y **verificar la cita antes de
responder**. Si se verifica antes de emitir, el tiempo hasta el primer token es el tiempo de
generación completa. La resolución adoptada —y esto es lo que implementa este módulo— es que
salgan los tokens con sus marcadores, y que las **citas resueltas y verificadas** salgan al
final. Lo que hace segura esa concesión es `agent.stream_guard`: un marcador fuera de rango
corta en el token en que aparece, no al terminar.

**Se publican dos latencias, no una.** `TTFS` hasta `sources` y `TTFT` hasta el primer `token`.
Medir el TTFT hasta `sources` sería hacer trampa —`sources` sale antes de que el modelo hable—
y por eso los dos números viajan en `done` y el README lo dice.

La secuencia se construye aquí como **datos**, no como efectos: una función que devuelve
eventos se puede comprobar con un *snapshot* sin levantar un servidor, y eso es lo que `RULES`
§3.1 pide para `api/` en lugar de TDD.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from citebound.agent.graph import Resultado
from citebound.domain.citation import Fuente
from citebound.domain.retry import Salida

__all__ = ["Evento", "Latencias", "eventos", "formatear", "secuencia"]


class Evento(StrEnum):
    """Los siete del contrato, y ninguno más."""

    SOURCES = "sources"
    # `noqa: S105` con motivo: es el nombre del evento del contrato SSE, no una credencial.
    TOKEN = "token"  # noqa: S105
    RETRACT = "retract"
    CITATIONS = "citations"
    ABSTAIN = "abstain"
    DONE = "done"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Latencias:
    """Lo que `done` publica. **Las dos, siempre**, y por etapa además del total.

    `RULES` §2.1 reparte 1.290 ms entre etapas con 210 ms de margen, y una etapa fuera de su
    presupuesto marca ámbar aunque el total pase. Publicar solo el total escondería justo eso.
    """

    ttfs_ms: float
    ttft_ms: float
    por_etapa: dict[str, float]


def formatear(evento: Evento, datos: dict[str, Any]) -> str:
    """Un evento SSE en el formato del estándar: `event:`, `data:` y una línea en blanco.

    `ensure_ascii=False` y `sort_keys=True`: lo primero porque el corpus es español y escapar
    las tildes hace ilegible la traza; lo segundo porque un orden estable es lo que permite
    comparar dos ejecuciones byte a byte, que es lo que `G-EVAL-DET` exigirá en la fase 4.
    """
    carga = json.dumps(datos, ensure_ascii=False, sort_keys=True)
    return f"event: {evento.value}\ndata: {carga}\n\n"


def eventos(
    resultado: Resultado,
    *,
    latencias: Latencias,
    index_version: str,
    physical_table: str,
    modelo: str,
    prompt_id: str,
    prompt_version: int,
) -> Iterator[tuple[Evento, dict[str, Any]]]:
    """La secuencia entera, como datos. El transporte la serializa; aquí se decide qué va.

    El orden no es decorativo: `sources` va primero porque es lo primero que el usuario puede
    ver y llega mucho antes que el modelo, y `citations` va al final porque hasta entonces no
    están verificadas. Emitirlas antes sería prometer una verificación que aún no ocurrió.
    """
    yield Evento.SOURCES, {"fuentes": [_fuente(f, i) for i, f in enumerate(resultado.fuentes, 1)]}

    # Un `retract` por cada borrador que no salió. Van antes que el resultado porque eso es lo
    # que ocurrió, y esconderlos dejaría al usuario sin saber que el sistema se corrigió.
    for i in range(resultado.curso.reintentos):
        yield Evento.RETRACT, {"intento": i + 1, "motivo": _motivo(resultado, i)}

    if resultado.curso.salida is Salida.RESPONDER:
        yield Evento.TOKEN, {"texto": resultado.respuesta}
        yield (
            Evento.CITATIONS,
            {
                "citas": [
                    {
                        "n": cita.n,
                        "legal_ref": str(resultado.curso.refs[i]),
                        "quote": cita.quote,
                    }
                    for i, cita in enumerate(resultado.citas)
                    if i < len(resultado.curso.refs)
                ]
            },
        )
    else:
        yield (
            Evento.ABSTAIN,
            {
                "motivo": resultado.curso.motivo.value if resultado.curso.motivo else "sin_fuentes",
                "reintentos": resultado.curso.reintentos,
            },
        )

    yield (
        Evento.DONE,
        {
            "index_version": index_version,
            "latencias_ms": {
                "ttfs": round(latencias.ttfs_ms, 1),
                "ttft": round(latencias.ttft_ms, 1),
                **{k: round(v, 1) for k, v in sorted(latencias.por_etapa.items())},
            },
            "modelo": modelo,
            "physical_table": physical_table,
            "prompt_id": prompt_id,
            "prompt_version": prompt_version,
            "reintentos": resultado.curso.reintentos,
            "salida": resultado.curso.salida.value,
        },
    )


def _fuente(fuente: Fuente, n: int) -> dict[str, Any]:
    """Lo que se enseña de una fuente: su hueco, su referencia y su encabezado.

    **No se manda el texto entero.** Es el primer evento y compite con el presupuesto de
    `TTFS`; y el usuario no necesita el artículo completo para saber sobre qué se le va a
    responder — necesita saber cuál es.
    """
    return {"n": n, "legal_ref": str(fuente.ref), "titulo": fuente.texto.split("\n", 1)[0]}


def _motivo(resultado: Resultado, intento: int) -> str:
    """El motivo del intento `i`, si el grafo lo dejó anotado."""
    motivo = resultado.curso.motivo
    ultimo = intento == resultado.curso.reintentos - 1
    return motivo.value if (ultimo and motivo) else "no_verificado"


def secuencia(pares: Sequence[tuple[Evento, dict[str, Any]]]) -> str:
    """Los eventos ya serializados y pegados. Lo que un test de contrato compara."""
    return "".join(formatear(evento, datos) for evento, datos in pares)
