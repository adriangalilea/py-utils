"""Hex color codes (``#FF0000``, ``0xDEAD``).

Without this they'd survive into the cardinal pass which then either
ignores them (no digits) or mangles a partial match. Reading "F F
cero cero cero cero" letter-by-letter is the cleanest spoken form —
short, unambiguous, the listener can transcribe it back.

Two formats:

- CSS-style ``#FF0000`` / ``#fff`` (3-, 4-, 6-, 8-hex with leading hash)
- C-style ``0xDEAD`` / ``0xCAFEBABE`` (any-length hex with 0x prefix)

The leading word "color" / "hex" is NOT prepended — the surrounding
sentence usually has its own ("the color #FF0000", "el color #FF0000").
We just vocalize the digits.
"""

from __future__ import annotations

import re

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


_CSS_HEX = re.compile(r"(?<![\w#])#([0-9A-Fa-f]{3,8})\b")
_C_HEX = re.compile(r"\b0[xX]([0-9A-Fa-f]{1,16})\b")

_ISO = {"spanish": "es", "english": "en"}


def _spell(n: int, iso: str) -> str:
    if not _HAS_NUM2WORDS:
        return str(n)
    try:
        return num2words(n, lang=iso)
    except (NotImplementedError, ValueError):
        return str(n)


def _spell_hex(s: str, lang: str) -> str:
    """Spell hex digits one at a time. Numeric digits use the cardinal
    word; letter digits keep their letter name (the surrounding TTS
    pronounces them as English letters)."""
    iso = _ISO.get(lang, "en")
    out = []
    for c in s.lower():
        if c.isdigit():
            out.append(_spell(int(c), iso))
        else:
            out.append(c)
    return " ".join(out)


def expand_hex_colors(text: str, lang: str) -> str:
    if lang not in _ISO:
        return text

    def _replace_css(m):
        return _spell_hex(m.group(1), lang)

    def _replace_c(m):
        return _spell_hex(m.group(1), lang)

    text = _CSS_HEX.sub(_replace_css, text)
    text = _C_HEX.sub(_replace_c, text)
    return text
