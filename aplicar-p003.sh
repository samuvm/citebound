#!/bin/bash
# P-003, aprobada. Baja G-RECALL5 a 0.79 y G-RECALL30 a 0.96, y regenera el candado.
# Solo Samuel puede ejecutarlo: el agente tiene GOALS.yaml y thresholds.lock en deny.
set -e
cd /Users/samuelviciana/Documents/day-300/citebound-01
sed -i '' -e '156s/valor: 0.80/valor: 0.79/' -e '175s/valor: 0.97/valor: 0.96/' docs/GOALS.yaml
sed -i '' '$ s/^\*\*Estado: PENDIENTE\*\*$/**Estado: APROBADA · 2026-08-20**/' docs/PARA-SAMUEL.md
shasum -a 256 docs/GOALS.yaml | cut -d' ' -f1 > thresholds.lock
echo "umbrales:"; sed -n '156p;175p' docs/GOALS.yaml
echo "candado: $(cat thresholds.lock)"
