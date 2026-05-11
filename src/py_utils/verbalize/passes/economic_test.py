from py_utils.verbalize.passes.economic import (
    expand_currency,
    expand_percent,
    expand_plus_suffix,
)


def test_currency_prefix():
    out = expand_currency("$10", "spanish")
    assert "10 dólares" in out


def test_currency_suffix():
    out = expand_currency("10€", "spanish")
    assert "10 euros" in out


def test_currency_english():
    out = expand_currency("$100", "english")
    assert "100 dollars" in out


def test_percent_idiom_100_spanish():
    # "100%" → idiomatic "cien por cien" (NOT "cien por ciento")
    out = expand_percent("Tengo 100% confianza", "spanish")
    assert "cien por cien" in out


def test_percent_general_spanish():
    out = expand_percent("Tengo 200%", "spanish")
    assert "200 por ciento" in out


def test_percent_decimal():
    out = expand_percent("12,5%", "spanish")
    assert "12,5 por ciento" in out


def test_percent_english():
    out = expand_percent("50%", "english")
    assert "50 percent" in out


def test_plus_suffix_currency():
    out = expand_plus_suffix("$10,000+", "spanish")
    assert "10,000" in out  # untouched; plus suffix consumed
    assert "o más" in out


def test_plus_suffix_bare():
    out = expand_plus_suffix("1500+ users", "english")
    assert "1500 or more" in out


def test_plus_suffix_percent():
    # 100%+ → 100% o más (percent expander runs afterward)
    out = expand_plus_suffix("100%+", "spanish")
    assert "100%" in out
    assert "o más" in out


def test_plus_suffix_cpp_not_eaten():
    # C++ shouldn't match — no digits.
    assert expand_plus_suffix("C++", "english") == "C++"
