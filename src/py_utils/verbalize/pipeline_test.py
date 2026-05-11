"""Integration tests — full normalize() pipeline end-to-end.

These exercise pass ordering and locale post-pass interactions. Each
case is a real-ish input shape from chat / LLM output.
"""

from py_utils.verbalize.pipeline import normalize


# ─── ISO code resolution ────────────────────────────────────────────


def test_iso_code_accepted():
    long_form = normalize("100 GB/s", lang="spanish")
    iso_form = normalize("100 GB/s", lang="es")
    assert long_form == iso_form


def test_unknown_lang_doesnt_crash():
    # Falls through with minimal processing.
    out = normalize("100 GB/s", lang="klingon")
    # No num2words table → digits left as-is.
    assert "100" in out


# ─── End-to-end battery (same cases as tn-compare/ vs NeMo) ────────


def test_unit_with_ratio():
    out = normalize("Velocidad de 100 GB/s", lang="es")
    assert "cien gigabytes por segundo" in out


def test_date_and_time():
    out = normalize("El 25/6/2026 a las 15:30", lang="es")
    assert "veinticinco de junio" in out
    assert "dos mil veintiséis" in out
    assert "quince y media" in out


def test_decimal_with_unit():
    out = normalize("Pesa 2.5 kg y mide 1,75 m", lang="es")
    # Bug-fix case: "2.5" must read as decimal, not "veinticinco"
    assert "dos coma cinco" in out
    assert "kilogramos" in out


def test_abbreviation_chain():
    out = normalize("Sr. García nació en EE.UU. en 1985", lang="es")
    assert "señor García" in out
    assert "Estados Unidos" in out
    assert "mil novecientos ochenta y cinco" in out


def test_percent_general():
    out = normalize("Tengo 200% más energía", lang="es")
    assert "doscientos por ciento" in out


def test_percent_idiom():
    out = normalize("100% genial", lang="es")
    assert "cien por cien" in out


def test_currency_thousands():
    # US thousands handled correctly (NeMo gets this wrong).
    out = normalize("$10,000 USD", lang="es")
    assert "diez mil dólares" in out


def test_plus_suffix():
    out = normalize("1500+ usuarios activos", lang="es")
    assert "mil quinientos o más usuarios" in out


def test_url_in_sentence():
    out = normalize("Visita www.example.com para más info", lang="es")
    assert "uve doble uve doble uve doble" in out
    assert "example" in out


def test_glued_unit_speed():
    out = normalize("El procesador funciona a 3.2 GHz", lang="es")
    assert "tres coma dos gigahercios" in out


def test_european_thousands():
    out = normalize("Mide 1.234.567 píxeles", lang="es")
    assert "un millón" in out


def test_markdown_and_emoji_stripped():
    out = normalize("**Muy importante**: usa `código`", lang="es")
    assert "**" not in out
    assert "`" not in out


def test_emoji_stripped():
    out = normalize("🔥 Increíble noticia 🚀", lang="es")
    assert "🔥" not in out and "🚀" not in out
    assert "Increíble" in out


# ─── Ordinals ───────────────────────────────────────────────────────


def test_ordinal_in_sentence():
    out = normalize("Vivo en el 1º piso", lang="es")
    assert "primero" in out


# ─── Romans ─────────────────────────────────────────────────────────


def test_roman_monarch():
    out = normalize("Felipe VI reinó", lang="es")
    assert "Felipe sexto" in out


def test_roman_century():
    out = normalize("El siglo XXI empezó en 2001", lang="es")
    assert "siglo veintiuno" in out
    assert "dos mil uno" in out


# ─── Fractions ──────────────────────────────────────────────────────


def test_fraction():
    out = normalize("1/4 de la población", lang="es")
    assert "un cuarto" in out


# ─── Phones ─────────────────────────────────────────────────────────


def test_phone():
    out = normalize("Llama al +34 600 123 456", lang="es")
    assert "más" in out and "seis cero cero" in out


# ─── Sci notation ───────────────────────────────────────────────────


def test_sci_notation():
    out = normalize("Hay 6.022e23 moléculas", lang="es")
    assert "seis coma" in out
    assert "elevado a" in out


# ─── Bible references ──────────────────────────────────────────────


def test_bible_ref_single_verse():
    out = normalize("En Génesis 1:1 está el principio", lang="es")
    assert "Génesis, capítulo uno, versículo uno" in out


def test_bible_ref_range():
    # Used by the voiceclone bot's /test command.
    out = normalize("Lee Génesis 1:1-5 en voz alta", lang="es")
    assert "capítulo uno" in out
    assert "versículos uno al cinco" in out


# ─── Feature flags ──────────────────────────────────────────────────


def test_disable_emoji_strip():
    out = normalize("🔥 hola", lang="es", strip_emojis=False)
    assert "🔥" in out


def test_disable_number_expansion():
    out = normalize("100 personas", lang="es", expand_numbers=False)
    assert "100" in out


def test_disable_markdown():
    out = normalize("**bold**", lang="es", strip_markdown=False)
    assert "**" in out


def test_extra_abbreviations():
    out = normalize(
        "API rest",
        lang="es",
        extra_abbreviations={r"\bAPI\b": "interfaz"},
    )
    assert "interfaz" in out
