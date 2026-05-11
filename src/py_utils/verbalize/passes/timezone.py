"""Time zone tokens (``UTC``, ``GMT+1``, ``UTC-5``, ``CET``, …).

Three forms:

1. **Bare zone**: ``UTC``, ``GMT``, ``CET``, ``EST``, ``PST`` — short
   list of common ones, language-specific replacement.
2. **Offset**: ``UTC+1``, ``GMT-5``, ``UTC+05:30``. Read as "UTC más
   uno" / "UTC plus one" / "UTC más cinco horas y media".
3. **Trailing zone on time**: ``15:30 UTC`` — pass-through. The time
   pass already handles the digits; the zone is read literally by
   the TTS as an English token, which is fine.

Acronym replacements stay short (a few dozen most-used). Unknown zones
pass through unchanged — they're rare in chat content.
"""

from __future__ import annotations

import re

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


# Bare zones → spoken form per language. Keys must match the regex
# alternation below. Conservative list — only zones a Spanish/English
# listener routinely encounters.
_ZONES_ES = {
    "UTC": "U T C",
    "GMT": "G M T",
    "CET": "C E T",
    "CEST": "horario central europeo de verano",
    "EST": "E S T",
    "EDT": "E D T",
    "PST": "hora del Pacífico",
    "PDT": "hora del Pacífico de verano",
    "JST": "hora de Japón",
    "IST": "hora de la India",
}
_ZONES_EN = {
    "UTC": "U T C",
    "GMT": "G M T",
    "CET": "Central European Time",
    "CEST": "Central European Summer Time",
    "EST": "Eastern Standard Time",
    "EDT": "Eastern Daylight Time",
    "PST": "Pacific Standard Time",
    "PDT": "Pacific Daylight Time",
    "JST": "Japan Standard Time",
    "IST": "India Standard Time",
}

_OFFSET_WORD = {
    "spanish": ("más", "menos", "horas"),
    "english": ("plus", "minus", "hours"),
}

_ISO = {"spanish": "es", "english": "en"}


def _zones_pattern(zones):
    return (
        r"\b("
        + "|".join(re.escape(z) for z in zones)
        + r")(?:([+-])(\d{1,2})(?::(\d{2}))?)?\b"
    )


def _spell(n: int, iso: str) -> str:
    if not _HAS_NUM2WORDS:
        return str(n)
    try:
        return num2words(n, lang=iso)
    except (NotImplementedError, ValueError):
        return str(n)


def expand_timezones(text: str, lang: str) -> str:
    if lang == "spanish":
        zones = _ZONES_ES
    elif lang == "english":
        zones = _ZONES_EN
    else:
        return text

    iso = _ISO[lang]
    plus, minus, hours_word = _OFFSET_WORD[lang]
    pat = re.compile(_zones_pattern(zones.keys()))

    def _replace(m):
        zone = zones.get(m.group(1), m.group(1))
        sign = m.group(2)
        h = m.group(3)
        mins = m.group(4)
        if sign is None or h is None:
            return zone
        sign_word = plus if sign == "+" else minus
        h_word = _spell(int(h), iso)
        if mins is not None and int(mins) != 0:
            m_word = _spell(int(mins), iso)
            return f"{zone} {sign_word} {h_word} {hours_word} {m_word}"
        return f"{zone} {sign_word} {h_word}"

    return pat.sub(_replace, text)
