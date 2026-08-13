"""Hypothesis properties for `citebound.evals.bootstrap`.

Las **tres primeras son obligatorias** por `docs/RULES.md` §3.2, literalmente: «misma
semilla → mismo IC · muestras idénticas → el IC contiene 0 · el IC contiene la diferencia
observada». Su ausencia es un fallo del gate, no una omisión.

Existen porque un bootstrap mal implementado no falla ruidosamente: devuelve un intervalo
con decimales que parece razonable. Los tres casos de ejemplo del fichero unitario prueban
lo que a alguien se le ocurrió; estos prueban la forma del cálculo sobre cualquier reparto
de aciertos y fallos que el golden set pueda producir.
"""

from __future__ import annotations

from hypothesis import given, note
from hypothesis import strategies as st

from citebound.evals.bootstrap import hay_regresion, holm, ic_diferencia_pareada

# --------------------------------------------------------------------------------------
# Estrategias · con la forma real de lo que se remuestrea
# --------------------------------------------------------------------------------------

# La mayoría de métricas del contrato son todo-o-nada por caso (G-CITA-PRECISION,
# G-HALLUC, G-COBERTURA): una secuencia de 0 y 1. Las de latencia son continuas.
binarias = st.lists(st.sampled_from([0.0, 1.0]), min_size=1, max_size=60)

continuas = st.lists(
    st.floats(min_value=0.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=60,
)

# `n_resamples` pequeño a propósito: las tres propiedades se cumplen para cualquier
# número de réplicas, y el presupuesto de `make test-fast` es de 20 s (RULES §3.3).
resamples = st.integers(min_value=50, max_value=400)
semillas = st.integers(min_value=0, max_value=2**32 - 1)


@st.composite
def pares(
    draw: st.DrawFn, valores: st.SearchStrategy[list[float]]
) -> tuple[list[float], list[float]]:
    """Dos secuencias de la MISMA longitud: pareado significa los mismos casos."""
    base = draw(valores)
    head = draw(st.lists(st.sampled_from([0.0, 1.0]), min_size=len(base), max_size=len(base)))
    return base, head


# --------------------------------------------------------------------------------------
# Las tres de RULES §3.2
# --------------------------------------------------------------------------------------


@given(par=pares(binarias), n_resamples=resamples, semilla=semillas)
def test_misma_semilla_mismo_intervalo(
    par: tuple[list[float], list[float]], n_resamples: int, semilla: int
) -> None:
    """RULES §3.2 nº 1. Es la propiedad de la que cuelga `G-EVAL-DET`: sin ella, dos
    `make eval` seguidos dan informes distintos y el criterio de aceptación nº 2 del
    proyecto —«un desconocido ejecuta make eval y obtiene los mismos números»— es falso."""
    base, head = par
    uno = ic_diferencia_pareada(base, head, n_resamples=n_resamples, semilla=semilla)
    dos = ic_diferencia_pareada(base, head, n_resamples=n_resamples, semilla=semilla)
    assert uno == dos


@given(valores=binarias, n_resamples=resamples, semilla=semillas)
def test_muestras_identicas_el_intervalo_contiene_cero(
    valores: list[float], n_resamples: int, semilla: int
) -> None:
    """RULES §3.2 nº 2. Si head y base son la misma medida, la puerta NO puede bloquear:
    cada réplica da diferencia cero, luego el IC es [0, 0] y contiene el cero."""
    ic = ic_diferencia_pareada(valores, valores, n_resamples=n_resamples, semilla=semilla)
    note(f"IC = [{ic.inferior}, {ic.superior}]")
    assert ic.contiene(0.0)
    assert not hay_regresion(ic, mayor_es_mejor=True)
    assert not hay_regresion(ic, mayor_es_mejor=False)


@given(par=pares(binarias), n_resamples=resamples, semilla=semillas)
def test_el_intervalo_contiene_la_diferencia_observada(
    par: tuple[list[float], list[float]], n_resamples: int, semilla: int
) -> None:
    """RULES §3.2 nº 3. La media de la distribución bootstrap de la diferencia es
    exactamente la diferencia observada; un IC percentil que la dejara fuera indicaría
    que se está remuestreando otra cosa —típicamente, las dos muestras por separado en
    vez de los casos pareados—."""
    base, head = par
    ic = ic_diferencia_pareada(base, head, n_resamples=n_resamples, semilla=semilla)
    note(f"punto={ic.punto} IC=[{ic.inferior}, {ic.superior}]")
    assert ic.inferior <= ic.punto <= ic.superior


# --------------------------------------------------------------------------------------
# Dos más que no exige RULES pero sostienen la regla de la puerta
# --------------------------------------------------------------------------------------


@given(par=pares(continuas), n_resamples=resamples, semilla=semillas)
def test_los_dos_sentidos_de_regresion_son_excluyentes(
    par: tuple[list[float], list[float]], n_resamples: int, semilla: int
) -> None:
    """Un intervalo no puede quedar a la vez entero bajo cero y entero sobre cero. Si
    ambos sentidos dieran regresión a la vez, toda meta con `<=` y toda meta con `>=`
    bloquearían simultáneamente y la puerta sería inservible."""
    base, head = par
    ic = ic_diferencia_pareada(base, head, n_resamples=n_resamples, semilla=semilla)
    assert not (hay_regresion(ic, mayor_es_mejor=True) and hay_regresion(ic, mayor_es_mejor=False))


@given(
    pvalores=st.dictionaries(
        st.text(min_size=1, max_size=6),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=1,
        max_size=8,
    )
)
def test_holm_nunca_rechaza_menos_que_bonferroni(pvalores: dict[str, float]) -> None:
    """El motivo escrito en `GOALS.yaml` para elegir Holm: es uniformemente más potente
    que Bonferroni y no pide supuestos extra. Si esta propiedad cayera, la corrección
    estaría de más y bastaría con dividir alfa entre el número de métricas."""
    alfa = 0.05
    veredicto = holm(pvalores, alfa=alfa)
    for clave, p in pvalores.items():
        if p <= alfa / len(pvalores):
            assert veredicto[clave], f"{clave} p={p}"
