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
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager, redirect_stderr
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
            tags={"b", "c", "a"},
            frozen=frozenset({3, 1, 2}),
            mixed={1, "a"},
            keyed={2: "two", 1: "one"},
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
    # Sets are arrays, sorted when their items compare, iteration order otherwise.
    assert f["tags"] == ["a", "b", "c"] and f["frozen"] == [1, 2, 3]
    assert sorted(f["mixed"], key=str) == [1, "a"]
    # Non-string keys: each key's string form, sorted.
    assert list(f["keyed"]) == ["1", "2"]


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
    # The message it was given; str(e)'s [stripe:charge status=402] prefix is keys here.
    assert s["message"] == "declined", s["message"]
    assert (s["source"], s["operation"], s["status"]) == ("stripe", "charge", 402)
    assert list(s["context"]) == ["alpha", "zeta"]
    assert s["cause"] == {"type": "ValueError", "message": "card"}

    # `raise ... from None` hides the context, as Python's own traceback does.
    assert "cause" not in e["fields"]["suppressed"]

    # An empty context is none; so is an absent status.
    bare = SourcedError(source="db", operation="ping", message="down")
    [e] = events(lambda: log.error("failed", err=bare))
    assert list(e["fields"]["err"]) == ["type", "message", "source", "operation"]

    # Python only lets an exception be a cause, so every cause has the error shape.
    try:
        RuntimeError("x").__cause__ = "not an error"  # type: ignore[assignment]
    except TypeError:
        pass
    else:
        raise AssertionError("Python accepted a non-exception __cause__")


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

    # Anything raised ends the block failed, not only Exception subclasses.
    def interrupted() -> None:
        try:
            with log.span("wait for input"):
                raise KeyboardInterrupt
        except KeyboardInterrupt:
            pass

    _, end = events(interrupted)
    assert end["status"] == "error"
    assert end["fields"]["err"]["type"] == "KeyboardInterrupt"


def check_filtered_spans() -> None:
    handed: list[str] = []
    orphan: list[Any] = []

    def write() -> None:
        with log.span("request") as req:
            # DB_LOG_LEVEL=warn hides this span's own events.
            with req.scope("db").span("query") as q:
                q.info("filtered line")
                q.warn("slow query", ms=900)
                handed.append(q.traceparent())
                # DB_CACHE_LOG_LEVEL=info opens this one again.
                with q.scope("cache").span("lookup") as c:
                    c.info("hit")
            try:
                with req.scope("db").span("migrate"):
                    raise TimeoutError("lock")
            except TimeoutError:
                pass
        # A hidden root span has no shown ancestor to name.
        with log.scope("db").span("vacuum") as v:
            orphan.append(v)
            handed.append(v.traceparent())
            v.warn("vacuum slow", ms=4000)

    written = events(write, DB_LOG_LEVEL="warn", DB_CACHE_LOG_LEVEL="info")
    # Visibility is decided at begin and the end follows it: the hidden
    # "migrate" writes no start and no end, but its failure is one fail line.
    assert [(e["msg"], e.get("phase")) for e in written] == [
        ("request", "start"),
        ("slow query", None),
        ("lookup", "start"),
        ("hit", None),
        ("lookup", "end"),
        ("migrate", None),
        ("request", "end"),
        ("vacuum slow", None),
    ], written
    request, slow, lookup, hit, lookup_end, migrate, _, vacuum_slow = written
    # A failure is never lost: the hidden span's failure is a line of its
    # nearest shown span, with the span's fields plus err and dur_ms.
    assert (migrate["verb"], migrate["level"], migrate["scope"]) == (
        "fail",
        "error",
        ["db"],
    )
    assert migrate["span_id"] == request["span_id"]
    assert migrate["trace_id"] == request["trace_id"]
    for absent in ("phase", "parent_id", "status", "dur_ms"):
        assert absent not in migrate, (absent, migrate)
    assert list(migrate["fields"]) == ["dur_ms", "err"]
    assert migrate["fields"]["dur_ms"] >= 0
    assert migrate["fields"]["err"]["message"] == "lock"
    written = written[:5] + written[6:]
    # A line in a hidden span with no shown ancestor carries no ids at all,
    # like a line outside any span: an id names a span a viewer can find.
    assert "trace_id" not in vacuum_slow and "span_id" not in vacuum_slow
    written = written[:-1]
    rid, trace = request["span_id"], request["trace_id"]
    # What the hidden span holds belongs to its nearest shown ancestor.
    assert slow["span_id"] == rid
    assert lookup["parent_id"] == rid and lookup_end["parent_id"] == rid
    assert hit["span_id"] == lookup["span_id"]
    assert len({e["trace_id"] for e in written}) == 1
    # Its traceparent names that ancestor too; a hidden root hands on its own id.
    [vacuum] = orphan
    assert handed == [
        f"00-{trace}-{rid}-01",
        f"00-{vacuum._trace_id}-{vacuum._span_id}-01",
    ], handed


def check_hidden_failure() -> None:
    def write() -> None:
        try:
            with log.scope("db").span("reindex", table="users") as s:
                s.set(rows=3)
                raise TimeoutError("lock")
        except TimeoutError:
            pass

    # A hidden root span has no shown span to name: its failure line has no ids.
    [line] = events(write, DB_LOG_LEVEL="warn")
    assert (line["verb"], line["level"], line["msg"]) == ("fail", "error", "reindex")
    for absent in ("phase", "trace_id", "span_id", "parent_id", "status", "dur_ms"):
        assert absent not in line, (absent, line)
    assert list(line["fields"]) == ["dur_ms", "err", "rows", "table"]
    # The line is a line: a scope silenced at error writes nothing.
    assert events(write, DB_LOG_LEVEL="silent") == []


def check_stack_once() -> None:
    def write() -> None:
        try:
            with log.span("turn") as t:
                with t.span("tool"):
                    raise RuntimeError("tool broke")
        except RuntimeError:
            pass

    # Human: the inner failure prints the stack, the outer one only the message.
    rendered = lines(write, LOG_FORMAT="human", NO_COLOR="1", LOG_TIME="0")
    tracebacks = [i for i, x in enumerate(rendered) if "Traceback" in x]
    fails = [i for i, x in enumerate(rendered) if x.lstrip().startswith("⨯")]
    assert len(fails) == 2 and len(tracebacks) == 1, rendered
    assert fails[0] < tracebacks[0] < fails[1], rendered
    assert rendered[fails[1]].startswith("⨯ turn "), rendered
    assert "err=RuntimeError: tool broke" in rendered[fails[1]].replace('"', "")
    assert fails[1] == len(rendered) - 1, "nothing follows the outer failure"

    # JSON writes the error in full on both ends: they are two facts.
    _, _, inner, outer = events(write)
    assert inner["fields"]["err"] == outer["fields"]["err"]
    assert "stack" in outer["fields"]["err"]

    # A hidden span's failure line counts as the one that printed the stack.
    def hidden_inner() -> None:
        try:
            with log.span("turn") as t:
                with t.scope("db").span("query"):
                    raise RuntimeError("db broke")
        except RuntimeError:
            pass

    rendered = lines(
        hidden_inner,
        LOG_FORMAT="human",
        NO_COLOR="1",
        LOG_TIME="0",
        DB_LOG_LEVEL="warn",
    )
    assert sum("Traceback" in x for x in rendered) == 1, rendered
    assert rendered[-1].startswith("⨯ turn "), rendered

    # A different error raised by the outer span prints its own stack.
    def rewrapped() -> None:
        try:
            with log.span("turn") as t:
                try:
                    with t.span("tool"):
                        raise RuntimeError("tool broke")
                except RuntimeError as e:
                    raise ValueError("turn broke") from e
        except ValueError:
            pass

    rendered = lines(rewrapped, LOG_FORMAT="human", NO_COLOR="1", LOG_TIME="0")
    outer = next(i for i, x in enumerate(rendered) if x.startswith("⨯ turn "))
    assert rendered[-1].strip() == "ValueError: turn broke", rendered
    assert any("Traceback" in x for x in rendered[outer:]), rendered


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

    # Malformed input from outside: ignored, warned about once per distinct value.
    returned: list[Any] = []

    def malformed() -> None:
        returned.append(log.join("00-nonsense"))
        returned.append(log.join("00-nonsense"))
        returned.append(log.join("01-other"))

    first, second = events(malformed)
    assert returned == [log, log, log]
    assert (first["level"], first["msg"]) == ("warn", "malformed traceparent ignored")
    assert first["fields"] == {"traceparent": "00-nonsense"}
    assert second["fields"] == {"traceparent": "01-other"}


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

    # Values match without regard to case, from the environment and from code.
    assert shown(LOG_LEVEL="DEBUG")
    [_] = events(lambda: log.info("upper"), LOG_FORMAT="JSON")
    log.set_log_level("Info")
    assert not shown()

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
        ("LOG_LEVEL", "loud"),
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


@dataclass
class Batch:
    auth: str | None
    content_type: str | None
    user_agent: str | None
    body: str


class Collector:
    """A LOG_SHIP collector on 127.0.0.1: records every batch, answers `answer`."""

    def __init__(self) -> None:
        self.batches: list[Batch] = []
        self.answer = (204, b"")
        lock = threading.Lock()
        self.lock = lock
        collector = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers["Content-Length"]))
                with lock:
                    collector.batches.append(
                        Batch(
                            self.headers.get("Authorization"),
                            self.headers.get("Content-Type"),
                            self.headers.get("User-Agent"),
                            body.decode("utf-8"),
                        )
                    )
                    status, answer = collector.answer
                self.send_response(status)
                self.end_headers()
                self.wfile.write(answer)

            def log_message(self, *_: object) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/ingest"

    def take(self) -> list[Batch]:
        with self.lock:
            taken, self.batches = self.batches, []
        return taken

    def bodies(self) -> list[str]:
        return [b.body for b in self.take()]


def check_ship() -> None:
    """LOG_SHIP: a batch is the stderr lines byte for byte on the contract's
    wire; each trigger sends (50 events, a top-level span's end, 2s,
    flush_log, exit) and a nested span's end does not; 64 KB is the ceiling;
    only what passes the threshold ships; a refused or lost batch is one
    warning, never a raise; a bad configuration raises."""
    c = Collector()
    buf = io.StringIO()

    def taken() -> str:
        text = buf.getvalue()
        buf.seek(0)
        buf.truncate()
        return text.removesuffix("\n")

    def settle() -> None:
        time.sleep(0.3)

    with environ(LOG_FORMAT="json"), redirect_stderr(buf):
        # Off by default: nothing ships.
        log.info("not shipped")
        log.flush_log()
        taken()
        assert c.take() == [], "no LOG_SHIP, no batch"

        with environ(LOG_SHIP=c.url):
            # The wire: stderr's bytes, one POST, text/plain, the bearer.
            log.set_log_ship_token("tok-1")
            log.info("ready", port=1)
            log.warn("retrying", attempt=2, nested={"b": 1, "a": [True, None]})
            log.flush_log()
            [b] = c.take()
            assert b.body == taken(), "a batch is the written lines joined by \\n"
            assert b.content_type == "text/plain;charset=utf-8", b.content_type
            # Not urllib's own, which Cloudflare refuses in front of a collector.
            assert b.user_agent == "adrian-utils", b.user_agent
            assert b.auth == "Bearer tok-1", b.auth
            # The environment wins over code, read live.
            with environ(LOG_SHIP_TOKEN="tok-env"):
                log.info("env token")
                log.flush_log()
            [b] = c.take()
            assert b.auth == "Bearer tok-env", b.auth
            taken()

            # The threshold: what is not written is not shipped.
            log.debug("hidden")
            log.info("shown")
            log.flush_log()
            [body] = c.bodies()
            assert body == taken() and json.loads(body)["msg"] == "shown"

            # Human on stderr, json on the wire.
            with environ(LOG_FORMAT="human"):
                log.info("for a person", k="v")
                log.flush_log()
            [body] = c.bodies()
            assert not taken().startswith("{"), "human on stderr"
            assert json.loads(body)["fields"] == {"k": "v"}, "json shipped"

            # 50 events send at once, without waiting for the timer.
            for i in range(50):
                log.info("tick", i=i)
            settle()
            [body] = c.bodies()
            assert body.count("\n") == 49 and body == taken(), "50 events: one batch"

            # A top-level span's end sends its trace; a nested one's does not.
            log.info("before")
            root = log.begin("request")
            with root.span("db") as db:
                db.info("query")
            settle()
            assert c.take() == [], "a nested span's end does not send"
            root.end()
            settle()
            [body] = c.bodies()
            assert body.count("\n") == 5 and body == taken(), (
                "line, request start, db start, query, db end, request end"
            )
            # A request joined from its caller is top-level here: its end sends too.
            with log.join(REMOTE).span("POST /vote") as s:
                s.info("voted")
            settle()
            [body] = c.bodies()
            assert body == taken(), "a joined top-level span's end sends"
            # A hidden root span still sends what it holds.
            with environ(QUIET_LOG_LEVEL="warn"):
                with log.scope("quiet").span("hidden") as s:
                    s.warn("kept")
            settle()
            [body] = c.bodies()
            assert body.count("\n") == 0 and body == taken(), (
                "a hidden root span's end sends its one shown line"
            )

            # 2s after the first event, with no other trigger.
            log.info("alone")
            time.sleep(1.0)
            assert c.take() == [], "not before 2s"
            time.sleep(1.5)
            [body] = c.bodies()
            assert body == taken(), "the timer sends the waiting batch"

            # 64 KB per batch, never more. Batches in flight together may
            # arrive in any order: each is a run of the written lines, and
            # together they are all of them, once.
            big = "x" * 20_000
            for i in range(7):
                log.info("chunk", big=big, i=i)
            log.flush_log()
            got, written = c.bodies(), taken()
            assert len(got) == 3, f"7 × 20 KB: three batches, got {len(got)}"
            for body in got:
                assert len(body.encode()) <= 64 * 1024, len(body.encode())
                assert body + "\n" in written + "\n", "a run of the written lines"
            assert sum(len(body) + 1 for body in got) - 1 == len(written)
            # One event over the ceiling stays on stderr and warns once.
            log.info("huge", blob="y" * 70_000)
            log.info("huge again", blob="y" * 70_000)
            log.flush_log()
            [body] = c.bodies()
            warning = parse(body)
            assert warning["msg"] == "event too large to ship", warning
            assert warning["level"] == "warn" and warning["scope"] == ["ship"]
            assert taken().count("\n") == 2, "both huge events and the warning written"

            # A refused batch: one warning, shipped with the next batch.
            c.answer = (400, b'{"accepted":0,"rejected":[{"line":1,"why":"x"}]}')
            log.info("refused")
            log.info("refused again")
            log.flush_log()
            c.answer = (204, b"")
            refused, warned = c.take()
            assert refused.body.count("\n") == 1
            warning = parse(warned.body)
            assert warning["msg"] == "log batch refused", warning
            assert warning["fields"] == {
                "answer": '{"accepted":0,"rejected":[{"line":1,"why":"x"}]}',
                "status": 400,
            }, warning
            c.answer = (400, b"")
            log.info("refused once more")
            log.flush_log()
            c.answer = (204, b"")
            assert len(c.take()) == 1, "a refusal warns once"
            taken()

        # A lost batch: one warning with the error.
        dead = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
        dead_url = f"http://127.0.0.1:{dead.server_address[1]}/ingest"
        dead.server_close()
        with environ(LOG_SHIP=dead_url):
            log.info("into the void")
            log.flush_log()
        _, lost = [parse(line) for line in taken().splitlines()]
        assert lost["msg"] == "log batch not delivered", lost
        assert list(lost["fields"]) == ["err"], lost

        # A confused configuration raises.
        for bad in ("ftp://x/y", "not a url"):
            try:
                log.set_log_ship(bad)
            except ValueError:
                continue
            raise AssertionError(f"set_log_ship({bad!r}) must raise")
        try:
            log.set_log_ship_token("")
        except ValueError:
            pass
        else:
            raise AssertionError("an empty token must raise")
        try:
            with environ(LOG_SHIP="nope"):
                log.info("x")
        except ValueError:
            pass
        else:
            raise AssertionError("a bad LOG_SHIP raises on the next event")
        taken()

    # A process ending on its own ships what waits (atexit), and the 2s timer
    # does not hold it. set_log_ship is the setter form of LOG_SHIP.
    code = (
        "from py_utils import log\n"
        f"log.set_log_ship({c.url!r})\n"
        "log.info('child starting', n=1)\n"
        "with log.span('work') as s:\n"
        "    s.info('inside')\n"
        "log.warn('child done')\n"
    )
    env = {
        **os.environ,
        "LOG_FORMAT": "json",
        "LOG_SERVICE": "child",
        "LOG_SHIP_TOKEN": "tok-child",
        "PYTHONPATH": str(SRC_PATH),
    }
    started = time.monotonic()
    done = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    took = time.monotonic() - started
    batches = c.take()
    assert done.stderr.count("\n") == 5, done.stderr
    assert len(batches) == 2, "the span's end sent one batch, atexit the other"
    # Both can be in flight at once, so they may arrive in either order.
    ordered = sorted(batches, key=lambda b: done.stderr.index(b.body + "\n"))
    assert "\n".join(b.body for b in ordered) == done.stderr.removesuffix("\n")
    assert all(b.auth == "Bearer tok-child" for b in batches)
    assert took < 1.9, f"the 2s timer does not hold the process: {took:.2f}s"
    c.server.shutdown()


def demonstrate_human() -> None:
    """What a person at a terminal sees."""
    with environ(LOG_FORMAT="human"):
        log.info("human rendering follows")
        with log.span("release", version="0.8.0") as s:
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
        if key in (
            "LOG_FORMAT",
            "LOG_TIME",
            "LOG_SERVICE",
            "LOG_SHIP",
            "LOG_SHIP_TOKEN",
        ) or key.endswith("LOG_LEVEL"):
            del os.environ[key]

    check_shape()
    check_sorting()
    check_values()
    check_errors()
    check_spans()
    check_begin_end()
    check_failed_span()
    check_filtered_spans()
    check_hidden_failure()
    check_stack_once()
    check_join()
    check_traceparent_env()
    check_levels()
    check_warn_once()
    check_human()
    check_ship()
    demonstrate_human()
