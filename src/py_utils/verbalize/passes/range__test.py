from py_utils.verbalize.passes.range_ import expand_ranges


def test_year_range_spanish():
    out = expand_ranges("1990-2000", "spanish")
    assert "mil novecientos noventa" in out
    assert " a " in out
    assert "dos mil" in out


def test_year_range_english():
    out = expand_ranges("1990-2000", "english")
    assert "to" in out


def test_small_range():
    out = expand_ranges("10-20", "spanish")
    assert out == "diez a veinte"


def test_inverted_range_passthrough():
    # Inverted range probably isn't a range — leave alone.
    assert expand_ranges("2000-1990", "spanish") == "2000-1990"


def test_implausible_range_passthrough():
    # 5000+ difference: probably not a range.
    out = expand_ranges("100-9999", "spanish")
    assert "9999" in out  # passed through


def test_single_digit_not_matched():
    # Range regex requires ≥2 digits per side.
    assert expand_ranges("1-2", "spanish") == "1-2"
