"""Tests for IDNA encoding/decoding module and CLI."""

import subprocess
import sys

from icukit import (
    IDNAConverter,
    idna_decode,
    idna_decode_label,
    idna_encode,
    idna_encode_label,
    is_ascii_domain,
)


class TestIDNALibrary:
    """Tests for IDNA library functions."""

    def test_encode_german(self):
        """Test encoding German domain."""
        result = idna_encode("münchen.de")
        assert result == "xn--mnchen-3ya.de"

    def test_decode_german(self):
        """Test decoding German domain."""
        result = idna_decode("xn--mnchen-3ya.de")
        assert result == "münchen.de"

    def test_encode_ascii(self):
        """Test encoding already-ASCII domain."""
        result = idna_encode("example.com")
        assert result == "example.com"

    def test_decode_ascii(self):
        """Test decoding already-ASCII domain."""
        result = idna_decode("example.com")
        assert result == "example.com"

    def test_roundtrip(self):
        """Test encode/decode roundtrip."""
        original = "münchen.de"
        encoded = idna_encode(original)
        decoded = idna_decode(encoded)
        assert decoded == original

    def test_encode_label(self):
        """Test encoding single label."""
        result = idna_encode_label("münchen")
        assert result == "xn--mnchen-3ya"

    def test_decode_label(self):
        """Test decoding single label."""
        result = idna_decode_label("xn--mnchen-3ya")
        assert result == "münchen"

    def test_is_ascii_domain_true(self):
        """Test is_ascii_domain with ASCII."""
        assert is_ascii_domain("example.com") is True

    def test_is_ascii_domain_false(self):
        """Test is_ascii_domain with Unicode."""
        assert is_ascii_domain("münchen.de") is False


class TestIDNAConverter:
    """Tests for IDNAConverter class."""

    def test_init(self):
        """Test converter initialization."""
        converter = IDNAConverter()
        assert converter is not None

    def test_encode(self):
        """Test encode method."""
        converter = IDNAConverter()
        result = converter.encode("münchen.de")
        assert result == "xn--mnchen-3ya.de"

    def test_decode(self):
        """Test decode method."""
        converter = IDNAConverter()
        result = converter.decode("xn--mnchen-3ya.de")
        assert result == "münchen.de"

    def test_encode_label(self):
        """Test encode_label method."""
        converter = IDNAConverter()
        result = converter.encode_label("münchen")
        assert result == "xn--mnchen-3ya"

    def test_decode_label(self):
        """Test decode_label method."""
        converter = IDNAConverter()
        result = converter.decode_label("xn--mnchen-3ya")
        assert result == "münchen"

    def test_repr(self):
        """Test string representation."""
        converter = IDNAConverter()
        assert "IDNAConverter" in repr(converter)


class TestIDNACLI:
    """Tests for IDNA CLI command."""

    def test_encode(self):
        """Test encode command."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "idna", "encode", "münchen.de"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "xn--mnchen-3ya.de" in result.stdout

    def test_decode(self):
        """Test decode command."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "idna", "decode", "xn--mnchen-3ya.de"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "münchen.de" in result.stdout

    def test_encode_stdin(self):
        """Test encode from stdin."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "idna", "encode"],
            input="münchen.de\n",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "xn--mnchen-3ya.de" in result.stdout

    def test_decode_stdin(self):
        """Test decode from stdin."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "idna", "decode"],
            input="xn--mnchen-3ya.de\n",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "münchen.de" in result.stdout

    def test_alias_punycode(self):
        """Test 'punycode' alias."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "punycode", "encode", "münchen.de"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "xn--mnchen-3ya" in result.stdout

    def test_help(self):
        """Test help output."""
        result = subprocess.run(
            [sys.executable, "-m", "icukit.cli", "idna", "help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
