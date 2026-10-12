"""Runnable proof of the py_utils logger, plus the format helpers.

Run with:
    uv run python example_usage.py

Each check captures the JSON stream with stderr redirected and asserts a rule
of the logging contract (github.com/adriangalilea/utils): key order, sorting,
field values, spans and their ids, failed and filtered spans, joins and
TRACEPARENT, level resolution and the setters. A broken rule is an
AssertionError and a non-zero exit. The end prints a human rendering.
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager, redirect_stderr
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

# Ensure src/ is on the import path when running directly from the repo.
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from py_utils import SourcedError, log, percentage, usd  # noqa: E402

ORDER = [
    "time",
    "level",
    "verb",
    "msg",
    "service",
    "scope",
    "phase",
    "trace_id",
    "span_id",
    "parent_id",
    "status",
    "dur_ms",
    "fields",
]
TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
SPAN_ID = re.compile(r"^[0-9a-f]{16}$")
REMOTE = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"

Event = dict[str, Any]


def apply(values: dict[str, str | None]) -> None:
    for key, value in values.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@contextmanager
def environ(**values: str | None) -> Iterator[None]:
    saved = {key: os.environ.get(key) for key in values}
    apply(values)
    try:
        yield
    finally:
        apply(saved)


def lines(write: Callable[[], None], **env: str | None) -> list[str]:
    """The raw stderr lines `write` produces, LOG_FORMAT=json unless `env` says otherwise."""
    buf = io.StringIO()
    with environ(**{"LOG_FORMAT": "json", **env}), redirect_stderr(buf):
        write()
    return buf.getvalue().splitlines()


def parse(text: str) -> Event:
    event = json.loads(text)
    keys = list(event)
    assert keys == [k for k in ORDER if k in event], f"key order {keys}"
    assert TIME.match(event["time"]), event["time"]
    for key, pattern in (
        ("trace_id", TRACE_ID),
        ("span_id", SPAN_ID),
        ("parent_id", SPAN_ID),
    ):
        assert key not in event or pattern.match(event[key]), (key, event)
    return event


def events(write: Callable[[], None], **env: str | None) -> list[Event]:
    return [parse(text) for text in lines(write, **env)]


def check_shape() -> None:
    [e] = events(
        lambda: log.scope("payments").warn("retrying", attempt=2),
        LOG_SERVICE="checkout",
    )
    assert list(e) == ["time", "level", "verb", "msg", "service", "scope", "fields"]
    assert (e["level"], e["verb"], e["msg"]) == ("warn", "warn", "retrying")
    assert e["service"] == "checkout"
    assert e["scope"] == ["payments"]
    assert e["fields"] == {"attempt": 2}

    # Unset LOG_SERVICE: the script's name without its extension.
    [e] = events(lambda: log.info("plain"))
    assert list(e) == ["time", "level", "verb", "msg", "service"]
    assert e["service"] == "example_usage", e["service"]

    # The message is positional-only, so "message" is an ordinary field.
    [e] = events(lambda: log.info("named", message="free"))
    assert e["fields"] == {"message": "free"}

    verbs = {
        "error": "error",
        "fail": "error",
        "warn": "warn",
        "info": "info",
        "success": "info",
        "wait": "info",
        "ready": "info",
        "step": "info",
        "debug": "debug",
        "trace": "trace",
    }
    written = events(
        lambda: [getattr(log, verb)(verb) for verb in verbs], LOG_LEVEL="trace"
    )
    assert {e["verb"]: e["level"] for e in written} == verbs


def check_sorting() -> None:
    [text] = lines(
        lambda: log.info(
            "sorted", zeta=1, alpha={"b": [{"y": 1, "x": 2}], "a": None}, whole=2.0
        )
    )
    e = parse(text)
    assert list(e["fields"]) == ["alpha", "whole", "zeta"]
    assert list(e["fields"]["alpha"]) == ["a", "b"]
    assert list(e["fields"]["alpha"]["b"][0]) == ["x", "y"]
    # A float that is whole reads as JavaScript and Go write it.
    assert '"whole":2,' in text, text


@dataclass
class Point:
    y: int
    x: int


def check_values() -> None:
    loop: list[Any] = [1]
    loop.append(loop)
    [e] = events(
        lambda: log.info(
            "values",
            big=2**53,
            safe=2**53 - 1,
            nan=float("nan"),
            inf=float("inf"),
            neg=float("-inf"),
            tiny=1e-7,
            took=timedelta(seconds=1.5),
            at=datetime(2026, 10, 12, 12, 20, 39, 123456, tzinfo=timezone.utc),
            raw=b"hi",
            price=Decimal("1.10"),
            point=Point(y=2, x=1),
            pair=(1, "a"),
            loop=loop,
            path=Path("/tmp"),
        )
    )
    f = e["fields"]
    assert f["big"] == "9007199254740992"
    assert f["safe"] == 9007199254740991
    assert (f["nan"], f["inf"], f["neg"]) == ("NaN", "Infinity", "-Infinity")
    assert f["tiny"] == 1e-7
    assert f["took"] == 1500
    assert f["at"] == "2026-10-12T12:20:39.123Z"
    assert f["raw"] == "aGk="
    assert f["price"] == "1.10"
    assert f["point"] == {"x": 1, "y": 2} and list(f["point"]) == ["x", "y"]
    assert f["pair"] == [1, "a"]
    assert f["loop"] == [1, "[circular]"]
    assert f["path"] == "/tmp"


def check_errors() -> None:
    try:
        try:
            raise KeyError("k")
        except KeyError as inner:
            raise ValueError("bad") from inner
    except ValueError as caught:
        chained = caught

    try:
        raise SourcedError(
            source="stripe",
            operation="charge",
            message="declined",
            status=402,
            cause=ValueError("card"),
            zeta=1,
            alpha=2,
        )
    except SourcedError as caught:
        sourced = caught

    try:
        try:
            raise KeyError("hidden")
        except KeyError:
            raise RuntimeError("clean") from None
    except RuntimeError as caught:
        suppressed = caught

    [e] = events(
        lambda: log.error(
            "failed",
            err=chained,
            fresh=RuntimeError("expired"),
            sourced=sourced,
            suppressed=suppressed,
        )
    )
    err = e["fields"]["err"]
    assert list(err) == ["type", "message", "stack", "cause"]
    assert (err["type"], err["message"]) == ("ValueError", "bad")
    assert err["stack"].endswith("ValueError: bad"), err["stack"]
    assert (err["cause"]["type"], err["cause"]["message"]) == ("KeyError", "'k'")

    # Never raised: no traceback, so no stack.
    assert e["fields"]["fresh"] == {"type": "RuntimeError", "message": "expired"}

    s = e["fields"]["sourced"]
    assert list(s) == [
        "type",
        "message",
        "stack",
        "cause",
        "source",
        "operation",
        "status",
        "context",
    ]
    assert (s["source"], s["operation"], s["status"]) == ("stripe", "charge", 402)
    assert list(s["context"]) == ["alpha", "zeta"]
    assert s["cause"] == {"type": "ValueError", "message": "card"}

    # `raise ... from None` hides the context, as Python's own traceback does.
    assert "cause" not in e["fields"]["suppressed"]


def check_spans() -> None:
    handed: list[str] = []

    def write() -> None:
        with log.span("sync", repo="ui") as s:
            s.info("cloned", files=3)
            with s.span("build") as c:
                c.warn("slow step", ms=1200)
            s.scope("git").info("pushed")
            s.set(pushed=True)
            handed.append(s.traceparent())

    start, cloned, child_start, slow, child_end, pushed, end = events(write)
    trace, sid = start["trace_id"], start["span_id"]

    assert (start["phase"], start["verb"], start["level"]) == ("start", "wait", "info")
    assert "parent_id" not in start and start["fields"] == {"repo": "ui"}
    assert (cloned["trace_id"], cloned["span_id"]) == (trace, sid)
    assert "parent_id" not in cloned and "phase" not in cloned

    cid = child_start["span_id"]
    assert cid != sid and child_start["trace_id"] == trace
    assert child_start["parent_id"] == sid
    assert slow["span_id"] == cid
    assert (child_end["phase"], child_end["status"], child_end["parent_id"]) == (
        "end",
        "ok",
        sid,
    )
    assert "fields" not in child_end

    # A scope of a span still writes into the span.
    assert pushed["scope"] == ["git"] and pushed["span_id"] == sid

    assert (end["verb"], end["status"], end["span_id"]) == ("success", "ok", sid)
    assert end["fields"] == {"pushed": True, "repo": "ui"}
    assert end["dur_ms"] >= 0 and round(end["dur_ms"], 3) == end["dur_ms"]
    assert handed == [f"00-{trace}-{sid}-01"]


def check_begin_end() -> None:
    raised: list[RuntimeError] = []

    def write() -> None:
        upload = log.begin("upload", size=3)
        upload.info("chunk", n=1)
        part = upload.begin("part")
        part.end(ConnectionError("reset"))
        upload.end()
        try:
            upload.end()
        except RuntimeError as err:
            raised.append(err)

    start, chunk, child_start, child_end, end = events(write)
    assert start["phase"] == "start" and chunk["span_id"] == start["span_id"]
    assert end["status"] == "ok" and end["fields"] == {"size": 3}
    assert len(raised) == 1, "a second end() must raise"

    # end(err) ends failed; begin() on a span opens its child.
    assert child_start["parent_id"] == start["span_id"]
    assert (child_end["verb"], child_end["level"], child_end["status"]) == (
        "fail",
        "error",
        "error",
    )
    assert child_end["fields"]["err"] == {
        "type": "ConnectionError",
        "message": "reset",
    }


def check_failed_span() -> None:
    caught: list[RuntimeError] = []

    def write() -> None:
        try:
            with log.span("deploy"):
                raise RuntimeError("boom")
        except RuntimeError as err:
            caught.append(err)

    start, end = events(write)
    assert len(caught) == 1, "the exception must propagate"
    assert (end["verb"], end["level"], end["status"]) == ("fail", "error", "error")
    assert end["span_id"] == start["span_id"]
    err = end["fields"]["err"]
    assert (err["type"], err["message"]) == ("RuntimeError", "boom")
    # The stack starts at the caller's code, not inside the logger.
    assert "py_utils/log.py" not in err["stack"], err["stack"]


def check_filtered_spans() -> None:
    def write() -> None:
        with log.span("request") as req:
            # DB_LOG_LEVEL=warn hides this span's own events.
            with req.scope("db").span("query") as q:
                q.info("filtered line")
                q.warn("slow query", ms=900)
                # DB_CACHE_LOG_LEVEL=info opens this one again.
                with q.scope("cache").span("lookup") as c:
                    c.info("hit")
            try:
                with req.scope("db").span("migrate"):
                    raise TimeoutError("lock")
            except TimeoutError:
                pass

    written = events(write, DB_LOG_LEVEL="warn", DB_CACHE_LOG_LEVEL="info")
    assert [(e["msg"], e.get("phase")) for e in written] == [
        ("request", "start"),
        ("slow query", None),
        ("lookup", "start"),
        ("hit", None),
        ("lookup", "end"),
        ("migrate", "end"),
        ("request", "end"),
    ], written
    request, slow, lookup, hit, lookup_end, migrate, _ = written
    rid = request["span_id"]
    # What the hidden span holds belongs to its nearest shown ancestor.
    assert slow["span_id"] == rid
    assert lookup["parent_id"] == rid and lookup_end["parent_id"] == rid
    assert hit["span_id"] == lookup["span_id"]
    # A hidden span's failure is at error, so it shows, naming a parent that is there.
    assert migrate["status"] == "error" and migrate["parent_id"] == rid
    assert len({e["trace_id"] for e in written}) == 1


def check_join() -> None:
    assert log.join(None) is log

    def write() -> None:
        joined = log.join(REMOTE)
        joined.info("outside any span")
        with joined.span("handle") as s:
            s.info("inside")

    outside, start, inside, end = events(write)
    assert "trace_id" not in outside and "span_id" not in outside
    assert start["trace_id"] == "0af7651916cd43dd8448eb211c80319c"
    assert start["parent_id"] == "b7ad6b7169203331"
    assert inside["span_id"] == start["span_id"] == end["span_id"]

    returned: list[Any] = []
    [warned] = events(lambda: returned.append(log.join("00-nonsense")))
    assert returned == [log]
    assert (warned["level"], warned["msg"]) == ("warn", "malformed traceparent ignored")
    assert warned["fields"] == {"traceparent": "00-nonsense"}


def run_child(traceparent: str) -> list[Event]:
    code = "from py_utils import log\nwith log.span('child'):\n    pass\nlog.info('done')\n"
    env = {
        **os.environ,
        "TRACEPARENT": traceparent,
        "LOG_FORMAT": "json",
        "LOG_SERVICE": "child",
        "PYTHONPATH": str(SRC_PATH),
    }
    done = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return [parse(text) for text in done.stderr.splitlines()]


def check_traceparent_env() -> None:
    spawned: list[list[Event]] = []

    def write() -> None:
        with log.span("spawn") as s:
            spawned.append(run_child(s.traceparent()))

    start, _ = events(write)
    [[child_start, child_end, done]] = spawned
    # A process started with TRACEPARENT continues the trace with no code.
    assert child_start["trace_id"] == start["trace_id"]
    assert child_start["parent_id"] == start["span_id"]
    assert child_end["parent_id"] == start["span_id"]
    assert child_start["service"] == "child"
    assert "trace_id" not in done

    warned, fresh_start, _, _ = run_child("garbage")
    assert warned["msg"] == "malformed TRACEPARENT ignored"
    assert "parent_id" not in fresh_start


def check_levels() -> None:
    auth = log.scope("api").scope("auth")

    def shown(**env: str | None) -> bool:
        return len(events(lambda: auth.debug("token refreshed"), **env)) == 1

    assert not shown()
    log.set_log_level("debug")
    assert shown(), "set_log_level is the program's default"
    assert not shown(LOG_LEVEL="info"), "LOG_LEVEL overrides set_log_level"
    assert shown(LOG_LEVEL="info", API_LOG_LEVEL="debug"), "scope beats LOG_LEVEL"
    assert not shown(API_LOG_LEVEL="debug", API_AUTH_LOG_LEVEL="info"), (
        "the most specific scope wins"
    )
    log.set_log_level("info")
    assert shown(API_AUTH_LOG_LEVEL="debug")

    # Upper-cased, non-alphanumerics become _, segments joined with _.
    [_] = events(lambda: log.scope("my-api").debug("open"), MY_API_LOG_LEVEL="debug")
    assert events(lambda: log.error("quiet"), LOG_LEVEL="silent") == []

    for setter, value in (
        (log.set_log_level, "verbose"),
        (log.set_log_format, "record"),
        (log.set_log_time, "1"),
        (log.set_log_service, ""),
    ):
        try:
            setter(value)
        except ValueError:
            continue
        raise AssertionError(f"{setter.__name__}({value!r}) must raise")

    for var, value in (
        ("LOG_LEVEL", "DEBUG"),
        ("LOG_FORMAT", "record"),
        ("LOG_TIME", "true"),
    ):
        try:
            lines(lambda: log.info("x"), **{var: value})
        except ValueError:
            continue
        raise AssertionError(f"{var}={value} must raise")


def check_warn_once() -> None:
    def write() -> None:
        log.warn_once("flag --fast is deprecated")
        log.warn_once("flag --fast is deprecated")
        log.scope("cli").warn_once("flag --fast is deprecated")

    written = events(write)
    assert [e.get("scope") for e in written] == [None, ["cli"]]


def check_human() -> None:
    def write() -> None:
        with log.span("build", target="web") as s:
            s.step("transpiling")
            s.set(files=12)

    start, step, end = lines(write, LOG_FORMAT="human", NO_COLOR="1", LOG_TIME="0")
    assert start == "○ build target=web", start
    assert step == "    • transpiling", step
    # The end line renders the end event: the span's fields with what set() added.
    assert re.fullmatch(r"✓ build \d+ms files=12 target=web", end), end


def demonstrate_human() -> None:
    """What a person at a terminal sees."""
    with environ(LOG_FORMAT="human"):
        log.info("human rendering follows")
        with log.span("release", version="0.7.0") as s:
            s.step("building wheel")
            with s.span("checks") as c:
                c.info("ruff", result="clean")
                c.warn_once("slow network", ms=1200)
            s.info(
                "formatting",
                signed=usd(1234.56),
                unsigned=usd(1234.56, signed=False),
                change=percentage(15.234),
            )
            s.set(published=False)
        log.success("logger contract holds")


if __name__ == "__main__":
    assert "TRACEPARENT" not in os.environ, (
        "run without TRACEPARENT: these checks open root spans"
    )
    for key in list(os.environ):
        if key in ("LOG_FORMAT", "LOG_TIME", "LOG_SERVICE") or key.endswith(
            "LOG_LEVEL"
        ):
            del os.environ[key]

    check_shape()
    check_sorting()
    check_values()
    check_errors()
    check_spans()
    check_begin_end()
    check_failed_span()
    check_filtered_spans()
    check_join()
    check_traceparent_env()
    check_levels()
    check_warn_once()
    check_human()
    demonstrate_human()
