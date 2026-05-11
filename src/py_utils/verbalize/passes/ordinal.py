"""Spanish ordinal expansion.

Spanish ordinals come in four common written forms:

- ``1º`` / ``1o`` — masculine ("primero")
- ``1ª`` / ``1a`` — feminine ("primera")
- ``1er`` / ``3er`` — apocope masculine ("primer", "tercer")
- ``1.º``, ``1.ª`` — variants with the indicator after a period (RAE)

We handle the bare-indicator forms (no period). The numeric range
covered is 1-999 — beyond that ordinals are vanishingly rare in chat
content and even native speakers reach for a workaround ("número
1234" rather than "milésimo ducentésimo trigésimo cuarto").

num2words supports ``to='ordinal'`` for Spanish but only emits the
masculine form. We post-edit for feminine and apocope variants.
"""

from __future__ import annotations

from .. import patterns as P

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


# Apocope: drop trailing ``-o`` of masculine ordinals when followed by a
# masculine singular noun. We don't know the noun here so we encode the
# apocope by the explicit ``er`` / ``r`` suffix the writer chose. Map
# masculine form → apocope form for the words that need it.
_ES_APOCOPE = {
    "primero": "primer",
    "tercero": "tercer",
}


# Masculine → feminine. Spanish ordinals form feminine by replacing the
# final ``o`` with ``a`` for the entire word; for compound ordinals
# (vigésimo primero) only the final part takes the feminine ending.
def _to_feminine(masc: str) -> str:
    if masc.endswith("o"):
        return masc[:-1] + "a"
    return masc


def expand_ordinals_es(text: str) -> str:
    """Expand 1º/1ª/1er/1o/1a forms in Spanish text. Other languages: no-op."""
    if not _HAS_NUM2WORDS:
        return text

    def _spell(n: int, suffix: str) -> str:
        try:
            masc = num2words(n, lang="es", to="ordinal")
        except (NotImplementedError, ValueError):
            return f"{n}{suffix}"
        if suffix in ("ª", "a"):
            return _to_feminine(masc)
        if suffix == "er":
            return _ES_APOCOPE.get(masc, masc)
        return masc

    def _replace(m):
        n = int(m.group(1))
        suffix = m.group(2)
        if not (1 <= n <= 999):
            return m.group(0)
        return _spell(n, suffix)

    return P.ORDINAL_ES.sub(_replace, text)


def expand_ordinals(text: str, lang: str) -> str:
    if lang == "spanish":
        return expand_ordinals_es(text)
    return text
