"""Unit acronym expansion.

Runs *before* the bare-cardinal expander so a glued form like
``512GB`` becomes ``512 gigabytes`` first; the cardinal expander then
handles ``512`` in isolation and produces the expected space between
number and unit.

Languages with no table (most non-en/es) fall through unchanged. See
``tables.UNITS`` for the full per-language dictionary; this pass is
just dict-driven ``re.sub``.
"""

from __future__ import annotations

import re

from ..tables import UNITS


def expand_units(text: str, lang: str) -> str:
    table = UNITS.get(lang)
    if not table:
        return text
    for pattern, replacement in table.items():
        text = re.sub(pattern, replacement, text)
    return text
