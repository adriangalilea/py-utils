"""Explicit fraction expansion (``1/4`` → "un cuarto", "one quarter").

Disambiguates against:

- **Dates**: ``1/2/2026`` would otherwise match three times. The
  fraction regex uses negative lookahead/lookbehind for digits and
  slashes — ``(?<!\\d)`` and ``(?!\\d|/)`` — so it only fires on bare
  pairs.
- **Phone numbers**: phone pass runs FIRST and consumes those groups.
- **Ranges**: ranges use ``-``, not ``/``.

Denominators 2-12 get their idiomatic spoken form (un medio, un tercio,
un cuarto, …); larger ones fall back to ``<numerator> <denominator>-avos`` style. For numerators > 1
the numerator uses cardinal reading.

NeMo's Spanish fraction grammar covers more cases (fractions of unit
nouns, mixed numbers like "2 1/4") but our chat use case rarely needs
them — extend on demand.
"""

from __future__ import annotations

from .. import patterns as P

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


_DENOM_ES = {
    2: "medio", 3: "tercio", 4: "cuarto", 5: "quinto", 6: "sexto",
    7: "séptimo", 8: "octavo", 9: "noveno", 10: "décimo",
    11: "onceavo", 12: "doceavo",
}
_DENOM_EN = {
    2: "half", 3: "third", 4: "quarter", 5: "fifth", 6: "sixth",
    7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
    11: "eleventh", 12: "twelfth",
}


def _spell_numerator(n: int, iso: str) -> str:
    if not _HAS_NUM2WORDS:
        return str(n)
    try:
        return num2words(n, lang=iso)
    except (NotImplementedError, ValueError):
        return str(n)


def expand_fractions(text: str, lang: str) -> str:
    if lang == "spanish":
        denom_table = _DENOM_ES
        iso = "es"
        unit_pos = lambda: "un"        # un cuarto, un tercio
        plural_suffix = "s"
    elif lang == "english":
        denom_table = _DENOM_EN
        iso = "en"
        unit_pos = lambda: "one"
        plural_suffix = "s"
    else:
        return text

    def _replace(m):
        num = int(m.group(1))
        den = int(m.group(2))
        if den == 0 or den > 999 or num > 999:
            return m.group(0)

        # Denominator word
        if den in denom_table:
            den_word = denom_table[den]
            if num != 1:
                den_word = den_word + plural_suffix
        else:
            # Fall back to "<denom>-avos" (Spanish) / "<denom>ths" (English)
            den_card = _spell_numerator(den, iso)
            if lang == "spanish":
                den_word = f"{den_card}avos" if num != 1 else f"{den_card}avo"
            else:
                den_word = f"{den_card}ths" if num != 1 else f"{den_card}th"

        # Numerator word
        if num == 1:
            num_word = unit_pos()
        else:
            num_word = _spell_numerator(num, iso)
        return f"{num_word} {den_word}"

    return P.FRACTION.sub(_replace, text)
