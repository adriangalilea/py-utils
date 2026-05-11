"""Hashtags (``#hashtag``) and mentions (``@user``).

Social-media surface. Conventions:

- **Hashtags**: Spanish reads ``#`` as "almohadilla" (RAE) or "hashtag"
  (informal). We pick "etiqueta" for chat content — it's the cleanest
  spoken form. English: "hashtag". Then the tag body reads as the word.
- **Mentions**: ``@`` reads as "arroba" / "at" — same word as in URL
  vocalization. The handle body reads as a word.

CamelCase / kebab-case / snake_case handle bodies are intentionally NOT
split into separate words — TTS reads them better as a single token,
and splitting introduces its own ambiguities ("HelloWorld" → "Hello
World" vs "hello world" vs "helloworld").
"""

from __future__ import annotations

import re

from ..tables import AT_SIGN_WORD

_HASHTAG = re.compile(r"(?<![\w&])#([A-Za-z][A-Za-z0-9_]+)\b")
_MENTION = re.compile(r"(?<![\w@])@([A-Za-z][A-Za-z0-9_]+)\b")

_HASHTAG_WORD = {
    "spanish":    "etiqueta",
    "english":    "hashtag",
    "french":     "mot-clé",
    "german":     "Hashtag",
    "italian":    "hashtag",
    "portuguese": "hashtag",
}


def expand_hashtags(text: str, lang: str) -> str:
    word = _HASHTAG_WORD.get(lang)
    if not word:
        return text
    return _HASHTAG.sub(rf"{word} \1", text)


def expand_mentions(text: str, lang: str) -> str:
    word = AT_SIGN_WORD.get(lang)
    if not word:
        return text
    return _MENTION.sub(rf"{word} \1", text)
