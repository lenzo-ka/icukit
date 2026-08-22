"""
Per-locale abbreviation lexicons.

An abbreviation lexicon records, for one language, the abbreviations that
should not falsely end a sentence and the (possibly ambiguous) expansions they
stand for. Lexicons are authored as XML validated by a RELAX NG grammar of
CLDR lineage (``abbreviations.rng``) and shipped alongside this module under
``data/abbreviations/``.

Two downstream consumers are served, though neither lives here:

    * a sentence breaker, which turns ``break="suppress"`` surfaces into
      break-exceptions and ``break="ambiguous"`` surfaces into deposited
      alternatives; and
    * an abbreviation recognizer, which deposits the ``<expansion>`` readings
      as competing candidates without ever forcing one.

This module only PARSES a lexicon into a typed, immutable model. Ambiguity is
preserved: an entry keeps every expansion, and ``break`` distinguishes a
surface that never ends a sentence from one that merely might.

Parsing uses the Python standard library ``xml.etree`` at runtime (no lxml
dependency). The parser forbids DTDs and entity declarations, so external
entity (XXE) and entity-expansion attacks cannot reach the lexicon. RELAX NG
validation is a development/test concern and lives in the test suite.

Example:
    >>> from icukit.abbreviations import load_lexicon
    >>> lex = load_lexicon("en")
    >>> entry = lex.get("St.")
    >>> [e.value for e in entry.expansions]
    ['Saint', 'Street']
    >>> entry.is_ambiguous_expansion
    True
"""

from __future__ import annotations

import xml.parsers.expat as expat
from dataclasses import dataclass
from pathlib import Path
from xml.etree.ElementTree import Element, TreeBuilder

from .errors import AbbreviationError

__all__ = [
    "Expansion",
    "Entry",
    "Pattern",
    "AbbreviationLexicon",
    "BREAK_SUPPRESS",
    "BREAK_AMBIGUOUS",
    "load_lexicon",
    "load_lexicon_file",
    "parse_lexicon",
    "available_locales",
]

# ``break`` values (the attribute name is a Python keyword, hence the aliases).
BREAK_SUPPRESS = "suppress"
BREAK_AMBIGUOUS = "ambiguous"

_DATA_DIR = Path(__file__).parent / "data" / "abbreviations"
# The XML namespace URI, used when reading ``xml:lang`` off the root element.
_XML_NS = "http://www.w3.org/XML/1998/namespace"


@dataclass(frozen=True)
class Expansion:
    """One expansion reading of an abbreviation surface.

    ``sense`` names the semantic class of the expansion (``title``, ``saint``,
    ``thoroughfare``, ...). ``cue`` is an optional positional hint that favors
    this reading (e.g. ``precedes-number``); it is advisory, never a rule.
    """

    value: str
    sense: str
    cue: str | None = None


@dataclass(frozen=True)
class Entry:
    """A single abbreviation surface and its expansions.

    ``break_behavior`` is ``"suppress"`` when the trailing period always
    belongs to the abbreviation (never a sentence end) or ``"ambiguous"`` when
    the surface may also legitimately end a sentence. ``also`` flags a
    competing non-abbreviation reading (``proper-name``, ``common-word``).
    """

    surface: str
    break_behavior: str
    expansions: tuple[Expansion, ...] = ()
    also: str | None = None

    @property
    def is_break_ambiguous(self) -> bool:
        """True when the surface may also end a sentence."""
        return self.break_behavior == BREAK_AMBIGUOUS

    @property
    def is_ambiguous_expansion(self) -> bool:
        """True when the surface carries more than one expansion reading."""
        return len(self.expansions) > 1


@dataclass(frozen=True)
class Pattern:
    """A productive abbreviation family, named by a typed ``kind``.

    A pattern never carries a raw regular expression: the grammar admits only
    an enumerated ``kind`` (``single-initial``, ``multi-part-initials``,
    ``uncased-latin``), and a later compiler owns the boundary semantics.
    """

    kind: str
    break_behavior: str

    @property
    def is_break_ambiguous(self) -> bool:
        """True when a match may also end a sentence."""
        return self.break_behavior == BREAK_AMBIGUOUS


@dataclass(frozen=True)
class AbbreviationLexicon:
    """The parsed abbreviation lexicon of one language.

    Entries are keyed by surface for lookup while preserving document order.
    """

    language: str
    entries: tuple[Entry, ...] = ()
    patterns: tuple[Pattern, ...] = ()
    status: str | None = None

    def get(self, surface: str) -> Entry | None:
        """Return the entry for ``surface``, or ``None`` if there is none."""
        for entry in self.entries:
            if entry.surface == surface:
                return entry
        return None

    def __contains__(self, surface: object) -> bool:
        return isinstance(surface, str) and self.get(surface) is not None

    def surfaces(self) -> tuple[str, ...]:
        """All entry surfaces, in document order."""
        return tuple(entry.surface for entry in self.entries)


def _secure_parse(data: str) -> Element:
    """Parse ``data`` into an element tree with DTDs and entities forbidden.

    Blocking the DOCTYPE (and any entity declaration) closes both external
    entity (XXE) resolution and internal entity-expansion ("billion laughs")
    attacks while staying on the standard-library parser.
    """
    builder = TreeBuilder()
    parser = expat.ParserCreate()
    parser.buffer_text = True

    def _forbid_doctype(*_args: object) -> None:
        raise AbbreviationError("DOCTYPE declarations are not permitted in abbreviation lexicons")

    def _forbid_entity(*_args: object) -> None:
        raise AbbreviationError("entity declarations are not permitted in abbreviation lexicons")

    def _forbid_external(*_args: object) -> bool:
        raise AbbreviationError("external entities are not permitted in abbreviation lexicons")

    parser.StartDoctypeDeclHandler = _forbid_doctype
    parser.EntityDeclHandler = _forbid_entity
    parser.ExternalEntityRefHandler = _forbid_external
    parser.StartElementHandler = lambda tag, attrs: builder.start(tag, attrs)
    parser.EndElementHandler = builder.end
    parser.CharacterDataHandler = builder.data

    try:
        parser.Parse(data, True)
    except expat.ExpatError as error:
        raise AbbreviationError(f"malformed abbreviation lexicon XML: {error}") from error
    return builder.close()


def _expansion_from_element(element: Element) -> Expansion:
    sense = element.get("sense")
    if not sense:
        raise AbbreviationError("<expansion> is missing its required 'sense'")
    value = (element.text or "").strip()
    if not value:
        raise AbbreviationError(f"<expansion sense='{sense}'> has no value")
    return Expansion(value=value, sense=sense, cue=element.get("cue"))


def _entry_from_element(element: Element) -> Entry:
    break_behavior = element.get("break")
    if not break_behavior:
        raise AbbreviationError("<entry> is missing its required 'break'")
    surface_element = element.find("surface")
    if surface_element is None:
        raise AbbreviationError("<entry> is missing its required <surface>")
    surface = (surface_element.text or "").strip()
    if not surface:
        raise AbbreviationError("<entry> has an empty <surface>")
    expansions = tuple(_expansion_from_element(child) for child in element.findall("expansion"))
    return Entry(
        surface=surface,
        break_behavior=break_behavior,
        expansions=expansions,
        also=element.get("also"),
    )


def _pattern_from_element(element: Element) -> Pattern:
    kind = element.get("kind")
    if not kind:
        raise AbbreviationError("<pattern> is missing its required 'kind'")
    break_behavior = element.get("break")
    if not break_behavior:
        raise AbbreviationError("<pattern> is missing its required 'break'")
    return Pattern(kind=kind, break_behavior=break_behavior)


def parse_lexicon(xml_text: str) -> AbbreviationLexicon:
    """Parse abbreviation-lexicon XML text into an ``AbbreviationLexicon``.

    The input is parsed with DTDs and entities forbidden. Structural rules
    beyond the grammar (a present surface, a nonempty expansion value) are
    checked here so the model is always well formed; RELAX NG validation of
    the full controlled vocabularies is exercised by the test suite.
    """
    root = _secure_parse(xml_text)
    if root.tag != "abbreviations":
        raise AbbreviationError(f"root element is <{root.tag}>, expected <abbreviations>")
    # The parser runs without namespace processing, so ``xml:lang`` arrives as
    # a literal attribute name; accept the namespaced form defensively too.
    language = root.get("xml:lang") or root.get(f"{{{_XML_NS}}}lang")
    if not language:
        raise AbbreviationError("<abbreviations> is missing its required 'xml:lang'")

    entries: list[Entry] = []
    patterns: list[Pattern] = []
    for child in root:
        if child.tag == "entry":
            entries.append(_entry_from_element(child))
        elif child.tag == "pattern":
            patterns.append(_pattern_from_element(child))
        else:
            raise AbbreviationError(f"unexpected element <{child.tag}> in lexicon")

    return AbbreviationLexicon(
        language=language,
        entries=tuple(entries),
        patterns=tuple(patterns),
        status=root.get("status"),
    )


def load_lexicon_file(path: str | Path) -> AbbreviationLexicon:
    """Load and parse an abbreviation lexicon from an XML file path."""
    file_path = Path(path)
    try:
        xml_text = file_path.read_text(encoding="utf-8")
    except OSError as error:
        raise AbbreviationError(f"cannot read abbreviation lexicon {file_path}: {error}") from error
    return parse_lexicon(xml_text)


def load_lexicon(language: str = "en") -> AbbreviationLexicon:
    """Load the packaged abbreviation lexicon for ``language`` (e.g. ``"en"``).

    Raises :class:`~icukit.errors.AbbreviationError` if no lexicon is shipped
    for the requested language.
    """
    file_path = _DATA_DIR / f"{language}.xml"
    if not file_path.is_file():
        available = ", ".join(available_locales()) or "none"
        raise AbbreviationError(
            f"no abbreviation lexicon for language '{language}' (available: {available})"
        )
    return load_lexicon_file(file_path)


def available_locales() -> tuple[str, ...]:
    """Return the language codes with a packaged abbreviation lexicon."""
    if not _DATA_DIR.is_dir():
        return ()
    return tuple(sorted(path.stem for path in _DATA_DIR.glob("*.xml")))
