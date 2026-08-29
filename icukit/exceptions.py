"""Corpus exception rules for ICU text segmentation.

The persisted objects in this module are deliberately JSON-shaped ``TypedDict``
records.  Loading validates and compiles all records transactionally; applications
only ever see the immutable compiled inventory.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from importlib.resources import files
from json import loads
from typing import Literal, NotRequired, TypedDict, cast

import icu

from ._offsets import OffsetMaps, offset_maps, set_span_offsets
from .breaker import (
    BreakSpan,
    break_grapheme_spans,
    break_line_spans,
    break_sentence_spans,
    break_word_spans,
)
from .detect import Detection, collation_detect, regex_detect
from .errors import ExceptionConflictError, ExceptionLoadError, RuleRefusal

__all__ = [
    "Condition",
    "ExceptionContextBounds",
    "ExceptionInventory",
    "ExceptionPolicy",
    "ExceptionRule",
    "LoadedExceptionInventory",
    "NamedListCondition",
    "Provenance",
    "SkipSpec",
    "UnicodeSetCondition",
    "Witnesses",
    "compose_inventories",
    "example_exception_inventory",
    "load_exception_inventory",
    "merge_retypes",
]

Level = Literal["sentence", "word", "line"]
Effect = Literal["suppress", "retype"]
Direction = Literal["left", "right"]
Variant = Literal["exact", "collation"]

_MANDATORY_LINE_BREAK_VALUES = frozenset(
    icu.Char.getPropertyValueEnum(icu.UProperty.LINE_BREAK, alias)
    for alias in ("BK", "CR", "LF", "NL")
)


@dataclass(frozen=True)
class ExceptionPolicy:
    """Choose how matching exception rules affect candidate boundaries.

    The defaults preserve each rule's authored effect at its declared level,
    require every condition, reject absent context, and combine compatible
    overlaps. ``retype_as`` is used by the explicit ``"retype"`` disposition.

    ``missing_context`` governs an edge of the *complete* text: a condition that
    runs off the start or end of the string with no character left to inspect.
    The text passed to :meth:`LoadedExceptionInventory.break_spans` is always
    taken to be complete. A caller feeding text incrementally must not rely on
    this dimension to describe a buffer that is merely unfinished, because a
    condition reaching past the end of a partial buffer is undetermined rather
    than absent, and either value would decide it prematurely. Such a caller
    should withhold a tail of the buffer and break only the prefix whose context
    has already arrived.

    ``mandatory_breaks`` controls whitespace-skipping conditions. ``"barrier"``
    prevents them from inspecting or crossing an ICU mandatory line-break
    sequence, while ``"cross"`` preserves the former cross-line behavior. A
    barrier-blocked condition is false regardless of ``missing_context``; a rule
    at a line start therefore behaves differently from the same rule at the true
    start of the complete text.
    """

    disposition: Literal["rule", "suppress", "retype", "mark"] = "rule"
    conditions: Literal["all", "any"] = "all"
    missing_context: Literal["fail", "match"] = "fail"
    mandatory_breaks: Literal["barrier", "cross"] = "barrier"
    overlap: Literal["combine", "first", "error"] = "combine"
    retype_as: str = "exception:match"

    def __post_init__(self) -> None:
        choices = {
            "disposition": (
                self.disposition,
                {"rule", "suppress", "retype", "mark"},
            ),
            "conditions": (self.conditions, {"all", "any"}),
            "missing_context": (self.missing_context, {"fail", "match"}),
            "mandatory_breaks": (self.mandatory_breaks, {"barrier", "cross"}),
            "overlap": (self.overlap, {"combine", "first", "error"}),
        }
        for name, (value, allowed) in choices.items():
            if value not in allowed:
                raise ValueError(f"invalid exception policy {name}: {value!r}")
        if not _TYPE_RE.fullmatch(self.retype_as):
            raise ValueError(f"invalid exception policy retype_as: {self.retype_as!r}")


class SkipSpec(TypedDict):
    kind: Literal["none", "whitespace"]
    max: NotRequired[int]


class UnicodeSetCondition(TypedDict):
    id: NotRequired[str]
    kind: Literal["unicode_set"]
    direction: Direction
    set: str
    skip: SkipSpec


class NamedListCondition(TypedDict):
    id: NotRequired[str]
    kind: Literal["named_list"]
    direction: Direction
    list: str
    skip: NotRequired[SkipSpec]


Condition = UnicodeSetCondition | NamedListCondition


class Provenance(TypedDict):
    source: str
    source_id: NotRequired[str]
    license: NotRequired[str]
    retrieved: NotRequired[str]
    note: NotRequired[str]


class Witnesses(TypedDict):
    positive: str | dict[str, object]
    near_miss: str | dict[str, object]
    condition_negatives: list[str | dict[str, object]]


class ExceptionRule(TypedDict):
    id: str
    locale: str
    level: Level | list[Level]
    effect: Effect
    type: NotRequired[str | None]
    surface: str
    variant: Variant
    strength: NotRequired[str]
    conditions: list[Condition]
    unconditionality: Literal["conditional", "empirical"]
    provenance: Provenance
    witnesses: Witnesses


class ExceptionInventory(TypedDict):
    schema_version: int
    corpus: str
    named_lists: dict[str, list[str]]
    rules: list[ExceptionRule]


_TYPE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*:[A-Za-z_][A-Za-z0-9_.-]*$")
_LOCALE_RE = re.compile(r"^(?:und|[A-Za-z]{2,8}(?:[-_][A-Za-z0-9]{1,8})*)$")
_STRENGTHS = {"primary", "secondary", "tertiary", "quaternary", "identical"}
_PUNCTUATION = icu.UnicodeSet("[[:P:]]")
_PUNCTUATION.freeze()
_RULE_KEYS = {
    "id",
    "locale",
    "level",
    "effect",
    "type",
    "surface",
    "variant",
    "strength",
    "conditions",
    "unconditionality",
    "provenance",
    "witnesses",
}


@dataclass(frozen=True)
class _CompiledCondition:
    id: str
    kind: str
    direction: Direction
    skip_kind: str
    skip_max: int | None
    unicode_set: icu.UnicodeSet | None = None
    words: frozenset[str] = frozenset()


@dataclass(frozen=True)
class _CompiledRule:
    id: str
    locale: str
    levels: tuple[Level, ...]
    effect: Effect
    type: str | None
    surface: str
    variant: Variant
    strength: str
    conditions: tuple[_CompiledCondition, ...]


@dataclass(frozen=True)
class ExceptionContextBounds:
    """Maximum code-point reach of a loaded exception inventory.

    ``right`` is measured after a match's end, and ``left`` before its start.
    ``max_surface_length`` records the longest declared surface, while
    ``right_from_match_start`` combines each rule's match extent and right
    context. Collation match extent is unbounded because collation-equivalent
    text may contain arbitrarily many ignorable code points. ``None`` means
    that direction is unbounded, while zero means that no rule inspects beyond
    the match. Direction-specific rule IDs identify every source of unbounded
    reach.

    At runtime, mandatory breaks may provide a nearer dynamic anchor: an
    incremental caller's usable horizon in each direction is the minimum of
    this static reach and the distance to the next mandatory boundary. This
    object remains inventory-only because that dynamic distance depends on the
    text being segmented.
    """

    left: int | None
    right: int | None
    max_surface_length: int
    right_from_match_start: int | None
    unbounded_rule_ids: tuple[str, ...] = ()
    unbounded_left_rule_ids: tuple[str, ...] = ()
    unbounded_right_rule_ids: tuple[str, ...] = ()


def _condition_reach(
    condition: _CompiledCondition,
) -> int | None:
    if condition.skip_max is None:
        return None
    inspected = 1
    if condition.kind == "named_list":
        # The word-break terminator is required to establish that the entire
        # adjacent token, rather than a longer token with a listed prefix, matched.
        inspected = max((len(word) for word in condition.words), default=0) + 1
    return condition.skip_max + inspected


def _context_bounds(
    rules: tuple[_CompiledRule, ...],
) -> ExceptionContextBounds:
    left = 0
    right = 0
    max_surface_length = max((len(rule.surface) for rule in rules), default=0)
    right_from_match_start = max_surface_length
    unbounded_left: list[str] = []
    unbounded_right: list[str] = []
    unbounded: list[str] = []
    unbounded_right_context = False
    for rule in rules:
        if rule.variant == "collation":
            unbounded.append(rule.id)
            unbounded_right.append(rule.id)
        for condition in rule.conditions:
            reach = _condition_reach(condition)
            if reach is None:
                if rule.id not in unbounded:
                    unbounded.append(rule.id)
                target = unbounded_left if condition.direction == "left" else unbounded_right
                if rule.id not in target:
                    target.append(rule.id)
                if condition.direction == "right":
                    unbounded_right_context = True
            elif condition.direction == "left":
                left = max(left, reach)
            else:
                right = max(right, reach)
                right_from_match_start = max(right_from_match_start, len(rule.surface) + reach)
    return ExceptionContextBounds(
        None if unbounded_left else left,
        None if unbounded_right_context else right,
        max_surface_length,
        None if unbounded_right else right_from_match_start,
        tuple(unbounded),
        tuple(unbounded_left),
        tuple(unbounded_right),
    )


def _refuse(rule_id: str, code: str, detail: str) -> RuleRefusal:
    return RuleRefusal(rule_id=rule_id, reason=code, detail=detail)


def _text(witness: object) -> str | None:
    if isinstance(witness, str):
        return witness
    if isinstance(witness, dict) and isinstance(witness.get("text"), str):
        return cast(str, witness["text"])
    return None


def _quote_regex(value: str) -> str:
    return "\\Q" + value.replace("\\E", "\\E\\\\E\\Q") + "\\E"


def _compile_condition(
    value: object,
    index: int,
    named_lists: dict[str, list[str]],
    rule_id: str,
) -> tuple[_CompiledCondition | None, list[RuleRefusal]]:
    if not isinstance(value, dict):
        return None, [_refuse(rule_id, "INVALID_CONDITION", f"condition {index} is not an object")]
    kind = value.get("kind")
    direction = value.get("direction")
    if kind not in {"unicode_set", "named_list"} or direction not in {"left", "right"}:
        return None, [_refuse(rule_id, "INVALID_CONDITION", f"condition {index} kind/direction")]
    skip = value.get("skip", {"kind": "none", "max": 0})
    if not isinstance(skip, dict) or skip.get("kind") not in {"none", "whitespace"}:
        return None, [_refuse(rule_id, "INVALID_SKIP", f"condition {index} has invalid skip")]
    skip_kind = cast(str, skip["kind"])
    maximum = skip.get("max", 0 if skip_kind == "none" else 1)
    if maximum is not None and (
        not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 0
    ):
        return None, [_refuse(rule_id, "INVALID_SKIP", f"condition {index} has invalid max")]
    if skip_kind == "whitespace" and "max" not in skip:
        # Omission uses the schema default; explicit null means unbounded.
        maximum = 1
    if skip_kind == "none" and maximum != 0:
        return None, [_refuse(rule_id, "INVALID_SKIP", "none skip requires max=0")]
    condition_id = value.get("id", str(index))
    if not isinstance(condition_id, str) or not condition_id:
        return None, [_refuse(rule_id, "INVALID_CONDITION", f"condition {index} has invalid id")]
    if kind == "unicode_set":
        pattern = value.get("set")
        if not isinstance(pattern, str) or not pattern:
            return None, [_refuse(rule_id, "INVALID_UNICODE_SET", f"condition {index}")]
        try:
            unicode_set = icu.UnicodeSet(pattern)
            unicode_set.freeze()
        except icu.ICUError as error:
            return None, [_refuse(rule_id, "INVALID_UNICODE_SET", str(error))]
        return (
            _CompiledCondition(
                condition_id,
                kind,
                cast(Direction, direction),
                skip_kind,
                maximum,
                unicode_set=unicode_set,
            ),
            [],
        )
    list_name = value.get("list")
    if not isinstance(list_name, str) or list_name not in named_lists:
        return None, [_refuse(rule_id, "UNKNOWN_NAMED_LIST", f"condition {index}: {list_name!r}")]
    words = named_lists[list_name]
    if not isinstance(words, list) or any(not isinstance(word, str) or not word for word in words):
        return None, [_refuse(rule_id, "INVALID_NAMED_LIST", list_name)]
    return (
        _CompiledCondition(
            condition_id,
            kind,
            cast(Direction, direction),
            skip_kind,
            maximum,
            words=frozenset(words),
        ),
        [],
    )


def _compile_rule(
    raw: object,
    named_lists: dict[str, list[str]],
) -> tuple[_CompiledRule | None, list[RuleRefusal]]:
    if not isinstance(raw, dict):
        return None, [_refuse("<unknown>", "INVALID_RULE", "rule is not an object")]
    rule_id = raw.get("id") if isinstance(raw.get("id"), str) else "<unknown>"
    errors: list[RuleRefusal] = []
    unknown = set(raw) - _RULE_KEYS
    if unknown:
        errors.append(_refuse(rule_id, "UNKNOWN_FIELD", ", ".join(sorted(unknown))))
    required = _RULE_KEYS - {"type", "strength"}
    missing = required - set(raw)
    if missing:
        errors.append(_refuse(rule_id, "MISSING_FIELD", ", ".join(sorted(missing))))
    locale = raw.get("locale")
    if not isinstance(locale, str) or not _LOCALE_RE.fullmatch(locale):
        errors.append(_refuse(rule_id, "INVALID_LOCALE", repr(locale)))
    level = raw.get("level")
    level_values = level if isinstance(level, list) else [level]
    valid_levels = {"sentence", "word", "line"}
    level_shape_valid = bool(level_values) and all(
        isinstance(value, str) and value in valid_levels for value in level_values
    )
    if not level_shape_valid or len(level_values) != len(set(map(repr, level_values))):
        errors.append(
            _refuse(
                rule_id,
                "INVALID_LEVEL",
                "expected a level or a nonempty list of unique levels",
            )
        )
    effect = raw.get("effect")
    if effect not in {"suppress", "retype"}:
        errors.append(_refuse(rule_id, "INVALID_EFFECT", repr(effect)))
    type_name = raw.get("type")
    if effect == "retype":
        if not isinstance(type_name, str) or not _TYPE_RE.fullmatch(type_name):
            errors.append(_refuse(rule_id, "INVALID_TYPE", repr(type_name)))
    elif type_name is not None:
        errors.append(_refuse(rule_id, "TYPE_FORBIDDEN", "suppress rules have no type"))
    surface = raw.get("surface")
    if not isinstance(surface, str) or not surface:
        errors.append(_refuse(rule_id, "INVALID_SURFACE", "surface must be a nonempty literal"))
    variant = raw.get("variant")
    if variant not in {"exact", "collation"}:
        errors.append(_refuse(rule_id, "INVALID_VARIANT", repr(variant)))
    strength = raw.get("strength", "tertiary")
    if variant == "collation" and strength not in _STRENGTHS:
        errors.append(_refuse(rule_id, "INVALID_STRENGTH", repr(strength)))
    if variant == "exact" and "strength" in raw:
        errors.append(_refuse(rule_id, "STRENGTH_FORBIDDEN", "exact rules have no strength"))
    conditions_raw = raw.get("conditions")
    if not isinstance(conditions_raw, list):
        errors.append(_refuse(rule_id, "INVALID_CONDITIONS", "conditions must be a list"))
        conditions_raw = []
    unconditionality = raw.get("unconditionality")
    if unconditionality == "structural":
        errors.append(_refuse(rule_id, "ESCALATE_STRUCTURAL", "structural rules are v2"))
    elif unconditionality not in {"conditional", "empirical"}:
        errors.append(_refuse(rule_id, "INVALID_UNCONDITIONALITY", repr(unconditionality)))
    elif unconditionality == "conditional" and not conditions_raw:
        errors.append(_refuse(rule_id, "CONDITIONS_REQUIRED", "conditional rule has no conditions"))
    elif unconditionality == "empirical" and conditions_raw:
        errors.append(_refuse(rule_id, "CONDITIONS_FORBIDDEN", "empirical rule has conditions"))
    conditions: list[_CompiledCondition] = []
    for index, condition_raw in enumerate(conditions_raw):
        condition, condition_errors = _compile_condition(condition_raw, index, named_lists, rule_id)
        errors.extend(condition_errors)
        if condition is not None:
            conditions.append(condition)
    if effect == "retype":
        for condition in conditions:
            if condition.skip_max is None:
                side = condition.direction.upper()
                errors.append(
                    _refuse(
                        rule_id,
                        f"UNHOSTABLE_UNBOUNDED_{side}",
                        "retype condition has unbounded whitespace",
                    )
                )
    for first_index, first in enumerate(conditions):
        if first.kind != "unicode_set" or first.unicode_set is None:
            continue
        for second in conditions[first_index + 1 :]:
            if (
                second.kind == "unicode_set"
                and second.direction == first.direction
                and second.skip_kind == first.skip_kind
                and second.skip_max == first.skip_max
                and second.unicode_set is not None
                and (
                    first.unicode_set.containsAll(second.unicode_set)
                    or second.unicode_set.containsAll(first.unicode_set)
                )
            ):
                errors.append(
                    _refuse(
                        rule_id,
                        "NON_SEPARABLE_CONDITIONS",
                        f"conditions {first.id!r} and {second.id!r}",
                    )
                )
    witnesses = raw.get("witnesses")
    if not isinstance(witnesses, dict):
        errors.append(_refuse(rule_id, "INVALID_WITNESSES", "witnesses must be an object"))
    else:
        negatives = witnesses.get("condition_negatives")
        if _text(witnesses.get("positive")) is None or _text(witnesses.get("near_miss")) is None:
            errors.append(_refuse(rule_id, "INVALID_WITNESSES", "positive/near_miss text required"))
        if not isinstance(negatives, list) or len(negatives) != len(conditions_raw):
            errors.append(
                _refuse(rule_id, "INVALID_CONDITION_NEGATIVES", "exactly one per condition")
            )
    if not isinstance(raw.get("provenance"), dict):
        errors.append(_refuse(rule_id, "INVALID_PROVENANCE", "provenance must be an object"))
    if errors:
        return None, errors
    return (
        _CompiledRule(
            rule_id,
            cast(str, locale),
            tuple(cast(list[Level], level_values)),
            cast(Effect, effect),
            cast(str | None, type_name),
            cast(str, surface),
            cast(Variant, variant),
            cast(str, strength),
            tuple(conditions),
        ),
        [],
    )


def _locale_applies(rule_locale: str, locale: str) -> bool:
    if rule_locale == "und":
        return True
    rule = rule_locale.replace("_", "-").lower()
    candidate = locale.replace("_", "-").lower()
    return candidate == rule or candidate.startswith(rule + "-")


def _base_spans(text: str, level: Level, locale: str) -> list[BreakSpan]:
    functions = {
        "word": break_word_spans,
        "sentence": break_sentence_spans,
        "line": break_line_spans,
    }
    return functions[level](text, locale)


def _condition_position(
    text: str,
    start: int,
    end: int,
    condition: _CompiledCondition,
    policy: ExceptionPolicy,
    mandatory_info: Callable[[], _MandatoryLineInfo],
) -> _ConditionPosition:
    step = -1 if condition.direction == "left" else 1
    position = start - 1 if step < 0 else end
    skipped = 0
    while 0 <= position < len(text):
        barrier = condition.skip_kind == "whitespace" and policy.mandatory_breaks == "barrier"
        info = mandatory_info() if barrier else None
        if info is not None and position in info.sequence_positions:
            return _ConditionPosition("barrier")
        if not text[position].isspace():
            return _ConditionPosition("found", position)
        if condition.skip_kind != "whitespace" or (
            condition.skip_max is not None and skipped == condition.skip_max
        ):
            return _ConditionPosition("found", position)
        skipped += 1
        next_position = position + step
        if info is not None and (
            next_position in info.sequence_positions
            or (step > 0 and next_position in info.boundaries)
            or (step < 0 and position in info.boundaries)
        ):
            return _ConditionPosition("barrier")
        position = next_position
    return _ConditionPosition("missing")


@dataclass(frozen=True)
class _ConditionPosition:
    outcome: Literal["found", "missing", "barrier"]
    position: int | None = None


def _condition_matches(
    condition: _CompiledCondition,
    text: str,
    start: int,
    end: int,
    locale: str,
    position: int,
) -> bool:
    if condition.kind == "unicode_set":
        assert condition.unicode_set is not None
        return condition.unicode_set.contains(text[position])
    words = break_word_spans(text, locale)
    adjacent = next(
        (
            span
            for span in words
            if "letter" in span["types"]
            and (
                (condition.direction == "right" and span["start"] == position)
                or (condition.direction == "left" and span["end"] - 1 == position)
            )
        ),
        None,
    )
    return adjacent is not None and adjacent["text"] in condition.words


def _condition_result(
    condition: _CompiledCondition,
    text: str,
    start: int,
    end: int,
    locale: str,
    policy: ExceptionPolicy,
    mandatory_info: Callable[[], _MandatoryLineInfo],
) -> bool:
    result = _condition_position(text, start, end, condition, policy, mandatory_info)
    if result.outcome == "missing":
        return policy.missing_context == "match"
    if result.outcome == "barrier":
        return False
    assert result.position is not None
    return _condition_matches(condition, text, start, end, locale, result.position)


def _anchored_exact(rule: _CompiledRule, text: str) -> list[Detection]:
    # A surface starts at a lexical boundary. This is the compiler invariant exercised by
    # the deliberately naive near-miss variant in the witness harness.
    pattern = rf"(?<![\p{{L}}\p{{N}}_]){_quote_regex(rule.surface)}"
    return regex_detect(text, pattern, cast(str, rule.type))


def _detections(
    rule: _CompiledRule,
    text: str,
    locale: str,
    policy: ExceptionPolicy | None = None,
    mandatory_info: Callable[[], _MandatoryLineInfo] | None = None,
) -> list[Detection]:
    policy = policy or ExceptionPolicy()
    mandatory_info = mandatory_info or _mandatory_info_supplier(text, locale)
    if rule.variant == "exact":
        found = _anchored_exact(rule, text)
    else:
        found = collation_detect(
            text,
            rule.surface,
            cast(str, rule.type),
            locale=locale,
            strength=rule.strength,
        )
        found = [
            item
            for item in found
            if item["start"] == 0
            or not (text[item["start"] - 1].isalnum() or text[item["start"] - 1] == "_")
        ]
    if not rule.conditions:
        return found
    predicate = all if policy.conditions == "all" else any
    return [
        item
        for item in found
        if predicate(
            _condition_result(c, text, item["start"], item["end"], locale, policy, mandatory_info)
            for c in rule.conditions
        )
    ]


def merge_retypes(
    text: str,
    base_spans: list[BreakSpan],
    detections: list[Detection],
) -> list[BreakSpan]:
    """Retype owning spans by containment; never split, replace, or coalesce them."""
    boundaries = {0, len(text)}
    for span in break_grapheme_spans(text):
        boundaries.add(span["start"])
        boundaries.add(span["end"])
    replacements: dict[int, str] = {}
    for detection in detections:
        if detection["start"] not in boundaries or detection["end"] not in boundaries:
            raise ExceptionConflictError("DETECTION_NOT_GRAPHEME_ALIGNED")
        owners = [
            index
            for index, span in enumerate(base_spans)
            if span["start"] <= detection["start"] and detection["end"] <= span["end"]
        ]
        if len(owners) != 1:
            raise ExceptionConflictError("UNHOSTABLE_NEEDS_REPLACE")
        owner = owners[0]
        previous = replacements.get(owner)
        if previous is not None and previous != detection["type"]:
            raise ExceptionConflictError("RETYPE_CONFLICT")
        replacements[owner] = detection["type"]
    result: list[BreakSpan] = []
    for index, original in enumerate(base_spans):
        span = cast(BreakSpan, dict(original))
        if index in replacements:
            span["types"] = [replacements[index]]
        result.append(span)
    return result


@dataclass(frozen=True)
class LoadedExceptionInventory:
    """An immutable, validated exception inventory."""

    corpus: str
    named_lists: dict[str, tuple[str, ...]]
    _rules: tuple[_CompiledRule, ...]

    @property
    def context_bounds(self) -> ExceptionContextBounds:
        """Return context reach derived from the inventory's compiled rules."""
        return _context_bounds(self._rules)

    def break_spans(
        self,
        text: str,
        level: Level,
        locale: str = "en_US",
        *,
        policy: ExceptionPolicy | None = None,
    ) -> list[BreakSpan]:
        """Segment ``text`` and apply matching rules under ``policy``."""
        policy = policy or ExceptionPolicy()
        selected = [
            rule
            for rule in self._rules
            if level in rule.levels and _locale_applies(rule.locale, locale)
        ]
        base = _base_spans(text, level, locale)
        mandatory_info = _mandatory_info_supplier(text, locale, base if level == "line" else None)
        boundary_rules = [
            rule for rule in selected if rule.effect == "suppress" or policy.disposition != "rule"
        ]
        claims = _boundary_claims(text, base, boundary_rules, locale, policy, mandatory_info)
        if policy.overlap == "error" and any(len(rule_ids) > 1 for rule_ids in claims.values()):
            raise ExceptionConflictError("OVERLAPPING_EXCEPTION_RULES")
        if policy.overlap == "first":
            claims = {boundary: rule_ids[:1] for boundary, rule_ids in claims.items()}
        if boundary_rules:
            if policy.disposition in {"rule", "suppress"}:
                base = _drop_boundaries(text, base, set(claims))
            elif policy.disposition == "retype":
                base = _annotate_boundaries(base, claims, policy.retype_as, mark=False)
            else:
                base = _annotate_boundaries(base, claims, policy.retype_as, mark=True)
        detections = [
            detection
            for rule in selected
            if rule.effect == "retype" and policy.disposition == "rule"
            for detection in _detections(rule, text, locale, policy, mandatory_info)
        ]
        return merge_retypes(text, base, detections)

    def apply(
        self,
        text: str,
        level: Level,
        locale: str = "en_US",
        *,
        policy: ExceptionPolicy | None = None,
    ) -> list[BreakSpan]:
        """Alias for :meth:`break_spans`."""
        return self.break_spans(text, level, locale, policy=policy)


def _merge_spans(text: str, spans: list[BreakSpan], maps: OffsetMaps) -> BreakSpan:
    merged = cast(BreakSpan, dict(spans[-1]))
    set_span_offsets(merged, spans[0]["start"], spans[-1]["end"], maps)
    merged["text"] = text[merged["start"] : merged["end"]]
    merged["types"] = list(dict.fromkeys(item for span in spans for item in span["types"]))
    if "break_type" not in merged:
        merged["statuses"] = list(
            dict.fromkeys(item for span in spans for item in span["statuses"])
        )
    return merged


@dataclass(frozen=True)
class _MandatoryLineInfo:
    boundaries: frozenset[int]
    sequence_positions: frozenset[int]


def _mandatory_line_info(text: str, line_spans: list[BreakSpan]) -> _MandatoryLineInfo:
    return _MandatoryLineInfo(
        boundaries=frozenset(
            span["end"] for span in line_spans if span.get("break_type") == "mandatory"
        ),
        sequence_positions=frozenset(
            position
            for position, char in enumerate(text)
            if icu.Char.getIntPropertyValue(ord(char), icu.UProperty.LINE_BREAK)
            in _MANDATORY_LINE_BREAK_VALUES
        ),
    )


def _mandatory_info_supplier(
    text: str, locale: str, line_spans: list[BreakSpan] | None = None
) -> Callable[[], _MandatoryLineInfo]:
    info: _MandatoryLineInfo | None = None

    def supply() -> _MandatoryLineInfo:
        nonlocal info
        if info is None:
            spans = line_spans if line_spans is not None else break_line_spans(text, locale)
            info = _mandatory_line_info(text, spans)
        return info

    return supply


def _filter_suppressions(
    text: str,
    base: list[BreakSpan],
    rules: list[_CompiledRule],
    locale: str,
    mandatory_info: Callable[[], _MandatoryLineInfo],
) -> tuple[list[BreakSpan], set[int]]:
    """Drop base boundaries made false by matching suppression surfaces.

    Internal optional boundaries split the surface itself and are dropped. Some
    breakers attach trailing whitespace to a punctuation boundary (notably the
    sentence breaker); when there is no internal boundary, drop that immediately
    following optional boundary instead. Mandatory line breaks are never dropped.
    """
    policy = ExceptionPolicy()
    dropped = set(_boundary_claims(text, base, rules, locale, policy, mandatory_info))
    return _drop_boundaries(text, base, dropped), dropped


def _boundary_claims(
    text: str,
    base: list[BreakSpan],
    rules: list[_CompiledRule],
    locale: str,
    policy: ExceptionPolicy,
    mandatory_info: Callable[[], _MandatoryLineInfo],
) -> dict[int, list[str]]:
    boundaries = {span["end"] for span in base[:-1]}
    claims: dict[int, list[str]] = {}
    for rule in rules:
        for match in _detections(rule, text, locale, policy, mandatory_info):
            internal = {
                boundary for boundary in boundaries if match["start"] < boundary < match["end"]
            }
            if internal:
                for boundary in internal:
                    claims.setdefault(boundary, []).append(rule.id)
                continue
            following = next(
                (
                    boundary
                    for boundary in sorted(boundaries)
                    if boundary >= match["end"] and text[match["end"] : boundary].isspace()
                ),
                None,
            )
            owns_punctuation = _PUNCTUATION.contains(text[match["end"] - 1])
            if match["end"] in boundaries and owns_punctuation:
                claims.setdefault(match["end"], []).append(rule.id)
            elif following is not None and owns_punctuation:
                claims.setdefault(following, []).append(rule.id)
    if not claims:
        return claims
    mandatory = mandatory_info().boundaries
    return {
        boundary: rule_ids for boundary, rule_ids in claims.items() if boundary not in mandatory
    }


def _drop_boundaries(text: str, base: list[BreakSpan], dropped: set[int]) -> list[BreakSpan]:
    result: list[BreakSpan] = []
    run: list[BreakSpan] = []
    maps = offset_maps(text)
    for span in base:
        run.append(span)
        if span["end"] not in dropped:
            result.append(_merge_spans(text, run, maps))
            run = []
    if run:
        result.append(_merge_spans(text, run, maps))
    return result


def _annotate_boundaries(
    base: list[BreakSpan], claims: dict[int, list[str]], type_name: str, *, mark: bool
) -> list[BreakSpan]:
    result: list[BreakSpan] = []
    for original in base:
        span = cast(BreakSpan, dict(original))
        rule_ids = claims.get(span["end"])
        if rule_ids:
            if mark:
                span["exceptions"] = [
                    {"rule_id": rule_id, "relation": "boundary"} for rule_id in rule_ids
                ]
            elif type_name not in span["types"]:
                span["types"] = [*span["types"], type_name]
        result.append(span)
    return result


def _fires(rule: _CompiledRule, text: str, level: Level) -> bool:
    if rule.effect == "retype":
        detections = _detections(rule, text, rule.locale)
        if not detections:
            return False
        merged = merge_retypes(text, _base_spans(text, level, rule.locale), detections)
        return any(rule.type in span["types"] for span in merged)
    base = _base_spans(text, level, rule.locale)
    mandatory_info = _mandatory_info_supplier(text, rule.locale, base if level == "line" else None)
    filtered, _ = _filter_suppressions(text, base, [rule], rule.locale, mandatory_info)
    if filtered == base:
        return False
    filtered_boundaries = {span["end"] for span in filtered}
    removed = {span["end"] for span in base[:-1]} - filtered_boundaries
    for match in _detections(rule, text, rule.locale):
        if any(match["start"] < boundary < match["end"] for boundary in removed):
            return True
        if not _PUNCTUATION.contains(text[match["end"] - 1]):
            continue
        if any(
            boundary == match["end"]
            or (boundary > match["end"] and text[match["end"] : boundary].isspace())
            for boundary in removed
        ):
            return True
    return False


def _run_witnesses(rule: _CompiledRule, raw: ExceptionRule) -> list[RuleRefusal]:
    witnesses = raw["witnesses"]
    positive = cast(str, _text(witnesses["positive"]))
    near_miss = cast(str, _text(witnesses["near_miss"]))
    errors: list[RuleRefusal] = []
    try:
        for level in rule.levels:
            if not _fires(rule, positive, level):
                errors.append(
                    _refuse(rule.id, "WITNESS_POSITIVE_FAILED", f"rule did not fire at {level}")
                )
            if _fires(rule, near_miss, level):
                errors.append(
                    _refuse(rule.id, "WITNESS_NEAR_MISS_FAILED", f"real rule fired at {level}")
                )
        # Deliberately faulty compiler seam: bare search, with no lexical boundary.
        naive = (
            rule.surface in near_miss
            if rule.variant == "exact"
            else bool(
                collation_detect(
                    near_miss,
                    rule.surface,
                    cast(str, rule.type or "exception:naive"),
                    locale=rule.locale,
                    strength=rule.strength,
                )
            )
        )
        if not naive:
            errors.append(_refuse(rule.id, "WITNESS_NEAR_MISS_VACUOUS", "naive rule did not fire"))
        for index, negative in enumerate(witnesses["condition_negatives"]):
            negative_text = cast(str, _text(negative))
            if negative_text is None:
                errors.append(_refuse(rule.id, "INVALID_CONDITION_NEGATIVE", str(index)))
                continue
            surface_start = negative_text.find(rule.surface)
            if surface_start < 0:
                errors.append(_refuse(rule.id, "VACUOUS_CONDITION_NEGATIVE", str(index)))
                continue
            policy = ExceptionPolicy()
            mandatory_info = _mandatory_info_supplier(negative_text, rule.locale)
            values = [
                _condition_result(
                    condition,
                    negative_text,
                    surface_start,
                    surface_start + len(rule.surface),
                    rule.locale,
                    policy,
                    mandatory_info,
                )
                for condition in rule.conditions
            ]
            if values[index] or any(not value for i, value in enumerate(values) if i != index):
                errors.append(_refuse(rule.id, "VACUOUS_CONDITION_NEGATIVE", str(index)))
            for level in rule.levels:
                if _fires(rule, negative_text, level):
                    errors.append(
                        _refuse(
                            rule.id,
                            "WITNESS_CONDITION_NEGATIVE_FAILED",
                            f"condition {index} fired at {level}",
                        )
                    )
    except ExceptionConflictError as error:
        errors.append(_refuse(rule.id, str(error), "witness requires an unsupported mutation"))
    except Exception as error:  # compilation/runtime backend errors become transactional refusals
        errors.append(_refuse(rule.id, "WITNESS_EXECUTION_FAILED", str(error)))
    return errors


def _load_exception_inventory(
    inventory: object, *, require_finite_context: bool = False
) -> LoadedExceptionInventory:
    if not isinstance(inventory, dict):
        raise ExceptionLoadError([_refuse("<inventory>", "INVALID_INVENTORY", "not an object")])
    errors: list[RuleRefusal] = []
    if inventory.get("schema_version") != 1:
        errors.append(_refuse("<inventory>", "INVALID_SCHEMA_VERSION", "expected 1"))
    corpus = inventory.get("corpus")
    if not isinstance(corpus, str) or not corpus:
        errors.append(_refuse("<inventory>", "INVALID_CORPUS", "nonempty string required"))
        corpus = "<invalid>"
    named_lists = inventory.get("named_lists", {})
    if not isinstance(named_lists, dict):
        errors.append(_refuse("<inventory>", "INVALID_NAMED_LISTS", "object required"))
        named_lists = {}
    rules = inventory.get("rules")
    if not isinstance(rules, list):
        errors.append(_refuse("<inventory>", "INVALID_RULES", "list required"))
        rules = []
    ids = [rule.get("id") for rule in rules if isinstance(rule, dict)]
    if len(ids) != len(set(ids)):
        errors.append(_refuse("<inventory>", "DUPLICATE_RULE_ID", "rule ids must be unique"))
    compiled: list[_CompiledRule] = []
    raw_by_id: dict[str, ExceptionRule] = {}
    for raw in rules:
        rule, rule_errors = _compile_rule(raw, cast(dict[str, list[str]], named_lists))
        errors.extend(rule_errors)
        if rule is not None:
            compiled.append(rule)
            raw_by_id[rule.id] = cast(ExceptionRule, raw)
    if not errors:
        for rule in compiled:
            errors.extend(_run_witnesses(rule, raw_by_id[rule.id]))
    if errors:
        raise ExceptionLoadError(errors)
    loaded = LoadedExceptionInventory(
        cast(str, corpus),
        {name: tuple(words) for name, words in cast(dict[str, list[str]], named_lists).items()},
        tuple(compiled),
    )
    if require_finite_context:
        refusals = []
        for rule in loaded._rules:
            causes = []
            if rule.variant == "collation":
                causes.append("collation match extent")
            if any(condition.skip_max is None for condition in rule.conditions):
                causes.append("unbounded skip.max")
            if causes:
                refusals.append(
                    _refuse(
                        rule.id,
                        "UNBOUNDED_CONTEXT",
                        f"rule has unbounded context reach: {', '.join(causes)}",
                    )
                )
        if refusals:
            raise ExceptionLoadError(refusals)
    return loaded


def compose_inventories(
    layers: Sequence[ExceptionInventory],
    *,
    disable: Sequence[str] = (),
    require_finite_context: bool = False,
) -> LoadedExceptionInventory:
    """Compose ordered inventories, then validate and atomically publish the result.

    Later layers replace rules with the same ID and named lists with the same name.
    Disabled IDs are removed after composition. The composed corpus label joins layer
    corpus names with ``" + "``. Loading is opt-in and does not alter default breakers.
    Set ``require_finite_context`` to refuse rules with unbounded context reach.
    """
    errors: list[RuleRefusal] = []
    corpora: list[str] = []
    named_lists: dict[str, list[str]] = {}
    rules: dict[str, object] = {}
    for layer_index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            errors.append(
                _refuse("<inventory>", "INVALID_INVENTORY", f"layer {layer_index}: not an object")
            )
            continue
        if layer.get("schema_version") != 1:
            errors.append(
                _refuse(
                    "<inventory>",
                    "INVALID_SCHEMA_VERSION",
                    f"layer {layer_index}: expected 1",
                )
            )
        corpus = layer.get("corpus")
        if not isinstance(corpus, str) or not corpus:
            errors.append(
                _refuse(
                    "<inventory>",
                    "INVALID_CORPUS",
                    f"layer {layer_index}: nonempty string required",
                )
            )
        else:
            corpora.append(corpus)
        layer_lists = layer.get("named_lists", {})
        if not isinstance(layer_lists, dict):
            errors.append(
                _refuse(
                    "<inventory>",
                    "INVALID_NAMED_LISTS",
                    f"layer {layer_index}: object required",
                )
            )
        else:
            named_lists.update(cast(dict[str, list[str]], layer_lists))
        layer_rules = layer.get("rules")
        if not isinstance(layer_rules, list):
            errors.append(
                _refuse("<inventory>", "INVALID_RULES", f"layer {layer_index}: list required")
            )
            continue
        layer_ids = [rule.get("id") for rule in layer_rules if isinstance(rule, dict)]
        if len(layer_ids) != len(set(layer_ids)):
            errors.append(
                _refuse(
                    "<inventory>",
                    "DUPLICATE_RULE_ID",
                    f"layer {layer_index}: rule ids must be unique",
                )
            )
        for rule in layer_rules:
            rule_id = rule.get("id") if isinstance(rule, dict) else None
            if isinstance(rule_id, str):
                rules[rule_id] = rule
            else:
                errors.append(
                    _refuse(
                        "<unknown>", "INVALID_RULE", f"layer {layer_index}: rule has no string id"
                    )
                )
    disabled = list(disable)
    for rule_id in disabled:
        if rule_id not in rules:
            errors.append(_refuse(str(rule_id), "UNKNOWN_DISABLED_ID", "not in composed rules"))
        else:
            del rules[rule_id]
    if errors:
        raise ExceptionLoadError(errors)
    composed: ExceptionInventory = {
        "schema_version": 1,
        "corpus": " + ".join(corpora) or "<composed>",
        "named_lists": named_lists,
        "rules": cast(list[ExceptionRule], list(rules.values())),
    }
    return _load_exception_inventory(composed, require_finite_context=require_finite_context)


def load_exception_inventory(
    inventory: ExceptionInventory, *, require_finite_context: bool = False
) -> LoadedExceptionInventory:
    """Validate, compile, witness-test, and atomically publish an inventory.

    Set ``require_finite_context`` to refuse rules with unbounded context reach.
    """
    return _load_exception_inventory(inventory, require_finite_context=require_finite_context)


def example_exception_inventory() -> ExceptionInventory:
    """Return electable example rules; they are never loaded or applied by default."""
    resource = files("icukit").joinpath("data/exceptions/examples-en.json")
    return cast(ExceptionInventory, loads(resource.read_text(encoding="utf-8")))
