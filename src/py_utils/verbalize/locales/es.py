"""Spanish post-pass: gender concordance + apocope, spaCy-backed.

Runs AFTER cardinal expansion. num2words emits the canonical masculine
form ("trescientos"); this pass swaps to feminine ("trescientas") when
the next noun is feminine, and applies apocope ("uno"→"un",
"veintiuno"→"veintiún") when the next word is a masculine singular
noun. The grammar is well-defined; the hard part is knowing the gender
+ number of the next word — that's what spaCy gives us.

## Two backends

This module lazy-loads spaCy + ``es_core_news_sm`` if available. The
model knows the morphology of every Spanish noun trained on millions
of tokens (including unknown / invented words via its neural tagger).
That eliminates the entire hand-maintained gender dictionary the
previous incarnation carried.

If spaCy isn't installed (the user didn't opt into the
``verbalize-spanish`` extra), the module falls back to a coarse suffix
heuristic:

- words ending in ``-as`` → assume feminine plural
- words ending in ``-a`` → assume feminine singular
- everything else → masculine

This is dramatically less accurate (false positives on "días", "mapas",
"problemas") but keeps the library usable without the 40 MB model.

## Performance

The orchestrator only enters this pass if the regex finds a trigger
word from ``_MASC_TO_FEM``. Texts with no trigger word — the
overwhelming majority of chat content — pay <100µs of regex scan and
zero spaCy calls.

When a trigger fires, spaCy analyses *only the next token* (not the
whole text). With ``parser`` / ``ner`` / ``lemmatizer`` /
``attribute_ruler`` disabled, that's ~200µs per cold token and <1µs
per cached repeat (LRU 10 000).

## Rules kept as code (not data)

``_MASC_TO_FEM`` and ``_APOCOPE`` are transformation rules — they
encode HOW masculine forms become feminine or apocopate. Those are
finite, well-defined, and Spanish-grammar-canonical. They stay as
code. What's gone: the dictionaries of WHICH nouns are feminine, which
were incomplete by construction and the spaCy model replaces.
"""

from __future__ import annotations

import functools
import re
from typing import Optional, Tuple


# Hundreds + standalone "uno" / "veintiuno" / "alguno" / "ninguno":
# masculine canonical form num2words emits, paired with the feminine
# variant we swap to before a feminine noun.
_MASC_TO_FEM = {
    "doscientos": "doscientas",
    "trescientos": "trescientas",
    "cuatrocientos": "cuatrocientas",
    "quinientos": "quinientas",
    "seiscientos": "seiscientas",
    "setecientos": "setecientas",
    "ochocientos": "ochocientas",
    "novecientos": "novecientas",
    "uno": "una",
    "veintiún": "veintiuna",
    "veintiuno": "veintiuna",
    "alguno": "alguna",
    "ninguno": "ninguna",
}

# Apocope: drop final ``-o`` before a masculine singular noun.
_APOCOPE = {
    "uno": "un",
    "veintiuno": "veintiún",
    "alguno": "algún",
    "ninguno": "ningún",
}


# ─── spaCy backend (lazy) ───────────────────────────────────────────

_nlp: Optional[object] = None
_spacy_available: Optional[bool] = None


def _try_load_spacy() -> Optional[object]:
    """Lazily load spaCy + ``es_core_news_sm`` once per process.

    Returns the loaded ``nlp`` callable or ``None`` if spaCy / the
    model aren't installed. The pipeline is stripped to its minimum:
    only the tagger + morphologizer run, parser / NER / lemmatizer /
    attribute ruler are disabled. That makes per-token analysis
    ~5-10× faster than the default pipeline without losing the
    morphology we need.
    """
    global _nlp, _spacy_available
    if _spacy_available is False:
        return None
    if _nlp is not None:
        return _nlp
    try:
        import spacy

        _nlp = spacy.load(
            "es_core_news_sm",
            disable=["parser", "ner", "lemmatizer", "attribute_ruler"],
        )
        _spacy_available = True
    except (ImportError, OSError):
        # ImportError: spacy not installed
        # OSError: spacy installed but model not downloaded
        _spacy_available = False
        _nlp = None
    return _nlp


@functools.lru_cache(maxsize=10_000)
def _morph(word: str) -> Tuple[str, str, str]:
    """Return ``(pos, gender, number)`` for a single Spanish word.

    Cached aggressively: chat content has high lexical repetition
    ("personas", "días", "veces" recur), so this hits the cache the
    second time on. Empty triple on lookup failure.
    """
    nlp = _try_load_spacy()
    if nlp is None:
        return ("", "", "")
    doc = nlp(word)
    if not doc:
        return ("", "", "")
    tok = doc[0]
    gender = (tok.morph.get("Gender") or [""])[0]
    number = (tok.morph.get("Number") or [""])[0]
    return (tok.pos_, gender, number)


# ─── Heuristic fallback (when spaCy unavailable) ────────────────────


def _heuristic_gender_number(word: str) -> Tuple[str, str]:
    """Coarse suffix-based gender/number guess. Used only when spaCy
    isn't available. Trades accuracy for zero dependencies.
    """
    w = word.lower()
    if w.endswith("as") and len(w) > 2:
        return ("Fem", "Plur")
    if w.endswith("os") and len(w) > 2:
        return ("Masc", "Plur")
    if w.endswith("es") and len(w) > 2:
        return ("", "Plur")  # gender ambiguous
    if w.endswith("a") and len(w) > 1:
        return ("Fem", "Sing")
    if w.endswith("o") and len(w) > 1:
        return ("Masc", "Sing")
    return ("", "Sing")


# ─── Trigger scan ───────────────────────────────────────────────────

# Bug-fix vs prior version: the "next word" group now demands ≥2 ASCII
# letters. Standalone symbols, digits, and single letters don't trigger
# apocope / gender swap anymore.
_PATTERN = re.compile(
    r"\b("
    + "|".join(re.escape(k) for k in _MASC_TO_FEM)
    + r")\b(\s+)([a-záéíóúüñ]{2,})",
    re.IGNORECASE,
)


def _classify_next(word: str) -> Tuple[bool, str, str]:
    """Return ``(eligible, gender, number)``.

    ``eligible`` is ``True`` when the next token is a noun-like target
    where concordance / apocope make sense (NOUN, PROPN, ADJ). When
    spaCy classifies the token as a function word (ADP, CCONJ, VERB, …)
    we return ``False`` so the caller leaves the trigger alone — this
    is what kills the "uno de cada" false-positive.

    When spaCy isn't available we fall back to the heuristic and
    declare the token eligible: the suffix rule is all we have to go
    on, so we take its word for it.
    """
    pos, gender, number = _morph(word)
    if pos in ("NOUN", "PROPN", "ADJ"):
        return (True, gender, number)
    if pos:
        # spaCy classified it as something we don't want to concordance
        # against (ADP, CCONJ, VERB, AUX, …).
        return (False, "", "")
    # spaCy unavailable: heuristic + assume eligible.
    g, n = _heuristic_gender_number(word)
    return (True, g, n)


def post_pass(text: str) -> str:
    def _swap(m):
        masc = m.group(1)
        gap = m.group(2)
        next_word = m.group(3)
        eligible, gender, number = _classify_next(next_word)
        is_apocope = masc in _APOCOPE

        if not eligible:
            # Function word (preposition / conjunction / verb). Leaves
            # the trigger untouched: "uno de cada", "uno por uno".
            return m.group(0)

        if gender == "Fem":
            return f"{_MASC_TO_FEM[masc]}{gap}{next_word}"

        # Masculine context (confident "Masc" OR unknown gender on a
        # noun-eligible token — typical for loanwords / proper nouns
        # spaCy hasn't seen). Apocope fires for "uno", "veintiuno",
        # "alguno", "ninguno" regardless of grammatical number, because
        # the rule applies to both "un libro" (sing) and "veintiún
        # años" (plur). Hundreds (doscientos, etc.) stay as-is — they
        # have no apocope form.
        if is_apocope:
            return f"{_APOCOPE[masc]}{gap}{next_word}"
        return m.group(0)

    return _PATTERN.sub(_swap, text)
