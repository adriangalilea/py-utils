# verbalize — TTS Text Normalization

This subpackage implements **Text Normalization (TN)** for TTS frontends:
the step that converts written text ("Velocidad de 100 GB/s") into spoken
form ("Velocidad de cien gigabytes por segundo") before the TTS model
phonemizes and synthesizes audio. Distinct from Grapheme-to-Phoneme (G2P)
— that's what the TTS model does internally on the normalized text.

## Why this exists

We built it for chat → TTS. The Telegram bots stream LLM output (with
markdown, emojis, URLs, currency, abbreviations) into a TTS model. The
model can't pronounce raw `**bold**` or `$10,000+`; it reads digits one
at a time, mangles units (`GB/s`), and skips emojis as glyphs. A
preprocessing pass that expands semiotic classes to their spoken form is
the difference between "robot reading raw text" and "human-like
narration".

## Why NOT NeMo / nemo-text-processing

NVIDIA's `nemo-text-processing` is the standard FST-based TN library
(Apache 2.0, Pynini + OpenFst). We evaluated it head-to-head on Spanish:

- **148× slower per call** (14.7ms mean vs 0.10ms ours).
- **13 second cold-start** (FST grammar compilation per process).
- **No support for chat content**: leaves Markdown / emojis intact,
  doesn't expand `EE.UU.`, breaks on US-style thousand separators
  (`$10,000 USD` → "diez dólares cero cero cero USD").
- **Misses TTS-specific niceties**: no idiom "100% → cien por cien",
  spells URL words letter-by-letter (`example` → "e x a m p l e"), reads
  `2.5` as "dos . cinco" (literal dot).
- **Install pain on arm64 macOS**: Pynini needs OpenFst compiled at the
  exact version Pynini was built against; brew's openfst is too new;
  conda-forge works (we used pixi for the comparison) but adds a heavy
  toolchain to the deploy.

What NeMo does have that we didn't: ordinals (1º), Roman numerals (siglo
XXI), explicit fractions (1/4 → "un cuarto"), phone numbers, ranges,
scientific notation. We ported those classes ourselves rather than take
the dependency.

The comparison harness lives at
`infra/mac-studio/tn-compare/` in the smarthome repo — re-runnable any
time NeMo claims an upgrade closes the gap.

## Architecture

Single sequential pipeline with explicit pass ordering — no FSTs, no
grammar composition. Each pass is one Python function with one
responsibility:

```
input ──► cleaners ──► web ──► abbreviation ──► temporal
                                                    │
                                                    ▼
        spanish post ◄── discourse ◄── cardinal ◄── ordinal ◄── roman
        (gender +        (slash → or)  (decimal +   (1º, 3er,   (XXI,
         apocope)                      thousands)    2ª)         VI)
                                              ▲
                                              │
                fraction ◄─ range_ ◄─ sci ◄─ phone ◄─ units ◄─ economic
                (1/4)       (90-00)  (1e10)  (+34..)  (GB,kg)  ($/%, +)
```

Order matters: compound patterns ("$10,000+") must run before the bare
cardinal expander pulls the digits apart. The `passes/` modules each
own one semiotic class; `pipeline.py` is the orchestrator that
sequences them and applies the locale post-pass.

## Semiotic class coverage

| Class | Module | Languages | Example | Notes |
|---|---|---|---|---|
| Emoji | `passes/cleaners.py` | all | `🔥 hola` → `hola` | Unicode category-based |
| Markdown | `passes/cleaners.py` | all | `**bold**` → `bold` | Keeps link text + URL |
| URL / email | `passes/web.py` | 10 | `www.example.com` → letter-spelled host | Complex URLs → placeholder |
| Abbreviations | `passes/abbreviation.py` | es/en/fr/de/it/pt | `EE.UU.` → `Estados Unidos` | Per-lang dict |
| Hashtag / mention | `passes/handle.py` | es/en/+more | `@adrian` → `arroba adrian` | |
| Acronyms | `passes/acronym.py` | es/en | `FBI` → `F B I`, `NASA` → `nasa` | Per-lang dict |
| DOI | `passes/academic.py` | es/en | `10.1234/abcd` → `D O I diez punto …` | |
| ISBN | `passes/academic.py` | es/en | `978-3-16-148410-0` → `I S B N novecientos…` | |
| Citation pages | `passes/academic.py` | es/en | `p. 5` → `página 5` | |
| Footnotes | `passes/academic.py` | es/en | `texto¹` → `texto nota uno` | Superscript digits |
| Version | `passes/version.py` | es/en | `v1.3.13` → `versión uno punto tres punto trece` | Requires `v` or `versión` prefix |
| IBAN | `passes/finance.py` | es/en | `ES12 3456 ...` → `E S doce …` | |
| Tickers (stock) | `passes/finance.py` | es/en | `$AAPL` → `A A P L` | `$` prefix required for stocks |
| Tickers (crypto) | `passes/finance.py` | es/en | `BTC` → `bitcoin` | Per-symbol lookup |
| IP addresses | `passes/network.py` | es/en | `192.168.1.1:8080` → digit-by-digit + port | |
| Time zones | `passes/timezone.py` | es/en | `UTC+1` → `U T C más uno` | Bare zones + offsets |
| Bible references | `passes/bible.py` | es/en | `Génesis 1:1-5` → `Génesis, capítulo uno, versículos uno al cinco` | |
| Chemistry | `passes/chemistry.py` | es/en | `H2O`, `H₂O` → `h dos o` | Needs ≥1 digit (avoids "VI" false-positive) |
| Hex colors | `passes/color.py` | es/en | `#FF0000` → `f f cero cero cero cero` | |
| Dates | `passes/temporal.py` | 6 | `25/6/2026` → `25 de junio de 2026` | DD/MM/YYYY + ISO |
| Times | `passes/temporal.py` | 6 | `15:30` → `15 y media` | Quarter / half / generic |
| Phones | `passes/phone.py` | es/en | `+34 600 123 456` → digit-by-digit + country |
| Sci notation | `passes/sci.py` | es/en | `1.5e10` → `uno coma cinco por diez elevado a diez` | |
| Currency | `passes/economic.py` | 10 | `$10`, `10€` → `10 dólares`, `10 euros` | Prefix + suffix forms |
| Percent | `passes/economic.py` | 10 | `100%` → `cien por cien` (idiom for ES) | |
| Plus-suffix | `passes/economic.py` | 10 | `1500+` → `mil quinientos o más` | |
| Units | `passes/units.py` | es/en | `GB/s` → `gigabytes por segundo` | 30+ unit acronyms |
| Ordinals | `passes/ordinal.py` | es | `1º`, `3er` → `primero`, `tercer` | |
| Romans | `passes/roman.py` | es/en | `Felipe VI` → `Felipe sexto` (ordinal context), `siglo XXI` → `siglo veintiuno` (cardinal context) | Context-tagged only |
| Fractions | `passes/fraction.py` | es/en | `1/4` → `un cuarto` | Disambig vs dates/paths |
| Ranges | `passes/range_.py` | 6 | `1990-2000` → `mil novecientos noventa a dos mil` | |
| Math symbols | `passes/math.py` | es/en | `π`, `5 = 5` → `pi`, `5 igual a 5` | Operators need digit flanking |
| Cardinals | `passes/cardinal.py` | 9 | `1.234,56` → locale-aware reading | Last numeric pass |
| Prose slash | `passes/discourse.py` | es/en/fr/de/it/pt | `foo / bar` → `foo or bar` | Whitespace-flanked only |
| ES concordance | `locales/es.py` | es | `300 personas` → `trescientas personas` | spaCy-backed if installed |
| ES apocope | `locales/es.py` | es | `uno libro` → `un libro` | spaCy-backed if installed |

Counts: 31 semiotic classes across 25 pass modules + 2 locale post-passes.

## File layout

| File | Responsibility |
|---|---|
| `__init__.py` | Public API: `normalize(text, lang)` |
| `pipeline.py` | Orchestrator — sequences passes + locale post-pass |
| `tables.py` | All multilingual data tables |
| `patterns.py` | Compiled regex constants |
| `cli.py` | `verbalize "..." --lang es` |
| `passes/<class>.py` + `passes/<class>_test.py` | One semiotic class per file, co-located Go-style |
| `locales/{es,en}.py` + `_test.py` | Language-specific post-passes |
| `stress_test.py` | Realistic multi-class inputs + `xfail`-tagged known limits |

## Language coverage

10 languages match Qwen3-TTS's `codec_language_id` map:

```
chinese, english, french, german, italian, japanese,
korean, portuguese, russian, spanish
```

Coverage is best-effort and grows over time. Spanish and English are
production-tuned (chatbot + voiceclone bots run them daily). The rest are
correct in shape but their abbreviation dictionaries are minimal — PRs to
expand them are welcome.

Per-language assets live in `tables.py` (data) and `locales/<lang>.py`
(language-specific post-passes that aren't expressible as simple
dictionary lookups — Spanish gender concordance + apocope are the only
case so far).

## Public API

```python
from py_utils.verbalize import normalize

normalize("Visita www.example.com el 25/6/2026", lang="es")
# → "Visita uve doble uve doble uve doble punto example punto com el
#    veinticinco de junio de dos mil veintiséis"

normalize("Visit www.example.com on 6/25/2026",  lang="en")
# → "Visit w w w dot example dot com on 25 June 2026"
```

`lang=` accepts both Qwen3-TTS-style long names (`"spanish"`, `"english"`)
and ISO codes (`"es"`, `"en"`) — pipeline normalizes internally.

Every pass has a feature flag in the `normalize()` keyword args
(`strip_emojis`, `expand_numbers`, etc.) so consumers can disable
individual passes without forking the pipeline.

## Bug fixes vs previous incarnation

This rewrite from the in-tree `mlx-audio` text_pipeline.py also fixes
two bugs surfaced by the NeMo comparison:

1. **`2.5 kg` was read as "veinticinco kilogramos"** (twenty-five) because
   the dot-thousands-vs-dot-decimal disambiguation defaulted to thousands
   in Spanish mode. Fix: dot+digit-run-after-it of ≤2 digits is decimal
   regardless of language. `cardinal.py` carries the heuristic.
2. **Apocope mis-fired on standalone symbols / single letters** (`1,75 m`
   produced "una coma setenta y cinco" because the trailing `m` looked
   like the start of a feminine noun). Fix: only fire apocope when the
   following token is an actual word (≥2 letters, alphabetic only).
   `locales/es.py` carries the new guard.
3. **snake_case identifiers had their underscores eaten** — italic
   stripping matched `_WORD_` inside `WAKE_WORD_MODEL_PATH` and
   collapsed it to `WAKEWORDMODELPATH`. Fix: the underscore italic
   alternative now requires non-word boundaries on both sides;
   surviving identifier underscores are converted to spaces so TTS
   reads "wake word model path". `cleaners.py` / `patterns.py`.
4. **Numbered lists merged into a single sentence** — bullet/number
   markers were dropped without leaving a sentence terminator, so the
   final whitespace collapse produced run-on prose. Fix: insert a
   period before the line break when the previous line lacks
   terminal punctuation. `cleaners.py`.
5. **Inline-code stripping produced double hyphens** — ``` `pb-` ```
   followed by `-prefixed` glued to `pb--prefixed`. Fix: collapse
   word-flanked `--+` runs to a single hyphen (spaced em-dashes
   intact). `cleaners.py`.
6. **`→` read as "implies"** — wrong reading for chat prose where the
   arrow means "to" / "becomes". Fix: `→` now maps to "to" / "a";
   strict logical implication uses `⇒`. `passes/math.py`.
7. **Bare `/` between word tokens read as "slash"** — jarring in
   chat content like `ask_session / kill_session`. Fix: new
   `passes/discourse.py` substitutes whitespace-flanked slashes with
   "or" / "o" after every other slash-consuming pass has run.

## Future direction

Two tiers that would make this whole pipeline redundant, in priority
order:

1. **Audio-native model**: a TTS that takes raw text — emojis, markdown,
   numbers, currency, URLs, abbreviations — and synthesizes correct
   speech without a preprocessing pass. Every entry in our class
   coverage is a workaround for the model not handling its own input.

2. **LLM streaming sanitization layer** (Phase 2): a small fast LLM
   that re-emits the main LLM's stream as TTS-clean text, replacing
   this regex pipeline entirely. Concretely:

   ```
   user prompt
       ↓
   main LLM (stream)
       ↓                       ← chat content with formatting/symbols
   sanitizer LLM (stream)
       ↓                       ← prose-only, expanded numbers, no md
   TTS model (stream)
       ↓
   audio
   ```

   Pros: handles every semiotic class without a `passes/` module —
   chemistry formulas, citation formats, code references, music
   notation, anything an LLM understands as text. Subsumes the entire
   regex pipeline. Cons: latency, cost, determinism.

   **The reason to keep evolving `passes/` even while the LLM tier is
   planned**: when the LLM lands we need a strong baseline to A/B
   against. A naïve regex pipeline would lose trivially to any LLM;
   a well-tuned one with 30 semiotic classes + spaCy concordance
   makes the comparison honest. Two head-to-head dimensions we need:

   - **Latency**: current pipeline is 0.10 ms / sentence (warm,
     NeMo-comparison battery). An LLM running locally adds at minimum
     the model's TTFT (tens of ms for small models, hundreds for
     bigger). The pipeline sets the floor LLM latency must beat.
   - **Accuracy**: stress tests in `stress_test.py` are the seeds of
     the A/B harness. Each `xfail` case is a gap the LLM tier should
     close to win; each passing case is a benchmark the LLM tier
     must not regress on.

   When stress tests deepen and limits get documented honestly (via
   `xfail` with `reason=`), the pipeline becomes both the production
   default AND a fixed reference point for the LLM comparison. The
   more classes we cover here, the higher the bar the LLM must clear
   to justify its latency cost.

3. **Hybrid** (corollary): an LLM running ONLY on inputs that the
   regex pipeline can't confidently handle (detected via per-class
   confidence signals — e.g. a regex match is "confident", an
   abbreviation expansion with surrounding context is "uncertain"
   when no dictionary entry matched). Cheap for clean inputs, slow
   for messy inputs. Right architecture if LLM latency stays high.

Until either tier ships, the active surface is `passes/` — add a class,
port a NeMo grammar, fix a bug surfaced by listening, document a new
limit in `stress_test.py`.
