# Citebound · tutor de normativa de circulación

> Responde preguntas sobre normativa de circulación española **citando el artículo exacto**,
> verifica literalmente el fragmento que cita, y se abstiene cuando no puede verificarlo.

**No puede citar lo que no ha recuperado. Por construcción, no por buena voluntad.**

---

## Dónde está, y con qué números

Una fase **solo** se marca hecha cuando `make done MILESTONE=N` devuelve 0. No hay «casi hecho»:
el criterio de salida de cada fase es un comando que devuelve 0 o 1, y está en
[`docs/PLAN.md`](docs/PLAN.md).

- [x] **0 · Esqueleto vertical que camina** — doce condiciones en verde · [números](CHANGELOG.md)
- [x] **1 · Scoring congelado y golden set** — el corrector se cerró **antes** de anotar el primer caso · **274 casos**, 15,3 h de revisión humana
- [~] **2 · Retrieval híbrido** — medido: `G-RECALL30` **0,977** ✓ · `G-RECALL5` en curso
- [ ] **3 · Agente** — cita cerrada, verificación literal, abstención y reintento acotado
- [ ] **3b · Interfaz de práctica de test** — el producto. Frontera única: la API HTTP
- [ ] **4 · Evals, juez y determinismo** — que cualquiera obtenga los mismos números
- [ ] **5 · Endurecimiento y publicación** — suite adversarial, observabilidad, arranque en frío
- [ ] 6 · Personalización — **ampliación**. No hacerla no es un fallo, y se dice así

Las metas de generación —`G-HALLUC`, `G-QUOTE-LIT`, `G-CITA-PRECISION`, `G-ABST-*`— **no están
medidas**: hasta la fase 3 no hay generador, y un cero sin generador es un cero trivial. Cuando
haya resultados se publicarán con su `n`, su intervalo de confianza y el artefacto del que salen,
salgan como salgan.

---

## El problema

Un RAG normal recupera documentos, se los pasa al modelo y el modelo redacta la respuesta
*mencionando* sus fuentes. El fallo está en esa última palabra: cuando el modelo escribe
«…según el artículo 47.3…», esos caracteres son tokens que predice igual que predice el resto de
la frase. Si el fragmento recuperado era el artículo 45, **nada en el sistema se entera**. Después
se mide *faithfulness* con un juez LLM, sale 0,92, y todo el mundo se queda tranquilo.

En un dominio donde la respuesta equivocada tiene consecuencias, ese 0,92 es una opinión con
decimales.

## La solución: cita cerrada

El generador **tiene prohibido escribir referencias**. Escribe huecos numerados —`[[REF:n]]` con
`n ∈ {1..5}`— sobre los fragmentos que la búsqueda sí recuperó. La traducción de `n` a
`RD-1428/2003#art34.1` la hace **código**, nunca el modelo.

![Cita cerrada: recuperar, redactar con huecos, y resolver y verificar en código](docs/img/cita-cerrada.svg)

Cuatro consecuencias, y ninguna depende de que un modelo se porte bien:

| | |
|---|---|
| **Citar un artículo inexistente es inexpresable** | El modelo elige entre 1 y 5. No hay forma de escribir otra cosa |
| **Un número fuera de rango se detecta en su token** | No es un filtro sobre la respuesta ya escrita |
| **Cada fragmento entrecomillado se verifica letra a letra** | Comparación de cadenas tras normalización declarada. Sin LLM, sin coste |
| **Abstenerse es una salida de primera clase** | Y se mide en los dos sentidos, para que callarse siempre no sea la estrategia óptima |

**Lo que esto cuesta, dicho en voz alta:** si la búsqueda falla, el sistema no «se acuerda» del
artículo — se abstiene o cita peor. La calidad del retrieval deja de ser un detalle y pasa a ser
**el techo del sistema**. Por eso la fase 2 existe, y por eso se mide por separado antes y después
de reordenar.

Y hay una capa que **no** queda garantizada, solo medida: que la *interpretación* del artículo sea
correcta. Se hace determinista todo lo que puede serlo, y el residuo se acota y se publica.

---

## Retrieval, medido

216 preguntas positivas del golden set `v2`, `recall@k` como intersección de conjuntos de
`LegalRef` a nivel de artículo ([por qué a nivel de artículo](docs/PARA-SAMUEL.md)). Reproducible
con `make eval-retrieval`.

![Recall por canal](docs/img/recall-por-canal.svg)

| Canal | recall@5 | recall@30 |
|---|---:|---:|
| Solo vectorial · HNSW coseno | 0,792 | 0,954 |
| Solo léxico · `ts_rank_cd` | 0,370 | 0,815 |
| Híbrido · fusión RRF | 0,727 | **0,977** |
| Híbrido + reordenador | **RECALL5_FINAL** | **0,977** |
| *Umbral que exige el gate* | *≥ 0,90* | *≥ 0,97* |

**El híbrido es peor que el vectorial solo en el top-5 y mejor en el top-30.** No es un accidente
ni un defecto: la fusión mete candidatos léxicos que ensucian la cabeza de la lista y a cambio
ensancha la red. Justo por eso hay un reordenador — buscar más y ordenar después es más barato
que acertar a la primera.

**Todo lo que se probó y salió mal está anotado**, con su número, en
[`docs/JOURNAL.md`](docs/JOURNAL.md): un modelo de 9B que rescata menos que el de 4B, 1.200
caracteres de contexto que van peor que 500, una fusión RRF entre el orden de fusión y el del
reordenador, y el formato de instrucción que documenta `Qwen3-Embedding` — que **empeora** aquí,
en inglés y en castellano.

---

## Corpus

XML **consolidado** del BOE, congelado por `sha256` en [`corpus/MANIFEST.yaml`](corpus/MANIFEST.yaml).
No PDF, no *scraping*: la fuente ya publica la jerarquía exacta y sin pérdida
([ADR-001](docs/adr/001-corpus-fuente-boe.md)).

| | |
|---|---|
| Norma | RD 1428/2003 · Reglamento General de Circulación |
| Identificador | `BOE-A-2003-23514` |
| Consolidación | 2026-07-31 |
| Contenido | 232 bloques `precepto` · **236 unidades citables** tras el parseo · 103 encabezados |
| Troceado | **235 chunks** · el artículo 51, derogado, queda fuera · 0 referencias duplicadas |

La unidad de verdad es la **`LegalRef`** (`norma#artNN.apartado`), nunca el `chunk_id`. Eso es lo
que permite cambiar el troceado, el modelo de embeddings o el reordenador sin invalidar el
conjunto de evaluación — y es exactamente lo que se hizo en la fase 2 sin tocar un solo caso.

## Golden set

**274 casos · 216 positivos · 58 negativos · 8 materias.** Sellado por `sha256` en
[`evals/golden/CHECKSUMS`](evals/golden/CHECKSUMS), append-only por versión: corregir crea una
`v2` con su ADR, nunca un `sed` sobre la `v1`.

Lo que lo distingue no es el tamaño, es la procedencia. **Cada caso lo revisó Samuel a mano, uno
a uno, a lo largo de 15,3 horas**, y ningún caso entra sin revisor y sin fecha — es la regla dura
nº 3 del contrato compartido: generación asistida por LLM sí, aprobación automática no. La
trazabilidad completa está en [`evals/golden/cola/PROCEDENCIA.md`](evals/golden/cola/PROCEDENCIA.md).

Los **negativos** son la mitad interesante: preguntas que el corpus **no** responde. Sin ellos,
abstenerse siempre sería la estrategia óptima y `G-CITA-PRECISION` daría 1,00 a un sistema mudo.
Seis de ellos resultaron ser respondibles al revisarlos y cambian de bando en el montaje: si
entraran como negativos, la métrica premiaría callarse justo donde hay que hablar.

Tres casos salieron en la `v2` ([ADR-021](docs/adr/021-golden-v2-tres-casos-sin-texto.md)) con un
criterio escrito y aplicable por otro: *sale un caso si su enunciado, sin la imagen, no identifica
el supuesto de hecho.* Un primer recuento decía cinco; al leerlos enteros eran tres, y quedarse
con el número honesto costó que la meta no cerrara ese día.

---

## Stack

Python 3.12 · FastAPI + SSE · PostgreSQL 18 + pgvector 0.8.6 · LangGraph como máquina de estados
(sin LangChain) · Ollama en el host. Versiones exactas con `==` y motivo en
[`docs/STACK.md`](docs/STACK.md).

| Pieza | Modelo | Licencia |
|---|---|---|
| Embeddings | `Qwen3-Embedding-0.6B` · 1024 dim | Apache-2.0 |
| Generador **y reordenador** | `Qwen3.5-4B` (MLX) | Apache-2.0 |
| Juez (fase 4) | `Gemma 4 12B` | — |

Tres precisiones que suelen darse por supuestas y aquí no lo son:

- La búsqueda léxica es `ts_rank_cd` con configuración `spanish_unaccent`, **y no se llama BM25
  porque no lo es** mientras no haya una extensión BM25 de verdad instalada.
- **Un solo transporte.** El reordenador no es un modelo aparte: es el propio generador por
  `/v1/chat/completions`. Ollama no tiene endpoint de rerank, y montar un segundo camino de
  servir modelos costaba ~2 GB de dependencias y una descarga más en el arranque en frío
  ([ADR-022](docs/adr/022-reordenador-por-el-mismo-transporte.md)).
- **Nada exige un Mac.** Los modelos van por Ollama o cualquier proveedor compatible con la API
  de OpenAI; el backend MLX es una elección de la máquina de desarrollo, no un requisito.

## Cómo está gobernado

Es la parte más interesante del repositorio en este momento, y probablemente lo que más se lee.

- **[`docs/GOALS.yaml`](docs/GOALS.yaml)** — 24 metas ejecutables. Cada una con umbral estructurado,
  comando de medida, artefacto y desde qué fase bloquea.
- **[`docs/RULES.md`](docs/RULES.md)** — 20 invariantes, cada uno con el comando que lo verifica.
  Una regla sin comprobación mecánica es una sugerencia, y las sugerencias se erosionan.
- **[`docs/CONSTITUCION.md`](docs/CONSTITUCION.md)** — separación entre lo que el agente puede
  escribir, lo que propone y lo que no toca jamás. Seis mecanismos anti-*gaming*.
- **[`docs/adr/`](docs/adr/)** — decisiones con sus alternativas descartadas y el coste de cada una.
- **[`docs/JOURNAL.md`](docs/JOURNAL.md)** — qué se intentó, qué falló y **qué número salió**.
- **[`docs/CONTRACTS/`](docs/CONTRACTS/)** — contratos compartidos con otros proyectos. Copias
  literales: un `diff` contra el original es un test.

Dos reglas que gobiernan de verdad: **el agente puede cambiar cómo llega al número, nunca el
número** — los umbrales están firmados con un hash y bajarlos exige una propuesta escrita. Y
**lo verificable deterministamente no se delega a un LLM**: el juez es el último recurso y solo
vale con su κ publicado.

## Empezar

```bash
make up                  # Postgres + pgvector, fijado por digest
make warm                # residencia de los modelos. NUNCA dentro de `up`: rompe el cronómetro
uv run citebound ingest  # 235 chunks desde el XML congelado
make smoke-f0            # ingesta + 3 preguntas + al menos una ref presente en refs.json
make eval-retrieval      # G-RECALL5 y G-RECALL30 contra el golden set (6 s desde cache)
make done MILESTONE=2    # la única definición de «hecho»: exit 0 o 1
```

Requiere [Ollama](https://ollama.com) **en el host** (no en compose) y Docker. `make check-ollama`
lo comprueba y dice qué falta.

---

## Fuentes

**Normativa.** Real Decreto 1428/2003, de 21 de noviembre, Reglamento General de Circulación.
Agencia Estatal Boletín Oficial del Estado, [datos abiertos](https://www.boe.es/datosabiertos/),
identificador `BOE-A-2003-23514`, consolidación 2026-07-31. Información del sector público,
reutilizable conforme a la normativa española. El texto se reproduce sin modificar.

**Banco de preguntas.** Banco de preguntas tipo test de circulación de terceros, de acceso público.
**No se redistribuye** en este repositorio en ninguna de sus versiones: lo que se publica es el
golden set derivado, con la revisión humana que lo valida. Las imágenes asociadas no se descargan,
no se procesan y no se publican.

**Modelos.** [`Qwen3-Embedding-0.6B`](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) y
[`Qwen3.5`](https://huggingface.co/Qwen), Apache-2.0, ejecutados en local vía Ollama. No se
redistribuyen.

**Método.** La fusión de canales es *Reciprocal Rank Fusion* con `k=60` — Cormack, Clarke y
Buettcher, [«Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning
Methods»](https://dl.acm.org/doi/10.1145/1571941.1572114), SIGIR 2009. El detalle completo, con
lo que no se copió y por qué, en [`docs/adr/`](docs/adr/) y
[`docs/CONTRACTS/`](docs/CONTRACTS/).

## Aviso

Este proyecto no es una fuente jurídica y sus respuestas no son asesoramiento legal. El carácter
oficial del texto normativo corresponde únicamente a su publicación en el BOE.

## Licencia

Código bajo [Apache 2.0](LICENSE). Los datos tienen procedencia y condiciones propias, declaradas
en [`NOTICE`](NOTICE).
