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


from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated, MutantDict


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
mutants_x_normalize__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_normalize__mutmut)
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


def x_normalize__mutmut_orig(raw: str) -> str:
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


def x_normalize__mutmut_1(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = None
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


def x_normalize__mutmut_2(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize(None, raw)
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


def x_normalize__mutmut_3(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize("NFKC", None)
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


def x_normalize__mutmut_4(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize(raw)
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


def x_normalize__mutmut_5(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize("NFKC", )
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


def x_normalize__mutmut_6(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize("XXNFKCXX", raw)
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


def x_normalize__mutmut_7(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize("nfkc", raw)
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


def x_normalize__mutmut_8(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = None
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


def x_normalize__mutmut_9(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = _DASHES.sub(None, text).strip()
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


def x_normalize__mutmut_10(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = _DASHES.sub("-", None).strip()
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


def x_normalize__mutmut_11(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = _DASHES.sub(text).strip()
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


def x_normalize__mutmut_12(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = _DASHES.sub("-", ).strip()
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


def x_normalize__mutmut_13(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = _DASHES.sub("XX-XX", text).strip()
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


def x_normalize__mutmut_14(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = _DASHES.sub("-", text).strip()
    if text:
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


def x_normalize__mutmut_15(raw: str) -> str:
    """Fold every accepted spelling of a reference onto its canonical text.

    Pure text in, pure text out: this does **not** validate. `"RD-1428/2003#34"`
    normalizes to itself, marker and all, and it is `parse` that rejects it. Keeping
    the two apart is what makes the property ``format(parse(s)) == normalize(s)``
    say something instead of being a tautology.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = _DASHES.sub("-", text).strip()
    if not text:
        return "XXXX"

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


def x_normalize__mutmut_16(raw: str) -> str:
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
    text = None
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


def x_normalize__mutmut_17(raw: str) -> str:
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
    text = re.sub(None, "#", text)
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


def x_normalize__mutmut_18(raw: str) -> str:
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
    text = re.sub(r"\s*#\s*", None, text)
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


def x_normalize__mutmut_19(raw: str) -> str:
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
    text = re.sub(r"\s*#\s*", "#", None)
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


def x_normalize__mutmut_20(raw: str) -> str:
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
    text = re.sub("#", text)
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


def x_normalize__mutmut_21(raw: str) -> str:
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
    text = re.sub(r"\s*#\s*", text)
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


def x_normalize__mutmut_22(raw: str) -> str:
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
    text = re.sub(r"\s*#\s*", "#", )
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


def x_normalize__mutmut_23(raw: str) -> str:
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
    text = re.sub(r"XX\s*#\s*XX", "#", text)
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


def x_normalize__mutmut_24(raw: str) -> str:
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
    text = re.sub(r"\s*#\s*", "XX#XX", text)
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


def x_normalize__mutmut_25(raw: str) -> str:
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
    text = None

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


def x_normalize__mutmut_26(raw: str) -> str:
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
    text = re.sub(None, ".", text)

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


def x_normalize__mutmut_27(raw: str) -> str:
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
    text = re.sub(r"\s*\.\s*", None, text)

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


def x_normalize__mutmut_28(raw: str) -> str:
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
    text = re.sub(r"\s*\.\s*", ".", None)

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


def x_normalize__mutmut_29(raw: str) -> str:
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
    text = re.sub(".", text)

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


def x_normalize__mutmut_30(raw: str) -> str:
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
    text = re.sub(r"\s*\.\s*", text)

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


def x_normalize__mutmut_31(raw: str) -> str:
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
    text = re.sub(r"\s*\.\s*", ".", )

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


def x_normalize__mutmut_32(raw: str) -> str:
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
    text = re.sub(r"XX\s*\.\s*XX", ".", text)

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


def x_normalize__mutmut_33(raw: str) -> str:
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
    text = re.sub(r"\s*\.\s*", "XX.XX", text)

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


def x_normalize__mutmut_34(raw: str) -> str:
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

    norma, sep, rest = None
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


def x_normalize__mutmut_35(raw: str) -> str:
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

    norma, sep, rest = text.partition(None)
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


def x_normalize__mutmut_36(raw: str) -> str:
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

    norma, sep, rest = text.rpartition("#")
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


def x_normalize__mutmut_37(raw: str) -> str:
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

    norma, sep, rest = text.partition("XX#XX")
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


def x_normalize__mutmut_38(raw: str) -> str:
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
    norma = None
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


def x_normalize__mutmut_39(raw: str) -> str:
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
    norma = _WS.sub(None, norma.strip())
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


def x_normalize__mutmut_40(raw: str) -> str:
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
    norma = _WS.sub("-", None)
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


def x_normalize__mutmut_41(raw: str) -> str:
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
    norma = _WS.sub(norma.strip())
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


def x_normalize__mutmut_42(raw: str) -> str:
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
    norma = _WS.sub("-", )
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


def x_normalize__mutmut_43(raw: str) -> str:
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
    norma = _WS.sub("XX-XX", norma.strip())
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


def x_normalize__mutmut_44(raw: str) -> str:
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
    if sep:
        return norma

    rest = rest.lower()
    marker = _ART_MARKER.match(rest)
    if marker is None:
        # No marker: leave it as it came so `parse` can refuse it. Inventing the
        # marker here would silently turn "#34" into a valid article reference.
        return f"{norma}#{_WS.sub('', rest)}"
    designador = _WS.sub("", rest[marker.end() :])
    return f"{norma}#art{designador}"


def x_normalize__mutmut_45(raw: str) -> str:
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

    rest = None
    marker = _ART_MARKER.match(rest)
    if marker is None:
        # No marker: leave it as it came so `parse` can refuse it. Inventing the
        # marker here would silently turn "#34" into a valid article reference.
        return f"{norma}#{_WS.sub('', rest)}"
    designador = _WS.sub("", rest[marker.end() :])
    return f"{norma}#art{designador}"


def x_normalize__mutmut_46(raw: str) -> str:
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

    rest = rest.upper()
    marker = _ART_MARKER.match(rest)
    if marker is None:
        # No marker: leave it as it came so `parse` can refuse it. Inventing the
        # marker here would silently turn "#34" into a valid article reference.
        return f"{norma}#{_WS.sub('', rest)}"
    designador = _WS.sub("", rest[marker.end() :])
    return f"{norma}#art{designador}"


def x_normalize__mutmut_47(raw: str) -> str:
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
    marker = None
    if marker is None:
        # No marker: leave it as it came so `parse` can refuse it. Inventing the
        # marker here would silently turn "#34" into a valid article reference.
        return f"{norma}#{_WS.sub('', rest)}"
    designador = _WS.sub("", rest[marker.end() :])
    return f"{norma}#art{designador}"


def x_normalize__mutmut_48(raw: str) -> str:
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
    marker = _ART_MARKER.match(None)
    if marker is None:
        # No marker: leave it as it came so `parse` can refuse it. Inventing the
        # marker here would silently turn "#34" into a valid article reference.
        return f"{norma}#{_WS.sub('', rest)}"
    designador = _WS.sub("", rest[marker.end() :])
    return f"{norma}#art{designador}"


def x_normalize__mutmut_49(raw: str) -> str:
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
    if marker is not None:
        # No marker: leave it as it came so `parse` can refuse it. Inventing the
        # marker here would silently turn "#34" into a valid article reference.
        return f"{norma}#{_WS.sub('', rest)}"
    designador = _WS.sub("", rest[marker.end() :])
    return f"{norma}#art{designador}"


def x_normalize__mutmut_50(raw: str) -> str:
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
        return f"{norma}#{_WS.sub(None, rest)}"
    designador = _WS.sub("", rest[marker.end() :])
    return f"{norma}#art{designador}"


def x_normalize__mutmut_51(raw: str) -> str:
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
        return f"{norma}#{_WS.sub('', None)}"
    designador = _WS.sub("", rest[marker.end() :])
    return f"{norma}#art{designador}"


def x_normalize__mutmut_52(raw: str) -> str:
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
        return f"{norma}#{_WS.sub(rest)}"
    designador = _WS.sub("", rest[marker.end() :])
    return f"{norma}#art{designador}"


def x_normalize__mutmut_53(raw: str) -> str:
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
        return f"{norma}#{_WS.sub('', )}"
    designador = _WS.sub("", rest[marker.end() :])
    return f"{norma}#art{designador}"


def x_normalize__mutmut_54(raw: str) -> str:
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
        return f"{norma}#{_WS.sub('XXXX', rest)}"
    designador = _WS.sub("", rest[marker.end() :])
    return f"{norma}#art{designador}"


def x_normalize__mutmut_55(raw: str) -> str:
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
    designador = None
    return f"{norma}#art{designador}"


def x_normalize__mutmut_56(raw: str) -> str:
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
    designador = _WS.sub(None, rest[marker.end() :])
    return f"{norma}#art{designador}"


def x_normalize__mutmut_57(raw: str) -> str:
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
    designador = _WS.sub("", None)
    return f"{norma}#art{designador}"


def x_normalize__mutmut_58(raw: str) -> str:
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
    designador = _WS.sub(rest[marker.end() :])
    return f"{norma}#art{designador}"


def x_normalize__mutmut_59(raw: str) -> str:
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
    designador = _WS.sub("", )
    return f"{norma}#art{designador}"


def x_normalize__mutmut_60(raw: str) -> str:
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
    designador = _WS.sub("XXXX", rest[marker.end() :])
    return f"{norma}#art{designador}"

mutants_x_normalize__mutmut['_mutmut_orig'] = x_normalize__mutmut_orig # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_1'] = x_normalize__mutmut_1 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_2'] = x_normalize__mutmut_2 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_3'] = x_normalize__mutmut_3 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_4'] = x_normalize__mutmut_4 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_5'] = x_normalize__mutmut_5 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_6'] = x_normalize__mutmut_6 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_7'] = x_normalize__mutmut_7 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_8'] = x_normalize__mutmut_8 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_9'] = x_normalize__mutmut_9 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_10'] = x_normalize__mutmut_10 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_11'] = x_normalize__mutmut_11 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_12'] = x_normalize__mutmut_12 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_13'] = x_normalize__mutmut_13 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_14'] = x_normalize__mutmut_14 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_15'] = x_normalize__mutmut_15 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_16'] = x_normalize__mutmut_16 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_17'] = x_normalize__mutmut_17 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_18'] = x_normalize__mutmut_18 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_19'] = x_normalize__mutmut_19 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_20'] = x_normalize__mutmut_20 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_21'] = x_normalize__mutmut_21 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_22'] = x_normalize__mutmut_22 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_23'] = x_normalize__mutmut_23 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_24'] = x_normalize__mutmut_24 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_25'] = x_normalize__mutmut_25 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_26'] = x_normalize__mutmut_26 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_27'] = x_normalize__mutmut_27 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_28'] = x_normalize__mutmut_28 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_29'] = x_normalize__mutmut_29 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_30'] = x_normalize__mutmut_30 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_31'] = x_normalize__mutmut_31 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_32'] = x_normalize__mutmut_32 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_33'] = x_normalize__mutmut_33 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_34'] = x_normalize__mutmut_34 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_35'] = x_normalize__mutmut_35 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_36'] = x_normalize__mutmut_36 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_37'] = x_normalize__mutmut_37 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_38'] = x_normalize__mutmut_38 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_39'] = x_normalize__mutmut_39 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_40'] = x_normalize__mutmut_40 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_41'] = x_normalize__mutmut_41 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_42'] = x_normalize__mutmut_42 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_43'] = x_normalize__mutmut_43 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_44'] = x_normalize__mutmut_44 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_45'] = x_normalize__mutmut_45 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_46'] = x_normalize__mutmut_46 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_47'] = x_normalize__mutmut_47 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_48'] = x_normalize__mutmut_48 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_49'] = x_normalize__mutmut_49 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_50'] = x_normalize__mutmut_50 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_51'] = x_normalize__mutmut_51 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_52'] = x_normalize__mutmut_52 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_53'] = x_normalize__mutmut_53 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_54'] = x_normalize__mutmut_54 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_55'] = x_normalize__mutmut_55 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_56'] = x_normalize__mutmut_56 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_57'] = x_normalize__mutmut_57 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_58'] = x_normalize__mutmut_58 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_59'] = x_normalize__mutmut_59 # type: ignore # mutmut generated
mutants_x_normalize__mutmut['x_normalize__mutmut_60'] = x_normalize__mutmut_60 # type: ignore # mutmut generated
mutants_x_parse__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_parse__mutmut)
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


def x_parse__mutmut_orig(raw: str) -> LegalRef:
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


def x_parse__mutmut_1(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = None
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


def x_parse__mutmut_2(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(None)
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


def x_parse__mutmut_3(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if text:
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


def x_parse__mutmut_4(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if not text:
        raise LegalRefError(None)
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


def x_parse__mutmut_5(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if not text:
        raise LegalRefError("XXreferencia vacíaXX")
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


def x_parse__mutmut_6(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if not text:
        raise LegalRefError("REFERENCIA VACÍA")
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


def x_parse__mutmut_7(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if not text:
        raise LegalRefError("referencia vacía")
    if text.count(None) > 1:
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


def x_parse__mutmut_8(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if not text:
        raise LegalRefError("referencia vacía")
    if text.count("XX#XX") > 1:
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


def x_parse__mutmut_9(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if not text:
        raise LegalRefError("referencia vacía")
    if text.count("#") >= 1:
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


def x_parse__mutmut_10(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if not text:
        raise LegalRefError("referencia vacía")
    if text.count("#") > 2:
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


def x_parse__mutmut_11(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if not text:
        raise LegalRefError("referencia vacía")
    if text.count("#") > 1:
        raise LegalRefError(None)

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


def x_parse__mutmut_12(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if not text:
        raise LegalRefError("referencia vacía")
    if text.count("#") > 1:
        raise LegalRefError(f"más de una referencia en {raw!r}")

    norma, sep, rest = None
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


def x_parse__mutmut_13(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if not text:
        raise LegalRefError("referencia vacía")
    if text.count("#") > 1:
        raise LegalRefError(f"más de una referencia en {raw!r}")

    norma, sep, rest = text.partition(None)
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


def x_parse__mutmut_14(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if not text:
        raise LegalRefError("referencia vacía")
    if text.count("#") > 1:
        raise LegalRefError(f"más de una referencia en {raw!r}")

    norma, sep, rest = text.rpartition("#")
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


def x_parse__mutmut_15(raw: str) -> LegalRef:
    """Canonical text — or anything `normalize` accepts — into a `LegalRef`.

    Raises `LegalRefError` rather than guessing. A reference that cannot be resolved
    against the corpus must never reach a citation.
    """
    text = normalize(raw)
    if not text:
        raise LegalRefError("referencia vacía")
    if text.count("#") > 1:
        raise LegalRefError(f"más de una referencia en {raw!r}")

    norma, sep, rest = text.partition("XX#XX")
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


def x_parse__mutmut_16(raw: str) -> LegalRef:
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
    if _NORMA.match(norma):
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


def x_parse__mutmut_17(raw: str) -> LegalRef:
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
    if not _NORMA.match(None):
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


def x_parse__mutmut_18(raw: str) -> LegalRef:
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
        raise LegalRefError(None)
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


def x_parse__mutmut_19(raw: str) -> LegalRef:
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
    if sep:
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


def x_parse__mutmut_20(raw: str) -> LegalRef:
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
        return LegalRef(None)
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


def x_parse__mutmut_21(raw: str) -> LegalRef:
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
    if rest.startswith("art"):
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


def x_parse__mutmut_22(raw: str) -> LegalRef:
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
    if not rest.startswith(None):
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


def x_parse__mutmut_23(raw: str) -> LegalRef:
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
    if not rest.startswith("XXartXX"):
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


def x_parse__mutmut_24(raw: str) -> LegalRef:
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
    if not rest.startswith("ART"):
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


def x_parse__mutmut_25(raw: str) -> LegalRef:
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
        raise LegalRefError(None)

    designador = rest[len("art") :]
    if not designador:
        raise LegalRefError(f"marcador de artículo sin designador en {raw!r}")

    articulo, dot, apartado = designador.partition(".")
    if dot and not apartado:
        raise LegalRefError(f"apartado vacío en {raw!r}")
    if not articulo:
        raise LegalRefError(f"artículo vacío en {raw!r}")
    return LegalRef(norma, articulo, apartado or None)


def x_parse__mutmut_26(raw: str) -> LegalRef:
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

    designador = None
    if not designador:
        raise LegalRefError(f"marcador de artículo sin designador en {raw!r}")

    articulo, dot, apartado = designador.partition(".")
    if dot and not apartado:
        raise LegalRefError(f"apartado vacío en {raw!r}")
    if not articulo:
        raise LegalRefError(f"artículo vacío en {raw!r}")
    return LegalRef(norma, articulo, apartado or None)


def x_parse__mutmut_27(raw: str) -> LegalRef:
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
    if designador:
        raise LegalRefError(f"marcador de artículo sin designador en {raw!r}")

    articulo, dot, apartado = designador.partition(".")
    if dot and not apartado:
        raise LegalRefError(f"apartado vacío en {raw!r}")
    if not articulo:
        raise LegalRefError(f"artículo vacío en {raw!r}")
    return LegalRef(norma, articulo, apartado or None)


def x_parse__mutmut_28(raw: str) -> LegalRef:
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
        raise LegalRefError(None)

    articulo, dot, apartado = designador.partition(".")
    if dot and not apartado:
        raise LegalRefError(f"apartado vacío en {raw!r}")
    if not articulo:
        raise LegalRefError(f"artículo vacío en {raw!r}")
    return LegalRef(norma, articulo, apartado or None)


def x_parse__mutmut_29(raw: str) -> LegalRef:
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

    articulo, dot, apartado = None
    if dot and not apartado:
        raise LegalRefError(f"apartado vacío en {raw!r}")
    if not articulo:
        raise LegalRefError(f"artículo vacío en {raw!r}")
    return LegalRef(norma, articulo, apartado or None)


def x_parse__mutmut_30(raw: str) -> LegalRef:
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

    articulo, dot, apartado = designador.partition(None)
    if dot and not apartado:
        raise LegalRefError(f"apartado vacío en {raw!r}")
    if not articulo:
        raise LegalRefError(f"artículo vacío en {raw!r}")
    return LegalRef(norma, articulo, apartado or None)


def x_parse__mutmut_31(raw: str) -> LegalRef:
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

    articulo, dot, apartado = designador.rpartition(".")
    if dot and not apartado:
        raise LegalRefError(f"apartado vacío en {raw!r}")
    if not articulo:
        raise LegalRefError(f"artículo vacío en {raw!r}")
    return LegalRef(norma, articulo, apartado or None)


def x_parse__mutmut_32(raw: str) -> LegalRef:
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

    articulo, dot, apartado = designador.partition("XX.XX")
    if dot and not apartado:
        raise LegalRefError(f"apartado vacío en {raw!r}")
    if not articulo:
        raise LegalRefError(f"artículo vacío en {raw!r}")
    return LegalRef(norma, articulo, apartado or None)


def x_parse__mutmut_33(raw: str) -> LegalRef:
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
    if dot or not apartado:
        raise LegalRefError(f"apartado vacío en {raw!r}")
    if not articulo:
        raise LegalRefError(f"artículo vacío en {raw!r}")
    return LegalRef(norma, articulo, apartado or None)


def x_parse__mutmut_34(raw: str) -> LegalRef:
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
    if dot and apartado:
        raise LegalRefError(f"apartado vacío en {raw!r}")
    if not articulo:
        raise LegalRefError(f"artículo vacío en {raw!r}")
    return LegalRef(norma, articulo, apartado or None)


def x_parse__mutmut_35(raw: str) -> LegalRef:
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
        raise LegalRefError(None)
    if not articulo:
        raise LegalRefError(f"artículo vacío en {raw!r}")
    return LegalRef(norma, articulo, apartado or None)


def x_parse__mutmut_36(raw: str) -> LegalRef:
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
    if articulo:
        raise LegalRefError(f"artículo vacío en {raw!r}")
    return LegalRef(norma, articulo, apartado or None)


def x_parse__mutmut_37(raw: str) -> LegalRef:
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
        raise LegalRefError(None)
    return LegalRef(norma, articulo, apartado or None)


def x_parse__mutmut_38(raw: str) -> LegalRef:
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
    return LegalRef(None, articulo, apartado or None)


def x_parse__mutmut_39(raw: str) -> LegalRef:
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
    return LegalRef(norma, None, apartado or None)


def x_parse__mutmut_40(raw: str) -> LegalRef:
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
    return LegalRef(norma, articulo, None)


def x_parse__mutmut_41(raw: str) -> LegalRef:
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
    return LegalRef(articulo, apartado or None)


def x_parse__mutmut_42(raw: str) -> LegalRef:
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
    return LegalRef(norma, apartado or None)


def x_parse__mutmut_43(raw: str) -> LegalRef:
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
    return LegalRef(norma, articulo, )


def x_parse__mutmut_44(raw: str) -> LegalRef:
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
    return LegalRef(norma, articulo, apartado and None)

mutants_x_parse__mutmut['_mutmut_orig'] = x_parse__mutmut_orig # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_1'] = x_parse__mutmut_1 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_2'] = x_parse__mutmut_2 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_3'] = x_parse__mutmut_3 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_4'] = x_parse__mutmut_4 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_5'] = x_parse__mutmut_5 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_6'] = x_parse__mutmut_6 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_7'] = x_parse__mutmut_7 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_8'] = x_parse__mutmut_8 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_9'] = x_parse__mutmut_9 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_10'] = x_parse__mutmut_10 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_11'] = x_parse__mutmut_11 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_12'] = x_parse__mutmut_12 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_13'] = x_parse__mutmut_13 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_14'] = x_parse__mutmut_14 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_15'] = x_parse__mutmut_15 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_16'] = x_parse__mutmut_16 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_17'] = x_parse__mutmut_17 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_18'] = x_parse__mutmut_18 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_19'] = x_parse__mutmut_19 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_20'] = x_parse__mutmut_20 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_21'] = x_parse__mutmut_21 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_22'] = x_parse__mutmut_22 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_23'] = x_parse__mutmut_23 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_24'] = x_parse__mutmut_24 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_25'] = x_parse__mutmut_25 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_26'] = x_parse__mutmut_26 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_27'] = x_parse__mutmut_27 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_28'] = x_parse__mutmut_28 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_29'] = x_parse__mutmut_29 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_30'] = x_parse__mutmut_30 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_31'] = x_parse__mutmut_31 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_32'] = x_parse__mutmut_32 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_33'] = x_parse__mutmut_33 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_34'] = x_parse__mutmut_34 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_35'] = x_parse__mutmut_35 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_36'] = x_parse__mutmut_36 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_37'] = x_parse__mutmut_37 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_38'] = x_parse__mutmut_38 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_39'] = x_parse__mutmut_39 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_40'] = x_parse__mutmut_40 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_41'] = x_parse__mutmut_41 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_42'] = x_parse__mutmut_42 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_43'] = x_parse__mutmut_43 # type: ignore # mutmut generated
mutants_x_parse__mutmut['x_parse__mutmut_44'] = x_parse__mutmut_44 # type: ignore # mutmut generated
mutants_x_try_parse__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_try_parse__mutmut)
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


def x_try_parse__mutmut_orig(raw: str) -> LegalRef | None:
    """`parse`, returning `None` instead of raising.

    For the hot paths that see untrusted text — resolving a `[[REF:n]]` marker,
    reading a golden-set row — where a malformed reference is an expected outcome
    and not an exceptional one.
    """
    try:
        return parse(raw)
    except LegalRefError:
        return None


def x_try_parse__mutmut_1(raw: str) -> LegalRef | None:
    """`parse`, returning `None` instead of raising.

    For the hot paths that see untrusted text — resolving a `[[REF:n]]` marker,
    reading a golden-set row — where a malformed reference is an expected outcome
    and not an exceptional one.
    """
    try:
        return parse(None)
    except LegalRefError:
        return None

mutants_x_try_parse__mutmut['_mutmut_orig'] = x_try_parse__mutmut_orig # type: ignore # mutmut generated
mutants_x_try_parse__mutmut['x_try_parse__mutmut_1'] = x_try_parse__mutmut_1 # type: ignore # mutmut generated
mutants_x_format_ref__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_format_ref__mutmut)
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


def x_format_ref__mutmut_orig(ref: LegalRef) -> str:
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


def x_format_ref__mutmut_1(ref: LegalRef) -> str:
    """A `LegalRef` back into its canonical text.

    Byte-identical to what `chunks-ddl.sql` computes for the `legal_ref` generated
    column, so a Python value and a database row are always the same string.
    """
    text = None
    if ref.articulo is not None:
        text += f"#art{ref.articulo}"
        if ref.apartado is not None:
            text += f".{ref.apartado}"
    return text


def x_format_ref__mutmut_2(ref: LegalRef) -> str:
    """A `LegalRef` back into its canonical text.

    Byte-identical to what `chunks-ddl.sql` computes for the `legal_ref` generated
    column, so a Python value and a database row are always the same string.
    """
    text = ref.norma
    if ref.articulo is None:
        text += f"#art{ref.articulo}"
        if ref.apartado is not None:
            text += f".{ref.apartado}"
    return text


def x_format_ref__mutmut_3(ref: LegalRef) -> str:
    """A `LegalRef` back into its canonical text.

    Byte-identical to what `chunks-ddl.sql` computes for the `legal_ref` generated
    column, so a Python value and a database row are always the same string.
    """
    text = ref.norma
    if ref.articulo is not None:
        text = f"#art{ref.articulo}"
        if ref.apartado is not None:
            text += f".{ref.apartado}"
    return text


def x_format_ref__mutmut_4(ref: LegalRef) -> str:
    """A `LegalRef` back into its canonical text.

    Byte-identical to what `chunks-ddl.sql` computes for the `legal_ref` generated
    column, so a Python value and a database row are always the same string.
    """
    text = ref.norma
    if ref.articulo is not None:
        text -= f"#art{ref.articulo}"
        if ref.apartado is not None:
            text += f".{ref.apartado}"
    return text


def x_format_ref__mutmut_5(ref: LegalRef) -> str:
    """A `LegalRef` back into its canonical text.

    Byte-identical to what `chunks-ddl.sql` computes for the `legal_ref` generated
    column, so a Python value and a database row are always the same string.
    """
    text = ref.norma
    if ref.articulo is not None:
        text += f"#art{ref.articulo}"
        if ref.apartado is None:
            text += f".{ref.apartado}"
    return text


def x_format_ref__mutmut_6(ref: LegalRef) -> str:
    """A `LegalRef` back into its canonical text.

    Byte-identical to what `chunks-ddl.sql` computes for the `legal_ref` generated
    column, so a Python value and a database row are always the same string.
    """
    text = ref.norma
    if ref.articulo is not None:
        text += f"#art{ref.articulo}"
        if ref.apartado is not None:
            text = f".{ref.apartado}"
    return text


def x_format_ref__mutmut_7(ref: LegalRef) -> str:
    """A `LegalRef` back into its canonical text.

    Byte-identical to what `chunks-ddl.sql` computes for the `legal_ref` generated
    column, so a Python value and a database row are always the same string.
    """
    text = ref.norma
    if ref.articulo is not None:
        text += f"#art{ref.articulo}"
        if ref.apartado is not None:
            text -= f".{ref.apartado}"
    return text

mutants_x_format_ref__mutmut['_mutmut_orig'] = x_format_ref__mutmut_orig # type: ignore # mutmut generated
mutants_x_format_ref__mutmut['x_format_ref__mutmut_1'] = x_format_ref__mutmut_1 # type: ignore # mutmut generated
mutants_x_format_ref__mutmut['x_format_ref__mutmut_2'] = x_format_ref__mutmut_2 # type: ignore # mutmut generated
mutants_x_format_ref__mutmut['x_format_ref__mutmut_3'] = x_format_ref__mutmut_3 # type: ignore # mutmut generated
mutants_x_format_ref__mutmut['x_format_ref__mutmut_4'] = x_format_ref__mutmut_4 # type: ignore # mutmut generated
mutants_x_format_ref__mutmut['x_format_ref__mutmut_5'] = x_format_ref__mutmut_5 # type: ignore # mutmut generated
mutants_x_format_ref__mutmut['x_format_ref__mutmut_6'] = x_format_ref__mutmut_6 # type: ignore # mutmut generated
mutants_x_format_ref__mutmut['x_format_ref__mutmut_7'] = x_format_ref__mutmut_7 # type: ignore # mutmut generated
mutants_x_matches__mutmut: MutantDict = {}  # type: ignore


@_mutmut_mutated(mutants_x_matches__mutmut)
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


def x_matches__mutmut_orig(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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


def x_matches__mutmut_1(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
    """Do two references agree all the way down to `level`?

    Reflexive and symmetric. Agreement at `APARTADO` implies agreement at `ARTICULO`,
    which implies agreement at `NORMA`; **the converse never holds**. A reference that
    does not reach the requested level is a miss, not a match by default: asking for
    apartado precision from `RD-1428/2003#art34` returns `False`, which is what makes
    `G-CITA-PRECISION` refuse to reward a citation coarser than the golden set's.
    """
    if a.norma == b.norma:
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


def x_matches__mutmut_2(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
    """Do two references agree all the way down to `level`?

    Reflexive and symmetric. Agreement at `APARTADO` implies agreement at `ARTICULO`,
    which implies agreement at `NORMA`; **the converse never holds**. A reference that
    does not reach the requested level is a miss, not a match by default: asking for
    apartado precision from `RD-1428/2003#art34` returns `False`, which is what makes
    `G-CITA-PRECISION` refuse to reward a citation coarser than the golden set's.
    """
    if a.norma != b.norma:
        return True
    if level is MatchLevel.NORMA:
        return True

    if a.articulo is None or b.articulo is None or a.articulo != b.articulo:
        return False
    if level is MatchLevel.ARTICULO:
        return True

    if a.apartado is None or b.apartado is None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_3(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
    """Do two references agree all the way down to `level`?

    Reflexive and symmetric. Agreement at `APARTADO` implies agreement at `ARTICULO`,
    which implies agreement at `NORMA`; **the converse never holds**. A reference that
    does not reach the requested level is a miss, not a match by default: asking for
    apartado precision from `RD-1428/2003#art34` returns `False`, which is what makes
    `G-CITA-PRECISION` refuse to reward a citation coarser than the golden set's.
    """
    if a.norma != b.norma:
        return False
    if level is not MatchLevel.NORMA:
        return True

    if a.articulo is None or b.articulo is None or a.articulo != b.articulo:
        return False
    if level is MatchLevel.ARTICULO:
        return True

    if a.apartado is None or b.apartado is None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_4(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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
        return False

    if a.articulo is None or b.articulo is None or a.articulo != b.articulo:
        return False
    if level is MatchLevel.ARTICULO:
        return True

    if a.apartado is None or b.apartado is None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_5(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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

    if a.articulo is None or b.articulo is None and a.articulo != b.articulo:
        return False
    if level is MatchLevel.ARTICULO:
        return True

    if a.apartado is None or b.apartado is None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_6(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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

    if a.articulo is None and b.articulo is None or a.articulo != b.articulo:
        return False
    if level is MatchLevel.ARTICULO:
        return True

    if a.apartado is None or b.apartado is None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_7(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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

    if a.articulo is not None or b.articulo is None or a.articulo != b.articulo:
        return False
    if level is MatchLevel.ARTICULO:
        return True

    if a.apartado is None or b.apartado is None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_8(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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

    if a.articulo is None or b.articulo is not None or a.articulo != b.articulo:
        return False
    if level is MatchLevel.ARTICULO:
        return True

    if a.apartado is None or b.apartado is None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_9(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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

    if a.articulo is None or b.articulo is None or a.articulo == b.articulo:
        return False
    if level is MatchLevel.ARTICULO:
        return True

    if a.apartado is None or b.apartado is None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_10(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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
        return True
    if level is MatchLevel.ARTICULO:
        return True

    if a.apartado is None or b.apartado is None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_11(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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
    if level is not MatchLevel.ARTICULO:
        return True

    if a.apartado is None or b.apartado is None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_12(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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
        return False

    if a.apartado is None or b.apartado is None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_13(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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

    if a.apartado is None and b.apartado is None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_14(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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

    if a.apartado is not None or b.apartado is None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_15(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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

    if a.apartado is None or b.apartado is not None:
        return False
    return a.apartado == b.apartado


def x_matches__mutmut_16(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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
        return True
    return a.apartado == b.apartado


def x_matches__mutmut_17(a: LegalRef, b: LegalRef, level: MatchLevel) -> bool:
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
    return a.apartado != b.apartado

mutants_x_matches__mutmut['_mutmut_orig'] = x_matches__mutmut_orig # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_1'] = x_matches__mutmut_1 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_2'] = x_matches__mutmut_2 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_3'] = x_matches__mutmut_3 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_4'] = x_matches__mutmut_4 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_5'] = x_matches__mutmut_5 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_6'] = x_matches__mutmut_6 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_7'] = x_matches__mutmut_7 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_8'] = x_matches__mutmut_8 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_9'] = x_matches__mutmut_9 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_10'] = x_matches__mutmut_10 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_11'] = x_matches__mutmut_11 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_12'] = x_matches__mutmut_12 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_13'] = x_matches__mutmut_13 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_14'] = x_matches__mutmut_14 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_15'] = x_matches__mutmut_15 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_16'] = x_matches__mutmut_16 # type: ignore # mutmut generated
mutants_x_matches__mutmut['x_matches__mutmut_17'] = x_matches__mutmut_17 # type: ignore # mutmut generated
