# py-utils

Python 3.12+. `uv` for everything. `ruff` for lint/format.

- `uv run ruff check src`
- `uv run ruff format src`
- `uv add <pkg>` — add deps
- Runnable examples are the integration tests: `uv run python example_*.py`

No pytest. Correctness comes from offensive primitives (`require`/`invariant`/`ensure`/`must`), the logger tracing every operation, and typed errors with context (`SourcedError`). See `src/py_utils/offensive.py` and `src/py_utils/log.py` for design rationale at the top of each file.

## Logger status: STALE vs siblings (2026-08-07)

go-utils and ts-utils rewrote their loggers to a shared doctrine; py-utils deliberately did not (Adrian barely writes Python now), so `log.py` predates it. If Python use ever resumes, align rather than invent, the design questions are all settled. The doctrine: logs go to STDERR (log.py writes stdout today, its one real bug: piped data chokes on log lines); two renderings decided by TTY on the sink, human (symbols, color) vs record, where the record line is byte-identical across the family: `2026-08-07T12:34:56Z WARN  [scope] message` (UTC RFC3339, level word padded to 5, scope bracketed); knobs LOG_FORMAT=human|record and LOG_TIME=1|0 (default: time on in record, off in human; human time is dim local HH:MM:SS), unknown values raise; ladder silent<error<warn<info<debug<trace with unknown LOG_LEVEL raising (log.py silently defaults today); scoped children read {SCOPE}_LOG_LEVEL before LOG_LEVEL (log.py's with_prefix/tag print but do not filter per scope); verbs render, never filter (and `event` should render ✓ like the siblings, not ℹ). Also stale: the dead `time_enabled` config knob (never read), `fatal` as a level (offensive.py owns exiting), the logger globally mutating format's color state, and Rich markup parsing of user messages (text with [brackets] can silently vanish). Keep: task/section/step/progress are the best structure semantics in the family and should survive any rewrite intact. Reference implementations: go-utils logger.go (smallest), ts-utils src/universal/log.ts.
