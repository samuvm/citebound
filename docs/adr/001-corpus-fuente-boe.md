# ADR-001 · El corpus es el XML consolidado del BOE, no un PDF

- **Fecha:** 2026-08-10
- **Fase:** 0
- **Estado:** **Aceptado**
- **Supersede a:** —

## Contexto

`G-HALLUC` tiene umbral `== 0` y `propuesta_admisible: false`: se define como pertenencia de la
`legal_ref` al conjunto de refs del índice. Eso obliga a que la jerarquía norma → artículo →
apartado sea **exacta**, porque un error de parseo produce una `legal_ref` que no existe y la meta
más dura del proyecto falla por una razón que no tiene nada que ver con el modelo.

Sondeo del 2026-08-10 contra `https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{id}`:

| id | HTTP | bytes | consolidación |
|---|:--:|---:|---|
| `BOE-A-2003-21806` *(el que decía Q-001)* | **404** | — | no existe |
| **`BOE-A-2003-23514`** RD 1428/2003, RGC | 200 | 1 158 926 | `20260731T082621Z` |

232 bloques `precepto` (217 `Artículo N`), 103 `encabezado`, `Artículo 14 bis`, y cada precepto con
`<version id_norma= fecha_vigencia=>`: procedencia por artículo, sin coste.

## Opciones consideradas

| Opción | Pros | Contras | Coste medido |
|---|---|---|---|
| **A · XML consolidado por API** | Jerarquía explícita y sin pérdida · gratis · fecha de consolidación oficial · procedencia por artículo | El apartado no está marcado (ver abajo) | 1 curl, 1,16 MB |
| B · PDF + Docling | Reutiliza herramienta del proyecto 04 | Un parser de *layout* mete error evitable en la métrica que declaramos con tolerancia cero. Y `docling` es 200 MB de dependencias que aquí no hacen falta | ≥1 día de spike + error residual no acotado |
| C · *scraping* del HTML de boe.es | Igual de gratis | La jerarquía hay que reconstruirla desde clases CSS, que no son contrato y cambian sin aviso | Frágil, sin ventaja |

## Decisión

**A.** Se congelan `corpus/raw/BOE-A-2003-23514.xml`
(sha256 `1105a26b…40072`) y su `metadatos.xml` (`1122cd91…3884e`) en `corpus/MANIFEST.yaml`,
consolidación `2026-07-31`. Alcance: solo el RGC (Q-001 opción A). Docling se queda en el
proyecto 04, donde el reto **sí** es el PDF sucio; traerlo aquí sería resolver un problema que la
fuente ya resuelve.

## Consecuencias

- **Se gana** un árbol fiable, y `make corpus-verify` (R4) pasa a ser un `sha256` más una
  regeneración con `diff`, no una inspección manual.
- **Se pierde** cobertura: lo que no esté en el RGC no se puede responder. Eso es deliberado — se
  convierte en los casos `tipo: negativo` del golden set y da de comer a `G-ABST-FN`.
- **Dos rarezas del árbol que gobiernan `ingest/boe_xml.py`** y son el riesgo técnico nº 1 de `0.3`:
  1. **El apartado no es estructural.** Va como prefijo dentro de `<p class="parrafo">`
     (`"1. Se deberá conducir…"`). Como `retrieval-metrics.md` §2 considera fallo citar `art21`
     cuando lo correcto es `art21.1`, la granularidad de la que dependen `G-CITA-PRECISION` y
     `G-QUOTE-LIT` **se deriva del texto**, no se lee del árbol.
  2. **Dos espacios de numeración en un documento.** El RD tiene un `Artículo único`; el Reglamento
     anexo tiene los suyos, 1..N. **`LegalRef` numera los del Reglamento**; el artículo único del RD
     se indexa aparte y nunca colisiona.
- **623 `<p class="imagen">`** son señales de tráfico: chunks sin texto útil. Quedan fuera del
  índice y se declara en el README, porque afecta al recall de la materia «señalización».
- **Pendiente honesto:** la URL del aviso legal de reutilización del BOE devolvió 404 el
  2026-08-10. La atribución del README se cierra antes de la fase 5; la decisión de qué se
  redistribuye ya está tomada en Q-003 + D-06 (a).
- **Revertir** cuesta re-descargar y re-ingerir: horas, no días, mientras el ancla siga siendo
  `legal_ref` y no `chunk_id` (R1).
