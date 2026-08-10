# Plan de fases · citebound-01

> **Solo lectura para el agente.** Cambiar una fase, su criterio de salida o su presupuesto se
> propone en `docs/PARA-SAMUEL.md` (tipo `cambiar-plan`) y lo aplica Samuel.
>
> Los "hitos" del `PROJECT.md` se renumeran aquí como **fases** para casar con
> `bloqueante_desde_fase` de `GOALS.yaml` y con `make done MILESTONE=N`. La correspondencia es
> uno a uno: hito 0 → fase 0, …, hito 5 → fase 5. La fase 6 (BKT) no existía como fase separada
> en el `PROJECT.md`; se separa aquí y se degrada a ampliación (motivo en la fase 6).
>
> Notación: **[S]** estrictamente secuencial · **[P]** paralelizable · `h-ag` horas de agente ·
> `h-hu` horas humanas irreducibles (las que Samuel no puede delegar en ningún agente).

---

## 1. Tabla de fases

| # | Nombre | Tipo | Entregable concreto | Criterio de salida (comando) | Tests exigidos | Metas que activa | h-ag | h-hu | Paralelismo |
|:-:|---|:-:|---|---|---|---|---:|---:|---|
| **0** | Esqueleto vertical que camina | **NÚCLEO** | Una rebanada fea y completa: una norma, 1 artículo = 1 chunk, solo vectorial, sin reranker, sin agente, sin streaming. `citebound ask "..."` devuelve texto y ≥1 `LegalRef` que existe | `make up && make warm && make smoke-f0` → exit 0.<br>`smoke-f0` = ingesta del corpus + 3 preguntas fijas + aserción de que cada respuesta trae ≥1 ref presente en `corpus/index/refs.json` | ≥8 unitarios del parser XML (apartados numerados, apartados con letras, artículo *bis*, artículo derogado, disposición adicional/transitoria/final, anexo) · Hypothesis en `legalref` (`format(parse(s)) == normalize(s)`) · Hypothesis en `chunking` (la concatenación ordenada de los chunks de un artículo reproduce su texto exacto) · contrato del DDL (snapshot) · integración con testcontainers: ingerir dos veces no duplica | `G-HALLUC`, `G-SECRETS` | 25-35 | 1-2 | **[S]** |
| **1** | Scoring primero, golden set después | **NÚCLEO** | `evals/scoring.py` + `evals/schema.py` + `evals/bootstrap.py` **congelados antes de anotar nada** · generación asistida · TUI de revisión · `evals/golden/v1.jsonl` + `CHECKSUMS` + `STRATA.md` | `make golden-validate` → exit 0 | TDD completo del scoring con la tabla de casos del contrato (múltiples citas, apartado, dos artículos, abstención) · Hypothesis en `bootstrap` (misma semilla → mismo IC; muestras idénticas → el IC contiene 0) · contrato: todo caso valida contra el esquema Pydantic | `G-GOLDEN-VALID`, `G-COV-FUNC` | 20-30 | **10-16** | 1a **[P]** con 0.3-0.4; 1b-1d **[S]** |
| **2** | Retrieval híbrido | **NÚCLEO** | `retrieval/{lexical,vector,rerank,fusion,pipeline}.py` + `db/{fts,hnsw}.sql`. RRF `k=60`. Filtro por materia | `make eval-retrieval` → `G-RECALL5 ≥ 0,90` y `G-RECALL30 ≥ 0,97`, en < 90 s | RRF con listas conocidas + Hypothesis (idempotencia con lista única, invarianza ante permutación sin empates, monotonía del rango fusionado) · constructor SQL: tests sobre la cadena generada + test de que ningún parámetro se interpola por formato · integración con datos sembrados de resultado conocido · contrato de los tres puertos con `Recorded*` | `G-RECALL5`, `G-RECALL30`, `G-COV-LINE` | 35-50 | 1 | **[P] en 3 ramas** tras congelar puertos |
| **3** | Agente: cita cerrada, verificación, abstención | **NÚCLEO** | Grafo LangGraph `retrieve → rerank → draft → verify → {emit ⏐ retract→retry(≤2) ⏐ abstain}` + contrato SSE completo | `make eval` (pareja `G-CITA-PRECISION`+`G-COBERTURA`, pareja `G-ABST-FP`+`G-ABST-FN`, `G-HALLUC=0`, `G-QUOTE-LIT=1,00`) **y** `make bench` (`G-TTFT` p95 ≤ 1500 ms y ninguna etapa fuera de su presupuesto) | ≥20 unitarios del verificador (ref inexistente · ref no recuperada · `n=0` · `n=6` · quote con un carácter cambiado · guion tipográfico · comillas curvas · quote que cruza dos artículos · apartado inventado sobre artículo real · quote vacío · quote de 3 caracteres) · Hypothesis en `retry` (termina siempre, nunca >2, `ABSTAIN` absorbente) y en `stream_guard` · integración del grafo con `RecordedProvider`: reintento exitoso, reintento agotado, error del proveedor, timeout de nodo, corpus sin resultados · contrato: snapshot SSE y OpenAPI | `G-CITA-PRECISION`, `G-COBERTURA`, `G-QUOTE-LIT`, `G-ABST-FP`, `G-ABST-FN`, `G-TTFT`, `G-MUT` (`G-CITA-F1` se mide y publica; no bloquea) | 40-55 | 0-2 | **[S]** |
| **4** | Evals, juez y determinismo | **NÚCLEO** | `make eval` determinista desde caché · informe conforme a `docs/CONTRACTS/eval-report.schema.json` · caché de juicios versionada · calibración del juez con κ e IC · MLflow como Prompt Registry + trazas OTel | `make eval-determinism && make eval-calibrate && make eval-refresh --dry-run` → exit 0 | Contrato: el informe valida contra el JSON Schema y falla si falta un campo de procedencia · unitarios del cacheador de juicios (hash estable ante reordenación de claves) · integración: dos ejecuciones producen informes normalizados idénticos | `G-EVAL-DET`, `G-FAITH-JUEZ`, `G-TTVA` (`G-JUEZ-KAPPA` se mide y publica; no bloquea) | 25-35 | **4-6** | **[P] parcial** con la fase 3 |
| **5** | Endurecimiento y publicación | **NÚCLEO** | Suite adversarial · OTel con los atributos literales del contrato + capa de traducción · límite de tasa en `/ask` y `GET /metrics` · `make cold-start` · README con los números medidos, cotas superiores y el *caveat* de la cita cerrada | `make done MILESTONE=5` → exit 0 (incluye `make eval-adversarial`, `make eval-broad`, `make cold-start` y `check_reversion_evidence.py`) | `tests/adversarial/` permanentes (chunk envenenado sembrado, fuera de dominio, prompt leaking, homoglifos) · contrato OTel: atributos obligatorios presentes, cero nombres propios dentro de `gen_ai.*` · e2e de humo: `compose up`, tres preguntas reales, hay streaming y hay citas | `G-HALLUC-AMPLIO`, `G-INJECT`, `G-COLD-CACHE`, `G-REVERSION` | 30-45 | **3-5** | **[S]** |
| **6** | BKT y selector de bloque | **AMPLIACIÓN** | `domain/knowledge.py` (BKT en NumPy, 4 parámetros) + `domain/selector.py`, ambos dominio puro. Simulador determinista con semilla como banco de pruebas del selector. Endpoints `/session/*` solo si sobra tiempo | `pytest tests/property/test_knowledge.py tests/property/test_selector.py` → exit 0. **Timebox duro: 3 días** | TDD completo + Hypothesis: monotonía tras acierto, cotas [0,1], el selector nunca repite una pregunta dominada, respeta el tamaño solicitado | `G-BKT-PROP` (**nunca bloquea el núcleo**) | 12-18 | 0 | **[P]**, opcional |

---

## 2. Qué se paraleliza y qué no, exactamente

**Estrictamente secuenciales:** 0 → 1 → 2 → 3 → 5. La fase 1 **bloquea todo lo demás**: sin
golden set no hay `G-RECALL5`, no hay `G-CITA-F1` y no hay tesis. Es el cuello de botella humano
del proyecto entero.

**Paralelizables, con condiciones:**

- **Fase 1a** (`scoring`, `schema`, `bootstrap`) puede ir en paralelo con 0.3-0.4. Se **congela
  antes** de anotar el primer caso: anotar 190 casos contra un scorer que va a cambiar tira las
  12 horas humanas.
- **Fase 2 en tres ramas** (A léxico · B vectorial · C rerank), **solo después** de congelar los
  puertos `Retriever`, `Reranker` y `Fusion` con sus tests de contrato en verde. El punto de
  reunión (`fusion.py` + `pipeline.py`) lo escribe **un solo agente**.
- **Fase 4 parcial con la 3**: el runner, el esquema del informe y el bootstrap no dependen del
  grafo. La calibración del juez sí: necesita salidas reales.
- **Fase 6** en cualquier momento después de la 1, o nunca.

**Condiciones para bifurcar sin git** (las cuatro, no tres):
(i) el contrato de la interfaz está congelado y su test de contrato en **verde** antes de
bifurcar; (ii) `STATE.md` declara un `owner` por ruta y ningún agente escribe fuera de las suyas;
(iii) cada rama pasa `make gate-fast` sola; (iv) el punto de reunión lo ejecuta un único agente
con `make gate-full` sobre la unión. **Sin (i) no se bifurca**: dos agentes negociando un contrato
a posteriori cuesta más que hacerlo en serie.

---

## 3. Presupuesto honesto

| Fase | h-agente | h-humanas | Acumulado h-hu |
|---|---:|---:|---:|
| 0 · esqueleto | 25-35 | 1-2 | 1-2 |
| 1 · golden set | 20-30 | **10-16** | 11-18 |
| 2 · retrieval | 35-50 | 1 | 12-19 |
| 3 · agente | 40-55 | 0-2 | 12-21 |
| 4 · evals y juez | 25-35 | **4-6** | 16-27 |
| 5 · endurecimiento | 30-45 | **3-5** | 19-32 |
| **Total núcleo** | **175-250** | **19-32** | |
| 6 · BKT (ampliación) | 12-18 | 0 | |
| **Total con ampliación** | **187-268** | **19-32** | |

**El `PROJECT.md` declara 4-6 semanas "a ritmo de tardes"**, es decir 40-90 h. La estimación real
es de 175-250 h de agente. La desviación es de **2,5-4×** y está medida, no intuida: coincide con
el análisis de huecos. Este plan lleva el número real, no el declarado. Con un agente autónomo el
multiplicador baja mucho en las horas de código y **no baja nada en las 19-32 horas humanas**.

Las horas humanas no son opcionales ni paralelizables: 10-16 h de revisión del golden set
(fase 1), 4-6 h de etiquetado de calibración del juez (fase 4), 3-5 h de vídeo, capturas y
decisiones de publicación (fase 5). Están detalladas una a una en `docs/PARA-SAMUEL.md`. **Si no
se reservan en calendario, el proyecto muere en la fase 1**, que es exactamente el riesgo nº 1
que declara el propio `PROJECT.md`.

### Punto de parada digno

**Fases 0 a 3 completas hacen el proyecto enseñable y defendible.** En ese punto ya existe:
troceado estructural con identificador legal estable, golden set propio revisado por un humano
con dominio, retrieval híbrido con recall medido y comparado, cita cerrada que hace la alucinación
de referencia imposible por construcción, verificación literal del fragmento, abstención como
salida de primera clase con sus dos métricas, y un `make done` que bloquea de verdad. Eso se
defiende en una entrevista sin una sola disculpa.

Lo que añade cada fase posterior, en orden de valor:

- **Fase 4** convierte "yo obtengo estos números" en "cualquiera obtiene estos números": es el
  criterio de aceptación nº 2 y cuesta 25-35 h. Es la primera que yo haría después del corte.
- **Fase 5** es la que se ve: README con números, suite adversarial, observabilidad y la evidencia
  de una reversión por métrica caída (`G-REVERSION`), que es el criterio de aceptación nº 4 y
  vale más que los otros tres juntos. **Se anota desde la fase 2**: no se fabrica al final.
- **Fase 6** no cubre ningún requisito del puesto y es un segundo producto dentro del primero.
  Si hay que cortar algo, se corta esto. No empezarla no es un fallo.
