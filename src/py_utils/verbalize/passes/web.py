"""URL + email vocalization.

Two paths, decided per URL:

- **Simple URL** (just a host, optionally with protocol or trailing /):
  drop the protocol, vocalize the host. Join segments with the
  language's dot word. Spell out known acronym prefixes ("www",
  "ftp", …) letter-by-letter via the per-language ``LETTER_NAMES``
  table so Spanish "www" reads "uve doble uve doble uve doble" instead
  of bare 'w' that the TTS mispronounces.
- **Complex URL** (any path / query / fragment): substitute the
  language's URL placeholder word ("enlace" / "link" / …). Reading
  "barra docs interrogación q igual…" aloud is useless.

Emails are always vocalized: ``foo arroba bar punto com``. The email
placeholder is only used when the @-split fails. Trailing terminal
punctuation eaten by the greedy regex (``https://example.com.``) is
split off before vocalization so it survives as part of the
surrounding sentence.

Pass ``url_placeholder=""`` to force-strip URLs instead of replacing
them with a word; in that case empty bracket-pairs left behind are
cleaned up.
"""

from __future__ import annotations

from typing import Optional, Tuple
from urllib.parse import urlparse

from .. import patterns as P
from ..tables import (
    AT_SIGN_WORD,
    EMAIL_PLACEHOLDER,
    LETTER_NAMES,
    URL_DOT_WORD,
    URL_PLACEHOLDER,
)

# Hostname prefixes that read poorly without letter-by-letter spelling.
# Anything else stays as-is (the TTS reads it as a word).
_SPELL_LETTERWISE = {"www", "ftp", "smtp", "imap", "pop", "ssh", "http", "https"}


def _vocalize_host(host: str, dot_word: str, lang: str) -> str:
    letters = LETTER_NAMES.get(lang)
    parts = host.split(".")
    rendered = []
    for p in parts:
        if p.lower() in _SPELL_LETTERWISE:
            if letters:
                rendered.append(" ".join(letters.get(c.lower(), c) for c in p))
            else:
                rendered.append(" ".join(p.lower()))
        else:
            rendered.append(p)
    return f" {dot_word} ".join(rendered)


def _classify_url(matched: str) -> Tuple[bool, str]:
    """Return ``(is_simple, host)``. Simple = host only, no path / query / auth / port."""
    candidate = matched if "://" in matched else f"//{matched}"
    try:
        parsed = urlparse(candidate, scheme="http")
    except ValueError:
        return False, ""
    netloc = parsed.netloc
    if "@" in netloc or ":" in netloc:
        return False, ""
    if not netloc:
        return False, ""
    is_simple = parsed.path in ("", "/") and not parsed.query and not parsed.fragment
    return is_simple, netloc


def _split_trailing(matched: str) -> Tuple[str, str]:
    trailing = ""
    while matched and matched[-1] in P.TRAILING_PUNCT:
        trailing = matched[-1] + trailing
        matched = matched[:-1]
    return matched, trailing


def replace_urls(
    text: str,
    lang: str,
    url_placeholder: Optional[str] = None,
    email_placeholder: Optional[str] = None,
) -> str:
    url_word = url_placeholder
    email_word = email_placeholder
    if url_word is None:
        url_word = URL_PLACEHOLDER.get(lang, URL_PLACEHOLDER["english"])
    if email_word is None:
        email_word = EMAIL_PLACEHOLDER.get(lang, EMAIL_PLACEHOLDER["english"])

    dot_word = URL_DOT_WORD.get(lang, URL_DOT_WORD["english"])
    at_word = AT_SIGN_WORD.get(lang, AT_SIGN_WORD["english"])

    def _replace_url(m):
        matched, trailing = _split_trailing(m.group(0))
        if not url_word.strip():
            return url_word + trailing
        is_simple, host = _classify_url(matched)
        if is_simple and host:
            return _vocalize_host(host, dot_word, lang) + trailing
        return url_word + trailing

    def _replace_email(m):
        matched, trailing = _split_trailing(m.group(0))
        if not email_word.strip():
            return email_word + trailing
        local, sep, host = matched.partition("@")
        if sep and host:
            return (
                f"{local} {at_word} {_vocalize_host(host, dot_word, lang)}" + trailing
            )
        return email_word + trailing

    text = P.URL_PATTERN.sub(_replace_url, text)
    text = P.EMAIL_PATTERN.sub(_replace_email, text)
    if not url_word.strip() or not email_word.strip():
        text = P.EMPTY_BRACKETS.sub("", text)
    return text
