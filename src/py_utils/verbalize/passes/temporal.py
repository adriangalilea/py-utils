"""Date and time expansion.

Both go BEFORE the bare-cardinal expander so a date isn't pulled apart
into three independent numbers and a time isn't pulled apart into two.
Only languages with a populated ``MONTH_NAMES`` table get date
expansion; the rest leave dates as digit-by-digit-group readings.

Date phrasing per language lives in ``DATE_GLUE``. Time phrasing
handles natural fractional minutes (15 / 30) where the language has
them ("y media", "et quart", "e mezza"); other minutes use the
language's join word ("y" / "and" / "et" / "e") between H and M.

German is intentionally NOT special-cased for time — German "halb elf"
anchors to the NEXT hour (10:30 → "halb elf"), and getting that wrong
is more jarring than reading "zehn dreißig" verbatim.
"""

from __future__ import annotations

from .. import patterns as P
from ..tables import DATE_GLUE, MONTH_NAMES


def expand_dates(text: str, lang: str) -> str:
    """Expand DD/MM/YYYY and YYYY-MM-DD to spoken form.

    Both formats yield the same spoken result. We assume the European
    DD/MM/YYYY convention; US MM/DD/YYYY would mis-render but our
    target audience is es/en EU content. Add a US-mode flag if a
    consumer ever needs it.
    """
    months = MONTH_NAMES.get(lang)
    if not months:
        return text
    sep_dm, sep_my = DATE_GLUE.get(lang, (" ", " "))

    def _expand_dmy(m):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not (1 <= d <= 31 and 1 <= mo <= 12):
            return m.group(0)
        return f"{d}{sep_dm}{months[mo]}{sep_my}{y}"

    def _expand_iso(m):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not (1 <= d <= 31 and 1 <= mo <= 12):
            return m.group(0)
        return f"{d}{sep_dm}{months[mo]}{sep_my}{y}"

    text = P.DATE_DMY.sub(_expand_dmy, text)
    text = P.DATE_ISO.sub(_expand_iso, text)
    return text


_FRACTIONAL = {
    "spanish": {15: "y cuarto", 30: "y media"},
    "french": {15: "et quart", 30: "et demie"},
    "italian": {15: "e un quarto", 30: "e mezza"},
    "portuguese": {15: "e quinze", 30: "e meia"},
}

_JOIN = {
    "spanish": " y ",
    "english": " ",
    "french": " ",
    "german": " ",
    "italian": " e ",
    "portuguese": " e ",
}


def expand_times(text: str, lang: str) -> str:
    """Expand ``HH:MM`` (and ``HH:MM:SS``) to natural spoken form.

    Two passes inside:

    1. Common fractional minutes (:15, :30) get the natural phrase if
       the language has one. Only applies when there are no seconds;
       full timestamps fall back to the join form.
    2. Everything else: ``HH<join>MM``. When MM == 00 and no SS, emit
       just ``HH`` — surrounding text usually has its own qualifier
       ("en punto", "o'clock").

    Minute group must be exactly 2 digits to avoid clashing with
    non-time constructs (``2:5`` is not a time). Hours 0-29 to allow
    24h schedules; out-of-range matches pass through.
    """
    fractional = _FRACTIONAL.get(lang, {})
    join = _JOIN.get(lang, " ")

    def _expand(m):
        h, mn = int(m.group(1)), int(m.group(2))
        s = m.group(3)
        if not (0 <= h <= 29 and 0 <= mn <= 59):
            return m.group(0)
        if mn == 0 and s is None:
            return str(h)
        if mn in fractional and s is None:
            return f"{h} {fractional[mn]}"
        out = f"{h}{join}{mn:02d}"
        if s is not None:
            ss = int(s)
            if 0 <= ss <= 59:
                out += f"{join}{ss:02d}"
        return out

    return P.TIME_HM.sub(_expand, text)
