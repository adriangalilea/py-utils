from py_utils.verbalize.passes.sci import expand_sci


def test_positive_exponent_spanish():
    out = expand_sci("1.5e10", "spanish")
    assert "uno coma cinco" in out
    assert "por diez elevado a" in out
    assert "diez" in out  # exponent


def test_negative_exponent():
    out = expand_sci("1e-3", "spanish")
    assert "menos" in out and "tres" in out


def test_capital_E():
    out = expand_sci("2.4E5", "spanish")
    assert "dos coma cuatro" in out
    assert "cinco" in out


def test_english():
    out = expand_sci("1.5e10", "english")
    assert "times ten to the" in out
    assert "one point five" in out
    assert "ten" in out  # exponent


def test_avogadro():
    out = expand_sci("6.022e23", "spanish")
    assert "seis coma" in out
    assert "veintitrés" in out


def test_non_supported_lang_noop():
    assert expand_sci("1.5e10", "italian") == "1.5e10"
