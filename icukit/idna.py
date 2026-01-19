"""
Internationalized Domain Name (IDNA) encoding and decoding.

Converts between Unicode domain names and ASCII-compatible encoding
(Punycode), following the IDNA standard.

Example:
    >>> from icukit import idna_encode, idna_decode
    >>> idna_encode("münchen.de")
    'xn--mnchen-3ya.de'
    >>> idna_decode("xn--mnchen-3ya.de")
    'münchen.de'
"""

import icu

from .errors import IDNAError

__all__ = [
    "idna_encode",
    "idna_decode",
    "idna_encode_label",
    "idna_decode_label",
    "is_ascii_domain",
    "IDNAConverter",
]


def _get_idna() -> icu.IDNA:
    """Get default IDNA instance."""
    return icu.IDNA(icu.IDNA.DEFAULT)


def idna_encode(domain: str) -> str:
    """
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
    """
    try:
        idna = _get_idna()
        info = icu.IDNAInfo()
        result = idna.nameToASCII(domain, info)
        if info.errors():
            raise IDNAError(f"IDNA encoding error for '{domain}': error code {info.errors()}")
        return result
    except icu.ICUError as e:
        raise IDNAError(f"Failed to encode domain '{domain}': {e}") from e


def idna_decode(domain: str) -> str:
    """
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
    """
    try:
        idna = _get_idna()
        info = icu.IDNAInfo()
        result = idna.nameToUnicode(domain, info)
        if info.errors():
            raise IDNAError(f"IDNA decoding error for '{domain}': error code {info.errors()}")
        return result
    except icu.ICUError as e:
        raise IDNAError(f"Failed to decode domain '{domain}': {e}") from e


def idna_encode_label(label: str) -> str:
    """
    Encode a single domain label to ASCII.

    A label is a single component of a domain name (between dots).

    Args:
        label: Unicode label (e.g., "münchen").

    Returns:
        ASCII-encoded label (e.g., "xn--mnchen-3ya").

    Example:
        >>> idna_encode_label("münchen")
        'xn--mnchen-3ya'
    """
    try:
        idna = _get_idna()
        info = icu.IDNAInfo()
        result = idna.labelToASCII(label, info)
        if info.errors():
            raise IDNAError(f"IDNA label encoding error for '{label}': error code {info.errors()}")
        return result
    except icu.ICUError as e:
        raise IDNAError(f"Failed to encode label '{label}': {e}") from e


def idna_decode_label(label: str) -> str:
    """
    Decode a single ASCII domain label to Unicode.

    Args:
        label: ASCII-encoded label (e.g., "xn--mnchen-3ya").

    Returns:
        Unicode label (e.g., "münchen").

    Example:
        >>> idna_decode_label("xn--mnchen-3ya")
        'münchen'
    """
    try:
        idna = _get_idna()
        info = icu.IDNAInfo()
        result = idna.labelToUnicode(label, info)
        if info.errors():
            raise IDNAError(f"IDNA label decoding error for '{label}': error code {info.errors()}")
        return result
    except icu.ICUError as e:
        raise IDNAError(f"Failed to decode label '{label}': {e}") from e


def is_ascii_domain(domain: str) -> bool:
    """
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
    """
    try:
        return all(ord(c) < 128 for c in domain)
    except TypeError:
        return False


class IDNAConverter:
    """
    Reusable IDNA converter for batch operations.

    Example:
        >>> converter = IDNAConverter()
        >>> converter.encode("münchen.de")
        'xn--mnchen-3ya.de'
        >>> converter.decode("xn--mnchen-3ya.de")
        'münchen.de'
    """

    def __init__(self):
        """Create a new IDNA converter."""
        try:
            self._idna = icu.IDNA(icu.IDNA.DEFAULT)
        except icu.ICUError as e:
            raise IDNAError(f"Failed to create IDNA converter: {e}") from e

    def encode(self, domain: str) -> str:
        """Encode Unicode domain to ASCII."""
        try:
            info = icu.IDNAInfo()
            result = self._idna.nameToASCII(domain, info)
            if info.errors():
                raise IDNAError(f"IDNA encoding error: {info.errors()}")
            return result
        except icu.ICUError as e:
            raise IDNAError(f"Failed to encode domain: {e}") from e

    def decode(self, domain: str) -> str:
        """Decode ASCII domain to Unicode."""
        try:
            info = icu.IDNAInfo()
            result = self._idna.nameToUnicode(domain, info)
            if info.errors():
                raise IDNAError(f"IDNA decoding error: {info.errors()}")
            return result
        except icu.ICUError as e:
            raise IDNAError(f"Failed to decode domain: {e}") from e

    def encode_label(self, label: str) -> str:
        """Encode single label to ASCII."""
        try:
            info = icu.IDNAInfo()
            result = self._idna.labelToASCII(label, info)
            if info.errors():
                raise IDNAError(f"Label encoding error: {info.errors()}")
            return result
        except icu.ICUError as e:
            raise IDNAError(f"Failed to encode label: {e}") from e

    def decode_label(self, label: str) -> str:
        """Decode single label to Unicode."""
        try:
            info = icu.IDNAInfo()
            result = self._idna.labelToUnicode(label, info)
            if info.errors():
                raise IDNAError(f"Label decoding error: {info.errors()}")
            return result
        except icu.ICUError as e:
            raise IDNAError(f"Failed to decode label: {e}") from e

    def __repr__(self) -> str:
        return "IDNAConverter()"
