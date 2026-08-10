# Citebound · tutor de normativa de circulación

> Responde preguntas sobre normativa de circulación española **citando el artículo exacto**,
> verifica literalmente el fragmento que cita, y se abstiene cuando no puede verificarlo.

**No puede citar lo que no ha recuperado. Por construcción, no por buena voluntad.**

---

> ### ⚠️ Estado: fase 0, sin código todavía
>
> Este repositorio está en su primer commit. Hoy contiene el **gobierno del proyecto**, el
> **corpus congelado** y las **decisiones de arquitectura** tomadas antes de escribir la primera
> línea. No hay `src/`, no hay `Makefile` y **ningún número de los que aparecen abajo está medido
> aún**: son los umbrales que la puerta de calidad exigirá, no resultados.
>
> Cuando haya resultados se publicarán con su `n`, su intervalo de confianza y el artefacto del
> que salen — salgan como salgan. Esa es la política declarada del proyecto.

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

Ninguno medido todavía. Cada uno lleva el comando exacto que lo produce en
[`docs/GOALS.yaml`](docs/GOALS.yaml) — una meta sin comando no es una meta.

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
| Contenido | 232 preceptos · 217 artículos · 103 encabezados |

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
