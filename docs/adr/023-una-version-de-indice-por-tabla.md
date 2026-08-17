# ADR-023 · una versión de índice por tabla física, y lo que eso le quita a ADR-018

- **Fecha:** 2026-08-17
- **Fase:** 2
- **Estado:** **Aceptado**
- **Supersede a:** —  · **Matiza:** ADR-018 (conmutación por alias)

## Contexto

Al reindexar el corpus con `qwen3-embedding:0.6b` —misma dimensión que `bge-m3`, 1024— la
ingesta anunció el índice nuevo, el alias apuntó a él, y **las 235 filas siguieron diciendo que
eran del viejo**. Los vectores sí eran los nuevos: medida la distancia euclídea del vector
guardado contra lo que produce cada modelo para el mismo texto, `0,000000` con `qwen3` y
`1,420182` con `bge-m3`.

La causa está en el contrato compartido, y no es un descuido de nadie: `chunk_id` es
`blake2b(doc_id ‖ content_hash ‖ occurrence)`, una función pura del documento **que no depende
del modelo de embedding**. Reindexar el mismo corpus con otro modelo calcula por tanto los
mismos identificadores, cae en el `ON CONFLICT (chunk_id)` y sustituye los vectores en sitio.

El contrato admite dos lecturas y conviene decir cuál se sigue:

> «los vectores de dimensiones distintas viven en TABLAS distintas (`chunk_v1`, `chunk_v2`, …).
> Esta es la plantilla; **cada index_version materializa la suya** y el alias decide cuál está
> activa.»

La primera frase sugiere partir **por dimensión**; la segunda, **por versión de índice**. Y hay
un tercer dato que decide: `chunk_id` es la **clave primaria**. Dos versiones de índice de la
misma dimensión en la misma tabla **colisionan**, así que la lectura por dimensión no se sostiene
sola. Los `UNIQUE (index_version, doc_id, …)` que también trae la tabla son redundantes bajo esta
lectura, no contradictorios.

## Opciones consideradas

| Opción | Pros | Contras |
|---|---|---|
| **A · una versión de índice por tabla; a igual dimensión, el reindexado es destructivo en sitio** | Es lo único compatible con `chunk_id` como PK. Cero cambios en el contrato, que es compartido | Se pierde la conmutación sin parar el servicio **dentro** de una dimensión |
| B · meter `index_version` en el `chunk_id` | Permitiría dos índices de la misma dimensión a la vez | **Rechazada.** Cambia la fórmula del `chunk_id`, que está escrita en un contrato compartido con `indexkeeper-04`. Un cambio así se hace como v3 y de acuerdo, nunca por conveniencia de un repo |
| C · materializar `chunk_v2` con la misma dimensión | No toca la fórmula | **Rechazada por ahora.** El DDL del contrato fija los nombres y los índices (`chunk_v1_embedding_hnsw`); generarlos por sustitución de cadenas sería fabricar DDL que el contrato no declara. Es la salida si algún día hace falta el A/B en caliente |

## Decisión

**A.** Una versión de índice por tabla física. La consecuencia se declara en vez de disimularse:

> **A igual dimensión, reindexar es destructivo en sitio.** La conmutación sin parar el servicio
> de ADR-018 sigue valiendo **entre dimensiones distintas**, que son las que viven en tablas
> distintas. Con dos modelos de 1024 no hay dos índices a la vez.

Y el `ON CONFLICT` pasa a actualizar también `index_version`, para que la fila no mienta sobre
su procedencia.

## Consecuencias

- **El síntoma era ninguno**, y ese es el motivo de que esto tenga ADR. La fila con vectores de
  un modelo y el nombre de otro no rompe nada visible: `make eval-retrieval` publicaba una
  procedencia falsa y no había forma de contradecirla.
- **El informe de eval registra ahora `index_version` y `physical_table` resueltos**, que el
  contrato ya exigía en mayúsculas y este repositorio no cumplía.
- **La consulta toma su embedder del índice, no del entorno.** Es el fallo hermano y el peor de
  los dos: vectorizar la consulta con un modelo distinto del que construyó el índice no da
  error —dimensiones iguales, `<=>` calcula, la búsqueda devuelve sus 30 filas— y todas están
  mal. Con `CITEBOUND_EMBEDDING_MODEL` por defecto en `bge-m3` y la base ya en `qwen3`, estuvo
  a un `make eval-retrieval` de publicarse.
- **Queda un hueco conocido**: entre la primera fila actualizada y la última, la tabla tiene
  mitad de vectores viejos y mitad nuevos, y `chunks_active` los sirve. Para un sistema local de
  un solo usuario es aceptable; para un despliegue, la salida es la opción **C**. Se anota aquí
  para que quien lo necesite no lo descubra midiendo.
- **Revertir** es reindexar con el modelo anterior: un comando y 17 s.
