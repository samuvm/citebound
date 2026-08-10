# ADR-NNN · <título en una línea, en presente>

- **Fecha:** AAAA-MM-DD
- **Fase:** N
- **Estado:** Propuesto | **Aceptado** | Rechazado | Sustituido por ADR-MMM
- **Supersede a:** — (o ADR-MMM)

> **Reglas de esta carpeta.** Un ADR es un fichero **nuevo**: modificar uno existente está
> prohibido, y corregir una decisión se hace escribiendo otro ADR que lo supersede (y editando
> **solo** la línea `Estado:` del viejo para apuntar al nuevo). Tope orientativo: 40 líneas.
> Un ADR se escribe cuando la decisión es **no obvia**: si es reversible y trivial, va a
> `JOURNAL.md` y no aquí. Español, ~40 líneas, sin relleno.

## Contexto

Qué problema concreto obliga a decidir ahora, con el dato que lo provoca (un número medido, una
limitación de una versión fijada, un requisito de un contrato de `docs/CONTRACTS/`). Sin dato, no
hay ADR: hay opinión.

## Opciones consideradas

| Opción | Pros | Contras | Coste medido |
|---|---|---|---|
| A · … | | | |
| B · … | | | |
| C · no hacer nada | | | 0 |

**Las opciones descartadas se escriben con su coste real, no supuesto.** Es la parte del ADR que
se lee en una entrevista: un ADR sin alternativas descartadas es una justificación a posteriori.

## Decisión

Qué se elige y **por qué esta y no las otras**, en dos o tres frases. Si la elección depende de un
número, el número va aquí con su comando y su artefacto (`evals/reports/…`).

## Consecuencias

- Qué se gana.
- **Qué se pierde** (siempre hay algo; si no lo encuentras, no has entendido la alternativa).
- Qué se vuelve más difícil de cambiar después, y cuál es la salida si hay que revertir.
- Qué invariante de `docs/RULES.md`, meta de `docs/GOALS.yaml` o contrato de `docs/CONTRACTS/`
  queda afectado.

---

## ADR pendientes de escribir en este proyecto

Lista viva salida de la investigación. Cada uno se escribe **en la fase que lo provoca**, no al
final. El número definitivo lo asigna el agente por orden de escritura; el orden de abajo es el
orden esperado.

| # esperado | Título | Fase | Qué obliga a decidir |
|---|---|:-:|---|
| 001 | Fuente del corpus: XML consolidado del BOE, no PDF ni Docling | 0 | El BOE publica jerarquía exacta y sin pérdida; sacarla de un PDF mete error evitable en la métrica que declaras con tolerancia cero. Se escribe **con los datos reales del sondeo**: endpoint literal, fecha de consolidación observada, nº de artículos, condiciones de reutilización |
| 002 | Python 3.12 porque MWAA no ofrece más | 0 | El motivo correcto, no "requisito de la oferta". Existen 3.13 y 3.14 |
| 003 | La unidad de verdad es `legal_ref`, nunca `chunk_id` | 0 | Es la tesis nº 1 del proyecto y la que hace que el golden set sobreviva a la fase 2 |
| 004 | Contrato SSE: `sources` antes que `token`, y dos latencias publicadas | 0 | Streaming y "verificar antes de responder" son incompatibles; hay que resolverlo antes de diseñar la API |
| 005 | Idempotencia del corpus: identidad y cobertura, no bytes | 0 | El enunciado ingenuo ("índice idéntico byte a byte") es imposible y hace fallar el test más importante por razones ajenas a la idempotencia. Ver `docs/CONTRACTS/chunks-ddl.sql` |
| 006 | `ts_rank_cd` frente a BM25 real (`pg_textsearch`): el spike y su número | 2 | Sale el ADR se adopte o no. "Probamos BM25 real, mejoró/no mejoró X puntos, decidimos Y" es señal; poner la etiqueta sin medirlo es ruido negativo |
| 007 | Pre-filtro con índice parcial frente a post-filtro por materia | 2 | Cambia el plan de ejecución de PG18 y el presupuesto de latencia de la etapa de búsqueda |
| 008 | pgvector frente a un motor vectorial dedicado, con la cifra real de vectores | 2 | Es la pregunta que hará cualquiera que mire el repo; se responde con el nº de vectores del corpus, no con una opinión |
| 009 | Reranker elegido, con la tabla nDCG@5 / p95 y la instrucción de dominio | 2 | `Qwen3-Reranker-0.6B` es *instruction-aware*; el retador es `bge-reranker-v2-m3`. Y por qué **no** pasa por Ollama |
| 010 | LangGraph solo como máquina de estados; `langchain*` fuera | 3 | PydanticAI 2.27 es el rival serio en 2026 y encaja mejor con `mypy --strict`; para un ciclo con reintento y abstención acotados gana LangGraph. Se escribe el descarte |
| 011 | Cita cerrada `[[REF:n]]` frente a extraer el span con el reranker | 3 | La alternativa es más segura pero pierde la señal de faithfulness que da forzar al modelo a señalar el texto. Va con el *caveat* honesto del README |
| 012 | Coste de calidad de la decodificación restringida (JSON Schema en `format`) | 3 | Puede degradar la redacción: se mide A/B sobre el golden set, no se supone |
| 013 | Ragas fuera del gate; DeepEval como métrica de nombre y suite propia como gate | 4 | Ragas congelado desde febrero de 2026. Es el hallazgo más grave de la revisión |
| 014 | Juez de familia distinta al generador, y qué se hace si κ < 0,60 | 4 | Un modelo juzgando su propia salida infla faithfulness sistemáticamente |
| 015 | Evals deterministas desde caché versionada, y qué se vuelve a grabar | 4 | Resuelve la contradicción "sin claves de API" ↔ "juez LLM" ↔ "un desconocido reproduce los números" |
| 016 | Modelo OTel interno propio con capa de traducción al esquema pineado | 5 | Nada de `gen_ai.*` es estable; una ruptura debe ser un cambio en un fichero, no una migración |
| 017 | Alcance de la fase 6 (BKT): dominio puro, timebox, `/session/*` fuera | 6 | Solo si Q-010 se responde A. Si se responde C, el ADR es el de "fuera de alcance y por qué" |
| 018 | Versión adoptada de `chunks-ddl.sql` (v1 o v2) y mecanismo de conmutación de índice | 0 | Contrato compartido con `indexkeeper-04`. Se escribe cuando Samuel responda **Q-012 y Q-013**, con lo que cambia aquí: `chunk_id`, `occurrence`, el `CHECK` de `norma` y qué registra el informe como índice activo |
