# ADR-002 · Python 3.12 porque MWAA no ofrece más, no porque lo pida la oferta

- **Fecha:** 2026-08-10
- **Fase:** 0
- **Estado:** **Aceptado**
- **Supersede a:** —

## Contexto

`docs/PROJECT.md` justifica Python 3.12 con «requisito de la oferta». Eso es transcripción, no
ingeniería, y en agosto de 2026 existen 3.13 y 3.14 — la propia máquina de desarrollo tiene
`python3` en **3.14.6** y `python3.12` en **3.12.4** (medido el 2026-08-10). Hace falta un motivo
que sobreviva a la pregunta «¿y por qué no 3.14?».

Hay dos, y ninguno es la oferta:

1. **Amazon MWAA solo ofrece Python 3.12**, atado a `apache-airflow==3.2.1` desde mayo de 2026
   (`docs/STACK.md` §4.1). El proyecto 04 promete «el mismo DAG en local y en MWAA». Si los cinco
   proyectos no comparten intérprete, esa promesa se rompe en el punto donde se cruzan.
2. **Uniformidad con las wheels de `torch`/MPS**, de las que depende el reranker en proceso (R8).
   Una minor por delante de las wheels significa compilar desde fuente en un portátil.

## Opciones consideradas

| Opción | Pros | Contras | Coste medido |
|---|---|---|---|
| **A · `requires-python = "==3.12.*"`** | Paridad real con MWAA · wheels precompiladas · uniforme en los cinco repos | Se renuncia a lo que traigan 3.13 y 3.14 | 0 |
| B · 3.14 aquí y 3.12 en el 04 | Lo último en el repo que se enseña | Dos intérpretes en la misma máquina, y la promesa del 04 pasa a ser falsa por un detalle que nadie ve venir | Desincroniza `_comun/STACK.md` |
| C · rango `>=3.12,<3.15` | Flexible | Un rango en `requires-python` es exactamente lo que hace que el repo deje de compilar dentro de seis meses (constitución §7.2) | 0 hoy, caro después |

## Decisión

**A**, con `==` exacto. `python3.12 --version` → `3.12.4` en la máquina de referencia, y el
`Makefile` falla con mensaje accionable si el intérprete no es 3.12.

La frase del README es «Python 3.12 porque MWAA no ofrece más», no «porque lo pide la oferta». Es
la misma versión y una respuesta distinta.

## Consecuencias

- **Se gana** que los cinco proyectos compartan intérprete y que el ADR se sostenga en una
  entrevista.
- **Se pierde** todo lo que traigan 3.13 y 3.14 durante la vida del proyecto.
- **Se vuelve difícil de cambiar** el día que MWAA suba: subir aquí sin subir en el 04 rompe la
  paridad. La salida es un evento consciente en `_comun/STACK.md` propagado a los cinco, no un
  cambio local.
- **Afecta a** `pyproject.toml :: requires-python` y a la regla `==` de la constitución §7.2.
