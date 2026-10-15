"""
Pure number formatting: plain strings, no color, no terminal knowledge, so a
value reads the same in a terminal, a file, a JSON field or a bot message.
Color is presentation and belongs to the caller: `cli.ui.ok(percentage(x))`.
"""

from __future__ import annotations

from math import isfinite

SI_SUFFIXES = [
    (1_000_000_000_000_000_000, "E"),
    (1_000_000_000_000_000, "P"),
    (1_000_000_000_000, "T"),
    (1_000_000_000, "G"),
    (1_000_000, "M"),
    (1_000, "K"),
]


def apply_sign(value: float, body: str, *, signed: bool = True) -> str:
    if value < 0:
        return f"-{body}"
    if value > 0 and signed:
        return f"+{body}"
    return body


def number(value: float, decimals: int, *, signed: bool = True) -> str:
    return apply_sign(value, number_plain(abs(value), decimals), signed=signed)


def number_plain(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}"


def with_commas(value: float, decimals: int | None = None) -> str:
    return f"{value:,}" if decimals is None else f"{value:,.{decimals}f}"


def compact(value: float) -> str:
    v = float(value)
    if not isfinite(v) or v == 0:
        return "0"
    for threshold, suffix in SI_SUFFIXES:
        if abs(v) >= threshold:
            return f"{v / threshold:.1f}{suffix}"
    return f"{v:.0f}"


def bytes_fmt(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    v = float(n)
    for unit in ["KiB", "MiB", "GiB", "TiB", "PiB", "EiB"]:
        v /= 1024.0
        if abs(v) < 1024.0:
            return f"{v:.1f} {unit}"
    return f"{v:.1f} ZiB"


def duration(ms: float) -> str:
    if ms >= 10_000:
        return f"{ms / 1000:.1f}s"
    if ms >= 1000:
        return f"{ms / 1000:.2f}s"
    return f"{ms:.0f}ms"


def _percentage_decimals(value: float) -> int:
    av = abs(value)
    if av < 0.1:
        return 2
    if av >= 100:
        return 0
    return 1


def percentage(value: float, *, signed: bool = True) -> str:
    body = f"{abs(value):.{_percentage_decimals(value)}f}%"
    return apply_sign(value, body, signed=signed)


def percentage_change(old: float, new: float, *, signed: bool = True) -> str:
    if old == 0:
        if new == 0:
            return percentage(0.0, signed=signed)
        return percentage(100.0 if new > 0 else -100.0, signed=signed)
    return percentage(((new - old) / abs(old)) * 100.0, signed=signed)


def percentage_diff(a: float, b: float, *, signed: bool = True) -> str:
    avg = (abs(a) + abs(b)) / 2.0
    if avg == 0:
        return percentage(0.0, signed=signed)
    return percentage((abs(a - b) / avg) * 100.0, signed=signed)


def bps(basis_points: int) -> str:
    return f"{basis_points} bps"


def sign(value: float) -> str:
    return "+" if value > 0 else ""


__all__ = [
    "number",
    "number_plain",
    "with_commas",
    "compact",
    "bytes_fmt",
    "duration",
    "percentage",
    "percentage_change",
    "percentage_diff",
    "bps",
    "sign",
    "apply_sign",
]
