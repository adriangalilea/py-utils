"""
cli, asserted then shown. `uv run python example_cli.py` checks measurement,
clipping and alignment, then renders a table, a kv block, a live region with
worker threads logging above it, and a spinner. Pipe it (`| cat`) to see the
non-TTY degradation: same code, final frames only, no escapes.
"""

import threading
import time

from py_utils import log
from py_utils.ansi import BOLD, RESET, fg, strip_ansi
from py_utils.cli import bar, clip, kv, live, spin, spinner, table, ui, width
from py_utils.offensive import PreconditionError

# --- measurement: visible terminal cells ---
assert width("abc") == 3
assert width(f"{BOLD}{fg(171)}abc{RESET}") == 3, "escapes take no cells"
assert width("é") == 1, "a letter and its accent are one cell"
assert width("👨‍👩‍👧") == 2, "a ZWJ family is one wide grapheme"
assert width("🇪🇸") == 2, "a flag is one wide grapheme"
assert width("日本") == 4, "CJK takes two cells each"

# --- clip: ellipsis at the cut, styles survive and close ---
assert clip("a very long value", 10) == "a very lo…"
assert clip("short", 10) == "short"
styled = clip(f"{fg(2)}a very long value{RESET}", 6)
assert strip_ansi(styled) == "a ver…" and styled.endswith(RESET)
assert clip("日本語テキスト", 5) == "日本…", "a wide char never straddles the cut"

# --- table: aligned on visible width, no trailing whitespace ---
plain = table([["Ada", "x"], ["Bo", "longer"]], head=["name", "v"])
lines = [strip_ansi(line) for line in plain.split("\n")]
assert lines == ["name  v", "Ada   x", "Bo    longer"], lines
colored = table([[ui.ok("ok"), "1"], ["failed", "22"]], align=["l", "r"])
assert [strip_ansi(line) for line in colored.split("\n")] == [
    "ok       1",
    "failed  22",
]
assert all(line == line.rstrip() for line in colored.split("\n"))

# --- offensive edges ---
for bad in (lambda: fg(256), lambda: bar(-1, 3)):
    try:
        bad()
        raise AssertionError("expected a PreconditionError")
    except PreconditionError:
        pass

print(
    table(
        [
            ["ts-utils", ui.ok("10.0.0"), ui.muted("~/Developer/ts-utils")],
            ["zod", ui.ok("4.6.7"), ui.muted("colinhacks/zod")],
            ["ui", "-", ui.muted("~/Developer/ui")],
        ],
        head=["name", "version", "source"],
    )
)
print()
print(kv([("name", "Ada"), ("email", ui.accent("ada@x.com"))], indent=2))
print()

# --- live: workers mutate state and log from threads; lines print above ---
done = {"alpha": 0, "beta": 0, "gamma": 0}
total = 12


def work(name: str, pace: float) -> None:
    for i in range(total):
        time.sleep(pace)
        done[name] = i + 1
        if i == total // 2:
            log.info("halfway", repo=name)


def frame() -> str:
    return table(
        [
            [
                ui.ok("✓") if n == total else spin(),
                name,
                bar(n, total, 18),
                f"{n}/{total}",
            ]
            for name, n in done.items()
        ]
    )


with live(frame):
    threads = [
        threading.Thread(target=work, args=(n, p))
        for n, p in (("alpha", 0.05), ("beta", 0.08), ("gamma", 0.03))
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

with spinner("connecting 0/2") as set_label:
    time.sleep(0.4)
    set_label("connecting 1/2")
    time.sleep(0.4)
    set_label("connected 2/2")

try:
    with spinner("doomed"):
        time.sleep(0.2)
        raise RuntimeError("upstream said no")
except RuntimeError:
    pass
