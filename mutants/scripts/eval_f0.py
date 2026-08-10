"""`make eval` de la fase 0 · mide **solo** `G-HALLUC`, y dice por qué solo esa.

`docs/GOALS.yaml` pone `G-HALLUC` con `bloqueante_desde_fase: 0`, así que tiene que ser
medible ya. Las demás metas necesitan el golden set (fase 1) o el agente (fase 3), y
fabricar un número para ellas hoy sería exactamente lo que D-06 prohíbe.

Lo que se mide es literal: **cuántas referencias emite el sistema que no existen en el
índice activo**. Hoy es cero por una razón floja —no hay generador, las referencias salen
del propio índice— y el informe lo dice en `notes` en lugar de dejar que el cero parezca
lo que no es. Desde la fase 3, con cita cerrada, será cero por una razón fuerte.

El informe cumple `docs/CONTRACTS/eval-report.schema.json` desde el primer día: un
artefacto que empieza sin procedencia no la gana después.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

from citebound.cli import REFS
from citebound.db.conexion import dsn
from citebound.evals.preguntas_f0 import PREGUNTAS
from citebound.ingest.pipeline import refs_conocidas
from citebound.providers.embeddings import embedder_por_defecto
from citebound.retrieval.vector import EF_SEARCH, buscar, indice_activo

RAIZ = Path(__file__).resolve().parents[1]
INFORME = RAIZ / "evals" / "reports" / "eval-latest.json"
K = 5


def main() -> int:
    import psycopg

    conocidas = refs_conocidas(REFS)
    embedder = embedder_por_defecto()
    emitidas: list[str] = []
    inexistentes: list[str] = []

    with psycopg.connect(dsn()) as conn, conn.cursor() as cur:
        index_version, physical_table = indice_activo(cur)
        for pregunta in PREGUNTAS:
            for recuperado in buscar(cur, pregunta, embedder=embedder, k=K):
                ref = str(recuperado.ref)
                emitidas.append(ref)
                if ref not in conocidas:
                    inexistentes.append(f"{pregunta} -> {ref}")

    semilla = "\n".join(PREGUNTAS).encode()
    informe = {
        "contract_version": 1,
        "run_id": hashlib.sha256(f"{index_version}{semilla!r}{len(emitidas)}".encode()).hexdigest()[
            :16
        ],
        "project": "citebound",
        "suite": "fase-0",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "environment": {
            "hardware": "MacBook Pro M4 Max, 36 GB, macOS 26.5",
            "python": platform.python_version(),
            # No determinista todavia: se consulta la base de datos en vivo. La cache de
            # juicios y `make eval-determinism` son de la fase 4 (G-EVAL-DET).
            "deterministic": False,
        },
        "dataset": {
            "name": "smoke-f0 (3 preguntas fijas)",
            "version": 0,
            "n_cases": len(PREGUNTAS),
            "sha256": hashlib.sha256(semilla).hexdigest(),
        },
        "metrics": [
            {
                "id": "G-HALLUC",
                "value": len(inexistentes),
                "n": len(emitidas),
                "unit": "count",
            }
        ],
        "notes": (
            f"Fase 0: NO hay generador. Las {len(emitidas)} referencias salen del propio "
            f"indice, asi que G-HALLUC=0 hoy es cero por construccion trivial y no por la "
            f"cita cerrada, que llega en la fase 3. Con n={len(emitidas)} la cota superior "
            f"al 95 % de la tasa real es ~{3.0 / max(len(emitidas), 1):.1%} (regla de tres). "
            f"index_version={index_version} physical_table={physical_table} "
            f"ef_search={EF_SEARCH} k={K}. Ningun otro G- se mide aqui: necesitan el golden "
            f"set (fase 1) o el agente (fase 3), y fabricarlos hoy es lo que D-06 prohibe."
        ),
    }

    INFORME.parent.mkdir(parents=True, exist_ok=True)
    INFORME.write_text(
        json.dumps(informe, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
    )
    print(f"G-HALLUC = {len(inexistentes)} sobre n={len(emitidas)} referencias emitidas")
    print(f"informe: {INFORME.relative_to(RAIZ)}")
    for fallo in inexistentes:
        print(f"   INEXISTENTE: {fallo}")
    return 1 if inexistentes else 0


if __name__ == "__main__":
    sys.exit(main())
