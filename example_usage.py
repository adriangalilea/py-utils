"""Example usage of py_utils logger and format helpers.

Run with:
    uv run python example_usage.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure src/ is on the import path when running directly from the repo.
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from py_utils import log, percentage, usd  # noqa: E402


def demonstrate_logger() -> None:
    log.info("Starting demo")

    with log.task("Build assets"):
        log.step("Transpiling modules")
        time.sleep(0.05)
        log.step("Bundling")
        time.sleep(0.05)

    with log.task("Sync files"):
        progress = log.progress(total=3, title="Uploading")
        for _ in range(3):
            time.sleep(0.05)
            progress.tick()
        progress.done(success=True)

    log.warn_once("Flag --fast is deprecated")
    log.warn_once("Flag --fast is deprecated")  # suppressed

    log.time("fetch")
    time.sleep(0.04)
    log.time_end("fetch")


def demonstrate_formatting() -> None:
    with log.section("Formatting helpers"):
        log.info(f"Revenue {usd(1234.56)}")
        log.info(f"Revenue (unsigned) {usd(1234.56, signed=False)}")
        log.info(f"Change {percentage(15.234)}")


def assert_record_golden() -> None:
    """The record line is the shared grep surface of go-utils, ts-utils and
    py-utils — this golden line must match theirs byte for byte."""
    from datetime import datetime, timezone

    from py_utils.log import record_line

    ts = datetime(2026, 8, 7, 12, 34, 56, tzinfo=timezone.utc)
    got = record_line(ts, "WARN", "theater", "scan failed: EOF")
    want = "2026-08-07T12:34:56Z WARN  [theater] scan failed: EOF"
    assert got == want, f"{got!r} != {want!r}"
    assert record_line(ts, "ERROR", "", "boom") == "2026-08-07T12:34:56Z ERROR boom"


if __name__ == "__main__":
    assert_record_golden()
    demonstrate_logger()
    demonstrate_formatting()
    log.success("Demo finished")
