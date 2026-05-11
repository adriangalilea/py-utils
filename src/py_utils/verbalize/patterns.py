"""Compiled regular expressions shared across passes.

Module-level so we don't recompile per call. Anything that's a
``re.compile`` constant lives here; per-call ``re.sub`` invocations with
literal patterns stay inside their pass file (small one-off patterns
are clearer in context).
"""

from __future__ import annotations

import re


# ─── Web ────────────────────────────────────────────────────────────

URL_PATTERN = re.compile(
    r"https?://\S+|www\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}\S*",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
)

EMPTY_BRACKETS = re.compile(r"\(\s*\)|\[\s*\]|\{\s*\}|<\s*>")
TRAILING_PUNCT = ".,;:!?)]}"


# ─── Markdown ───────────────────────────────────────────────────────
# Code blocks must run first because they shadow inline patterns.

MD_CODE_BLOCK   = re.compile(r"```[\s\S]*?```", re.MULTILINE)
MD_INLINE_CODE  = re.compile(r"`+([^`]+)`+")
MD_LINK         = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
MD_IMAGE        = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
# Bold/italic/strike: keep inner text. Order matters — longest first.
MD_BOLD_ITALIC  = re.compile(r"(\*\*\*|\*\*|\*|_{1,3}|~~)(.+?)\1")
MD_HEADING      = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)
MD_BLOCKQUOTE   = re.compile(r"^\s{0,3}>\s+", re.MULTILINE)
MD_HR           = re.compile(r"^\s*[-*_]{3,}\s*$", re.MULTILINE)
MD_LIST_BULLET  = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
MD_LIST_NUM     = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)


# ─── Whitespace + sentence terminators ──────────────────────────────

WHITESPACE = re.compile(r"\s+")
SENT_TERMINAL = ".!?"


# ─── Compound numeric patterns ──────────────────────────────────────
# Run BEFORE the bare cardinal expander so multi-digit-group constructs
# (dates, times, ranges) are consumed as units, not pulled apart.

DATE_DMY = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
DATE_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
TIME_HM  = re.compile(r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b")
PERCENT  = re.compile(r"(\d+(?:[.,]\d+)*)\s*%")

# "<digits>+" or "<digits>%+" written immediately after a number/percent
# meaning "or more" / "and up" ("$10,000+", "100%+"). Optional %? lets
# plus-suffix run BEFORE the percent expander without losing the %;
# percent runs afterward as usual. Lookahead excludes "++" so "C++"
# stays intact.
PLUS_SUFFIX = re.compile(r"(\d+(?:[.,]\d+)*\s*%?)\+(?![\w+])")

# Pure thousand-separator patterns: ASCII digit groups separated by
# either ',' or '.' with EXACTLY 3 digits per group. Used to
# disambiguate "7,000" vs "7,5" before applying the locale-specific
# decimal rule.
THOUSANDS_COMMA = re.compile(r"^\d{1,3}(,\d{3})+$")
THOUSANDS_DOT   = re.compile(r"^\d{1,3}(\.\d{3})+$")

# Number matcher. Digit runs with optional thousands separators and
# decimal mark. Locale resolves the separator semantics in
# :mod:`passes.cardinal`.
NUMBER = re.compile(r"\d[\d.,]*\d|\d")


# ─── Ordinals (Spanish) ─────────────────────────────────────────────
# 1º / 1ª (cardinal + masculine/feminine indicator), 1er / 3er (apocope),
# 1o / 1a (ASCII variant of ordinal indicator). Up to 999 covered — we
# don't try to verbalize ordinals beyond that since they're vanishingly
# rare in chat content.
ORDINAL_ES = re.compile(r"\b(\d{1,3})(º|ª|er|o|a)\b")


# ─── Roman numerals ─────────────────────────────────────────────────
# Matches I, II, III, IV, V, VI, VII, VIII, IX, X, XI… up to 3999. The
# all-caps constraint avoids matching English "I" / "i" as a roman.
# Word boundaries on both sides keep "MIX" (mixed) from matching as
# 1009.
ROMAN = re.compile(
    r"\b(M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3}))\b"
)


# ─── Fractions ──────────────────────────────────────────────────────
# Bare "<int>/<int>" not preceded by a digit (avoids matching the year
# part of a slash-date). Followed-by-digit lookahead too — "1/2/2026"
# is a date, not three fractions.
FRACTION = re.compile(r"(?<!\d)(\d{1,3})/(\d{1,3})(?!\d|/)")


# ─── Numeric ranges ─────────────────────────────────────────────────
# "1990-2000", "10-20", "p. 5-7". Two integer groups separated by a
# hyphen, with non-digit boundaries. Excludes phone-shaped hyphens via
# the digit-count constraint (phones are matched first).
RANGE_NUM = re.compile(r"(?<!\d)(\d{2,4})-(\d{2,4})(?!\d)")


# ─── Scientific notation ────────────────────────────────────────────
# "1.5e10", "1e-3", "2.4E5". Matches mantissa + exponent. The exponent
# can be negative. Decimal point optional in mantissa.
SCI_NOTATION = re.compile(r"(?<![\w.])(-?\d+(?:\.\d+)?)[eE]([+-]?\d+)\b")


# ─── Phone numbers ──────────────────────────────────────────────────
# European-style: optional +<countrycode> then 9 digits, optionally
# spaced. Spanish convention: +34 600 123 456 or 600 123 456.
# Conservative — only matches recognizable phone shapes to avoid eating
# generic numeric sequences.
PHONE = re.compile(
    r"(?<![\w.])"
    r"(\+\d{1,3}[\s.-]?)?"          # optional country code
    r"(\d{3})[\s.-]?(\d{3})[\s.-]?(\d{3})"  # 9-digit body, 3-3-3
    r"(?!\d)"
)
