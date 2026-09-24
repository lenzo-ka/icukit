"""Lexicon-driven abbreviation recognition."""

from __future__ import annotations

from dataclasses import dataclass

from .abbreviation_compile import CompiledLexicon, compile_lexicon
from .abbreviations import AbbreviationLexicon
from .detectors import Capture, DetectorSet, ValueDetection, _word_edges

__all__ = [
    "AbbreviationDetector",
    "AbbreviationExpansion",
    "AbbreviationSpec",
    "AbbreviationValue",
    "abbreviation_detectors",
    "reformat_abbreviation",
]


@dataclass(frozen=True)
class AbbreviationSpec:
    """The requested locale and source lexicon language."""

    locale: str
    source: str


@dataclass(frozen=True)
class AbbreviationExpansion:
    """One annotated expansion of an abbreviation surface.

    ``type`` is ``"expansion"`` when ``text`` is read as words, or ``"spell-out"``
    when the surface is spelled out and ``text`` lists the characters to name,
    separated by spaces (``MD`` -> ``M D``).
    """

    text: str
    sense: str
    cue: str | None = None
    type: str = "expansion"


@dataclass(frozen=True)
class AbbreviationValue:
    """An abbreviation surface and all of its co-located expansion annotations."""

    surface: str
    expansions: tuple[AbbreviationExpansion, ...] = ()
    also: str | None = None
    break_behavior: str = "suppress"


def reformat_abbreviation(spec: AbbreviationSpec, value: AbbreviationValue) -> str:
    """Return the recognized surface; expansions are annotations, not reformats."""
    return value.surface


class AbbreviationDetector:
    """Deposit one structural candidate for each recognized abbreviation surface.

    Surface identity upholds ``reformat_abbreviation(spec, value) == text``.
    Expansions are typed annotations on that candidate, never reformat operands.
    """

    group = "abbreviation"
    type = "abbreviation"

    def __init__(
        self, locale: str = "en", lexicon: AbbreviationLexicon | CompiledLexicon | None = None
    ) -> None:
        self.locale = locale
        if isinstance(lexicon, CompiledLexicon):
            self.compiled = lexicon
        elif isinstance(lexicon, AbbreviationLexicon):
            self.compiled = CompiledLexicon.from_lexicon(lexicon)
        else:
            self.compiled = compile_lexicon(locale)
        self.classified_surfaces = (
            self.compiled.classified_surfaces if self.compiled is not None else frozenset()
        )
        source = self.compiled.lexicon.language if self.compiled is not None else ""
        self.spec = AbbreviationSpec(locale, source)
        self._surfaces = tuple(sorted(self.classified_surfaces, key=len, reverse=True))

    @staticmethod
    def _left_boundary(text: str, start: int) -> bool:
        return start == 0 or not (text[start - 1].isalnum() or text[start - 1] in "_.")

    @staticmethod
    def _right_boundary(text: str, end: int) -> bool:
        return end == len(text) or not (text[end].isalnum() or text[end] == "_")

    def _detection(
        self,
        text: str,
        start: int,
        end: int,
        expansions: tuple[AbbreviationExpansion, ...],
        also: str | None,
        behavior: str,
    ) -> ValueDetection:
        surface = text[start:end]
        value = AbbreviationValue(surface, expansions, also, behavior)
        detection = ValueDetection(
            text=surface,
            start=start,
            end=end,
            type=self.type,
            value=value,
            captures=(Capture("surface", start, end, surface),),
            spec=self.spec,
        )
        assert reformat_abbreviation(self.spec, value) == detection["text"]
        return detection

    @staticmethod
    def _borrows_a_literal(surface: str, provenance: str | None) -> bool:
        """Whether a surface is classified only by matching some entry case-insensitively.

        ``uncased-latin`` backs a single dotted lowercase segment with a literal entry of
        any case. That tells the breaker how to treat the period, but it is not a
        recognition of the entry: "sun." is not "Sun." (Sunday), and borrowing its
        classification would deposit a reading with no expansions.
        """
        return provenance == "uncased-latin" and "." not in surface[:-1]

    def detect(self, text: str) -> list[ValueDetection]:
        """Scan token starts and return all co-located readings."""
        if self.compiled is None:
            return []
        # An abbreviation starts a word: "s." in "C's." is inside the word "C's".
        word_starts = _word_edges(text, self.locale)
        detections: list[ValueDetection] = []
        for start in range(len(text)):
            if (
                not text[start].isalpha()
                or start not in word_starts
                or not self._left_boundary(text, start)
            ):
                continue
            literal = next(
                (
                    surface
                    for surface in self._surfaces
                    if text.startswith(surface, start)
                    and self._right_boundary(text, start + len(surface))
                ),
                None,
            )
            if literal is not None:
                entry = self.compiled.entries[literal]
                end = start + len(literal)
                expansions = tuple(
                    AbbreviationExpansion(
                        expansion.value, expansion.sense, expansion.cue, expansion.type
                    )
                    for expansion in entry.expansions
                )
                detections.append(
                    self._detection(text, start, end, expansions, entry.also, entry.break_behavior)
                )
                continue
            end = start
            while end < len(text) and (text[end].isalpha() or text[end] == "."):
                end += 1
            surface = text[start:end]
            behavior, provenance = self.compiled.classify(surface)
            if (
                behavior is None
                or provenance in {None, "literal"}
                or self._borrows_a_literal(surface, provenance)
                or not self._right_boundary(text, end)
            ):
                continue
            detections.append(self._detection(text, start, end, (), None, behavior))
        return detections


def abbreviation_detectors(locale: str = "en") -> DetectorSet:
    """Return the locale's abbreviation detector gang, empty when unsupported."""
    detector = AbbreviationDetector(locale)
    return DetectorSet(()) if detector.compiled is None else DetectorSet((detector,))
