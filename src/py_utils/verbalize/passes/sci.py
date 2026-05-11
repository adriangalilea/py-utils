"""Scientific notation expansion (``1.5e10`` → "uno coma cinco por diez elevado a diez").

Standard form: ``<mantissa>e<exponent>`` (case-insensitive). Mantissa
allows a leading sign and optional decimal point; exponent is an
integer with optional sign.

Spanish: "por diez elevado a N" or "por diez a la N". We use the
former because it's the more common reading in scientific contexts.

English: "times ten to the N" / "times ten to the power N". We pick
the shorter form.

Negative exponents read as "menos N" / "negative N". Negative
mantissa reads as "menos M" / "negative M".
"""

from __future__ import annotations

from .. import patterns as P

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


_PHRASING = {
    "spanish": ("por diez elevado a", "menos", "coma"),
    "english": ("times ten to the", "negative", "point"),
}


def expand_sci(text: str, lang: str) -> str:
    if not _HAS_NUM2WORDS:
        return text
    if lang not in _PHRASING:
        return text
    iso = "es" if lang == "spanish" else "en"
    join, neg_word, dec_word = _PHRASING[lang]

    def _spell(n: int) -> str:
        try:
            return num2words(abs(n), lang=iso)
        except (NotImplementedError, ValueError):
            return str(abs(n))

    def _spell_mantissa(s: str) -> str:
        sign = ""
        if s.startswith("-"):
            sign = f"{neg_word} "
            s = s[1:]
        if "." in s:
            int_part, frac_part = s.split(".", 1)
            int_n = int(int_part) if int_part else 0
            frac_trim = frac_part.rstrip("0") or "0"
            frac_n = int(frac_trim)
            if len(frac_trim) <= 3:
                frac_words = _spell(frac_n)
            else:
                frac_words = " ".join(_spell(int(c)) for c in frac_trim)
            return f"{sign}{_spell(int_n)} {dec_word} {frac_words}"
        return f"{sign}{_spell(int(s))}"

    def _replace(m):
        mantissa = m.group(1)
        exponent = int(m.group(2))
        exp_word = _spell(exponent)
        if exponent < 0:
            exp_word = f"{neg_word} {exp_word}"
        return f"{_spell_mantissa(mantissa)} {join} {exp_word}"

    return P.SCI_NOTATION.sub(_replace, text)
