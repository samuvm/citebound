# ADR-019 · El producto es una interfaz de práctica de test, y no comparte código con el motor

- **Fecha:** 2026-08-10
- **Fase:** 0
- **Estado:** **Aceptado**
- **Supersede a:** —

## Contexto

`docs/PROJECT.md` ya listaba `POST /session/{id}/next-block` y `POST /session/{id}/answer` entre los
objetivos funcionales, pero `docs/PLAN.md` los degradó a la fase 6 («solo si sobra tiempo») porque
**no había banco de preguntas**: construir la interfaz habría exigido inventarse los contenidos.

El 2026-08-10 Samuel aportó un banco de 2.597 preguntas tipo test con sus opciones y la correcta
marcada, y decidió que el producto es la interfaz de práctica. La condición que puso, literal, es
que el motor y la interfaz vayan «en código muy separado».

Eso no es una preferencia estética. Un producto pegado al motor obliga a que `[tool.gate].testable`
incluya código de presentación, y entonces `G-COV-FUNC` (cero funciones públicas sin test) y `G-MUT`
(≥70 % de mutantes muertos) empiezan a exigirse sobre *handlers* de UI, que es exactamente el «ruido
en adaptadores» que `PROJECT.md` §2 rechaza con razón.

## Opciones consideradas

| Opción | Pros | Contras | Coste |
|---|---|---|---|
| **A · dos capas, una frontera HTTP** | El motor no sabe que existe una UI. La UI solo habla la API pública. `[tool.gate]` no cambia | Hay que mantener el contrato OpenAPI como frontera real | Un test de contrato más |
| B · la UI importa el dominio directamente | Menos ceremonia, sin capa HTTP | El régimen de pruebas se contamina: o metes la UI en `testable` y persigues cobertura en botones, o la excluyes y creas un agujero por donde se cuela lógica sin test | Barato hoy, caro en fase 5 |
| C · dejarlo en fase 6 como estaba | Cero decisión | El proyecto no tiene producto que enseñar hasta el final, y `PLAN.md` admite no llegar a la fase 6 | 0 |

## Decisión

**A.** Dos capas con una frontera única:

- **`src/citebound/`** — el motor. No cambia nada de lo ya escrito: mismos invariantes, mismo
  `[tool.gate]`, mismo régimen de TDD. **No importa nada de la interfaz ni sabe que existe.**
- **`ui/`** — la interfaz de práctica. Directorio propio, entra en `[tool.gate].excluido` y en
  `tdd_prohibido`, y **su única forma de hablar con el motor es la API HTTP**. Se le exige un test
  de contrato contra el snapshot de OpenAPI y nada más.

La analogía de Samuel es la correcta: son las manetas de la bici. Hay que ponerlas, se cambian sin
tocar la transmisión, y no se diseñan con el mismo cuidado que los frenos.

El BKT **no entra**. Servir preguntas y explicarlas con su artículo no necesita trazado de
conocimiento; la selección adaptativa es un producto distinto y se queda donde está, en la fase 6
como ampliación con su timebox de 3 días.

## Consecuencias

- **Se gana** un producto enseñable mucho antes, y con la ventaja técnica de que **la consulta deja
  de ser texto libre**: es la pregunta más sus tres opciones, redactadas en lenguaje casi normativo
  y **conocidas de antemano** — las 2.597 son fijas, así que el retrieval se puede auditar caso a
  caso e incluso precalcular. Eso reduce de verdad el riesgo de `G-RECALL5`.
- **Se pierde** la promesa de chat libre. `POST /ask` sigue existiendo y sigue siendo el corazón del
  motor, pero deja de ser el producto que se enseña.
- **Se vuelve difícil de cambiar** el día que la UI necesite algo que la API no expone: la respuesta
  correcta es ampliar la API, nunca importar el dominio desde `ui/`. Si esa línea se cruza una vez,
  se cruza siempre.
- **Cambia `docs/PLAN.md`**, que es zona roja: la divergencia nº 10 de Q-002 se parte en dos. Va
  como propuesta **P-001** (`cambiar-plan`) en `docs/PARA-SAMUEL.md` y **no se ejecuta hasta que
  Samuel la apruebe**.
- **Afecta a** `pyproject.toml [tool.gate].excluido` y `tdd_prohibido`, y al test de contrato del
  snapshot OpenAPI.
