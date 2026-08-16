# Ensayo automático del golden set · 2026-08-15

**Qué fue.** Samuel pasó la cola entera de forma automática **a propósito**, para detectar
errores antes de arriesgar sus 10-16 horas. 304 casos en 31,5 minutos.

**No es el golden set.** Ningún caso de aquí entra en `v1.jsonl`: la regla dura nº 3 del
contrato exige revisión humana y esto no lo fue. Se conserva como evidencia de lo que
encontró y de cómo se corrigió.

## Qué encontró

| | |
|---|---|
| Referencias corregidas | 34 (23 distintas; 11 eran idénticas a la propuesta) |
| Descartes propuestos | 27 — **los 27 ya marcados en mis notas** |
| Puntos ciegos míos | arts. **97** y **108**, que nunca abrí |
| Afirmaciones falsas mías | 3 «no aparece en el corpus» que sí aparecían |
| Fallos de diseño de la cola | 1, y grave |

## Las tres afirmaciones falsas

Peores que equivocarse de artículo, porque las di por comprobadas:

- «El poste de socorro no aparece en el corpus» → está en el **97.3.d**, literal. No lo busqué.
- «El Reglamento no dice por qué carril se sale de una glorieta, buscado en todo el corpus» →
  lo dice el **art. 77**. Mi búsqueda exigía la palabra «glorieta» en el mismo párrafo y el 77
  dice «cualquier otra vía». La búsqueda era estrecha y publiqué su resultado como definitivo.
- El **art. 108** no lo abrí nunca: volqué el 109 y el 110 y me salté el que gobierna la
  jerarquía «señalización luminosa o, en su defecto, con el brazo». Seis correcciones van ahí.

## El fallo de diseño, que produjo un número al revés

En un caso a ciegas no se ve ninguna propuesta, así que la tecla `a` («ok») no tenía nada que
aceptar: **la única que registraba referencia era `e`**. Las 14 respuestas ciegas se guardaron
todas como «corregir», y **11 de ellas con una referencia idéntica a la propuesta**.

Contando la tecla salía un **22 %** de acuerdo. Comparando las referencias, que es la medida
real, es un **79 %**. Con la propuesta a la vista, 92 %. El anclaje existe y son **13 puntos**,
no 70.

Un número que se publica con esa diferencia no es un error de cálculo: es una conclusión al
revés. Corregido en `tecla_valida` y `registrar_ciego`, con sus tests.
