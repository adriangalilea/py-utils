# py-utils

Python 3.12+. `uv` for everything. `ruff` for lint/format.

- `uv run ruff check src`
- `uv run ruff format src`
- `uv add <pkg>` — add deps
- Runnable examples are the integration tests: `uv run python example_*.py`

No pytest. Correctness comes from offensive primitives (`require`/`invariant`/`ensure`/`must`), the logger tracing every operation, and typed errors with context (`SourcedError`). See `src/py_utils/offensive.py` and `src/py_utils/log.py` for design rationale at the top of each file.

## Logger

`log.py` writes the event stream go-utils and ts-utils write byte for byte. The contract is `~/Developer/utils/README.md` (schema and harness beside it); `log.py`'s header states it for Python. Every verb is `log.info("message", **fields)`, message positional-only. `scope(name)` names a subsystem, `span(name, **fields)` is a context manager and `begin(name, **fields)` / `end(err=None)` the open form; a span is a logger with `span`, `begin`, `set`, `traceparent`, `end`. `join(traceparent)` continues a remote trace, `TRACEPARENT` at start joins root spans. No ambient context: a function that logs inside a span takes the span. Process settings are `log.set_log_level/format/time/service/ship/ship_token`, each overridden by its environment variable. `LOG_SHIP` also POSTs every event's json line in batches; `log.flush_log()` drains them (atexit does it on a normal exit). No dependencies.

Proof, in this order, after any change to `log.py`:

- `uv run python example_usage.py` asserts every rule (key order, sorting, field values, spans, failed and filtered spans, a hidden span's failure line, a stack printed once, join, TRACEPARENT, levels, setters, shipping against a local collector) and prints a human rendering.
- `LOCAL=~/Developer ~/Developer/utils/conformance/run.sh` must print `py PASS`.

No raw writes: `uv run ruff check` refuses `print` (T20) and `sys.stdout.write`/`sys.stderr.write` (TID251) outside the allowlist in `pyproject.toml` (`[tool.ruff.lint.per-file-ignores]`, one reason per entry). A diagnostic is a `log.scope(...)` event; only data for a pipe goes to stdout.
