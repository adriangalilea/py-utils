# py-utils

Python 3.12+. `uv` for everything. `ruff` for lint/format.

- `uv run ruff check src`
- `uv run ruff format src`
- `uv add <pkg>` — add deps
- Runnable examples are the integration tests: `uv run python example_*.py`

No pytest. Correctness comes from offensive primitives (`require`/`invariant`/`ensure`/`must`), the logger tracing every operation, and typed errors with context (`SourcedError`). See `src/py_utils/offensive.py` and `src/py_utils/log.py` for design rationale at the top of each file.
