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


# ─── snake_case identifiers ─────────────────────────────────────────


def test_snake_case_preserved_not_eaten_by_italic():
    # `_WORD_` inside an identifier must not be matched as italic.
    out = strip_markdown("WAKE_WORD_MODEL_PATH")
    assert out == "WAKE WORD MODEL PATH"


def test_snake_case_in_inline_code():
    out = strip_markdown("`dispatch_to_tmux`")
    assert out == "dispatch to tmux"


def test_leading_underscore_dropped():
    # `_fire_wake` → "fire wake" (leading underscore eaten; internal one
    # becomes a space).
    out = strip_markdown("`_fire_wake`")
    assert out == "fire wake"


def test_italic_still_works_at_word_boundary():
    assert strip_markdown("_italic_") == "italic"
    assert strip_markdown("hello _italic_ world") == "hello italic world"


# ─── List item phrase break ─────────────────────────────────────────


def test_numbered_list_inserts_sentence_break():
    # Items without their own terminator get one so TTS phrase-breaks.
    out = strip_markdown("1. one\n2. two\n3. three")
    # Normalised through pipeline whitespace collapse would read
    # "one. two. three".
    assert out == "one.\ntwo.\nthree"


def test_list_after_colon_keeps_colon():
    # An intro ending in `:` is already a sentence boundary; don't
    # double it.
    out = strip_markdown("intro:\n1. foo\n2. bar")
    assert out == "intro:\nfoo.\nbar"


def test_list_after_period_unchanged():
    out = strip_markdown("intro.\n1. foo\n2. bar")
    assert out == "intro.\nfoo.\nbar"


# ─── Double-hyphen artifact ─────────────────────────────────────────


def test_word_glued_double_hyphen_collapsed():
    # ``\`pb-\`-prefixed`` leaves ``pb--prefixed`` after inline-code
    # stripping; collapse the double dash so TTS doesn't read "dash
    # dash".
    out = strip_markdown("`pb-`-prefixed")
    assert out == "pb-prefixed"


def test_spaced_em_dash_preserved():
    # `a -- b` is em-dash usage in prose; don't collapse.
    out = strip_markdown("a -- b")
    assert out == "a -- b"
