# Fuente del golden set · banco de preguntas tipo test

**Qué es.** El material bruto del que salen los 190 casos de `evals/golden/v1.jsonl`.
No es el golden set: es su materia prima. El golden set son estas preguntas **más la
referencia legal validada por un humano**, que es justo lo que aquí no hay.

## Ficheros

| Fichero | Qué es | sha256 |
|---|---|---|
| `preguntas-dgt-202606.original.csv` | El volcado tal cual llegó. **No se toca.** Existe para que la poda sea rederivable | `fedfc307f9f9b578…` |
| `preguntas-dgt-202606.csv` | El mismo, podado a 11 columnas y con 2 columnas derivadas | `5646d01e0cf7ac13…` |

2.597 preguntas, tres opciones cada una, con la correcta marcada. Ninguna descatalogada.

## Qué se conservó y qué se tiró

De 28 columnas quedan 11. Se conservan:

| Columna | Origen | Para qué |
|---|---|---|
| `source_id` | `idpregunta` | Trazabilidad al volcado original |
| `pregunta` | `textopregunta` | |
| `opcion_1..3` | `respuesta1..3` | `respuesta4` estaba vacía en las 2.597 |
| **`respuesta_correcta`** | `respuestaCorrecta` | **Verificado: casa con una de las tres opciones en las 2.597 filas, sin una sola excepción** |
| `tema`, `subtema` | `temaDenominacion`, `subtemaDenominacion` | Estratificación por materia (`G-GOLDEN-VALID` exige ≥6 materias con ≥20 casos) |
| `pct_fallo` | `mediaFallada` | **Dificultad empírica real** (% de gente que la falla). Sustituye al campo `dificultad` subjetivo del contrato. Mediana 10,1 · p75 15,8 · máx 54,2 |

Se descartaron 17 columnas sin uso aquí: `traffictest`, `fotoRouteComplete`,
`vecesHecha`, `vecesHechaExperimento`, `mediaFalladaExperimento`, `idTema`, `idSubtema`,
`descatalogada` (constante `No`), `idRespuesta1..4`, `idRespuestaCorrecta`, `respuesta4`
(siempre vacía) y los cinco `enableFor*`.

## Las dos columnas derivadas

**`depende_imagen`** — la pregunta necesita ver la foto para responderse
(«¿qué indica esta señal?»). Detectado por patrón sobre el enunciado. **193 preguntas
(7,4 %)**, concentradas en señales: 72 de las 116 de «Señales de Peligro y Prohibición».
**Quedan fuera del golden set** y se declara en el README del proyecto. El 92,6 % restante
lleva imagen decorativa que no aporta a la respuesta.

**`cobertura_rgc`** — si el tema está o no dentro del Reglamento General de Circulación,
que es el corpus decidido en Q-001 opción A:

| Valor | Temas | Total | Usables (sin imagen) | Papel en el golden set |
|---|---|---:|---:|---|
| `rgc` | Definiciones, Señalización, Marcas viales, Cambios de dirección, Inmovilizaciones, Uso de la vía y adelantamientos, Señales, Arcenes, Preferencias, Velocidad, Luces | 1.284 | **1.103** | **Positivos.** Hacen falta 150 |
| `fuera` | Mecánica, Primeros auxilios, Tiempo y distancia de reacción, Factores humano/vía/vehículo, Permisos de conducir | 961 | **954** | **Negativos naturales.** Hacen falta 40 |
| `mixto` | Personas y mercancías transportadas, Motocicleta, Preguntas nuevas | 352 | 347 | Por clasificar caso a caso |

Los negativos son el hallazgo que abarata la fase 1: son preguntas **reales de examen**
cuya respuesta genuinamente no está en el Reglamento de Circulación (una está en el
Reglamento de Conductores, otra en el de Vehículos, otra en ninguna norma). Fabricar
negativos creíbles a mano es lo más caro del golden set, y aquí ya están escritos.

## Procedencia y licencia

Banco de preguntas tipo test de circulación, de acceso público en internet, aportado por
Samuel el 2026-08-10. Las rutas de imagen del volcado original apuntan a una plataforma de
autoescuela; **las imágenes no están en este repositorio y no se redistribuyen**.

Decisión registrada en `docs/PARA-SAMUEL.md` Q-003. El campo `provenance` de cada caso del
golden set y el README del proyecto declaran este origen, según la política de honestidad
**D-06 opción (a)**.

## Lo que falta

Ninguna de estas 2.597 preguntas tiene todavía su **referencia legal**. Ese es el trabajo
de la fase 1c: el agente propone `LegalRef` para 190 casos, Samuel valida o corrige, y solo
entonces existe `evals/golden/v1.jsonl`. Ninguna entra sin revisión humana
(`retrieval-metrics.md` §3, regla dura nº 3).
