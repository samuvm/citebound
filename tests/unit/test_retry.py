"""`domain/retry.py` · qué hacer cuando la verificación dice que no.

El contrato SSE (`docs/RULES.md` §2.2) fija las salidas: `retract` dispara un reintento acotado
a dos, y `abstain` es **salida de primera clase**, no un error disfrazado. Este módulo es la
máquina de estados que decide entre las tres, y es puro a propósito: la decisión de abstenerse
no puede depender de si el proveedor estaba lento.

**Por qué abstenerse tiene que ser barato de elegir y caro de abusar.** `G-ABST-FP` (abstenerse
habiendo respuesta, ≤ 0,05) y `G-ABST-FN` (responder sin haberla, ≤ 0,10) son una **pareja
atómica**: medidas por separado, la forma óptima de aprobar cualquiera de las dos es hacer
trampa. Callarse siempre da un `G-CITA-PRECISION` de 1,00 sobre cero respuestas.

`docs/RULES.md` §3.2 exige tres propiedades aquí y las tres están abajo: termina siempre, nunca
más de dos reintentos, y `ABSTENERSE` es absorbente.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from citebound.domain.citation import Motivo, Veredicto
from citebound.domain.legalref import parse
from citebound.domain.retry import (
    MAX_REINTENTOS,
    UMBRAL_RELEVANCIA,
    Curso,
    Salida,
    decidir,
    resolver_curso,
)

REF = parse("RD-1428/2003#art34")
BIEN = Veredicto(ok=True, refs=(REF,))
MAL = Veredicto(ok=False, motivo=Motivo.QUOTE_NO_LITERAL)
FUERA = Veredicto(ok=False, motivo=Motivo.FUERA_DE_RANGO)
SIN_CITAS = Veredicto(ok=False, motivo=Motivo.SIN_CITAS)


# ======================================================================================
# La decisión, caso a caso
# ======================================================================================


def test_una_verificacion_buena_responde() -> None:
    assert decidir(BIEN, reintentos_hechos=0, hay_fuentes=True) is Salida.RESPONDER


def test_una_verificacion_buena_responde_aunque_se_haya_reintentado() -> None:
    """El reintento existe para llegar aquí. Si el segundo intento verifica, sale."""
    assert decidir(BIEN, reintentos_hechos=MAX_REINTENTOS, hay_fuentes=True) is Salida.RESPONDER


@pytest.mark.parametrize("veredicto", [MAL, FUERA, SIN_CITAS])
def test_una_verificacion_mala_con_presupuesto_reintenta(veredicto: Veredicto) -> None:
    assert decidir(veredicto, reintentos_hechos=0, hay_fuentes=True) is Salida.REINTENTAR


def test_agotado_el_presupuesto_se_abstiene_y_no_se_responde_igual() -> None:
    """**El test que sostiene la tesis.** Sin esto la salida natural del código sería emitir el
    último borrador «porque es lo que hay», y eso es exactamente el RAG que este proyecto no
    quiere ser: una respuesta que no verificó, presentada como si lo hubiera hecho."""
    assert decidir(MAL, reintentos_hechos=MAX_REINTENTOS, hay_fuentes=True) is Salida.ABSTENERSE


def test_sin_fuentes_se_abstiene_sin_gastar_un_solo_reintento() -> None:
    """Si la búsqueda no trajo nada, el modelo no puede citar lo que no existe: reintentar es
    pagar latencia por un resultado que ya se conoce. Y `G-TTFT` no perdona dos llamadas."""
    assert decidir(SIN_CITAS, reintentos_hechos=0, hay_fuentes=False) is Salida.ABSTENERSE
    assert decidir(BIEN, reintentos_hechos=0, hay_fuentes=False) is Salida.ABSTENERSE


def test_un_contador_negativo_se_rechaza() -> None:
    """No puede pasar, y por eso mismo revienta aquí en vez de convertirse en reintentos
    infinitos aguas abajo."""
    with pytest.raises(ValueError, match="reintentos"):
        decidir(MAL, reintentos_hechos=-1, hay_fuentes=True)


# ======================================================================================
# El curso completo · lo que ve el grafo
# ======================================================================================


def test_el_primer_intento_bueno_responde_sin_reintentos() -> None:
    curso = resolver_curso([BIEN])
    assert curso == Curso(salida=Salida.RESPONDER, reintentos=0, refs=(REF,))


def test_el_segundo_intento_bueno_responde_con_un_reintento() -> None:
    curso = resolver_curso([MAL, BIEN])
    assert curso.salida is Salida.RESPONDER
    assert curso.reintentos == 1
    assert curso.refs == (REF,)


def test_tres_intentos_malos_se_abstienen_con_el_motivo_del_ultimo() -> None:
    """El motivo que se publica es el del último intento, no el del primero: es el que describe
    por qué no hay respuesta ahora."""
    curso = resolver_curso([MAL, FUERA, SIN_CITAS])
    assert curso.salida is Salida.ABSTENERSE
    assert curso.reintentos == MAX_REINTENTOS
    assert curso.motivo is Motivo.SIN_CITAS
    assert curso.refs == ()


def test_quedarse_sin_borradores_se_abstiene_con_el_motivo_del_ultimo() -> None:
    """Camino real: el grafo dejó de reintentar antes de agotar el presupuesto —un timeout de
    nodo, un error del proveedor— y no hay nada verificado que emitir.

    El motivo tiene que sobrevivir: el evento `abstain` del contrato SSE lo lleva **tipado**, y
    abstenerse sin decir por qué es indistinguible de un fallo para quien recibe la respuesta."""
    curso = resolver_curso([MAL])
    assert curso.salida is Salida.ABSTENERSE
    assert curso.motivo is Motivo.QUOTE_NO_LITERAL
    assert resolver_curso([MAL, FUERA]).motivo is Motivo.FUERA_DE_RANGO


def test_un_curso_sin_intentos_se_abstiene() -> None:
    """Ni un borrador. No hay nada que emitir y fingir lo contrario sería inventar."""
    curso = resolver_curso([])
    assert curso.salida is Salida.ABSTENERSE
    assert curso.motivo is None, "sin ningún borrador no hay motivo que dar, y fingirlo mentiría"


def test_no_se_miran_los_intentos_de_mas() -> None:
    """Si alguien pasa cuatro intentos, el curso termina en el tercero. Que el grafo respete el
    presupuesto es una cosa; que este módulo lo imponga aunque no lo respeten, otra."""
    curso = resolver_curso([MAL, MAL, MAL, BIEN])
    assert curso.salida is Salida.ABSTENERSE
    assert curso.reintentos == MAX_REINTENTOS


# ======================================================================================
# Propiedades obligatorias · docs/RULES.md §3.2
# ======================================================================================

veredictos = st.sampled_from([BIEN, MAL, FUERA, SIN_CITAS])


@given(st.lists(veredictos, max_size=12), st.booleans())
def test_propiedad_termina_siempre(intentos: list[Veredicto], hay_fuentes: bool) -> None:
    """**Propiedad exigida.** Sea cual sea la secuencia, el curso acaba en una salida terminal.
    Un bucle aquí sería una petición que nunca contesta y un modelo llamado sin tope."""
    curso = resolver_curso(intentos, hay_fuentes=hay_fuentes)
    assert curso.salida in (Salida.RESPONDER, Salida.ABSTENERSE)


@given(st.lists(veredictos, max_size=12), st.booleans())
def test_propiedad_nunca_mas_de_dos_reintentos(
    intentos: list[Veredicto], hay_fuentes: bool
) -> None:
    """**Propiedad exigida.** El tope no es una sugerencia: cada reintento es una llamada al
    modelo dentro del presupuesto de `G-TTFT`."""
    assert resolver_curso(intentos, hay_fuentes=hay_fuentes).reintentos <= MAX_REINTENTOS


@given(veredictos, st.integers(min_value=0, max_value=20), st.booleans())
def test_propiedad_abstenerse_es_absorbente(
    veredicto: Veredicto, hechos: int, hay_fuentes: bool
) -> None:
    """**Propiedad exigida**, enunciada sobre la decisión y no sobre el curso.

    Una vez que `decidir` dice abstenerse para un número de reintentos, lo sigue diciendo para
    cualquier número mayor: gastar más presupuesto no reabre una puerta cerrada.

    La primera versión de este test decía «si el curso se abstiene, alargarlo sigue
    abstiniéndose», y Hypothesis la tumbó con razón: `[MAL]` se abstiene porque **se acabaron
    los borradores**, no porque se decidiera abstenerse, y alargarlo debe poder rescatarlo —
    eso es exactamente lo que significa reintentar. Confundir las dos cosas habría convertido
    la propiedad en una prohibición del reintento."""
    if decidir(veredicto, reintentos_hechos=hechos, hay_fuentes=hay_fuentes) is Salida.ABSTENERSE:
        for mas in (hechos + 1, hechos + 7, hechos + 100):
            assert (
                decidir(veredicto, reintentos_hechos=mas, hay_fuentes=hay_fuentes)
                is Salida.ABSTENERSE
            )


@given(st.lists(veredictos, max_size=12))
def test_propiedad_agotado_el_presupuesto_ningun_intento_de_mas_rescata(
    intentos: list[Veredicto],
) -> None:
    """La otra mitad de lo mismo, a nivel de curso: si se abstuvo **habiendo gastado el
    presupuesto entero**, añadir borradores buenos no lo cambia. Si pudiera, el tope de
    reintentos no sería un tope."""
    curso = resolver_curso(intentos)
    if curso.salida is Salida.ABSTENERSE and curso.reintentos >= MAX_REINTENTOS:
        assert resolver_curso([*intentos, BIEN, BIEN]).salida is Salida.ABSTENERSE


@given(st.lists(veredictos, max_size=12))
def test_propiedad_responder_implica_que_el_ultimo_intento_mirado_verifico(
    intentos: list[Veredicto],
) -> None:
    """No está en la lista de obligatorias y sostiene la tesis igual: **nunca se responde con un
    borrador que no verificó.** Sin ella, «termina siempre» se cumpliría emitiendo cualquier
    cosa."""
    curso = resolver_curso(intentos)
    if curso.salida is Salida.RESPONDER:
        assert curso.refs != ()
        assert curso.motivo is None


# ======================================================================================
# Abstención por irrelevancia · la señal que faltaba
# ======================================================================================
#
# La cita cerrada garantiza que el fragmento **existe**. No garantiza que **responda**, y eso
# se midió el 2026-08-21: de 58 preguntas que el corpus no contesta, el sistema respondió y
# verificó en 42. Las citas eran reales; simplemente no venían a cuento.
#
# El cross-encoder sí distingue: sobre los 274 casos, la mejor puntuación de las cinco fuentes
# tiene mediana 0,893 en los positivos y 0,011 en los negativos.


def test_una_puntuacion_alta_deja_responder() -> None:
    assert decidir(BIEN, reintentos_hechos=0, hay_fuentes=True, relevancia=0.9) is Salida.RESPONDER


def test_una_puntuacion_baja_abstiene_sin_llamar_al_modelo() -> None:
    """**El punto entero.** Si lo recuperado no viene a cuento, generar es pagar latencia para
    acabar citando algo real que no responde — que es peor que callarse, porque parece bueno."""
    assert (
        decidir(BIEN, reintentos_hechos=0, hay_fuentes=True, relevancia=0.001)
        is Salida.ABSTENERSE
    )


def test_sin_puntuacion_se_decide_como_siempre() -> None:
    """`None` es «no se midió», no «cero». El evaluador y la API pueden correr sin puntuador, y
    tratar su ausencia como irrelevancia abstendría el sistema entero."""
    assert decidir(BIEN, reintentos_hechos=0, hay_fuentes=True, relevancia=None) is Salida.RESPONDER


def test_el_borde_del_umbral_deja_responder() -> None:
    """Justo en el umbral se responde: `>=`. Un borde ambiguo aquí movería la pareja
    `G-ABST-FP`/`G-ABST-FN` sin que nadie supiera por qué."""
    assert (
        decidir(BIEN, reintentos_hechos=0, hay_fuentes=True, relevancia=UMBRAL_RELEVANCIA)
        is Salida.RESPONDER
    )


def test_la_irrelevancia_manda_sobre_el_veredicto() -> None:
    """Se comprueba antes que el reintento: si nada de lo recuperado viene a cuento, reintentar
    es pedirle al modelo que lo intente otra vez con el mismo material inútil."""
    assert decidir(MAL, reintentos_hechos=0, hay_fuentes=True, relevancia=0.0) is Salida.ABSTENERSE


def test_un_curso_irrelevante_se_abstiene_con_su_motivo() -> None:
    """El motivo es propio: `sin_relevancia` dice «el corpus no lo responde», y
    `quote_no_literal` dice «el modelo lo escribió mal». Confundirlos manda a arreglar lo que
    no está roto."""
    curso = resolver_curso([BIEN], hay_fuentes=True, relevancia=0.0)
    assert curso.salida is Salida.ABSTENERSE
    assert curso.motivo is Motivo.SIN_RELEVANCIA
