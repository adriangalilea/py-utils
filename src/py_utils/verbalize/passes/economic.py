"""Currency, percent, and plus-suffix expansion.

All three are "<digits><symbol>" patterns where the symbol carries
semantic weight (₂€ → euros, % → percent, + → or more). Run BEFORE the
bare-cardinal expander so the symbol is consumed first and the digits
fall through cleanly.

Pass order within this module matters too: plus-suffix BEFORE
currency/percent because the ``+`` is glued to the digits — once
currency or percent consumes its symbol the ``+`` gets orphaned and
plus-suffix can no longer relate it to the number. Example: ``$10,000+``
must become ``10,000 dólares o más`` not ``10,000 dólares+``.
"""

from __future__ import annotations

import re

from .. import patterns as P
from ..tables import CURRENCY, PERCENT_WORD, PLUS_SUFFIX_WORD


def expand_currency(text: str, lang: str) -> str:
    """Replace currency symbols with their spoken word.

    Matches the symbol whether it appears before (``$10``) or after
    (``10€``) a number. Inserts a space so the cardinal expander picks
    up the digits cleanly.
    """
    cur = CURRENCY.get(lang) or CURRENCY["english"]
    for sym, word in cur.items():
        esc = re.escape(sym)
        text = re.sub(rf"(\d+(?:[.,]\d+)*)\s*{esc}", rf"\1 {word}", text)
        text = re.sub(rf"{esc}\s*(\d+(?:[.,]\d+)*)", rf"\1 {word}", text)
    return text


def expand_percent(text: str, lang: str) -> str:
    """Replace ``N%`` with ``N <percent_word>``.

    Spanish has an idiomatic exception for exactly 100%: native
    speakers say "cien por cien", not "cien por ciento". Both are
    grammatically valid, but the doubled form is overwhelmingly
    preferred. Other percentages (87%, 12,5%) take the regular
    ``<n> por ciento``. NeMo's Spanish TN gets this wrong — we
    explicitly handle it.
    """
    word = PERCENT_WORD.get(lang, PERCENT_WORD["english"])
    if lang == "spanish":
        text = re.sub(r"\b100\s*%(?!\d)", "cien por cien", text)
    return P.PERCENT.sub(rf"\1 {word}", text)


def expand_plus_suffix(text: str, lang: str) -> str:
    """Replace ``<digits>+`` (and ``<digits>%+``) with ``<digits> <or-more-word>``.

    Common in LLM-produced copy: ``"$10,000+"``, ``"1500+ users"``,
    ``"10+ minutes"``. Without this the model reads the trailing ``+``
    as a literal "más" / "plus" or just stops short.
    """
    word = PLUS_SUFFIX_WORD.get(lang, PLUS_SUFFIX_WORD["english"])
    return P.PLUS_SUFFIX.sub(rf"\1 {word}", text)
