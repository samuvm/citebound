# ADR-021 · `v2` del golden set: fuera tres casos que ningún sistema puede responder

- **Fecha:** 2026-08-17
- **Fase:** 2
- **Estado:** **Aceptado**
- **Supersede a:** —

## Contexto

La primera medición de `G-RECALL30` sobre `v1.jsonl` dio **0,954** contra un umbral de 0,97.
El diagnóstico —puesto del artículo correcto en la lista recuperada— mostró que en 10 de los
219 casos positivos el artículo **no aparece entre los 30**, y que de esos 10 hay tres cuyo
enunciado **no contiene información**:

| Caso | Enunciado |
|---|---|
| `gs-0036` | «Ante esta situación, el conductor debe….» |
| `gs-0061` | «El conductor del turismo amarillo….» |
| `gs-0127` | «Cuando el vehículo amarillo gire a la derecha, ¿qué debe hacer el conductor del vehículo verde?» |

Los tres remiten a un dibujo. El banco los traía marcados como `depende_imagen: no` porque ese
campo se derivó por patrón sobre el enunciado —buscando cosas como «¿qué indica esta señal?»—
y esa clase de pregunta no se detecta así. Las imágenes no están en el repositorio (Q-003) y
no se van a redistribuir.

## Opciones consideradas

| Opción | Pros | Contras |
|---|---|---|
| **A · sacarlos, creando `v2`** | La métrica mide lo que el sistema puede controlar. El `v1` queda como testigo y el cambio es auditable | Es tocar el conjunto de evaluación **después** de medir, que siempre merece lupa |
| B · dejarlos | Cero manipulación | `G-RECALL30` queda acotado por debajo de su propio umbral por una razón ajena al sistema, y perseguir esos puntos llevaría a optimizar contra ruido |
| C · sacar los diez | Cerraría la meta de golpe (0,977) | **Rechazada.** Siete de los diez son preguntas respondibles: sacarlas sería barrer fallos reales de recuperación |

## Decisión

**A, y solo con los tres.** Un primer recuento clasificó cinco por expresión regular; al leerlos
enteros, `gs-0152` («sale marcha atrás de un garaje, ¿quién tiene preferencia?») y `gs-0215`
(«inmovilizado en el lado derecho de la calzada…») **sí** se responden desde el texto: el color
es decorativo en uno y el otro está truncado pero conserva el supuesto. Contarlos como
irrecuperables habría subido la métrica escondiendo dos fallos de verdad.

El criterio, para que sea aplicable por otro: **sale un caso si su enunciado, sin la imagen, no
identifica el supuesto de hecho.** No basta con que mencione un color o esté cortado.

## Consecuencias

- **Se gana** una métrica que mide el sistema. `G-RECALL30` pasa de 0,954 a **0,968**.
- **Se pierde** el cierre automático de la meta: 0,968 sigue por debajo de 0,97. El hueco que
  queda son **siete casos respondibles** que el recuperador no trae, y ese sí es su problema.
- **`v1.jsonl` no se toca** (R12, append-only). Queda como testigo de lo que se anotó, y el
  README publica los dos números con este ADR al lado.
- **Los tres casos no se borran del banco**: siguen en la cola con su veredicto. Lo que cambia
  es que no entran en el conjunto contra el que se mide.
- **Revertir** es reconstruir desde `v1`, que sigue ahí. Cuesta un comando.
