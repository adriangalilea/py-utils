from py_utils.verbalize.passes.web import replace_urls


def test_simple_url_vocalized_spanish():
    out = replace_urls("Visita www.example.com", "spanish")
    # "www" → letter-by-letter Spanish names
    assert "uve doble uve doble uve doble" in out
    assert "punto" in out
    assert "example" in out  # word preserved (not letter-by-letter)


def test_simple_url_vocalized_english():
    out = replace_urls("Visit www.example.com", "english")
    assert "w w w" in out
    assert "dot" in out


def test_complex_url_placeholder():
    out = replace_urls("Documentation at https://docs.example.com/v1/api?q=foo", "spanish")
    assert "enlace" in out


def test_force_strip_url():
    out = replace_urls("Visita https://example.com hoy", "spanish", url_placeholder="")
    assert "https" not in out
    assert "example" not in out


def test_email_vocalized():
    out = replace_urls("Escríbeme a foo@example.com", "spanish")
    assert "foo arroba" in out


def test_trailing_punctuation_preserved():
    out = replace_urls("Visita https://example.com.", "spanish")
    # The trailing sentence terminator survives
    assert out.endswith(".")


def test_email_force_strip():
    out = replace_urls("Mail to foo@example.com", "english", email_placeholder="")
    assert "@" not in out
