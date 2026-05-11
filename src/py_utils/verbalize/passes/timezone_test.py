from py_utils.verbalize.passes.timezone import expand_timezones


def test_bare_utc_spanish():
    out = expand_timezones("a las 14 UTC", "spanish")
    assert "U T C" in out


def test_offset_positive():
    out = expand_timezones("UTC+1", "spanish")
    assert "U T C" in out and "más uno" in out


def test_offset_negative():
    out = expand_timezones("GMT-5", "spanish")
    assert "menos cinco" in out


def test_offset_with_minutes():
    out = expand_timezones("UTC+05:30", "spanish")
    assert "más cinco" in out and "treinta" in out


def test_named_zone_spanish():
    out = expand_timezones("nos vemos en CET", "spanish")
    assert "C E T" in out


def test_english():
    out = expand_timezones("Meeting at 14 UTC+1", "english")
    assert "plus one" in out
