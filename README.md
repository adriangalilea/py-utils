# adrian-utils

Generic Python utilities for DX — structured logger, typed boundary errors, env var manager (KEV), XDG paths, formatting helpers. Python 3.12+.

The sibling of [go-utils](https://github.com/adriangalilea/go-utils) and [ts-utils](https://github.com/adriangalilea/ts-utils). The logging contract the three share, and the harness that proves they write the same event stream, live in [utils](https://github.com/adriangalilea/utils).

## Install

```bash
pip install adrian-utils
# or with uv
uv add adrian-utils
```

## Install (local dev)

```bash
uv add -e .
```

## Usage

```python
from py_utils import log, kev, xdg, boundary, SourcedError, must, usd, percentage

# Logger: a message, then fields
log.info("connected", host="postgres", port=5432)
with log.span("build assets") as s:
    s.step("transpiling")
    s.step("bundling")
log.success("deployed")

# Typed boundary errors — every external call wears its source
@boundary("stripe")
def charge(customer_id: str, amount: int):
    return stripe.Charge.create(customer=customer_id, amount=amount)

try:
    charge("cus_ABC", 500)
except SourcedError as e:
    log.error("charge failed", err=e)  # source, operation, status, context, cause: all in the event

# Optional[T] → T with context
user = must(users.get(user_id), "user vanished", user_id=user_id)

# KEV — Redis-style env vars with source fallbacks
api_key = kev.must_get("API_KEY")
port = kev.int("PORT", 8080)
kev.set("DEBUG", "true")

# XDG paths
config_file = xdg.config / "myapp" / "config.toml"
state_dir = xdg.state / "myapp"

# Formatting
usd(1234.56)          # "+$1,234.56"
percentage(15.234)    # "+15.2%"
```

### Logger

A program's telemetry is one stream of events: a log line is an event at an instant, a span is a piece of work written as a start and an end event, and every line written inside a span names it. go-utils and ts-utils write the same stream byte for byte; the contract and the harness that checks it live in [utils](https://github.com/adriangalilea/utils).

Every verb takes a message, then fields. The message is positional-only, so any field name works:

```python
from py_utils import log

log.info("ready")
log.warn("retrying", attempt=2)
log.error("charge failed", err=e)
```

| verb | level | human |
|---|---|---|
| `error`, `fail` | error | `⨯` |
| `warn`, `warn_once` (once per message and scope) | warn | `⚠` |
| `info` | info | |
| `success` | info | `✓` |
| `wait` | info | `○` |
| `ready` | info | `▶` |
| `step` | info | `•`, indented |
| `debug` | debug | `◦` |
| `trace` | trace | `»` |

**Scopes** name subsystems: `log.scope("api").scope("auth")` writes `"scope":["api","auth"]`.

**Spans** are loggers. What is written through the span belongs to it; there is no ambient context, so a function that logs inside a span takes the span:

```python
with log.span("charge", amount=a) as s:
    s.warn("retrying", attempt=2)
    with s.span("stripe") as c:
        c.info("posted")
    s.set(receipt=r)          # carried on the end event
```

An exception escaping the block ends the span failed (`status: error`, the exception in `fields.err`) and propagates. Work that does not fit a block opens and ends the span by hand, once (a second `end` raises):

```python
s = log.begin("upload", size=n)
...
s.end()                       # or s.end(err)
```

**Traces cross processes** explicitly. `s.traceparent()` is the W3C value to send in an HTTP `traceparent` header or a child's `TRACEPARENT`; `log.join(value)` returns a logger whose spans are children of that remote span (`None` returns `log`, a malformed value is ignored with a warn once per distinct value). A process started with `TRACEPARENT` set joins it for its root spans with no code.

**Output** goes to stderr. `LOG_FORMAT=json` writes one event per line:

```json
{"time":"2026-10-12T12:20:39.123Z","level":"warn","verb":"warn","msg":"retrying","service":"checkout","scope":["payments"],"trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b7","fields":{"attempt":2}}
```

`LOG_FORMAT=human` writes symbols, colour (`NO_COLOR`, `FORCE_COLOR`), dim `key=value` fields, a raised exception's traceback under its line (once: a span that fails with the error a span inside it already failed with shows the message only), and spans with what they hold indented:

```
○ release version=0.7.0
    • building wheel
  ○ checks
      ruff result=clean
  ✓ checks 41ms
✓ release 254ms published=false version=0.7.0
```

The default is human when stderr is a TTY, json otherwise. Field values follow one set of rules: maps sorted at every depth, exceptions as `type`, `message`, `stack`, `cause` (and a `SourcedError`'s `source`, `operation`, `status`, `context`), `datetime` as a UTC millisecond string, `timedelta` as milliseconds, bytes (base64), `Decimal` and integers beyond 2^53 as strings, NaN and infinities as strings, dataclasses as objects, sets as arrays (sorted when their items compare), non-string map keys as their string form, a value that contains itself as `"[circular]"`, anything else as `str()`.

**Configuration.** Each variable has a setter that sets the program's default; the environment overrides it. Values match without regard to case (`LOG_LEVEL=DEBUG` is `debug`), an empty variable is unset, and an unknown value raises `ValueError`.

| variable | setter | values |
|---|---|---|
| `LOG_LEVEL`, `{SCOPE}_LOG_LEVEL` | `log.set_log_level` | `silent` `error` `warn` `info` `debug` `trace`, default `info` |
| `LOG_FORMAT` | `log.set_log_format` | `human` `json` |
| `LOG_TIME` | `log.set_log_time` | `1` `0`: a dim local `HH:MM:SS` before human lines |
| `LOG_SERVICE` | `log.set_log_service` | the program's name, default the script's file name without extension |

A scoped event reads its level live from the most specific variable set: scope `["api", "auth"]` reads `API_AUTH_LOG_LEVEL`, then `API_LOG_LEVEL`, then `LOG_LEVEL`, then `set_log_level`, then `info`. Whether a span is shown is decided once, when it begins, by its start's level; its end follows, so a hidden span writes no end. A failure is never lost to that: a hidden span that fails writes one `fail` line (level error, its name as the message, its fields plus `err` and `dur_ms`) as a line of its nearest shown span, with no `phase`. A hidden span hands its lines, child spans and `traceparent()` to its nearest shown ancestor (its own id only when it has none), so a viewer never meets a parent that is not there.

The runnable proof of every rule above is `uv run python example_usage.py`.

### Typed errors

> "A confused program SHOULD scream." — John Carmack

Python is already offensive by default: exceptions propagate, uncaught crashes the process, `assert` is a language keyword. `py_utils.offensive` does **not** try to replace `assert`. It fills the one real gap Python has — **typed forensics at external-system boundaries** — and adds a small ergonomic helper for `Optional[T]` plus a typed assertion complement for the narrow case of catch-boundaries that route on bug-class.

#### The real win — `@boundary` + `SourcedError`

Every Python codebase talking to external systems reinvents error wrapping badly:

```python
try:
    return stripe.Charge.create(...)
except stripe.error.StripeError as e:
    raise RuntimeError(f"stripe failed: {e}")   # type lost, status lost, context lost
```

Upstream can't tell which system failed, can't read the HTTP status, can't retry per-source, can't serialize the forensics across a queue. `@boundary` + `SourcedError` provide the missing convention:

```python
from py_utils import boundary, SourcedError, log

@boundary("stripe")
def charge(customer_id: str, amount: int) -> Charge:
    return stripe.Charge.create(customer=customer_id, amount=amount)

@boundary("postgres")
def save(row: dict) -> None:
    db.execute("INSERT INTO charges VALUES (?)", row)

for doc in docs:
    try:
        save({"summary": summarize(doc.text)})
    except SourcedError as e:
        log.error("skipping doc", doc=doc.id, err=e)
        if e.source == "stripe" and e.status == 402:
            continue        # card declined, keep going
        if e.source == "postgres":
            raise           # db down, abort the whole batch
```

Every `SourcedError` carries `source`, `operation`, `status`, the original exception (chained via `__cause__`), arbitrary keyword context, and `.to_dict()` for transport across process boundaries. You can also raise one explicitly when you want finer control than the decorator gives you.

#### The ergonomic win — `must()`

`users.get(user_id)` → `Optional[User]` is everywhere in Python, and the idiomatic unwrap is verbose and untyped:

```python
user = users.get(user_id)
if user is None:
    raise RuntimeError(f"user vanished: {user_id}")
process(user)
```

`must()` is the one-liner. It narrows the type for pyright/mypy and carries structured context on failure:

```python
from py_utils import must

user = must(users.get(user_id), "user vanished", user_id=user_id)
process(user)   # user: User, not User | None
```

#### The narrow case — typed assertions that route on bug-class

**For most code, `assert` is fine.** `assert amount > 0, f"bad amount: {amount}"` does the job in scripts and CLIs.

The typed assertion primitives exist for one specific case: a catch boundary that needs to route on *whose bug it is*. HTTP handlers are the canonical example:

```python
from fastapi import FastAPI, HTTPException
from py_utils import require, ensure, boundary, SourcedError, PreconditionError, ContractError

app = FastAPI()

@boundary("stripe")
def stripe_charge(customer_id: str, amount: int) -> Charge:
    return stripe.Charge.create(customer=customer_id, amount=amount)

def do_charge(customer_id: str, amount: int) -> Charge:
    require(amount > 0, "amount must be positive", amount=amount)                 # caller's bug → 400
    result = stripe_charge(customer_id, amount)                                    # stripe's bug → 502
    ensure(result.id is not None, "stripe returned no id", customer_id=customer_id)  # our bug  → 500
    return result

@app.post("/charge")
def charge_endpoint(customer_id: str, amount: int):
    try:
        return do_charge(customer_id, amount)
    except PreconditionError as e:
        raise HTTPException(status_code=400, detail={"error": str(e), **e.context})
    except SourcedError as e:
        raise HTTPException(status_code=502, detail=e.to_dict())
    except ContractError as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})
```

The design-by-contract vocabulary (Eiffel's lineage) names *whose bug* each check catches:

- `require(cond, msg, **ctx)` — precondition: **caller** is wrong → `PreconditionError`
- `invariant(cond, msg, **ctx)` — internal state: **we** are wrong → `InvariantError`
- `ensure(cond, msg, **ctx)` — postcondition: **we broke our promise** → `PostconditionError`

All three subclass `ContractError` → `AssertionError`, so existing `except AssertionError` still catches. **In a script with no such routing boundary, these are overkill — use `assert`.**

#### When to reach for what

| Situation | Use |
|---|---|
| Script or CLI | `assert x, f"..."` |
| Calling an external system (HTTP, db, subprocess) | `@boundary("source")` |
| Unwrapping `Optional[T]` where `None` is a bug | `must(value, ...)` |
| Handler that maps exceptions to HTTP status | `require` / `invariant` / `ensure` |
| Anywhere else | `assert` is fine |

#### Exception hierarchy

```
AssertionError
└── ContractError
    ├── PreconditionError   (require)
    ├── InvariantError      (invariant, must)
    └── PostconditionError  (ensure)

Exception
└── SourcedError            (boundary failures)
```

`@boundary` wraps raw exceptions into `SourcedError` but **lets `ContractError` pass through unwrapped** — contract failures are bugs in *us*, not failures of the external source, and should not be mislabeled.

Full rationale at the top of `src/py_utils/offensive.py`. Runnable demo: `uv run python example_offensive.py`.

### KEV

Redis-style KV store for environment variables. Searches memory → `os.environ` → `.env` files, caches results.

```python
from py_utils import kev

# Basics
api_key = kev.must_get("API_KEY")       # Raises if not found
api_key = kev.get("API_KEY", "dev")     # With default
port = kev.int("PORT", 8080)            # Type conversion
debug = kev.bool("DEBUG", False)        # true/1/yes/on → True
rate = kev.float("RATE", 0.5)           # Float conversion
kev.set("APP_NAME", "myapp")            # Memory only (fast)

# Namespaced access (skip the search chain)
kev.get("os:PATH")                      # ONLY from OS
kev.get(".env:SECRET")                  # ONLY from .env file
kev.set("os:DEBUG", "true")             # Write directly to OS
kev.set(".env:API_KEY", "secret")       # Update .env file

# Source tracking
value, source = kev.get_with_source("API_KEY")  # ("secret", ".env")
kev.source_of("API_KEY")                        # ".env" or "os" or "default"

# Customize search order
kev.source.remove("os")                 # Ignore OS env (perfect for tests!)
kev.source.add(".env.local")            # Add more fallbacks
kev.source.set(".env.test")             # Replace entirely

# Pattern matching
kev.keys("API_*")                       # Find all API_ keys
kev.has("API_KEY")                      # Check if configured
kev.clear("TEMP_*")                     # Clear from memory

# Lookup trace: KEV_LOG_LEVEL=debug logs each source checked (never the value)
kev.get("DATABASE_URL")
```

### XDG

XDG Base Directory paths — reads env vars set by [xdg-dirs](https://github.com/adriangalilea/xdg-dirs), falls back to spec defaults:

```python
from py_utils import xdg

xdg.config / "myapp" / "config.toml"    # ~/.config/myapp/config.toml
xdg.data / "myapp" / "data.db"          # ~/.local/share/myapp/data.db
xdg.state / "notify"                    # ~/.local/state/notify
xdg.cache / "myapp"                     # ~/.cache/myapp
xdg.runtime / "myapp"                   # $XDG_RUNTIME_DIR/myapp
```

### Unseen

"What's new since last time?" — filters a sequence of dicts to only the ones you haven't seen before. Remembers across runs.

```python
from py_utils import unseen

messages = fetch_messages()
new_messages = unseen("messages", messages, "id")
```

1st run:
```
messages     = [{"id": "1", "from": "alice", "text": "hi"}]
new_messages = [{"id": "1", "from": "alice", "text": "hi"}]
```

2nd run, no new message:
```
new_messages = []
```

3rd run, bob replied:
```
messages     = [{"id": "1", ...}, {"id": "2", "from": "bob", "text": "hey"}]
new_messages = [{"id": "2", "from": "bob", "text": "hey"}]
```

Saves state to: `$XDG_STATE_HOME/unseen/{name}.json`

### Colors

Colors auto-disable when stdout is not a TTY. Override at runtime:

```python
from py_utils import set_color_enabled

set_color_enabled(True)   # force on
set_color_enabled(False)  # force off
set_color_enabled(None)   # auto
```

## Run the demos

```bash
uv add -e .
uv run python example_usage.py       # logger contract, asserted; human rendering
uv run python example_offensive.py   # offensive primitives
```

## Linting / formatting

```bash
uv run ruff check src
uv run ruff format src
```

Part of the utils suite by Adrian Galilea: **[go-utils](https://github.com/adriangalilea/go-utils)**, **[ts-utils](https://github.com/adriangalilea/ts-utils)**, **py-utils**.
