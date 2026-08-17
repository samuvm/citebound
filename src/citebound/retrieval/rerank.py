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

**Nunca pierde ni inventa un candidato.** El modelo devuelve etiquetas; si se salta una, su
candidato se añade al final en su orden original, y si escribe una que no existe, se ignora. Un
reordenador que perdiera documentos bajaría el recall por su cuenta y el diagnóstico apuntaría
al índice, que es donde no estaría el problema.

**Al modelo no se le enseña la referencia, solo el texto.** El texto ya abre con «Artículo 108.
Obligación de advertir las maniobras», así que la ref no añadía nada — y sí añadía un segundo
número junto al del candidato, que es lo que hizo que en `gs-0199` contestara `108,75,24`.
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
    "PEDIDOS",
    "PROMPT_VERSION",
    "CacheJuicios",
    "ReordenadorLLM",
    "clave_de",
    "etiquetas",
    "ordenar_por_etiquetas",
]

PROMPT_VERSION = 2
"""Sube cuando cambie `_PLANTILLA`. Forma parte de la clave de caché: un juicio emitido con
otro prompt es un juicio sobre otra pregunta, y reutilizarlo sería mentir sobre qué se midió.

`2` (2026-08-17): etiquetas de dos letras en vez de números, y se piden exactamente `PEDIDOS`
en vez de una ordenación completa. Los dos cambios salen de leer lo que el modelo contestaba,
no de tunear — el detalle está abajo.
"""

# Cuánto texto de cada artículo se le enseña al modelo. No es una constante caprichosa: con
# 30 candidatos completos el prompt pasa de 5.000 tokens y la llamada deja de caber en el
# presupuesto de 90 s de `make eval-retrieval` (RULES §3.3). La rúbrica y el primer párrafo
# son lo que decide si un artículo tipifica la conducta; el resto son excepciones y remisiones.
CARACTERES_POR_CANDIDATO = 500

PEDIDOS = 5
"""Cuántos se le piden. **Son los mismos 5 de la cita cerrada**: es la decisión que hace falta.

Pedir la ordenación entera parecía más general y era peor. El modelo nombraba **2, 3 o 4** de
los 30 y paraba —medido el 2026-08-17 sobre los fallos— así que el top-5 acababa siendo una
mezcla: los pocos que el modelo eligió, y detrás los primeros de la fusión que él no había
mirado. Esa mezcla **expulsa** aciertos que la fusión ya tenía dentro: `gs-0002` estaba en el
puesto 4 y salió en el 6; `gs-0239` estaba en el 3 y salió en el 7.

Pidiendo cinco, el top-5 es exactamente lo que el modelo decidió. Si se equivoca, se equivoca
él y se mide; antes se perdía por una discrepancia entre lo que el prompt pedía y lo que el
código daba por hecho.
"""

_ETIQUETA = re.compile(r"\b[A-Z]{2}\b")

_ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def etiquetas(cuantas: int) -> list[str]:
    """`AA, AB, … AZ, BA, …` — tantas como candidatos haya.

    **Dos letras y no números, y no es cosmética.** El texto de cada candidato empieza por
    «Artículo 108.», así que un candidato numerado `[3]` le ofrece al modelo dos números
    distintos y ninguna forma de saber cuál se le pide. Contestó lo que tenía que contestar:
    en `gs-0199` respondió `108,75,24` — el número del **artículo**, no el del candidato. El
    parseo descartó 108 y 75 por fuera de rango y se quedó con un 24 que no significaba nada.

    Instruir «usa el número entre corchetes» habría sido pedirle que se porte bien. Con letras
    la confusión es **inexpresable**, que es la misma idea que la cita cerrada.
    """
    if cuantas > len(_ALFABETO) ** 2:
        raise ValueError(f"{cuantas} candidatos no caben en etiquetas de dos letras")
    return [_ALFABETO[i // 26] + _ALFABETO[i % 26] for i in range(cuantas)]


_PLANTILLA = """Pregunta: {pregunta}

Artículos candidatos:
{bloques}

De los candidatos anteriores, elige los {pedidos} MÁS relevantes, del más al menos relevante.

Relevante significa: el artículo que TIPIFICA la conducta por la que se pregunta, no el que
solo la menciona de pasada ni el que regula algo parecido.

Responde ÚNICAMENTE con {pedidos} etiquetas separadas por comas, así: {ejemplo}
Nada más: ni el número del artículo, ni explicación.
"""


def ordenar_por_etiquetas(respuesta: str, candidatos: Sequence[Recuperado]) -> list[Recuperado]:
    """`"AC, AA, AG"` → los candidatos en ese orden, y detrás los que el modelo no nombró.

    Defensivo a propósito: las etiquetas fuera de rango se ignoran y las repetidas cuentan una
    vez. Lo que **nunca** ocurre es perder un candidato — el recall del sistema no puede
    depender de que el modelo se acuerde de listarlos todos, y `recall@30` se mide sobre esta
    misma lista.
    """
    indice = {e: i for i, e in enumerate(etiquetas(len(candidatos)))}
    elegidos: list[int] = []
    for cruda in _ETIQUETA.findall(respuesta):
        i = indice.get(cruda)
        if i is not None and i not in elegidos:
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

        marcas = etiquetas(len(cabeza))
        bloques = "\n\n".join(
            f"[{e}] {r.content[:CARACTERES_POR_CANDIDATO]}"
            for e, r in zip(marcas, cabeza, strict=True)
        )
        respuesta = self._generador.completar(
            _PLANTILLA.format(
                pregunta=pregunta,
                bloques=bloques,
                pedidos=PEDIDOS,
                ejemplo=", ".join(marcas[:PEDIDOS]),
            ),
            max_tokens=48,
        )
        ordenada = ordenar_por_etiquetas(respuesta.texto, cabeza)
        if self._cache is not None:
            self._cache.guardar(clave, [str(r.ref) for r in ordenada])
        return ordenada + cola
