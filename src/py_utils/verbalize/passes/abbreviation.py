"""Abbreviation expansion.

Per-language dictionary lookup. The matching regex consumes its
trailing period (``\\.`` is part of the match for things like ``Sr.``)
which would silently swallow end-of-sentence terminators —
``"Vivo en EE.UU."`` → ``"Vivo en Estados Unidos"`` loses the ``.``
even though the original ended a sentence. We capture the final
terminator before the pass and restore it afterward if the expansion
ate it.

Consumers can pass ``extra_abbreviations`` (regex → replacement) to
augment the built-in dictionary with domain glossaries.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

from .. import patterns as P
from ..tables import ABBREVIATIONS


def expand_abbreviations(
    text: str,
    lang: str,
    extra_abbreviations: Optional[Dict[str, str]] = None,
) -> str:
    table = ABBREVIATIONS.get(lang)
    if not table:
        if extra_abbreviations:
            for pattern, replacement in extra_abbreviations.items():
                text = re.sub(pattern, replacement, text)
        return text

    stripped = text.rstrip()
    final = stripped[-1] if stripped else ""
    had_terminator = final in P.SENT_TERMINAL
    trailing_ws = text[len(stripped) :] if had_terminator else ""

    for pattern, replacement in table.items():
        text = re.sub(pattern, replacement, text)
    if extra_abbreviations:
        for pattern, replacement in extra_abbreviations.items():
            text = re.sub(pattern, replacement, text)

    if had_terminator and not text.rstrip().endswith(final):
        text = text.rstrip() + final + trailing_ws
    return text
