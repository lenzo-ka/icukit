"""ICU word tokens, caller-protected units, and token features.

Token-scoped protected spans can join ICU word segments and intervening
whitespace into one unit. Hint spans are validated but intentionally do not
change tokenization; the sentence-break rule layer will consume them later.
Locale-material extensions are likewise deferred to that later integration.

Example:
    >>> [(token["text"], token["run"]) for token in tokens("the U.S. Then", "en_US")]
    [('the', 0), ('U.S', 1), ('.', 1), ('Then', 2)]
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Literal, NotRequired, TypedDict, cast

import icu

from .breaker import break_word_spans
from .classes import char_classes
from .errors import OverlappingProtectedSpans
from .exceptions import LoadedExceptionInventory
from .shape import shape

__all__ = ["ProtectedSpan", "Token", "tokens", "token_features"]


class ProtectedSpan(TypedDict):
    """A caller-owned code-point span used as a token unit or a later hint."""

    start: int
    end: int
    type: str
    scope: NotRequired[Literal["token", "hint"]]


class Token(TypedDict):
    """A non-whitespace ICU word segment or protected token unit.

    ``protected`` is the lexicographically first type on a protected token;
    ``protected_types`` is the sorted tuple of every type on equal-extent
    protected spans.
    """

    start: int
    end: int
    text: str
    run: int
    protected: NotRequired[str]
    protected_types: NotRequired[tuple[str, ...]]


def _validated_protected(
    protected: Iterable[ProtectedSpan], text_length: int
) -> tuple[list[ProtectedSpan], list[ProtectedSpan]]:
    token_spans: list[ProtectedSpan] = []
    hints: list[ProtectedSpan] = []
    for original in protected:
        span = cast(ProtectedSpan, dict(original))
        start = span.get("start")
        end = span.get("end")
        type_name = span.get("type")
        scope = span.get("scope", "token")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or not 0 <= start < end <= text_length
        ):
            raise ValueError("protected spans must be nonempty code-point ranges within text")
        if not isinstance(type_name, str) or not type_name:
            raise ValueError("protected span type must be a nonempty string")
        if scope not in {"token", "hint"}:
            raise ValueError("protected span scope must be 'token' or 'hint'")
        span["scope"] = scope
        (token_spans if scope == "token" else hints).append(span)

    for index, first in enumerate(token_spans):
        for second in token_spans[index + 1 :]:
            if first["start"] == second["start"] and first["end"] == second["end"]:
                continue
            overlaps = max(first["start"], second["start"]) < min(first["end"], second["end"])
            first_contains = first["start"] <= second["start"] and second["end"] <= first["end"]
            second_contains = second["start"] <= first["start"] and first["end"] <= second["end"]
            if overlaps and not (first_contains or second_contains):
                raise OverlappingProtectedSpans(
                    f"partially overlapping token spans: "
                    f"[{first['start']}, {first['end']}) and "
                    f"[{second['start']}, {second['end']})"
                )
    return token_spans, hints


def _outermost_spans(spans: list[ProtectedSpan]) -> list[tuple[int, int, tuple[str, ...]]]:
    grouped: dict[tuple[int, int], set[str]] = {}
    for span in spans:
        grouped.setdefault((span["start"], span["end"]), set()).add(span["type"])
    extents = sorted(grouped, key=lambda item: (item[0], -item[1]))
    result: list[tuple[int, int, tuple[str, ...]]] = []
    for start, end in extents:
        if any(outer_start <= start and end <= outer_end for outer_start, outer_end, _ in result):
            continue
        result.append((start, end, tuple(sorted(grouped[(start, end)]))))
    return result


def _run_labels(text: str, protected: list[tuple[int, int, tuple[str, ...]]]) -> list[int | None]:
    covered = [False] * len(text)
    for start, end, _types in protected:
        covered[start:end] = [True] * (end - start)
    labels: list[int | None] = [None] * len(text)
    current = -1
    active = False
    for index, char in enumerate(text):
        if char.isspace() and not covered[index]:
            active = False
            continue
        if not active:
            current += 1
            active = True
        labels[index] = current
    return labels


def tokens(
    text: str,
    locale: str,
    /,
    *,
    inventory: LoadedExceptionInventory | None = None,
    protected: Iterable[ProtectedSpan] = (),
) -> list[Token]:
    """Return ICU non-whitespace word segments with whitespace-run indexes.

    Token-scoped protected spans take precedence over inventory word merges and
    ICU segmentation. Nested spans use the outermost unit; partial overlaps are
    refused; equal extents produce one token carrying all sorted types.

    Example:
        >>> spans = [{"start": 5, "end": 9, "type": "range"}]
        >>> token = tokens("from 5-10 m", "en_US", protected=spans)[1]
        >>> (token["text"], token["run"], token["protected"])
        ('5-10', 1, 'range')
    """
    token_spans, _hints = _validated_protected(protected, len(text))
    protected_units = _outermost_spans(token_spans)
    icu_base = break_word_spans(text, locale)
    inventory_units: list[tuple[int, int, tuple[str, ...]]] = []
    if inventory is None:
        base = icu_base
    else:
        base = []
        for span in inventory.break_spans(text, "word", locale):
            start = span["start"]
            end = span["end"]
            if any(
                max(start, protected_start) < min(end, protected_end)
                for protected_start, protected_end, _types in protected_units
            ):
                # Protection discards an intersected inventory unit wholesale.
                # Restore ICU's boundaries before applying the protected extent,
                # rather than retaining whitespace in an inventory remainder.
                base.extend(
                    icu_span
                    for icu_span in icu_base
                    if max(start, icu_span["start"]) < min(end, icu_span["end"])
                )
            else:
                base.append(span)
                if (
                    any(char.isspace() for char in text[start:end])
                    and not text[start:end].isspace()
                ):
                    inventory_units.append((start, end, ()))
    boundaries = {0, len(text)}
    for span in base:
        boundaries.add(span["start"])
        boundaries.add(span["end"])
    for start, end, _types in protected_units:
        boundaries.add(start)
        boundaries.add(end)
        boundaries = {point for point in boundaries if not start < point < end}

    ordered = sorted(boundaries)
    protected_by_extent = {(start, end): types for start, end, types in protected_units}
    merged_units = [*protected_units, *inventory_units]
    labels = _run_labels(text, merged_units)
    result: list[Token] = []
    for start, end in zip(ordered, ordered[1:], strict=False):
        extent = (start, end)
        types = protected_by_extent.get(extent)
        if types is None and text[start:end].isspace():
            continue
        label = next((item for item in labels[start:end] if item is not None), None)
        if label is None:
            # A protected whitespace-only span is marked active by _run_labels,
            # so only an ordinary whitespace segment can reach this branch.
            continue
        token: Token = {"start": start, "end": end, "text": text[start:end], "run": label}
        if types is not None:
            token["protected"] = types[0]
            token["protected_types"] = types
        result.append(token)
    return result


def token_features(toks: Sequence[Token], i: int, text: str, /) -> dict[str, str | int | bool]:
    """Return the feature-set-v1 values for token ``i``.

    ``run.shape.cased`` covers the complete whitespace-delimited run containing
    the token. ``lex`` is reserved and is currently always ``"none"``.
    """
    token = toks[i]
    surface = token["text"]
    if not surface:
        raise ValueError("tokens must have nonempty text")
    run_tokens = [item for item in toks if item["run"] == token["run"]]
    run_start = min(item["start"] for item in run_tokens)
    run_end = max(item["end"] for item in run_tokens)
    first = surface[0]
    last = surface[-1]
    return {
        "text": surface,
        "lower": str(icu.UnicodeString(surface).toLower(icu.Locale.getRoot())),
        "len": len(surface),
        "shape.coarse": shape(surface, "coarse@1"),
        "shape.cased": shape(surface, "cased@1"),
        "general_category.first": char_classes(first, "general_category")[0],
        "general_category.last": char_classes(last, "general_category")[0],
        "sentence_break.first": char_classes(first, "sentence_break")[0],
        "word_break.first": char_classes(first, "word_break")[0],
        "script.first": char_classes(first, "script")[0],
        "ws.before": token["start"] > 0 and text[token["start"] - 1].isspace(),
        "run.shape.cased": shape(text[run_start:run_end], "cased@1"),
        "lex": "none",
    }
