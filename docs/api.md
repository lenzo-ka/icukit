# icukit API Reference

Version: 0.1.0

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

### `get_locale_info(locale_str: str, display_locale: str = 'en') -> Dict[str, Any]`

Get detailed information about a locale.

Args:
    locale_str: Locale string to get info for.
    display_locale: Locale for display names.

Returns:
    Dict with locale info including display names.

Example:
    >>> info = get_locale_info('ja_JP')
    >>> info['display_name']
    'Japanese (Japan)'
    >>> info['display_language']
    'Japanese'

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

### `get_region_info(code: str) -> Optional[Dict[str, Any]]`

Get information about a region.

Args:
    code: Region code (e.g., 'US', 'FR', '001' for World).

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

### `get_script_info(script: str) -> Optional[Dict[str, Any]]`

Get information about a script.

Args:
    script: Script name (e.g., 'Greek', 'Latin') or code (e.g., 'Grek', 'Latn').

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

### `get_timezone_info(tz_id: str) -> Optional[Dict[str, Any]]`

Get information about a timezone.

Args:
    tz_id: Timezone ID (e.g., 'America/New_York', 'Europe/London').

Returns:
    Dict with timezone info, or None if not found.

Example:
    >>> info = get_timezone_info('America/New_York')
    >>> info['id']
    'America/New_York'
    >>> info['display_name']
    'Eastern Standard Time'

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

### class `CalendarError`

Error related to calendar operations.

### class `FormatError`

Error related to formatting operations.

### class `ICUKitError`

Base exception for all icukit errors.

### class `LocaleError`

Error related to locale operations.

### class `NormalizationError`

Error related to Unicode normalization.

### class `ParseError`

Error related to parsing operations.

### class `PatternError`

Error related to patterns (regex, date format, etc.).

### class `RegionError`

Error related to region operations.

### class `ScriptError`

Error related to script detection operations.

### class `TimezoneError`

Error related to timezone operations.

### class `TransliteratorError`

Error related to transliteration operations.
