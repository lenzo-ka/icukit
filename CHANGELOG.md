# Changelog

## [Unreleased]

### Added

- A spell-out expansion type in the abbreviation lexicon: `<expansion type="spell-out">`
  says the surface is spelled out, and its text lists the characters to name, separated
  by spaces. `Expansion` and `AbbreviationExpansion` carry it as `type`, which is
  `"expansion"` for an expansion read as words. The English lexicon uses it for `MD`,
  spelled out "M D" as the degree, alongside Maryland as the postal code.
- Regional abbreviation lexicons. A locale reads every packaged lexicon on its ICU
  fallback chain, from the most general to the most specific, so `en_US` reads `en.xml`
  with the new `en_US.xml` over it, and `en_GB` follows CLDR's parent through `en_001`
  to `en`. `locale_chain`, `merge_lexicons`, and `load_locale_lexicon` expose this, and
  `compile_lexicon` uses it.
- `AlphanumericRunsDetector` (`alnum:runs`): a word that mixes letters and digits reads
  as its runs, the path a speaker takes for "3D", "5pm", or "2Q22", beside any other
  reading of the word.
- `PluralNumeralDetector` (`number:plural`): a numeral made plural, "1990s", "1990's",
  "'90s", "100s", with the written number as its value and no guessed decade or
  century. Its suffix letters are a small per-language table, since CLDR has none.
- `FlexibleTimeDetector` reads an hour with a day period and no minutes ("5pm",
  "10 a.m."), reads ICU's day-period forms at every width for every locale of the
  language (en_US reads en_CA's "a.m."), and reads CLDR's hour symbol after a time
  ("10:30h") or, where CLDR writes it attached, between hour and minutes (fr "10h30"),
  keeping the plain time beside a trailing symbol ("10:30" and "10:30 hr"). A
  one-letter narrow day period is read only attached and only in CLDR's case, so "5p"
  is a time and "5A" is not.
- `FlexibleDateDetector` reads every CLDR short-date pattern of the language, its own
  included, and deposits each distinct valid date: en_US reads "31.12.2012" and ISO
  "2011-11-11", and reads "03/05/2013" both month first and day first. A year written
  first needs four digits.
- `FlexibleOrdinalDetector` reads grouped ordinals ("1,000th") and another locale's
  ordinal indicator when none of its letters is in this locale's CLDR exemplars ("1º"
  in English text). A Roman numeral and a fraction span a plural or possessive suffix
  ("II's", "3/4s").

### Fixed

- `FlexibleTimeDetector` and `FlexibleDateIntervalDetector` keep no per-call state on
  the detector, so one detector serves nested or concurrent calls: a call made inside
  another no longer drops the outer call's trailing-unit reading or clears its offset
  maps. No detector in icukit now writes to itself outside its constructor.
- A number, date, or other value reading no longer starts or ends inside a word with
  alphanumerics on both sides of it in that word: "2788" no longer yields "788",
  "29th" no longer yields "29", "asdf123" no longer yields "123", "ab2,788" no longer
  yields "788", "v2.0" no longer yields "0", and "2016/07/03" no longer yields
  "6/07/03". This also refuses the bare "1.2" inside "1.2M" and the bare mantissa
  inside "1.2345E4", which the compact and scientific readings still cover, and
  anything inside an unspaced "1,2,3". Words are ICU's, so "3" in "我有3个" still
  reads, and a combining mark or format character is part of the word it extends. A
  digit against a letter of a script ICU breaks between letters is a token of its own,
  so "100" in the Thai "ราคา100บาท" still reads.
- `AbbreviationDetector` no longer deposits a lowercase word that matches an entry
  only case-insensitively ("sun." against "Sun.", Sunday), and no longer starts an
  abbreviation inside a word ("s." in "C's.").
- `LetterNameDetector` reads a letter with a plural or possessive suffix ("C's", "i's",
  "Cs") as the letter's name, spanning the whole token with the suffix in its own
  `suffix` capture. The suffix follows an apostrophe, a quotation mark that Unicode word
  breaking joins, or is a bare "s" after a capital. "As" and "Is" also read as letter
  plurals, left for a prior to rank against the word.

### Changed

- A locale whose short-time pattern has no day period (en_GB, de_DE) now reads one
  written after a time as a 12-hour time: "5:30 p.m." reads as 17:30, and de_DE
  "3:45 PM" as 15:45. Such a time was previously refused outright, which left it with
  no reading at all.
- The traditional US state abbreviations (`Calif.`, `Md.`, `N.Y.`, and the rest) and
  Maryland as a reading of `MD` moved from `en.xml` to the `en_US` overlay, so they are
  read, and suppress a sentence break, in US English only. Every English locale still
  reads `MD` spelled out as the degree, and `U.S.`, `U.K.`, and the other country
  names. An `en_US` detection's `AbbreviationSpec.source` is now `en-US`.

- The development extra's tiergraph requirement is a floor without an upper cap,
  `tiergraph>=0.2`, so a tiergraph release that breaks the test suite shows up there
  instead of being held back.

## [0.4.0] - 2026-09-07

### Added

- `LetterNameDetector` and `SingleLetterWordDetector`, which deposit a letter's
  spoken name and locale word reading alongside other candidates for an isolated
  letter. Their locale tables are lexical because CLDR carries neither letter
  pronunciations nor word lists.
- `--json` on every remaining `collate`, `datetime`, `idna`, and `measure`
  subcommand: `collate compare` and `collate sort`; `datetime format`,
  `relative`, `interval`, `parse`, `patterns`, and `calendars`; `idna encode`
  and `idna decode`; and `measure format`, `convert`, `range`, `sequence`,
  `usage`, and `check`. Those four commands previously emitted only human text
  from at least one subcommand, so no pipeline could consume them. Each of those
  four commands is now uniform: every one of its subcommands takes `--json`. The
  rest of the CLI is not — forty-two leaves elsewhere still emit only human text —
  so the claim here is about `collate`, `datetime`, `idna`, and `measure` and no
  wider, and `tests/test_cli_registry.py` holds it to exactly that scope while
  recording the forty-two with a reason each.
- `print_record`, a formatter for a command that yields exactly one thing by
  nature — one unit's information, one parse result, one comparison. It renders
  a bare JSON object, or a single TSV row.
- `icukit.datetime.list_pattern_symbols()`, the catalog of date/time pattern
  field symbols with a name and an example for each. The catalog previously
  lived in the `datetime patterns` command module, where nothing but that one
  command could read it; it is library knowledge, and the command is now a
  client of it. `PATTERNS`, already re-exported by the package, is now declared
  in `icukit.datetime.__all__` alongside it.
- Command-line routes for four library capabilities that had none:
  - `collate key` emits the ICU collation sort key for each input line as
    lowercase hex, one per line, or as a JSON list of `{text, key}` at any size.
    Hex preserves byte order, so sorting the keys reproduces `collate sort`.
  - `idna encode --label` and `idna decode --label` convert a single domain
    label rather than a whole name, refusing any input containing a dot. Without
    the option the behavior is unchanged.
  - `measure abbrev UNIT` reports a unit's abbreviation in a locale, with no
    value attached — `measure abbrev kilometer -l ru_RU` gives `км`.
  - `locale format --type scientific` joins `number`, `currency`, and `percent`,
    reaching ICU's scientific instance.
- `locale maximize` as a spelling of `locale expand`. The CLI already offered
  `locale minimize`, and `maximize` is the name ICU gives its counterpart, so it
  is the word a user reaches for after seeing one half of the pair.
- Strict, round-tripping date and number detectors, typed value and format-spec
  classes, candidate resolution, `detect()`, and `DetectorSet` composition.
- Flexible recognizers for numbers, numeric and textual dates, currency symbols
  and names, compact and scientific numbers, spellout numbers, relative dates,
  date intervals, fractions, ordinals, times, percents, and measures.
- A reflective detector engine with `Family`, `generated_detectors()`, detector
  reports, and abbreviation, date/time skeleton, date interval, compact number,
  scientific number, spellout number, and relative date family constants.
- An abbreviation subsystem with a RELAX NG-validated XML lexicon, English
  lexicon data, compilation and loading APIs, a sentence-break post-filter, and
  an abbreviation detector.
- A recall evaluation harness backed by a vendored oracle and a round-trip
  conformance harness with a golden detector inventory.
- Measure recognition values and format specifications, plus locale-aware unit
  abbreviation utilities.
- Recognition for written shapes the flexible detectors previously passed over.
  Roman numerals read as cardinals, through ICU's own Roman rule set with a
  format-back check, under a `number:cardinal:roman` type and an option
  governing whether an isolated letter counts as one. Vulgar fraction characters
  and signed fractions, reached through the compatibility decomposition rather
  than a character table. Decimals written with no leading digit. Amounts
  carrying a CLDR compact scale word or symbol, alone or under a currency, with
  `FlexibleCompactDetector` matching multi-letter scale words without regard to
  case and single-letter symbols only when a caller asks it to fold them.
  ISO-qualified currency symbols such as `US$` and `A$`, harvested from the
  sibling locales of the same language, and imported only where a locale's short
  form differs from its narrow form, which is what keeps a bare `$` meaning USD.
  Day-first and month-year textual dates, read from those sibling locales'
  pattern generators because the `en_US` generator returns a month-first pattern
  for every skeleton. Two facts here are lexical because CLDR does not carry
  them, and the code says so: the suffix `bn`, and bare English `dollar` and
  `dollars`. Decades stay out of scope; CLDR has no pattern for them and the
  date value has no year-range field.

### Changed

- Isolated letter-name and one-letter-word readings carry a capture over the observed letter, allowing equal-span readings with parsed structure to reach downstream ranking on equal geometry.
- The detector conformance gate no longer disappears when ICU moves. It compared
  a committed inventory against the one the running ICU produces and skipped the
  whole module when the versions differed, and the backend is declared with a
  version floor rather than an equality, so an ordinary dependency resolve could
  carry ICU forward and take the entire signal with it while the build stayed
  green — including `test_inventory_cannot_pass_vacuously`, the guard that the
  gate is measuring something, which was disabled by exactly the drift it exists
  to survive. A mismatch now fails the build in CI and warns everywhere else, and
  only the byte-for-byte comparison against the recorded file is conditional on
  the ICU version; the digest, the positive controls, the anti-vacuity guard and
  the negative mutation controls describe live ICU behavior and run on every ICU.
  `ICUKIT_CONFORMANCE_STRICT=1` opts into the CI behavior locally. The dependency
  floor is deliberately left a floor: a runtime cap would hold every downstream
  consumer at this project's golden and would stop CI ever meeting a newer ICU,
  which is the notice the gate is built to give.
- `icukit spoof check` names the check that fired. It listed the checks by hand
  and omitted the restriction level, which is the one ICU sets for a mixed-script
  identifier, so `icukit spoof check 'pаypal'` reported `suspicious` and then
  named no issue at all. The issue list is now read off the record, so a check
  added to `check_string` reaches the human output without a second edit.
- `check_string` and `SpoofChecker.check` report a `hidden_overlay` field. ICU's
  default check already set the bit — for a combining mark concealed by the base
  character's own mark, as in `i` followed by U+0307 — so it reached
  `is_suspicious` with no field to say which check had fired.
- Every registered command alias now reaches `icukit --help` and the generated
  CLI reference. Aliases are declared once, in the command registry, and the
  prefix matcher resolved them before argparse ever saw them; only six commands
  repeated their aliases by hand at the parser, so the other twenty-two had
  working aliases that no help text or document mentioned. Nothing new resolves —
  `icukit brk`, `icukit listformat`, and `icukit recognize` worked before — but
  they are now visible where a user would look for them.
- `timezone equiv` is now spelled `timezone equivalent`, with `equiv` kept as an
  alias alongside `e` and `eq`. Every other subcommand in the CLI is named with a
  whole word and abbreviates through aliases; this was the one that inverted
  that, so typing more of the word failed. Every existing invocation, and every
  prefix of one, still resolves to the same command.

- **Breaking:** `format_output(data, as_json=True)` no longer unwraps a
  single-item sequence. It now preserves the shape it is given, so a sequence
  renders as a JSON array at every length, including one and zero, and callers
  never have to branch on cardinality. Callers that want a bare object should
  pass the object, or use `print_record`.

  This changes `--json` output for any command whose result happens to hold
  exactly one item. `icukit plural categories -l ja --json` now emits
  `[{"category": "other"}]` rather than `{"category": "other"}`, and
  `icukit script detect --all --json -t abc` now emits `["Latin"]` rather than
  `"Latin"`. Commands that return one thing by nature — `bidi detect`,
  `calendar info`, `collate info`, `duration parse`, `measure info`,
  `parse currency`, `plural info`, `region info`, `script info`,
  `timezone info` — still emit a bare object, and their output is unchanged.
- Export the complete recognition surface from the top-level package, including
  flexible recognizers, detector entry points and groups, value classes, and
  reflective families; `from icukit import *` is coherent again.
- Document Python 3.11 as the minimum supported version, matching package
  metadata.

### Fixed

- Single-letter Roman cardinals use the letter detectors' isolation rule, excluding identifier and contraction members while leaving multi-letter Roman runs unchanged.
- The generated CLI reference documented each command under its longest
  spelling rather than its own name, so `spoof` and `idna` appeared as aliases
  of `confusable` and `punycode`. A command is now documented under the name its
  parser was created with, whatever the length of its aliases.
- Nine subcommands were missing from the generated CLI reference entirely. The
  generator identified aliases by comparing descriptions and argument lists, so
  any two genuinely distinct commands that happened to match — `bidi check` and
  `bidi strip`, `discover all`/`api`/`cli`, `search count` and `search find`
  among them — were collapsed into a single entry and the rest were dropped.
  Aliases are now identified by the parser they share.
- `check_string`'s documented example claimed `mixed_script` was `True` for a
  string spelled with a Cyrillic `а`. It is not, and never was: the confusability
  flags answer a pairwise question, and ICU does not set them for a check of one
  string on its own. What fires is `restriction_level`. The docstring records the
  distinction, and the test asserted only `is_suspicious`, which is why the
  example could stay wrong.
- `resolve()` and `resolve_text()` annotated `epsilon` as `int` while
  `DEFAULT_EPSILON` is `1.0`. A fractional tolerance is meaningful — weights are
  integral, so a threshold between two of them is only expressible as a float —
  and the annotation told callers otherwise.
- Four unused constants in `icukit.spoof`, among them a hard-coded
  `_CHECK_HIDDEN_OVERLAY` carrying an unfinished investigation in its comment. In
  an anti-spoofing module a named-but-unread check reads as a capability that was
  intended and dropped. Three were genuinely dead and are gone; the fourth turned
  out to name a check ICU really does report, and is now wired up and witnessed.
- The API reference documented a constant with the last line of its comment rather
  than the whole comment, so a two-line explanation was published as a sentence
  fragment: `DEFAULT_FAMILIES` read "inverter. Abbreviations use their typed
  lexicon." Nothing was malformed, which is why it stood — a fragment still reads
  as prose. The generator now takes the contiguous comment block, and an
  assignment docstring still takes precedence over a comment.
- Preserve exact `Decimal` values for large flexible compact numbers, percents,
  and fractions instead of rounding, emitting exponent notation, or raising.
- Derive unit abbreviations from ICU's numeric field position, preserving digits
  that belong to unit labels and handling locale-specific digits correctly.
- Treat unreformattable date parses as non-matches and recognize standalone
  month and weekday date skeletons without crashing.

## 0.3.0

### Added

- Typed segmentation spans: `break_word_spans`, `break_sentence_spans`,
  `break_line_spans`, `break_grapheme_spans` (and `Breaker.iter_*_spans`) return
  `BreakSpan` dicts with code-point `start`/`end`, ICU rule-status-derived `types`,
  the raw `statuses` vector, and, on the line tier, `break_type`
  (`"mandatory"`/`"optional"`).
- `RuleBreaker` and `default_rules`: segment text with a custom ICU
  `RuleBasedBreakIterator` rule set, mapping in-rule status tags to type names;
  `default_rules(kind, locale)` returns the standard rules as a base to extend.

### Fixed

- Text segmentation returned UTF-16 code-unit offsets sliced as Python code points,
  corrupting every token after an astral character (all four `break_*` iterators).
  Boundaries are now code-point indices, and the iterators hold the `UnicodeString`
  passed to ICU. **Output for text containing astral characters changes and is not
  backward compatible.**
- `tokenize_sentences` segments over the whole text instead of re-segmenting each
  sentence substring, so a word is no longer split across a sentence boundary.
- `regex` and `search` reported UTF-16 match offsets that were used as Python
  string indices, corrupting `search_replace`/`regex_split` output on text with
  astral characters; offsets are now code points.

### Changed

- Require Python 3.11 or newer.

## 0.2.0

### Fixed

- CLI commands now report a clean `Error: ...` message and exit non-zero
  instead of dumping a Python traceback for bad file paths, invalid
  transliterator IDs, and other ICU errors.
- `ik discover all` and `python -m icukit.discover` no longer crash with an
  `AttributeError`.
- `ik measure info/types/units --json` no longer crash (they passed an
  unknown `json_output=` argument to the formatter).
- `bidi check` now exits `1` (was `2`) on error, matching every other command.

### Changed

- Depend on `icukit-pyicu>=78.3.0` on every platform. icukit-pyicu now ships
  manylinux wheels in addition to macOS wheels, so the bundled ICU/PyICU is the
  single default backend on both macOS and Linux (previously Linux pulled in
  system `PyICU`, which required ICU dev packages). The now-redundant `bundled`
  extra is removed; advanced users can still install a system PyICU and then
  `pip install --no-deps icukit`.
- `get_transliterator_info()` returns `None` for an invalid transliterator ID
  instead of a dictionary of `None` values, matching `get_calendar_info`,
  `get_region_info`, and `get_timezone_info`.
- Dropped the `Python :: 3.14` classifier (not yet in the test matrix; PyICU
  segfaults there).

### Added

- Ship a `py.typed` marker so downstream type checkers use icukit's type hints.

### Internal

- Adopt `ruff` for linting and formatting (replaces black/flake8/isort) and run
  it in CI; modernize type hints to `from __future__ import annotations` with
  builtin generics.
- Remove dead code (`cli/output_helpers.py`, unused `base.py` helpers); add a
  shared `_add_locale_option` helper; single-source the package version.

## 0.1.3

- Platform-conditional ICU dependencies: icukit-pyicu on macOS, PyICU on Linux
- Add `[bundled]` extra for explicit bundled ICU installation on any platform
- Add runtime check with helpful error message when PyICU is not installed
- Add installation documentation (`docs/install.md`)

## 0.1.2

- Remove TestPyPI publishing
- Re-enable PyPI publish on tags

## 0.1.1

- Add future annotations for Python 3.9 compatibility
- Fix circular import in discover.py

## 0.1.0

- Initial release

[Unreleased]: https://github.com/lenzo-ka/icukit/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/lenzo-ka/icukit/compare/v0.3.0...v0.4.0
