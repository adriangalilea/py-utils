from py_utils.verbalize.passes.color import expand_hex_colors


def test_css_hex_6_digit_spanish():
    out = expand_hex_colors("#FF0000", "spanish")
    # F F cero cero cero cero
    assert "cero cero cero cero" in out
    assert "f f" in out


def test_css_hex_3_digit():
    out = expand_hex_colors("#fff", "spanish")
    assert "f f f" in out


def test_css_hex_8_digit_with_alpha():
    out = expand_hex_colors("#FF0000FF", "spanish")
    assert "f f cero cero cero cero f f" in out


def test_c_hex_0x():
    out = expand_hex_colors("0xDEAD", "spanish")
    assert "d e a d" in out


def test_c_hex_long():
    out = expand_hex_colors("0xCAFEBABE", "spanish")
    assert "c a f e b a b e" in out


def test_english():
    out = expand_hex_colors("#FF0000", "english")
    assert "f f" in out and "zero" in out


def test_hashtag_word_not_matched():
    # Letters only, not hex
    out = expand_hex_colors("#tailwind", "spanish")
    assert "#tailwind" in out  # hashtag, not hex


def test_unsupported_lang_noop():
    assert expand_hex_colors("#FF0000", "swahili") == "#FF0000"
