# Changelog

## [Unreleased]

### Added

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

### Changed

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

### Fixed

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

## [0.4.0] - 2026-08-23

### Added

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

### Changed

- Export the complete recognition surface from the top-level package, including
  flexible recognizers, detector entry points and groups, value classes, and
  reflective families; `from icukit import *` is coherent again.
- Document Python 3.11 as the minimum supported version, matching package
  metadata.

### Fixed

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
