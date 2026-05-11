from py_utils.verbalize.passes.version import expand_versions


def test_v_prefixed_three_part():
    out = expand_versions("Bun v1.3.13", "spanish")
    assert "versión uno punto tres punto trece" in out


def test_word_prefixed_bare():
    # Bare X.Y.Z without "version" word: passes through (avoids
    # collision with European thousand-separator numbers).
    out = expand_versions("Python 3.12.10 stable", "spanish")
    assert "3.12.10" in out  # untouched
    # But "versión X.Y.Z" form does expand.
    out2 = expand_versions("Python versión 3.12.10 stable", "spanish")
    assert "versión tres punto doce punto diez" in out2


def test_v_prefixed_two_part():
    out = expand_versions("v1.0 released", "spanish")
    assert "versión uno punto cero" in out


def test_bare_two_part_not_matched():
    # Bare "1.0" with no v/versión context: ambiguous with decimal,
    # leave alone.
    out = expand_versions("the API is at 1.0 stable", "spanish")
    assert "1.0" in out  # untouched


def test_prerelease_suffix():
    out = expand_versions("v1.0.0-rc1", "spanish")
    assert "versión uno punto cero punto cero" in out
    assert "rc1" in out  # suffix preserved


def test_english():
    out = expand_versions("v2.4.0", "english")
    assert "version two point four point zero" in out


def test_unsupported_lang_noop():
    assert expand_versions("v1.0.0", "german") == "v1.0.0"
