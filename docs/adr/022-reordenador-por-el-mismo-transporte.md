# ADR-022 · el reordenador es el generador, por el mismo transporte

- **Fecha:** 2026-08-17
- **Fase:** 2
- **Estado:** **Aceptado** (Q-017, decidido por Samuel)
- **Supersede a:** el punto 1 de `docs/STACK.md` §2.1, **pendiente de que él lo escriba** (Q-018)

## Contexto

Medido sobre los 216 casos positivos del golden set `v2`, sin reordenar, **sobre el índice
`v1-bge-m3-1024`**, que era el activo el día de la decisión. El índice se declara porque sin él
la tabla no se puede reproducir — es la misma exigencia que el contrato compartido pone a todo
informe de eval. Al pasar a `qwen3-embedding:0.6b` estos números mejoran y las conclusiones no
cambian: el cuello sigue estando en el orden, no en la búsqueda.

| Canal | recall@5 | recall@30 |
|---|---:|---:|
| Solo vectorial | 0,790 | 0,941 |
| Solo léxico | 0,365 | 0,804 |
| Híbrido | 0,727 | 0,954 |

El artículo correcto **ya está** entre los 30 recuperados en el 95 % de los casos, y en el top-5
solo en el 73 %. El problema no es buscar: es **ordenar**. Y ninguna combinación de los dos
canales llega a 0,90 en el top-5 sin reordenar — el vectorial solo, que es el mejor ahí, se
queda en 0,790.

La pregunta no era si hacía falta reordenar, sino **cómo se sirve** ese modelo. Samuel puso la
restricción al preguntar por qué el reranker no pasaba por Ollama: *«me gustaría que todo modelo
que se use pase por Ollama o proveedor compatible»*. Y el obstáculo es real: **Ollama no tiene
endpoint de rerank** — `/api/rerank` y `/v1/rerank` devuelven 404, comprobado contra la 0.32.14.

## Opciones consideradas

| Opción | Pros | Contras |
|---|---|---|
| A · cross-encoder en proceso (`Qwen3-Reranker-0.6B` + `sentence-transformers`) | Lo más preciso y lo más rápido; sin salto de red en el presupuesto de `G-TTFT`. **No exige Mac**: MPS es el backend aquí, pero el mismo código corre sobre CUDA o CPU | Un **segundo camino** para servir modelos, ~2 GB de dependencias, y una descarga más en `G-COLD-CACHE` |
| **B · el generador como reordenador**, por `/v1/chat/completions` | Un solo transporte, cero dependencias nuevas, `G-COLD-CACHE` intacto. Y es **instruction-aware por definición**: se le puede decir qué significa «relevante» aquí | Más lento; su calidad hay que medirla, no está dada |
| C · sin reordenador, proponiendo bajar `G-RECALL5` | — | **Rechazada.** Bajar un umbral para que pase lo que hay es lo que `CLAUDE.md` prohíbe sin diagnóstico. El diagnóstico está hecho y dice que tiene arreglo |

## Decisión

**B.** El reordenador es el propio generador. La resolución del orden la hace código: el modelo
devuelve números, nunca referencias.

**Lo que decide de verdad es la instrucción, no el modelo.** «Relevante» aquí no es «parecido»:
es el artículo que **tipifica** la conducta, no el que la menciona de pasada. Esa distinción es
la tesis del proyecto —el art. 34 habla de cómputo de carriles y el 35 de separación lateral, y
elegir mal es exactamente el error que el golden set existe para medir— y un modelo instruido
puede recibirla, mientras que una distancia coseno no.

## Consecuencias

- **`tope=30`, no 10.** Con 10, el 17 % de los casos tenía el artículo correcto en los puestos
  11-30 y el reordenador **ni los miraba**: el techo era 0,785. Un tope mal puesto no da un
  error, da un número mediocre cuyo diagnóstico apunta al modelo o al prompt, que es donde no
  está el problema.
- **Nunca pierde ni inventa un candidato.** Los números fuera de rango se ignoran y los que el
  modelo no nombra van detrás en su orden original. Tiene su test: si el reordenador perdiera
  documentos, el recall bajaría por su culpa y el diagnóstico apuntaría al índice.
- **Caché de juicios versionada en el repo**, con la pregunta, los candidatos **en su orden**, el
  modelo y la versión del prompt en la clave. La primera corrida paga el modelo; las siguientes
  son gratis y deterministas — que es lo que `G-EVAL-DET` exigirá en la fase 4. Un juicio emitido
  con otro prompt es un juicio sobre otra pregunta, y por eso `PROMPT_VERSION` entra en la clave.
- **`G-TTFT` queda por confirmar.** El reordenador entra en su presupuesto, que tiene 210 ms de
  holgura, y eso se mide en la fase 3 con `make bench`. Si no cabe, la salida no es volver a A
  sino sacar el reordenador del camino interactivo.
- **Coste medido de la decisión:** ~20 minutos la primera corrida de `make eval-retrieval` contra
  ~4 s sin reordenador. Por eso la caché no es una optimización: es lo que mantiene la meta
  dentro del gate.
- **`docs/STACK.md` §2.1 dice hoy lo contrario** y es de solo lectura para el agente. Va como
  **Q-018**. Mientras no se aplique, el repositorio afirma dos cosas distintas y `STACK.md` es la
  que manda por regla escrita — de ahí que esto quede anotado aquí y en `JOURNAL.md` en vez de
  resolverse por mi cuenta.
