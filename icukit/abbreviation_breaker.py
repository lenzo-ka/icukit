"""Sentence-break post-filter driven by an abbreviation lexicon."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict
from unicodedata import category

from ._offsets import offset_maps, set_span_offsets
from .abbreviation_compile import CompiledLexicon, compile_lexicon
from .abbreviations import AbbreviationLexicon
from .breaker import Breaker, BreakSpan

__all__ = [
    "AbbreviationBoundary",
    "AbbreviationProvenance",
    "AbbreviationSegmentation",
    "AbbreviationSentenceBreaker",
]


class AbbreviationProvenance(TypedDict):
    """The lexicon decision responsible for merging a boundary."""

    surface: str
    break_behavior: str
    provenance: str


class AbbreviationBoundary(TypedDict):
    """An ambiguous boundary retaining both possible readings."""

    offset: int
    left_surface: str
    alternatives: list[str]


@dataclass(frozen=True)
class AbbreviationSegmentation:
    """Primary segmentation plus deposited ambiguous boundaries."""

    spans: list[BreakSpan]
    ambiguous_boundaries: list[AbbreviationBoundary]


def _candidate(text: str, boundary: int) -> tuple[str, int] | None:
    end = boundary
    while end and (
        text[end - 1].isspace()
        or category(text[end - 1]) in {"Pe", "Pf"}
        or text[end - 1] in {'"', "'"}
    ):
        end -= 1
    if not end or text[end - 1] != ".":
        return None
    start = end
    while start and (text[start - 1].isalpha() or text[start - 1] == "."):
        start -= 1
    surface = text[start:end]
    if not surface or not surface[0].isalpha():
        return None
    # The maximal scan itself supplies the left-word-boundary guard: a tail
    # such as ``p.`` in ``help.`` can never be presented independently.
    if start and (text[start - 1].isalnum() or text[start - 1] == "_"):
        return None
    return surface, end


class AbbreviationSentenceBreaker:
    """Post-filter ICU sentence spans using one compiled abbreviation lexicon."""

    def __init__(
        self, locale: str = "en_US", lexicon: AbbreviationLexicon | CompiledLexicon | None = None
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
        self._breaker = Breaker(locale)

    def segmentations(self, text: str) -> AbbreviationSegmentation:
        """Return maximally merged spans and every ambiguous boundary."""
        original = self._breaker.break_sentence_spans(text)
        if self.compiled is None or not original:
            return AbbreviationSegmentation(original, [])
        merged: list[BreakSpan] = []
        ambiguous: list[AbbreviationBoundary] = []
        maps = offset_maps(text)
        current = original[0].copy()
        provenance: list[AbbreviationProvenance] = []
        for following in original[1:]:
            found = _candidate(text, current["end"])
            behavior: str | None = None
            source: str | None = None
            if found is not None:
                behavior, source = self.compiled.classify(found[0])
            if behavior in {"suppress", "ambiguous"} and found is not None and source is not None:
                if behavior == "ambiguous":
                    ambiguous.append(
                        {
                            "offset": found[1],
                            "left_surface": found[0],
                            "alternatives": ["break", "no-break"],
                        }
                    )
                provenance.append(
                    {"surface": found[0], "break_behavior": behavior, "provenance": source}
                )
                set_span_offsets(current, current["start"], following["end"], maps)
                current["text"] = text[current["start"] : current["end"]]
                if "abbreviation" not in current["types"]:
                    current["types"].append("abbreviation")
                current["abbreviations"] = provenance
                continue
            merged.append(current)
            current = following.copy()
            provenance = []
        merged.append(current)
        # ICU sometimes already suppresses an ambiguous point (notably before
        # a number). Deposit that break alternative too; the primary reading
        # remains the unchanged/no-break ICU span.
        deposited = {boundary["offset"] for boundary in ambiguous}
        for start, character in enumerate(text):
            preceded_by_word = start and (text[start - 1].isalnum() or text[start - 1] in "_.")
            if not character.isalpha() or preceded_by_word:
                continue
            end = start
            while end < len(text) and (text[end].isalpha() or text[end] == "."):
                end += 1
            surface = text[start:end]
            behavior, _source = self.compiled.classify(surface)
            if behavior != "ambiguous" or end in deposited or not text[end:].strip():
                continue
            ambiguous.append(
                {
                    "offset": end,
                    "left_surface": surface,
                    "alternatives": ["break", "no-break"],
                }
            )
        ambiguous.sort(key=lambda boundary: boundary["offset"])
        return AbbreviationSegmentation(merged, ambiguous)

    def spans(self, text: str) -> list[BreakSpan]:
        """Return the primary maximally merged sentence spans."""
        return self.segmentations(text).spans
