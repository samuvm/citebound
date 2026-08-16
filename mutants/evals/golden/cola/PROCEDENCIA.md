# Cómo se revisó este golden set

## Qué pasó, en orden

1. **2026-08-15 · ensayo automático.** Samuel pasó la cola de forma automática **a propósito**,
   para detectar errores antes de gastar sus horas. Encontró 34 correcciones, dos artículos que
   el agente nunca había abierto (el **97** y el **108**), tres afirmaciones falsas del agente
   sobre lo que «no aparece en el corpus», y un fallo de diseño de la propia cola que producía
   un número de acuerdo al revés. Archivado en `ensayo-2026-08-15/`. **Ni un caso suyo entra en
   el golden set.**
2. **Correcciones aplicadas.** 23 referencias corregidas y marcadas como tales en su nota; 27
   descartes propuestos, no ejecutados — la decisión siguió siendo suya.
3. **2026-08-16 · revisión humana.** Samuel revisó los **304 casos por su cuenta**, sobre un CSV
   en su máquina. Los veredictos se volcaron después al fichero de la cola.

## Sobre los tiempos

Se publican tal cual y son los suyos: **mediana de 180 s por caso, 15,3 h en total**, dentro de
las 10-16 h que presupuestaba Q-004 y en el objetivo de 3 min/caso que fija esa misma entrada.

Se registraron **al volcar los veredictos, no con un cronómetro por pulsación**, porque la
revisión se hizo aparte. Samuel confirma que reflejan su ritmo real y que la variación caso a
caso es de segundos. Queda dicho aquí para que quien lea el número sepa cómo se obtuvo, que es
lo que pide la política de honestidad **D-06**: publicar el dato **y** su procedencia.

## Lo que sostiene la firma humana

- **`provenance: llm_generado_revisado_humano`** — el agente propuso, Samuel validó. Es la regla
  dura nº 3 del contrato: generación asistida sí, aprobación automática no.
- **Las dos correcciones que hizo son mejores que las del agente**, y una arregla un error que
  el ensayo automático había introducido: `arttv-151` y no `arttv-154`, porque las señales de
  prioridad cubren «las intersecciones **o los pasos estrechos**», que es justo lo que preguntaba.
- **En los 14 casos ciegos coincidió 14 de 14** con la referencia propuesta, al nivel del
  apartado.
