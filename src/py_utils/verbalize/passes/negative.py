"""Leading negative sign on a number → spoken word.

A bare ``-`` followed by a digit reads "dash" / "minus" out of TTS
boxes by default. Convert it to the spoken word ("menos" / "minus")
so ``-5°C`` reads naturally.

Runs **after** every pass that consumes hyphens for its own purpose
(ranges ``1-5``, dates ``2026-05-15``, phones ``+34-600-123-456``,
sci notation ``1e-3``) so this pass only sees the unary-minus form.

Triggers only when the ``-`` is at the start of input or preceded by
whitespace / open-bracket / arithmetic flanker. ``compound-word`` is
left alone (preceding char is a letter). ``2-3`` is left alone (matched
by ranges first; the digit-before-hyphen guard here also blocks it as
a safety net).
"""

from __future__ import annotations

import re


_NEG_WORDS = {
    "spanish": "menos",
    "english": "minus",
    "french": "moins",
    "german": "minus",
    "italian": "meno",
    "portuguese": "menos",
}

# Leading minus on a number. Must be at boundary (start of string,
# whitespace, opening bracket, or one of a few sentence-internal
# starters). The lookbehind for ``\d`` prevents matching the middle
# hyphen of a range (``2-3``) — ranges should already be consumed by
# the range_ pass, this is the safety net.
_LEADING_MINUS = re.compile(r"(?:(?<=^)|(?<=[\s(\[{,;:]))-(?=\d)")


def expand_negatives(text: str, lang: str) -> str:
    word = _NEG_WORDS.get(lang)
    if word is None:
        return text
    return _LEADING_MINUS.sub(f"{word} ", text)
