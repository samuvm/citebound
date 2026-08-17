"""Contract tests for `citebound.providers.embeddings`, written against the recording.

TDD is prohibited in `providers/` (RULES §3.1). These tests were written **after**
`scripts/record_embeddings.py` produced `tests/recordings/embeddings-bge-m3.json` from the
real `bge-m3` running on the host, so they assert the shape the provider actually returns
rather than one somebody imagined. That is the whole argument of §3.1: a test written
first would encode an invented API, and going green would certify the invention.

One test here talks to the real model and is marked `integration`. It is the analogue of
`test_the_fixture_is_verbatim_from_the_frozen_corpus`: a recording that has drifted from
what the model now answers stops being a double and becomes fiction, and the only way to
know is to ask the model again.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from citebound.providers.embeddings import (
    DIM_CONTRATO,
    Embedder,
    EmbeddingError,
    OpenAICompatEmbedder,
    RecordedEmbedder,
    clave_de,
    embedder_por_defecto,
)
from citebound.providers.embeddings import _vectores as validar_respuesta

GRABACION = Path(__file__).resolve().parents[1] / "recordings" / "embeddings-bge-m3.json"
DATOS = json.loads(GRABACION.read_text(encoding="utf-8"))
PREGUNTA = DATOS["preguntas"][0]


@pytest.fixture
def grabado() -> RecordedEmbedder:
    return RecordedEmbedder.desde_fichero(GRABACION)


# --------------------------------------------------------------------------------------
# the recording itself
# --------------------------------------------------------------------------------------


def test_the_recording_holds_vectors_of_the_width_the_contract_fixes() -> None:
    """`chunk_v1.embedding` is `vector(1024)` and Postgres has no variable-width column.
    A model of another width is not a swap: it is a new table and a re-index."""
    assert DATOS["dim"] == DIM_CONTRATO
    assert DATOS["vectores"]
    for clave, vector in DATOS["vectores"].items():
        assert len(vector) == DIM_CONTRATO, f"{clave[:12]}… tiene {len(vector)}"


def test_the_recording_declares_which_model_produced_it() -> None:
    """A recording without its model is an anonymous pile of numbers: nobody can tell
    later whether it still corresponds to what the system uses."""
    assert DATOS["model"] == "bge-m3"
    assert DATOS["endpoint"].endswith("/v1/embeddings")


def test_every_declared_question_has_its_vector_recorded() -> None:
    """The three fixed questions of `make smoke-f0`. If one is missing, the phase-0 smoke
    test would hit the network and stop being deterministic."""
    for pregunta in DATOS["preguntas"]:
        assert clave_de(DATOS["model"], pregunta) in DATOS["vectores"]


# --------------------------------------------------------------------------------------
# the recorded double
# --------------------------------------------------------------------------------------


def test_the_double_returns_the_recorded_vector(grabado: RecordedEmbedder) -> None:
    (vector,) = grabado.embed([PREGUNTA])
    assert len(vector) == DIM_CONTRATO
    assert vector == tuple(DATOS["vectores"][clave_de(DATOS["model"], PREGUNTA)])


def test_the_double_is_deterministic(grabado: RecordedEmbedder) -> None:
    assert grabado.embed([PREGUNTA]) == grabado.embed([PREGUNTA])


def test_the_double_keeps_the_order_of_the_input(grabado: RecordedEmbedder) -> None:
    """Vectors are paired with chunks by position. Reordering them would attach every
    embedding to the wrong article, and the index would be perfectly well formed and
    entirely wrong — nothing downstream could notice."""
    preguntas = DATOS["preguntas"]
    salida = grabado.embed(preguntas)
    for pregunta, vector in zip(preguntas, salida, strict=True):
        assert vector == tuple(DATOS["vectores"][clave_de(DATOS["model"], pregunta)])


def test_a_miss_raises_instead_of_inventing_a_vector(grabado: RecordedEmbedder) -> None:
    """**The most important test in this file.** A double that fabricates on a miss turns
    the suite green over numbers nobody produced, and the first symptom is a recall figure
    that cannot be explained. The error says how to re-record, because the fix is a
    command and not a debugging session."""
    with pytest.raises(EmbeddingError, match="no hay grabación"):
        grabado.embed(["una pregunta que nadie ha grabado nunca"])


def test_a_recording_of_the_wrong_width_is_refused() -> None:
    """El modelo se nombra aquí en vez de heredarse del defecto del paquete.

    Cuando el defecto pasó de `bge-m3` a `qwen3-embedding:0.6b`, la clave dejó de casar y este
    test empezó a fallar por «no hay grabación» — es decir, dejó de probar lo que dice probar
    sin dejar de existir. Un test que depende de una constante que puede cambiar por otro
    motivo mide dos cosas y no avisa de cuál se rompió.
    """
    modelo = "un-modelo-cualquiera"
    doble = RecordedEmbedder(grabacion={clave_de(modelo, "x"): [0.1, 0.2]}, model=modelo)
    with pytest.raises(EmbeddingError, match="dimensiones"):
        doble.embed(["x"])


def test_embedding_nothing_returns_nothing(grabado: RecordedEmbedder) -> None:
    assert grabado.embed([]) == ()


# --------------------------------------------------------------------------------------
# the port
# --------------------------------------------------------------------------------------


def test_both_implementations_satisfy_the_port(grabado: RecordedEmbedder) -> None:
    """`domain/` never sees an implementation (R6); it sees this protocol or nothing."""
    assert isinstance(grabado, Embedder)
    assert isinstance(OpenAICompatEmbedder(), Embedder)


def test_the_adapter_is_openai_compatible_and_not_ollama_specific() -> None:
    """`docs/STACK.md` §2.1: Ollama, llama.cpp, vLLM and LM Studio all expose
    `/v1/embeddings`. One adapter covers the four, and swapping runtime is a variable
    rather than an edit — cheap insurance while Ollama pivots to a consumer product."""
    assert OpenAICompatEmbedder().base_url.endswith("/v1")
    assert "ollama" not in OpenAICompatEmbedder.__name__.lower()


def test_the_default_embedder_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "http://otra-maquina:8000/v1")
    monkeypatch.setenv("CITEBOUND_EMBEDDING_MODEL", "otro-modelo")
    embedder = embedder_por_defecto()
    assert embedder.base_url == "http://otra-maquina:8000/v1"  # type: ignore[attr-defined]
    assert embedder.model == "otro-modelo"


# --------------------------------------------------------------------------------------
# the response is validated, not trusted
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cuerpo", "motivo"),
    [
        ({}, "sin `data`"),
        ({"data": "no es una lista"}, "vectores"),
        ({"data": []}, "vectores"),  # pidió uno y no vino ninguno
        ({"data": [{"embedding": "no es una lista"}]}, "no es una lista"),
        ({"data": [{"embedding": [0.1, 0.2]}]}, "dimensiones"),
    ],
)
def test_a_malformed_response_is_refused(cuerpo: object, motivo: str) -> None:
    """A provider that returns the wrong count or the wrong width would attach embeddings
    to the wrong chunks. Validating costs microseconds; the alternative is an index that
    looks healthy and answers wrong."""
    with pytest.raises(EmbeddingError, match=motivo):
        validar_respuesta(cuerpo, esperados=1, dim=DIM_CONTRATO, model="bge-m3")


def test_the_key_separates_model_from_text() -> None:
    """`\\x00` between the two, so no pair can be confused with another by concatenation."""
    assert clave_de("ab", "c") != clave_de("a", "bc")
    assert clave_de("bge-m3", "x") == clave_de("bge-m3", "x")


# --------------------------------------------------------------------------------------
# the recording has not drifted from the model
# --------------------------------------------------------------------------------------


@pytest.mark.integration
def test_the_real_model_still_answers_what_the_recording_says() -> None:
    """A recording that no longer matches the model is not a double, it is fiction — and
    the only way to find out is to ask again. Runs against the host (R9: Ollama is never
    in compose), and skips rather than fails when it is not up: this checks the recording,
    not the developer's machine.

    Cosine similarity rather than equality: `bge-m3` is deterministic in practice, but
    batch composition can move the last bits, and a test that fails on 1e-7 gets switched
    off within a week. `0.999` catches a changed model and ignores arithmetic noise.
    """
    httpx = pytest.importorskip("httpx")
    try:
        httpx.get("http://localhost:11434/api/version", timeout=2.0).raise_for_status()
    except Exception:
        pytest.skip("Ollama no responde en el host; `ollama ps`")

    real = OpenAICompatEmbedder(model=DATOS["model"]).embed(DATOS["preguntas"])
    doble = RecordedEmbedder.desde_fichero(GRABACION).embed(DATOS["preguntas"])
    for pregunta, a, b in zip(DATOS["preguntas"], real, doble, strict=True):
        producto = sum(x * y for x, y in zip(a, b, strict=True))
        norma = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5)
        assert producto / norma > 0.999, (
            f"la grabación ya no corresponde a lo que responde {DATOS['model']} "
            f"para {pregunta!r}. Regrábala: python scripts/record_embeddings.py"
        )
