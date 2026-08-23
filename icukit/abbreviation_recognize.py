"""Lexicon-driven abbreviation recognition."""

from __future__ import annotations

from dataclasses import dataclass

from .abbreviation_compile import CompiledLexicon, compile_lexicon
from .abbreviations import AbbreviationLexicon
from .detectors import Capture, DetectorSet, ValueDetection

__all__ = [
    "AbbreviationDetector",
    "AbbreviationSpec",
    "AbbreviationValue",
    "abbreviation_detectors",
]


@dataclass(frozen=True)
class AbbreviationSpec:
    """The requested locale and source lexicon language."""

    locale: str
    source: str


@dataclass(frozen=True)
class AbbreviationValue:
    """One abbreviation reading; ``expansion`` is absent for bare readings."""

    surface: str
    expansion: str | None
    sense: str
    cue: str | None
    also: str | None
    break_behavior: str


class AbbreviationDetector:
    """Deposit every literal expansion and productive-pattern reading.

    Expansion is interpretation rather than invertible formatting, so the
    usual ``reformat(spec, value) == surface`` invariant is intentionally
    relaxed. A zero-expansion entry deposits one ``abbreviation:none`` bare
    reading so the surface remains recognized.
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
        expansion: str | None,
        sense: str,
        cue: str | None,
        also: str | None,
        behavior: str,
    ) -> ValueDetection:
        surface = text[start:end]
        return ValueDetection(
            text=surface,
            start=start,
            end=end,
            type=f"abbreviation:{sense}",
            value=AbbreviationValue(surface, expansion, sense, cue, also, behavior),
            captures=(Capture("surface", start, end, surface),),
            spec=self.spec,
        )

    def detect(self, text: str) -> list[ValueDetection]:
        """Scan token starts and return all co-located readings."""
        if self.compiled is None:
            return []
        detections: list[ValueDetection] = []
        for start in range(len(text)):
            if not text[start].isalpha() or not self._left_boundary(text, start):
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
                if entry.expansions:
                    for expansion in entry.expansions:
                        detections.append(
                            self._detection(
                                text,
                                start,
                                end,
                                expansion.value,
                                expansion.sense,
                                expansion.cue,
                                entry.also,
                                entry.break_behavior,
                            )
                        )
                else:
                    detections.append(
                        self._detection(
                            text, start, end, None, "none", None, entry.also, entry.break_behavior
                        )
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
                or not self._right_boundary(text, end)
            ):
                continue
            detections.append(
                self._detection(text, start, end, None, provenance, None, None, behavior)
            )
        return detections


def abbreviation_detectors(locale: str = "en") -> DetectorSet:
    """Return the locale's abbreviation detector gang, empty when unsupported."""
    detector = AbbreviationDetector(locale)
    return DetectorSet(()) if detector.compiled is None else DetectorSet((detector,))
