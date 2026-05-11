from py_utils.verbalize.passes.finance import expand_tickers, expand_iban


def test_crypto_btc_spanish():
    out = expand_tickers("el precio de BTC", "spanish")
    assert "bitcoin" in out


def test_crypto_eth():
    out = expand_tickers("ETH subió", "spanish")
    assert "ethereum" in out


def test_crypto_doge():
    out = expand_tickers("DOGE", "english")
    assert "dogecoin" in out


def test_stock_with_dollar_prefix():
    out = expand_tickers("compré $AAPL", "spanish")
    assert "A A P L" in out


def test_exchange_prefixed():
    out = expand_tickers("NYSE:TSLA cotiza", "spanish")
    assert "T S L A" in out


def test_unknown_dollar_token_letterwise():
    # $ABCD not in dict still letterizes
    out = expand_tickers("$ABCD", "spanish")
    assert "A B C D" in out


def test_iban_spanish():
    out = expand_iban("ES12 3456 7890 1234 5678 9012", "spanish")
    # Country letterwise, check-digit as number, body digit-by-digit
    assert "E S" in out
    assert "doce" in out
    assert "tres cuatro cinco seis" in out


def test_iban_unsupported_lang_noop():
    assert expand_iban("ES12 3456 7890 1234 5678 9012", "german") == "ES12 3456 7890 1234 5678 9012"
