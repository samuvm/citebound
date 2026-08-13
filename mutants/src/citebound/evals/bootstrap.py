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


from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated, MutantDict


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
mutants_x_ic_diferencia_pareada__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_ic_diferencia_pareada__mutmut)
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


def x_ic_diferencia_pareada__mutmut_orig(
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


def x_ic_diferencia_pareada__mutmut_1(
    base: Sequence[float],
    head: Sequence[float],
    *,
    n_resamples: int,
    semilla: int,
    nivel: float = 1.95,
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


def x_ic_diferencia_pareada__mutmut_2(
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
    if len(base) == len(head):
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


def x_ic_diferencia_pareada__mutmut_3(
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
            None
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


def x_ic_diferencia_pareada__mutmut_4(
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
    if base:
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


def x_ic_diferencia_pareada__mutmut_5(
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
        raise ValueError(None)
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


def x_ic_diferencia_pareada__mutmut_6(
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
        raise ValueError("XXno se puede remuestrear un conjunto vacío: 0 casosXX")
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


def x_ic_diferencia_pareada__mutmut_7(
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
        raise ValueError("NO SE PUEDE REMUESTREAR UN CONJUNTO VACÍO: 0 CASOS")
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


def x_ic_diferencia_pareada__mutmut_8(
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
    if n_resamples <= 1:
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


def x_ic_diferencia_pareada__mutmut_9(
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
    if n_resamples < 2:
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


def x_ic_diferencia_pareada__mutmut_10(
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
        raise ValueError(None)
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


def x_ic_diferencia_pareada__mutmut_11(
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
    if 0.0 < nivel < 1.0:
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


def x_ic_diferencia_pareada__mutmut_12(
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
    if not 1.0 < nivel < 1.0:
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


def x_ic_diferencia_pareada__mutmut_13(
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
    if not 0.0 <= nivel < 1.0:
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


def x_ic_diferencia_pareada__mutmut_14(
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
    if not 0.0 < nivel <= 1.0:
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


def x_ic_diferencia_pareada__mutmut_15(
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
    if not 0.0 < nivel < 2.0:
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


def x_ic_diferencia_pareada__mutmut_16(
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
        raise ValueError(None)

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


def x_ic_diferencia_pareada__mutmut_17(
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

    diferencias = None
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


def x_ic_diferencia_pareada__mutmut_18(
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

    diferencias = np.asarray(head, dtype=np.float64) + np.asarray(base, dtype=np.float64)
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


def x_ic_diferencia_pareada__mutmut_19(
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

    diferencias = np.asarray(None, dtype=np.float64) - np.asarray(base, dtype=np.float64)
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


def x_ic_diferencia_pareada__mutmut_20(
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

    diferencias = np.asarray(head, dtype=None) - np.asarray(base, dtype=np.float64)
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


def x_ic_diferencia_pareada__mutmut_21(
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

    diferencias = np.asarray(dtype=np.float64) - np.asarray(base, dtype=np.float64)
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


def x_ic_diferencia_pareada__mutmut_22(
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

    diferencias = np.asarray(head, ) - np.asarray(base, dtype=np.float64)
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


def x_ic_diferencia_pareada__mutmut_23(
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

    diferencias = np.asarray(head, dtype=np.float64) - np.asarray(None, dtype=np.float64)
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


def x_ic_diferencia_pareada__mutmut_24(
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

    diferencias = np.asarray(head, dtype=np.float64) - np.asarray(base, dtype=None)
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


def x_ic_diferencia_pareada__mutmut_25(
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

    diferencias = np.asarray(head, dtype=np.float64) - np.asarray(dtype=np.float64)
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


def x_ic_diferencia_pareada__mutmut_26(
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

    diferencias = np.asarray(head, dtype=np.float64) - np.asarray(base, )
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


def x_ic_diferencia_pareada__mutmut_27(
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
    n = None

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


def x_ic_diferencia_pareada__mutmut_28(
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
    generador = None
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


def x_ic_diferencia_pareada__mutmut_29(
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
    generador = np.random.default_rng(None)
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


def x_ic_diferencia_pareada__mutmut_30(
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
    indices = None
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


def x_ic_diferencia_pareada__mutmut_31(
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
    indices = generador.integers(None, n, size=(n_resamples, n))
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


def x_ic_diferencia_pareada__mutmut_32(
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
    indices = generador.integers(0, None, size=(n_resamples, n))
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


def x_ic_diferencia_pareada__mutmut_33(
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
    indices = generador.integers(0, n, size=None)
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


def x_ic_diferencia_pareada__mutmut_34(
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
    indices = generador.integers(n, size=(n_resamples, n))
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


def x_ic_diferencia_pareada__mutmut_35(
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
    indices = generador.integers(0, size=(n_resamples, n))
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


def x_ic_diferencia_pareada__mutmut_36(
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
    indices = generador.integers(0, n, )
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


def x_ic_diferencia_pareada__mutmut_37(
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
    indices = generador.integers(1, n, size=(n_resamples, n))
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


def x_ic_diferencia_pareada__mutmut_38(
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
    replicas = None

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


def x_ic_diferencia_pareada__mutmut_39(
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
    replicas = diferencias[indices].mean(axis=None)

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


def x_ic_diferencia_pareada__mutmut_40(
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
    replicas = diferencias[indices].mean(axis=2)

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


def x_ic_diferencia_pareada__mutmut_41(
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

    cola = None
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


def x_ic_diferencia_pareada__mutmut_42(
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

    cola = (1.0 - nivel) * 2.0
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


def x_ic_diferencia_pareada__mutmut_43(
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

    cola = (1.0 + nivel) / 2.0
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


def x_ic_diferencia_pareada__mutmut_44(
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

    cola = (2.0 - nivel) / 2.0
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


def x_ic_diferencia_pareada__mutmut_45(
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

    cola = (1.0 - nivel) / 3.0
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


def x_ic_diferencia_pareada__mutmut_46(
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
    inferior, superior = None

    return Intervalo(
        punto=float(diferencias.mean()),
        inferior=float(inferior),
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_47(
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
    inferior, superior = np.quantile(None, [cola, 1.0 - cola])

    return Intervalo(
        punto=float(diferencias.mean()),
        inferior=float(inferior),
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_48(
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
    inferior, superior = np.quantile(replicas, None)

    return Intervalo(
        punto=float(diferencias.mean()),
        inferior=float(inferior),
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_49(
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
    inferior, superior = np.quantile([cola, 1.0 - cola])

    return Intervalo(
        punto=float(diferencias.mean()),
        inferior=float(inferior),
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_50(
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
    inferior, superior = np.quantile(replicas, )

    return Intervalo(
        punto=float(diferencias.mean()),
        inferior=float(inferior),
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_51(
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
    inferior, superior = np.quantile(replicas, [cola, 1.0 + cola])

    return Intervalo(
        punto=float(diferencias.mean()),
        inferior=float(inferior),
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_52(
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
    inferior, superior = np.quantile(replicas, [cola, 2.0 - cola])

    return Intervalo(
        punto=float(diferencias.mean()),
        inferior=float(inferior),
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_53(
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
        punto=None,
        inferior=float(inferior),
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_54(
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
        inferior=None,
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_55(
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
        superior=None,
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_56(
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
        n=None,
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_57(
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
        n_resamples=None,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_58(
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
        semilla=None,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_59(
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
        nivel=None,
    )


def x_ic_diferencia_pareada__mutmut_60(
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
        inferior=float(inferior),
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_61(
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
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_62(
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
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_63(
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
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_64(
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
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_65(
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
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_66(
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
        )


def x_ic_diferencia_pareada__mutmut_67(
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
        punto=float(None),
        inferior=float(inferior),
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_68(
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
        inferior=float(None),
        superior=float(superior),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_69(
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
        superior=float(None),
        n=int(n),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )


def x_ic_diferencia_pareada__mutmut_70(
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
        n=int(None),
        n_resamples=n_resamples,
        semilla=semilla,
        nivel=nivel,
    )

mutants_x_ic_diferencia_pareada__mutmut['_mutmut_orig'] = x_ic_diferencia_pareada__mutmut_orig # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_1'] = x_ic_diferencia_pareada__mutmut_1 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_2'] = x_ic_diferencia_pareada__mutmut_2 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_3'] = x_ic_diferencia_pareada__mutmut_3 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_4'] = x_ic_diferencia_pareada__mutmut_4 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_5'] = x_ic_diferencia_pareada__mutmut_5 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_6'] = x_ic_diferencia_pareada__mutmut_6 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_7'] = x_ic_diferencia_pareada__mutmut_7 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_8'] = x_ic_diferencia_pareada__mutmut_8 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_9'] = x_ic_diferencia_pareada__mutmut_9 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_10'] = x_ic_diferencia_pareada__mutmut_10 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_11'] = x_ic_diferencia_pareada__mutmut_11 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_12'] = x_ic_diferencia_pareada__mutmut_12 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_13'] = x_ic_diferencia_pareada__mutmut_13 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_14'] = x_ic_diferencia_pareada__mutmut_14 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_15'] = x_ic_diferencia_pareada__mutmut_15 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_16'] = x_ic_diferencia_pareada__mutmut_16 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_17'] = x_ic_diferencia_pareada__mutmut_17 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_18'] = x_ic_diferencia_pareada__mutmut_18 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_19'] = x_ic_diferencia_pareada__mutmut_19 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_20'] = x_ic_diferencia_pareada__mutmut_20 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_21'] = x_ic_diferencia_pareada__mutmut_21 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_22'] = x_ic_diferencia_pareada__mutmut_22 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_23'] = x_ic_diferencia_pareada__mutmut_23 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_24'] = x_ic_diferencia_pareada__mutmut_24 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_25'] = x_ic_diferencia_pareada__mutmut_25 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_26'] = x_ic_diferencia_pareada__mutmut_26 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_27'] = x_ic_diferencia_pareada__mutmut_27 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_28'] = x_ic_diferencia_pareada__mutmut_28 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_29'] = x_ic_diferencia_pareada__mutmut_29 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_30'] = x_ic_diferencia_pareada__mutmut_30 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_31'] = x_ic_diferencia_pareada__mutmut_31 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_32'] = x_ic_diferencia_pareada__mutmut_32 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_33'] = x_ic_diferencia_pareada__mutmut_33 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_34'] = x_ic_diferencia_pareada__mutmut_34 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_35'] = x_ic_diferencia_pareada__mutmut_35 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_36'] = x_ic_diferencia_pareada__mutmut_36 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_37'] = x_ic_diferencia_pareada__mutmut_37 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_38'] = x_ic_diferencia_pareada__mutmut_38 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_39'] = x_ic_diferencia_pareada__mutmut_39 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_40'] = x_ic_diferencia_pareada__mutmut_40 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_41'] = x_ic_diferencia_pareada__mutmut_41 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_42'] = x_ic_diferencia_pareada__mutmut_42 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_43'] = x_ic_diferencia_pareada__mutmut_43 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_44'] = x_ic_diferencia_pareada__mutmut_44 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_45'] = x_ic_diferencia_pareada__mutmut_45 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_46'] = x_ic_diferencia_pareada__mutmut_46 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_47'] = x_ic_diferencia_pareada__mutmut_47 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_48'] = x_ic_diferencia_pareada__mutmut_48 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_49'] = x_ic_diferencia_pareada__mutmut_49 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_50'] = x_ic_diferencia_pareada__mutmut_50 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_51'] = x_ic_diferencia_pareada__mutmut_51 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_52'] = x_ic_diferencia_pareada__mutmut_52 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_53'] = x_ic_diferencia_pareada__mutmut_53 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_54'] = x_ic_diferencia_pareada__mutmut_54 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_55'] = x_ic_diferencia_pareada__mutmut_55 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_56'] = x_ic_diferencia_pareada__mutmut_56 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_57'] = x_ic_diferencia_pareada__mutmut_57 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_58'] = x_ic_diferencia_pareada__mutmut_58 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_59'] = x_ic_diferencia_pareada__mutmut_59 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_60'] = x_ic_diferencia_pareada__mutmut_60 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_61'] = x_ic_diferencia_pareada__mutmut_61 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_62'] = x_ic_diferencia_pareada__mutmut_62 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_63'] = x_ic_diferencia_pareada__mutmut_63 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_64'] = x_ic_diferencia_pareada__mutmut_64 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_65'] = x_ic_diferencia_pareada__mutmut_65 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_66'] = x_ic_diferencia_pareada__mutmut_66 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_67'] = x_ic_diferencia_pareada__mutmut_67 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_68'] = x_ic_diferencia_pareada__mutmut_68 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_69'] = x_ic_diferencia_pareada__mutmut_69 # type: ignore # mutmut generated
mutants_x_ic_diferencia_pareada__mutmut['x_ic_diferencia_pareada__mutmut_70'] = x_ic_diferencia_pareada__mutmut_70 # type: ignore # mutmut generated
mutants_x_hay_regresion__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_hay_regresion__mutmut)
def hay_regresion(ic: Intervalo, *, mayor_es_mejor: bool) -> bool:
    """¿El intervalo queda **enteramente** en el lado malo del cero?

    Cruzar el cero es «no se puede afirmar», y ahí la puerta no bloquea: bloquear por
    ruido cuesta una tarde y erosiona la confianza hasta que alguien desactiva la puerta,
    que es el riesgo nº 1 declarado del proyecto 02.
    """
    return ic.superior < 0.0 if mayor_es_mejor else ic.inferior > 0.0


def x_hay_regresion__mutmut_orig(ic: Intervalo, *, mayor_es_mejor: bool) -> bool:
    """¿El intervalo queda **enteramente** en el lado malo del cero?

    Cruzar el cero es «no se puede afirmar», y ahí la puerta no bloquea: bloquear por
    ruido cuesta una tarde y erosiona la confianza hasta que alguien desactiva la puerta,
    que es el riesgo nº 1 declarado del proyecto 02.
    """
    return ic.superior < 0.0 if mayor_es_mejor else ic.inferior > 0.0


def x_hay_regresion__mutmut_1(ic: Intervalo, *, mayor_es_mejor: bool) -> bool:
    """¿El intervalo queda **enteramente** en el lado malo del cero?

    Cruzar el cero es «no se puede afirmar», y ahí la puerta no bloquea: bloquear por
    ruido cuesta una tarde y erosiona la confianza hasta que alguien desactiva la puerta,
    que es el riesgo nº 1 declarado del proyecto 02.
    """
    return ic.superior <= 0.0 if mayor_es_mejor else ic.inferior > 0.0


def x_hay_regresion__mutmut_2(ic: Intervalo, *, mayor_es_mejor: bool) -> bool:
    """¿El intervalo queda **enteramente** en el lado malo del cero?

    Cruzar el cero es «no se puede afirmar», y ahí la puerta no bloquea: bloquear por
    ruido cuesta una tarde y erosiona la confianza hasta que alguien desactiva la puerta,
    que es el riesgo nº 1 declarado del proyecto 02.
    """
    return ic.superior < 1.0 if mayor_es_mejor else ic.inferior > 0.0


def x_hay_regresion__mutmut_3(ic: Intervalo, *, mayor_es_mejor: bool) -> bool:
    """¿El intervalo queda **enteramente** en el lado malo del cero?

    Cruzar el cero es «no se puede afirmar», y ahí la puerta no bloquea: bloquear por
    ruido cuesta una tarde y erosiona la confianza hasta que alguien desactiva la puerta,
    que es el riesgo nº 1 declarado del proyecto 02.
    """
    return ic.superior < 0.0 if mayor_es_mejor else ic.inferior >= 0.0


def x_hay_regresion__mutmut_4(ic: Intervalo, *, mayor_es_mejor: bool) -> bool:
    """¿El intervalo queda **enteramente** en el lado malo del cero?

    Cruzar el cero es «no se puede afirmar», y ahí la puerta no bloquea: bloquear por
    ruido cuesta una tarde y erosiona la confianza hasta que alguien desactiva la puerta,
    que es el riesgo nº 1 declarado del proyecto 02.
    """
    return ic.superior < 0.0 if mayor_es_mejor else ic.inferior > 1.0

mutants_x_hay_regresion__mutmut['_mutmut_orig'] = x_hay_regresion__mutmut_orig # type: ignore # mutmut generated
mutants_x_hay_regresion__mutmut['x_hay_regresion__mutmut_1'] = x_hay_regresion__mutmut_1 # type: ignore # mutmut generated
mutants_x_hay_regresion__mutmut['x_hay_regresion__mutmut_2'] = x_hay_regresion__mutmut_2 # type: ignore # mutmut generated
mutants_x_hay_regresion__mutmut['x_hay_regresion__mutmut_3'] = x_hay_regresion__mutmut_3 # type: ignore # mutmut generated
mutants_x_hay_regresion__mutmut['x_hay_regresion__mutmut_4'] = x_hay_regresion__mutmut_4 # type: ignore # mutmut generated
mutants_x_holm__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_holm__mutmut)
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


def x_holm__mutmut_orig(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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


def x_holm__mutmut_1(pvalores: Mapping[str, float], *, alfa: float = 1.05) -> dict[str, bool]:
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


def x_holm__mutmut_2(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
    """Holm-Bonferroni. Devuelve, por métrica, si se rechaza su hipótesis nula.

    Obligatorio cuando se vigilan más de tres métricas bloqueantes a la vez. Holm controla
    la tasa de error **por familia** —la probabilidad de bloquear al menos una vez sin
    causa—, que es justo lo que arruina una puerta. Es además uniformemente más potente
    que Bonferroni sin pedir supuestos adicionales, así que no hay motivo para preferirlo.

    El paso que se olvida es el **descenso escalonado**: se ordena de menor a mayor y, en
    cuanto una comparación falla, todas las siguientes se rechazan también, aunque su
    p-valor pasara su umbral individual. Comparar cada una por su cuenta no es Holm.
    """
    if 0.0 < alfa < 1.0:
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


def x_holm__mutmut_3(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
    """Holm-Bonferroni. Devuelve, por métrica, si se rechaza su hipótesis nula.

    Obligatorio cuando se vigilan más de tres métricas bloqueantes a la vez. Holm controla
    la tasa de error **por familia** —la probabilidad de bloquear al menos una vez sin
    causa—, que es justo lo que arruina una puerta. Es además uniformemente más potente
    que Bonferroni sin pedir supuestos adicionales, así que no hay motivo para preferirlo.

    El paso que se olvida es el **descenso escalonado**: se ordena de menor a mayor y, en
    cuanto una comparación falla, todas las siguientes se rechazan también, aunque su
    p-valor pasara su umbral individual. Comparar cada una por su cuenta no es Holm.
    """
    if not 1.0 < alfa < 1.0:
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


def x_holm__mutmut_4(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
    """Holm-Bonferroni. Devuelve, por métrica, si se rechaza su hipótesis nula.

    Obligatorio cuando se vigilan más de tres métricas bloqueantes a la vez. Holm controla
    la tasa de error **por familia** —la probabilidad de bloquear al menos una vez sin
    causa—, que es justo lo que arruina una puerta. Es además uniformemente más potente
    que Bonferroni sin pedir supuestos adicionales, así que no hay motivo para preferirlo.

    El paso que se olvida es el **descenso escalonado**: se ordena de menor a mayor y, en
    cuanto una comparación falla, todas las siguientes se rechazan también, aunque su
    p-valor pasara su umbral individual. Comparar cada una por su cuenta no es Holm.
    """
    if not 0.0 <= alfa < 1.0:
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


def x_holm__mutmut_5(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
    """Holm-Bonferroni. Devuelve, por métrica, si se rechaza su hipótesis nula.

    Obligatorio cuando se vigilan más de tres métricas bloqueantes a la vez. Holm controla
    la tasa de error **por familia** —la probabilidad de bloquear al menos una vez sin
    causa—, que es justo lo que arruina una puerta. Es además uniformemente más potente
    que Bonferroni sin pedir supuestos adicionales, así que no hay motivo para preferirlo.

    El paso que se olvida es el **descenso escalonado**: se ordena de menor a mayor y, en
    cuanto una comparación falla, todas las siguientes se rechazan también, aunque su
    p-valor pasara su umbral individual. Comparar cada una por su cuenta no es Holm.
    """
    if not 0.0 < alfa <= 1.0:
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


def x_holm__mutmut_6(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
    """Holm-Bonferroni. Devuelve, por métrica, si se rechaza su hipótesis nula.

    Obligatorio cuando se vigilan más de tres métricas bloqueantes a la vez. Holm controla
    la tasa de error **por familia** —la probabilidad de bloquear al menos una vez sin
    causa—, que es justo lo que arruina una puerta. Es además uniformemente más potente
    que Bonferroni sin pedir supuestos adicionales, así que no hay motivo para preferirlo.

    El paso que se olvida es el **descenso escalonado**: se ordena de menor a mayor y, en
    cuanto una comparación falla, todas las siguientes se rechazan también, aunque su
    p-valor pasara su umbral individual. Comparar cada una por su cuenta no es Holm.
    """
    if not 0.0 < alfa < 2.0:
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


def x_holm__mutmut_7(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
        raise ValueError(None)
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


def x_holm__mutmut_8(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
        if 0.0 <= p <= 1.0:
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


def x_holm__mutmut_9(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
        if not 1.0 <= p <= 1.0:
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


def x_holm__mutmut_10(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
        if not 0.0 < p <= 1.0:
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


def x_holm__mutmut_11(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
        if not 0.0 <= p < 1.0:
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


def x_holm__mutmut_12(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
        if not 0.0 <= p <= 2.0:
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


def x_holm__mutmut_13(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
            raise ValueError(None)

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


def x_holm__mutmut_14(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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

    m = None
    veredicto: dict[str, bool] = {}
    cortado = False
    for posicion, (clave, p) in enumerate(sorted(pvalores.items(), key=lambda par: par[1])):
        if cortado or p > alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_15(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
    veredicto: dict[str, bool] = None
    cortado = False
    for posicion, (clave, p) in enumerate(sorted(pvalores.items(), key=lambda par: par[1])):
        if cortado or p > alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_16(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
    cortado = None
    for posicion, (clave, p) in enumerate(sorted(pvalores.items(), key=lambda par: par[1])):
        if cortado or p > alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_17(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
    cortado = True
    for posicion, (clave, p) in enumerate(sorted(pvalores.items(), key=lambda par: par[1])):
        if cortado or p > alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_18(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
    for posicion, (clave, p) in enumerate(None):
        if cortado or p > alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_19(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
    for posicion, (clave, p) in enumerate(sorted(None, key=lambda par: par[1])):
        if cortado or p > alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_20(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
    for posicion, (clave, p) in enumerate(sorted(pvalores.items(), key=None)):
        if cortado or p > alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_21(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
    for posicion, (clave, p) in enumerate(sorted(key=lambda par: par[1])):
        if cortado or p > alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_22(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
    for posicion, (clave, p) in enumerate(sorted(pvalores.items(), )):
        if cortado or p > alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_23(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
    for posicion, (clave, p) in enumerate(sorted(pvalores.items(), key=lambda par: None)):
        if cortado or p > alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_24(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
    for posicion, (clave, p) in enumerate(sorted(pvalores.items(), key=lambda par: par[2])):
        if cortado or p > alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_25(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
        if cortado and p > alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_26(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
        if cortado or p >= alfa / (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_27(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
        if cortado or p > alfa * (m - posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_28(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
        if cortado or p > alfa / (m + posicion):
            cortado = True
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_29(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
            cortado = None
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_30(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
            cortado = False
            veredicto[clave] = False
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_31(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
            veredicto[clave] = None
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_32(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
            veredicto[clave] = True
        else:
            veredicto[clave] = True
    return veredicto


def x_holm__mutmut_33(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
            veredicto[clave] = None
    return veredicto


def x_holm__mutmut_34(pvalores: Mapping[str, float], *, alfa: float = 0.05) -> dict[str, bool]:
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
            veredicto[clave] = False
    return veredicto

mutants_x_holm__mutmut['_mutmut_orig'] = x_holm__mutmut_orig # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_1'] = x_holm__mutmut_1 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_2'] = x_holm__mutmut_2 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_3'] = x_holm__mutmut_3 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_4'] = x_holm__mutmut_4 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_5'] = x_holm__mutmut_5 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_6'] = x_holm__mutmut_6 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_7'] = x_holm__mutmut_7 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_8'] = x_holm__mutmut_8 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_9'] = x_holm__mutmut_9 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_10'] = x_holm__mutmut_10 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_11'] = x_holm__mutmut_11 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_12'] = x_holm__mutmut_12 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_13'] = x_holm__mutmut_13 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_14'] = x_holm__mutmut_14 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_15'] = x_holm__mutmut_15 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_16'] = x_holm__mutmut_16 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_17'] = x_holm__mutmut_17 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_18'] = x_holm__mutmut_18 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_19'] = x_holm__mutmut_19 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_20'] = x_holm__mutmut_20 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_21'] = x_holm__mutmut_21 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_22'] = x_holm__mutmut_22 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_23'] = x_holm__mutmut_23 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_24'] = x_holm__mutmut_24 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_25'] = x_holm__mutmut_25 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_26'] = x_holm__mutmut_26 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_27'] = x_holm__mutmut_27 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_28'] = x_holm__mutmut_28 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_29'] = x_holm__mutmut_29 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_30'] = x_holm__mutmut_30 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_31'] = x_holm__mutmut_31 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_32'] = x_holm__mutmut_32 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_33'] = x_holm__mutmut_33 # type: ignore # mutmut generated
mutants_x_holm__mutmut['x_holm__mutmut_34'] = x_holm__mutmut_34 # type: ignore # mutmut generated
