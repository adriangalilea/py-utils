"""
py_utils: Generic Python utilities (Python 3.12+)

Currently includes:
- TTY-focused logger with tasks/steps/indentation, symbols, colors
- Number/percentage formatting helpers
- Currency formatting utilities with optimal decimals

This package intentionally avoids stdlib logging and JSON outputs.
It focuses on crisp terminal output for interactive use and CI-friendly
plain text when not attached to a TTY.
"""

from .log import (
    log,
    Logger,
)

from .format import (
    number,
    number_plain,
    with_commas,
    compact,
    bytes_fmt,
    duration,
    percentage,
    percentage_change,
    percentage_diff,
    bps,
    sign,
    apply_sign,
    set_color_enabled,
    color_enabled,
)

from .currency import (
    get_symbol,
    get_optimal_decimals,
    usd,
    btc,
    eth,
    auto,
    is_crypto,
    is_fiat,
    is_stablecoin,
    bps_to_percent,
    percent_to_bps,
)

__all__ = [
    # logger
    "log",
    "Logger",
    # format
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
    "set_color_enabled",
    "color_enabled",
    # currency
    "get_symbol",
    "get_optimal_decimals",
    "usd",
    "btc",
    "eth",
    "auto",
    "is_crypto",
    "is_fiat",
    "is_stablecoin",
    "bps_to_percent",
    "percent_to_bps",
]
