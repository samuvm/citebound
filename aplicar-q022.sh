#!/bin/bash
# Q-022 · aplica lo que Samuel ratificó y regenera el candado.
#
# Toca docs/GOALS.yaml y thresholds.lock, que son ZONA ROJA: el agente no los edita.
# Por eso esto es un script que ejecutas tú, igual que aplicar-p003.sh.
#
#   Uso:  ./aplicar-q022.sh               solo la pareja de máquinas (ya ratificada)
#         ./aplicar-q022.sh --metas D     mueve a la fase 4 la pareja CITA-PRECISION+COBERTURA
#         ./aplicar-q022.sh --metas D+    mueve además la pareja ABST-FP+ABST-FN  <-- RECOMENDADO
#
# Por qué D+ y no D: G-ABST-FP (0,412 contra 0,05) está en PAREJA ATÓMICA con G-ABST-FN
# (R16), así que las dos bloquean juntas. Moviendo solo la primera pareja, la fase 3 sigue
# sin cerrar. Y las cuatro se arreglan con la misma palanca, que es de fase 4.
set -euo pipefail
cd "$(dirname "$0")"

python3 - "$@" <<'PY'
import re, sys, pathlib
g = pathlib.Path("docs/GOALS.yaml")
s = g.read_text(encoding="utf-8")

nuevo = """hardware_referencia: >
  PAREJA DE MAQUINAS, ratificada por Samuel el 2026-08-22 (Q-022). Los modelos NO
  corren en la maquina de desarrollo. (1) Desarrollo, retrieval, reordenador y API:
  MacBook Pro M4 Max, 36 GB unificados, 14 nucleos, macOS, por WiFi. (2) Modelos por
  Ollama: equipo local con RTX 3070 de 8 GB, por cable, alcanzable en la red local.
  Jitter de red medido entre las dos: mediana 11,3 ms, p95 97,1 ms sobre 40 peticiones.
  Condiciones de medida obligatorias (docs/RULES.md R11 y docs/PARA-SAMUEL.md Q-006):
  ambos equipos enchufados, sin throttling termico entre repeticiones, modelos
  residentes en el equipo remoto (OLLAMA_KEEP_ALIVE >= 10m y 100% en VRAM), ninguna
  otra carga de GPU en ninguna de las dos.
  Las metas de latencia -- G-TTFT, G-TTFS, G-COLD-CACHE -- SOLO significan algo con
  esta pareja. Las de calidad y los invariantes no dependen del hardware.
"""
viejo = re.search(r"^hardware_referencia: >\n(?:  .*\n)+", s, re.M)
assert viejo, "hardware_referencia no está con esa forma; no se toca nada"
s = s[: viejo.start()] + nuevo + s[viejo.end() :]
print("  · hardware_referencia -> pareja de maquinas")

eleccion = ""
if "--metas" in sys.argv:
    eleccion = sys.argv[sys.argv.index("--metas") + 1].upper()
    assert eleccion in ("D", "D+"), f"opcion desconocida: {eleccion}. Usa D o D+"
if eleccion:
    metas = ["G-CITA-PRECISION", "G-COBERTURA"]
    if eleccion == "D+":
        metas += ["G-ABST-FP", "G-ABST-FN"]
    n = 0
    for meta in metas:
        bloque = re.search(rf"^  - id: {re.escape(meta)}\n(?:    .*\n|\n(?=    ))+", s, re.M)
        assert bloque, f"no encuentro el bloque de {meta}"
        trozo = bloque.group(0)
        assert "bloqueante_desde_fase: 3" in trozo, f"{meta} ya no bloquea desde la 3"
        s = s.replace(trozo, trozo.replace("bloqueante_desde_fase: 3", "bloqueante_desde_fase: 4"), 1)
        n += 1
    print(f"  · {n} metas movidas a bloqueante_desde_fase: 4 (opcion {eleccion} de Q-022)")

g.write_text(s, encoding="utf-8")
PY

shasum -a 256 docs/GOALS.yaml | cut -d' ' -f1 > thresholds.lock
echo "  · thresholds.lock regenerado: $(cat thresholds.lock)"
echo
echo "Hecho. Dile al agente que continue; el correra 'make done MILESTONE=3'."
