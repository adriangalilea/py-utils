# adrian-utils

Generic Python utilities — DX-first terminal logger, XDG directories, number/percentage/currency formatting. Python 3.12+.

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
from py_utils import log, xdg, usd, percentage

# XDG directories
config_file = xdg.config / "myapp" / "config.toml"
data_file = xdg.data / "myapp" / "database.db"
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

## TODO

- Port the KEV environment manager (see `ts-utils/src/platform/kev.ts` and `go-utils/kev.go`).

Part of the utils suite by Adrian Galilea.
