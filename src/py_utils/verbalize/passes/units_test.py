from py_utils.verbalize.passes.units import expand_units


def test_storage_units_spanish():
    assert "gigabytes" in expand_units("512GB", "spanish")
    assert "megabytes" in expand_units("MB libres", "spanish")


def test_glue_form_handled():
    out = expand_units("100GB rápido", "spanish")
    assert " gigabytes" in out


def test_speed_units():
    out = expand_units("1000 Mbps", "spanish")
    assert "megabits por segundo" in out


def test_byte_rate_units():
    out = expand_units("velocidad 5 GB/s", "spanish")
    assert "gigabytes por segundo" in out


def test_frequency_units():
    out = expand_units("3.2 GHz", "spanish")
    assert "gigahercios" in out


def test_weight_units():
    out = expand_units("2.5 kg", "spanish")
    assert "kilogramos" in out


def test_english():
    out = expand_units("512GB drive", "english")
    assert "gigabytes" in out


def test_not_glued_to_word():
    # "GB" inside "MGBC" shouldn't match
    out = expand_units("MGBC label", "spanish")
    assert out == "MGBC label"


def test_unsupported_lang_noop():
    assert expand_units("512GB", "swahili") == "512GB"


def test_longer_specific_wins_over_shorter():
    # Mbps before MB ensures we don't get "M b p s"-style mangling
    out = expand_units("Mbps", "spanish")
    assert "megabits" in out
