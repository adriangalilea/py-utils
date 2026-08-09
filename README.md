# adrian-utils

Generic Python utilities for DX — terminal logger, typed boundary errors, env var manager (KEV), XDG paths, formatting helpers. Python 3.12+.

The sibling of [go-utils](https://github.com/adriangalilea/go-utils) and [ts-utils](https://github.com/adriangalilea/ts-utils). The logging doctrine the three share, and the harness that proves they emit the same record line, live in [utils](https://github.com/adriangalilea/utils).

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

# Logger — narrate work, not state
log.info("Connected to postgres:5432")
with log.task("Build assets"):
    log.step("Transpiling")
    log.step("Bundling")
log.success("Deployed")

# Typed boundary errors — every external call wears its source
@boundary("stripe")
def charge(customer_id: str, amount: int):
    return stripe.Charge.create(customer=customer_id, amount=amount)

try:
    charge("cus_ABC", 500)
except SourcedError as e:
    log.error(f"[{e.source}] {e.operation} failed: {e}")  # typed forensics, not a string blob

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
        log.error(f"[{e.source}:{e.operation}] skip {doc.id} — {e}")
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

# Debug mode — shows the full lookup chain
kev.debug = True
kev.get("DATABASE_URL")                 # Prints each source checked
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
uv run python example_usage.py       # logger + formatting
uv run python example_offensive.py   # offensive primitives
```

## Linting / formatting

```bash
uv run ruff check src
uv run ruff format src
```

Part of the utils suite by Adrian Galilea: **[go-utils](https://github.com/adriangalilea/go-utils)**, **[ts-utils](https://github.com/adriangalilea/ts-utils)**, **py-utils**.
