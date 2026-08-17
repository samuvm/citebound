"""Unit tests for `citebound.retrieval.rerank` — la parte que no es el modelo.

`RULES` §3 pone `retrieval/rerank` en «se mide, no se testea unitariamente»: su **calidad** es
una distribución sobre un corpus y la juzga `make eval-retrieval`. Pero alrededor del modelo
hay lógica pura que sí tiene respuesta correcta, y que si falla lo hace en silencio:

  · **el parseo**, porque un modelo puede escribir cualquier cosa y perder un candidato bajaría
    el recall sin que nada apunte al reordenador;
  · **la clave de caché**, porque una clave de menos reutiliza el juicio equivocado y una de
    más lo tira todo en cada corrida.
"""

from __future__ import annotations

import json
from pathlib import Path

from citebound.domain.legalref import parse
from citebound.providers.chat import Respuesta
from citebound.retrieval.rerank import (
    PEDIDOS,
    PROMPT_VERSION,
    CacheJuicios,
    ReordenadorLLM,
    clave_de,
    etiquetas,
    ordenar_por_etiquetas,
)
from citebound.retrieval.vector import Recuperado

NORMA = "RD-1428/2003"


def cand(articulo: str) -> Recuperado:
    return Recuperado(
        ref=parse(f"{NORMA}#art{articulo}"),
        content=f"texto del {articulo}",
        distancia=0.5,
        titulo="TÍTULO II",
        id_norma_version="BOE-A-2003-23514",
    )


CANDIDATOS = [cand("82"), cand("85"), cand("87")]


# --------------------------------------------------------------------------------------
# El parseo: nunca pierde, nunca inventa
# --------------------------------------------------------------------------------------


def test_el_orden_que_dice_el_modelo_es_el_que_se_aplica() -> None:
    assert [str(r.ref) for r in ordenar_por_etiquetas("AC, AA, AB", CANDIDATOS)] == [
        f"{NORMA}#art87",
        f"{NORMA}#art82",
        f"{NORMA}#art85",
    ]


def test_un_candidato_que_el_modelo_no_nombra_no_se_pierde() -> None:
    """**Lo que más importa de este módulo.** Si el reordenador perdiera documentos, el recall
    bajaría por su culpa y el diagnóstico apuntaría al índice o al troceado, que es donde no
    está el problema. Los que no nombra van detrás, en su orden original."""
    ordenados = ordenar_por_etiquetas("AB", CANDIDATOS)
    assert len(ordenados) == 3
    assert [str(r.ref) for r in ordenados] == [f"{NORMA}#art85", f"{NORMA}#art82", f"{NORMA}#art87"]


def test_una_etiqueta_fuera_de_rango_se_ignora() -> None:
    """El modelo puede escribir `ZZ` con tres candidatos. Eso no puede reventar ni desplazar
    nada: se descarta y ya."""
    assert len(ordenar_por_etiquetas("ZZ, QQ, AB", CANDIDATOS)) == 3
    assert str(ordenar_por_etiquetas("ZZ, QQ, AB", CANDIDATOS)[0].ref) == f"{NORMA}#art85"


def test_una_etiqueta_repetida_cuenta_una_vez() -> None:
    assert len(ordenar_por_etiquetas("AA, AA, AA", CANDIDATOS)) == 3


def test_una_respuesta_sin_numeros_deja_el_orden_como_estaba() -> None:
    """Si el modelo contesta «no lo sé», el orden de la fusión es mejor que ninguno."""
    assert ordenar_por_etiquetas("no estoy seguro", CANDIDATOS) == CANDIDATOS


def test_una_respuesta_vacia_deja_el_orden_como_estaba() -> None:
    assert ordenar_por_etiquetas("", CANDIDATOS) == CANDIDATOS


def test_las_etiquetas_se_leen_aunque_vengan_con_texto_alrededor() -> None:
    """Aunque el prompt pida solo etiquetas, un modelo instruido se explica igual. Cazarlas
    donde estén es más barato que pelearse con el prompt."""
    assert str(ordenar_por_etiquetas("El más relevante es AC, luego AA.", CANDIDATOS)[0].ref) == (
        f"{NORMA}#art87"
    )


def test_un_numero_de_articulo_en_la_respuesta_ya_no_puede_confundirse_con_un_candidato() -> None:
    """**El fallo que obligó a cambiar de números a letras** (2026-08-17).

    Con candidatos numerados, `gs-0199` recibió del modelo `108,75,24`: el número del
    **artículo**, no el del candidato. El parseo tiró 108 y 75 por fuera de rango y se quedó
    con un 24 que no significaba nada, así que el reordenado fue ruido con pinta de decisión.

    Con etiquetas de dos letras la confusión no se detecta: **no se puede escribir.**
    """
    assert ordenar_por_etiquetas("108, 75, 24", CANDIDATOS) == CANDIDATOS


def test_las_etiquetas_son_estables_y_del_tamano_pedido() -> None:
    assert etiquetas(3) == ["AA", "AB", "AC"]
    assert etiquetas(30)[-1] == "BD"
    assert len(set(etiquetas(30))) == 30


def test_se_piden_los_mismos_cinco_de_la_cita_cerrada() -> None:
    """Si `PEDIDOS` y el `n` de `[[REF:n]]` se separaran, el reordenador estaría decidiendo
    sobre un conjunto distinto del que verá el generador."""
    assert PEDIDOS == 5


# --------------------------------------------------------------------------------------
# La clave de caché: ni de menos ni de más
# --------------------------------------------------------------------------------------


def test_la_misma_pregunta_y_los_mismos_candidatos_dan_la_misma_clave() -> None:
    assert clave_de("¿por dónde?", CANDIDATOS, "m") == clave_de("¿por dónde?", CANDIDATOS, "m")


def test_otro_orden_de_candidatos_es_otro_juicio() -> None:
    """Reordenar una lista distinta **es otra pregunta**: el modelo ve los candidatos numerados
    y su respuesta depende de qué número tiene cada uno."""
    assert clave_de("q", CANDIDATOS, "m") != clave_de("q", list(reversed(CANDIDATOS)), "m")


def test_otro_modelo_es_otro_juicio() -> None:
    assert clave_de("q", CANDIDATOS, "qwen") != clave_de("q", CANDIDATOS, "gemma")


def test_otra_pregunta_es_otro_juicio() -> None:
    assert clave_de("a", CANDIDATOS, "m") != clave_de("b", CANDIDATOS, "m")


def test_la_version_del_prompt_forma_parte_de_la_clave() -> None:
    """Un juicio emitido con otro prompt es un juicio sobre otra pregunta. Sin esto, cambiar
    la plantilla dejaría la caché llena de respuestas a una pregunta que ya no se hace — y el
    informe diría que midió con el prompt nuevo."""
    material = clave_de("q", CANDIDATOS, "m")
    import citebound.retrieval.rerank as modulo

    original = modulo.PROMPT_VERSION
    try:
        modulo.PROMPT_VERSION = original + 1
        assert clave_de("q", CANDIDATOS, "m") != material
    finally:
        modulo.PROMPT_VERSION = original
    assert PROMPT_VERSION >= 1


# --------------------------------------------------------------------------------------
# La caché
# --------------------------------------------------------------------------------------


def test_la_cache_devuelve_lo_guardado(tmp_path: Path) -> None:
    cache = CacheJuicios(tmp_path / "c.json")
    cache.guardar("k", ["a", "b"])
    assert cache.obtener("k") == ["a", "b"]


def test_una_clave_que_no_esta_es_none(tmp_path: Path) -> None:
    assert CacheJuicios(tmp_path / "c.json").obtener("no-existe") is None


def test_la_cache_sobrevive_al_disco(tmp_path: Path) -> None:
    """Es el punto entero: la primera corrida paga el modelo y las siguientes son gratis y
    deterministas, que es lo que `G-EVAL-DET` va a exigir en la fase 4."""
    ruta = tmp_path / "c.json"
    primera = CacheJuicios(ruta)
    primera.guardar("k", ["a"])
    primera.volcar()
    assert CacheJuicios(ruta).obtener("k") == ["a"]


def test_la_cache_se_escribe_ordenada_y_estable(tmp_path: Path) -> None:
    """Se versiona en el repo: si el orden de las claves bailara, cada corrida produciría un
    diff enorme y nadie volvería a mirarlo."""
    ruta = tmp_path / "c.json"
    cache = CacheJuicios(ruta)
    for clave in ("z", "a", "m"):
        cache.guardar(clave, ["x"])
    cache.volcar()
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    assert list(contenido) == sorted(contenido)


# --------------------------------------------------------------------------------------
# El reordenador entero
# --------------------------------------------------------------------------------------


class _Guion:
    """Un `Generador` que contesta lo que se le diga, en orden, y cuenta las llamadas."""

    model = "de-mentira"

    def __init__(self, respuestas: list[str]) -> None:
        self._respuestas = list(respuestas)
        self.llamadas = 0

    def completar(self, prompt: str, *, max_tokens: int = 0) -> Respuesta:
        self.llamadas += 1
        return Respuesta(self._respuestas.pop(0) if self._respuestas else "", self.model, "", 1)


def treinta() -> list[Recuperado]:
    return [cand(str(i)) for i in range(1, 31)]


def test_una_sola_llamada_con_los_treinta_delante() -> None:
    """El reordenado por ventanas —cuatro llamadas— se midió y salió peor: 0,806 contra 0,852.
    Que el número de llamadas esté fijado por un test no es un detalle interno: multiplica el
    coste de `make eval-retrieval` en frío y entra entero en el presupuesto de `G-TTFT`."""
    guion = _Guion(["AA, AB, AC, AD, AE"])
    ReordenadorLLM(guion, tope=30).reordenar("¿por dónde?", treinta())
    assert guion.llamadas == 1


def test_no_pierde_ni_duplica_un_solo_candidato() -> None:
    """**Lo que no puede fallar.** Perder un documento bajaría el recall por culpa del
    reordenador mientras el diagnóstico apuntaría al índice, que es donde no estaría el
    problema. `recall@30` se mide sobre esta misma lista."""
    candidatos = treinta()
    salida = ReordenadorLLM(_Guion(["AB, AD, AF"]), tope=30).reordenar("q", candidatos)
    assert len(salida) == len(candidatos)
    assert {str(r.ref) for r in salida} == {str(r.ref) for r in candidatos}


def test_un_modelo_mudo_deja_el_orden_de_la_fusion() -> None:
    """Si el modelo no contesta, el orden de la fusión es mejor que ninguno — y sobre todo,
    no es un orden **peor** que el de partida. Solo se adelanta lo que el modelo nombra."""
    candidatos = treinta()
    salida = ReordenadorLLM(_Guion([""]), tope=30).reordenar("q", candidatos)
    assert [str(r.ref) for r in salida] == [str(r.ref) for r in candidatos]


def test_lo_que_queda_fuera_del_tope_no_se_toca_ni_se_pierde() -> None:
    candidatos = [*treinta(), cand("99")]
    salida = ReordenadorLLM(_Guion(["AA, AB, AC"]), tope=30).reordenar("q", candidatos)
    assert len(salida) == 31
    assert str(salida[-1].ref) == f"{NORMA}#art99"
