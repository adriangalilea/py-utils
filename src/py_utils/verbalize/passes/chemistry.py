"""Chemical formulas (``H2O``, ``CO2``, ``C2H5OH``, ``H₂O``).

Two input shapes:

- **Subscript Unicode** (``H₂O``): direct codepoint substitution to
  digit + word.
- **ASCII digits** (``H2O``): pattern is "uppercase letter, optional
  lowercase, digit", repeated. The full formula reads element by
  element with the count between.

Per-language phrasing keeps the count's "sub" position implicit —
"hache dos o" / "h two o" / "agua" — context dictates which. We pick
the literal symbol-spelling reading because it's unambiguous in chat
("la fórmula de H2O" reads naturally as "la fórmula de hache dos o"
when surrounded by Spanish).

We do NOT try to expand the formula to "agua" / "water" — that's a
chemistry-knowledge step beyond text normalization. The whole point is
to make the formula PRONOUNCEABLE, not to translate it.
"""

from __future__ import annotations

import re

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


# Requires AT LEAST ONE element with a digit count. Without this guard
# "VI" / "GB" / "GHz" / "MIX" all match (just consecutive capitals) and
# the chemistry pass eats them before Roman numerals / unit acronyms /
# bare words can process them. The cost of this constraint: bare
# letter-only formulas ("NaCl", "CO") don't match — those are rare in
# chat content and can be added per-name to the acronym pass if
# specific cases need it.
_FORMULA = re.compile(
    r"(?<![A-Za-z])"
    r"((?:[A-Z][a-z]?\d*)*[A-Z][a-z]?\d+(?:[A-Z][a-z]?\d*)*)"
    r"(?![A-Za-z])"
)

_SUBSCRIPT = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")

_ISO = {"spanish": "es", "english": "en"}


def _spell(n: int, iso: str) -> str:
    if not _HAS_NUM2WORDS:
        return str(n)
    try:
        return num2words(n, lang=iso)
    except (NotImplementedError, ValueError):
        return str(n)


def _vocalize_formula(formula: str, lang: str) -> str:
    iso = _ISO[lang]
    parts = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
    out = []
    for elem, count in parts:
        if not elem:
            continue
        # Each element letter pronounced as its bare letter (TTS reads
        # H as "ache" / "h", O as "o", etc.) — letter-by-letter spacing.
        out.append(" ".join(elem.lower()))
        if count:
            out.append(_spell(int(count), iso))
    return " ".join(out)


def expand_chemistry(text: str, lang: str) -> str:
    if lang not in _ISO:
        return text

    # First: subscript codepoints → ASCII digits, then proceed
    text_ascii = text.translate(_SUBSCRIPT)

    def _replace(m):
        return _vocalize_formula(m.group(1), lang)

    return _FORMULA.sub(_replace, text_ascii)
