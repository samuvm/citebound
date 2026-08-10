"""`make smoke-f0` · la salida de la fase 0.

`docs/PLAN.md` lo define exactamente: **ingesta del corpus + 3 preguntas fijas + aserción
de que cada respuesta trae ≥1 referencia presente en `corpus/index/refs.json`.**

Esa última parte es la que importa y por eso se comprueba contra el fichero y no contra
la memoria del proceso: `G-HALLUC` se define como pertenencia de la `legal_ref` al
conjunto de refs del índice, y este humo es la primera vez que esa pertenencia se
verifica de punta a punta. Con cita cerrada será un invariante estructural; hoy, sin
generador, se confirma que la cañería no pierde por ningún lado.

    uv run python scripts/smoke_f0.py     # exit 0 o 1
"""

from __future__ import annotations

import sys
import time

from citebound.cli import CORPUS, NORMA, REFS, SNAPSHOT, URI
from citebound.db.conexion import dsn
from citebound.db.schema import aplicar_esquema
from citebound.ingest.pipeline import escribir_refs, ingerir, refs_conocidas
from citebound.providers.embeddings import embedder_por_defecto
from citebound.retrieval.vector import buscar, indice_activo

PREGUNTAS = [
    "¿Se puede adelantar en un cambio de rasante sin visibilidad?",
    "¿Con qué diligencia hay que conducir?",
    "¿Cómo se computan los carriles de una calzada?",
]


def main() -> int:
    import psycopg

    t0 = time.monotonic()
    embedder = embedder_por_defecto()
    print(f"· embedder {embedder.model} ({embedder.dim} dim) en {dsn().split('@')[-1]}")

    with psycopg.connect(dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.chunk_v1')")
            if cur.fetchone()[0] is None:
                aplicar_esquema(cur)
                print("· esquema creado")
            conn.commit()

        with conn.cursor() as cur:
            ingesta = ingerir(
                cur,
                xml=CORPUS.read_text(encoding="utf-8"),
                norma=NORMA,
                source_uri=URI,
                embedder=embedder,
                corpus_snapshot=SNAPSHOT,
            )
            conn.commit()
        escribir_refs(REFS, ingesta, norma=NORMA, corpus_snapshot=SNAPSHOT)
        conocidas = refs_conocidas(REFS)
        print(
            f"· ingesta: {len(ingesta.chunks)} chunks, {len(conocidas)} refs, "
            f"índice {ingesta.index_id}"
        )

        fallos: list[str] = []
        with conn.cursor() as cur:
            index_version, physical_table = indice_activo(cur)
            for pregunta in PREGUNTAS:
                recuperados = buscar(cur, pregunta, embedder=embedder, k=5)
                refs = [str(r.ref) for r in recuperados]
                presentes = [r for r in refs if r in conocidas]
                estado = "ok " if presentes else "FALLO"
                print(f"  [{estado}] {pregunta}")
                print(
                    f"          {len(presentes)}/{len(refs)} refs en el índice · "
                    f"1ª {refs[0] if refs else '—'}"
                )
                if not presentes:
                    fallos.append(pregunta)

    print(f"· índice activo: {index_version} -> {physical_table}")
    print(f"· {time.monotonic() - t0:.1f} s")

    if fallos:
        print(f"\nsmoke-f0 ROJO · {len(fallos)} preguntas sin una sola cita del índice")
        return 1
    print("\nsmoke-f0 VERDE · las 3 preguntas traen al menos una referencia que existe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
