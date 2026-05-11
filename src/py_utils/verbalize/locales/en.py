"""English post-pass.

Currently a no-op placeholder. English has minimal gender / agreement
rules that need post-processing on top of num2words output. If audit
surfaces real failures, add them here following the Spanish pattern.
"""

from __future__ import annotations


def post_pass(text: str) -> str:
    return text
