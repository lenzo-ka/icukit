"""Exception classes for icukit."""


class ICUKitError(Exception):
    """Base exception for all icukit errors."""

    pass


class LocaleError(ICUKitError):
    """Error related to locale operations."""

    pass


class FormatError(ICUKitError):
    """Error related to formatting operations."""

    pass


class ParseError(ICUKitError):
    """Error related to parsing operations."""

    pass


class PatternError(ICUKitError):
    """Error related to patterns (regex, date format, etc.)."""

    pass


class TransliteratorError(ICUKitError):
    """Error related to transliteration operations."""

    pass


class ScriptError(ICUKitError):
    """Error related to script detection operations."""

    pass


class NormalizationError(ICUKitError):
    """Error related to Unicode normalization."""

    pass


class RegionError(ICUKitError):
    """Error related to region operations."""

    pass


class TimezoneError(ICUKitError):
    """Error related to timezone operations."""

    pass


class CalendarError(ICUKitError):
    """Error related to calendar operations."""

    pass


class CollatorError(ICUKitError):
    """Error related to collation operations."""

    pass


class BidiError(ICUKitError):
    """Error related to bidirectional text operations."""

    pass


class BreakerError(ICUKitError):
    """Error related to text breaking operations."""

    pass


class MessageError(ICUKitError):
    """Error related to message formatting operations."""

    pass


class ListFormatError(ICUKitError):
    """Error related to list formatting operations."""

    pass


class DateTimeError(ICUKitError):
    """Error related to date/time formatting operations."""

    pass


class MeasureError(ICUKitError):
    """Error related to measurement formatting operations."""

    pass


class PluralError(ICUKitError):
    """Error related to plural rules operations."""

    pass


class DurationError(ICUKitError):
    """Error related to duration formatting operations."""

    pass


class DisplayNameError(ICUKitError):
    """Error related to display name operations."""

    pass


class SearchError(ICUKitError):
    """Error related to locale-aware search operations."""

    pass


class SpoofError(ICUKitError):
    """Error related to spoof/confusable detection."""

    pass


class IDNAError(ICUKitError):
    """Error related to IDNA encoding/decoding."""

    pass


class AlphaIndexError(ICUKitError):
    """Error related to alphabetic index operations."""

    pass
