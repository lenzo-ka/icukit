"""Text transliteration using ICU Transliterator.

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
"""

from typing import List, Set

import icu

from .errors import TransliteratorError


class Transliterator:
    """Text transliteration using ICU's transformation engine.

    Transliterators transform text from one writing system to another or apply
    other text transformations like normalization or case mapping.
    """

    def __init__(self, transliterator_id: str, reverse: bool = False):
        """Initialize a Transliterator.

        Args:
            transliterator_id: ICU transliterator ID (e.g., 'Latin-Greek').
            reverse: If True, creates the inverse transliterator.

        Raises:
            TransliteratorError: If the transliterator ID is not available.
        """
        self.id = transliterator_id
        self.is_reverse = reverse

        try:
            if reverse:
                forward_trans = icu.Transliterator.createInstance(transliterator_id)
                self._trans = forward_trans.createInverse()
                self.id = transliterator_id + "-Inverse"
            else:
                self._trans = icu.Transliterator.createInstance(transliterator_id)
                self.id = transliterator_id
        except Exception as e:
            raise TransliteratorError(
                f"Invalid transliterator ID '{transliterator_id}'. "
                f"Error: {e}. Use list_transliterators() to see available IDs."
            ) from e

        self.display_name = self.id

    @classmethod
    def from_rules(cls, name: str, rules: str, direction: str = "FORWARD") -> "Transliterator":
        """Create a custom transliterator from rules.

        Args:
            name: A unique name for this transliterator.
            rules: Transformation rules in ICU syntax (e.g., "a > b; c > d;").
            direction: Either 'FORWARD' or 'REVERSE'.

        Returns:
            A new Transliterator instance.

        Raises:
            TransliteratorError: If the rules are invalid.
        """
        try:
            if direction.upper() == "REVERSE":
                dir_enum = icu.UTransDirection.REVERSE
            else:
                dir_enum = icu.UTransDirection.FORWARD

            trans_icu = icu.Transliterator.createFromRules(name, rules, dir_enum)

            instance = cls.__new__(cls)
            instance._trans = trans_icu
            instance.id = name
            instance.is_reverse = direction.upper() == "REVERSE"
            instance.display_name = name

            return instance

        except Exception as e:
            raise TransliteratorError(f"Invalid transliterator rules: {e}") from e

    def transliterate(self, text: str) -> str:
        """Transform text using this transliterator.

        Args:
            text: The text to transform.

        Returns:
            The transformed text.
        """
        return self._trans.transliterate(text)

    def get_source_set(self) -> Set[str]:
        """Get the set of characters this transliterator can convert."""
        uset = self._trans.getSourceSet()
        return set(icu.UnicodeSet(uset))

    def get_target_set(self) -> Set[str]:
        """Get the set of characters this transliterator can produce."""
        uset = self._trans.getTargetSet()
        return set(icu.UnicodeSet(uset))

    def create_inverse(self) -> "Transliterator":
        """Create the inverse of this transliterator.

        Returns:
            A new Transliterator that reverses this one's transformation.

        Raises:
            TransliteratorError: If this transliterator has no inverse.
        """
        try:
            inverse_trans = self._trans.createInverse()

            instance = self.__class__.__new__(self.__class__)
            instance._trans = inverse_trans
            instance.id = self.id + "-Inverse"
            instance.is_reverse = not self.is_reverse
            instance.display_name = instance.id

            return instance

        except Exception as e:
            raise TransliteratorError(
                f"Cannot create inverse of transliterator '{self.id}': {e}"
            ) from e

    def __repr__(self) -> str:
        return f"Transliterator('{self.id}', reverse={self.is_reverse})"


class CommonTransliterators:
    """Common pre-configured transliterators for frequent use cases."""

    @staticmethod
    def remove_accents(text: str) -> str:
        """Remove accents and diacritical marks from text."""
        trans = Transliterator("NFD; [:Nonspacing Mark:] Remove; NFC")
        return trans.transliterate(text)

    @staticmethod
    def to_ascii(text: str) -> str:
        """Convert text to ASCII representation."""
        trans = Transliterator("Any-Latin; Latin-ASCII")
        return trans.transliterate(text)

    @staticmethod
    def to_latin(text: str) -> str:
        """Convert text from any script to Latin script."""
        trans = Transliterator("Any-Latin")
        return trans.transliterate(text)

    @staticmethod
    def normalize(text: str, form: str = "NFC") -> str:
        """Normalize Unicode text to a standard form (NFC, NFD, NFKC, NFKD)."""
        if form not in ["NFC", "NFD", "NFKC", "NFKD"]:
            raise TransliteratorError(
                f"Invalid normalization form: {form}. Use NFC, NFD, NFKC, or NFKD."
            )
        trans = Transliterator(form)
        return trans.transliterate(text)

    @staticmethod
    def to_upper(text: str) -> str:
        """Convert text to uppercase using Unicode rules."""
        trans = Transliterator("Upper")
        return trans.transliterate(text)

    @staticmethod
    def to_lower(text: str) -> str:
        """Convert text to lowercase using Unicode rules."""
        trans = Transliterator("Lower")
        return trans.transliterate(text)

    @staticmethod
    def to_title(text: str) -> str:
        """Convert text to title case using Unicode rules."""
        trans = Transliterator("Title")
        return trans.transliterate(text)


def transliterate(text: str, transliterator_id: str, reverse: bool = False) -> str:
    """Transliterate text using the specified transliterator.

    Args:
        text: Text to transliterate.
        transliterator_id: ICU transliterator ID (e.g., 'Latin-Cyrillic').
        reverse: If True, uses the inverse transformation.

    Returns:
        Transliterated text.
    """
    trans = Transliterator(transliterator_id, reverse)
    return trans.transliterate(text)


def list_transliterators() -> List[str]:
    """Get list of all available transliterator IDs.

    Returns:
        Sorted list of transliterator ID strings.
    """
    return sorted(trans_id for trans_id in icu.Transliterator.getAvailableIDs())


def get_transliterator_info(transliterator_id: str) -> dict:
    """Get detailed information about a transliterator.

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
    """
    info = {"id": transliterator_id}

    # Parse ID for source/target/variant
    parts = transliterator_id.split("-")
    if len(parts) >= 2:
        info["source"] = parts[0]
        target_parts = parts[1].split("/")
        info["target"] = target_parts[0]
        info["variant"] = target_parts[1] if len(target_parts) > 1 else None
    else:
        # Special transliterators like NFD, Lower, etc.
        info["source"] = None
        info["target"] = None
        info["variant"] = None

    try:
        t = icu.Transliterator.createInstance(transliterator_id)
        info["elements"] = t.countElements()
        info["max_context"] = t.getMaximumContextLength()

        # Check reversibility
        try:
            t.createInverse()
            info["reversible"] = True
        except Exception:
            info["reversible"] = False

    except Exception:
        info["elements"] = None
        info["max_context"] = None
        info["reversible"] = None

    return info


def list_transliterators_info() -> List[dict]:
    """Get detailed info for all available transliterators.

    Returns:
        List of info dicts for each transliterator.
    """
    return [get_transliterator_info(tid) for tid in list_transliterators()]
