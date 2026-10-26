"""
Shared text primitives for terminal presentation: ANSI-aware measurement,
clipping, padding, and the semantic `ui` palette. Both the static layer
(`cli` table/kv/tree) and the live layer (`cli.live`) build on these.

Same names and behaviour as ts-utils `cli/text`: width counts terminal cells,
so East Asian wide characters and wide emoji take two.
"""

import os
import sys
import unicodedata
from collections.abc import Callable, Iterator
from types import SimpleNamespace

from ..ansi import ANSI_RE, BOLD, DIM, RESET, color_asked, fg


def _color_enabled() -> bool:
    # The one rule (ansi.color_asked, the logger's too). cli writes to both
    # streams (static output to stdout, live regions to stderr), so when the
    # environment leaves it to the TTY, color requires BOTH to be TTYs: any
    # redirection means some cli string may land in a file.
    asked = color_asked(os.environ)
    return sys.stdout.isatty() and sys.stderr.isatty() if asked is None else asked


COLOR = _color_enabled()


def _paint(open_: str) -> Callable[[str], str]:
    if not COLOR:
        return lambda s: s
    return lambda s: f"{open_}{s}{RESET}"


bold = _paint(BOLD)
dim = _paint(DIM)
red = _paint(fg(1))
green = _paint(fg(2))
yellow = _paint(fg(3))
cyan = _paint(fg(6))
gray = _paint(fg(8))

_ZWJ = "‍"


def _joins(c: str) -> bool:
    """Code points that extend the previous grapheme instead of starting one."""
    o = ord(c)
    return (
        unicodedata.combining(c) != 0
        or unicodedata.category(c) in ("Mn", "Me")
        or 0xFE00 <= o <= 0xFE0F  # variation selectors
        or 0x1F3FB <= o <= 0x1F3FF  # skin tone modifiers
        or 0xE0020 <= o <= 0xE007F  # tag sequences (subdivision flags)
    )


def _regional(c: str) -> bool:
    return 0x1F1E6 <= ord(c) <= 0x1F1FF


def _graphemes(text: str) -> Iterator[tuple[str, int]]:
    """(cluster, terminal cells) for each user-perceived character: a ZWJ
    emoji family, a flag, a letter with its accents are one cluster. Plain
    text only: strip or split out ANSI escapes first."""
    i = 0
    n = len(text)
    while i < n:
        start = i
        i += 1
        if _regional(text[start]) and i < n and _regional(text[i]):
            i += 1
        while i < n and (_joins(text[i]) or text[i] == _ZWJ):
            if text[i] == _ZWJ and i + 1 < n:
                i += 2
            else:
                i += 1
        cluster = text[start:i]
        wide = unicodedata.east_asian_width(cluster[0]) in ("W", "F")
        yield cluster, 2 if wide or _regional(cluster[0]) else 1


def width(s: str) -> int:
    """Visible width of a string in terminal cells, ANSI escapes stripped."""
    return sum(cells for _, cells in _graphemes(ANSI_RE.sub("", s)))


def clip(s: str, n: int) -> str:
    """Truncate to `n` visible cells (ellipsis at the cut), ANSI-aware:
    escape sequences pass through so styling survives, and an open style is
    closed with a final reset. Plain strings work too: this is THE truncate."""
    if width(s) <= n:
        return s
    out: list[str] = []
    used = 0
    styled = False
    cut = False
    pos = 0
    for m in [*ANSI_RE.finditer(s), None]:
        chunk = s[pos : m.start()] if m else s[pos:]
        for cluster, cells in _graphemes(chunk):
            if cut:
                break
            if used + cells <= n - 1:
                out.append(cluster)
                used += cells
            else:
                out.append("…")
                cut = True
        if m:
            out.append(m.group())
            styled = True
            pos = m.end()
    text = "".join(out)
    # close any open style, without doubling a reset the input already ends on
    return f"{text}{RESET}" if styled and not text.endswith(RESET) else text


def pad_end(s: str, n: int) -> str:
    return s + " " * max(0, n - width(s))


def pad_start(s: str, n: int) -> str:
    return " " * max(0, n - width(s)) + s


# Semantic palette: use these, not raw colors, so intent stays consistent.
ui = SimpleNamespace(
    head=bold,
    accent=cyan,
    muted=dim,
    ok=green,
    warn=yellow,
    bad=red,
    ref=gray,  # ids / refs, de-emphasized
)
