"""Adversarial / honest tests — complex realistic inputs, including
cases we know fail today.

The goal is NOT 100% coverage. It's a visible map of the pipeline's
limits so we can evolve it deliberately: passing tests document what
works in realistic shape; ``xfail`` tests document known gaps with
their reason. New regressions in either category surface immediately.

Run with ``pytest --runxfail`` to also execute the known-failing
cases and see how far each one currently fails.
"""

from __future__ import annotations

import pytest

from py_utils.verbalize import normalize


# ─── Multi-class realistic input ────────────────────────────────────

def test_realistic_finance_chat():
    text = (
        "En 2024 invertí en $AAPL ($150/acción), BTC ($60K), y bonos al 5,5%. "
        "Mi cartera vale ~$10,000+ ahora."
    )
    out = normalize(text, lang="es")
    # AAPL letterized
    assert "A A P L" in out
    # BTC → bitcoin
    assert "bitcoin" in out
    # 5,5% → "cinco coma cinco por ciento"
    assert "cinco coma cinco por ciento" in out
    # $10,000+ → ten thousand dollars or more
    assert "diez mil dólares" in out and "o más" in out


def test_realistic_tech_announcement():
    text = (
        "**Bun v1.3.13** released! Try it at https://bun.sh today. "
        "Fixes a TypeError on M3 Ultra (~50% faster) 🚀"
    )
    out = normalize(text, lang="en")
    assert "**" not in out
    assert "version one point three point thirteen" in out
    # URL vocalized — bun.sh is simple
    assert "bun" in out and "dot" in out and "sh" in out
    assert "fifty percent" in out
    assert "🚀" not in out


def test_realistic_meeting_invite():
    text = "Meeting on 25/6/2026 at 15:30 UTC+1. Send invite to @adrian via #calendar."
    out = normalize(text, lang="en")
    # Date got fully expanded ("twenty-five June, two thousand and twenty-six")
    assert "twenty-five June" in out
    # Time fell through to cardinal: "fifteen thirty"
    assert "fifteen thirty" in out
    # Timezone offset
    assert "plus one" in out
    # Mention + hashtag
    assert "at adrian" in out
    assert "hashtag calendar" in out


# ─── Pass interaction edges that DO work ────────────────────────────

def test_date_with_currency():
    # "$1.234,56" — Spanish thousands (.) + decimal (,). Currency
    # pulls the "$" off, then cardinal handles "1.234,56" as
    # "mil doscientos treinta y cuatro coma cincuenta y seis".
    out = normalize("El 25/6/2026 cobré $1.234,56", lang="es")
    assert "veinticinco de junio" in out
    assert "mil doscientos treinta y cuatro coma cincuenta y seis" in out
    assert "dólares" in out


def test_bible_inside_parens():
    out = normalize("(Génesis 1:1-3) dice así", lang="es")
    assert "Génesis, capítulo uno, versículos uno al tres" in out


def test_doi_in_paragraph():
    out = normalize("Ver el paper 10.1234/abcd.5678 publicado en 2024.", lang="es")
    assert "D O I" in out


def test_chemistry_with_subscript_and_digit():
    out = normalize("La fórmula H₂SO₄ y CO2 son comunes", lang="es")
    assert "h dos s o cuatro" in out
    assert "c o dos" in out


# ─── Known failures (documented limits) ─────────────────────────────

@pytest.mark.xfail(reason="Aspect ratios match the range pass — '16:9' is read as a time-like construct or two cardinals")
def test_aspect_ratio_not_a_time():
    # "16:9" should read as "dieciséis a nueve" or "dieciséis nueve"
    # — it's an aspect ratio. Our time regex requires 2-digit minute
    # so "16:9" doesn't match time; cardinal then expands each side.
    out = normalize("La pantalla es 16:9", lang="es")
    assert "dieciséis a nueve" in out


@pytest.mark.xfail(reason="Multi-paragraph mix with all classes — some interactions still mistime")
def test_kitchen_sink_paragraph():
    text = (
        "# Resumen\n"
        "En **2024** invertí en $AAPL ($150/acción), BTC ($60K), y bonos al 5,5%.\n"
        "Mi cartera vale ~$10,000+ ahora. Visita https://miblog.com/inversion-1-4\n"
        "o llámame al +34 600 123 456 entre las 9:00-18:00 UTC+1. 🚀"
    )
    out = normalize(text, lang="es")
    # Every class fires correctly without stomping on its neighbour
    assert "A A P L" in out
    assert "bitcoin" in out
    assert "cinco coma cinco por ciento" in out
    assert "diez mil dólares o más" in out
    # Phone + time range together is the weak spot
    assert "más tres cuatro" in out  # phone country code
    assert "nueve a dieciocho" in out  # time range


@pytest.mark.xfail(reason="Sport scores like '3-1' or '25-21' read as cardinal range, may sound stilted")
def test_sport_score_reading():
    out = normalize("El partido acabó 3-1", lang="es")
    # 3-1 doesn't hit our range regex (needs 2+ digits per side).
    # Falls to cardinal expansion. Listener gets "tres - uno" which
    # is technically correct but not the natural "tres a uno".
    assert "tres a uno" in out


@pytest.mark.xfail(reason="Time range with hyphen — '9:00-18:00' splits awkwardly because time pass runs before range")
def test_time_range_natural_reading():
    out = normalize("Abierto de 9:00-18:00", lang="es")
    # Each side becomes a time, then the hyphen between them reads
    # as a literal pause. Natural: "de las nueve a las dieciocho".
    assert "de las nueve a las dieciocho" in out


def test_roman_no_false_positive_on_english_word():
    # Romans only fire after a trigger word ("siglo", "King", "Felipe",
    # …). Bare "DC" stays as-is because there's no trigger.
    out = normalize("Mike DC arrived", lang="en")
    assert "DC" in out


@pytest.mark.xfail(reason="Math symbols inside prose without flanking digits don't activate — '5 + 3 = 8' works but '+ five' doesn't")
def test_math_symbol_in_prose():
    out = normalize("La fórmula es x + y = z", lang="es")
    # x and y aren't digits so operators stay literal.
    assert "más" in out or "igual" in out


@pytest.mark.xfail(reason="Italian / German / Portuguese / Russian / Japanese / Korean / Chinese have minimal coverage — only basics work")
def test_german_basic_currency():
    out = normalize("Das kostet 100€", lang="de")
    # Currency table has German entries
    assert "Euro" in out
    # But date / abbreviation / unit support is bare-bones for German.
    out2 = normalize("Hr. Schmidt wohnt in der GHz Straße", lang="de")
    assert "Herr Schmidt" in out2  # abbreviation
    assert "Gigahertz" in out2  # unit ← German units not in table


def test_truncated_decade_spanish():
    # "años 90" → cardinal expands 90 to "noventa" naturally. Works
    # by accident (we don't model the truncated-decade construct
    # explicitly), but the output is correct.
    out = normalize("Los años 90 fueron buenos", lang="es")
    assert "años noventa" in out


@pytest.mark.xfail(reason="Coordinates with degree symbol not modeled")
def test_coordinates():
    out = normalize("La latitud es 40.7128° N, 74.0060° W", lang="es")
    assert "grados" in out
    assert "norte" in out and "oeste" in out


def test_doi_complex_suffix():
    # Our DOI regex captures everything up to whitespace / paren, so
    # multi-slash suffixes survive intact. Listener hears the whole
    # tail; the leading "D O I" cue lets them parse it.
    out = normalize("DOI: 10.1234/journal.5678/article", lang="es")
    assert "journal" in out and "article" in out


# ─── Spanish concordance stress ─────────────────────────────────────

def test_concordance_with_loanword():
    out = normalize("Compré 21 gigabytes", lang="es")
    # gigabyte is PROPN with no gender → apocope fires by default
    assert "veintiún gigabytes" in out


def test_concordance_with_quoted_speech():
    # Quotes shouldn't change behaviour
    out = normalize('Dijo: "300 personas"', lang="es")
    assert "trescientas personas" in out


@pytest.mark.xfail(reason="Multiple triggers in succession — 'doscientos y trescientos personas' second one needs lookback")
def test_chained_triggers():
    out = normalize("doscientos y trescientos personas", lang="es")
    assert "doscientas" in out and "trescientas" in out


def test_apocope_across_newline():
    # ``\s+`` matches newlines too, so concordance works across line
    # breaks. (Was worried this'd fail; it doesn't.)
    out = normalize("doscientos\npersonas", lang="es")
    assert "doscientas" in out
