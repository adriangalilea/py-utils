"""Per-language data tables shared across passes.

Single source of truth so passes don't carry their own copies. Each
dict is keyed by Qwen3-TTS-style long language name (``"spanish"``,
``"english"``, …); the ISO-code accepted by ``normalize()`` is mapped
to the long form in :mod:`py_utils.verbalize.pipeline` before any pass
sees it.

Languages in this file match the Qwen3-TTS ``codec_language_id`` map:
chinese, english, french, german, italian, japanese, korean,
portuguese, russian, spanish. Per-class coverage is best-effort —
Spanish and English are production-tuned, the rest are correct in
shape but contain minimal dictionaries.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


# Map Qwen3-TTS language names to num2words ISO codes. num2words supports
# 25+ languages; this is the subset Qwen3-TTS itself supports. Chinese is
# omitted because num2words renders Chinese numbers in pinyin words rather
# than the natural form a Chinese speaker would say.
NUM2WORDS_LANG: Dict[str, str] = {
    "spanish":    "es",
    "english":    "en",
    "french":     "fr",
    "german":     "de",
    "italian":    "it",
    "portuguese": "pt",
    "japanese":   "ja",
    "korean":     "ko",
    "russian":    "ru",
}

# ISO → long name. Accepted as input by `normalize(lang=…)` so callers
# can use either convention. Unknown values fall through unchanged and
# downstream passes treat them as "language we have no table for, leave
# alone" — same behaviour as if the long name had been passed directly.
ISO_TO_LONG: Dict[str, str] = {
    "es": "spanish",
    "en": "english",
    "fr": "french",
    "de": "german",
    "it": "italian",
    "pt": "portuguese",
    "ja": "japanese",
    "ko": "korean",
    "zh": "chinese",
    "ru": "russian",
}

# Per-language word for the dot in vocalized hostnames ("example punto
# com") and for the @ in vocalized email addresses ("foo arroba bar").
# Distinct from DECIMAL_WORD — Spanish uses "punto" for URL dots but
# "coma" for decimal numbers. Native readers really do say different
# words for the same character in different contexts.
URL_DOT_WORD: Dict[str, str] = {
    "spanish":    "punto",
    "english":    "dot",
    "french":     "point",
    "german":     "Punkt",
    "italian":    "punto",
    "portuguese": "ponto",
    "japanese":   "ドット",
    "korean":     "점",
    "chinese":    "点",
    "russian":    "точка",
}

# Letter names for letter-by-letter spelling. Only populated where the
# bare letter would mispronounce — Spanish "w" must be spelled "uve
# doble" (RAE) rather than emitting a bare 'w' that TTS reads as "wuwuwu".
# Languages without an entry fall through to bare letter emission.
LETTER_NAMES: Dict[str, Dict[str, str]] = {
    "spanish": {
        "a": "a",        "b": "be",       "c": "ce",       "d": "de",
        "e": "e",        "f": "efe",      "g": "ge",       "h": "hache",
        "i": "i",        "j": "jota",     "k": "ka",       "l": "ele",
        "m": "eme",      "n": "ene",      "ñ": "eñe",      "o": "o",
        "p": "pe",       "q": "cu",       "r": "erre",     "s": "ese",
        "t": "te",       "u": "u",        "v": "uve",      "w": "uve doble",
        "x": "equis",    "y": "ye",       "z": "zeta",
    },
}

AT_SIGN_WORD: Dict[str, str] = {
    "spanish":    "arroba",
    "english":    "at",
    "french":     "arobase",
    "german":     "at",
    "italian":    "chiocciola",
    "portuguese": "arroba",
    "japanese":   "アット",
    "korean":     "골뱅이",
    "chinese":    "at",
    "russian":    "собака",
}

# Used for COMPLEX URLs only (any path, query, fragment beyond bare host).
# Simple URLs bypass this and get vocalized directly via LETTER_NAMES so a
# listener can transcribe them back from audio. Pass empty string to force
# strip; empty-bracket cleanup runs in that mode.
URL_PLACEHOLDER: Dict[str, str] = {
    "spanish":    "enlace",
    "english":    "link",
    "french":     "lien",
    "german":     "Link",
    "italian":    "collegamento",
    "portuguese": "ligação",
    "japanese":   "リンク",
    "korean":     "링크",
    "chinese":    "链接",
    "russian":    "ссылка",
}

EMAIL_PLACEHOLDER: Dict[str, str] = {
    "spanish":    "correo",
    "english":    "email",
    "french":     "courriel",
    "german":     "E-Mail",
    "italian":    "email",
    "portuguese": "email",
    "japanese":   "メール",
    "korean":     "이메일",
    "chinese":    "电子邮件",
    "russian":    "адрес",
}

# Currency symbol → spoken word, per language. Symbols are matched both
# as prefix ("$10") and suffix ("10€") because conventions vary.
CURRENCY: Dict[str, Dict[str, str]] = {
    "spanish":    {"€": "euros", "$": "dólares", "£": "libras",   "¥": "yenes"},
    "english":    {"€": "euros", "$": "dollars", "£": "pounds",   "¥": "yen"},
    "french":     {"€": "euros", "$": "dollars", "£": "livres",   "¥": "yens"},
    "german":     {"€": "Euro",  "$": "Dollar",  "£": "Pfund",    "¥": "Yen"},
    "italian":    {"€": "euro",  "$": "dollari", "£": "sterline", "¥": "yen"},
    "portuguese": {"€": "euros", "$": "dólares", "£": "libras",   "¥": "ienes"},
    "japanese":   {"€": "ユーロ", "$": "ドル",    "£": "ポンド",    "¥": "円"},
    "korean":     {"€": "유로",   "$": "달러",    "£": "파운드",    "¥": "엔"},
    "chinese":    {"€": "欧元",   "$": "美元",    "£": "英镑",      "¥": "元"},
    "russian":    {"€": "евро",  "$": "долларов","£": "фунтов",    "¥": "иен"},
}

# Unit acronyms with letter-only lookbehind/lookahead so the regex
# matches whether glued to digits ("512GB") or standalone ("the GB
# drive"). Each replacement is prefixed with a space so glued forms get
# a clean separator (whitespace collapse pass at the end fixes any
# double-space in the standalone case).
#
# Insertion order matters: longer/more-specific patterns must come
# before shorter ones so "Mbps" doesn't get partially eaten by "MB".
# Python 3.7+ preserves dict insertion order — relied on here.
#
# Standalone single-letter units (g for gramos, m for metros) are
# excluded because they collide too easily with ordinary text. Only
# acronyms unambiguous in normal text get expanded.
UNITS: Dict[str, Dict[str, str]] = {
    "spanish": {
        r"(?<![a-zA-Z])Mbps(?![a-zA-Z])": " megabits por segundo",
        r"(?<![a-zA-Z])Gbps(?![a-zA-Z])": " gigabits por segundo",
        r"(?<![a-zA-Z])Kbps(?![a-zA-Z])": " kilobits por segundo",
        r"(?<![a-zA-Z])kWh(?![a-zA-Z])":  " kilovatios hora",
        r"(?<![a-zA-Z])GHz(?![a-zA-Z])":  " gigahercios",
        r"(?<![a-zA-Z])MHz(?![a-zA-Z])":  " megahercios",
        r"(?<![a-zA-Z])kHz(?![a-zA-Z])":  " kilohercios",
        r"(?<![a-zA-Z])RPM(?![a-zA-Z])":  " revoluciones por minuto",
        r"(?<![a-zA-Z])FPS(?![a-zA-Z])":  " fotogramas por segundo",
        r"(?<![a-zA-Z])DPI(?![a-zA-Z])":  " puntos por pulgada",
        r"(?<![a-zA-Z])GB/s(?![a-zA-Z])": " gigabytes por segundo",
        r"(?<![a-zA-Z])MB/s(?![a-zA-Z])": " megabytes por segundo",
        r"(?<![a-zA-Z])KB/s(?![a-zA-Z])": " kilobytes por segundo",
        r"(?<![a-zA-Z])TB/s(?![a-zA-Z])": " terabytes por segundo",
        r"(?<![a-zA-Z])GB(?![a-zA-Z])":   " gigabytes",
        r"(?<![a-zA-Z])MB(?![a-zA-Z])":   " megabytes",
        r"(?<![a-zA-Z])KB(?![a-zA-Z])":   " kilobytes",
        r"(?<![a-zA-Z])TB(?![a-zA-Z])":   " terabytes",
        r"(?<![a-zA-Z])PB(?![a-zA-Z])":   " petabytes",
        r"(?<![a-zA-Z])MP(?![a-zA-Z])":   " megapíxeles",
        r"(?<![a-zA-Z])kW(?![a-zA-Z])":   " kilovatios",
        r"(?<![a-zA-Z])MW(?![a-zA-Z])":   " megavatios",
        r"(?<![a-zA-Z])GW(?![a-zA-Z])":   " gigavatios",
        r"(?<![a-zA-Z])Hz(?![a-zA-Z])":   " hercios",
        r"(?<![a-zA-Z])km/h(?![a-zA-Z])": " kilómetros por hora",
        r"(?<![a-zA-Z])m/s(?![a-zA-Z])":  " metros por segundo",
        r"(?<![a-zA-Z])kg(?![a-zA-Z])":   " kilogramos",
        r"(?<![a-zA-Z])mg(?![a-zA-Z])":   " miligramos",
        r"(?<![a-zA-Z])ml(?![a-zA-Z])":   " mililitros",
        r"(?<![a-zA-Z])km(?![a-zA-Z])":   " kilómetros",
        r"(?<![a-zA-Z])cm(?![a-zA-Z])":   " centímetros",
        r"(?<![a-zA-Z])mm(?![a-zA-Z])":   " milímetros",
        r"(?<![a-zA-Z])ms(?![a-zA-Z])":   " milisegundos",
    },
    "english": {
        r"(?<![a-zA-Z])Mbps(?![a-zA-Z])": " megabits per second",
        r"(?<![a-zA-Z])Gbps(?![a-zA-Z])": " gigabits per second",
        r"(?<![a-zA-Z])Kbps(?![a-zA-Z])": " kilobits per second",
        r"(?<![a-zA-Z])kWh(?![a-zA-Z])":  " kilowatt-hours",
        r"(?<![a-zA-Z])GHz(?![a-zA-Z])":  " gigahertz",
        r"(?<![a-zA-Z])MHz(?![a-zA-Z])":  " megahertz",
        r"(?<![a-zA-Z])kHz(?![a-zA-Z])":  " kilohertz",
        r"(?<![a-zA-Z])RPM(?![a-zA-Z])":  " revolutions per minute",
        r"(?<![a-zA-Z])FPS(?![a-zA-Z])":  " frames per second",
        r"(?<![a-zA-Z])DPI(?![a-zA-Z])":  " dots per inch",
        r"(?<![a-zA-Z])GB/s(?![a-zA-Z])": " gigabytes per second",
        r"(?<![a-zA-Z])MB/s(?![a-zA-Z])": " megabytes per second",
        r"(?<![a-zA-Z])KB/s(?![a-zA-Z])": " kilobytes per second",
        r"(?<![a-zA-Z])TB/s(?![a-zA-Z])": " terabytes per second",
        r"(?<![a-zA-Z])GB(?![a-zA-Z])":   " gigabytes",
        r"(?<![a-zA-Z])MB(?![a-zA-Z])":   " megabytes",
        r"(?<![a-zA-Z])KB(?![a-zA-Z])":   " kilobytes",
        r"(?<![a-zA-Z])TB(?![a-zA-Z])":   " terabytes",
        r"(?<![a-zA-Z])PB(?![a-zA-Z])":   " petabytes",
        r"(?<![a-zA-Z])MP(?![a-zA-Z])":   " megapixels",
        r"(?<![a-zA-Z])kW(?![a-zA-Z])":   " kilowatts",
        r"(?<![a-zA-Z])MW(?![a-zA-Z])":   " megawatts",
        r"(?<![a-zA-Z])GW(?![a-zA-Z])":   " gigawatts",
        r"(?<![a-zA-Z])Hz(?![a-zA-Z])":   " hertz",
        r"(?<![a-zA-Z])km/h(?![a-zA-Z])": " kilometers per hour",
        r"(?<![a-zA-Z])m/s(?![a-zA-Z])":  " meters per second",
        r"(?<![a-zA-Z])kg(?![a-zA-Z])":   " kilograms",
        r"(?<![a-zA-Z])mg(?![a-zA-Z])":   " milligrams",
        r"(?<![a-zA-Z])ml(?![a-zA-Z])":   " milliliters",
        r"(?<![a-zA-Z])km(?![a-zA-Z])":   " kilometers",
        r"(?<![a-zA-Z])cm(?![a-zA-Z])":   " centimeters",
        r"(?<![a-zA-Z])mm(?![a-zA-Z])":   " millimeters",
        r"(?<![a-zA-Z])ms(?![a-zA-Z])":   " milliseconds",
    },
}

# Per-language abbreviation dictionary. Conservative — only expansions
# whose context is unambiguous regardless of surrounding text. Long
# lists hurt more than help; false-positive expansions are jarring.
ABBREVIATIONS: Dict[str, Dict[str, str]] = {
    "spanish": {
        r"\bSr\.": "señor",
        r"\bSra\.": "señora",
        r"\bSrta\.": "señorita",
        r"\bDr\.": "doctor",
        r"\bDra\.": "doctora",
        r"\bD\.": "don",
        r"\bDña\.": "doña",
        r"\bUd\.": "usted",
        r"\bUds\.": "ustedes",
        r"\betc\.": "etcétera",
        r"\bp\.\s?ej\.": "por ejemplo",
        r"\bEE\.\s?UU\.": "Estados Unidos",
        # S.A. / S.L. intentionally NOT expanded — native speakers more
        # often read them as letter sequences ("ese a", "ese ele") than
        # as the full "sociedad anónima". Consumer can pass
        # extra_abbreviations to add them.
        r"\bvs\.": "contra",
        # ISO-4217 currency codes — LLMs produce them alongside numbers
        # ("$7,000 (USD)"). Expand to the spoken word; the cardinal
        # expander handles the digits.
        r"\bUSD\b": "dólares",
        r"\bEUR\b": "euros",
        r"\bGBP\b": "libras",
        r"\bJPY\b": "yenes",
        r"\bCNY\b": "yuanes",
        r"\bCHF\b": "francos suizos",
    },
    "english": {
        r"\bMr\.": "Mister",
        r"\bMrs\.": "Misses",
        r"\bMs\.": "Miss",
        r"\bDr\.": "Doctor",
        r"\bSt\.": "Saint",
        r"\bJr\.": "Junior",
        r"\bSr\.": "Senior",
        r"\betc\.": "et cetera",
        r"\be\.g\.": "for example",
        r"\bi\.e\.": "that is",
        r"\bvs\.": "versus",
        r"\bU\.S\.A\.": "United States",
        r"\bU\.K\.": "United Kingdom",
        r"\bU\.S\.": "United States",
        r"\bUSD\b": "dollars",
        r"\bEUR\b": "euros",
        r"\bGBP\b": "pounds",
        r"\bJPY\b": "yen",
        r"\bCNY\b": "yuan",
        r"\bCHF\b": "Swiss francs",
    },
    "french": {
        r"\bM\.": "monsieur",
        r"\bMme\.": "madame",
        r"\bMlle\.": "mademoiselle",
        r"\bDr\.": "docteur",
        r"\betc\.": "et cetera",
        r"\bp\.\s?ex\.": "par exemple",
    },
    "german": {
        r"\bHr\.": "Herr",
        r"\bFr\.": "Frau",
        r"\bDr\.": "Doktor",
        r"\bz\.\s?B\.": "zum Beispiel",
        r"\bd\.\s?h\.": "das heißt",
        r"\busw\.": "und so weiter",
    },
    "italian": {
        r"\bSig\.": "signore",
        r"\bSig\.ra": "signora",
        r"\bDr\.": "dottore",
        r"\becc\.": "eccetera",
        r"\bes\.": "esempio",
    },
    "portuguese": {
        r"\bSr\.": "senhor",
        r"\bSra\.": "senhora",
        r"\bDr\.": "doutor",
        r"\bDra\.": "doutora",
        r"\betc\.": "et cetera",
    },
}

# Decimal separator word per language. num2words' built-in float
# handling defaults to "punto" / "point" / digit-by-digit, not how
# natives read decimals — Spanish uses "coma", French "virgule", etc.
# We split integer and fractional parts ourselves and join with this.
DECIMAL_WORD: Dict[str, str] = {
    "spanish":    "coma",
    "english":    "point",
    "french":     "virgule",
    "german":     "Komma",
    "italian":    "virgola",
    "portuguese": "vírgula",
    "russian":    "запятая",
    "japanese":   "テン",
    "korean":     "쩜",
    "chinese":    "点",
}

# "X or more" suffix per language for "1500+" → "1500 o más".
PLUS_SUFFIX_WORD: Dict[str, str] = {
    "spanish":    "o más",
    "english":    "or more",
    "french":     "ou plus",
    "german":     "oder mehr",
    "italian":    "o più",
    "portuguese": "ou mais",
    "russian":    "или больше",
    "japanese":   "以上",
    "korean":     "이상",
    "chinese":    "或更多",
}

# "X percent" expansion per language. Applied before number expansion
# so the bare digits get spelled out afterwards.
PERCENT_WORD: Dict[str, str] = {
    "spanish":    "por ciento",
    "english":    "percent",
    "french":     "pour cent",
    "german":     "Prozent",
    "italian":    "per cento",
    "portuguese": "por cento",
    "russian":    "процентов",
    "japanese":   "パーセント",
    "korean":     "퍼센트",
    "chinese":    "百分之",
}

# Month names for date expansion (numeric → spoken). Indexed 1..12.
# Sentinel at index 0 keeps access ergonomic.
MONTH_NAMES: Dict[str, List[str]] = {
    "spanish": ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "english": ["", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"],
    "french":  ["", "janvier", "février", "mars", "avril", "mai", "juin",
                "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    "german":  ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
                "Juli", "August", "September", "Oktober", "November", "Dezember"],
    "italian": ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
                "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"],
    "portuguese": ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
                   "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"],
}

# Date phrasing per language: (between_day_and_month, between_month_and_year).
DATE_GLUE: Dict[str, Tuple[str, str]] = {
    "spanish":    (" de ", " de "),
    "english":    (" ", ", "),
    "french":     (" ", " "),
    "german":     (". ", " "),
    "italian":    (" ", " "),
    "portuguese": (" de ", " de "),
}

# Heuristic synthesis rate per language: chars of input per second of
# generated audio at speed=1.0. Used for duration sanity checks (regen
# decisions in chunked generation). Rough — wide tolerance downstream.
CHARS_PER_SEC: Dict[str, float] = {
    "spanish":    14.0,
    "english":    14.5,
    "french":     14.0,
    "german":     13.0,
    "italian":    14.0,
    "portuguese": 14.0,
    "russian":    13.0,
    "japanese":   7.0,
    "korean":     8.0,
    "chinese":    5.0,
}
