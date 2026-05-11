from py_utils.verbalize.passes.network import expand_ips


def test_ipv4_spanish():
    out = expand_ips("192.168.1.1", "spanish")
    assert "ciento noventa y dos" in out
    assert "punto" in out
    assert "ciento sesenta y ocho" in out
    assert "uno" in out


def test_ipv4_with_port():
    out = expand_ips("192.168.1.1:8080", "spanish")
    assert "puerto" in out
    assert "ocho mil ochenta" in out


def test_ipv4_english():
    out = expand_ips("10.0.0.1", "english")
    assert "ten" in out and "dot" in out and "zero" in out


def test_invalid_octet_passthrough():
    # 999 > 255 — not a valid IP
    out = expand_ips("999.0.0.1", "spanish")
    assert out == "999.0.0.1"


def test_inside_word_not_matched():
    # ip-like substring inside a longer word
    out = expand_ips("abc1.2.3.4def", "spanish")
    assert out == "abc1.2.3.4def"


def test_unsupported_lang_noop():
    assert expand_ips("192.168.1.1", "german") == "192.168.1.1"
