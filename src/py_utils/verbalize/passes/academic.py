"""Academic identifiers — DOI, ISBN, citation formats, footnote markers.

Surface that creeps into chat content via copy-paste from papers,
blogs, or markdown content.

## DOI

Format: ``10.<registrant>/<suffix>``. Always starts with ``10.``,
then digits, then ``/`` and any printable identifier. Speakers
universally say "D O I" letter-by-letter for the prefix, then read
the structure with "barra" / "slash" for the separator.

## ISBN

10 or 13 digits separated by hyphens or spaces. Read as digit
sequences with the conventional grouping. Detect via the optional
``ISBN`` prefix or the precise hyphen-pattern shape.

## Citation formats

``(Smith, 2024)`` / ``Smith (2024)`` / ``Smith 2024, p. 5``. Common in
academic text. We just expand the page-marker abbreviations
(``p.`` / ``pp.``) which the abbreviation pass might miss in this
context, and leave the rest to read naturally — author name + year
already reads correctly.

## Footnote markers

Superscript digits (``¹ ² ³ ⁴ ⁵``) that LLMs sometimes produce.
Replaced with a parenthetical "nota 1" / "footnote 1" reading so
the listener gets the cue without the model trying to fonemize the
superscript glyph.
"""

from __future__ import annotations

import re

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


_SUPERSCRIPT_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
_SUPERSCRIPT = re.compile(r"([⁰¹²³⁴⁵⁶⁷⁸⁹]+)")

_DOI = re.compile(r"\b(10\.\d{4,9})/([^\s)]+)")

# ISBN-10 or ISBN-13 with hyphens (and optional prefix).
_ISBN = re.compile(
    r"\b(?:ISBN[-:\s]?)?"
    r"(\d{1,5}-\d{1,7}-\d{1,7}-[\dX])\b"
)
_ISBN13 = re.compile(
    r"\b(?:ISBN[-:\s]?)?"
    r"(978|979)-(\d{1,5})-(\d{1,7})-(\d{1,7})-(\d)\b"
)

# Page abbreviations inside citations
_PAGE_ABBREV = re.compile(r"\b(p|pp)\.\s*(\d+(?:-\d+)?)", re.IGNORECASE)


_PHRASING = {
    "spanish": {
        "doi": "D O I",
        "slash": "barra",
        "isbn": "I S B N",
        "footnote": "nota",
        "page": "página",
        "pages": "páginas",
    },
    "english": {
        "doi": "D O I",
        "slash": "slash",
        "isbn": "I S B N",
        "footnote": "footnote",
        "page": "page",
        "pages": "pages",
    },
}

_ISO = {"spanish": "es", "english": "en"}


def _spell(n: int, iso: str) -> str:
    if not _HAS_NUM2WORDS:
        return str(n)
    try:
        return num2words(n, lang=iso)
    except (NotImplementedError, ValueError):
        return str(n)


def expand_doi(text: str, lang: str) -> str:
    if lang not in _PHRASING:
        return text
    p = _PHRASING[lang]
    iso = _ISO[lang]

    def _replace(m):
        reg = m.group(1)
        suf = m.group(2)
        # Registrant: read the prefix digit-by-digit + sub-codes
        prefix = (
            "ten " + _spell(int(reg.split(".")[1]), iso)
            if lang == "english"
            else "diez punto " + _spell(int(reg.split(".")[1]), iso)
        )
        return f"{p['doi']} {prefix} {p['slash']} {suf}"

    return _DOI.sub(_replace, text)


def expand_isbn(text: str, lang: str) -> str:
    if lang not in _PHRASING:
        return text
    p = _PHRASING[lang]
    iso = _ISO[lang]

    def _spell_digits(s: str) -> str:
        return " ".join(_spell(int(c), iso) if c.isdigit() else c for c in s)

    def _replace13(m):
        groups = [m.group(i) for i in range(1, 6)]
        return f"{p['isbn']} " + " ".join(_spell_digits(g) for g in groups)

    def _replace10(m):
        return f"{p['isbn']} " + _spell_digits(m.group(1).replace("-", " "))

    text = _ISBN13.sub(_replace13, text)
    text = _ISBN.sub(_replace10, text)
    return text


def expand_citations(text: str, lang: str) -> str:
    """Just the page-marker abbreviations inside citation strings.
    Author + year reads naturally already.
    """
    if lang not in _PHRASING:
        return text
    p = _PHRASING[lang]

    def _replace(m):
        prefix = m.group(1).lower()
        body = m.group(2)
        word = p["pages"] if prefix == "pp" else p["page"]
        return f"{word} {body}"

    return _PAGE_ABBREV.sub(_replace, text)


def expand_footnotes(text: str, lang: str) -> str:
    if lang not in _PHRASING:
        return text
    p = _PHRASING[lang]
    iso = _ISO[lang]

    def _replace(m):
        digits = m.group(1).translate(_SUPERSCRIPT_DIGITS)
        return f"{p['footnote']} {_spell(int(digits), iso)}"

    return _SUPERSCRIPT.sub(_replace, text)
