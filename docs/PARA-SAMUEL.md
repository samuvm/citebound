# Para Samuel · buzón único de citebound-01

Este fichero es el único canal entre el agente y tú para lo que es **de este proyecto**: datos,
cuentas, dinero, criterio legal, decisión de negocio o tus horas.
**Para responder: edita la línea `Estado:` (`PENDIENTE` → `RESPONDIDA`) y escribe tu respuesta
debajo, en la línea `>>`. No hace falta borrar nada; el fichero es append-only y la respuesta
queda como registro.** Si una entrada trae opciones con `[ ]`, marca una con `[x]`.

Prioridad de lectura: **Q-001, Q-002, Q-012 y Q-013 bloquean el arranque**; **Q-004 es el cuello
de botella del proyecto entero**. Las demás pueden esperar, pero cada una dice exactamente en qué
fase deja de poder esperar.

## Cómo se le piden las cosas a Samuel · norma del 2026-08-14

El **formato de una entrada `Q-NNN` lo fija la constitución §3** y no cambia: identificador, fase
que bloquea, qué pido, por qué, opciones con pros y contras, alternativa si dice que no, estado.

Lo que fija esta norma es **cómo se le presenta en la conversación** lo que tiene pendiente. No se
le resume el estado del proyecto ni se le describe el trabajo: se le dan **instrucciones que puede
ejecutar**, en este formato y sin excepción:

1. **Ordenadas por cuándo**, no por importancia: lo de **ahora** separado de lo que **puede
   esperar**, y dicho explícitamente qué **no** tiene que hacer todavía.
2. **Un paso, una acción.** Qué fichero abre o qué escribe, literal. Qué decide. Nada más.
3. **Una línea de por qué**, en castellano llano. Sin nombres de módulos ni de métricas si se
   puede evitar.
4. **Cuánto le cuesta**, en minutos u horas.
5. **Cuál se puede quedar sin contestar** y qué pasa entonces. Si hay una opción por defecto
   segura, se dice que no hacer nada también vale.

**Por qué esta norma existe.** Lo pidió él el 2026-08-14, después de que se le explicaran sus
pendientes en términos del proyecto en vez de en términos de sus manos. Una lista de temas
pendientes se pospone; una lista de pasos se ejecuta. Y sus horas son el recurso más escaso del
proyecto: 17-28 h irreducibles según la tabla del final de este fichero.

**Dónde se aplica:** al cerrar cualquier turno que le deje algo pendiente, la última sección es la
lista de pasos — no el resumen de lo hecho.

---

## Decisiones transversales

Estas no se deciden aquí. Están en `/Users/samuelviciana/Documents/day-300/_comun/PARA-SAMUEL-GLOBAL.md` y se responden **una sola vez**
para los cinco proyectos. Este proyecto no las repite; solo declara por qué le afectan y, cuando
lo hay, el matiz que le es propio.

- **D-01 (horas por semana y reparto)** — `docs/PLAN.md` estima 175-250 h de agente y 19-32 h
  tuyas para el núcleo, frente a las 40-90 h que declaraba `PROJECT.md`: sin tu número el
  calendario es ficción y el "punto de parada digno" no se puede situar en el tiempo.
  *Matiz propio:* si el reparto a este proyecto queda por debajo de 8 h/semana, la recomendación
  es fijar el corte en la fase 3 desde ahora, no descubrirlo a mitad.
- **D-02 (nombres canónicos)** — bloquea la creación de `src/`: directorio `citebound-01`, paquete
  `citebound`, CLI `citebound`. Hoy el `PROJECT.md` todavía dice `src/tutor/` y `tutor-normativa`;
  renombrar después toca cada import, cada Makefile y cada ruta de `[tool.gate]`.
- **D-03 (la máquina y qué cabe a la vez)** — este proyecto es el que más memoria pide
  (~18-22 GB con generador y juez cargados) y es la mitad del único conflicto físico entre los
  cinco: 01 y 04 se pelean por la GPU. *Matiz propio:* `docs/RULES.md` R10 ya impone
  `OLLAMA_MAX_LOADED_MODELS=1` y el lock `~/.claude/locks/gpu.lock` (opción **c** de D-03), pero
  el lock solo funciona **si el 04 también lo implementa**; si eliges (a) o (b), R10 sigue siendo
  correcto y el lock sobra.
- **D-04 (cuenta AWS y límite de gasto)** — le afecta poco y a propósito: **01 no lleva
  infraestructura**, solo `compose.yaml` (divergencia 11 de Q-002). No pide nada de ese límite.
- **D-05 (clave de API de pago para jueces LLM)** — solo se activa si el juez local no llega a
  κ ≥ 0,60 contra tu etiquetado de Q-008. *Matiz propio:* el gasto estimado es **< 1 €**
  (80 casos × 2 pasadas × ~2.000 tokens) y es **contingente**, no previsto: si dices que no,
  `G-FAITH-JUEZ` queda informativa y `G-QUOTE-LIT` —determinista, sin LLM— carga todo el peso
  de la verificación, sin que la tesis del proyecto dependa del juez.
- **D-06 (política de honestidad)** — es la decisión que más se nota aquí: el proyecto se vende
  como "los números son reproducibles", y hay que declarar qué se publica **antes** de saber si
  `G-RECALL5` sale 0,90 o 0,81. *Matiz propio:* afecta además a `G-JUEZ-KAPPA`, que se publica
  con su IC bootstrap sea cual sea, y a las cotas superiores de `G-HALLUC-AMPLIO`.
- **D-07 (visibilidad y licencia de los repos)** — decide si el corpus se puede redistribuir y si
  "un desconocido clona y ejecuta" es literal o figurado. *Matiz propio:* está encadenada con
  **Q-003** de este fichero, que es el criterio legal concreto del material de la DGT.
- **D-08 (vídeos y capturas)** — la fase 5 declara 3-5 h-hu, de las que **2-3 h son el vídeo de
  60 s y las capturas del README**. El guion lo escribe el agente; grabarlo, no.
- **D-09 (instalar el gobierno fuera de los proyectos)** — mientras `~/.claude/gates/` no exista,
  el gate de este proyecto es persuasión, no ejecución: `make gate-fast` y `make done` funcionan
  igual, pero nada impide saltárselos.

---

## PREGUNTAS ABIERTAS

### Q-001 · fase 0 · BLOQUEA la primera unidad de trabajo (0.1, descarga del corpus)

**Qué necesito:** la lista cerrada de normas del corpus, con su identificador del BOE y la fecha de
consolidación que se congela en `corpus/MANIFEST.yaml`.

**Por qué:** "Reglamento de circulación y manuales DGT" no es un corpus. Sin normas concretas y
fecha congelada no hay parser, ni troceado, ni golden set, ni recall, ni proyecto. Y no puedo
elegirlo por ti: determina cuántas horas tuyas cuesta anotar el golden set y qué se publica.
El agente sondeará la API del BOE (solo cabeceras y metadatos, sin descargar) y rellenará los
`<…>` con los datos reales antes de que respondas; no des por buenos los identificadores hasta
que estén verificados.

**Opciones:**

| Opción | Pros | Contras | Coste extra de anotación |
|---|---|---|---|
| **A (por defecto)** · solo **RD 1428/2003**, Reglamento General de Circulación (`BOE-A-2003-21806`) | Alcance suficiente para toda la tesis; el corpus más denso en conductas tipificadas; menos casos que anotar | Preguntas sobre permisos o sobre la ley marco quedan fuera del corpus (se convierten en casos negativos, lo cual **es útil**) | — |
| **B** · A + **RDLeg 6/2015**, texto refundido de la LSV (`BOE-A-2015-11722`) | Cubre la ley marco; permite casos que exigen dos artículos de normas distintas, que es donde se ve el `nivel_exigido` | Solapamiento parcial con el reglamento: más casos ambiguos que revisar | ≈ +40 casos ≈ **+2-3 h tuyas** |
| **C** · A + B + **RD 818/2009**, Reglamento General de Conductores (`BOE-A-2009-9481`) | Corpus completo del dominio | Triplica la superficie sin añadir tesis; el cuello de botella humano crece un 50 % | ≈ +80 casos ≈ **+4-6 h tuyas** |

`[x] A (solo RD 1428/2003)   [ ] B (+LSV)   [ ] C (las tres)`
Fecha de consolidación observada por el agente: **`2026-07-31T08:26:21Z`**. `[x] confirmo congelarla`

**Tiempo tuyo:** 5-10 minutos.
**Estado: RESPONDIDA · 2026-08-10**
`>> ` **A**, solo el RD 1428/2003. B y C quedan como ampliación futura, no como alcance actual;
anotadas en `corpus/MANIFEST.yaml :: ampliacion_futura` con su coste estimado.

> **CORRECCIÓN DEL AGENTE, sondeo del 2026-08-10.** El identificador que esta pregunta proponía,
> `BOE-A-2003-21806`, **no existe**: la API devuelve `404 · La información solicitada no existe`.
> El correcto es **`BOE-A-2003-23514`** (Real Decreto, Ministerio de la Presidencia,
> `fecha_disposicion 20031121`), verificado por metadatos. Es el que se ha congelado.
> Los otros dos identificadores de la tabla sí eran correctos.
> Ver `docs/JOURNAL.md 2026-08-10` y `docs/adr/001-corpus-fuente-boe.md`.

---

### Q-002 · fase 0 · BLOQUEA la primera línea de código

**Qué necesito:** que ratifiques (o rechaces) las divergencias entre `docs/PROJECT.md` y lo que
gobierna de verdad este proyecto (`STACK.md`, `GOALS.yaml`, `RULES.md`). `PROJECT.md` es zona roja
y no se toca; por eso las divergencias se ratifican aquí en vez de reescribirlo.

**Por qué:** el agente lee los dos y necesita saber cuál manda en cada punto. Si no lo ratificas,
cada divergencia es una decisión que el agente toma solo, y esas son las que hacen que el proyecto
acabe siendo otro proyecto.

| # | `PROJECT.md` dice | Se hace | Motivo en una línea |
|:-:|---|---|---|
| 1 | `Faithfulness (Ragas) ≥ 0,90` como métrica de portada y criterio de bloqueo | **DeepEval 4.1.5** con juez `gemma4:12b-mlx`, y solo bloquea si κ ≥ 0,60 | Ragas está congelado desde febrero de 2026; como gate es un riesgo de credibilidad, no técnico |
| 2 | `qwen2.5:7b` | `qwen3.5:9b-mlx` (Apache-2.0, backend MLX) | Dos generaciones obsoleto; MLX da +93 % de decode y es lo que hace alcanzable el p95 de 1,5 s |
| 3 | Postgres 16 + pgvector 0.8 | **PG18 + pgvector 0.8.6 por digest** | Mismo SQL, coste cero; 0.8.2 parchea CVE-2026-3172 (desbordamiento en construcción paralela de HNSW) |
| 4 | Reranker `bge-reranker-v2-m3`, listado junto al LLM | `Qwen3-Reranker-0.6B`, **en proceso con MPS, nunca por Ollama** | Es *instruction-aware* (se le da "relevante = el artículo que tipifica, no el que menciona") y Ollama no tiene `/api/rerank` |
| 5 | "híbrido (vector + **BM25**, RRF)" | `ts_rank_cd` con configuración `spanish_unaccent`, llamado por su nombre | `tsvector` no es BM25; se hace un spike de 1 día contra BM25 real y sale un ADR con el número, sea cual sea |
| 6 | `src/tutor/`, proyecto `tutor-normativa` | `src/citebound/`, CLI `citebound` | Nombre canónico de la constitución §7.1, ratificado en **D-02** |
| 7 | "corre entero sin claves de API" **y** métricas con juez LLM **y** "un desconocido reproduce los números" | Las tres a la vez, vía caché de juicios versionada: `make eval` es determinista y gratis, `make eval-refresh` es lo único que llama al modelo | Las tres afirmaciones eran incompatibles tal como estaban escritas |
| 8 | Evals "en cada PR" y "CI en dos velocidades" | Sin git todavía: las evals corren en local y lo que se verifica es el **informe versionado** (hash, frescura, comparación pareada) | Un runner hospedado sin GPU tarda 3-5 h por ejecución; y no hay git hasta que tú lo inicies |
| 9 | Fuera de alcance: "corpus de más de una comunidad autónoma" | **Se borra del alcance** | La normativa de circulación es estatal; es un residuo de otro dominio y confunde |
| 10 | BKT + selector + alumnos sintéticos como hito 4 del camino crítico | **Fase 6, ampliación, timebox de 3 días, nunca bloquea** | Es un segundo producto dentro del primero (ver Q-010) |
| 11 | (el mapa de conjunto decía que 01 importa módulos Terraform del 05) | **01 no lleva infraestructura: solo `compose.yaml`** | El 05 se construye el último y se extrae de lo que escriban 01 y 04; la dependencia inversa era imposible |

`[x] ratifico las 11   [ ] ratifico todas menos: ______`

**Tiempo tuyo:** 10-15 minutos.
**Estado: RESPONDIDA · 2026-08-10**
`>> ` **Ratificadas las 11**, con dos matices registrados:

- **La nº 6 ya estaba cubierta** por D-02 de `_comun`, ratificada en la misma sesión.
- **La nº 10 se revisa.** Samuel decidió que el producto **es** la interfaz de práctica de test.
  La divergencia se parte en dos: los endpoints `/session/*` y una interfaz mínima **pasan al
  núcleo**; el BKT sigue siendo ampliación de fase 6 con su timebox de 3 días. Eso cambia
  `docs/PLAN.md`, que es zona roja, así que va como **propuesta P-001** al final de este fichero
  y **no se ejecuta hasta que la apruebes**. Condición que puso Samuel y que se acata: motor e
  interfaz en código separado, con la API HTTP como única frontera
  (`docs/adr/019-frontera-motor-interfaz.md`).

---

### Q-003 · fase 1 · BLOQUEA la generación de candidatos del golden set

**Qué necesito:** decisión sobre qué se redistribuye en el repositorio.

**Por qué:** es criterio legal y no lo decide un agente. El BOE consolidado tiene sus condiciones
de reutilización y atribución. **Los manuales y el banco de preguntas tipo test de la DGT no son
redistribuibles**: si el golden set se construye con preguntas tipo test reales y el repo es
público, es un problema legal, no un detalle de estilo. Depende de **D-07** (visibilidad), pero
no se agota en ella: aunque el repo sea privado, hay que decidir de dónde salen las preguntas.

**Opciones:**

- **A (por defecto):** el golden set se genera **exclusivamente desde el texto del BOE**, nunca
  copiado ni parafraseado del banco DGT, y se declara así en el README junto con la atribución que
  exija el BOE. *Pros:* seguro, publicable con cualquier respuesta de D-07, y el `provenance` por
  caso ya está en el esquema. *Contras:* las preguntas suenan menos "de examen" que las del banco real.
- **B:** repo privado (D-07), y entonces el material DGT se puede usar como inspiración interna.
  *Pros:* preguntas más realistas. *Contras:* un portfolio privado no es portfolio; y si algún día
  lo abres, hay que reanotar.

`[ ] A   [ ] B   [x] otra: ver respuesta`

**Tiempo tuyo:** 5 minutos.
**Estado: RESPONDIDA · 2026-08-10**
`>> ` Samuel aporta un **banco de 2.597 preguntas tipo test de acceso público en internet** y lo
declara usable. El golden set sale de ahí, no de generación asistida: **desaparecen las horas de
revisar candidatos generados** y quedan solo las de validar la referencia legal.

Cómo se acata la parte que sigue siendo obligación del proyecto:

- **Las imágenes no se redistribuyen.** El volcado original apuntaba a rutas de una plataforma de
  autoescuela; solo se conserva el texto. Las 193 preguntas (7,4 %) que necesitan ver la foto para
  responderse quedan **fuera** del golden set.
- **`provenance` se declara** en cada caso y en el README, según **D-06 opción (a)**. Esconder el
  origen de los datos es exactamente lo que `PROJECT.md` §6 dice que "se nota y resta credibilidad".
- El volcado íntegro se conserva en `evals/golden/source/preguntas-dgt-202606.original.csv` para
  que la poda sea rederivable. Detalle completo en el README de esa carpeta.

---

### Q-004 · fase 1 · **EL CUELLO DE BOTELLA DEL PROYECTO ENTERO**

**Qué necesito:** un bloque de calendario reservado de **10-16 horas tuyas** para revisar el golden
set, y la confirmación de que existe.

**Por qué:** eres la única persona que puede confirmar que la respuesta de referencia es correcta y
que el artículo citado es **el adecuado y no el adyacente**. Ningún agente puede hacerlo, ninguna
generación automática lo sustituye, y el propio `PROJECT.md` declara esto como su riesgo número 1
("el golden set es tedioso y se pospone"). **Si esto no se reserva, el proyecto muere aquí**, con
las fases 0 y 1a ya construidas y sin poder medir nada.

Cómo se llega a 10-16 h y no a 20-40: el agente genera candidatos con el perfil de calidad
(`qwen3.5:27b-mlx`), estratificados por materia, a 1,6× el objetivo para permitir rechazos; y
construye una TUI de una tecla (`a` aceptar · `e` editar · `r` rechazar · `s` saltar) que muestra
el artículo íntegro a la izquierda y el candidato a la derecha. Objetivo: **≤ 3 min/caso**.
**Control de calidad del propio flujo:** si en los primeros 20 casos no bajas de 3 min/caso, el
agente **para y rediseña la cola**. Es la diferencia entre 10 h y 25 h, y hay que detectarla en el
minuto 60, no en la hora 12.

**Opciones:**

- **A (por defecto):** 190 casos (150 positivos + 40 negativos) → 10-16 h. Es el suelo estadístico:
  con menos de 150 no distingues una regresión real del ruido y la puerta no significa nada. Son
  los `adicionales` de `G-GOLDEN-VALID` en `docs/GOALS.yaml`.
- **B:** arrancar con 120 (95 + 25) → 7-10 h, y crecer después. *Pros:* desbloquea antes.
  *Contras:* el efecto mínimo detectable sube a ±7 pp y el README tiene que publicarlo; con menos
  del 15 % de negativos, `G-ABST-FN` no es calculable.
- **C:** no reservar y hacerlo "a ratos". *Contras:* es exactamente el modo en que muere.

`[x] A   [ ] B   [ ] C`  ·  `Fechas reservadas: noche del 15 al 16 de agosto de 2026`

**Tiempo tuyo:** **10-16 h** (A) / 7-10 h (B). Es la partida más grande de todo el proyecto.
**Estado: RESPONDIDA · 2026-08-16 — HECHA**
`>> ` **A**, y ejecutada. Lo que salió, medido y no estimado:

| | |
|---|---|
| Casos revisados | **304** (240 positivos + 64 negativos, el 1,6× de esta entrada) |
| Veredictos | 261 ok · 16 corregidos · 27 descartados |
| Tiempo | **15,3 h**, mediana de 180 s/caso — dentro de las 10-16 previstas |
| Golden set resultante | **277 casos**: 219 positivos, 58 negativos, 8 materias con ≥20 |
| Acuerdo en los casos a ciegas | **14 de 14**, al nivel del apartado |

**Antes de gastar las horas se hizo un ensayo automático de 31 minutos**, a propósito, para
detectar errores sin arriesgar la sesión larga. Encontró 34 correcciones, dos artículos que el
agente nunca había abierto (el 97 y el 108), tres afirmaciones falsas del agente sobre lo que
«no aparece en el corpus», y un fallo de diseño de la propia cola. Fue la mejor inversión de
tiempo de la fase. Detalle en `evals/golden/cola/PROCEDENCIA.md`.

<!-- Registro escrito por el agente el 2026-08-16 con permiso explícito de Samuel y por una sola
     vez. No decide nada: recoge lo que ya estaba hecho y medido en veredictos.jsonl. -->

---

### Q-005 · fase 2 · BLOQUEA solo si el spike de BM25 sale positivo

**Qué necesito:** autorización para construir una imagen de Postgres propia.

**Por qué:** la fase 2 incluye un spike de un día contra `pg_textsearch` 1.3 (BM25 real) medido con
`G-RECALL30`. Si mejora el recall, adoptarlo obliga a construir imagen propia: la extensión no
viene en `pgvector/pgvector:*`, y eso rompe la regla "una imagen oficial por digest" y añade un
paso al arranque en 10 minutos (`G-COLD-CACHE`).

**Opciones:**

- **A (por defecto):** el spike se hace igual y su resultado va a un ADR, **pero no se adopta**:
  se queda `ts_rank_cd` y el README dice "probamos BM25 real, mejoró X puntos, no lo adoptamos
  por Y". *Pros:* el ADR es igual de bueno y el arranque sigue siendo limpio.
- **B:** se adopta si mejora ≥ 3 puntos de `G-RECALL30`. *Pros:* mejor recall y puedes decir BM25
  sin mentir. *Contras:* imagen propia, `Dockerfile` que mantener, arranque más lento.

`[x] A   [ ] B (umbral de adopción: ____ puntos)`

**Tiempo tuyo:** 5 minutos.
**Estado: RESPONDIDA · 2026-08-16**
`>> ` **A**. El spike de BM25 se hace y su resultado va a un ADR, pero no se adopta: se queda
`ts_rank_cd` y el README dirá qué mejoró y por qué no se adoptó.

<!-- Marca [x] puesta por Samuel. El cierre del Estado lo formalizó el agente el 2026-08-16 con
     su permiso explícito y por una sola vez: la opción la eligió él, aquí no se decide nada. -->

---

### Q-006 · fase 3 · BLOQUEA la publicación de `G-TTFT`

**Qué necesito:** las condiciones bajo las que se miden las latencias, y que las respetes cuando
toque medir.

**Por qué:** `G-TTFT ≤ 1500 ms` y `G-COLD-CACHE ≤ 600 s` son números de portada, y su
`hardware_referencia` está declarado en `docs/GOALS.yaml`. Un p95 medido con el portátil a batería,
con *throttling* térmico, o con otra cosa comiéndose la GPU, no es comparable con nada, y
`scripts/bench_ttft.py` **abortará** si detecta cualquiera de esas condiciones. El total
informativo de `G-COLD-CACHE` incluye descargar 8,9 GB: depende de tu línea.

Necesito confirmar:
1. `[ ]` Portátil enchufado durante los benchmarks y ~20 min sin usarlo para otra cosa.
2. Ancho de banda de bajada medido (`speedtest` o equivalente): `______ Mbps` — se declara en el README.
3. `[ ]` Ninguna otra carga de GPU en marcha (política de la máquina: **D-03**).

**Tiempo tuyo:** 20 minutos, una vez por fase que mida latencia (fases 3 y 5).
**Estado: PENDIENTE**
`>> `

---

### Q-007 · fase 3 · AMBIGÜEDAD DE CONTRATO — no bloquea, pero decide qué se publica

**Qué necesito:** decidir si la métrica de cita que **bloquea** sigue siendo la del contrato
transversal, o se cambia el contrato.

**Por qué:** `docs/CONTRACTS/retrieval-metrics.md` (v1, compartido con 02 y 04) define
`precision_cita = casos_con_todas_las_citas_en_R / casos_respondidos_no_abstenidos`: todo o nada
por caso. La investigación de este proyecto proponía en su lugar un **F1 macro**, que es más
informativo. Un contrato compartido no se improvisa —romperlo hace que los README de 01, 02 y 04
dejen de ser comparables, que es exactamente para lo que existe— así que **he dejado la del
contrato como bloqueante (`G-CITA-PRECISION`) y el F1 macro como diagnóstico publicado que no
bloquea (`G-CITA-F1`)**. Lo digo explícitamente porque es una corrección a la hoja de trabajo.

**Opciones:**

- **A (por defecto, ya implementada):** contrato intacto. `G-CITA-PRECISION` bloquea, `G-CITA-F1`
  se publica al lado y explica *por qué* cae cuando cae. *Pros:* cero coste, comparabilidad
  intacta, y publicar las dos es más honesto que publicar una. *Contras:* la que bloquea es la
  menos informativa.
- **B:** subir el contrato a v2 con el F1 macro incorporado y propagarlo a mano a `evalgate-02` e
  `indexkeeper-04`, con entrada en el CHANGELOG de los tres. *Pros:* la métrica que bloquea es la
  buena. *Contras:* toca tres repos, y dos de ellos aún no existen; hacerlo ahora es decidir por
  agentes que no han empezado.

`[ ] A   [ ] B`

**Tiempo tuyo:** 5 minutos.
**Estado: PENDIENTE**
`>> `

---

### Q-008 · fase 4 · BLOQUEA `G-JUEZ-KAPPA` y, con él, si `G-FAITH-JUEZ` bloquea

**Qué necesito:** que etiquetes **80 casos** como `sustentado` / `no sustentado`: 50 respuestas
reales del sistema y 30 con un fallo inducido a propósito.

**Por qué:** un juez LLM sin calibrar es una opinión con decimales. El κ de Cohen contra tu
criterio es lo que decide si `G-FAITH-JUEZ` puede bloquear una fase o se publica como informativa.
Es la segunda cosa que ningún agente puede hacer por ti. Se publica el κ real con su IC bootstrap,
sea cual sea (política de honestidad: **D-06**). Si κ < 0,60, entra en juego **D-05**.

**Tiempo tuyo:** **3-5 h**, en una sesión, con TUI de una tecla igual que Q-004.
**Estado: PENDIENTE**
`>> `

---

### Q-009 · fase 4 · BLOQUEA el perfil de calidad (`qwen3.5:27b-mlx`, 17 GB)

**Qué necesito:** autorización para ejecutar `sudo sysctl iogpu.wired_limit_mb=30000` en tu
máquina, o la decisión de renunciar al perfil de calidad.

**Por qué:** macOS limita por defecto la memoria "cableada" de GPU a ~75 % de la RAM unificada. Con
36 GB son ~27 GB; el modelo de 27B más el contexto puede quedarse justo. Subir el límite es un
comando de una línea, reversible al reiniciar, y **no es una decisión que un agente deba tomar en
tu portátil**. Es específico de este proyecto —es el único de los cinco que carga un modelo de
27B— aunque el reparto de memoria entre proyectos se decida en **D-03**.

**Opciones:**

- **A (por defecto):** se autoriza, y el agente lo ejecuta solo antes de `make eval-quality`,
  dejando el valor original anotado en `JOURNAL.md`. *Contras:* un `sudo` en tu máquina.
- **B:** no se autoriza. La generación de candidatos del golden set y las evals nocturnas usan
  `qwen3.5:9b-mlx`. *Contras:* candidatos de golden set algo peores → más ediciones tuyas en Q-004.

`[ ] A   [ ] B`

**Tiempo tuyo:** 2 minutos.
**Estado: PENDIENTE**
`>> `

---

### Q-010 · fase 4 · BLOQUEA saber si se planifica la fase 6

**Qué necesito:** decidir si el BKT y el selector de bloque entran en el proyecto.

**Por qué:** el `PROJECT.md` los pone como hito 4 del camino crítico. Son 25-40 h si se hacen
completos (BKT + generador de alumnos sintéticos + endpoints `/session/*`) y **no cubren ningún
requisito del puesto**: es un segundo producto dentro del primero.

**Opciones:**

- **A (recomendada):** fase 6, ampliación, timebox duro de 3 días, **solo dominio puro**
  (`domain/knowledge.py` + `domain/selector.py`) con TDD y propiedades Hypothesis. Los endpoints
  `/session/*` solo si sobra tiempo; si no, ADR de "fuera de alcance y por qué". *Pros:* los tests
  de propiedad del BKT son de los mejores del repo y cuestan un día. *Contras:* el README no puede
  prometer un producto educativo.
- **B:** dentro del camino crítico como en el documento original. *Contras:* +25-40 h sobre un plan
  que ya va 2,5-4× por encima de lo declarado.
- **C:** fuera del todo, con ADR. *Pros:* foco máximo. *Contras:* se pierde el mejor ejemplo de
  Hypothesis del proyecto.

`[ ] A   [ ] B   [ ] C`

**Tiempo tuyo:** 5 minutos.
**Estado: PENDIENTE**
`>> `

---

### Q-011 · continuo · BLOQUEA cada vez que haga falta una dependencia nueva

**Qué necesito:** aprobar cada `uv add`, uno a uno.

**Por qué:** `uv add` y `uv remove` están en `ask` (constitución §7.2). El agente no amplía la
superficie de dependencias solo, y cada petición viene con justificación en el mismo turno.
Dependencias previstas y ya justificadas por `docs/STACK.md`: `fastapi`, `uvicorn`, `pydantic`,
`psycopg[binary,pool]`, `pgvector`, `langgraph` (+`-prebuilt`, +`-checkpoint`),
`sentence-transformers`, `deepeval`, `mlflow`, `opentelemetry-sdk`, `scipy`, `numpy`, `httpx`,
`pytest`+extras, `hypothesis`, `testcontainers`, `schemathesis`, `mutmut`, `ruff`, `mypy`,
`bandit`, `detect-secrets`. **Cualquier cosa fuera de esa lista se pregunta.** Recuerda que los
rangos de `docs/STACK.md` son la investigación, no el pin: el agente traduce cada rango a un `==`
concreto en `pyproject.toml` y anota la versión elegida en `docs/JOURNAL.md` (constitución §7.2).

`[x] apruebo la lista de arriba en bloque   [ ] las quiero una a una`

**Ampliación aprobada el 2026-08-10, fuera de la lista original:**

| Paquete | Para qué | Por qué se preguntó |
|---|---|---|
| `defusedxml==0.7.1` | Parseo defensivo del XML del BOE | `xml.etree` no defiende contra la expansión de entidades y **no tiene interruptor** para desactivarla. Había una guarda propia que escaneaba el prólogo entero, con su test de *billion laughs*, pero una librería probada es mejor que una guarda escrita a mano |
| `types-defusedxml` (dev) | Stubs de tipos | `mypy --strict` no puede comprobar un paquete sin `py.typed`, y bajar la exigencia de tipos para acomodar una dependencia es empezar por el lado equivocado |

La guarda propia **se conserva** encima: falla con un mensaje en español que dice qué pasa,
en la capa que primero toca bytes de la red. `defusedxml` levanta `EntitiesForbidden`, que
es correcto e inútil para quien tiene que arreglar la descarga. Las dos son baratas y
fallan distinto, que es el motivo de tener las dos.

**Tiempo tuyo:** 2 minutos ahora; después, 30 segundos por petición.
**Estado: RESPONDIDA · 2026-08-10**
`>> ` **Aprobada en bloque.** Cualquier paquete **fuera** de esa lista sigue exigiendo permiso
explícito en el mismo turno.

Los rangos de `docs/STACK.md` se han traducido a `==` exactos en `pyproject.toml` y cada versión
elegida queda anotada en `docs/JOURNAL.md` (constitución §7.2). Desbloquea `0.2 domain/legalref.py`,
la primera unidad de código del proyecto.

---

### Q-012 · fase 0 · CONFLICTO DE CONTRATO CON EL 04 · el `chunk_id` lleva la posición

*(Entrada espejo de `indexkeeper-04/docs/PARA-SAMUEL.md` Q-002. Un conflicto sobre un contrato
compartido declarado en un solo repositorio **no está declarado**: se decide una vez y se propaga
a los dos. Se responde junto con Q-013, en un único evento de cambio de contrato.)*

**Qué necesito:** decidir si `_comun/CONTRACTS/chunks-ddl.sql` sube a la versión 2, sabiendo qué
le cuesta a **este** proyecto cada opción.

**Por qué:** el contrato congelado dice literalmente
`chunk_id = sha256(f"{doc_id}:{ordinal}:{content_hash}")[:24]` — **incluye la posición**. El 04
sostiene que con la posición dentro del hash, insertar un párrafo al principio de un documento
desplaza todos los ordinales y obliga a re-embeber el documento entero, lo que hace su meta
insignia (`G-INCR-2`, ahorro de tokens ≥ 0,90) **inalcanzable por construcción**. Yo no puedo
tocar un contrato compartido y él tampoco: rompería al otro.

**Qué impacto tiene en citebound-01, opción por opción:**

| Opción (la nombra el 04) | Impacto real aquí |
|---|---|
| **A · contrato v2** con `chunk_id = blake2b(doc_id ‖ content_hash ‖ occurrence, digest_size=16)`, `ordinal` como columna y `UNIQUE (doc_id, ordinal) DEFERRABLE` (la entrada del 04 lo escribe `content_sha256`; el nombre del contrato es `content_hash`, y v2 debe fijar uno) | **Coste bajo y acotado, si se decide antes de `0.5 db/ddl.sql`.** Este proyecto **nunca cita ni evalúa por `chunk_id`** (`RULES.md` R1 y `retrieval-metrics.md` §1: todo se ancla en `legal_ref`), así que el golden set, `G-RECALL5`, `G-CITA-PRECISION` y `G-HALLUC` no se enteran. Lo que sí cambia: (1) el *snapshot* de contrato del DDL de la fase 0; (2) `ingest/chunking.py` tiene que calcular `occurrence` para desempatar contenido duplicado dentro de una misma norma —y en texto legal eso **no es teórico**: hay apartados cortos idénticos repetidos—, lo que añade un invariante y una propiedad Hypothesis. `ordinal` sigue siendo columna, así que la propiedad "la concatenación ordenada de los chunks de un artículo reproduce su texto exacto" se mantiene intacta. Estimación: **3-5 h de agente en fase 0**; si se decide después de la fase 2, hay que reingerir el corpus entero y rehacer el snapshot |
| **B · mantener v1** | **Coste cero aquí, y es la razón por la que es tentador.** Pero obliga al 04 a bajar su meta insignia *antes de medirla*, que es exactamente lo que la constitución §3 prohíbe, y deja al 01 con un contrato que solo él respeta |
| **C · dos identificadores** (el `chunk_id` del contrato para el 01 + una clave de contenido estable para el incremental del 04) | **Es la peor para este proyecto.** `RULES.md` R1 y `scripts/check_no_chunk_ids.py` prohíben la subcadena `chunk_id` en el golden set, en `Citation` y en el OpenAPI; con dos identidades por fila se duplica la superficie por la que un identificador de troceado puede filtrarse a un artefacto de evaluación, que es justo el fallo que R1 existe para impedir |

**Recomendación desde el 01:** **A**, y decidida ahora. Este proyecto no pierde nada sustantivo y
el 04 recupera su tesis; el coste (3-5 h) solo crece con el tiempo.

`[x] A (contrato v2)   [ ] B (v1 intacto)   [ ] C (dos identificadores)`

**Tiempo tuyo:** 30 min de decisión (compartidos con la entrada Q-002 del 04) + 15 min de
propagación a los dos repos y su CHANGELOG.
**Estado: RESPONDIDA · 2026-08-10 — falta la propagación, que es tuya**
`>> ` **A**, contrato v2. `chunk_id = blake2b(doc_id ‖ content_hash ‖ occurrence, digest_size=16)`,
`ordinal` como columna con su `UNIQUE` en `DEFERRABLE`.

Borrador listo para aplicar: **`docs/spec/propuesta-chunks-ddl-v2.sql`**. Razonamiento y coste en
`docs/adr/018-chunks-ddl-v2-y-conmutacion.md`.

**Te quedan cuatro pasos que ningún agente puede dar** (`_comun/` está en `deny`):
1. Que el agente de `indexkeeper-04` revise el borrador — el contrato es de los dos.
2. Copiar el resultado acordado a `_comun/CONTRACTS/chunks-ddl.sql`.
3. Copiarlo a `docs/CONTRACTS/chunks-ddl.sql` de **los dos** repos.
4. Anotarlo en el CHANGELOG de **los dos**.

Hasta entonces, las tareas **`0.4` (`ingest/chunking.py`) y `0.5` (`db/ddl.sql`) siguen
bloqueadas**. Todo lo anterior de la fase 0 puede avanzar.

---

### Q-013 · fase 0 · CONFLICTO DE CONTRATO CON EL 04 · esquema legal y mecanismo de conmutación

*(Entrada espejo de `indexkeeper-04/docs/PARA-SAMUEL.md` Q-003. Se responde junto con Q-012.)*

**Qué necesito:** dos decisiones que van juntas, y que aquí pesan más que en el 04 porque
`G-HALLUC` (umbral `== 0`, `propuesta_admisible: false`) se define literalmente como "pertenencia
de la `legal_ref` al conjunto de refs del **índice activo**".

**(a) Campos legales.** `chunks-ddl.sql` modela un corpus normativo: `norma TEXT NOT NULL`,
`articulo`, `apartado` y una columna generada `legal_ref`. El 04 no sabe aún si su corpus será
normativo, y propone generalizar.

- **A1 · el 04 usa corpus normativo** → aquí no cambia nada. Coste cero.
- **A2 · generalizar el contrato**: `ref TEXT NOT NULL` como identificador estable de
  documento/sección, con `norma`/`articulo`/`apartado` **opcionales**. *Impacto aquí:* aceptable,
  pero **no es gratis**. `legal_ref` es columna generada y `RULES.md` R1/R15 y `G-HALLUC` dependen
  de que exista siempre; si `norma` pasa a admitir NULL en el contrato, este proyecto tiene que
  añadir en **su propio** DDL (`docs/spec/`, no en `docs/CONTRACTS/`) un `CHECK (norma IS NOT NULL)`
  y un test de contrato que lo verifique, o un chunk sin norma produciría una `legal_ref` no
  resoluble y `G-HALLUC` estaría midiendo contra un conjunto roto. Coste: **~1 h**, y hay que
  hacerlo el mismo día.
- **A3 · el 04 usa su propia tabla** y renuncia a que el 01 lea su índice. *Impacto aquí:* mata el
  único contrato real entre 01 y 04 y convierte `chunks-ddl.sql` en un documento decorativo.

**(b) Mecanismo de conmutación de índice.** El contrato conmuta con `index_version.is_active`
(una fila por índice, índice único parcial que garantiza uno solo activo). La hoja de trabajo del
04 conmuta con una **vista** `chunks_active` más una tabla `index_alias`. Son dos diseños válidos
e incompatibles, y el 04 **mide** la conmutación.

- **B1 · vista `chunks_active` + `index_alias`.** *Impacto aquí, que es el que hay que ver:*
  (1) `retrieval/query_builder.py` deja de filtrar `chunk` por `index_version` y consulta la
  vista; hay que probar con `EXPLAIN` en un test de integración que el plan **sigue usando el
  índice HNSW** y que `SET hnsw.ef_search` (obligatorio por `RULES.md` error nº 12) surte efecto
  a través de la vista — una vista mal formada lo destruye en silencio y `G-RECALL5` cae sin que
  nadie entienda por qué. (2) **`G-EVAL-DET` y `R15` obligan a un requisito extra**: si el índice
  se resuelve por alias, el informe de eval no puede registrar el alias, tiene que registrar el
  **destino físico resuelto** (tabla + `index_version.id`); si no, dos ejecuciones con el mismo
  alias apuntando a datos distintos producirían informes "idénticos" sobre corpus distintos, y
  `G-EVAL-DET` (`propuesta_admisible: false`) dejaría de significar nada. (3) A favor: B1 es la
  única que permite cambiar la **dimensión** del embedding sin parar el servicio, que es
  precisamente lo que este proyecto necesitaría si algún día cambia de modelo de embeddings, y el
  rollback es cambiar la vista en vez de borrar millones de filas.
- **B2 · `index_version.is_active`.** *Impacto aquí:* **cero**. Es lo que ya asumen `GOALS.yaml`
  y `RULES.md` R15: se resuelve el activo con una subconsulta escalar y el informe registra ese
  `id`. Más simple, pero obliga a que las dos generaciones convivan en la misma tabla con la misma
  dimensión.

**Recomendación desde el 01:** **A2 + B1** —la misma que el 04— **con una condición explícita**:
el informe de eval registra el destino físico resuelto, no el alias, y el `CHECK` de `norma` vive
en el DDL propio de este proyecto. Con esa condición escrita, B1 aporta más de lo que cuesta.
Si prefieres el mínimo movimiento, **A1 + B2** deja este proyecto exactamente como está.

`(a) [ ] A1   [x] A2   [ ] A3`     `(b) [x] B1   [ ] B2`

**Tiempo tuyo:** 30 minutos (compartidos con la entrada Q-003 del 04).
**Estado: RESPONDIDA · 2026-08-10 — falta la propagación, va junta con Q-012**
`>> ` **A2 + B1**, con las dos condiciones que este proyecto puso y que quedan escritas en el
contrato v2:

1. **`CHECK (norma IS NOT NULL)` vive en el DDL propio de este repo** (`docs/spec/`, nunca en
   `docs/CONTRACTS/`), con su test de contrato. Sin él, un chunk sin norma produce una `legal_ref`
   no resoluble y `G-HALLUC` —umbral `== 0`, `propuesta_admisible: false`— mide contra un
   conjunto roto.
2. **El informe de eval registra el destino físico resuelto**, `index_alias.index_version` +
   `index_alias.physical_table`, **nunca el alias**. Con el alias, dos ejecuciones sobre datos
   distintos darían informes normalizados idénticos y `G-EVAL-DET` dejaría de significar nada.

Coste adicional aceptado: un test de integración con `EXPLAIN` que demuestre que la consulta a
través de la vista `chunks_active` **sigue usando el índice HNSW** y que `SET hnsw.ef_search`
surte efecto. Una vista mal formada lo destruye en silencio y `G-RECALL5` cae sin causa aparente.

---

### Resumen de tus horas irreducibles

| Entrada | Fase | Horas |
|---|:-:|---:|
| Q-001, Q-002, Q-003 · decisiones de arranque | 0-1 | 0,5-1 |
| Q-012, Q-013 · conflicto de contrato con el 04 (compartido con su buzón) | 0 | 1-1,5 |
| **Q-004 · revisión del golden set** | **1** | **10-16** |
| Q-005 · spike de BM25 | 2 | 0,1 |
| Q-006, Q-007 · condiciones de medida (×2) y métrica de cita del contrato | 3, 5 | 0,5-1 |
| **Q-008 · calibración del juez** | **4** | **3-5** |
| Q-009, Q-010, Q-011 · autorizaciones, alcance y dependencias | 4, continuo | 0,25 |
| D-07, D-08 · vídeo y capturas (la **decisión** está en `_comun`; las horas son de aquí) | 5 | 2-3 |
| **Total** | | **17-28 h** |

Coincide con las 19-32 h de `docs/PLAN.md` (que incluye margen). No baja a cero con ningún agente,
ningún modelo y ninguna herramienta: es la parte del proyecto que **es tuya**. Las horas de
responder `/Users/samuelviciana/Documents/day-300/_comun/PARA-SAMUEL-GLOBAL.md` no están aquí porque se pagan una vez para los cinco.

---

## PROPUESTAS DE CAMBIO

> Vacía. Aquí escribe **el agente** cuando necesite cambiar algo de la zona roja (`GOALS.yaml`,
> `PLAN.md`, `RULES.md`, `PROJECT.md`) y **para** hasta que respondas.
>
> Reglas que aplican a esta sección (constitución §3):
> - El agente escribe la propuesta y **para**. No sigue asumiendo que sí.
> - **Toda propuesta se pregunta explícitamente**, tanto si nace del agente como si el cambio lo
>   pides tú. Que tú sugieras bajar un umbral no lo convierte en aprobado.
> - Una propuesta `bajar-umbral` **solo es admisible con ≥ 2 intentos medidos y registrados en
>   `docs/JOURNAL.md`** entre el inicio de la fase y hoy. El gate lo verifica y marca rojo si no.
> - **No se admite propuesta alguna** sobre `G-HALLUC`, `G-HALLUC-AMPLIO`, `G-QUOTE-LIT`,
>   `G-EVAL-DET`, `G-SECRETS`, `G-COV-FUNC`, `G-GOLDEN-VALID`, `G-INJECT` ni `G-JUEZ-KAPPA`
>   (`propuesta_admisible: false` en `GOALS.yaml`).
> - Aprobar es: **tú** editas `docs/GOALS.yaml`, pones `Estado: APROBADA` y **regeneras
>   `thresholds.lock`**. Solo tú puedes regenerar el lock.

```markdown
## PROPUESTA P-NNN · AAAA-MM-DD · fase N
Tipo: bajar-umbral | cambiar-meta | cambiar-spec | cambiar-plan | necesito-recurso
Afecta a: docs/GOALS.yaml :: G-XXXX (valor actual)
Qué pido:
Por qué:            (horas invertidas, configuraciones medidas, tabla en JOURNAL AAAA-MM-DD, ADR-NNN)
Qué he descartado:  (con su coste medido, no supuesto)
Alternativa si dices que no:
Estado: PENDIENTE
```

---

## PROPUESTA P-001 · 2026-08-10 · fase 0

**Tipo:** `cambiar-plan`
**Afecta a:** `docs/PLAN.md` §1 fila 6 y §3 «punto de parada digno» · divergencia nº 10 de Q-002

**Qué pido.** Partir la fase 6 en dos, sin tocar ninguna meta ni ningún umbral:

| | Hoy en `PLAN.md` | Propuesto |
|---|---|---|
| Endpoints `/session/*` + interfaz mínima de práctica | fase 6, ampliación, «solo si sobra tiempo» | **núcleo**, al final de la fase 3, ~8-12 h-agente |
| BKT y selector de bloque (`domain/knowledge.py`) | fase 6, ampliación, timebox 3 días | **igual**, sin cambios |

**Por qué.** El 2026-08-10 Samuel aportó un banco de 2.597 preguntas tipo test con opciones y
respuesta correcta (`evals/golden/source/`, 1.103 positivos y 954 negativos usables) y decidió que
el producto es la interfaz de práctica. `PLAN.md` degradó esos endpoints porque **no había
contenido que servir**; esa premisa ya no se sostiene. `PROJECT.md` §2 los listaba desde el
principio como objetivos funcionales, así que esto no amplía el alcance del documento original:
lo recupera.

Hay además una ganancia técnica medible, no solo de producto: con la interfaz de test **la consulta
deja de ser texto libre**. Es la pregunta más sus tres opciones, redactada en lenguaje casi
normativo y **conocida de antemano** — las 2.597 son fijas. El retrieval se puede auditar caso a
caso e incluso precalcular, lo que reduce directamente el riesgo de `G-RECALL5 ≥ 0,90`, que es la
meta con más probabilidad de no salir a la primera.

Razonamiento y frontera de código en **`docs/adr/019-frontera-motor-interfaz.md`**.

**Qué he descartado.**

- *Dejarlo en fase 6 como está* — coste 0 hoy, pero `PLAN.md` §3 admite explícitamente que la
  fase 6 puede no hacerse. El proyecto se quedaría sin producto que enseñar, teniendo el contenido
  en el repo.
- *Que la interfaz importe el dominio directamente* — más barato hoy, y contamina el régimen de
  pruebas: o metes código de presentación en `[tool.gate].testable` y `G-COV-FUNC` y `G-MUT`
  empiezan a exigirse sobre *handlers* de UI, o lo excluyes y abres un agujero por donde se cuela
  lógica sin test. Por eso la frontera es HTTP y `ui/` va a `excluido` + `tdd_prohibido`.
- *Subir también el BKT al núcleo* — son 25-40 h y no cubre ningún requisito del puesto. Sigue
  siendo ampliación (Q-010 opción A).

**Qué NO pido.** Ni una meta nueva, ni un umbral distinto, ni tocar `thresholds.lock`. `G-BKT-PROP`
sigue con `bloqueante_desde_fase: null`. Lo único que cambia es dónde vive una tarea en `PLAN.md`.

**Alternativa si dices que no.** La interfaz se construye igual pero fuera del plan, sin entrar en
`make done`, y el README la presenta como demo y no como entregable. Funciona, pero es peor: una
demo fuera del gate es exactamente el tipo de código que acaba sin test de contrato.

**Estado: APROBADA · 2026-08-10 · APLICADA**
`>> ` **Sí: la interfaz es obligatoria para `make done` completo.**

Aplicado en `docs/PLAN.md` —zona roja, editada por el agente con autorización explícita de Samuel
en esta sesión— con la marca `<!-- P-001 -->` en las dos líneas tocadas:

- **Nueva fila `3b · Interfaz de práctica de test`, tipo NÚCLEO.** 8-12 h de agente, 0 horas
  humanas. Entra en `make done MILESTONE=3`. Se le exige test de contrato contra el snapshot de
  OpenAPI y humo e2e; **no** lleva TDD ni cobertura por función, porque es presentación
  (ADR-019, y `ui/` ya está en `[tool.gate].excluido` y `tdd_prohibido` de `pyproject.toml`).
- **La fase 6 se queda solo con la selección adaptativa** (BKT + selector), ampliación con timebox
  duro de 3 días. No empezarla sigue sin ser un fallo.

**Ninguna meta nueva, ningún umbral tocado, `thresholds.lock` intacto.** Lo único que cambia es
dónde vive una tarea. Si no estás de acuerdo con cómo quedó redactada, revertir es borrar la fila
`3b` y la línea de la fase 6: está marcada para que se encuentre en un `grep`.

---

## Pendiente de registrar en `_comun/PARA-SAMUEL-GLOBAL.md`

Samuel respondió estas dos en la sesión del 2026-08-10, pero **`_comun/` está en `deny` y ningún
agente lo escribe**. Hay que trasladarlas a mano o quedan sin registro para los otros cuatro
proyectos:

| Decisión | Respuesta dada | Qué escribir |
|---|---|---|
| **D-02** nombres canónicos | Ratificados | `Estado: DECIDIDO` |
| **D-06** política de honestidad | **(a)** publicar el número real y explicar por qué no se alcanzó | `Elección: (a)` + `Estado: DECIDIDO` |

**Q-009 deja de aplicar.** Pedía autorización para `sudo sysctl iogpu.wired_limit_mb=30000` con el
fin de cargar `qwen3.5:27b-mlx` (17 GB) y generar candidatos de golden set. Con el banco de
preguntas ya escrito, ese modelo sale del plan y con él la petición. Se marca así al cerrar la
fase 1; no hace falta que respondas nada.

---

### Q-014 · fase 1 · NO bloquea hoy · discrepancia dentro de `docs/RULES.md`

**Qué necesito:** que decidas si `src/citebound/evals/bootstrap.py` entra en
`[tool.gate].tdd_obligatorio`, y que lo apliques tú si la respuesta es sí. `RULES.md` es zona
roja y no lo toco.

**Por qué:** el documento se contradice consigo mismo.

- **`RULES.md` §3**, tabla «qué se testea y dónde vive TDD», dice: `evals/{scoring,bootstrap}`
  → **TDD obligatorio + Hypothesis**, y añade que se congela antes de anotar el primer caso.
- **`RULES.md` §4**, el bloque `[tool.gate]` marcado «literal, para copiar a `pyproject.toml`»,
  lista en `tdd_obligatorio` solo `evals/scoring.py`. `bootstrap.py` aparece en `testable`,
  pero no en `tdd_obligatorio`.

Manda §4, porque es lo que lee el script. Consecuencia práctica: **`bootstrap.py` queda fuera
de `make mutation`**, o sea que `G-MUT` no lo mide. Y `bootstrap.py` es la puerta estadística:
decide qué cambio se acepta y cuál se revierte a partir de la fase 2.

He copiado §4 al `pyproject.toml` **literalmente**, que es lo que manda el contrato, y he
dejado el motivo escrito en el propio fichero. No lo he «arreglado» por mi cuenta: divergir la
copia del original rompe el `diff` que sirve de test.

**Opciones:**

- **A (por defecto):** añadir `"src/citebound/evals/bootstrap.py"` a `tdd_obligatorio` en
  `RULES.md` §4. *Pros:* casa §4 con §3, y la puerta estadística pasa a estar medida por
  mutación como el resto del núcleo. Su TDD ya está hecho —rojo de 32 congelado en `a6a3ccf`—,
  así que no cuesta trabajo nuevo, solo mide el que ya hay. *Contras:* `make mutation` tarda
  algo más.
- **B:** cambiar §3 para que diga solo `evals/scoring`. *Pros:* también resuelve la
  contradicción. *Contras:* la puerta estadística se queda sin medir, y es el módulo que
  decide si una regresión bloquea. No lo recomiendo.

`[x] A   [ ] B`

**Tiempo tuyo:** 2 minutos (editar `RULES.md` §4 y la copia de `pyproject.toml`).
**Estado: RESPONDIDA · 2026-08-13**
`>> ` **A**, con el criterio general de que ante dos reglas contradictorias manda **la más
estricta**. Aplicado en `pyproject.toml`: `bootstrap.py` entra en `tdd_obligatorio` y en
`paths_to_mutate`, así que `G-MUT` ya lo mide.

**Queda tuyo, 30 segundos:** añadir `"src/citebound/evals/bootstrap.py"` a `tdd_obligatorio` en
`RULES.md` §4. Hasta que lo hagas, esa línea del `pyproject` es lo único que **no** es copia
literal de §4, y está marcada como tal en el propio fichero para que nadie la confunda con una
divergencia accidental.

---

### Q-015 · fase 3 · `G-MUT` no es reproducible · NO bloquea la fase 1

**Qué necesito:** que elijas cómo se mide `G-MUT`, porque la herramienta que lo mide da un
número distinto cada vez.

**Por qué:** `mutmut 3.7.0` no es determinista en este repo. Medido hoy, con el **mismo código
y los mismos tests**, sin tocar una línea entre corridas:

| Corrida | Supervivientes | `G-MUT` |
|---|---:|---:|
| limpia, en paralelo | 1 | 99,9 % |
| limpia, en paralelo (repetida) | 3 | 99,7 % |
| limpia, en paralelo (otra vez) | 3 | 99,7 % |
| limpia, `--max-children 1` | **100** | **88,9 %** |

Y los nombres de los supervivientes **cambian por completo** entre corridas, no son los mismos
tres. Además verifiqué a mano dos casos concretos:

- **Falso superviviente:** `boe_xml.x__precepto__mutmut_70` figuraba vivo y **muere** con tests
  que existían desde el 10 de agosto. Causa encontrada y arreglada: un *fixture* de ámbito
  `module` hacía que `--cov-context=test` atribuyera el parseo solo al primer test del fichero,
  y mutmut selecciona por contexto de cobertura.
- **Falso muerto:** `chunking` `"utf-8"` → `"UTF-8"` se reportó como muerto. Es **equivalente**
  —mismo códec, mismos bytes, mismo sha256— y aplicándolo a mano **los 409 tests pasan**.

Un falso muerto es peor que un falso superviviente: infla la métrica en vez de mandarte a
buscar un agujero que no existe.

Ya he arreglado tres causas reales por el camino (el *fixture* de módulo, el
`dynamic_context` que rompía la tabla de contextos de coverage, y la config deprecada de mutmut
que dejaba 108 mutantes sin medir). La variabilidad que queda es de la herramienta.

**El umbral no está en riesgo:** `mutantes_muertos_min` es 70 y el peor número medido es 88,9 %.
El problema no es pasar, es que **el número no se puede reproducir**, y eso choca de frente con
el criterio de aceptación nº 2 del proyecto y con el espíritu de `G-EVAL-DET`.

**Opciones:**

- **A (por defecto):** se queda mutmut, y el protocolo de medida pasa a ser **tres corridas
  limpias y se publica la peor**. *Pros:* cero dependencias nuevas, conservador por
  construcción, y la frase «publicamos el peor de tres» se defiende en una entrevista.
  *Contras:* `make mutation` tarda el triple, y sigue sin ser reproducible caso a caso.
- **B:** cambiar a `cosmic-ray`. *Pros:* guarda los resultados en una base de datos propia y
  su modelo de ejecución es reproducible. *Contras:* dependencia nueva —necesita tu permiso
  explícito, Q-011— y hay que reescribir la integración con el gate.
- **C:** `G-MUT` deja de bloquear y pasa a diagnóstico, publicando el rango medido. *Contras:*
  la mutación es lo único que distingue cobertura de verificación; degradarla es perder
  justo la meta que hace creíble el 100 % de cobertura.

`[x] A   [ ] B   [ ] C`

**Tiempo tuyo:** 5 minutos. **No corre prisa:** `G-MUT` bloquea desde la fase 3.
**Estado: RESPONDIDA · 2026-08-16**
`>> ` **A**. Se queda mutmut y el protocolo pasa a ser **tres corridas limpias, publicando la
peor**. `make mutation` tardará el triple y el README dirá que el número publicado es el mínimo
de tres, no el mejor de tres.

<!-- Marca [x] puesta por Samuel. Cierre formalizado por el agente el 2026-08-16, con su permiso
     explícito y por una sola vez. La opción la eligió él. -->

---

### Q-016 · fase 2 · AMBIGÜEDAD DE CONTRATO · BLOQUEA publicar `G-RECALL5` y `G-RECALL30`

**Qué necesito:** que decidas a qué granularidad se compara el recall.

**Por qué:** `docs/CONTRACTS/retrieval-metrics.md` §2 define
`recall@k = |R(q) ∩ P_k(q)| / |R(q)|` como una intersección de conjuntos de `legal_ref`, y
**calla sobre la granularidad**. La regla del apartado está escrita, pero para *precisión de
cita*, no para recall.

Y aquí eso no es un matiz: el troceador es `articulo-v1`, así que **ninguna** de las 235
referencias del índice lleva apartado, mientras que **190 de las 219** del golden set (86 %) sí.
Con la lectura literal el recall está **acotado por construcción**, con el mejor recuperador
imaginable.

Medido hoy sobre los 219 casos positivos:

| | Lectura literal | A nivel de artículo | Umbral |
|---|---|---|---|
| `G-RECALL5` | 0,068 | 0,717 | ≥ 0,90 |
| `G-RECALL30` | 0,128 | 0,954 | ≥ 0,97 |

**Opciones:**

- **A (por defecto):** el recall se compara **a nivel de artículo**. Traer el artículo correcto
  es trabajo del recuperador; bajar al apartado es del generador, y para eso está
  `G-CITA-PRECISION`, cuya regla de granularidad **sí** está en el contrato. *Pros:* la métrica
  mide lo que el recuperador puede controlar, y el rigor del apartado no se pierde — se cobra
  en la fase 3. *Contras:* es una **interpretación** del contrato compartido, así que hay que
  decírselo a los otros dos repos o los números dejan de ser comparables.
- **B:** lectura literal, y entonces el troceador tiene que bajar al apartado para que la
  métrica sea alcanzable. *Pros:* cero interpretación. *Contras:* rehacer el troceado y
  reindexar; y ADR-001 explica que el apartado **no es estructural** en el XML del BOE, así que
  el troceo por apartado se deriva del texto y mete error propio en la métrica más dura.
- **C:** dejar `G-RECALL` como diagnóstico y que no bloquee. *Contras:* es la única meta de
  calidad barata que hay; sin ella la fase 2 no tiene criterio de salida.

`[x] A   [ ] B   [ ] C`

**Si dices que no a todo:** se publican las dos columnas y el README explica por qué, pero
entonces `make done MILESTONE=2` no puede evaluar la meta y la fase no cierra.

**Tiempo tuyo:** 5 minutos. **Es un contrato compartido**, así que si eliges A conviene
decírselo al 02 y al 04 — igual que se hizo con Q-012 y Q-013.
**Estado: RESPONDIDA · 2026-08-17**
`>> ` **A**. El recall se compara **a nivel de artículo**: traer el artículo correcto es trabajo
del recuperador y bajar al apartado es del generador, que es lo que cobra `G-CITA-PRECISION`.

**Queda pendiente decírselo al 02 y al 04**, porque es una interpretación de un contrato
compartido y sin avisar los tres repos dejarían de ser comparables. Va con la misma propagación
que Q-012 y Q-013.

---

### Q-017 · fase 2 · BLOQUEA llegar a `G-RECALL5` · el transporte del reordenador

**Qué necesito:** elegir **cómo se sirve** el reordenador, ahora que está medido que hace falta.

**Por qué:** preguntaste si todo modelo debería pasar por Ollama o un proveedor compatible, y
la respuesta corta es que Ollama **no tiene** endpoint de rerank — comprobado hoy contra tu
0.32.14: `/api/rerank` y `/v1/rerank` devuelven 404. `docs/STACK.md` §2.1 ya lo decía y sigue
siendo cierto.

Y no se puede esquivar sin reordenador. Medido sobre los 219 casos:

| Canal | recall@5 | recall@30 |
|---|---:|---:|
| Solo vectorial | 0,790 | 0,941 |
| Solo léxico | 0,365 | 0,804 |
| Híbrido | **0,717** | **0,954** |

El material correcto **ya está** entre los 30 en el 95 % de los casos: no hay que buscar mejor,
hay que **ordenar** mejor. Y ninguna combinación de los dos canales llega a 0,90 en el top-5
sin reordenar — el vectorial solo, que es el mejor de los dos ahí, se queda en 0,790.

**Opciones:**

- **A (por defecto):** cross-encoder **en proceso** (`Qwen3-Reranker-0.6B` con
  `sentence-transformers`), que es lo que dice hoy `STACK.md`. *Pros:* es lo más preciso y lo
  más rápido, y no añade un salto de red al presupuesto de `G-TTFT`. **No exige Mac**: MPS es
  el backend aquí, pero el mismo código corre sobre CUDA o CPU en cualquier máquina.
  *Contras:* es un **segundo camino** para servir modelos —Hugging Face además de Ollama—, son
  ~2 GB de dependencias, y añade una descarga al camino de `G-COLD-CACHE`.
- **B:** el **generador como reordenador**, por `/v1/chat/completions`. *Pros:* cumple tu regla
  de un solo transporte, cero dependencias nuevas, y `G-COLD-CACHE` se queda como está.
  *Contras:* mucho más lento —entra en el presupuesto de `G-TTFT`, que tiene 210 ms de holgura—
  y su calidad como reordenador hay que medirla, no está dada.
- **C:** sin reordenador, y se propone bajar el umbral de `G-RECALL5`. *Contras:* `GOALS.yaml`
  admite propuesta sobre esa meta, pero bajar un umbral para que pase lo que hay es justo lo
  que `CLAUDE.md` prohíbe hacer sin diagnóstico. El diagnóstico está hecho y dice que el
  problema tiene arreglo.

`[ ] A   [x] B   [ ] C`

**Si dices que no a todo:** la fase 2 se queda en 0,717 y no cierra. Se puede seguir a la
fase 3 y volver, pero entonces el agente se construye sobre un recuperador que sabemos flojo.

**Recomendación:** **B primero**, porque cumple tu regla y se mide en una tarde. Si su latencia
no cabe en `G-TTFT`, entonces A con su ADR explicando por qué se aceptó el segundo transporte.

**Tiempo tuyo:** 5 minutos.
**Estado: RESPONDIDA · 2026-08-17**
`>> ` **B**. El reordenador es el generador por `/v1/chat/completions`: **un solo transporte**
para todos los modelos del proyecto. `docs/STACK.md` §2.1 y `CLAUDE.md` invariante 6 dicen hoy
otra cosa —cross-encoder en proceso— así que su cambio va como propuesta aparte; esta entrada
solo fija la decisión.

### Q-018 · fase 2 · BLOQUEA cerrar la fase 3 · aplicar tu propia decisión de Q-017 a dos ficheros de solo lectura

**Qué necesito:** que edites **tú** `docs/STACK.md` §2.1 **y `docs/RULES.md` R8**, porque los dos
son de solo lectura para mí.

**Por qué:** en Q-017 elegiste **B** —un solo transporte, el reordenador es el generador por
`/v1/chat/completions`— y ya está construido y medido así. Pero los dos documentos siguen
diciendo lo contrario, y `CLAUDE.md` remite a ellos como la fuente que manda. No es una decisión
nueva: es tu decisión sin aplicar.

**R8 es el urgente de los dos**, porque no es descriptivo: es una regla **con comando de
verificación**. Dice literalmente *«El reranker no pasa por Ollama. Corre en proceso,
`sentence-transformers`, backend MPS»*, y manda comprobarlo con un
`tests/contract/test_reranker_port.py` que asegure **negativamente** que
`OpenAICompatProvider` **no** implementa `Reranker`. Ese test no existe todavía; si alguien lo
escribiera tal como está redactada la regla, fallaría — y fallaría por estar el código bien. Su
otra comprobación, `grep -r "api/rerank" src/` vacío, **ya da falso positivo**: las dos veces que
aparece son comentarios que explican por qué ese endpoint no existe.

**Qué escribir en `docs/RULES.md`, literal.** Sustituir la fila **R8** entera por:

> | **R8** | **Un solo transporte: todo modelo pasa por Ollama o proveedor compatible.** El reordenador **es** el generador por `/v1/chat/completions` (Q-017). No existe `/api/rerank` ni un segundo camino de servir modelos | `grep -r "sentence_transformers\|CrossEncoder" src/ pyproject.toml` vacío + `tests/unit/test_rerank.py` | B |

**Qué escribir, literal.** En `docs/STACK.md`, punto 1 de §2.1, sustituir desde «El reranker
corre **en proceso**…» hasta «…se estrella.» por:

> El reranker **es el propio generador**, por `/v1/chat/completions` (Q-017, 2026-08-17): un
> solo transporte para todos los modelos del proyecto. Se le pasan los candidatos numerados y
> devuelve el orden; la resolución la hace código. `Qwen3-Reranker-0.6B` y `bge-reranker-v2-m3`
> quedan como retadores **no adoptados**: exigían un segundo camino de servir modelos.

Las filas «Reranker» y «Reranker (retador)» de la tabla se dejan como están —son la
investigación, no el pin— añadiendo `no adoptado (Q-017)` en su columna de motivo.

**Opciones:**

- **A (por defecto):** lo escribes tal cual arriba. *Pros:* el repo deja de decir dos cosas.
  *Contras:* ninguno; es transcribir tu decisión.
- **B:** te lo repiensas y vuelves a A de Q-017 (cross-encoder en proceso). *Pros:* es más
  rápido y más preciso. *Contras:* rompe tu regla del transporte único, son ~2 GB de
  dependencias y hay que rehacer lo medido.
- **C:** no tocar nada y dejar la contradicción anotada aquí. *Contras:* `STACK.md` y `RULES.md`
  mandan sobre `CLAUDE.md` por regla escrita, así que la contradicción se resuelve en contra de
  lo que de verdad hay construido. Y R8 quedaría como una regla que, cumplida al pie de la letra,
  rompe el sistema.

`[ ] A   [ ] B   [ ] C`

**Si dices que no a todo:** la fase 2 no se para, pero la 3 sí acaba parándose: R8 es una regla
de nivel **B** y su comprobación pertenece al gate. Mientras tanto queda anotado en `JOURNAL.md`
y en el ADR-022 para que al menos no sea invisible.

**Recomendación:** **A**, y R8 antes que `STACK.md` si solo vas a hacer una.

**Tiempo tuyo:** 5 minutos.
**Estado: SIN OBJETO · 2026-08-17 · la responde Q-020**
`>> ` **No hay nada que escribir.** Q-020 eligió **A** y devuelve el proyecto al cross-encoder en
proceso, así que `docs/RULES.md` R8 y `docs/STACK.md` §2.1 —que nunca se llegaron a cambiar—
vuelven a describir lo que hay. Esta entrada se queda como registro de que hubo un tramo en el
que el código y los documentos ratificados decían cosas distintas, y de cuánto duró.

**Queda una cosa pequeña**: la segunda comprobación de R8, `grep -r "api/rerank" src/` vacío, da
falso positivo — las dos apariciones son comentarios que explican por qué ese endpoint no existe.
No bloquea nada y se anota aquí para que no se descubra midiendo.

### Q-019 · fase 2 · BLOQUEA la fase 3 · el reordenador no cabe en el presupuesto de latencia que tú ratificaste

**Qué necesito:** decidir si el reordenador entra o no en el camino interactivo, sabiendo que
**no puede entrar sin romper `G-TTFT`**.

**Por qué:** `docs/RULES.md` §2.1 reparte el presupuesto de 1.500 ms por etapas y le da al
rerank **400 ms**. Ese número venía de un cross-encoder en proceso, que es lo que decía el
`STACK.md` de entonces. En Q-017 elegiste **B** —el reordenador es el generador, un solo
transporte— y ahora está medido lo que cuesta:

| | medido | presupuesto de RULES §2.1 |
|---|---:|---:|
| Una llamada al reordenador (30 candidatos) | **~4.600 ms** | 400 ms |
| Cuatro llamadas (reordenado por ventanas) | **~18.000 ms** | 400 ms |

No es un ajuste: son 11 y 46 veces el presupuesto. Y `G-TTFT` bloquea desde la fase 3, así que
esto no se puede dejar para más adelante sin construir la fase 3 encima de una decisión que
habrá que deshacer.

**Lo que está en juego de verdad no es la latencia, es qué significa `G-RECALL5`.** Si el
reordenador no corre al responder, el usuario recibe el top-5 de la fusión —**0,727** medido— y
no el número que publica la meta. La meta seguiría siendo cierta sobre el sistema construido y
falsa sobre el producto, que es la clase de número que este proyecto existe para no publicar.

Y hay un segundo desfase, menor pero del mismo origen: la nota de `G-RECALL5` en `GOALS.yaml`
dice *«Coste ~90 s y sin LLM generador: es la única meta de calidad barata»*. Con Q-017 el
reordenador **es** el generador, y en frío la meta cuesta ~65 min. Sigue costando 6,2 s desde la
caché de juicios —por eso se puede quedar en el gate— pero la frase ya no describe lo que pasa.

**Opciones:**

- **A (recomendada):** el reordenador es **de evaluación**, no del camino interactivo. El
  producto responde con el top-5 de la fusión. *Pros:* `G-TTFT` intacto, el arranque en frío
  intacto, y la fase 3 se construye sobre lo que de verdad va a correr. *Contras:* el usuario
  recibe 0,727 y no 0,9. Habría que decirlo en el README con esas palabras, y `G-RECALL5` pasa a
  medir **el techo del recuperador**, no la experiencia.
- **B:** el reordenador entra y se renegocia `G-TTFT` (`propuesta_admisible: true`). *Pros:* el
  usuario recibe el mejor top-5. *Contras:* 18 s hasta el primer token no es un tutor, es un
  proceso por lotes. Y `docs/RULES.md` §2.2 ya resolvió una vez el conflicto entre *streaming* y
  verificación; volver a moverlo por la misma pieza empieza a ser un patrón.
- **C:** reordenador **reducido** en el camino interactivo — una sola ventana de 10 en vez de
  cuatro llamadas— y el completo solo en evaluación. *Pros:* algo de mejora dentro de un
  presupuesto renegociable a ~5 s. *Contras:* dos configuraciones que medir y mantener, y
  `G-RECALL5` tendría que publicar **las dos**, que es lo honesto pero es más trabajo.

`[x] A   [ ] B   [ ] C`

**Si dices que no a todo:** me quedo con **A** al empezar la fase 3, porque es lo único que no
rompe una meta ya ratificada, y lo declaro así en el README y en el CHANGELOG.

**Tiempo tuyo:** 10 minutos. Es una decisión de producto, no de implementación: cuánto está
dispuesto a esperar quien pregunta.

**Estado: PENDIENTE**
`>> `

### Q-020 · fase 2 · el hueco de `G-RECALL5` ya no es de ingeniería · reabrir Q-017 con la evidencia nueva

**Qué necesito:** decidir qué se hace con `G-RECALL5`, **sabiendo que el trade-off que se te
presentó en Q-017 ya no es el que hay.**

**Por qué.** En Q-017 elegiste **B** —el reordenador es el generador, un solo transporte— frente
a **A**, un cross-encoder en proceso. La comparación que tenías entonces decía que A era «más
preciso y más rápido» pero costaba un segundo camino de servir modelos. Lo que se ha medido
desde entonces cambia las dos columnas:

| | lo que se dijo en Q-017 | lo que está medido hoy |
|---|---|---|
| Coste de B | «más lento, hay que medirlo» | **4.600 ms** contra un presupuesto de **400 ms** (`RULES` §2.1) |
| Calidad de B | «hay que medirla, no está dada» | `G-RECALL5` **0,852** contra un umbral de 0,90 |
| Qué queda por probar | mucho | **nada**: dieciséis experimentos, diez negativos |

Y el techo no es el problema: con 80 candidatos por canal el artículo correcto aparece en **216
de 216** casos. El corpus lo tiene y la búsqueda lo encuentra siempre. **Todo el hueco es de
ordenación**, y el reordenador elegido no llega ni en tiempo ni en calidad.

**Lo que se probó y no bastó**, cada cosa con su número en `docs/JOURNAL.md`: subir el tope del
reordenador de 10 a 30 (esto **sí** funcionó, +8 puntos), cambiar el modelo de embeddings al
principal del `STACK.md`, tres troceados distintos del corpus, ponderar la fusión, pedir más
candidatos por canal, dos formatos de prompt, el reordenado por ventanas, y el formato de
instrucción que documenta `Qwen3-Embedding`.

**Y no es cuestión de tamaño.** Repetido el 9B con el prompt de ahora y el índice que se sirve
—la medida anterior era de otro prompt y otro índice, y no valía—: **0,843** contra los 0,852 del
4B, tardando un 56 % más. Un modelo 2,25 veces mayor no ordena mejor. **No es el tamaño del
modelo, es el tipo**, y un cross-encoder está entrenado exactamente para esto.

**El hallazgo que lo explica:** con trozos afilados —troceado por apartado— el reordenador
aporta **un** caso; con trozos gruesos aporta **veintiséis**. Su trabajo real es tapar el ruido
del embedding, no juzgar mejor que él. Un modelo generalista de 4B no distingue entre el
artículo 74, el 108, el 109 y el 110, que es exactamente lo que hay que distinguir aquí.

**Opciones:**

- **A · reabrir Q-017 y adoptar el cross-encoder** (`Qwen3-Reranker-0.6B`). *Pros:* está
  **entrenado para ordenar**, y es la única opción que arregla **las dos** cosas a la vez — cabe
  en los 400 ms de `RULES` §2.1 y devuelve el reordenador al camino interactivo, que es lo que
  Q-019 acaba de descartar. *Contras:* rompe tu regla del transporte único, ~2 GB de
  dependencias y una descarga más en el arranque en frío. Y hay que medirlo: puede no llegar a
  0,90 tampoco, y entonces habríamos pagado eso por nada.
- **B · aceptar 0,852 y proponer bajar el umbral.** `GOALS.yaml` lo admite
  (`propuesta_admisible: true`) y la condición que `CLAUDE.md` pone —diagnosticar la causa real
  antes de tocar un número— **está cumplida y escrita**. *Pros:* la fase 2 cierra hoy con lo que
  hay. *Contras:* es bajar la vara, y aunque esté justificado conviene decirlo con esas
  palabras en el README y en el CHANGELOG.
- **C · dejar `G-RECALL5` roja y seguir a la fase 3.** *Pros:* el agente se puede construir; el
  recuperador funciona (211 de 216 entre los 30). *Contras:* la fase 2 no cierra, y se construye
  sobre un recuperador que sabemos que no llega. `PLAN.md` no lo prohíbe pero tampoco lo prevé.

`[x] A   [ ] B   [ ] C`

**Si dices que no a todo:** me quedo en **C** y lo declaro así, porque es lo único que no
requiere ni una decisión tuya ni tocar un umbral.

**Recomendación:** **A**, y solo por una razón: es la única que además arregla `G-TTFT`. Si su
medida tampoco llega a 0,90, entonces **B** con el diagnóstico completo delante — que para eso
se ha hecho.

**Tiempo tuyo:** 10 minutos. Si eliges A, la medición la hago yo: unas dos horas de máquina.

<!-- Marca [x] puesta por Samuel el 2026-08-17. Cierre formalizado por el agente en el mismo
     turno, con su permiso explícito ("ya esta elegido podemos seguir"), igual que en Q-004. -->
**Estado: RESPONDIDA · 2026-08-17**
`>> ` **A**. Se reabre Q-017: el reordenador pasa a ser un **cross-encoder en proceso**
(`Qwen3-Reranker-0.6B`, `sentence-transformers`), que es lo que `docs/STACK.md` §2.1 y
`docs/RULES.md` R8 decían desde el principio. Se acepta el segundo camino de servir modelos
porque es la única opción que arregla a la vez la calidad y `G-TTFT`, y porque lo que se midió
del generador-como-reordenador —4.600 ms y 0,852— no es lo que se sopesó en Q-017.

---

## PROPUESTA P-002 · 2026-08-18 · fase 2

**Tipo:** `bajar-umbral`
**Afecta a:** `docs/GOALS.yaml :: G-RECALL5` (valor actual **0.90**)

**Qué pido.** Bajar `G-RECALL5` a **0.80**, que es el máximo alcanzado y medido. `G-RECALL30`
**no se toca**: pasa su umbral con 0,977 contra 0,97.

**Por qué.** Veinte configuraciones medidas sobre los mismos 216 casos positivos del golden set
`v2`, doce con resultado negativo, todas con su número en `docs/JOURNAL.md` (2026-08-17, tres
entradas). El diagnóstico está cerrado y dice tres cosas:

1. **No falta información.** Con 80 candidatos por canal el artículo correcto aparece en
   **216 de 216** casos. El corpus lo tiene y la búsqueda lo encuentra siempre.
2. **No falta recuperador.** `G-RECALL30` da 0,977: el artículo está entre los 30 en 211 de 216.
3. **Falta un ordenador mejor, y no existe entre lo probado.** Ningún reordenador llega a 0,90:

| reordenador | `G-RECALL5` | p95 |
|---|---:|---:|
| ninguno | 0,727 | — |
| `bge-reranker-v2-m3` ← el que se sirve | **0,801** | 400 ms |
| `Qwen3-Reranker-0.6B` | 0,787 | 886 ms |
| generador `qwen3.5:4b` | 0,852 | 4.600 ms |
| generador `qwen3.5:9b` | 0,843 | ~7.100 ms |

**Qué he descartado, con su coste medido y no supuesto.** Tope del reordenador en 10 (techo
0,785) · modelo de 9B (0,843, +56 % de tiempo) · 1.200 caracteres de contexto (peor que 500,
doble de tiempo) · RRF entre el orden de fusión y el del reordenador (0,782) · formato de
instrucción de `Qwen3-Embedding` en inglés (0,722) y en castellano (0,708) · reordenado por
ventanas de 10 (0,806) · ponderar la fusión 10:1 a favor del vectorial (sube el top-5 a 0,819
pero **rompe `G-RECALL30`**, que baja a 0,954) · troceado por apartado (0,806) · troceado
multinivel (0,824) · instrucción de dominio en el cross-encoder (0,773).

**Por qué 0.80 y no 0.85.** Porque 0,85 solo lo alcanza el generador puesto a ordenar, y ese
número **el producto no lo entrega**: cuesta 4.600 ms contra un presupuesto de 400 ms
(`RULES` §2.1), no es reproducible entre corridas y Q-019 lo sacó del camino interactivo. 0,801
es lo que recibe quien pregunta. Ver **ADR-024**.

**Lo que se pierde, dicho claro.** 0.80 deja **cero margen**: el valor medido es 0,8009. Es
sostenible solo porque el cross-encoder es determinista byte a byte —comprobado con dos corridas
en frío idénticas— así que la meta pasa a ser **un suelo del que no se puede bajar**, no una
aspiración. Cualquier cambio de índice, troceado o reordenador que empeore un solo caso la pone
en rojo, que es exactamente lo que debe hacer.

**Alternativa si dices que no.** Seguir a la fase 3 con `G-RECALL5` en rojo y `make done
MILESTONE=2` sin cerrar. El agente se puede construir igual —el material está en el top-30 en el
97,7 % de los casos— pero la fase 2 queda abierta y el gate de la 3 arrastra una meta roja que no
tiene nada que ver con la 3.

**Estado: APROBADA · 2026-08-18**

---

## PROPUESTA P-003 · 2026-08-19 · fase 3

**Tipo:** `bajar-umbral`
**Afecta a:** `docs/GOALS.yaml :: G-RECALL5` (**0.80**) y `:: G-RECALL30` (**0.97**)

**Qué pido.** Bajar `G-RECALL5` a **0.79** y `G-RECALL30` a **0.96**. Las dos quedan **a un
caso** de su umbral actual, y las dos bajan por el mismo motivo: el troceado cambió.

**Por qué. El troceado por apartado no es una preferencia, es un requisito de la fase 3.**
`G-CITA-PRECISION` bloquea desde la fase 3, y el contrato compartido dice que si el golden set
especifica apartado, la cita **debe** incluirlo. Las 216 refs positivas del golden set lo
llevan; el índice `articulo-v1` no tiene **ninguna**. Con él, `G-CITA-PRECISION` es **cero por
construcción** — el sistema no puede citar lo que no indexa. Medido: 0,0000 sobre 25 casos, y no
por calidad.

**Lo que se recupera antes de pedir nada.** Al cambiar el índice las dos metas caían a 0,764 y
0,968. Buscando la causa apareció un defecto real en el orden de las operaciones: se fusionaba
por apartado y se colapsaba después, así que un artículo con tres apartados metía tres entradas
en el RRF —tres puntuaciones mediocres en vez de una buena— y como `1/(k+r)` es convexa, ganaba
plaza por acumulación y no por relevancia. Colapsando **antes** de fusionar:

| | `G-RECALL5` | `G-RECALL30` |
|---|---:|---:|
| `articulo-v1` (fase 2) | 0,801 | 0,977 |
| `apartado-v1`, fusionar y colapsar | 0,764 | 0,968 |
| `apartado-v1`, **colapsar y fusionar** | **0,796** | **0,968** |
| *umbral actual* | *0,80* | *0,97* |

Siete casos recuperados de los ocho perdidos. Lo que queda es **un caso en cada meta**.

**Qué he descartado, con su número.** Barrido de `K_CANAL` sobre el índice nuevo: 30 → 0,968 ·
45 → 0,963 · 60 → 0,968 · 90 → 0,958 · 120 → 0,963. Ninguno llega a 0,97, y el mejor es el más
barato, así que se queda en 30 — menos candidatos es menos trabajo para el reordenador dentro
del presupuesto de `G-TTFT`.

**Por qué 0.79 y 0.96 y no menos.** Porque es lo medido menos el redondeo, igual que en P-002.
Los dos siguen siendo **suelos de los que no se puede bajar**: cualquier cambio que empeore un
caso los pone en rojo.

**Alternativa si dices que no.** Volver a `articulo-v1` y aceptar que `G-CITA-PRECISION` vale
cero por construcción. Las dos metas de recall quedarían verdes y la fase 3 no cerraría nunca,
porque su meta insignia sería inalcanzable por una decisión de troceado y no por el sistema.

**Estado: PENDIENTE**

---

### Q-021 · fase 3 · DIVERGENCIA DE CONTRATO DECLARADA · granularidad de la precisión de cita

**Qué es esto.** No es una pregunta: es el registro de una decisión que ya tomaste el
2026-08-20 («vamos con B») y de lo que implica, porque toca un contrato compartido y **eso se
declara en los dos repos** (regla de `CLAUDE.md`, igual que Q-012 y Q-013).

**Qué dice el contrato.** `docs/CONTRACTS/retrieval-metrics.md`, tabla de precisión de cita:
*«Si el golden set especifica apartado, la cita **debe** incluirlo. `21` cuando lo correcto es
`21.1` es fallo»*.

**Por qué diverge este repositorio.** Porque ese nivel es inalcanzable, y **no por el
generador**. Medido el 2026-08-20 sobre 80 casos positivos, cuántas veces el apartado exacto
está entre las fuentes que se le ofrecen al modelo:

| candidatos ofrecidos | con colapso por artículo | sin colapso |
|---:|---:|---:|
| 5 | 0,388 | 0,463 |
| 8 | 0,463 | 0,537 |
| 12 | 0,487 | **0,562** |

El umbral de `G-CITA-PRECISION` es **0,85**. Ni ofreciéndole doce fuentes sin colapsar se pasa
de 0,56: **no se le ofrece lo que se le exige citar.** El recuperador encuentra el *artículo*
bien —0,80 en top-5 y 0,97 en top-30— y el *apartado* aproximadamente la mitad de las veces.

**Qué se hace.** `G-CITA-PRECISION` se compara a **nivel de artículo**, y la lectura estricta se
publica al lado en el mismo informe. Es la misma lectura que Q-016 eligió para el recall, y
resolver la misma pregunta distinto en dos sitios es lo que crea las contradicciones que este
proyecto lleva dos fases pagando.

Medido con el prompt v3 sobre 25 casos: **0,167 estricta · 0,444 a nivel de artículo.**

**Lo que se pierde, y conviene que esté escrito.** Con esta lectura, citar `art34.2` cuando lo
correcto es `art34.1` **cuenta como acierto**. El sistema puede señalar el apartado de al lado y
la métrica no lo verá. El README lo dirá con esas palabras.

**Y una tensión con tu propia respuesta de Q-016**, que señalo para que la ratifiques sabiéndolo:
allí escribiste que *«bajar al apartado es del generador, que es lo que cobra
`G-CITA-PRECISION`»*. Esta decisión dice que el generador tampoco se mide por el apartado. Es
coherente con lo medido —no se le ofrece— pero deja **a nadie** cobrando esa precisión, y eso es
una pérdida real de garantía, no un tecnicismo.

**Pendiente de propagar:** decírselo al **02** y al **04**, como Q-012, Q-013 y Q-016. Queda
escrito en `indexkeeper-04/docs/PARA-SAMUEL.md` con esta misma fecha.

**Estado: RESPONDIDA · 2026-08-20**
`>> ` **B**, decidido por Samuel: la precisión de cita se mide a nivel de artículo, las dos
lecturas se publican, y la divergencia con el contrato queda declarada aquí y en el 04.
