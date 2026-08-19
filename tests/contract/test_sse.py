"""El contrato SSE, contra un *snapshot*. `RULES` §3.1 pide esto en vez de TDD para `api/`.

Lo que un *snapshot* protege aquí no es el formato por el formato: es que **el orden de los
eventos no cambie sin que nadie lo decida**. `sources` va primero porque llega mucho antes que
el modelo y es lo primero que el usuario puede ver; `citations` va al final porque hasta
entonces no están verificadas. Adelantarlas sería prometer una verificación que aún no ocurrió,
y es el tipo de cambio que se cuela en un refactor.
"""

from __future__ import annotations

import json

from citebound.agent.graph import Resultado
from citebound.api.sse import Evento, Latencias, eventos, formatear, secuencia
from citebound.domain.citation import Cita, Fuente, Motivo
from citebound.domain.legalref import parse
from citebound.domain.retry import Curso, Salida

NORMA = "RD-1428/2003"
ART34 = Fuente(ref=parse(f"{NORMA}#art34"), texto="Artículo 34. Cómputo de carriles.\n1. Texto.")
ART35 = Fuente(ref=parse(f"{NORMA}#art35"), texto="Artículo 35. Separación lateral.\n1. Texto.")
LAT = Latencias(ttfs_ms=531.4, ttft_ms=1187.9, por_etapa={"embedding": 38.2, "busqueda": 91.7})

COMUNES = {
    "latencias": LAT,
    "index_version": "v1-qwen3-embedding-0.6b-1024",
    "physical_table": "chunk_v1",
    "modelo": "qwen3.5:4b-mlx",
    "prompt_id": "responder",
    "prompt_version": 1,
}


def respondido() -> Resultado:
    return Resultado(
        curso=Curso(salida=Salida.RESPONDER, reintentos=0, refs=(ART34.ref,)),
        respuesta="Se cuentan de derecha a izquierda [[REF:1]].",
        citas=(Cita(n=1, quote="Texto"),),
        fuentes=(ART34, ART35),
    )


def abstenido() -> Resultado:
    return Resultado(
        curso=Curso(salida=Salida.ABSTENERSE, reintentos=2, motivo=Motivo.QUOTE_NO_LITERAL),
        fuentes=(ART34,),
    )


def nombres(resultado: Resultado) -> list[str]:
    return [e.value for e, _ in eventos(resultado, **COMUNES)]


# --------------------------------------------------------------------------------------
# El orden, que es lo que el snapshot protege
# --------------------------------------------------------------------------------------


def test_una_respuesta_emite_los_eventos_del_contrato_en_su_orden() -> None:
    assert nombres(respondido()) == ["sources", "token", "citations", "done"]


def test_una_abstencion_no_emite_ni_token_ni_citations() -> None:
    """Abstenerse es una salida de primera clase, no un `token` vacío. Emitir uno haría que el
    cliente creyera que hay respuesta."""
    assert nombres(abstenido()) == ["sources", "retract", "retract", "abstain", "done"]


def test_las_citas_van_despues_del_token_y_nunca_antes() -> None:
    """Hasta el final no están verificadas. Adelantarlas prometería una verificación que aún
    no ha ocurrido, y es el cambio que se cuela en un refactor."""
    orden = nombres(respondido())
    assert orden.index("citations") > orden.index("token")


def test_sources_es_siempre_el_primero() -> None:
    """Llega mucho antes que el modelo: es lo primero que el usuario puede ver, y de ahí que
    `TTFS` se publique aparte."""
    for resultado in (respondido(), abstenido()):
        assert nombres(resultado)[0] == "sources"


def test_hay_un_retract_por_cada_reintento() -> None:
    """Esconderlos dejaría al usuario sin saber que el sistema se corrigió, que es justo lo
    que lo distingue de uno que no verifica."""
    assert nombres(abstenido()).count("retract") == 2
    assert nombres(respondido()).count("retract") == 0


# --------------------------------------------------------------------------------------
# El contenido que el contrato exige
# --------------------------------------------------------------------------------------


def test_done_publica_las_dos_latencias_y_no_solo_una() -> None:
    """Medir el `TTFT` hasta `sources` sería hacer trampa: `sources` sale antes de que el
    modelo hable. Por eso viajan las dos y el README lo dice."""
    datos = dict(eventos(respondido(), **COMUNES))[Evento.DONE]
    assert datos["latencias_ms"]["ttfs"] == 531.4
    assert datos["latencias_ms"]["ttft"] == 1187.9
    assert datos["latencias_ms"]["ttft"] > datos["latencias_ms"]["ttfs"]


def test_done_publica_la_latencia_por_etapa() -> None:
    """`RULES` §2.1 reparte 1.290 ms entre etapas: una fuera de su presupuesto marca ámbar
    aunque el total pase, y publicar solo el total escondería justo eso."""
    datos = dict(eventos(respondido(), **COMUNES))[Evento.DONE]
    assert datos["latencias_ms"]["embedding"] == 38.2
    assert datos["latencias_ms"]["busqueda"] == 91.7


def test_done_publica_la_procedencia_entera() -> None:
    """Índice físico resuelto, modelo y prompt con su versión. Sin esto, dos trazas de dos
    configuraciones distintas serían indistinguibles."""
    datos = dict(eventos(respondido(), **COMUNES))[Evento.DONE]
    for clave in ("index_version", "physical_table", "modelo", "prompt_id", "prompt_version"):
        assert datos[clave], clave


def test_las_citas_llevan_su_referencia_resuelta_y_no_el_hueco() -> None:
    """El hueco es lo que escribió el modelo; la referencia la puso el código. El cliente
    recibe las dos y puede comprobarlo."""
    datos = dict(eventos(respondido(), **COMUNES))[Evento.CITATIONS]
    assert datos["citas"] == [{"n": 1, "legal_ref": f"{NORMA}#art34", "quote": "Texto"}]


def test_sources_no_manda_el_texto_entero_del_articulo() -> None:
    """Es el primer evento y compite con el presupuesto de `TTFS`. El usuario necesita saber
    sobre qué se le responde, no leer el artículo."""
    datos = dict(eventos(respondido(), **COMUNES))[Evento.SOURCES]
    assert datos["fuentes"][0]["titulo"] == "Artículo 34. Cómputo de carriles."
    assert "1. Texto." not in json.dumps(datos)


def test_la_abstencion_lleva_su_motivo_tipado() -> None:
    datos = dict(eventos(abstenido(), **COMUNES))[Evento.ABSTAIN]
    assert datos["motivo"] == "quote_no_literal"
    assert datos["reintentos"] == 2


# --------------------------------------------------------------------------------------
# La serialización
# --------------------------------------------------------------------------------------


def test_el_formato_es_el_del_estandar_sse() -> None:
    assert formatear(Evento.TOKEN, {"a": 1}) == 'event: token\ndata: {"a": 1}\n\n'


def test_las_tildes_no_se_escapan() -> None:
    """El corpus es español y escapar las tildes hace ilegible la traza."""
    assert "artículo" in formatear(Evento.TOKEN, {"t": "artículo"})


def test_las_claves_salen_ordenadas() -> None:
    """Un orden estable es lo que permite comparar dos ejecuciones byte a byte, que es lo que
    `G-EVAL-DET` exigirá en la fase 4."""
    assert formatear(Evento.DONE, {"z": 1, "a": 2}).index('"a"') < formatear(
        Evento.DONE, {"z": 1, "a": 2}
    ).index('"z"')


def test_la_secuencia_completa_se_puede_comparar_byte_a_byte() -> None:
    """Dos veces la misma entrada dan exactamente el mismo flujo."""
    pares = list(eventos(respondido(), **COMUNES))
    assert secuencia(pares) == secuencia(list(eventos(respondido(), **COMUNES)))
    assert secuencia(pares).count("\n\n") == len(pares)
