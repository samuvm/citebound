"""Reordenador · el generador puesto a ordenar, por `/v1/chat/completions`.

**Por qué el generador y no un cross-encoder.** Q-017, respondida por Samuel el 2026-08-17:
**un solo transporte** para todos los modelos del proyecto. Ollama no tiene endpoint de rerank
—`/api/rerank` y `/v1/rerank` devuelven 404, comprobado contra la 0.32.14— así que un
cross-encoder obligaría a un segundo camino de servir modelos, con sus 2 GB de dependencias y
una descarga más en el arranque en frío.

**Por qué hace falta reordenar, medido y no supuesto.** Sobre los 219 casos del golden set,
el material correcto ya está entre los 30 recuperados en el 95 % de los casos, pero el top-5
se queda en 0,717 contra un umbral de 0,90. No hay que buscar mejor: hay que **ordenar** mejor.

**La instrucción es la que importa.** «Relevante» aquí no es «parecido»: es el artículo que
**tipifica** la conducta, no el que la menciona de pasada. Esa distinción es la tesis del
proyecto entera —el 34 habla de cómputo de carriles y el 35 de separación lateral, y elegir mal
es exactamente el error que el golden set existe para medir— y un modelo instruido puede
recibirla, mientras que una distancia coseno no.

**Nunca pierde ni inventa un candidato.** El modelo devuelve números; si se salta uno, se
añade al final en su orden original, y si escribe uno que no existe, se ignora. Un reordenador
que perdiera documentos bajaría el recall por su cuenta y el diagnóstico apuntaría al índice.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path

from citebound.providers.chat import Generador
from citebound.retrieval.vector import Recuperado

__all__ = [
    "CARACTERES_POR_CANDIDATO",
    "PROMPT_VERSION",
    "CacheJuicios",
    "ReordenadorLLM",
    "clave_de",
    "ordenar_por_numeros",
]

PROMPT_VERSION = 1
"""Sube cuando cambie `_PLANTILLA`. Forma parte de la clave de caché: un juicio emitido con
otro prompt es un juicio sobre otra pregunta, y reutilizarlo sería mentir sobre qué se midió."""

# Cuánto texto de cada artículo se le enseña al modelo. No es una constante caprichosa: con
# 30 candidatos completos el prompt pasa de 5.000 tokens y la llamada deja de caber en el
# presupuesto de 90 s de `make eval-retrieval` (RULES §3.3). La rúbrica y el primer párrafo
# son lo que decide si un artículo tipifica la conducta; el resto son excepciones y remisiones.
CARACTERES_POR_CANDIDATO = 500

_NUMERO = re.compile(r"\d+")

_PLANTILLA = """Pregunta: {pregunta}

Artículos candidatos:
{bloques}

Ordena los números del artículo MÁS relevante al menos relevante.

Relevante significa: el artículo que TIPIFICA la conducta por la que se pregunta, no el que
solo la menciona de pasada ni el que regula algo parecido.

Responde ÚNICAMENTE con los números separados por comas. Sin explicación.
"""


def ordenar_por_numeros(respuesta: str, candidatos: Sequence[Recuperado]) -> list[Recuperado]:
    """`"3, 1, 7"` → los candidatos en ese orden, y detrás los que el modelo no nombró.

    Defensivo a propósito: los números fuera de rango se ignoran y los repetidos cuentan una
    vez. Lo que **nunca** ocurre es perder un candidato — el recall del sistema no puede
    depender de que el modelo se acuerde de listarlos todos.
    """
    elegidos: list[int] = []
    for crudo in _NUMERO.findall(respuesta):
        i = int(crudo) - 1
        if 0 <= i < len(candidatos) and i not in elegidos:
            elegidos.append(i)
    elegidos.extend(i for i in range(len(candidatos)) if i not in elegidos)
    return [candidatos[i] for i in elegidos]


def clave_de(pregunta: str, candidatos: Sequence[Recuperado], modelo: str) -> str:
    """Identifica un juicio por todo lo que lo determina, y por nada más.

    Entran la pregunta, **los candidatos en su orden** —reordenar una lista distinta es otro
    juicio—, el modelo y la versión del prompt. No entra el contenido del artículo: viene del
    corpus congelado y su sha256 ya lo verifica `make corpus-verify`.
    """
    material = json.dumps(
        [pregunta, [str(r.ref) for r in candidatos], modelo, PROMPT_VERSION],
        ensure_ascii=False,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class CacheJuicios:
    """Los juicios del reordenador, versionados en el repo.

    Es el mismo mecanismo que `GOALS.yaml` fija para el juez de la fase 4, y por el mismo
    motivo: una meta que tarda veinte minutos se acaba sacando del gate. Con la caché, la
    primera corrida paga el modelo y las siguientes son deterministas y gratis — que es
    literalmente lo que `G-EVAL-DET` va a exigir.

    Guardar el orden y no la respuesta cruda es deliberado: lo que se reutiliza es la
    **decisión**, y así un cambio en cómo se parsea el texto no invalida la caché entera.
    """

    def __init__(self, ruta: Path) -> None:
        self._ruta = ruta
        self._datos: dict[str, list[str]] = (
            json.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else {}
        )
        self._nuevos = 0

    @property
    def aciertos(self) -> int:
        return len(self._datos) - self._nuevos

    def obtener(self, clave: str) -> list[str] | None:
        return self._datos.get(clave)

    def guardar(self, clave: str, orden: Sequence[str]) -> None:
        self._datos[clave] = list(orden)
        self._nuevos += 1

    def volcar(self) -> None:
        self._ruta.parent.mkdir(parents=True, exist_ok=True)
        self._ruta.write_text(
            json.dumps(self._datos, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )


class ReordenadorLLM:
    """Implementa el puerto `Reordenador` de `pipeline`.

    `tope=30` y no 10, y el motivo está medido: con 10, el 17 % de los casos tenía el artículo
    correcto en los puestos 11-30 y el reordenador **ni los miraba**. El techo con 10 era 0,785
    y con 30 es 0,954. Un tope mal puesto no da un error: da un número mediocre cuyo
    diagnóstico apunta al modelo o al prompt, que es donde no está el problema.
    """

    def __init__(
        self, generador: Generador, *, tope: int = 30, cache: CacheJuicios | None = None
    ) -> None:
        self._generador = generador
        self._tope = tope
        self._cache = cache

    def reordenar(self, pregunta: str, candidatos: Sequence[Recuperado]) -> list[Recuperado]:
        cabeza, cola = list(candidatos[: self._tope]), list(candidatos[self._tope :])
        if len(cabeza) < 2:
            return list(candidatos)

        clave = clave_de(pregunta, cabeza, self._generador.model)
        if self._cache is not None and (guardado := self._cache.obtener(clave)) is not None:
            por_ref = {str(r.ref): r for r in cabeza}
            # Defensivo aunque venga de la caché: si el índice cambió, una ref guardada puede
            # no estar ya entre los candidatos. Se ignora, y los que falten se añaden detrás.
            ordenada = [por_ref[ref] for ref in guardado if ref in por_ref]
            ordenada += [r for r in cabeza if r not in ordenada]
            return ordenada + cola

        bloques = "\n\n".join(
            f"[{i}] {r.ref}\n{r.content[:CARACTERES_POR_CANDIDATO]}"
            for i, r in enumerate(cabeza, start=1)
        )
        respuesta = self._generador.completar(
            _PLANTILLA.format(pregunta=pregunta, bloques=bloques), max_tokens=96
        )
        ordenada = ordenar_por_numeros(respuesta.texto, cabeza)
        if self._cache is not None:
            self._cache.guardar(clave, [str(r.ref) for r in ordenada])
        return ordenada + cola
