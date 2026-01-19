# icukit CLI Reference

ICU Kit - Unicode ICU utilities for text processing

A toolkit for international text processing, providing:
  - Text transliteration between scripts
  - Unicode-aware regular expressions
  - Script detection and properties
  - Unicode normalization and character info

Examples:
  # Transliterate to Greek
  echo 'Hello' | icukit transliterate name Latin-Greek

  # Unicode regex with script matching
  echo 'Hello Αθήνα' | icukit regex find '\p{Script=Greek}+'

  # Detect script of text
  icukit script detect -t 'Ελληνικά'

  # Normalize Unicode text
  echo 'café' | icukit unicode normalize --form NFC

  # Get character info
  icukit unicode info -t 'α'

For detailed help on any command:
  icukit <command> --help

**Options:**

- `--version`: Show version and exit
- `-v, --verbose`: Increase verbosity (-v for INFO, -vv for DEBUG) (default: `0`)

## Commands

## `icukit calendar`

Query available calendar systems (Gregorian, Buddhist, Hebrew, Islamic, etc.).

Calendar types include:
  gregorian  - Western standard calendar
  buddhist   - Thai Buddhist calendar
  chinese    - Chinese lunar calendar
  hebrew     - Hebrew/Jewish calendar
  islamic    - Islamic/Hijri calendar (multiple variants)
  japanese   - Japanese Imperial calendar
  persian    - Persian/Jalali calendar

Examples:
  # List all calendar types
  icukit calendar list
  icukit cal list

  # Get info about a calendar
  icukit cal info hebrew
  icukit cal info islamic --json

### `icukit calendar help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit calendar info` (aliases: i)

**Options:**

- `calendar`: Calendar type (e.g., gregorian, hebrew)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit calendar list` (aliases: l, ls)

**Options:**

- `-s, --short`: Show only calendar type names (default: `False`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

## `icukit discover`

Discover icukit's available features, API exports, and CLI commands.

Examples:
  # Show all features
  icukit discover all
  icukit discover

  # Show API details
  icukit discover api

  # Show CLI commands
  icukit discover cli

  # Search for features
  icukit discover search translit

  # JSON output
  icukit discover all --json

### `icukit discover commands` (aliases: a, all, api, cli, cmds)

**Options:**

- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit discover help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit discover search` (aliases: find, s)

**Options:**

- `query`: Search query
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

## `icukit help`

Show help information for icukit commands

**Options:**

- `command`: Command to show help for

## `icukit locale`

Parse, validate, and query locale identifiers (language + region + script).
Format numbers, currency, and percentages according to locale conventions.

Locale format: language[_Script][_REGION][@keywords]
  Examples: en, en_US, zh_Hans, zh_Hans_CN, sr_Latn_RS

Examples:
  # Get comprehensive locale attributes
  icukit locale attrs en_US
  icukit locale attrs de_DE --json

  # Format numbers
  icukit locale format 1234567.89 --locale de_DE
  icukit locale format 1234.56 --locale ja_JP --type currency
  icukit locale format 0.15 --locale fr_FR --type percent

  # Spell out numbers
  icukit locale spellout 42 --locale en_US
  icukit locale ordinal 1 --locale en_US

  # Get display name
  icukit locale name ja_JP
  icukit locale name ja_JP --in ja

  # List locales/languages
  icukit locale list --short
  icukit locale languages

  # Parse and manipulate
  icukit locale parse sr_Latn_RS
  icukit locale expand zh
  icukit locale minimize zh_Hans_CN

### `icukit locale attributes` (aliases: a, attrs)

**Options:**

- `locale`: Locale identifier (e.g., en_US)
- `--display, -d`: Locale for display names (default: en) (default: `en`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit locale canonicalize` (aliases: c, canon)

**Options:**

- `locale`: Locale string to canonicalize

### `icukit locale display` (aliases: n, name)

**Options:**

- `locale`: Locale to get display name for
- `--in, -i`: Locale for the display name (default: en) (default: `en`)

### `icukit locale expand` (aliases: e, likely)

**Options:**

- `locale`: Minimal locale to expand (e.g., zh, sr)

### `icukit locale format` (aliases: f, fmt)

**Options:**

- `value`: Number to format
- `--locale, -l`: Locale for formatting (default: en_US) (default: `en_US`)
- `--type, -t`: Format type (default: number) (default: `number`)
- `--currency, -c`: Currency code for currency format (e.g., EUR)

### `icukit locale help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit locale info` (aliases: i)

**Options:**

- `locale`: Locale identifier (e.g., en_US, zh-Hans-CN)
- `--display, -d`: Locale for display names (default: en) (default: `en`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit locale languages` (aliases: lang)

**Options:**

- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit locale list` (aliases: l, ls)

**Options:**

- `-s, --short`: Show only locale IDs (default: `False`)
- `--display, -d`: Locale for display names (default: en) (default: `en`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit locale minimize` (aliases: m, min)

**Options:**

- `locale`: Full locale to minimize

### `icukit locale ordinal` (aliases: ord)

**Options:**

- `value`: Integer to format as ordinal
- `--locale, -l`: Locale for formatting (default: en_US) (default: `en_US`)

### `icukit locale parse` (aliases: p)

**Options:**

- `locale`: Locale string to parse
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit locale spellout` (aliases: spell, words)

**Options:**

- `value`: Integer to spell out
- `--locale, -l`: Locale for spelling (default: en_US) (default: `en_US`)

### `icukit locale validate` (aliases: check, v)

**Options:**

- `locale`: Locale string to validate

## `icukit regex`

Unicode-aware regular expressions with full Unicode support.

Features:
  - Unicode properties and categories (\p{L}, \p{Script=Greek})
  - List available properties, categories, and scripts
  - Find/replace with Unicode awareness
  - Named capture groups
  - Split text by patterns

Examples:
  # List Unicode properties and categories
  icukit regex list properties
  icukit regex list categories
  icukit regex list scripts

  # Find matches
  echo 'Hello Αθήνα مرحبا' | icukit regex find '\p{Script=Greek}+'
  echo 'abc123def456' | icukit regex find '\d+' --all

  # Replace text
  echo 'Hello123World' | icukit regex replace '\d+' ' '
  echo 'test@example.com' | icukit regex replace '(\w+)@(\w+\.\w+)' '$1 at $2'

  # Split text
  echo 'apple,banana;orange:grape' | icukit regex split '[,;:]'

  # Case-insensitive Unicode matching
  echo 'Café CAFÉ café' | icukit regex find 'café' -i

Common Properties:
  \p{L}          - Any letter
  \p{N}          - Any number
  \p{P}          - Any punctuation
  \p{Z}          - Any separator
  \p{Ll}, \p{Lu} - Lowercase/uppercase letters
  \p{Script=X}   - Characters from script X

Common Scripts:
  Latin, Cyrillic, Greek, Arabic, Hebrew, Devanagari,
  Han (Chinese), Hiragana, Katakana, Thai

### `icukit regex find` (aliases: f)

**Options:**

- `pattern`: ICU regex pattern
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `--all`: Find all matches (default: first only) (default: `False`)
- `-g, --groups`: Show capture groups (default: `False`)
- `-n, --line-numbers`: Show line numbers (default: `False`)
- `--only-matching`: Show only matching parts (default: `False`)
- `-c, --count`: Count matches only (default: `False`)
- `--limit`: Maximum matches to find
- `-i, --ignore-case`: Case-insensitive matching (Unicode-aware) (default: `False`)
- `-m, --multiline`: Multiline mode (^ and $ match line boundaries) (default: `False`)
- `-s, --dotall`: Dot matches newlines (default: `False`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit regex help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit regex list` (aliases: l, ls)

**Options:**

- `what`: What to list (default: all) (default: `all`)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit regex match` (aliases: m)

**Options:**

- `pattern`: ICU regex pattern
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-i, --ignore-case`: Case-insensitive matching (Unicode-aware) (default: `False`)
- `-m, --multiline`: Multiline mode (^ and $ match line boundaries) (default: `False`)
- `-s, --dotall`: Dot matches newlines (default: `False`)
- `-v, --verbose`: Show match details (default: `False`)

### `icukit regex replace` (aliases: r, sub)

**Options:**

- `pattern`: ICU regex pattern to find
- `replacement`: Replacement text (use $1, $2 for groups)
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `--limit`: Maximum replacements per line
- `-i, --ignore-case`: Case-insensitive matching (Unicode-aware) (default: `False`)
- `-m, --multiline`: Multiline mode (^ and $ match line boundaries) (default: `False`)
- `-s, --dotall`: Dot matches newlines (default: `False`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit regex script` (aliases: expr, s, sed)

**Options:**

- `expression`: Substitution expression: s/pattern/replacement/[gi] (delimiter can be any char)
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit regex search` (aliases: t, test)

**Options:**

- `pattern`: ICU regex pattern
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-i, --ignore-case`: Case-insensitive matching (Unicode-aware) (default: `False`)
- `-m, --multiline`: Multiline mode (^ and $ match line boundaries) (default: `False`)
- `-s, --dotall`: Dot matches newlines (default: `False`)

### `icukit regex split` (aliases: sp)

**Options:**

- `pattern`: ICU regex pattern to split by
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `--limit`: Maximum number of splits
- `-i, --ignore-case`: Case-insensitive matching (Unicode-aware) (default: `False`)
- `-m, --multiline`: Multiline mode (^ and $ match line boundaries) (default: `False`)
- `-s, --dotall`: Dot matches newlines (default: `False`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

## `icukit region`

Query countries, territories, continents, and their relationships.

Region types:
  territory   - Countries and territories (US, FR, JP, ...)
  continent   - Continents (Africa, Americas, Asia, Europe, Oceania)
  subcontinent - Subcontinental regions (Northern America, ...)
  grouping    - Economic/political groupings (EU, UN, ...)
  world       - The world (001)

Examples:
  # List all countries/territories
  icukit region list

  # List continents
  icukit region list --type continent

  # Get info about a region
  icukit region info US
  icukit region info FR --json

  # What regions are in the Americas?
  icukit region contains 019

  # List region types
  icukit region types

### `icukit region contains` (aliases: c, in)

**Options:**

- `code`: Region code to get contained regions for
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit region help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit region info` (aliases: i)

**Options:**

- `code`: Region code (e.g., US, FR, 001)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit region list` (aliases: l, ls)

**Options:**

- `--type, -t`: Region type to list (default: territory) (default: `territory`)
- `-s, --short`: Show only region codes (default: `False`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit region types` (aliases: t)

**Options:**

- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

## `icukit script`

Detect writing systems (scripts) and query script properties.

Scripts include Latin, Greek, Cyrillic, Han, Arabic, Hebrew, and many more.

Examples:
  # Detect script of text
  echo 'Hello' | icukit script detect
  echo 'Ελληνικά' | icukit script detect
  icukit script detect -t '你好世界'

  # Detect all scripts in mixed text
  icukit script detect -t 'Hello Ελληνικά 你好' --all

  # Check if text is right-to-left
  icukit script rtl -t 'مرحبا'
  icukit script rtl -t 'Hello'

  # Get info about a script
  icukit script info Greek
  icukit script info Arabic --json

  # List all scripts
  icukit script list
  icukit script list --cased    # only cased scripts
  icukit script list --rtl      # only RTL scripts

### `icukit script detect` (aliases: d)

**Options:**

- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-a, --all`: Detect all scripts in text (default: `False`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit script help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit script info` (aliases: i)

**Options:**

- `script`: Script name (e.g., Greek, Latin, Han)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit script list` (aliases: l, ls)

**Options:**

- `--cased`: Only cased scripts (default: `False`)
- `--rtl`: Only RTL scripts (default: `False`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit script rtl` (aliases: r)

**Options:**

- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)

## `icukit timezone`

Query timezone data including offsets, DST rules, and display names.

Examples:
  # List all timezones
  icukit timezone list
  icukit tz list

  # List US timezones only
  icukit tz list --country US

  # Get info about a timezone
  icukit tz info America/New_York
  icukit tz info Europe/London --json

  # Get equivalent timezone IDs
  icukit tz equiv America/New_York

### `icukit timezone equiv` (aliases: e, eq)

**Options:**

- `timezone`: Timezone ID to find equivalents for
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit timezone help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit timezone info` (aliases: i)

**Options:**

- `timezone`: Timezone ID (e.g., America/New_York)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit timezone list` (aliases: l, ls)

**Options:**

- `--country, -c`: Filter by country code (e.g., US, DE, JP)
- `-s, --short`: Show only timezone IDs (default: `False`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

## `icukit transliterate`

Transliterate text using ICU transliterators or custom rules.

Shortcut: If a transliterator ID is given directly, 'name' is assumed:
  icukit tr Latin-Greek        # same as: icukit tr name Latin-Greek

Examples:
  # List available transliterators
  icukit transliterate list
  icukit transliterate list --name 'Latin-.*'

  # Convert text
  echo 'Hello World' | icukit transliterate name Latin-Greek

  # Reverse transliteration
  echo 'Ελληνικά' | icukit transliterate from Latin-Greek

  # Custom rules
  icukit transliterate rules my-rules.txt < input.txt

  # Remove accents using inline script
  echo 'Café' | icukit transliterate script 'NFD; [:Nonspacing Mark:] Remove; NFC'

### `icukit transliterate custom` (aliases: r, rules)

**Options:**

- `rules_file`: File containing transliteration rules
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-n, --name`: Name for custom transliterator (default: `custom`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit transliterate help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit transliterate inline` (aliases: expr, s, script)

**Options:**

- `expression`: ICU transform expression (e.g., "NFD; [:Nonspacing Mark:] Remove; NFC")
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit transliterate list` (aliases: l, ls)

**Options:**

- `--name`: Filter by transliterator name (regex supported)
- `--from`: Filter by source script
- `--to`: Filter by target script
- `--scripts`: Group by source scripts (default: `False`)
- `-s, --short`: Show only IDs (default: `False`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit transliterate name` (aliases: n)

**Options:**

- `transliterators`: Transliterator name(s) - comma-separated or regex
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit transliterate reverse` (aliases: f, from)

**Options:**

- `transliterators`: Transliterator name(s) for reverse
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

## `icukit unicode`

Normalize Unicode text and query character properties.

Normalization forms:
  NFC  - Canonical composition (default, recommended for storage)
  NFD  - Canonical decomposition
  NFKC - Compatibility composition (normalizes ligatures, etc.)
  NFKD - Compatibility decomposition

Examples:
  # Normalize text to NFC (default)
  echo 'café' | icukit unicode normalize

  # Normalize to specific form
  echo 'café' | icukit unicode normalize --form NFD
  echo 'ﬁ' | icukit unicode normalize --form NFKC  # fi ligature -> fi

  # Check if text is normalized
  icukit unicode check -t 'café' --form NFC

  # Get character name
  icukit unicode name -t 'α'
  icukit unicode name -t '😀'

  # Get full character info
  icukit unicode info -t 'α' --json

  # List Unicode categories
  icukit unicode categories

### `icukit unicode categories` (aliases: cat, cats)

**Options:**

- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit unicode charname` (aliases: char, i, info, name)

**Options:**

- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit unicode check` (aliases: c)

**Options:**

- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-f, --form`: Normalization form to check (default: NFC) (default: `NFC`)

### `icukit unicode help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit unicode normalize` (aliases: n, norm)

**Options:**

- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-f, --form`: Normalization form (default: NFC) (default: `NFC`)
- `-o, --output`: Output file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
