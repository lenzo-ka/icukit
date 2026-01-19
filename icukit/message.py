"""
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
"""

import re
from typing import Any

import icu

from .errors import MessageError


def _convert_named_to_positional(pattern: str, locale: str) -> tuple[str, list[str]]:
    """Convert named placeholders to positional for PyICU compatibility.

    Args:
        pattern: ICU message format pattern with named placeholders.
        locale: Locale code.

    Returns:
        Tuple of (converted pattern, list of placeholder names in order).
    """
    # First, parse pattern to get actual placeholder names
    # Use a temporary formatter to extract the real names
    try:
        temp_fmt = icu.MessageFormat(pattern, icu.Locale(locale))
        names = list(temp_fmt.getFormatNames())
    except icu.ICUError:
        names = []

    if not names:
        return pattern, names

    # Replace named placeholders with positional indices
    # Only replace at word boundaries to avoid matching inside nested content
    new_pattern = pattern
    for i, name in enumerate(names):
        # Match {name} or {name, followed by space/type info
        # Use word boundary after name to avoid partial matches
        new_pattern = re.sub(
            r"\{" + re.escape(name) + r"(\}|,\s)",
            r"{" + str(i) + r"\1",
            new_pattern,
        )

    return new_pattern, names


__all__ = [
    "format_message",
    "MessageFormatter",
]


class MessageFormatter:
    """ICU MessageFormat wrapper for localized string formatting.

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
    """

    def __init__(self, pattern: str, locale: str = "en_US"):
        """Initialize a MessageFormatter.

        Args:
            pattern: ICU message format pattern.
            locale: Locale for formatting rules.

        Raises:
            MessageError: If the pattern is invalid.
        """
        self.pattern = pattern
        self.locale = locale
        try:
            self._locale_obj = icu.Locale(locale)
            # Convert named placeholders to positional for PyICU compatibility
            self._positional_pattern, self._arg_names = _convert_named_to_positional(
                pattern, locale
            )
            self._formatter = icu.MessageFormat(self._positional_pattern, self._locale_obj)
        except icu.ICUError as e:
            raise MessageError(f"Invalid message pattern: {e}") from e

    def format(self, args: dict[str, Any]) -> str:
        """Format the message with the given arguments.

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
        """
        try:
            # Build list of Formattable values in the order of arg_names
            formattable_args = []
            for name in self._arg_names:
                value = args.get(name, "")
                formattable_args.append(icu.Formattable(value))

            return self._formatter.format(formattable_args)
        except icu.ICUError as e:
            raise MessageError(f"Failed to format message: {e}") from e

    def __repr__(self) -> str:
        return f"MessageFormatter({self.pattern!r}, locale={self.locale!r})"


def format_message(
    pattern: str,
    args: dict[str, Any],
    locale: str = "en_US",
) -> str:
    """Format a message with the given arguments.

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
    """
    return MessageFormatter(pattern, locale).format(args)
