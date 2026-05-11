from py_utils.verbalize.passes.acronym import expand_acronyms


def test_letter_initialism_spanish():
    out = expand_acronyms("trabaja en la CIA", "spanish")
    assert "C I A" in out


def test_word_form_spanish():
    out = expand_acronyms("la OTAN se reúne", "spanish")
    assert "otan" in out


def test_letter_initialism_english():
    out = expand_acronyms("the FBI investigates", "english")
    assert "F B I" in out


def test_word_form_english():
    out = expand_acronyms("NASA launched", "english")
    assert "nasa" in out


def test_unknown_acronym_passthrough():
    # Not in dict → unchanged
    out = expand_acronyms("XYZ Corporation", "spanish")
    assert "XYZ" in out


def test_unsupported_lang_noop():
    assert expand_acronyms("FBI", "german") == "FBI"
