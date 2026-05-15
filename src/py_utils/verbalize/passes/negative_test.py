from py_utils.verbalize.passes.negative import expand_negatives


def test_leading_minus_start_of_string_es():
    assert expand_negatives("-5", "spanish") == "menos 5"


def test_leading_minus_start_of_string_en():
    assert expand_negatives("-5", "english") == "minus 5"


def test_minus_after_space():
    assert expand_negatives("hace -5 grados", "spanish") == "hace menos 5 grados"


def test_minus_in_temperature():
    # Real-world: -5°C — pass only converts the unary minus, temperature
    # pass handles the °C separately downstream.
    assert expand_negatives("-5°C", "spanish") == "menos 5°C"


def test_compound_word_unchanged():
    # Hyphen between letters is not unary minus.
    assert expand_negatives("compound-word", "english") == "compound-word"


def test_range_unchanged_when_already_consumed():
    # Ranges should be consumed by range_ pass before us. Even if a
    # range-shaped fragment slips through ("2-3"), the digit-before
    # guard keeps us from misreading the inner hyphen as unary minus.
    assert expand_negatives("2-3", "english") == "2-3"


def test_minus_after_comma():
    assert expand_negatives("delta: -2", "english") == "delta: minus 2"


def test_minus_in_parens():
    assert expand_negatives("(-3)", "english") == "(minus 3)"


def test_multiple_negatives():
    out = expand_negatives("from -5 to -10", "english")
    assert out == "from minus 5 to minus 10"


def test_unknown_lang_unchanged():
    assert expand_negatives("-5", "klingon") == "-5"


def test_minus_after_letter_unchanged():
    # ``A-5`` is a name/code shape, not unary minus.
    assert expand_negatives("A-5", "english") == "A-5"
