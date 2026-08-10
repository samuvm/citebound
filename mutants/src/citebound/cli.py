"""`citebound` — ingest the frozen corpus and ask it questions.

Phase 0 has no generator: `ask` returns the text of the retrieved article with its
`LegalRef`. Saying that plainly in `--help` and in the output matters more than a demo
that looks smarter than it is.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from citebound.db.conexion import dsn
from citebound.db.schema import aplicar_esquema
from citebound.ingest.pipeline import escribir_refs, ingerir
from citebound.providers.embeddings import embedder_por_defecto
from citebound.retrieval.vector import buscar, indice_activo

RAIZ = Path(__file__).resolve().parents[2]
CORPUS = RAIZ / "corpus" / "raw" / "BOE-A-2003-23514.xml"
REFS = RAIZ / "corpus" / "index" / "refs.json"
NORMA = "RD-1428/2003"
SNAPSHOT = "2026-07-31"
URI = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/BOE-A-2003-23514"


def _ingest(_: argparse.Namespace) -> int:
    import psycopg

    with psycopg.connect(dsn()) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.chunk_v1')")
        if cur.fetchone()[0] is None:
            aplicar_esquema(cur)
        conn.commit()

    with psycopg.connect(dsn()) as conn, conn.cursor() as cur:
        ingesta = ingerir(
            cur,
            xml=CORPUS.read_text(encoding="utf-8"),
            norma=NORMA,
            source_uri=URI,
            embedder=embedder_por_defecto(),
            corpus_snapshot=SNAPSHOT,
        )
        conn.commit()
    escribir_refs(REFS, ingesta, norma=NORMA, corpus_snapshot=SNAPSHOT)
    print(f"{len(ingesta.chunks)} chunks · índice {ingesta.index_id}")
    print(f"{len(set(ingesta.refs))} referencias en {REFS.relative_to(RAIZ)}")
    return 0


def _ask(args: argparse.Namespace) -> int:
    import psycopg

    with psycopg.connect(dsn()) as conn, conn.cursor() as cur:
        index_version, physical_table = indice_activo(cur)
        recuperados = buscar(cur, args.pregunta, embedder=embedder_por_defecto(), k=args.k)

    if not recuperados:
        print("el índice no devolvió nada", file=sys.stderr)
        return 1

    print(f"# {args.pregunta}\n")
    print(recuperados[0].content)
    print("\n--- citas ---")
    for r in recuperados:
        print(f"  {r.ref}   d={r.distancia:.4f}   {(r.titulo or '')[:40]}")
    print(f"\nindex_version={index_version}  physical_table={physical_table}")
    print("fase 0: no hay generador; el texto es el del artículo recuperado")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="citebound",
        description=(
            "Tutor de normativa de circulación con cita cerrada. En la fase 0 no hay "
            "generador: `ask` devuelve el texto del artículo recuperado y su referencia."
        ),
    )
    sub = parser.add_subparsers(dest="orden", required=True)

    sub.add_parser("ingest", help="crea el esquema e indexa el corpus congelado").set_defaults(
        func=_ingest
    )

    p_ask = sub.add_parser("ask", help="pregunta al índice")
    p_ask.add_argument("pregunta")
    p_ask.add_argument("-k", type=int, default=5, help="cuántos preceptos recuperar")
    p_ask.set_defaults(func=_ask)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
