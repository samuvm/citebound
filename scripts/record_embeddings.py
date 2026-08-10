"""Grabar embeddings reales para que los tests sean deterministas y gratis.

Esto es lo ÚNICO que llama al modelo. Se ejecuta a mano cuando cambia el modelo o
hacen falta textos nuevos, y la grabación se versiona en el repo (RULES §3.1).

    uv run python scripts/record_embeddings.py
"""

from __future__ import annotations

import json
from pathlib import Path

from citebound.ingest.boe_xml import parse_norma
from citebound.ingest.chunking import chunk_preceptos
from citebound.providers.embeddings import OpenAICompatEmbedder, clave_de

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "tests" / "recordings" / "embeddings-bge-m3.json"
CORPUS = RAIZ / "corpus" / "raw" / "BOE-A-2003-23514.xml"
URI = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/BOE-A-2003-23514"

# Preguntas fijas del humo de la fase 0 (`make smoke-f0`) mas unos cuantos chunks
# reales: suficiente para ejercitar el flujo entero sin grabar 235 vectores.
PREGUNTAS = [
    "¿Se puede adelantar en un cambio de rasante sin visibilidad?",
    "¿Con qué diligencia hay que conducir?",
    "¿Cómo se computan los carriles de una calzada?",
]
REFS_MUESTRA = [
    "RD-1428/2003#art3",
    "RD-1428/2003#art34",
    "RD-1428/2003#art1",
    "RD-1428/2003#art2",
    "RD-1428/2003#art5",
    "RD-1428/2003#art14",
    "RD-1428/2003#art33",
    "RD-1428/2003#art35",
]


def main() -> None:
    preceptos = parse_norma(CORPUS.read_text(encoding="utf-8"), norma="RD-1428/2003")
    chunks = chunk_preceptos(preceptos, source_uri=URI)
    por_ref = {str(c.ref): c for c in chunks}

    textos = list(PREGUNTAS)
    for ref in REFS_MUESTRA:
        if ref in por_ref:
            textos.append(por_ref[ref].content)

    embedder = OpenAICompatEmbedder()
    print(f"grabando {len(textos)} textos con {embedder.model} en {embedder.base_url}…")
    vectores = embedder.embed(textos)

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(
        json.dumps(
            {
                "model": embedder.model,
                "dim": embedder.dim,
                "endpoint": f"{embedder.base_url}/embeddings",
                "nota": (
                    "Grabacion real. La regenera scripts/record_embeddings.py y NADA mas "
                    "llama al modelo. Las claves son sha256(model \\x00 texto)."
                ),
                "refs_muestra": [r for r in REFS_MUESTRA if r in por_ref],
                "preguntas": PREGUNTAS,
                "vectores": {
                    clave_de(embedder.model, t): [round(x, 7) for x in v]
                    for t, v in zip(textos, vectores, strict=True)
                },
            },
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(f"escrito {DESTINO.relative_to(RAIZ)} · {len(vectores)} vectores de {embedder.dim}")


if __name__ == "__main__":
    main()
