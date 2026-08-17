"""Montaje de `evals/golden/v1.jsonl` desde la revisión de Samuel · fase `1d`.

Convierte tres ficheros de trabajo —la cola, las propuestas del agente y los veredictos de
Samuel— en el **único artefacto que el resto del proyecto consume**. A partir de aquí, recall,
precisión de cita, alucinación y abstención se anclan en estas referencias y en ninguna otra.

Por eso lo importante de este script no es lo que junta, sino **lo que se niega a montar**:
un caso descartado no entra, un caso sin veredicto tampoco, y nada sale sin revisor y sin
fecha — que es la regla dura nº 3 del contrato: generación asistida por LLM sí, aprobación
automática no.

**El caso que más cuidado pide** es el negativo que resultó ser respondible. Seis de los 64
lo eran (alcohol, drogas, deber de auxilio) y cambian de bando aquí. Si entraran como
negativos, `G-ABST-FN` contaría como fallo cada vez que el sistema respondiera bien: la
métrica premiaría callarse justo donde hay que hablar.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

from citebound.evals.schema import CasoGolden, Dificultad, Provenance, Tipo

__all__ = ["dificultad_de", "escribir", "estratos", "main", "montar"]

RAIZ = Path(__file__).resolve().parents[1]
COLA = RAIZ / "evals" / "golden" / "cola" / "candidatos.jsonl"
VEREDICTOS = RAIZ / "evals" / "golden" / "cola" / "veredictos.jsonl"
PROPUESTAS = RAIZ / "evals" / "golden" / "propuestas"
VERSION = 2
DESTINO = RAIZ / "evals" / "golden" / f"v{VERSION}.jsonl"

# ADR-021: fuera del conjunto de evaluación, no del banco. Su enunciado no identifica el
# supuesto de hecho sin la imagen, así que ningún sistema puede responderlos y su presencia
# acota `G-RECALL30` por debajo de su umbral por una razón ajena al sistema.
SIN_TEXTO_SUFICIENTE = frozenset({"gs-0036", "gs-0061", "gs-0127"})
CHECKSUMS = RAIZ / "evals" / "golden" / "CHECKSUMS"
STRATA = RAIZ / "evals" / "golden" / "STRATA.md"

# Cortes de `pct_fallo` para derivar `dificultad`. El banco mide el porcentaje real de gente
# que falla cada pregunta sobre miles de intentos; su mediana es 10,1 y su p75 15,8, así que
# los cortes parten la distribución real en vez de repartir por intuición.
FACIL_HASTA = 6.0
DIFICIL_DESDE = 20.0


def dificultad_de(pct_fallo: float) -> Dificultad:
    """El contrato exige el campo `dificultad`, que es un juicio; el banco trae el dato.

    Se deriva del porcentaje de fallo real en vez de inventarlo, y los dos viajan juntos en
    el caso: el contrato se cumple y la medida se conserva.
    """
    if pct_fallo <= FACIL_HASTA:
        return Dificultad.FACIL
    if pct_fallo >= DIFICIL_DESDE:
        return Dificultad.DIFICIL
    return Dificultad.MEDIA


def montar(
    cola: Sequence[Mapping[str, object]],
    propuestas: Mapping[str, Mapping[str, object]],
    veredictos: Sequence[Mapping[str, object]],
    *,
    revisor: str,
    fecha: date | None = None,
) -> list[CasoGolden]:
    """Los casos que Samuel aprobó, y solo esos.

    El orden es el de la cola, que es estable: si bailara, el sha256 del conjunto cambiaría
    sin que cambiara ni un caso, y el sello dejaría de servir para verificar nada.
    """
    if not revisor:
        raise ValueError("montar exige un revisor: ningún caso entra sin revisión humana")
    dictamen = {str(v["id"]): v for v in veredictos}

    casos: list[CasoGolden] = []
    for bruto in sorted(cola, key=lambda c: str(c["id"])):
        ident = str(bruto["id"])
        veredicto = dictamen.get(ident)
        if veredicto is None or veredicto["veredicto"] in ("descartar", "saltar"):
            continue
        if ident in SIN_TEXTO_SUFICIENTE:
            continue

        propuesta = propuestas.get(ident, {})
        era_negativo = bruto["tipo"] == "negativo"
        # En un negativo la referencia vive en `responde`, y solo existe si la revisión
        # concluyó que el corpus SÍ contesta. Ese caso deja de ser negativo aquí.
        del_agente = propuesta.get("responde") if era_negativo else propuesta.get("ref")
        ref = veredicto.get("ref") or del_agente
        es_positivo = bool(ref) if era_negativo else True

        casos.append(
            CasoGolden(
                id=ident,
                version=VERSION,
                pregunta=str(bruto["pregunta"]),
                respuesta_referencia=str(bruto["respuesta_correcta"]) if es_positivo else None,
                refs=[str(ref)] if es_positivo and ref else [],
                materia=str(bruto["tema"]),
                dificultad=dificultad_de(float(bruto["pct_fallo"])),  # type: ignore[arg-type]
                pct_fallo=float(bruto["pct_fallo"]),  # type: ignore[arg-type]
                tipo=Tipo.POSITIVO if es_positivo else Tipo.NEGATIVO,
                provenance=Provenance.LLM_GENERADO_REVISADO_HUMANO,
                revisado_por=revisor,
                revisado_en=fecha or date.today(),
                notas=str(propuesta.get("nota", "")),
            )
        )
    return casos


def escribir(casos: Sequence[CasoGolden], destino: Path) -> str:
    """Escribe el JSONL y devuelve el sha256 **del fichero**, no de la lista en memoria.

    La diferencia importa: el sello existe para que un tercero verifique lo que hay en disco.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8") as fichero:
        for caso in casos:
            fichero.write(caso.model_dump_json() + "\n")
    return hashlib.sha256(destino.read_bytes()).hexdigest()


def estratos(casos: Sequence[CasoGolden]) -> dict[str, object]:
    """El desglose que el gate va a mirar y que el README publica."""
    positivos = [c for c in casos if c.tipo is Tipo.POSITIVO]
    negativos = [c for c in casos if c.tipo is Tipo.NEGATIVO]
    por_materia = Counter(c.materia for c in positivos)
    return {
        "n": len(casos),
        "positivos": len(positivos),
        "negativos": len(negativos),
        "fraccion_negativos": len(negativos) / len(casos) if casos else 0.0,
        "por_materia": dict(sorted(por_materia.items())),
        "materias_con_20_o_mas": sum(1 for n in por_materia.values() if n >= 20),
        "por_dificultad": dict(sorted(Counter(c.dificultad.value for c in casos).items())),
    }


def _leer(ruta: Path) -> list[dict[str, object]]:
    return [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines() if x.strip()]


def main() -> int:
    if not VEREDICTOS.is_file():
        print(f"no existe {VEREDICTOS.relative_to(RAIZ)}: la cola no se ha revisado todavía")
        return 1

    propuestas: dict[str, Mapping[str, object]] = {}
    for fichero in sorted(PROPUESTAS.glob("*.json")):
        for clave, valor in json.loads(fichero.read_text(encoding="utf-8")).items():
            if not clave.startswith("_"):
                propuestas[clave] = valor

    casos = montar(_leer(COLA), propuestas, _leer(VEREDICTOS), revisor="samuel")
    sello = escribir(casos, DESTINO)
    desglose = estratos(casos)

    CHECKSUMS.write_text(f"{sello}  v{VERSION}.jsonl\n", encoding="utf-8")
    STRATA.write_text(
        f"# Estratos de `evals/golden/v{VERSION}.jsonl`\n\n"
        "Generado por `make golden-build`. Procedencia de la revisión en\n"
        "`evals/golden/cola/PROCEDENCIA.md`.\n\n"
        f"- **{desglose['n']} casos** · {desglose['positivos']} positivos · "
        f"{desglose['negativos']} negativos ({desglose['fraccion_negativos']:.1%})\n"
        f"- **{desglose['materias_con_20_o_mas']} materias** con 20 casos o más\n"
        f"- sha256 `{sello}`\n\n"
        "## Por materia (positivos)\n\n"
        + "".join(f"- {m}: {n}\n" for m, n in desglose["por_materia"].items())  # type: ignore[union-attr]
        + "\n## Por dificultad\n\n"
        + "".join(f"- {d}: {n}\n" for d, n in desglose["por_dificultad"].items())  # type: ignore[union-attr]
        + "\nLa dificultad se deriva de `pct_fallo`, el porcentaje real de personas que falla\n"
        "cada pregunta en el banco de origen. El contrato pide la etiqueta; el banco da el dato.\n",
        encoding="utf-8",
    )

    print(f"{desglose['n']} casos escritos en {DESTINO.relative_to(RAIZ)}")
    print(f"  {desglose['positivos']} positivos · {desglose['negativos']} negativos")
    print(f"  {desglose['materias_con_20_o_mas']} materias con 20 casos o más")
    print(f"  sha256 {sello}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
