"""`make eval` · las metas de **generación**, sobre el golden set y con el agente entero.

Es la salida de la fase 3 junto con `make bench`, y mide seis cosas que hasta ahora no existían
porque no había generador: `G-HALLUC`, `G-QUOTE-LIT`, la pareja `G-CITA-PRECISION` +
`G-COBERTURA` y la pareja `G-ABST-FP` + `G-ABST-FN`.

**Las parejas son atómicas y por eso se publican juntas.** Medidas por separado, la forma óptima
de aprobar cualquiera de las dos es hacer trampa: abstenerse siempre da una precisión de cita de
1,00 sobre cero respuestas, y responder siempre nunca se abstiene de más. Un informe que
enseñara una sin la otra sería un informe que invita a optimizar la trampa.

**`G-HALLUC` y `G-QUOTE-LIT` son invariantes, no métricas de calidad.** Sus umbrales son `= 0` y
`= 1,00` y no admiten propuesta. Si bajan, no es que el sistema responda peor: es que el
verificador dejó pasar algo, y eso es un fallo del código y no del modelo.

**Caché de respuestas versionada**, igual que la de juicios del reordenador y por el mismo
motivo: una meta que tarda media hora se acaba sacando del gate, y sin caché el sistema no es
reproducible aunque no cambie nada — está medido en la fase 2 con el generador puesto a ordenar.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from citebound.agent.graph import Resultado, construir, responder
from citebound.domain.citation import Fuente
from citebound.domain.retry import Salida
from citebound.evals.schema import CasoGolden
from citebound.evals.scoring import (
    Prediccion,
    abstencion_incorrecta,
    abstencion_indebida,
    alucinacion,
    cobertura,
    precision_cita,
    precision_cita_articulo,
)
from citebound.providers.chat import generador_por_defecto
from citebound.retrieval import pipeline
from citebound.retrieval.vector import embedder_del_indice, indice_activo

__all__ = ["CacheRespuestas", "main", "medir"]

RAIZ = Path(__file__).resolve().parents[1]
GOLDEN = max((RAIZ / "evals" / "golden").glob("v*.jsonl"))
INFORME = RAIZ / "evals" / "reports" / "eval-latest.json"
CACHE = RAIZ / "evals" / "cache" / "respuestas.json"
PROMPT_ID, PROMPT_VERSION = "responder", 3

MAX_TOKENS = 1024
"""Suficiente para la prosa **y** el bloque de citas, que es donde se rompía.

Con 512 el modelo agotaba el presupuesto escribiendo la respuesta y no llegaba nunca a la línea
`CITAS`: el veredicto era `SIN_CITAS`, se reintentaba, y volvía a pasar lo mismo. Nueve de
veinticinco casos se abstenían por eso — un fallo de presupuesto que se leía como si el modelo
no supiera citar. Los quotes literales son largos por definición: son texto del BOE."""


class CacheRespuestas:
    """Los borradores del modelo, versionados en el repositorio.

    La clave lleva pregunta, **fuentes en su orden**, modelo y versión del prompt: cambiar
    cualquiera de las cuatro es hacerle otra pregunta, y reutilizar la respuesta sería mentir
    sobre qué se midió. Es exactamente el mismo razonamiento que `retrieval.rerank.clave_de`.
    """

    def __init__(self, ruta: Path) -> None:
        self._ruta = ruta
        self._datos: dict[str, list[str]] = (
            json.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else {}
        )
        self.aciertos = 0

    @staticmethod
    def clave(pregunta: str, fuentes: Sequence[Fuente], modelo: str) -> str:
        material = json.dumps(
            [pregunta, [str(f.ref) for f in fuentes], modelo, PROMPT_ID, PROMPT_VERSION],
            ensure_ascii=False,
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def obtener(self, clave: str) -> list[str] | None:
        guardado = self._datos.get(clave)
        if guardado is not None:
            self.aciertos += 1
        return guardado

    def guardar(self, clave: str, borradores: Sequence[str]) -> None:
        self._datos[clave] = list(borradores)

    def volcar(self) -> None:
        self._ruta.parent.mkdir(parents=True, exist_ok=True)
        self._ruta.write_text(
            json.dumps(self._datos, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _plantilla() -> str:
    texto = (RAIZ / "prompts" / f"{PROMPT_ID}.md").read_text(encoding="utf-8")
    return texto.split("\n---\n", 1)[1].lstrip("\n") if texto.startswith("---\n") else texto


def medir(
    casos: Sequence[CasoGolden], resultados: dict[str, Resultado]
) -> tuple[list[Prediccion], dict[str, object]]:
    """De los resultados del agente a las seis metas. Sin tocar nada más.

    Se separa del bucle que llama al modelo a propósito: así se puede comprobar con resultados
    fabricados y sin Ollama, y el cálculo de la métrica no depende de que haya red.
    """
    predicciones = [
        Prediccion(
            caso_id=caso.id,
            refs=() if _abstenido(resultados[caso.id]) else resultados[caso.id].curso.refs,
            abstenida=_abstenido(resultados[caso.id]),
        )
        for caso in casos
        if caso.id in resultados
    ]

    citas_emitidas = [
        (cita, r) for r in resultados.values() for cita in r.citas if not _abstenido(r)
    ]
    literales = sum(
        1
        for cita, r in citas_emitidas
        if _es_literal(cita.quote, r.fuentes[cita.n - 1].texto if cita.n <= len(r.fuentes) else "")
    )

    return predicciones, {
        "G-QUOTE-LIT": {
            "value": literales / len(citas_emitidas) if citas_emitidas else 1.0,
            "n": len(citas_emitidas),
        }
    }


def _abstenido(resultado: Resultado) -> bool:
    return resultado.curso.salida is not Salida.RESPONDER


def _es_literal(quote: str, texto: str) -> bool:
    from citebound.domain.citation import normalizar_para_cotejo

    return bool(quote) and normalizar_para_cotejo(quote) in normalizar_para_cotejo(texto)


def main() -> int:
    import psycopg

    casos = [
        CasoGolden.model_validate_json(x)
        for x in GOLDEN.read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]
    puerto = os.environ.get("CITEBOUND_PG_PORT", "5434")
    url = os.environ.get(
        "CITEBOUND_PG_URL", f"postgresql://citebound:citebound@localhost:{puerto}/citebound"
    )
    tope = int(os.environ.get("CITEBOUND_EVAL_N", "0")) or len(casos)
    casos = casos[:tope]

    cache = CacheRespuestas(CACHE)
    generador = generador_por_defecto()
    plantilla = _plantilla()
    resultados: dict[str, Resultado] = {}
    arranque = time.monotonic()

    with psycopg.connect(url) as conn, conn.cursor() as cur:
        index_version, physical_table = indice_activo(cur)
        embedder = embedder_del_indice(cur)

        for caso in casos:
            fuentes = [
                Fuente(ref=r.ref, texto=r.content)
                for r in pipeline.recuperar(cur, caso.pregunta, embedder=embedder, k=5)
            ]
            clave = CacheRespuestas.clave(caso.pregunta, fuentes, generador.model)
            guardados = cache.obtener(clave)
            grabados: list[str] = []

            def responde(
                prompt: str, _g: list[str] = grabados, _c: list[str] | None = guardados
            ) -> str:
                if _c is not None and len(_g) < len(_c):
                    texto = _c[len(_g)]
                else:
                    texto = generador.completar(prompt, max_tokens=MAX_TOKENS).texto
                _g.append(texto)
                return texto

            grafo = construir(
                recuperador=lambda _q, _f=fuentes: _f, generador=responde, plantilla=plantilla
            )
            resultados[caso.id] = responder(grafo, caso.pregunta)
            cache.guardar(clave, grabados)

    cache.volcar()
    total = time.monotonic() - arranque
    predicciones, extra = medir(casos, resultados)

    refs_del_corpus = json.loads(
        (RAIZ / "corpus" / "index" / "refs.json").read_text(encoding="utf-8")
    )["refs"]
    m_halluc = alucinacion(casos, predicciones, frozenset(refs_del_corpus))
    m_prec = precision_cita(casos, predicciones)
    m_prec_art = precision_cita_articulo(casos, predicciones)
    m_cob = cobertura(casos, predicciones)
    m_fp = abstencion_incorrecta(casos, predicciones)
    m_fn = abstencion_indebida(casos, predicciones)
    quote = extra["G-QUOTE-LIT"]

    semilla = GOLDEN.read_bytes()
    informe = {
        "contract_version": 1,
        "run_id": hashlib.sha256(
            f"{index_version}{generador.model}{PROMPT_VERSION}{len(casos)}".encode()
        ).hexdigest()[:16],
        "project": "citebound",
        "suite": "fase-3",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "environment": {
            "hardware": "MacBook Pro M4 Max, 36 GB, macOS 26.5",
            "python": platform.python_version(),
            "modelo": generador.model,
            "prompt_id": PROMPT_ID,
            "prompt_version": PROMPT_VERSION,
            "index_version": index_version,
            "physical_table": physical_table,
            # Determinista **desde la caché**, que es lo que la hace reproducible: sin ella el
            # modelo da respuestas distintas entre corridas aunque no cambie nada (medido en
            # la fase 2). `make eval-determinism` lo comprueba en la fase 4.
            "deterministic": cache.aciertos == len(casos),
            "aciertos_cache": cache.aciertos,
        },
        "dataset": {
            "name": GOLDEN.name,
            "version": int(GOLDEN.stem.lstrip("v")),
            "n_cases": len(casos),
            "sha256": hashlib.sha256(semilla).hexdigest(),
        },
        "metrics": [
            {"id": "G-HALLUC", "value": m_halluc.valor, "n": m_halluc.n},
            {"id": "G-QUOTE-LIT", "value": quote["value"], "n": quote["n"]},  # type: ignore[index]
            # `value` es la lectura **a nivel de artículo** (Q-021), que es la que lee el
            # gate. La estricta viaja al lado: la honestidad no está en elegir el número
            # bueno, está en enseñar los dos y decir cuál se publica y por qué. Es
            # exactamente lo que hace `make eval-retrieval` con el recall desde Q-016.
            {
                "id": "G-CITA-PRECISION",
                "value": m_prec_art.valor,
                "n": m_prec_art.n,
                "estricto": m_prec.valor,
                "a_nivel_articulo": m_prec_art.valor,
            },
            {"id": "G-COBERTURA", "value": m_cob.valor, "n": m_cob.n},
            {"id": "G-ABST-FP", "value": m_fp.valor, "n": m_fp.n},
            {"id": "G-ABST-FN", "value": m_fn.valor, "n": m_fn.n},
        ],
        "segundos": round(total, 1),
        "lectura_publicada": "a_nivel_articulo (Q-021)",
        "nota": (
            "G-CITA-PRECISION se publica a nivel de ARTICULO por Q-021, que declara una "
            "divergencia con docs/CONTRACTS/retrieval-metrics.md. Motivo medido: el apartado "
            "exacto esta entre las cinco fuentes ofrecidas en el 39 % de los casos, asi que la "
            "lectura estricta esta acotada muy por debajo de su umbral por una razon ajena al "
            "generador. La estricta se publica al lado. "
            "Las parejas G-CITA-PRECISION+G-COBERTURA y G-ABST-FP+G-ABST-FN son atomicas: "
            "medidas por separado, la forma optima de aprobar cualquiera de las dos es hacer "
            "trampa. G-HALLUC y G-QUOTE-LIT son invariantes del verificador, no metricas de "
            "calidad: si bajan, es que dejo pasar algo."
        ),
    }
    INFORME.parent.mkdir(parents=True, exist_ok=True)
    INFORME.write_text(
        json.dumps(informe, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"{len(casos)} casos · {total:.1f} s · {cache.aciertos} desde caché")
    for metrica in informe["metrics"]:  # type: ignore[attr-defined]
        # `None` con `n=0` no es un cero: es que la métrica **no está definida** sobre esta
        # muestra —sin casos negativos no hay abstención indebida que medir— y publicarla como
        # 0,0000 diría que el sistema acertó donde no se le preguntó.
        valor = metrica["value"]
        legible = "sin definir" if valor is None else f"{valor:.4f}"
        print(f"  {metrica['id']:<18} {legible:>11}  (n={metrica['n']})")
    print(f"\ninforme en {INFORME.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
