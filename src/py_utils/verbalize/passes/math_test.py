from py_utils.verbalize.passes.math import expand_math


def test_pi_spanish():
    out = expand_math("π es aproximadamente 3.14", "spanish")
    assert " pi " in out


def test_infinity():
    out = expand_math("∞", "spanish")
    assert "infinito" in out


def test_squared():
    out = expand_math("E = mc²", "spanish")
    assert "al cuadrado" in out


def test_operator_with_digits():
    out = expand_math("5 = 5", "spanish")
    assert "igual a" in out


def test_operator_not_in_prose():
    # Hyphen between words shouldn't activate
    out = expand_math("compound-word", "spanish")
    assert out == "compound-word"


def test_less_than_digits():
    out = expand_math("5 < 10", "spanish")
    assert "menor que" in out


def test_times_operator():
    out = expand_math("3 × 4", "spanish")
    assert "por" in out


def test_english():
    out = expand_math("5 = 5", "english")
    assert "equals" in out


def test_logical_operators():
    out = expand_math("A ⇒ B", "spanish")
    assert "implica" in out


def test_arrow_reads_as_to_in_prose():
    # ``→`` in chat / code prose reads as "to" / "a", not "implies"
    # (which is reserved for the strict-logic ``⇒`` glyph).
    out = expand_math("input → output", "english")
    assert " to " in out
    assert "implies" not in out

    out = expand_math("entrada → salida", "spanish")
    assert " a " in out
    assert "implica" not in out


def test_set_operators():
    out = expand_math("x ∈ S", "spanish")
    assert "pertenece" in out
