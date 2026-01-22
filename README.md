# icukit

A comprehensive Python toolkit for Unicode and internationalization, built on ICU (International Components for Unicode).

icukit provides a Pythonic interface to ICU's powerful text processing, localization, and internationalization capabilities. It includes both a library API and a command-line interface.

## Installation

```bash
pip install icukit
```

On **macOS**, this automatically includes bundled ICU libraries (via `icukit-pyicu`).

On **Linux**, you need PyICU installed. Either install system ICU packages first:

```bash
# Ubuntu/Debian
sudo apt install libicu-dev && pip install PyICU

# Fedora/RHEL
sudo dnf install libicu-devel && pip install PyICU
```

Or use bundled ICU: `pip install icukit[bundled]` or `pip install icukit icukit-pyicu`

See [Installation Guide](https://github.com/lenzo-ka/icukit/blob/main/docs/install.md) for details.

## Features

### Text Processing

- **Transliteration**: Convert between scripts (Latin to Cyrillic, Hangul to Latin, etc.)
- **Normalization**: NFC, NFD, NFKC, NFKD Unicode normalization forms
- **Text Segmentation**: Break text into words, sentences, lines, or grapheme clusters
- **Unicode Regex**: Full Unicode-aware regular expressions with script and property support

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
sort_strings(["cafe", "café", "CAFE"], "en_US")  # ['cafe', 'café', 'CAFE']
sort_strings(["Öl", "Ol", "öl"], "de_DE")  # ['Ol', 'Öl', 'öl']

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
break_words("Hello, world!")  # ["Hello", ",", " ", "world", "!"]
```

### Command-Line Interface

icukit includes a full-featured CLI accessible via `icukit` or `ik`:

```bash
# Transliterate text
ik transliterate "Москва" Russian-Latin/BGN
# Output: Moskva

# Format numbers
ik number 1234567.89 --locale de_DE
# Output: 1.234.567,89

# Get locale information
ik locale info en_US

# List available transliterators
ik transliterate --list

# Sort lines with locale collation
cat names.txt | ik sort --locale sv_SE

# Detect scripts in text
ik script detect "Hello Мир 世界"

# Get Unicode character information
ik unicode info "A"
```

Run `ik help` or `ik <command> --help` for detailed usage information.

## Supported Python Versions

- Python 3.9+
- Tested on Linux and macOS

## Documentation

- [API Reference](https://github.com/lenzo-ka/icukit/blob/main/docs/api.md)
- [CLI Reference](https://github.com/lenzo-ka/icukit/blob/main/docs/cli.md)

## License

MIT License
