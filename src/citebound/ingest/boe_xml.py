"""Structural parser for the BOE consolidated XML.

Turns a consolidated document into `Precepto` values carrying a `LegalRef`. Four
things about the real format drive the whole design, and none of them is guessable
from the outside — they were measured on `corpus/raw/BOE-A-2003-23514.xml` on
2026-08-10 and are recorded in ADR-001 and `corpus/MANIFEST.yaml`:

**A block can hold several `<version>`, and the one in force is the LAST.** 78 of the
335 blocks do; one holds four. Reading the first would serve superseded wording for a
quarter of the corpus, and it would be invisible: the quote is real, the reference
resolves, `G-QUOTE-LIT` stays at 1,00 and `G-HALLUC` at 0. Literal and wrong is worse
than obviously wrong, because nothing flags it.

**The block id is not the designator.** `Artículo 14 bis` lives in `<bloque id="a1-3">`;
the BOE mints internal ids for inserted articles. The designator comes from the `titulo`
attribute or from nowhere.

**The apartado is not a node.** It arrives as a `"1. "` prefix inside
`<p class="parrafo">`, so the granularity `G-CITA-PRECISION` depends on is recovered
from the text by `split_apartados`.

**An `ANEXO` is a heading block that nevertheless holds text**, while `TÍTULO` and
`CAPÍTULO` are heading blocks that only place what follows. "Skip every encabezado"
would drop the sign catalogue; "keep every encabezado" would mint references for the
table of contents.
"""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET  # nosec B405 B314 — prólogo filtrado, ver _PELIGROSO
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

from citebound.domain.legalref import LegalRef, LegalRefError

__all__ = [
    "Apartado",
    "BoeXmlError",
    "Precepto",
    "PreceptoTipo",
    "parse_norma",
    "split_apartados",
]

# `^(\d+)\.\s` and nothing looser. "30 km/h" must not become apartado 30, and the
# whitespace is consumed so that the apartado text starts where the sentence does —
# a leading "1. " inside the text would make every quote that begins at the top of an
# apartado fail `G-QUOTE-LIT`.
_APARTADO = re.compile(r"^(\d+)\.\s")

_TIT_ARTICULO = re.compile(r"^articulo\s+(.+)$")
_TIT_DISPOSICION = re.compile(r"^disposicion\s+(adicional|derogatoria|final|transitoria)\s+(.+)$")
_TIT_ANEXO = re.compile(r"^anexo\s+(.+)$")
_DEROGADO = re.compile(r"\(derogad[oa]", re.IGNORECASE)

# `<p>` classes that are structure, not body text.
_NO_ES_CUERPO = frozenset(
    {"articulo", "anexo", "titulo_num", "titulo_tit", "capitulo_num", "capitulo_tit", "firma"}
)

# Entity expansion — the "billion laughs" — is the one XML attack `ElementTree` does not
# defend against, and both markers can only appear in the PROLOG, before the root
# element. So the whole prolog is scanned rather than a fixed prefix: a cheap guard that
# can be evaded is worse than none, because it buys false confidence.
#
# The corpus is frozen and sha256-verified before it reaches here (RULES R4), so this is
# belt and braces today. It is not decorative tomorrow: ingest is the layer that first
# touches bytes off the network, and this parser is the obvious thing to reuse.
#
# `defusedxml` would be the textbook answer and is deliberately NOT used: it is outside
# the dependency list Samuel approved in Q-011, and widening that list is his call, not
# the agent's. Declared as debt in `docs/JOURNAL.md` with the question attached.
_PELIGROSO = ("<!doctype", "<!entity")


class BoeXmlError(ValueError):
    """The document is not a consolidated BOE text this parser can read."""


class PreceptoTipo(StrEnum):
    """What kind of citable unit a block holds."""

    ARTICULO = "articulo"
    DISPOSICION = "disposicion"
    ANEXO = "anexo"


@dataclass(frozen=True, slots=True)
class Apartado:
    """One subdivision of a precepto.

    `numero` is `None` when the article does not number its paragraphs. Inventing a
    `1` there would mint `art34.1`, a reference that does not exist — exactly the
    hallucination `G-HALLUC` is built to make impossible.
    """

    numero: str | None
    texto: str


@dataclass(frozen=True, slots=True)
class Precepto:
    """A citable unit with its reference, its text and its place in the hierarchy."""

    ref: LegalRef
    tipo: PreceptoTipo
    # Cómo lo llama el BOE: "Artículo 3", "Disposición adicional primera", "ANEXO I".
    # El designador de la `ref` está canonizado y no se puede revertir a algo legible
    # (`daprimera` no vuelve a ser "Disposición adicional primera"), y el troceado lo
    # necesita para encabezar el chunk con algo que un humano — y un embedding — sepa leer.
    rotulo: str
    rubrica: str
    apartados: tuple[Apartado, ...]
    titulo: str | None
    capitulo: str | None
    seccion: str | None
    vigente: bool
    id_norma_version: str
    fecha_vigencia: str | None


def split_apartados(parrafos: Sequence[str]) -> tuple[Apartado, ...]:
    """Recover the apartado structure the BOE XML does not mark.

    A paragraph opening with `"N. "` starts a new apartado; anything else continues the
    one above it, joined with a newline. That is what keeps lettered items — which the
    contract writes as the compound apartado `2.a` — inside their parent instead of
    becoming references of their own.

    Regrouping only: the text is never rewritten, so the paragraphs can always be
    reconstructed from the result. `tests/property/test_boe_xml.py` proves it.
    """
    out: list[tuple[str | None, str]] = []
    for parrafo in parrafos:
        marca = _APARTADO.match(parrafo)
        if marca is not None:
            out.append((marca.group(1), parrafo[marca.end() :]))
        elif out:
            numero, texto = out[-1]
            out[-1] = (numero, f"{texto}\n{parrafo}")
        else:
            out.append((None, parrafo))
    return tuple(Apartado(numero, texto) for numero, texto in out)


def parse_norma(xml: str, norma: str) -> tuple[Precepto, ...]:
    """Every citable unit of a consolidated document, in document order.

    `norma` is passed in rather than inferred: the slug is what `corpus/MANIFEST.yaml`
    declares and what the `legal_ref` column is built from, and guessing it from the
    metadata would put a second, silently divergent source of truth in the pipeline.
    """
    try:
        LegalRef(norma)
    except LegalRefError as err:
        raise BoeXmlError(f"norma no reconocida: {norma!r}") from err

    texto = _raiz_texto(xml)
    preceptos: list[Precepto] = []
    titulo = capitulo = seccion = None
    # The document opens with the Royal Decree's own seven preceptos, before the
    # Reglamento it approves. See ADR-020 for why the container has to be tracked.
    contenedor = "rd"

    for bloque in texto.iter("bloque"):
        rotulo = (bloque.get("titulo") or "").strip()

        rango = _rango_de_encabezado(rotulo)
        if rango is not None:
            # A heading applies to everything after it until the next one of its rank,
            # and clears the ranks below.
            if rango == "titulo":
                titulo, capitulo, seccion = rotulo, None, None
                # A TÍTULO is a division of the Reglamento's body, so it brings the
                # parser back out of any annex. That is not hypothetical: TÍTULO VI,
                # added by RD 465/2025, sits PHYSICALLY AFTER the four anexos in the
                # file, and without this its articles would come out as `anexoii-…`.
                contenedor = ""
            elif rango == "capitulo":
                capitulo, seccion = rotulo, None
            else:
                seccion = rotulo
            continue

        precepto = _precepto(bloque, rotulo, norma, contenedor, titulo, capitulo, seccion)
        if precepto is not None:
            preceptos.append(precepto)

        siguiente = _siguiente_contenedor(contenedor, rotulo, bloque.get("tipo") or "")
        if siguiente != contenedor and siguiente.startswith("anexo"):
            # An annex opens its own space. Carrying TÍTULO VI into ANEXO II — which is
            # what the file order produces, since the annexes come after it — would
            # report a hierarchy the block does not belong to.
            titulo = capitulo = seccion = None
        contenedor = siguiente

    return _desambiguar(tuple(preceptos), norma)


# --------------------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------------------


def _raiz_texto(xml: str) -> ET.Element:
    if not xml.strip():
        raise BoeXmlError("documento vacío")
    prologo = xml.split("<bloque", 1)[0].split("<response", 1)[0].lower()
    if any(marca in prologo for marca in _PELIGROSO):
        raise BoeXmlError("el documento declara entidades o DTD y no se procesa")
    try:
        raiz = ET.fromstring(xml)  # noqa: S314  # nosec B314 — prólogo filtrado arriba
    except ET.ParseError as err:
        raise BoeXmlError(f"XML mal formado: {err}") from err
    texto = raiz.find(".//texto")
    if texto is None:
        raise BoeXmlError("el documento no trae <texto>: ¿es un consolidado del BOE?")
    return texto


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower().strip()


def _rango_de_encabezado(rotulo: str) -> str | None:
    """`TÍTULO`, `CAPÍTULO` and `SECCIÓN` place what follows; `ANEXO` does not."""
    plano = _sin_acentos(rotulo)
    for rango in ("titulo", "capitulo", "seccion"):
        if plano.startswith(rango + " ") or plano == rango:
            return rango
    return None


def _designador(rotulo: str) -> tuple[str, PreceptoTipo] | None:
    """Turn the `titulo` attribute into a canonical designator.

    Never the block id: `Artículo 14 bis` is `<bloque id="a1-3">`. Disposiciones and
    anexos get non-numeric designators (`daprimera`, `ddunica`, `anexoi`) so they can
    never collide with an article number.
    """
    plano = _sin_acentos(rotulo)

    articulo = _TIT_ARTICULO.match(plano)
    if articulo is not None:
        return re.sub(r"\s+", "", articulo.group(1)), PreceptoTipo.ARTICULO

    disposicion = _TIT_DISPOSICION.match(plano)
    if disposicion is not None:
        clase, ordinal = disposicion.group(1), re.sub(r"\s+", "", disposicion.group(2))
        return f"d{clase[0]}{ordinal}", PreceptoTipo.DISPOSICION

    anexo = _TIT_ANEXO.match(plano)
    if anexo is not None:
        return "anexo" + re.sub(r"\s+", "", anexo.group(1)), PreceptoTipo.ANEXO

    return None


def _ultima_version(bloque: ET.Element) -> ET.Element | None:
    """The wording in force. **The last one, never the first.**"""
    versiones = bloque.findall("version")
    return versiones[-1] if versiones else None


def _parrafos(version: ET.Element) -> Iterator[tuple[str, str]]:
    """Direct `<p>` children only, as `(clase, texto)`.

    Direct is load-bearing: the `<blockquote class="soloTexto">` that follows a
    `(Derogado)` marker is a sibling, so its paragraphs — editorial commentary about the
    repeal, not the norm — never reach the text simply by not being descended into.
    """
    for p in version.findall("p"):
        yield (p.get("class") or ""), "".join(p.itertext()).strip()


def _precepto(
    bloque: ET.Element,
    rotulo: str,
    norma: str,
    contenedor: str,
    titulo: str | None,
    capitulo: str | None,
    seccion: str | None,
) -> Precepto | None:
    designado = _designador(rotulo)
    if designado is None:
        return None  # preámbulo, firma, nota inicial: no son unidades citables
    designador, tipo = designado

    version = _ultima_version(bloque)
    if version is None:
        return None

    rubrica = ""
    cuerpo: list[str] = []
    for clase, texto in _parrafos(version):
        if clase in {"articulo", "anexo"}:
            rubrica = rubrica or _rubrica(texto, rotulo)
        elif clase not in _NO_ES_CUERPO and texto:
            cuerpo.append(texto)

    if not cuerpo:
        return None  # un bloque sin texto no se puede citar ni verificar

    return Precepto(
        ref=LegalRef(norma, _con_contenedor(designador, contenedor, tipo)),
        tipo=tipo,
        rotulo=rotulo,
        rubrica=rubrica,
        apartados=split_apartados(cuerpo),
        titulo=titulo,
        capitulo=capitulo,
        seccion=seccion,
        vigente=not any(_DEROGADO.search(t) for t in cuerpo),
        id_norma_version=version.get("id_norma") or "",
        fecha_vigencia=version.get("fecha_vigencia") or None,
    )


def _rubrica(cabecera: str, rotulo: str) -> str:
    """`"Artículo 3. Conductores."` → `"Conductores."`

    Kept out of the body on purpose: a quote that begins at the top of an article would
    otherwise have to include a heading the article does not carry at that position.
    """
    prefijo = f"{rotulo}."
    if cabecera.startswith(prefijo):
        return cabecera[len(prefijo) :].strip()
    return cabecera.strip()


def _siguiente_contenedor(actual: str, rotulo: str, tipo: str) -> str:
    """Which numbering space the blocks *after* this one belong to.

    Three spaces share one document and all restart at 1 (ADR-020). The Reglamento is
    the default and takes no prefix; the other two are prefixed by their container.

    The switch out of `rd` fires on the first heading that is not hierarchical — the
    block that announces the annexed Reglamento — and only while still in `rd`. Without
    that guard the numbered section headings inside ANEXO I (`1`, `2`, …, which are not
    TÍTULO/CAPÍTULO/SECCIÓN either) would throw the parser back to the body and give the
    sign catalogue's articles the references of the road rules.
    """
    if tipo != "encabezado":
        return actual
    designado = _designador(rotulo)
    if designado is not None and designado[1] is PreceptoTipo.ANEXO:
        return designado[0]
    if actual == "rd" and _rango_de_encabezado(rotulo) is None:
        return ""
    return actual


def _con_contenedor(designador: str, contenedor: str, tipo: PreceptoTipo) -> str:
    """Prefix the designator with the numbering space it belongs to.

    An ANEXO is the ROOT of its own space, so it never carries a prefix: `ANEXO II`
    reached while the parser is still inside ANEXO I would otherwise come out as
    `anexoi-anexoii`, which is not a reference to anything.
    """
    if tipo is PreceptoTipo.ANEXO or not contenedor:
        return designador
    return f"{contenedor}-{designador}"


def _desambiguar(preceptos: tuple[Precepto, ...], norma: str) -> tuple[Precepto, ...]:
    """Resolve designators that collide inside one container.

    The frozen corpus has eight: `TÍTULO VI`, added by RD 465/2025, restarts its
    articulado at 151 and lands on top of the existing 151-158 of `TÍTULO V`. That is a
    fact about the norm, not a parser bug — both articles are in force and both say
    "Artículo 151".

    Leaving it would be the quiet kind of damage: `recall@k` compares SETS of
    references (`retrieval-metrics.md` §2), so two different articles sharing one
    reference are counted as one, and a golden-set case citing `art151` would be
    ambiguous between road signs and urban traffic rules.

    The rule prefixes **both** members of a colliding pair with their TÍTULO — never
    just the second — so the outcome does not depend on reading order, and the other
    228 references of the corpus keep the plain form the contract's own example uses.
    """
    veces: dict[str, int] = {}
    for p in preceptos:
        veces[str(p.ref)] = veces.get(str(p.ref), 0) + 1
    if all(n == 1 for n in veces.values()):
        return preceptos

    resueltos: list[Precepto] = []
    for p in preceptos:
        if veces[str(p.ref)] == 1 or p.titulo is None:
            resueltos.append(p)
            continue
        marca = _sin_acentos(p.titulo).removeprefix("titulo").strip()
        designador = f"t{re.sub(r'[^a-z0-9]', '', marca)}-{p.ref.articulo}"
        resueltos.append(replace(p, ref=LegalRef(norma, designador, p.ref.apartado)))
    return tuple(resueltos)
