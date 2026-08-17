"""`make golden-validate` · la salida de la fase 1 y el comando de `G-GOLDEN-VALID`.

Comprueba lo que la `nota` de esa meta enumera y las **tres reglas duras** del contrato
`docs/CONTRACTS/retrieval-metrics.md` §3. Nada de lo que hay aquí es criterio propio.

**Se escribe antes de generar la cola de candidatos, no después.** Sin él no hay forma de
saber si lo que se le pone delante a Samuel cumple el suelo estadístico, y descubrir en su
hora 12 que una materia se quedó en 18 casos es tirar horas que no se recuperan.

**Los umbrales no viven aquí.** Viven en `docs/GOALS.yaml`, en los `adicionales` de
`G-GOLDEN-VALID`, y se leen de ahí. Un suelo escrito en este fichero sería una segunda
fuente de verdad, y el día que Samuel lo subiera este script seguiría validando contra el
viejo sin que nadie se entere — que es exactamente el fallo que ya se ha comido este
proyecto con la lista de mypy, con la de mutmut y con la semilla del bootstrap. Hay un test
que lee este fuente para comprobar que las cifras no están escritas, y por eso tampoco
aparecen en los comentarios: un test que se puede romper escribiendo prosa no distingue
entre prosa y umbral, y esa rigidez aquí es la que lo hace útil.

**Nada se salta en silencio.** Un caso sin vector no se omite: se reporta. Un comprobador
que omite callando es uno que un día no comprueba nada y nadie lo nota.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from citebound.domain.legalref import MatchLevel, format_ref, matches, parse
from citebound.evals.schema import CasoGolden, Tipo
from citebound.providers.embeddings import embedder_por_defecto

__all__ = ["Umbrales", "cargar", "informe", "main", "umbrales_de_goals", "validar"]

RAIZ = Path(__file__).resolve().parents[1]
# La versión más reciente, no una fija: el golden set es append-only por versión (R12) y
# `v2` existe desde ADR-021. Clavar `v1` aquí validaría un conjunto que ya no es el que se mide.
GOLDEN = max((RAIZ / "evals" / "golden").glob("v*.jsonl"), default=RAIZ / "evals/golden/v1.jsonl")
INDICE = RAIZ / "corpus" / "index" / "refs.json"
DESTINO = RAIZ / "evals" / "golden" / "VALIDATION.json"
GOALS = RAIZ / "docs" / "GOALS.yaml"
META = "G-GOLDEN-VALID"

# Regla dura nº 1 del contrato §3, en fracción. NO es lo mismo que el suelo absoluto de
# `GOALS.yaml`, y por eso se comprueban las dos: en cuanto el conjunto crece, el número
# mínimo de negativos se sigue cumpliendo mientras su proporción cae, y ahí `G-ABST-FP`
# pasaría a calcularse sobre una muestra que ya no representa nada.
FRACCION_NEGATIVOS_CONTRATO = 0.15

# `docs/GOALS.yaml` `G-GOLDEN-VALID` habla de «coseno < 0,95 entre pares» en su `nota`, que
# es prosa y no un umbral estructurado, así que no lo puede leer un script. Vive aquí con su
# procedencia escrita; si algún día pasa a `adicionales`, se lee de allí como los demás.
COSENO_DUPLICADO_CONTRATO = 0.95


@dataclass(frozen=True, slots=True)
class Umbrales:
    """El suelo estadístico. Sale de `GOALS.yaml`, nunca de aquí."""

    positivos_min: int
    negativos_min: int
    materias_min: int
    casos_por_materia: int
    fraccion_negativos_min: float
    coseno_duplicado: float


def umbrales_de_goals(ruta: Path) -> Umbrales:
    """Lee los `adicionales` de `G-GOLDEN-VALID`, por etiqueta y no por posición.

    Por posición sería frágil de la peor manera: reordenar la lista en `GOALS.yaml` no
    rompería nada visible, solo cambiaría en silencio qué umbral se aplica a qué recuento.
    """
    metas = yaml.safe_load(ruta.read_text(encoding="utf-8"))["metas"]
    meta = next(m for m in metas if m["id"] == META)
    por_etiqueta = {a["etiqueta"]: a["valor"] for a in meta["umbral"]["adicionales"]}
    etiqueta_materias = next(e for e in por_etiqueta if e.startswith("materias_"))
    cuantos = re.search(r"\d+", etiqueta_materias)
    if cuantos is None:
        raise ValueError(
            f"la etiqueta {etiqueta_materias!r} de {META} no lleva el número de casos por "
            "materia, y ese número no está en ningún otro sitio de GOALS.yaml"
        )
    return Umbrales(
        positivos_min=int(por_etiqueta["casos_positivos"]),
        negativos_min=int(por_etiqueta["casos_negativos"]),
        materias_min=int(por_etiqueta[etiqueta_materias]),
        # Ese umbral solo existe DENTRO del nombre de la etiqueta
        # (`materias_con_N_casos_o_mas`): `GOALS.yaml` no tiene campo para él. Se extrae con
        # una expresión regular y no por posición de palabra, porque por posición un
        # renombrado que un humano consideraría cosmético cambiaría el umbral en silencio.
        casos_por_materia=int(cuantos.group()),
        fraccion_negativos_min=FRACCION_NEGATIVOS_CONTRATO,
        coseno_duplicado=COSENO_DUPLICADO_CONTRATO,
    )


def cargar(lineas: Sequence[str]) -> tuple[list[CasoGolden], list[str]]:
    """JSONL → casos, y los fallos con el número de línea o el id, no con un traceback.

    Un `ValidationError` a mitad de fichero corta la validación y esconde los otros 189
    problemas: quien anota quiere la lista entera de una pasada, no ir uno por uno.
    """
    casos: list[CasoGolden] = []
    errores: list[str] = []
    for numero, linea in enumerate(lineas, start=1):
        if not linea.strip():
            continue
        try:
            crudo: Any = json.loads(linea)
        except json.JSONDecodeError as err:
            errores.append(f"línea {numero}: no es JSON válido ({err.msg})")
            continue
        identificador = crudo.get("id", f"línea {numero}") if isinstance(crudo, dict) else numero
        try:
            casos.append(CasoGolden.model_validate(crudo))
        except ValidationError as err:
            primero = err.errors()[0]
            errores.append(f"{identificador}: {primero['msg']}")
    return casos, errores


def validar(
    lineas: Sequence[str],
    *,
    refs_indice: frozenset[str],
    umbrales: Umbrales,
    vectores: Mapping[str, Sequence[float]],
) -> list[str]:
    """Todos los errores del conjunto, no el primero."""
    casos, errores = cargar(lineas)
    errores += _ids_unicos(casos)
    errores += _refs_existen(casos, refs_indice)
    errores += _suelo_estadistico(casos, umbrales)
    errores += _sin_duplicados(casos, vectores, umbrales.coseno_duplicado)
    return errores


def _ids_unicos(casos: Sequence[CasoGolden]) -> list[str]:
    """El id es la clave con la que `scoring` empareja casos y predicciones. Duplicarlo da
    un número perfectamente plausible sobre un conjunto que no es el golden set."""
    vistos = Counter(c.id for c in casos)
    return [f"{ident}: id duplicado, aparece {n} veces" for ident, n in vistos.items() if n > 1]


def _refs_existen(casos: Sequence[CasoGolden], indice: frozenset[str]) -> list[str]:
    """`G-HALLUC` aplicado al propio patrón oro: si el golden set cita un artículo que no
    existe, ninguna métrica anclada en él significa nada.

    Se compara **a nivel de artículo**, no por cadena. El índice es `articulo-v1` y nunca
    va a contener apartados; comparar literalmente rechazaría `art34.1` y con ello la
    granularidad de la que dependen `G-CITA-PRECISION` y `G-QUOTE-LIT`.
    """
    articulos = [parse(r) for r in indice]
    errores: list[str] = []
    for caso in casos:
        for ref in caso.refs:
            if not any(matches(ref, a, MatchLevel.ARTICULO) for a in articulos):
                errores.append(f"{caso.id}: {format_ref(ref)} no existe en el índice del corpus")
    return errores


def _suelo_estadistico(casos: Sequence[CasoGolden], umbrales: Umbrales) -> list[str]:
    """Los `adicionales` de `G-GOLDEN-VALID` más la regla dura nº 1 del contrato.

    Se comprueba aunque no haya ni un caso: cero casos produce cero fallos de esquema, y
    sin esto un fichero vacío pondría la meta en verde.
    """
    positivos = [c for c in casos if c.tipo is Tipo.POSITIVO]
    negativos = [c for c in casos if c.tipo is Tipo.NEGATIVO]
    errores: list[str] = []

    if len(positivos) < umbrales.positivos_min:
        errores.append(
            f"suelo: {len(positivos)} casos positivos, hacen falta {umbrales.positivos_min}. "
            "Por debajo de ahí el efecto mínimo detectable sube y la puerta no distingue "
            "una regresión real del ruido (contrato §3)"
        )
    if len(negativos) < umbrales.negativos_min:
        errores.append(
            f"suelo: {len(negativos)} casos negativos, hacen falta {umbrales.negativos_min}. "
            "Sin ellos G-ABST-FP y G-ABST-FN no son calculables"
        )
    if casos:
        fraccion = len(negativos) / len(casos)
        if fraccion < umbrales.fraccion_negativos_min:
            errores.append(
                f"contrato §3 regla 1: los negativos son el {fraccion:.1%} del conjunto y el "
                f"mínimo es el {umbrales.fraccion_negativos_min:.0%}"
            )

    por_materia = Counter(c.materia for c in casos)
    suficientes = [m for m, n in por_materia.items() if n >= umbrales.casos_por_materia]
    if len(suficientes) < umbrales.materias_min:
        errores.append(
            f"estratos: {len(suficientes)} materias con {umbrales.casos_por_materia} casos o "
            f"más, hacen falta {umbrales.materias_min}. Sin estratificar, un recall agregado "
            "esconde que una materia va bien y otra fatal"
        )
    return errores


def _sin_duplicados(
    casos: Sequence[CasoGolden], vectores: Mapping[str, Sequence[float]], umbral: float
) -> list[str]:
    """Preguntas casi iguales inflan el `n` sin aportar información: el bootstrap las cuenta
    como dos casos independientes y estrecha el intervalo de confianza sin motivo."""
    errores: list[str] = []
    presentes = []
    for caso in casos:
        if caso.id not in vectores:
            errores.append(f"{caso.id}: sin vector, no se puede comprobar si está duplicado")
        else:
            presentes.append((caso.id, vectores[caso.id]))

    for i, (id_a, va) in enumerate(presentes):
        for id_b, vb in presentes[i + 1 :]:
            if _coseno(va, vb) >= umbral:
                errores.append(f"{id_a} y {id_b}: preguntas casi idénticas (coseno >= {umbral})")
    return errores


def _coseno(a: Sequence[float], b: Sequence[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=True)) / (na * nb)


def informe(
    *, errores: Sequence[str], casos: Sequence[CasoGolden], sha256: str
) -> dict[str, object]:
    """El artefacto que lee el gate.

    `errores` es un **entero**, no la lista: `GOALS.yaml` apunta a `VALIDATION.json ::
    errores` con umbral `== 0` y unidad `count`, y `[] == 0` es falso — la meta no daría
    verde jamás. El detalle viaja aparte, que es lo que de verdad hace falta para
    arreglarlo.
    """
    por_materia = Counter(c.materia for c in casos)
    return {
        "errores": len(errores),
        "detalle": list(errores),
        "sha256": sha256,
        "n": len(casos),
        "positivos": sum(1 for c in casos if c.tipo is Tipo.POSITIVO),
        "negativos": sum(1 for c in casos if c.tipo is Tipo.NEGATIVO),
        "por_materia": dict(sorted(por_materia.items())),
    }


def main() -> int:
    if not GOLDEN.is_file():
        print(f"no existe {GOLDEN.relative_to(RAIZ)}: la fase 1 no ha llegado a `1d` todavía")
        return 1

    bruto = GOLDEN.read_bytes()
    lineas = bruto.decode("utf-8").splitlines()
    indice = frozenset(json.loads(INDICE.read_text(encoding="utf-8"))["refs"])
    umbrales = umbrales_de_goals(GOALS)

    casos, _ = cargar(lineas)
    embedder = embedder_por_defecto()
    vectores = dict(
        zip([c.id for c in casos], embedder.embed([c.pregunta for c in casos]), strict=True)
    )

    errores = validar(lineas, refs_indice=indice, umbrales=umbrales, vectores=vectores)
    resultado = informe(errores=errores, casos=casos, sha256=hashlib.sha256(bruto).hexdigest())

    DESTINO.write_text(
        json.dumps(resultado, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for fallo in errores:
        print(f"  {fallo}")
    print(
        f"G-GOLDEN-VALID · {resultado['errores']} errores · {resultado['n']} casos "
        f"({resultado['positivos']} positivos, {resultado['negativos']} negativos)"
    )
    return 0 if not errores else 1


if __name__ == "__main__":
    sys.exit(main())
