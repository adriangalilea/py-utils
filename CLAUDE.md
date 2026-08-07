# py-utils

Python 3.12+. `uv` for everything. `ruff` for lint/format.

- `uv run ruff check src`
- `uv run ruff format src`
- `uv add <pkg>` — add deps
- Runnable examples are the integration tests: `uv run python example_*.py`

No pytest. Correctness comes from offensive primitives (`require`/`invariant`/`ensure`/`must`), the logger tracing every operation, and typed errors with context (`SourcedError`). See `src/py_utils/offensive.py` and `src/py_utils/log.py` for design rationale at the top of each file.

## Logger

`log.py` implements the family logging doctrine shared with go-utils and ts-utils (full spec in its header): stderr sink, human/record renderings decided by TTY, the byte-identical record line `2026-08-07T12:34:56Z WARN  [scope] message`, LOG_FORMAT/LOG_TIME knobs, `scope()` children reading `{SCOPE}_LOG_LEVEL`, and the structure primitives (task/section/step/progress) that are py-utils' own strength. Zero dependencies (Rich dropped). The record golden line is asserted in `example_usage.py`.
