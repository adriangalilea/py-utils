# Logger Design Rationale

This document explains the design of the terminal logger provided by `py_utils.log`. It is optimized for interactive terminals (TTY) and readable plain text when output is redirected (CI/files). No JSON, no stdlib logging.

## Goals
- Instant legibility with minimal cognitive load.
- Small, memorable surface that matches how you narrate work.
- Hierarchical structure (tasks/steps) through indentation, not k=v noise.
- Universal symbols and colors that read at a glance.
- Zero ceremony: works out of the box, minimal configuration.

## Non‑Goals
- No JSON output, no log shipping adapters.
- No stdlib logging configuration or handlers.
- No advanced formatting pipelines; this is a terminal‑first logger.

## Output Modes
- TTY (interactive): colors, symbols, indentation, live spinners for progress.
- Non‑interactive (piped/CI): plain text, no colors, no live updates. Final summaries only.

Detection uses `sys.stdout.isatty()`. Color and live updates can be overridden at runtime.

## Symbols and Colors
- info: ℹ (blue)
- warn: ⚠ (yellow)
- error/fail: ⨯ (red)
- success: ✓ (green)
- wait: ○ (bright white)
- ready: ▶ (green)
- trace: » (magenta)
- step (indented): • (dim)
- section: ▸ (dim)

ASCII fallbacks are trivial (e.g., `i`, `[i]`, `*`).

## Levels vs Status Verbs
- Levels (filter only): trace < debug < info < warn < error < fatal.
- Status verbs (semantics): success, fail, event, wait, ready.

Status verbs are how you naturally think (“start”, “succeeded”, “failed”). Levels remain for filtering noise.

## Structure and Indentation
- task(title): block that logs start and end with duration, indenting its body.
- section(title): grouping without start/end status, indents body.
- step(msg): a single indented bullet under the current block.

This reflects how humans scan logs: hierarchies, not flat lines.

## Progress
A minimal progress handle draws an in‑place spinner/counter in TTY. On completion it prints one final summary line:
- ✓ Sync (3/3, 2.1s)
- ⨯ Sync (2/3, 1.4s)

When not a TTY, only the final line is printed.

## Timers
- time(label) and time_end(label): ad‑hoc measurement that prints a compact duration (default at trace level). Tasks already include durations.

## Context Without k=v
Context is optional and lightweight:
- with_prefix("api") → prints `[api]` before messages.
- tag("auth") → prints `[api auth]` if combined with a prefix.

We avoid `op=`/`k=v` noise; prefer natural phrases and tags.

Numeric tokens produced by `py_utils.format` and `py_utils.currency` emit Rich markup
(`[green]…[/]`, `[red]…[/]`) when color is enabled. The logger parses this markup
automatically in TTY environments and strips it when writing plain text.

## API Overview
- trace(msg)
- debug(msg)
- info(msg)
- warn(msg)
- warn_once(msg)
- error(msg_or_exc, exc: bool=False)
- fatal(msg_or_exc, exit_code=1, exc: bool=False)
- success(msg)
- fail(msg)
- event(msg)
- wait(msg)
- ready(msg)
- step(msg)
- section(title): context manager
- task(title): context manager
- progress(total: int|None=None, title: str|None=None) → handle.tick(), update(n), done(success=True)
- time(label), time_end(label, level="trace")
- with_prefix(text) → Logger
- tag(*tags) → Logger

Configuration (runtime only):
- set_level(level)
- enable_color(bool)
- enable_live_updates(bool)
- set_show_tracebacks(bool)
- set_symbols(bool)

Formatting helpers now add explicit `+`/`-` for non-zero values. Pass `signed=False`
when you want to drop the leading `+` for positive numbers. Color follows the logger:
`enable_color(False)` forces plain text and `set_color_enabled(False)` (in
`py_utils.format`) mirrors that behaviour. Passing `None` reverts to auto detection.

## Error Handling and Tracebacks
- error() prints a single line. If given an Exception or `exc=True`, prints the traceback indented (dim) when enabled.
- task() failures show a red closing line with duration, then an indented traceback (if enabled).

## Examples
- Narration
  - `ℹ Connected to postgres:5432`
- Task
  - `○ Build assets`
  - `  • Transpiling`
  - `  • Bundling`
  - `✓ Build assets (2.3s)`
- Failure
  - `○ Sync`
  - `⨯ Sync (340ms)`
  - `  RuntimeError: ECONNRESET`
  - `  [traceback…]`
- Ready/wait
  - `○ Connecting to DB`
  - `▶ Listening on :8080`

## Why This Shape
- Fast visual parsing via symbols and indentation.
- Status verbs map to how you think and communicate outcomes.
- Minimal config; sensible behavior across TTY/CI without surprises.
- Keeps code terse: no handlers, formatters, or k=v clutter.

## Cross‑Language Alignment
The same semantics map cleanly to TypeScript and Go:
- TS: console/ANSI with the same symbols, task/step helpers.
- Go: text output with the same symbols; structured backends can be added later if needed without changing the front‑door API.

## Future Extensions (Optional)
- Sticky task banners for long‑running services.
- Scoped time prefixes (enable timestamps selectively).
- Simple, explicit adapters if central logging is ever required (opt‑in only).
