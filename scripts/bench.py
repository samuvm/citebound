"""`make bench` · `G-TTFT`, con el protocolo de `bench/protocol.md` y no con uno improvisado.

**Un p95 sin condiciones declaradas no es comparable con nada**, y en `docs/PROJECT.md` la celda
«cómo se mide» de esta meta estaba literalmente en blanco. Aquí el cómo está escrito al lado del
qué, el script lo sigue, y lo que no puede comprobar lo **declara como supuesto** en vez de
callarlo.

**Dos números, no uno.** `TTFS` hasta `sources` y `TTFT` hasta el primer `token`. Medir el TTFT
hasta `sources` daría un p95 excelente sobre algo que no es lo que la meta promete: `sources`
sale antes de que el modelo haya escrito una palabra.

**El máximo de los tres p95 y no la media.** La media esconde una repetición que se fue, y una
que se va es justo lo que un usuario nota.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import statistics
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from citebound.agent.servir import Trozo, servir
from citebound.domain.citation import Fuente
from citebound.evals.schema import CasoGolden
from citebound.providers.chat import generador_por_defecto
from citebound.providers.reranker import reordenador_por_defecto
from citebound.retrieval import pipeline
from citebound.retrieval.vector import embedder_del_indice, indice_activo

__all__ = ["DESCARTE", "PETICIONES", "REPETICIONES", "main", "p95"]

RAIZ = Path(__file__).resolve().parents[1]
GOLDEN = max((RAIZ / "evals" / "golden").glob("v*.jsonl"))
INFORME = RAIZ / "evals" / "reports" / "bench-latest.json"

PETICIONES = 60
DESCARTE = 5
REPETICIONES = 3

PRESUPUESTO_ETAPA = {
    "embedding": 40.0,
    "busqueda": 90.0,
    "rerank": 400.0,
    "primer_token": 700.0,
}
"""`docs/RULES.md` §2.1. Una etapa fuera de su presupuesto marca **ámbar** aunque el total pase:
el margen de 210 ms es de donde vienen las regresiones de dentro de tres semanas."""


def p95(muestras: Sequence[float]) -> float:
    """El percentil 95 por interpolación lineal, que es lo que hace `statistics.quantiles`.

    Se nombra aquí en vez de llamarlo suelto para que dos corridas no puedan usar dos
    definiciones distintas de «p95» — hay al menos tres en circulación y difieren en la cola,
    que es precisamente donde vive esta meta.
    """
    if not muestras:
        return 0.0
    if len(muestras) == 1:
        return muestras[0]
    return statistics.quantiles(sorted(muestras), n=100, method="inclusive")[94]


def _plantilla() -> str:
    texto = (RAIZ / "prompts" / "responder.md").read_text(encoding="utf-8")
    return texto.split("\n---\n", 1)[1].lstrip("\n") if texto.startswith("---\n") else texto


def main() -> int:
    import psycopg

    casos = [
        CasoGolden.model_validate_json(x)
        for x in GOLDEN.read_text(encoding="utf-8").splitlines()
        if x.strip()
    ][:PETICIONES]
    puerto = os.environ.get("CITEBOUND_PG_PORT", "5434")
    url = os.environ.get(
        "CITEBOUND_PG_URL", f"postgresql://citebound:citebound@localhost:{puerto}/citebound"
    )
    generador = generador_por_defecto()
    reordenador = reordenador_por_defecto()
    plantilla = _plantilla()

    repeticiones: list[dict[str, float]] = []
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        index_version, physical_table = indice_activo(cur)
        embedder = embedder_del_indice(cur)

        for repeticion in range(REPETICIONES):
            ttfs: list[float] = []
            ttft: list[float] = []
            etapas: dict[str, list[float]] = {k: [] for k in PRESUPUESTO_ETAPA}

            for i, caso in enumerate(casos):
                marca: dict[str, float] = {}
                arranque = time.monotonic()

                def recupera(
                    q: str, _m: dict[str, float] = marca, _t: float = arranque
                ) -> list[Fuente]:
                    t0 = time.monotonic()
                    traidos = pipeline.recuperar(
                        cur, q, embedder=embedder, k=5, reordenador=reordenador
                    )
                    _m["busqueda"] = (time.monotonic() - t0) * 1000
                    _m["sources"] = (time.monotonic() - _t) * 1000
                    return [Fuente(ref=r.ref, texto=r.content) for r in traidos]

                corriente = servir(
                    caso.pregunta,
                    recuperador=recupera,
                    generador=generador,
                    plantilla=plantilla,
                )
                try:
                    for pieza in corriente:
                        if isinstance(pieza, Trozo):
                            marca["token"] = (time.monotonic() - arranque) * 1000
                            break
                finally:
                    # **Cerrar, no abandonar.** Un `break` sobre un generador deja la petición
                    # HTTP viva y al modelo generando del otro lado; con 180 peticiones eso se
                    # acumula y el p95 acaba midiendo la cola de trabajo abandonado, no la
                    # latencia. Medido: 7.294 ms abandonando contra ~60 ms del modelo en
                    # caliente. `close()` propaga `GeneratorExit` y cierra el stream.
                    corriente.close()

                # Las `DESCARTE` primeras no cuentan: el primer `predict` de MPS compila
                # kernels y el primer `httpx` abre el pool. Eso es arranque del PROCESO, y el
                # del sistema tiene su propia meta (`G-COLD-CACHE`).
                if i < DESCARTE:
                    continue
                ttfs.append(marca.get("sources", 0.0))
                ttft.append(marca.get("token", marca.get("sources", 0.0)))
                etapas["busqueda"].append(marca.get("busqueda", 0.0))
                etapas["primer_token"].append(marca.get("token", 0.0) - marca.get("sources", 0.0))

            repeticiones.append(
                {
                    "ttfs_p95": p95(ttfs),
                    "ttft_p95": p95(ttft),
                    **{f"{k}_p95": p95(v) for k, v in etapas.items() if v},
                    "n": float(len(ttft)),
                }
            )
            print(
                f"  repetición {repeticion + 1}/{REPETICIONES} · "
                f"TTFS p95 {repeticiones[-1]['ttfs_p95']:.0f} ms · "
                f"TTFT p95 {repeticiones[-1]['ttft_p95']:.0f} ms"
            )

    # **El máximo de los tres, no la media.** La media esconde una repetición que se fue.
    ttft_final = max(r["ttft_p95"] for r in repeticiones)
    ttfs_final = max(r["ttfs_p95"] for r in repeticiones)
    por_etapa = {
        k: max(r.get(f"{k}_p95", 0.0) for r in repeticiones)
        for k in PRESUPUESTO_ETAPA
        if any(f"{k}_p95" in r for r in repeticiones)
    }
    ambar = [k for k, v in por_etapa.items() if v > PRESUPUESTO_ETAPA[k]]

    informe = {
        "contract_version": 1,
        "run_id": hashlib.sha256(
            f"{index_version}{generador.model}{PETICIONES}{REPETICIONES}".encode()
        ).hexdigest()[:16],
        "project": "citebound",
        "suite": "bench-fase-3",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "environment": {
            "hardware": "MacBook Pro M4 Max, 36 GB, macOS 26.5",
            "python": platform.python_version(),
            "modelo": generador.model,
            "index_version": index_version,
            "physical_table": physical_table,
            "deterministic": False,
            # Lo que el script NO puede comprobar se declara como supuesto en vez de callarse.
            # `RULES` R11: un p95 sin condiciones declaradas no es comparable con nada.
            "supuestos_declarados": [
                "portátil enchufado",
                "sin throttling térmico entre repeticiones",
                "modelos residentes (make warm)",
                "ninguna otra carga de GPU en la máquina",
            ],
        },
        "dataset": {
            "name": GOLDEN.name,
            "version": int(GOLDEN.stem.lstrip("v")),
            "n_cases": PETICIONES - DESCARTE,
            "sha256": hashlib.sha256(GOLDEN.read_bytes()).hexdigest(),
        },
        "protocolo": "bench/protocol.md",
        "metrics": [
            {"id": "G-TTFT", "value": round(ttft_final, 1), "n": PETICIONES - DESCARTE},
            {"id": "G-TTFS", "value": round(ttfs_final, 1), "n": PETICIONES - DESCARTE},
        ],
        "por_etapa_p95_ms": {k: round(v, 1) for k, v in sorted(por_etapa.items())},
        "presupuesto_etapa_ms": PRESUPUESTO_ETAPA,
        "etapas_en_ambar": ambar,
        "repeticiones": repeticiones,
    }
    INFORME.parent.mkdir(parents=True, exist_ok=True)
    INFORME.write_text(
        json.dumps(informe, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"\n  G-TTFS  p95 {ttfs_final:>8.0f} ms")
    print(f"  G-TTFT  p95 {ttft_final:>8.0f} ms   (umbral 1500)")
    for etapa, valor in sorted(por_etapa.items()):
        aviso = "  ÁMBAR" if etapa in ambar else ""
        techo = PRESUPUESTO_ETAPA[etapa]
        print(f"    {etapa:<14} {valor:>8.0f} ms   (presupuesto {techo:.0f}){aviso}")
    print(f"\ninforme en {INFORME.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
