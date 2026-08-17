"""Hypothesis properties for `citebound.retrieval.fusion`.

Las tres son **obligatorias** por `docs/RULES.md` §3.2, literalmente: «idempotencia con lista
única · invarianza ante permutación de las listas de entrada cuando no hay empates · monotonía:
empeorar el rango en todas las listas nunca mejora el rango fusionado». Su ausencia es un fallo
del gate, no una omisión.

Existen porque un fusionador roto **no falla ruidosamente**: devuelve una lista ordenada de
documentos plausibles. El recall bajaría unos puntos y el diagnóstico apuntaría al recuperador
o al troceado, que es donde nadie lo encontraría.
"""

from __future__ import annotations

from hypothesis import assume, given, note
from hypothesis import strategies as st

from citebound.retrieval.fusion import fusionar

# Identificadores cortos: lo que se prueba es el orden, no el contenido.
docs = st.text(alphabet="abcdefgh", min_size=1, max_size=2)
listas = st.lists(st.lists(docs, min_size=0, max_size=8, unique=True), min_size=0, max_size=4)


@given(lista=st.lists(docs, min_size=0, max_size=10, unique=True))
def test_idempotencia_con_lista_unica(lista: list[str]) -> None:
    """RULES §3.2 nº 1. Con una sola lista no hay nada que fusionar, así que fusionar tiene
    que ser la identidad. Si reordenara, estaría inventando una señal que no existe."""
    assert fusionar([lista]) == lista


@given(entrada=listas, permutacion=st.randoms(use_true_random=False))
def test_invarianza_ante_permutacion_de_las_listas(entrada: list[list[str]], permutacion) -> None:  # type: ignore[no-untyped-def]
    """RULES §3.2 nº 2. Da igual en qué orden lleguen el léxico y el vectorial: RRF suma, y la
    suma es conmutativa. Si el resultado dependiera del orden de los argumentos, el recall
    cambiaría según cómo se hubiera escrito la llamada.

    **Solo cuando no hay empates**, que es lo que dice la regla: con empates el desempate es
    una convención y puede depender del orden en que se vieron los documentos.
    """
    fusionada = fusionar(entrada)
    barajada = list(entrada)
    permutacion.shuffle(barajada)
    otra = fusionar(barajada)
    note(f"{entrada} → {fusionada}\n{barajada} → {otra}")
    assume(len(set(fusionada)) == len(fusionada))
    assume(_sin_empates(entrada))
    assert fusionada == otra


def _sin_empates(entrada: list[list[str]]) -> bool:
    """Dos documentos empatan si suman el mismo recíproco. Se calcula igual que `fusionar`
    para no depender de su implementación interna."""
    from citebound.retrieval.fusion import K_RRF

    puntos: dict[str, float] = {}
    for lista in entrada:
        for posicion, doc in enumerate(lista, start=1):
            puntos[doc] = puntos.get(doc, 0.0) + 1.0 / (K_RRF + posicion)
    return len(set(puntos.values())) == len(puntos)


@st.composite
def entrada_y_documento(draw: st.DrawFn) -> tuple[list[list[str]], str]:
    """Las listas **y** un documento que de verdad está en ellas.

    Generarlos por separado y filtrar con `assume` descarta el 85 % de los casos: Hypothesis
    avisa, y con razón — el filtrado deforma la distribución y deja el test probando mucho
    menos de lo que parece.
    """
    entrada = draw(listas)
    presentes = sorted({d for lista in entrada for d in lista})
    assume(presentes)
    return entrada, draw(st.sampled_from(presentes))


@given(caso=entrada_y_documento())
def test_monotonia_empeorar_el_rango_nunca_mejora_el_resultado(
    caso: tuple[list[list[str]], str],
) -> None:
    """RULES §3.2 nº 3, y la más importante de las tres.

    Si un documento baja de puesto en **todas** las listas donde aparece, no puede subir en la
    fusionada. Un fusionador que violara esto premiaría a los peores resultados de los dos
    recuperadores a la vez, y el síntoma sería un recall mediocre sin causa visible.
    """
    entrada, doc = caso
    antes = fusionar(entrada)
    peor = [_atras(lista, doc) for lista in entrada]
    despues = fusionar(peor)
    note(f"{doc}: {antes.index(doc)} → {despues.index(doc)}")
    assert despues.index(doc) >= antes.index(doc)


def _atras(lista: list[str], doc: str) -> list[str]:
    """Baja `doc` una posición, si puede. Si ya es el último o no está, la lista no cambia."""
    if doc not in lista:
        return lista
    i = lista.index(doc)
    if i == len(lista) - 1:
        return lista
    movida = list(lista)
    movida[i], movida[i + 1] = movida[i + 1], movida[i]
    return movida


@given(entrada=listas)
def test_la_fusion_no_pierde_ni_inventa_documentos(entrada: list[list[str]]) -> None:
    """No la exige RULES, pero es la que protege el recall: si la fusión perdiera un documento
    que el recuperador sí trajo, `G-RECALL30` bajaría por culpa del fusionador y el
    diagnóstico apuntaría al índice."""
    esperados = {d for lista in entrada for d in lista}
    assert set(fusionar(entrada)) == esperados
