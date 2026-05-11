from py_utils.verbalize.passes.handle import expand_hashtags, expand_mentions


def test_hashtag_spanish():
    out = expand_hashtags("Usa #tailwind hoy", "spanish")
    assert "etiqueta tailwind" in out


def test_hashtag_english():
    out = expand_hashtags("Try #nextjs today", "english")
    assert "hashtag nextjs" in out


def test_mention_spanish():
    out = expand_mentions("Saluda a @adrian", "spanish")
    assert "arroba adrian" in out


def test_mention_english():
    out = expand_mentions("Ping @adrian", "english")
    assert "at adrian" in out


def test_hashtag_with_digits():
    out = expand_hashtags("#hello2world", "english")
    assert "hashtag hello2world" in out


def test_mention_not_inside_email():
    # @ following digits/word — email-like, leave alone
    out = expand_mentions("send to user@example.com", "english")
    assert "user@example.com" in out  # untouched


def test_unsupported_lang_noop():
    # Pick a language we don't have an entry for in either _HASHTAG_WORD
    # or AT_SIGN_WORD — "swahili" qualifies.
    assert expand_hashtags("#foo", "swahili") == "#foo"
