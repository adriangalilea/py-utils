"""Roman numeral expansion.

Heuristic, not exhaustive. Romans are ambiguous in raw text because
the same glyphs are valid English words ("I", "MIX") and acronyms
("MI", "DC"). We only expand when the context strongly suggests a
Roman:

- Preceded by ``siglo`` / ``century`` / ``capítulo`` / ``chapter`` /
  ``Felipe`` / ``Juan Pablo`` / monarch trigger words — the token is a
  Roman ordinal.
- Standalone all-caps token of length ≥2 that matches the Roman regex
  AND parses to a non-zero integer ≤ 3999 AND ALL CHARS are valid
  Roman digits — read as a cardinal (papal "XXIII", historical "MMXIV").

Single-letter ``I`` / ``V`` / ``X`` / ``M`` are NOT expanded — too
ambiguous in raw text.

Context-aware verbalization:

- After ``siglo`` (Spanish) or ``century`` (English): cardinal reading
  ("siglo XXI" → "siglo veintiuno"). Spanish ordinal reading
  ("siglo vigésimo primero") is correct too but conversationally
  Spanish-speakers use the cardinal form past the 10th century, and the
  cardinal is unambiguously correct everywhere.
- After a person's first name + space (king / pope context): ordinal
  reading ("Felipe VI" → "Felipe sexto", "Juan Pablo II" → "Juan Pablo
  segundo"). Up to X (10th) ordinal forms read natural; beyond that we
  fall back to cardinal because Spanish-speakers also do.
"""

from __future__ import annotations

import re
from typing import Set

from .. import patterns as P

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def _roman_to_int(s: str) -> int:
    total = 0
    prev = 0
    for c in reversed(s):
        v = _ROMAN_VALUES.get(c, 0)
        if v < prev:
            total -= v
        else:
            total += v
        prev = v
    return total


# Trigger words → "ordinal reading" (for monarchs/popes/chapters).
_ORDINAL_TRIGGERS_ES: Set[str] = {
    "Felipe",
    "Juan",
    "Carlos",
    "Alfonso",
    "Fernando",
    "Isabel",
    "Pedro",
    "Luis",
    "Enrique",
    "Ricardo",
    "Jorge",
    "Eduardo",
    "Pío",
    "Pablo",
    "Benedicto",
    "Francisco",
    "Gregorio",
    "León",
    "papa",
    "rey",
    "reina",
    "Juan Pablo",
    "capítulo",
    "tomo",
    "volumen",
}
_ORDINAL_TRIGGERS_EN: Set[str] = {
    "King",
    "Queen",
    "Pope",
    "Prince",
    "Princess",
    "Chapter",
    "Volume",
    "Henry",
    "Edward",
    "George",
    "Louis",
    "Charles",
    "James",
    "Richard",
}

# Trigger words → "cardinal reading" (centuries, years).
_CARDINAL_TRIGGERS_ES: Set[str] = {"siglo", "siglos", "Siglo", "Siglos"}
_CARDINAL_TRIGGERS_EN: Set[str] = {"century", "centuries", "Century", "Centuries"}


def _spell_cardinal(n: int, lang: str) -> str:
    if not _HAS_NUM2WORDS:
        return str(n)
    iso = "es" if lang == "spanish" else "en" if lang == "english" else None
    if iso is None:
        return str(n)
    try:
        return num2words(n, lang=iso)
    except (NotImplementedError, ValueError):
        return str(n)


def _spell_ordinal(n: int, lang: str) -> str:
    if not _HAS_NUM2WORDS:
        return str(n)
    iso = "es" if lang == "spanish" else "en" if lang == "english" else None
    if iso is None:
        return str(n)
    try:
        return num2words(n, lang=iso, to="ordinal")
    except (NotImplementedError, ValueError):
        return str(n)


def expand_romans(text: str, lang: str) -> str:
    """Expand context-tagged Roman numerals. Bare romans in arbitrary
    text are NOT touched — too ambiguous with English / acronyms.
    """
    if lang == "spanish":
        ord_triggers, card_triggers = _ORDINAL_TRIGGERS_ES, _CARDINAL_TRIGGERS_ES
    elif lang == "english":
        ord_triggers, card_triggers = _ORDINAL_TRIGGERS_EN, _CARDINAL_TRIGGERS_EN
    else:
        return text

    def _apply(triggers: Set[str], spell_fn) -> str:
        nonlocal text
        # "<trigger> ROMAN" — replace the ROMAN with the spelled form.
        # Trigger preserved as-is.
        trigger_re = "|".join(re.escape(t) for t in triggers)
        # Up to 10 for ordinals (Spanish/English speakers switch to
        # cardinals past that for monarch names); cardinals have no
        # cap.
        roman_re = P.ROMAN.pattern

        def _sub(m):
            trigger = m.group(1)
            roman = m.group(2)
            if not roman:
                return m.group(0)
            n = _roman_to_int(roman)
            if n == 0 or n > 3999:
                return m.group(0)
            return f"{trigger} {spell_fn(n)}"

        text = re.sub(
            rf"({trigger_re})\s+({roman_re})\b",
            _sub,
            text,
        )

    # Cardinal context first (siglo XXI) — uses cardinal reading.
    _apply(card_triggers, lambda n: _spell_cardinal(n, lang))
    # Ordinal context (Felipe VI) — ordinal up to 10, cardinal beyond.
    _apply(
        ord_triggers,
        lambda n: _spell_ordinal(n, lang) if n <= 10 else _spell_cardinal(n, lang),
    )
    return text
