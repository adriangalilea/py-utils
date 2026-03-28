"""Filters a sequence of dicts to only the ones you haven't seen before.
Remembers across runs. Safe to re-run on any schedule.

    from py_utils import unseen

    messages = fetch_messages()
    new_messages = unseen("messages", messages, "id")
    # First run → all messages. Second run → only new ones.

State: $XDG_STATE_HOME/unseen/{namespace}.json
"""

import json
from typing import Sequence, TypeVar

from . import xdg

T = TypeVar("T")

_STORE_DIR = xdg.state / "unseen"


def unseen(namespace: str, items: Sequence[T], key: str) -> list[T]:
    store_path = _STORE_DIR / f"{namespace}.json"
    store_path.parent.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set(
        json.loads(store_path.read_text()) if store_path.exists() else []
    )

    result: list[T] = []
    for item in items:
        k = str(item[key])  # type: ignore[index]
        if k not in seen:
            seen.add(k)
            result.append(item)

    store_path.write_text(json.dumps(sorted(seen)))
    return result
