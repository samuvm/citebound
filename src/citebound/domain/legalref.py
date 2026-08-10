"""Stable legal reference — the unit of truth of the whole project.

Every metric is anchored here and never on `chunk_id` (RULES R1,
`docs/CONTRACTS/retrieval-metrics.md` §1): the golden set, `recall@k`, citation
precision and the verifier all compare sets of `LegalRef`. That is what lets the
chunker, the embedding model and the reranker change without invalidating the
190 hand-reviewed cases of the golden set.

Canonical text form, identical to the `legal_ref` generated column of
`docs/CONTRACTS/chunks-ddl.sql`::

    norma[#art<designador>[.<apartado>]]
    RD-1428/2003
    RD-1428/2003#art34
    RD-1428/2003#art34.1
    RD-1428/2003#art65.5.c

Three decisions worth stating, because they are not obvious and they come from the
frozen corpus rather than from taste (ADR-001):

**The apartado is everything after the first dot.** The BOE XML does not mark it at
all — it arrives as a `"1. "` prefix inside `<p class="parrafo">` — and the contract
writes compound apartados as ``2.a``. Splitting on the *first* dot is what makes
``art65.5.c`` mean article 65, apartado ``5.c`` instead of something ambiguous.

**Two numbering spaces live in one document.** `BOE-A-2003-23514` is a Royal Decree
holding a single ``Artículo único`` plus an annexed Reglamento numbering its own
articles 1..N. This type numbers the Reglamento's; the Decree's own article is the
non-numeric designator ``unico``, and disposiciones and anexos are likewise
non-numeric (``ddunica``, ``dfprimera``, ``anexoi``), so they can never collide with
an article number.

**One document, three numbering spaces.** `RD-1428/2003` holds the Royal Decree's own
preceptos, the annexed Reglamento, and an articulado inside each ANEXO — and all three
restart at 1. The Reglamento is the default and takes no prefix, because it is what the
contract's own example cites; the other two are prefixed by their container
(``rd-unico``, ``anexoi-1``). Without that, 47 references of the frozen corpus collide.
See ADR-020.

**A `LegalRef` is always canonical.** The constructor validates and rejects; it does
not repair. Use `parse` when the text comes from outside — a prompt, a CSV, a
database row — and construct directly only with values you already know are clean.
The article designator is lowercase because ``ART34``, ``Art.34`` and ``art34`` must
be the same reference; the norma keeps its case because it is an official identifier
issued by the BOE, not a token we mint.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "LegalRef",
    "LegalRefError",
    "MatchLevel",
    "format_ref",
    "matches",
    "normalize",
    "parse",
    "try_parse",
]

# Unicode dashes that NFKC leaves alone — U+2011 in particular survives normalisation,
# and it is the one that arrives from copy-pasted PDFs. Written as escapes rather than
# as the literal glyphs: seven near-identical dashes in a row are unreadable in source,
# and `ruff` flags them as ambiguous with good reason. This keeps RUF001 on everywhere
# instead of silencing it, which matters because `G-INJECT` tests homoglyph attacks.
_DASHES = re.compile(
    "["
    "\u2010"  # HYPHEN
    "\u2011"  # NON-BREAKING HYPHEN
    "\u2012"  # FIGURE DASH
    "\u2013"  # EN DASH
    "\u2014"  # EM DASH
    "\u2015"  # HORIZONTAL BAR
    "\u2212"  # MINUS SIGN
    "]"
)

# Alternation order matters: the long spellings are tried before the bare marker, so
# "articulo34" does not degrade into "iculo34". The optional dot absorbs "Art.34"
# without eating the dot that separates article from apartado in "art34.1".
_ART_MARKER = re.compile(r"^(?:art[íi]culo|art)\.?")

_WS = re.compile(r"\s+")

# Deliberately strict. A permissive norma would let a chunk id parse as a legal
# reference, which is exactly what R1 and `scripts/check_no_chunk_ids.py` exist to
# prevent. Widening it for a norm that does not fit this shape is a contract change
# and needs an ADR, because `legal_ref` is a shared column.
_NORMA = re.compile(r"^[A-Za-z]+-\d+/\d{4}$")

# A hyphen JOINS segments and never dangles. One document holds three numbering spaces
# that all restart at 1 — the Royal Decree's own preceptos, the annexed Reglamento, and
# the articulado inside each ANEXO — and without a container prefix 47 references of the
# frozen corpus collide. That is measured, not feared: `recall@k` is a set operation over
# references, so a collision counts two different articles as one. See ADR-020.
_DESIGNADOR = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_APARTADO = re.compile(r"^[a-z0-9]+(?:\.[a-z0-9]+)*$")


class LegalRefError(ValueError):
    """A string that does not denote a resolvable legal reference."""


class MatchLevel(StrEnum):
    """How precise a comparison between two references is.

    Ordered from coarse to fine. Agreement at a finer level always implies agreement
    at every coarser one; the converse does not hold, and that asymmetry is what
    `retrieval-metrics.md` §2 rests on: citing ``art21`` when the golden set says
    ``art21.1`` is a failure, not a partial credit.
    """

    NORMA = "norma"
    ARTICULO = "articulo"
    APARTADO = "apartado"


@dataclass(frozen=True, slots=True)
class LegalRef:
    """`norma#artNN.apartado` — never a `chunk_id` (RULES R1).

    Immutable and hashable, because `recall@k` is a set operation over references.
    Raises `LegalRefError` on anything that is not already canonical.
    """

    norma: str
    articulo: str | None = None
    apartado: str | None = None

    def __post_init__(self) -> None:
        if not _NORMA.match(self.norma):
            raise LegalRefError(f"norma no reconocida: {self.norma!r}")
        if self.apartado is not None and self.articulo is None:
            # `legal_ref` is built left to right; an apartado hanging off no article
            # would produce a reference that cannot be resolved against the corpus,
            # and `G-HALLUC` would be measuring against a broken set.
            raise LegalRefError(f"apartado {self.apartado!r} sin artículo")
        if self.articulo is not None and not _DESIGNADOR.match(self.articulo):
            raise LegalRefError(f"designador de artículo no canónico: {self.articulo!r}")
        if self.apartado is not None and not _APARTADO.match(self.apartado):
            raise LegalRefError(f"apartado no canónico: {self.apartado!r}")

    @property
    def level(self) -> MatchLevel:
        """How precise this reference is."""
        if self.apartado is not None:
            return MatchLevel.APARTADO
        if self.articulo is not None:
            return MatchLevel.ARTICULO
        return MatchLevel.NORMA

    def __str__(self) -> str:
        return format_ref(self)


def normalize(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = _DASHES.sub("-", text).strip()
    if not text:
        return ""

    # Whitespace around the two separators never carries meaning.
    text = re.sub(r"\s*#\s*", "#", text)
    text = re.sub(r"\s*\.\s*", ".", text)

    norma, sep, rest = text.partition("#")
    norma = _WS.sub("-", norma.strip())
    if not sep:
        return norma

    rest = rest.lower()
    marker = _ART_MARKER.match(rest)
    if marker is None:
        # No marker: leave it as it came so `parse` can refuse it. Inventing the
        # marker here would silently turn "#34" into a valid article reference.
        return f"{norma}#{_WS.sub('', rest)}"
    designador = _WS.sub("", rest[marker.end() :])
    return f"{norma}#art{designador}"


def parse(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if not text:
        raise LegalRefError("referencia vacía")
    if text.count("#") > 1:
        raise LegalRefError(f"más de una referencia en {raw!r}")

    norma, sep, rest = text.partition("#")
    if not _NORMA.match(norma):
        raise LegalRefError(f"norma no reconocida en {raw!r}: {norma!r}")
    if not sep:
        return LegalRef(norma)
    if not rest.startswith("art"):
        raise LegalRefError(f"falta el marcador de artículo en {raw!r}")

    designador = rest[len("art") :]
    if not designador:
        raise LegalRefError(f"marcador de artículo sin designador en {raw!r}")

    articulo, dot, apartado = designador.partition(".")
    if dot and not apartado:
        raise LegalRefError(f"apartado vacío en {raw!r}")
    if not articulo:
        raise LegalRefError(f"artículo vacío en {raw!r}")
    return LegalRef(norma, articulo, apartado or None)


def try_parse(raw: str) -> LegalRef | None:
    """`parse`, returning `None` instead of raising.

    For the hot paths that see untrusted text — resolving a `[[REF:n]]` marker,
    reading a golden-set row — where a malformed reference is an expected outcome
    and not an exceptional one.
    """
    try:
        return parse(raw)
    except LegalRefError:
        return None


def format_ref(ref: LegalRef) -> str:
    """A `LegalRef` back into its canonical text.

    Byte-identical to what `chunks-ddl.sql` computes for the `legal_ref` generated
    column, so a Python value and a database row are always the same string.
    """
    text = ref.norma
    if ref.articulo is not None:
        text += f"#art{ref.articulo}"
        if ref.apartado is not None:
            text += f".{ref.apartado}"
    return text


def matches(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
    """Do two references agree all the way down to `level`?

    Reflexive and symmetric. Agreement at `APARTADO` implies agreement at `ARTICULO`,
    which implies agreement at `NORMA`; **the converse never holds**. A reference that
    does not reach the requested level is a miss, not a match by default: asking for
    apartado precision from `RD-1428/2003#art34` returns `False`, which is what makes
    `G-CITA-PRECISION` refuse to reward a citation coarser than the golden set's.
    """
    if a.norma != b.norma:
        return False
    if level is MatchLevel.NORMA:
        return True

    if a.articulo is None or b.articulo is None or a.articulo != b.articulo:
        return False
    if level is MatchLevel.ARTICULO:
        return True

    if a.apartado is None or b.apartado is None:
        return False
    return a.apartado == b.apartado
