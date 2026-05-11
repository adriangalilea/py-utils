from py_utils.verbalize.passes.roman import expand_romans, _roman_to_int


def test_roman_to_int_basic():
    assert _roman_to_int("I") == 1
    assert _roman_to_int("IV") == 4
    assert _roman_to_int("IX") == 9
    assert _roman_to_int("XV") == 15
    assert _roman_to_int("XXI") == 21
    assert _roman_to_int("MCMXCIV") == 1994


def test_monarch_ordinal_spanish():
    # Felipe VI → ordinal up to 10
    out = expand_romans("Felipe VI", "spanish")
    assert "Felipe sexto" in out


def test_century_cardinal_spanish():
    # siglo XXI → cardinal
    out = expand_romans("siglo XXI", "spanish")
    assert "siglo veintiuno" in out


def test_high_monarch_falls_back_to_cardinal():
    # >X for monarchs: fall back to cardinal
    out = expand_romans("Felipe XV", "spanish")
    # Should NOT expand to "decimoquinto" (would be ordinal); cardinal "quince"
    assert "Felipe quince" in out


def test_pope_context():
    out = expand_romans("Juan Pablo II", "spanish")
    # "Juan Pablo" is in triggers so ordinal reading applies
    assert "Juan Pablo segundo" in out


def test_english_king():
    out = expand_romans("Henry VIII", "english")
    assert "Henry eighth" in out


def test_bare_roman_untouched():
    # Without a trigger word: don't touch, too ambiguous with English/acronyms.
    out = expand_romans("VIII something", "spanish")
    assert "VIII" in out


def test_non_supported_lang_noop():
    assert expand_romans("Felipe VI", "german") == "Felipe VI"
