# ADR-018 · Se adopta `chunks-ddl.sql` v2: `chunk_id` sin posición y conmutación por vista

- **Fecha:** 2026-08-10
- **Fase:** 0
- **Estado:** **Aceptado** — pendiente de que Samuel aplique el contrato en `_comun/`
- **Supersede a:** —

## Contexto

`_comun/CONTRACTS/chunks-ddl.sql` v1 es el único contrato de datos entre **citebound-01** e
**indexkeeper-04**, y define literalmente
`chunk_id = sha256(f"{doc_id}:{ordinal}:{content_hash}")[:24]` — **con la posición dentro del
hash**. Insertar un párrafo al principio de un documento desplaza todos los ordinales posteriores,
cambia todos los `chunk_id` y obliga a re-embeber el documento entero. La meta insignia del 04
(`G-INCR-2 ≥ 0,90` de tokens de embedding evitados) queda **inalcanzable por construcción**: ningún
trabajo del agente la arregla, y bajarla antes de medirla es justo lo que la constitución §3 prohíbe.

Ni el agente del 01 ni el del 04 pueden tocar un contrato compartido. Se declaró como Q-012 y Q-013
aquí y como Q-002 y Q-003 allí. Samuel respondió el 2026-08-10: **A** y **A2 + B1**.

## Opciones consideradas

| Opción | Pros | Contras | Coste medido **aquí** |
|---|---|---|---|
| **A · contrato v2**, `chunk_id = blake2b(doc_id ‖ content_hash ‖ occurrence, 16)`, `ordinal` como columna | El 04 recupera su tesis. El 01 no se entera: nunca cita ni evalúa por `chunk_id` (R1) | Hay que propagar a mano a los dos repos | **3-5 h en fase 0**; si se decide tras la fase 2, reingesta completa |
| B · mantener v1 | Cero propagación | Obliga al 04 a bajar su meta antes de medirla, y deja al 01 con un contrato que solo él respeta | 0 h, coste ajeno |
| C · dos identificadores | No rompe a nadie hoy | **La peor aquí.** Duplica la superficie por la que un id de troceado puede filtrarse a un artefacto de evaluación, que es el fallo exacto que R1 y `check_no_chunk_ids.py` existen para impedir | Se paga entera en fase 3 |

Para la conmutación de índice: **B2** (`index_version.is_active`) cuesta cero aquí y es lo que ya
asumían `GOALS.yaml` y R15; **B1** (vista `chunks_active` + `index_alias`) cuesta dos tests y aporta
poder cambiar de dimensión de embedding sin parar y deshacer con un `DROP TABLE` en vez de un
`DELETE` de millones de filas.

## Decisión

**A + A2 + B1**, con una condición escrita y no negociable:

> **El informe de eval registra el destino físico resuelto** (`index_alias.index_version` +
> `index_alias.physical_table`), **nunca el alias.** Si registrase el alias, dos ejecuciones con el
> mismo alias apuntando a datos distintos producirían informes «idénticos» sobre corpus distintos y
> `G-EVAL-DET` (`propuesta_admisible: false`) dejaría de significar nada.

Y una segunda, propia de este repo: como v2 permite `norma` opcional, el DDL **de este proyecto**
—que vive en `docs/spec/`, nunca en `docs/CONTRACTS/`— añade `CHECK (norma IS NOT NULL)` más su test
de contrato. Sin eso, un chunk sin norma produce una `legal_ref` no resoluble y `G-HALLUC` mide
contra un conjunto roto.

Borrador listo para aplicar: `docs/spec/propuesta-chunks-ddl-v2.sql`.

## Consecuencias

- **Se gana** que el 04 mantenga su tesis, y que este proyecto pueda cambiar de modelo de
  embeddings (y de dimensión) sin parar el servicio.
- **Se pierde**: `ingest/chunking.py` tiene que calcular `occurrence` para desempatar contenido
  duplicado dentro de una misma norma. En texto legal **no es teórico**: hay apartados cortos
  idénticos repetidos. Añade un invariante y una propiedad Hypothesis. Y `retrieval/query_builder.py`
  deja de filtrar por `index_version` y consulta la vista, lo que obliga a un test de integración
  con `EXPLAIN` que demuestre que el plan **sigue usando el índice HNSW** y que
  `SET hnsw.ef_search` surte efecto a través de la vista — una vista mal formada lo destruye en
  silencio y `G-RECALL5` cae sin que nadie entienda por qué.
- **Intacto:** `ordinal` sigue siendo columna, así que la propiedad «la concatenación ordenada de
  los chunks de un artículo reproduce su texto exacto» no se toca. Y el golden set, `G-RECALL5`,
  `G-CITA-PRECISION` y `G-HALLUC` no se enteran del cambio, porque se anclan en `legal_ref`.
- **Bloqueante hasta que Samuel lo aplique:** las tareas `0.4` y `0.5` no arrancan. El coste de
  esperar crece con cada fase.
- **Afecta a** `docs/CONTRACTS/chunks-ddl.sql` (v1 → v2), R1, R15, `G-EVAL-DET`, `G-HALLUC`, y al
  CHANGELOG de **los dos** repos.
