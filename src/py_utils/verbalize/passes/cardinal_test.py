from py_utils.verbalize.passes.cardinal import expand_numbers


def test_bare_integer_spanish():
    assert expand_numbers("100", "spanish") == "cien"
    assert expand_numbers("1985", "spanish") == "mil novecientos ochenta y cinco"


def test_bare_integer_english():
    assert expand_numbers("100", "english") == "one hundred"


def test_thousands_comma_disambig():
    # US thousands separator. Both languages should read as 7000.
    out_es = expand_numbers("7,000", "spanish")
    assert "siete mil" in out_es
    out_en = expand_numbers("7,000", "english")
    assert "seven thousand" in out_en


def test_thousands_dot_disambig():
    # European thousands separator.
    out_es = expand_numbers("1.234.567", "spanish")
    assert "un millón" in out_es
    out_en = expand_numbers("1.234.567", "english")
    # English reads "1.234.567" as Spanish-style thousands too (3-3-3 pattern).
    assert "one million" in out_en


def test_decimal_spanish_comma():
    # Native Spanish decimal.
    out = expand_numbers("1,75", "spanish")
    assert out == "uno coma setenta y cinco"


def test_decimal_english_dot():
    out = expand_numbers("1.75", "english")
    assert out == "one point seventy-five"


def test_bug_fix_dot_decimal_in_spanish_mixed_text():
    # The classic mixed-locale leak: "2.5 kg" in Spanish text. Previously
    # parsed as "veinticinco" (=25) because dot-thousands triumphed.
    # Now should read as the decimal it visually represents.
    out = expand_numbers("2.5", "spanish")
    assert out == "dos coma cinco"


def test_glue_to_letter_inserts_space():
    # "512GB" should produce "quinientos doce GB" with a space so units
    # pass can vocalize cleanly.
    out = expand_numbers("512GB", "spanish")
    assert out.startswith("quinientos doce ")


def test_single_digit_path():
    assert expand_numbers("5", "spanish") == "cinco"


def test_unknown_lang_passthrough():
    # Language we don't have a num2words mapping for: text unchanged.
    assert expand_numbers("100", "swahili") == "100"
