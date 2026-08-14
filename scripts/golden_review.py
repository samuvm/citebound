"""La cola de revisión de Samuel · `make golden-review`.

Esto es lo único de la fase 1 que Samuel toca con las manos, y son las 10-16 horas que
`PLAN.md` §3 y Q-004 presupuestan. Todo lo que hay aquí existe para que esas horas no se
desperdicien:

**El artículo íntegro a la izquierda, la propuesta a la derecha, una tecla.** Es lo que
convierte tres minutos en veinte segundos: nadie abre el BOE para validar un caso.

**Se guarda cada veredicto en cuanto se emite**, en un JSONL append-only. Cerrar el portátil
en el caso 137 cuesta cero minutos y se reanuda por el 138.

**El ritmo se vigila mientras anota, no al terminar.** Q-004 ratifica que si en los primeros
casos no baja de 3 min/caso, se para y se rediseña la cola: «es la diferencia entre 10 h y
25 h, y hay que detectarla en el minuto 60, no en la hora 12». Se mide con la **mediana**,
porque una interrupción larga dispararía la media sin decir nada del ritmo real.

**Los 18 casos a ciegas no enseñan la propuesta.** Miden dos cosas que no se separan de otra
forma: la tasa de acierto real, y cuánto ancla ver una respuesta plausible antes de pensar.
"""

from __future__ import annotations

import json
import statistics
import sys
import termios
import tty
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from citebound.domain.legalref import (
    LegalRef,
    LegalRefError,
    MatchLevel,
    format_ref,
    matches,
    parse,
)

__all__ = [
    "COLA",
    "PROPUESTAS",
    "TECLAS",
    "Vista",
    "alerta_de_ritmo",
    "anotar",
    "cargar_cola",
    "cargar_propuestas",
    "consolidar",
    "main",
    "pendientes",
    "resumen",
    "validar_correccion",
    "vista",
]

RAIZ = Path(__file__).resolve().parents[1]
COLA = RAIZ / "evals" / "golden" / "cola" / "candidatos.jsonl"
PROPUESTAS = RAIZ / "evals" / "golden" / "propuestas"
VEREDICTOS = RAIZ / "evals" / "golden" / "cola" / "veredictos.jsonl"
CORPUS = RAIZ / "corpus" / "raw" / "BOE-A-2003-23514.xml"
INDICE = RAIZ / "corpus" / "index" / "refs.json"
NORMA = "RD-1428/2003"

# Las cuatro de Q-004, sin añadir ninguna: cada tecla nueva es una decisión más por caso.
TECLAS: Mapping[str, str] = {
    "a": "ok",
    "e": "corregir",
    "r": "descartar",
    "s": "saltar",
}

MINIMO_CASOS_RITMO = 20
TOPE_SEGUNDOS = 180.0  # los 3 min/caso de Q-004


@dataclass(frozen=True, slots=True)
class Vista:
    """Lo que se le enseña a Samuel de un caso. Lo que NO lleva importa tanto como lo que sí."""

    id: str
    pregunta: str
    opciones: tuple[str, ...]
    respuesta_correcta: str
    tema: str
    subtema: str
    tipo: str
    a_ciegas: bool
    ref_propuesta: str | None
    nota: str | None
    texto: str | None


def cargar_cola(ruta: Path) -> list[dict[str, object]]:
    return [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines() if linea]


def cargar_propuestas(carpeta: Path) -> dict[str, dict[str, object]]:
    """Junta los ocho ficheros de tema y el de negativos en un solo mapa por id."""
    todas: dict[str, dict[str, object]] = {}
    for fichero in sorted(carpeta.glob("*.json")):
        for clave, valor in json.loads(fichero.read_text(encoding="utf-8")).items():
            if not clave.startswith("_"):  # `_formato` documenta el fichero, no es un caso
                todas[clave] = valor
    return todas


def pendientes(
    cola: Sequence[Mapping[str, object]], hechos: Sequence[Mapping[str, object]]
) -> list[Mapping[str, object]]:
    """Los que faltan, en el orden de la cola. Reanudar es no volver a ver lo juzgado."""
    juzgados = set(consolidar(hechos))
    return [c for c in cola if c["id"] not in juzgados]


def consolidar(hechos: Sequence[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    """El último veredicto de cada caso es el que vale.

    El fichero es append-only a propósito, así que corregirse sobre la marcha no puede
    exigir editarlo a mano: se vuelve a anotar y la última línea gana.
    """
    ultimo: dict[str, Mapping[str, object]] = {}
    for h in hechos:
        ultimo[str(h["id"])] = h
    return ultimo


def anotar(destino: Path, veredicto: Mapping[str, object]) -> None:
    """Una línea, un veredicto, y al disco inmediatamente."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("a", encoding="utf-8") as fichero:
        fichero.write(json.dumps(veredicto, ensure_ascii=False) + "\n")


def vista(
    caso: Mapping[str, object], propuesta: Mapping[str, object], texto: str | None = None
) -> Vista:
    """Monta lo que se ve. En los casos a ciegas la propuesta **no viaja**, ni la nota.

    Ocultarla en el renderizado y no aquí sería un accidente esperando a ocurrir: bastaría
    con imprimir el objeto en una traza para arruinar la medida.
    """
    a_ciegas = bool(caso.get("a_ciegas"))
    es_negativo = caso["tipo"] == "negativo"
    # En un negativo no hay `ref` que validar... salvo que la revisión lo haya marcado como
    # FALSO negativo, y entonces `responde` lleva el artículo que sí lo contesta. Ese caso es
    # el más valioso de la cola y tiene que llegar a la pantalla: si se presenta como «confirma
    # que el corpus no responde» y se traga el hallazgo, Samuel lo confirmaría y `G-ABST-FN`
    # acabaría penalizando al sistema por acertar.
    ref = propuesta.get("responde") if es_negativo else propuesta.get("ref")
    return Vista(
        id=str(caso["id"]),
        pregunta=str(caso["pregunta"]),
        opciones=tuple(str(o) for o in caso.get("opciones", ())),
        respuesta_correcta=str(caso["respuesta_correcta"]),
        tema=str(caso["tema"]),
        subtema=str(caso["subtema"]),
        tipo=str(caso["tipo"]),
        a_ciegas=a_ciegas,
        ref_propuesta=None if (a_ciegas or ref is None) else str(ref),
        nota=None if a_ciegas else str(propuesta.get("nota", "")),
        texto=None if a_ciegas else texto,
    )


def validar_correccion(texto: str, *, indice: frozenset[str]) -> LegalRef:
    """Una corrección tiene que existir en el corpus, o no entra.

    Sin esto, una errata al teclear metería en el golden set exactamente la alucinación de
    referencia que `G-HALLUC` existe para hacer imposible — y encima con la firma de un
    humano, que es la peor forma de colarla.
    """
    try:
        ref = parse(texto)
    except LegalRefError as err:
        raise ValueError(f"{texto!r} no es una referencia legal: {err}") from err
    articulos = [parse(r) for r in indice]
    if not any(matches(ref, a, MatchLevel.ARTICULO) for a in articulos):
        raise ValueError(f"{format_ref(ref)} no existe en el índice del corpus")
    return ref


def alerta_de_ritmo(
    hechos: Sequence[Mapping[str, object]], *, minimo_casos: int, tope_segundos: float
) -> str | None:
    """La regla de parada de Q-004, comprobada sobre la marcha.

    **Mediana y no media**: una interrupción larga —un café, una llamada— dispara la media
    y no dice nada del ritmo real. Lo que Q-004 presupuesta es el ritmo sostenido.

    Por debajo de `minimo_casos` no se juzga nada: los primeros son de calibración, donde
    Samuel está decidiendo su propio criterio, y ahí tardar es lo esperable.
    """
    tiempos = [float(h["segundos"]) for h in hechos if h.get("segundos") is not None]
    if len(tiempos) < minimo_casos:
        return None
    mediana = statistics.median(tiempos)
    if mediana <= tope_segundos:
        return None
    return (
        f"PARADA (Q-004): mediana de {mediana:.0f} s/caso sobre {len(tiempos)} casos, "
        f"objetivo {tope_segundos:.0f} s. Con este ritmo la cola entera son "
        f"{mediana * 304 / 3600:.1f} h. Hay que rediseñarla antes de seguir"
    )


def resumen(hechos: Sequence[Mapping[str, object]], pendientes: int = 0) -> dict[str, object]:
    """Los números que se le deben a Samuel, incluido el que Q-004 lleva estimando sin medir.

    La tasa de acierto se publica **dos veces**: sobre todo lo anotado y solo sobre los casos
    a ciegas. La primera está contaminada por el anclaje —ver una respuesta plausible antes
    de pensar—; la segunda no. La que vale es la segunda.
    """
    juzgados = [h for h in hechos if h.get("veredicto") in ("ok", "corregir", "descartar")]
    decididos = [h for h in juzgados if h["veredicto"] in ("ok", "corregir")]
    ciegas = [h for h in decididos if h.get("a_ciegas")]
    tiempos = [float(h["segundos"]) for h in hechos if h.get("segundos") is not None]
    mediana = statistics.median(tiempos) if tiempos else None

    def tasa(muestra: Sequence[Mapping[str, object]]) -> float | None:
        if not muestra:
            return None
        return sum(1 for h in muestra if h["veredicto"] == "ok") / len(muestra)

    return {
        "n": len(juzgados),
        "aciertos": sum(1 for h in decididos if h["veredicto"] == "ok"),
        "tasa_acierto": tasa(decididos),
        "n_ciegas": len(ciegas),
        "tasa_acierto_ciegas": tasa(ciegas),
        "descartados": sum(1 for h in juzgados if h["veredicto"] == "descartar"),
        "mediana_segundos": mediana,
        "restante_horas": (mediana * pendientes / 3600) if mediana is not None else None,
    }


# --------------------------------------------------------------------------------------
# La interfaz. Deliberadamente delgada: aquí no vive ninguna decisión
# --------------------------------------------------------------------------------------

ANCHO = 96


def _tecla() -> str:
    """Una pulsación, sin Enter. Es lo que hace que un caso cueste una tecla y no tres."""
    descriptor = sys.stdin.fileno()
    previo = termios.tcgetattr(descriptor)
    try:
        tty.setraw(descriptor)
        return sys.stdin.read(1).lower()
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, previo)


def _envolver(texto: str, ancho: int) -> list[str]:
    lineas: list[str] = []
    for parrafo in texto.split("\n"):
        actual = ""
        for palabra in parrafo.split():
            if len(actual) + len(palabra) + 1 > ancho:
                lineas.append(actual)
                actual = palabra
            else:
                actual = f"{actual} {palabra}".strip()
        lineas.append(actual)
    return lineas


def _pintar(v: Vista, hecho: int, total: int) -> None:
    print("\033[2J\033[H", end="")
    marca = " · A CIEGAS" if v.a_ciegas else ""
    print(f"╭─ {v.id}  ({hecho}/{total}){marca}  ·  {v.tema} / {v.subtema}")
    print("│")
    for linea in _envolver(v.pregunta, ANCHO - 4):
        print(f"│  {linea}")
    print(f"│  → {v.respuesta_correcta}")
    print("│")
    if v.tipo == "negativo" and v.ref_propuesta is None:
        print("│  NEGATIVO · confirma que el Reglamento NO responde esta pregunta")
        if v.nota:
            for linea in _envolver(f"nota: {v.nota}", ANCHO - 6):
                print(f"│    {linea}")
    elif v.tipo == "negativo":
        print("│  NEGATIVO, pero creo que el corpus SI lo responde:")
        print(f"│  Propongo pasarlo a POSITIVO con  {v.ref_propuesta}")
        if v.nota:
            for linea in _envolver(f"nota: {v.nota}", ANCHO - 6):
                print(f"│    {linea}")
        if v.texto:
            print("│")
            for linea in _envolver(v.texto, ANCHO - 4)[:16]:
                print(f"│  {linea}")
    elif v.a_ciegas:
        print("│  Sin propuesta: escribe tú la referencia con [e]")
    else:
        print(f"│  Propongo:  {v.ref_propuesta}")
        if v.nota:
            for linea in _envolver(f"nota: {v.nota}", ANCHO - 6):
                print(f"│    {linea}")
        if v.texto:
            print("│")
            for linea in _envolver(v.texto, ANCHO - 4)[:22]:
                print(f"│  {linea}")
    print("╰" + "─" * (ANCHO - 1))
    print("  [a] ok    [e] corregir    [r] descartar    [s] saltar    [q] guardar y salir")


def _texto_de(ref: str, preceptos: Mapping[str, object]) -> str | None:
    """El artículo entero, o el apartado concreto si la referencia baja a él."""
    objetivo = parse(ref)
    articulo = preceptos.get(f"{objetivo.norma}#art{objetivo.articulo}")
    if articulo is None:
        return None
    apartados = articulo.apartados  # type: ignore[attr-defined]
    if objetivo.apartado:
        exacto = [a for a in apartados if a.numero == objetivo.apartado]
        if exacto:
            return f"[{exacto[0].numero}] {exacto[0].texto}"
    return "\n".join(f"[{a.numero}] {a.texto}" for a in apartados)


def main() -> int:
    from citebound.ingest.boe_xml import parse_norma

    if not COLA.is_file():
        print(f"no existe {COLA.relative_to(RAIZ)}. Ejecuta antes: make golden-sample")
        return 1

    cola = cargar_cola(COLA)
    propuestas = cargar_propuestas(PROPUESTAS)
    indice = frozenset(json.loads(INDICE.read_text(encoding="utf-8"))["refs"])
    preceptos = {
        str(p.ref): p for p in parse_norma(CORPUS.read_text(encoding="utf-8"), norma=NORMA)
    }
    hechos = cargar_cola(VEREDICTOS) if VEREDICTOS.is_file() else []
    cola_pendiente = pendientes(cola, hechos)

    print(f"{len(cola)} casos · {len(hechos)} juzgados · {len(cola_pendiente)} pendientes")
    for caso in cola_pendiente:
        propuesta = propuestas.get(str(caso["id"]), {})
        # Misma resolución que `vista`: en un negativo el artículo relevante es el que lo
        # DESMIENTE, si la revisión encontró uno.
        ref = propuesta.get("responde") if caso["tipo"] == "negativo" else propuesta.get("ref")
        v = vista(caso, propuesta, texto=_texto_de(str(ref), preceptos) if ref else None)
        _pintar(v, len(cola) - len(cola_pendiente) + cola_pendiente.index(caso) + 1, len(cola))

        arranque = monotonic()
        tecla = _tecla()
        if tecla == "q":
            break
        while tecla not in TECLAS:
            tecla = _tecla()
            if tecla == "q":
                return _cerrar(hechos, len(cola_pendiente))

        registro: dict[str, object] = {
            "id": v.id,
            "veredicto": TECLAS[tecla],
            "ref": ref,
            "a_ciegas": v.a_ciegas,
            "segundos": round(monotonic() - arranque, 1),
            "en": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        if TECLAS[tecla] == "corregir":
            while True:
                escrito = input("\n  referencia correcta (p. ej. RD-1428/2003#art36.2): ").strip()
                try:
                    registro["ref"] = format_ref(validar_correccion(escrito, indice=indice))
                    break
                except ValueError as err:
                    print(f"  ✗ {err}")
        anotar(VEREDICTOS, registro)
        hechos.append(registro)

        alerta = alerta_de_ritmo(
            hechos, minimo_casos=MINIMO_CASOS_RITMO, tope_segundos=TOPE_SEGUNDOS
        )
        if alerta is not None:
            print(f"\n\n  {alerta}\n")
            return _cerrar(hechos, len(cola_pendiente))
    return _cerrar(hechos, len(pendientes(cola, hechos)))


def _cerrar(hechos: Sequence[Mapping[str, object]], quedan: int) -> int:
    r = resumen(hechos, pendientes=quedan)
    print("\033[2J\033[H", end="")
    print(f"anotados {r['n']} · quedan {quedan}")
    if r["tasa_acierto"] is not None:
        print(f"  tasa de acierto (con propuesta a la vista): {r['tasa_acierto']:.0%}")
    if r["tasa_acierto_ciegas"] is not None:
        print(f"  tasa de acierto A CIEGAS ({r['n_ciegas']} casos): {r['tasa_acierto_ciegas']:.0%}")
        print("    ← esta es la limpia: la otra la contamina ver la propuesta antes de pensar")
    if r["mediana_segundos"] is not None:
        print(
            f"  mediana: {r['mediana_segundos']:.0f} s/caso · quedan ~{r['restante_horas']:.1f} h"
        )
    print(f"  descartados: {r['descartados']}")
    print(f"\nveredictos en {VEREDICTOS.relative_to(RAIZ)} · se reanuda con `make golden-review`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
