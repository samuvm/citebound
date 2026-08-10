# Citebound · tutor de normativa de circulación

> Responde preguntas sobre normativa de circulación española **citando el artículo exacto**,
> verifica literalmente el fragmento que cita, y se abstiene cuando no puede verificarlo.

**No puede citar lo que no ha recuperado. Por construcción, no por buena voluntad.**

---

> ### Fase 0 cerrada. **Ninguno de los umbrales de calidad está medido todavía**
>
> `make done MILESTONE=0` devuelve 0 con las doce condiciones en verde, y los números de esa
> puerta están en el [CHANGELOG](CHANGELOG.md): 295 tests, 100 % de cobertura en los paquetes
> con TDD obligatorio, 587 de 588 mutantes muertos.
>
> **Los umbrales de la tabla de abajo siguen sin medir**, y `G-HALLUC = 0` hoy vale poco: en la
> fase 0 **no hay generador**, así que no hay nada que pueda alucinar. El cero de verdad —el que
> viene de la cita cerrada— llega en la fase 3. Cuando haya resultados se publicarán con su `n`,
> su intervalo de confianza y el artefacto del que salen, salgan como salgan.

## Dónde está

Una fase **solo** se marca hecha cuando `make done MILESTONE=N` devuelve 0. No hay «casi hecho»:
el criterio de salida de cada fase es un comando que devuelve 0 o 1, y está en
[`docs/PLAN.md`](docs/PLAN.md).

- [x] **0 · Esqueleto vertical que camina** — `make done MILESTONE=0` → exit 0 · [números en el CHANGELOG](CHANGELOG.md)
- [ ] **1 · Scoring congelado y golden set** — el corrector se cierra **antes** de anotar el primer caso
- [ ] **2 · Retrieval híbrido** — cada cambio se acepta o se tira con el número de recall, no con la sensación
- [ ] **3 · Agente** — cita cerrada, verificación literal, abstención y reintento acotado
- [ ] **3b · Interfaz de práctica de test** — el producto. Frontera única: la API HTTP
- [ ] **4 · Evals, juez y determinismo** — que cualquiera obtenga los mismos números
- [ ] **5 · Endurecimiento y publicación** — suite adversarial, observabilidad, arranque en frío
- [ ] 6 · Personalización — **ampliación**. No hacerla no es un fallo, y se dice así

<details>
<summary><b>Fase 0, tarea a tarea</b></summary>

- [x] `0.1` corpus congelado desde el BOE, con su `sha256` en `corpus/MANIFEST.yaml`
- [x] `0.2` `domain/legalref.py` — el tipo del que depende todo lo demás
- [x] `0.3` `ingest/boe_xml.py` — 236 preceptos, 0 referencias duplicadas
- [x] `0.4` `ingest/chunking.py` — 235 chunks, identificadores deterministas
- [x] `0.5` `db/ddl.sql` — verificado contra PG18 real, ingerir dos veces no duplica
- [x] `0.6` `providers/embeddings.py` — grabado contra el modelo real
- [x] `0.7` `retrieval` + `api` + `cli` + `compose.yaml` + `Makefile`
- [x] salida: `make up && make warm && make smoke-f0` → exit 0, en 10,0 s

Hecho además: contrato `chunks-ddl.sql` subido a v2 y **verificado ejecutándolo** contra PG18 +
pgvector; `pyproject.toml` con versiones exactas; y cuatro ADR.
El detalle vivo está en [`docs/JOURNAL.md`](docs/JOURNAL.md), incluidos los cuatro fallos que
encontró medir contra el corpus en vez de razonar sobre él. Los números de cada puerta van, fase
a fase, en [`CHANGELOG.md`](CHANGELOG.md).

</details>

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

```
                     ┌─────────────────────────────────────────┐
  pregunta ─────────►│  recuperar 30  →  reordenar  →  top 5   │
                     └────────────────────┬────────────────────┘
                                          ▼
                     ┌─────────────────────────────────────────┐
                     │  el modelo redacta con  [[REF:n]]       │
                     └────────────────────┬────────────────────┘
                                          ▼
                     ┌─────────────────────────────────────────┐
                     │  código:  n → LegalRef                  │
                     │  código:  ¿el fragmento está literal?   │
                     └───┬──────────────┬──────────────────┬───┘
                         ▼              ▼                  ▼
                    responder      retractar          abstenerse
                    con la cita    y reintentar       con motivo
                                   (máx. 2)
```

Cuatro consecuencias, y ninguna depende de que un modelo se porte bien:

| | |
|---|---|
| **Citar un artículo inexistente es inexpresable** | El modelo elige entre 1 y 5. No hay forma de escribir otra cosa |
| **Un número fuera de rango se detecta en su token** | No es un filtro sobre la respuesta ya escrita |
| **Cada fragmento entrecomillado se verifica letra a letra** | Comparación de cadenas tras normalización declarada. Sin LLM, sin coste |
| **Abstenerse es una salida de primera clase** | Y se mide en los dos sentidos, para que callarse siempre no sea la estrategia óptima |

**Lo que esto cuesta, dicho en voz alta:** si la búsqueda falla, el sistema no «se acuerda» del
artículo — se abstiene o cita peor. La calidad del retrieval deja de ser un detalle y pasa a ser
el techo del sistema. Por eso se mide por separado antes y después de reordenar.

Y hay una capa que **no** queda garantizada, solo medida: que la *interpretación* del artículo sea
correcta. Se hace determinista todo lo que puede serlo, y el residuo se acota y se publica.

## Umbrales que la puerta exigirá

**Ninguno medido todavía**, y el único que ya tiene número —`G-HALLUC = 0`— vale poco: en la
fase 0 no hay generador. Cada meta lleva el comando exacto que la produce en
[`docs/GOALS.yaml`](docs/GOALS.yaml); una meta sin comando no es una meta.

| Meta | Qué significa | Umbral |
|---|---|---:|
| `G-HALLUC` | Referencias emitidas que no existen en el corpus | `= 0` |
| `G-QUOTE-LIT` | Fragmentos citados que están literalmente en su artículo | `= 1,00` |
| `G-RECALL30` / `G-RECALL5` | El artículo correcto entre los 30 candidatos / entre los 5 finales | `≥ 0,97` / `≥ 0,90` |
| `G-CITA-PRECISION` + `G-COBERTURA` | Precisión de cita **y** fracción respondida. **Pareja atómica** | `≥ 0,85` + `≥ 0,90` |
| `G-ABST-FP` + `G-ABST-FN` | Se calló habiendo respuesta / respondió sin haberla. **Pareja atómica** | `≤ 0,05` + `≤ 0,10` |
| `G-TTFT` | p95 hasta el primer token, con presupuesto repartido por etapa | `≤ 1500 ms` |

Las parejas son atómicas porque, medidas por separado, la forma óptima de aprobar es hacer trampa:
con solo `G-CITA-PRECISION`, abstenerse siempre da 1,00.

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
conjunto de evaluación.

## Stack

Python 3.12 · FastAPI + SSE · PostgreSQL 18 + pgvector 0.8.6 · LangGraph como máquina de estados
(sin LangChain) · Ollama en el host con backend MLX · reranker en proceso sobre MPS.
Versiones exactas con `==` y motivo en [`docs/STACK.md`](docs/STACK.md).

Dos precisiones que suelen darse por supuestas y aquí no lo son: la búsqueda léxica es
`ts_rank_cd` con configuración `spanish_unaccent`, **y no se llama BM25 porque no lo es**; y el
reranker **no pasa por Ollama**, que no tiene endpoint de rerank.

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

## Aviso

Este proyecto no es una fuente jurídica y sus respuestas no son asesoramiento legal. El carácter
oficial del texto normativo corresponde únicamente a su publicación en el BOE.

## Licencia

Código bajo [Apache 2.0](LICENSE). Los datos tienen procedencia y condiciones propias, declaradas
en [`NOTICE`](NOTICE).
