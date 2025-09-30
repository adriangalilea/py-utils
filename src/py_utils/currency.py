from __future__ import annotations

from math import fabs

from .format import number_plain, color_by_sign, apply_sign


SYMBOLS: dict[str, str] = {
    "BTC": "₿",
    "XBT": "₿",
    "ETH": "Ξ",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CNY": "¥",
    "KRW": "₩",
    "INR": "₹",
    "RUB": "₽",
    "TRY": "₺",
    "AUD": "A$",
    "CAD": "C$",
    "CHF": "Fr",
    "HKD": "HK$",
    "SGD": "S$",
    "NZD": "NZ$",
    "SEK": "kr",
    "NOK": "kr",
    "DKK": "kr",
    "PLN": "zł",
    "THB": "฿",
    "USDT": "₮",
    "USDC": "$",
    "DAI": "$",
    "BUSD": "$",
}


def get_symbol(code: str) -> str:
    return SYMBOLS.get(code.upper(), code)


def is_stablecoin(code: str) -> bool:
    return code.upper() in {
        "USDT",
        "USDC",
        "DAI",
        "BUSD",
        "UST",
        "TUSD",
        "USDP",
        "GUSD",
        "FRAX",
        "LUSD",
    }


def is_fiat(code: str) -> bool:
    return code.upper() in {
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "CNY",
        "CAD",
        "AUD",
        "CHF",
        "HKD",
        "SGD",
        "NZD",
        "KRW",
        "SEK",
        "NOK",
        "DKK",
        "PLN",
        "THB",
        "INR",
        "RUB",
        "TRY",
        "BRL",
        "MXN",
        "ARS",
        "CLP",
        "COP",
        "PEN",
        "UYU",
        "ZAR",
        "NGN",
        "KES",
    }


def is_crypto(code: str) -> bool:
    return code.upper() in {
        "BTC",
        "XBT",
        "ETH",
        "BNB",
        "XRP",
        "ADA",
        "DOGE",
        "SOL",
        "DOT",
        "MATIC",
        "SHIB",
        "TRX",
        "AVAX",
        "UNI",
        "ATOM",
        "LINK",
        "XMR",
        "XLM",
        "ALGO",
        "VET",
        "MANA",
        "SAND",
        "AXS",
        "THETA",
        "FTM",
        "NEAR",
        "HNT",
        "GRT",
        "ENJ",
        "CHZ",
    }


def get_optimal_decimals(value: float, code: str) -> int:
    if value == 0:
        return 8 if is_crypto(code) else 2
    abs_v = fabs(value)

    if code.upper() in {"BTC", "XBT"}:
        if abs_v < 0.00001:
            return 10
        if abs_v < 0.0001:
            return 9
        if abs_v < 0.001:
            return 8
        if abs_v < 0.01:
            return 7
        if abs_v < 0.1:
            return 6
        if abs_v < 1:
            return 5
        return 4

    if code.upper() == "ETH":
        if abs_v < 0.001:
            return 8
        if abs_v < 0.01:
            return 7
        if abs_v < 0.1:
            return 6
        if abs_v < 1:
            return 5
        return 4

    if code.upper() in {"USD", "USDT", "USDC", "DAI", "BUSD"}:
        if abs_v < 0.01:
            return 6
        if abs_v < 0.1:
            return 4
        if abs_v < 1:
            return 3
        return 2

    if is_crypto(code):
        if abs_v < 0.00001:
            return 8
        if abs_v < 0.0001:
            return 6
        if abs_v < 0.001:
            return 5
        if abs_v < 0.01:
            return 4
        if abs_v < 0.1:
            return 3
        if abs_v < 1:
            return 3
        if abs_v < 100:
            return 2
        return 0

    # fiat defaults
    if abs_v < 0.01:
        return 4
    if abs_v < 0.1:
        return 3
    if abs_v < 1000:
        return 2
    return 0


def usd(value: float, *, signed: bool = True) -> str:
    decimals = get_optimal_decimals(value, "USD")
    body = f"${number_plain(abs(value), decimals)}"
    token = apply_sign(value, body, signed=signed)
    return color_by_sign(value, token)


def btc(value: float, *, signed: bool = True) -> str:
    decimals = get_optimal_decimals(value, "BTC")
    body = f"{number_plain(abs(value), decimals)} ₿"
    token = apply_sign(value, body, signed=signed)
    return color_by_sign(value, token)


def eth(value: float, *, signed: bool = True) -> str:
    decimals = get_optimal_decimals(value, "ETH")
    body = f"{number_plain(abs(value), decimals)} Ξ"
    token = apply_sign(value, body, signed=signed)
    return color_by_sign(value, token)


def auto(value: float, code: str, *, signed: bool = True) -> str:
    decimals = get_optimal_decimals(value, code)
    symbol = get_symbol(code)

    if is_fiat(code) or is_stablecoin(code):
        body = f"{symbol}{number_plain(abs(value), decimals)}"
        token = apply_sign(value, body, signed=signed)
        return color_by_sign(value, token)

    base_body = (
        f"{number_plain(abs(value), decimals)} {symbol if symbol != code else code}"
    )
    token = apply_sign(value, base_body, signed=signed)
    return color_by_sign(value, token)


def bps_to_percent(bps: int) -> float:
    return bps / 100.0


def percent_to_bps(percent: float) -> int:
    return int(round(percent * 100))


__all__ = [
    "get_symbol",
    "is_stablecoin",
    "is_fiat",
    "is_crypto",
    "get_optimal_decimals",
    "usd",
    "btc",
    "eth",
    "auto",
    "bps_to_percent",
    "percent_to_bps",
]
