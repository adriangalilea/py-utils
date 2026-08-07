"""
The terminal-first, file-honest logger.

Doctrine (shared with go-utils and ts-utils, each in its own idiom):

Two independent decisions, both automatic, both forceable from the environment:

    LOG_FORMAT=human|record  how lines render. Default: human when stderr is a
                             TTY (symbols, color, indentation), record when it
                             is not (level words, plain text).
    LOG_TIME=1|0             whether lines open with time. Default: on in
                             record, off in human.

A file collecting evidence gets the full instant, 2026-08-07T12:34:56Z, UTC,
because a triage line whose age is unknowable is worthless. A human who turns
time on gets a dim local 14:32:56, because they know today's date. LOG_TIME=0
in record mode is for sinks that stamp lines themselves (journald, Cloudflare).
NO_COLOR/FORCE_COLOR only affect color inside human rendering.

The record line is identical across the three languages by design, so logs
from mixed-language systems share one grep surface:

    2026-08-07T12:34:56Z WARN  [theater] scan failed: EOF

UTC RFC3339, level word padded to five columns, scope in brackets when
present. Level words instead of symbols: `rg WARN` beats `rg ⚠`.

Levels filter noise: silent < error < warn < info < debug < trace, read live
from LOG_LEVEL. An unknown level, format or time value raises: a confused
program should scream. Verbs express outcome and are renderings, never
levels: success ✓, ready ▶, wait ○, step • render at info; fail ⨯ at error.

scope() is the one composition primitive: log.scope("stt") returns a child
that prints [stt] and reads STT_LOG_LEVEL before LOG_LEVEL, so one subsystem
can be silenced or opened from the environment without touching code. Scopes
nest; the most specific level wins.

Structure stays first-class: task(title) logs start and end with duration and
indents its body, section(title) groups without timing, step() is the
indented bullet, progress() counts with a live line on a TTY and one honest
summary line anywhere else. In record mode indentation and live updates stand
down; the open/close lines remain, and under timestamps they become tracing.

Everything goes to stderr. stdout is reserved for data, so piping a tool's
output never chokes on a log line.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

_LEVELS = {"silent": 0, "error": 1, "warn": 2, "info": 3, "debug": 4, "trace": 5}
_WORDS = {
    "error": "ERROR",
    "warn": "WARN",
    "info": "INFO",
    "debug": "DEBUG",
    "trace": "TRACE",
}

_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"

# verb -> (level, symbol, ansi color)
_VERBS = {
    "error": ("error", "⨯", "\x1b[31m"),
    "fail": ("error", "⨯", "\x1b[31m"),
    "warn": ("warn", "⚠", "\x1b[33m"),
    "info": ("info", " ", "\x1b[37m"),
    "success": ("info", "✓", "\x1b[32m"),
    "wait": ("info", "○", "\x1b[37m"),
    "ready": ("info", "▶", "\x1b[32m"),
    "step": ("info", "•", "\x1b[90m"),
    "section": ("info", "▸", "\x1b[90m"),
    "debug": ("debug", "◦", "\x1b[90m"),
    "trace": ("trace", "»", "\x1b[35m"),
}

_WARN_ONCE_CAP = 1024


def _parse_level(value: str) -> int:
    level = _LEVELS.get(value.lower())
    if level is None:
        raise ValueError(
            f"unknown log level: {value} (want silent/error/warn/info/debug/trace)"
        )
    return level


def _stderr_tty() -> bool:
    try:
        return sys.stderr.isatty()
    except Exception:
        return False


def _color() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    return _stderr_tty()


class _Output:
    """The two per-process decisions, resolved once: stderr does not change
    class mid-run, and deciding per line would tax every call."""

    def __init__(self) -> None:
        self._resolved = False
        self.record = False
        self.timestamps = False

    def resolve(self) -> None:
        if self._resolved:
            return
        fmt = os.getenv("LOG_FORMAT", "")
        if fmt == "":
            self.record = not _stderr_tty()
        elif fmt == "human":
            self.record = False
        elif fmt == "record":
            self.record = True
        else:
            raise ValueError(f"unknown LOG_FORMAT: {fmt} (want human/record)")

        logtime = os.getenv("LOG_TIME", "")
        if logtime == "":
            self.timestamps = self.record
        elif logtime in ("1", "true"):
            self.timestamps = True
        elif logtime in ("0", "false"):
            self.timestamps = False
        else:
            raise ValueError(f"unknown LOG_TIME: {logtime} (want 1/0)")
        self._resolved = True

    def set_format(self, fmt: str) -> None:
        self.resolve()
        if fmt not in ("human", "record"):
            raise ValueError(f"unknown log format: {fmt} (want human/record)")
        self.record = fmt == "record"

    def set_time(self, enabled: bool) -> None:
        self.resolve()
        self.timestamps = bool(enabled)


_OUTPUT = _Output()


def record_line(t: datetime, level_word: str, scope: str, message: str) -> str:
    """Pure, so the format stays testable against the golden line the three
    sibling libraries share."""
    line = (
        t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        + " "
        + f"{level_word:<5}"
    )
    if scope:
        line += f" [{scope}]"
    return line + " " + message


class _State(threading.local):
    def __init__(self) -> None:
        super().__init__()
        self.indent: int = 0


_STATE = _State()


def _dur(ms: float) -> str:
    if ms >= 10_000:
        return f"{ms / 1000:.1f}s"
    return f"{ms:.0f}ms"


class Logger:
    def __init__(self, *, _scope: tuple[str, ...] = ()) -> None:
        self._scope = _scope
        self._warn_once: set[str] = set()
        self._timers: dict[str, float] = {}
        self._level_override: str | None = None
        self.show_tracebacks = True

    # ----- composition -----
    def scope(self, name: str) -> "Logger":
        """Child that prints [name] and resolves {NAME}_LOG_LEVEL first."""
        return Logger(_scope=self._scope + (name,))

    # ----- configuration -----
    def set_level(self, level: str) -> None:
        _parse_level(level)
        self._level_override = level.lower()

    def set_log_format(self, fmt: str) -> None:
        _OUTPUT.set_format(fmt)

    def set_log_time(self, enabled: bool) -> None:
        _OUTPUT.set_time(enabled)

    # ----- filtering -----
    def _threshold(self) -> int:
        if self._level_override is not None:
            return _LEVELS[self._level_override]
        for seg in reversed(self._scope):
            key = "".join(c if c.isalnum() else "_" for c in seg.upper())
            value = os.getenv(f"{key}_LOG_LEVEL")
            if value:
                return _parse_level(value)
        return _parse_level(os.getenv("LOG_LEVEL", "info"))

    def _on(self, level: str) -> bool:
        return _LEVELS[level] <= self._threshold()

    # ----- the one write door -----
    def _write(self, verb: str, message: Any) -> None:
        level, symbol, color = _VERBS[verb]
        if not self._on(level):
            return
        _OUTPUT.resolve()
        text = str(message)
        scope = " ".join(self._scope)

        if _OUTPUT.record:
            line = f"{_WORDS[level]:<5}" + (f" [{scope}]" if scope else "") + " " + text
            if _OUTPUT.timestamps:
                line = (
                    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    + " "
                    + line
                )
            sys.stderr.write(line + "\n")
            sys.stderr.flush()
            return

        color_on = _color()
        parts: list[str] = []
        if _OUTPUT.timestamps:
            stamp = time.strftime("%H:%M:%S")
            parts.append(f"{_DIM}{stamp}{_RESET} " if color_on else stamp + " ")
        if _STATE.indent:
            parts.append("  " * _STATE.indent)
        if verb == "step":
            parts.append("  ")
        sym = (
            f"{color}{_BOLD}{symbol}{_RESET}" if color_on and symbol.strip() else symbol
        )
        parts.append(sym + " ")
        if scope:
            tag = f"[{scope}]"
            parts.append((f"{_DIM}{tag}{_RESET}" if color_on else tag) + " ")
        parts.append(text)
        sys.stderr.write("".join(parts) + "\n")
        sys.stderr.flush()

    # ----- verbs -----
    def trace(self, message: Any) -> None:
        self._write("trace", message)

    def debug(self, message: Any) -> None:
        self._write("debug", message)

    def info(self, message: Any) -> None:
        self._write("info", message)

    def warn(self, message: Any) -> None:
        self._write("warn", message)

    def warn_once(self, message: Any) -> None:
        key = str(message)
        if key in self._warn_once:
            return
        # Bounded: a daemon emitting unbounded distinct warnings must not
        # leak; on overflow the set purges and an old warning firing once
        # more is the honest failure mode.
        if len(self._warn_once) >= _WARN_ONCE_CAP:
            self._warn_once.clear()
        self._warn_once.add(key)
        self.warn(message)

    def error(self, msg_or_exc: Any, *, exc: bool | None = None) -> None:
        self._write("error", msg_or_exc)
        want_tb = exc or isinstance(msg_or_exc, BaseException)
        if want_tb and self.show_tracebacks:
            for line in traceback.format_exc().strip().splitlines():
                self.step(line)

    def success(self, message: Any) -> None:
        self._write("success", message)

    def fail(self, message: Any) -> None:
        self._write("fail", message)

    def wait(self, message: Any) -> None:
        self._write("wait", message)

    def ready(self, message: Any) -> None:
        self._write("ready", message)

    def step(self, message: Any) -> None:
        self._write("step", message)

    # ----- structure -----
    @contextmanager
    def section(self, title: str):
        self._write("section", title)
        _STATE.indent += 1
        try:
            yield
        finally:
            _STATE.indent -= 1

    @contextmanager
    def task(self, title: str):
        start = time.perf_counter()
        self._write("wait", title)
        _STATE.indent += 1
        failed = False
        try:
            yield
        except BaseException:
            failed = True
            raise
        finally:
            _STATE.indent -= 1
            ms = (time.perf_counter() - start) * 1000.0
            if failed:
                self._write("fail", f"{title} ({_dur(ms)})")
                if self.show_tracebacks:
                    for line in traceback.format_exc().strip().splitlines():
                        self.step(line)
            else:
                self._write("success", f"{title} ({_dur(ms)})")

    # ----- timers -----
    def time(self, label: str) -> None:
        if len(self._timers) >= _WARN_ONCE_CAP:
            self._timers.clear()
        self._timers[label] = time.perf_counter()

    def time_end(self, label: str, *, level: str = "trace") -> float:
        start = self._timers.pop(label, None)
        if start is None:
            self.warn(f"Timer '{label}' does not exist")
            return 0.0
        ms = (time.perf_counter() - start) * 1000.0
        self._write(level if level in _VERBS else "trace", f"{label}: {_dur(ms)}")
        return ms

    # ----- progress -----
    class _Progress:
        def __init__(
            self, logger: "Logger", total: int | None, title: str | None
        ) -> None:
            self.logger = logger
            self.total = total
            self.title = title or ""
            self.count = 0
            self._start = time.perf_counter()
            _OUTPUT.resolve()
            self._live = not _OUTPUT.record and _stderr_tty() and logger._on("info")

        def _suffix(self) -> str:
            return (
                f"{self.count}/{self.total}"
                if self.total is not None
                else str(self.count)
            )

        def tick(self) -> None:
            self.update(1)

        def update(self, n: int = 1) -> None:
            self.count += n
            if self._live:
                sys.stderr.write(f"\r○ {self.title} {self._suffix()}…")
                sys.stderr.flush()

        def done(self, *, success: bool = True) -> None:
            if self._live:
                sys.stderr.write("\r\x1b[2K")
            ms = (time.perf_counter() - self._start) * 1000.0
            line = (
                f"{self.title} ({self._suffix()}, {_dur(ms)})"
                if self.title
                else f"{self._suffix()} ({_dur(ms)})"
            )
            self.logger._write("success" if success else "fail", line)

    def progress(
        self, total: int | None = None, title: str | None = None
    ) -> "Logger._Progress":
        return Logger._Progress(self, total, title)


log = Logger()
