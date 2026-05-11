"""Financial identifiers — stock tickers, crypto tickers, IBANs.

## Tickers

Three flavours coexist in chat:

1. **Stock tickers**: ``$AAPL``, ``$TSLA``, ``NYSE:AAPL``,
   ``NASDAQ:MSFT``. Spoken letter-by-letter ("a a p l") in both
   languages — short codes are rarely pronounceable.
2. **Crypto tickers**: ``BTC``, ``ETH``, ``USDT``, ``SOL``. Native
   speakers say the FULL NAME ("bitcoin", "ethereum", "solana") rather
   than letter-by-letter. We carry a small lookup for the common ones.
3. **Inline ticker mentions**: ``the BTC price``. Same lookup applies
   (bare tokens) when context (``$`` prefix, exchange-prefix, or
   currency-symbol-adjacent) signals a ticker.

## IBANs

International Bank Account Numbers: ``ES12 3456 7890 1234 5678 9012``.
Read country code + digit groups. The IBAN spec allows up to 34 alnum
characters; we handle the common European 22-26 char form.

Both passes only act on tokens IN their dictionary (tickers) or
matching the precise shape (IBAN). Unknown stock-like tokens pass
through.
"""

from __future__ import annotations

import re

try:
    from num2words import num2words

    _HAS_NUM2WORDS = True
except ImportError:  # pragma: no cover
    _HAS_NUM2WORDS = False


# ─── Crypto ticker lookup ───────────────────────────────────────────
# Crypto convention: read the full chain name. Adding entries here is
# cheaper than maintaining a "letterize or not" heuristic.
_CRYPTO = {
    "BTC":  "bitcoin",
    "ETH":  "ethereum",
    "USDT": "tether",
    "USDC": "u s d c",
    "BNB":  "binance coin",
    "SOL":  "solana",
    "ADA":  "cardano",
    "XRP":  "ripple",
    "DOGE": "dogecoin",
    "DOT":  "polkadot",
    "AVAX": "avalanche",
    "MATIC": "polygon",
    "LINK": "chainlink",
    "LTC":  "litecoin",
    "TRX":  "tron",
    "ATOM": "cosmos",
    "ALGO": "algorand",
    "FIL":  "filecoin",
    "NEAR": "near",
    "APT":  "aptos",
    "ARB":  "arbitrum",
    "OP":   "optimism",
    "SHIB": "shiba inu",
    "TON":  "toncoin",
    "SUI":  "sui",
}

# Stock tickers that aren't already covered by acronym dict. Letter-
# by-letter for most; the ones below are unambiguous and read fine
# spelled out.
_STOCKS_LETTERWISE = {
    "AAPL", "TSLA", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NFLX",
    "NVDA", "AMD", "INTC", "QCOM", "ORCL", "CRM", "ADBE", "PYPL",
    "JPM", "BAC", "GS", "MS", "C", "V", "MA", "DIS", "WMT", "T", "VZ",
    "NYSE", "NASDAQ", "SP500",
}


def _spell(n: int, iso: str) -> str:
    if not _HAS_NUM2WORDS:
        return str(n)
    try:
        return num2words(n, lang=iso)
    except (NotImplementedError, ValueError):
        return str(n)


# Crypto matches anywhere — they're unambiguous tokens, mostly only
# appear as financial mentions.
def _crypto_pattern():
    keys = sorted(_CRYPTO.keys(), key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(re.escape(k) for k in keys) + r")\b")


# Stocks only match when prefixed with $ or NYSE:/NASDAQ: — bare 4-letter
# tokens are too ambiguous with English words.
_DOLLAR_TICKER = re.compile(r"\$([A-Z]{1,5})\b")
_EXCHANGE_TICKER = re.compile(r"\b(?:NYSE|NASDAQ):([A-Z]{1,5})\b")


def expand_tickers(text: str, lang: str) -> str:
    # Crypto first (bare tokens)
    crypto_pat = _crypto_pattern()

    def _crypto(m):
        return _CRYPTO[m.group(1)]

    text = crypto_pat.sub(_crypto, text)

    # $TICKER form
    def _dollar(m):
        sym = m.group(1)
        if sym in _CRYPTO:
            return _CRYPTO[sym]
        if sym in _STOCKS_LETTERWISE:
            return " ".join(sym)
        return " ".join(sym)  # default: letter-by-letter

    text = _DOLLAR_TICKER.sub(_dollar, text)

    # NYSE:TICKER / NASDAQ:TICKER
    def _exchange(m):
        return " ".join(m.group(1))

    text = _EXCHANGE_TICKER.sub(_exchange, text)
    return text


# ─── IBAN ───────────────────────────────────────────────────────────

_IBAN = re.compile(r"\b([A-Z]{2})(\d{2})\s?((?:[A-Z0-9]{4}\s?){3,7})\b")

_ISO = {"spanish": "es", "english": "en"}


def expand_iban(text: str, lang: str) -> str:
    if lang not in _ISO:
        return text
    iso = _ISO[lang]

    def _replace(m):
        country = " ".join(m.group(1))
        check = _spell(int(m.group(2)), iso)
        body_groups = m.group(3).split()
        body_spelled = []
        for grp in body_groups:
            for c in grp:
                if c.isdigit():
                    body_spelled.append(_spell(int(c), iso))
                else:
                    body_spelled.append(c.lower())
        return f"{country} {check} " + " ".join(body_spelled)

    return _IBAN.sub(_replace, text)
