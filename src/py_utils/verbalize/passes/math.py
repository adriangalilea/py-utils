"""Math symbols and operators.

Operators (``=``, ``+``, ``-``, ``×``, ``÷``, ``≈``, ``<``, ``>``,
``≤``, ``≥``, ``≠``) and Greek/math constants (``π``, ``∞``, ``∑``,
``∫``, ``∂``, ``∇``, ``√``) read as their spoken name.

Operators are NOT touched in normal prose — replacing every ``-`` with
"menos" would mangle hyphens, ranges, lists. The pass only acts when
the operator is **flanked by digits** (with optional spaces):
``E = mc²``, ``a + b = c``, ``5 < 10``. That keeps "minus 5"
("-5") behaviour while leaving "compound-word" intact.

Greek/math symbols are SIMPLE substitutions (always replace) — they
have no other use in prose.

We don't try to verbalize equations end-to-end ("equis igual a uve por
te cuadrado") — that's a structured-math-rendering job that goes far
beyond regex. The pass makes equations PRONOUNCEABLE token by token;
context fills in the rest.
"""

from __future__ import annotations

import re


# Symbol → per-language spoken word.
_SYMBOLS = {
    "π": {"spanish": "pi", "english": "pi"},
    "∞": {"spanish": "infinito", "english": "infinity"},
    "∑": {"spanish": "sumatorio", "english": "sum"},
    "∫": {"spanish": "integral", "english": "integral"},
    "∂": {"spanish": "derivada parcial", "english": "partial derivative"},
    "∇": {"spanish": "gradiente", "english": "gradient"},
    "√": {"spanish": "raíz cuadrada de", "english": "square root of"},
    "²": {"spanish": "al cuadrado", "english": "squared"},
    "³": {"spanish": "al cubo", "english": "cubed"},
    "±": {"spanish": "más menos", "english": "plus minus"},
    "→": {"spanish": "implica", "english": "implies"},
    "⇒": {"spanish": "implica", "english": "implies"},
    "⇔": {"spanish": "si y sólo si", "english": "if and only if"},
    "∈": {"spanish": "pertenece a", "english": "in"},
    "∉": {"spanish": "no pertenece a", "english": "not in"},
    "∀": {"spanish": "para todo", "english": "for all"},
    "∃": {"spanish": "existe", "english": "there exists"},
    "∅": {"spanish": "conjunto vacío", "english": "empty set"},
}

# Binary operators activated only when flanked by digits.
_OPERATORS = {
    "=": {"spanish": "igual a", "english": "equals"},
    "≠": {"spanish": "distinto de", "english": "not equal to"},
    "<": {"spanish": "menor que", "english": "less than"},
    ">": {"spanish": "mayor que", "english": "greater than"},
    "≤": {"spanish": "menor o igual que", "english": "less than or equal to"},
    "≥": {"spanish": "mayor o igual que", "english": "greater than or equal to"},
    "×": {"spanish": "por", "english": "times"},
    "÷": {"spanish": "dividido entre", "english": "divided by"},
    "≈": {"spanish": "aproximadamente", "english": "approximately"},
}


def expand_math(text: str, lang: str) -> str:
    # Symbols (always replace).
    for sym, langs in _SYMBOLS.items():
        word = langs.get(lang)
        if word is None:
            continue
        text = text.replace(sym, f" {word} ")

    # Binary operators: must be flanked by digits or spaces+digits.
    for op, langs in _OPERATORS.items():
        word = langs.get(lang)
        if word is None:
            continue
        pat = re.compile(r"(\d)\s*" + re.escape(op) + r"\s*(\d)")
        text = pat.sub(rf"\1 {word} \2", text)

    # Whitespace collapse handled by pipeline's final pass.
    return text
