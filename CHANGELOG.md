# Changelog

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
