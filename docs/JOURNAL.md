# Bitácora · citebound-01

**Qué es:** la memoria del proyecto contra repetir errores. Una entrada por sesión, con lo que se
intentó, lo que falló y **el número que salió**. Es lo que evita que dentro de tres semanas se
vuelva a probar una configuración de troceado que ya se descartó.

**Formato y reglas:**

- **Append-only.** Nunca se edita ni se borra una entrada pasada. El hook rechaza una escritura
  cuyo contenido nuevo no empiece exactamente por el viejo. Si algo era erróneo, se corrige en una
  entrada nueva que lo diga.
- Una entrada por sesión, encabezada por `## AAAA-MM-DD · fase N · <titular en una línea>`.
- Secciones fijas: **Qué se intentó · Qué falló · Números · Decisiones · Siguiente**.
- **Todo número va con su comando y su artefacto.** Un número sin comando no es evidencia y no
  sirve para respaldar una propuesta.
- Una propuesta `bajar-umbral` **solo es admisible con ≥2 intentos medidos aquí** entre el inicio
  de la fase y hoy. El gate lo comprueba: si no hay entradas, marca rojo.
- Una reversión por caída de métrica se marca con `<!-- reversion -->` y lleva **tabla antes/después
  y el snapshot correspondiente**. Es la evidencia de `G-REVERSION`, que sustituye al criterio de
  aceptación nº 4 mientras no haya git. **Se anota cuando ocurre, desde la fase 2. No se fabrica al
  final.**
- Español. Los identificadores, comandos y mensajes de error, tal cual salen: en inglés.

---

## 2026-08-08 · fase 0 · ENTRADA DE EJEMPLO — no describe trabajo real, se conserva como plantilla

> **Marcada como EJEMPLO.** Los números de aquí abajo son inventados y sirven solo para enseñar la
> forma. La primera entrada real la escribe el agente al terminar la verificación de entorno
> (`## ENTORNO-0`) descrita en `.claude/state/STATE.md`.

**Qué se intentó**
Medir si el filtro por materia conviene aplicarlo antes (pre-filtro con índice parcial) o después
(post-filtro sobre el top-k ampliado) de la búsqueda vectorial. Dos configuraciones, mismo corpus
congelado (`MANIFEST` sha `a1b2c3…`), mismo golden set `v1` (190 casos, sha `d4e5f6…`), mismo
`index_version` `v1-bgem3-1024`.

**Qué falló**
El primer intento de pre-filtro usaba un índice HNSW global y el planificador de PG18 lo ignoraba,
cayendo a *seq scan*: 340 ms p95 en vez de los 90 ms de presupuesto. No era un problema de recall
sino de plan de ejecución; se detectó con `EXPLAIN (ANALYZE, BUFFERS)`, no adivinando. Con índice
parcial por materia el plan vuelve a usar HNSW.

**Números**

| Configuración | `G-RECALL30` | `G-RECALL5` | p95 búsqueda | Comando |
|---|---:|---:|---:|---|
| post-filtro, `ef_search=100`, k=100→30 | 0,958 | 0,871 | 88 ms | `make eval-retrieval` |
| pre-filtro, índice global | 0,961 | 0,879 | 340 ms | `make eval-retrieval` |
| **pre-filtro, índice parcial por materia** | **0,974** | **0,896** | **71 ms** | `make eval-retrieval` |

Artefactos: `evals/reports/retrieval-20260808T1712.json`, `…T1748.json`, `…T1831.json`.
`G-RECALL5` sigue por debajo de 0,90 (falta 0,004): **no se propone bajar el umbral**, quedan dos
palancas sin medir (instrucción de dominio en el reranker, y `k` de RRF).

**Decisiones**
Se adopta pre-filtro con índice parcial por materia. Decisión no obvia y con alternativa medida →
`docs/adr/007-prefiltro-materia.md`. La configuración descartada se deja documentada en el ADR: sin
eso, dentro de tres semanas alguien vuelve a probar el índice global.

**Siguiente**
Instrucción de dominio en `Qwen3-Reranker-0.6B` ("relevante = el artículo que *tipifica* la
conducta, no el que la *menciona*") y barrido de `k` de RRF ∈ {30, 60, 90}. Si con eso `G-RECALL5`
no llega a 0,90, entonces sí habrá dos intentos medidos y procede una propuesta con evidencia.

---

## 2026-08-10 · fase 0 · ENTORNO-0, sondeo del BOE, y el ID de Q-001 estaba equivocado

Primera entrada real. Sesión de orientación: cero código, cero instalaciones. Se ejecutaron solo
comandos de lectura, y con sus resultados se respondieron seis decisiones bloqueantes.

**Qué se intentó**

Los tres pasos de `.claude/state/STATE.md`: verificación de entorno, sondeo del corpus sin
descargarlo, y relleno de los `<…>` de Q-001. Se añadió por encargo de Samuel una revisión completa
del stack contra PyPI, el registro de Ollama y el registro de imágenes de Docker, porque
`docs/STACK.md` fija versiones de agosto de 2026 y ninguna estaba comprobada contra la realidad.

**Qué falló**

1. **`BOE-A-2003-21806`, el identificador que `docs/PARA-SAMUEL.md` Q-001 daba como opción A por
   defecto, no existe.** La API devuelve `404 · La información solicitada no existe`. El correcto
   es **`BOE-A-2003-23514`** (`fecha_disposicion 20031121`, Ministerio de la Presidencia, Real
   Decreto), verificado por metadatos. Arrancar `0.1` con el ID del buzón habría fallado en el
   primer minuto, y el fallo no es evidente porque el formato del ID es válido.
2. **`docker manifest inspect … | jq -r '.config.digest'`, tal como lo manda `STATE.md`, no
   funciona** con `pgvector/pgvector:0.8.6-pg18-bookworm`: es un índice multiarquitectura
   (`application/vnd.oci.image.index.v1+json`) y no tiene `.config.digest`. El digest correcto
   para fijar en `compose.yaml` es el del índice, y sale con `docker buildx imagetools inspect`.
3. **La URL del aviso legal de datos abiertos del BOE devuelve 404.** Único punto del checklist de
   la primera hora que queda sin cerrar; se resuelve en el ADR-001 y, en cualquier caso, la
   decisión de redistribución es de Samuel (Q-003 + D-07).
4. La máquina tiene **Ollama 0.31.1** y `docs/STACK.md` fija **0.32.6**. El generador instalado
   (`qwen3.5:9b`) es la compilación GGUF `Q4_K_M`, **no la variante MLX** de la que depende el
   presupuesto de `G-TTFT`.

**Números**

*Entorno* — `uv --version` 0.9.27 · `python3.12 --version` 3.12.4 · `docker version` 29.2.1 ·
`docker compose version` v5.0.2 · `ollama --version` 0.31.1 · `curl $OLLAMA_BASE_URL/api/version`
`{"version":"0.31.1"}` · `sysctl hw.memsize` 38 654 705 664 (36 GB) ·
`sysctl iogpu.wired_limit_mb` **0** (por defecto, ~27 GB de los 36 · Q-009) ·
`system_profiler SPHardwareDataType` MacBook Pro, Apple M4 Max, 14 núcleos (10P/4E) ·
`df -h` **133 GB libres** (umbral de parada: 60) · `pmset -g batt` AC Power, 100 % ·
`platform.machine()/mac_ver()` `arm64 26.5.2`. Ninguna condición de parada de `STATE.md` se cumple.

*Modelos residentes* — `ollama ps` vacío. `ollama list`: `gemma4:26b-mlx` 17 GB ·
`qwen3.5:9b` 6,6 GB · `gemma4:12b-mlx` 7,7 GB · `gemma4:12b` 7,6 GB · `bge-m3` 1,2 GB ·
`gemma4:31b-cloud` · `gemma3:12b` 8,1 GB.
`ollama show qwen3.5:9b` → arch `qwen35`, 9,7B, contexto 262 144, embedding 4 096, quant `Q4_K_M`.
`ollama show gemma4:12b-mlx` → arch `gemma4_unified`, 12,4B, quant `nvfp4`, requiere ≥0.31.0.

*Imagen de Postgres* — `docker buildx imagetools inspect pgvector/pgvector:0.8.6-pg18-bookworm`
→ índice `sha256:691673308c99d2161ba298736f3147f1f22d79de2fb7ec93ae9b4afcab870b62`,
manifiesto arm64 `sha256:7db83f583053b1c09e2741578ef6f5758cc785a65088977d5e577ec3f445fdb9`.
**Es el digest del índice el que va en `compose.yaml`.**

*Sondeo del BOE* — `GET /datosabiertos/api/legislacion-consolidada/id/{id}/metadatos`:

| id | HTTP | bytes del texto | `fecha_actualizacion` | estado |
|---|:--:|---:|---|---|
| `BOE-A-2003-21806` (el del buzón) | **404** | — | — | no existe |
| **`BOE-A-2003-23514`** RGC | 200 | 1 158 926 | `20260731T082621Z` | Finalizado, vigente |
| `BOE-A-2015-11722` LSV | 200 | 633 113 | `20260731T082622Z` | Finalizado, vigente |
| `BOE-A-2009-9481` Conductores | 200 | 2 053 997 | `20251219T120350Z` | Finalizado, vigente |

*Estructura del XML consolidado del RGC* — 232 `<bloque tipo="precepto">` (217 con
`titulo="Artículo N"`), 103 `encabezado`, 1 `preambulo`, 1 `nota_inicial`, 1 `firma`.
Clases de `<p>`: `parrafo` 2 273 · `imagen` **623** · `cuerpo_tabla_centro` 514 · `parrafo_2` 510 ·
`articulo` 332 · `nota_pie` 133. Existe `Artículo 14 bis`. Cada precepto lleva
`<version id_norma= fecha_publicacion= fecha_vigencia=>`, o sea **procedencia por artículo, gratis**.

*Verificación del stack contra PyPI* — las 17 dependencias fijadas en `docs/STACK.md` coinciden
**exactamente** con la última versión publicada: pydantic 2.13.4 · langgraph 1.2.10 ·
sentence-transformers 5.7.0 · deepeval 4.1.5 · mlflow 3.15.1 · pgvector 0.5.0 · scipy 1.18.0 ·
pytest 9.1.1 · mypy 2.3.0 · ruff 0.16.2 · mutmut 3.7.0 · testcontainers 4.15.0 ·
detect-secrets 1.5.0 · fastapi 0.141.1 · hypothesis 6.165.2 · langgraph-prebuilt 1.1.0 ·
langgraph-checkpoint 4.2.0. **`docs/STACK.md` no necesita ninguna corrección.**
Ollama v0.32.6 es real (publicada 2026-08-04). Existen las cuatro etiquetas del plan
(`qwen3.5:9b-mlx`, `4b-mlx`, `27b-mlx`, `gemma4:12b-mlx`) y los tres modelos de HF, los tres
Apache-2.0: `Qwen3-Embedding-0.6B`, `Qwen3-Reranker-0.6B`, `bge-reranker-v2-m3`.

*Banco de preguntas aportado por Samuel* — 2.597 filas, 3 opciones, 20 temas, 0 descatalogadas.
`respuesta_correcta` casa con una de las tres opciones en **2 597 de 2 597** filas, sin excepción.
Dificultad empírica (`mediaFallada`): mín 0,0 · p25 2,5 · mediana 10,1 · p75 15,8 · máx 54,2.
Clasificación por cobertura del RGC:

| grupo | total | usables sin imagen | papel |
|---|---:|---:|---|
| `rgc` | 1 284 | **1 103** | positivos (hacen falta 150) |
| `fuera` | 961 | **954** | negativos naturales (hacen falta 40) |
| `mixto` | 352 | 347 | por clasificar |
| dependen de la imagen | 193 (7,4 %) | — | descartados |

**Decisiones**

- **`corpus/raw/` congelado** con el RGC: `BOE-A-2003-23514.xml`
  sha256 `1105a26b…40072` y `…metadatos.xml` sha256 `1122cd91…3884e`. `corpus/MANIFEST.yaml`
  escrito con los dos hashes, la fecha de consolidación y tres avisos que gobiernan el parser.
- **El apartado no es estructural en el XML del BOE**: va como prefijo dentro de
  `<p class="parrafo">`. Como `LegalRef` es `norma#artNN.apartado` y `retrieval-metrics.md` §2
  considera fallo citar `art21` cuando toca `art21.1`, la granularidad de la que dependen
  `G-CITA-PRECISION`, `G-QUOTE-LIT` y el golden set entero **se deriva del texto**. Es el riesgo
  técnico nº 1 de la tarea `0.3` y va al ADR-001.
- **El documento del RGC tiene dos espacios de numeración**: el RD (un "Artículo único") y el
  Reglamento anexo (artículos 1..N). `LegalRef` (tarea `0.2`) numera los del Reglamento. Decisión
  no obvia y anterior a la primera línea de código → ADR-001.
- **CSV podado de 28 a 11 columnas** y movido a `evals/golden/source/`, con el volcado original
  conservado al lado para que la poda sea rederivable. Se derivan `depende_imagen` y
  `cobertura_rgc`. Se descarta el campo `dificultad` subjetivo del contrato en favor de
  `pct_fallo`, que es dificultad medida sobre miles de intentos reales.
- **Respuestas de Samuel** (sesión de hoy, registradas en `docs/PARA-SAMUEL.md`): D-02 ratificado ·
  Q-001 **A** (solo RGC; B y C como ampliación futura) · Q-002 las 11 divergencias ratificadas,
  con la nº 10 revisada · Q-003 dataset usable con `provenance` declarada · Q-012 **A**
  (contrato v2, `chunk_id` sin posición) · Q-013 **A2 + B1** · D-06 **(a)**.
- **Q-009 muere.** Con el banco de preguntas ya escrito no hace falta generar candidatos, así que
  `qwen3.5:27b-mlx` (17 GB) sale del plan y con él la petición de `sudo sysctl iogpu.wired_limit_mb`.

**Siguiente**

`0.2 domain/legalref.py` en **fase ROJA de TDD**, que es la primera unidad de código del proyecto.
Antes: ADR-001 (fuente del corpus y las dos rarezas del árbol), ADR-002 (Python 3.12 por MWAA),
ADR-003 (frontera motor/interfaz), y la propuesta P-001 de `cambiar-plan` para la divergencia nº 10.
Bloqueante pendiente de Samuel: aplicar a mano la versión 2 de `_comun/CONTRACTS/chunks-ddl.sql`
y propagarla a los dos repos. Sin eso, `0.4` y `0.5` siguen bloqueadas.
