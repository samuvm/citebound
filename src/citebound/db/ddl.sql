-- =============================================================================
-- DDL PROPIO DE citebound-01  ·  se aplica DESPUES del contrato compartido
-- =============================================================================
--
-- Esto NO es el esquema. El esquema es `docs/CONTRACTS/chunks-ddl.sql` v2, que es
-- copia literal de `_comun/` y no se toca. Aqui van SOLO las condiciones propias de
-- este proyecto, y por eso el fichero es corto: cuanto mas corto, menos superficie
-- por la que el esquema puede divergir del que construye `indexkeeper-04`.
--
-- `db.esquema_sql()` concatena contrato + esto, en ese orden. Que la divergencia sea
-- imposible por construccion es mejor que un test que la detecte tarde.
--
-- Condicion pactada en Q-013 (a) = A2, escrita en el ADR-018.
-- =============================================================================

-- El contrato v2 admite `norma` NULL para que `indexkeeper-04` pueda usarlo con un
-- corpus que no sea normativo. Aqui NO se admite: `G-HALLUC` tiene umbral `== 0` y
-- `propuesta_admisible: false`, y se define como pertenencia de la `legal_ref` al
-- conjunto de refs del indice. Un chunk sin norma produce una `legal_ref` que cae a
-- `ref` y no se puede resolver contra el corpus, asi que la meta estaria midiendo
-- contra un conjunto roto y seguiria diciendo 0.
ALTER TABLE chunk_v1
    ADD CONSTRAINT chunk_v1_norma_obligatoria CHECK (norma IS NOT NULL);

-- Mismo motivo, un paso mas: una `legal_ref` vacia es tan inutil como una nula.
ALTER TABLE chunk_v1
    ADD CONSTRAINT chunk_v1_legal_ref_no_vacia CHECK (length(legal_ref) > 0);

-- El troceado de la fase 0 nunca emite un chunk sin texto (`ingest/chunking.py` lo
-- rechaza en voz alta). Se declara tambien aqui porque una fila vacia que entrase por
-- otra via se embeberia a ruido y contaminaria el indice con una referencia que jamas
-- puede ser una respuesta correcta.
ALTER TABLE chunk_v1
    ADD CONSTRAINT chunk_v1_content_no_vacio CHECK (length(btrim(content)) > 0);
