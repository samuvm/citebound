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
    cur: object, casos: Sequence[CasoGolden], *, k_canal: int = 30, con_reranker: bool = False
) -> dict[str, object]:
    """Recupera para cada caso positivo y devuelve las dos lecturas del recall."""
    positivos = [c for c in casos if c.tipo is Tipo.POSITIVO and c.refs]
    cache = CacheJuicios(CACHE_RERANK) if con_reranker else None
    reordenador = ReordenadorLLM(generador_por_defecto(), cache=cache) if con_reranker else None
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
            k=k_canal,
            k_canal=k_canal,
            reordenador=reordenador,
        )
        recuperado[caso.id] = [r.ref for r in traidos]
        # Los canales sueltos, para que la tabla del README salga del artefacto medido y no
        # de un script aparte que puede quedarse viejo sin que nada lo note. No cuestan LLM.
        solo_vector[caso.id] = [
            r.ref
            for r in vector_mod.buscar(cur, caso.pregunta, embedder=precalculado, k=k_canal)  # type: ignore[arg-type]
        ]
        solo_lexico[caso.id] = [r.ref for r in lexical.buscar(cur, caso.pregunta, k=k_canal)]  # type: ignore[arg-type]

    # Lectura a nivel de artículo: se recorta el golden set, no lo recuperado. Recortar lo
    # recuperado sería lo mismo aquí (el índice ya viene sin apartado) pero dejaría de serlo
    # el día que el troceado baje al apartado, y entonces la métrica cambiaría en silencio.
    por_articulo = [
        c.model_copy(update={"refs": [a_nivel_articulo(r) for r in c.refs]}) for c in positivos
    ]

    if cache is not None:
        cache.volcar()

    medidas: dict[str, object] = {
        "n_casos": len(positivos),
        "segundos_embedding": round(t_embed, 1),
    }
    for k in K_MEDIDOS:
        estricto = recall_at_k(positivos, recuperado, k)
        articulo = recall_at_k(por_articulo, recuperado, k)
        medidas[f"G-RECALL{k}"] = {
            "estricto": estricto.valor,
            "a_nivel_articulo": articulo.valor,
            "n": estricto.n,
        }
    medidas["por_canal"] = {
        nombre: {f"recall{k}": recall_at_k(por_articulo, traido, k).valor for k in K_MEDIDOS}
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

    con_reranker = os.environ.get("CITEBOUND_RERANK") == "1"
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
