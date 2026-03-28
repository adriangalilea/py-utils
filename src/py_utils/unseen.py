"""Persistent dedup filter — "what's new since last time?"

Makes any script idempotent. Run it once or a thousand times,
you only process each item once. Any scheduling works:
manual, cron, a loop, whatever.

    1st run: 5 orders exist  → returns 5
    2nd run: same 5 orders   → returns 0
    3rd run: 7 orders exist  → returns 2

Usage:
    from py_utils import unseen

    fresh = unseen("orders", all_orders, key=lambda o: o["id"])
    for o in fresh:
        notify(o["summary"])

State persists at ~/.local/state/unseen/{namespace}.json
"""

import json
from typing import Callable, Sequence, TypeVar

from . import xdg

T = TypeVar("T")

_STORE_DIR = xdg.state / "unseen"


def unseen(namespace: str, items: Sequence[T], key: Callable[[T], str]) -> list[T]:
    _STORE_DIR.mkdir(parents=True, exist_ok=True)
    store_path = _STORE_DIR / f"{namespace}.json"

    seen: set[str] = set(
        json.loads(store_path.read_text()) if store_path.exists() else []
    )

    result: list[T] = []
    for item in items:
        k = key(item)
        if k not in seen:
            seen.add(k)
            result.append(item)

    store_path.write_text(json.dumps(sorted(seen)))
    return result
