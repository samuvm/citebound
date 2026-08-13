"""Quién entra en la cola de revisión de Samuel.

Este script **no propone referencias**: decide qué preguntas ve. Es la última pieza barata
antes de gastar sus 10-16 horas, y cada defecto aquí se paga en tiempo suyo que no se
recupera — una cuota corta hace que la fase 1 no cierre *después* de anotar, y dos preguntas
casi iguales le hacen validar dos veces para tirar una.

**De dónde salen los números.** El suelo es el de `G-GOLDEN-VALID` en `docs/GOALS.yaml`, y el
factor de sobremuestreo el que ratifica Q-004: se genera a **1,6 veces** el objetivo
justamente para permitir descartes. Dar exactamente el suelo con opción de descartar es
aritméticamente inviable — un solo descarte deja el conjunto por debajo y la fase no cierra.
Ninguna de esas cifras está escrita aquí, y hay un test que lee este fuente para comprobarlo.

**Qué queda fuera, dicho y no callado.** Las preguntas que necesitan ver la foto (7,4 % del
banco; las imágenes no se redistribuyen, Q-003) y las de temas a caballo entre el Reglamento
y otras normas, que exigen clasificación caso a caso y quedan para una `v2`.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from scripts.golden_validate import GOALS, Umbrales, umbrales_de_goals

__all__ = [
    "BANCO",
    "Candidato",
    "deduplicar",
    "leer",
    "marcar_a_ciegas",
    "muestrear",
    "objetivo",
    "plan",
    "por_tipo",
    "temas_objetivo",
    "umbrales",
    "usables",
]

RAIZ = Path(__file__).resolve().parents[1]
BANCO = RAIZ / "evals" / "golden" / "source" / "preguntas-dgt-202606.csv"

# Q-004: «genera candidatos a 1,6 veces el objetivo para permitir rechazos».
FACTOR_Q004 = 1.6

# Materias por encima del mínimo de `G-GOLDEN-VALID`. El mínimo se exige sobre el golden set
# **final**, o sea después de los descartes de Samuel: muestrear las justas significa que un
# solo tema flojo tumbe la meta al final del todo.
MATERIAS_DE_MARGEN = 2

# La cobertura del banco, ya derivada en su README: qué preguntas responde el Reglamento y
# cuáles no. `mixto` no cae en ninguno de los dos montones a propósito.
COBERTURA = {"positivo": "rgc", "negativo": "fuera"}


@dataclass(frozen=True, slots=True)
class Candidato:
    """Una pregunta elegida para la cola, todavía **sin** referencia legal.

    Esa referencia es justo lo que el banco no trae y lo único que Samuel no puede delegar.
    """

    id: str
    source_id: str
    pregunta: str
    opciones: tuple[str, ...]
    respuesta_correcta: str
    tema: str
    subtema: str
    pct_fallo: float
    tipo: str
    a_ciegas: bool = False


def leer(ruta: Path) -> list[dict[str, str]]:
    """El volcado podado, que va con `;` porque los enunciados llevan comas."""
    with ruta.open(newline="", encoding="utf-8") as fichero:
        return list(csv.DictReader(fichero, delimiter=";"))


def usables(filas: Sequence[Mapping[str, str]]) -> list[Mapping[str, str]]:
    """Fuera las que no se pueden responder sin ver la foto.

    Son el 7,4 % del banco y se concentran en señales. Meter una en el golden set es meter
    un caso que el sistema **nunca** podrá acertar, y que bajaría todas las métricas por una
    razón que no tiene nada que ver con el motor.
    """
    return [f for f in filas if f["depende_imagen"] == "no"]


def por_tipo(filas: Sequence[Mapping[str, str]], tipo: str) -> list[Mapping[str, str]]:
    """Positivos del Reglamento; negativos de fuera de él.

    Los negativos son el hallazgo que abarata esta fase: son preguntas **reales de examen**
    cuya respuesta genuinamente no está en el Reglamento de Circulación. Fabricar negativos
    creíbles a mano es lo más caro de un golden set, y aquí ya están escritos.
    """
    return [f for f in filas if f["cobertura_rgc"] == COBERTURA[tipo]]


def umbrales() -> Umbrales:
    return umbrales_de_goals(GOALS)


def objetivo(suelo: int) -> int:
    """El suelo de `GOALS.yaml` por el factor de Q-004, redondeado hacia arriba."""
    return math.ceil(suelo * FACTOR_Q004)


def temas_objetivo(materias_min: int) -> int:
    return materias_min + MATERIAS_DE_MARGEN


def plan(filas: Sequence[Mapping[str, str]], *, objetivo: int, temas_max: int) -> dict[str, int]:
    """Reparte el objetivo entre los temas con más material, a partes iguales.

    A partes iguales y no en proporción al banco: el banco tiene la distribución de un examen
    de autoescuela, no la que hace falta para medir. Repartir proporcionalmente dejaría los
    temas pequeños por debajo de los casos que exige `materias_con_N_casos_o_mas`, que es
    donde de verdad se mira si el recall agregado esconde una materia que va fatal.

    Un tema sin material suficiente es un `ValueError`, no una cuota corta: descubrirlo en la
    hora 12 de Samuel es tirar el bloque entero.
    """
    disponibles = Counter(f["tema"] for f in filas)
    elegidos = [t for t, _ in disponibles.most_common(temas_max)]
    if not elegidos:
        raise ValueError("no hay ni un tema con material en el banco")

    base, resto = divmod(objetivo, len(elegidos))
    reparto = {t: base + (1 if i < resto else 0) for i, t in enumerate(elegidos)}

    cortos = {t: (disponibles[t], n) for t, n in reparto.items() if disponibles[t] < n}
    if cortos:
        detalle = ", ".join(f"{t}: hay {hay} y hacen falta {n}" for t, (hay, n) in cortos.items())
        raise ValueError(f"sin material suficiente para el objetivo · {detalle}")
    return reparto


def muestrear(
    filas: Sequence[Mapping[str, str]], *, plan: Mapping[str, int], tipo: str, semilla: int
) -> list[Candidato]:
    """La muestra estratificada, reproducible y sin repetir.

    Reproducible importa más de lo que parece: el README tiene que poder decir de dónde salió
    cada caso del golden set, y «los elegí yo» no es una respuesta.
    """
    por_tema: dict[str, list[Mapping[str, str]]] = {}
    for f in filas:
        por_tema.setdefault(f["tema"], []).append(f)

    elegidas: list[Mapping[str, str]] = []
    for tema, cuantas in plan.items():
        pozo = sorted(por_tema.get(tema, []), key=lambda f: f["source_id"])
        if len(pozo) < cuantas:
            raise ValueError(f"{tema}: hay {len(pozo)} preguntas y la cuota pide {cuantas}")
        elegidas.extend(random.Random(f"{semilla}·{tema}").sample(pozo, cuantas))  # noqa: S311

    return [
        Candidato(
            id=f"gs-{i:04d}",
            source_id=f["source_id"],
            pregunta=f["pregunta"],
            opciones=(f["opcion_1"], f["opcion_2"], f["opcion_3"]),
            respuesta_correcta=f["respuesta_correcta"],
            tema=f["tema"],
            subtema=f["subtema"],
            # El volcado trae el decimal con coma, que es como lo escribe la plataforma.
            pct_fallo=float(f["pct_fallo"].replace(",", ".")),
            tipo=tipo,
        )
        for i, f in enumerate(elegidas, start=1)
    ]


def deduplicar(
    candidatos: Sequence[Candidato],
    vectores: Mapping[str, Sequence[float]],
    *,
    umbral: float,
) -> tuple[list[Candidato], list[Candidato]]:
    """Quita las preguntas casi iguales **antes** de que Samuel las vea.

    `G-GOLDEN-VALID` las rechaza al final. Filtrarlas aquí y no allí es la diferencia entre
    descartar una fila de un fichero y descartar tres minutos de su tiempo. Se conserva
    siempre la primera, que es lo que hace la operación determinista.

    Un candidato sin vector es un error y no un salto: un comprobador que omite en silencio
    es uno que un día no comprueba nada.
    """
    faltan = [c.id for c in candidatos if c.id not in vectores]
    if faltan:
        raise ValueError(f"sin vector para comprobar duplicados: {', '.join(faltan[:5])}")

    conservados: list[Candidato] = []
    tirados: list[Candidato] = []
    for candidato in candidatos:
        gemelo = next(
            (c for c in conservados if _coseno(vectores[c.id], vectores[candidato.id]) >= umbral),
            None,
        )
        (tirados if gemelo is not None else conservados).append(candidato)
    return conservados, tirados


def _coseno(a: Sequence[float], b: Sequence[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=True)) / (na * nb)


def marcar_a_ciegas(candidatos: Sequence[Candidato], *, n: int, semilla: int) -> list[Candidato]:
    """Marca los casos en los que Samuel **no** verá la referencia propuesta.

    Mide dos cosas de golpe: la tasa de acierto real, y cuánto le está anclando ver una
    respuesta plausible antes de pensar. Un candidato malo se caza en dos segundos; uno
    plausible pero equivocado es el que se cuela con un «sí, vale», y ese riesgo **sube**
    con un modelo mejor, no baja.

    Se reparten por tema en vez de al azar sobre el montón: concentrados medirían la tasa de
    acierto de un tema, no la del conjunto.
    """
    if n > len(candidatos):
        raise ValueError(f"se piden {n} casos a ciegas y solo hay {len(candidatos)} candidatos")

    por_tema: dict[str, list[Candidato]] = {}
    for c in candidatos:
        por_tema.setdefault(c.tema, []).append(c)

    azar = random.Random(semilla)  # noqa: S311
    turnos = sorted(por_tema)
    elegidos: set[str] = set()
    ronda = 0
    while len(elegidos) < n:
        tema = turnos[ronda % len(turnos)]
        disponibles = [c.id for c in por_tema[tema] if c.id not in elegidos]
        if disponibles:
            elegidos.add(azar.choice(disponibles))
        ronda += 1

    return [replace(c, a_ciegas=c.id in elegidos) for c in candidatos]


# --------------------------------------------------------------------------------------
# Orquestación
# --------------------------------------------------------------------------------------

COLA = RAIZ / "evals" / "golden" / "cola" / "candidatos.jsonl"
SEMILLA = 20260808  # la de `comparacion` en GOALS.yaml, para no acuñar una segunda
SOBREDRAW = 1.25  # margen para que la deduplicación no deje ninguna cuota corta
A_CIEGAS = 18  # casos en los que Samuel no ve la propuesta


def _cola_de(
    tipo: str, filas: Sequence[Mapping[str, str]], reparto: Mapping[str, int]
) -> list[Candidato]:
    """Sobremuestrea, deduplica y recorta a la cuota. En ese orden y no en otro.

    Deduplicar antes de recortar es lo que evita que una cuota se quede corta por culpa de
    un duplicado: se pide de más, se tiran los gemelos y se recorta al final.
    """
    from citebound.providers.embeddings import embedder_por_defecto

    inflado = {t: math.ceil(n * SOBREDRAW) for t, n in reparto.items()}
    muestra = muestrear(filas, plan=inflado, tipo=tipo, semilla=SEMILLA)

    embedder = embedder_por_defecto()
    vectores = dict(
        zip([c.id for c in muestra], embedder.embed([c.pregunta for c in muestra]), strict=True)
    )
    conservados, tirados = deduplicar(muestra, vectores, umbral=COSENO)
    print(f"  {tipo}: {len(muestra)} muestreados · {len(tirados)} duplicados fuera")

    recortada: list[Candidato] = []
    for tema, cuantos in reparto.items():
        del_tema = [c for c in conservados if c.tema == tema]
        if len(del_tema) < cuantos:
            raise ValueError(
                f"{tema}: tras deduplicar quedan {len(del_tema)} y la cuota pide {cuantos}. "
                "Sube SOBREDRAW en vez de bajar la cuota"
            )
        recortada.extend(del_tema[:cuantos])
    return recortada


COSENO = 0.95  # el mismo que aplica `golden_validate`, y por el mismo motivo


def main() -> int:
    filas = usables(leer(BANCO))
    u = umbrales()
    print(
        f"banco: {len(filas)} usables · objetivo {objetivo(u.positivos_min)} positivos + "
        f"{objetivo(u.negativos_min)} negativos"
    )

    positivos = por_tipo(filas, "positivo")
    negativos = por_tipo(filas, "negativo")
    reparto_pos = plan(
        positivos,
        objetivo=objetivo(u.positivos_min),
        temas_max=temas_objetivo(u.materias_min),
    )
    reparto_neg = plan(negativos, objetivo=objetivo(u.negativos_min), temas_max=5)

    cola = _cola_de("positivo", positivos, reparto_pos) + _cola_de(
        "negativo", negativos, reparto_neg
    )
    # Los ids se renumeran al final: `gs-0001..gs-0304` sobre la cola definitiva, para que no
    # queden huecos donde estuvo un duplicado.
    cola = [replace(c, id=f"gs-{i:04d}") for i, c in enumerate(cola, start=1)]
    cola = marcar_a_ciegas(cola, n=A_CIEGAS, semilla=SEMILLA)

    COLA.parent.mkdir(parents=True, exist_ok=True)
    with COLA.open("w", encoding="utf-8") as fichero:
        for c in cola:
            fichero.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

    por_materia = Counter(c.tema for c in cola)
    print(f"cola escrita en {COLA.relative_to(RAIZ)} · {len(cola)} candidatos")
    print(f"  {sum(1 for c in cola if c.tipo == 'positivo')} positivos · ", end="")
    print(f"{sum(1 for c in cola if c.tipo == 'negativo')} negativos · ", end="")
    print(f"{sum(1 for c in cola if c.a_ciegas)} a ciegas · {len(por_materia)} materias")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
