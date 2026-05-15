"""Orchestrator — sequences the passes and applies the locale post-pass.

Pass order is significant. Top-level intuition:

1. **Cleaners** first — strip presentational markup (markdown / emojis)
   so it doesn't smuggle digits / punctuation past later passes.
2. **Web** before **abbreviation** — URLs may contain dot-separated
   acronyms that look like abbrev patterns; vocalizing the URL first
   keeps abbrev from eating its dots.
3. **Abbreviation** before **temporal** — abbreviations may carry
   trailing periods that look like sentence terminators around date
   patterns.
4. **Temporal** before any number expander — dates and times are
   compound digit groups; bare-cardinal would otherwise rip them apart.
5. **Phone** before **range** before **cardinal** — phones consume
   3-digit groups; ranges consume hyphenated pairs; cardinal handles
   what's left.
6. **Plus-suffix** before **currency / percent** — ``+`` is glued to
   digits or ``%``; if currency/percent consumes the symbol first the
   ``+`` gets orphaned.
7. **Sci notation** before **cardinal** — ``1.5e10`` looks like a
   decimal to the cardinal pass.
8. **Ordinal** before **cardinal** — ``1º`` has a suffix the cardinal
   pass would strip.
9. **Roman** before **cardinal** — uppercase roman tokens are
   independent of digit runs but the substitution emits cardinal
   words, run before the cardinal pass for consistency.
10. **Units** before **cardinal** — glued forms (``512GB``) need their
    unit expanded first so the cardinal pass can leave a clean space.
11. **Fraction** before **cardinal** — slash form would otherwise
    split into two cardinals.
12. **Cardinal** last among the numeric passes — handles whatever
    digit runs remain.
13. **Locale post-pass** at the very end — operates on the spelled
    Spanish text, so all the numeric passes must have run.

This module is short on purpose. The complexity lives in the passes;
this file is the contract that says "this is the order".
"""

from __future__ import annotations

from typing import Dict, Optional

from . import patterns as P
from .passes import (
    abbreviation,
    academic,
    acronym,
    bible,
    cardinal,
    chemistry,
    cleaners,
    color,
    discourse,
    economic,
    finance,
    fraction,
    handle,
    math as math_pass,
    negative,
    network,
    ordinal,
    phone,
    range_,
    roman,
    sci,
    temperature,
    temporal,
    timezone,
    units,
    version,
    web,
)
from .locales import en as locale_en
from .locales import es as locale_es
from .tables import ISO_TO_LONG


_LOCALE_PASS = {
    "spanish": locale_es.post_pass,
    "english": locale_en.post_pass,
}


def _resolve_lang(lang: str) -> str:
    """Normalize lang argument. Accepts ISO codes (``"es"``) and long
    names (``"spanish"``). Unknown values pass through unchanged — each
    pass falls back to a sensible default or no-op for unknown langs.
    """
    return ISO_TO_LONG.get(lang.lower(), lang.lower())


def normalize(
    text: str,
    lang: str = "english",
    *,
    strip_emojis: bool = True,
    strip_urls: bool = True,
    strip_markdown: bool = True,
    expand_abbreviations: bool = True,
    expand_numbers: bool = True,
    url_placeholder: Optional[str] = None,
    email_placeholder: Optional[str] = None,
    extra_abbreviations: Optional[Dict[str, str]] = None,
) -> str:
    """Normalize text for TTS synthesis.

    Designed for chat / LLM-output content: strips formatting, emojis,
    and URLs; expands numbers, units, dates, times, ordinals, romans,
    fractions, phones, ranges, scientific notation, currency, percent,
    and per-language abbreviations.

    Args:
        text: Input text.
        lang: Language. Accepts ISO codes (``"es"``) or long names
            (``"spanish"``). Unknown values pass through with minimal
            processing.
        strip_emojis: Drop emoji and pictograph codepoints.
        strip_urls: Replace URLs and emails (see ``url_placeholder``
            and ``email_placeholder`` for how).
        strip_markdown: Strip Markdown formatting markers (keeps text).
        expand_abbreviations: Apply per-language abbreviation
            dictionary.
        expand_numbers: Apply every numeric pass (cardinal, decimal,
            currency, percent, plus-suffix, units, dates, times,
            ordinals, romans, fractions, phones, ranges, sci notation).
            One flag controls all numeric passes because they're
            intertwined; toggle individual passes only by editing
            ``pipeline.normalize``.
        url_placeholder: Word substituted for complex URLs. ``None``
            uses the per-language default. Empty string force-strips.
        email_placeholder: Same idea for emails.
        extra_abbreviations: Regex → replacement mappings applied
            after the built-in dictionary.

    Returns:
        Normalized text, ready to feed to a TTS model.
    """
    lang = _resolve_lang(lang)

    # 1. Cleaners
    if strip_markdown:
        text = cleaners.strip_markdown(text)
    if strip_urls:
        text = web.replace_urls(text, lang, url_placeholder, email_placeholder)
    if strip_emojis:
        text = cleaners.strip_emojis(text)

    # 2. Abbreviations + handle (social handles consume @ and # which
    #    look adjacent to abbrev periods)
    if expand_abbreviations:
        text = abbreviation.expand_abbreviations(text, lang, extra_abbreviations)
        text = handle.expand_hashtags(text, lang)
        text = handle.expand_mentions(text, lang)
        text = acronym.expand_acronyms(text, lang)

    # 3. Numeric / structured passes.
    #    Order matters — see module docstring above.
    if expand_numbers:
        # Structured identifiers first — their patterns include dots /
        # colons / hyphens that downstream passes would otherwise eat.
        text = academic.expand_doi(text, lang)
        text = academic.expand_isbn(text, lang)
        text = academic.expand_citations(text, lang)
        text = academic.expand_footnotes(text, lang)
        text = version.expand_versions(text, lang)
        text = finance.expand_iban(text, lang)
        text = finance.expand_tickers(text, lang)
        text = network.expand_ips(text, lang)
        text = timezone.expand_timezones(text, lang)
        text = bible.expand_bible_refs(text, lang)
        text = chemistry.expand_chemistry(text, lang)
        text = color.expand_hex_colors(text, lang)
        # Time / date next — compound digit patterns.
        text = temporal.expand_dates(text, lang)
        text = temporal.expand_times(text, lang)
        text = phone.expand_phones(text, lang)
        text = sci.expand_sci(text, lang)
        # Symbolic / suffix-driven.
        text = economic.expand_plus_suffix(text, lang)
        text = economic.expand_currency(text, lang)
        text = economic.expand_percent(text, lang)
        # Temperature/degree before units so ``°C`` doesn't survive as
        # a bare letter "C" out of the units pass.
        text = temperature.expand_temperatures(text, lang)
        text = units.expand_units(text, lang)
        text = ordinal.expand_ordinals(text, lang)
        text = roman.expand_romans(text, lang)
        text = fraction.expand_fractions(text, lang)
        text = range_.expand_ranges(text, lang)
        # Math symbols + operators just before the bare-cardinal pass
        # so digit operands stay intact for the operator regex.
        text = math_pass.expand_math(text, lang)
        # Negative sign last among the symbolic passes — every other
        # hyphen consumer (range, sci, date, phone) has already run.
        text = negative.expand_negatives(text, lang)
        text = cardinal.expand_numbers(text, lang)

    # 4. Discourse cleanups — whitespace-flanked slashes left over after
    #    fractions / units / URLs read as "or" in chat prose.
    text = discourse.expand_slash_or(text, lang)

    # 5. Locale post-pass
    locale_fn = _LOCALE_PASS.get(lang)
    if locale_fn is not None:
        text = locale_fn(text)

    text = P.WHITESPACE.sub(" ", text).strip()
    return text
