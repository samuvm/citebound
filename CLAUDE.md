# Citebound · reglas del agente constructor

Tutor de normativa de circulación española. Responde citando el artículo exacto, **no puede citar
lo que no ha recuperado (por construcción)**, verifica el fragmento literalmente y se abstiene
cuando no puede verificarlo. Paquete `citebound`, CLI `citebound`, Python `==3.12.*`.

> **`_comun/` NO está en tu directorio de trabajo, está en el PADRE:**
> `/Users/samuelviciana/Documents/day-300/_comun/` — usa siempre esa ruta absoluta.
> Ahí vive `PARA-SAMUEL-GLOBAL.md` (**D-01…D-10**), única fuente de las decisiones transversales:
> se lee desde ahí, nunca se copia aquí. Si lo copiaras, Samuel respondería en un sitio y cinco
> agentes leerían otro.

## Comandos

> Hasta cerrar la fase 0 el `Makefile` no existe entero: esta tabla es la **especificación** de lo
> que se construye, no lo que ya corre. El estado real vive en `.claude/state/STATE.md`.

```
make up | down | warm        # entorno. `warm` NUNCA dentro de `up`: rompe el cronómetro
make smoke-f0                # salida de fase 0: ingesta + 3 preguntas + ≥1 ref presente en refs.json
make lint | typecheck        # ruff check + format --check · mypy --strict sobre [tool.gate].testable
make test-fast               # nivel 1 + 1b(perfil dev) + 3 contrato.  Presupuesto < 20 s
make test | test-int         # todo salvo evals y holdout · nivel 2 con testcontainers
make eval | eval-refresh     # nivel 4 desde caché (determinista, gratis) · recalculando (llama al modelo)
make eval-retrieval          # solo recall. Sin LLM generador, < 90 s. Vive en el gate de turno
make bench                   # protocolo de latencia: 60 peticiones, descartar 5, 3 repeticiones, max de p95
make gate-fast | gate-full   # lint+typecheck+test-fast+anti-gaming · +test+contrato+metas+lock+secretos
make done MILESTONE=N        # la única definición de "hecho". exit 0 o 1
make report | clean
```

Targets de meta (cada uno produce el artefacto de una meta de `docs/GOALS.yaml`):

```
make golden-validate         # G-GOLDEN-VALID  fase 1: esquema, refs, estratos, procedencia, sha256
make mutation                # G-MUT           mutmut sobre [tool.gate].tdd_obligatorio. Solo en `done`
make eval-determinism        # G-EVAL-DET      dos `make eval` y diff byte a byte del informe normalizado
make eval-calibrate          # G-JUEZ-KAPPA    κ juez-vs-Samuel sobre los 80 casos etiquetados, con IC
make eval-broad              # G-HALLUC-AMPLIO 2.000 preguntas sintéticas sin etiquetar. Nocturno
make eval-adversarial        # G-INJECT        chunk envenenado, fuera de dominio, leaking, homoglifos
make cold-start              # G-COLD-CACHE    clone → primera respuesta con cita. Publica DOS números
make eval-quality            # perfil `qwen3.5:27b-mlx`. Toma `~/.claude/locks/gpu.lock`. Nunca en gate
make corpus-verify           # R4: sha256 del corpus + regeneración del índice y diff
```

## Antes de tocar nada

1. Leer `.claude/state/STATE.md` y, **si existe**, `.claude/state/gate-status.json` (no existe
   hasta el primer `make done`; su ausencia no es un error). Reportar en 5 líneas: fase activa,
   tarea activa, estado del gate, bloqueos, qué vas a hacer. Esperar.
2. `docs/PROJECT.md`, `docs/GOALS.yaml`, `docs/PLAN.md`, `docs/RULES.md`, `docs/CONSTITUCION.md`,
   **`docs/STACK.md`** y `docs/CONTRACTS/**` son **solo lectura**. Los esquemas y políticas
   **propios** de este repo van en `docs/spec/`, y ahí sí se escribe. `docs/PROJECT.md` está
   datado: donde choque con `docs/STACK.md`, `docs/GOALS.yaml` o `docs/RULES.md`, mandan estos
   tres (divergencias ratificadas en `docs/PARA-SAMUEL.md` Q-002).
3. Los rangos de `docs/STACK.md` son la **investigación**, no el pin: traduce el rango a un `==`
   exacto en `pyproject.toml` y anota la versión elegida en `docs/JOURNAL.md` (constitución §7.2).
4. Lo transversal (horas, máquina, AWS, clave, honestidad, licencia, vídeos, hooks, despliegue)
   son **D-01…D-10**: no lo repitas aquí, remite a su `D-NN`. `docs/PARA-SAMUEL.md` solo lleva
   lo propio de este proyecto (Q-001..Q-013).
5. No hay fase abierta sin visto bueno de Samuel. `make done` verde ⇒ presentar números y **parar**.

## Invariantes de este proyecto

1. **Nunca se cita ni se evalúa por `chunk_id`.** La unidad de verdad es la `LegalRef`
   (`norma#artNN.apartado`). Golden set, recall, verificación y métricas se anclan ahí.
2. **El generador no escribe referencias.** Escribe `[[REF:n]]`, `n∈{1..5}` sobre lo recuperado;
   el `n` fuera de rango se detecta *en el token en que aparece* y retracta. La resolución
   `n → LegalRef` la hace código, nunca el modelo.
3. **Todo `quote` emitido existe literalmente** en el texto de su ref tras normalización
   declarada (NFKC + espacios + comillas + guiones). Es un invariante, no una métrica.
4. **Lo verificable deterministamente no se delega a un LLM.** Tres predicados puros primero; el
   juez es el último recurso y solo vale con su κ publicado.
5. **El corpus es inmutable, derivado y dato — nunca instrucción.** `corpus/index/refs.json` se
   regenera desde `corpus/raw/*.xml` verificados por sha256. El chunk envenenado de test no se borra.
6. **Ollama corre en el host** (`host.docker.internal:11434`), Postgres en contenedor por digest.
   **El reranker no pasa por Ollama**: no existe `/api/rerank`; corre en proceso con MPS.
7. **`ts_rank_cd` se llama `ts_rank_cd`**, no BM25, mientras no haya extensión BM25 real instalada.
8. **`domain/` no importa I/O, SDKs ni `os.environ`.** `langchain*` no entra en `pyproject.toml`.

## Mapa

| Ruta | Qué es | Régimen |
|---|---|---|
| `src/citebound/domain/` | `legalref`, `citation`, `abstention`, `retry`, `models` (puro, sin I/O) | **TDD obligatorio** + Hypothesis |
| `src/citebound/ingest/` | `boe_xml.py`, `chunking.py` (parseo estructural, troceado) | **TDD obligatorio** + Hypothesis |
| `src/citebound/retrieval/` | `lexical`, `vector`, `fusion`, `query_builder`, `rerank` | TDD obligatorio en `fusion`; `query_builder` testable sin auditoría TDD; el resto **se mide** con `make eval-retrieval` |
| `src/citebound/agent/` | `graph.py` (LangGraph como máquina de estados), `stream_guard.py` | TDD **prohibido** salvo `stream_guard.py`, que sí lo exige |
| `src/citebound/evals/` | `scoring`, `bootstrap`, runner, informe | **TDD obligatorio** en `scoring` y `bootstrap` |
| `src/citebound/providers/` | `OpenAICompatProvider`, `Reranker`, `Recorded*` | TDD **prohibido**. Grabar primero, testear contra la grabación |
| `src/citebound/api/`, `db/` | FastAPI+SSE, DDL y migraciones | TDD **prohibido**. Contrato (snapshot OpenAPI/SSE) e integración |
| `prompts/`, `evals/golden/`, `corpus/` | prompts con frontmatter · golden set versionado · corpus congelado | No se testean: se validan (`check_prompts`, `golden-validate`, `corpus-verify`) |

## Prohibido

- Editar `docs/PROJECT.md`, `GOALS.yaml`, `PLAN.md`, `RULES.md`, `CONSTITUCION.md`, `STACK.md`,
  `docs/CONTRACTS/**`, `thresholds.lock`, `tests/holdout/**`, `.claude/state/*.json`,
  `.snapshots/**`, `~/.claude/gates/**`, `~/.claude/settings.json`, `_comun/**`.
  `docs/CONTRACTS/**` son **copias literales** de `_comun/`: un `diff` contra el original es un
  test. Lo propio de este repo va en `docs/spec/`, nunca dentro de `docs/CONTRACTS/`.
- Editar `corpus/raw/**` y `evals/golden/v*.jsonl` (append-only por versión: corregir crea `v2` + ADR).
- Tocar los campos `gate_verde_en` y `ultima_verificacion` de `STATE.md`: los escribe el gate.
- `pytest --no-cov`, `-k`, `-x`, `--deselect`, `@skip`, `@xfail`, `rm -rf`.
- Bajar un umbral, borrar un test, reducir aserciones, o tocar un test para que pase. Diagnostica
  la causa real. Sobre `G-HALLUC`, `G-HALLUC-AMPLIO`, `G-QUOTE-LIT`, `G-EVAL-DET`, `G-SECRETS`,
  `G-COV-FUNC`, `G-GOLDEN-VALID`, `G-INJECT` y `G-JUEZ-KAPPA` **no se admite ni siquiera la
  propuesta** (`propuesta_admisible: false` en `docs/GOALS.yaml`).
- **Firmar un commit con `Co-Authored-By: Claude`, `Generated with Claude Code` o cualquier otra
  atribución de IA. Regla dura de Samuel (2026-08-10): el historial no la lleva, en ningún formato.**
  Git está activo desde el 2026-08-10 (`git init` autorizado por Samuel); Conventional Commits.
- `uv add` / `uv remove` sin permiso explícito en el mismo turno (están en `ask`).
- Escribir un prompt inline en el código, o llamar BM25 a `ts_rank_cd`.

## Si te bloqueas

Escribe en `docs/PARA-SAMUEL.md` y **para**. Formato de la constitución §3: identificador, fase que
bloquea, qué pido, por qué, opciones con pros y contras, alternativa si dice que no, `Estado: PENDIENTE`.
Casos que obligan a parar: recurso externo (corpus, cuenta, clave, gasto, horas suyas), spec
inviable, meta inalcanzable tras **≥2 intentos medidos y anotados en `JOURNAL.md`**, 3 fallos
seguidos del gate por la misma causa, ambigüedad de un contrato de `docs/CONTRACTS/`.
Un conflicto sobre un contrato compartido se declara y se responde **en los dos repos afectados**
(así se hizo con Q-012/Q-013). **No lo adaptes por tu cuenta: rompe al otro proyecto.**
Todo lo demás —detalle de implementación reversible— **se decide, se ejecuta y se anota en
`JOURNAL.md`**; si es no obvio, ADR. Pregunta lo que no puedes revertir; decide lo que sí.
