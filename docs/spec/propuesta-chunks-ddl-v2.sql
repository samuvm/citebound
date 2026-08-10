-- =============================================================================
-- BORRADOR · chunks-ddl.sql  VERSION 2   ·   proyectos 01 (citebound) y 04 (indexkeeper)
-- =============================================================================
--
-- ESTO NO ES EL CONTRATO. Es el borrador que implementa las respuestas de Samuel
-- del 2026-08-10 (Q-012 = A · Q-013 = A2 + B1, espejo de Q-002 y Q-003 del 04),
-- listo para que SAMUEL lo revise y lo aplique. Ningun agente toca `_comun/`.
--
-- PASOS QUE TE TOCAN A TI, EN ESTE ORDEN:
--   1. Que el agente de indexkeeper-04 revise este fichero. El contrato es de los dos.
--   2. Copiar el resultado acordado a  _comun/CONTRACTS/chunks-ddl.sql
--   3. Copiarlo tambien a  citebound-01/docs/CONTRACTS/chunks-ddl.sql
--                     y a  indexkeeper-04/docs/CONTRACTS/chunks-ddl.sql
--   4. Anotar el cambio en el CHANGELOG de LOS DOS repos
-- Responder en un solo buzon deja los dos repos con contratos distintos, que es el
-- fallo exacto que este contrato existe para evitar.
--
-- Version del contrato: 2      (v1: 2026-08-08 · v2: 2026-08-10)
-- =============================================================================
--
-- QUE CAMBIA RESPECTO A v1, Y POR QUE
--
--  1. chunk_id SIN POSICION.  v1: sha256(f"{doc_id}:{ordinal}:{content_hash}")[:24]
--     Con el ordinal dentro del hash, insertar un parrafo al principio de un
--     documento desplaza todos los ordinales y cambia todos los chunk_id, lo que
--     obliga a re-embeber el documento entero. G-INCR-2 del 04 (>= 0,90 de tokens
--     evitados) quedaba inalcanzable POR CONSTRUCCION.
--     v2: blake2b(doc_id || content_hash || occurrence, digest_size=16).
--     El 01 no pierde nada: nunca cita ni evalua por chunk_id (RULES R1).
--
--  2. NUEVA COLUMNA `occurrence`.  Al sacar la posicion del hash hace falta algo
--     que desempate contenido IDENTICO dentro del MISMO documento. En texto legal
--     no es teorico: hay apartados cortos repetidos literalmente.
--
--  3. `ordinal` SIGUE SIENDO COLUMNA, y su UNIQUE pasa a DEFERRABLE, para que una
--     reordenacion masiva quepa en una transaccion. Que siga existiendo es lo que
--     mantiene intacta la propiedad Hypothesis del 01: "la concatenacion ordenada
--     de los chunks de un articulo reproduce exactamente su texto".
--
--  4. CAMPOS LEGALES OPCIONALES (Q-013 a = A2).  El 04 no sabe aun si su corpus
--     sera normativo. Se generaliza con `ref` obligatorio y norma/articulo/apartado
--     opcionales. CONDICION DEL 01: su DDL propio anade CHECK (norma IS NOT NULL);
--     sin eso, un chunk sin norma da una legal_ref no resoluble y G-HALLUC
--     (umbral == 0, propuesta_admisible: false) mide contra un conjunto roto.
--
--  5. CONMUTACION POR VISTA (Q-013 b = B1).  Desaparece index_version.is_active.
--     Entra la tabla index_alias y la vista chunks_active. Permite que v1 y v2 sean
--     TABLAS distintas -> se puede migrar de dimension de embedding sin parar, y el
--     rollback es DROP TABLE en vez de DELETE de millones de filas.
--     CONDICION DEL 01, no negociable: el informe de eval registra el DESTINO FISICO
--     RESUELTO (index_alias.index_version + index_alias.physical_table), NUNCA el
--     alias. Con el alias, dos ejecuciones sobre datos distintos producirian
--     informes "identicos" y G-EVAL-DET dejaria de significar nada.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector 0.8.6
CREATE EXTENSION IF NOT EXISTS unaccent;

-- -----------------------------------------------------------------------------
-- Busqueda lexica en espanol, sin acentos.
-- OJO: esto es ts_rank_cd, NO es BM25. Ver _comun/STACK.md seccion 3.
-- -----------------------------------------------------------------------------
CREATE TEXT SEARCH CONFIGURATION spanish_unaccent ( COPY = spanish );
ALTER TEXT SEARCH CONFIGURATION spanish_unaccent
  ALTER MAPPING FOR hword, hword_part, word
  WITH unaccent, spanish_stem;

-- -----------------------------------------------------------------------------
-- Un indice = una fila. Ya NO lleva is_active: el alias vive en index_alias.
-- -----------------------------------------------------------------------------
CREATE TABLE index_version (
    id              TEXT PRIMARY KEY,           -- p.ej. 'v2-qwen3emb-1024'
    embedding_model TEXT        NOT NULL,
    dim             INT         NOT NULL,
    distance        TEXT        NOT NULL
                    CHECK (distance = 'cosine'),
    chunker_id      TEXT        NOT NULL,
    corpus_snapshot TEXT        NOT NULL,       -- fecha de consolidacion del corpus
    physical_table  TEXT        NOT NULL,       -- v2: 'chunk_v1', 'chunk_v2', ...
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- v2 · El alias. Una fila por nombre logico. La conmutacion es DDL transaccional:
--   BEGIN;
--     UPDATE index_alias SET index_version='v2-...', physical_table='chunk_v2',
--            switched_at=now() WHERE alias='active';
--     CREATE OR REPLACE VIEW chunks_active AS SELECT * FROM chunk_v2;
--   COMMIT;
-- Rollback = repetir apuntando a la tabla anterior. No se borra ninguna fila.
-- -----------------------------------------------------------------------------
CREATE TABLE index_alias (
    alias           TEXT PRIMARY KEY,           -- 'active' es el unico obligatorio
    index_version   TEXT        NOT NULL REFERENCES index_version(id),
    physical_table  TEXT        NOT NULL,
    switched_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- Chunks. dim = 1024 en el contrato. Cada index_version materializa SU tabla.
-- Esta es la plantilla; chunk_v1, chunk_v2... la copian.
-- -----------------------------------------------------------------------------
CREATE TABLE chunk_v1 (
    -- v2: blake2b(doc_id || content_hash || occurrence, digest_size=16) -> 32 hex
    chunk_id        TEXT        PRIMARY KEY,
    index_version   TEXT        NOT NULL REFERENCES index_version(id),

    content         TEXT        NOT NULL,
    content_hash    TEXT        NOT NULL,       -- sha256 del content normalizado

    embedding       vector(1024) NOT NULL,

    content_tsv     tsvector    GENERATED ALWAYS AS (
                        to_tsvector('spanish_unaccent', content)
                    ) STORED,

    -- v2 · Identificador estable GENERICO. Obligatorio para todos.
    ref             TEXT        NOT NULL,

    -- v2 · Campos legales OPCIONALES en el contrato compartido.
    -- El 01 los exige en su propio DDL con CHECK (norma IS NOT NULL).
    norma           TEXT,                       -- 'RD-1428/2003'
    articulo        TEXT,                       -- '3'
    apartado        TEXT,                       -- '1', '2.a'

    -- Nunca NULL: cae a `ref` cuando el corpus no es normativo.
    legal_ref       TEXT        GENERATED ALWAYS AS (
                        COALESCE(
                          norma
                          || COALESCE('#art' || articulo, '')
                          || COALESCE('.' || apartado, ''),
                          ref
                        )
                    ) STORED,

    titulo          TEXT,
    capitulo        TEXT,
    seccion         TEXT,
    materia         TEXT,

    doc_id          TEXT        NOT NULL,
    ordinal         INT         NOT NULL,       -- v2: columna, YA NO va en el hash
    occurrence      INT         NOT NULL DEFAULT 0,   -- v2: desempata contenido repetido

    metadata        JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- v2: DEFERRABLE para que una reordenacion masiva quepa en una transaccion
    CONSTRAINT chunk_v1_doc_ordinal
        UNIQUE (index_version, doc_id, ordinal) DEFERRABLE INITIALLY DEFERRED,
    -- v2: el par (contenido, ocurrencia) es unico dentro de un documento
    CONSTRAINT chunk_v1_doc_content_occ
        UNIQUE (index_version, doc_id, content_hash, occurrence)
);

CREATE VIEW chunks_active AS SELECT * FROM chunk_v1;

-- -----------------------------------------------------------------------------
-- Indices. Los hiperparametros son parte del contrato: sin ellos, dos proyectos
-- miden recall sobre estructuras distintas y los numeros no comparan.
-- Se crean sobre la TABLA FISICA, nunca sobre la vista.
-- -----------------------------------------------------------------------------
CREATE INDEX chunk_v1_embedding_hnsw ON chunk_v1
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
-- Consulta: SET hnsw.ef_search = 100;   -- declarado, no por defecto
-- v2 · OBLIGATORIO para el 01: un test de integracion con EXPLAIN que demuestre
--      que la consulta a traves de chunks_active SIGUE usando este indice y que
--      SET hnsw.ef_search surte efecto. Una vista mal formada lo destruye en
--      silencio y G-RECALL5 cae sin que nadie entienda por que.

CREATE INDEX chunk_v1_tsv_gin    ON chunk_v1 USING gin (content_tsv);
CREATE INDEX chunk_v1_legal_ref  ON chunk_v1 (legal_ref);
CREATE INDEX chunk_v1_ref        ON chunk_v1 (ref);
CREATE INDEX chunk_v1_materia    ON chunk_v1 (materia);
CREATE INDEX chunk_v1_index_ver  ON chunk_v1 (index_version);

-- -----------------------------------------------------------------------------
-- Estado por documento. Sin cambios respecto a v1.
-- Invariante del 04: para todo documento existe EXACTAMENTE un registro de estado.
-- -----------------------------------------------------------------------------
CREATE TABLE document_state (
    doc_id          TEXT        PRIMARY KEY,
    source_uri      TEXT        NOT NULL,
    doc_hash        TEXT        NOT NULL,       -- hash del CONTENIDO, no de metadatos
    state           TEXT        NOT NULL
                    CHECK (state IN ('indexed', 'quarantined', 'pending')),
    quarantine_reason TEXT,
    n_chunks        INT,
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (state <> 'quarantined' OR quarantine_reason IS NOT NULL)
);

-- =============================================================================
-- CONTRATO DE IDENTIFICADORES  ·  v2
-- =============================================================================
--
--   doc_id       = sha256(source_uri)[:16]
--   content_hash = sha256(normalize(content))      normalize = NFC + colapso de
--                                                  espacios + strip
--   occurrence   = indice 0-based de esta aparicion de content_hash dentro del
--                  documento, en orden de lectura
--   chunk_id     = blake2b(doc_id || content_hash || str(occurrence),
--                          digest_size=16).hexdigest()          -> 32 hex
--
-- Funcion pura de (documento, contenido, ocurrencia). SIN posicion, sin
-- timestamps, sin UUID aleatorio, sin contadores de proceso.
--
-- Propiedad que esto compra al 04: insertar o borrar un parrafo cambia SOLO los
-- chunk_id de los parrafos cuyo contenido cambio. Los demas se reutilizan y no se
-- vuelven a embeber. Es lo que hace medible G-INCR-2.
--
-- Propiedad que esto NO rompe en el 01: `ordinal` sigue existiendo como columna,
-- asi que "la concatenacion ordenada de los chunks de un articulo reproduce
-- exactamente su texto" sigue siendo comprobable.
--
-- NOMENCLATURA: la columna es `content_hash`, no `content_sha256`. En el 04,
-- `raw_sha256` es otra cosa (el hash de los bytes crudos del fichero) y existe.
--
-- =============================================================================
-- SOBRE LA IDEMPOTENCIA "BYTE A BYTE"   (sin cambios respecto a v1)
-- =============================================================================
--
-- "Dos ejecuciones -> indice identico byte a byte" es IMPOSIBLE: los bytes fisicos
-- de una tabla Postgres incluyen cabeceras de tupla, xmin y orden fisico; y las
-- salidas de un modelo de embeddings no son bit-reproducibles cuando cambia la
-- composicion del lote.
--
-- Invariante correcto:
--   A) IDENTIDAD Y COBERTURA (exacto, siempre):
--        sha256 del conjunto ORDENADO de
--        (chunk_id, content_hash, embedding_model, dim, index_version)
--   B) IGUALDAD DE VECTORES (bajo condiciones declaradas):
--        solo con tamano de lote y orden fijados, tolerancia L2 < 1e-5.
--
-- =============================================================================
-- v2 · PROCEDENCIA EN EL INFORME DE EVAL   (condicion del 01, no negociable)
-- =============================================================================
--
-- Todo informe registra el DESTINO FISICO RESUELTO, nunca el alias:
--     index_alias.alias           -> 'active'          (informativo)
--     index_alias.index_version   -> 'v2-qwen3emb-1024'  (OBLIGATORIO)
--     index_alias.physical_table  -> 'chunk_v2'          (OBLIGATORIO)
--
-- Sin esto, dos ejecuciones con el mismo alias apuntando a datos distintos darian
-- informes normalizados identicos sobre corpus distintos, y G-EVAL-DET
-- (propuesta_admisible: false) dejaria de significar nada.
-- =============================================================================
