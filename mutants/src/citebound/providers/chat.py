"""El adaptador de generación · `/v1/chat/completions`, no `/api/chat`.

**`OpenAICompatProvider`, no `OllamaProvider`** (`docs/STACK.md` §2.1 regla 2). Ollama,
llama.cpp server, vLLM y LM Studio exponen los cuatro `/v1/chat/completions`: un solo
adaptador los cubre y cambiar de runtime es una variable de entorno, no una reescritura.

**El generador es un modelo de razonamiento, y eso hay que apagarlo explícitamente.**
`qwen3.5` emite su cadena de pensamiento en un campo aparte y **se come el presupuesto de
tokens antes de contestar**: medido el 2026-08-17, una pregunta trivial con `max_tokens=200`
devolvía `content` vacío, `finish_reason=length` y 1.168 caracteres de razonamiento.

Con `reasoning_effort="none"` la misma llamada baja de **4,0 s a 0,2 s** y responde bien. No
es una optimización: sin ello `G-TTFT ≤ 1500 ms` es inalcanzable por construcción, porque el
modelo piensa varios segundos antes de emitir el primer token útil. Y es un parámetro del
estándar OpenAI, así que no ata el proyecto a Ollama.

`RULES` §3 pone `providers/` en **TDD prohibido**: escribir un test antes de conocer la forma
real de la respuesta produce un mock que codifica una API imaginada. Aquí se graba primero y
se testea contra la grabación.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

__all__ = [
    "ChatError",
    "Generador",
    "OpenAICompatProvider",
    "RecordedGenerador",
    "Respuesta",
    "generador_por_defecto",
]

_BASE_POR_DEFECTO = "http://localhost:11434/v1"
_MODELO_POR_DEFECTO = "qwen3.5:4b-mlx"


class ChatError(RuntimeError):
    """La respuesta del proveedor no tiene la forma que promete el estándar."""


@dataclass(frozen=True, slots=True)
class Respuesta:
    """Lo que devolvió el modelo, con lo que hace falta para auditarlo.

    `razonamiento` se conserva aunque venga vacío: si un día vuelve a llenarse, es la señal de
    que alguien reactivó el pensamiento y de que el presupuesto de latencia se acaba de ir.
    """

    texto: str
    modelo: str
    razonamiento: str
    tokens_salida: int


class Generador(Protocol):
    """El puerto. `retrieval` y `agent` hablan con esto, nunca con `httpx`."""

    @property
    def model(self) -> str: ...

    def completar(
        self, prompt: str, *, max_tokens: int = 256, temperatura: float = 0.0
    ) -> Respuesta: ...

    def emitir(
        self, prompt: str, *, max_tokens: int = 256, temperatura: float = 0.0
    ) -> Iterator[str]: ...


class OpenAICompatProvider:
    """Un `POST /v1/chat/completions` y la validación de lo que vuelve."""

    def __init__(self, *, base_url: str, model: str, timeout: float = 120.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    def completar(
        self, prompt: str, *, max_tokens: int = 256, temperatura: float = 0.0
    ) -> Respuesta:
        cuerpo: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperatura,
            "max_tokens": max_tokens,
            # Ver el docstring del módulo: sin esto el modelo piensa y no contesta.
            "reasoning_effort": "none",
        }
        respuesta = httpx.post(
            f"{self._base_url}/chat/completions", json=cuerpo, timeout=self._timeout
        )
        respuesta.raise_for_status()
        return _leer(respuesta.json(), esperado=self._model)

    def emitir(
        self, prompt: str, *, max_tokens: int = 256, temperatura: float = 0.0
    ) -> Iterator[str]:
        """Los trozos según llegan. **Es lo que hace que `G-TTFT` mida lo que dice medir.**

        Sin esto el primer `event: token` saldría cuando el modelo hubiera terminado de
        escribir, y el `p95 hasta el primer token` sería en realidad el tiempo de generación
        completa — un número que cumple el nombre de la meta y no su intención.
        """
        import json as _json

        import httpx

        cuerpo = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperatura,
            "max_tokens": max_tokens,
            "reasoning_effort": "none",
            "stream": True,
        }
        try:
            with httpx.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=cuerpo,
                timeout=self._timeout,
            ) as respuesta:
                respuesta.raise_for_status()
                for linea in respuesta.iter_lines():
                    trozo = _trozo_sse(linea, _json)
                    if trozo:
                        yield trozo
        except httpx.HTTPError as err:
            raise ChatError(f"{self._model} en {self._base_url} no respondió: {err}") from err


def _leer(cuerpo: object, *, esperado: str) -> Respuesta:
    """Validar en vez de confiar.

    Un proveedor que devuelve otra forma —o el modelo equivocado— produciría texto plausible
    sobre otra cosa, y nada más abajo podría notarlo.
    """
    if not isinstance(cuerpo, dict) or not cuerpo.get("choices"):
        raise ChatError(f"respuesta sin `choices` de {esperado}: {str(cuerpo)[:160]}")
    eleccion = cuerpo["choices"][0]
    mensaje = eleccion.get("message") or {}
    if eleccion.get("finish_reason") == "length" and not (mensaje.get("content") or "").strip():
        raise ChatError(
            f"{esperado} agotó `max_tokens` sin emitir contenido "
            f"({len(mensaje.get('reasoning') or '')} caracteres de razonamiento). "
            "Comprueba que `reasoning_effort` sigue en 'none'"
        )
    uso = cuerpo.get("usage") or {}
    return Respuesta(
        texto=(mensaje.get("content") or "").strip(),
        modelo=str(cuerpo.get("model") or esperado),
        razonamiento=str(mensaje.get("reasoning") or ""),
        tokens_salida=int(uso.get("completion_tokens") or 0),
    )


class RecordedGenerador:
    """Reproduce una grabación. Determinista, gratis y sin Ollama levantado.

    Es lo que permite testear el grafo de la fase 3 contra respuestas reales en vez de contra
    una API imaginada, que es el motivo por el que `RULES` §3.1 prohíbe el TDD aquí.
    """

    def __init__(self, respuestas: Sequence[Respuesta]) -> None:
        self._respuestas = list(respuestas)
        self._i = 0

    @property
    def model(self) -> str:
        return self._respuestas[0].modelo if self._respuestas else "grabado"

    def completar(
        self, prompt: str, *, max_tokens: int = 256, temperatura: float = 0.0
    ) -> Respuesta:
        if self._i >= len(self._respuestas):
            raise ChatError(
                f"la grabación tiene {len(self._respuestas)} respuestas y se ha pedido una más. "
                "Regrábala en vez de improvisar una."
            )
        self._i += 1
        return self._respuestas[self._i - 1]

    def emitir(
        self, prompt: str, *, max_tokens: int = 256, temperatura: float = 0.0
    ) -> Iterator[str]:
        """Trocea la grabación como llegaría por red. **No imita al tokenizador del modelo** —
        eso dependería del modelo— sino que da una entrada troceada realista al guardia, y lo
        que el guardia garantiza no depende de dónde caigan los cortes."""
        import re as _re

        yield from _re.findall(r"\S+\s*|\s+", self.completar(prompt).texto)


def generador_por_defecto() -> Generador:
    """El de verdad, configurado desde el entorno.

    Se lee aquí y en ningún sitio más abajo: `domain/` no toca `os.environ` (R6), y el sentido
    del puerto es que cambiar de runtime sea una variable y no una edición.
    """
    return OpenAICompatProvider(
        base_url=os.environ.get("OPENAI_BASE_URL", _BASE_POR_DEFECTO),
        model=os.environ.get("CITEBOUND_MODELO", _MODELO_POR_DEFECTO),
    )


def _trozo_sse(linea: str, _json: Any) -> str:
    """El `delta.content` de una línea `data:` del stream, o `""` si no lo trae.

    Se ignora en silencio lo que no es contenido —`[DONE]`, líneas vacías, el primer *chunk*
    con el rol— porque son parte del protocolo y no un error. Lo que sí sería un error es
    reventar aquí y dejar la petición sin respuesta por una línea de control.
    """
    if not linea.startswith("data:"):
        return ""
    carga = linea[5:].strip()
    if not carga or carga == "[DONE]":
        return ""
    try:
        trozos = _json.loads(carga).get("choices") or [{}]
    except ValueError:
        return ""
    return str((trozos[0].get("delta") or {}).get("content") or "")
