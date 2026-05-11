from py_utils.verbalize.passes.phone import expand_phones


def test_spanish_with_country_code():
    out = expand_phones("+34 600 123 456", "spanish")
    assert "más" in out
    assert "tres cuatro" in out  # country
    assert "seis cero cero" in out
    assert "cuatro cinco seis" in out


def test_spanish_bare():
    out = expand_phones("600 123 456", "spanish")
    assert "seis cero cero" in out


def test_dash_separator():
    out = expand_phones("600-123-456", "spanish")
    assert "seis cero cero" in out


def test_english():
    out = expand_phones("+1 555 123 456", "english")
    assert "plus" in out
    assert "five five five" in out


def test_short_number_not_matched():
    # 8 digits — shouldn't trigger (regex needs 9-digit body)
    out = expand_phones("12345678", "spanish")
    assert out == "12345678"


def test_non_supported_lang_noop():
    assert expand_phones("+34 600 123 456", "german") == "+34 600 123 456"
