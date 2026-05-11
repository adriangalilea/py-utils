"""Acronym verbalization (``FBI`` → "F B I", ``NASA`` → "nasa").

Per-language dictionary of well-known acronyms with their conventional
spoken form. Two flavours:

- **Letter-by-letter**: ``FBI`` → "F B I", ``USA`` → "U S A". The
  acronym isn't pronounceable as a word in the local language.
- **Word**: ``NASA`` → "nasa", ``OTAN`` → "otan". The acronym IS
  pronounceable, native readers say it that way.

We only act on acronyms IN the dictionary. Unknown all-caps tokens are
left alone — TTS guesses correctly often enough, and a global "always
spell letter-by-letter" rule would mangle every proper noun. Add
entries to the dict as audit listening surfaces missed cases.

The pattern is conservative: standalone 2-6 letter all-caps tokens
only, with word boundaries on both sides. Single-letter "I" and "A"
are not eligible (too ambiguous).
"""

from __future__ import annotations

import re
from typing import Dict


def _letterwise(s: str) -> str:
    return " ".join(s)


# Spanish acronym dict. Value: spoken form. "_LETTERS" sentinel means
# spell out via LETTER_NAMES; otherwise the value is read verbatim.
_DICT: Dict[str, Dict[str, str]] = {
    "spanish": {
        # Letter-by-letter (initialisms)
        "FBI": _letterwise("FBI"),
        "CIA": _letterwise("CIA"),
        "EEUU": "Estados Unidos",
        "USA": _letterwise("USA"),
        "UK": _letterwise("UK"),
        "DNI": _letterwise("DNI"),
        "NIE": _letterwise("NIE"),
        "IRPF": _letterwise("IRPF"),
        "IVA": _letterwise("IVA"),
        "PIB": _letterwise("PIB"),
        "BCE": _letterwise("BCE"),
        "FMI": _letterwise("FMI"),
        "OMS": _letterwise("OMS"),
        "ONG": _letterwise("ONG"),
        "ESO": _letterwise("ESO"),
        "ETT": _letterwise("ETT"),
        "PSOE": _letterwise("PSOE"),
        "PP": _letterwise("PP"),
        # Word-form (read as pronounceable)
        "ONU": "onu",
        "OTAN": "otan",
        "RAE": "rae",
        "UNED": "uned",
        "SIDA": "sida",
        "OVNI": "ovni",
        "RENFE": "renfe",
    },
    "english": {
        # Initialisms
        "FBI": _letterwise("FBI"),
        "CIA": _letterwise("CIA"),
        "USA": _letterwise("USA"),
        "UK": _letterwise("UK"),
        "EU": _letterwise("EU"),
        "UN": _letterwise("UN"),
        "WHO": _letterwise("WHO"),
        "IMF": _letterwise("IMF"),
        "ECB": _letterwise("ECB"),
        "GDP": _letterwise("GDP"),
        "PhD": "P h D",
        "FAQ": _letterwise("FAQ"),
        "API": _letterwise("API"),
        "CEO": _letterwise("CEO"),
        "CTO": _letterwise("CTO"),
        "AWS": _letterwise("AWS"),
        "GCP": _letterwise("GCP"),
        "SDK": _letterwise("SDK"),
        # Word-form
        "NASA": "nasa",
        "NATO": "nato",
        "ASCII": "askee",
        "SCUBA": "scuba",
        "LASER": "laser",
        "PIXAR": "pixar",
    },
}


def expand_acronyms(text: str, lang: str) -> str:
    table = _DICT.get(lang)
    if not table:
        return text
    # Sort by length descending so longer matches win first.
    keys = sorted(table.keys(), key=len, reverse=True)
    pat = re.compile(r"\b(" + "|".join(re.escape(k) for k in keys) + r")\b")

    def _replace(m):
        return table[m.group(1)]

    return pat.sub(_replace, text)
