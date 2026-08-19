"""El camino **servido**: streaming a través del guardia, con las mismas reglas que el grafo.

Hay dos caminos y conviene decir por qué. `agent.graph` es el que **se evalúa**: no necesita
streaming, corre entero y `make eval` lo usa para medir. Este es el que **se sirve**: emite
tokens según llegan para que `G-TTFT` mida lo que dice medir.

**Que sean dos no puede significar que decidan distinto.** Los dos preguntan a
`domain.retry.decidir`, los dos verifican con `domain.citation.verificar`, y hay un test de
integración que los enfrenta sobre las mismas grabaciones y exige el mismo veredicto. Si algún
día divergen, `make eval` estaría midiendo un sistema que nadie ejecuta — que es exactamente el
problema que Q-019 planteó con el reordenador y del que este proyecto ya tiene cicatriz.

`RULES` §3.1 pone `agent/` en TDD prohibido salvo `stream_guard`. Esto se prueba por su
comportamiento observable con dobles grabados.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from citebound.agent.graph import NO_PUEDO_RESPONDER, Generador, Recuperador, Resultado
from citebound.agent.stream_guard import Estado, StreamGuard
from citebound.domain.citation import Fuente, Veredicto, parsear_borrador, verificar
from citebound.domain.retry import Salida, decidir, resolver_curso

__all__ = ["Trozo", "servir"]


@dataclass(frozen=True, slots=True)
class Trozo:
    """Lo que sale mientras el modelo escribe. `retractado` marca el corte."""

    texto: str
    intento: int
    retractado: bool = False


def servir(
    pregunta: str,
    *,
    recuperador: Recuperador,
    generador: Generador,
    plantilla: str,
    max_reintentos: int | None = None,
) -> Iterator[Trozo | Resultado]:
    """Emite `Trozo` mientras el modelo escribe y termina con un `Resultado`.

    El `Resultado` final lo calcula `domain.retry.resolver_curso` sobre la lista entera de
    veredictos, igual que el grafo: es el mismo código puro decidiendo, y por eso los dos
    caminos coinciden por construcción y no por disciplina.
    """
    from citebound.domain.retry import MAX_REINTENTOS

    tope = MAX_REINTENTOS if max_reintentos is None else max_reintentos
    fuentes: list[Fuente] = list(recuperador(pregunta))
    veredictos: list[Veredicto] = []
    borradores: list[str] = []

    for intento in range(tope + 1):
        guardia = StreamGuard(len(fuentes))
        prompt = plantilla.format(pregunta=pregunta, fuentes=_bloques(fuentes))
        emitido_antes = ""

        for token in generador.emitir(prompt):
            estado = guardia.consumir(token)
            nuevo = guardia.emitido[len(emitido_antes) :]
            if nuevo:
                yield Trozo(texto=nuevo, intento=intento)
                emitido_antes = guardia.emitido
            if estado is Estado.RETRACTADO:
                # **Aquí está la diferencia con un filtro final**: el hueco malo no ha salido y
                # el resto del borrador no se llega a pedir.
                yield Trozo(texto="", intento=intento, retractado=True)
                break

        borradores.append(guardia.emitido)
        if guardia.estado is Estado.RETRACTADO:
            veredictos.append(_fuera_de_rango())
        else:
            _, citas = parsear_borrador(guardia.emitido)
            veredictos.append(verificar(citas, fuentes))

        if NO_PUEDO_RESPONDER in guardia.emitido.upper():
            yield _abstenido(fuentes, borradores)
            return

        salida = decidir(veredictos[-1], reintentos_hechos=intento, hay_fuentes=bool(fuentes))
        if salida is not Salida.REINTENTAR:
            break

    curso = resolver_curso(veredictos, hay_fuentes=bool(fuentes))
    if curso.salida is not Salida.RESPONDER:
        yield Resultado(curso=curso, fuentes=tuple(fuentes), borradores=tuple(borradores))
        return

    respuesta, citas = parsear_borrador(borradores[curso.reintentos])
    yield Resultado(
        curso=curso,
        respuesta=respuesta,
        citas=citas,
        fuentes=tuple(fuentes),
        borradores=tuple(borradores),
    )


def _bloques(fuentes: Sequence[Fuente]) -> str:
    """Idéntico al del grafo, y a propósito: si numeraran distinto, el mismo borrador
    significaría cosas distintas según por dónde se sirviera."""
    return "\n\n".join(f"[{i}] {f.texto}" for i, f in enumerate(fuentes, start=1))


def _fuera_de_rango() -> Veredicto:
    from citebound.domain.citation import Motivo

    return Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)


def _abstenido(fuentes: Sequence[Fuente], borradores: Sequence[str]) -> Resultado:
    from citebound.domain.retry import Curso

    return Resultado(
        curso=Curso(salida=Salida.ABSTENERSE, reintentos=max(0, len(borradores) - 1)),
        fuentes=tuple(fuentes),
        borradores=tuple(borradores),
    )
