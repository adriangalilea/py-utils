"""
`cli`: terminal presentation. Aligned tables, key/value blocks, trees, a
semantic palette, and live output (pinned region, spinner, progress bar).
Separate from `format` (universal value formatting): this is terminal-scoped.

Colors are gated in `cli.text` (TTY + NO_COLOR / FORCE_COLOR) on the `ansi`
vocabulary, so a `table()` renders colored in a terminal and as plain aligned
text in a pipe, a log file, or a bot's monospace block. Alignment is
ANSI-aware: padding uses the visible width, so colored cells line up.

    from py_utils.cli import table, kv, ui

    print(table(
        [["Ada", ui.accent("ada@x.com"), ui.muted("work")],
         ["Bo",  ui.accent("bo@y.com"),  ui.muted("home")]],
        head=["name", "email", "label"],
    ))

Same names and behaviour as ts-utils `cli` (options are keyword arguments).
"""

from collections.abc import Sequence

from .live import Live, bar, elapsed, live, spin, spinner
from .text import clip, pad_end, pad_start, ui, width


def table(
    rows: Sequence[Sequence[str]],
    *,
    head: Sequence[str] | None = None,
    align: Sequence[str] | None = None,
    gap: int = 2,
    indent: int = 0,
) -> str:
    """Rows as aligned columns. Cells may be pre-colored: widths use visible
    length so colored columns still line up. `align` is "l" or "r" per column
    (default all left). The last left-aligned column isn't right-padded, so
    no line carries trailing whitespace."""
    body = [list(head), *map(list, rows)] if head else [list(r) for r in rows]
    cols = max((len(r) for r in body), default=0)
    widths = [
        max((width(r[c]) for r in body if c < len(r)), default=0) for c in range(cols)
    ]
    sep = " " * gap
    lead = " " * indent

    def line(r: Sequence[str]) -> str:
        cells = []
        for c in range(cols):
            cell = r[c] if c < len(r) else ""
            if align and c < len(align) and align[c] == "r":
                cells.append(pad_start(cell, widths[c]))
            elif c == cols - 1:
                cells.append(cell)
            else:
                cells.append(pad_end(cell, widths[c]))
        return (lead + sep.join(cells)).rstrip()

    out = [line([ui.head(h) for h in head])] if head else []
    out.extend(line(r) for r in rows)
    return "\n".join(out)


def kv(pairs: Sequence[tuple[str, str]], *, indent: int = 0, gap: int = 2) -> str:
    """Key/value block with aligned keys, e.g. for a detail view."""
    w = max((width(k) for k, _ in pairs), default=0)
    lead = " " * indent
    return "\n".join(f"{lead}{ui.muted(pad_end(k, w))}{' ' * gap}{v}" for k, v in pairs)


def indent(s: str, n: int) -> str:
    """Indent every line of a (possibly multi-line) string by `n` spaces."""
    return "\n".join(" " * n + line for line in s.split("\n"))


def tree(label: str, children: Sequence[str], *, indent: int = 0) -> str:
    """A labeled node with child lines drawn under it."""
    lead = " " * indent
    return "\n".join([lead + label, *(f"{lead}  {c}" for c in children)])


__all__ = [
    "table",
    "kv",
    "indent",
    "tree",
    "ui",
    "width",
    "clip",
    "pad_end",
    "pad_start",
    "live",
    "Live",
    "spinner",
    "spin",
    "bar",
    "elapsed",
]
