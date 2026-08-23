"""Compile abbreviation lexicons into a shared consumer-facing view."""

from __future__ import annotations

from dataclasses import dataclass

import icu

from .abbreviations import AbbreviationLexicon, Entry, Pattern, load_lexicon
from .errors import AbbreviationError

__all__ = ["CompiledLexicon", "PatternMatch", "compile_lexicon"]


@dataclass(frozen=True)
class PatternMatch:
    """The behavior and typed pattern kind that classified a surface."""

    behavior: str
    kind: str


@dataclass(frozen=True)
class CompiledLexicon:
    """One immutable, anti-drift view shared by abbreviation consumers.

    ``uncased-latin`` is deliberately conservative: a single dotted lowercase
    segment must be backed by a literal entry (case-insensitively), while a
    multi-part dotted lowercase surface is productive.
    """

    lexicon: AbbreviationLexicon
    entries: dict[str, Entry]
    suppress: frozenset[str]
    ambiguous: frozenset[str]
    classified_surfaces: frozenset[str]
    patterns: dict[str, Pattern]

    @classmethod
    def from_lexicon(cls, lexicon: AbbreviationLexicon) -> CompiledLexicon:
        entries = {entry.surface: entry for entry in lexicon.entries}
        return cls(
            lexicon=lexicon,
            entries=entries,
            suppress=frozenset(
                entry.surface for entry in lexicon.entries if entry.break_behavior == "suppress"
            ),
            ambiguous=frozenset(
                entry.surface for entry in lexicon.entries if entry.break_behavior == "ambiguous"
            ),
            classified_surfaces=frozenset(entries),
            patterns={pattern.kind: pattern for pattern in lexicon.patterns},
        )

    def _pattern_match(self, surface: str) -> PatternMatch | None:
        def dotted_parts(value: str) -> list[str] | None:
            if not value.endswith("."):
                return None
            parts = value[:-1].split(".")
            if not parts or any(not part or not part.isalpha() for part in parts):
                return None
            return parts

        parts = dotted_parts(surface)
        if parts is None:
            return None
        pattern = self.patterns.get("single-initial")
        if pattern is not None and len(parts) == 1 and len(parts[0]) == 1 and parts[0].isupper():
            return PatternMatch(pattern.break_behavior, pattern.kind)
        pattern = self.patterns.get("multi-part-initials")
        if pattern is not None and len(parts) >= 2 and all(len(part) == 1 for part in parts):
            return PatternMatch(pattern.break_behavior, pattern.kind)
        pattern = self.patterns.get("uncased-latin")
        if pattern is not None and surface == surface.lower() and surface.isascii():
            if len(parts) >= 2:
                return PatternMatch(pattern.break_behavior, pattern.kind)
            backing = next(
                (
                    entry
                    for entry in self.entries.values()
                    if entry.surface.casefold() == surface.casefold()
                ),
                None,
            )
            if backing is not None:
                return PatternMatch(backing.break_behavior, pattern.kind)
        return None

    def classify(self, surface: str) -> tuple[str | None, str | None]:
        """Return ``(behavior, provenance)``, preferring a literal entry."""
        entry = self.entries.get(surface)
        if entry is not None:
            return entry.break_behavior, "literal"
        match = self._pattern_match(surface)
        if match is None:
            return None, None
        return match.behavior, match.kind

    def pattern_kind(self, surface: str) -> str | None:
        """Return the matching productive kind, unless a literal wins."""
        if surface in self.entries:
            return None
        match = self._pattern_match(surface)
        return match.kind if match is not None else None


def compile_lexicon(locale: str = "en") -> CompiledLexicon | None:
    """Load and compile the language lexicon, or return ``None`` when absent.

    Locale variants use their ICU language subtag, making ``en_US`` consume
    the packaged ``en`` lexicon while unsupported languages degrade cleanly.
    """
    language = icu.Locale(locale).getLanguage() or locale
    try:
        return CompiledLexicon.from_lexicon(load_lexicon(language))
    except AbbreviationError:
        return None
