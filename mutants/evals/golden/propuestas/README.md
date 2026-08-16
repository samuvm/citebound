# Propuestas de referencia legal · fase `1b`

Un fichero por tema. Cada entrada es `id del candidato → {ref, nota}`: **la referencia legal
que propongo y por qué**, para que Samuel valide o corrija en `1c`.

**Esto sí se versiona, y la cola no.** La cola (`evals/golden/cola/`) lleva el enunciado y las
tres opciones literales del banco de terceros. Estos ficheros no llevan ni una palabra ajena:
solo identificadores, artículos del BOE y criterio propio. Es exactamente la parte
transformativa que el `.gitignore` distingue.

## Qué significa el campo `nota`

Vacío es «lo tengo claro». Con texto es **dónde mirar con más cuidado**, y hay tres clases:

- **Por qué este artículo y no el vecino**, cuando dos se parecen y uno tipifica la conducta
  mientras el otro solo la menciona.
- **DUDOSA**, cuando la respuesta depende de algo que la pregunta no dice (típicamente, si la
  vía del dibujo es urbana o interurbana).
- **CONTRADICE AL TEXTO**, cuando la respuesta del banco no casa con el artículo. Son las
  candidatas a `descartar`, y son las que más agradecen un ojo humano.

Las que llevan nota son las que más probablemente cambien tras la revisión, y su proporción
es en sí un dato: mide cuánto de este trabajo es mecánico y cuánto es criterio.
