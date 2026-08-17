"""Unit tests for `citebound.retrieval.fusion` · fase 2, TDD obligatorio.

**Reciprocal Rank Fusion.** Junta las listas del recuperador léxico y del vectorial en una
sola sin necesitar que sus puntuaciones sean comparables — que es justo el problema: un
`ts_rank_cd` de 0,08 y un coseno de 0,73 no se pueden sumar, y normalizarlos exige una
calibración que cambia con el corpus. RRF solo mira **posiciones**, así que no hay nada que
calibrar.

La fórmula del contrato es `score(d) = Σ 1/(k + rango(d))` con **k = 60**, el valor del paper
original y el que `docs/PLAN.md` fija para esta fase.

Lo que se prueba aquí no es que sume bien, sino las tres propiedades que hacen que el
resultado signifique algo, y un cuarto grupo de casos que el recall va a encontrar seguro:
un documento en una sola lista, listas de longitudes distintas y empates.
"""

from __future__ import annotations

import pytest

from citebound.retrieval.fusion import K_RRF, fusionar


def test_una_sola_lista_conserva_su_orden() -> None:
    """Con una lista, fusionar no puede reordenar nada: `score` es monótono decreciente en el
    rango. Si esto fallara, el fusionador estaría inventando información que no tiene."""
    assert fusionar([["a", "b", "c"]]) == ["a", "b", "c"]


def test_lo_que_aparece_en_las_dos_listas_sube() -> None:
    """El punto entero de RRF: el acuerdo entre recuperadores es la señal.

    `b` sale segundo en las dos listas; `a` y `c` salen primeros, pero cada uno en una sola.
    Aparecer dos veces gana a un primer puesto aislado, que es exactamente lo que se le pide
    a un fusionador híbrido.
    """
    fusionada = fusionar([["a", "b"], ["c", "b"]])
    assert fusionada[0] == "b"


def test_con_rangos_simetricos_ganan_los_extremos_y_no_el_centro() -> None:
    """Una propiedad de RRF que NO es intuitiva y que conviene tener escrita.

    Con `[[a,b,c],[c,b,a]]`, `b` va segundo en las dos y `a` y `c` van primero en una y
    tercero en la otra. Parece que `b` debería ganar, y pierde: `1/61 + 1/63 > 2/62` porque
    `1/x` es **convexa**. Con rangos simétricos, RRF premia a quien destaca en una lista
    aunque falle en la otra, frente a quien es mediocre en las dos.

    No es un defecto: es lo que hace que un recuperador que encuentra algo que el otro no ve
    siga aportando. Pero si alguien mira este caso esperando lo contrario, va a pensar que la
    fusión está rota.
    """
    fusionada = fusionar([["a", "b", "c"], ["c", "b", "a"]])
    assert fusionada[-1] == "b"


def test_un_documento_en_una_sola_lista_no_desaparece() -> None:
    """El vectorial encuentra cosas que el léxico no, y al revés. Si la fusión exigiera estar
    en las dos, se perdería justo lo que aporta cada uno."""
    fusionada = fusionar([["a", "b"], ["c"]])
    assert set(fusionada) == {"a", "b", "c"}


def test_las_listas_pueden_tener_longitudes_distintas() -> None:
    """El léxico devuelve lo que casa y el vectorial siempre devuelve `k`. Nunca miden igual."""
    assert set(fusionar([["a"], ["b", "c", "d", "e"]])) == {"a", "b", "c", "d", "e"}


def test_una_lista_vacia_no_rompe_ni_aporta() -> None:
    """Una consulta sin resultados léxicos es normal, no un error."""
    assert fusionar([["a", "b"], []]) == ["a", "b"]


def test_sin_ninguna_lista_el_resultado_es_vacio() -> None:
    assert fusionar([]) == []
    assert fusionar([[], []]) == []


def test_los_empates_se_rompen_de_forma_estable() -> None:
    """Dos documentos con el mismo score tienen que salir siempre en el mismo orden, o
    `G-EVAL-DET` fallaría por una razón que no tiene nada que ver con el modelo."""
    entrada = [["a", "b"], ["b", "a"]]
    assert fusionar(entrada) == fusionar(entrada)


def test_ningun_documento_sale_repetido() -> None:
    """Un duplicado en la lista fusionada contaría dos veces en el recall y lo inflaría."""
    fusionada = fusionar([["a", "a", "b"], ["a"]])
    assert fusionada.count("a") == 1


def test_la_constante_k_es_la_del_contrato() -> None:
    """`k = 60` no es un ajuste libre: lo fija `docs/PLAN.md` para esta fase. Cambiarlo mueve
    todas las métricas de recall a la vez, así que vive en una constante con nombre y no
    incrustado en la fórmula."""
    assert K_RRF == 60


def test_k_grande_aplana_las_diferencias_de_rango() -> None:
    """El papel de `k`: cuanto mayor, menos pesa la diferencia entre el puesto 1 y el 2, y más
    pesa aparecer en varias listas. Con `k` enorme, dos documentos que aparecen una vez cada
    uno quedan casi empatados aunque uno vaya primero y el otro décimo."""
    poco = fusionar([["a"], ["b"]], k=1)
    mucho = fusionar([["a"], ["b"]], k=10_000)
    assert set(poco) == set(mucho) == {"a", "b"}


@pytest.mark.parametrize("k", [0, -1])
def test_una_k_no_positiva_es_un_error(k: int) -> None:
    """Con `k = 0` el documento en primera posición (rango 1) sigue funcionando, pero la
    fórmula pierde su sentido y con rangos base 0 dividiría por cero. Se rechaza en la
    frontera en vez de producir un número raro."""
    with pytest.raises(ValueError, match="k"):
        fusionar([["a"]], k=k)


def test_el_top_k_recorta_sin_cambiar_el_orden() -> None:
    """`G-RECALL5` mira los cinco primeros y `G-RECALL30` los treinta: recortar es parte del
    trabajo, no del consumidor."""
    fusionada = fusionar([["a", "b", "c", "d"]], tope=2)
    assert fusionada == ["a", "b"]


def test_un_tope_mayor_que_los_resultados_no_inventa_nada() -> None:
    assert fusionar([["a", "b"]], tope=10) == ["a", "b"]
