"""Semantic version expansion (``v1.2.3`` → "versión uno punto dos punto tres").

Software versions are common in chat ("Bun v1.3.13", "Python 3.12.10",
"Tailwind v4.3.0"). Without this pass the dot-separated parts get
mauled by the cardinal-decimal pass — "1.2.3" → "uno coma dos punto
tres" or similar nonsense (multiple dots fail the decimal parser and
get left as-is, but pre-released versions like "1.0.0-rc1" go even
worse).

Patterns covered:

- ``v1.2.3`` / ``V1.2.3``
- ``1.2.3`` standalone (no leading word, requires ≥3 dot-separated parts)
- ``1.2.3-rc1`` / ``1.2.3-beta.4`` (pre-release suffix kept as-is)

The leading ``v`` is mandatory for 2-part versions (``v1.0``) since
bare ``1.0`` is ambiguous with a decimal. 3+ parts always count as a
version because no other construct has that shape.
"""

from __future__ import annotations

import re

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


_V_PREFIXED = re.compile(r"\b[vV](\d+(?:\.\d+){1,5})(-[\w.]+)?\b")
# Bare semver (no ``v`` prefix) collides with European thousand-separator
# numbers ("1.234.567" matches semver too) — too dangerous. Require an
# explicit prefix word "version" / "versión" before the number for the
# no-v case. Anything else falls through to the cardinal pass.
_PREFIXED_BARE = re.compile(
    r"\b(?:version|versión|Version|Versión)\s+(\d+(?:\.\d+){1,5})(-[\w.]+)?\b"
)

_PHRASING = {
    "spanish": ("versión", "punto"),
    "english": ("version", "point"),
}

_ISO = {"spanish": "es", "english": "en"}


def _spell(n: int, iso: str) -> str:
    if not _HAS_NUM2WORDS:
        return str(n)
    try:
        return num2words(n, lang=iso)
    except (NotImplementedError, ValueError):
        return str(n)


def _build(version: str, suffix: str, lang: str) -> str:
    word, dot = _PHRASING[lang]
    iso = _ISO[lang]
    parts = [_spell(int(p), iso) for p in version.split(".")]
    body = f" {dot} ".join(parts)
    out = f"{word} {body}"
    if suffix:
        # Keep pre-release suffix verbatim — "rc1", "beta.4". TTS reads
        # them however its tokenizer pleases; full expansion of every
        # pre-release tag is more work than it's worth in chat.
        out += suffix.replace("-", " ").replace(".", " ")
    return out


def expand_versions(text: str, lang: str) -> str:
    if lang not in _PHRASING:
        return text

    def _replace_v(m):
        return _build(m.group(1), m.group(2) or "", lang)

    text = _V_PREFIXED.sub(_replace_v, text)

    def _replace_prefixed(m):
        # The "version" word is consumed by the match and re-emitted by
        # _build, so we just replace the whole span.
        return _build(m.group(1), m.group(2) or "", lang)

    return _PREFIXED_BARE.sub(_replace_prefixed, text)
