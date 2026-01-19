r"""Unicode regular expression utilities using ICU.

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
"""

from typing import Any, Dict, Iterator, List, Optional

import icu

from .errors import PatternError
from .script import list_scripts as _list_scripts


class UnicodeRegex:
    r"""Unicode-aware regular expression operations using ICU.

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
    """

    # Common Unicode properties for reference
    COMMON_PROPERTIES = {
        # General categories
        "Letter": r"\p{L}",
        "Lowercase": r"\p{Ll}",
        "Uppercase": r"\p{Lu}",
        "Digit": r"\p{N}",
        "Punctuation": r"\p{P}",
        "Symbol": r"\p{S}",
        "Whitespace": r"\p{Z}",
        # Scripts
        "Latin": r"\p{Script=Latin}",
        "Greek": r"\p{Script=Greek}",
        "Cyrillic": r"\p{Script=Cyrillic}",
        "Arabic": r"\p{Script=Arabic}",
        "Hebrew": r"\p{Script=Hebrew}",
        "Han": r"\p{Script=Han}",
        "Hiragana": r"\p{Script=Hiragana}",
        "Katakana": r"\p{Script=Katakana}",
        # Other properties
        "ASCII": r"[\x00-\x7F]",
        "Emoji": r"\p{Emoji}",
        "Currency": r"\p{Sc}",
        "Math": r"\p{Sm}",
    }

    def __init__(self, pattern: str, flags: int = 0):
        """Initialize a Unicode regex.

        Args:
            pattern: ICU regex pattern.
            flags: Regex flags (CASE_INSENSITIVE, MULTILINE, etc.).

        Raises:
            PatternError: If the pattern is invalid.
        """
        self.pattern = pattern
        self.flags = flags
        self._regex = None
        self._compile()

    def _compile(self):
        """Compile the regex pattern."""
        try:
            self._regex = icu.RegexPattern.compile(self.pattern, self.flags)
        except Exception as e:
            raise PatternError(f"Invalid regex pattern '{self.pattern}': {e}") from e

    @classmethod
    def list_properties(cls) -> Dict[str, str]:
        """List common Unicode properties and their patterns.

        Returns:
            Dictionary of property names to patterns.
        """
        return cls.COMMON_PROPERTIES.copy()

    @classmethod
    def list_categories(cls) -> Dict[str, str]:
        """List Unicode general categories.

        Returns:
            Dictionary of category codes to descriptions.
        """
        # Group categories (first letter) - not directly in ICU
        groups = {
            "L": "Letter",
            "M": "Mark",
            "N": "Number",
            "P": "Punctuation",
            "S": "Symbol",
            "Z": "Separator",
            "C": "Other",
        }

        # Get specific categories from ICU
        result = dict(groups)
        gc = icu.UProperty.GENERAL_CATEGORY
        min_val = icu.Char.getIntPropertyMinValue(gc)
        max_val = icu.Char.getIntPropertyMaxValue(gc)

        for i in range(min_val, max_val + 1):
            try:
                short_name = icu.Char.getPropertyValueName(
                    gc, i, icu.UPropertyNameChoice.SHORT_PROPERTY_NAME
                )
                long_name = icu.Char.getPropertyValueName(
                    gc, i, icu.UPropertyNameChoice.LONG_PROPERTY_NAME
                )
                if short_name and long_name:
                    # Convert "Uppercase_Letter" to "Uppercase Letter"
                    result[short_name] = long_name.replace("_", " ")
            except icu.ICUError:
                pass

        return result

    @classmethod
    def list_scripts(cls) -> List[str]:
        """List available Unicode scripts.

        Returns:
            Sorted list of script names.
        """
        return _list_scripts()

    @classmethod
    def escape(cls, text: str) -> str:
        """Escape special regex characters.

        Args:
            text: Text to escape.

        Returns:
            Escaped text safe for use in regex.
        """
        special_chars = r"\.^$*+?{}[]|()"
        result = []
        for char in text:
            if char in special_chars:
                result.append("\\" + char)
            else:
                result.append(char)
        return "".join(result)

    def validate(self) -> bool:
        """Check if the pattern is valid.

        Returns:
            True if pattern is valid.
        """
        return self._regex is not None

    def find(self, text: str, start: int = 0) -> Optional[Dict[str, Any]]:
        """Find first match in text.

        Args:
            text: Text to search.
            start: Starting position.

        Returns:
            Match dict with text, start, end, and groups, or None if no match.
        """
        matcher = self._regex.matcher(text)
        if matcher.find(start):
            result = {
                "text": matcher.group(),
                "start": matcher.start(),
                "end": matcher.end(),
                "groups": {},
            }

            # Get groups
            for i in range(1, matcher.groupCount() + 1):
                group_text = matcher.group(i)
                result["groups"][i] = group_text

            return result
        return None

    def find_all(self, text: str) -> List[Dict[str, Any]]:
        """Find all matches in text.

        Args:
            text: Text to search.

        Returns:
            List of match dictionaries.
        """
        matches = []
        matcher = self._regex.matcher(text)

        while matcher.find():
            match = {
                "text": matcher.group(),
                "start": matcher.start(),
                "end": matcher.end(),
                "groups": {},
            }

            # Get groups
            for i in range(1, matcher.groupCount() + 1):
                match["groups"][i] = matcher.group(i)

            matches.append(match)

        return matches

    def match(self, text: str) -> bool:
        """Check if pattern matches entire text.

        Args:
            text: Text to match.

        Returns:
            True if entire text matches.
        """
        matcher = self._regex.matcher(text)
        return matcher.matches()

    def search(self, text: str) -> bool:
        """Check if pattern exists anywhere in text.

        Args:
            text: Text to search.

        Returns:
            True if pattern found.
        """
        matcher = self._regex.matcher(text)
        return matcher.find()

    def replace(self, text: str, replacement: str, limit: int = -1) -> str:
        """Replace matches with replacement text.

        Args:
            text: Text to process.
            replacement: Replacement string (supports $1, $2 for groups).
            limit: Maximum replacements (-1 for all).

        Returns:
            Text with replacements made.
        """
        matcher = self._regex.matcher(text)

        if limit == -1:
            return matcher.replaceAll(replacement)
        elif limit == 1:
            return matcher.replaceFirst(replacement)
        else:
            # For limited replacements, do it manually
            result = []
            last_end = 0
            count = 0

            while matcher.find() and count < limit:
                result.append(text[last_end : matcher.start()])

                # Process replacement with group substitutions
                replaced = replacement
                for i in range(matcher.groupCount() + 1):
                    group_text = matcher.group(i) or ""
                    replaced = replaced.replace(f"${i}", group_text)

                result.append(replaced)
                last_end = matcher.end()
                count += 1

            result.append(text[last_end:])
            return "".join(result)

    def replace_with_callback(self, text: str, callback) -> str:
        """Replace matches using a callback function.

        Args:
            text: Text to process.
            callback: Function that takes match dict and returns replacement.

        Returns:
            Text with replacements made.
        """
        result = []
        last_end = 0

        for match in self.find_all(text):
            result.append(text[last_end : match["start"]])
            replacement = callback(match)
            result.append(replacement)
            last_end = match["end"]

        result.append(text[last_end:])
        return "".join(result)

    def split(self, text: str, limit: int = -1) -> List[str]:
        """Split text by pattern.

        Args:
            text: Text to split.
            limit: Maximum splits (-1 for unlimited).

        Returns:
            List of split parts.
        """
        parts = []
        last_end = 0
        split_count = 0

        for match in self.iter_matches(text):
            # Add the part before this match
            parts.append(text[last_end : match["start"]])
            last_end = match["end"]

            split_count += 1
            if limit > 0 and split_count >= limit:
                break

        # Add the remaining part
        parts.append(text[last_end:])

        return parts

    def iter_matches(self, text: str) -> Iterator[Dict[str, Any]]:
        """Iterate over matches.

        Args:
            text: Text to search.

        Yields:
            Match dictionaries.
        """
        matcher = self._regex.matcher(text)

        while matcher.find():
            match = {
                "text": matcher.group(),
                "start": matcher.start(),
                "end": matcher.end(),
                "groups": {},
            }

            for i in range(1, matcher.groupCount() + 1):
                match["groups"][i] = matcher.group(i)

            yield match


# Flags
CASE_INSENSITIVE = icu.URegexpFlag.CASE_INSENSITIVE
MULTILINE = icu.URegexpFlag.MULTILINE
DOTALL = icu.URegexpFlag.DOTALL
COMMENTS = icu.URegexpFlag.COMMENTS


def regex_find(pattern: str, text: str, flags: int = 0) -> List[Dict[str, Any]]:
    """Find all matches of pattern in text.

    Args:
        pattern: ICU regex pattern.
        text: Text to search.
        flags: Regex flags.

    Returns:
        List of match dictionaries.
    """
    regex = UnicodeRegex(pattern, flags)
    return regex.find_all(text)


def regex_replace(
    pattern: str, text: str, replacement: str, flags: int = 0, limit: int = -1
) -> str:
    """Replace pattern matches in text.

    Args:
        pattern: ICU regex pattern.
        text: Text to process.
        replacement: Replacement string.
        flags: Regex flags.
        limit: Maximum replacements.

    Returns:
        Text with replacements.
    """
    regex = UnicodeRegex(pattern, flags)
    return regex.replace(text, replacement, limit)


def regex_split(pattern: str, text: str, flags: int = 0, limit: int = -1) -> List[str]:
    """Split text by pattern.

    Args:
        pattern: ICU regex pattern.
        text: Text to split.
        flags: Regex flags.
        limit: Maximum splits.

    Returns:
        List of split parts.
    """
    regex = UnicodeRegex(pattern, flags)
    return regex.split(text, limit)


def list_unicode_properties() -> List[Dict[str, Any]]:
    """List Unicode properties with structured info for TSV/JSON output.

    Returns:
        List of dicts with 'category', 'pattern', and 'description' keys.
    """
    properties_by_category = {
        "Letter": {
            r"\p{L}": "Any letter",
            r"\p{Ll}": "Lowercase letter",
            r"\p{Lu}": "Uppercase letter",
            r"\p{Lt}": "Titlecase letter",
            r"\p{Lm}": "Modifier letter",
            r"\p{Lo}": "Other letter",
        },
        "Number": {
            r"\p{N}": "Any number",
            r"\p{Nd}": "Decimal digit",
            r"\p{Nl}": "Letter number",
            r"\p{No}": "Other number",
        },
        "Punctuation": {
            r"\p{P}": "Any punctuation",
            r"\p{Pc}": "Connector punctuation",
            r"\p{Pd}": "Dash punctuation",
            r"\p{Ps}": "Open punctuation",
            r"\p{Pe}": "Close punctuation",
            r"\p{Pi}": "Initial punctuation",
            r"\p{Pf}": "Final punctuation",
            r"\p{Po}": "Other punctuation",
        },
        "Symbol": {
            r"\p{S}": "Any symbol",
            r"\p{Sm}": "Math symbol",
            r"\p{Sc}": "Currency symbol",
            r"\p{Sk}": "Modifier symbol",
            r"\p{So}": "Other symbol",
        },
        "Separator": {
            r"\p{Z}": "Any separator",
            r"\p{Zs}": "Space separator",
            r"\p{Zl}": "Line separator",
            r"\p{Zp}": "Paragraph separator",
        },
        "Other": {
            r"\p{C}": "Any control/format/private-use",
            r"\p{Cc}": "Control character",
            r"\p{Cf}": "Format character",
            r"\p{Co}": "Private use",
            r"\p{Cn}": "Unassigned",
        },
    }
    result = []
    for category, props in properties_by_category.items():
        for pattern, description in props.items():
            result.append({"category": category, "pattern": pattern, "description": description})
    return result


def list_unicode_categories() -> List[Dict[str, str]]:
    """List Unicode general categories with structured info.

    Returns:
        List of dicts with 'code' and 'description' keys.
    """
    categories = UnicodeRegex.list_categories()
    return [{"code": code, "description": desc} for code, desc in categories.items()]


def list_unicode_scripts() -> List[Dict[str, str]]:
    """List Unicode scripts with structured info.

    Returns:
        List of dicts with 'name' and 'pattern' keys.
    """
    scripts = UnicodeRegex.list_scripts()
    return [{"name": s, "pattern": rf"\p{{Script={s}}}"} for s in scripts]
