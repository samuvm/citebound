# Changelog

Todos los cambios relevantes de **Citebound · tutor de normativa** (`citebound-01`).

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto se
adhiere a [Versionado Semántico](https://semver.org/lang/es/).

**Se escribe una entrada por fase cerrada, nunca por sesión ni por cambio suelto.** Una fase se
cierra cuando `make done MILESTONE=N` devuelve 0; hasta entonces no hay entrada. La entrada es
append-only y **lleva los números medidos**, no adjetivos: cada meta activa con su valor, su `n`,
su intervalo de confianza cuando aplique y el artefacto del que sale. Sin eso, el CHANGELOG es una
lista de intenciones y el proyecto pierde justo lo que lo distingue.

Regla que aplica también aquí: cambiar un fichero de `docs/CONTRACTS/` es un evento consciente y
**deja entrada propia**, con la versión del contrato y qué otros proyectos hay que propagar a mano.

## [No publicado]

### Añadido
- Capa de gobierno inicial: `CLAUDE.md`, `docs/GOALS.yaml`, `docs/PLAN.md`, `docs/RULES.md`,
  `docs/PARA-SAMUEL.md`, `docs/JOURNAL.md`, `docs/adr/000-plantilla.md`, `.claude/state/STATE.md`.
- Copias de `docs/CONSTITUCION.md` y `docs/STACK.md`, y de los contratos que aplican a este
  proyecto: `chunks-ddl.sql` (v1), `retrieval-metrics.md` (v1), `otel-genai.md` (v1) y
  `eval-report.schema.json` (v1). No se copian los que no aplican (`pricing-table.md`, 02 → 04).
- `docs/CONTRACTS/goals.schema.json` (v1) y `docs/CONTRACTS/README.md`, nuevos en `_comun/`.
- `docs/PARA-SAMUEL.md` Q-012 y Q-013: entradas **espejo** de Q-002 y Q-003 de `indexkeeper-04`
  sobre `docs/CONTRACTS/chunks-ddl.sql` (el `chunk_id` incluye el ordinal; `index_version.is_active`
  frente a vista `chunks_active` + `index_alias`), con el impacto medido en este proyecto. Un
  conflicto de contrato compartido declarado en un solo repositorio no está declarado.
- `docs/RULES.md` R20 y §2.3: la corrección múltiple de la puerta es Holm-Bonferroni, con el motivo
  (controla la FWER; un falso bloqueo acaba desactivando la puerta). Benjamini-Hochberg queda para
  el panel de diagnóstico, no para la puerta.

### Cambiado
- Resincronizadas todas las copias de `_comun/` tras el cambio de la capa común: `CONSTITUCION.md`
  (topes de tamaño, `docs/CONTRACTS/` vs `docs/spec/`, alcance de `==`, §8 reescrita),
  `retrieval-metrics.md` (§4 admite y recomienda `holm`) y `eval-report.schema.json`. Idénticas
  byte a byte al original; el `diff` es un test.
- `docs/GOALS.yaml` reescrito para cumplir `docs/CONTRACTS/goals.schema.json` v1: umbrales
  estructurados `{operador, valor, unidad}` con `adicionales`, `clase` sustituido por `tipo` +
  `requiere` + `propuesta_admisible`, `pareja`/`condicionada_a` movidos a `nota`, y
  `hardware_referencia` declarado por las metas de latencia. Ningún umbral cambia de valor.
- Las decisiones transversales dejan de preguntarse aquí: viven en `_comun/PARA-SAMUEL-GLOBAL.md`
  como D-01..D-09. `docs/PARA-SAMUEL.md` las remite y renumera lo propio como Q-001..Q-013.

---

<!--
Plantilla de una fase cerrada. Copiar tal cual y rellenar.

## [fase-N] · AAAA-MM-DD · <nombre de la fase>

`make done MILESTONE=N` → exit 0.  Snapshot: `.snapshots/AAAA-MM-DD-faseN/`

### Números medidos
| Meta | Umbral | Valor | n | IC95 | Artefacto |
|---|---:|---:|---:|---|---|
| G-XXXX | >= 0,90 | 0,00 | 000 | [0,00 – 0,00] | evals/reports/... |

Entorno: hardware declarado · Python 3.12.x · determinista: si/no · index_version: ... ·
modelos {generador, juez, embeddings, reranker} con su digest · semilla: ...

### Añadido / Cambiado / Corregido / Eliminado
- ...

### Decisiones
- ADR-NNN · <título>

### Deuda declarada
- <TODO/FIXME que quedan, y por qué se aceptan> (tope: 10 en `src/`)
-->
