# Changelog

## 0.2.0 (unreleased)

- Fix text segmentation boundary offsets: ICU BreakIterator reports UTF-16
  code-unit indices, which were sliced as Python code points and corrupted every
  token after an astral character (all four iterators). Boundaries are now mapped
  to code-point indices before slicing. Output for text containing astral
  characters changes and is not backward compatible.
- Hold the `UnicodeString` passed to `BreakIterator.setText`.
- `tokenize_sentences` segments over the whole text instead of re-segmenting each
  sentence substring, so a word is no longer split across a sentence boundary.

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
