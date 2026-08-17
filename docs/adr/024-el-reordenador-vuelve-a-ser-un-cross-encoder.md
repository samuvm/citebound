# ADR-024 · el reordenador vuelve a ser un cross-encoder en proceso

- **Fecha:** 2026-08-17
- **Fase:** 2
- **Estado:** **Aceptado** (Q-020, decidido por Samuel)
- **Supersede a:** [ADR-022](022-reordenador-por-el-mismo-transporte.md)

## Contexto

ADR-022 adoptó el generador como reordenador —un solo transporte— porque era lo que Q-017
decidió. Entonces las dos columnas de la comparación decían *«más lento, hay que medirlo»* y
*«su calidad hay que medirla, no está dada»*. Se midió, y lo que salió no es lo que se sopesó:

| | lo que se supuso en Q-017 | lo medido |
|---|---|---|
| Coste | por confirmar | **4.600 ms** contra un presupuesto de 400 (`RULES` §2.1) |
| Calidad | por confirmar | `G-RECALL5` **0,852** contra un umbral de 0,90 |

Y el diagnóstico que lo cierra: **no era cuestión de tamaño.** Un generalista de 9B ordena
igual o peor que el de 4B —0,843 contra 0,852— tardando un 56 % más. No es el tamaño del
modelo, es el tipo.

## Opciones consideradas

Las de Q-020, con dieciséis experimentos medidos delante y diez negativos:

| Opción | Pros | Contras |
|---|---|---|
| **A · cross-encoder en proceso** | Entrenado para ordenar. Única que ataca a la vez la calidad y `G-TTFT` | Segundo camino de servir modelos, ~2 GB de dependencias, una descarga más en frío |
| B · aceptar 0,852 y proponer bajar el umbral | La fase cierra hoy | Es bajar la vara, aunque el diagnóstico esté hecho |
| C · dejar la meta roja y seguir | El agente se puede construir | Se construye sobre un recuperador que sabemos que no llega |

## Decisión

**A**, y **con el retador y no con el principal.** `docs/STACK.md` §2.2 proponía
`Qwen3-Reranker-0.6B` por ser *instruction-aware*; ese argumento no se sostuvo al medirlo.

| modelo | `G-RECALL5` | p95 de reordenar 30 |
|---|---:|---:|
| `BAAI/bge-reranker-v2-m3` (retador) | **0,801** | **400 ms** |
| `Qwen/Qwen3-Reranker-0.6B` (principal) | 0,787 | 886 ms |
| `Qwen3-Reranker` con instrucción de dominio | 0,773 | 886 ms |

La instrucción del dominio —la que motivaba elegir el principal— **empeora**: 0,773 contra
0,787. Sobre un par de ejemplo separaba mejor que la genérica, y sobre los 216 casos no. Es la
tercera vez en esta fase que una medida dirigida sobrepredice, y por eso las tres se anotan.

## Consecuencias

**Se pierden 5 puntos de `G-RECALL5`** — de 0,852 a 0,801 — y hay que decirlo con esas
palabras: la opción elegida **no** mejora la calidad, que era la mitad de su argumento.

**Se gana lo demás, y tres de esas cosas son metas por derecho propio:**

| | generador (ADR-022) | cross-encoder |
|---|---|---|
| p95 de reordenar 30 | 4.600 ms | **400 ms** — exactamente el presupuesto |
| `make eval-retrieval` en frío | 1.030 s | **96,5 s** |
| ¿necesita caché de juicios? | sí, o no es reproducible | **no** |
| ¿reproducible? | **no** (0,852 · 0,847 · 0,852) | **sí, byte a byte** |
| ¿cabe en el camino interactivo? | no (por eso Q-019 eligió A) | **sí** |

- **`G-EVAL-DET` pasa de problema a propiedad.** Su umbral es `== true` y no admite propuesta.
  Con el generador, dos corridas en frío de la misma configuración daban números distintos —en
  GPU la reducción de coma flotante no es asociativa y el *greedy* elige distinto— y la caché
  era lo único que lo tapaba. El cross-encoder es determinista por construcción.
- **Q-019 se reabre de hecho.** Se eligió **A** —reordenador solo de evaluación— *porque*
  costaba 4,6 s. A 400 ms esa razón desaparece, y con ella el problema de fondo que planteaba:
  publicar un `G-RECALL5` medido con un componente que el producto no ejecuta. Ahora el número
  publicado **es** el que recibe quien pregunta.
- **El número publicado baja y la brecha crece**: 0,801 contra un umbral de 0,90. `G-RECALL5`
  sigue siendo lo único rojo del gate.
- **Revertir cuesta una variable**: `CITEBOUND_RERANK_LLM=1` vuelve al generador. Los dos
  reordenadores se quedan en el código con su medida, porque comparar exige poder repetir.
- **`docs/RULES.md` R8 y `docs/STACK.md` §2.1 vuelven a ser correctos** sin tocarlos: describían
  el cross-encoder en proceso desde el principio. Q-018 queda **sin objeto**.
