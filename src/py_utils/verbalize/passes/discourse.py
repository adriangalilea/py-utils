"""Discourse-level prose cleanups that run after all semiotic passes.

The slash is the only entry today. In chat / code-adjacent prose, a
whitespace-flanked ``/`` between word tokens reads as "or"
(``ask_session / kill_session``, ``and/or``). Earlier passes already
consumed the structural slashes (fractions, units, dates, URLs); a
``/`` surrounded by spaces at this point is almost always an
alternative-marker. TTS otherwise reads it as the literal word "slash",
which is jarring.

We deliberately only fire on the whitespace-flanked form. Glued
variants (``He/she``, ``n/a``) are rarer in dictated prose and risk
clobbering domain-specific shorthand; revisit if real cases surface.
"""

from __future__ import annotations

import re


_SLASH_OR = {
    "spanish": "o",
    "english": "or",
    "french": "ou",
    "german": "oder",
    "italian": "o",
    "portuguese": "ou",
}

_SLASH = re.compile(r"\s+/\s+")


def expand_slash_or(text: str, lang: str) -> str:
    word = _SLASH_OR.get(lang)
    if word is None:
        return text
    return _SLASH.sub(f" {word} ", text)
