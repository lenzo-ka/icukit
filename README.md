# icukit

A comprehensive Python toolkit for Unicode and internationalization, built on ICU (International Components for Unicode).

icukit provides a Pythonic interface to ICU's powerful text processing, localization, and internationalization capabilities. It includes both a library API and a command-line interface.

## Installation

```bash
pip install icukit
```

This pulls in [`icukit-pyicu`](https://github.com/lenzo-ka/icukit-pyicu), which
bundles pre-built ICU libraries and PyICU. There are no system dependencies to
install on either **macOS** or **Linux** — the wheels are self-contained.

See [Installation Guide](https://github.com/lenzo-ka/icukit/blob/main/docs/install.md) for details, including how to use a system PyICU instead.

## Features

### Text Processing

- **Transliteration**: Convert between scripts (Latin to Cyrillic, Hangul to Latin, etc.)
- **Normalization**: NFC, NFD, NFKC, NFKD Unicode normalization forms
- **Text Segmentation**: Break text into words, sentences, lines, or grapheme clusters
- **Unicode Regex**: Full Unicode-aware regular expressions with script and property support

### Recognition

- **Value readings**: Find numbers, dates, times, measures, currencies, ordinals, and abbreviations in text by inverting ICU's own formatting, keeping every plausible reading of a span
- **Language-wide forms**: Read the forms every locale of a language writes (en_US text reads en_GB's "12 kilometres"), or only the locales a caller chooses

Readers come assembled in sets. `generated_detectors(locale)` holds the readers that invert ICU's canonical formatting (each date skeleton, each interval, compact, spelled-out, and relative form); `flexible_detectors(locale)` holds the flexible readers, which read the forms text writes beyond ICU's own (negative and accounting currency, dates with eras, mixed measures, other decimal styles, times with zone names), each reader that takes a currency or unit built for those it chooses from ICU. A unit is read where CLDR's unit preferences give it to a region of the language, and every duration and data-size unit everywhere, so German text's "°F" is not read unless you pass `units=`. The flexible set costs more than the generated one: on the order of 5 to 10 seconds to build for en_US (a few for a language of few locales), so build it once and reuse it, and each `detect` a small multiple of the generated set's (the readers share the numbers they read, kept for the 16 texts read last, about 110 bytes per character each for en_US). For every reading, use both: `generated_detectors(locale).with_(*flexible_detectors(locale).detectors)`. Pass `guarded=True` to `flexible_detectors`, or build `generated_detectors(locale, (*DEFAULT_FAMILIES, *GUARDED_FAMILIES))` (`GUARDED_FAMILIES` alone builds only the guarded readers), to add the readings the default readers refuse on purpose ("May" alone as a month).

Recognition reads plain text strings. Markdown, rich text, HTML, XML, and other markup must be turned into text before icukit reads it, by the caller or on the client; icukit has no mode for them. It also has no URL or email detector, so readings can fall inside a URL ("2004" in a path).

### Localization

- **Number Formatting**: Decimal, currency, percent, scientific, spelled-out numbers
- **Date/Time Formatting**: Locale-aware date and time formatting with multiple styles
- **Duration Formatting**: Human-readable time durations ("2 hours, 30 minutes")
- **List Formatting**: Locale-aware list formatting ("A, B, and C")
- **Plural Rules**: Determine plural categories (one, few, many, other) for any locale
- **Message Formatting**: ICU MessageFormat for complex localized strings

### Internationalization Utilities

- **Collation**: Locale-aware string sorting and comparison
- **Locale Information**: Parse, validate, and query locale data
- **Script Detection**: Identify writing scripts in text
- **Bidirectional Text**: Detect and handle RTL/LTR text
- **IDNA**: Internationalized domain name encoding/decoding
- **Spoof Detection**: Detect confusable characters and homograph attacks

### Reference Data

- **Regions**: Country and region codes with containment relationships
- **Scripts**: Writing system information and properties
- **Timezones**: Timezone data with offsets and equivalents
- **Calendars**: Calendar system information (Gregorian, Hebrew, Islamic, etc.)

## Quick Start

### Library API

```python
from icukit import (
    transliterate,
    sort_strings,
    format_number,
    format_datetime,
    get_plural_category,
    break_words,
)

# Transliterate text between scripts
transliterate("Привет мир", "Russian-Latin/BGN")  # "Privet mir"
transliterate("hello", "Latin-Cyrillic")  # "хелло"

# Sort strings with locale-aware collation
sort_strings(["cafe", "café", "CAFE"], "en_US")  # ['cafe', 'CAFE', 'café']
sort_strings(["Öl", "Ol", "öl"], "de_DE")  # ['Ol', 'öl', 'Öl']

# Format numbers for different locales
format_number(1234567.89, "en_US")  # "1,234,567.89"
format_number(1234567.89, "de_DE")  # "1.234.567,89"
format_number(1234567.89, "hi_IN")  # "12,34,567.89"

# Format dates
from datetime import datetime

now = datetime.now()
format_datetime(now, "en_US", style="LONG")  # "January 19, 2026 at 4:00:00 PM PST"
format_datetime(now, "ja_JP", style="LONG")  # "2026年1月19日 16:00:00 PST"

# Determine plural category
get_plural_category(1, "en")  # "one"
get_plural_category(2, "en")  # "other"
get_plural_category(2, "ru")  # "few"
get_plural_category(5, "ru")  # "many"

# Break text into words
break_words("Hello, world!")  # ['Hello', ',', 'world', '!']
```

### Recognition

```python
from icukit import flexible_detectors, generated_detectors, icu_abbreviations

readers = generated_detectors("en_US")
for d in readers.detect("Due March 5, 2024."):
    print(d["start"], d["end"], d["type"], d["text"])
# 4 17 date:yMMMMd March 5, 2024
# 4 11 date:MMMMd March 5

d = readers.detect("Due March 5, 2024.")[0]
# The value: DateTimeValue(fields=(('y', 2024), ('M', 3), ('d', 5)), calendar='gregorian')
d["value"]
# Each part with its own span: (Capture(name='y', start=13, end=17, text='2024', ...), ...)
d["captures"]
# How to write it again: DateFormatSpec(locale='en_US', skeleton='yMMMMd', pattern='MMMM d, y', ...)
d["spec"]

# Every locale of the language by default; `locales=` chooses them, and () is the locale alone
flexible_detectors("en_US").detect("12 kilometres")  # measure:kilometer and number:decimal
flexible_detectors("en_US", locales=()).detect("12 kilometres")  # number:decimal only

# The short forms ICU writes, with their expansions
icu_abbreviations("en_US", kinds=("unit",))  # (..., IcuAbbreviation(surface='m/s²', ...), ...)
```

Offsets are code points. `date_detectors(locale, skeletons)` and `number_detectors(locale, currencies=...)` build smaller sets by hand.

### Command-Line Interface

icukit includes a full-featured CLI accessible via `icukit` or `ik`:

```bash
# Transliterate text
ik transliterate name Russian-Latin/BGN -t "Москва"
# Output: Moskva

# List transliterators
ik transliterate list --name "Russian-.*"

# Recognize typed values in running text
ik detect --currency USD -t 'Paid $1,234.50 on March 5, 2024'

# Add the flexible readers (accounting currency, mixed measures); --locales alone reads en_US only
ik detect --flexible --locales -t 'Paid ($12.50) for 5 ft 3 in'

# Format numbers
ik locale format 1234567.89 --locale de_DE
# Output: 1.234.567,89
ik compact 1234567 --locale de_DE
# Output: 1,2 Mio.

# Get locale information
ik locale info en_US

# Sort lines with locale collation
cat names.txt | ik sort --locale sv_SE

# Detect the scripts in text
ik script detect --all -t "Hello Мир 世界"

# Get Unicode character information
ik unicode info -t "Aé"
```

Run `ik help` or `ik <command> --help` for detailed usage information.

## Supported Python Versions

- Python 3.11+
- Tested on Linux and macOS

## Documentation

- [API Reference](https://github.com/lenzo-ka/icukit/blob/main/docs/api.md)
- [CLI Reference](https://github.com/lenzo-ka/icukit/blob/main/docs/cli.md)

## License

BSD 2-Clause License
