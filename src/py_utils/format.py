from __future__ import annotations

import os
import sys
from math import isfinite
from typing import Optional


SI_SUFFIXES = [
    (1_000_000_000_000_000_000, "E"),
    (1_000_000_000_000_000, "P"),
    (1_000_000_000_000, "T"),
    (1_000_000_000, "G"),
    (1_000_000, "M"),
    (1_000, "K"),
]


def _detect_color() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


_COLOR_ENABLED: bool = _detect_color()


def set_color_enabled(enabled: Optional[bool]) -> None:
    """Override automatic color detection (None resets to auto)."""

    global _COLOR_ENABLED
    if enabled is None:
        _COLOR_ENABLED = _detect_color()
    else:
        _COLOR_ENABLED = bool(enabled)


def color_enabled() -> bool:
    return _COLOR_ENABLED


def _apply_style(text: str, style: str, *, enable_color: Optional[bool] = None) -> str:
    use_color = _COLOR_ENABLED if enable_color is None else bool(enable_color)
    if not use_color:
        return text
    return f"[{style}]{text}[/]"


def _style_by_sign(
    value: float, text: str, *, enable_color: Optional[bool] = None
) -> str:
    if value > 0:
        return _apply_style(text, "green", enable_color=enable_color)
    if value < 0:
        return _apply_style(text, "red", enable_color=enable_color)
    return _apply_style(text, "grey50", enable_color=enable_color)


def color_by_sign(value: float, text: str) -> str:
    return _style_by_sign(value, text)


def apply_sign(value: float, body: str, *, signed: bool = True) -> str:
    if value < 0:
        return f"-{body}"
    if value > 0 and signed:
        return f"+{body}"
    return body


def number(value: float, decimals: int, *, signed: bool = True) -> str:
    body = number_plain(abs(value), decimals)
    text = apply_sign(value, body, signed=signed)
    return _style_by_sign(value, text)


def number_plain(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}"


def with_commas(value: float, decimals: int | None = None) -> str:
    if decimals is None:
        text = f"{value:,}"
    else:
        text = f"{value:,.{decimals}f}"
    return _style_by_sign(value, text)


def compact(value: float) -> str:
    v = float(value)
    if not isfinite(v) or v == 0:
        return _apply_style("0", "grey50")
    abs_v = abs(v)
    for threshold, suffix in SI_SUFFIXES:
        if abs_v >= threshold:
            short = v / threshold
            text = f"{short:.1f}{suffix}"
            return _style_by_sign(v, text)
    text = f"{v:.0f}"
    return _style_by_sign(v, text)


def bytes_fmt(n: int) -> str:
    if n < 1024:
        return _style_by_sign(n, f"{n} B")
    units = ["KiB", "MiB", "GiB", "TiB", "PiB", "EiB"]
    v = float(n)
    for unit in units:
        v /= 1024.0
        if abs(v) < 1024.0:
            text = f"{v:.1f} {unit}"
            return _style_by_sign(n, text)
    return _style_by_sign(n, f"{v:.1f} ZiB")


def duration(ms: float) -> str:
    if ms >= 10_000:
        text = f"{ms / 1000:.1f}s"
    elif ms >= 1000:
        text = f"{ms / 1000:.2f}s"
    else:
        text = f"{ms:.0f}ms"
    return text


def _percentage_decimals(value: float) -> int:
    av = abs(value)
    if av < 0.1:
        return 2
    if av >= 100:
        return 0
    return 1


def percentage(value: float, *, signed: bool = True) -> str:
    d = _percentage_decimals(value)
    body = f"{abs(value):.{d}f}%"
    text = apply_sign(value, body, signed=signed)
    return _style_by_sign(value, text)


def percentage_change(old: float, new: float, *, signed: bool = True) -> str:
    if old == 0:
        if new == 0:
            return percentage(0.0, signed=signed)
        return percentage(100.0 if new > 0 else -100.0, signed=signed)
    pct = ((new - old) / abs(old)) * 100.0
    return percentage(pct, signed=signed)


def percentage_diff(a: float, b: float, *, signed: bool = True) -> str:
    if a == 0 and b == 0:
        return percentage(0.0, signed=signed)
    avg = (abs(a) + abs(b)) / 2.0
    if avg == 0:
        return percentage(0.0, signed=signed)
    pct = (abs(a - b) / avg) * 100.0
    return percentage(pct, signed=signed)


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
    "color_by_sign",
    "apply_sign",
    "set_color_enabled",
    "color_enabled",
]
