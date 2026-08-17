"""`docs/img/recall-por-canal.svg` desde el informe medido, nunca a mano.

Un gráfico transcrito a mano es una copia más del número, y las copias se quedan viejas sin
que nada lo note — que es exactamente el fallo que este proyecto persigue en todas partes. Se
dibuja desde `evals/reports/retrieval-latest.json`, así que si el README enseña una barra que
no corresponde es porque nadie volvió a correr esto, y eso se ve en el `git diff`.

SVG a mano y no una librería de gráficos: son 60 líneas, no añade dependencia, y el resultado
es texto que se revisa en un diff.
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = ["barras", "main"]

RAIZ = Path(__file__).resolve().parents[1]
INFORME = RAIZ / "evals" / "reports" / "retrieval-latest.json"
DESTINO = RAIZ / "docs" / "img" / "recall-por-canal.svg"

ETIQUETAS = {
    "solo_vectorial": "Solo vectorial",
    "solo_lexico": "Solo léxico",
    "fusion": "Híbrido (RRF)",
    "fusion_y_reordenador": "Híbrido + reordenador",
}
UMBRAL = {"recall5": 0.90, "recall30": 0.97}

ANCHO, FILA, IZQUIERDA, BARRA = 900, 34, 210, 560


def barras(por_canal: dict[str, dict[str, float]], n: int, indice: str) -> str:
    """El SVG entero como cadena. Sin estado y sin disco: así tiene un test de verdad."""
    canales = [c for c in ETIQUETAS if c in por_canal]
    alto = 96 + len(canales) * FILA * 2 + 40
    p: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {alto}" '
        f'width="{ANCHO}" height="{alto}" font-family="ui-sans-serif, -apple-system, '
        '\'Segoe UI\', Roboto, Helvetica, Arial, sans-serif" role="img" '
        'aria-label="Recall por canal, medido sobre el golden set">',
        f'<rect width="{ANCHO}" height="{alto}" fill="#fbfbfa"/>',
        '<text x="24" y="34" font-size="17" font-weight="600" fill="#2b2a26">'
        "Recall por canal · el artículo correcto entre los k recuperados</text>",
        f'<text x="24" y="56" font-size="12" fill="#8a8578">{n} preguntas del golden set v2 · '
        f"índice {indice} · make eval-retrieval</text>",
    ]
    y = 88
    for canal in canales:
        p.append(
            f'<text x="{IZQUIERDA - 14}" y="{y + 26}" font-size="13" fill="#2b2a26" '
            f'text-anchor="end">{ETIQUETAS[canal]}</text>'
        )
        for k, tono in (("recall5", "#5b7a9a"), ("recall30", "#9ab0c2")):
            valor = por_canal[canal].get(k)
            if valor is None:
                continue
            ancho = max(1.0, BARRA * valor)
            pasa = valor >= UMBRAL[k]
            p += [
                f'<rect x="{IZQUIERDA}" y="{y}" width="{BARRA}" height="18" rx="3" '
                'fill="#eeece6"/>',
                f'<rect x="{IZQUIERDA}" y="{y}" width="{ancho:.1f}" height="18" rx="3" '
                f'fill="{tono}"/>',
                f'<text x="{IZQUIERDA + BARRA + 12}" y="{y + 14}" font-size="13" '
                f'fill="{"#3f5738" if pasa else "#2b2a26"}" '
                f'font-weight="{"600" if pasa else "400"}" '
                f'font-family="ui-monospace, SFMono-Regular, Menlo, monospace">'
                f"{valor:.3f}".replace(".", ",")
                + ("  ✓" if pasa else "")
                + "</text>",
                f'<text x="{IZQUIERDA + 8}" y="{y + 14}" font-size="11" fill="#fff">'
                f"@{k.removeprefix('recall')}</text>",
            ]
            # La línea del umbral, dibujada sobre la barra: enseña la distancia que falta en
            # vez de obligar a compararla con un número de la leyenda.
            x = IZQUIERDA + BARRA * UMBRAL[k]
            p.append(
                f'<line x1="{x:.1f}" y1="{y - 2}" x2="{x:.1f}" y2="{y + 20}" '
                'stroke="#b4553f" stroke-width="1.5" stroke-dasharray="3 2"/>'
            )
            y += FILA
        y += 6

    p += [
        f'<text x="{IZQUIERDA}" y="{alto - 18}" font-size="11" fill="#8a8578">'
        "La línea roja es el umbral que exige el gate: 0,90 en @5 y 0,97 en @30. "
        "Ninguna barra se dibuja a mano.</text>",
        "</svg>",
    ]
    return "\n".join(p) + "\n"


def main() -> int:
    if not INFORME.is_file():
        print(f"no existe {INFORME.relative_to(RAIZ)}: corre `make eval-retrieval` antes")
        return 1
    datos = json.loads(INFORME.read_text(encoding="utf-8"))
    if "por_canal" not in datos:
        print("el informe no trae `por_canal`: es de antes de que se midiera. Vuelve a correrlo")
        return 1
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(
        barras(datos["por_canal"], int(datos["n_casos"]), str(datos["index_version"])),
        encoding="utf-8",
    )
    print(f"{DESTINO.relative_to(RAIZ)} desde {INFORME.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
