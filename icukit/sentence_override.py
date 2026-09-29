"""Experimental whole-text sentence-break overrides.

ICU always supplies the candidate boundaries: this module can retain or
suppress them, but never add one. ``base="none"`` is the default and is exactly
ICU's current sentence output. Incremental operation belongs to the later B2
API and is deliberately unavailable here.

Example:
    >>> override = SentenceOverride()
    >>> [(item["offset"], item["layer"]) for item in override.decide("Hi. Bye.")]
    [(4, 'icu'), (8, 'icu')]
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal, NotRequired, TypedDict, cast

import icu

from .breaker import BreakSpan, break_sentence_spans
from .classes import ClassPoint, char_classes, class_window
from .errors import BreakRuleLoadError, OverlappingProtectedSpans, RuleRefusal
from .exceptions import (
    ExceptionPolicy,
    LoadedExceptionInventory,
    _boundary_claims,
    _mandatory_info_supplier,
)
from .shape import shape, shape_scheme
from .tokens import (
    TOKEN_PROFILE,
    ProtectedSpan,
    Token,
    _validated_protected,
    token_features,
    tokens,
)

__all__ = [
    "BreakBoundary",
    "BreakDecision",
    "BreakPredicate",
    "BreakRule",
    "BreakRuleIdentity",
    "BreakRuleSet",
    "BreakSegmentation",
    "SentenceOverride",
    "break_rule_identity",
    "load_break_rules",
]

Effect = Literal["break", "no-break", "ambiguous"]
Layer = Literal["icu", "token", "before", "exceptions", "rules", "after"]
_OPS = {"in", "not_in", "prefix", "le", "ge"}
_FEATURES = "icukit.features@1"
_TOKEN_FEATURES = {
    "text",
    "lower",
    "len",
    "shape.coarse",
    "shape.cased",
    "general_category.first",
    "general_category.last",
    "sentence_break.first",
    "word_break.first",
    "script.first",
    "ws.before",
    "run.shape.cased",
    "lex",
}
_CHAR_FEATURES = {
    "text",
    "word_break",
    "sentence_break",
    "general_category",
    "script",
    "extension_classes",
}


class BreakRuleIdentity(TypedDict):
    """Runtime identity against which a break-rule artifact was authored."""

    icu: str
    unicode: str
    token_profile: str


BreakPredicate = TypedDict(
    "BreakPredicate",
    {
        "at": int | str,
        "f": str,
        "in": NotRequired[list[object]],
        "not_in": NotRequired[list[object]],
        "prefix": NotRequired[list[str]],
        "le": NotRequired[int | float],
        "ge": NotRequired[int | float],
    },
)
"""One flat-rule predicate; exactly one operator is present."""


class BreakRule(TypedDict):
    """One ordered sentence candidate rule.

    Authored witnesses validate the containing rule set as one isolated rule
    layer. Loader inventories contribute word-level token merges only; their
    sentence-level suppression rules and all deployment layers are excluded.

    ``run-1`` is the complete left whitespace run truncated at the candidate.
    Its text, lower-case text, length, shapes, first/last character classes,
    leading-whitespace flag, and run shape are all derived from that same
    truncated run, never from only its final token.
    """

    id: str
    effect: Effect
    lookahead: int
    when: list[dict[str, object]]
    receipt: dict[str, int | float]
    witnesses: dict[str, list[str | dict[str, object]]]


class BreakDecision(TypedDict):
    """The attributed decision for one ICU sentence candidate."""

    offset: int
    end: int
    decision: Literal["break", "no-break"]
    alternatives: tuple[Literal["break", "no-break"], ...]
    layer: Layer
    id: str | None
    tokens_read: int


class BreakBoundary(TypedDict):
    """An open sentence boundary carrying both readings."""

    offset: int
    end: int
    alternatives: tuple[Literal["break", "no-break"], ...]
    layer: Layer
    id: str | None


class BreakSegmentation(TypedDict):
    """Primary sentence spans plus every boundary left open by a rule."""

    spans: list[BreakSpan]
    boundaries: list[BreakBoundary]


@dataclass(frozen=True)
class _CompiledPredicate:
    at: int | str
    feature: str
    op: str
    operand: object


@dataclass(frozen=True)
class _CompiledBreakRule:
    id: str
    effect: Effect
    lookahead: int
    when: tuple[_CompiledPredicate, ...]


@dataclass(frozen=True)
class BreakRuleSet:
    """An immutable, validated ordered set of flat break rules."""

    id: str
    locale: str
    status: Literal["experimental"]
    features: str
    runtime_identity: Mapping[str, str]
    digest: str
    _rules: tuple[_CompiledBreakRule, ...]
    provenance: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        identity = cast(Mapping[str, str], _freeze(self.runtime_identity))
        rules = tuple(
            _CompiledBreakRule(
                rule.id,
                rule.effect,
                rule.lookahead,
                tuple(
                    _CompiledPredicate(
                        predicate.at,
                        predicate.feature,
                        predicate.op,
                        _freeze(predicate.operand),
                    )
                    for predicate in rule.when
                ),
            )
            for rule in self._rules
        )
        object.__setattr__(self, "runtime_identity", identity)
        object.__setattr__(self, "_rules", rules)
        object.__setattr__(self, "provenance", _freeze(self.provenance))

    @property
    def lookahead(self) -> int:
        """Maximum declared token lookahead in this rule set."""
        return max((rule.lookahead for rule in self._rules), default=0)


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze(item) for item in value)
    return value


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_plain(item) for item in value]
    return value


def _rule_set_digest(rule_set: BreakRuleSet) -> str:
    definition = {
        "id": rule_set.id,
        "locale": rule_set.locale,
        "status": rule_set.status,
        "features": rule_set.features,
        "identity": _plain(rule_set.runtime_identity),
        "provenance": _plain(rule_set.provenance),
        "rules": [
            {
                "id": rule.id,
                "effect": rule.effect,
                "lookahead": rule.lookahead,
                "when": [
                    {
                        "at": predicate.at,
                        "f": predicate.feature,
                        "op": predicate.op,
                        "operand": _plain(predicate.operand),
                    }
                    for predicate in rule.when
                ],
            }
            for rule in rule_set._rules
        ],
    }
    return "sha256:" + hashlib.sha256(_canonical(definition)).hexdigest()


def _inventory_definition(inventory: LoadedExceptionInventory) -> dict[str, object]:
    return {
        "corpus": inventory.corpus,
        "named_lists": {key: list(value) for key, value in sorted(inventory.named_lists.items())},
        "rules": [
            {
                "id": rule.id,
                "locale": rule.locale,
                "levels": list(rule.levels),
                "effect": rule.effect,
                "type": rule.type,
                "surface": rule.surface,
                "variant": rule.variant,
                "strength": rule.strength,
                "conditions": [
                    {
                        "id": condition.id,
                        "kind": condition.kind,
                        "direction": condition.direction,
                        "skip_kind": condition.skip_kind,
                        "skip_max": condition.skip_max,
                        "unicode_set": (
                            condition.unicode_set.toPattern() if condition.unicode_set else None
                        ),
                        "words": sorted(condition.words),
                    }
                    for condition in rule.conditions
                ],
            }
            for rule in inventory._rules
        ],
    }


def _require_raw_sentence_locale(locale: str) -> None:
    if icu.Locale(locale).getKeywordValue("ss") is not None:
        raise ValueError(
            "sentence override candidates are raw ICU sentence breaks without ULI; "
            "suppression belongs in rule layers or inventories, not the locale ss keyword"
        )


def break_rule_identity(
    locale: str = "en_US", /, *, inventories: Sequence[LoadedExceptionInventory] = ()
) -> BreakRuleIdentity:
    """Return the runtime identity an authored break-rule set must declare.

    The token profile binds the explicit :data:`icukit.tokens.TOKEN_PROFILE`
    version, locale, ordered exception inventories, protected-span policy, and
    built-in shape definitions. The profile version is bumped when the golden
    tokenizer behavior changes; it is not a proof derived from implementation
    text. Fixtures should call this function instead of hard-coding versions.
    """
    _require_raw_sentence_locale(locale)
    profile = {
        "schema": TOKEN_PROFILE,
        "locale": locale,
        "inventories": [_inventory_definition(item) for item in inventories],
        "protected": {
            "scope_default": "token",
            "token": "outermost-wins; equal-extents-union; strict-interior-suppresses",
            "hint": "no-merge; covering-types-visible",
        },
        "shapes": [shape_scheme("coarse@1"), shape_scheme("cased@1")],
    }
    return {
        "icu": icu.ICU_VERSION,
        "unicode": icu.UNICODE_VERSION,
        "token_profile": "sha256:" + hashlib.sha256(_canonical(profile)).hexdigest(),
    }


def _refuse(rule_id: str, reason: str, detail: str) -> RuleRefusal:
    return RuleRefusal(rule_id, reason, detail)


def _parse_at(value: object) -> int | str | None:
    if isinstance(value, int) and not isinstance(value, bool):
        if value in {-3, -2, -1} or value > 0:
            return value
    if isinstance(value, str) and value in {"run-1", "protected"}:
        return cast(str, value)
    if isinstance(value, str) and len(value) >= 3 and value[0] == "c" and value[1] in "+-":
        try:
            distance = int(value[1:])
        except ValueError:
            return None
        if distance and -8 <= distance <= 8:
            return value
    return None


def _compile_rule(raw: object) -> tuple[_CompiledBreakRule | None, list[RuleRefusal]]:
    if not isinstance(raw, dict):
        return None, [_refuse("<unknown>", "INVALID_RULE", "rule must be an object")]
    rule_id = raw.get("id")
    label = rule_id if isinstance(rule_id, str) and rule_id else "<unknown>"
    errors: list[RuleRefusal] = []
    if not isinstance(rule_id, str) or not rule_id:
        errors.append(_refuse(label, "INVALID_RULE_ID", "nonempty string required"))
    effect = raw.get("effect")
    if not isinstance(effect, str) or effect not in {"break", "no-break", "ambiguous"}:
        errors.append(_refuse(label, "INVALID_EFFECT", "expected break, no-break, or ambiguous"))
    lookahead = raw.get("lookahead")
    if not isinstance(lookahead, int) or isinstance(lookahead, bool) or lookahead < 0:
        errors.append(_refuse(label, "INVALID_LOOKAHEAD", "nonnegative integer required"))
        lookahead = 0
    receipt = raw.get("receipt")
    if (
        not isinstance(receipt, dict)
        or not receipt
        or any(
            not isinstance(key, str)
            or not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
            for key, value in receipt.items()
        )
    ):
        errors.append(_refuse(label, "INVALID_RECEIPT", "nonempty numeric-count object required"))
    witnesses = raw.get("witnesses")

    def valid_witness(item: object) -> bool:
        if isinstance(item, str):
            return bool(item)
        if not isinstance(item, dict):
            return False
        text = item.get("text")
        protected = item.get("protected", [])
        offset = item.get("offset")
        decision = item.get("decision")
        if (
            not isinstance(text, str)
            or not text
            or not isinstance(protected, list)
            or (offset is not None and (not isinstance(offset, int) or isinstance(offset, bool)))
            or (
                decision is not None
                and (
                    not isinstance(decision, str)
                    or decision not in {"break", "no-break", "ambiguous"}
                )
            )
        ):
            return False
        try:
            _validated_protected(cast(Iterable[ProtectedSpan], protected), len(text))
        except (TypeError, ValueError, OverlappingProtectedSpans):
            return False
        return True

    if not isinstance(witnesses, dict) or any(
        not isinstance(witnesses.get(kind), list)
        or not witnesses.get(kind)
        or any(not valid_witness(item) for item in witnesses.get(kind, []))
        for kind in ("match", "no_match")
    ):
        errors.append(
            _refuse(
                label,
                "INVALID_WITNESSES",
                "nonempty match and no_match authored witness lists required",
            )
        )
    predicates: list[_CompiledPredicate] = []
    conditions = raw.get("when")
    if not isinstance(conditions, list) or not conditions:
        errors.append(_refuse(label, "INVALID_WHEN", "nonempty predicate list required"))
        conditions = []
    furthest = 0
    has_forward_character = False
    for index, condition in enumerate(conditions):
        if not isinstance(condition, dict):
            errors.append(
                _refuse(label, "INVALID_PREDICATE", f"predicate {index} is not an object")
            )
            continue
        at = _parse_at(condition.get("at"))
        feature = condition.get("f")
        ops = [key for key in _OPS if key in condition]
        if at is None or not isinstance(feature, str) or not feature or len(ops) != 1:
            errors.append(
                _refuse(
                    label,
                    "INVALID_PREDICATE",
                    f"predicate {index} needs valid at, f, and one op",
                )
            )
            continue
        allowed_features = (
            {"protected.type"}
            if at == "protected"
            else _CHAR_FEATURES
            if isinstance(at, str) and at.startswith("c")
            else _TOKEN_FEATURES
        )
        if feature not in allowed_features:
            errors.append(
                _refuse(
                    label,
                    "INVALID_FEATURE",
                    f"predicate {index}: {feature!r} is not valid at {at!r}",
                )
            )
            continue
        op = ops[0]
        operand = condition[op]
        if op in {"in", "not_in", "prefix"} and (not isinstance(operand, list) or not operand):
            errors.append(_refuse(label, "INVALID_OPERAND", f"predicate {index}: list required"))
            continue
        if op == "prefix" and any(
            not isinstance(item, str) for item in cast(list[object], operand)
        ):
            errors.append(_refuse(label, "INVALID_OPERAND", f"predicate {index}: strings required"))
            continue
        if op in {"in", "not_in"} and any(
            item is None
            or isinstance(item, (list, dict))
            or (isinstance(item, float) and not math.isfinite(item))
            for item in cast(list[object], operand)
        ):
            errors.append(
                _refuse(label, "INVALID_OPERAND", f"predicate {index}: scalar values required")
            )
            continue
        if op in {"le", "ge"} and (
            not isinstance(operand, (int, float))
            or isinstance(operand, bool)
            or not math.isfinite(operand)
        ):
            errors.append(_refuse(label, "INVALID_OPERAND", f"predicate {index}: number required"))
            continue
        if isinstance(at, int) and at > 0:
            furthest = max(furthest, at)
        if isinstance(at, str) and at.startswith("c+"):
            has_forward_character = True
        immutable_operand = tuple(operand) if isinstance(operand, list) else operand
        predicates.append(_CompiledPredicate(at, feature, op, immutable_operand))
    required = max(furthest, int(has_forward_character))
    if cast(int, lookahead) < required:
        errors.append(
            _refuse(
                label,
                "LOOKAHEAD_TOO_SMALL",
                f"declares {lookahead}; predicates require {required}",
            )
        )
    if errors:
        return None, errors
    return (
        _CompiledBreakRule(
            cast(str, rule_id), cast(Effect, effect), cast(int, lookahead), tuple(predicates)
        ),
        [],
    )


def _locale_applies(declared: str, runtime: str) -> bool:
    declared = declared.replace("-", "_").lower()
    runtime = runtime.replace("-", "_").lower()
    return declared == runtime or declared == runtime.split("_", 1)[0]


def _load_source(source: str | Path | Mapping[str, object]) -> Mapping[str, object]:
    if isinstance(source, Mapping):
        try:
            return deepcopy(dict(source))
        except Exception as error:
            raise BreakRuleLoadError(
                [_refuse("<ruleset>", "INVALID_SOURCE", f"cannot snapshot input: {error}")]
            ) from error
    if not isinstance(source, (str, Path)):
        raise BreakRuleLoadError(
            [_refuse("<ruleset>", "INVALID_SOURCE", "mapping or JSON path required")]
        )
    path = Path(source)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BreakRuleLoadError([_refuse("<ruleset>", "INVALID_SOURCE", str(error))]) from error
    if not isinstance(value, dict):
        raise BreakRuleLoadError([_refuse("<ruleset>", "INVALID_RULE_SET", "object required")])
    return value


def load_break_rules(
    source: str | Path | Mapping[str, object],
    /,
    *,
    locale: str = "en_US",
    inventories: Sequence[LoadedExceptionInventory] = (),
) -> BreakRuleSet:
    """Load, validate, identity-check, and witness-test flat break rules.

    ``source`` may be a parsed JSON object or a path to a ``break-rules`` JSON
    file. Witnesses execute transactionally after compilation; no partially
    validated rule set is returned. An object witness may add an integer
    ``offset`` and a ``decision`` of ``break``, ``no-break``, or ``ambiguous``
    to pin the candidate and result. A ``no_match`` witness always requires
    that its rule decide no candidate anywhere in the text. Witnesses evaluate
    the loaded set as one isolated rule layer: ``inventories`` contribute only
    word-level token merges, while sentence-level inventory suppression and
    all other deployment layers are excluded. Callers compose those layers at
    deployment, where each candidate's attribution reports the deciding one.
    """
    _require_raw_sentence_locale(locale)
    raw = _load_source(source)
    errors: list[RuleRefusal] = []
    schema_version = raw.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != 1
    ):
        errors.append(_refuse("<ruleset>", "INVALID_SCHEMA_VERSION", "expected 1"))
    kind = raw.get("kind")
    if not isinstance(kind, str) or kind != "break-rules":
        errors.append(_refuse("<ruleset>", "INVALID_KIND", "expected break-rules"))
    set_id = raw.get("id")
    if not isinstance(set_id, str) or not set_id:
        errors.append(_refuse("<ruleset>", "INVALID_ID", "nonempty string required"))
        set_id = "<invalid>"
    declared_locale = raw.get("locale")
    if not isinstance(declared_locale, str) or not _locale_applies(declared_locale, locale):
        errors.append(_refuse(str(set_id), "LOCALE_MISMATCH", f"{declared_locale!r} vs {locale!r}"))
        declared_locale = str(declared_locale)
    status = raw.get("status")
    if not isinstance(status, str) or status != "experimental":
        errors.append(_refuse(str(set_id), "INVALID_STATUS", "expected experimental"))
    features = raw.get("features")
    if not isinstance(features, str) or features != _FEATURES:
        errors.append(_refuse(str(set_id), "FEATURES_MISMATCH", f"expected {_FEATURES}"))
    expected_identity = break_rule_identity(locale, inventories=inventories)
    declared_identity = raw.get("identity")
    if not isinstance(declared_identity, dict):
        errors.append(_refuse(str(set_id), "INVALID_IDENTITY", "identity object required"))
        declared_identity = {}
    for key, expected in expected_identity.items():
        if declared_identity.get(key) != expected:
            errors.append(
                _refuse(str(set_id), "IDENTITY_MISMATCH", f"{key}: expected {expected!r}")
            )
    provenance = raw.get("provenance")
    if provenance is not None and not isinstance(provenance, dict):
        errors.append(_refuse(str(set_id), "INVALID_PROVENANCE", "object required"))
    raw_rules = raw.get("rules")
    if not isinstance(raw_rules, list):
        errors.append(_refuse(str(set_id), "INVALID_RULES", "list required"))
        raw_rules = []
    ids = [item.get("id") for item in raw_rules if isinstance(item, dict)]
    valid_ids = [item for item in ids if isinstance(item, str)]
    if len(valid_ids) != len(set(valid_ids)):
        errors.append(_refuse(str(set_id), "DUPLICATE_RULE_ID", "rule ids must be unique"))
    compiled: list[_CompiledBreakRule] = []
    for item in raw_rules:
        rule, rule_errors = _compile_rule(item)
        errors.extend(rule_errors)
        if rule is not None:
            compiled.append(rule)
    if errors:
        raise BreakRuleLoadError(errors)
    try:
        _canonical(raw)
    except (TypeError, ValueError) as error:
        raise BreakRuleLoadError(
            [_refuse(str(set_id), "INVALID_RULE_SET", f"not canonical JSON: {error}")]
        ) from error
    loaded = BreakRuleSet(
        str(set_id),
        cast(str, declared_locale),
        "experimental",
        _FEATURES,
        expected_identity,
        "",
        tuple(compiled),
        cast(Mapping[str, object] | None, provenance),
    )
    object.__setattr__(loaded, "digest", _rule_set_digest(loaded))
    witness_errors = _run_witnesses(
        loaded, cast(list[dict[str, object]], raw_rules), locale, inventories
    )
    if witness_errors:
        raise BreakRuleLoadError(witness_errors)
    return loaded


def _token_index_after(toks: Sequence[Token], offset: int) -> int:
    return next((index for index, token in enumerate(toks) if token["start"] >= offset), len(toks))


def _logical_end(toks: Sequence[Token], offset: int) -> int:
    return max((token["end"] for token in toks if token["end"] <= offset), default=offset)


def _sentinel_features(value: str) -> dict[str, object]:
    return {
        "text": value,
        "lower": value,
        "len": value,
        "shape.coarse": value,
        "shape.cased": value,
        "general_category.first": value,
        "general_category.last": value,
        "sentence_break.first": value,
        "word_break.first": value,
        "script.first": value,
        "ws.before": value,
        "run.shape.cased": value,
        "lex": value,
    }


def _point_feature(point: ClassPoint, feature: str) -> object:
    values: dict[str, object] = {
        "text": point.text,
        "word_break": point.word_break,
        "sentence_break": point.sentence_break,
        "general_category": point.general_category,
        "script": point.script,
        "extension_classes": point.extension_classes,
    }
    if point.text == "":
        return point.word_break
    return values.get(feature, "<UNKNOWN>")


def _feature_value(
    predicate: _CompiledPredicate,
    rule: _CompiledBreakRule,
    text: str,
    offset: int,
    toks: Sequence[Token],
    protected_types: tuple[str, ...],
) -> tuple[object, int]:
    at = predicate.at
    if at == "protected":
        value: object = protected_types
        return value, 0
    pivot = _token_index_after(toks, offset)
    if at == "run-1":
        if pivot == 0:
            return _sentinel_features("<BOS>").get(predicate.feature, "<BOS>"), 0
        previous = toks[pivot - 1]
        same_run = [
            item for item in toks if item["run"] == previous["run"] and item["end"] <= offset
        ]
        start = min(item["start"] for item in same_run)
        run_text = text[start:offset].rstrip()
        first = run_text[0]
        last = run_text[-1]
        cased_shape = shape(run_text, "cased@1")
        features = {
            "text": run_text,
            "lower": str(icu.UnicodeString(run_text).toLower(icu.Locale.getRoot())),
            "len": len(run_text),
            "shape.coarse": shape(run_text, "coarse@1"),
            "shape.cased": cased_shape,
            "general_category.first": char_classes(first, "general_category")[0],
            "general_category.last": char_classes(last, "general_category")[0],
            "sentence_break.first": char_classes(first, "sentence_break")[0],
            "word_break.first": char_classes(first, "word_break")[0],
            "script.first": char_classes(first, "script")[0],
            "ws.before": start > 0 and text[start - 1].isspace(),
            "run.shape.cased": cased_shape,
            "lex": "none",
        }
        return features.get(predicate.feature, "<UNKNOWN>"), 0
    if isinstance(at, int):
        index = pivot + at - 1 if at > 0 else pivot + at
        if index < 0:
            return _sentinel_features("<BOS>").get(predicate.feature, "<BOS>"), 0
        if index >= len(toks):
            reached = min(max(at, 0), max(len(toks) - pivot, 0))
            return _sentinel_features("<EOS>").get(predicate.feature, "<EOS>"), reached
        return token_features(toks, index, text).get(predicate.feature, "<UNKNOWN>"), max(at, 0)
    distance = int(cast(str, at)[1:])
    index = offset + distance - 1 if distance > 0 else offset + distance
    if distance > 0:
        horizon_index = pivot + rule.lookahead - 1
        if horizon_index < len(toks) and index >= toks[horizon_index]["end"]:
            return "<BEYOND>", rule.lookahead
    if index < 0:
        return "<BOS>", 0
    if index >= len(text):
        return "<EOS>", rule.lookahead if distance > 0 else 0
    window = class_window(text, index, before=0, after=1)
    tokens_read = 0
    if distance > 0:
        tokens_read = sum(1 for token in toks[pivot:] if token["start"] <= index)
        tokens_read = min(tokens_read, rule.lookahead)
    return _point_feature(window.after[0], predicate.feature), tokens_read


def _predicate_matches(value: object, predicate: _CompiledPredicate) -> bool:
    operand = predicate.operand
    values = value if isinstance(value, tuple) else (value,)
    if predicate.op == "in":
        return any(item in cast(tuple[object, ...], operand) for item in values)
    if predicate.op == "not_in":
        return all(item not in cast(tuple[object, ...], operand) for item in values)
    if predicate.op == "prefix":
        return any(
            isinstance(item, str)
            and any(item.startswith(prefix) for prefix in cast(tuple[str, ...], operand))
            for item in values
        )
    if predicate.op == "le":
        return isinstance(value, (int, float)) and value <= cast(int | float, operand)
    return isinstance(value, (int, float)) and value >= cast(int | float, operand)


def _match_rule(
    rule: _CompiledBreakRule,
    text: str,
    offset: int,
    toks: Sequence[Token],
    protected_types: tuple[str, ...],
) -> tuple[bool, int]:
    read = 0
    for predicate in rule.when:
        value, reached = _feature_value(predicate, rule, text, offset, toks, protected_types)
        read = max(read, reached)
        if not _predicate_matches(value, predicate):
            return False, read
    return True, read


def _decision(
    offset: int,
    end: int,
    effect: Effect,
    layer: Layer,
    rule_id: str | None,
    tokens_read: int,
) -> BreakDecision:
    ambiguous = effect == "ambiguous"
    return {
        "offset": offset,
        "end": end,
        "decision": "no-break" if effect in {"no-break", "ambiguous"} else "break",
        "alternatives": (
            ("break", "no-break") if ambiguous else (cast(Literal["break", "no-break"], effect),)
        ),
        "layer": layer,
        "id": rule_id,
        "tokens_read": tokens_read,
    }


def _rules_decision(
    rule_set: BreakRuleSet,
    layer: Layer,
    text: str,
    offset: int,
    end: int,
    toks: Sequence[Token],
    protected_types: tuple[str, ...],
) -> tuple[BreakDecision | None, int]:
    furthest = 0
    for rule in rule_set._rules:
        matched, read = _match_rule(rule, text, offset, toks, protected_types)
        furthest = max(furthest, read)
        if matched:
            return _decision(offset, end, rule.effect, layer, rule.id, furthest), furthest
    return None, furthest


def _run_witnesses(
    rule_set: BreakRuleSet,
    raw_rules: list[dict[str, object]],
    locale: str,
    inventories: Sequence[LoadedExceptionInventory],
) -> list[RuleRefusal]:
    errors: list[RuleRefusal] = []
    for rule, raw in zip(rule_set._rules, raw_rules, strict=True):
        witnesses = cast(dict[str, list[str | dict[str, object]]], raw["witnesses"])
        for kind, should_match in (("match", True), ("no_match", False)):
            for index, witness in enumerate(witnesses[kind]):
                text = witness if isinstance(witness, str) else cast(str, witness["text"])
                protected = () if isinstance(witness, str) else witness.get("protected", ())
                expected_offset = None if isinstance(witness, str) else witness.get("offset")
                expected_decision = None if isinstance(witness, str) else witness.get("decision")
                expected_alternatives = {
                    "break": ("break",),
                    "no-break": ("no-break",),
                    "ambiguous": ("break", "no-break"),
                }
                protected_items = tuple(cast(Iterable[ProtectedSpan], protected))
                combined_inventory = (
                    LoadedExceptionInventory(
                        " + ".join(item.corpus for item in inventories),
                        {
                            key: value
                            for item in inventories
                            for key, value in item.named_lists.items()
                        },
                        tuple(rule for item in inventories for rule in item._rules),
                    )
                    if inventories
                    else None
                )
                toks = tokens(text, locale, inventory=combined_inventory, protected=protected_items)
                decisions = []
                for span in break_sentence_spans(text, locale):
                    offset = span["end"]
                    containing = next(
                        (token for token in toks if token["start"] < offset < token["end"]),
                        None,
                    )
                    if containing is not None:
                        continue
                    covering = tuple(
                        sorted(
                            {
                                item["type"]
                                for item in protected_items
                                if item["start"] < offset < item["end"]
                            }
                        )
                    )
                    decision, _read = _rules_decision(
                        rule_set,
                        "rules",
                        text,
                        offset,
                        _logical_end(toks, offset),
                        toks,
                        covering,
                    )
                    if decision is not None:
                        decisions.append(decision)
                found = any(
                    item["id"] == rule.id
                    and (
                        not should_match
                        or (
                            (expected_offset is None or item["offset"] == expected_offset)
                            and (
                                expected_decision is None
                                or item["alternatives"]
                                == expected_alternatives[cast(str, expected_decision)]
                            )
                        )
                    )
                    for item in decisions
                )
                if found != should_match:
                    errors.append(
                        _refuse(
                            rule.id,
                            "WITNESS_MATCH_FAILED" if should_match else "WITNESS_NO_MATCH_FAILED",
                            f"{kind}[{index}]",
                        )
                    )
    return errors


def _inventory_claims(
    inventory: LoadedExceptionInventory, text: str, locale: str
) -> dict[int, list[str]]:
    base = break_sentence_spans(text, locale)
    selected = [
        rule
        for rule in inventory._rules
        if "sentence" in rule.levels
        and rule.effect == "suppress"
        and _locale_applies(rule.locale, locale)
    ]
    return _boundary_claims(
        text,
        base,
        selected,
        locale,
        ExceptionPolicy(),
        _mandatory_info_supplier(text, locale),
    )


def _decide_core(
    text: str,
    locale: str,
    inventories: Sequence[LoadedExceptionInventory],
    before: Sequence[BreakRuleSet],
    base: BreakRuleSet | None,
    after: Sequence[BreakRuleSet],
    protected: Iterable[ProtectedSpan],
) -> list[BreakDecision]:
    protected_items = tuple(protected)
    combined_inventory = (
        LoadedExceptionInventory(
            " + ".join(item.corpus for item in inventories),
            {key: value for item in inventories for key, value in item.named_lists.items()},
            tuple(rule for item in inventories for rule in item._rules),
        )
        if inventories
        else None
    )
    toks = tokens(text, locale, inventory=combined_inventory, protected=protected_items)
    _token_spans, _hints = _validated_protected(protected_items, len(text))
    claims = [_inventory_claims(item, text, locale) for item in inventories]
    result: list[BreakDecision] = []
    for span in break_sentence_spans(text, locale):
        offset = span["end"]
        covering = tuple(
            sorted(
                {item["type"] for item in protected_items if item["start"] < offset < item["end"]}
            )
        )
        containing = next((token for token in toks if token["start"] < offset < token["end"]), None)
        end = containing["end"] if containing is not None else _logical_end(toks, offset)
        if containing is not None:
            result.append(_decision(offset, end, "no-break", "token", None, 0))
            continue
        tokens_read = 0
        forced = None
        for rule_set in before:
            forced, read = _rules_decision(rule_set, "before", text, offset, end, toks, covering)
            tokens_read = max(tokens_read, read)
            if forced is not None:
                forced["tokens_read"] = tokens_read
                break
        if forced is not None:
            result.append(forced)
            continue
        exception = next(
            (
                (rule_ids[0], inventory_index)
                for inventory_index, inventory_claims in enumerate(claims)
                if (rule_ids := inventory_claims.get(offset))
            ),
            None,
        )
        if exception is not None:
            result.append(
                _decision(offset, end, "no-break", "exceptions", exception[0], tokens_read)
            )
            continue
        current = None
        if base is not None:
            current, read = _rules_decision(base, "rules", text, offset, end, toks, covering)
            tokens_read = max(tokens_read, read)
        if current is None:
            current = _decision(offset, end, "break", "icu", None, tokens_read)
        else:
            current["tokens_read"] = tokens_read
        for rule_set in after:
            changed, read = _rules_decision(rule_set, "after", text, offset, end, toks, covering)
            tokens_read = max(tokens_read, read)
            if changed is not None:
                current = changed
                break
        current["tokens_read"] = tokens_read
        result.append(current)
    return result


class SentenceOverride:
    """Apply opt-in flat rules to ICU sentence candidates over complete text.

    Args:
        locale: ICU locale used for both sentence and word boundaries.
        base: ``"none"`` (the unchanged ICU default), a loaded rule set, or a
            path to a ``break-rules`` JSON file.
        before: Ordered caller rules that force a decision before inventories
            and the base.
        after: Ordered caller rules that may override the base decision.
        inventories: Exception inventories; word rules merge tokens and
            sentence rules suppress candidates.
        cache: Reserved for API parity with the incremental implementation.

    Example:
        >>> SentenceOverride().spans("Hello. Next.") == break_sentence_spans(
        ...     "Hello. Next.", "en_US"
        ... )
        True
    """

    def __init__(
        self,
        locale: str = "en_US",
        /,
        *,
        base: Literal["none"] | str | Path | BreakRuleSet = "none",
        before: Sequence[BreakRuleSet] = (),
        after: Sequence[BreakRuleSet] = (),
        inventories: Sequence[LoadedExceptionInventory] = (),
        cache: bool = True,
    ) -> None:
        if not isinstance(locale, str) or not locale:
            raise ValueError("locale must be a nonempty string")
        _require_raw_sentence_locale(locale)
        if not isinstance(cache, bool):
            raise TypeError("cache must be bool")
        self.locale = locale
        self.cache = cache
        self.inventories = tuple(inventories)
        expected = break_rule_identity(locale, inventories=self.inventories)
        if base == "none":
            loaded_base = None
        elif isinstance(base, BreakRuleSet):
            loaded_base = base
        elif isinstance(base, (str, Path)):
            loaded_base = load_break_rules(base, locale=locale, inventories=self.inventories)
        else:
            raise TypeError("base must be 'none', a BreakRuleSet, or a break-rules JSON path")
        self.base = loaded_base
        self.before = tuple(before)
        self.after = tuple(after)
        layers = (*self.before, *((loaded_base,) if loaded_base is not None else ()), *self.after)
        invalid_digests = [item.id for item in layers if _rule_set_digest(item) != item.digest]
        if invalid_digests:
            raise BreakRuleLoadError(
                [
                    _refuse(item, "DIGEST_MISMATCH", "rule-set contents differ from digest")
                    for item in invalid_digests
                ]
            )
        mismatched = [item.id for item in layers if item.runtime_identity != expected]
        if mismatched:
            raise BreakRuleLoadError(
                [
                    _refuse(item, "IDENTITY_MISMATCH", "runtime token profile differs")
                    for item in mismatched
                ]
            )
        ids: list[tuple[str, str]] = [
            (rule.id, f"layer:{index}:{rule_set.id}")
            for index, rule_set in enumerate(layers)
            for rule in rule_set._rules
        ]
        ids.extend(
            (rule.id, f"inventory:{index}")
            for index, inventory in enumerate(self.inventories)
            for rule in inventory._rules
        )
        seen: dict[str, str] = {}
        duplicates: list[RuleRefusal] = []
        for rule_id, owner in ids:
            if rule_id in seen:
                duplicates.append(
                    _refuse(
                        rule_id,
                        "DUPLICATE_RULE_ID",
                        f"declared by {seen[rule_id]} and {owner}",
                    )
                )
            else:
                seen[rule_id] = owner
        if duplicates:
            raise BreakRuleLoadError(duplicates)
        definition = {
            "runtime": expected,
            "locale": locale,
            "inventories": [_inventory_definition(item) for item in self.inventories],
            "before": [item.digest for item in self.before],
            "base": loaded_base.digest if loaded_base is not None else "none",
            "after": [item.digest for item in self.after],
            "features": _FEATURES,
        }
        self.identity = "sha256:" + hashlib.sha256(_canonical(definition)).hexdigest()
        self.lookahead = max((item.lookahead for item in layers), default=0)

    def decide(
        self, text: str, /, *, protected: Iterable[ProtectedSpan] = ()
    ) -> list[BreakDecision]:
        """Return an attributed decision for every raw ICU sentence candidate."""
        return _decide_core(
            text,
            self.locale,
            self.inventories,
            self.before,
            self.base,
            self.after,
            protected,
        )

    def spans(self, text: str, /, *, protected: Iterable[ProtectedSpan] = ()) -> list[BreakSpan]:
        """Return the one-best sentence spans; trailing whitespace stays left."""
        decisions = self.decide(text, protected=protected)
        originals = break_sentence_spans(text, self.locale)
        if not originals:
            return []
        result: list[BreakSpan] = []
        group: list[BreakSpan] = []
        for span, decision in zip(originals, decisions, strict=True):
            group.append(span)
            if decision["decision"] == "break":
                merged = cast(BreakSpan, dict(group[-1]))
                merged["start"] = group[0]["start"]
                merged["codepoint_start"] = group[0]["codepoint_start"]
                merged["utf8_start"] = group[0]["utf8_start"]
                merged["utf16_start"] = group[0]["utf16_start"]
                merged["text"] = text[merged["start"] : merged["end"]]
                merged["types"] = list(dict.fromkeys(x for item in group for x in item["types"]))
                merged["statuses"] = list(
                    dict.fromkeys(x for item in group for x in item["statuses"])
                )
                result.append(merged)
                group = []
        if group:
            merged = cast(BreakSpan, dict(group[-1]))
            merged["start"] = group[0]["start"]
            merged["codepoint_start"] = group[0]["codepoint_start"]
            merged["utf8_start"] = group[0]["utf8_start"]
            merged["utf16_start"] = group[0]["utf16_start"]
            merged["text"] = text[merged["start"] : merged["end"]]
            merged["types"] = list(dict.fromkeys(x for item in group for x in item["types"]))
            merged["statuses"] = list(dict.fromkeys(x for item in group for x in item["statuses"]))
            result.append(merged)
        return result

    def segmentations(
        self, text: str, /, *, protected: Iterable[ProtectedSpan] = ()
    ) -> BreakSegmentation:
        """Return one-best spans and each candidate retaining two alternatives."""
        protected_items = tuple(protected)
        decisions = self.decide(text, protected=protected_items)
        boundaries: list[BreakBoundary] = [
            {
                "offset": item["offset"],
                "end": item["end"],
                "alternatives": item["alternatives"],
                "layer": item["layer"],
                "id": item["id"],
            }
            for item in decisions
            if len(item["alternatives"]) == 2
        ]
        return {"spans": self.spans(text, protected=protected_items), "boundaries": boundaries}

    def stream(self, *args: object, **kwargs: object) -> None:
        """Refuse incremental operation, which is reserved for lane B2."""
        raise NotImplementedError("incremental sentence breaking is implemented by lane B2")
