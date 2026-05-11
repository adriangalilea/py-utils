"""Cardinal number expansion via num2words.

Last numeric pass — runs AFTER date, time, currency, percent,
plus-suffix, units, fraction, range, sci, phone (each of which
consumes its own digit-bearing patterns). What's left here is bare
integers and locale-style decimals.

## Locale rules for separators

- ``"spanish"``, ``"german"``, ``"french"``, ``"italian"``,
  ``"portuguese"``, ``"russian"``: period = thousands, comma = decimal.
- ``"english"``: comma = thousands, period = decimal.

## Disambiguation heuristic

Plain digit groups separated by exactly three digits are thousands
regardless of language: ``"7,000"`` in Spanish text is almost
certainly US-style thousands (LLMs produce currency this way), and
``"1.234.567"`` in English is almost certainly Spanish-style thousands
copied in. We detect those patterns up-front to bypass the locale rule.

**Bug fix vs prior version**: ``"2.5"`` in Spanish was previously
mis-parsed as the integer ``"25"`` because the dot-thousands rule
applied. The fix below: in comma-decimal languages, treat a single
``.`` with 1-2 trailing digits as a US-style decimal (mixed-locale
text leaks "2.5" everywhere — `kg`, `GHz`, English copy quoted in
Spanish — overwhelmingly more often than it would be intentional
Spanish thousands of the form "2.500").

## Fractional readings

Up to 3 fractional digits → cardinal reading ("setenta y cinco");
longer → digit-by-digit ("uno cuatro uno cinco nueve"), how
mathematicians read them.

Trailing zeros are stripped: ``"3,50"`` reads "tres coma cinco" not
"tres coma cincuenta". Disable in the source if mathematical fidelity
matters more than naturalness.
"""

from __future__ import annotations

import re

from .. import patterns as P
from ..tables import DECIMAL_WORD, NUM2WORDS_LANG

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


_COMMA_DECIMAL_LANGS = {
    "spanish",
    "german",
    "french",
    "italian",
    "portuguese",
    "russian",
}

# Single ``.`` followed by 1-2 digits — almost certainly a US-style
# decimal, not a Spanish/German thousands group (those always have
# exactly 3 digits after the dot). Used in the bug-fix branch below.
_DOT_DECIMAL_LIKELY = re.compile(r"^\d+\.\d{1,2}$")


def expand_numbers(text: str, lang: str) -> str:
    if not _HAS_NUM2WORDS:
        return text
    iso = NUM2WORDS_LANG.get(lang)
    if iso is None:
        return text

    use_comma_decimal = lang in _COMMA_DECIMAL_LANGS
    decimal_word = DECIMAL_WORD.get(lang, "point")

    def _spell_int(n: int) -> str:
        try:
            return num2words(n, lang=iso)
        except (NotImplementedError, ValueError):
            return str(n)

    def _replace(m):
        tok = m.group(0)

        # Glue protection: when a digit run is glued to a trailing
        # letter (e.g. "512GB", "100kg"), bare expansion would produce
        # "quinientos doceGB" with no audible separator. Detect from
        # context and append a space so the unit stays a separate
        # spoken token.
        end = m.end()
        full = m.string
        needs_trailing_space = end < len(full) and full[end].isalpha()

        # Single bare digit — cheap path.
        if len(tok) == 1:
            words = _spell_int(int(tok))
            return words + " " if needs_trailing_space else words

        # Thousand-only patterns first (locale-agnostic).
        if P.THOUSANDS_COMMA.fullmatch(tok):
            normalized = tok.replace(",", "")
        elif P.THOUSANDS_DOT.fullmatch(tok):
            normalized = tok.replace(".", "")
        elif use_comma_decimal:
            # Bug-fix path: in comma-decimal languages, a single ``.``
            # with 1-2 trailing digits is almost certainly a US-style
            # decimal leaked into mixed-locale text. Treat the ``.`` as
            # the decimal separator (do NOT delete it as a thousands
            # marker). Without this, "2.5 kg" reads "veinticinco
            # kilogramos" instead of "dos coma cinco kilogramos".
            if _DOT_DECIMAL_LIKELY.fullmatch(tok):
                normalized = tok  # already in canonical form for split below
            else:
                # period = thousands, comma = decimal
                normalized = tok.replace(".", "").replace(",", ".")
        else:
            # comma = thousands, period = decimal
            normalized = tok.replace(",", "")

        if normalized.count(".") > 1:
            return tok  # ambiguous, give up

        if "." in normalized:
            int_part_str, frac_part_str = normalized.split(".", 1)
            if not int_part_str:
                int_part_str = "0"
            try:
                int_part = int(int_part_str)
            except ValueError:
                return tok

            frac_trimmed = frac_part_str.rstrip("0") or "0"
            int_words = _spell_int(int_part)
            if len(frac_trimmed) <= 3:
                try:
                    frac_words = _spell_int(int(frac_trimmed))
                except ValueError:
                    return tok
            else:
                frac_words = " ".join(_spell_int(int(c)) for c in frac_trimmed)

            words = f"{int_words} {decimal_word} {frac_words}"
            return words + " " if needs_trailing_space else words

        try:
            words = _spell_int(int(normalized))
        except ValueError:
            return tok
        return words + " " if needs_trailing_space else words

    return P.NUMBER.sub(_replace, text)
