"""
One stream of events: log lines and spans, written the same way byte for byte
by go-utils, ts-utils and py-utils. The contract, its schema and the harness
that diffs the three live in github.com/adriangalilea/utils.

Writing. Every verb takes a message, then fields:

    log.info("ready")
    log.warn("retrying", attempt=2)
    log.error("charge failed", err=e)

The message is positional-only, so any field name is allowed. Verbs say what
happened and each prints at a fixed level: error and fail at error, warn and
warn_once at warn, info, success, wait, ready and step at info, debug, trace.
warn_once prints once per message and scope for the process.

Scope is the subsystem. log.scope("api").scope("auth") writes scope
["api", "auth"] and reads API_AUTH_LOG_LEVEL, then API_LOG_LEVEL, then
LOG_LEVEL, then set_log_level(), then info, live on every event.

A span is a piece of work, and a span is a logger:

    with log.span("charge", amount=a) as s:
        s.warn("retrying", attempt=2)
        with s.span("stripe") as c:
            ...
        s.set(receipt=r)

It writes a start event (verb wait) and an end event (success, or fail with
the exception in fields.err when one escapes the block, which then propagates).
Work that does not fit a block opens and ends the span by hand, once:

    s = log.begin("upload", size=n)
    ...
    s.end()        # or s.end(err)

The with form is begin and end round a block. Only what is written through
the span object belongs to it; there is no ambient context. Whether a span
is shown is decided once, at begin, by its start's level; its end follows,
failed or not. A hidden span hands its lines, children and traceparent to its
nearest shown ancestor, so a viewer never meets a parent that is absent.

A trace crosses processes explicitly: s.traceparent() is the W3C value to hand
on (HTTP header, or TRACEPARENT of a spawned process); log.join(value) returns
a logger whose spans are children of that remote span, and warns once per
distinct malformed value. A process started with TRACEPARENT set joins it for
its root spans.

Rendering. LOG_FORMAT=json writes one event per line in the contract's key
order; human writes symbols, colour (NO_COLOR, FORCE_COLOR), dim key=value
fields, a raised exception's traceback under its line and spans as
"○ name" ... "✓ name 254ms" with their contents indented. The default is human
when stderr is a TTY, json otherwise. LOG_TIME=1 puts a dim local HH:MM:SS
before human lines; json always carries time. LOG_SERVICE names the program,
else the script's file name without its extension.

Each variable has a setter (set_log_format, set_log_time, set_log_level,
set_log_service) that sets the program's default; the environment overrides
it. Values match without regard to case, an empty variable is unset, and an
unknown value in either raises ValueError. Everything goes to stderr; stdout
is for data.
"""

from __future__ import annotations

import base64
import dataclasses
import functools
import json
import math
import os
import re
import secrets
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, NamedTuple

_LEVELS = {"silent": 0, "error": 1, "warn": 2, "info": 3, "debug": 4, "trace": 5}
_FORMATS = ("human", "json")

_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"

# verb -> (level, human symbol, ansi colour). " " keeps info aligned with the rest.
_VERBS = {
    "error": ("error", "⨯", "\x1b[31m"),
    "fail": ("error", "⨯", "\x1b[31m"),
    "warn": ("warn", "⚠", "\x1b[33m"),
    "info": ("info", " ", ""),
    "success": ("info", "✓", "\x1b[32m"),
    "wait": ("info", "○", "\x1b[37m"),
    "ready": ("info", "▶", "\x1b[32m"),
    "step": ("info", "•", "\x1b[90m"),
    "debug": ("debug", "◦", "\x1b[90m"),
    "trace": ("trace", "»", "\x1b[35m"),
}

# warn_once memory is bounded: past the cap it clears, and an old warning
# printing once more is the honest failure mode for a daemon that never exits.
_WARN_ONCE_CAP = 1024

# Integers beyond this lose precision in a JavaScript reader, so they travel as strings.
_MAX_SAFE_INT = 2**53 - 1

_TRACEPARENT = re.compile(r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}$")

# Snapshot at process start: TRACEPARENT is how a parent hands its span to us.
_ENV_TRACEPARENT = os.environ.get("TRACEPARENT", "")


class _Defaults:
    """The program's own choices, set by the set_log_* functions. The
    environment overrides every one of them, read live on each event."""

    def __init__(self) -> None:
        self.level = "info"
        self.format: str | None = None
        self.time = False
        self.service: str | None = None


_DEFAULTS = _Defaults()
_WRITE_LOCK = threading.Lock()
_ONCE: set[tuple[Any, ...]] = set()


def _first_time(key: tuple[Any, ...]) -> bool:
    """True the first time `key` is seen in this process, within _WARN_ONCE_CAP."""
    if key in _ONCE:
        return False
    if len(_ONCE) >= _WARN_ONCE_CAP:
        _ONCE.clear()
    _ONCE.add(key)
    return True


def set_log_level(level: str) -> None:
    """The program's default threshold; LOG_LEVEL and {SCOPE}_LOG_LEVEL override it."""
    _parse_level(level, "set_log_level")
    _DEFAULTS.level = level.lower()


def set_log_format(fmt: str) -> None:
    """The program's default rendering, "human" or "json"; LOG_FORMAT overrides it."""
    _DEFAULTS.format = _parse_format(fmt, "set_log_format")


def set_log_time(enabled: bool) -> None:
    """Whether human lines open with a local HH:MM:SS; LOG_TIME overrides it."""
    if not isinstance(enabled, bool):
        raise ValueError(f"set_log_time: want a bool, got {enabled!r}")
    _DEFAULTS.time = enabled


def set_log_service(name: str) -> None:
    """The program's name in every event; LOG_SERVICE overrides it."""
    if not isinstance(name, str) or not name:
        raise ValueError(f"set_log_service: want a non-empty name, got {name!r}")
    _DEFAULTS.service = name


def _parse_level(value: str, source: str) -> int:
    level = _LEVELS.get(value.lower())
    if level is None:
        raise ValueError(
            f"{source}: unknown log level {value!r} "
            "(want silent/error/warn/info/debug/trace)"
        )
    return level


def _parse_format(value: str, source: str) -> str:
    fmt = value.lower()
    if fmt not in _FORMATS:
        raise ValueError(f"{source}: unknown format {value!r} (want human/json)")
    return fmt


def _scope_var(path: tuple[str, ...]) -> str:
    segments = (
        "".join(c if c.isascii() and c.isalnum() else "_" for c in seg.upper())
        for seg in path
    )
    return "_".join(segments) + "_LOG_LEVEL"


def _threshold(scope: tuple[str, ...]) -> int:
    for n in range(len(scope), 0, -1):
        var = _scope_var(scope[:n])
        value = os.environ.get(var)
        if value:
            return _parse_level(value, var)
    value = os.environ.get("LOG_LEVEL")
    if value:
        return _parse_level(value, "LOG_LEVEL")
    return _LEVELS[_DEFAULTS.level]


def _enabled(scope: tuple[str, ...], level: str) -> bool:
    return _LEVELS[level] <= _threshold(scope)


def _format() -> str:
    value = os.environ.get("LOG_FORMAT")
    if value:
        return _parse_format(value, "LOG_FORMAT")
    if _DEFAULTS.format is not None:
        return _DEFAULTS.format
    return "human" if sys.stderr.isatty() else "json"


def _time_on() -> bool:
    value = os.environ.get("LOG_TIME")
    if value:
        if value not in ("1", "0"):
            raise ValueError(f"LOG_TIME: unknown value {value!r} (want 1/0)")
        return value == "1"
    return _DEFAULTS.time


def _service() -> str:
    value = os.environ.get("LOG_SERVICE")
    if value:
        return value
    if _DEFAULTS.service is not None:
        return _DEFAULTS.service
    argv0 = sys.argv[0] if sys.argv else ""
    stem = Path(argv0).stem if argv0 not in ("", "-c", "-") else ""
    if not stem:
        raise ValueError(
            "no service name: this process has no script name, "
            "set LOG_SERVICE or call log.set_log_service()"
        )
    return stem


def _color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stderr.isatty()


# ----- field values -----


def _instant(t: datetime) -> str:
    u = t.astimezone(timezone.utc)
    return u.strftime("%Y-%m-%dT%H:%M:%S") + f".{u.microsecond // 1000:03d}Z"


def _number(x: float) -> str:
    """ECMAScript Number-to-string, which Go's encoding/json also follows, so a
    float reads the same from all three: shortest round-trip digits, 2.0 as 2,
    positional from 1e-7 up to 1e21, exponent outside it."""
    if math.isnan(x):
        return '"NaN"'
    if math.isinf(x):
        return '"Infinity"' if x > 0 else '"-Infinity"'
    if x == 0:
        return "0"
    sign, digit_tuple, exp = Decimal(repr(x)).normalize().as_tuple()
    assert isinstance(exp, int), f"finite float {x!r} decoded to exponent {exp!r}"
    digits = "".join(map(str, digit_tuple))
    k = len(digits)
    n = exp + k
    if k <= n <= 21:
        text = digits + "0" * (n - k)
    elif 0 < n <= 21:
        text = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        text = "0." + "0" * -n + digits
    else:
        e = n - 1
        mantissa = digits if k == 1 else digits[0] + "." + digits[1:]
        text = f"{mantissa}e{'+' if e > 0 else '-'}{abs(e)}"
    return "-" + text if sign else text


def _string(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def _object(pairs: list[tuple[str, str]]) -> str:
    return "{" + ",".join(f"{_string(k)}:{v}" for k, v in pairs) + "}"


def _cause(e: BaseException) -> BaseException | None:
    if e.__cause__ is not None:
        return e.__cause__
    return None if e.__suppress_context__ else e.__context__


def _error(e: BaseException, seen: frozenset[int]) -> str:
    # Imported here: offensive.py logs through this module, so a top-level
    # import would be a cycle.
    from .offensive import SourcedError

    # A SourcedError's str() prefixes [source:op status=...]; those are keys
    # of their own here, so its message is the one it was given.
    message = e.message if isinstance(e, SourcedError) else str(e)
    pairs = [("type", _string(type(e).__name__)), ("message", _string(message))]
    if e.__traceback__ is not None:
        stack = "".join(traceback.format_exception(e, chain=False)).rstrip("\n")
        pairs.append(("stack", _string(stack)))
    cause = _cause(e)
    if cause is not None:
        pairs.append(("cause", _json(cause, seen)))
    if isinstance(e, SourcedError):
        pairs.append(("source", _string(e.source)))
        pairs.append(("operation", _string(e.operation)))
        if e.status is not None:
            pairs.append(("status", _json(e.status, seen)))
        if e.context:
            pairs.append(("context", _json(e.context, seen)))
    return _object(pairs)


def _set_order(s: set[Any] | frozenset[Any]) -> list[Any]:
    """A set's items sorted, so the same set always writes the same array;
    iteration order when its items do not compare (mixed types)."""
    try:
        return sorted(s)
    except TypeError:
        return list(s)


def _json(v: Any, seen: frozenset[int]) -> str:
    """A field value as JSON text by the contract's rules: maps sorted at every
    depth, an error's keys in their fixed order. `seen` holds the containers on
    the path from the root, so a value that encloses itself prints "[circular]"."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return _string(v)
    if isinstance(v, int):
        return str(int(v)) if -_MAX_SAFE_INT <= v <= _MAX_SAFE_INT else _string(str(v))
    if isinstance(v, float):
        return _number(v)
    if isinstance(v, datetime):
        return _string(_instant(v))
    if isinstance(v, timedelta):
        return _number(v / timedelta(milliseconds=1))
    if isinstance(v, (bytes, bytearray, memoryview)):
        return _string(base64.b64encode(v).decode("ascii"))
    if isinstance(v, Decimal):
        return _string(str(v))
    is_dataclass = dataclasses.is_dataclass(v) and not isinstance(v, type)
    containers = (BaseException, dict, list, tuple, set, frozenset)
    if not (isinstance(v, containers) or is_dataclass):
        return _string(str(v))
    if id(v) in seen:
        return '"[circular]"'
    inner = seen | {id(v)}
    if isinstance(v, BaseException):
        return _error(v, inner)
    if isinstance(v, (set, frozenset)):
        return "[" + ",".join(_json(x, inner) for x in _set_order(v)) + "]"
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(_json(x, inner) for x in v) + "]"
    items = (
        {f.name: getattr(v, f.name) for f in dataclasses.fields(v)}
        if is_dataclass
        else v
    )
    keyed = sorted(((str(k), x) for k, x in items.items()), key=lambda kx: kx[0])
    return _object([(k, _json(x, inner)) for k, x in keyed])


# ----- events -----


class _Event(NamedTuple):
    time: datetime
    verb: str
    msg: str
    scope: tuple[str, ...]
    fields: dict[str, Any]
    depth: int
    phase: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    parent_id: str | None = None
    status: str | None = None
    dur_ms: float | None = None


def _json_line(e: _Event) -> str:
    pairs = [
        ("time", _string(_instant(e.time))),
        ("level", _string(_VERBS[e.verb][0])),
        ("verb", _string(e.verb)),
        ("msg", _string(e.msg)),
        ("service", _string(_service())),
    ]
    if e.scope:
        pairs.append(("scope", "[" + ",".join(_string(s) for s in e.scope) + "]"))
    for key in ("phase", "trace_id", "span_id", "parent_id", "status"):
        value = getattr(e, key)
        if value is not None:
            pairs.append((key, _string(value)))
    if e.dur_ms is not None:
        pairs.append(("dur_ms", _number(e.dur_ms)))
    if e.fields:
        pairs.append(("fields", _json(e.fields, frozenset())))
    return _object(pairs)


def _human_text(s: str) -> str:
    plain = s and not any(c.isspace() or c == '"' for c in s)
    return s if plain else _string(s)


def _human_value(v: Any) -> str:
    if isinstance(v, BaseException):
        return _human_text(f"{type(v).__name__}: {v}")
    text = _json(v, frozenset())
    return _human_text(json.loads(text)) if text.startswith('"') else text


def _human_ms(ms: float) -> str:
    return f"{ms / 1000:.1f}s" if ms >= 10_000 else f"{ms:.0f}ms"


def _human_line(e: _Event, time_on: bool) -> str:
    _, symbol, colour = _VERBS[e.verb]
    on = _color()

    def dim(s: str) -> str:
        return f"{_DIM}{s}{_RESET}" if on else s

    pad = "  " * e.depth + ("  " if e.verb == "step" else "")
    stamp = dim(e.time.astimezone().strftime("%H:%M:%S")) + " " if time_on else ""
    parts = [f"{colour}{_BOLD}{symbol}{_RESET}" if on and colour else symbol]
    if e.scope:
        parts.append(dim("[" + " ".join(e.scope) + "]"))
    parts.append(e.msg)
    if e.dur_ms is not None:
        parts.append(_human_ms(e.dur_ms))
    ordered = sorted(e.fields.items())
    if ordered:
        parts.append(dim(" ".join(f"{k}={_human_value(v)}" for k, v in ordered)))
    lines = [stamp + pad + " ".join(parts)]
    for _, v in ordered:
        if isinstance(v, BaseException) and v.__traceback__ is not None:
            block = "".join(traceback.format_exception(v)).rstrip("\n")
            lines.extend(
                dim((pad + "    " + line).rstrip()) for line in block.splitlines()
            )
    return "\n".join(lines)


def _write(e: _Event) -> None:
    # Both knobs resolve on every event, so a bad LOG_TIME screams under json too.
    fmt, time_on = _format(), _time_on()
    text = _json_line(e) if fmt == "json" else _human_line(e, time_on)
    with _WRITE_LOCK:
        sys.stderr.write(text + "\n")
        sys.stderr.flush()


# ----- spans -----


class _Remote(NamedTuple):
    trace_id: str
    span_id: str


def _parse_traceparent(value: str) -> _Remote | None:
    m = _TRACEPARENT.match(value)
    if m is None or m[1] == "ff" or m[2] == "0" * 32 or m[3] == "0" * 16:
        return None
    return _Remote(m[2], m[3])


@functools.cache
def _env_remote() -> _Remote | None:
    if not _ENV_TRACEPARENT:
        return None
    remote = _parse_traceparent(_ENV_TRACEPARENT)
    if remote is None:
        log.warn("malformed TRACEPARENT ignored", traceparent=_ENV_TRACEPARENT)
    return remote


# ----- the logger -----


class Logger:
    """Writes events. `log` is the root; scope(), begin(), span() and join()
    derive the rest. A Logger holding a span writes its lines into that span
    and opens its spans as that span's children."""

    def __init__(
        self,
        scope: tuple[str, ...] = (),
        span: Span | None = None,
        remote: _Remote | None = None,
    ) -> None:
        self._scope = scope
        self._span = span
        self._remote = remote

    set_log_level = staticmethod(set_log_level)
    set_log_format = staticmethod(set_log_format)
    set_log_time = staticmethod(set_log_time)
    set_log_service = staticmethod(set_log_service)

    def scope(self, name: str) -> Logger:
        """A child whose events carry `name` after this logger's scope path."""
        assert isinstance(name, str) and name, f"scope name must be non-empty: {name!r}"
        return Logger(self._scope + (name,), self._span, self._remote)

    def join(self, traceparent: str | None) -> Logger:
        """A logger whose spans are children of the remote span `traceparent`
        names. None returns this logger; a malformed value is ignored, warned
        about once per distinct value, since it is input from outside."""
        if traceparent is None:
            return self
        remote = _parse_traceparent(traceparent)
        if remote is None:
            if _first_time(("traceparent", traceparent)):
                self.warn("malformed traceparent ignored", traceparent=traceparent)
            return self
        return Logger(self._scope, None, remote)

    def begin(self, name: str, /, **fields: Any) -> Span:
        """Open a span and return it; it stays open until its end() is called.
        Under a span it is that span's child, else a root span (joined to the
        remote parent when there is one)."""
        assert isinstance(name, str) and name, f"span name must be non-empty: {name!r}"
        parent = self._span
        if parent is not None:
            assert not parent._ended, (
                f"span {name!r} opened in {parent._name!r} after it ended"
            )
            trace_id, parent_id, depth = parent._trace_id, parent._anchor, parent._inner
        else:
            remote = self._remote or _env_remote()
            trace_id = remote.trace_id if remote else secrets.token_hex(16)
            parent_id = remote.span_id if remote else None
            depth = 0
        s = Span(name, self._scope, trace_id, parent_id, depth, fields)
        if s._shown:
            _write(s._event("wait", fields=fields, phase="start"))
        return s

    def span(self, name: str, /, **fields: Any) -> _Block:
        """begin() and end() round a with block: an exception escaping it ends
        the span failed (fields.err) and propagates."""
        return _Block(self, name, fields)

    def _line(self, verb: str, message: str, fields: dict[str, Any]) -> None:
        assert isinstance(message, str), f"message must be a str, got {message!r}"
        if not _enabled(self._scope, _VERBS[verb][0]):
            return
        span = self._span
        trace_id = span_id = None
        depth = 0
        if span is not None:
            assert not span._ended, (
                f"{message!r} written to {span._name!r} after it ended"
            )
            if span._anchor is not None:
                trace_id, span_id = span._trace_id, span._anchor
            depth = span._inner
        _write(
            _Event(
                time=datetime.now(timezone.utc),
                verb=verb,
                msg=message,
                scope=self._scope,
                fields=fields,
                depth=depth,
                trace_id=trace_id,
                span_id=span_id,
            )
        )

    def error(self, message: str, /, **fields: Any) -> None:
        self._line("error", message, fields)

    def fail(self, message: str, /, **fields: Any) -> None:
        self._line("fail", message, fields)

    def warn(self, message: str, /, **fields: Any) -> None:
        self._line("warn", message, fields)

    def warn_once(self, message: str, /, **fields: Any) -> None:
        """warn, once per message and scope for the process."""
        if _first_time(("warn", self._scope, message)):
            self._line("warn", message, fields)

    def info(self, message: str, /, **fields: Any) -> None:
        self._line("info", message, fields)

    def success(self, message: str, /, **fields: Any) -> None:
        self._line("success", message, fields)

    def wait(self, message: str, /, **fields: Any) -> None:
        self._line("wait", message, fields)

    def ready(self, message: str, /, **fields: Any) -> None:
        self._line("ready", message, fields)

    def step(self, message: str, /, **fields: Any) -> None:
        self._line("step", message, fields)

    def debug(self, message: str, /, **fields: Any) -> None:
        self._line("debug", message, fields)

    def trace(self, message: str, /, **fields: Any) -> None:
        self._line("trace", message, fields)


class Span(Logger):
    """A running span, made by begin() or span(): every verb writes into it,
    begin() and span() make children, set() adds fields to its end event,
    traceparent() hands it on, end() closes it.

    Whether it is shown is decided once, at begin, by its start's level; its
    end follows. `_anchor` is the span id its lines, children and
    traceparent carry: its own when shown, else its nearest shown
    ancestor's (or the remote parent's, or none). `_depth` indents its own
    events, `_inner` what it holds."""

    def __init__(
        self,
        name: str,
        scope: tuple[str, ...],
        trace_id: str,
        parent_id: str | None,
        depth: int,
        fields: dict[str, Any],
    ) -> None:
        super().__init__(scope, self)
        self._name = name
        self._trace_id = trace_id
        self._span_id = secrets.token_hex(8)
        self._parent_id = parent_id
        self._shown = _enabled(scope, "info")
        self._anchor = self._span_id if self._shown else parent_id
        self._depth = depth
        self._inner = depth + 1 if self._shown else depth
        self._fields = fields
        self._added: dict[str, Any] = {}
        self._start = time.perf_counter()
        self._ended = False

    def _event(self, verb: str, **rest: Any) -> _Event:
        return _Event(
            time=datetime.now(timezone.utc),
            verb=verb,
            msg=self._name,
            scope=self._scope,
            depth=self._depth,
            trace_id=self._trace_id,
            span_id=self._span_id,
            parent_id=self._parent_id,
            **rest,
        )

    def set(self, **fields: Any) -> None:
        """Fields learned while the span runs, carried on its end event."""
        assert not self._ended, f"set() on span {self._name!r} after it ended"
        self._added.update(fields)

    def traceparent(self) -> str:
        """The W3C traceparent of this span, for an HTTP header or the
        TRACEPARENT of a process it spawns. A hidden span names its nearest
        shown ancestor, its own id only when it has none."""
        return f"00-{self._trace_id}-{self._anchor or self._span_id}-01"

    def end(self, err: BaseException | None = None) -> None:
        """Close the span: ok with no argument, failed with `err` in
        fields.err. A span ends once; a second end() raises."""
        if self._ended:
            raise RuntimeError(f"span {self._name!r} ended twice")
        self._ended = True
        if not self._shown:
            return
        dur_ms = round((time.perf_counter() - self._start) * 1000.0, 3)
        verb = "fail" if err is not None else "success"
        fields = {**self._fields, **self._added}
        if err is not None:
            fields["err"] = err
        status = "error" if err is not None else "ok"
        _write(
            self._event(verb, fields=fields, phase="end", status=status, dur_ms=dur_ms)
        )


class _Block:
    """What span() returns. A class rather than a generator so a failed
    span's stack starts at the caller's code, not inside this module."""

    def __init__(self, logger: Logger, name: str, fields: dict[str, Any]) -> None:
        self._logger = logger
        self._name = name
        self._fields = fields
        self._span: Span | None = None

    def __enter__(self) -> Span:
        assert self._span is None, f"span {self._name!r} block entered twice"
        self._span = self._logger.begin(self._name, **self._fields)
        return self._span

    def __exit__(self, _type: object, err: BaseException | None, _tb: object) -> None:
        assert self._span is not None
        self._span.end(err)


log = Logger()
