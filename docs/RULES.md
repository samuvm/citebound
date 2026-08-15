# Reglas propias de citebound-01

> **Solo lectura para el agente.** Complementa `docs/CONSTITUCION.md`; nada de aquí puede
> contradecirla. Lo que no esté aquí, se rige por ella.
>
> Cada invariante lleva **el comando que lo verifica**. Una regla sin comprobación mecánica es
> una sugerencia, y las sugerencias se erosionan en dos semanas.
>
> Columna *gate*: **B** = gate de paso (`PostToolBatch`) · **C** = gate de turno (`Stop`) ·
> **done** = `make done` · **up/bench** = el target correspondiente.

---

## 1. Invariantes verificables

| # | Invariante | Cómo se verifica | Gate |
|---|---|---|:--:|
| **R1** | **Ninguna cita se identifica por `chunk_id`.** Toda cita es una `LegalRef` estable (`norma#artNN.apartado`) | `scripts/check_no_chunk_ids.py`: prohíbe la subcadena `chunk_id` en `evals/golden/**`, en el modelo `Citation` y en cualquier propiedad de respuesta del OpenAPI | C |
| **R2** | **El generador no escribe referencias: escribe `[[REF:n]]` con `n∈{1..5}`** | `tests/unit/test_stream_guard.py` (≥11 casos) + `tests/contract/test_prompt_forbids_refs.py`: el prompt de respuesta contiene la instrucción y ningún prompt menciona formatos de artículo | B |
| **R3** | **Todo `quote` emitido existe literalmente en el texto de su ref**, tras la normalización declarada (NFKC · colapso de espacios · comillas tipográficas → rectas · guiones Unicode → `-`) | `G-QUOTE-LIT == 1,00` en `make eval` + ≥20 casos unitarios del nodo `verify` | C, done |
| **R4** | **El corpus es inmutable y derivado.** `corpus/index/refs.json` se regenera solo desde `corpus/raw/*.xml`, cuyos sha256 están en `corpus/MANIFEST.yaml`. Nadie edita el corpus a mano | `make corpus-verify` (sha256 de cada fichero + regeneración del índice y diff) + `permissions.deny` de Edit/Write sobre `corpus/raw/**` | C |
| **R5** | **Los prompts viven en `prompts/*.md` con frontmatter completo.** Nunca inline | `scripts/check_prompts.py`: (a) AST — ningún literal de cadena en `src/` de >200 caracteres que contenga `\n\n`; (b) todo `.md` tiene `id`, `version`, `modelo_destino`, `temperatura`, `cambios`; (c) todo `prompt_id` referenciado en código existe | B |
| **R6** | **`domain/` no importa I/O ni SDKs** | `scripts/check_layering.py` (AST): `src/citebound/domain/**` no puede importar `psycopg`, `httpx`, `requests`, `ollama`, `openai`, `boto3`, `langgraph`, `fastapi`, `sentence_transformers`, `torch`, `mlflow`, ni leer `os.environ` | B |
| **R7** | **`langchain*` no aparece en `pyproject.toml`.** LangGraph se usa **solo como máquina de estados**; el retrieval es SQL propio; el LLM pasa por `LLMProvider` | `scripts/check_deps.py` con allowlist de paquetes raíz | B |
| **R8** | **El reranker no pasa por Ollama.** Corre en proceso, `sentence-transformers`, backend MPS | `tests/contract/test_reranker_port.py`: aserción **negativa** de que `OpenAICompatProvider` no implementa `Reranker` + `grep -r "api/rerank" src/` vacío | B |
| **R9** | **Ollama en el host, Postgres en contenedor por digest** | `tests/contract/test_compose.py` parsea `compose.yaml` y falla si hay un servicio con imagen `ollama/*` o una imagen referenciada por tag; `make up` hace `curl -sf $OLLAMA_BASE_URL/api/version` y aborta con mensaje accionable si no responde | up, C |
| **R10** | **Nunca dos LLM cargados a la vez.** `OLLAMA_MAX_LOADED_MODELS=1`. `make eval-quality` (27b) y cualquier trabajo del proyecto 04 son **mutuamente excluyentes** | `scripts/gpu-lock.sh` toma `~/.claude/locks/gpu.lock` con el PID y aborta si está tomado; `make eval-quality` comprueba `ollama ps` antes de arrancar | eval-quality |
| **R11** | **Toda medida de latencia es en caliente y con protocolo** (`bench/protocol.md`): 60 peticiones, se descartan las 5 primeras, 3 repeticiones, se publica el **máximo de los tres p95**, loopback, streaming activo, distribución de longitud de prompt declarada | `scripts/bench_ttft.py` sale con 1 si el modelo no está residente (`ollama ps`), si `OLLAMA_KEEP_ALIVE < 10m`, si el portátil no está enchufado, o si detecta *throttling* térmico entre repeticiones | bench |
| **R12** | **El golden set es append-only por versión.** Corregir un caso crea `v2` + ADR; nunca se reescribe `v1` | `evals/golden/CHECKSUMS` verificado en `make eval` + `permissions.deny` de Edit sobre `evals/golden/v*.jsonl` | C, done |
| **R13** | **El juez nunca es el modelo generador**, ni de la misma familia | `scripts/check_judge_model.py`: falla si `judge.model == generator.model` o si comparten prefijo de familia | B |
| **R14** | **`make eval` es determinista y gratis desde caché.** `make eval-refresh` es lo único que llama al modelo | `make eval-determinism`: dos ejecuciones y `diff` byte a byte del informe normalizado (sin timestamps) → `G-EVAL-DET` | done |
| **R15** | **Todo informe de eval registra la procedencia completa**: sha256 del golden set, sha256 del `MANIFEST` del corpus, `id`+`version`+sha256 de cada prompt, modelo generador y su digest, modelo juez y su digest, `index_version`, semilla | El JSON Schema de `docs/CONTRACTS/eval-report.schema.json` con `required`; `make eval` falla si falta un campo | done |
| **R16** | **La abstención se evalúa en los dos sentidos y siempre juntas.** `G-CITA-PRECISION` no puede subir a costa de `G-COBERTURA` | `goals-check.sh` trata el campo `pareja:` de `GOALS.yaml` como **una sola condición atómica** | C, done |
| **R17** | **Ningún cambio en `retrieval/` se cierra sin número.** Si el turno tocó `src/citebound/retrieval/**` y no hay informe nuevo en `evals/reports/` posterior al primer cambio, el turno no cierra | Hook de capa C: comparación de mtimes + presencia del campo `G-RECALL5` en el informe | C |
| **R18** | **El corpus es dato, nunca instrucción.** El chunk envenenado permanece sembrado en el corpus de test | `tests/adversarial/test_injection.py` con `RecordedProvider`: el sistema sigue citando y no obedece. **Nunca se borra ni se marca `skip`** | C, done |
| **R19** | **`ts_rank_cd` se llama `ts_rank_cd`.** La palabra "BM25" solo puede aparecer en el repo si hay una extensión BM25 real en `pyproject.toml`/`compose.yaml` | `scripts/check_bm25_honesty.py`: `grep -ri "bm25"` en `README.md`, `src/`, `docs/` → si hay coincidencias sin extensión real instalada, rojo | C |
| **R20** | **La corrección por comparaciones múltiples de la puerta es Holm-Bonferroni**, nunca Benjamini-Hochberg. Ver §2.3 | `goals-check.sh` lee `comparacion.correccion_multiple` de `GOALS.yaml` y falla si no es `holm`; el informe de eval lo registra y el JSON Schema lo valida contra la enum del contrato | done |

---

## 2. Tres contratos internos que no son metas pero gobiernan el diseño

### 2.1 Presupuesto de latencia por etapa

`p95 TTFT ≤ 1,5 s` es inservible sin repartirlo. Cada etapa tiene además su **timeout duro de
nodo** en LangGraph (`add_node(..., timeout=)`).

| Etapa | Presupuesto p95 | Timeout duro |
|---|---:|---:|
| Embedding de la consulta | 40 ms | 300 ms |
| Búsqueda híbrida (SQL, 1 round-trip) | 90 ms | 600 ms |
| Rerank 30 → 5 (MPS, en proceso) | 400 ms | 1200 ms |
| Prefill + primer token (`qwen3.5:9b-mlx`) | 700 ms | 4000 ms |
| Overhead FastAPI/SSE | 60 ms | — |
| **TTFT total** | **1290 ms** | margen 210 ms |

**Una etapa que supera su presupuesto marca ámbar en `make bench` aunque el total pase.** El
margen es de donde vienen las regresiones de dentro de tres semanas.

### 2.2 Contrato SSE, y el conflicto que resuelve

`POST /ask` promete streaming **y** "verificar la cita antes de responder". Son incompatibles: si
verificas antes de emitir, el TTFT es el tiempo de generación completa. Resolución adoptada:

```
event: sources     ← inmediato tras rerank (~530 ms). Refs y títulos. Lo primero que ve el usuario
event: token       ← borrador con marcadores [[REF:n]], n∈{1..5} validado en vuelo
event: retract     ← n fuera de rango o quote no literal. Motivo tipado. Dispara reintento (≤2)
event: citations   ← al final: refs resueltas + quote + offsets, ya verificadas
event: abstain     ← salida de primera clase, con motivo tipado
event: done        ← latencias por etapa, prompt_id+version, index_version, modelo+digest
event: error
```

Se publican **dos** latencias, no una: `TTFS` (hasta `sources`) y `TTFT` (hasta el primer
`token`). Medir el TTFT hasta `sources` sería hacer trampa, y eso se dice en el README.

### 2.3 La corrección múltiple de la puerta es Holm, y el motivo importa

`docs/GOALS.yaml :: comparacion.correccion_multiple` vale **`holm`**, que es además el valor por
defecto de `docs/CONTRACTS/retrieval-metrics.md` §4. No es una preferencia de estilo:

**Holm-Bonferroni controla la FWER** —la probabilidad de bloquear **al menos una vez** sin causa—
y eso es exactamente lo que arruina una puerta de calidad. Este proyecto vigila más de tres
métricas bloqueantes a la vez desde la fase 3 (`G-CITA-PRECISION`, `G-COBERTURA`, `G-ABST-FP`,
`G-ABST-FN`, `G-QUOTE-LIT`, `G-TTFT`), así que la corrección es obligatoria. Un falso bloqueo
cuesta una tarde y, sobre todo, erosiona la confianza: **la puerta que bloquea sin motivo se acaba
desactivando**, y entonces no hay puerta. Holm es además uniformemente más potente que Bonferroni
y no exige supuestos adicionales, así que no hay razón para preferir Bonferroni.

**Benjamini-Hochberg controla la FDR**, no la FWER, y es la elección correcta cuando se exploran
muchas métricas *informativas* y un falso positivo aislado no bloquea nada: el desglose por
materia y `G-CITA-F1`, que se publican y no bloquean. Ahí se admite; **en la puerta, no**.

---

## 3. Qué se testea, qué se mide, y dónde vive TDD

| Módulo | Determinista | Régimen | Motivo |
|---|:--:|---|---|
| `domain/{legalref,citation,abstention,retry,models}` | sí | **TDD obligatorio** + Hypothesis + cobertura por función | Puro, especificación clara. `legalref` es el tipo del que dependen parser, troceado, scoring, verificador y golden set: equivocarse ahí es equivocarse en todo |
| `ingest/{boe_xml,chunking}` | sí | **TDD obligatorio** + Hypothesis | El árbol del BOE es una especificación escrita; el troceado tiene un invariante de no pérdida |
| `retrieval/{fusion,query_builder}` | sí | **TDD obligatorio** (fusion) / testable (query_builder) | RRF es una función pura de dos listas; el constructor SQL es una cadena verificable |
| `retrieval/{lexical,vector,rerank}` | no | **Se miden** con `make eval-retrieval`, no se testean unitariamente | Su calidad es una distribución sobre un corpus, no un booleano |
| `agent/stream_guard` | sí | **TDD obligatorio** + Hypothesis | Es una función pura sobre un buffer de tokens, y es lo que hace imposible la alucinación de referencia |
| `agent/graph` | no | **TDD prohibido.** Integración determinista con `RecordedProvider` + evals | El grafo se prueba por su comportamiento observable: reintento, abstención, error, timeout |
| `evals/{scoring,bootstrap}` | sí | **TDD obligatorio** + Hypothesis. **Se congela antes de anotar el primer caso golden** | Anotar 190 casos contra un scorer que va a cambiar tira 12 horas humanas |
| `providers/*` | no | **TDD prohibido.** Contrato + grabaciones VCR | Ver §3.1 |
| `api/*`, `db/*` | parcial | **TDD prohibido.** Contrato (snapshot OpenAPI y SSE) + integración con testcontainers | La forma la fija FastAPI y el motor, no tú |
| `prompts/*` | no | **TDD prohibido.** Se validan (`check_prompts.py`) y se miden (evals) | Forzar TDD sobre un prompt es teatro |

### 3.1 Por qué TDD está prohibido en `providers/` y `agent/`

Escribir un test antes de conocer la forma real de la respuesta del proveedor produce un mock que
codifica una **API imaginada**, y el test verde certifica la imaginación. Es el mecanismo exacto
por el que una suite se vuelve un obstáculo y acaba desactivada.

**El orden correcto ahí es el inverso: grabar primero** (una traza real con `--refresh`),
**escribir el test contra la grabación después.** La grabación se versiona en el repo, y desde ese
momento el test es determinista, gratuito y prueba el flujo real.

### 3.2 Propiedades Hypothesis obligatorias

**La ausencia de propiedad es un fallo del gate, no una omisión.** Perfiles: `dev` = 25 ejemplos
(gate B) · `gate` = 100 (gate C) · `nightly` = 1000.

| Módulo | Propiedades exigidas |
|---|---|
| `domain/legalref` | `format(parse(s)) == normalize(s)` · `match` reflexiva · `match(APARTADO)` implica `match(ARTICULO)`, **no al revés** |
| `ingest/chunking` | la concatenación ordenada de los chunks de un artículo reproduce **exactamente** su texto · todo chunk tiene ref no vacía · ningún chunk cruza frontera de artículo |
| `retrieval/fusion` | idempotencia con lista única · invarianza ante permutación de las listas de entrada cuando no hay empates · monotonía: empeorar el rango en todas las listas nunca mejora el rango fusionado |
| `agent/stream_guard` | todo prefijo de un stream válido es aceptado · todo stream con `n∉{1..5}` se rechaza **en el token en que aparece**, no después |
| `domain/retry` | termina siempre · nunca más de 2 reintentos · `ABSTAIN` es absorbente |
| `evals/bootstrap` | misma semilla → mismo IC · muestras idénticas → el IC contiene 0 · el IC contiene la diferencia observada |
| `domain/knowledge` (fase 6) | monotonía tras acierto · cotas [0,1] · el selector nunca repite una pregunta dominada |

### 3.3 Presupuestos de tiempo

`make test-fast` **< 20 s** — es la condición para activar el hook de capa B (constitución §9.6).
Si se pasa: `pytest -n auto`, mover casos a `integration/`, o recortar el perfil de Hypothesis.
**El gate no se relaja; el test se arregla.**
`make eval-retrieval` **< 90 s** — por eso puede vivir en el gate de turno.
`make eval` desde caché **< 3 min**. `make eval-refresh` no tiene presupuesto y **nunca** corre en
un gate.

---

## 4. `[tool.gate]` de este proyecto — literal, para copiar a `pyproject.toml`

```toml
[tool.gate]
testable = [
  "src/citebound/domain",
  "src/citebound/ingest/boe_xml.py",
  "src/citebound/ingest/chunking.py",
  "src/citebound/retrieval/fusion.py",
  "src/citebound/retrieval/query_builder.py",
  "src/citebound/agent/stream_guard.py",
  "src/citebound/evals/scoring.py",
  "src/citebound/evals/bootstrap.py",
]
tdd_obligatorio = [
  "src/citebound/domain",
  "src/citebound/ingest/boe_xml.py",
  "src/citebound/ingest/chunking.py",
  "src/citebound/retrieval/fusion.py",
  "src/citebound/agent/stream_guard.py",
  "src/citebound/evals/scoring.py",
  "src/citebound/evals/bootstrap.py",
]
tdd_prohibido = [
  "src/citebound/agent/graph.py",
  "src/citebound/api",
  "src/citebound/providers",
  "prompts",
]
excluido = [
  "src/citebound/api",
  "src/citebound/providers",
  "src/citebound/db",
  "prompts",
]
cobertura_linea_min  = 85
mutantes_muertos_min = 70
sin_test_requerido = [
  # Cada entrada exige motivo. El gate RECHAZA una entrada sin motivo.
  { symbol = "domain.models.*.__repr__", motivo = "generado por Pydantic" },
]
```

**Qué significa aquí "un test unitario por cada función", en tres niveles automáticos:**

1. **Cobertura por función** (todo `testable`): `pytest tests/unit --cov --cov-context=test` +
   `scripts/check_function_coverage.py` recorre el AST y exige que **toda función pública (sin `_`
   inicial) tenga ≥1 contexto de test que la ejerza directamente**. No se mide por convención de
   nombres: eso se falsea trivialmente. Cero excepciones fuera de `sin_test_requerido`.
2. **TDD auditable** (solo `tdd_obligatorio`): no basta con que el test exista, tiene que haber
   existido **antes**. `tdd-guard.sh` escribe `.claude/state/tdd-log.jsonl` con
   `{fichero_test, sha_test, timestamp_rojo, causa_rojo, timestamp_verde}` y **distingue rojo por
   aserción de rojo por `ImportError`/`SyntaxError`**, que no es rojo sino ruido. `make done` exige
   una entrada rojo→verde por función pública.
3. **Propiedades obligatorias**: §3.2.

---

## 5. Errores típicos de este dominio que el agente debe evitar

1. **Medir recall sobre `chunk_id`.** Invalida el golden set entero en cuanto cambia el troceado,
   que es justo lo que pasa en la fase 2. Se ancla siempre en `legal_ref` (R1).
2. **Asumir que el reranker se sirve por Ollama.** No existe `/api/rerank`, ni en 0.32.6. Los
   modelos reranker están en su librería, y eso confunde. Corre en proceso con MPS (R8).
3. **Meter Ollama en `compose.yaml`.** Docker en macOS no pasa la GPU: 5-20× más lento, y la
   promesa de `compose up` en 10 minutos se cae sin que nadie entienda por qué (R9).
4. **Llamar BM25 a `ts_rank_cd`.** No normaliza por longitud de documento ni satura frecuencia de
   término. Es la imprecisión que un revisor técnico detecta y que resta credibilidad al resto del
   README. Solo se puede llamar BM25 si el spike adopta una extensión BM25 real (R19).
5. **Usar el mismo modelo como generador y como juez.** Infla `faithfulness` sistemáticamente.
   Familia distinta, no solo tamaño distinto (R13).
6. **Poner Ragas en el gate.** Está congelado desde febrero de 2026. El riesgo no es técnico, es
   de credibilidad: en una entrevista, "¿sabías que Ragas lleva medio año parado?" deja al
   proyecto sin respuesta.
7. **Escribir DAGs, prompts o llamadas de memoria con hábitos de la versión anterior.** `pytest 9`
   y `mypy 2.x` son saltos de *major*; `langgraph-prebuilt==1.0.2` publicó un cambio rompedor sin
   restricción de versión. Todo con `==`, y comprobar la API real antes de escribir.
8. **Sacar la jerarquía del corpus de un PDF.** El BOE publica XML consolidado con la jerarquía
   exacta y sin pérdida. Un parser de *layout* mete error evitable en la métrica que declaras con
   tolerancia cero. Docling se queda en el proyecto 04, donde el reto sí es el PDF sucio.
9. **Verificar la cita antes de emitir el primer token.** Rompe el TTFT por diseño. El contrato
   SSE de §2.2 es la resolución; cualquier otra vuelve a caer en la misma trampa.
10. **Fabricar la evidencia de `G-REVERSION` al final.** Se recoge de lo que pase de verdad en las
    fases 2-4. Por eso se anota en `JOURNAL.md` con la marca `<!-- reversion -->` **desde la fase 2**.
11. **Dar por hecho que "abstenerse" es gratis.** Con `G-CITA-PRECISION` sola, la estrategia óptima
    es abstenerse siempre. Las parejas de `GOALS.yaml` existen por eso y el gate las evalúa juntas (R16).
12. **Bajar `hnsw.ef_search` por defecto o dejarlo implícito.** El contrato de `chunks-ddl.sql`
    fija `m=16`, `ef_construction=64` y exige declarar `SET hnsw.ef_search` en la consulta: sin eso,
    dos proyectos miden recall sobre estructuras distintas y los números no comparan.
13. **Inventar una métrica y llamarla como la del contrato.** `precision_cita`, `recall@k` y las
    dos de abstención están definidas literalmente en `docs/CONTRACTS/retrieval-metrics.md` §2, y
    son lo que hace comparables los README de 01, 02 y 04. Una métrica propia es legítima —
    `G-CITA-F1` lo es— pero **se publica con nombre propio y no bloquea**, porque un contrato
    compartido no se improvisa: se cambia de versión y se propaga a mano a los tres repos (Q-007).
