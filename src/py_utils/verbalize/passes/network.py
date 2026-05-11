"""IP addresses and ports.

IPv4 (``192.168.1.1``) → digit-by-digit per octet so listeners can
transcribe back. Ports trailing the IP (``:8080``) read as "puerto
N" / "port N".

IPv6 is intentionally NOT covered — its colon-hex shape collides with
times and would need a full parser; rare in chat content. Add later if
needed.

Runs BEFORE phone (some IP shapes look phone-like with all the digits)
and BEFORE temporal (so the trailing port doesn't get caught by
``HH:MM``).
"""

from __future__ import annotations

import re

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


_IPV4 = re.compile(
    r"(?<![\w.])"
    r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})"
    r"(?::(\d{1,5}))?"
    r"(?![\w.])"
)

_PHRASING = {
    "spanish": {
        "dot": "punto",
        "port": "puerto",
    },
    "english": {
        "dot": "dot",
        "port": "port",
    },
}

_ISO = {"spanish": "es", "english": "en"}


def _spell(n: int, iso: str) -> str:
    if not _HAS_NUM2WORDS:
        return str(n)
    try:
        return num2words(n, lang=iso)
    except (NotImplementedError, ValueError):
        return str(n)


def expand_ips(text: str, lang: str) -> str:
    if lang not in _PHRASING:
        return text
    phrasing = _PHRASING[lang]
    iso = _ISO[lang]

    def _replace(m):
        octs = [m.group(i) for i in range(1, 5)]
        port = m.group(5)
        for o in octs:
            if int(o) > 255:
                return m.group(0)  # not a real IP, leave alone
        spoken_octets = [_spell(int(o), iso) for o in octs]
        body = f" {phrasing['dot']} ".join(spoken_octets)
        if port is not None:
            body += f" {phrasing['port']} {_spell(int(port), iso)}"
        return body

    return _IPV4.sub(_replace, text)
