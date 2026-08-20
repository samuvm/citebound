# `ui/` · la interfaz de práctica de test

**Su única forma de hablar con el motor es la API HTTP** (ADR-019, P-001). No importa
`citebound` ni conoce el dominio: si necesitara algo que la API no da, lo correcto es **ampliar
la API**, nunca importar el motor desde aquí. Esa línea cruzada una vez deja de existir.

Por eso este directorio está en `[tool.gate].excluido` y en `tdd_prohibido`: son las manetas de
la bici. Hay que ponerlas, se cambian sin tocar la transmisión, y no se diseñan con el mismo
cuidado que los frenos. Lo que sí se le exige es un test de contrato contra el snapshot de
OpenAPI —para que la frontera sea real y no una intención— y un humo de punta a punta.

## Qué hace

Sirve una pregunta del banco, registra la opción elegida, y pide al motor la explicación
**citada** del artículo que la resuelve. Lo que el usuario ve del motor son sus citas, no su
prosa: la respuesta va acompañada de la referencia legal y del fragmento verificado.

## Qué NO hace

- **No selecciona adaptativamente.** El BKT es la fase 6 y es un producto distinto (ADR-019).
- **No decide si una respuesta es válida.** Eso lo hace el verificador, y la UI solo enseña lo
  que la API le da: si el motor se abstuvo, la UI dice que se abstuvo y por qué.
