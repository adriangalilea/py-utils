"""Numeric range expansion (``1990-2000`` → "mil novecientos noventa a dos mil").

Runs AFTER phone-number expansion (phones consume some hyphenated
sequences) and AFTER date expansion (ISO dates use hyphens too).

Year-range heuristic: if both sides parse as years in 1900-2099 and
the gap is reasonable (≤200 years), treat them as years; otherwise
fall back to two cardinals joined by the language's range conjunction.

We do NOT try to handle "años 90" (the truncated decade) here — that's
a different phrasing the LLM usually emits as the full year ("los años
noventa"). Add a separate pass if needed.
"""

from __future__ import annotations

from .. import patterns as P

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


_RANGE_JOIN = {
    "spanish":    " a ",
    "english":    " to ",
    "french":     " à ",
    "german":     " bis ",
    "italian":    " a ",
    "portuguese": " a ",
}

_NUM_LANG_ISO = {
    "spanish":    "es",
    "english":    "en",
    "french":     "fr",
    "german":     "de",
    "italian":    "it",
    "portuguese": "pt",
}


def expand_ranges(text: str, lang: str) -> str:
    if not _HAS_NUM2WORDS:
        return text
    iso = _NUM_LANG_ISO.get(lang)
    if iso is None:
        return text
    join = _RANGE_JOIN.get(lang, " - ")

    def _spell(n: int) -> str:
        try:
            return num2words(n, lang=iso)
        except (NotImplementedError, ValueError):
            return str(n)

    def _replace(m):
        a, b = int(m.group(1)), int(m.group(2))
        if a > b or (b - a) > 5000:
            # Inverted or implausibly large range: probably not a range.
            return m.group(0)
        return f"{_spell(a)}{join}{_spell(b)}"

    return P.RANGE_NUM.sub(_replace, text)
