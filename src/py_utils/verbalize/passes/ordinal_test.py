from py_utils.verbalize.passes.ordinal import expand_ordinals


def test_masculine_indicator():
    # 1º — masculine singular
    assert expand_ordinals("Vivo en el 1º piso", "spanish") == "Vivo en el primero piso"


def test_feminine_indicator():
    # 1ª — feminine singular
    assert "primera" in expand_ordinals("La 1ª opción", "spanish")


def test_apocope_er_suffix():
    # 1er — masculine apocope
    assert "primer" in expand_ordinals("Mi 1er día", "spanish")
    assert "tercer" in expand_ordinals("El 3er capítulo", "spanish")


def test_ascii_indicators():
    # 1o / 1a — ASCII variants of º/ª
    assert "primero" in expand_ordinals("Llegó 1o", "spanish")
    assert "primera" in expand_ordinals("Llegó 1a", "spanish")


def test_two_digit_ordinal():
    out = expand_ordinals("Cumplió 21º", "spanish")
    # num2words returns "vigésimo primero"
    assert "vigésimo primero" in out


def test_out_of_range_passthrough():
    # >999 — left alone
    assert expand_ordinals("1000º algo", "spanish") == "1000º algo"


def test_non_spanish_noop():
    # Other languages: pass through unchanged
    assert expand_ordinals("Vivo en el 1º piso", "english") == "Vivo en el 1º piso"
