"""Typed-span detectors over icukit's offset-correct surfaces.

A *detector* finds typed spans in running text -- unanchored, partial, and tolerant of
finding nothing -- as opposed to a *parser*, which is anchored and total (requires the whole
input to be one value). This module wires two ICU capabilities that already ship in icukit
into a single detector seam that produces :class:`Detection` spans:

* :func:`regex_detect` -- ICU regular expressions with **bounded** lookbehind/lookahead used
  as context conditions (F8). The regex *match* is the detection; lookaround conditions it
  without being consumed, so a rule can assert left/right context yet emit only the span it
  is about (e.g. the abbreviation period in ``Fig. 5``). ICU refuses *unbounded* lookbehind
  at compile time, so a rule needing unbounded left context is rejected rather than hosted.

* :func:`collation_detect` -- ICU collation-aware search (F9). At ``primary`` strength the
  case and accent variants of a term collapse to one inventory entry, so a single query for
  ``fig.`` matches ``fig.``, ``Fig.``, and ``FIG.`` alike.

Both return :class:`Detection` dicts whose ``start``/``end`` are **code-point** offsets into
the source -- the same convention as :class:`icukit.breaker.BreakSpan` -- so detections
compose with segmentation spans (they may nest within, or cross, a token).

This is the producer side of the seam. Consuming detections to suppress or retype
segmentation boundaries (the exception layer) is a separate, larger piece of work.
"""

from __future__ import annotations

from typing import TypedDict

from .regex import UnicodeRegex
from .search import StringSearcher

__all__ = ["Detection", "regex_detect", "collation_detect"]


class Detection(TypedDict):
    """One typed span found by a detector.

    ``start``/``end`` are code-point indices into the source text, half-open
    (``text[start:end] == text``), matching :class:`icukit.breaker.BreakSpan`.
    """

    text: str
    start: int
    end: int
    type: str


def regex_detect(
    text: str,
    pattern: str,
    type: str,
    *,
    flags: int = 0,
) -> list[Detection]:
    """Detect typed spans with an ICU regex whose match is the span.

    ``pattern`` may use bounded lookbehind ``(?<=...)`` and lookahead ``(?=...)`` to condition
    the match on surrounding context; only the match extent becomes the detection. ICU rejects
    unbounded lookbehind at compile time, so a pattern that needs it raises rather than
    silently matching -- the seam refuses an unhostable rule rather than hosting it wrong.

    Args:
        text: Source text to scan.
        pattern: ICU regex; its match extent is the detected span.
        type: Type label carried on every detection.
        flags: ICU regex flags forwarded to the matcher.

    Returns:
        Detections in source order (empty if nothing matches).

    Raises:
        Whatever :class:`icukit.regex.UnicodeRegex` raises for an invalid or unhostable
        pattern -- notably a compile error for unbounded lookbehind.
    """
    matcher = UnicodeRegex(pattern, flags)
    return [
        Detection(text=m["text"], start=m["start"], end=m["end"], type=type)
        for m in matcher.find_all(text)
    ]


def collation_detect(
    text: str,
    term: str,
    type: str,
    *,
    locale: str = "en_US",
    strength: str = "primary",
) -> list[Detection]:
    """Detect typed spans equal to ``term`` under locale collation.

    At ``primary`` strength, case and accent variants collapse, so one query matches every
    surface form of the term. Raise ``strength`` to ``secondary``/``tertiary`` to tighten the
    match (accent-, then case-sensitive).

    Args:
        text: Source text to scan.
        term: Inventory term to match under collation.
        type: Type label carried on every detection.
        locale: Collation locale.
        strength: Collation strength -- ``primary`` (loosest), ``secondary``, ``tertiary``.

    Returns:
        Detections in source order (empty if nothing matches).
    """
    searcher = StringSearcher(term, locale, strength=strength)
    return [
        Detection(text=m["text"], start=m["start"], end=m["end"], type=type)
        for m in searcher.find_all(text)
    ]
