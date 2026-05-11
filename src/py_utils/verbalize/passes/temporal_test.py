from py_utils.verbalize.passes.temporal import expand_dates, expand_times


def test_date_dmy_spanish():
    out = expand_dates("25/6/2026", "spanish")
    assert out == "25 de junio de 2026"


def test_date_iso_spanish():
    out = expand_dates("2026-06-25", "spanish")
    assert out == "25 de junio de 2026"


def test_date_english_glue():
    out = expand_dates("25/6/2026", "english")
    assert "25 June, 2026" == out


def test_invalid_date_passthrough():
    # Day > 31: not a date
    assert expand_dates("99/6/2026", "spanish") == "99/6/2026"
    # Month > 12: not a date
    assert expand_dates("25/99/2026", "spanish") == "25/99/2026"


def test_time_quarter_past_spanish():
    out = expand_times("15:15", "spanish")
    assert "15 y cuarto" in out


def test_time_half_past_spanish():
    out = expand_times("15:30", "spanish")
    assert "15 y media" in out


def test_time_regular():
    out = expand_times("15:45", "spanish")
    assert "15 y 45" in out


def test_time_on_the_hour():
    # MM == 0, no seconds → just the hour
    assert expand_times("15:00", "spanish") == "15"


def test_time_with_seconds():
    out = expand_times("15:30:45", "spanish")
    assert "15" in out and "30" in out and "45" in out
    # Fractional reading suppressed when seconds present
    assert "y media" not in out


def test_time_out_of_range_passthrough():
    assert expand_times("30:00", "spanish") == "30:00"


def test_unknown_lang_dates_unchanged():
    # No month names table → unchanged.
    assert expand_dates("25/6/2026", "swahili") == "25/6/2026"
