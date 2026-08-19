# Vendored evaluation oracle: NeMo-text-processing

A small subset of the text-normalization test tables from NVIDIA
NeMo-text-processing, vendored as an evaluation oracle for icukit's
recognizers. These are eval-only fixtures and are not part of the shipped
`icukit` package.

- Source: https://github.com/NVIDIA/NeMo-text-processing
- Upstream path: `tests/nemo_text_processing/en/data_text_normalization/test_cases_<class>.txt`
- Fetched: 2026-08-19 from the `main` branch
- License: Apache License 2.0 (see `LICENSE` in this directory)

Format: each line is `written~spoken`, for example `13,000~thirteen thousand`
or `13000~one three zero zero zero`. The harness uses the written (left) side
as input to icukit's recognizers and measures recall per class; the spoken
(right) side is retained for later verbalization evaluation.

Classes present: cardinal, decimal, date, time, money, fraction, ordinal
(English). Additional locales and the CLDR/ICU format oracle and Duckling
negative corpus are follow-on additions.
