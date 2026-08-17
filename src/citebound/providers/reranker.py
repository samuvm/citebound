"""Reordenador cross-encoder, en proceso · `Qwen3-Reranker-0.6B` sobre `sentence-transformers`.

**Por qué vuelve a estar aquí.** Q-017 eligió el generador como reordenador, por un solo
transporte. Q-020 lo revierte con la medida delante: aquel costaba **4.600 ms** contra un
presupuesto de 400 y se quedaba en `G-RECALL5` 0,852 contra un umbral de 0,90. Y el diagnóstico
que lo cierra es que **no era cuestión de tamaño** — un generalista de 9B ordena igual o peor
que el de 4B (0,843 contra 0,852) tardando un 56 % más. No es el tamaño del modelo, es el tipo:
esto está entrenado para ordenar.

Lo que cuesta, dicho entero: un **segundo camino de servir modelos** —Hugging Face además de
Ollama—, ~2 GB de dependencias y una descarga más en el arranque en frío. Samuel lo aceptó
sabiéndolo (Q-020 A), porque era la única opción que atacaba a la vez la calidad y `G-TTFT`.

**No exige un Mac.** `mps` es el backend de la máquina de desarrollo; el mismo código corre
sobre `cuda` o `cpu` cambiando `dispositivo`, que es un parámetro y no una edición.

`RULES` §3.1 pone `providers/` en **TDD prohibido**, y aquí se ve por qué: la forma de lo que
devuelve `CrossEncoder.predict` la fija la librería, no un test escrito antes. El orden es
grabar primero y testear contra la grabación — de ahí `RecordedReranker`.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from citebound.retrieval.vector import Recuperado

__all__ = [
    "CARACTERES_POR_CANDIDATO",
    "INSTRUCCION",
    "MODELO_POR_DEFECTO",
    "CrossEncoderReranker",
    "RecordedReranker",
    "RerankerError",
    "ordenar_por_puntos",
    "reordenador_por_defecto",
]

MODELO_POR_DEFECTO = "BAAI/bge-reranker-v2-m3"
"""**El retador de `docs/STACK.md` §2.2, que gana al principal en las dos columnas.**

Medido el 2026-08-17 sobre los mismos 216 casos:

| modelo | `G-RECALL5` | p95 de reordenar 30 |
|---|---:|---:|
| `BAAI/bge-reranker-v2-m3` (retador) | **0,801** | **400 ms** |
| `Qwen/Qwen3-Reranker-0.6B` (principal) | 0,787 | 886 ms |

`STACK.md` eligió el principal por ser *instruction-aware*, y ese argumento resultó no
sostenerse aquí: con la instrucción del dominio baja a **0,773**, peor que con la genérica.
El retador es de junio de 2024 y aun así ordena mejor este corpus, y encima cabe clavado en
los 400 ms que `RULES` §2.1 le presupuesta al rerank — un número que se escribió para un
cross-encoder y que este cumple exactamente."""

CARACTERES_POR_CANDIDATO = 500
"""Lo mismo que veía el reordenador anterior, para que la comparación sea de una sola variable.

Medido el 2026-08-17 con el generador: 1.200 caracteres iban **peor** que 500 y costaban el
doble. Si aquí conviene otro número, se mide y se cambia con el número delante."""

INSTRUCCION = (
    "Dada una pregunta sobre normativa de circulación española, recupera el artículo del "
    "Reglamento General de Circulación que TIPIFICA la conducta por la que se pregunta, "
    "no el que solo la menciona de pasada ni el que regula algo parecido"
)
"""**El motivo por el que `STACK.md` eligió este modelo, y que casi se queda sin usar.**

`Qwen3-Reranker` es *instruction-aware*: se le puede decir qué significa «relevante» aquí, y
esa distinción —tipificar contra mencionar— es la tesis del proyecto. `sentence-transformers`
carga el modelo con su instrucción por defecto, *«Given a web search query, retrieve relevant
passages»*, y con esa genérica funcionaba como un cross-encoder cualquiera.

Medido sobre un par de ejemplo, la distancia entre el artículo correcto y su vecino pasa de
**2,0 con la genérica a 5,5 con esta**. El efecto sobre el recall está en `docs/JOURNAL.md`.
"""

_TOPE = 30
"""Cuántos candidatos se reordenan. Con 10 el techo medido era 0,785 y con 30 es 0,977: el 17 %
de los casos tenía el artículo correcto en los puestos 11-30 y el reordenador ni los miraba."""


class RerankerError(RuntimeError):
    """El reordenador no puede cargar o no devuelve lo que se espera."""


def ordenar_por_puntos(
    candidatos: Sequence[Recuperado], puntos: Sequence[float]
) -> list[Recuperado]:
    """Los candidatos de mayor a menor puntuación, **sin perder ni inventar ninguno**.

    Es el mismo invariante que tenía el reordenador anterior y por el mismo motivo: si el
    reordenador perdiera documentos, el recall bajaría por su culpa y el diagnóstico apuntaría
    al índice, que es donde no estaría el problema. Aquí es más fácil de sostener —hay una
    puntuación por candidato— pero se comprueba igual, porque una librería que devuelva un
    array de otra longitud lo haría en silencio.
    """
    if len(puntos) != len(candidatos):
        raise RerankerError(
            f"{len(candidatos)} candidatos y {len(puntos)} puntuaciones: el reordenador "
            "perdería o inventaría documentos"
        )
    # `sorted` es estable, así que a igualdad de puntuación manda el orden de la fusión — que
    # ya es una señal. Empatar y barajar sería tirar información.
    return [c for _, c in sorted(zip(puntos, candidatos, strict=True), key=lambda p: -p[0])]


@dataclass
class CrossEncoderReranker:
    """Implementa el puerto `Reordenador` de `retrieval.pipeline`.

    El modelo se carga **la primera vez que se usa**, no al construir: `make eval-retrieval`
    sin reordenador no debe pagar 37 s de carga, y el arranque en frío de la API tampoco.
    """

    modelo: str = MODELO_POR_DEFECTO
    dispositivo: str = "mps"
    tope: int = _TOPE
    caracteres: int = CARACTERES_POR_CANDIDATO
    instruccion: str = INSTRUCCION
    _motor: Any = field(default=None, repr=False, compare=False)

    @property
    def motor(self) -> Any:
        if self._motor is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as err:  # pragma: no cover - depende del entorno
                raise RerankerError(
                    "falta `sentence-transformers`. Está pinado en pyproject.toml desde la "
                    "fase 0; ejecuta `uv sync`."
                ) from err
            motor = CrossEncoder(self.modelo, device=self.dispositivo)
            # La instrucción del dominio, en vez de la genérica de búsqueda web que trae la
            # librería. Se pone aquí y no en cada `predict` para que no haya dos caminos por
            # los que llamar al modelo con instrucciones distintas.
            if getattr(motor, "prompts", None) and "query" in motor.prompts:
                motor.prompts["query"] = self.instruccion
            self._motor = motor
        return self._motor

    def reordenar(self, pregunta: str, candidatos: Sequence[Recuperado]) -> list[Recuperado]:
        cabeza, cola = list(candidatos[: self.tope]), list(candidatos[self.tope :])
        if len(cabeza) < 2:
            return list(candidatos)
        pares = [(pregunta, c.content[: self.caracteres]) for c in cabeza]
        puntos = [float(p) for p in self.motor.predict(pares)]
        return ordenar_por_puntos(cabeza, puntos) + cola


@dataclass(frozen=True, slots=True)
class RecordedReranker:
    """Reproduce puntuaciones grabadas. Determinista, gratis, y nunca inventa una.

    Un doble que improvisa ante una pregunta no grabada pone la suite en verde sobre números
    que nadie ha producido, y el primer sitio donde se nota es un recall que no se explica.
    """

    grabacion: dict[str, list[float]]

    def reordenar(self, pregunta: str, candidatos: Sequence[Recuperado]) -> list[Recuperado]:
        if pregunta not in self.grabacion:
            raise RerankerError(
                f"no hay grabación para {pregunta[:60]!r}. Regrábala en vez de inventarla."
            )
        return ordenar_por_puntos(candidatos, self.grabacion[pregunta])


def reordenador_por_defecto() -> CrossEncoderReranker:
    """El de verdad, configurado desde el entorno. Se lee aquí y en ningún sitio más abajo."""
    return CrossEncoderReranker(
        modelo=os.environ.get("CITEBOUND_RERANKER", MODELO_POR_DEFECTO),
        dispositivo=os.environ.get("CITEBOUND_RERANKER_DEVICE", "mps"),
    )
