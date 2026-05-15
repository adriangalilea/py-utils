from py_utils.verbalize.passes.discourse import expand_slash_or


def test_slash_or_english():
    assert expand_slash_or("foo / bar", "english") == "foo or bar"


def test_slash_or_spanish():
    assert expand_slash_or("foo / bar", "spanish") == "foo o bar"


def test_slash_or_chain():
    out = expand_slash_or("a / b / c", "english")
    assert out == "a or b or c"


def test_slash_glued_left_intact():
    # No whitespace on the left — leave it (could be a path or unit).
    assert expand_slash_or("foo/ bar", "english") == "foo/ bar"


def test_slash_glued_right_intact():
    assert expand_slash_or("foo /bar", "english") == "foo /bar"


def test_slash_no_spaces_intact():
    # Glued slashes (n/a, He/she) stay — handled by earlier passes or
    # not handled at all.
    assert expand_slash_or("and/or", "english") == "and/or"


def test_unknown_lang_pass_through():
    assert expand_slash_or("foo / bar", "klingon") == "foo / bar"
