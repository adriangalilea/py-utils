from py_utils.verbalize.passes.chemistry import expand_chemistry


def test_water():
    out = expand_chemistry("H2O", "spanish")
    assert "h dos o" in out


def test_co2():
    out = expand_chemistry("CO2", "spanish")
    assert "c o dos" in out


def test_ethanol():
    out = expand_chemistry("C2H5OH", "spanish")
    assert "c dos h cinco o h" in out


def test_unicode_subscript():
    out = expand_chemistry("H₂O", "spanish")
    assert "h dos o" in out


def test_no_match_single_capital():
    # Just one capital letter — not a formula
    out = expand_chemistry("Carlos", "spanish")
    assert out == "Carlos"


def test_no_match_inside_word():
    out = expand_chemistry("abH2Ocd", "spanish")
    # Bounded by word-chars: lookbehind/ahead exclude letters
    assert out == "abH2Ocd"


def test_english():
    out = expand_chemistry("CO2", "english")
    assert "c o two" in out


def test_unsupported_lang_noop():
    assert expand_chemistry("H2O", "german") == "H2O"
