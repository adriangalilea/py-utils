"""
py_utils: Generic Python utilities (Python 3.12+)

- KEV: Redis-style KV store for environment variables
- XDG: Base Directory paths with spec-compliant fallbacks
- Logger: TTY-focused with tasks/steps/indentation, symbols, colors
- Format: Number/percentage formatting helpers
- Currency: Formatting utilities with optimal decimals
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

from .kev import kev, Kev

from .unseen import unseen

from .offensive import (
    require,
    invariant,
    ensure,
    must,
    boundary,
    ContractError,
    PreconditionError,
    InvariantError,
    PostconditionError,
    SourcedError,
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
    # unseen
    "unseen",
    # offensive
    "require",
    "invariant",
    "ensure",
    "must",
    "boundary",
    "ContractError",
    "PreconditionError",
    "InvariantError",
    "PostconditionError",
    "SourcedError",
    # kev
    "kev",
    "Kev",
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
