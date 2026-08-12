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
