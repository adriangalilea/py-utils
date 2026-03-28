# adrian-utils

Generic Python utilities — KEV environment manager, XDG directories, DX-first terminal logger, number/percentage/currency formatting. Python 3.12+.

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
from py_utils import log, kev, xdg, usd, percentage

# KEV - Redis-style env vars
api_key = kev.must_get("API_KEY")      # Raises if not found
api_key = kev.get("API_KEY", "dev")    # With default
port = kev.int("PORT", 8080)           # Type conversion
kev.set("DEBUG", "true")               # Memory only (fast)
kev.get("os:PATH")                     # Direct from OS
kev.get(".env:SECRET")                 # Direct from .env

# XDG directories
config_file = xdg.config / "myapp" / "config.toml"
data_file = xdg.data / "myapp" / "database.db"
state_dir = xdg.state / "notify"
cache_dir = xdg.cache / "myapp"

# Narration
log.info("Connected to postgres:5432")

# Task with steps
with log.task("Build assets"):
    log.step("Transpiling")
    log.step("Bundling")

# Status
log.success("Deployed")
log.warn_once("Flag --fast is deprecated")

# Progress
with log.task("Sync"):
    p = log.progress(total=3, title="Uploading")
    p.tick(); p.tick(); p.tick(); p.done(success=True)

# Formatting
usd(1234.56)                  # "+$1,234.56" (color and + by default)
usd(1234.56, signed=False)    # "$1,234.56" (no leading +)
percentage(15.234)            # "+15.2%"
percentage(15.234, signed=False)  # "15.2%"
```

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

Colors automatically disable when stdout is not a TTY. To override:

```python
from py_utils import set_color_enabled

set_color_enabled(True)   # force color on
set_color_enabled(False)  # force color off
set_color_enabled(None)   # return to auto detection
```

Run the bundled demo:

```bash
# After `uv add -e .`
uv run python example_usage.py
```

## Linting / Formatting

```bash
uv run ruff check src
uv run ruff format src
```

### Unseen

Persistent dedup filter — makes any script idempotent. Run it once or a thousand times, you only process each item once. Any scheduling works: manual, cron, a loop, whatever.

```python
from py_utils import unseen

# only notifies on NEW orders — safe to run on any schedule
fresh = unseen("orders", all_orders, key=lambda o: o["id"])
for o in fresh:
    notify(o["summary"])
# 1st run: 5 orders → notifies 5. 2nd run: same 5 → notifies 0. 3rd run: 7 → notifies 2.
```

State persists at `~/.local/state/unseen/{namespace}.json`.

## No offensive module

Unlike [go-utils](https://github.com/adriangalilea/go-utils) and [ts-utils](https://github.com/adriangalilea/ts-utils), py-utils has no offensive programming module. Python's exception model is already offensive by default — functions raise with full stack traces, uncaught exceptions crash the process, and `assert` is a language keyword. Go and TS need offensive primitives because their error patterns (`(val, err)` tuples, `try/catch`, `process.exit`) encourage silent failure. Python doesn't have this problem.

Part of the utils suite by Adrian Galilea: **[go-utils](https://github.com/adriangalilea/go-utils)**, **[ts-utils](https://github.com/adriangalilea/ts-utils)**, **py-utils**.
