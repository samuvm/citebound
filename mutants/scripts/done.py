"""`make done MILESTONE=N` · la única definición de «hecho» (constitución §5).

Doce condiciones, **en orden y parando en la primera que falle**. Escribe el resultado en
`.claude/state/gate-status.json`, que el agente no puede editar.

Dos cosas que este fichero hace a propósito y que son la mitad de su valor:

**Una condición que no se puede comprobar es ROJA, nunca verde.** «No hay reserva de tests»
no significa «la reserva pasa». Un gate que da por bueno lo que no ha mirado es peor que
no tener gate, porque además da confianza.

**Cada fallo dice el comando que lo arregla.** Un gate que dice «rojo» y calla se acaba
desactivando; uno que dice «rojo, y esto es lo que hay que ejecutar» se usa.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess  # nosec B404 — listas fijas de argumentos, nunca shell
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ESTADO = RAIZ / ".claude" / "state" / "gate-status.json"
LOCK = RAIZ / "thresholds.lock"
GOALS = RAIZ / "docs" / "GOALS.yaml"
INVENTARIO = RAIZ / ".claude" / "state" / "test-inventory.json"
MUTACION = RAIZ / "evals" / "reports" / "mutation-latest.json"
TOPE_DEUDA = 10


@dataclass
class Resultado:
    numero: int
    nombre: str
    ok: bool
    detalle: str
    arreglo: str = ""
    datos: dict[str, object] = field(default_factory=dict)


def _correr(orden: str, *, cwd: Path = RAIZ) -> tuple[int, str]:
    proceso = subprocess.run(  # noqa: S603  # nosec B603 — lista fija, sin shell
        shlex.split(orden), cwd=cwd, capture_output=True, text=True, check=False
    )
    return proceso.returncode, (proceso.stdout + proceso.stderr)


# ---------------------------------------------------------------- 1 · estáticos ---
def c1_estaticos() -> Resultado:
    for orden in (
        "uv run ruff check src tests scripts",
        "uv run ruff format --check src tests scripts",
        # NO `uv run mypy` a pelo: `[tool.mypy].files` ya no existe (se quitó al derivar
        # la lista de [tool.gate].testable) y mypy sin rutas aborta con exit 2. El gate
        # llama al MISMO comprobador que `make typecheck`, no a una copia que pueda divergir.
        "uv run python scripts/typecheck.py",
        "uv run bandit -q -r src",
    ):
        codigo, salida = _correr(orden)
        if codigo != 0:
            return Resultado(1, "estáticos", False, f"{orden} → {codigo}\n{salida[-400:]}", orden)
    return Resultado(1, "estáticos", True, "ruff, format, mypy --strict y bandit limpios")


# ------------------------------------------------------------------- 2 · suite ---
def c2_suite() -> Resultado:
    codigo, salida = _correr("uv run pytest tests -q --no-cov -p no:randomly")
    n = re.search(r"(\d+) passed", salida)
    if codigo != 0:
        return Resultado(2, "suite completa", False, salida[-500:], "uv run pytest tests")
    return Resultado(
        2,
        "suite completa",
        True,
        f"{n.group(1) if n else '?'} tests, integración incluida",
        datos={"tests": int(n.group(1)) if n else 0},
    )


# ----------------------------------------------------------------- 3 · reserva ---
def c3_holdout() -> Resultado:
    carpeta = RAIZ / "tests" / "holdout"
    if not carpeta.is_dir() or not list(carpeta.glob("test_*.py")):
        return Resultado(
            3,
            "reserva",
            False,
            "no existe `tests/holdout/`. NO se da por buena: una condición que no se "
            "puede comprobar es roja.\n"
            "    Los escribe el subagente `qa-adversario`, que NO lee `tests/unit/`, y "
            "quedan en `deny` de lectura para el constructor (constitución §2.5 nº 4 y "
            "§9 paso 7).\n"
            "    El agente que ha escrito la suite NO puede escribirlos: sería tests "
            "contra sus propios tests, que es exactamente lo que la reserva existe para "
            "impedir.",
            "decisión de Samuel: lanzar `qa-adversario` o declarar la reserva fuera de "
            "alcance con su ADR",
        )
    codigo, salida = _correr("uv run pytest tests/holdout -q --no-cov")
    return Resultado(3, "reserva", codigo == 0, salida[-300:], "uv run pytest tests/holdout")


# ------------------------------------------------------- 4 · cobertura por función ---
def c4_cobertura_funcion() -> Resultado:
    codigo, salida = _correr("uv run python scripts/check_function_coverage.py")
    # `G-COV-FUNC` bloquea desde la fase 1 y su artefacto es este número. Antes esta
    # condición pasaba y la meta daba rojo por no encontrarlo: la misma verdad, verde por un
    # camino y roja por el otro. Si el comprobador falla y no se puede leer el recuento, NO
    # se apunta cero: se apunta 1, porque un fallo que no se sabe medir no es «ninguno».
    cuantas = re.search(r"G-COV-FUNC roja · (\d+) funciones", salida)
    MEDIDO["coverage.functions_without_test"] = (
        0 if codigo == 0 else (int(cuantas.group(1)) if cuantas else 1)
    )
    return Resultado(
        4,
        "cobertura por función",
        codigo == 0,
        salida.strip()[-400:],
        "uv run python scripts/check_function_coverage.py",
    )


# ---------------------------------------------------------- 5 · cobertura de línea ---
def c5_cobertura_linea() -> Resultado:
    cfg = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["gate"]
    minimo = cfg["cobertura_linea_min"]
    existentes = [r for r in cfg["testable"] if (RAIZ / r).exists()]
    informe = RAIZ / ".coverage-gate.json"
    codigo, _ = _correr(
        "uv run pytest tests -q -m 'not integration' --cov=citebound "
        f"--cov-report=json:{informe} -p no:randomly"
    )
    # El TOTAL del informe NO sirve: `[tool.coverage.run].source` mide `src/citebound`
    # entero, y ahi dentro estan `api/`, `db/` y `providers/`, que estan en
    # [tool.gate].excluido a proposito. Perseguir el 100 % en adaptadores es el ruido
    # que PROJECT.md §2 rechaza con razon. Se filtra a las rutas testable y punto.
    datos = json.loads(informe.read_text(encoding="utf-8"))["files"]
    cubiertas = faltan = 0
    for ruta, medida in datos.items():
        if not any(ruta == r or ruta.startswith(r.rstrip("/") + "/") for r in existentes):
            continue
        cubiertas += medida["summary"]["covered_lines"]
        faltan += medida["summary"]["missing_lines"]
    pct = round(100 * cubiertas / (cubiertas + faltan)) if cubiertas + faltan else -1
    # `G-COV-LINE` nombra `coverage.json :: totals.percent_covered (filtrado a
    # [tool.gate].testable)`. El paréntesis es la instrucción: el `totals` del fichero mide
    # `src/citebound` entero, adaptadores incluidos, y ese no es el número de la meta. Se
    # publica aquí el que sí lo es, y así la condición 7 lee lo mismo que enseña la 5.
    CALCULADO[("coverage.json", "totals.percent_covered")] = pct
    return Resultado(
        5,
        "cobertura de línea",
        codigo == 0 and pct >= minimo,
        f"{pct} % sobre las {len(existentes)} rutas de [tool.gate].testable que existen "
        f"(mínimo {minimo}); `api/`, `db/` y `providers/` quedan fuera a propósito",
        "uv run pytest tests --cov",
        {"porcentaje": pct, "minimo": minimo},
    )


# ---------------------------------------------------------------- 6 · mutación ---
def mutacion_caducada() -> str | None:
    """¿Hay código o tests más nuevos que la última corrida de mutación?

    Existe porque `make done` **no ejecuta** `mutmut run`: lee su caché. Y mutmut solo
    invalida al cambiar `src/`, nunca al cambiar los tests — así que el gate llevaba desde
    el 10 de agosto publicando un `587/588` calculado sobre un código que ya no existía.
    Un número que no se ha calculado es peor que no tener número, porque además da confianza.

    Correr la mutación entera dentro del gate costaría medio minuto en cada `make done`; que
    el gate **detecte** que la medida está caducada y se ponga rojo cuesta milisegundos y da
    la misma garantía, con la instrucción de qué ejecutar.
    """
    cache = RAIZ / "mutants"
    if not cache.is_dir():
        return "no hay ninguna corrida de mutación"
    medido_en = cache.stat().st_mtime
    for carpeta in ("src", "tests"):
        for fichero in (RAIZ / carpeta).rglob("*.py"):
            if "__pycache__" in fichero.parts:
                continue
            if fichero.stat().st_mtime > medido_en:
                return f"{fichero.relative_to(RAIZ)} es más nuevo que la última mutación"
    return None


def cfg_mutados() -> list[str]:
    """Qué ficheros mutó esta corrida. Va en el informe porque un `killed_pct` sin saber sobre
    qué se calculó es lo que dejó a `G-MUT` verde midiendo cinco de seis ficheros."""
    datos = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    return list(datos["tool"]["mutmut"]["source_paths"])


def c6_mutacion(milestone: int) -> Resultado:
    cfg = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["gate"]
    minimo = cfg["mutantes_muertos_min"]
    caducada = mutacion_caducada()
    if caducada is not None:
        return Resultado(
            6,
            "mutación",
            milestone < 3,
            f"medida caducada: {caducada}. NO se da por buena la corrida anterior — el gate "
            "leería un número calculado sobre otro código. Cuenta **también** un cambio en "
            "`tests/`, y a propósito: un mutante lo mata un test, así que tocar los tests "
            "puede cambiar el recuento aunque `src/` no se mueva. mutmut por su cuenta no "
            "invalida por eso, y ahí es donde el número se queda viejo sin que nadie lo note",
            "make clean-mutants && make mutation",
        )
    _, salida = _correr("uv run mutmut results --all true")
    muertos = len(re.findall(r": killed", salida))
    vivos = re.findall(r"(\S+): survived", salida)
    total = muertos + len(vivos)
    if total == 0:
        # `mutmut results` sin datos: hay que correr `mutmut run` antes.
        return Resultado(
            6,
            "mutación",
            milestone < 3,
            "sin resultados de mutación. G-MUT bloquea desde la fase 3, así que en la 0 "
            "esto informa y no bloquea",
            "uv run mutmut run",
        )
    pct = round(100 * muertos / total)
    # `G-MUT` nombra `evals/reports/mutation-latest.json :: killed_pct` y bloquea desde la
    # fase 3. Sin esto sería la cuarta meta muda por fontanería —tras `G-GOLDEN-VALID`,
    # `G-COV-FUNC` y `G-COV-LINE`—, y la habría descubierto el gate de la fase 3 en vez de
    # este. Se escribe el fichero **y** se publica en memoria: el fichero es para leerlo, y
    # `CALCULADO` para que la condición 7 use el número de ESTA corrida y no el de la anterior.
    informe = {
        "killed_pct": pct,
        "killed": muertos,
        "total": total,
        "supervivientes": vivos,
        "minimo": minimo,
        "ficheros": cfg_mutados(),
    }
    MUTACION.parent.mkdir(parents=True, exist_ok=True)
    MUTACION.write_text(
        json.dumps(informe, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    CALCULADO[("evals/reports/mutation-latest.json", "killed_pct")] = pct
    return Resultado(
        6,
        "mutación",
        pct >= minimo or milestone < 3,
        f"{muertos}/{total} mutantes muertos ({pct} %, mínimo {minimo})"
        + (f" · sobreviven: {', '.join(vivos[:3])}" if vivos else ""),
        "uv run mutmut run",
        {"killed_pct": pct, "supervivientes": vivos},
    )


# ------------------------------------------------------------ 7 · metas activas ---
def c7_metas(milestone: int) -> Resultado:
    import yaml

    metas = yaml.safe_load(GOALS.read_text(encoding="utf-8"))["metas"]
    activas = [
        m
        for m in metas
        if m.get("bloqueante_desde_fase") is not None and m["bloqueante_desde_fase"] <= milestone
    ]
    fallos, medidas = [], {}
    for meta in activas:
        valor = _leer_artefacto(meta)
        medidas[meta["id"]] = valor
        if valor is None:
            fallos.append(f"{meta['id']}: sin artefacto ({meta['artefacto'].split(' ::')[0]})")
            continue
        if not _cumple(valor, meta["umbral"]):
            fallos.append(
                f"{meta['id']}: {valor} incumple {meta['umbral']['operador']} "
                f"{meta['umbral']['valor']}"
            )
    return Resultado(
        7,
        "metas activas",
        not fallos,
        f"{len(activas)} metas bloquean en la fase {milestone}: "
        + (", ".join(f"{k}={v}" for k, v in medidas.items()) if medidas else "ninguna")
        + ("\n    " + "\n    ".join(fallos) if fallos else ""),
        "make eval",
        {"medidas": medidas},
    )


# Lo que ESTA corrida ha medido, por la ruta con que `GOALS.yaml` lo nombra. Se consulta en
# vez de releer `gate-status.json`, que en el momento de evaluar las metas todavía es el de
# la corrida anterior.
MEDIDO: dict[str, object] = {}

# Artefactos que produce ESTA corrida bajo la ruta con que `GOALS.yaml` los nombra, aunque en
# disco no exista un fichero con ese nombre. La clave es `(ruta, selector)` entero: dos metas
# pueden pedir selectores distintos del mismo fichero y no deben pisarse.
CALCULADO: dict[tuple[str, str], object] = {}


def _medir_secretos() -> int:
    codigo, salida = _correr(
        "uv run detect-secrets scan --baseline .secrets.baseline "
        "--exclude-files uv\\.lock|tests/recordings/|corpus/raw/|\\.snapshot\\.json"
    )
    return 0 if codigo == 0 else len(re.findall(r'"type":', salida))


# Medidas que la condición que las produce ejecuta DESPUÉS de evaluarse las metas. Se miden
# bajo demanda y se memorizan, para no correr `detect-secrets` dos veces por gate.
MEDIDORES: dict[str, Callable[[], object]] = {"secrets.new_findings": _medir_secretos}


def partir_artefacto(destino: str) -> tuple[str, str] | None:
    """`"fichero :: selector"` → `("fichero", "selector")`, o `None` si no tiene esa forma.

    `None` significa «este artefacto no es un JSON con un selector», no «no pasa nada». Hoy
    el único caso legítimo es `G-REVERSION`, que apunta a `docs/JOURNAL.md` más `.snapshots/`
    y tiene su propio comprobador; hay un test que lo nombra, para que un artefacto nuevo
    que nadie sepa leer salte en vez de colarse.

    El paréntesis explicativo se descarta: `totals.percent_covered (filtrado a
    [tool.gate].testable)` es una aclaración para quien lee, no parte de la clave.
    """
    if " :: " not in destino:
        return None
    ruta, _, selector = destino.partition(" :: ")
    selector = selector.split(" (")[0].strip()
    ruta = ruta.strip()
    if not ruta or not selector or "+" in selector:
        return None
    return ruta, selector


def seleccionar(datos: object, selector: str) -> object:
    """Resuelve una ruta punteada, con `clave[id=X]` para buscar dentro de una lista.

    Devuelve `None` en cuanto algo no encaja, y eso es lo correcto: `None` es rojo, mientras
    que un `KeyError` a mitad del gate dejaría las condiciones siguientes sin evaluar y
    escondería el resto de los problemas.
    """
    actual = datos
    for tramo in selector.split("."):
        indexado = re.fullmatch(r"(\w+)\[id=([^\]]+)\]", tramo)
        if indexado:
            clave, buscado = indexado.groups()
            if not isinstance(actual, dict) or not isinstance(actual.get(clave), list):
                return None
            elegido = [x for x in actual[clave] if isinstance(x, dict) and x.get("id") == buscado]
            if not elegido:
                return None
            actual = elegido[0]
            continue
        if not isinstance(actual, dict) or tramo not in actual:
            return None
        actual = actual[tramo]
    return actual


def leer_artefacto_ruta(ruta: str, selector: str) -> object:
    """El valor que declara `GOALS.yaml`, venga de disco o de esta misma corrida.

    **`gate-status.json` se resuelve en memoria, no leyendo el fichero.** La condición 7
    corre *antes* de que el estado se escriba, así que leerlo del disco daría el número de
    la corrida anterior: el gate se aprobaría con datos viejos. Es la misma familia de fallo
    que `G-MUT` leyendo la caché de mutmut, y aquí no se repite.

    `CALCULADO` cubre el caso contrario: la meta nombra un artefacto que **no** existe con
    ese nombre porque el número pedido no es el que trae el fichero. Es lo que pasa con
    `G-COV-LINE`, y el paréntesis de su artefacto lo dice — «filtrado a `[tool.gate].testable`».
    """
    if (ruta, selector) in CALCULADO:
        return CALCULADO[(ruta, selector)]
    if ruta.endswith("gate-status.json"):
        if selector not in MEDIDO and selector in MEDIDORES:
            MEDIDO[selector] = MEDIDORES[selector]()
        return MEDIDO.get(selector)
    fichero = Path(ruta) if Path(ruta).is_absolute() else RAIZ / ruta
    if not fichero.is_file():
        return None
    try:
        return seleccionar(json.loads(fichero.read_text(encoding="utf-8")), selector)
    except json.JSONDecodeError:
        return None


def medido_anidado() -> dict[str, object]:
    """`{"secrets.new_findings": 0}` → `{"secrets": {"new_findings": 0}}`.

    `GOALS.yaml` escribe rutas punteadas, así que en el fichero tienen que ser objetos
    anidados: una clave literal `"secrets.new_findings"` no la encontraría nadie que siguiera
    el contrato.
    """
    salida: dict[str, object] = {}
    for ruta, valor in MEDIDO.items():
        tramos = ruta.split(".")
        nodo = salida
        for tramo in tramos[:-1]:
            nodo = nodo.setdefault(tramo, {})  # type: ignore[assignment]
        nodo[tramos[-1]] = valor
    return salida


def _leer_artefacto(meta: dict[str, object]) -> object:
    partido = partir_artefacto(str(meta["artefacto"]))
    if partido is None:
        return None
    ruta, selector = partido
    return leer_artefacto_ruta(ruta, selector)


def _cumple(valor: object, umbral: dict[str, object]) -> bool:
    op, esperado = umbral["operador"], umbral["valor"]
    return {
        "==": lambda: valor == esperado,
        ">=": lambda: float(valor) >= float(esperado),  # type: ignore[arg-type]
        "<=": lambda: float(valor) <= float(esperado),  # type: ignore[arg-type]
    }[str(op)]()


# ------------------------------------------------------------ 8 · thresholds.lock ---
def c8_lock() -> Resultado:
    sha = hashlib.sha256(GOALS.read_bytes()).hexdigest()
    if not LOCK.is_file():
        return Resultado(
            8,
            "umbrales intactos",
            False,
            "no existe `thresholds.lock`. Sin él, nada impide que un agente baje un "
            "umbral y el gate no se entere: es el candado de todo lo demás.\n"
            f"    sha256 actual de docs/GOALS.yaml: {sha}",
            "SOLO SAMUEL, y solo tras aprobar docs/GOALS.yaml:\n"
            "       shasum -a 256 docs/GOALS.yaml | cut -d' ' -f1 > thresholds.lock",
        )
    guardado = LOCK.read_text(encoding="utf-8").strip().split()[0]
    return Resultado(
        8,
        "umbrales intactos",
        guardado == sha,
        "el lock coincide con GOALS.yaml"
        if guardado == sha
        else f"GOALS.yaml cambió sin regenerar el lock\n    lock={guardado}\n    real={sha}",
        "solo Samuel regenera el lock, y solo tras poner Estado: APROBADA",
    )


# --------------------------------------------------------- 9 · inventario de tests ---
def c9_inventario() -> Resultado:
    actual = _contar_tests()
    if not INVENTARIO.is_file():
        INVENTARIO.parent.mkdir(parents=True, exist_ok=True)
        INVENTARIO.write_text(json.dumps(actual, indent=1, sort_keys=True), encoding="utf-8")
        return Resultado(
            9,
            "inventario de tests",
            True,
            f"primera línea base: {sum(v['n_tests'] for v in actual.values())} tests, "
            f"{sum(v['n_asserts'] for v in actual.values())} aserciones",
        )
    previo = json.loads(INVENTARIO.read_text(encoding="utf-8"))
    caidas = [
        f"{f}: {previo[f]['n_tests']}→{actual.get(f, {}).get('n_tests', 0)} tests"
        for f in previo
        if actual.get(f, {}).get("n_tests", 0) < previo[f]["n_tests"]
        or actual.get(f, {}).get("n_asserts", 0) < previo[f]["n_asserts"]
    ]
    if not caidas:
        INVENTARIO.write_text(json.dumps(actual, indent=1, sort_keys=True), encoding="utf-8")
    return Resultado(
        9,
        "inventario de tests",
        not caidas,
        "ningún fichero pierde tests ni aserciones"
        if not caidas
        else "bajan tests o aserciones sin propuesta aprobada:\n    " + "\n    ".join(caidas),
        "diagnostica la causa real; borrar un test no es arreglarlo",
    )


def _contar_tests() -> dict[str, dict[str, int]]:
    inventario: dict[str, dict[str, int]] = {}
    for fichero in sorted((RAIZ / "tests").rglob("test_*.py")):
        texto = fichero.read_text(encoding="utf-8")
        inventario[str(fichero.relative_to(RAIZ))] = {
            "n_tests": len(re.findall(r"^\s*def test_", texto, re.M)),
            "n_asserts": len(re.findall(r"^\s*assert\b", texto, re.M)),
            "sha": hashlib.sha256(texto.encode()).hexdigest()[:16],
        }
    return inventario


# ------------------------------------------------------------------- 10 · deuda ---
def c10_deuda() -> Resultado:
    marcas = 0
    for fichero in (RAIZ / "src").rglob("*.py"):
        marcas += len(
            re.findall(r"\b(TODO|FIXME|XXX|NotImplementedError)\b", fichero.read_text("utf-8"))
        )
    # `skip`/`xfail` a secas, NO `skipif`. Un `skipif(not COMUN.is_file(), reason=...)`
    # es comportamiento correcto en un repo clonado sin `_comun/`, no una forma de
    # esquivar la suite; marcarlo en rojo seria un falso positivo, y un gate que grita
    # sin motivo se acaba desactivando (constitución §2.4).
    saltados = sum(
        len(re.findall(r"@pytest\.mark\.(?:skip|xfail)\b(?!if)", f.read_text("utf-8")))
        for f in (RAIZ / "tests").rglob("test_*.py")
    )
    return Resultado(
        10,
        "deuda bajo tope",
        marcas <= TOPE_DEUDA and saltados == 0,
        f"{marcas} marcas TODO/FIXME/XXX/NotImplementedError en src/ (tope {TOPE_DEUDA}) · "
        f"{saltados} tests con skip/xfail (deben ser 0 sin ticket en STATE.md)",
        "resuelve o declara la deuda en STATE.md",
        {"marcas": marcas, "skip_xfail": saltados},
    )


# ----------------------------------------------------------- 11 · documentación ---
def c11_docs() -> Resultado:
    fallos = []
    if not (RAIZ / "CHANGELOG.md").is_file():
        fallos.append("falta CHANGELOG.md")
    referenciados = set()
    # `docs/adr/000-plantilla.md` lleva la LISTA de ADR pendientes de escribir, y
    # `CONSTITUCION.md` y `JOURNAL.md` usan numeros de ejemplo. Contar esas citas como
    # referencias rotas convertiria la condicion en ruido permanente: lo que importa es
    # que un ADR citado como DECISION exista.
    fuentes = [
        f
        for f in list((RAIZ / "docs").rglob("*.md")) + list((RAIZ / "src").rglob("*.py"))
        if f.name not in {"000-plantilla.md", "CONSTITUCION.md", "JOURNAL.md"}
    ]
    for fichero in fuentes:
        referenciados |= set(re.findall(r"ADR-(\d{3})", fichero.read_text("utf-8")))
    existentes = {p.name[:3] for p in (RAIZ / "docs" / "adr").glob("*.md")}
    huerfanos = sorted(referenciados - existentes)
    if huerfanos:
        fallos.append(f"ADR citados que no existen: {', '.join('ADR-' + h for h in huerfanos)}")
    return Resultado(
        11,
        "documentación",
        not fallos,
        "; ".join(fallos)
        if fallos
        else f"CHANGELOG presente y los {len(referenciados)} ADR citados existen",
        "escribe el ADR que falta o corrige la referencia",
    )


# --------------------------------------------------------------- 12 · secretos ---
def c12_secretos() -> Resultado:
    # Memorizado: si la condición 7 ya evaluó `G-SECRETS`, el escaneo está hecho y correrlo
    # otra vez solo cuesta segundos de gate para llegar al mismo número.
    if "secrets.new_findings" not in MEDIDO:
        MEDIDO["secrets.new_findings"] = _medir_secretos()
    hallazgos = MEDIDO["secrets.new_findings"]
    return Resultado(
        12,
        "sin secretos",
        hallazgos == 0,
        "sin hallazgos nuevos sobre la baseline"
        if hallazgos == 0
        else f"{hallazgos} hallazgos nuevos sobre la baseline",
        "uv run detect-secrets scan --baseline .secrets.baseline",
    )


# ---------------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="La única definición de «hecho»")
    parser.add_argument("--milestone", type=int, required=True)
    parser.add_argument(
        "--diagnostico",
        action="store_true",
        help=(
            "evalúa las doce sin parar, para saber si la primera roja es la única. "
            "NO relaja el gate: `make done` sigue parando en la primera."
        ),
    )
    args = parser.parse_args()
    milestone, seguir = args.milestone, args.diagnostico

    print(f"make done MILESTONE={milestone} · doce condiciones, parando en la primera roja\n")
    comprobaciones = [
        c1_estaticos,
        c2_suite,
        c3_holdout,
        c4_cobertura_funcion,
        c5_cobertura_linea,
        lambda: c6_mutacion(milestone),
        lambda: c7_metas(milestone),
        c8_lock,
        c9_inventario,
        c10_deuda,
        c11_docs,
        c12_secretos,
    ]

    resultados: list[Resultado] = []
    for comprobar in comprobaciones:
        r = comprobar()
        resultados.append(r)
        print(f"  [{'ok  ' if r.ok else 'ROJO'}] {r.numero:2d} · {r.nombre}")
        for linea in r.detalle.splitlines():
            print(f"           {linea}")
        if not r.ok:
            print(f"           arréglalo con: {r.arreglo}")
            if not seguir:
                break

    verde = all(r.ok for r in resultados) and len(resultados) == len(comprobaciones)
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(
        json.dumps(
            {
                "milestone": milestone,
                "verde": verde,
                "evaluado_en": datetime.now(UTC).isoformat(timespec="seconds"),
                "condiciones": [
                    {
                        "n": r.numero,
                        "nombre": r.nombre,
                        "ok": r.ok,
                        "detalle": r.detalle.splitlines()[0] if r.detalle else "",
                        **r.datos,
                    }
                    for r in resultados
                ],
                "no_evaluadas": [
                    c.__name__ if hasattr(c, "__name__") else "lambda"
                    for c in comprobaciones[len(resultados) :]
                ],
                # Las medidas con la forma anidada que `GOALS.yaml` nombra, para quien lea
                # el fichero desde fuera. Dentro de la corrida se consulta `MEDIDO`.
                **medido_anidado(),
            },
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"\n{'=' * 74}")
    if verde:
        print(f"make done MILESTONE={milestone} · VERDE. Presenta los números y PARA.")
        return 0
    pendientes = len(comprobaciones) - len(resultados)
    print(
        f"make done MILESTONE={milestone} · ROJO en la condición {resultados[-1].numero}. "
        f"{pendientes} condiciones sin evaluar."
    )
    print("Una condición que no se puede comprobar es roja, nunca verde.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
