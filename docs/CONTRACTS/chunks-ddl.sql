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
-- Version del contrato: 1
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
-- Un indice = una fila. El alias "activo" apunta a uno de ellos.
-- La conmutacion atomica del proyecto 04 opera sobre esta tabla, no sobre datos.
-- -----------------------------------------------------------------------------
CREATE TABLE index_version (
    id              TEXT PRIMARY KEY,           -- p.ej. 'v2-qwen3emb-1024'
    embedding_model TEXT        NOT NULL,       -- id exacto del modelo
    dim             INT         NOT NULL,       -- dimension real de los vectores
    distance        TEXT        NOT NULL        -- 'cosine' fijo en el contrato v1
                    CHECK (distance = 'cosine'),
    chunker_id      TEXT        NOT NULL,       -- estrategia de troceado usada
    corpus_snapshot TEXT        NOT NULL,       -- fecha de consolidacion del corpus
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active       BOOLEAN     NOT NULL DEFAULT false
);

-- Solo puede haber un indice activo. Es lo que hace atomica la conmutacion.
CREATE UNIQUE INDEX one_active_index
    ON index_version (is_active) WHERE is_active;

-- -----------------------------------------------------------------------------
-- Chunks. dim = 1024 en el contrato v1.
--
-- Nota para el 04: cambiar de modelo de embeddings puede cambiar la dimension.
-- Por eso los vectores de dimensiones distintas viven en TABLAS distintas
-- (chunk_v1, chunk_v2, ...) y no en la misma con una columna nullable.
-- Postgres no permite dimension variable en una columna vector.
-- Esta tabla es la plantilla; cada version_indice materializa la suya.
-- -----------------------------------------------------------------------------
CREATE TABLE chunk (
    chunk_id        TEXT        PRIMARY KEY,    -- DETERMINISTA. Ver contrato de IDs abajo
    index_version   TEXT        NOT NULL REFERENCES index_version(id),

    content         TEXT        NOT NULL,
    content_hash    TEXT        NOT NULL,       -- sha256 del content normalizado

    embedding       vector(1024) NOT NULL,

    -- Busqueda lexica. Generada, nunca escrita a mano.
    content_tsv     tsvector    GENERATED ALWAYS AS (
                        to_tsvector('spanish_unaccent', content)
                    ) STORED,

    -- Identificador legal ESTABLE. Es lo que cita el sistema y contra lo que
    -- se evalua. NUNCA se evalua contra chunk_id: ver retrieval-metrics.md.
    norma           TEXT        NOT NULL,       -- 'RD-1428/2003'
    articulo        TEXT,                       -- '21'
    apartado        TEXT,                       -- '1', '2.a'
    legal_ref       TEXT        GENERATED ALWAYS AS (
                        norma
                        || COALESCE('#art' || articulo, '')
                        || COALESCE('.' || apartado, '')
                    ) STORED,

    -- Jerarquia estructural, para filtrado por materia.
    titulo          TEXT,
    capitulo        TEXT,
    seccion         TEXT,
    materia         TEXT,

    -- Posicion dentro del documento fuente. Parte del ID determinista.
    doc_id          TEXT        NOT NULL,
    ordinal         INT         NOT NULL,

    metadata        JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (index_version, doc_id, ordinal)
);

-- -----------------------------------------------------------------------------
-- Indices. Los hiperparametros son parte del contrato: sin ellos, dos
-- proyectos miden recall sobre estructuras distintas y los numeros no comparan.
-- -----------------------------------------------------------------------------
CREATE INDEX chunk_embedding_hnsw ON chunk
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
-- Consulta: SET hnsw.ef_search = 100;   -- declarado, no por defecto

CREATE INDEX chunk_tsv_gin      ON chunk USING gin (content_tsv);
CREATE INDEX chunk_legal_ref    ON chunk (legal_ref);
CREATE INDEX chunk_materia      ON chunk (materia);
CREATE INDEX chunk_index_ver    ON chunk (index_version);

-- -----------------------------------------------------------------------------
-- Estado por documento. El invariante que gobierna el proyecto 04:
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
-- CONTRATO DE IDENTIFICADORES  (critico para la idempotencia del 04)
-- =============================================================================
--
--   doc_id      = sha256(source_uri)[:16]
--   content_hash= sha256(normalize(content))        normalize = NFC + colapso de
--                                                   espacios + strip
--   chunk_id    = sha256(f"{doc_id}:{ordinal}:{content_hash}")[:24]
--
-- Funcion pura de (documento, posicion, contenido). Sin timestamps, sin UUID
-- aleatorio, sin contadores de proceso. Es lo que hace que dos ejecuciones
-- produzcan la misma secuencia de IDs.
--
-- doc_hash NO incluye metadatos irrelevantes (fecha de descarga, cabeceras
-- HTTP, mtime). Ese detalle es lo que evita reprocesar el corpus entero cada
-- noche, y es un caso de test obligatorio.
--
-- =============================================================================
-- SOBRE LA IDEMPOTENCIA "BYTE A BYTE"
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
-- =============================================================================
