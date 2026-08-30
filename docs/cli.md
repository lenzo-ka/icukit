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

## `icukit alpha-index` (aliases: ai, aindex, index)

Create locale-aware alphabetic index buckets for sorted lists.

Organizes items into A-Z style buckets appropriate for the locale
(e.g., A-Z for English, あかさたな for Japanese hiragana index).

Examples:
  # Create buckets from names
  echo -e 'Alice\nBob\nCarol\nZebra' | icukit alpha-index buckets

  # Get bucket labels for a locale
  icukit alpha-index labels ja_JP

  # Get bucket for a specific name
  icukit alpha-index bucket Alice

  # JSON output
  echo -e 'Alice\nBob' | icukit alpha-index buckets --json

### `icukit alpha-index bucket` (aliases: g, get)

**Options:**

- `name`: Name to get bucket for
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)

### `icukit alpha-index buckets` (aliases: b, create)

**Options:**

- `-l, --locale`: Locale for bucket labels (default: en_US) (default: `en_US`)
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit alpha-index help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit alpha-index labels` (aliases: l, ls)

**Options:**

- `locale`: Locale for bucket labels (default: en_US) (default: `en_US`)

## `icukit bidi`

Analyze and manipulate bidirectional (mixed LTR/RTL) text.

Useful for:
  - Detecting text direction
  - Finding hidden bidi control characters (security)
  - Stripping bidi controls from text

Examples:
  # Detect text direction
  icukit bidi detect -t 'Hello שלום'

  # Check for bidi controls (security)
  icukit bidi detect -t $'hello\u200fworld'

  # Strip bidi controls from text
  echo 'suspicious text' | icukit bidi strip

  # List all bidi control characters
  icukit bidi list

### `icukit bidi check` (aliases: c, clean, s, strip)

**Options:**

- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)

### `icukit bidi detect` (aliases: d, info)

**Options:**

- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit bidi help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit bidi list` (aliases: l, ls)

**Options:**

- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

## `icukit break`

Break text into linguistic units using ICU's BreakIterator.

Supports locale-aware segmentation for sentences, words, line breaks,
and grapheme clusters (user-perceived characters).

Examples:
  # Break into sentences
  echo 'Hello world. How are you?' | icukit break sentences

  # Break into words
  icukit break words -t 'Hello, world!'

  # Break into words, skipping punctuation
  icukit break words --skip-punctuation -t 'Hello, world!'

  # Use Japanese locale for word breaking
  icukit break words --locale ja -t 'こんにちは世界'

  # Break into grapheme clusters (handles emoji correctly)
  icukit break graphemes -t '👨‍👩‍👧‍👦'

  # Tokenize sentences (sentences then words)
  icukit break tokenize -t 'Hello world. How are you?'

  # Emit one word object per line
  icukit break words --jsonl -t 'Hello, world!'

  # Show the standard ICU word rules to start a tailoring from
  icukit break rules --kind word

  # Segment with a custom RBBI rule file
  icukit break custom -r my.rules -t 'See Fig. 5 now'

### `icukit break custom` (aliases: cust)

Segment text with a caller-supplied ICU RBBI rule set rather than a locale's standard iterator. Segment types come only from --status-type, since rule statuses are defined by the rule set, not by ICU. Because the rule set determines the boundaries, --provenance adds a rules_sha256 digest of it to the version stamp; the four standard version keys alone do not identify a custom rule set.

**Options:**

- `-r, --rules`: ICU RBBI rule file to segment with
- `--status-type`: Map numeric rule status N to type name NAME (repeatable)
- `--spans`: Output structured spans (JSON includes text, compatibility start/end, explicit code-point, UTF-8 byte, UTF-16 code-unit offsets, types, and statuses; TSV shows explicitly named offsets) (default: `False`)
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)
- `--jsonl`: One JSON object per line: one segment per line (a full span object with --spans); takes precedence over --json (default: `False`)
- `--provenance`: Wrap JSON output with ICU, Unicode, PyICU, and icukit versions (default: `False`)

### `icukit break graphemes` (aliases: c, chars, g)

**Options:**

- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `--show-codepoints, -c`: Show Unicode codepoints for each grapheme (default: `False`)
- `--spans`: Output structured spans (JSON includes text, compatibility start/end, explicit code-point, UTF-8 byte, UTF-16 code-unit offsets, types, and statuses; TSV shows explicitly named offsets) (default: `False`)
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)
- `--jsonl`: One JSON object per line: one grapheme cluster per line (a full span object with --spans); takes precedence over --json (default: `False`)
- `--provenance`: Wrap JSON output with ICU, Unicode, PyICU, and icukit versions (default: `False`)

### `icukit break help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit break lines` (aliases: l, line)

**Options:**

- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `--spans`: Output structured spans (JSON includes text, compatibility start/end, explicit code-point, UTF-8 byte, UTF-16 code-unit offsets, types, and statuses; TSV shows explicitly named offsets, plus the break_type at each span's end boundary) (default: `False`)
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)
- `--jsonl`: One JSON object per line: one line segment per line (a full span object with --spans); takes precedence over --json (default: `False`)
- `--provenance`: Wrap JSON output with ICU, Unicode, PyICU, and icukit versions (default: `False`)

### `icukit break rules` (aliases: r, rule)

Show ICU's standard root rule source as a tailoring base. Locale dictionary and keyword behavior, including CJK dictionary breaking and lw= line options, is not represented, so recompiling the text may not faithfully clone the locale iterator.

**Options:**

- `-k, --kind`: Iterator kind (default: word) (default: `word`)
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `--jsonl`: One JSON object per line: a single rule-set record; takes precedence over --json (default: `False`)
- `--provenance`: Wrap JSON output with ICU, Unicode, PyICU, and icukit versions (default: `False`)

### `icukit break sentences` (aliases: s, sent)

**Options:**

- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `--spans`: Output structured spans (JSON includes text, compatibility start/end, explicit code-point, UTF-8 byte, UTF-16 code-unit offsets, types, and statuses; TSV shows explicitly named offsets) (default: `False`)
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)
- `--jsonl`: One JSON object per line: one sentence per line (a full span object with --spans); takes precedence over --json (default: `False`)
- `--provenance`: Wrap JSON output with ICU, Unicode, PyICU, and icukit versions (default: `False`)

### `icukit break tokenize` (aliases: t, tok)

**Options:**

- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `--spans`: Output structured spans (JSON includes text, compatibility start/end, explicit code-point, UTF-8 byte, UTF-16 code-unit offsets, types, and statuses; TSV shows explicitly named offsets) (default: `False`)
- `--skip-punctuation, -p`: Skip punctuation tokens (default: `False`)
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)
- `--jsonl`: One JSON object per line: one token per line, each with a 1-based sentence number; takes precedence over --json (default: `False`)
- `--provenance`: Wrap JSON output with ICU, Unicode, PyICU, and icukit versions (default: `False`)

### `icukit break words` (aliases: w, word)

**Options:**

- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `--spans`: Output structured spans (JSON includes text, compatibility start/end, explicit code-point, UTF-8 byte, UTF-16 code-unit offsets, types, and statuses; TSV shows explicitly named offsets) (default: `False`)
- `--skip-punctuation, -p`: Skip punctuation tokens (default: `False`)
- `--include-whitespace`: Include whitespace tokens (excluded by default) (default: `False`)
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)
- `--jsonl`: One JSON object per line: one word per line (a full span object with --spans); takes precedence over --json (default: `False`)
- `--provenance`: Wrap JSON output with ICU, Unicode, PyICU, and icukit versions (default: `False`)

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
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit calendar list` (aliases: l, ls)

**Options:**

- `-s, --short`: Show only calendar type names (default: `False`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

## `icukit collate` (aliases: col)

Sort and compare strings using ICU's locale-aware collation.

Different languages have different sorting rules. For example, Swedish
sorts 'o' after 'z', while German sorts 'o' with 'o'.

Strength levels control how strings are compared:
  primary    - Base letters only (a=A=a)
  secondary  - Base + accents (a=A, a!=a)
  tertiary   - Base + accents + case (default)
  quaternary - Tertiary + punctuation
  identical  - Bit-for-bit comparison

Examples:
  # Sort lines from stdin
  echo -e 'cafe\ncafe\nCafe' | icukit collate sort

  # Sort with Swedish rules (o after z)
  echo -e 'o\no\nz' | icukit collate sort --locale sv_SE

  # Sort ignoring accents
  icukit collate sort --strength primary < words.txt

  # Compare two strings
  icukit collate compare 'cafe' 'cafe'

  # List collation types
  icukit collate list types

  # Machine-readable output (every subcommand takes --json)
  icukit collate compare 'cafe' 'cafe' --json

### `icukit collate compare` (aliases: c, cmp)

**Options:**

- `string_a`: First string
- `string_b`: Second string
- `-l, --locale`: Locale for comparison (default: en_US) (default: `en_US`)
- `--strength, -s`: Collation strength
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit collate help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit collate info` (aliases: i)

**Options:**

- `locale`: Locale to get collator info for (default: en_US) (default: `en_US`)
- `--extended, -x`: Include extended attributes (default: `False`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit collate list` (aliases: l, ls)

**Options:**

- `what`: What to list (default: types) (default: `types`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit collate sort` (aliases: s)

**Options:**

- `-l, --locale`: Locale for sorting rules (default: en_US) (default: `en_US`)
- `--reverse, -r`: Sort in descending order (default: `False`)
- `--unique, -u`: Remove duplicate lines (default: `False`)
- `--strength, -s`: Collation strength (default: tertiary)
- `--case-first`: Sort uppercase or lowercase first
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

## `icukit compact`

Format large numbers with locale-appropriate abbreviations.

Styles:
  SHORT - "1.2M", "3.5K" (default)
  LONG  - "1.2 million", "3.5 thousand"

Examples:
  # Basic usage
  icukit compact 1234567
  # → 1.2M

  icukit compact 1234567 --style LONG
  # → 1.2 million

  # German locale
  icukit compact 1234567 --locale de_DE
  # → 1,2 Mio.

  icukit compact 1000000000 --locale de_DE
  # → 1 Mrd.

  # Japanese (uses 万=10000, not K=1000)
  icukit compact 12345 --locale ja_JP
  # → 1.2万

  # Multiple numbers
  icukit compact 1000 10000 100000 1000000
  # → 1K  10K  100K  1M

  # Financial display
  icukit compact 1500000000 --style LONG --locale en_US
  # → 1.5 billion

**Options:**

- `numbers`: Number(s) to format
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-s, --style`: Format style (default: SHORT) (default: `SHORT`)
- `--separator`: Separator for multiple numbers (default: tab) (default: `	`)

## `icukit confusable` (aliases: homoglyph, spoof)

Detect visually confusable strings using ICU's SpoofChecker.

Useful for security applications to detect phishing attempts where
attackers use lookalike characters (e.g., Cyrillic 'а' vs Latin 'a').

Examples:
  # Check if two strings are confusable
  icukit spoof compare 'paypal' 'pаypal'

  # Get skeleton form (normalized for comparison)
  icukit spoof skeleton 'pаypal'

  # Check a string for suspicious characters
  icukit spoof check 'pаypal'

  # Detailed confusability info
  icukit spoof info 'paypal' 'pаypal' --json

### `icukit confusable check` (aliases: chk)

**Options:**

- `text`: Text to check
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit confusable compare` (aliases: c, cmp)

**Options:**

- `string1`: First string
- `string2`: Second string

### `icukit confusable help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit confusable info` (aliases: i)

**Options:**

- `string1`: First string
- `string2`: Second string
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit confusable skeleton` (aliases: s, skel)

**Options:**

- `text`: Text to get skeleton for

## `icukit datetime`

Format dates and times according to locale conventions.

Styles:
  FULL   - Monday, January 15, 2024 at 3:45:30 PM Eastern Standard Time
  LONG   - January 15, 2024 at 3:45:30 PM EST
  MEDIUM - Jan 15, 2024, 3:45:30 PM (default)
  SHORT  - 1/15/24, 3:45 PM

Examples:
  # Format current date/time
  icukit datetime format
  icukit datetime format --style SHORT

  # Format with custom pattern
  icukit datetime format --pattern 'EEEE, MMMM d, yyyy'

  # Format specific date
  icukit datetime format '2024-01-15T14:30:00' --locale de_DE

  # Different calendar systems
  icukit datetime format '2024-01-15' --calendar hebrew
  icukit datetime format '2024-01-15' --calendar islamic
  icukit datetime format '2024-01-15' --calendar buddhist

  # Relative time
  icukit datetime relative -1
  icukit datetime relative --hours 2

  # Date interval
  icukit datetime interval 2024-01-15 2024-01-20

  # Parse date string
  icukit datetime parse '1/15/24'
  icukit datetime parse '1/15/24' --json

  # List patterns and calendars
  icukit datetime patterns
  icukit datetime calendars

  # Localized date symbols
  icukit datetime months --locale fr_FR
  icukit datetime months --locale de_DE --width abbreviated
  icukit datetime weekdays --locale ja_JP
  icukit datetime eras --locale en_US
  icukit datetime ampm --locale zh_CN
  icukit datetime symbols --locale ar_SA --json

### `icukit datetime calendars` (aliases: cal)

**Options:**

- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit datetime eras` (aliases: era)

**Options:**

- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-w, --width`: Name width: wide (Before Christ) or abbreviated (BC) (default: `WIDE`)
- `-c, --calendar`: Calendar system
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit datetime format` (aliases: f, fmt)

**Options:**

- `datetime`: Date/time to format (ISO format, default: now)
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-s, --style`: Format style for both date and time
- `--date-style`: Date style (NONE for time-only)
- `--time-style`: Time style (NONE for date-only)
- `-p, --pattern`: Custom ICU pattern (e.g., 'yyyy-MM-dd HH:mm')
- `-c, --calendar`: Calendar system (gregorian, buddhist, hebrew, islamic, japanese, etc.)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit datetime help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit datetime interval` (aliases: i, int)

**Options:**

- `start`: Start date (ISO format)
- `end`: End date (ISO format)
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-k, --skeleton`: Format skeleton (default: yMMMd) (default: `yMMMd`)
- `-c, --calendar`: Calendar system
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit datetime months` (aliases: mon)

**Options:**

- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-w, --width`: Name width: wide (January) or abbreviated (Jan) (default: `WIDE`)
- `-c, --calendar`: Calendar system (gregorian, hebrew, islamic, etc.)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit datetime parse` (aliases: p)

**Options:**

- `text`: Date/time string to parse
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-p, --pattern`: Expected pattern (tries common formats if not given)
- `-c, --calendar`: Calendar system
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit datetime patterns` (aliases: pat)

**Options:**

- `-l, --locale`: Locale for examples (default: en_US) (default: `en_US`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit datetime relative` (aliases: r, rel)

**Options:**

- `offset`: Day offset (negative for past) (default: `0`)
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `--hours`: Hour offset (default: `0`)
- `--minutes`: Minute offset (default: `0`)
- `--seconds`: Second offset (default: `0`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit datetime symbols` (aliases: am, ampm, sym)

**Options:**

- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-c, --calendar`: Calendar system
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit datetime weekdays` (aliases: days, wd)

**Options:**

- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-w, --width`: Name width: wide (Sunday) or abbreviated (Sun) (default: `WIDE`)
- `-c, --calendar`: Calendar system
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

## `icukit detect`

Recognize typed values in running text. Offsets are half-open Unicode code-point
indices. The default set covers dates, date intervals, compact numbers, relative
dates, scientific numbers, spellout numbers, abbreviations, decimals, and percents.
Currencies and measures require explicit --currency and --measure options.

Overlapping candidates for a span are expected: recognition deposits a candidate
forest, and downstream consumers perform disambiguation.

**Options:**

- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `--currency`: Add an ISO currency (default: `[]`)
- `--measure`: Add an ICU measure unit (default: `[]`)
- `--skeleton`: Add a date skeleton (default: `[]`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)
- `--jsonl`: One JSON object per line (one detection per line) (default: `False`)

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

- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit discover help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit discover search` (aliases: find, s)

**Options:**

- `query`: Search query
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

## `icukit displayname`

Get localized display names for languages, scripts, regions, currencies,
and locales.

Examples:
  # Language names
  icukit displayname language zh
  # → Chinese

  icukit displayname language zh --display de
  # → Chinesisch

  icukit displayname language zh --display ja
  # → 中国語

  # Script names
  icukit displayname script Cyrl
  # → Cyrillic

  icukit displayname script Hans --display zh
  # → 简体中文

  # Region/country names
  icukit displayname region JP
  # → Japan

  icukit displayname region JP --display ja
  # → 日本

  # Currency names
  icukit displayname currency USD
  # → US Dollar

  icukit displayname currency USD --display ja
  # → 米ドル

  # Currency symbols
  icukit displayname symbol USD
  # → $

  icukit displayname symbol EUR
  # → €

  # Full locale names
  icukit displayname locale zh_Hans_CN
  # → Chinese (Simplified, China)

  icukit displayname locale zh_Hans_CN --display de
  # → Chinesisch (Vereinfacht, China)

### `icukit displayname country` (aliases: r, reg, region)

**Options:**

- `code`: ISO 3166-1 alpha-2 region code (e.g., US, JP, DE)
- `-d, --display`: Display locale (default: en_US) (default: `en_US`)

### `icukit displayname currency` (aliases: c, cur, sym, symbol)

**Options:**

- `code`: ISO 4217 currency code (e.g., USD, EUR, JPY)
- `-d, --display`: Display locale (default: en_US) (default: `en_US`)

### `icukit displayname help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit displayname language` (aliases: l, lang)

**Options:**

- `code`: ISO 639 language code (e.g., en, zh, ar)
- `-d, --display`: Display locale (default: en_US) (default: `en_US`)

### `icukit displayname locale` (aliases: loc)

**Options:**

- `code`: Locale code (e.g., en_US, zh_Hans_CN)
- `-d, --display`: Display locale (default: en_US) (default: `en_US`)

### `icukit displayname script` (aliases: s, scr)

**Options:**

- `code`: ISO 15924 script code (e.g., Latn, Cyrl, Hans)
- `-d, --display`: Display locale (default: en_US) (default: `en_US`)

## `icukit duration`

Format time durations with proper locale conventions.

Width Styles:
  WIDE   - "2 hours, 30 minutes, 15 seconds"
  SHORT  - "2 hr, 30 min, 15 sec"
  NARROW - "2h 30m 15s"

Input Formats:
  - Total seconds: 3661
  - ISO 8601: P2DT3H30M (2 days, 3 hours, 30 minutes)
  - Components: --hours 2 --minutes 30

Examples:
  # Format from total seconds
  icukit duration format 3661
  # → 1 hour, 1 minute, 1 second

  icukit duration format 3661 --width SHORT
  # → 1 hr, 1 min, 1 sec

  icukit duration format 3661 --locale de_DE
  # → 1 Stunde, 1 Minute und 1 Sekunde

  # Format with individual components
  icukit duration format --hours 2 --minutes 30
  # → 2 hours, 30 minutes

  # Format ISO 8601 duration
  icukit duration iso P2DT3H30M
  # → 2 days, 3 hours, 30 minutes

  icukit duration iso PT1H30M15S --locale ja_JP
  # → 1時間30分15秒

  # Parse ISO 8601 (show components)
  icukit duration parse P2DT3H30M
  # → days=2, hours=3, minutes=30

### `icukit duration format` (aliases: f, fmt)

**Options:**

- `seconds`: Total seconds (optional if using component flags)
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-w, --width`: Width style (default: WIDE) (default: `WIDE`)
- `--years`: Years (default: `0`)
- `--months`: Months (default: `0`)
- `--weeks`: Weeks (default: `0`)
- `--days`: Days (default: `0`)
- `--hours`: Hours (default: `0`)
- `--minutes`: Minutes (default: `0`)

### `icukit duration help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit duration iso` (aliases: i)

**Options:**

- `duration`: ISO 8601 duration string (e.g., P2DT3H30M)
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-w, --width`: Width style (default: WIDE) (default: `WIDE`)

### `icukit duration parse` (aliases: p)

**Options:**

- `duration`: ISO 8601 duration string to parse
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

## `icukit help`

Show help information for icukit commands

**Options:**

- `command`: Command to show help for

## `icukit listfmt`

Format lists of items with locale-appropriate conjunctions and separators.

Styles:
  and   - "a, b, and c" (default)
  or    - "a, b, or c"
  unit  - "a, b, c" (no conjunction)

Examples:
  # Basic usage (comma-separated input)
  icukit listfmt 'apples,oranges,bananas'
  # → apples, oranges, and bananas

  # With "or" style
  icukit listfmt 'red,green,blue' --style or
  # → red, green, or blue

  # German (no Oxford comma)
  icukit listfmt 'Äpfel,Orangen,Bananen' --locale de
  # → Äpfel, Orangen und Bananen

  # Two items (special case)
  icukit listfmt 'yes,no' --style or
  # → yes or no

  # Custom delimiter
  icukit listfmt 'apples|oranges|bananas' --delimiter '|'

**Options:**

- `items`: Items to format (comma-separated, or use --delimiter)
- `--style, -s`: List style (default: and) (default: `and`)
- `-l, --locale`: Locale for formatting (default: en_US) (default: `en_US`)
- `--delimiter, -d`: Input delimiter (default: comma) (default: `,`)

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

  # Compact numbers (1.2M, 3.5K)
  icukit locale compact 1234567
  icukit locale compact 1234567 --style LONG

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

  # Number formatting symbols
  icukit locale symbols --locale de_DE
  icukit locale symbols --locale ar_SA --json

### `icukit locale attributes` (aliases: a, attrs)

**Options:**

- `locale`: Locale identifier (e.g., en_US)
- `--display, -d`: Locale for display names (default: en) (default: `en`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit locale canonicalize` (aliases: c, canon)

**Options:**

- `locale`: Locale string to canonicalize

### `icukit locale compact` (aliases: comp)

**Options:**

- `value`: Number to format in compact form
- `-l, --locale`: Locale for formatting (default: en_US) (default: `en_US`)
- `--style, -s`: Format style (default: SHORT) (default: `SHORT`)

### `icukit locale compare` (aliases: cmp)

**Options:**

- `string_a`: First string
- `string_b`: Second string
- `-l, --locale`: Locale for comparison (default: en_US) (default: `en_US`)
- `--strength, -s`: Collation strength

### `icukit locale display` (aliases: n, name)

**Options:**

- `locale`: Locale to get display name for
- `--in, -i`: Locale for the display name (default: en) (default: `en`)

### `icukit locale exemplars` (aliases: chars, ex)

**Options:**

- `locale`: Locale code (default: en_US) (default: `en_US`)
- `--type, -t`: Exemplar type: standard, auxiliary, index, punctuation (default: standard) (default: `standard`)
- `--all, -a`: Show all exemplar types (default: `False`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit locale expand` (aliases: e, likely)

**Options:**

- `locale`: Minimal locale to expand (e.g., zh, sr)

### `icukit locale format` (aliases: f, fmt)

**Options:**

- `value`: Number to format
- `-l, --locale`: Locale for formatting (default: en_US) (default: `en_US`)
- `--type, -t`: Format type (default: number) (default: `number`)
- `--currency, -c`: Currency code for currency format (e.g., EUR)

### `icukit locale help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit locale info` (aliases: i)

**Options:**

- `locales`: Locale identifier(s) (e.g., en_US)
- `--display, -d`: Locale for display names (default: en) (default: `en`)
- `-x, --extended`: Include extended attributes (calendar, currency, RTL, etc.) (default: `False`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit locale list` (aliases: l, ls)

**Options:**

- `type`: What to list (default: locales) (default: `locales`)
- `-s, --short`: Show only IDs/codes (default: `False`)
- `--display, -d`: Locale for display names (default: en) (default: `en`)
- `--language`: Filter by language code (e.g., en, es)
- `--region`: Filter by region code (e.g., US, MX)
- `--script`: Filter by script code (e.g., Latn, Hans)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit locale minimize` (aliases: m, min)

**Options:**

- `locale`: Full locale to minimize

### `icukit locale ordinal` (aliases: ord)

**Options:**

- `value`: Integer to format as ordinal
- `-l, --locale`: Locale for formatting (default: en_US) (default: `en_US`)

### `icukit locale parse` (aliases: p)

**Options:**

- `locale`: Locale string to parse
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit locale sort` (aliases: s)

**Options:**

- `-l, --locale`: Locale for sorting rules (default: en_US) (default: `en_US`)
- `--reverse, -r`: Sort in descending order (default: `False`)
- `--unique, -u`: Remove duplicate lines (default: `False`)
- `--strength, -s`: Collation strength (default: tertiary)
- `--case-first`: Sort uppercase or lowercase first
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)

### `icukit locale spellout` (aliases: spell, words)

**Options:**

- `value`: Integer to spell out
- `-l, --locale`: Locale for spelling (default: en_US) (default: `en_US`)

### `icukit locale symbols` (aliases: numsym, sym)

**Options:**

- `locale`: Locale code (default: en_US) (default: `en_US`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit locale validate` (aliases: check, v)

**Options:**

- `locale`: Locale string to validate

## `icukit measure`

Format measurements with locale-appropriate unit names.

Width styles:
  WIDE   - "5.5 kilometers" (full unit names)
  SHORT  - "5.5 km" (abbreviated)
  NARROW - "5.5km" (minimal)

Examples:
  # Format a measurement (abbreviations work: km, mi, C, F, etc.)
  icukit measure format 5.5 kilometer
  icukit measure format 5.5 km
  icukit measure format 100 fahrenheit --width SHORT

  # Convert with the limited built-in explicit factors
  icukit measure convert 10 km mi
  icukit measure convert 100 C F
  icukit measure convert 1 lb kg

  # Compound measurements
  icukit measure sequence '5 foot, 10 inch'
  icukit measure sequence '1 hour, 30 minute'

  # Format for locale usage (converts to preferred units)
  icukit measure usage 100 km --usage road --locale en_US

  # Unit info and compatibility
  icukit measure info kilometer
  icukit measure check km mi

  # Format a range
  icukit measure range 5 10 kilometer

  # List unit types and units
  icukit measure types
  icukit measure units --type length

  # Machine-readable output (every subcommand takes --json)
  icukit measure convert 10 km mi --json

### `icukit measure compat` (aliases: check)

**Options:**

- `from_unit`: Source unit
- `to_unit`: Target unit
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit measure compound` (aliases: seq, sequence)

**Options:**

- `measures`: Comma-separated measures (e.g., '5 foot, 10 inch')
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-w, --width`: Width style (default: WIDE) (default: `WIDE`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit measure convert` (aliases: c, conv)

**Options:**

- `value`: Value to convert
- `from_unit`: Source unit (e.g., kilometer)
- `to_unit`: Target unit (e.g., mile)
- `-l, --locale`: Locale for formatted output (default: en_US) (default: `en_US`)
- `-w, --width`: Width style for formatted output (default: SHORT) (default: `SHORT`)
- `-r, --raw`: Output raw number only (no formatting) (default: `False`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit measure format` (aliases: f, fmt)

**Options:**

- `value`: Numeric value
- `unit`: Unit name (e.g., kilometer, fahrenheit)
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-w, --width`: Width style (default: WIDE) (default: `WIDE`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit measure help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit measure info` (aliases: i)

**Options:**

- `unit`: Unit name or abbreviation
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit measure range` (aliases: r)

**Options:**

- `low`: Low value
- `high`: High value
- `unit`: Unit name
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-w, --width`: Width style (default: WIDE) (default: `WIDE`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit measure types` (aliases: t)

**Options:**

- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit measure units` (aliases: list, u)

**Options:**

- `-t, --type`: Filter by unit type (e.g., length, mass, temperature)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit measure usage` (aliases: use)

**Options:**

- `value`: Numeric value
- `unit`: Unit name or abbreviation
- `-u, --usage`: Usage context (default, road, person-height, weather, etc.) (default: `default`)
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-w, --width`: Width style (default: SHORT) (default: `SHORT`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

## `icukit message` (aliases: msg)

Format messages using ICU MessageFormat syntax.

Supports placeholders, plurals, selects, and number/date formatting.

Pattern syntax:
  {name}                              Simple placeholder
  {count, number}                     Number formatting
  {price, number, currency}           Currency formatting
  {date, date, short}                 Date formatting
  {count, plural, one {# item} other {# items}}   Plural rules
  {gender, select, male {He} female {She} other {They}}  Select

Examples:
  # Simple substitution
  icukit message format 'Hello, {name}!' --arg name=World

  # Plural rules (locale-aware)
  icukit message format '{count, plural, one {# item} other {# items}}' --arg count=5
  icukit message format '{count, plural, one {# item} other {# items}}' --arg count=1

  # Select (gender, etc.)
  icukit message format '{g, select, male {He} female {She} other {They}} liked it' --arg g=female

  # Number formatting
  icukit message format 'Total: {n, number, currency}' --arg n=1234.56 --locale de_DE

  # Multiple arguments
  icukit message format '{name} has {count, plural, one {# cat} other {# cats}}' \
      --arg name=Alice --arg count=3

  # Russian plurals (1 кот, 2 кота, 5 котов)
  icukit message format '{n, plural, one {# кот} few {# кота} many {# котов} other {# кота}}' \
      --arg n=5 --locale ru

### `icukit message examples` (aliases: ex)


### `icukit message format` (aliases: f, fmt)

**Options:**

- `pattern`: ICU message format pattern
- `-a, --arg`: Argument in name=value format (can be repeated)
- `-l, --locale`: Locale for formatting (default: en_US) (default: `en_US`)

### `icukit message help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

## `icukit parse`

Parse locale-formatted numbers, currencies, and percentages back to values.

This handles locale-specific conventions like:
  - Decimal separators (. vs ,)
  - Grouping separators (, vs . vs space)
  - Currency symbols and positions
  - Percent signs

Examples:
  # Parse numbers
  icukit parse number '1,234.56' --locale en_US
  # → 1234.56

  icukit parse number '1.234,56' --locale de_DE
  # → 1234.56

  icukit parse number '1 234,56' --locale fr_FR
  # → 1234.56

  # Parse currencies
  icukit parse currency '$1,234.56' --locale en_US
  # → {"value": 1234.56, "currency": "USD"}

  icukit parse currency '€1.234,56' --locale de_DE
  # → {"value": 1234.56, "currency": "EUR"}

  # Parse percentages
  icukit parse percent '50%' --locale en_US
  # → 0.5

  icukit parse percent '125%'
  # → 1.25

### `icukit parse currency` (aliases: c, cur)

**Options:**

- `text`: Currency string to parse
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `--strict`: Strict parsing (no lenient mode) (default: `False`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit parse help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit parse number` (aliases: n, num)

**Options:**

- `text`: Number string to parse
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `--strict`: Strict parsing (no lenient mode) (default: `False`)

### `icukit parse percent` (aliases: p, pct)

**Options:**

- `text`: Percentage string to parse
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `--strict`: Strict parsing (no lenient mode) (default: `False`)

## `icukit plural`

Determine which plural category a number falls into for a given locale.

Plural Categories:
  zero  - For 0 in some languages (Arabic)
  one   - Singular form (1 in English, complex rules in other languages)
  two   - Dual form (Arabic, Hebrew, Slovenian)
  few   - Paucal form (2-4 in Slavic languages)
  many  - "Many" category (5+ in Slavic, 11-99 in Maltese)
  other - General plural (default fallback)

Examples:
  # Get plural category for a number
  icukit plural select 1 --locale en
  # → one

  icukit plural select 2 --locale ru
  # → few

  icukit plural select 5 --locale ru
  # → many

  # Get ordinal category (1st, 2nd, 3rd...)
  icukit plural ordinal 1 --locale en
  # → one (for "1st")

  icukit plural ordinal 2 --locale en
  # → two (for "2nd")

  # List categories used by a locale
  icukit plural categories --locale en
  icukit plural categories --locale ar
  icukit plural categories --locale ru --type ordinal

  # Show detailed info about locale's plural rules
  icukit plural info --locale ru

### `icukit plural categories` (aliases: c, cat, list)

**Options:**

- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-t, --type`: Plural type (default: cardinal) (default: `cardinal`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit plural help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit plural info` (aliases: i)

**Options:**

- `-l, --locale`: Locale (default: en_US) (default: `en_US`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit plural ordinal` (aliases: get, o, ord, s, select)

**Options:**

- `number`: Number to categorize
- `-l, --locale`: Locale (default: en_US) (default: `en_US`)

## `icukit punycode` (aliases: idn, idna)

Convert between Unicode domain names and ASCII (Punycode) encoding.

Internationalized domain names (IDN) allow non-ASCII characters in
domain names. IDNA encoding converts them to ASCII-compatible format.

Examples:
  # Encode Unicode domain to Punycode
  icukit idna encode 'münchen.de'
  # Output: xn--mnchen-3ya.de

  # Decode Punycode to Unicode
  icukit idna decode 'xn--mnchen-3ya.de'
  # Output: münchen.de

  # Process multiple domains
  echo -e 'münchen.de\n例え.jp' | icukit idna encode

  # Machine-readable output: always a list of {input, output}, at any size
  echo -e 'münchen.de\n例え.jp' | icukit idna encode --json

### `icukit punycode help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit punycode to-ascii` (aliases: ascii, e, encode)

**Options:**

- `domain`: Unicode domain to encode (or read from stdin)
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit punycode to-unicode` (aliases: d, decode, unicode)

**Options:**

- `domain`: ASCII domain to decode (or read from stdin)
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

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
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
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
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit regex script` (aliases: expr, s, sed)

**Options:**

- `expression`: Substitution expression: s/pattern/replacement/[gi] (delimiter can be any char)
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
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
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
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
  icukit region list types

### `icukit region contains` (aliases: c, in)

**Options:**

- `code`: Region code to get contained regions for
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit region help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit region info` (aliases: i)

**Options:**

- `code`: Region code (e.g., US, FR, 001)
- `-x, --extended`: Include extended attributes (contained_regions) (default: `False`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit region list` (aliases: l, ls)

**Options:**

- `what`: What to list (default: regions) (default: `regions`)
- `--type, -t`: Region type filter (default: territory) (default: `territory`)
- `-s, --short`: Show only region codes (default: `False`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
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
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit script help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit script info` (aliases: i)

**Options:**

- `script`: Script name (e.g., Greek, Latin, Han)
- `-x, --extended`: Include extended attributes (sample_char) (default: `False`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit script list` (aliases: l, ls)

**Options:**

- `--cased`: Only cased scripts (default: `False`)
- `--rtl`: Only RTL scripts (default: `False`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit script rtl` (aliases: r)

**Options:**

- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)

## `icukit search` (aliases: find)

Search text using ICU's locale-aware collation rules.

Unlike simple string matching, locale-aware search can find matches
that are linguistically equivalent. For example, with primary strength,
"cafe" matches "café" and "CAFE".

Strength levels control matching:
  primary    - Base letters only (cafe=café=CAFE)
  secondary  - Base + accents (cafe=CAFE, but café≠cafe)
  tertiary   - Base + accents + case (exact match, default)
  quaternary - Tertiary + punctuation differences
  identical  - Bit-for-bit identical

Examples:
  # Find all matches (case-insensitive)
  echo 'The café and CAFE' | icukit search find cafe --strength primary

  # Count matches
  icukit search count cafe -t 'café, Cafe, CAFE' -s primary

  # Replace matches
  echo 'Visit the café' | icukit search replace cafe tea -s primary

  # Search with French locale
  icukit search find cafe -t 'Un café au lait' -l fr_FR -s primary

### `icukit search contains` (aliases: c, cnt, count, has)

**Options:**

- `pattern`: Pattern to search for
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-l, --locale`: Locale for collation rules (default: en_US) (default: `en_US`)
- `--strength, -s`: Collation strength (default: tertiary/exact)

### `icukit search first` (aliases: 1, all, f, find)

**Options:**

- `pattern`: Pattern to search for
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-l, --locale`: Locale for collation rules (default: en_US) (default: `en_US`)
- `--strength, -s`: Collation strength (default: tertiary/exact)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit search help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit search replace` (aliases: r, sub)

**Options:**

- `pattern`: Pattern to search for
- `replacement`: Replacement string
- `--max, -n`: Maximum replacements (0=unlimited) (default: `0`)
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-l, --locale`: Locale for collation rules (default: en_US) (default: `en_US`)
- `--strength, -s`: Collation strength (default: tertiary/exact)

## `icukit sort`

Sort lines using ICU's locale-aware collation.

Different languages have different sorting rules. For example, Swedish
sorts 'o' after 'z', while German sorts 'o' with 'o'.

Examples:
  # Sort lines from stdin
  echo -e 'cafe\ncafe\nCafe' | icukit sort

  # Sort with Swedish rules (o after z)
  echo -e 'o\no\nz' | icukit sort --locale sv_SE

  # Sort ignoring accents
  icukit sort --strength primary < words.txt

  # Sort with uppercase first
  icukit sort --case-first upper < words.txt

**Options:**

- `-l, --locale`: Locale for sorting rules (default: en_US) (default: `en_US`)
- `--reverse, -r`: Sort in descending order (default: `False`)
- `--unique, -u`: Remove duplicate lines (default: `False`)
- `--strength, -s`: Collation strength (default: tertiary)
- `--case-first`: Sort uppercase or lowercase first
- `-t, --text`: Process TEXT directly
- `files`: Files to process (default: stdin)

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
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit timezone help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit timezone info` (aliases: i)

**Options:**

- `timezone`: Timezone ID (e.g., America/New_York)
- `-x, --extended`: Include extended attributes (region, windows_id, equivalent_ids) (default: `False`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit timezone list` (aliases: l, ls)

**Options:**

- `--country, -c`: Filter by country code (e.g., US, DE, JP)
- `-s, --short`: Show only timezone IDs (default: `False`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
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
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)

### `icukit transliterate help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit transliterate inline` (aliases: expr, s, script)

**Options:**

- `expression`: ICU transform expression (e.g., "NFD; [:Nonspacing Mark:] Remove; NFC")
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit transliterate list` (aliases: l, ls)

**Options:**

- `--name`: Filter by transliterator name (regex supported)
- `--from`: Filter by source script
- `--to`: Filter by target script
- `--scripts`: Group by source scripts (default: `False`)
- `-s, --short`: Show only IDs (default: `False`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit transliterate name` (aliases: n)

**Options:**

- `transliterators`: Transliterator name(s) - comma-separated or regex
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit transliterate reverse` (aliases: f, from)

**Options:**

- `transliterators`: Transliterator name(s) for reverse
- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
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

  # Get character info using escape sequences
  icukit unicode info -t '\u03B1'      # Greek alpha
  icukit unicode info -t 'U+1F600'      # Grinning face emoji
  icukit unicode info -t '\U0001F600'  # Same, 8-digit form

  # Get full character info
  icukit unicode info -t 'α' --json

  # List Unicode categories, blocks, or normalization forms
  icukit unicode list
  icukit unicode list categories
  icukit unicode list blocks
  icukit unicode list forms

  # Get characters in a Unicode block
  icukit unicode block 'Basic Latin'
  icukit unicode block 'Greek and Coptic' --json

  # Get characters in a Unicode category
  icukit unicode category Lu
  icukit unicode category Nd --json

  # Convert between escape formats
  icukit unicode encode -t 'α' --format u      # \u03B1
  icukit unicode encode -t 'α' --format U      # \U000003B1
  icukit unicode encode -t 'α' --format x      # \xCE\xB1 (UTF-8 bytes)
  icukit unicode encode -t 'α' --format uplus  # U+03B1
  icukit unicode encode -t '\u03B1' --format char  # α (decode to char)

### `icukit unicode block`

**Options:**

- `name`: Unicode block name (e.g., 'Basic Latin')
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit unicode cat-chars` (aliases: category)

**Options:**

- `code`: Unicode category code (e.g., 'Lu', 'Nd')
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit unicode categories` (aliases: cat, cats, l, list, ls)

**Options:**

- `type`: What to list (default: categories) (default: `categories`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit unicode charname` (aliases: char, i, info, name)

**Options:**

- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
- `-H, --no-header`: Suppress header in TSV output (default: `False`)

### `icukit unicode check` (aliases: c)

**Options:**

- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-f, --form`: Normalization form to check (default: NFC) (default: `NFC`)

### `icukit unicode convert` (aliases: e, enc, encode, escape)

**Options:**

- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-f, --format`: Output format: u (\uXXXX), U (\UXXXXXXXX), x (\xXX UTF-8), uplus (U+XXXX), char (decode to character). Default: uplus (default: `uplus`)

### `icukit unicode help` (aliases: h)

**Options:**

- `help_command`: Subcommand to show help for

### `icukit unicode normalize` (aliases: n, norm)

**Options:**

- `-t, --text`: Process TEXT directly
- `files`: Process FILE(s)
- `-f, --form`: Normalization form (default: NFC) (default: `NFC`)
- `-o, --output`: Output file in UTF-8; atomically replaces an existing file (default: stdout)
- `-j, --json`: Output in JSON format (default: `False`)
