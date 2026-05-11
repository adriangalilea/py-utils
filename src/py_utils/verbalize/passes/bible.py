"""Bible references (``Génesis 1:1-5`` → "Génesis, capítulo uno, versículos uno al cinco").

Common in religious / literary content. Spanish bot ``/test`` reads
Génesis 1:1-5; without this pass it gets rendered as
"Génesis uno dos puntos uno guión cinco" — barely intelligible.

Pattern: ``<book> <chapter>:<verse>[-<verse_end>]``. Book names come
from a known list (Spanish + English standard names, including
deutero-canonical and the common ordinal-prefixed books like
"1 Corintios" / "1 Corinthians"). Single-chapter books (Filemón,
Judas, 3 Juan…) accept either ``<book> <verse>`` or
``<book> 1:<verse>`` forms.

Per-language phrasing:

- Spanish: ``Génesis, capítulo uno, versículo uno`` /
  ``Génesis, capítulo uno, versículos uno al cinco``.
- English: ``Genesis chapter one, verse one`` /
  ``Genesis chapter one, verses one through five``.

Runs BEFORE the bare-cardinal expander so the digit groups inside the
reference are consumed atomically. Names with leading ordinal
("1 Corintios") match by greedy prefix; the ordinal stays in the
spoken form ("uno Corintios capítulo…").
"""

from __future__ import annotations

import re
from typing import List

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


# Standard Spanish + English book names. Order matters in the regex
# alternation: longer / more specific first. Ordinal-prefixed books
# share the same shape ("1 Corintios" / "1 Corinthians") — the leading
# digit is matched as part of the book token.
_BOOKS_ES = [
    "Génesis",
    "Éxodo",
    "Levítico",
    "Números",
    "Deuteronomio",
    "Josué",
    "Jueces",
    "Rut",
    "1 Samuel",
    "2 Samuel",
    "1 Reyes",
    "2 Reyes",
    "1 Crónicas",
    "2 Crónicas",
    "Esdras",
    "Nehemías",
    "Tobías",
    "Judit",
    "Ester",
    "1 Macabeos",
    "2 Macabeos",
    "Job",
    "Salmos",
    "Salmo",
    "Proverbios",
    "Eclesiastés",
    "Cantares",
    "Sabiduría",
    "Eclesiástico",
    "Isaías",
    "Jeremías",
    "Lamentaciones",
    "Baruc",
    "Ezequiel",
    "Daniel",
    "Oseas",
    "Joel",
    "Amós",
    "Abdías",
    "Jonás",
    "Miqueas",
    "Nahúm",
    "Habacuc",
    "Sofonías",
    "Hageo",
    "Zacarías",
    "Malaquías",
    "Mateo",
    "Marcos",
    "Lucas",
    "Juan",
    "Hechos",
    "Romanos",
    "1 Corintios",
    "2 Corintios",
    "Gálatas",
    "Efesios",
    "Filipenses",
    "Colosenses",
    "1 Tesalonicenses",
    "2 Tesalonicenses",
    "1 Timoteo",
    "2 Timoteo",
    "Tito",
    "Filemón",
    "Hebreos",
    "Santiago",
    "1 Pedro",
    "2 Pedro",
    "1 Juan",
    "2 Juan",
    "3 Juan",
    "Judas",
    "Apocalipsis",
]

_BOOKS_EN = [
    "Genesis",
    "Exodus",
    "Leviticus",
    "Numbers",
    "Deuteronomy",
    "Joshua",
    "Judges",
    "Ruth",
    "1 Samuel",
    "2 Samuel",
    "1 Kings",
    "2 Kings",
    "1 Chronicles",
    "2 Chronicles",
    "Ezra",
    "Nehemiah",
    "Tobit",
    "Judith",
    "Esther",
    "1 Maccabees",
    "2 Maccabees",
    "Job",
    "Psalms",
    "Psalm",
    "Proverbs",
    "Ecclesiastes",
    "Song of Songs",
    "Song of Solomon",
    "Wisdom",
    "Sirach",
    "Isaiah",
    "Jeremiah",
    "Lamentations",
    "Baruch",
    "Ezekiel",
    "Daniel",
    "Hosea",
    "Joel",
    "Amos",
    "Obadiah",
    "Jonah",
    "Micah",
    "Nahum",
    "Habakkuk",
    "Zephaniah",
    "Haggai",
    "Zechariah",
    "Malachi",
    "Matthew",
    "Mark",
    "Luke",
    "John",
    "Acts",
    "Romans",
    "1 Corinthians",
    "2 Corinthians",
    "Galatians",
    "Ephesians",
    "Philippians",
    "Colossians",
    "1 Thessalonians",
    "2 Thessalonians",
    "1 Timothy",
    "2 Timothy",
    "Titus",
    "Philemon",
    "Hebrews",
    "James",
    "1 Peter",
    "2 Peter",
    "1 John",
    "2 John",
    "3 John",
    "Jude",
    "Revelation",
]


def _compile_pattern(books: List[str]) -> re.Pattern:
    # Longer first so "1 Corintios" matches before "Corintios"-alone
    sorted_books = sorted(books, key=len, reverse=True)
    book_alt = "|".join(re.escape(b) for b in sorted_books)
    # <book> <chapter>:<verse>[-<verse_end>]
    return re.compile(rf"\b({book_alt})\s+(\d{{1,3}}):(\d{{1,3}})(?:-(\d{{1,3}}))?\b")


_PATTERN_ES = _compile_pattern(_BOOKS_ES)
_PATTERN_EN = _compile_pattern(_BOOKS_EN)


_PHRASING = {
    "spanish": {
        "chapter": ", capítulo {ch}",
        "verse_one": ", versículo {v1}",
        "verse_many": ", versículos {v1} al {v2}",
    },
    "english": {
        "chapter": " chapter {ch}",
        "verse_one": ", verse {v1}",
        "verse_many": ", verses {v1} through {v2}",
    },
}


def expand_bible_refs(text: str, lang: str) -> str:
    if not _HAS_NUM2WORDS:
        return text
    if lang == "spanish":
        pattern = _PATTERN_ES
        iso = "es"
    elif lang == "english":
        pattern = _PATTERN_EN
        iso = "en"
    else:
        return text
    phrasing = _PHRASING[lang]

    def _spell(n: int) -> str:
        try:
            return num2words(n, lang=iso)
        except (NotImplementedError, ValueError):
            return str(n)

    def _replace(m):
        book = m.group(1)
        ch = int(m.group(2))
        v1 = int(m.group(3))
        v2 = m.group(4)
        chapter_part = phrasing["chapter"].format(ch=_spell(ch))
        if v2 is None:
            verse_part = phrasing["verse_one"].format(v1=_spell(v1))
        else:
            verse_part = phrasing["verse_many"].format(
                v1=_spell(v1), v2=_spell(int(v2))
            )
        return f"{book}{chapter_part}{verse_part}"

    return pattern.sub(_replace, text)
