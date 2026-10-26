"""
Raw ANSI escape primitives: ALWAYS ON, no TTY detection, no env checks.

The vocabulary, not the policy. `cli` decides WHETHER to color (TTY,
NO_COLOR, FORCE_COLOR) and builds semantics on top; this module is for output
whose consumer renders ANSI regardless of what stdout is: Claude Code status
lines, tmux status strings, files a terminal will cat. A TTY-gated palette
emits nothing through those pipes, which is exactly wrong there.

256-color escapes (`fg`/`bg`) over 24-bit as the house default: the xterm cube
is stable across every terminal and multiplexer, while 24-bit gets quantized
or dropped by tmux/screen configs. `rgb` exists for when the consumer is known
to render truecolor.

Same names and behaviour as ts-utils `ansi`.
"""

import re
from collections.abc import Mapping

from .offensive import require


def color_asked(env: Mapping[str, str]) -> bool | None:
    """What the environment says about colour, before any TTY is asked: True
    forced on, False forced off, None for the TTY to decide. The one rule every
    library keeps (utils' README, "Rendering"; its harness checks it), and the
    one function both `log` and `cli` call: `FORCE_COLOR` decides when not
    empty (`0` or `false` off, anything else on), then `NO_COLOR` not empty
    turns it off, as does `TERM=dumb`. An empty variable is an unset one.
    Takes the environment rather than reading it: this module reads none."""
    force = env.get("FORCE_COLOR")
    if force:
        return force not in ("0", "false")
    if env.get("NO_COLOR") or env.get("TERM") == "dumb":
        return False
    return None


RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
ITALIC = "\x1b[3m"
UNDERLINE = "\x1b[4m"


def fg(n: int) -> str:
    """Foreground, xterm-256 palette index."""
    require(isinstance(n, int) and 0 <= n <= 255, "xterm-256 index", n=n)
    return f"\x1b[38;5;{n}m"


def bg(n: int) -> str:
    """Background, xterm-256 palette index."""
    require(isinstance(n, int) and 0 <= n <= 255, "xterm-256 index", n=n)
    return f"\x1b[48;5;{n}m"


def rgb(r: int, g: int, b: int) -> str:
    """Foreground, 24-bit: only when the consumer is known to render truecolor."""
    require(
        all(isinstance(v, int) and 0 <= v <= 255 for v in (r, g, b)),
        "rgb components",
        r=r,
        g=g,
        b=b,
    )
    return f"\x1b[38;2;{r};{g};{b}m"


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(s: str) -> str:
    """The string minus its ANSI style escapes."""
    return ANSI_RE.sub("", s)


__all__ = [
    "RESET",
    "BOLD",
    "DIM",
    "ITALIC",
    "UNDERLINE",
    "fg",
    "bg",
    "rgb",
    "ANSI_RE",
    "strip_ansi",
]
