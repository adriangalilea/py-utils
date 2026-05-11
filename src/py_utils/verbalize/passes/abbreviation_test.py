from py_utils.verbalize.passes.abbreviation import expand_abbreviations


def test_spanish_basic():
    out = expand_abbreviations("Sr. García", "spanish")
    assert out == "señor García"


def test_spanish_country_abbrev():
    out = expand_abbreviations("Nací en EE.UU.", "spanish")
    # EE.UU. consumes the trailing dot — sentence terminator is restored.
    assert "Estados Unidos" in out
    assert out.endswith(".")


def test_spanish_currency_codes():
    out = expand_abbreviations("Pago en USD y EUR", "spanish")
    assert "dólares" in out
    assert "euros" in out


def test_english_basic():
    out = expand_abbreviations("Mr. Smith", "english")
    assert "Mister Smith" == out


def test_extra_abbreviations():
    extra = {r"\bAPI\b": "interfaz de programación"}
    out = expand_abbreviations("Usa la API", "spanish", extra_abbreviations=extra)
    assert "interfaz de programación" in out


def test_terminator_restoration():
    # Final period gets restored if abbrev consumed it
    out = expand_abbreviations("Visita EE.UU.", "spanish")
    assert out.endswith(".")


def test_unknown_lang_noop_unless_extra():
    # No table for German Sr. — pass through.
    assert expand_abbreviations("Sr. García", "german") == "Sr. García"
