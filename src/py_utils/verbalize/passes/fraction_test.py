from py_utils.verbalize.passes.fraction import expand_fractions


def test_quarter_spanish():
    assert expand_fractions("1/4", "spanish") == "un cuarto"


def test_quarter_english():
    assert expand_fractions("1/4", "english") == "one quarter"


def test_half():
    assert expand_fractions("1/2", "spanish") == "un medio"
    assert expand_fractions("1/2", "english") == "one half"


def test_plural_numerator():
    out = expand_fractions("3/8", "spanish")
    assert "tres" in out and "octavos" in out


def test_large_denominator_fallback():
    # Denominators not in the idiom table fall back to "<n>-avos"
    out = expand_fractions("1/15", "spanish")
    assert "avo" in out or "avos" in out


def test_no_match_on_date():
    # 25/6/2026 should NOT match the fraction pattern (third digit
    # group disqualifies via the negative lookahead).
    assert expand_fractions("25/6/2026", "spanish") == "25/6/2026"


def test_no_match_inside_path():
    # /api/v1/users should not match — preceded by '/' which the
    # negative lookbehind catches.
    assert expand_fractions("path/1/2/end", "spanish") == "path/1/2/end"


def test_non_supported_lang_noop():
    assert expand_fractions("1/4", "german") == "1/4"
