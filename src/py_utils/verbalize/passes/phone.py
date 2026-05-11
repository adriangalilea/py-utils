"""Phone number expansion (``+34 600 123 456`` → digit pairs).

Convention for Spain (and most European countries): phone numbers are
read in **digit pairs** with the first digit standalone:
``"600 123 456"`` reads as "seis, cero, cero, uno, veintitrés,
cuatrocientos cincuenta y seis" colloquially, or
"seis cero cero, uno dos tres, cuatro cinco seis" formally. We go with
formal digit-by-digit because it's unambiguous across countries — pair
readings differ subtly (some say "treinta y cuatro" for "34", others
"tres cuatro").

Country code is read as ``+`` → "más" (Spanish) / "plus" (English),
followed by the digits.

This pass MUST run before ``cardinal`` and before ``range_`` because
otherwise the 3-digit groups get parsed as separate cardinals
(``"600"`` → "seiscientos") and the spaces between groups would be
indistinguishable from a real cardinal sequence.
"""

from __future__ import annotations

from .. import patterns as P

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


_PHRASING = {
    "spanish":  ("más", "es"),
    "english":  ("plus", "en"),
}


def expand_phones(text: str, lang: str) -> str:
    if not _HAS_NUM2WORDS:
        return text
    if lang not in _PHRASING:
        return text
    plus_word, iso = _PHRASING[lang]

    def _spell(n: int) -> str:
        try:
            return num2words(n, lang=iso)
        except (NotImplementedError, ValueError):
            return str(n)

    def _digits(s: str) -> str:
        return " ".join(_spell(int(c)) for c in s if c.isdigit())

    def _replace(m):
        country = m.group(1) or ""
        body = "".join(c for c in m.group(0) if c.isdigit())
        if country:
            cc_digits = "".join(c for c in country if c.isdigit())
            body = body[len(cc_digits):]
            return f"{plus_word} {_digits(cc_digits)} {_digits(body)}"
        return _digits(body)

    return P.PHONE.sub(_replace, text)
