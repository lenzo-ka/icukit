"""Tests for icukit errors."""

import pytest

from icukit import Transliterator
from icukit.errors import (
    FormatError,
    ICUKitError,
    LocaleError,
    ParseError,
    PatternError,
    TransliteratorError,
)


def test_exception_hierarchy():
    """All exceptions should inherit from ICUKitError."""
    assert issubclass(LocaleError, ICUKitError)
    assert issubclass(FormatError, ICUKitError)
    assert issubclass(ParseError, ICUKitError)
    assert issubclass(PatternError, ICUKitError)
    assert issubclass(TransliteratorError, ICUKitError)


def test_exceptions_are_catchable():
    """Exceptions should be raiseable and catchable."""
    try:
        raise LocaleError("test locale error")
    except ICUKitError as e:
        assert "test locale error" in str(e)

    try:
        raise FormatError("test format error")
    except ICUKitError as e:
        assert "test format error" in str(e)

    try:
        raise TransliteratorError("test transliterator error")
    except ICUKitError as e:
        assert "test transliterator error" in str(e)


def test_transliterator_error_on_invalid_id():
    """TransliteratorError should be raised for invalid transliterator ID."""
    with pytest.raises(TransliteratorError):
        Transliterator("Invalid-Nonexistent-ID")
