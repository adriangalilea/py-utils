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
        cat = unicodedata.category(c)
        if cat in ("So", "Sk"):
            out.append(" ")
            continue
        cp = ord(c)
        if 0xFE00 <= cp <= 0xFE0F:  # variation selectors
            continue
        if cp in (0x200D, 0x2060, 0xFEFF):  # ZWJ, WJ, BOM
            continue
        out.append(c)
    return "".join(out)


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
    text = P.MD_BOLD_ITALIC.sub(r"\2", text)
    text = P.MD_HEADING.sub("", text)
    text = P.MD_BLOCKQUOTE.sub("", text)
    text = P.MD_HR.sub("", text)
    text = P.MD_LIST_BULLET.sub("", text)
    text = P.MD_LIST_NUM.sub("", text)
    return text
