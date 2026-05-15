"""Emoji + Markdown stripping.

Both run before any semiotic-class expansion so that formatting markers
don't smuggle digits or punctuation past the bare-cardinal expander
("**100**" with the asterisks intact looks like a sentence terminator).
"""

from __future__ import annotations

import unicodedata
from typing import List

from .. import patterns as P


def strip_emojis(text: str) -> str:
    """Remove emoji, pictograph, dingbat, and zero-width formatting codepoints.

    Uses the Unicode general-category database so we don't need an
    external emoji table. ``So`` covers most emoji; ``Sk`` catches skin-
    tone modifiers; visible emoji codepoints are replaced with a space
    so "wow🔥cool" becomes "wow cool" rather than "wowcool" (the trailing
    whitespace cleanup pass collapses runs back to one). Variation
    selectors and zero-width glue codepoints are dropped silently —
    invisible by definition, no space replacement needed.
    """
    out: List[str] = []
    for c in text:
        cp = ord(c)
        # ``So`` is a coarse category — it covers pictographs (🔥) but
        # also textual symbols (°, ™, ©) that carry pronounceable
        # meaning downstream. Whitelist the latter so e.g. ``°C`` and
        # ``25°`` survive to the temperature pass.
        if c in _TEXT_SYMBOLS:
            out.append(c)
            continue
        cat = unicodedata.category(c)
        if cat in ("So", "Sk"):
            out.append(" ")
            continue
        if 0xFE00 <= cp <= 0xFE0F:  # variation selectors
            continue
        if cp in (0x200D, 0x2060, 0xFEFF):  # ZWJ, WJ, BOM
            continue
        out.append(c)
    return "".join(out)


_TEXT_SYMBOLS = frozenset("°™©®")


def strip_markdown(text: str) -> str:
    """Strip Markdown formatting markers, keeping the underlying text.

    Code blocks are removed entirely (rarely speech-friendly). Inline
    code keeps its contents. Links/images keep their alt text AND URL
    (the URL pass downstream vocalizes the URL — listeners hear the
    same information a sighted reader gets from the rendered link).
    Bold, italic, strikethrough markers are stripped while preserving
    content. Heading / blockquote / list markers are removed;
    horizontal rules are dropped.
    """
    text = P.MD_CODE_BLOCK.sub(" ", text)
    text = P.MD_IMAGE.sub(r"\1", text)
    text = P.MD_LINK.sub(r"\1 \2", text)
    text = P.MD_INLINE_CODE.sub(r"\1", text)
    text = P.MD_BOLD_ITALIC.sub(lambda m: m.group(2) or m.group(4), text)
    text = P.MD_HEADING.sub("", text)
    text = P.MD_BLOCKQUOTE.sub("", text)
    text = P.MD_HR.sub("", text)
    # List items: ensure the line before a list marker ends with a
    # sentence terminator. The pipeline's final whitespace collapse
    # otherwise merges "intro:\n1. foo\n2. bar" into one run-on
    # sentence the TTS reads without phrase breaks.
    text = P.LIST_ITEM_BREAK.sub(".\n", text)
    text = P.MD_LIST_BULLET.sub("", text)
    text = P.MD_LIST_NUM.sub("", text)
    # snake_case identifiers (``WAKE_WORD_MODEL_PATH``, ``dispatch_to_tmux``)
    # survive italic stripping by the non-word-boundary guard in
    # MD_BOLD_ITALIC. Replace their connecting underscores with a space
    # so the TTS reads "wake word model path", not letter-by-letter.
    # Edge underscores (``_fire_wake`` → ``fire wake``) drop too.
    text = P.SNAKE_UNDERSCORE.sub(" ", text)
    text = P.EDGE_UNDERSCORE.sub("", text)
    text = P.WORD_DOUBLE_HYPHEN.sub("-", text)
    return text
