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
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from citebound.retrieval.vector import Recuperado

__all__ = [
    "CARACTERES_POR_CANDIDATO",
    "DISPOSITIVO_POR_DEFECTO",
    "INSTRUCCION",
    "MODELO_POR_DEFECTO",
    "CrossEncoderReranker",
    "RecordedReranker",
    "RerankerError",
    "ordenar_por_puntos",
    "puntuador_por_defecto",
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

DISPOSITIVO_POR_DEFECTO = os.environ.get("CITEBOUND_DISPOSITIVO_PUNTUADOR", "cpu")
"""Dónde corre el cross-encoder. **El valor correcto depende de dónde viva Ollama**, y esa es
toda la lección:

| Ollama | dispositivo | `G-TTFT` p95 | `make eval-retrieval` |
|---|---|---:|---:|
| en esta máquina | `mps` | 3.140 ms | — |
| en esta máquina | **`cpu`** | **2.039 ms** | 299 s |
| en otra máquina | **`mps`** | **1.014 ms** | **154 s** |
| en otra máquina | `cpu` | — | 299 s |

Compartiendo máquina, MPS puntúa más rápido y **hace que responder sea mucho más lento**: la
contienda por la GPU cuesta más de lo que ahorra. Sin compartir, MPS gana en todo por el doble.

El valor por defecto sigue siendo `cpu` porque `GOALS.yaml :: hardware_referencia` declara **una
sola máquina**. Cambiarlo antes que esa declaración sería publicar números de una configuración
que el proyecto no dice ejecutar — la cicatriz de Q-019, otra vez."""
"""**CPU y no MPS, y es contraintuitivo hasta que se mide.**

El cross-encoder corre en proceso con PyTorch; Ollama sirve el generador en la misma GPU. Cuando
los dos se pelean por ella, puntuar es más rápido y **responder es mucho más lento**:

| dispositivo | puntuar 5 | primer token después | total |
|---|---:|---:|---:|
| `mps` | 161 ms | 1.598 ms | 1.759 ms |
| **`cpu`** | 313 ms | **255 ms** | **569 ms** |

En MPS la contienda cuesta ~1,3 s de `G-TTFT`. Medirlo por separado no lo enseña: aislado, el
puntuador en MPS parece el doble de rápido. Es exactamente el coste escondido del «segundo
camino de servir modelos» que Q-017 temía, ahora medido desde el otro lado.

`mps` y `cuda` siguen disponibles por `CITEBOUND_RERANKER_DEVICE`: en una máquina con GPU
dedicada al reranker la aritmética es otra."""

HILOS_POR_DEFECTO = int(os.environ.get("CITEBOUND_HILOS_PUNTUADOR", "4"))
"""Cuántos hilos de CPU se le dejan a PyTorch. `0` = los que quiera (14 en esta máquina).

**Cuatro, y es una medida.** PyTorch coge por defecto los 14 y deja a Ollama sin CPU para su
lado del trabajo. Tres pares de `make bench` alternados, misma dirección las tres veces:

| `G-TTFT` p95 | 14 hilos | 4 hilos |
|---|---:|---:|
| par 1 | 5.835 ms | 5.634 ms |
| par 2 | 2.225 ms | 2.039 ms |
| par 3 | 2.541 ms | 2.095 ms |

Con 2 hilos se hunde a 4.166: puntuar pasa a ser el cuello. Y el salto entre pares —5.8 s
contra 2.2 s con la MISMA configuración— es estado de la máquina, no del código: el par 1 corrió
detrás de un experimento que dejó generaciones abandonadas. **Por eso se comparan pares
alternados y no corridas sueltas.**"""

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
    dispositivo: str = DISPOSITIVO_POR_DEFECTO
    tope: int = _TOPE
    caracteres: int = CARACTERES_POR_CANDIDATO
    instruccion: str = INSTRUCCION
    hilos: int = HILOS_POR_DEFECTO
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
            if self.hilos:
                import torch

                torch.set_num_threads(self.hilos)
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
        dispositivo=os.environ.get("CITEBOUND_RERANKER_DEVICE", DISPOSITIVO_POR_DEFECTO),
    )


def puntuador_por_defecto() -> Callable[[str, Sequence[Any]], list[float]]:
    """Puntúa las fuentes **que se le enseñan al modelo**, no las treinta recuperadas.

    Es la diferencia entre caber en `G-TTFT` y no caber: puntuar cinco cuesta **67 ms** y
    reordenar treinta **348**, contra 116 ms de margen. Y para decidir si el corpus responde
    basta con la mejor de las cinco, que son las únicas que el modelo puede citar.
    """
    reordenador = reordenador_por_defecto()

    def puntuar(pregunta: str, fuentes: Sequence[Any]) -> list[float]:
        if not fuentes:
            return []
        pares = [(pregunta, f.texto[: reordenador.caracteres]) for f in fuentes]
        return [float(p) for p in reordenador.motor.predict(pares)]

    return puntuar
