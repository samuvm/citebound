"""Puerta estadística: bootstrap **pareado** y corrección por comparaciones múltiples.

Implementa `docs/CONTRACTS/retrieval-metrics.md` §4, que es contrato compartido con
`evalgate-02` e `indexkeeper-04`. Nada de aquí es invención de este repo.

**Pareado, y por qué importa.** Se remuestrean los *casos*, no las ejecuciones: cada
réplica toma `head - base` sobre el mismo subconjunto de casos. La varianza cae mucho
respecto al no pareado, y con `n = 190` esa es la diferencia entre una puerta que detecta
una regresión real y una que no la distingue del ruido.

**La semilla y el número de réplicas no viven aquí.** Viven en `docs/GOALS.yaml`, bloque
`comparacion`, con el comentario «vive aqui, NUNCA en el codigo». Por eso son argumentos
obligatorios sin valor por defecto: un default es una segunda fuente de verdad, y el día
que Samuel cambie el número en `GOALS.yaml` el informe seguiría publicando el viejo sin
que nadie se entere. Hay un test que lee este fichero para comprobar que no está escrito.

**El sentido de la regresión se deriva, no se presume.** El contrato redacta la regla —«el
IC95 queda enteramente bajo cero»— pensando en métricas de mayor-es-mejor. `G-ABST-FP`,
`G-TTFT`, `G-TTVA` y `G-COLD-CACHE` llevan operador `<=`, y ahí empeorar es *subir*. El
sentido sale del `operador` de cada meta en `GOALS.yaml`; `hay_regresion` lo recibe
explícito y no lo adivina.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

__all__ = ["Intervalo", "hay_regresion", "holm", "ic_diferencia_pareada"]


@dataclass(frozen=True, slots=True)
class Intervalo:
    """Un IC de la diferencia pareada `head - base`, con su procedencia.

    Los cuatro últimos campos no son adorno: un intervalo sin `n`, sin número de réplicas
    y sin semilla no lo puede reproducir un tercero, y reproducirlo es el criterio de
    aceptación nº 2 del proyecto.
    """

    punto: float
    inferior: float
    superior: float
    n: int
    n_resamples: int
    semilla: int
    nivel: float

    def contiene(self, valor: float) -> bool:
        """Extremos incluidos: el IC es cerrado."""
        return self.inferior <= valor <= self.superior


def ic_diferencia_pareada(
    base: Sequence[float],
    head: Sequence[float],
    *,
    n_resamples: int,
    semilla: int,
    nivel: float = 0.95,
) -> Intervalo:
    """IC percentil de `media(head) - media(base)` por bootstrap pareado.

    `base` y `head` son los valores **por caso** de la misma métrica en dos ejecuciones,
    en el mismo orden: `base[i]` y `head[i]` son el mismo caso del golden set. Que las
    longitudes coincidan no es una comprobación de cortesía — comparar 190 casos contra
    187 produce un número perfectamente plausible sobre dos conjuntos distintos, y eso
    no se detecta mirando el resultado.

    `nivel` sí lleva defecto porque el contrato dice IC95 en todas partes; la semilla y
    las réplicas no, porque son configuración de `GOALS.yaml`.
    """
    if len(base) != len(head):
        raise ValueError(
            f"el bootstrap es pareado y exige los mismos casos: "
            f"len(base)={len(base)} != len(head)={len(head)}"
        )
    if not base:
        raise ValueError("no se puede remuestrear un conjunto vacío: 0 casos")
    if n_resamples < 1:
        raise ValueError(f"n_resamples debe ser >= 1, recibido {n_resamples}")
    if not 0.0 < nivel < 1.0:
        raise ValueError(f"nivel debe estar en el intervalo abierto (0, 1), recibido {nivel}")

    diferencias = np.asarray(head, dtype=np.float64) - np.asarray(base, dtype=np.float64)
    n = diferencias.size

    # Remuestrear las DIFERENCIAS es exactamente remuestrear los casos: para cada réplica
    # se eligen n casos con reemplazo y se promedia `head[i] - base[i]` sobre ellos. Hacerlo
    # sobre las dos muestras por separado rompería el emparejamiento y es el error clásico.
    generador = np.random.default_rng(semilla)
    indices = generador.integers(0, n, size=(n_resamples, n))
    replicas = diferencias[indices].mean(axis=1)

    cola = (1.0 - nivel) / 2.0
    inferior, superior = np.quantile(replicas, [cola, 1.0 - cola])

    return Intervalo(
        punto=float(diferencias.mean()),
        inferior=float(inferior),
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def hay_regresion(ic: Intervalo, *, mayor_es_mejor: bool) -> bool:
    """¿El intervalo queda **enteramente** en el lado malo del cero?

    Cruzar el cero es «no se puede afirmar», y ahí la puerta no bloquea: bloquear por
    ruido cuesta una tarde y erosiona la confianza hasta que alguien desactiva la puerta,
    que es el riesgo nº 1 declarado del proyecto 02.
    """
    return ic.superior < 0.0 if mayor_es_mejor else ic.inferior > 0.0


def holm(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
    """Holm-Bonferroni. Devuelve, por métrica, si se rechaza su hipótesis nula.

    Obligatorio cuando se vigilan más de tres métricas bloqueantes a la vez. Holm controla
    la tasa de error **por familia** —la probabilidad de bloquear al menos una vez sin
    causa—, que es justo lo que arruina una puerta. Es además uniformemente más potente
    que Bonferroni sin pedir supuestos adicionales, así que no hay motivo para preferirlo.

    El paso que se olvida es el **descenso escalonado**: se ordena de menor a mayor y, en
    cuanto una comparación falla, todas las siguientes se rechazan también, aunque su
    p-valor pasara su umbral individual. Comparar cada una por su cuenta no es Holm.
    """
    if not 0.0 < alfa < 1.0:
        raise ValueError(f"alfa debe estar en el intervalo abierto (0, 1), recibido {alfa}")
    for clave, p in pvalores.items():
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"p-valor fuera de [0, 1] en {clave!r}: {p}")

    m = len(pvalores)
    veredicto: dict[str, bool] = {}
    cortado = False
    for posicion, (clave, p) in enumerate(sorted(pvalores.items(), key=lambda par: par[1])):
        if cortado or p > alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto
