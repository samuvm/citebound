"""Unit tests for `citebound.evals.scoring` and `citebound.evals.schema`.

**Estos tests se escriben y se congelan ANTES de anotar el primer caso del golden set**
(`docs/PLAN.md` fase 1a). Anotar el golden set contra un corrector que después cambia tira las
**10-16 horas** que `PLAN.md` §3 y Q-004 presupuestan, y no hay forma de recuperarlas: los casos
se anotaron respondiendo a una definición que ya no existe.

Nada de lo que se afirma aquí es invención de este proyecto. Todo sale literal de
`docs/CONTRACTS/retrieval-metrics.md` §2, que es el contrato compartido con `evalgate-02` e
`indexkeeper-04` y la razón de que los tres README sean comparables. El propio contrato
existe porque «¿el artículo citado es el del golden set? Exacto, sí/no» **no resolvía cuatro
casos que aparecen constantemente**, y esos cuatro son la mitad de este fichero:

  1. La respuesta cita varias referencias → **todas** deben pertenecer a `R(q)`. Una correcta
     más una inventada es **fallo**, no medio acierto.
  2. Granularidad de apartado → si el caso especifica apartado, la cita debe incluirlo.
     Citar `art21` cuando lo correcto es `art21.1` es fallo. Al revés no: si el caso no
     especifica apartado, citar uno es correcto siempre que el artículo coincida.
  3. Respuesta apoyada en dos artículos → basta citar **uno** y **ninguno fuera de `R(q)`**.
  4. Abstenciones → **fuera del denominador** de precisión de cita. Se miden aparte, y en
     los dos sentidos, porque con una sola métrica la estrategia óptima es callarse siempre.
"""

from __future__ import annotations

from datetime import date

import pytest

from citebound.domain.legalref import LegalRef, parse
from citebound.evals.schema import CasoGolden, Dificultad, Provenance, Tipo
from citebound.evals.scoring import (
    Prediccion,
    abstencion_incorrecta,
    abstencion_indebida,
    alucinacion,
    cobertura,
    precision_cita,
    precision_cita_articulo,
    recall_at_k,
)

NORMA = "RD-1428/2003"


def caso(
    ident: str,
    *refs: str,
    tipo: Tipo = Tipo.POSITIVO,
    materia: str = "adelantamiento",
) -> CasoGolden:
    return CasoGolden(
        id=ident,
        version=1,
        pregunta=f"¿Pregunta {ident}?",
        respuesta_referencia="Sí." if tipo is Tipo.POSITIVO else None,
        refs=[parse(r) for r in refs],
        materia=materia,
        dificultad=Dificultad.MEDIA,
        pct_fallo=10.0,
        tipo=tipo,
        provenance=Provenance.LLM_GENERADO_REVISADO_HUMANO,
        revisado_por="samuel",
        revisado_en=date(2026, 8, 20),
    )


def pred(ident: str, *refs: str, abstenida: bool = False) -> Prediccion:
    return Prediccion(caso_id=ident, refs=tuple(parse(r) for r in refs), abstenida=abstenida)


# --------------------------------------------------------------------------------------
# el esquema del golden set · contrato §3
# --------------------------------------------------------------------------------------


def test_a_positive_case_needs_at_least_one_reference() -> None:
    """`refs` vacía **si y solo si** `tipo="negativo"`. Un positivo sin referencia no se
    puede puntuar: no hay contra qué comparar la cita."""
    with pytest.raises(ValueError, match="refs"):
        CasoGolden(
            id="gs-0001",
            version=1,
            pregunta="¿?",
            respuesta_referencia="Sí.",
            refs=[],
            materia="x",
            dificultad=Dificultad.FACIL,
            pct_fallo=1.0,
            tipo=Tipo.POSITIVO,
            provenance=Provenance.HUMANO,
            revisado_por="samuel",
            revisado_en=date(2026, 8, 20),
        )


def test_a_negative_case_must_have_no_references() -> None:
    """El «si y solo si» del contrato en la otra dirección. Un negativo con referencia es
    una contradicción: si hay artículo que lo responde, el corpus sí lo contiene."""
    with pytest.raises(ValueError, match="refs"):
        CasoGolden(
            id="gs-0002",
            version=1,
            pregunta="¿?",
            respuesta_referencia=None,
            refs=[LegalRef(NORMA, "34")],
            materia="x",
            dificultad=Dificultad.FACIL,
            pct_fallo=1.0,
            tipo=Tipo.NEGATIVO,
            provenance=Provenance.HUMANO,
            revisado_por="samuel",
            revisado_en=date(2026, 8, 20),
        )


def test_a_positive_case_needs_a_reference_answer() -> None:
    with pytest.raises(ValueError, match="respuesta_referencia"):
        CasoGolden(
            id="gs-0003",
            version=1,
            pregunta="¿?",
            respuesta_referencia=None,
            refs=[LegalRef(NORMA, "34")],
            materia="x",
            dificultad=Dificultad.FACIL,
            pct_fallo=1.0,
            tipo=Tipo.POSITIVO,
            provenance=Provenance.HUMANO,
            revisado_por="samuel",
            revisado_en=date(2026, 8, 20),
        )


def test_no_case_enters_the_golden_set_without_human_review() -> None:
    """Regla dura nº 3 del contrato §3. Generación asistida por LLM sí; aprobación
    automática no. Es el único punto del proyecto donde el criterio de dominio de Samuel
    es insustituible, y por eso el esquema lo exige en vez de confiar en el proceso."""
    with pytest.raises(ValueError, match="revis"):
        CasoGolden(
            id="gs-0004",
            version=1,
            pregunta="¿?",
            respuesta_referencia="Sí.",
            refs=[LegalRef(NORMA, "34")],
            materia="x",
            dificultad=Dificultad.FACIL,
            pct_fallo=1.0,
            tipo=Tipo.POSITIVO,
            provenance=Provenance.LLM_GENERADO_REVISADO_HUMANO,
            revisado_por=None,
            revisado_en=None,
        )


def test_a_case_is_immutable_once_built() -> None:
    """El golden set es append-only por versión (R12): corregir un caso crea `v2` + ADR,
    nunca se reescribe `v1`. Un caso mutable en memoria invita a lo contrario."""
    c = caso("gs-0005", f"{NORMA}#art34.1")
    with pytest.raises((AttributeError, TypeError, ValueError)):
        c.pregunta = "otra"  # type: ignore[misc]


def test_the_empirical_difficulty_travels_with_the_case() -> None:
    """`pct_fallo` es el porcentaje real de gente que falla la pregunta, medido sobre miles
    de intentos en el banco de origen. Es mejor dato que `dificultad`, que es un juicio, y
    por eso se conserva además del campo que exige el contrato."""
    assert caso("gs-0006", f"{NORMA}#art34").pct_fallo == 10.0


def test_a_case_round_trips_through_jsonl() -> None:
    """El golden set vive en JSONL y sus sha256 están en `CHECKSUMS`. Si serializar y
    volver a leer no da el mismo caso, el checksum deja de significar nada."""
    original = caso("gs-0007", f"{NORMA}#art34.1", f"{NORMA}#art35")
    assert CasoGolden.model_validate_json(original.model_dump_json()) == original


# --------------------------------------------------------------------------------------
# precisión de cita · los cuatro casos que el contrato cierra
# --------------------------------------------------------------------------------------


def test_a_single_exact_citation_is_correct() -> None:
    casos = [caso("a", f"{NORMA}#art34.1")]
    assert precision_cita(casos, [pred("a", f"{NORMA}#art34.1")]).valor == 1.0


def test_one_correct_citation_plus_one_invented_is_a_failure() -> None:
    """**Todo o nada por caso.** No es medio acierto: una respuesta que cita el artículo
    bueno y además uno que no viene a cuento es una respuesta en la que no se puede
    confiar, y promediar dentro del caso lo escondería."""
    casos = [caso("a", f"{NORMA}#art34.1")]
    prediccion = [pred("a", f"{NORMA}#art34.1", f"{NORMA}#art99")]
    assert precision_cita(casos, prediccion).valor == 0.0


def test_citing_the_article_when_the_case_demands_the_apartado_is_a_failure() -> None:
    """`art34` cuando lo correcto es `art34.1`. El nivel exigido **no es un campo nuevo**
    del golden set: se deriva de si la ref del caso lleva apartado o no."""
    casos = [caso("a", f"{NORMA}#art34.1")]
    assert precision_cita(casos, [pred("a", f"{NORMA}#art34")]).valor == 0.0


def test_citing_an_apartado_when_the_case_only_demands_the_article_is_correct() -> None:
    """La asimetría del contrato, en la otra dirección: si el caso no especifica apartado,
    citar uno es correcto siempre que el artículo coincida. Ser más preciso que lo exigido
    no puede penalizar."""
    casos = [caso("a", f"{NORMA}#art34")]
    assert precision_cita(casos, [pred("a", f"{NORMA}#art34.1")]).valor == 1.0


def test_with_two_supporting_articles_citing_one_is_enough() -> None:
    """`R(q)` contiene los dos; se exige citar **al menos uno** y **ninguno fuera**."""
    casos = [caso("a", f"{NORMA}#art34", f"{NORMA}#art35")]
    assert precision_cita(casos, [pred("a", f"{NORMA}#art34")]).valor == 1.0


def test_with_two_supporting_articles_citing_both_is_also_correct() -> None:
    casos = [caso("a", f"{NORMA}#art34", f"{NORMA}#art35")]
    assert precision_cita(casos, [pred("a", f"{NORMA}#art34", f"{NORMA}#art35")]).valor == 1.0


def test_with_two_supporting_articles_one_outside_the_set_still_fails() -> None:
    casos = [caso("a", f"{NORMA}#art34", f"{NORMA}#art35")]
    assert precision_cita(casos, [pred("a", f"{NORMA}#art34", f"{NORMA}#art99")]).valor == 0.0


def test_abstentions_are_outside_the_denominator() -> None:
    """Contrato §2: `precision_cita = casos_con_todas_las_citas_en_R / casos_respondidos`.
    Dos casos, uno respondido bien y otro abstenido, dan 1,00 y no 0,50."""
    casos = [caso("a", f"{NORMA}#art34"), caso("b", f"{NORMA}#art35")]
    metrica = precision_cita(casos, [pred("a", f"{NORMA}#art34"), pred("b", abstenida=True)])
    assert metrica.valor == 1.0
    assert metrica.n == 1


def test_answering_with_no_citation_at_all_is_a_failure() -> None:
    """Responder sin citar no es abstenerse: es afirmar sin respaldo, que es justo lo que
    el proyecto existe para impedir."""
    casos = [caso("a", f"{NORMA}#art34")]
    assert precision_cita(casos, [pred("a")]).valor == 0.0


def test_precision_over_no_answered_cases_is_undefined_and_says_so() -> None:
    """Cero de cero no es 1,00 ni es 0,00. Devolver un número aquí sería inventarlo, y un
    informe con un 1,00 inventado es peor que uno que dice «no medible»."""
    casos = [caso("a", f"{NORMA}#art34")]
    metrica = precision_cita(casos, [pred("a", abstenida=True)])
    assert metrica.valor is None
    assert metrica.n == 0


# --------------------------------------------------------------------------------------
# recall@k · contrato §2
# --------------------------------------------------------------------------------------


def test_recall_is_the_fraction_of_the_relevant_set_among_the_retrieved() -> None:
    casos = [caso("a", f"{NORMA}#art34", f"{NORMA}#art35")]
    recuperado = {"a": [parse(f"{NORMA}#art34"), parse(f"{NORMA}#art99")]}
    assert recall_at_k(casos, recuperado, k=5).valor == 0.5


def test_recall_counts_a_reference_once_even_if_two_chunks_point_at_it() -> None:
    """`|P_k(q)|` puede ser menor que `k` porque varios chunks apuntan al mismo artículo.
    Es correcto y deliberado: importa si la referencia está, no cuántas veces."""
    casos = [caso("a", f"{NORMA}#art34")]
    recuperado = {"a": [parse(f"{NORMA}#art34")] * 3}
    assert recall_at_k(casos, recuperado, k=5).valor == 1.0


def test_recall_only_counts_the_first_k_retrieved() -> None:
    casos = [caso("a", f"{NORMA}#art35")]
    recuperado = {"a": [parse(f"{NORMA}#art{i}") for i in range(30, 40)]}
    assert recall_at_k(casos, recuperado, k=3).valor == 0.0
    assert recall_at_k(casos, recuperado, k=10).valor == 1.0


def test_negative_cases_are_outside_the_recall_denominator() -> None:
    """Contrato §2: las preguntas sin respuesta en el corpus quedan fuera del denominador
    de recall. Se usan solo para medir abstención."""
    casos = [caso("a", f"{NORMA}#art34"), caso("b", tipo=Tipo.NEGATIVO)]
    recuperado = {"a": [parse(f"{NORMA}#art34")], "b": [parse(f"{NORMA}#art99")]}
    metrica = recall_at_k(casos, recuperado, k=5)
    assert metrica.valor == 1.0
    assert metrica.n == 1


def test_recall_at_the_apartado_level_demands_the_apartado() -> None:
    """El mismo criterio de granularidad que la precisión de cita: si el caso pide
    apartado, recuperar el artículo suelto no cuenta como haberlo encontrado."""
    casos = [caso("a", f"{NORMA}#art34.1")]
    assert recall_at_k(casos, {"a": [parse(f"{NORMA}#art34")]}, k=5).valor == 0.0
    assert recall_at_k(casos, {"a": [parse(f"{NORMA}#art34.1")]}, k=5).valor == 1.0


# --------------------------------------------------------------------------------------
# alucinación · tolerancia cero, sin intervalo de confianza
# --------------------------------------------------------------------------------------


def test_a_citation_outside_the_index_is_a_hallucination() -> None:
    """Contrato §2: «no existe» significa que la `legal_ref` no está en el índice activo.
    Es pertenencia a un conjunto, determinista y barata. Objetivo 0,00 **sin intervalo de
    confianza**: aquí no hay umbral estadístico que negociar."""
    indice = frozenset({f"{NORMA}#art34", f"{NORMA}#art35"})
    casos = [caso("a", f"{NORMA}#art34")]
    assert alucinacion(casos, [pred("a", f"{NORMA}#art34")], indice).valor == 0.0
    assert alucinacion(casos, [pred("a", f"{NORMA}#art404")], indice).valor == 1.0


def test_a_citation_can_exist_in_the_index_and_still_be_the_wrong_article() -> None:
    """La distinción que separa alucinación de imprecisión, y que hace falta publicar las
    dos: citar el artículo 35 cuando tocaba el 34 **no es una alucinación** —el 35 existe—
    pero sí es un fallo de precisión de cita."""
    indice = frozenset({f"{NORMA}#art34", f"{NORMA}#art35"})
    casos = [caso("a", f"{NORMA}#art34")]
    prediccion = [pred("a", f"{NORMA}#art35")]
    assert alucinacion(casos, prediccion, indice).valor == 0.0
    assert precision_cita(casos, prediccion).valor == 0.0


def test_abstentions_do_not_count_as_hallucinations() -> None:
    indice = frozenset({f"{NORMA}#art34"})
    casos = [caso("a", f"{NORMA}#art34")]
    assert alucinacion(casos, [pred("a", abstenida=True)], indice).n == 0


# --------------------------------------------------------------------------------------
# abstención · en los dos sentidos, siempre. La pareja de RULES R16
# --------------------------------------------------------------------------------------


def test_staying_silent_when_the_corpus_had_the_answer_is_a_false_positive() -> None:
    """`G-ABST-FP ≤ 0,05`. Se abstuvo habiendo respuesta: un sistema inútil pero prudente."""
    casos = [caso("a", f"{NORMA}#art34"), caso("b", f"{NORMA}#art35")]
    prediccion = [pred("a", abstenida=True), pred("b", f"{NORMA}#art35")]
    assert abstencion_incorrecta(casos, prediccion).valor == 0.5


def test_answering_when_the_corpus_had_nothing_is_a_false_negative() -> None:
    """`G-ABST-FN ≤ 0,10`. Sin este dual, **no abstenerse nunca** sería la estrategia
    óptima, igual que con la precisión sola lo sería abstenerse siempre."""
    casos = [caso("a", tipo=Tipo.NEGATIVO), caso("b", tipo=Tipo.NEGATIVO)]
    prediccion = [pred("a", f"{NORMA}#art34"), pred("b", abstenida=True)]
    assert abstencion_indebida(casos, prediccion).valor == 0.5


def test_coverage_is_the_fraction_of_answerable_cases_actually_answered() -> None:
    """`G-COBERTURA ≥ 0,90`, pareja atómica de `G-CITA-PRECISION` (R16). Se evalúan como
    UNA sola condición porque, separadas, subir una a costa de la otra es trivial."""
    casos = [caso(x, f"{NORMA}#art34") for x in "abcd"]
    prediccion = [
        pred("a", f"{NORMA}#art34"),
        pred("b", f"{NORMA}#art34"),
        pred("c", f"{NORMA}#art34"),
        pred("d", abstenida=True),
    ]
    assert cobertura(casos, prediccion).valor == 0.75


def test_always_abstaining_gets_a_perfect_precision_and_zero_coverage() -> None:
    """**El test que justifica la pareja.** Callarse siempre deja la precisión indefinida
    y la cobertura en cero. Si alguien mira solo la primera, este sistema parece
    perfecto — y no responde nada."""
    casos = [caso(x, f"{NORMA}#art34") for x in "abc"]
    prediccion = [pred(x, abstenida=True) for x in "abc"]
    assert precision_cita(casos, prediccion).valor is None
    assert cobertura(casos, prediccion).valor == 0.0


# --------------------------------------------------------------------------------------
# rechazos · una métrica calculada sobre datos descuadrados no es una métrica
# --------------------------------------------------------------------------------------


def test_a_prediction_for_an_unknown_case_is_refused() -> None:
    """Silenciarlo daría un número plausible sobre un conjunto que no es el golden set."""
    with pytest.raises(ValueError, match="gs-fantasma"):
        precision_cita([caso("a", f"{NORMA}#art34")], [pred("gs-fantasma", f"{NORMA}#art34")])


def test_a_case_without_prediction_is_refused() -> None:
    with pytest.raises(ValueError, match="sin predicción"):
        precision_cita(
            [caso("a", f"{NORMA}#art34"), caso("b", f"{NORMA}#art35")],
            [pred("a", f"{NORMA}#art34")],
        )


def test_two_predictions_for_one_case_are_refused() -> None:
    with pytest.raises(ValueError, match="duplicad"):
        precision_cita(
            [caso("a", f"{NORMA}#art34")],
            [pred("a", f"{NORMA}#art34"), pred("a", f"{NORMA}#art35")],
        )


def test_an_abstention_that_also_carries_citations_is_refused() -> None:
    """Abstenerse y citar a la vez no es un estado del sistema: es un error de quien
    construyó la predicción, y contarlo como cualquiera de los dos falsea las dos métricas."""
    with pytest.raises(ValueError, match="absten"):
        Prediccion(caso_id="a", refs=(LegalRef(NORMA, "34"),), abstenida=True)


# --------------------------------------------------------------------------------------
# los denominadores vacíos y las guardas · cero de cero nunca es un número
# --------------------------------------------------------------------------------------


def test_recall_over_a_set_with_no_positive_cases_is_undefined() -> None:
    """Un conjunto de solo negativos no tiene recall. Devolver 1,00 aquí sería publicar un
    recall perfecto sobre cero preguntas medibles."""
    metrica = recall_at_k([caso("a", tipo=Tipo.NEGATIVO)], {}, k=5)
    assert metrica.valor is None
    assert metrica.n == 0


@pytest.mark.parametrize("k", [0, -1])
def test_recall_with_a_nonsensical_k_is_refused(k: int) -> None:
    with pytest.raises(ValueError, match="k debe ser"):
        recall_at_k([caso("a", f"{NORMA}#art34")], {"a": []}, k=k)


def test_a_positive_case_with_no_retrieval_list_is_refused() -> None:
    """Tratar la ausencia como «no se recuperó nada» daría un recall más bajo pero
    plausible, y nadie sabría que en realidad falta el dato."""
    with pytest.raises(ValueError, match="sin lista de recuperados"):
        recall_at_k([caso("a", f"{NORMA}#art34")], {}, k=5)


def test_coverage_and_false_positive_abstention_over_only_negatives_are_undefined() -> None:
    """Las dos se miden sobre casos con respuesta en el corpus. Sin ninguno, no hay
    fracción que calcular — y `0,00` diría que el sistema no responde nada, que es falso."""
    casos = [caso("a", tipo=Tipo.NEGATIVO)]
    prediccion = [pred("a", abstenida=True)]
    assert cobertura(casos, prediccion).valor is None
    assert abstencion_incorrecta(casos, prediccion).valor is None


def test_undue_abstention_over_a_set_with_no_negatives_is_undefined() -> None:
    """El caso simétrico, y el que más importa: si el golden set se quedara sin negativos,
    `G-ABST-FN` no diría 0,00 —«nunca responde de más»— sino que no es medible. Es lo que
    obliga a los 40 negativos de `G-GOLDEN-VALID`."""
    metrica = abstencion_indebida([caso("a", f"{NORMA}#art34")], [pred("a", f"{NORMA}#art34")])
    assert metrica.valor is None
    assert metrica.n == 0


# --------------------------------------------------------------------------------------
# El `id` y el `n` de cada métrica, que la mutación destapó sin cubrir
# --------------------------------------------------------------------------------------
#
# `make mutation` sobre `scoring.py` dejó 22 mutantes vivos con el 100 % de cobertura de
# línea, y 20 eran del mismo tipo: los tests miraban `.valor` y nunca `.id` ni `.n`, así
# que `Metrica(None, 0.87, 4)` y `Metrica("g-halluc", …)` pasaban. No es cosmético:
#
#   · el `id` es la clave con la que `done.py` busca el número en `eval-latest.json`
#     (`metrics[id=G-HALLUC].value`). Un id equivocado no da un número malo: da «sin
#     artefacto», que el gate reporta como rojo de fontanería y manda a mirar donde no es.
#     Dos métricas con el mismo id son peores: una tapa a la otra y el gate pasa con el
#     número que no era.
#   · el `n` es el denominador que se publica. `G-HALLUC = 0` sobre 15 y sobre 2.000 son
#     la misma cifra y dos afirmaciones distintas; es la razón de que exista
#     `G-HALLUC-AMPLIO`. El propio docstring de `Metrica` lo dice y ningún test lo probaba.


def test_cada_metrica_declara_su_id_y_su_denominador_con_datos() -> None:
    """Los identificadores son los de `docs/GOALS.yaml`, literales y en mayúsculas."""
    casos = [
        caso("a", f"{NORMA}#art34"),
        caso("b", f"{NORMA}#art35"),
        caso("c", tipo=Tipo.NEGATIVO),
    ]
    prediccion = [pred("a", f"{NORMA}#art34"), pred("b", abstenida=True), pred("c", abstenida=True)]

    esperado = {
        "G-CITA-PRECISION": (precision_cita(casos, prediccion), 1),
        "G-HALLUC": (alucinacion(casos, prediccion, frozenset({f"{NORMA}#art34"})), 1),
        "G-COBERTURA": (cobertura(casos, prediccion), 2),
        "G-ABST-FP": (abstencion_incorrecta(casos, prediccion), 2),
        "G-ABST-FN": (abstencion_indebida(casos, prediccion), 1),
    }
    for identificador, (metrica, n) in esperado.items():
        assert metrica.id == identificador
        assert metrica.n == n
        assert metrica.valor is not None


def test_cada_metrica_declara_su_id_y_denominador_cero_cuando_no_es_medible() -> None:
    """El caso vacío también publica: `valor=None` **con `n=0`**, no con `n=None`."""
    vacio: list[CasoGolden] = []
    sin_pred: list[Prediccion] = []
    for metrica, identificador in (
        (precision_cita(vacio, sin_pred), "G-CITA-PRECISION"),
        (alucinacion(vacio, sin_pred, frozenset()), "G-HALLUC"),
        (cobertura(vacio, sin_pred), "G-COBERTURA"),
        (abstencion_incorrecta(vacio, sin_pred), "G-ABST-FP"),
        (abstencion_indebida(vacio, sin_pred), "G-ABST-FN"),
        (recall_at_k(vacio, {}, k=5), "G-RECALL5"),
    ):
        assert metrica.id == identificador
        assert metrica.valor is None
        assert metrica.n == 0


def test_recall_lleva_la_k_en_el_identificador() -> None:
    """`G-RECALL5` y `G-RECALL30` son dos metas distintas de `GOALS.yaml` con umbrales
    distintos (0,90 y 0,97). Si el id no llevara la `k`, la segunda taparía a la primera
    en el informe y el gate leería el número equivocado sin fallar."""
    casos = [caso("a", f"{NORMA}#art34")]
    recuperado = {"a": [parse(f"{NORMA}#art34")]}
    assert recall_at_k(casos, recuperado, k=5).id == "G-RECALL5"
    assert recall_at_k(casos, recuperado, k=30).id == "G-RECALL30"


def test_la_abstencion_indebida_cuenta_los_que_respondio_no_los_que_callo() -> None:
    """**El mutante más grave de los 22: invertir la condición y que nadie se entere.**

    `G-ABST-FN` es la fracción de negativos en los que el sistema respondió **debiendo
    callarse**. Con la condición invertida mediría lo contrario, el umbral `<= 0,10`
    premiaría justo la conducta que castiga, y «responder siempre» pasaría el gate.

    Por eso el reparto es asimétrico —3 negativos, 1 respondido— y no mitad y mitad:
    con 2 y 2 el valor es 0,5 en los dos sentidos y el test no prueba nada.
    """
    casos = [caso(c, tipo=Tipo.NEGATIVO) for c in "abc"]
    prediccion = [pred("a", f"{NORMA}#art34"), pred("b", abstenida=True), pred("c", abstenida=True)]
    metrica = abstencion_indebida(casos, prediccion)
    assert metrica.valor == pytest.approx(1 / 3)
    assert metrica.n == 3


def test_los_casos_sin_prediccion_se_nombran_todos_y_separados_por_coma() -> None:
    """El mensaje es el que lee quien tiene que arreglarlo: si no dice **cuáles** faltan,
    obliga a comparar 190 identificadores a mano."""
    casos = [caso("a", f"{NORMA}#art34"), caso("b", f"{NORMA}#art35"), caso("c", f"{NORMA}#art36")]
    with pytest.raises(ValueError) as fallo:
        precision_cita(casos, [pred("a", f"{NORMA}#art34")])
    assert "casos sin predicción: b, c" in str(fallo.value)


# --------------------------------------------------------------------------------------
# Dos agujeros que solo aparecieron cuando la mutación empezó a medir de verdad
# --------------------------------------------------------------------------------------


def test_el_recall_promedia_sobre_todos_los_casos_y_no_se_queda_con_el_ultimo() -> None:
    """El mutante era `total = ...` en vez de `total += ...`, y sobrevivía porque **todos
    los tests de recall usaban un solo caso**: con n=1 las dos versiones dan lo mismo.

    Con la acumulación rota, `G-RECALL5` publicaría el recall del último caso del golden
    set como si fuera el de los 190. Aquí el reparto es asimétrico —uno acierta, otro
    falla— para que la media (0,5) no coincida con ninguno de los dos valores sueltos.
    """
    casos = [caso("a", f"{NORMA}#art34"), caso("b", f"{NORMA}#art35")]
    recuperado = {
        "a": [parse(f"{NORMA}#art34")],  # acierta
        "b": [parse(f"{NORMA}#art99")],  # falla
    }
    metrica = recall_at_k(casos, recuperado, k=5)
    assert metrica.valor == pytest.approx(0.5)
    assert metrica.n == 2


def test_la_alucinacion_divide_entre_los_respondidos_y_no_multiplica() -> None:
    """El mutante cambiaba `inventadas / len(respondidos)` por `inventadas * len(...)` y
    sobrevivía porque **ningún test tenía a la vez una cita inventada y más de un caso
    respondido**: con `inventadas = 0`, dividir y multiplicar dan cero igual.

    Es la meta con umbral `== 0` y `propuesta_admisible: false`. Que su aritmética no
    estuviera comprobada cuando el numerador no es cero es exactamente el agujero que la
    mutación existe para encontrar.
    """
    casos = [caso(c, f"{NORMA}#art34") for c in "abcd"]
    prediccion = [
        pred("a", f"{NORMA}#art999"),  # inventada
        pred("b", f"{NORMA}#art34"),
        pred("c", f"{NORMA}#art34"),
        pred("d", f"{NORMA}#art34"),
    ]
    metrica = alucinacion(casos, prediccion, frozenset({f"{NORMA}#art34"}))
    assert metrica.valor == pytest.approx(0.25)  # 1/4, no 1*4
    assert metrica.n == 4


def test_recall_admite_k_igual_a_uno_que_es_la_frontera_del_guardia() -> None:
    """`k=1` es válido y hasta ahora nadie lo probaba: los mutantes `k <= 1` y `k < 2`
    sobrevivían los dos.

    No es un caso de laboratorio. `recall@1` es el diagnóstico que dice si el reranker
    está poniendo el artículo correcto **el primero**, que es lo que de verdad ve el
    generador cuando el presupuesto de contexto aprieta. Si el guardia lo rechazara, ese
    diagnóstico no se podría medir y el mensaje de error culparía a quien lo pidió.
    """
    casos = [caso("a", f"{NORMA}#art34")]
    recuperado = {"a": [parse(f"{NORMA}#art34"), parse(f"{NORMA}#art35")]}
    metrica = recall_at_k(casos, recuperado, k=1)
    assert metrica.id == "G-RECALL1"
    assert metrica.valor == pytest.approx(1.0)

    # Y con el correcto en segunda posición, `k=1` no lo alcanza: el corte se aplica.
    recuperado_al_reves = {"a": [parse(f"{NORMA}#art35"), parse(f"{NORMA}#art34")]}
    assert recall_at_k(casos, recuperado_al_reves, k=1).valor == pytest.approx(0.0)


def test_la_precision_de_cita_divide_entre_los_respondidos_y_no_multiplica() -> None:
    """Mismo patrón que en `alucinacion`: `aciertos / n` y `aciertos * n` solo se
    distinguen si hay **más de un caso respondido y al menos un acierto**, y todos los
    tests de precisión usaban un caso.

    Es la meta que forma pareja atómica con `cobertura` y la que se publica en la portada
    del README. Que su aritmética no estuviera comprobada con más de un caso es el tipo de
    agujero que el 100 % de cobertura de línea no ve.
    """
    casos = [caso(c, f"{NORMA}#art34") for c in "abcd"]
    prediccion = [
        pred("a", f"{NORMA}#art34"),
        pred("b", f"{NORMA}#art34"),
        pred("c", f"{NORMA}#art34"),
        pred("d", f"{NORMA}#art35"),  # el artículo adyacente: existe, pero no es el suyo
    ]
    metrica = precision_cita(casos, prediccion)
    assert metrica.valor == pytest.approx(0.75)  # 3/4, no 3*4
    assert metrica.n == 4


# ======================================================================================
# Precisión de cita a nivel de artículo · Q-021, la divergencia declarada
# ======================================================================================
#
# El contrato compartido dice que si el golden set especifica apartado, la cita **debe**
# incluirlo. Medido el 2026-08-20, ese nivel es inalcanzable y no por el modelo: el apartado
# exacto está entre las cinco fuentes ofrecidas en el 39 % de los casos, y entre doce sin
# colapsar en el 56 %. El umbral es 0,85. No es que el generador cite mal — es que no se le
# ofrece lo que se le exige citar.
#
# Samuel eligió medir también la precisión de cita **a nivel de artículo** (Q-021), que es la
# misma lectura que ya había elegido para el recall en Q-016. Se publican **las dos**, igual
# que con el recall: la honestidad no está en elegir el número bueno, está en enseñar los dos.


def test_a_nivel_de_articulo_una_cita_sin_apartado_vale() -> None:
    """`art34` cuando el golden set dice `art34.1`. Con la lectura estricta es fallo; con
    esta, acierto — y la diferencia entre las dos es exactamente lo que Q-021 declara."""
    uno = caso("gs-1", "RD-1428/2003#art34.1")
    pred = [Prediccion(caso_id="gs-1", refs=(parse("RD-1428/2003#art34"),))]
    assert precision_cita([uno], pred).valor == 0.0
    assert precision_cita_articulo([uno], pred).valor == 1.0


def test_a_nivel_de_articulo_el_apartado_equivocado_tambien_vale() -> None:
    """`art34.2` cuando lo correcto es `art34.1`. **Esto es lo que se pierde** al bajar el
    nivel, y por eso se dice en voz alta: el sistema puede señalar el apartado de al lado y
    la métrica no lo verá."""
    uno = caso("gs-1", "RD-1428/2003#art34.1")
    pred = [Prediccion(caso_id="gs-1", refs=(parse("RD-1428/2003#art34.2"),))]
    assert precision_cita([uno], pred).valor == 0.0
    assert precision_cita_articulo([uno], pred).valor == 1.0


def test_a_nivel_de_articulo_otro_articulo_sigue_siendo_fallo() -> None:
    """Lo que **no** cambia: citar el 35 cuando la respuesta es el 34 es fallo en las dos
    lecturas. Bajar la granularidad no es dejar de medir."""
    uno = caso("gs-1", "RD-1428/2003#art34.1")
    pred = [Prediccion(caso_id="gs-1", refs=(parse("RD-1428/2003#art35.1"),))]
    assert precision_cita_articulo([uno], pred).valor == 0.0


def test_a_nivel_de_articulo_una_cita_buena_y_una_de_mas_sigue_siendo_fallo() -> None:
    """La regla de todo o nada del contrato no se toca: lo que cambia es la granularidad,
    no la exigencia de que **todas** las citas pertenezcan a R(q)."""
    uno = caso("gs-1", "RD-1428/2003#art34.1")
    pred = [
        Prediccion(
            caso_id="gs-1",
            refs=(parse("RD-1428/2003#art34"), parse("RD-1428/2003#art99")),
        )
    ]
    assert precision_cita_articulo([uno], pred).valor == 0.0


def test_a_nivel_de_articulo_las_abstenciones_siguen_fuera_del_denominador() -> None:
    casos = [caso("gs-1", "RD-1428/2003#art34.1"), caso("gs-2", "RD-1428/2003#art35")]
    pred = [
        Prediccion(caso_id="gs-1", refs=(parse("RD-1428/2003#art34"),)),
        Prediccion(caso_id="gs-2", abstenida=True),
    ]
    metrica = precision_cita_articulo(casos, pred)
    assert metrica.n == 1
    assert metrica.valor == 1.0


def test_la_lectura_de_articulo_nunca_es_peor_que_la_estricta() -> None:
    """Propiedad de las dos lecturas: recortar el apartado solo puede convertir fallos en
    aciertos, nunca al revés. Si alguna vez fuera al revés, una de las dos estaría mal."""
    casos = [
        caso("gs-1", "RD-1428/2003#art34.1"),
        caso("gs-2", "RD-1428/2003#art35.2"),
        caso("gs-3", "RD-1428/2003#art36"),
    ]
    pred = [
        Prediccion(caso_id="gs-1", refs=(parse("RD-1428/2003#art34"),)),
        Prediccion(caso_id="gs-2", refs=(parse("RD-1428/2003#art35.2"),)),
        Prediccion(caso_id="gs-3", refs=(parse("RD-1428/2003#art99"),)),
    ]
    estricta = precision_cita(casos, pred).valor or 0.0
    articulo = precision_cita_articulo(casos, pred).valor or 0.0
    assert articulo >= estricta
