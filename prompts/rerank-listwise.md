---
id: rerank-listwise
version: 2
modelo_destino: qwen3.5:4b-mlx
temperatura: 0.0
cambios: |
  v1 · ordenación completa de los 30 candidatos, numerados. recall@5 = 0,856.
  v2 · etiquetas de dos letras y se piden exactamente 5. recall@5 = 0,852.
       Los dos cambios salen de leer lo que el modelo contestaba, no de tunear:
       nombraba 2 o 3 de los 30 y paraba, y confundía el número del candidato con
       el del artículo (en gs-0199 contestó "108,75,24"). No mejora el recall y se
       queda igual, porque arregla dos defectos reales.
nota: |
  NO ES EL REORDENADOR QUE SE SIRVE. Q-020 (A) lo sustituyó por un cross-encoder en
  proceso: 0,801 en 400 ms contra 0,852 en 4.600 ms, y además determinista. Este
  prompt se conserva porque comparar exige poder repetir las dos medidas, y se
  activa con CITEBOUND_RERANK_LLM=1. Detalle en docs/adr/024.
---
Pregunta: {pregunta}

Artículos candidatos:
{bloques}

De los candidatos anteriores, elige los {pedidos} MÁS relevantes, del más al menos relevante.

Relevante significa: el artículo que TIPIFICA la conducta por la que se pregunta, no el que
solo la menciona de pasada ni el que regula algo parecido.

Responde ÚNICAMENTE con {pedidos} etiquetas separadas por comas, así: {ejemplo}
Nada más: ni el número del artículo, ni explicación.
