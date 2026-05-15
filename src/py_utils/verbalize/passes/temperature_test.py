from py_utils.verbalize.passes.temperature import expand_temperatures


def test_celsius_glued_es():
    assert expand_temperatures("12.9°C", "spanish") == "12.9 grados Celsius"


def test_celsius_spaced_es():
    assert expand_temperatures("12.9 °C", "spanish") == "12.9 grados Celsius"


def test_celsius_lowercase():
    assert expand_temperatures("20°c", "spanish") == "20 grados Celsius"


def test_fahrenheit_en():
    assert expand_temperatures("72°F", "english") == "72 degrees Fahrenheit"


def test_celsius_en():
    assert expand_temperatures("12.9°C", "english") == "12.9 degrees Celsius"


def test_bare_degree_es():
    # Latitude / coordinate.
    assert expand_temperatures("20°", "spanish") == "20 grados"


def test_bare_degree_en():
    assert expand_temperatures("45°", "english") == "45 degrees"


def test_no_scale_letter_after_word():
    # ``20° latitud`` — the bare-degree case (no C/F).
    out = expand_temperatures("20° latitud", "spanish")
    assert out.startswith("20 grados")


def test_celsius_in_sentence():
    out = expand_temperatures("Hace 12.9°C ahora", "spanish")
    assert "grados Celsius" in out
    assert "12.9" in out


def test_unknown_lang_unchanged():
    assert expand_temperatures("12.9°C", "klingon") == "12.9°C"


def test_no_digit_no_match():
    # ``°C`` without a preceding digit shouldn't fire.
    assert expand_temperatures("the °C scale", "english") == "the °C scale"
