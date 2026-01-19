# icukit API Reference

Version: 0.1.0

## icukit.alpha_index

Alphabetic index buckets for sorted lists using ICU's AlphabeticIndex.

Creates locale-aware A-Z style index buckets for organizing sorted lists
like contacts, glossaries, or directory listings.

Example:
    >>> from icukit import create_index_buckets
    >>> buckets = create_index_buckets(["Alice", "Bob", "Carol", "Zebra"], "en_US")
    >>> buckets
    {'A': ['Alice'], 'B': ['Bob'], 'C': ['Carol'], 'Z': ['Zebra']}

### class `AlphabeticIndex`

Reusable alphabetic index for organizing items into buckets.

Useful when you need to add items incrementally or access
bucket information multiple times.

Example:
    >>> index = AlphabeticIndex("en_US")
    >>> index.add("Alice")
    >>> index.add("Bob")
    >>> index.add("Zebra")
    >>> index.get_buckets()
    {'A': ['Alice'], 'B': ['Bob'], 'Z': ['Zebra']}

#### `AlphabeticIndex(locale: str = 'en_US')`

Create an alphabetic index for the given locale.

Args:
    locale: Locale for bucket labels and sorting.

#### `add(name: str, data: Any = None) -> 'AlphabeticIndex'`

Add an item to the index.

Args:
    name: Name/label for the item.
    data: Optional associated data (not returned by get_buckets).

Returns:
    Self for chaining.

#### `add_many(names: list[str]) -> 'AlphabeticIndex'`

Add multiple items to the index.

Args:
    names: List of names to add.

Returns:
    Self for chaining.

#### `clear() -> 'AlphabeticIndex'`

Clear all records from the index.

Returns:
    Self for chaining.

#### `get_bucket_for(name: str) -> str`

Get the bucket label for a name without adding it.

Args:
    name: Name to look up.

Returns:
    Bucket label.

#### `get_buckets() -> dict[str, list[str]]`

Get all non-empty buckets with their items.

Returns:
    Dict mapping bucket labels to lists of items.

#### `get_labels() -> list[str]`

Get all bucket labels for this locale.

Returns:
    List of bucket label strings.

### `create_index_buckets(items: list[str], locale: str = 'en_US') -> dict[str, list[str]]`

Create alphabetic index buckets for a list of items.

Organizes items into locale-appropriate alphabetic buckets (like A-Z
in English, or あかさたな in Japanese).

Args:
    items: List of strings to organize into buckets.
    locale: Locale for bucket labels and sorting rules.

Returns:
    Dict mapping bucket labels to lists of items in each bucket.

Example:
    >>> create_index_buckets(["Apple", "Banana", "Bob", "Zebra"], "en_US")
    {'A': ['Apple'], 'B': ['Banana', 'Bob'], 'Z': ['Zebra']}

### `get_bucket_for_name(name: str, locale: str = 'en_US') -> str`

Get the bucket label for a given name.

Args:
    name: Name to look up.
    locale: Locale for bucket determination.

Returns:
    Bucket label for the name.

Example:
    >>> get_bucket_for_name("Alice", "en_US")
    'A'
    >>> get_bucket_for_name("山田", "ja_JP")
    'や'

### `get_bucket_labels(locale: str = 'en_US') -> list[str]`

Get the bucket labels for a locale.

Returns the alphabetic index labels used for the given locale
(e.g., A-Z for English, あかさたな for Japanese).

Args:
    locale: Locale code.

Returns:
    List of bucket label strings.

Example:
    >>> get_bucket_labels("en_US")[:5]
    ['A', 'B', 'C', 'D', 'E']
    >>> get_bucket_labels("ja_JP")[:5]
    ['あ', 'か', 'さ', 'た', 'な']

## icukit.bidi

Bidirectional text handling.

ICU's BiDi implementation provides the Unicode Bidirectional Algorithm (UBA)
for handling mixed left-to-right and right-to-left text.

Key Features:
    * Detect text direction (LTR, RTL, mixed)
    * Get paragraph embedding level
    * Strip invisible bidi control characters
    * List bidi control characters

Example:
    >>> from icukit import get_bidi_info, strip_bidi_controls
    >>> get_bidi_info('Hello שלום')
    {'direction': 'mixed', 'base_direction': 'ltr', 'has_rtl': True, 'has_ltr': True}
    >>> strip_bidi_controls('hello\u200fworld')
    'helloworld'

### `get_base_direction(text: str) -> str`

Get the base direction of text using the first strong directional character.

Args:
    text: Text to analyze.

Returns:
    Direction string: 'ltr', 'rtl', or 'neutral' if no strong characters.

Example:
    >>> get_base_direction('Hello')
    'ltr'
    >>> get_base_direction('שלום')
    'rtl'
    >>> get_base_direction('123')
    'neutral'

### `get_bidi_info(text: str) -> dict`

Get bidirectional text information.

Args:
    text: Text to analyze.

Returns:
    Dictionary with:
        - direction: 'ltr', 'rtl', 'mixed', or 'neutral'
        - base_direction: 'ltr', 'rtl', or 'neutral'
        - has_rtl: True if text contains RTL characters
        - has_ltr: True if text contains LTR characters
        - bidi_control_count: Number of bidi control characters

Example:
    >>> get_bidi_info('Hello שלום')
    {'direction': 'mixed', 'base_direction': 'ltr', 'has_rtl': True, ...}

### `has_bidi_controls(text: str) -> bool`

Check if text contains any bidirectional control characters.

Args:
    text: Text to check.

Returns:
    True if text contains bidi controls, False otherwise.

Example:
    >>> has_bidi_controls('hello world')
    False
    >>> has_bidi_controls('hello\u200fworld')
    True

### `list_bidi_controls() -> list[dict]`

List all bidirectional control characters.

Returns:
    List of dicts with char, codepoint, abbrev, and name.

Example:
    >>> controls = list_bidi_controls()
    >>> controls[0]
    {'char': '\u200e', 'codepoint': 'U+200E', 'abbrev': 'LRM', 'name': 'Left-to-Right Mark'}

### `strip_bidi_controls(text: str) -> str`

Remove all bidirectional control characters from text.

Useful for security (preventing bidi-based text spoofing attacks like
CVE-2021-42574 "Trojan Source") and cleaning text for processing.

Args:
    text: Text to clean.

Returns:
    Text with bidi controls removed.

Example:
    >>> strip_bidi_controls('hello\u200fworld')
    'helloworld'
    >>> strip_bidi_controls('a\u202eb\u202cc')
    'abc'

## icukit.breaker

Text segmentation using ICU BreakIterator.

This module provides text segmentation capabilities for breaking text into
sentences, words, lines, or grapheme clusters using ICU's BreakIterator.

Key Features:
    * Locale-aware sentence segmentation
    * Word tokenization with optional punctuation filtering
    * Line break detection
    * Grapheme cluster iteration (user-perceived characters)
    * Memory-efficient iteration over large texts

Example:
    >>> from icukit import break_sentences, break_words
    >>> break_sentences('Hello world. How are you?', 'en')
    ['Hello world. ', 'How are you?']
    >>> break_words('Hello, world!', 'en', skip_punctuation=True)
    ['Hello', 'world']

### class `Breaker`

Text segmentation using ICU BreakIterator.

A versatile text segmentation tool that can break text into sentences,
words, lines, or grapheme clusters based on locale-specific rules.

Example:
    >>> breaker = Breaker('en')
    >>> list(breaker.iter_sentences('Hello. World.'))
    ['Hello. ', 'World.']
    >>> breaker.break_words('Hello, world!', skip_punctuation=True)
    ['Hello', 'world']

#### `Breaker(locale: str = 'en_US')`

Initialize a Breaker instance.

Args:
    locale: Locale code for language-specific rules (e.g., 'en', 'en_US', 'ja').

Raises:
    BreakerError: If the locale is invalid.

#### `break_graphemes(text: str) -> list[str]`

Break text into grapheme clusters (user-perceived characters).

Useful for correctly handling emoji, combining characters, etc.

Args:
    text: The text to segment.

Returns:
    List of grapheme clusters.

Example:
    >>> breaker = Breaker('en')
    >>> breaker.break_graphemes('e\u0301')  # e + combining accent
    ['é']

#### `break_lines(text: str) -> list[str]`

Find line break opportunities in text.

Returns segments where line breaks can occur (for text wrapping).

Args:
    text: The text to analyze.

Returns:
    List of segments at line break boundaries.

#### `break_sentences(text: str, skip_empty: bool = True) -> list[str]`

Break text into sentences.

Args:
    text: The text to segment.
    skip_empty: If True, empty sentences are excluded.

Returns:
    List of sentence strings.

Example:
    >>> breaker = Breaker('en')
    >>> breaker.break_sentences('Hello world. How are you?')
    ['Hello world. ', 'How are you?']

#### `break_words(text: str, skip_whitespace: bool = True, skip_punctuation: bool = False) -> list[str]`

Break text into words.

Args:
    text: The text to tokenize.
    skip_whitespace: If True, whitespace tokens are excluded (default True).
    skip_punctuation: If True, punctuation tokens are excluded.

Returns:
    List of word/token strings.

Example:
    >>> breaker = Breaker('en')
    >>> breaker.break_words('Hello, world!')
    ['Hello', ',', 'world', '!']
    >>> breaker.break_words('Hello, world!', skip_punctuation=True)
    ['Hello', 'world']

#### `iter_graphemes(text: str) -> Iterator[str]`

Iterate over grapheme clusters.

Args:
    text: The text to segment.

Yields:
    Individual grapheme clusters.

#### `iter_lines(text: str) -> Iterator[str]`

Iterate over line break segments.

Args:
    text: The text to analyze.

Yields:
    Segments at line break boundaries.

#### `iter_sentences(text: str, skip_empty: bool = True) -> Iterator[str]`

Iterate over sentences in text.

Memory-efficient sentence iteration.

Args:
    text: The text to segment.
    skip_empty: If True, skip empty sentences.

Yields:
    Individual sentence strings.

#### `iter_words(text: str, skip_whitespace: bool = True, skip_punctuation: bool = False) -> Iterator[str]`

Iterate over words in text.

Args:
    text: The text to tokenize.
    skip_whitespace: If True, skip whitespace tokens.
    skip_punctuation: If True, skip punctuation tokens.

Yields:
    Individual word/token strings.

#### `tokenize_sentences(text: str, skip_whitespace: bool = True, skip_punctuation: bool = False) -> list[list[str]]`

Break text into sentences, then tokenize each sentence.

Args:
    text: The text to process.
    skip_whitespace: If True, skip whitespace tokens.
    skip_punctuation: If True, skip punctuation tokens.

Returns:
    List of sentences, where each sentence is a list of tokens.

Example:
    >>> breaker = Breaker('en')
    >>> breaker.tokenize_sentences('Hello world. How are you?')
    [['Hello', 'world', '.'], ['How', 'are', 'you', '?']]

### `break_graphemes(text: str, locale: str = 'en_US') -> list[str]`

Break text into grapheme clusters.

Args:
    text: The text to segment.
    locale: Locale code for language-specific rules.

Returns:
    List of grapheme clusters.

Example:
    >>> break_graphemes('👨‍👩‍👧‍👦')  # Family emoji
    ['👨‍👩‍👧‍👦']

### `break_lines(text: str, locale: str = 'en_US') -> list[str]`

Find line break opportunities in text.

Args:
    text: The text to analyze.
    locale: Locale code for language-specific rules.

Returns:
    List of segments at line break boundaries.

### `break_sentences(text: str, locale: str = 'en_US', skip_empty: bool = True) -> list[str]`

Break text into sentences.

Convenience function that creates a Breaker for one-off use.

Args:
    text: The text to segment.
    locale: Locale code for language-specific rules.
    skip_empty: If True, empty sentences are excluded.

Returns:
    List of sentence strings.

Example:
    >>> break_sentences('Hello. World.', 'en')
    ['Hello. ', 'World.']

### `break_words(text: str, locale: str = 'en_US', skip_whitespace: bool = True, skip_punctuation: bool = False) -> list[str]`

Break text into words.

Convenience function that creates a Breaker for one-off use.

Args:
    text: The text to tokenize.
    locale: Locale code for language-specific rules.
    skip_whitespace: If True, whitespace tokens are excluded.
    skip_punctuation: If True, punctuation tokens are excluded.

Returns:
    List of word/token strings.

Example:
    >>> break_words('Hello, world!', 'en', skip_punctuation=True)
    ['Hello', 'world']

## icukit.calendar

Calendar system information.

Query available calendar systems (Gregorian, Buddhist, Hebrew, Islamic, etc.)
and their properties.

Key Features:
    * List all available calendar types
    * Get calendar info (type, description)
    * 17+ calendar systems supported

Calendar Types:
    * gregorian - Gregorian calendar (default Western calendar)
    * buddhist - Thai Buddhist calendar
    * chinese - Chinese lunar calendar
    * coptic - Coptic calendar (Egypt)
    * ethiopic - Ethiopian calendar
    * hebrew - Hebrew/Jewish calendar
    * indian - Indian National calendar
    * islamic - Islamic/Hijri calendar (various variants)
    * japanese - Japanese Imperial calendar
    * persian - Persian/Jalali calendar
    * roc - Republic of China (Taiwan) calendar

Example:
    List and query calendars::

        >>> from icukit import list_calendars, get_calendar_info
        >>>
        >>> # List all calendar types
        >>> cals = list_calendars()
        >>> 'hebrew' in cals
        True
        >>>
        >>> # Get info about a calendar
        >>> info = get_calendar_info('islamic')
        >>> info['type']
        'islamic'

### `get_calendar_info(cal_type: str) -> Optional[Dict[str, Any]]`

Get information about a calendar type.

Args:
    cal_type: Calendar type name (e.g., 'gregorian', 'hebrew').

Returns:
    Dict with calendar info, or None if not found.

Example:
    >>> info = get_calendar_info('hebrew')
    >>> info['type']
    'hebrew'

### `is_valid_calendar(cal_type: str) -> bool`

Check if a calendar type is valid.

Args:
    cal_type: Calendar type to check.

Returns:
    True if valid, False otherwise.

Example:
    >>> is_valid_calendar('gregorian')
    True
    >>> is_valid_calendar('invalid')
    False

### `list_calendars() -> List[str]`

List all available calendar types.

Returns:
    List of calendar type names sorted alphabetically.

Example:
    >>> cals = list_calendars()
    >>> 'gregorian' in cals
    True
    >>> 'hebrew' in cals
    True

### `list_calendars_info() -> List[Dict[str, Any]]`

List all calendars with their info.

Returns:
    List of dicts with calendar info.

Example:
    >>> cals = list_calendars_info()
    >>> greg = next(c for c in cals if c['type'] == 'gregorian')
    >>> 'Western' in greg['description']
    True

## icukit.collator

Locale-aware string collation and sorting.

ICU's Collator provides Unicode-compliant string comparison that respects
language-specific sorting rules.

Example:
    >>> from icukit import sort_strings
    >>> sort_strings(["café", "cafe", "CAFÉ"], "en_US")
    ['cafe', 'café', 'CAFÉ']
    >>> sort_strings(["Öl", "Ol", "öl"], "de_DE")
    ['Ol', 'Öl', 'öl']

### `compare_strings(a: 'str', b: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None) -> 'int'`

Compare two strings using locale-aware collation.

Args:
    a: First string.
    b: Second string.
    locale: Locale for comparison rules.
    strength: Collation strength.

Returns:
    -1 if a < b, 0 if a == b, 1 if a > b.

Example:
    >>> compare_strings("cafe", "café", "en_US")
    -1
    >>> compare_strings("cafe", "café", "en_US", strength="primary")
    0

### `get_collator_info(locale: 'str', *, include_extended: 'bool' = False) -> 'dict'`

Get information about a collator for a locale.

Args:
    locale: Locale identifier.
    include_extended: Include additional details in extended dict.

Returns:
    Dictionary with collator properties.

Example:
    >>> info = get_collator_info("de_DE")
    >>> info["locale"]
    'de_DE'

### `get_sort_key(text: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None) -> 'bytes'`

Get a binary sort key for external sorting.

Sort keys can be compared using standard byte comparison, useful for
database indexing or when sorting needs to be done outside Python.

Args:
    text: String to get sort key for.
    locale: Locale for collation rules.
    strength: Collation strength.

Returns:
    Binary sort key.

Example:
    >>> key_a = get_sort_key("apple", "en_US")
    >>> key_b = get_sort_key("banana", "en_US")
    >>> key_a < key_b
    True

### `list_collation_types() -> 'list[str]'`

List available collation types.

Returns:
    List of collation type names (e.g., standard, phonebook, emoji).

Example:
    >>> types = list_collation_types()
    >>> "phonebook" in types
    True

### `sort_strings(items: 'list[str]', locale: 'str' = 'en_US', *, reverse: 'bool' = False, strength: 'str | None' = None, case_first: 'str | None' = None) -> 'list[str]'`

Sort strings using locale-aware collation.

Args:
    items: List of strings to sort.
    locale: Locale for sorting rules (default: en_US).
    reverse: Sort in descending order.
    strength: Collation strength (primary, secondary, tertiary, quaternary, identical).
    case_first: "upper" or "lower" to control case ordering.

Returns:
    Sorted list of strings.

Example:
    >>> sort_strings(["café", "cafe", "Cafe"], "en_US")
    ['cafe', 'Cafe', 'café']
    >>> sort_strings(["ö", "o", "p"], "de_DE")
    ['o', 'ö', 'p']
    >>> sort_strings(["ö", "o", "p"], "sv_SE")
    ['o', 'p', 'ö']

## icukit.compact

Compact number formatting.

Format large numbers in abbreviated form with locale-appropriate suffixes.

This module provides a standalone interface to compact number formatting.
The core function `format_compact` is defined in `locale.py` alongside
other number formatting functions.

Styles:
    SHORT - "1.2M", "3.5K", "1,2 Mrd." (German)
    LONG  - "1.2 million", "3.5 thousand"

Example:
    >>> from icukit import format_compact
    >>>
    >>> format_compact(1234567)
    '1.2M'
    >>> format_compact(1234567, locale="de_DE")
    '1,2 Mio.'
    >>> format_compact(1234567, style="LONG")
    '1.2 million'
    >>>
    >>> format_compact(3500)
    '3.5K'
    >>> format_compact(3500, locale="ja_JP")
    '3500'  # Japanese uses 万 (10000) not K (1000)

### class `CompactFormatter`

Locale-aware compact number formatter.

Formats large numbers with locale-appropriate abbreviations.

Example:
    >>> fmt = CompactFormatter("en_US")
    >>> fmt.format(1234567)
    '1.2M'
    >>> fmt.format(1234567, style="LONG")
    '1.2 million'

#### `CompactFormatter(locale: 'str' = 'en_US', style: 'str' = 'SHORT')`

Create a CompactFormatter.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP")
    style: Default style (SHORT or LONG)

#### `format(number: 'int | float', style: 'str | None' = None) -> 'str'`

Format a number in compact form.

Args:
    number: Number to format
    style: Style override (SHORT or LONG)

Returns:
    Formatted string (e.g., "1.2M", "1.2 million")

Example:
    >>> fmt.format(1234567)
    '1.2M'
    >>> fmt.format(1234567, style="LONG")
    '1.2 million'

## icukit.datetime

Locale-aware date and time formatting.

ICU's DateFormat provides sophisticated date/time formatting that adapts to
different locales and cultural conventions.

Styles:
    FULL   - Monday, January 15, 2024 at 3:45:30 PM Eastern Standard Time
    LONG   - January 15, 2024 at 3:45:30 PM EST
    MEDIUM - Jan 15, 2024, 3:45:30 PM
    SHORT  - 1/15/24, 3:45 PM

Pattern symbols:
    y - Year (yyyy=2024, yy=24)
    M - Month (M=1, MM=01, MMM=Jan, MMMM=January)
    d - Day of month (d=1, dd=01)
    E - Day of week (E=Mon, EEEE=Monday)
    h - Hour 1-12
    H - Hour 0-23
    m - Minute
    s - Second
    a - AM/PM
    z - Time zone (PST)
    Z - Time zone offset (-0800)

Example:
    >>> from icukit import DateTimeFormatter
    >>> from datetime import datetime
    >>>
    >>> fmt = DateTimeFormatter("en_US")
    >>> now = datetime.now()
    >>> print(fmt.format(now, style="SHORT"))
    1/15/24, 3:45 PM
    >>> print(fmt.format(now, pattern="EEEE, MMMM d, yyyy"))
    Monday, January 15, 2024
    >>>
    >>> fmt_de = DateTimeFormatter("de_DE")
    >>> print(fmt_de.format(now, style="LONG"))
    15. Januar 2024 um 15:45:30 MEZ

### class `DateTimeFormatter`

Locale-aware date/time formatter.

Provides formatting with predefined styles or custom patterns,
relative time formatting, and date interval formatting.

Example:
    >>> fmt = DateTimeFormatter("fr_FR")
    >>> fmt.format(datetime.now(), style="LONG")
    '15 janvier 2024 à 15:45:30 UTC−5'
    >>> fmt.format_relative(days=-1)
    'hier'
    >>>
    >>> # Different calendar systems
    >>> fmt = DateTimeFormatter("en_US", calendar="hebrew")
    >>> fmt.format(datetime(2024, 1, 15), pattern="yyyy-MM-dd")
    '5784-04-05'

#### `DateTimeFormatter(locale: 'str' = 'en_US', calendar: 'str | None' = None)`

Create a DateTimeFormatter for the given locale.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP")
    calendar: Calendar system (e.g., "gregorian", "buddhist", "hebrew",
             "islamic", "japanese", "chinese", "persian")

#### `format(dt: 'datetime | date | time', style: 'str | None' = None, date_style: 'str | None' = None, time_style: 'str | None' = None, pattern: 'str | None' = None) -> 'str'`

Format a date/time value.

Args:
    dt: Date/time to format
    style: Combined style (FULL, LONG, MEDIUM, SHORT) for both date and time
    date_style: Date style (overrides style for date part)
    time_style: Time style (overrides style for time part, NONE for date-only)
    pattern: Custom ICU pattern (overrides all styles)

Returns:
    Formatted string

Example:
    >>> fmt.format(now, style="SHORT")
    '1/15/24, 3:45 PM'
    >>> fmt.format(now, date_style="LONG", time_style="NONE")
    'January 15, 2024'
    >>> fmt.format(now, pattern="yyyy-MM-dd")
    '2024-01-15'

#### `format_interval(start: 'datetime | date', end: 'datetime | date', skeleton: 'str' = 'yMMMd') -> 'str'`

Format a date/time interval.

Args:
    start: Start date/time
    end: End date/time
    skeleton: Format skeleton (e.g., "yMMMd", "MMMd", "Hm")

Returns:
    Formatted interval (e.g., "Jan 15 – 20, 2024")

Example:
    >>> start = date(2024, 1, 15)
    >>> end = date(2024, 1, 20)
    >>> fmt.format_interval(start, end)
    'Jan 15 – 20, 2024'

#### `format_relative(delta: 'int | timedelta | None' = None, days: 'int' = 0, hours: 'int' = 0, minutes: 'int' = 0, seconds: 'int' = 0) -> 'str'`

Format relative time.

Args:
    delta: Time delta (int for days, or timedelta object)
    days: Days offset (can combine with delta)
    hours: Hours offset
    minutes: Minutes offset
    seconds: Seconds offset

Returns:
    Relative time string (e.g., "yesterday", "in 2 hours", "3 days ago")

Example:
    >>> fmt.format_relative(days=-1)
    'yesterday'
    >>> fmt.format_relative(hours=2)
    'in 2 hours'
    >>> fmt.format_relative(timedelta(days=-7))
    '1 week ago'

#### `parse(text: 'str', pattern: 'str | None' = None) -> 'datetime'`

Parse a date/time string.

Args:
    text: String to parse
    pattern: Expected format pattern (optional, tries common formats if not given)

Returns:
    Parsed datetime

Raises:
    DateTimeError: If parsing fails

### `format_datetime(dt: 'datetime | date | time', locale: 'str' = 'en_US', calendar: 'str | None' = None, **kwargs) -> 'str'`

Format a date/time value (convenience function).

Args:
    dt: Date/time to format
    locale: Locale code
    calendar: Calendar system (e.g., "hebrew", "islamic", "buddhist")
    **kwargs: Passed to DateTimeFormatter.format()

Returns:
    Formatted string

### `format_relative(delta: 'int | timedelta | None' = None, locale: 'str' = 'en_US', calendar: 'str | None' = None, **kwargs) -> 'str'`

Format relative time (convenience function).

Args:
    delta: Time delta
    locale: Locale code
    calendar: Calendar system
    **kwargs: Passed to DateTimeFormatter.format_relative()

Returns:
    Relative time string

### `get_am_pm_strings(locale: 'str' = 'en_US', calendar: 'str | None' = None) -> 'list[str]'`

Get localized AM/PM strings.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
    calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

Returns:
    List of 2 strings: [AM, PM] or locale equivalent.

Example:
    >>> get_am_pm_strings("en_US")
    ['AM', 'PM']
    >>> get_am_pm_strings("ja_JP")
    ['午前', '午後']
    >>> get_am_pm_strings("zh_CN")
    ['上午', '下午']

### `get_date_symbols(locale: 'str' = 'en_US', calendar: 'str | None' = None) -> 'dict'`

Get all date/time symbols for a locale.

Returns a comprehensive dict of all localized date/time symbols including
month names, weekday names, era names, and AM/PM strings.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
    calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

Returns:
    Dict with all date symbols organized by category.

Example:
    >>> symbols = get_date_symbols("fr_FR")
    >>> symbols["months"]["wide"]
    ['janvier', 'février', ..., 'décembre']
    >>> symbols["weekdays"]["abbreviated"]
    ['dim.', 'lun.', 'mar.', ...]
    >>> symbols["am_pm"]
    ['AM', 'PM']

### `get_era_names(locale: 'str' = 'en_US', width: 'str' = 'WIDE', calendar: 'str | None' = None) -> 'list[str]'`

Get localized era names.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
    width: Name width - WIDTH_WIDE ("Before Christ") or WIDTH_ABBREVIATED ("BC").
    calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

Returns:
    List of era names (typically 2 for Gregorian: BC/AD or equivalent).

Example:
    >>> get_era_names("en_US")
    ['Before Christ', 'Anno Domini']
    >>> get_era_names("en_US", WIDTH_ABBREVIATED)
    ['BC', 'AD']
    >>> get_era_names("ja_JP")
    ['紀元前', '西暦']

### `get_month_names(locale: 'str' = 'en_US', width: 'str' = 'WIDE', calendar: 'str | None' = None) -> 'list[str]'`

Get localized month names.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
    width: Name width - WIDTH_WIDE ("January") or WIDTH_ABBREVIATED ("Jan").
    calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

Returns:
    List of 12 month names (January-December or equivalent).

Example:
    >>> get_month_names("en_US")
    ['January', 'February', 'March', ..., 'December']
    >>> get_month_names("de_DE", WIDTH_ABBREVIATED)
    ['Jan.', 'Feb.', 'März', ..., 'Dez.']
    >>> get_month_names("ja_JP")
    ['1月', '2月', '3月', ..., '12月']

### `get_weekday_names(locale: 'str' = 'en_US', width: 'str' = 'WIDE', calendar: 'str | None' = None) -> 'dict'`

Get localized weekday names.

Returns weekday names in standard Sunday-Saturday order, along with
metadata about which day is the first day of the week for this locale.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
    width: Name width - WIDTH_WIDE ("Sunday") or WIDTH_ABBREVIATED ("Sun").
    calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

Returns:
    Dict with:
        - names: List of 7 weekday names (Sunday-Saturday order)
        - first_day_index: Index of locale's first day (0=Sunday, 1=Monday, etc.)
        - first_day: Name of locale's first day of week

Example:
    >>> get_weekday_names("en_US")
    {'names': ['Sunday', 'Monday', ...], 'first_day_index': 0, 'first_day': 'Sunday'}
    >>> get_weekday_names("de_DE")
    {'names': ['Sonntag', 'Montag', ...], 'first_day_index': 1, 'first_day': 'Montag'}
    >>> get_weekday_names("ja_JP", WIDTH_ABBREVIATED)
    {'names': ['日', '月', '火', ...], 'first_day_index': 0, 'first_day': '日'}

### `parse_datetime(text: 'str', locale: 'str' = 'en_US', calendar: 'str | None' = None, pattern: 'str | None' = None) -> 'datetime'`

Parse a date/time string (convenience function).

Args:
    text: String to parse
    locale: Locale code
    calendar: Calendar system
    pattern: Expected format pattern

Returns:
    Parsed datetime

## icukit.discover

Discovery utilities for icukit features and capabilities.

This module provides introspection of icukit's API and CLI, helping users
discover available functionality. It dynamically reflects the actual
exports and commands rather than hardcoding them.

Note: Import this module directly (from icukit.discover import ...) rather
than from icukit to avoid circular imports.

### `discover_features() -> Dict[str, Any]`

Discover all available features in icukit.

Returns:
    Dictionary with API exports and CLI commands

### `get_api_exports() -> List[str]`

Get all exported API functions and classes.

Returns:
    List of exported names from icukit.__all__

### `get_api_info(name: str) -> Optional[Dict[str, Any]]`

Get information about an API export.

Args:
    name: Name of the exported function/class

Returns:
    Dictionary with name, type, signature, and docstring, or None if not found

### `get_cli_commands() -> Dict[str, Dict[str, Any]]`

Get available CLI commands with their details.

Returns:
    Dictionary mapping command names to their info (aliases, minimal_prefix)

### `print_discovery_report()`

Print a formatted discovery report to stdout.

### `search_features(query: str) -> Dict[str, List[str]]`

Search for features matching a query.

Args:
    query: Search term (case-insensitive)

Returns:
    Dictionary with matching API exports and CLI commands

## icukit.displayname

Locale-aware display names.

Get localized names for languages, scripts, regions, currencies, and
calendar types using ICU's display name capabilities.

Example:
    >>> from icukit import get_language_name, get_region_name, get_currency_name
    >>>
    >>> get_language_name("zh", "en")
    'Chinese'
    >>> get_language_name("zh", "de")
    'Chinesisch'
    >>> get_language_name("zh", "ja")
    '中国語'
    >>>
    >>> get_region_name("JP", "en")
    'Japan'
    >>> get_region_name("JP", "ja")
    '日本'
    >>>
    >>> get_currency_name("USD", "en")
    'US Dollar'
    >>> get_currency_name("USD", "ja")
    '米ドル'

### class `DisplayNames`

Locale-aware display names provider.

Provides localized names for languages, scripts, regions, and currencies.

Example:
    >>> names = DisplayNames("de")
    >>> names.language("zh")
    'Chinesisch'
    >>> names.region("JP")
    'Japan'
    >>> names.currency("USD")
    'US-Dollar'

#### `DisplayNames(display_locale: str = 'en_US')`

Create a DisplayNames instance.

Args:
    display_locale: Locale for the display names (e.g., "en", "de", "ja")

#### `currency(currency_code: str) -> str`

Get the display name for a currency.

Args:
    currency_code: ISO 4217 currency code (e.g., "USD", "EUR", "JPY")

Returns:
    Localized currency name

Example:
    >>> names = DisplayNames("de")
    >>> names.currency("USD")
    'US-Dollar'

#### `currency_symbol(currency_code: str) -> str`

Get the currency symbol.

Args:
    currency_code: ISO 4217 currency code (e.g., "USD", "EUR", "JPY")

Returns:
    Currency symbol (e.g., "$", "€", "¥")

Example:
    >>> names = DisplayNames("en_US")
    >>> names.currency_symbol("USD")
    '$'
    >>> names.currency_symbol("EUR")
    '€'

#### `language(language_code: str) -> str`

Get the display name for a language.

Args:
    language_code: ISO 639 language code (e.g., "en", "zh", "ar")

Returns:
    Localized language name

Example:
    >>> names = DisplayNames("de")
    >>> names.language("zh")
    'Chinesisch'

#### `locale(locale_code: str) -> str`

Get the display name for a locale.

Args:
    locale_code: Locale code (e.g., "en_US", "zh_Hans_CN", "de_DE")

Returns:
    Localized locale name

Example:
    >>> names = DisplayNames("en")
    >>> names.locale("zh_Hans_CN")
    'Chinese (Simplified, China)'

#### `region(region_code: str) -> str`

Get the display name for a region/country.

Args:
    region_code: ISO 3166-1 alpha-2 region code (e.g., "US", "JP", "DE")

Returns:
    Localized region name

Example:
    >>> names = DisplayNames("ja")
    >>> names.region("US")
    'アメリカ合衆国'

#### `script(script_code: str) -> str`

Get the display name for a script.

Args:
    script_code: ISO 15924 script code (e.g., "Latn", "Cyrl", "Hans")

Returns:
    Localized script name

Example:
    >>> names = DisplayNames("en")
    >>> names.script("Cyrl")
    'Cyrillic'
    >>> names.script("Hans")
    'Simplified Han'

### `get_currency_name(currency_code: str, display_locale: str = 'en_US') -> str`

Get the display name for a currency (convenience function).

Args:
    currency_code: ISO 4217 currency code
    display_locale: Locale for the display name

Returns:
    Localized currency name

Example:
    >>> get_currency_name("USD", "en")
    'US Dollar'
    >>> get_currency_name("USD", "ja")
    '米ドル'

### `get_currency_symbol(currency_code: str, display_locale: str = 'en_US') -> str`

Get the currency symbol (convenience function).

Args:
    currency_code: ISO 4217 currency code
    display_locale: Locale for symbol formatting

Returns:
    Currency symbol

Example:
    >>> get_currency_symbol("USD", "en_US")
    '$'
    >>> get_currency_symbol("EUR", "de_DE")
    '€'

### `get_language_name(language_code: str, display_locale: str = 'en_US') -> str`

Get the display name for a language (convenience function).

Args:
    language_code: ISO 639 language code
    display_locale: Locale for the display name

Returns:
    Localized language name

Example:
    >>> get_language_name("zh", "en")
    'Chinese'
    >>> get_language_name("zh", "de")
    'Chinesisch'

### `get_locale_name(locale_code: str, display_locale: str = 'en_US') -> str`

Get the display name for a locale (convenience function).

Args:
    locale_code: Locale code
    display_locale: Locale for the display name

Returns:
    Localized locale name

Example:
    >>> get_locale_name("zh_Hans_CN", "en")
    'Chinese (Simplified, China)'

### `get_region_name(region_code: str, display_locale: str = 'en_US') -> str`

Get the display name for a region/country (convenience function).

Args:
    region_code: ISO 3166-1 alpha-2 region code
    display_locale: Locale for the display name

Returns:
    Localized region name

Example:
    >>> get_region_name("JP", "en")
    'Japan'
    >>> get_region_name("JP", "ja")
    '日本'

### `get_script_name(script_code: str, display_locale: str = 'en_US') -> str`

Get the display name for a script (convenience function).

Args:
    script_code: ISO 15924 script code
    display_locale: Locale for the display name

Returns:
    Localized script name

Example:
    >>> get_script_name("Cyrl", "en")
    'Cyrillic'

## icukit.duration

Locale-aware duration formatting.

Format time durations (e.g., "2 hours, 30 minutes") with proper locale
conventions using ICU's MeasureFormat.

Width Styles:
    WIDE   - "2 hours, 30 minutes, 15 seconds"
    SHORT  - "2 hr, 30 min, 15 sec"
    NARROW - "2h 30m 15s"

Example:
    >>> from icukit import format_duration, DurationFormatter
    >>>
    >>> format_duration(3661)  # seconds
    '1 hour, 1 minute, 1 second'
    >>>
    >>> format_duration(3661, locale="de_DE")
    '1 Stunde, 1 Minute und 1 Sekunde'
    >>>
    >>> format_duration(3661, width="SHORT")
    '1 hr, 1 min, 1 sec'
    >>>
    >>> fmt = DurationFormatter("ja_JP", width="NARROW")
    >>> fmt.format(hours=2, minutes=30)
    '2時間30分'

### class `DurationFormatter`

Locale-aware duration formatter.

Formats time durations with proper locale conventions.

Example:
    >>> fmt = DurationFormatter("en_US")
    >>> fmt.format(hours=2, minutes=30)
    '2 hours, 30 minutes'
    >>> fmt.format(seconds=3661)
    '1 hour, 1 minute, 1 second'

#### `DurationFormatter(locale: str = 'en_US', width: str = 'WIDE')`

Create a DurationFormatter.

Args:
    locale: Locale code (e.g., "en_US", "de_DE")
    width: Width style (WIDE, SHORT, NARROW)

#### `format(seconds: float | None = None, minutes: float = 0, hours: float = 0, days: float = 0, weeks: float = 0, months: float = 0, years: float = 0) -> str`

Format a duration.

Args:
    seconds: Total seconds (will be decomposed if other args are 0),
            or just the seconds component if other args are provided
    minutes: Minutes component
    hours: Hours component
    days: Days component
    weeks: Weeks component
    months: Months component
    years: Years component

Returns:
    Formatted duration string

Example:
    >>> fmt.format(seconds=3661)
    '1 hour, 1 minute, 1 second'
    >>> fmt.format(hours=2, minutes=30)
    '2 hours, 30 minutes'

#### `format_iso(iso_string: str) -> str`

Format an ISO 8601 duration string.

Args:
    iso_string: ISO 8601 duration (e.g., "P2DT3H30M")

Returns:
    Formatted duration string

Example:
    >>> fmt.format_iso("P2DT3H30M")
    '2 days, 3 hours, 30 minutes'

### `format_duration(seconds: float | None = None, locale: str = 'en_US', width: str = 'WIDE', **kwargs) -> str`

Format a duration (convenience function).

Args:
    seconds: Total seconds (or provide individual components via kwargs)
    locale: Locale code
    width: Width style (WIDE, SHORT, NARROW)
    **kwargs: Individual components (minutes, hours, days, weeks, months, years)

Returns:
    Formatted duration string

Example:
    >>> format_duration(3661)
    '1 hour, 1 minute, 1 second'
    >>> format_duration(3661, locale="de_DE")
    '1 Stunde, 1 Minute und 1 Sekunde'
    >>> format_duration(hours=2, minutes=30)
    '2 hours, 30 minutes'

### `parse_iso_duration(iso_string: str) -> dict`

Parse an ISO 8601 duration string.

Args:
    iso_string: ISO 8601 duration (e.g., "P2DT3H30M", "PT1H30M")

Returns:
    Dictionary with duration components (years, months, days, hours, minutes, seconds)

Raises:
    DurationError: If parsing fails

Example:
    >>> parse_iso_duration("P2DT3H30M")
    {'years': 0, 'months': 0, 'weeks': 0, 'days': 2, 'hours': 3, 'minutes': 30, 'seconds': 0}
    >>> parse_iso_duration("PT1H30M15S")
    {'years': 0, 'months': 0, 'weeks': 0, 'days': 0, 'hours': 1, 'minutes': 30, 'seconds': 15}

## icukit.idna

Internationalized Domain Name (IDNA) encoding and decoding.

Converts between Unicode domain names and ASCII-compatible encoding
(Punycode), following the IDNA standard.

Example:
    >>> from icukit import idna_encode, idna_decode
    >>> idna_encode("münchen.de")
    'xn--mnchen-3ya.de'
    >>> idna_decode("xn--mnchen-3ya.de")
    'münchen.de'

### class `IDNAConverter`

Reusable IDNA converter for batch operations.

Example:
    >>> converter = IDNAConverter()
    >>> converter.encode("münchen.de")
    'xn--mnchen-3ya.de'
    >>> converter.decode("xn--mnchen-3ya.de")
    'münchen.de'

#### `IDNAConverter()`

Create a new IDNA converter.

#### `decode(domain: str) -> str`

Decode ASCII domain to Unicode.

#### `decode_label(label: str) -> str`

Decode single label to Unicode.

#### `encode(domain: str) -> str`

Encode Unicode domain to ASCII.

#### `encode_label(label: str) -> str`

Encode single label to ASCII.

### `idna_decode(domain: str) -> str`

Decode an ASCII (Punycode) domain name to Unicode.

Converts ASCII-encoded domain names back to their Unicode representation.

Args:
    domain: ASCII-encoded domain name (e.g., "xn--mnchen-3ya.de").

Returns:
    Unicode domain name (e.g., "münchen.de").

Raises:
    IDNAError: If decoding fails.

Example:
    >>> idna_decode("xn--mnchen-3ya.de")
    'münchen.de'
    >>> idna_decode("xn--r8jz45g.jp")
    '例え.jp'

### `idna_decode_label(label: str) -> str`

Decode a single ASCII domain label to Unicode.

Args:
    label: ASCII-encoded label (e.g., "xn--mnchen-3ya").

Returns:
    Unicode label (e.g., "münchen").

Example:
    >>> idna_decode_label("xn--mnchen-3ya")
    'münchen'

### `idna_encode(domain: str) -> str`

Encode a Unicode domain name to ASCII (Punycode).

Converts internationalized domain names to ASCII-compatible encoding
that can be used in DNS lookups and URLs.

Args:
    domain: Unicode domain name (e.g., "münchen.de", "例え.jp").

Returns:
    ASCII-encoded domain name (e.g., "xn--mnchen-3ya.de").

Raises:
    IDNAError: If encoding fails.

Example:
    >>> idna_encode("münchen.de")
    'xn--mnchen-3ya.de'
    >>> idna_encode("例え.jp")
    'xn--r8jz45g.jp'

### `idna_encode_label(label: str) -> str`

Encode a single domain label to ASCII.

A label is a single component of a domain name (between dots).

Args:
    label: Unicode label (e.g., "münchen").

Returns:
    ASCII-encoded label (e.g., "xn--mnchen-3ya").

Example:
    >>> idna_encode_label("münchen")
    'xn--mnchen-3ya'

### `is_ascii_domain(domain: str) -> bool`

Check if a domain name is already ASCII-only.

Args:
    domain: Domain name to check.

Returns:
    True if the domain contains only ASCII characters.

Example:
    >>> is_ascii_domain("example.com")
    True
    >>> is_ascii_domain("münchen.de")
    False

## icukit.list_format

Locale-aware list formatting.

ICU's ListFormatter formats lists of items with appropriate conjunctions
and separators for each locale.

Key Features:
    * Locale-aware conjunctions ("and", "oder", "と", etc.)
    * Multiple styles: and, or, unit
    * Handles two-item special case
    * Oxford comma where appropriate

Example:
    >>> from icukit import format_list
    >>> format_list(['apples', 'oranges', 'bananas'], 'en')
    'apples, oranges, and bananas'
    >>> format_list(['Äpfel', 'Orangen', 'Bananen'], 'de')
    'Äpfel, Orangen und Bananen'

### class `ListFormatter`

Locale-aware list formatter.

Formats lists of items with appropriate conjunctions and separators.

Example:
    >>> lf = ListFormatter('en', style='and')
    >>> lf.format(['apples', 'oranges', 'bananas'])
    'apples, oranges, and bananas'

#### `ListFormatter(locale: str = 'en_US', style: str = 'and')`

Initialize a ListFormatter.

Args:
    locale: Locale for formatting rules.
    style: List style - 'and', 'or', or 'unit'.

Raises:
    ListFormatError: If locale or style is invalid.

#### `format(items: list[str]) -> str`

Format a list of items.

Args:
    items: List of strings to format.

Returns:
    Formatted string with locale-appropriate conjunctions.

Example:
    >>> lf = ListFormatter('en')
    >>> lf.format(['a', 'b', 'c'])
    'a, b, and c'

### `format_list(items: list[str], locale: str = 'en_US', style: str = 'and') -> str`

Format a list of items with locale-appropriate conjunctions.

Args:
    items: List of strings to format.
    locale: Locale for formatting rules.
    style: List style - 'and', 'or', or 'unit'.

Returns:
    Formatted string.

Example:
    >>> format_list(['apples', 'oranges', 'bananas'], 'en')
    'apples, oranges, and bananas'

    >>> format_list(['apples', 'oranges', 'bananas'], 'en', style='or')
    'apples, oranges, or bananas'

    >>> format_list(['Äpfel', 'Orangen'], 'de')
    'Äpfel und Orangen'

## icukit.locale

Locale parsing and information.

Parse, validate, and query locale identifiers (language + region + script).
Integrates with other icukit domain objects (region, script, calendar, timezone).

Key Features:
    * Parse locale strings (BCP 47 and ICU format)
    * Get display names for languages, regions, scripts
    * List available locales
    * Add likely subtags (e.g., 'zh' -> 'zh_Hans_CN')
    * Query locale components

Locale Format:
    Locales follow the pattern: language[_Script][_REGION][@keywords]

    Examples:
        * 'en' - English
        * 'en_US' - English (United States)
        * 'zh_Hans' - Chinese (Simplified)
        * 'zh_Hans_CN' - Chinese (Simplified, China)
        * 'sr_Latn_RS' - Serbian (Latin, Serbia)
        * 'en_US@calendar=hebrew' - English (US) with Hebrew calendar

Example:
    Parse and query locales::

        >>> from icukit import parse_locale, get_locale_info, list_locales
        >>>
        >>> # Parse a locale
        >>> info = parse_locale('el_GR')
        >>> info['language']
        'el'
        >>> info['region']
        'GR'
        >>>
        >>> # Get display names
        >>> info = get_locale_info('ja_JP')
        >>> info['display_name']
        'Japanese (Japan)'
        >>>
        >>> # Add likely subtags
        >>> from icukit import add_likely_subtags
        >>> add_likely_subtags('zh')
        'zh_Hans_CN'

### `add_likely_subtags(locale_str: str) -> str`

Add likely subtags to a locale identifier.

Expands a minimal locale to include likely script and region.

Args:
    locale_str: Minimal locale string (e.g., 'zh', 'sr').

Returns:
    Expanded locale string.

Example:
    >>> add_likely_subtags('zh')
    'zh_Hans_CN'
    >>> add_likely_subtags('sr')
    'sr_Cyrl_RS'

### `canonicalize_locale(locale_str: str) -> str`

Canonicalize a locale identifier.

Converts to canonical form (e.g., deprecated codes to current ones).

Args:
    locale_str: Locale string.

Returns:
    Canonical locale string.

Example:
    >>> canonicalize_locale('iw')  # deprecated Hebrew code
    'he'

### `format_compact(value: int | float, locale_str: str = 'en_US', style: str = 'SHORT') -> str`

Format a number in compact form with locale-appropriate abbreviations.

Args:
    value: Number to format.
    locale_str: Locale for formatting.
    style: COMPACT_SHORT ("1.2M") or COMPACT_LONG ("1.2 million").

Returns:
    Compact formatted string.

Example:
    >>> format_compact(1234567, 'en_US')
    '1.2M'
    >>> format_compact(1234567, 'de_DE')
    '1,2 Mio.'
    >>> format_compact(1234567, 'en_US', COMPACT_LONG)
    '1.2 million'

### `format_currency(value: float, locale_str: str = 'en_US', currency: str = None) -> str`

Format a value as currency.

Args:
    value: Amount to format.
    locale_str: Locale for formatting.
    currency: Optional currency code (e.g., 'EUR'). If None, uses locale default.

Returns:
    Formatted currency string.

Example:
    >>> format_currency(1234.56, 'en_US')
    '$1,234.56'
    >>> format_currency(1234.56, 'de_DE')
    '1.234,56 €'
    >>> format_currency(1234.56, 'en_US', 'EUR')
    '€1,234.56'

### `format_number(value: float, locale_str: str = 'en_US') -> str`

Format a number according to locale conventions.

Args:
    value: Number to format.
    locale_str: Locale for formatting.

Returns:
    Formatted number string.

Example:
    >>> format_number(1234567.89, 'en_US')
    '1,234,567.89'
    >>> format_number(1234567.89, 'de_DE')
    '1.234.567,89'

### `format_ordinal(value: int, locale_str: str = 'en_US') -> str`

Format a number as an ordinal.

Args:
    value: Integer to format.
    locale_str: Locale for formatting.

Returns:
    Ordinal string.

Example:
    >>> format_ordinal(1, 'en_US')
    '1st'
    >>> format_ordinal(2, 'en_US')
    '2nd'
    >>> format_ordinal(1, 'de_DE')
    '1.'

### `format_percent(value: float, locale_str: str = 'en_US') -> str`

Format a value as a percentage.

Args:
    value: Decimal value (0.15 = 15%).
    locale_str: Locale for formatting.

Returns:
    Formatted percentage string.

Example:
    >>> format_percent(0.15, 'en_US')
    '15%'
    >>> format_percent(0.15, 'de_DE')
    '15 %'

### `format_scientific(value: float, locale_str: str = 'en_US') -> str`

Format a value in scientific notation.

Args:
    value: Number to format.
    locale_str: Locale for formatting.

Returns:
    Formatted scientific notation string.

Example:
    >>> format_scientific(1234567.89, 'en_US')
    '1.234568E6'

### `format_spellout(value: int, locale_str: str = 'en_US') -> str`

Spell out a number in words.

Args:
    value: Integer to spell out.
    locale_str: Locale for spelling.

Returns:
    Number spelled out in words.

Example:
    >>> format_spellout(42, 'en_US')
    'forty-two'
    >>> format_spellout(42, 'de_DE')
    'zwei­und­vierzig'

### `get_default_locale() -> str`

Get the system default locale.

Returns:
    Default locale identifier.

Example:
    >>> get_default_locale()
    'en_US'  # or whatever the system default is

### `get_display_name(locale_str: str, display_locale: str = 'en') -> str`

Get the display name for a locale.

Args:
    locale_str: Locale to get display name for.
    display_locale: Locale for the display name.

Returns:
    Display name string.

Example:
    >>> get_display_name('el_GR')
    'Greek (Greece)'
    >>> get_display_name('el_GR', 'el')
    'Ελληνικά (Ελλάδα)'

### `get_exemplar_characters(locale_str: str = 'en_US', exemplar_type: str = 'standard') -> str`

Get exemplar characters for a locale.

Exemplar characters are the characters commonly used in a locale's
writing system.

Args:
    locale_str: Locale code (e.g., "en_US", "de_DE", "ja_JP").
    exemplar_type: Type of exemplar set:
        - "standard" - Main characters used in the locale
        - "auxiliary" - Characters for borrowed/foreign words
        - "index" - Characters for alphabetic indexes (A-Z sidebar)
        - "punctuation" - Punctuation characters

Returns:
    String representation of the exemplar character set (ICU UnicodeSet format).

Example:
    >>> get_exemplar_characters("de_DE")
    '[a-zßäöü]'
    >>> get_exemplar_characters("de_DE", "index")
    '[A-Z]'
    >>> get_exemplar_characters("ja_JP", "index")
    '[あかさたなはまやらわ]'

### `get_exemplar_info(locale_str: str = 'en_US') -> Dict[str, str]`

Get all exemplar character sets for a locale.

Args:
    locale_str: Locale code.

Returns:
    Dictionary mapping exemplar type to character set string.

Example:
    >>> info = get_exemplar_info("de_DE")
    >>> info["standard"]
    '[a-zßäöü]'
    >>> info["index"]
    '[A-Z]'

### `get_language_display_name(language: str, display_locale: str = 'en') -> str`

Get the display name for a language code.

Args:
    language: ISO 639 language code.
    display_locale: Locale for the display name.

Returns:
    Display name string.

Example:
    >>> get_language_display_name('el')
    'Greek'
    >>> get_language_display_name('ja')
    'Japanese'

### `get_locale_attributes(locale_str: str, display_locale: str = 'en') -> Dict[str, Any]`

Get comprehensive locale attributes.

Returns detailed information including currency, measurement system,
quote delimiters, and more.

Args:
    locale_str: Locale identifier.
    display_locale: Locale for display names.

Returns:
    Dict with comprehensive locale attributes.

Example:
    >>> attrs = get_locale_attributes('en_US')
    >>> attrs['currency']
    'USD'
    >>> attrs['measurement_system']
    'US'
    >>> attrs['quote_start']
    '"'

### `get_locale_extended(locale_str: str) -> Dict[str, Any]`

Get extended locale attributes.

Args:
    locale_str: Locale string.

Returns:
    Dict with extended attributes (calendar, currency, RTL, index_labels, etc.)

Example:
    >>> ext = get_locale_extended('ja_JP')
    >>> ext['currency']
    'JPY'
    >>> ext['calendar']
    'gregorian'
    >>> ext['index_labels'][:3]
    ['あ', 'か', 'さ']

### `get_locale_info(locale_str: str, display_locale: str = 'en', extended: bool = False) -> Dict[str, Any]`

Get detailed information about a locale.

Args:
    locale_str: Locale string to get info for.
    display_locale: Locale for display names.
    extended: Include extended attributes (calendar, currency, etc.)

Returns:
    Dict with locale info including display names and scripts.

Example:
    >>> info = get_locale_info('ja_JP')
    >>> info['display_name']
    'Japanese (Japan)'
    >>> info['scripts']
    ['Han', 'Hiragana', 'Katakana']
    >>> info = get_locale_info('ja_JP', extended=True)
    >>> info['extended']['currency']
    'JPY'

### `get_locale_scripts(locale_str: str) -> List[str]`

Get the scripts used by a locale.

Derives scripts from the locale's exemplar character set.

Args:
    locale_str: Locale string.

Returns:
    List of script names used by the locale.

Example:
    >>> get_locale_scripts('ja_JP')
    ['Han', 'Hiragana', 'Katakana']
    >>> get_locale_scripts('en_US')
    ['Latin']

### `get_number_symbols(locale_str: str = 'en_US') -> Dict[str, str]`

Get number formatting symbols for a locale.

Returns the symbols used for formatting numbers, including decimal
separator, grouping separator, percent sign, and more.

Args:
    locale_str: Locale code (e.g., "en_US", "de_DE", "ar_SA").

Returns:
    Dict with number formatting symbols:
        - decimal: Decimal separator ("." or ",")
        - grouping: Grouping/thousands separator ("," or "." or " ")
        - percent: Percent sign
        - per_mille: Per-mille sign (‰)
        - plus: Plus sign
        - minus: Minus sign
        - exponential: Exponential sign (E)
        - infinity: Infinity symbol (∞)
        - nan: Not-a-number symbol
        - currency: Default currency symbol for locale

Example:
    >>> get_number_symbols("en_US")
    {'decimal': '.', 'grouping': ',', 'percent': '%', ...}
    >>> get_number_symbols("de_DE")
    {'decimal': ',', 'grouping': '.', 'percent': '%', ...}
    >>> get_number_symbols("fr_FR")
    {'decimal': ',', 'grouping': ' ', 'percent': '%', ...}

### `is_valid_locale(locale_str: str) -> bool`

Check if a locale string is valid.

Args:
    locale_str: Locale string to validate.

Returns:
    True if valid, False otherwise.

Example:
    >>> is_valid_locale('en_US')
    True
    >>> is_valid_locale('xx_YY')
    False

### `list_exemplar_types() -> List[str]`

List available exemplar character set types.

Returns:
    List of exemplar type names.

Example:
    >>> list_exemplar_types()
    ['standard', 'auxiliary', 'index', 'punctuation']

### `list_languages() -> List[str]`

List all available language codes.

Returns:
    List of ISO 639 language codes sorted alphabetically.

Example:
    >>> langs = list_languages()
    >>> 'en' in langs
    True
    >>> 'el' in langs
    True

### `list_locales() -> List[str]`

List all available locale identifiers.

Returns:
    List of locale identifiers sorted alphabetically.

Example:
    >>> locales = list_locales()
    >>> 'en_US' in locales
    True
    >>> len(locales)
    851

### `list_locales_info(display_locale: str = 'en') -> List[Dict[str, Any]]`

List all locales with their info.

Args:
    display_locale: Locale for display names.

Returns:
    List of dicts with locale info.

Example:
    >>> locales = list_locales_info()
    >>> el = next(l for l in locales if l['id'] == 'el_GR')
    >>> el['display_name']
    'Greek (Greece)'

### `minimize_subtags(locale_str: str) -> str`

Remove likely subtags from a locale identifier.

Minimizes a locale to the shortest unambiguous form.

Args:
    locale_str: Full locale string.

Returns:
    Minimized locale string.

Example:
    >>> minimize_subtags('zh_Hans_CN')
    'zh'
    >>> minimize_subtags('en_Latn_US')
    'en'

### `parse_locale(locale_str: str) -> Dict[str, Any]`

Parse a locale string into components.

Args:
    locale_str: Locale string (e.g., 'en_US', 'zh-Hans-CN', 'sr_Latn_RS').

Returns:
    Dict with parsed components.

Example:
    >>> info = parse_locale('zh_Hans_CN')
    >>> info['language']
    'zh'
    >>> info['script']
    'Hans'
    >>> info['region']
    'CN'

## icukit.measure

Locale-aware unit measurement formatting.

ICU's MeasureFormat formats measurements with proper unit names and
locale-specific conventions.

Unit Types:
    length      - meter, kilometer, mile, foot, inch, yard, etc.
    mass        - gram, kilogram, pound, ounce, etc.
    temperature - celsius, fahrenheit, kelvin
    speed       - kilometer-per-hour, mile-per-hour, meter-per-second
    volume      - liter, milliliter, gallon, cup, tablespoon
    area        - square-meter, square-kilometer, acre, hectare
    duration    - second, minute, hour, day, week, month, year
    pressure    - hectopascal, millibar, inch-ofhg
    energy      - joule, kilocalorie, kilojoule
    power       - watt, kilowatt, horsepower
    digital     - byte, kilobyte, megabyte, gigabyte, terabyte

Width Styles:
    WIDE   - "5 kilometers" (full unit names)
    SHORT  - "5 km" (abbreviated)
    NARROW - "5km" (minimal, no space)

Example:
    >>> from icukit import MeasureFormatter
    >>>
    >>> fmt = MeasureFormatter("en_US")
    >>> fmt.format(5.5, "kilometer")
    '5.5 kilometers'
    >>> fmt.format(100, "fahrenheit", width="SHORT")
    '100°F'
    >>>
    >>> fmt_de = MeasureFormatter("de_DE")
    >>> fmt_de.format(5.5, "kilometer")
    '5,5 Kilometer'

### class `MeasureFormatter`

Locale-aware measurement formatter.

Example:
    >>> fmt = MeasureFormatter("en_US")
    >>> fmt.format(5.5, "kilometer")
    '5.5 kilometers'
    >>> fmt.format(100, "fahrenheit", width="SHORT")
    '100°F'

#### `MeasureFormatter(locale: 'str' = 'en_US', width: 'str' = 'WIDE')`

Create a MeasureFormatter.

Args:
    locale: Locale code (e.g., "en_US", "de_DE")
    width: Default width style (WIDE, SHORT, NARROW)

#### `convert(value: 'float | int', from_unit: 'str', to_unit: 'str') -> 'float'`

Convert a value between units.

Args:
    value: Numeric value to convert
    from_unit: Source unit or abbreviation (e.g., "kilometer", "km")
    to_unit: Target unit or abbreviation (e.g., "mile", "mi")

Returns:
    Converted value

Example:
    >>> fmt.convert(10, "kilometer", "mile")
    6.21371...
    >>> fmt.convert(10, "km", "mi")  # abbreviations work too
    6.21371...
    >>> fmt.convert(100, "celsius", "fahrenheit")
    212.0

#### `convert_and_format(value: 'float | int', from_unit: 'str', to_unit: 'str', width: 'str | None' = None) -> 'str'`

Convert a value and format the result.

Args:
    value: Numeric value to convert
    from_unit: Source unit
    to_unit: Target unit
    width: Width style for formatting

Returns:
    Formatted converted measurement

Example:
    >>> fmt.convert_and_format(10, "kilometer", "mile")
    '6.21371 miles'

#### `format(value: 'float | int', unit: 'str', width: 'str | None' = None) -> 'str'`

Format a measurement.

Args:
    value: Numeric value
    unit: Unit name or abbreviation (e.g., "kilometer", "km", "fahrenheit", "F")
    width: Width style (WIDE, SHORT, NARROW), overrides default

Returns:
    Formatted measurement string

Example:
    >>> fmt.format(5.5, "kilometer")
    '5.5 kilometers'
    >>> fmt.format(5.5, "km")  # abbreviation works too
    '5.5 kilometers'
    >>> fmt.format(100, "fahrenheit", width="SHORT")
    '100°F'

#### `format_for_usage(value: 'float | int', unit: 'str', usage: 'str' = 'default', width: 'str | None' = None) -> 'str'`

Format a measurement using locale-preferred units.

Converts to units preferred by the locale for the given usage.
For example, "road" usage in en_US converts km to miles.

Note: Usage-based conversion may not be available in all PyICU versions.
Falls back to standard formatting.

Args:
    value: Numeric value
    unit: Source unit
    usage: Usage context ("default", "road", "person-height", "weather", etc.)
    width: Width style

Returns:
    Formatted measurement in locale-preferred units

Example:
    >>> fmt_us = MeasureFormatter("en_US")
    >>> fmt_us.format_for_usage(100, "kilometer", usage="road")
    '62 miles'
    >>> fmt_de = MeasureFormatter("de_DE")
    >>> fmt_de.format_for_usage(100, "kilometer", usage="road")
    '100 Kilometer'

#### `format_range(low: 'float | int', high: 'float | int', unit: 'str', width: 'str | None' = None) -> 'str'`

Format a measurement range.

Args:
    low: Low value
    high: High value
    unit: Unit name or abbreviation
    width: Width style

Returns:
    Formatted range (e.g., "5-10 kilometers")

#### `format_sequence(measures: 'list[tuple[float | int, str]]', width: 'str | None' = None) -> 'str'`

Format a sequence of measurements (compound units).

Args:
    measures: List of (value, unit) tuples
    width: Width style

Returns:
    Formatted compound measurement

Example:
    >>> fmt.format_sequence([(5, "foot"), (10, "inch")])
    '5 feet, 10 inches'
    >>> fmt.format_sequence([(1, "hour"), (30, "minute")])
    '1 hour, 30 minutes'

### `can_convert(from_unit: 'str', to_unit: 'str') -> 'bool'`

Check if two units can be converted to each other.

Args:
    from_unit: Source unit name or abbreviation
    to_unit: Target unit name or abbreviation

Returns:
    True if conversion is possible, False otherwise

Example:
    >>> can_convert("kilometer", "mile")
    True
    >>> can_convert("kilometer", "celsius")
    False

### `convert_units(value: 'float | int', from_unit: 'str', to_unit: 'str') -> 'float'`

Convert a value between units (convenience function).

Args:
    value: Numeric value to convert
    from_unit: Source unit (e.g., "kilometer")
    to_unit: Target unit (e.g., "mile")

Returns:
    Converted value

Example:
    >>> convert_units(10, "kilometer", "mile")
    6.21371...
    >>> convert_units(100, "celsius", "fahrenheit")
    212.0

### `format_measure(value: 'float | int', unit: 'str', locale: 'str' = 'en_US', width: 'str' = 'WIDE') -> 'str'`

Format a measurement (convenience function).

Args:
    value: Numeric value
    unit: Unit name
    locale: Locale code
    width: Width style (WIDE, SHORT, NARROW)

Returns:
    Formatted measurement string

### `get_unit_abbreviation(unit: 'str', locale: 'str' = 'en_US') -> 'str'`

Get the abbreviation for a unit.

Args:
    unit: Unit name (e.g., "kilometer")
    locale: Locale for abbreviation

Returns:
    Abbreviated form (e.g., "km")

### `get_unit_info(unit: 'str') -> 'dict'`

Get information about a unit.

Args:
    unit: Unit name or abbreviation

Returns:
    Dict with unit info: type, identifier, complexity

Example:
    >>> get_unit_info("mile")
    {'identifier': 'mile', 'type': 'length', 'complexity': 'single'}

### `get_units_by_type() -> 'dict[str, list[str]]'`

Get all units organized by type.

Returns:
    Dict mapping unit type to list of unit names.

Example:
    >>> units = get_units_by_type()
    >>> "meter" in units["length"]
    True

### `list_unit_types() -> 'list[str]'`

List available unit types.

Returns:
    List of unit type names (length, mass, temperature, etc.)

### `list_units(unit_type: 'str | None' = None) -> 'list[str]'`

List available units.

Args:
    unit_type: Optional type to filter by (e.g., "length", "mass")

Returns:
    List of unit names

### `resolve_unit(unit: 'str') -> 'str'`

Resolve a unit name or abbreviation to the canonical ICU unit name.

Args:
    unit: Unit name or abbreviation (e.g., "km", "kilometer", "mi")

Returns:
    Canonical ICU unit name (e.g., "kilometer", "mile")

Example:
    >>> resolve_unit("km")
    'kilometer'
    >>> resolve_unit("kilometer")
    'kilometer'

## icukit.message

ICU MessageFormat for localized string formatting.

MessageFormat provides locale-aware string formatting with support for
plurals, selects, and number/date formatting within messages.

Key Features:
    * Placeholder substitution: {name}
    * Number formatting: {count, number}
    * Plural rules: {count, plural, one {# item} other {# items}}
    * Select/gender: {gender, select, male {He} female {She} other {They}}
    * Nested formatting

Example:
    >>> from icukit import format_message
    >>> format_message('Hello, {name}!', {'name': 'World'}, 'en')
    'Hello, World!'
    >>> format_message('{count, plural, one {# item} other {# items}}',
    ...                {'count': 5}, 'en')
    '5 items'

### class `MessageFormatter`

ICU MessageFormat wrapper for localized string formatting.

Supports ICU message syntax including:
    - Simple placeholders: {name}
    - Number: {count, number} or {price, number, currency}
    - Date: {date, date, short|medium|long|full}
    - Time: {time, time, short|medium|long|full}
    - Plural: {count, plural, =0 {none} one {# item} other {# items}}
    - Select: {gender, select, male {He} female {She} other {They}}
    - SelectOrdinal: {pos, selectordinal, one {#st} two {#nd} few {#rd} other {#th}}

Example:
    >>> mf = MessageFormatter('{count, plural, one {# cat} other {# cats}}', 'en')
    >>> mf.format({'count': 1})
    '1 cat'
    >>> mf.format({'count': 5})
    '5 cats'

#### `MessageFormatter(pattern: str, locale: str = 'en_US')`

Initialize a MessageFormatter.

Args:
    pattern: ICU message format pattern.
    locale: Locale for formatting rules.

Raises:
    MessageError: If the pattern is invalid.

#### `format(args: dict[str, typing.Any]) -> str`

Format the message with the given arguments.

Args:
    args: Dictionary mapping placeholder names to values.

Returns:
    Formatted string.

Raises:
    MessageError: If formatting fails.

Example:
    >>> mf = MessageFormatter('Hello, {name}!', 'en')
    >>> mf.format({'name': 'World'})
    'Hello, World!'

### `format_message(pattern: str, args: dict[str, typing.Any], locale: str = 'en_US') -> str`

Format a message with the given arguments.

Convenience function that creates a MessageFormatter for one-off use.

Args:
    pattern: ICU message format pattern.
    args: Dictionary mapping placeholder names to values.
    locale: Locale for formatting rules.

Returns:
    Formatted string.

Example:
    >>> format_message('Hello, {name}!', {'name': 'World'}, 'en')
    'Hello, World!'

    >>> format_message(
    ...     '{count, plural, one {# item} other {# items}}',
    ...     {'count': 5},
    ...     'en'
    ... )
    '5 items'

    >>> format_message(
    ...     '{gender, select, male {He} female {She} other {They}} said hi',
    ...     {'gender': 'female'},
    ...     'en'
    ... )
    'She said hi'

## icukit.parse

Locale-aware parsing of numbers, currencies, and percentages.

ICU's NumberFormat can parse locale-formatted strings back to numeric values,
handling locale-specific conventions like decimal separators, grouping
separators, and currency symbols.

Example:
    >>> from icukit import parse_number, parse_currency, parse_percent
    >>>
    >>> parse_number("1,234.56", "en_US")
    1234.56
    >>> parse_number("1.234,56", "de_DE")
    1234.56
    >>>
    >>> parse_currency("$1,234.56", "en_US")
    {'value': 1234.56, 'currency': 'USD'}
    >>> parse_currency("€1.234,56", "de_DE")
    {'value': 1234.56, 'currency': 'EUR'}
    >>>
    >>> parse_percent("50%", "en_US")
    0.5

### class `NumberParser`

Locale-aware number parser.

Parses numbers, currencies, and percentages according to locale conventions.

Example:
    >>> parser = NumberParser("de_DE")
    >>> parser.parse_number("1.234,56")
    1234.56
    >>> parser.parse_currency("€1.234,56")
    {'value': 1234.56, 'currency': 'EUR'}

#### `NumberParser(locale: str = 'en_US')`

Create a NumberParser for the given locale.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP")

#### `parse_currency(text: str, lenient: bool = True) -> dict`

Parse a locale-formatted currency string.

Args:
    text: Currency string to parse (e.g., "$1,234.56" or "€1.234,56")
    lenient: If True, be lenient with formatting variations

Returns:
    Dictionary with 'value' (float) and 'currency' (ISO code)

Raises:
    ParseError: If parsing fails

Example:
    >>> parser = NumberParser("en_US")
    >>> parser.parse_currency("$1,234.56")
    {'value': 1234.56, 'currency': 'USD'}

#### `parse_number(text: str, lenient: bool = True) -> float`

Parse a locale-formatted number string.

Args:
    text: Number string to parse (e.g., "1,234.56" or "1.234,56")
    lenient: If True, be lenient with formatting variations

Returns:
    Parsed numeric value

Raises:
    ParseError: If parsing fails

Example:
    >>> parser = NumberParser("en_US")
    >>> parser.parse_number("1,234.56")
    1234.56
    >>> parser = NumberParser("de_DE")
    >>> parser.parse_number("1.234,56")
    1234.56

#### `parse_percent(text: str, lenient: bool = True) -> float`

Parse a locale-formatted percentage string.

Args:
    text: Percentage string to parse (e.g., "50%" or "50 %")
    lenient: If True, be lenient with formatting variations

Returns:
    Parsed value as decimal (50% → 0.5)

Raises:
    ParseError: If parsing fails

Example:
    >>> parser = NumberParser("en_US")
    >>> parser.parse_percent("50%")
    0.5
    >>> parser.parse_percent("125%")
    1.25

### `parse_currency(text: str, locale: str = 'en_US', lenient: bool = True) -> dict`

Parse a locale-formatted currency string (convenience function).

Args:
    text: Currency string to parse
    locale: Locale code
    lenient: If True, be lenient with formatting variations

Returns:
    Dictionary with 'value' and 'currency'

Example:
    >>> parse_currency("$1,234.56", "en_US")
    {'value': 1234.56, 'currency': 'USD'}
    >>> parse_currency("€1.234,56", "de_DE")
    {'value': 1234.56, 'currency': 'EUR'}

### `parse_number(text: str, locale: str = 'en_US', lenient: bool = True) -> float`

Parse a locale-formatted number string (convenience function).

Args:
    text: Number string to parse
    locale: Locale code
    lenient: If True, be lenient with formatting variations

Returns:
    Parsed numeric value

Example:
    >>> parse_number("1,234.56", "en_US")
    1234.56
    >>> parse_number("1.234,56", "de_DE")
    1234.56

### `parse_percent(text: str, locale: str = 'en_US', lenient: bool = True) -> float`

Parse a locale-formatted percentage string (convenience function).

Args:
    text: Percentage string to parse
    locale: Locale code
    lenient: If True, be lenient with formatting variations

Returns:
    Parsed value as decimal (50% → 0.5)

Example:
    >>> parse_percent("50%", "en_US")
    0.5

## icukit.plural

Locale-aware plural rules.

ICU's PluralRules determines which plural category (one, two, few, many, other)
a number falls into for a given locale.

Plural Categories:
    zero  - For 0 in some languages (Arabic)
    one   - Singular form (1 in English, but more complex in other languages)
    two   - Dual form (Arabic, Hebrew, Slovenian)
    few   - Paucal form (2-4 in Slavic languages)
    many  - "Many" category (5+ in Slavic, 11-99 in Maltese)
    other - General plural (default fallback)

Example:
    >>> from icukit import get_plural_category, list_plural_categories
    >>>
    >>> get_plural_category(1, "en")
    'one'
    >>> get_plural_category(2, "en")
    'other'
    >>> get_plural_category(1, "ru")
    'one'
    >>> get_plural_category(2, "ru")
    'few'
    >>> get_plural_category(5, "ru")
    'many'
    >>>
    >>> list_plural_categories("ar")
    ['zero', 'one', 'two', 'few', 'many', 'other']

### `get_ordinal_category(number: int | float, locale: str = 'en_US') -> str`

Get the ordinal category for a number.

Ordinal categories are used for "1st", "2nd", "3rd", etc.

Args:
    number: The number to categorize
    locale: Locale code

Returns:
    Ordinal category: "zero", "one", "two", "few", "many", or "other"

Example:
    >>> get_ordinal_category(1, "en")
    'one'
    >>> get_ordinal_category(2, "en")
    'two'
    >>> get_ordinal_category(3, "en")
    'few'
    >>> get_ordinal_category(4, "en")
    'other'

### `get_plural_category(number: int | float, locale: str = 'en_US') -> str`

Get the plural category for a number.

Args:
    number: The number to categorize
    locale: Locale code (e.g., "en_US", "ru", "ar")

Returns:
    Plural category: "zero", "one", "two", "few", "many", or "other"

Example:
    >>> get_plural_category(1, "en")
    'one'
    >>> get_plural_category(2, "en")
    'other'
    >>> get_plural_category(2, "ru")
    'few'
    >>> get_plural_category(5, "ru")
    'many'

### `get_plural_rules_info(locale: str = 'en_US') -> dict`

Get detailed plural rules information for a locale.

Args:
    locale: Locale code

Returns:
    Dictionary with:
        - locale: The locale code
        - cardinal_categories: List of cardinal plural categories
        - ordinal_categories: List of ordinal plural categories
        - examples: Sample numbers for each cardinal category

Example:
    >>> info = get_plural_rules_info("ru")
    >>> info["cardinal_categories"]
    ['one', 'few', 'many', 'other']

### `list_ordinal_categories(locale: str = 'en_US') -> list[str]`

List the ordinal categories used by a locale.

Args:
    locale: Locale code

Returns:
    List of ordinal category names used by this locale

Example:
    >>> list_ordinal_categories("en")
    ['one', 'two', 'few', 'other']

### `list_plural_categories(locale: str = 'en_US') -> list[str]`

List the plural categories used by a locale.

Args:
    locale: Locale code

Returns:
    List of category names used by this locale (subset of
    ["zero", "one", "two", "few", "many", "other"])

Example:
    >>> list_plural_categories("en")
    ['one', 'other']
    >>> list_plural_categories("ru")
    ['one', 'few', 'many', 'other']
    >>> list_plural_categories("ar")
    ['zero', 'one', 'two', 'few', 'many', 'other']

## icukit.regex

Unicode regular expression utilities using ICU.

This module provides powerful Unicode-aware regular expression capabilities that go
far beyond Python's standard re module. It supports the full range of Unicode
properties, scripts, and categories for sophisticated text matching and manipulation.

Key Features:
    * Full Unicode property support (\\p{Property} syntax)
    * Script-based matching (\\p{Script=Name})
    * Unicode category matching (\\p{Category})
    * True Unicode-aware case-insensitive matching
    * Character class operations with Unicode sets
    * Efficient find, replace, and split operations
    * Named capture groups

Unicode Properties:
    The module supports all Unicode properties including:

    * **General Categories**: \\p{L} (letters), \\p{N} (numbers), \\p{P} (punctuation)
    * **Scripts**: \\p{Script=Latin}, \\p{Script=Han}, \\p{Script=Arabic}
    * **Blocks**: \\p{InBasicLatin}, \\p{InCJKUnifiedIdeographs}
    * **Binary Properties**: \\p{Alphabetic}, \\p{Emoji}, \\p{WhiteSpace}
    * **Derived Properties**: \\p{Changes_When_Lowercased}, \\p{ID_Start}

Example:
    Basic pattern matching::

        >>> from icukit import UnicodeRegex
        >>>
        >>> # Match Greek characters
        >>> regex = UnicodeRegex(r'\\p{Script=Greek}+')
        >>> matches = regex.find_all('Hello Αθήνα World')
        >>> for match in matches:
        ...     print(f"Found: {match['text']} at {match['start']}-{match['end']}")
        Found: Αθήνα at 6-11

        >>> # Match any letter in any script
        >>> regex = UnicodeRegex(r'\\p{L}+')
        >>> words = regex.find_all('Hello κόσμος 世界')
        >>> print([m['text'] for m in words])
        ['Hello', 'κόσμος', '世界']

    Advanced Unicode matching::

        >>> # Match emoji
        >>> regex = UnicodeRegex(r'\\p{Emoji}+')
        >>> emojis = regex.find_all('Hello 👋 World 🌍!')
        >>> print([m['text'] for m in emojis])
        ['👋', '🌍']

        >>> # Match text by script with proper boundaries
        >>> regex = UnicodeRegex(r'\\b\\p{Script=Greek}+\\b')
        >>> greek = regex.find_all('The word Αθήνα means Athens')
        >>> print(greek[0]['text'])
        'Αθήνα'

    Search and replace::

        >>> # Replace all digits with X
        >>> regex = UnicodeRegex(r'\\p{N}+')
        >>> result = regex.replace('Order #12345 costs $678.90', 'XXX')
        >>> print(result)
        'Order #XXX costs $XXX.XXX'

        >>> # Use capture groups in replacement
        >>> regex = UnicodeRegex(r'(\\w+)@(\\w+\\.\\w+)')
        >>> result = regex.replace('Contact: john@example.com', r'\\1 at \\2')
        >>> print(result)
        'Contact: john at example.com'

Note:
    ICU regex syntax differs from Python's re module in several ways:
    - Use \\p{Property} instead of Unicode categories
    - Different escape sequences (use \\\\\\\\ for backslash in patterns)
    - More comprehensive Unicode support
    - Some metacharacters behave differently

See Also:
    * :func:`regex_find`: Convenience function for finding matches
    * :func:`regex_replace`: Convenience function for replacements
    * :func:`regex_split`: Convenience function for splitting

### class `UnicodeRegex`

Unicode-aware regular expression operations using ICU.

A powerful regex engine that provides full Unicode support, going beyond
Python's standard re module. It uses ICU's regex engine which implements
Unicode Technical Standard #18 for Unicode Regular Expressions.

The class provides methods for finding, matching, replacing, and splitting
text using Unicode-aware patterns. All operations return detailed match
information including positions and captured groups.

Attributes:
    pattern (str): The regex pattern string.
    flags (int): Combination of regex flags (CASE_INSENSITIVE, MULTILINE, etc.).

Pattern Syntax:
    ICU regex supports extensive Unicode property matching:

    * ``\\p{L}`` - Any letter
    * ``\\p{Script=Greek}`` - Greek script characters
    * ``\\p{Block=BasicLatin}`` - Characters in Basic Latin block
    * ``\\p{Emoji}`` - Emoji characters
    * ``\\P{...}`` - Negation (NOT the property)
    * ``\\b`` - Word boundary (Unicode-aware)
    * ``\\w``, ``\\d``, ``\\s`` - Unicode-aware word, digit, space

Example:
    Creating and using a Unicode regex::

        >>> # Match words in different scripts
        >>> regex = UnicodeRegex(r'\\b\\w+\\b')
        >>> matches = regex.find_all('Hello κόσμος 世界')
        >>> print([m['text'] for m in matches])
        ['Hello', 'κόσμος', '世界']

        >>> # Case-insensitive Unicode matching
        >>> regex = UnicodeRegex(r'café', CASE_INSENSITIVE)
        >>> print(regex.search('CAFÉ'))
        True

        >>> # Complex pattern with properties
        >>> # Match: letter, followed by digits, in parentheses
        >>> regex = UnicodeRegex(r'\\((\\p{L}+)(\\p{N}+)\\)')
        >>> match = regex.find('Code (A123) here')
        >>> print(match['groups'])
        {1: 'A', 2: '123'}

#### `UnicodeRegex(pattern: str, flags: int = 0)`

Initialize a Unicode regex.

Args:
    pattern: ICU regex pattern.
    flags: Regex flags (CASE_INSENSITIVE, MULTILINE, etc.).

Raises:
    PatternError: If the pattern is invalid.

#### `find(text: str, start: int = 0) -> Optional[Dict[str, Any]]`

Find first match in text.

Args:
    text: Text to search.
    start: Starting position.

Returns:
    Match dict with text, start, end, and groups, or None if no match.

#### `find_all(text: str) -> List[Dict[str, Any]]`

Find all matches in text.

Args:
    text: Text to search.

Returns:
    List of match dictionaries.

#### `iter_matches(text: str) -> Iterator[Dict[str, Any]]`

Iterate over matches.

Args:
    text: Text to search.

Yields:
    Match dictionaries.

#### `match(text: str) -> bool`

Check if pattern matches entire text.

Args:
    text: Text to match.

Returns:
    True if entire text matches.

#### `replace(text: str, replacement: str, limit: int = -1) -> str`

Replace matches with replacement text.

Args:
    text: Text to process.
    replacement: Replacement string (supports $1, $2 for groups).
    limit: Maximum replacements (-1 for all).

Returns:
    Text with replacements made.

#### `replace_with_callback(text: str, callback) -> str`

Replace matches using a callback function.

Args:
    text: Text to process.
    callback: Function that takes match dict and returns replacement.

Returns:
    Text with replacements made.

#### `search(text: str) -> bool`

Check if pattern exists anywhere in text.

Args:
    text: Text to search.

Returns:
    True if pattern found.

#### `split(text: str, limit: int = -1) -> List[str]`

Split text by pattern.

Args:
    text: Text to split.
    limit: Maximum splits (-1 for unlimited).

Returns:
    List of split parts.

#### `validate() -> bool`

Check if the pattern is valid.

Returns:
    True if pattern is valid.

### `list_unicode_categories() -> List[Dict[str, str]]`

List Unicode general categories with structured info.

Returns:
    List of dicts with 'code' and 'description' keys.

### `list_unicode_properties() -> List[Dict[str, Any]]`

List Unicode properties with structured info for TSV/JSON output.

Returns:
    List of dicts with 'category', 'pattern', and 'description' keys.

### `list_unicode_scripts() -> List[Dict[str, str]]`

List Unicode scripts with structured info.

Returns:
    List of dicts with 'name' and 'pattern' keys.

### `regex_find(pattern: str, text: str, flags: int = 0) -> List[Dict[str, Any]]`

Find all matches of pattern in text.

Args:
    pattern: ICU regex pattern.
    text: Text to search.
    flags: Regex flags.

Returns:
    List of match dictionaries.

### `regex_replace(pattern: str, text: str, replacement: str, flags: int = 0, limit: int = -1) -> str`

Replace pattern matches in text.

Args:
    pattern: ICU regex pattern.
    text: Text to process.
    replacement: Replacement string.
    flags: Regex flags.
    limit: Maximum replacements.

Returns:
    Text with replacements.

### `regex_split(pattern: str, text: str, flags: int = 0, limit: int = -1) -> List[str]`

Split text by pattern.

Args:
    pattern: ICU regex pattern.
    text: Text to split.
    flags: Regex flags.
    limit: Maximum splits.

Returns:
    List of split parts.

## icukit.region

Geographic region and territory information.

Query countries, territories, continents, and their relationships
using ICU's region data.

Key Features:
    * List all regions by type (territory, continent, etc.)
    * Get region info (code, numeric code, containing region)
    * Query containment hierarchy (which regions contain which)

Region Types:
    * TERRITORY - Countries and territories (US, FR, JP, etc.)
    * CONTINENT - Continents (Africa, Americas, Asia, Europe, Oceania)
    * SUBCONTINENT - Subcontinental regions (Northern America, Western Europe)
    * GROUPING - Economic/political groupings (EU, UN, etc.)
    * WORLD - The world (001)

Example:
    List and query regions::

        >>> from icukit import list_regions, get_region_info
        >>>
        >>> # List all territories (countries)
        >>> territories = list_regions('territory')
        >>> len(territories)
        257
        >>>
        >>> # Get info about a region
        >>> info = get_region_info('US')
        >>> info['name']
        'United States'
        >>> info['numeric_code']
        840
        >>> info['containing_region']
        '021'  # Northern America

### `get_contained_regions(code: str) -> List[str]`

Get regions directly contained by a region.

Args:
    code: Region code (e.g., '001' for World, '019' for Americas).

Returns:
    List of contained region codes.

Example:
    >>> # What's in the Americas?
    >>> get_contained_regions('019')
    ['005', '013', '021', '029']  # South/Central/North America, Caribbean

### `get_region_info(code: str, extended: bool = False) -> Optional[Dict[str, Any]]`

Get information about a region.

Args:
    code: Region code (e.g., 'US', 'FR', '001' for World).
    extended: Include extended attributes (contained_regions).

Returns:
    Dict with region info, or None if not found.

Example:
    >>> info = get_region_info('US')
    >>> info['code']
    'US'
    >>> info['numeric_code']
    840
    >>> info['type']
    'territory'
    >>> info = get_region_info('019', extended=True)
    >>> 'contained_regions' in info['extended']
    True

### `list_region_types() -> List[Dict[str, str]]`

List available region types.

Returns:
    List of dicts with type name and description.

Example:
    >>> types = list_region_types()
    >>> types[0]
    {'type': 'continent', 'description': 'Continents (Africa, Americas, ...)'}

### `list_regions(region_type: str = 'territory') -> List[str]`

List all regions of a given type.

Args:
    region_type: Type of regions to list. One of:
        'territory', 'continent', 'subcontinent', 'grouping', 'world'.
        Defaults to 'territory' (countries).

Returns:
    List of region codes sorted alphabetically.

Raises:
    RegionError: If region_type is invalid.

Example:
    >>> territories = list_regions('territory')
    >>> 'US' in territories
    True
    >>> continents = list_regions('continent')
    >>> len(continents)
    5

### `list_regions_info(region_type: str = 'territory') -> List[Dict[str, Any]]`

List all regions with their info.

Args:
    region_type: Type of regions to list.

Returns:
    List of dicts with region info.

Example:
    >>> regions = list_regions_info('territory')
    >>> us = next(r for r in regions if r['code'] == 'US')
    >>> us['numeric_code']
    840

## icukit.script

Unicode script detection and properties.

Detect the writing system (script) of text and query script properties.
Scripts include Latin, Greek, Cyrillic, Han, Arabic, Hebrew, and many more.

Key Features:
    * Detect script of text or individual characters
    * Check if script has case distinctions (upper/lowercase)
    * Check if script is right-to-left
    * List all available scripts

Example:
    Detect script of text::

        >>> from icukit import detect_script, is_rtl
        >>>
        >>> detect_script('Hello')
        'Latin'
        >>> detect_script('Ελληνικά')
        'Greek'
        >>> detect_script('你好')
        'Han'
        >>>
        >>> is_rtl('Hello')
        False
        >>> is_rtl('مرحبا')
        True

    Query script properties::

        >>> from icukit import get_script_info, list_scripts
        >>>
        >>> info = get_script_info('Greek')
        >>> info['is_cased']
        True
        >>> info['is_rtl']
        False
        >>>
        >>> scripts = list_scripts()
        >>> len(scripts)
        160

### `detect_script(text: str) -> str`

Detect the primary script of text.

Analyzes the first character to determine the script. For mixed-script
text, use detect_scripts() to get all scripts present.

Args:
    text: Text to analyze.

Returns:
    Script name (e.g., 'Latin', 'Greek', 'Han').

Example:
    >>> detect_script('Hello')
    'Latin'
    >>> detect_script('Ελληνικά')
    'Greek'
    >>> detect_script('你好世界')
    'Han'
    >>> detect_script('مرحبا')
    'Arabic'

### `detect_scripts(text: str) -> List[str]`

Detect all scripts present in text.

Args:
    text: Text to analyze.

Returns:
    List of unique script names found, in order of first occurrence.

Example:
    >>> detect_scripts('Hello Ελληνικά')
    ['Latin', 'Common', 'Greek']
    >>> detect_scripts('abc123')
    ['Latin', 'Common']

### `get_char_script(char: str) -> str`

Get the script of a single character.

Args:
    char: A single character.

Returns:
    Script name.

Raises:
    ValueError: If input is not a single character.

Example:
    >>> get_char_script('α')
    'Greek'
    >>> get_char_script('A')
    'Latin'
    >>> get_char_script('你')
    'Han'

### `get_script_info(script: str, extended: bool = False) -> Optional[Dict[str, Any]]`

Get information about a script.

Args:
    script: Script name (e.g., 'Greek', 'Latin') or code (e.g., 'Grek', 'Latn').
    extended: Include extended attributes (sample_char).

Returns:
    Dict with script info, or None if not found.

Raises:
    ScriptError: If script name/code is invalid.

Example:
    >>> info = get_script_info('Greek')
    >>> info['code']
    'Grek'
    >>> info['is_cased']
    True
    >>> info = get_script_info('Arabic', extended=True)
    >>> info['extended']['sample_char']
    'ب'

### `is_cased(script: str) -> bool`

Check if a script has case distinctions.

Cased scripts have uppercase and lowercase letter variants.
Examples: Latin, Greek, Cyrillic are cased. Han, Arabic, Hebrew are not.

Args:
    script: Script name or code.

Returns:
    True if script has case distinctions.

Raises:
    ScriptError: If script is invalid.

Example:
    >>> is_cased('Latin')
    True
    >>> is_cased('Greek')
    True
    >>> is_cased('Han')
    False
    >>> is_cased('Arabic')
    False

### `is_rtl(text: str) -> bool`

Check if text is in a right-to-left script.

RTL scripts include Arabic, Hebrew, Syriac, etc.

Args:
    text: Text to check.

Returns:
    True if the primary script is right-to-left.

Example:
    >>> is_rtl('Hello')
    False
    >>> is_rtl('مرحبا')
    True
    >>> is_rtl('שלום')
    True

### `list_scripts() -> List[str]`

List all available Unicode scripts.

Returns:
    List of script names sorted alphabetically.

Example:
    >>> scripts = list_scripts()
    >>> 'Latin' in scripts
    True
    >>> 'Greek' in scripts
    True

### `list_scripts_info() -> List[Dict[str, Any]]`

List all scripts with their properties.

Returns:
    List of dicts with script info: code, name, is_cased, is_rtl.

Example:
    >>> scripts = list_scripts_info()
    >>> greek = next(s for s in scripts if s['name'] == 'Greek')
    >>> greek['is_cased']
    True

## icukit.search

Locale-aware text search using ICU's StringSearch.

ICU's StringSearch provides collation-based searching that respects
language-specific rules, allowing matches like "café" to match "cafe"
when using accent-insensitive comparison.

Example:
    >>> from icukit import search_all, search_first
    >>> search_all("cafe", "Visit the café. The CAFE is open.", "fr_FR", strength="primary")
    [{'start': 10, 'end': 14, 'text': 'café'}, {'start': 20, 'end': 24, 'text': 'CAFE'}]
    >>> search_first("cafe", "The café is here", strength="primary")
    {'start': 4, 'end': 8, 'text': 'café'}

### class `StringSearcher`

Reusable locale-aware string searcher.

Useful when searching the same pattern across multiple texts,
or when you need more control over the search process.

Example:
    >>> searcher = StringSearcher("café", "en_US", strength="primary")
    >>> searcher.find_all("I love cafe and CAFÉ")
    [{'start': 7, 'end': 11, 'text': 'cafe'}, {'start': 16, 'end': 20, 'text': 'CAFÉ'}]
    >>> searcher.contains("No coffee here")
    False

#### `StringSearcher(pattern: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None)`

Create a reusable searcher for the given pattern.

Args:
    pattern: The string to search for.
    locale: Locale for collation rules.
    strength: Collation strength.

#### `contains(text: 'str') -> 'bool'`

Check if the pattern exists in text.

#### `count(text: 'str') -> 'int'`

Count matches of the pattern in text.

#### `find_all(text: 'str') -> 'list[dict[str, Any]]'`

Find all matches of the pattern in text.

#### `find_first(text: 'str') -> 'dict[str, Any] | None'`

Find the first match of the pattern in text.

#### `replace(text: 'str', replacement: 'str', count: 'int' = 0) -> 'str'`

Replace matches with replacement string.

### `search_all(pattern: 'str', text: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None) -> 'list[dict[str, Any]]'`

Find all occurrences of pattern in text using locale-aware matching.

Args:
    pattern: The string to search for.
    text: The text to search in.
    locale: Locale for collation rules (default: en_US).
    strength: Collation strength:
        - "primary" - Base letters only (café=cafe=CAFE)
        - "secondary" - Base + accents (cafe=CAFE, but café≠cafe)
        - "tertiary" - Base + accents + case (default, exact match)
        - "quaternary" - Tertiary + punctuation differences
        - "identical" - Bit-for-bit identical

Returns:
    List of match dicts with 'start', 'end', and 'text' keys.

Example:
    >>> search_all("cafe", "The café and CAFE", "en_US", strength="primary")
    [{'start': 4, 'end': 8, 'text': 'café'}, {'start': 13, 'end': 17, 'text': 'CAFE'}]

### `search_count(pattern: 'str', text: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None) -> 'int'`

Count occurrences of pattern in text.

Args:
    pattern: The string to search for.
    text: The text to search in.
    locale: Locale for collation rules (default: en_US).
    strength: Collation strength (see search_all).

Returns:
    Number of matches found.

Example:
    >>> search_count("cafe", "café, Cafe, CAFE", strength="primary")
    3

### `search_first(pattern: 'str', text: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None) -> 'dict[str, Any] | None'`

Find the first occurrence of pattern in text.

Args:
    pattern: The string to search for.
    text: The text to search in.
    locale: Locale for collation rules (default: en_US).
    strength: Collation strength (see search_all).

Returns:
    Match dict with 'start', 'end', 'text', or None if not found.

Example:
    >>> search_first("café", "Visit the cafe today", strength="primary")
    {'start': 10, 'end': 14, 'text': 'cafe'}

### `search_replace(pattern: 'str', text: 'str', replacement: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None, count: 'int' = 0) -> 'str'`

Replace occurrences of pattern in text using locale-aware matching.

Args:
    pattern: The string to search for.
    text: The text to search in.
    replacement: The replacement string.
    locale: Locale for collation rules (default: en_US).
    strength: Collation strength (see search_all).
    count: Maximum replacements (0 = unlimited).

Returns:
    Text with replacements made.

Example:
    >>> search_replace("cafe", "Visit the café", "tea", strength="primary")
    'Visit the tea'

## icukit.spoof

Confusable and homoglyph detection using ICU's SpoofChecker.

ICU's SpoofChecker detects visually confusable strings that could be used
in phishing or spoofing attacks (e.g., Cyrillic "а" vs Latin "a").

Example:
    >>> from icukit import are_confusable, get_skeleton
    >>> are_confusable("paypal", "pаypal")  # Cyrillic 'а'
    True
    >>> get_skeleton("pаypal")
    'paypal'

### class `SpoofChecker`

Reusable spoof checker for multiple operations.

Example:
    >>> checker = SpoofChecker()
    >>> checker.are_confusable("paypal", "pаypal")
    True
    >>> checker.get_skeleton("pаypal")
    'paypal'

#### `SpoofChecker()`

Create a new SpoofChecker.

#### `are_confusable(string1: str, string2: str) -> bool`

Check if two strings are confusable.

#### `check(text: str) -> dict[str, typing.Any]`

Check string for spoofing issues.

#### `get_confusable_type(string1: str, string2: str) -> int`

Get confusability type between two strings.

#### `get_skeleton(text: str) -> str`

Get skeleton form of a string.

### `are_confusable(string1: str, string2: str) -> bool`

Check if two strings are visually confusable.

Two strings are confusable if they could be mistaken for each other,
such as when one uses lookalike characters from different scripts.

Args:
    string1: First string to compare.
    string2: Second string to compare.

Returns:
    True if the strings are confusable, False otherwise.

Example:
    >>> are_confusable("paypal", "pаypal")  # Second has Cyrillic 'а'
    True
    >>> are_confusable("hello", "world")
    False

### `check_string(text: str) -> dict[str, typing.Any]`

Check a string for potential spoofing issues.

Analyzes the string for mixed scripts, invisible characters,
and other potential security issues.

Args:
    text: String to check.

Returns:
    Dict with check results:
    - 'flags': Raw check result flags
    - 'is_suspicious': True if any issues detected
    - 'mixed_script': Contains mixed scripts
    - 'restriction_level': Restriction level issue
    - 'invisible': Contains invisible characters
    - 'mixed_numbers': Contains mixed number systems

Example:
    >>> result = check_string("pаypal")  # Cyrillic 'а'
    >>> result['is_suspicious']
    True
    >>> result['mixed_script']
    True

### `get_confusable_info(string1: str, string2: str) -> dict[str, typing.Any]`

Get detailed confusability information between two strings.

Args:
    string1: First string to compare.
    string2: Second string to compare.

Returns:
    Dict with confusability details:
    - 'confusable': Whether strings are confusable
    - 'type': Confusability type flags
    - 'type_names': List of type names
    - 'skeleton1': Skeleton of first string
    - 'skeleton2': Skeleton of second string
    - 'same_skeleton': Whether skeletons match

Example:
    >>> info = get_confusable_info("paypal", "pаypal")
    >>> info['confusable']
    True
    >>> info['type_names']
    ['mixed_script']

### `get_confusable_type(string1: str, string2: str) -> int`

Get the type of confusability between two strings.

Args:
    string1: First string to compare.
    string2: Second string to compare.

Returns:
    Bitmask indicating confusability type:
    - CONFUSABLE_NONE (0): Not confusable
    - CONFUSABLE_SINGLE_SCRIPT (1): Confusable within same script
    - CONFUSABLE_MIXED_SCRIPT (2): Confusable across scripts
    - CONFUSABLE_WHOLE_SCRIPT (4): Entire string looks like different script

Example:
    >>> get_confusable_type("paypal", "pаypal")
    2  # CONFUSABLE_MIXED_SCRIPT

### `get_skeleton(text: str) -> str`

Get the skeleton form of a string for confusability comparison.

The skeleton is a normalized form where visually similar characters
are mapped to a common representation. Two strings with the same
skeleton are confusable.

Args:
    text: String to get skeleton for.

Returns:
    Skeleton string.

Example:
    >>> get_skeleton("pаypal")  # Cyrillic 'а'
    'paypal'
    >>> get_skeleton("paypal")
    'paypal'

## icukit.timezone

Timezone information and utilities.

Query timezone data including offsets, DST rules, and display names.

Key Features:
    * List all available timezones (637+)
    * Get timezone info (offset, DST, display name)
    * Query equivalent timezone IDs
    * Get current offset for a timezone

Example:
    List and query timezones::

        >>> from icukit import list_timezones, get_timezone_info
        >>>
        >>> # List all timezones
        >>> tzs = list_timezones()
        >>> len(tzs)
        637
        >>>
        >>> # Get info about a timezone
        >>> info = get_timezone_info('America/New_York')
        >>> info['offset_hours']
        -5.0
        >>> info['uses_dst']
        True

### `get_equivalent_timezones(tz_id: str) -> List[str]`

Get equivalent timezone IDs for a timezone.

Args:
    tz_id: Timezone ID.

Returns:
    List of equivalent timezone IDs.

Example:
    >>> equivs = get_equivalent_timezones('America/New_York')
    >>> 'US/Eastern' in equivs
    True

### `get_timezone_info(tz_id: str, extended: bool = False) -> Optional[Dict[str, Any]]`

Get information about a timezone.

Args:
    tz_id: Timezone ID (e.g., 'America/New_York', 'Europe/London').
    extended: Include extended attributes (region, windows_id, equivalent_ids).

Returns:
    Dict with timezone info, or None if not found.

Example:
    >>> info = get_timezone_info('America/New_York')
    >>> info['id']
    'America/New_York'
    >>> info['display_name']
    'Eastern Standard Time'
    >>> info = get_timezone_info('America/New_York', extended=True)
    >>> info['extended']['region']
    'US'

### `get_timezone_offset(tz_id: str) -> float`

Get the current UTC offset for a timezone in hours.

Args:
    tz_id: Timezone ID.

Returns:
    Offset in hours (negative for west of UTC).

Raises:
    TimezoneError: If timezone is not found.

Example:
    >>> get_timezone_offset('America/New_York')
    -5.0  # or -4.0 during DST

### `list_timezones(country: Optional[str] = None) -> List[str]`

List all available timezone IDs.

Args:
    country: Optional ISO 3166 country code to filter by (e.g., 'US', 'DE').

Returns:
    List of timezone IDs sorted alphabetically.

Example:
    >>> tzs = list_timezones()
    >>> 'America/New_York' in tzs
    True
    >>> us_tzs = list_timezones('US')
    >>> 'America/New_York' in us_tzs
    True

### `list_timezones_info(country: Optional[str] = None) -> List[Dict[str, Any]]`

List all timezones with their info.

Args:
    country: Optional country code to filter by.

Returns:
    List of dicts with timezone info.

Example:
    >>> tzs = list_timezones_info()
    >>> nyc = next(t for t in tzs if t['id'] == 'America/New_York')
    >>> nyc['uses_dst']
    True

## icukit.transliterator

Text transliteration using ICU Transliterator.

This module provides powerful text transformation capabilities through ICU's
transliteration engine. It supports conversion between writing systems,
normalization, and custom transformation rules.

Key Features:
    * Script-to-script conversion (Latin <-> Cyrillic <-> Greek <-> Arabic, etc.)
    * Text normalization (accent removal, case conversion, etc.)
    * Built-in transliterators for common transformations
    * Custom rule-based transliterators
    * Transliterator chaining and filtering
    * Bidirectional transformations

Common Transliterators:
    * Script Conversions: Latin-Greek, Latin-Arabic, Latin-Cyrillic,
      Han-Latin, Hiragana-Katakana, and many more
    * Normalizations: NFD, NFC, NFKD, NFKC, Lower, Upper, Title
    * Specialized: Any-Publishing (ASCII-safe), Any-Accents (remove accents)

### class `CommonTransliterators`

Common pre-configured transliterators for frequent use cases.

#### `normalize(text: str, form: str = 'NFC') -> str`

Normalize Unicode text to a standard form (NFC, NFD, NFKC, NFKD).

#### `remove_accents(text: str) -> str`

Remove accents and diacritical marks from text.

#### `to_ascii(text: str) -> str`

Convert text to ASCII representation.

#### `to_latin(text: str) -> str`

Convert text from any script to Latin script.

#### `to_lower(text: str) -> str`

Convert text to lowercase using Unicode rules.

#### `to_title(text: str) -> str`

Convert text to title case using Unicode rules.

#### `to_upper(text: str) -> str`

Convert text to uppercase using Unicode rules.

### class `Transliterator`

Text transliteration using ICU's transformation engine.

Transliterators transform text from one writing system to another or apply
other text transformations like normalization or case mapping.

#### `Transliterator(transliterator_id: str, reverse: bool = False)`

Initialize a Transliterator.

Args:
    transliterator_id: ICU transliterator ID (e.g., 'Latin-Greek').
    reverse: If True, creates the inverse transliterator.

Raises:
    TransliteratorError: If the transliterator ID is not available.

#### `create_inverse() -> 'Transliterator'`

Create the inverse of this transliterator.

Returns:
    A new Transliterator that reverses this one's transformation.

Raises:
    TransliteratorError: If this transliterator has no inverse.

#### `get_source_set() -> Set[str]`

Get the set of characters this transliterator can convert.

#### `get_target_set() -> Set[str]`

Get the set of characters this transliterator can produce.

#### `transliterate(text: str) -> str`

Transform text using this transliterator.

Args:
    text: The text to transform.

Returns:
    The transformed text.

### `get_transliterator_info(transliterator_id: str) -> dict`

Get detailed information about a transliterator.

Args:
    transliterator_id: ICU transliterator ID.

Returns:
    Dictionary with transliterator info:
        - id: The transliterator ID
        - source: Source script (parsed from ID)
        - target: Target script (parsed from ID)
        - variant: Variant name if any
        - reversible: Whether inverse is available
        - elements: Number of sub-transliterators
        - max_context: Maximum context length needed

### `list_transliterators() -> List[str]`

Get list of all available transliterator IDs.

Returns:
    Sorted list of transliterator ID strings.

### `list_transliterators_info() -> List[dict]`

Get detailed info for all available transliterators.

Returns:
    List of info dicts for each transliterator.

### `transliterate(text: str, transliterator_id: str, reverse: bool = False) -> str`

Transliterate text using the specified transliterator.

Args:
    text: Text to transliterate.
    transliterator_id: ICU transliterator ID (e.g., 'Latin-Cyrillic').
    reverse: If True, uses the inverse transformation.

Returns:
    Transliterated text.

## icukit.unicode

Unicode text normalization and character properties.

Normalize text to standard Unicode forms (NFC, NFD, NFKC, NFKD) and
query Unicode character properties like names and categories.

Key Features:
    * Normalize text to NFC, NFD, NFKC, NFKD forms
    * Get Unicode character names
    * Get character categories and properties
    * Check normalization status

Normalization Forms:
    * NFC - Canonical decomposition, then canonical composition (default)
    * NFD - Canonical decomposition
    * NFKC - Compatibility decomposition, then canonical composition
    * NFKD - Compatibility decomposition

Example:
    Normalize text::

        >>> from icukit import normalize
        >>>
        >>> # Composed vs decomposed forms
        >>> text = 'café'  # may be composed or decomposed
        >>> normalize(text, 'NFC')  # composed: é is one codepoint
        'café'
        >>> normalize(text, 'NFD')  # decomposed: e + combining accent
        'café'
        >>>
        >>> # Compatibility normalization
        >>> normalize('ﬁ', 'NFKC')  # ligature to separate chars
        'fi'

    Character properties::

        >>> from icukit import get_char_name, get_char_category
        >>>
        >>> get_char_name('α')
        'GREEK SMALL LETTER ALPHA'
        >>> get_char_name('😀')
        'GRINNING FACE'
        >>>
        >>> get_char_category('A')
        'Lu'  # Letter, uppercase
        >>> get_char_category('5')
        'Nd'  # Number, decimal digit

### `get_block_characters(block_name: str) -> List[str]`

Get all characters in a specific Unicode block.

Args:
    block_name: Name of the block (e.g., 'Basic Latin').

Returns:
    List of characters in the block.

Raises:
    ValueError: If block name is invalid.

### `get_category_characters(category_code: str) -> List[str]`

Get all characters in a specific Unicode general category.

Args:
    category_code: Two-letter category code (e.g., 'Lu', 'Nd').

Returns:
    List of characters in the category.

Raises:
    ValueError: If category code is invalid.

### `get_char_category(char: str) -> str`

Get the Unicode general category of a character.

Categories are two-letter codes like 'Lu' (Letter, uppercase),
'Ll' (Letter, lowercase), 'Nd' (Number, decimal digit), etc.

Args:
    char: A single character.

Returns:
    Two-letter category code.

Raises:
    ValueError: If input is not a single character.

Example:
    >>> get_char_category('A')
    'Lu'
    >>> get_char_category('a')
    'Ll'
    >>> get_char_category('5')
    'Nd'
    >>> get_char_category(' ')
    'Zs'
    >>> get_char_category('!')
    'Po'

### `get_char_info(char: str) -> Dict[str, Any]`

Get comprehensive information about a character.

Args:
    char: A single character.

Returns:
    Dict with character info: codepoint, name, category, script, etc.

Raises:
    ValueError: If input is not a single character.

Example:
    >>> info = get_char_info('α')
    >>> info['name']
    'GREEK SMALL LETTER ALPHA'
    >>> info['category']
    'Ll'
    >>> info['codepoint']
    'U+03B1'

### `get_char_name(char: str) -> str`

Get the Unicode name of a character.

Args:
    char: A single character.

Returns:
    Unicode character name.

Raises:
    ValueError: If input is not a single character.

Example:
    >>> get_char_name('A')
    'LATIN CAPITAL LETTER A'
    >>> get_char_name('α')
    'GREEK SMALL LETTER ALPHA'
    >>> get_char_name('你')
    'CJK UNIFIED IDEOGRAPH-4F60'
    >>> get_char_name('😀')
    'GRINNING FACE'

### `is_normalized(text: str, form: str = 'NFC') -> bool`

Check if text is already in the specified normalization form.

Args:
    text: Text to check.
    form: Normalization form to check against.

Returns:
    True if text is already normalized.

Example:
    >>> is_normalized('café', 'NFC')
    True
    >>> is_normalized('café', 'NFD')
    False  # if 'é' is composed

### `list_blocks() -> List[Dict[str, Any]]`

List all Unicode blocks.

Returns:
    List of dicts with block names and ranges.

Example:
    >>> blocks = list_blocks()
    >>> basic_latin = next(b for b in blocks if b['name'] == 'Basic Latin')
    >>> basic_latin['range']
    'U+0000-U+007F'

### `list_categories() -> List[Dict[str, str]]`

List all Unicode general categories.

Returns:
    List of dicts with category code and description.

Example:
    >>> cats = list_categories()
    >>> next(c for c in cats if c['code'] == 'Lu')
    {'code': 'Lu', 'description': 'Letter, uppercase'}

### `normalize(text: str, form: str = 'NFC') -> str`

Normalize Unicode text to a standard form.

Args:
    text: Text to normalize.
    form: Normalization form - 'NFC', 'NFD', 'NFKC', or 'NFKD'.
          Defaults to 'NFC'.

Returns:
    Normalized text.

Raises:
    NormalizationError: If form is invalid.

Example:
    >>> # NFC: Canonical composition (default)
    >>> normalize('café')
    'café'
    >>>
    >>> # NFD: Canonical decomposition
    >>> len(normalize('é', 'NFC'))
    1
    >>> len(normalize('é', 'NFD'))
    2
    >>>
    >>> # NFKC/NFKD: Compatibility normalization
    >>> normalize('ﬁ', 'NFKC')  # fi ligature
    'fi'
    >>> normalize('①', 'NFKC')  # circled digit
    '1'

## icukit.errors

Exception classes for icukit.

### class `AlphaIndexError`

Error related to alphabetic index operations.

### class `BidiError`

Error related to bidirectional text operations.

### class `BreakerError`

Error related to text breaking operations.

### class `CalendarError`

Error related to calendar operations.

### class `CollatorError`

Error related to collation operations.

### class `DateTimeError`

Error related to date/time formatting operations.

### class `DisplayNameError`

Error related to display name operations.

### class `DurationError`

Error related to duration formatting operations.

### class `FormatError`

Error related to formatting operations.

### class `ICUKitError`

Base exception for all icukit errors.

### class `IDNAError`

Error related to IDNA encoding/decoding.

### class `ListFormatError`

Error related to list formatting operations.

### class `LocaleError`

Error related to locale operations.

### class `MeasureError`

Error related to measurement formatting operations.

### class `MessageError`

Error related to message formatting operations.

### class `NormalizationError`

Error related to Unicode normalization.

### class `ParseError`

Error related to parsing operations.

### class `PatternError`

Error related to patterns (regex, date format, etc.).

### class `PluralError`

Error related to plural rules operations.

### class `RegionError`

Error related to region operations.

### class `ScriptError`

Error related to script detection operations.

### class `SearchError`

Error related to locale-aware search operations.

### class `SpoofError`

Error related to spoof/confusable detection.

### class `TimezoneError`

Error related to timezone operations.

### class `TransliteratorError`

Error related to transliteration operations.
