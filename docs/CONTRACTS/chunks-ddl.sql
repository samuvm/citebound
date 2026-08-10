-- =============================================================================
-- CONTRATO · tabla de chunks   ·   proyectos 01 (citebound) y 04 (indexkeeper)
-- =============================================================================
--
-- El mapa de conjunto declara este contrato como "id, contenido, embedding,
-- metadata, version_indice. Nada mas". Eso esta infra-especificado hasta ser
-- inutil: falta la dimension del vector, la metrica de distancia, los
-- hiperparametros del indice, el esquema de metadata, la semantica de
-- version_indice, y sobre todo la columna de busqueda lexica que el 01
-- necesita y el contrato omite.
--
-- Sin esto, el 04 construye una tabla que el 01 no puede consultar, y el
-- intercambio de indice -- que es la tesis del 04 -- no funciona.
--
-- Este fichero se COPIA a ambos proyectos. No se importa. Cambiarlo es un
-- evento consciente que se propaga a mano y se anota en el CHANGELOG de los
-- dos repos afectados.
--
-- Version del contrato: 2
--   v1 · 2026-08-08 · version inicial
--   v2 · 2026-08-10 · decidida por Samuel en los dos buzones a la vez
--                     (citebound-01 Q-012 = A, Q-013 = A2 + B1
--                      indexkeeper-04 Q-002 = A, Q-003 = A2 + B1)
--                     ADR: citebound-01/docs/adr/018-chunks-ddl-v2-y-conmutacion.md
-- =============================================================================
--
-- QUE CAMBIA EN v2, Y POR QUE
--
--  1. chunk_id SIN POSICION.
--     v1: sha256(f"{doc_id}:{ordinal}:{content_hash}")[:24]
--     Con el ordinal dentro del hash, insertar un parrafo al principio de un
--     documento desplaza todos los ordinales posteriores, cambia todos los
--     chunk_id y obliga a re-embeber el documento entero aunque el 95 % del
--     texto sea identico. G-INCR-2 del 04 (>= 0,90 de tokens de embedding
--     evitados) quedaba INALCANZABLE POR CONSTRUCCION: ninguna cantidad de
--     trabajo lo arregla.
--     v2: blake2b(doc_id || content_hash || occurrence, digest_size=16).
--     El 01 no pierde nada: nunca cita ni evalua por chunk_id. Su ancla es
--     legal_ref (citebound-01/docs/RULES.md R1, retrieval-metrics.md §1).
--
--  2. NUEVA COLUMNA `occurrence`.
--     Al sacar la posicion del hash hace falta algo que desempate contenido
--     IDENTICO dentro del MISMO documento. En texto legal no es teorico: hay
--     apartados cortos repetidos literalmente.
--
--  3. `ordinal` SIGUE SIENDO COLUMNA, con su UNIQUE en DEFERRABLE.
--     Que siga existiendo es lo que mantiene intacta la propiedad Hypothesis
--     del 01: "la concatenacion ordenada de los chunks de un articulo
--     reproduce exactamente su texto". DEFERRABLE permite que una
--     reordenacion masiva quepa en una sola transaccion.
--
--  4. CAMPOS LEGALES OPCIONALES.
--     El 04 no sabe aun si su corpus sera normativo. Se generaliza con `ref`
--     obligatorio y norma/articulo/apartado opcionales.
--     CONDICION DEL 01: su DDL propio anade CHECK (norma IS NOT NULL) con su
--     test de contrato. Sin eso, un chunk sin norma da una legal_ref no
--     resoluble y G-HALLUC (umbral == 0, propuesta_admisible: false) mide
--     contra un conjunto roto.
--
--  5. CONMUTACION POR VISTA.
--     Desaparece index_version.is_active y su indice unico parcial. Entran la
--     tabla index_alias y la vista chunks_active. Permite que v1 y v2 sean
--     TABLAS distintas, o sea migrar de dimension de embedding sin parar el
--     servicio, y que el rollback sea DROP TABLE en vez de DELETE de millones
--     de filas.
--     CONDICION DEL 01, no negociable: el informe de eval registra el DESTINO
--     FISICO RESUELTO (index_alias.index_version + index_alias.physical_table),
--     NUNCA el alias. Ver la seccion final de este fichero.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector 0.8.6
CREATE EXTENSION IF NOT EXISTS unaccent;

-- -----------------------------------------------------------------------------
-- Configuracion de busqueda lexica en espanol, sin acentos.
-- OJO: esto es ts_rank_cd, NO es BM25. Ver _comun/STACK.md seccion 3.
-- -----------------------------------------------------------------------------
CREATE TEXT SEARCH CONFIGURATION spanish_unaccent ( COPY = spanish );
ALTER TEXT SEARCH CONFIGURATION spanish_unaccent
  ALTER MAPPING FOR hword, hword_part, word
  WITH unaccent, spanish_stem;

-- -----------------------------------------------------------------------------
-- Un indice = una fila. v2: ya NO lleva is_active; el alias vive en index_alias.
-- -----------------------------------------------------------------------------
CREATE TABLE index_version (
    id              TEXT PRIMARY KEY,           -- p.ej. 'v2-qwen3emb-1024'
    embedding_model TEXT        NOT NULL,       -- id exacto del modelo
    dim             INT         NOT NULL,       -- dimension real de los vectores
    distance        TEXT        NOT NULL        -- 'cosine' fijo en el contrato
                    CHECK (distance = 'cosine'),
    chunker_id      TEXT        NOT NULL,       -- estrategia de troceado usada
    corpus_snapshot TEXT        NOT NULL,       -- fecha de consolidacion del corpus
    physical_table  TEXT        NOT NULL,       -- v2: 'chunk_v1', 'chunk_v2', ...
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- v2 · El alias. Una fila por nombre logico; 'active' es el unico obligatorio.
-- La conmutacion es DDL transaccional y medible con lectores en vuelo:
--
--   BEGIN;
--     UPDATE index_alias
--        SET index_version = 'v2-...', physical_table = 'chunk_v2',
--            switched_at = now()
--      WHERE alias = 'active';
--     CREATE OR REPLACE VIEW chunks_active AS SELECT * FROM chunk_v2;
--   COMMIT;
--
-- Rollback = repetir apuntando a la tabla anterior. No se borra ninguna fila.
-- -----------------------------------------------------------------------------
CREATE TABLE index_alias (
    alias           TEXT PRIMARY KEY,
    index_version   TEXT        NOT NULL REFERENCES index_version(id),
    physical_table  TEXT        NOT NULL,
    switched_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- Chunks. dim = 1024 en el contrato.
--
-- Postgres no permite dimension variable en una columna vector, asi que los
-- vectores de dimensiones distintas viven en TABLAS distintas (chunk_v1,
-- chunk_v2, ...). Esta es la plantilla; cada index_version materializa la suya
-- y el alias decide cual esta activa.
-- -----------------------------------------------------------------------------
CREATE TABLE chunk_v1 (
    -- v2: blake2b(doc_id || content_hash || occurrence, digest_size=16) -> 32 hex
    chunk_id        TEXT        PRIMARY KEY,
    index_version   TEXT        NOT NULL REFERENCES index_version(id),

    content         TEXT        NOT NULL,
    content_hash    TEXT        NOT NULL,       -- sha256 del content normalizado

    embedding       vector(1024) NOT NULL,

    -- Busqueda lexica. Generada, nunca escrita a mano.
    content_tsv     tsvector    GENERATED ALWAYS AS (
                        to_tsvector('spanish_unaccent', content)
                    ) STORED,

    -- v2 · Identificador estable GENERICO de documento/seccion. Obligatorio
    -- para todos. Es lo que permite que el 04 use este contrato aunque su
    -- corpus no sea normativo.
    ref             TEXT        NOT NULL,

    -- v2 · Campos legales OPCIONALES en el contrato compartido.
    -- El 01 los exige en su propio DDL con CHECK (norma IS NOT NULL).
    norma           TEXT,                       -- 'RD-1428/2003'
    articulo        TEXT,                       -- '3'
    apartado        TEXT,                       -- '1', '2.a'

    -- Identificador legal ESTABLE. Es lo que cita el sistema y contra lo que se
    -- evalua. NUNCA se evalua contra chunk_id: ver retrieval-metrics.md.
    -- v2: nunca NULL, cae a `ref` cuando el corpus no es normativo.
    legal_ref       TEXT        GENERATED ALWAYS AS (
                        COALESCE(
                          norma
                          || COALESCE('#art' || articulo, '')
                          || COALESCE('.' || apartado, ''),
                          ref
                        )
                    ) STORED,

    -- Jerarquia estructural, para filtrado por materia.
    titulo          TEXT,
    capitulo        TEXT,
    seccion         TEXT,
    materia         TEXT,

    -- Posicion dentro del documento fuente.
    -- v2: sigue siendo columna, pero YA NO forma parte del chunk_id.
    doc_id          TEXT        NOT NULL,
    ordinal         INT         NOT NULL,
    occurrence      INT         NOT NULL DEFAULT 0,   -- v2: desempata contenido repetido

    metadata        JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- v2: DEFERRABLE para que una reordenacion masiva quepa en una transaccion
    CONSTRAINT chunk_v1_doc_ordinal
        UNIQUE (index_version, doc_id, ordinal) DEFERRABLE INITIALLY DEFERRED,
    -- v2: el par (contenido, ocurrencia) es unico dentro de un documento.
    -- Es el invariante que hace determinista el calculo de occurrence.
    CONSTRAINT chunk_v1_doc_content_occ
        UNIQUE (index_version, doc_id, content_hash, occurrence)
);

CREATE VIEW chunks_active AS SELECT * FROM chunk_v1;

-- -----------------------------------------------------------------------------
-- Indices. Los hiperparametros son parte del contrato: sin ellos, dos
-- proyectos miden recall sobre estructuras distintas y los numeros no comparan.
-- Se crean sobre la TABLA FISICA, nunca sobre la vista.
-- -----------------------------------------------------------------------------
CREATE INDEX chunk_v1_embedding_hnsw ON chunk_v1
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
-- Consulta: SET hnsw.ef_search = 100;   -- declarado, no por defecto
--
-- v2 · OBLIGATORIO para quien consulte a traves de chunks_active: un test de
-- integracion con EXPLAIN que demuestre que el plan SIGUE usando este indice y
-- que SET hnsw.ef_search surte efecto a traves de la vista. Una vista mal
-- formada lo destruye en silencio y el recall cae sin causa aparente.

CREATE INDEX chunk_v1_tsv_gin    ON chunk_v1 USING gin (content_tsv);
CREATE INDEX chunk_v1_legal_ref  ON chunk_v1 (legal_ref);
CREATE INDEX chunk_v1_ref        ON chunk_v1 (ref);
CREATE INDEX chunk_v1_materia    ON chunk_v1 (materia);
CREATE INDEX chunk_v1_index_ver  ON chunk_v1 (index_version);

-- -----------------------------------------------------------------------------
-- Estado por documento. Sin cambios en v2. El invariante que gobierna el 04:
-- para todo documento de la fuente existe EXACTAMENTE un registro de estado.
-- Nunca ninguno, nunca dos.
-- -----------------------------------------------------------------------------
CREATE TABLE document_state (
    doc_id          TEXT        PRIMARY KEY,
    source_uri      TEXT        NOT NULL,
    doc_hash        TEXT        NOT NULL,       -- hash del CONTENIDO, no de los metadatos
    state           TEXT        NOT NULL
                    CHECK (state IN ('indexed', 'quarantined', 'pending')),
    quarantine_reason TEXT,                     -- obligatorio si state='quarantined'
    n_chunks        INT,
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (state <> 'quarantined' OR quarantine_reason IS NOT NULL)
);

-- =============================================================================
-- CONTRATO DE IDENTIFICADORES  ·  v2   (critico para la idempotencia del 04)
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
-- timestamps, sin UUID aleatorio, sin contadores de proceso. Es lo que hace que
-- dos ejecuciones produzcan la misma secuencia de IDs.
--
-- Lo que v2 compra al 04: insertar o borrar un parrafo cambia SOLO los chunk_id
-- de los parrafos cuyo contenido cambio. Los demas se reutilizan y no se vuelven
-- a embeber. Es lo que hace medible G-INCR-2.
--
-- Lo que v2 NO rompe en el 01: `ordinal` sigue siendo columna, asi que "la
-- concatenacion ordenada de los chunks de un articulo reproduce exactamente su
-- texto" sigue siendo comprobable.
--
-- doc_hash NO incluye metadatos irrelevantes (fecha de descarga, cabeceras
-- HTTP, mtime). Ese detalle es lo que evita reprocesar el corpus entero cada
-- noche, y es un caso de test obligatorio.
--
-- NOMENCLATURA: la columna es `content_hash`, no `content_sha256`. En el 04,
-- `raw_sha256` es otra cosa distinta -- el hash de los bytes crudos del fichero
-- -- y esa si existe.
--
-- =============================================================================
-- SOBRE LA IDEMPOTENCIA "BYTE A BYTE"      (sin cambios respecto a v1)
-- =============================================================================
--
-- El documento del 04 declara como invariante "dos ejecuciones -> indice
-- identico byte a byte". Eso es IMPOSIBLE de cumplir y hara fallar el test mas
-- importante del repo por razones que no tienen nada que ver con la
-- idempotencia:
--
--   - Los bytes fisicos de una tabla Postgres incluyen cabeceras de tupla,
--     xmin y orden fisico.
--   - Las salidas de un modelo de embeddings NO son bit-reproducibles cuando
--     cambia la composicion del lote, y la composicion cambia con la carga y
--     el orden de llegada.
--
-- Invariante correcto, que ademas es mas interesante de contar:
--
--   A) IDENTIDAD Y COBERTURA (exacto, siempre):
--        sha256 del conjunto ORDENADO de
--        (chunk_id, content_hash, embedding_model, dim, index_version)
--      Dos ejecuciones deben producir el mismo hash. Sin excepcion.
--
--   B) IGUALDAD DE VECTORES (bajo condiciones declaradas):
--        Solo con tamano de lote y orden fijados, y con tolerancia declarada
--        (norma L2 de la diferencia < 1e-5).
--
-- Se documenta como ADR. El enunciado ingenuo suena mejor en un README; este
-- es el que sobrevive a una pregunta en una entrevista.
--
-- =============================================================================
-- v2 · PROCEDENCIA EN EL INFORME DE EVAL   (condicion del 01, no negociable)
-- =============================================================================
--
-- Con conmutacion por alias, todo informe de eval registra el DESTINO FISICO
-- RESUELTO, nunca el nombre del alias:
--
--     index_alias.alias           -> 'active'              (informativo)
--     index_alias.index_version   -> 'v2-qwen3emb-1024'    (OBLIGATORIO)
--     index_alias.physical_table  -> 'chunk_v2'            (OBLIGATORIO)
--
-- Sin esto, dos ejecuciones con el mismo alias apuntando a datos distintos
-- producirian informes normalizados identicos sobre corpus distintos, y
-- G-EVAL-DET del 01 (propuesta_admisible: false) dejaria de significar nada.
-- =============================================================================
