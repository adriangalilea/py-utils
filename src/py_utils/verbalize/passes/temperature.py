"""Temperature and degree-symbol expansion.

Three patterns handled:

- ``<n>°C`` / ``<n> °C`` → "grados Celsius" / "degrees Celsius"
- ``<n>°F`` / ``<n> °F`` → "grados Fahrenheit" / "degrees Fahrenheit"
- ``<n>°`` (no scale letter following) → "grados" / "degrees". Covers
  angles, latitude / longitude, compass bearings.

Runs **before** ``units`` and ``cardinal`` so the number stays attached
to its scale and the cardinal pass spells out the digits afterward.

Kelvin (``K``) is deliberately skipped — ``K`` alone is too ambiguous
(``10K`` followers, chemistry symbol, variable). Add a guarded pattern
later if forecast-style ``300 K`` shows up.
"""

from __future__ import annotations

import re


_TEMP_WORDS = {
    "spanish": {
        "celsius": "grados Celsius",
        "fahrenheit": "grados Fahrenheit",
        "bare": "grados",
    },
    "english": {
        "celsius": "degrees Celsius",
        "fahrenheit": "degrees Fahrenheit",
        "bare": "degrees",
    },
    "french": {
        "celsius": "degrés Celsius",
        "fahrenheit": "degrés Fahrenheit",
        "bare": "degrés",
    },
    "german": {
        "celsius": "Grad Celsius",
        "fahrenheit": "Grad Fahrenheit",
        "bare": "Grad",
    },
    "italian": {
        "celsius": "gradi Celsius",
        "fahrenheit": "gradi Fahrenheit",
        "bare": "gradi",
    },
    "portuguese": {
        "celsius": "graus Celsius",
        "fahrenheit": "graus Fahrenheit",
        "bare": "graus",
    },
}

# Number followed (optionally with one space) by °C / °F.
_CELSIUS = re.compile(r"(\d)\s*°\s*[Cc](?![a-zA-Z])")
_FAHRENHEIT = re.compile(r"(\d)\s*°\s*[Ff](?![a-zA-Z])")
# Bare degree: number, optional space, °, not followed by a scale
# letter that would identify it as C/F (those are handled above).
_BARE_DEGREE = re.compile(r"(\d)\s*°(?![CcFf])")


def expand_temperatures(text: str, lang: str) -> str:
    words = _TEMP_WORDS.get(lang)
    if words is None:
        return text
    text = _CELSIUS.sub(rf"\1 {words['celsius']}", text)
    text = _FAHRENHEIT.sub(rf"\1 {words['fahrenheit']}", text)
    text = _BARE_DEGREE.sub(rf"\1 {words['bare']}", text)
    return text
