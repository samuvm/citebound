"""`make eval-retrieval` · mide `G-RECALL5` y `G-RECALL30` contra el golden set.

Es la meta de calidad **barata**: sin LLM generador, sin juez, en menos de 90 s. Por eso vive
en el gate de turno desde la fase 2 y por eso es la primera vez que este proyecto produce un
número que no es una opinión.

**Las dos lecturas del recall, y por qué se publican las dos.** El contrato define
`recall@k = |R(q) ∩ P_k(q)| / |R(q)|` como una intersección de conjuntos de `legal_ref`, y
calla sobre la granularidad. Pero el troceador es `articulo-v1`: **ninguna** ref indexada lleva
apartado, mientras que el 86 % de las del golden set sí. Con la lectura literal, el recall está
acotado por construcción en el 13 % — haga lo que haga el recuperador.

No es un fallo del recuperador ni del golden set: es que recall y precisión de cita miden
cosas distintas. Traer el artículo correcto es trabajo del recuperador; bajar al apartado es
trabajo del generador, y para eso está `G-CITA-PRECISION`, cuya regla de granularidad **sí**
está escrita en el contrato. Aun así, la decisión de qué número se publica no la toma este
script: mide las dos y las deja a la vista.

**Las preguntas se vectorizan en un solo lote.** 219 llamadas sueltas a Ollama son minutos;
un lote son segundos. El presupuesto de 90 s de `RULES` §3.3 no es decorativo — una meta que
tarda más se acaba sacando del gate.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from citebound.domain.legalref import LegalRef
from citebound.evals.schema import CasoGolden, Tipo
from citebound.evals.scoring import recall_at_k
from citebound.providers.chat import generador_por_defecto
from citebound.providers.reranker import reordenador_por_defecto
from citebound.retrieval import lexical, pipeline
from citebound.retrieval import vector as vector_mod
from citebound.retrieval.rerank import CacheJuicios, ReordenadorLLM
from citebound.retrieval.vector import embedder_del_indice, indice_activo

__all__ = ["a_nivel_articulo", "main", "medir"]

RAIZ = Path(__file__).resolve().parents[1]
GOLDEN = max((RAIZ / "evals" / "golden").glob("v*.jsonl"))
INFORME = RAIZ / "evals" / "reports" / "retrieval-latest.json"
CACHE_RERANK = RAIZ / "evals" / "cache" / "rerank.json"
K_MEDIDOS = (5, 30)


def a_nivel_articulo(ref: LegalRef) -> LegalRef:
    """`art82.2` → `art82`. Deja intacta la que ya venía sin apartado."""
    return ref if ref.apartado is None else replace(ref, apartado=None)


class _Precalculado:
    """Un `Embedder` que ya sabe la respuesta.

    Existe para no tocar `pipeline`: el evaluador vectoriza las 219 preguntas de una vez y
    después le pasa a cada consulta su vector ya hecho. `pipeline` sigue creyendo que habla
    con un embedder normal.
    """

    def __init__(self, vector: Sequence[float], model: str, dim: int) -> None:
        self._vector, self._model, self._dim = tuple(vector), model, dim

    @property
    def model(self) -> str:
        return self._model

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, textos: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return (self._vector,)


def medir(
    cur: object,
    casos: Sequence[CasoGolden],
    *,
    k_canal: int = pipeline.K_CANAL,
    con_reranker: bool = False,
) -> dict[str, object]:
    """Recupera para cada caso positivo y devuelve las dos lecturas del recall."""
    positivos = [c for c in casos if c.tipo is Tipo.POSITIVO and c.refs]
    # Q-020 (A): el reordenador es un cross-encoder en proceso. El del generador se queda en
    # `retrieval/rerank.py` con su medida, porque comparar exige poder repetir las dos.
    con_llm = os.environ.get("CITEBOUND_RERANK_LLM") == "1"
    cache = CacheJuicios(CACHE_RERANK) if con_reranker and con_llm else None
    reordenador = (
        (
            ReordenadorLLM(generador_por_defecto(), cache=cache)
            if con_llm
            else reordenador_por_defecto()
        )
        if con_reranker
        else None
    )
    # Del índice, no del entorno: medir con un modelo distinto del que construyó el índice no
    # da error, da un recall peor sin causa aparente. Ver `embedder_del_indice`.
    embedder = embedder_del_indice(cur)  # type: ignore[arg-type]
    arranque = time.monotonic()
    vectores = embedder.embed([c.pregunta for c in positivos])
    t_embed = time.monotonic() - arranque

    recuperado: dict[str, list[LegalRef]] = {}
    solo_vector: dict[str, list[LegalRef]] = {}
    solo_lexico: dict[str, list[LegalRef]] = {}
    for caso, vector in zip(positivos, vectores, strict=True):
        precalculado = _Precalculado(vector, embedder.model, embedder.dim)
        traidos = pipeline.recuperar(
            cur,  # type: ignore[arg-type]
            caso.pregunta,
            embedder=precalculado,
            k=K_MEDIDOS[-1],
            k_canal=k_canal,
            reordenador=reordenador,
        )
        recuperado[caso.id] = [r.ref for r in traidos]
        # Los canales sueltos, para que la tabla del README salga del artefacto medido y no
        # de un script aparte que puede quedarse viejo sin que nada lo note. No cuestan LLM.
        solo_vector[caso.id] = [
            r.ref
            for r in vector_mod.buscar(cur, caso.pregunta, embedder=precalculado, k=K_MEDIDOS[-1])  # type: ignore[arg-type]
        ]
        solo_lexico[caso.id] = [
            r.ref
            for r in lexical.buscar(cur, caso.pregunta, k=K_MEDIDOS[-1])  # type: ignore[arg-type]
        ]

    # Lectura a nivel de artículo: se recortan **los dos lados**. El comentario que ocupaba
    # este sitio decía que recortar solo el golden set daba igual «porque el índice ya viene
    # sin apartado», y avisaba de que dejaría de dar igual el día que el troceado bajara al
    # apartado. Ese día fue el 2026-08-17: con `apartado-v1` lo recuperado trae `art34.1` y
    # el golden set recortado trae `art34`, así que la intersección sería vacía y `G-RECALL5`
    # se habría desplomado sin que nada dijera por qué. La métrica NO cambia en silencio.
    por_articulo = [
        c.model_copy(update={"refs": [a_nivel_articulo(r) for r in c.refs]}) for c in positivos
    ]
    recuperado_articulo = {
        ident: [a_nivel_articulo(r) for r in refs] for ident, refs in recuperado.items()
    }

    if cache is not None:
        cache.volcar()

    medidas: dict[str, object] = {
        "n_casos": len(positivos),
        "segundos_embedding": round(t_embed, 1),
    }
    for k in K_MEDIDOS:
        estricto = recall_at_k(positivos, recuperado, k)
        articulo = recall_at_k(por_articulo, recuperado_articulo, k)
        medidas[f"G-RECALL{k}"] = {
            "estricto": estricto.valor,
            "a_nivel_articulo": articulo.valor,
            "n": estricto.n,
        }
    medidas["por_canal"] = {
        nombre: {
            f"recall{k}": recall_at_k(
                por_articulo,
                {i: [a_nivel_articulo(r) for r in refs] for i, refs in traido.items()},
                k,
            ).valor
            for k in K_MEDIDOS
        }
        for nombre, traido in (
            ("solo_vectorial", solo_vector),
            ("solo_lexico", solo_lexico),
            ("fusion" + ("_y_reordenador" if con_reranker else ""), recuperado),
        )
    }
    return medidas


def main() -> int:
    import psycopg

    casos = [
        CasoGolden.model_validate_json(linea)
        for linea in GOLDEN.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]
    puerto = os.environ.get("CITEBOUND_PG_PORT", "5434")
    url = os.environ.get(
        "CITEBOUND_PG_URL", f"postgresql://citebound:citebound@localhost:{puerto}/citebound"
    )

    # Con reordenador **por defecto**, y desactivarlo es lo que hay que pedir. `G-RECALL5` se
    # llama literalmente «Recall de articulo en top-5 tras rerank» y su valor lo lee el gate de
    # este informe: con el reordenador detrás de una variable, un `make eval-retrieval` a secas
    # escribía el número de antes de reordenar y el gate lo daba por bueno. `=0` queda para
    # diagnosticar —separar culpa del recuperador y del reordenador— y entonces el informe lo
    # dice en `con_reranker`.
    con_reranker = os.environ.get("CITEBOUND_RERANK", "1") != "0"
    # Qué modelo reordenó, en el informe. Sin esto, dos corridas con reordenadores distintos
    # producen informes indistinguibles — y el 2026-08-17 lancé el 9B con una variable de
    # entorno que no existe: habría medido el 4B otra vez y publicado «9B» al lado.
    modelo_reordenador = (
        (
            generador_por_defecto().model
            if os.environ.get("CITEBOUND_RERANK_LLM") == "1"
            else reordenador_por_defecto().modelo
        )
        if con_reranker
        else None
    )
    arranque = time.monotonic()
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        # El contrato compartido lo pone en OBLIGATORIO (`chunks-ddl.sql`, sección final):
        # todo informe registra el DESTINO FÍSICO RESUELTO, nunca el alias. Con el alias
        # solo, dos corridas sobre datos distintos producirían informes idénticos.
        index_version, physical_table = indice_activo(cur)
        medidas = medir(cur, casos, con_reranker=con_reranker)
    total = time.monotonic() - arranque

    INFORME.parent.mkdir(parents=True, exist_ok=True)
    INFORME.write_text(
        json.dumps(
            {
                # `value` es la lectura **a nivel de artículo**, que es la que decidió Samuel
                # en Q-016 (A) y la que lee el gate. Las dos siguen publicadas al lado: la
                # honestidad no está en elegir el número bueno, está en enseñar los dos y
                # decir cuál se publica y por qué.
                "metrics": [
                    {
                        "id": f"G-RECALL{k}",
                        "value": medidas[f"G-RECALL{k}"]["a_nivel_articulo"],  # type: ignore[index,call-overload]
                        **medidas[f"G-RECALL{k}"],  # type: ignore[dict-item]
                    }
                    for k in K_MEDIDOS
                ],
                "n_casos": medidas["n_casos"],
                "segundos": round(total, 1),
                "index_version": index_version,
                "physical_table": physical_table,
                "con_reranker": con_reranker,
                "modelo_reordenador": modelo_reordenador,
                "por_canal": medidas["por_canal"],
                "lectura_publicada": "a_nivel_articulo (Q-016 A)",
                "nota": (
                    "Dos lecturas: `estricto` compara legal_ref literalmente y "
                    "`a_nivel_articulo` recorta el apartado del golden set. El troceador es "
                    "articulo-v1, así que ninguna ref indexada lleva apartado y el 86 % de las "
                    "del golden set sí: con la lectura estricta el recall está acotado por "
                    "construcción. Cuál se publica como G-RECALL es decisión de Samuel."
                ),
            },
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"{medidas['n_casos']} casos positivos · {total:.1f} s "
        f"(vectorizar: {medidas['segundos_embedding']} s)"
    )
    for k in K_MEDIDOS:
        m = medidas[f"G-RECALL{k}"]
        print(
            f"  G-RECALL{k:<2}  estricto {m['estricto']:.3f}   "  # type: ignore[index,call-overload]
            f"a nivel de artículo {m['a_nivel_articulo']:.3f}"
        )  # type: ignore[index,call-overload]
    print(f"\ninforme en {INFORME.relative_to(RAIZ)}")
    if total > 90:
        print(f"OJO: {total:.0f} s supera el presupuesto de 90 s de RULES §3.3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
