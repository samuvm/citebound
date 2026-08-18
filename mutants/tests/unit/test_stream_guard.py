"""`agent/stream_guard.py` · el guardia que corta **en el token**, no al final.

La diferencia no es de rendimiento, es de promesa. Un filtro sobre la respuesta ya escrita
detecta lo mismo, pero para entonces el usuario ya está leyendo una respuesta que va a
retirarse. Cortar en el token en que aparece `[[REF:9]]` es lo que permite decir que el sistema
**no puede** emitir una referencia inexistente, en vez de que la retira deprisa.

`docs/RULES.md` §3.2 exige dos propiedades aquí y las dos están abajo con Hypothesis:
todo prefijo de un stream válido se acepta, y todo stream con `n∉{1..5}` se rechaza en el token
en que aparece.

`RULES` §3.1 pone `agent/` en TDD **prohibido** salvo este fichero, que lo **exige**: es el
único del paquete que es lógica pura con respuesta correcta.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from citebound.agent.stream_guard import (
    Estado,
    StreamGuard,
    trocear_en_tokens,
)

MAX = 5


def alimentar(guardia: StreamGuard, texto: str) -> Estado:
    """Le pasa el texto token a token, como llegaría por SSE."""
    estado = Estado.ABIERTO
    for token in trocear_en_tokens(texto):
        estado = guardia.consumir(token)
        if estado is Estado.RETRACTADO:
            break
    return estado


# ======================================================================================
# Lo que pasa y lo que no
# ======================================================================================


def test_un_texto_sin_huecos_se_acepta_entero() -> None:
    assert alimentar(StreamGuard(MAX), "No se puede adelantar en un cambio de rasante.") is (
        Estado.ABIERTO
    )


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_un_hueco_dentro_del_rango_se_acepta(n: int) -> None:
    assert alimentar(StreamGuard(MAX), f"Según [[REF:{n}]] no se puede.") is Estado.ABIERTO


@pytest.mark.parametrize("n", [0, 6, 9, 47, 100])
def test_un_hueco_fuera_del_rango_retracta(n: int) -> None:
    assert alimentar(StreamGuard(MAX), f"Según [[REF:{n}]] no se puede.") is Estado.RETRACTADO


def test_el_rango_lo_fija_lo_recuperado_y_no_la_plantilla() -> None:
    """Con dos fuentes recuperadas, `[[REF:3]]` es inválido **aunque** el prompt permita
    escribir hasta el 5. Es la misma regla que `domain.citation.resolver`, y tenerla en los dos
    sitios sería tenerla en ninguno: los dos leen el mismo número."""
    assert alimentar(StreamGuard(2), "Según [[REF:3]] sí.") is Estado.RETRACTADO
    assert alimentar(StreamGuard(2), "Según [[REF:2]] sí.") is Estado.ABIERTO


def test_sin_fuentes_ningun_hueco_vale() -> None:
    assert alimentar(StreamGuard(0), "Según [[REF:1]] sí.") is Estado.RETRACTADO


# ======================================================================================
# **En el token**, que es la razón de ser del módulo
# ======================================================================================


def test_retracta_en_el_token_del_hueco_y_no_al_final() -> None:
    """El test que define el módulo. Se cuentan los tokens consumidos: si retractara al final,
    los habría consumido todos."""
    guardia = StreamGuard(MAX)
    tokens = trocear_en_tokens("Uno dos tres [[REF:9]] cuatro cinco seis siete.")
    consumidos = 0
    for token in tokens:
        consumidos += 1
        if guardia.consumir(token) is Estado.RETRACTADO:
            break
    assert guardia.estado is Estado.RETRACTADO
    assert consumidos < len(tokens), "consumió el stream entero: retractó al final, no en el token"


def test_lo_emitido_antes_del_hueco_malo_esta_disponible() -> None:
    """Retractar no es olvidar: el nodo de reintento necesita saber qué se había emitido para
    no repetirlo, y la traza necesita poder enseñarlo."""
    guardia = StreamGuard(MAX)
    alimentar(guardia, "El artículo dice [[REF:9]] y más cosas.")
    assert guardia.emitido.startswith("El artículo dice")
    assert "[[REF:9]]" not in guardia.emitido


def test_un_hueco_partido_entre_dos_tokens_se_detecta_igual() -> None:
    """**El caso que un `if "[[REF:" in token` se comería.** Un modelo emite `[[RE`, `F:9]]`
    en dos tokens, y el hueco no está entero en ninguno. El guardia acumula."""
    guardia = StreamGuard(MAX)
    for trozo in ("Según ", "[[RE", "F:", "9", "]]", " no se puede."):
        if guardia.consumir(trozo) is Estado.RETRACTADO:
            break
    assert guardia.estado is Estado.RETRACTADO


def test_un_hueco_valido_partido_entre_tokens_no_retracta() -> None:
    guardia = StreamGuard(MAX)
    for trozo in ("Según ", "[[RE", "F:", "3", "]]", " no se puede."):
        guardia.consumir(trozo)
    assert guardia.estado is Estado.ABIERTO


def test_un_hueco_de_dos_digitos_no_se_confunde_con_uno_de_uno() -> None:
    """`[[REF:12]]` no es `[[REF:1]]` seguido de un `2`. Leer el primer dígito y decidir daría
    por bueno un 12 con cinco fuentes."""
    assert alimentar(StreamGuard(MAX), "Según [[REF:12]] sí.") is Estado.RETRACTADO


def test_retractado_es_absorbente() -> None:
    """Una vez retractado, nada lo reabre. Si un token posterior pudiera devolverlo a abierto,
    la respuesta saldría con el hueco malo dentro."""
    guardia = StreamGuard(MAX)
    alimentar(guardia, "Malo [[REF:9]].")
    assert guardia.consumir(" texto perfectamente normal") is Estado.RETRACTADO
    assert guardia.consumir("[[REF:1]]") is Estado.RETRACTADO


def test_tras_retractar_no_queda_nada_pendiente() -> None:
    """Si el guardia retuviera algo tras retractar, existiría un camino por el que el hueco malo
    —o lo que venía detrás— acaba saliendo. La garantía es que no lo hay."""
    guardia = StreamGuard(MAX)
    alimentar(guardia, "Texto [[REF:9]] y una cola larga que no debe salir.")
    assert guardia.estado is Estado.RETRACTADO
    assert guardia.pendiente == ""


def test_lo_pendiente_es_siempre_un_prefijo_de_hueco_y_no_texto_normal() -> None:
    """Retener texto que ya no puede llegar a ser un hueco sería un token que el usuario no ve
    sin motivo, y en un stream eso se nota."""
    guardia = StreamGuard(MAX)
    guardia.consumir("Un texto normal y corriente")
    assert guardia.pendiente == ""
    guardia.consumir(" [[RE")
    assert guardia.pendiente == "[[RE"


def test_las_citas_vistas_se_recogen_en_orden() -> None:
    """El verificador necesita saber qué huecos usó el modelo y en qué orden, y sacarlo del
    texto ya emitido sería parsearlo dos veces."""
    guardia = StreamGuard(MAX)
    alimentar(guardia, "Primero [[REF:2]], luego [[REF:1]], y otra vez [[REF:2]].")
    assert guardia.huecos == (2, 1, 2)


# ======================================================================================
# Propiedades obligatorias · docs/RULES.md §3.2
# ======================================================================================


@given(
    st.lists(st.integers(min_value=1, max_value=MAX), min_size=0, max_size=6),
    st.text(alphabet="abc ", max_size=12),
)
def test_propiedad_todo_prefijo_de_un_stream_valido_se_acepta(
    huecos: list[int], relleno: str
) -> None:
    """**Propiedad exigida.** Si el stream entero es válido, ningún prefijo suyo puede
    retractar — porque retractar a mitad de algo que iba a estar bien es un falso positivo que
    el usuario vive como una respuesta perdida."""
    texto = relleno.join(f"[[REF:{n}]]" for n in huecos) or relleno
    tokens = trocear_en_tokens(texto)
    for corte in range(len(tokens) + 1):
        guardia = StreamGuard(MAX)
        for token in tokens[:corte]:
            guardia.consumir(token)
        assert guardia.estado is Estado.ABIERTO


@given(
    st.text(alphabet="abc ", max_size=10),
    st.integers(min_value=MAX + 1, max_value=999),
    st.text(alphabet="abc ", max_size=10),
)
def test_propiedad_un_hueco_fuera_de_rango_retracta_en_su_token(
    antes: str, malo: int, despues: str
) -> None:
    """**Propiedad exigida.** No solo que retracte: que retracte **en el token en que aparece**.

    Se comprueba contra el índice exacto del token que cierra el hueco, y no contra «quedan
    tokens sin leer». Esa formulación era más débil y además falsa en un caso legítimo que
    encontró Hypothesis: con `[[REF:6]]a` sin espacios, el hueco y lo que viene detrás caen en
    el **mismo** token, así que no queda nada por leer y no por haber leído de más.
    """
    texto = f"{antes}[[REF:{malo}]]{despues}"
    tokens = trocear_en_tokens(texto)
    # En qué token termina el hueco: el primero cuyo prefijo acumulado ya lo contiene entero.
    fin_del_hueco = texto.index("]]", texto.index("[[REF:")) + 2
    acumulado, cierra_en = 0, len(tokens) - 1
    for i, token in enumerate(tokens):
        acumulado += len(token)
        if acumulado >= fin_del_hueco:
            cierra_en = i
            break

    guardia = StreamGuard(MAX)
    leidos = 0
    for token in tokens:
        leidos += 1
        if guardia.consumir(token) is Estado.RETRACTADO:
            break
    assert guardia.estado is Estado.RETRACTADO
    assert leidos == cierra_en + 1, (
        f"retractó en el token {leidos} y el hueco cerraba en el {cierra_en + 1}"
    )


@given(st.text(max_size=80))
def test_propiedad_ningun_texto_arbitrario_revienta_el_guardia(texto: str) -> None:
    """El guardia recibe lo que el modelo emita, incluido lo que nadie previó. Reventar aquí
    dejaría la petición sin respuesta y sin motivo."""
    guardia = StreamGuard(MAX)
    for token in trocear_en_tokens(texto):
        guardia.consumir(token)
    assert guardia.estado in (Estado.ABIERTO, Estado.RETRACTADO)
