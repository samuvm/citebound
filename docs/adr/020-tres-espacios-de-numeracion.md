# ADR-020 · Un documento, tres espacios de numeración: el contenedor entra en la `LegalRef`

- **Fecha:** 2026-08-10
- **Fase:** 0
- **Estado:** **Aceptado**
- **Supersede a:** — (corrige y amplía el ADR-001, que se queda corto en este punto)

## Contexto

El ADR-001 anotó que `BOE-A-2003-23514` tiene «dos espacios de numeración»: el Real Decreto con su
`Artículo único` y el Reglamento anexo con los suyos. Al escribir `ingest/boe_xml.py` y medirlo
contra el corpus congelado, el número real es **tres**, y hay además una colisión dentro del propio
Reglamento:

| Espacio | Cuántos | Ejemplo |
|---|---:|---|
| Real Decreto (antes de la frontera `REGLAMENTO GENERAL DE CIRCULACIÓN`, byte 15 706) | 7 | `Artículo único`, `Disposición final primera` |
| Reglamento (el cuerpo) | 189 | `Artículo 34` |
| Articulado **dentro de cada ANEXO**, que reinicia en 1 | 40 | `Artículo 1` de `ANEXO I`, byte 1 080 556 |
| **Colisión dentro del cuerpo:** `TÍTULO VI`, añadido por RD 465/2025, reinicia en 151 | 8 pares | dos `Artículo 151`, uno de señales y otro de zonas urbanas |

Con designador plano, **47 de 236 referencias colisionan**. No es un riesgo estimado: es el
recuento sobre el fichero. Y el daño es del tipo silencioso — `recall@k` compara **conjuntos** de
`legal_ref` (`retrieval-metrics.md` §2), así que dos artículos distintos con la misma referencia se
cuentan como uno, y un caso del golden set que cite `art151` es ambiguo entre dos textos que no
tienen nada que ver.

## Opciones consideradas

| Opción | Pros | Contras | Coste medido |
|---|---|---|---|
| **A · prefijo por contenedor**, y prefijo por TÍTULO solo donde colisiona | 228 de 236 referencias conservan la forma plana que usa el ejemplo del contrato. Determinista y explicable en una frase | Dos formas conviviendo: `art34` y `arttvi-151` | `_DESIGNADOR` admite guiones + seguimiento de contenedor: **~2 h** |
| B · prefijar **todas** por su TÍTULO | Una sola forma, sin excepciones | Rompe el ejemplo del propio contrato (`RD-1428/2003#art34.1`) y hace ilegible la cita que verá el usuario | Reescribir el contrato compartido: evento con propagación a dos repos |
| C · desambiguar solo la segunda aparición | Cambio mínimo | **Depende del orden de lectura.** Si el BOE reordena los bloques, las referencias cambian y el golden set se invalida en silencio | 0 h hoy, indefinido después |
| D · no hacer nada | 0 | 47 colisiones que envenenan `recall@k` y el golden set | 0 |

## Decisión

**A.** El designador lleva el contenedor cuando hace falta y solo entonces:

```
RD-1428/2003#art34            el Reglamento es el contenedor por defecto, sin prefijo
RD-1428/2003#artrd-unico      los siete preceptos propios del Real Decreto
RD-1428/2003#artanexoii-1     articulado interno de un anexo
RD-1428/2003#arttv-151        colisión: TÍTULO V
RD-1428/2003#arttvi-151       colisión: TÍTULO VI
```

Dos reglas que hacen esto determinista y no una heurística:

1. **El Reglamento no lleva prefijo.** Es lo que cita el ejemplo del contrato y donde estará casi
   todo el golden set.
2. **Ante una colisión se prefijan LOS DOS miembros, nunca solo el segundo.** El resultado no
   depende del orden de lectura, que es lo que descarta la opción C.

`_DESIGNADOR` de `domain/legalref.py` pasa de `^[a-z0-9]+$` a `^[a-z0-9]+(?:-[a-z0-9]+)*$`: un
guion **une** segmentos y nunca cuelga. No toca el contrato compartido, que no restringe el formato
del designador más allá de la regla de concatenación.

## Consecuencias

- **Se gana** que `parse_norma` sobre el corpus congelado dé **236 preceptos y 0 referencias
  duplicadas**, verificado por test. Y que un anexo pueda crecer sin pisar al cuerpo.
- **Se pierde** uniformidad: hay dos formas de designador. Se acepta porque la alternativa era
  romper el ejemplo del contrato compartido, y porque la forma prefijada solo aparece en 16 de 236.
- **Ojo al orden del fichero:** `TÍTULO VI` está **físicamente detrás de los cuatro anexos**. Un
  encabezado `TÍTULO` devuelve el parser al cuerpo, y entrar en un `ANEXO` limpia la jerarquía
  heredada; sin lo primero, el `Artículo 151` de zonas urbanas salía como `anexoii-151`.
- **Lo que hay que revisar si crece el corpus (Q-001 B o C):** cada norma nueva trae sus propios
  contenedores. La regla se aplica igual, pero el recuento de colisiones hay que volver a medirlo,
  no suponerlo.
- **Afecta a** `domain/legalref.py`, `ingest/boe_xml.py`, `corpus/MANIFEST.yaml` y —cuando exista—
  al golden set: un caso no puede citar `art151` sin decir de qué TÍTULO.
