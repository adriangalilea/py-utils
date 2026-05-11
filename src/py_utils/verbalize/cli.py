"""Command-line entry — ``verbalize "<text>" [--lang es]``.

Hooked from ``[project.scripts]`` in ``pyproject.toml``. Useful for
ad-hoc inspection ("how does this read aloud?") and for shell pipes
when sanity-checking LLM output offline.
"""

from __future__ import annotations

import argparse
import sys

from .pipeline import normalize


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="verbalize",
        description="Normalize text for TTS (emojis, markdown, URLs, "
        "numbers, dates, currency, units, abbreviations, …).",
    )
    parser.add_argument(
        "text", nargs="?", help="Text to normalize. If omitted, reads stdin."
    )
    parser.add_argument(
        "--lang",
        "-l",
        default="en",
        help="Language: ISO ('es', 'en') or long name "
        "('spanish', 'english'). Default: en.",
    )
    parser.add_argument("--no-strip-emojis", action="store_true")
    parser.add_argument("--no-strip-urls", action="store_true")
    parser.add_argument("--no-strip-markdown", action="store_true")
    parser.add_argument("--no-expand-abbreviations", action="store_true")
    parser.add_argument("--no-expand-numbers", action="store_true")
    args = parser.parse_args()

    text = args.text if args.text is not None else sys.stdin.read()
    out = normalize(
        text,
        lang=args.lang,
        strip_emojis=not args.no_strip_emojis,
        strip_urls=not args.no_strip_urls,
        strip_markdown=not args.no_strip_markdown,
        expand_abbreviations=not args.no_expand_abbreviations,
        expand_numbers=not args.no_expand_numbers,
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
