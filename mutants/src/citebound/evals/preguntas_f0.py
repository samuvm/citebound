"""Las tres preguntas fijas del humo de la fase 0.

Viven en el paquete y no en un script porque las usan tres sitios —`make smoke-f0`,
`make eval` y la grabación de embeddings— y tres copias de la misma lista es la forma
más barata de que un día midan cosas distintas creyendo que miden la misma.
"""

from __future__ import annotations

PREGUNTAS: tuple[str, ...] = (
    "¿Se puede adelantar en un cambio de rasante sin visibilidad?",
    "¿Con qué diligencia hay que conducir?",
    "¿Cómo se computan los carriles de una calzada?",
)
