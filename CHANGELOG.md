# Changelog

Todos los cambios relevantes de **Citebound · tutor de normativa** (`citebound-01`).

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto se
adhiere a [Versionado Semántico](https://semver.org/lang/es/).

**Se escribe una entrada por fase cerrada, nunca por sesión ni por cambio suelto.** Una fase se
cierra cuando `make done MILESTONE=N` devuelve 0; hasta entonces no hay entrada. La entrada es
append-only y **lleva los números medidos**, no adjetivos: cada meta activa con su valor, su `n`,
su intervalo de confianza cuando aplique y el artefacto del que sale. Sin eso, el CHANGELOG es una
lista de intenciones y el proyecto pierde justo lo que lo distingue.

Regla que aplica también aquí: cambiar un fichero de `docs/CONTRACTS/` es un evento consciente y
**deja entrada propia**, con la versión del contrato y qué otros proyectos hay que propagar a mano.

## [fase-0] · 2026-08-10 · Esqueleto vertical que camina

`make done MILESTONE=0` → **exit 0**, las doce condiciones de la constitución §5 en verde.
Punto de retorno: commit etiquetado `fase-0`.

### Números medidos

| Condición del gate | Valor | Comando |
|---|---:|---|
| Suite completa | **295 tests** (284 propios + 20 de reserva − deselección) | `pytest tests` |
| Reserva `tests/holdout/` | **20 pasan** | `pytest tests/holdout` |
| Cobertura de línea en `[tool.gate].testable` | **100 %** (mínimo 85) | `make done` |
| Cobertura por función | **0 funciones públicas sin test** | `scripts/check_function_coverage.py` |
| Mutación | **587/588 muertos, 100 %** (mínimo 70) | `mutmut run` |
| `G-HALLUC` | **0** sobre n=15 refs emitidas | `make eval` |
| `G-SECRETS` | **0** hallazgos nuevos | `detect-secrets` |
| Deuda | 0 marcas, 0 `skip`/`xfail` | `make done` |
| Salida de fase | `make smoke-f0` → **exit 0**, 10,0 s | `make smoke-f0` |

Entorno: MacBook Pro M4 Max 36 GB · Python 3.12.4 · Ollama 0.32.7 en el host ·
PG18 + pgvector 0.8.6 por digest · `bge-m3` 1024 dim · `index_version` `v1-bge-m3-1024` ·
corpus `BOE-A-2003-23514` consolidado 2026-07-31, sha256 `1105a26b…40072`.

**El informe de eval dice en `notes` que `G-HALLUC = 0` hoy es cero por construcción
trivial** —no hay generador en la fase 0— y no por la cita cerrada, que llega en la fase 3.
Con n=15 la cota superior al 95 % es ~20 %. Publicarlo sin eso sería lo que D-06 prohíbe.

### Añadido

- **Corpus congelado**: RD 1428/2003 desde la API del BOE, con sha256 en `corpus/MANIFEST.yaml`.
  236 preceptos → **235 chunks** (el artículo 51, derogado, queda fuera), 0 refs duplicadas.
- `domain/legalref.py`, `ingest/boe_xml.py`, `ingest/chunking.py` con TDD y Hypothesis.
- `db/` sobre el contrato v2, `providers/embeddings.py` con doble grabado,
  `retrieval/vector.py`, `api/app.py`, `cli.py`, `compose.yaml` y el `Makefile` con el gate.
- `scripts/`: `done.py` (las doce condiciones), `check_function_coverage.py`,
  `check_no_chunk_ids.py` (R1), `eval_f0.py`, `smoke_f0.py`, `record_embeddings.py`.
- **`tests/holdout/`**, escrito por el subagente `qa-adversario` sin leer `tests/`.

### Corregido

- **`_NORMA`, `_DESIGNADOR` y `_APARTADO` anclaban con `$`**, que en Python casa también
  antes de un salto de línea final: `LegalRef("RD-1428/2003", "34\n")` se aceptaba mientras
  el docstring prometía lo contrario. **Lo encontró la reserva, no la suite propia.** Se
  cambia a `\Z`. No era alcanzable por `parse`, que hace `strip`; sí construyendo directo.
- El identificador del corpus de Q-001 (`BOE-A-2003-21806`) no existe: el correcto es
  `BOE-A-2003-23514`.

### Contrato · `chunks-ddl.sql` v1 → v2

**Evento consciente de cambio de contrato compartido.** Propagado a mano a `_comun/CONTRACTS/`
y a `docs/CONTRACTS/` de **`citebound-01` e `indexkeeper-04`**, byte a byte idénticos
(sha256 `5f3266c6c08c2cf3da5ca19087edf975be2478faa6a33abf6ae6331e1c895d75`). Anotado también en el
CHANGELOG del 04. Decidido por Samuel en los dos buzones a la vez: Q-012 = **A** y Q-013 = **A2+B1**
aquí, espejo de Q-002 y Q-003 allí. Razonamiento y coste en
`docs/adr/018-chunks-ddl-v2-y-conmutacion.md`.

- **`chunk_id` deja de incluir la posición.** De `sha256(doc_id:ordinal:content_hash)[:24]` a
  `blake2b(doc_id ‖ content_hash ‖ occurrence, digest_size=16)`. Con el ordinal dentro del hash,
  insertar un párrafo cambiaba todos los `chunk_id` del documento y hacía `G-INCR-2` del 04
  inalcanzable **por construcción**. Aquí no afecta a ninguna métrica: todo se ancla en `legal_ref`
  (R1), nunca en `chunk_id`.
- **Nueva columna `occurrence`**, que desempata contenido idéntico dentro de un mismo documento —en
  texto legal hay apartados cortos repetidos literalmente—. `ingest/chunking.py` gana un invariante
  y una propiedad Hypothesis. **`ordinal` sigue siendo columna**, así que la propiedad «la
  concatenación ordenada de los chunks de un artículo reproduce su texto exacto» queda intacta.
- **Campos legales opcionales** en el contrato compartido: entra `ref TEXT NOT NULL` genérico y
  `norma`/`articulo`/`apartado` pasan a nullables. `legal_ref` sigue siendo columna generada y
  **nunca nula**: cae a `ref` cuando el corpus no es normativo. Condición de este proyecto: su DDL
  propio añade `CHECK (norma IS NOT NULL)` con test de contrato, o `G-HALLUC` mediría contra un
  conjunto roto.
- **Conmutación de índice por vista.** Desaparecen `index_version.is_active` y su índice único
  parcial; entran la tabla `index_alias` y la vista `chunks_active`. Permite migrar de dimensión de
  embedding sin parar y deshacer con `DROP TABLE` en vez de `DELETE` de millones de filas. Condición
  de este proyecto, escrita en el propio contrato: **el informe de eval registra el destino físico
  resuelto** (`index_alias.index_version` + `physical_table`), nunca el alias, o `G-EVAL-DET`
  dejaría de significar nada.
- **Verificado ejecutándolo**, no solo leyéndolo: el DDL corre entero contra
  `pgvector/pgvector@sha256:69167330…` (PG18 + pgvector 0.8.6) con `ON_ERROR_STOP=1`, crea las 4
  tablas, la vista y los 8 índices; `legal_ref` compone `RD-1428/2003#art3.1` con norma y cae a
  `manual-x#sec4` sin ella; y `UNIQUE (index_version, doc_id, content_hash, occurrence)` rechaza el
  duplicado exacto.
- **Desbloquea** las tareas `0.4` (`ingest/chunking.py`) y `0.5` (`db/ddl.sql`).

### Gobierno, escrito antes de la primera línea de código
- Capa de gobierno inicial: `CLAUDE.md`, `docs/GOALS.yaml`, `docs/PLAN.md`, `docs/RULES.md`,
  `docs/PARA-SAMUEL.md`, `docs/JOURNAL.md`, `docs/adr/000-plantilla.md`, `.claude/state/STATE.md`.
- Copias de `docs/CONSTITUCION.md` y `docs/STACK.md`, y de los contratos que aplican a este
  proyecto: `chunks-ddl.sql` (v1), `retrieval-metrics.md` (v1), `otel-genai.md` (v1) y
  `eval-report.schema.json` (v1). No se copian los que no aplican (`pricing-table.md`, 02 → 04).
- `docs/CONTRACTS/goals.schema.json` (v1) y `docs/CONTRACTS/README.md`, nuevos en `_comun/`.
- `docs/PARA-SAMUEL.md` Q-012 y Q-013: entradas **espejo** de Q-002 y Q-003 de `indexkeeper-04`
  sobre `docs/CONTRACTS/chunks-ddl.sql` (el `chunk_id` incluye el ordinal; `index_version.is_active`
  frente a vista `chunks_active` + `index_alias`), con el impacto medido en este proyecto. Un
  conflicto de contrato compartido declarado en un solo repositorio no está declarado.
- `docs/RULES.md` R20 y §2.3: la corrección múltiple de la puerta es Holm-Bonferroni, con el motivo
  (controla la FWER; un falso bloqueo acaba desactivando la puerta). Benjamini-Hochberg queda para
  el panel de diagnóstico, no para la puerta.

### Cambiado
- Resincronizadas todas las copias de `_comun/` tras el cambio de la capa común: `CONSTITUCION.md`
  (topes de tamaño, `docs/CONTRACTS/` vs `docs/spec/`, alcance de `==`, §8 reescrita),
  `retrieval-metrics.md` (§4 admite y recomienda `holm`) y `eval-report.schema.json`. Idénticas
  byte a byte al original; el `diff` es un test.
- `docs/GOALS.yaml` reescrito para cumplir `docs/CONTRACTS/goals.schema.json` v1: umbrales
  estructurados `{operador, valor, unidad}` con `adicionales`, `clase` sustituido por `tipo` +
  `requiere` + `propuesta_admisible`, `pareja`/`condicionada_a` movidos a `nota`, y
  `hardware_referencia` declarado por las metas de latencia. Ningún umbral cambia de valor.
- Las decisiones transversales dejan de preguntarse aquí: viven en `_comun/PARA-SAMUEL-GLOBAL.md`
  como D-01..D-09. `docs/PARA-SAMUEL.md` las remite y renumera lo propio como Q-001..Q-013.

---

<!--
Plantilla de una fase cerrada. Copiar tal cual y rellenar.

## [fase-N] · AAAA-MM-DD · <nombre de la fase>

`make done MILESTONE=N` → exit 0.  Snapshot: `.snapshots/AAAA-MM-DD-faseN/`

### Números medidos
| Meta | Umbral | Valor | n | IC95 | Artefacto |
|---|---:|---:|---:|---|---|
| G-XXXX | >= 0,90 | 0,00 | 000 | [0,00 – 0,00] | evals/reports/... |

Entorno: hardware declarado · Python 3.12.x · determinista: si/no · index_version: ... ·
modelos {generador, juez, embeddings, reranker} con su digest · semilla: ...

### Añadido / Cambiado / Corregido / Eliminado
- ...

### Decisiones
- ADR-NNN · <título>

### Deuda declarada
- <TODO/FIXME que quedan, y por qué se aceptan> (tope: 10 en `src/`)
-->
