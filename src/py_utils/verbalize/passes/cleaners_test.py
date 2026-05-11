from py_utils.verbalize.passes.cleaners import strip_emojis, strip_markdown


# ─── Emojis ─────────────────────────────────────────────────────────


def test_strip_emoji_basic():
    out = strip_emojis("Hola 🔥 mundo")
    assert "🔥" not in out
    assert "Hola" in out and "mundo" in out


def test_strip_emoji_glued():
    # "wow🔥cool" should become "wow cool", not "wowcool"
    out = strip_emojis("wow🔥cool")
    assert "wow cool" in out or "wow  cool" in out


def test_zero_width_dropped():
    # ZWJ should be silently removed
    out = strip_emojis("a‍b")
    assert out == "ab"


def test_skin_tone_modifier_stripped():
    # Sk category (skin tone modifiers like 🏻)
    out = strip_emojis("👍🏻")
    assert "🏻" not in out


# ─── Markdown ───────────────────────────────────────────────────────


def test_strip_bold():
    assert strip_markdown("**bold**") == "bold"


def test_strip_italic():
    assert strip_markdown("*italic*") == "italic"


def test_strip_code():
    assert strip_markdown("`code`") == "code"


def test_strip_strike():
    assert strip_markdown("~~strike~~") == "strike"


def test_keep_link_text_and_url():
    # Both alt text and URL are kept; URL gets vocalized in downstream pass.
    out = strip_markdown("[mi web](https://example.com)")
    assert "mi web" in out
    assert "https://example.com" in out


def test_strip_image_keeps_alt():
    out = strip_markdown("![alt text](https://img.png)")
    assert "alt text" in out
    assert "img.png" not in out


def test_strip_heading():
    out = strip_markdown("# Heading 1\nContent")
    assert "Heading 1" in out
    assert not out.startswith("#")


def test_strip_code_block():
    out = strip_markdown("```\nprint('x')\n```")
    # Code blocks dropped entirely
    assert "print" not in out


def test_strip_blockquote():
    out = strip_markdown("> quoted text")
    assert "quoted text" in out
    assert ">" not in out
