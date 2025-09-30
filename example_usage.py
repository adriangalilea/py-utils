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


if __name__ == "__main__":
    demonstrate_logger()
    demonstrate_formatting()
    log.success("Demo finished")
