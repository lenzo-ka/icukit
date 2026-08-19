"""Resolve a universe of overlapping detections into a best non-overlapping sequence.

See ``design/H4-resolution/design.md``. The detectors DEPOSIT every candidate they find --
running them on ``1/3/2026`` yields a ``date:yMd`` over the whole span alongside the digit
fragments ``1``, ``3``, ``26``. This module weighs that universe into the maximum-weight
non-overlapping cover (1-best), or an ordering of covers that collapses to 1-best.

The weight is span length times specificity: a longer coherent match is far less likely to
be coincidental, and a match that commits to more structure (more captures) and still fits is
stronger evidence. The two axes usually agree; where they diverge the scalar weight forces the
call. Preference is soft -- when the top two covers are within a margin the resolver reports
the contest as ambiguous rather than guessing.

This is additive: :func:`~icukit.detectors.detect` is unchanged; resolution is an opt-in layer.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass

from .detectors import Detector, ValueDetection, detect

DEFAULT_EPSILON = 1.0


def weight(detection: ValueDetection) -> int:
    """A candidate's score: span length (code points) times specificity.

    Specificity is one plus the capture count -- the structure the reading commits to -- so a
    richer match wins an equal-length contest while length carries the unequal ones.
    """
    length = detection["end"] - detection["start"]
    specificity = 1 + len(detection["captures"])
    return length * specificity


@dataclass(frozen=True)
class Resolution:
    """The weighed reading of a universe of detections.

    ``best`` is the maximum-weight non-overlapping sequence in source order. ``covers`` is the
    n-best ordering of covers by descending score, with ``covers[0] == best``. ``margin`` is the
    score gap between the top two covers; ``ambiguous`` is true when that gap is below the
    refusal threshold, meaning the resolver declines to commit between them.
    """

    best: tuple[ValueDetection, ...]
    covers: tuple[tuple[ValueDetection, ...], ...]
    margin: int
    ambiguous: bool


_ScoredCover = tuple[int, tuple[ValueDetection, ...]]


def _key(detection: ValueDetection) -> tuple:
    """A canonical content key: identifies a detection independent of object identity."""
    captures = tuple((c.name, c.start, c.end) for c in detection["captures"])
    return (
        detection["start"],
        detection["end"],
        detection["type"],
        repr(detection["value"]),
        captures,
    )


def _dedupe(detections: list[ValueDetection]) -> list[ValueDetection]:
    """Drop content-identical detections so equal candidates never split a cover's weight."""
    seen: set = set()
    unique = []
    for detection in detections:
        key = _key(detection)
        if key not in seen:
            seen.add(key)
            unique.append(detection)
    return unique


def _kbest(detections: list[ValueDetection], k: int) -> list[_ScoredCover]:
    """Top-k maximum-weight non-overlapping covers, by weighted interval scheduling.

    Items are sorted by end; ``dp[i]`` holds the top-k (score, chosen-index-tuple) covers over
    the first ``i`` items. Each item either extends the best compatible earlier cover (its
    predecessor is the last item ending at or before this item's start) or is left out.
    """
    # Sort by end for the scheduling recurrence; the content key breaks equal-span ties so the
    # chosen cover is deterministic regardless of the order detections were deposited in.
    items = sorted(detections, key=lambda d: (d["end"], d["start"], _key(d)))
    ends = [d["end"] for d in items]
    dp: list[list[tuple[int, tuple[int, ...]]]] = [[(0, ())]]
    for i in range(1, len(items) + 1):
        item = items[i - 1]
        w = weight(item)
        predecessor = bisect.bisect_right(ends, item["start"], 0, i - 1)
        merged = list(dp[i - 1])  # leave item i-1 out
        merged += [(score + w, path + (i - 1,)) for score, path in dp[predecessor]]  # take it
        merged.sort(key=lambda sp: -sp[0])
        dp.append(merged[:k])
    return [
        (score, tuple(sorted((items[idx] for idx in path), key=lambda d: (d["start"], d["end"]))))
        for score, path in dp[len(items)]
    ]


def resolve(
    detections: list[ValueDetection] | tuple[ValueDetection, ...],
    *,
    n: int = 8,
    epsilon: int = DEFAULT_EPSILON,
) -> Resolution:
    """Weigh a universe of (possibly overlapping) detections into a :class:`Resolution`.

    Returns the maximum-weight non-overlapping ``best`` sequence, the ``n``-best ordering of
    covers, and an ``ambiguous`` flag when the top two covers are within ``epsilon``.
    """
    scored = _kbest(_dedupe(list(detections)), max(n, 2))
    best = scored[0][1]
    margin = scored[0][0] - scored[1][0] if len(scored) > 1 else scored[0][0]
    return Resolution(
        best=best,
        covers=tuple(cover for _, cover in scored[:n]),
        margin=margin,
        ambiguous=len(scored) > 1 and margin < epsilon,
    )


def resolve_text(
    text: str,
    detectors: list[Detector] | tuple[Detector, ...],
    *,
    n: int = 8,
    epsilon: int = DEFAULT_EPSILON,
) -> Resolution:
    """Run every detector over ``text`` and resolve the deposited universe in one call."""
    return resolve(detect(text, detectors), n=n, epsilon=epsilon)
