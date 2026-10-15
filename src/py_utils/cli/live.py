"""
`live`: a pinned, self-repainting terminal region, the pure widgets that
animate inside it (`spin` / `bar` / `elapsed`), and the `spinner()` one-liner.

The model: you own the state, the region owns the screen. A region is a
`render() -> str` repainted on a timer (plus `refresh()` for instant updates).
A frame is just a string, so `table()` / `kv()` / `ui` compose inside it
unchanged, and widgets are plain string functions.

The hard problem this solves is interleaving: while a region is active,
`sys.stdout` and `sys.stderr` are replaced by proxies that print each complete
line ABOVE the region (erase, write, repaint). The logger writes through
`sys.stderr`, so logging never tears the UI, and there is no new logging API.

Threads are first-class: workers mutate the state the render reads and log
from anywhere; painting and routed writes share one lock. A render that raises
stops the repainting and the error is raised again by `done()`.

Non-TTY (pipe / CI / log file): nothing animates, nothing repaints.
`done(final)` prints the final frame once; the opt-in `heartbeat` (seconds)
prints plain snapshots for long CI silences. Same calling code either way.

The cursor is hidden while painting and restored on done/clear and at exit.
Exactly one region can be active: two pinned regions can't share the bottom of
one screen. Compose everything into a single `render()`.

Same names and behaviour as ts-utils `cli/live`. Python additions: `live()`
is also a context manager (done on exit, with the error re-raised), and
`spinner()` is a `with` block yielding the relabel function.
"""

from __future__ import annotations

import atexit
import os
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TextIO

from ..offensive import invariant, require
from .text import clip, cyan, dim, green, red

HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
# Synchronized-update markers: modern terminals (iTerm2, kitty, Ghostty,
# WezTerm, recent Terminal.app) paint the wrapped write atomically, no flicker
# on erase+rewrite. Unknown CSIs are ignored elsewhere, so always emit them.
SYNC_ON = "\x1b[?2026h"
SYNC_OFF = "\x1b[?2026l"

_LOCK = threading.RLock()
_active: Live | None = None


def _wipe(n: int) -> str:
    """Cursor to the first line of an `n`-line region + erase to end of screen."""
    return f"\x1b[{n}F\x1b[J" if n > 0 else ""


class _Routed:
    """Stands in for sys.stdout / sys.stderr while a region is active: each
    complete line is written above the region. A partial line waits for its
    newline (print() writes the text and the newline separately)."""

    def __init__(self, region: Live, target: TextIO):
        self._region = region
        self._target = target
        self._pending = ""

    def write(self, s: str) -> int:
        self._pending += s
        if "\n" in self._pending:
            complete, _, self._pending = self._pending.rpartition("\n")
            self._region._above(self._target, complete + "\n")
        return len(s)

    def flush(self) -> None:
        pass

    def drain(self) -> None:
        if self._pending:
            self._target.write(self._pending)
            self._pending = ""

    def __getattr__(self, name: str):
        return getattr(self._target, name)


class Live:
    """A pinned region; create it with `live()`."""

    def __init__(
        self,
        render: Callable[[], str],
        stream: TextIO | None = None,
        fps: float = 12.5,
        heartbeat: float | None = None,
    ):
        self._render = render
        self._stream = stream or sys.stderr
        self._tty = self._stream.isatty()
        # The lines on screen: what a routed write redraws, and how many to wipe
        self._shown: list[str] = []
        self._stopped = False
        self._error: BaseException | None = None
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._routed: tuple[TextIO, TextIO] | None = None

        if not self._tty:
            if heartbeat:
                self._thread = self._loop(heartbeat, self._snapshot)
            return

        global _active
        with _LOCK:
            require(
                _active is None,
                "one live region at a time: compose into a single render()",
            )
            _active = self
        self._route()
        atexit.register(self._restore_cursor)
        self._stream.write(HIDE_CURSOR)
        self._paint()
        self._thread = self._loop(1 / fps, self._paint)

    def refresh(self) -> None:
        """Repaint now (state changed and 80ms is too long to wait)."""
        if self._tty and not self._stopped:
            self._paint()

    def update(self, render: Callable[[], str]) -> None:
        """Swap the render function (e.g. a new phase of the same operation)."""
        self._render = render
        self.refresh()

    def done(self, final: str | None = None) -> None:
        """Stop and persist a final frame (default: the current render) into
        scrollback. Raises what a render raised while painting."""
        require(not self._stopped, "live region already stopped")
        frame = final if final is not None else self._render()
        self._stop()
        if self._tty:
            self._stream.write(f"{_wipe(len(self._shown))}{frame}\n{SHOW_CURSOR}")
        else:
            self._stream.write(f"{frame}\n")
        self._stream.flush()
        if self._error:
            raise self._error

    def clear(self) -> None:
        """Stop and remove the region entirely."""
        require(not self._stopped, "live region already stopped")
        self._stop()
        if self._tty:
            self._stream.write(_wipe(len(self._shown)) + SHOW_CURSOR)
            self._stream.flush()
        if self._error:
            raise self._error

    def __enter__(self) -> Live:
        return self

    def __exit__(self, kind, error, tb) -> None:
        if not self._stopped:
            self.done()

    # --- internals ---

    def _loop(self, every: float, tick: Callable[[], None]) -> threading.Thread:
        def run() -> None:
            while not self._wake.wait(every):
                try:
                    tick()
                except BaseException as e:  # noqa: BLE001 - re-raised by done()
                    self._error = e
                    return

        thread = threading.Thread(target=run, name="py_utils.cli.live", daemon=True)
        thread.start()
        return thread

    def _snapshot(self) -> None:
        self._stream.write(f"{self._render()}\n")
        self._stream.flush()

    def _frame(self) -> list[str]:
        """The current render, fitted to the terminal. Only `_paint` calls it,
        outside the lock and never from inside a routed write: a render may
        log, and the logger holds its non-reentrant write lock while writing
        into the routed stream. Rendering there would make the render's own
        log line wait on itself; rendering under this lock would invert the
        two locks' order."""
        try:
            cols, rows = os.get_terminal_size(self._stream.fileno())
        except OSError:
            cols, rows = 80, 24
        # A sizeless PTY reports 0x0; clip each line to the width (a wrapped
        # line breaks the erase math) and keep the BOTTOM rows-1 lines, the
        # latest activity, so an oversized frame degrades.
        cols, rows = cols or 80, rows or 24
        lines = [clip(line, cols - 1) for line in self._render().split("\n")]
        return lines if len(lines) < rows else lines[len(lines) - (rows - 1) :]

    def _draw(self, frame: list[str]) -> str:
        """Escapes that replace what is on screen with `frame`."""
        body = "".join(f"{line}\n" for line in frame)
        return f"{_wipe(len(self._shown))}{body}"

    def _paint(self) -> None:
        frame = self._frame()
        with _LOCK:
            if self._stopped:
                return
            self._stream.write(f"{SYNC_ON}{self._draw(frame)}{SYNC_OFF}")
            self._stream.flush()
            self._shown = frame

    def _above(self, target: TextIO, text: str) -> None:
        """Erase the region, write, redraw the frame underneath, as one sync
        block. Redraws what is shown, never renders (see `_frame`); the next
        tick brings the frame up to date."""
        with _LOCK:
            if self._stopped:
                target.write(text)
                target.flush()
                return
            shown = self._shown
            self._stream.write(SYNC_ON + _wipe(len(shown)))
            self._stream.flush()
            target.write(text)
            target.flush()
            self._stream.write("".join(f"{line}\n" for line in shown) + SYNC_OFF)
            self._stream.flush()

    def _route(self) -> None:
        self._routed = (sys.stdout, sys.stderr)
        sys.stdout = _Routed(self, self._routed[0])  # type: ignore[assignment]
        sys.stderr = _Routed(self, self._routed[1])  # type: ignore[assignment]

    def _restore_cursor(self) -> None:
        self._stream.write(SHOW_CURSOR)
        self._stream.flush()

    def _stop(self) -> None:
        global _active
        with _LOCK:
            self._stopped = True
            self._wake.set()
            if self._routed:
                routed_out, routed_err = sys.stdout, sys.stderr
                sys.stdout, sys.stderr = self._routed
                for proxy in (routed_out, routed_err):
                    if isinstance(proxy, _Routed):
                        proxy.drain()
                self._routed = None
            if self._tty:
                invariant(_active is self, "a different live region was active")
                _active = None
                atexit.unregister(self._restore_cursor)
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join()


def live(
    render: Callable[[], str],
    stream: TextIO | None = None,
    fps: float = 12.5,
    heartbeat: float | None = None,
) -> Live:
    """Start a pinned region at the bottom of the terminal, repainting
    `render()` until `done()` / `clear()`. Default stream stderr, so stdout
    stays clean for pipes and --json. Non-TTY: inert (see module doc)."""
    return Live(render, stream, fps, heartbeat)


# --- widgets: pure string builders, animated by being re-rendered ---

_SPIN_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def spin() -> str:
    """Spinner frame for "now": call it inside `render()` and it animates."""
    return cyan(_SPIN_FRAMES[int(time.time() / 0.08) % len(_SPIN_FRAMES)])


def bar(
    done: int | float,
    total: int | float,
    width: int = 24,
    style: Callable[[str], str] = green,
) -> str:
    """Progress bar, `width` cells; `style` colors the filled part (pass e.g.
    `ui.warn` for a throttled state). `done > total` clamps to full: live
    counters drift, and that's the caller's data, not a bug here."""
    require(done >= 0 and total >= 0, "bar: negative counts", done=done, total=total)
    fill = round(min(1, 1 if total == 0 else done / total) * width)
    return style("█" * fill) + dim("░" * (width - fill))


def elapsed(since: float) -> str:
    """Compact time since a `time.monotonic()` reading: 0.4s · 12s · 1m05s · 1h02m."""
    s = time.monotonic() - since
    if s < 10:
        return f"{s:.1f}s"
    r = round(s)
    if r < 60:
        return f"{r}s"
    m = r // 60
    if m < 60:
        return f"{m}m{r % 60:02d}s"
    return f"{m // 60}h{m % 60:02d}m"


@contextmanager
def spinner(label: str) -> Iterator[Callable[[str], None]]:
    """Animate `label` with a spinner + elapsed time while the block runs,
    persist `✓ label 1.2s` on success, `⨯ label 1.2s message` on failure (and
    re-raise). Yields a setter for relabeling mid-flight:

        with spinner("connecting 0/4") as set_label:
            ...
            set_label("connecting 2/4")

    Non-TTY prints just the final line. Under an active region it does not
    open a second one: the final line lands above the region."""
    start = time.monotonic()
    current = [label]

    def set_label(new: str) -> None:
        current[0] = new

    region = (
        live(lambda: f"{spin()} {current[0]} {dim(elapsed(start))}")
        if _active is None
        else None
    )

    def persist(line: str) -> None:
        if region:
            region.done(line)
        else:
            sys.stderr.write(line + "\n")

    try:
        yield set_label
    except BaseException as e:
        message = str(e) or type(e).__name__
        persist(f"{red('⨯')} {current[0]} {dim(elapsed(start))} {red(message)}")
        raise
    persist(f"{green('✓')} {current[0]} {dim(elapsed(start))}")
