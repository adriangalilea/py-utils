from __future__ import annotations

import os
import sys
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Any, Callable, Optional
import threading

try:
    from rich.console import Console
    from rich.text import Text
    from rich.theme import Theme
    from rich.status import Status
    from rich.markup import MarkupError

    HAVE_RICH = True
except Exception:  # pragma: no cover - optional dependency
    HAVE_RICH = False
    Console = None  # type: ignore


# Levels
_LEVELS = {"trace": 10, "debug": 20, "info": 30, "warn": 40, "error": 50, "fatal": 60}


def _env_level() -> str:
    return os.getenv("LOG_LEVEL", "info").lower()


def _isatty() -> bool:
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


@dataclass(slots=True)
class _Config:
    level: str = _env_level()
    color_enabled: bool = (
        os.getenv("NO_COLOR") is None or os.getenv("FORCE_COLOR") is not None
    )
    live_updates: bool = True
    show_tracebacks: bool = True
    time_enabled: bool = False
    symbols_enabled: bool = True
    indent_width: int = 2


_DEFAULT_THEME = Theme(
    {
        "info": "bold blue",
        "warn": "bold yellow",
        "error": "bold red",
        "success": "bold green",
        "ready": "bold green",
        "wait": "bright_white",
        "trace": "magenta",
        "dim": "dim",
    }
)


class _State(threading.local):
    def __init__(self) -> None:
        super().__init__()
        self.indent: int = 0
        self.warn_once_keys: set[str] = set()
        self.timers: dict[str, float] = {}


class Logger:
    """TTY-focused logger with tasks, steps, and indentation.

    This logger writes to stdout. When attached to a terminal (TTY), it uses
    colors and symbols (via Rich if installed). When not attached to a TTY,
    it prints plain text and avoids live updates.
    """

    def __init__(
        self, *, prefix: str | None = None, tags: tuple[str, ...] = ()
    ) -> None:
        self._cfg = _Config()
        self._state = _State()
        self._prefix = prefix
        self._tags = tags

        if HAVE_RICH:
            self._console = Console(theme=_DEFAULT_THEME)
        else:
            self._console = None

        self._sync_format_color()

    # ----- configuration -----
    def set_level(self, level: str) -> None:
        self._cfg.level = level.lower()

    def get_level(self) -> str:
        return self._cfg.level

    def enable_color(self, enabled: bool) -> None:
        self._cfg.color_enabled = enabled
        self._sync_format_color()

    def enable_live_updates(self, enabled: bool) -> None:
        self._cfg.live_updates = enabled

    def set_time_enabled(self, enabled: bool) -> None:
        self._cfg.time_enabled = enabled

    def set_show_tracebacks(self, enabled: bool) -> None:
        self._cfg.show_tracebacks = enabled

    def set_symbols(self, enabled: bool) -> None:
        self._cfg.symbols_enabled = enabled

    # ----- derived props -----
    @property
    def _active_console(self) -> Optional[Console]:
        return self._console if (HAVE_RICH and self._cfg.color_enabled) else None

    @property
    def _is_tty(self) -> bool:
        if self._active_console is not None:
            try:
                return self._active_console.is_terminal
            except Exception:
                pass
        return _isatty()

    def _should_log(self, level: str) -> bool:
        return _LEVELS[level] >= _LEVELS.get(self._cfg.level, 30)

    # ----- helpers -----
    def _indent_str(self) -> str:
        return " " * (self._state.indent * self._cfg.indent_width)

    def _prefix_text(self) -> str:
        parts = []
        if self._prefix:
            parts.append(self._prefix)
        if self._tags:
            parts.extend(self._tags)
        if not parts:
            return ""
        return f"[{' '.join(parts)}] "

    def _symbol(self, kind: str) -> str:
        if not self._cfg.symbols_enabled:
            return ""
        return {
            "info": "ℹ",
            "warn": "⚠",
            "error": "⨯",
            "fatal": "⨯",
            "success": "✓",
            "fail": "⨯",
            "wait": "○",
            "ready": "▶",
            "trace": "»",
            "step": "•",
            "section": "▸",
        }.get(kind, "")

    def _color_active(self) -> bool:
        return self._cfg.color_enabled and self._is_tty

    def _sync_format_color(self) -> None:
        try:
            from . import format as _format

            _format.set_color_enabled(self._color_active())
        except Exception:
            pass

    def _coerce_text(self, message: Any) -> Text:
        if isinstance(message, Text):
            return message
        msg_str = str(message)
        try:
            return Text.from_markup(msg_str, emoji=False)
        except (MarkupError, ValueError):
            return Text(msg_str)

    def _write_line(self, kind: str, message: Any) -> None:
        prefix = self._prefix_text()
        indent = self._indent_str()
        sym = self._symbol(kind)

        if self._active_console and self._is_tty:
            style = {
                "info": "info",
                "warn": "warn",
                "error": "error",
                "fatal": "error",
                "success": "success",
                "fail": "error",
                "wait": "wait",
                "ready": "ready",
                "trace": "trace",
                "step": "dim",
                "section": "dim",
            }.get(kind, "info")

            pieces: list[Text] = []
            if indent:
                pieces.append(Text(indent))
            if prefix:
                pieces.append(Text(prefix, style="dim"))
            if sym:
                pieces.append(Text(f"{sym} ", style=style))
            pieces.append(self._coerce_text(message))
            self._active_console.print(Text.assemble(*pieces))
        else:
            # Plain text fallback
            plain = str(message)
            if HAVE_RICH:
                try:
                    plain = Text.from_markup(plain, emoji=False).plain
                except (MarkupError, ValueError):
                    plain = str(message)
            base = f"{prefix}{(sym + ' ') if sym else ''}{plain}"
            sys.stdout.write(indent + base + "\n")
            sys.stdout.flush()

    # ----- public logging -----
    def trace(self, message: str) -> None:
        if self._should_log("trace"):
            self._write_line("trace", message)

    def debug(self, message: str) -> None:
        if self._should_log("debug"):
            self._write_line("trace", message)  # use trace style for visual distinction

    def info(self, message: str) -> None:
        if self._should_log("info"):
            self._write_line("info", message)

    def warn(self, message: str) -> None:
        if self._should_log("warn"):
            self._write_line("warn", message)

    def warn_once(self, message: str) -> None:
        key = message
        if key in self._state.warn_once_keys:
            return
        self._state.warn_once_keys.add(key)
        self.warn(message)

    def error(self, msg_or_exc: Any, *, exc: bool | None = None) -> None:
        if not self._should_log("error"):
            return
        message = str(msg_or_exc)
        self._write_line("error", message)
        want_tb = exc or isinstance(msg_or_exc, BaseException)
        if want_tb and self._cfg.show_tracebacks:
            tb = traceback.format_exc()
            for line in tb.strip().splitlines():
                self._with_extra_indent(lambda: self._write_line("step", line))

    def fatal(
        self, msg_or_exc: Any, *, exit_code: int = 1, exc: bool | None = None
    ) -> None:
        self.error(msg_or_exc, exc=exc)
        try:
            sys.exit(exit_code)
        except SystemExit:
            raise

    def success(self, message: str) -> None:
        if self._should_log("info"):
            self._write_line("success", message)

    def fail(self, message: str) -> None:
        if self._should_log("error"):
            self._write_line("fail", message)

    def event(self, message: str) -> None:
        if self._should_log("info"):
            self._write_line("info", message)

    def wait(self, message: str) -> None:
        if self._should_log("info"):
            self._write_line("wait", message)

    def ready(self, message: str) -> None:
        if self._should_log("info"):
            self._write_line("ready", message)

    # ----- indentation & grouping -----
    @contextmanager
    def _with_extra_indent(self, fn: Optional[Callable[[], None]] = None):
        self._state.indent += 1
        try:
            if fn is not None:
                fn()
            else:
                yield
        finally:
            self._state.indent -= 1

    def step(self, message: str) -> None:
        self._with_extra_indent(lambda: self._write_line("step", message))

    @contextmanager
    def section(self, title: str):
        self._write_line("section", title)
        with self._with_extra_indent():
            yield

    @contextmanager
    def task(self, title: str):
        start = time.perf_counter()
        self._write_line("wait", title)
        self._state.indent += 1
        failed = False
        try:
            yield
        except BaseException:
            failed = True
            raise
        finally:
            self._state.indent -= 1
            dur_ms = (time.perf_counter() - start) * 1000.0
            from .format import duration as _dur

            if failed:
                self._write_line("fail", f"{title} ({_dur(dur_ms)})")
                if self._cfg.show_tracebacks:
                    tb = traceback.format_exc()
                    for line in tb.strip().splitlines():
                        self._with_extra_indent(lambda: self._write_line("step", line))
            else:
                self._write_line("success", f"{title} ({_dur(dur_ms)})")

    def step_run(self, title: str, fn: Callable[..., Any], *args, **kwargs) -> Any:
        with self.task(title):
            return fn(*args, **kwargs)

    # ----- timers -----
    def time(self, label: str) -> None:
        self._state.timers[label] = time.perf_counter()

    def time_end(self, label: str, *, level: str = "trace") -> float:
        start = self._state.timers.pop(label, None)
        if start is None:
            self.warn(f"Timer '{label}' does not exist")
            return 0.0
        ms = (time.perf_counter() - start) * 1000.0
        from .format import duration as _dur

        if self._should_log(level):
            self._write_line("trace", f"{label}: {_dur(ms)}")
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
            self._status: Optional[Status] = None

            if (
                HAVE_RICH
                and logger._active_console is not None
                and logger._is_tty
                and logger._cfg.live_updates
            ):
                msg = (
                    logger._indent_str()
                    + (logger._prefix_text() or "")
                    + f"{self.title}…"
                )
                self._status = logger._active_console.status(msg, spinner="dots")
                self._status.start()

        def tick(self) -> None:
            self.update(1)

        def update(self, n: int = 1) -> None:
            self.count += n
            if self._status is not None:
                suffix = (
                    f" {self.count}/{self.total}"
                    if self.total is not None
                    else f" {self.count}"
                )
                msg = (
                    self.logger._indent_str()
                    + (self.logger._prefix_text() or "")
                    + f"{self.title}{suffix}…"
                )
                self._status.update(msg)

        def done(self, *, success: bool = True) -> None:
            if self._status is not None:
                self._status.stop()
            dur_ms = (time.perf_counter() - self._start) * 1000.0
            from .format import duration as _dur

            suffix = (
                f" ({self.count}/{self.total}, {_dur(dur_ms)})"
                if self.total is not None
                else f" ({self.count}, {_dur(dur_ms)})"
            )
            line = (
                f"{self.title}{suffix}"
                if self.title
                else (
                    f"{self.count}/{self.total} ({_dur(dur_ms)})"
                    if self.total is not None
                    else f"{self.count} ({_dur(dur_ms)})"
                )
            )
            if success:
                self.logger._write_line("success", line)
            else:
                self.logger._write_line("fail", line)

    def progress(
        self, total: int | None = None, title: str | None = None
    ) -> "Logger._Progress":
        return Logger._Progress(self, total, title)

    # ----- context binding -----
    def with_prefix(self, text: str) -> "Logger":
        return self._child(prefix=text, tags=self._tags)

    def tag(self, *tags: str) -> "Logger":
        return self._child(prefix=self._prefix, tags=self._tags + tuple(tags))

    def _child(self, *, prefix: str | None, tags: tuple[str, ...]) -> "Logger":
        child = Logger(prefix=prefix, tags=tags)
        child._cfg = replace(self._cfg)
        child._state = self._state  # share indent, timers, warn_once within thread
        child._console = self._console
        return child


# Global logger instance
log = Logger()
