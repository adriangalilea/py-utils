""""What's new since last time?" — filters a sequence of dicts to only
the ones you haven't seen before. Remembers across runs.

    messages = fetch_messages()
    new_messages = unseen("messages", messages, "id")

    # 1st run:
    #   messages     = [{"id": "1", "from": "alice", "text": "hi"}]
    #   new_messages = [{"id": "1", "from": "alice", "text": "hi"}]
    #
    # 2nd run, no new message:
    #   new_messages = []
    #
    # 3rd run, bob replied:
    #   messages     = [{"id": "1", ...}, {"id": "2", "from": "bob", "text": "hey"}]
    #   new_messages = [{"id": "2", "from": "bob", "text": "hey"}]

Saves state to: $XDG_STATE_HOME/unseen/{namespace}.json
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
