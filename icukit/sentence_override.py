"""Whole-text and incremental sentence-break overrides.

ICU always supplies the candidate boundaries: this module can retain or
suppress them, but never add one. The locale default is ``"en-tn-cart@1"`` for
English (language ``en``, with any region or script, except the ``POSIX``
variant) and ``"none"`` otherwise. That English default and the two learned
English named bases apply the locale's shipped abbreviation suppressions before
their rules or model. Explicit ``base="none"`` is exactly ICU's current
sentence output, without that list. Whole-text and incremental operation share
the same prefix-aware candidate evaluator.

Example:
    >>> override = SentenceOverride()
    >>> [(item["offset"], item["layer"]) for item in override.decide("Hi. Bye.")]
    [(4, 'model'), (8, 'model')]
"""

from __future__ import annotations

import hashlib
import json
import math
from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Literal, NotRequired, TypedDict, cast

import icu

from ._offsets import _offset_map_scope
from .abbreviation_compile import _load_break_exception_inventory
from .breaker import BreakSpan, _raw_break_sentence_spans, break_word_spans
from .classes import ClassPoint, char_classes, class_window
from .errors import BreakRuleLoadError, LateProtectedSpan, OverlappingProtectedSpans, RuleRefusal
from .exceptions import (
    ExceptionPolicy,
    LoadedExceptionInventory,
    _boundary_claims,
    _mandatory_info_supplier,
    _sentence_boundary_claims,
)
from .shape import shape, shape_scheme
from .tokens import (
    TOKEN_PROFILE,
    ProtectedSpan,
    Token,
    _token_features_base,
    _validated_protected,
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
    "CartletModelRef",
    "IncrementalSentenceBreaker",
    "PendingCandidate",
    "SentenceOverride",
    "break_rule_identity",
    "load_break_rules",
]

Effect = Literal["break", "no-break", "ambiguous"]
Layer = Literal["icu", "token", "before", "exceptions", "rules", "model", "after"]
_STREAM_WINDOW = 4 * 1024
_WHOLE_WINDOW = 64 * 1024
_OPS = {"in", "not_in", "prefix", "le", "ge"}
_FEATURES = "icukit.features@1"
_NAMED_RULE_BASES = {
    "en-tn@1": Path(__file__).with_name("data") / "break_rules" / "en" / "sentence-tn.json"
}
_EN_TN_CART_PATH = (
    Path(__file__).with_name("data") / "break_rules" / "en" / "sentence-tn-cart.json.gz"
)
_EN_TN_CART_DIGEST = "sha256:a390141818133a9fe7cbaa2b18a409d367c50996b93f9167851395a90e4eef6d"
_CARTLET_IDENTITY = {
    "icu": "78.3",
    "unicode": "17.0",
    "token_profile": "sha256:d181cf8c122b6fe98ef6ccdaa5139b35d3a1b24185a023845898a4941fd9e2d5",
}
_TOKEN_FEATURE_ORDER = (
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
)
_CHAR_FEATURE_ORDER = ("word_break", "sentence_break", "general_category", "script")
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

    A forward character position ``c+n`` has horizon equal to the number of
    right tokens ending at or before that code point, plus one when the code
    point is inside a right token, with a minimum of one. It is readable when
    that horizon is at most ``lookahead``. Thus the gap after token ``+k`` is
    readable at lookahead ``k``, while the first code point of token ``+(k+1)``
    is ``<BEYOND>``. At or past the end of the text, its horizon is the lesser
    of eight and one more than the number of right tokens; a readable position
    returns ``<EOS>``. ``tokens_read`` records this horizon, including ``k``
    rather than ``k+1`` for a gap after token ``+k``. Every ``c+n`` predicate
    therefore requires a declared lookahead of at least one.
    """

    id: str
    effect: Effect
    lookahead: int
    when: list[dict[str, object]]
    receipt: dict[str, int | float]
    witnesses: dict[str, list[str | dict[str, object]]]


class BreakDecision(TypedDict):
    """The attributed decision for one ICU sentence candidate.

    A cartlet model decision appends its model-global leaf id to ``id`` as
    ``"<model>#leaf:<id>"``.
    """

    offset: int
    end: int
    decision: Literal["break", "no-break"]
    alternatives: tuple[Literal["break", "no-break"], ...]
    layer: Layer
    id: str | None
    tokens_read: int


class PendingCandidate(TypedDict):
    """An ICU candidate awaiting stable context, a rule feature, or protection."""

    offset: int
    tokens_after: int
    waiting_on: str


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


@dataclass(frozen=True)
class CartletModelRef:
    """A digest- and runtime-bound reference to a cartlet model.

    Constructing a reference does not import cartlet. The dependency is
    imported only when a :class:`SentenceOverride` uses this reference. Model
    evaluation requires cartlet 0.7 or later.
    Models use ``icukit.features@1`` and are tied to the ICU, Unicode, and
    tokenizer identity under which those features were measured.
    """

    path: str | Path
    digest: str
    identity: Mapping[str, str] = field(default_factory=lambda: dict(_CARTLET_IDENTITY))
    features: str = _FEATURES
    name: str = "cartlet"

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path))
        digest = self.digest if self.digest.startswith("sha256:") else f"sha256:{self.digest}"
        if len(digest) != 71:
            raise ValueError("cartlet model digest must be a SHA-256 digest")
        object.__setattr__(self, "digest", digest)
        object.__setattr__(self, "identity", MappingProxyType(dict(self.identity)))
        if not self.name:
            raise ValueError("cartlet model name must be nonempty")


@dataclass(frozen=True)
class _LoadedCartletModel:
    ref: CartletModelRef
    model: object
    feature_names: tuple[str, ...]
    predicates: tuple[_CompiledPredicate, ...]
    lookahead: int


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


def _token_inventory_definition(inventory: LoadedExceptionInventory) -> dict[str, object]:
    """Return only inventory material that can change model token features."""
    rules = tuple(rule for rule in inventory._rules if "word" in rule.levels)
    # Retaining all named lists for a word-affecting inventory keeps the guard
    # conservative without binding sentence-only inventories that cannot alter
    # tokenization.
    return _inventory_definition(
        LoadedExceptionInventory(
            inventory.corpus,
            inventory.named_lists if rules else {},
            rules,
        )
    )


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
    version, locale, word-level exception inventory material, protected-span
    policy, and built-in shape definitions. Sentence-only exception rules are
    recorded in :attr:`SentenceOverride.identity` but do not enter this token
    profile because they cannot change model features. The profile version is
    bumped when the golden tokenizer behavior changes; it is not a proof
    derived from implementation text. Fixtures should call this function
    instead of hard-coding versions.
    """
    _require_raw_sentence_locale(locale)
    profile = {
        "schema": TOKEN_PROFILE,
        "locale": locale,
        "inventories": [
            definition
            for item in inventories
            if (definition := _token_inventory_definition(item))["rules"]
        ],
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


def _cartlet_runtime_identity(
    locale: str, inventories: Sequence[LoadedExceptionInventory]
) -> BreakRuleIdentity:
    identity_locale = "en" if _uses_english_cartlet_default(locale) else locale
    return break_rule_identity(identity_locale, inventories=inventories)


def _uses_english_cartlet_default(locale: str) -> bool:
    parsed = icu.Locale(locale)
    variant_subtags = {
        subtag.upper() for subtag in parsed.getVariant().replace("-", "_").split("_") if subtag
    }
    return parsed.getLanguage() == "en" and "POSIX" not in variant_subtags


def _cartlet_feature_names(lookahead: int) -> tuple[str, ...]:
    names: list[str] = []
    for at in ("-3", "-2", "-1"):
        features = _TOKEN_FEATURE_ORDER if at == "-1" else _TOKEN_FEATURE_ORDER[1:]
        names.extend(f"{feature}@{at}" for feature in features)
    names.extend(("text@run-1", "shape.cased@run-1"))
    for position in range(1, lookahead + 1):
        names.extend(f"{feature}@{position}" for feature in _TOKEN_FEATURE_ORDER)
    for position in (*range(-8, 0), *range(1, 9)):
        names.extend(f"{feature}@c{position:+d}" for feature in _CHAR_FEATURE_ORDER)
    return tuple(names)


def _load_cartlet_model(
    ref: CartletModelRef,
    locale: str,
    inventories: Sequence[LoadedExceptionInventory],
) -> _LoadedCartletModel:
    actual_digest = "sha256:" + hashlib.sha256(ref.path.read_bytes()).hexdigest()
    if actual_digest != ref.digest:
        raise BreakRuleLoadError(
            [_refuse(ref.name, "DIGEST_MISMATCH", "cartlet model bytes differ from digest")]
        )
    expected_identity = _cartlet_runtime_identity(locale, inventories)
    if dict(ref.identity) != expected_identity or ref.features != _FEATURES:
        raise BreakRuleLoadError(
            [
                _refuse(
                    ref.name,
                    "IDENTITY_MISMATCH",
                    "cartlet model ICU, Unicode, token profile, or features differ",
                )
            ]
        )
    # Keep this import lazy so base="none" and non-English locale defaults do
    # not pay the cartlet import cost. Packaging enforces cartlet>=0.7.
    from cartlet import DecisionTree

    model = DecisionTree()
    document = model.load_model(str(ref.path), format="json")
    metadata = document.get("metadata", {})
    raw_lookahead = metadata.get("k")
    if isinstance(raw_lookahead, bool) or not isinstance(raw_lookahead, int):
        raise ValueError("cartlet sentence-break model metadata must declare integer k")
    if not 0 <= raw_lookahead <= 8:
        raise ValueError("cartlet sentence-break model k must be between 0 and 8")
    feature_names = tuple(model.feature_names)
    expected_names = _cartlet_feature_names(raw_lookahead)
    if feature_names != expected_names:
        raise ValueError("cartlet sentence-break model feature schema is not icukit.features@1")
    predicates: list[_CompiledPredicate] = []
    for name in feature_names:
        feature, raw_at = name.rsplit("@", 1)
        at: int | str = int(raw_at) if raw_at.lstrip("-").isdigit() else raw_at
        predicates.append(_CompiledPredicate(at, feature, "in", ()))
    return _LoadedCartletModel(ref, model, feature_names, tuple(predicates), raw_lookahead)


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


class _FeatureNotYet(Exception):
    """A prefix does not yet make a requested feature immutable."""


class _TokenFeatureCache:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.values: dict[tuple[object, ...], dict[str, str | int | bool]] = {}
        self._toks: Sequence[Token] | None = None
        self._starts: tuple[int, ...] = ()
        self._ends: tuple[int, ...] = ()
        self._run_tokens: dict[int, tuple[Token, ...]] = {}
        self._run_ends: dict[int, tuple[int, ...]] = {}
        self._run_positions: dict[int, int] = {}
        self._run_texts: dict[int, str] = {}
        self._run_shapes: dict[int, str] = {}
        self._run_completion_horizons: dict[
            tuple[int, str, tuple[int, ...], bool], list[int | None]
        ] = {}

    def _bind(self, toks: Sequence[Token]) -> None:
        if self._toks is toks:
            return
        self._toks = toks
        self._starts = tuple(token["start"] for token in toks)
        self._ends = tuple(token["end"] for token in toks)
        self._run_positions.clear()
        grouped: dict[int, list[Token]] = {}
        for index, token in enumerate(toks):
            group = grouped.setdefault(token["run"], [])
            self._run_positions[index] = len(group)
            group.append(token)
        self._run_tokens = {run: tuple(items) for run, items in grouped.items()}
        self._run_ends = {
            run: tuple(item["end"] for item in items) for run, items in self._run_tokens.items()
        }
        self._run_texts.clear()
        self._run_shapes.clear()
        self._run_completion_horizons.clear()

    def index_after(self, toks: Sequence[Token], offset: int) -> int:
        self._bind(toks)
        return bisect_left(self._starts, offset)

    def logical_end(self, toks: Sequence[Token], offset: int) -> int:
        self._bind(toks)
        index = bisect_right(self._ends, offset) - 1
        return self._ends[index] if index >= 0 else offset

    def containing(self, toks: Sequence[Token], offset: int) -> Token | None:
        self._bind(toks)
        index = bisect_right(self._starts, offset) - 1
        if index >= 0 and offset < self._ends[index]:
            return toks[index]
        return None

    def forward_horizon(self, toks: Sequence[Token], pivot: int, index: int, text: str) -> int:
        self._bind(toks)
        if index >= len(text):
            return min(8, len(toks) - pivot + 1)
        completed = max(0, bisect_right(self._ends, index) - pivot)
        position = bisect_right(self._starts, index) - 1
        containing = position >= pivot and self._ends[position] > index
        return max(1, completed + int(containing))

    def tokens_ending_by(self, toks: Sequence[Token], pivot: int, offset: int) -> Sequence[Token]:
        self._bind(toks)
        return toks[pivot : bisect_right(self._ends, offset)]

    def count_starting_by(self, toks: Sequence[Token], pivot: int, offset: int) -> int:
        self._bind(toks)
        return max(0, bisect_right(self._starts, offset) - pivot)

    def run_start_before(self, toks: Sequence[Token], index: int, offset: int) -> int:
        self._bind(toks)
        run = toks[index]["run"]
        if not bisect_right(self._run_ends[run], offset):
            raise ValueError("no token in run ends by offset")
        return self._run_tokens[run][0]["start"]

    def run_completion_horizon(
        self,
        toks: Sequence[Token],
        index: int,
        offset: int,
        text: str,
        locale: str,
        inventories: Sequence[LoadedExceptionInventory],
        closed: bool,
    ) -> int | None:
        self._bind(toks)
        run = toks[index]["run"]
        count = bisect_right(self._run_ends[run], offset)
        key = (run, locale, tuple(id(item) for item in inventories), closed)
        prefix = self._run_completion_horizons.setdefault(key, [])
        run_tokens = self._run_tokens[run]
        while len(prefix) < count:
            horizon = _token_completion_horizon(
                run_tokens[len(prefix)], text, locale, inventories, closed
            )
            if prefix and prefix[-1] is None:
                horizon = None
            elif prefix and horizon is not None:
                horizon = max(cast(int, prefix[-1]), horizon)
            prefix.append(horizon)
        return prefix[count - 1] if count else offset

    def _key(self, toks: Sequence[Token], index: int, text: str) -> tuple[object, ...]:
        self._bind(toks)
        token = toks[index]
        run = token["run"]
        run_tokens = self._run_tokens[run]
        run_start = run_tokens[0]["start"]
        run_end = run_tokens[-1]["end"]
        if run not in self._run_texts:
            self._run_texts[run] = text[run_start:run_end]
        return (
            token["start"],
            token["end"],
            token["text"],
            run,
            self._run_texts[run],
            token.get("protected_types", ()),
        )

    def _compute_feature(
        self, toks: Sequence[Token], index: int, text: str, feature: str
    ) -> object:
        token = toks[index]
        surface = token["text"]
        if feature == "text":
            return surface
        if feature == "lower":
            return str(icu.UnicodeString(surface).toLower(icu.Locale.getRoot()))
        if feature == "len":
            return len(surface)
        if feature == "shape.coarse":
            return shape(surface, "coarse@1")
        if feature == "shape.cased":
            return shape(surface, "cased@1")
        if feature == "general_category.first":
            return char_classes(surface[0], "general_category")[0]
        if feature == "general_category.last":
            return char_classes(surface[-1], "general_category")[0]
        if feature == "sentence_break.first":
            return char_classes(surface[0], "sentence_break")[0]
        if feature == "word_break.first":
            return char_classes(surface[0], "word_break")[0]
        if feature == "script.first":
            return char_classes(surface[0], "script")[0]
        if feature == "ws.before":
            return token["start"] > 0 and text[token["start"] - 1].isspace()
        if feature == "run.shape.cased":
            run = token["run"]
            if run not in self._run_shapes:
                self._run_shapes[run] = shape(self._run_texts[run], "cased@1")
            return self._run_shapes[run]
        if feature == "lex":
            return "none"
        return "<UNKNOWN>"

    def get_value(self, toks: Sequence[Token], index: int, text: str, feature: str) -> object:
        if not self.enabled:
            return self._compute_feature(toks, index, text, feature)
        key = self._key(toks, index, text)
        values = self.values.get(key)
        if values is None:
            values = {}
            self.values[key] = values
            _token_features_base(toks, index, text, _features=frozenset())
        if feature not in values:
            values[feature] = self._compute_feature(toks, index, text, feature)
        return values.get(feature, "<UNKNOWN>")

    def get(self, toks: Sequence[Token], index: int, text: str) -> dict[str, str | int | bool]:
        """Return the complete feature mapping for compatibility with internal callers."""
        if not self.enabled:
            return _token_features_base(toks, index, text)
        key = self._key(toks, index, text)
        values = self.values.setdefault(key, {})
        if set(values) != _TOKEN_FEATURES:
            run = toks[index]["run"]
            if run not in self._run_shapes:
                self._run_shapes[run] = shape(self._run_texts[run], "cased@1")
            values.update(
                _token_features_base(
                    self._run_tokens[run],
                    self._run_positions[index],
                    text,
                    run_shape_cased=self._run_shapes[run],
                )
            )
        return values

    def evict_before(self, offset: int) -> None:
        self.values = {
            key: value for key, value in self.values.items() if cast(int, key[1]) >= offset
        }

    def clear(self) -> None:
        self.values.clear()
        self._toks = None
        self._starts = ()
        self._ends = ()
        self._run_tokens.clear()
        self._run_ends.clear()
        self._run_positions.clear()
        self._run_texts.clear()
        self._run_shapes.clear()
        self._run_completion_horizons.clear()


def _is_white_space(char: str) -> bool:
    return icu.Char.hasBinaryProperty(ord(char), icu.UProperty.WHITE_SPACE)


def _read_edge_stable(end: int, text: str, closed: bool) -> bool:
    """Whether ICU's boundary at ``end`` is immutable under extension."""
    # ICU's WB4-transparent Extend, Format and ZWJ runs make code-point
    # lookahead unbounded. White_Space is not transparent and cannot be joined
    # across by the ICU word rules, so an unabsorbed whitespace code point is
    # the first general extension-proof terminator. ICU's word rules have no
    # joining rule for a P* or S* code point with Word_Break=Other; after WB4
    # ignores its following Extend/Format/ZWJ run, WB999 therefore fixes the
    # edge as soon as the next non-ignored code point is present.
    if closed or any(_is_white_space(char) for char in text[end:]):
        return True
    if not 0 < end <= len(text):
        return False
    edge_index = end - 1
    while edge_index >= 0 and char_classes(text[edge_index], "word_break")[0] in {
        "Extend",
        "Format",
        "ZWJ",
    }:
        edge_index -= 1
    if edge_index < 0:
        return False
    category = char_classes(text[edge_index], "general_category")[0]
    word_break = char_classes(text[edge_index], "word_break")[0]
    if not (
        word_break == "Other"
        and (category.endswith("_Punctuation") or category.endswith("_Symbol"))
    ):
        return False
    return any(
        char_classes(char, "word_break")[0] not in {"Extend", "Format", "ZWJ"}
        for char in text[end:]
    )


def _extent_complete(
    start: int,
    end: int,
    text: str,
    closed: bool,
) -> bool:
    """Whether an observed extent is immutable under stream extension."""
    del start
    return _read_edge_stable(end, text, closed)


def _token_completion_horizon(
    token: Token,
    text: str,
    locale: str,
    inventories: Sequence[LoadedExceptionInventory],
    closed: bool,
) -> int | None:
    if not _extent_complete(
        token["start"],
        token["end"],
        text,
        closed,
    ):
        return None
    horizons = tuple(
        _inventory_locality_horizon(
            inventory,
            text,
            token["start"],
            locale,
            closed,
            levels=frozenset({"word"}),
        )
        for inventory in inventories
    )
    if any(item is None for item in horizons):
        return None
    return max((token["end"], *(cast(int, item) for item in horizons)))


def _forward_character_horizon(index: int, text: str, right: Sequence[Token]) -> int:
    """Return the token horizon of an absolute forward character position."""
    if index >= len(text):
        return min(8, len(right) + 1)
    completed = sum(token["end"] <= index for token in right)
    containing = any(token["start"] <= index < token["end"] for token in right)
    return max(1, completed + int(containing))


def _observed_feature_value(
    predicate: _CompiledPredicate,
    rule: _CompiledBreakRule,
    text: str,
    offset: int,
    toks: Sequence[Token],
    protected_types: tuple[str, ...],
    locale: str,
    inventories: Sequence[LoadedExceptionInventory],
    closed: bool,
    cache: _TokenFeatureCache,
) -> tuple[object, int, int]:
    """Return value, tokens read, and exclusive code-point read horizon."""
    at = predicate.at
    if at == "protected":
        return protected_types, 0, offset
    pivot = cache.index_after(toks, offset)
    if at == "run-1":
        if pivot == 0:
            return _sentinel_features("<BOS>").get(predicate.feature, "<BOS>"), 0, offset
        start = cache.run_start_before(toks, pivot - 1, offset)
        completion_horizon = cache.run_completion_horizon(
            toks,
            pivot - 1,
            offset,
            text,
            locale,
            inventories,
            closed,
        )
        if completion_horizon is None:
            raise _FeatureNotYet
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
        return (
            features.get(predicate.feature, "<UNKNOWN>"),
            0,
            max(offset, completion_horizon),
        )
    if isinstance(at, int):
        index = pivot + at - 1 if at > 0 else pivot + at
        if index < 0:
            return _sentinel_features("<BOS>").get(predicate.feature, "<BOS>"), 0, offset
        if index >= len(toks):
            if not closed:
                raise _FeatureNotYet
            reached = min(max(at, 0), max(len(toks) - pivot, 0))
            return (
                _sentinel_features("<EOS>").get(predicate.feature, "<EOS>"),
                reached,
                len(text),
            )
        token = toks[index]
        completion_horizon = _token_completion_horizon(token, text, locale, inventories, closed)
        if completion_horizon is None:
            raise _FeatureNotYet
        return (
            cache.get_value(toks, index, text, predicate.feature),
            max(at, 0),
            max(offset, completion_horizon),
        )
    distance = int(cast(str, at)[1:])
    index = offset + distance - 1 if distance > 0 else offset + distance
    if distance > 0:
        horizon = cache.forward_horizon(toks, pivot, index, text)
        if index >= len(text) and not closed:
            raise _FeatureNotYet
        completed_tokens = cache.tokens_ending_by(toks, pivot, index)
        completion_horizons = tuple(
            _token_completion_horizon(item, text, locale, inventories, closed)
            for item in completed_tokens
        )
        if any(item is None for item in completion_horizons):
            raise _FeatureNotYet
        read_horizon = max(
            offset,
            min(index + 1, len(text)),
            *(cast(int, item) for item in completion_horizons),
        )
        if horizon > rule.lookahead:
            return "<BEYOND>", rule.lookahead, read_horizon
    if index < 0:
        return "<BOS>", 0, offset
    if index >= len(text):
        return "<EOS>", horizon, read_horizon
    if distance > 0:
        window = class_window(text, index, before=0, after=1)
        return _point_feature(window.after[0], predicate.feature), horizon, read_horizon
    containing = cache.containing(toks, index)
    completion_horizon = None
    if containing is not None:
        completion_horizon = _token_completion_horizon(
            containing, text, locale, inventories, closed
        )
        if completion_horizon is None:
            raise _FeatureNotYet
    window = class_window(text, index, before=0, after=1)
    tokens_read = 0
    if distance > 0:
        tokens_read = min(cache.count_starting_by(toks, pivot, index), rule.lookahead)
    horizon = completion_horizon if completion_horizon is not None else index + 1
    return _point_feature(window.after[0], predicate.feature), tokens_read, max(offset, horizon)


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


def _match_observed_rule(
    rule: _CompiledBreakRule,
    text: str,
    offset: int,
    toks: Sequence[Token],
    protected_types: tuple[str, ...],
    locale: str,
    inventories: Sequence[LoadedExceptionInventory],
    closed: bool,
    cache: _TokenFeatureCache,
) -> tuple[bool | None, int, int]:
    """Return match, token reach, and read horizon; None means not yet decidable."""
    read = 0
    horizon = offset
    for predicate in rule.when:
        try:
            value, reached, predicate_horizon = _observed_feature_value(
                predicate,
                rule,
                text,
                offset,
                toks,
                protected_types,
                locale,
                inventories,
                closed,
                cache,
            )
        except _FeatureNotYet:
            # Predicate order is semantic.  An unavailable earlier feature
            # holds this rule; later predicates cannot exclude it early or
            # make the attributed read depend on chunk boundaries.
            return None, read, horizon
        read = max(read, reached)
        horizon = max(horizon, predicate_horizon)
        if not _predicate_matches(value, predicate):
            return False, read, horizon
    return True, read, horizon


class _CartletFeatureVector(Sequence[object]):
    """A model-width vector that computes only the path cartlet requests."""

    def __init__(
        self,
        loaded: _LoadedCartletModel,
        text: str,
        offset: int,
        toks: Sequence[Token],
        protected_types: tuple[str, ...],
        locale: str,
        inventories: Sequence[LoadedExceptionInventory],
        closed: bool,
        cache: _TokenFeatureCache,
    ) -> None:
        self.loaded = loaded
        self.text = text
        self.offset = offset
        self.toks = toks
        self.protected_types = protected_types
        self.locale = locale
        self.inventories = inventories
        self.closed = closed
        self.cache = cache
        self.tokens_read = 0
        self.horizon = offset
        self.indices_read: list[int] = []
        self._rule = _CompiledBreakRule(loaded.ref.name, "break", loaded.lookahead, ())

    def __len__(self) -> int:
        return len(self.loaded.feature_names)

    def __getitem__(self, index: int | slice) -> object:
        if isinstance(index, slice):
            return [self[item] for item in range(*index.indices(len(self)))]
        normalized = index + len(self) if index < 0 else index
        if not 0 <= normalized < len(self):
            raise IndexError(index)
        value, reached, horizon = _observed_feature_value(
            self.loaded.predicates[normalized],
            self._rule,
            self.text,
            self.offset,
            self.toks,
            self.protected_types,
            self.locale,
            self.inventories,
            self.closed,
            self.cache,
        )
        self.tokens_read = max(self.tokens_read, reached)
        self.horizon = max(self.horizon, horizon)
        self.indices_read.append(normalized)
        return value


def _cartlet_label(prediction: object) -> str:
    if isinstance(prediction, dict):
        prediction = max(prediction, key=prediction.__getitem__)
    return str(prediction)


def _observed_model_decision(
    loaded: _LoadedCartletModel,
    text: str,
    offset: int,
    end: int,
    toks: Sequence[Token],
    protected_types: tuple[str, ...],
    locale: str,
    inventories: Sequence[LoadedExceptionInventory],
    closed: bool,
    cache: _TokenFeatureCache,
) -> _ObservedResult:
    vector = _CartletFeatureVector(
        loaded,
        text,
        offset,
        toks,
        protected_types,
        locale,
        inventories,
        closed,
        cache,
    )
    try:
        path = loaded.model.predict_path(vector)
    except _FeatureNotYet:
        return _ObservedResult(None, "model", vector.tokens_read, vector.horizon)
    label = _cartlet_label(path["prediction"])
    if label not in {"0", "1"}:
        raise ValueError(f"cartlet sentence-break model returned unknown label {label!r}")
    leaf = path["trees"][0]["leaf"]
    effect: Effect = "break" if label == "1" else "no-break"
    return _ObservedResult(
        _decision(
            offset,
            end,
            effect,
            "model",
            f"{loaded.ref.name}#leaf:{leaf}",
            vector.tokens_read,
        ),
        None,
        vector.tokens_read,
        vector.horizon,
    )


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


@dataclass(frozen=True)
class _ObservedResult:
    decision: BreakDecision | None
    waiting_on: str | None
    tokens_read: int
    horizon: int


def _observed_rules_decision(
    rule_sets: Sequence[BreakRuleSet],
    layer: Layer,
    text: str,
    offset: int,
    end: int,
    toks: Sequence[Token],
    protected_types: tuple[str, ...],
    locale: str,
    inventories: Sequence[LoadedExceptionInventory],
    closed: bool,
    cache: _TokenFeatureCache,
) -> _ObservedResult:
    read = 0
    horizon = offset
    for rule_set in rule_sets:
        for rule in rule_set._rules:
            matched, reached, rule_horizon = _match_observed_rule(
                rule,
                text,
                offset,
                toks,
                protected_types,
                locale,
                inventories,
                closed,
                cache,
            )
            read = max(read, reached)
            horizon = max(horizon, rule_horizon)
            if matched is None:
                return _ObservedResult(None, rule.id, read, horizon)
            if matched:
                decision = _decision(offset, end, rule.effect, layer, rule.id, read)
                return _ObservedResult(decision, None, read, horizon)
    return _ObservedResult(None, None, read, horizon)


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
                combined_inventory = _combined_inventory(inventories, levels=frozenset({"word"}))
                toks = tokens(text, locale, inventory=combined_inventory, protected=protected_items)
                decisions = []
                for span in _raw_break_sentence_spans(text, locale):
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
                    observed = _observed_rules_decision(
                        (rule_set,),
                        "rules",
                        text,
                        offset,
                        _logical_end(toks, offset),
                        toks,
                        covering,
                        locale,
                        inventories,
                        True,
                        _TokenFeatureCache(True),
                    )
                    if observed.decision is not None:
                        decisions.append(observed.decision)
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
    inventory: LoadedExceptionInventory,
    text: str,
    locale: str,
    base: list[BreakSpan] | None = None,
) -> dict[int, list[str]]:
    base = base if base is not None else _raw_break_sentence_spans(text, locale)
    selected = [
        rule
        for rule in inventory._rules
        if "sentence" in rule.levels
        and rule.effect == "suppress"
        and _locale_applies(rule.locale, locale)
    ]
    return _sentence_boundary_claims(
        text,
        base,
        selected,
        locale,
        ExceptionPolicy(),
        _mandatory_info_supplier(text, locale),
    )


def _inventory_claims_legacy(
    inventory: LoadedExceptionInventory,
    text: str,
    locale: str,
    base: list[BreakSpan] | None = None,
) -> dict[int, list[str]]:
    """Return sentence claims through the former whole-text rule scan."""
    base = base if base is not None else _raw_break_sentence_spans(text, locale)
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


def _combined_inventory(
    inventories: Sequence[LoadedExceptionInventory],
    *,
    levels: frozenset[str] | None = None,
) -> LoadedExceptionInventory | None:
    rules = tuple(
        rule
        for item in inventories
        for rule in item._rules
        if levels is None or levels & set(rule.levels)
    )
    if not rules:
        return None
    return LoadedExceptionInventory(
        " + ".join(item.corpus for item in inventories),
        {key: value for item in inventories for key, value in item.named_lists.items()},
        rules,
    )


def _inventory_rules(
    inventory: LoadedExceptionInventory,
    locale: str,
    levels: frozenset[str] = frozenset({"word", "sentence"}),
) -> tuple[object, ...]:
    """Rules whose matcher results can affect a streamed sentence decision."""
    return tuple(
        rule
        for rule in inventory._rules
        if (levels & set(rule.levels))
        and rule.effect == "suppress"
        and _locale_applies(rule.locale, locale)
    )


def _whitespace_terminated_horizon(text: str, end: int) -> int | None:
    """Return the exclusive end of the first whitespace terminator after ``end``."""
    if end > len(text):
        return None
    terminator = next(
        (index for index in range(end, len(text)) if _is_white_space(text[index])),
        None,
    )
    return None if terminator is None else terminator + 1


def _inventory_locality_horizon(
    inventory: LoadedExceptionInventory,
    text: str,
    anchor: int,
    locale: str,
    closed: bool,
    *,
    levels: frozenset[str] = frozenset({"word", "sentence"}),
) -> int | None:
    """Return the real inventory matcher's exclusive right read horizon.

    Static reach is derived by ``exceptions._context_bounds`` through the
    public ``context_bounds`` property. Every possible exact surface is first
    completed from the candidate-side anchor through the inventory's maximum
    surface length and a whitespace terminator. An unbounded whitespace skip
    is then made finite for the current buffer by observing its complete next
    whitespace run, the following ICU word span, and whitespace terminating
    that span.
    """
    if closed:
        return len(text)
    rules = _inventory_rules(inventory, locale, levels)
    if not rules:
        return anchor
    local = LoadedExceptionInventory(inventory.corpus, inventory.named_lists, rules)
    bounds = local.context_bounds
    surface_end = anchor + bounds.max_surface_length
    surface_horizon = _whitespace_terminated_horizon(text, surface_end)
    if surface_horizon is None:
        return None

    reach = bounds.right_from_match_start
    if reach is not None:
        target = anchor + reach
        horizon = _whitespace_terminated_horizon(text, target)
        return None if horizon is None else max(surface_horizon, horizon)

    whitespace = next(
        (index for index in range(surface_end, len(text)) if _is_white_space(text[index])),
        None,
    )
    if whitespace is None:
        return None
    following = whitespace
    while following < len(text) and _is_white_space(text[following]):
        following += 1
    if following == len(text):
        return None
    word = next(
        (
            span
            for span in break_word_spans(text, locale)
            if span["start"] <= following < span["end"]
        ),
        None,
    )
    end = following + 1 if word is None else word["end"]
    condition_horizon = _whitespace_terminated_horizon(text, end)
    return None if condition_horizon is None else max(surface_horizon, condition_horizon)


def _inventory_anchor(toks: Sequence[Token], pivot: int, offset: int, lookahead: int) -> int:
    """End of the furthest word a candidate's flat rules may inspect."""
    if lookahead <= 0:
        return offset
    read = toks[pivot : pivot + lookahead]
    return read[-1]["end"] if read else offset


def _protected_types_by_offset(
    protected: Sequence[ProtectedSpan], offsets: Sequence[int]
) -> dict[int, tuple[str, ...]]:
    """Return protected types strictly covering each candidate offset."""
    starts = sorted(protected, key=lambda item: item["start"])
    ends = sorted(protected, key=lambda item: item["end"])
    active: dict[str, int] = {}
    result: dict[int, tuple[str, ...]] = {}
    start_index = 0
    end_index = 0
    for offset in sorted(set(offsets)):
        while start_index < len(starts) and starts[start_index]["start"] < offset:
            protected_type = starts[start_index]["type"]
            active[protected_type] = active.get(protected_type, 0) + 1
            start_index += 1
        while end_index < len(ends) and ends[end_index]["end"] <= offset:
            protected_type = ends[end_index]["type"]
            remaining = active[protected_type] - 1
            if remaining:
                active[protected_type] = remaining
            else:
                del active[protected_type]
            end_index += 1
        result[offset] = tuple(sorted(active))
    return result


def _candidate_observed(
    owner: SentenceOverride,
    word_inventories: Sequence[LoadedExceptionInventory],
    text: str,
    offset: int,
    toks: Sequence[Token],
    protected_types: tuple[str, ...],
    closed: bool,
    cache: _TokenFeatureCache,
    inventory_claims: dict[int, dict[int, list[str]]],
    candidates: list[BreakSpan],
) -> _ObservedResult:
    pivot = cache.index_after(toks, offset)
    previous = toks[pivot - 1] if pivot else None
    containing = previous if previous is not None and offset < previous["end"] else None
    end = containing["end"] if containing is not None else cache.logical_end(toks, offset)
    if containing is not None:
        completion_horizon = containing["end"]
        if word_inventories and "protected" not in containing:
            observed_horizon = _token_completion_horizon(
                containing,
                text,
                owner.locale,
                word_inventories,
                closed,
            )
            if observed_horizon is None:
                return _ObservedResult(None, "exceptions", 0, offset)
            completion_horizon = observed_horizon
        return _ObservedResult(
            _decision(offset, end, "no-break", "token", None, 0),
            None,
            0,
            completion_horizon,
        )

    read = 0
    word_locality_horizons = tuple(
        _inventory_locality_horizon(
            inventory,
            text,
            offset,
            owner.locale,
            closed,
            levels=frozenset({"word"}),
        )
        for inventory in word_inventories
    )
    if any(item is None for item in word_locality_horizons):
        return _ObservedResult(None, "exceptions", read, offset)
    horizon = max((offset, *(cast(int, item) for item in word_locality_horizons)))

    before = _observed_rules_decision(
        owner.before,
        "before",
        text,
        offset,
        end,
        toks,
        protected_types,
        owner.locale,
        owner.inventories,
        closed,
        cache,
    )
    read = max(read, before.tokens_read)
    horizon = max(horizon, before.horizon)
    if before.waiting_on is not None:
        return _ObservedResult(None, before.waiting_on, read, horizon)
    if before.decision is not None:
        decision = dict(before.decision)
        decision["tokens_read"] = read
        return _ObservedResult(cast(BreakDecision, decision), None, read, horizon)

    anchor = _inventory_anchor(toks, pivot, offset, owner.lookahead)
    locality_horizons = tuple(
        _inventory_locality_horizon(
            inventory,
            text,
            anchor,
            owner.locale,
            closed,
            levels=frozenset({"sentence"}),
        )
        for inventory in owner.inventories
    )
    if any(item is None for item in locality_horizons):
        return _ObservedResult(None, "exceptions", read, horizon)
    horizon = max((horizon, *(cast(int, item) for item in locality_horizons)))

    for inventory in owner.inventories:
        key = id(inventory)
        if key not in inventory_claims:
            inventory_claims[key] = _inventory_claims(inventory, text, owner.locale, candidates)
        rule_ids = inventory_claims[key].get(offset)
        if rule_ids:
            return _ObservedResult(
                _decision(offset, end, "no-break", "exceptions", rule_ids[0], read),
                None,
                read,
                horizon,
            )

    if owner.base is None:
        current = _decision(offset, end, "break", "icu", None, read)
    elif isinstance(owner.base, BreakRuleSet):
        base = _observed_rules_decision(
            (owner.base,),
            "rules",
            text,
            offset,
            end,
            toks,
            protected_types,
            owner.locale,
            owner.inventories,
            closed,
            cache,
        )
        read = max(read, base.tokens_read)
        horizon = max(horizon, base.horizon)
        if base.waiting_on is not None:
            return _ObservedResult(None, base.waiting_on, read, horizon)
        current = base.decision or _decision(offset, end, "break", "icu", None, read)
    else:
        base = _observed_model_decision(
            owner.base,
            text,
            offset,
            end,
            toks,
            protected_types,
            owner.locale,
            owner.inventories,
            closed,
            cache,
        )
        read = max(read, base.tokens_read)
        horizon = max(horizon, base.horizon)
        if base.waiting_on is not None:
            return _ObservedResult(None, "model", read, horizon)
        if base.decision is None:
            raise AssertionError("cartlet model returned neither a decision nor a wait")
        current = base.decision

    after = _observed_rules_decision(
        owner.after,
        "after",
        text,
        offset,
        end,
        toks,
        protected_types,
        owner.locale,
        owner.inventories,
        closed,
        cache,
    )
    read = max(read, after.tokens_read)
    horizon = max(horizon, after.horizon)
    if after.waiting_on is not None:
        return _ObservedResult(None, after.waiting_on, read, horizon)
    if after.decision is not None:
        current = after.decision
    copied = dict(current)
    copied["tokens_read"] = read
    return _ObservedResult(cast(BreakDecision, copied), None, read, horizon)


def _icu_stable(text: str, offset: int) -> bool:
    # A buffer-end candidate, including one followed only by Close/Sp or any
    # other whitespace, is provisional until a non-whitespace code point or
    # END has arrived.
    if not any(not _is_white_space(char) for char in text[offset:]):
        return False
    if offset < len(text):
        suffix = text[offset:]
        if any(
            value in {"Upper", "Lower", "OLetter"}
            for value in (char_classes(char, "sentence_break")[0] for char in suffix)
        ):
            return True
    prefix = text[:offset].rstrip(" \t")
    if not prefix:
        return False
    hard = char_classes(prefix[-1], "sentence_break")[0]
    if hard in {"LF", "Sep"}:
        return True
    return hard == "CR" and offset < len(text) and text[offset] != "\n"


class IncrementalSentenceBreaker:
    """Incrementally decide ICU sentence candidates with immutable output.

    Instances are created by :meth:`SentenceOverride.stream`. Offsets are code
    points in all text supplied so far. ``flush()`` treats the current end as
    END but permits later input; ``close()`` also prevents further input.

    Example:
        >>> stream = SentenceOverride().stream()
        >>> stream.feed("Hello. N") + stream.feed("ext.") + stream.close()
        [{'offset': 7, 'end': 6, 'decision': 'break', 'alternatives': ('break',),
          'layer': 'icu', 'id': None, 'tokens_read': 0},
         {'offset': 11, 'end': 11, 'decision': 'break', 'alternatives': ('break',),
          'layer': 'icu', 'id': None, 'tokens_read': 0}]
    """

    def __init__(self, owner: SentenceOverride, protection: Literal["none", "watermark"]) -> None:
        self._owner = owner
        self._protection = protection
        self._text = ""
        self._base_offset = 0
        self._total_length = 0
        self._protected: list[ProtectedSpan] = []
        self._emitted_through = -1
        self._read_horizon = 0
        self._watermark = 0
        self._pending: list[PendingCandidate] = []
        self._closed = False
        self._cache = _TokenFeatureCache(owner.cache)
        self.lookahead = owner.lookahead
        self._left_tokens = owner._left_tokens

    def _prospective_protected(
        self, additions: Iterable[ProtectedSpan], text_length: int
    ) -> list[ProtectedSpan]:
        items = [*self._protected, *(cast(ProtectedSpan, dict(item)) for item in additions)]
        _validated_protected(items, text_length)
        new_items = items[len(self._protected) :]
        for span in new_items:
            if self._protection == "watermark":
                if span["start"] < self._watermark:
                    raise LateProtectedSpan(
                        f"protected span starts at {span['start']} below "
                        f"watermark {self._watermark}"
                    )
            elif span["start"] < self._read_horizon:
                raise LateProtectedSpan(
                    f"protected span [{span['start']}, {span['end']}) arrived after emitted context"
                )
        return items

    def _local_protected(self) -> list[ProtectedSpan]:
        return [
            cast(
                ProtectedSpan,
                {
                    **item,
                    "start": item["start"] - self._base_offset,
                    "end": item["end"] - self._base_offset,
                },
            )
            for item in self._protected
            if item["end"] > self._base_offset
        ]

    def _inventory_left_context(self) -> int | None:
        """Return finite character lookbehind, or None for an unbounded rule."""
        reach = 0
        for inventory in self._owner.inventories:
            rules = _inventory_rules(inventory, self._owner.locale)
            if not rules:
                continue
            bounds = LoadedExceptionInventory(
                inventory.corpus,
                inventory.named_lists,
                cast(tuple, rules),
            ).context_bounds
            if bounds.left is None:
                return None
            reach = max(reach, bounds.max_surface_length + bounds.left)
        return reach

    def _compact(
        self,
        text: str,
        toks: Sequence[Token],
        candidates: Sequence[BreakSpan],
        *,
        force: bool = False,
    ) -> None:
        """Discard a settled prefix while retaining a restart-safe overlap.

        ICU sentence rules corresponding to UAX #29 SB6-SB8 and SB8a-SB11
        carry abbreviation and terminator state through ``Close``, ``Sp`` and
        ignored-format runs. Word rules WB6-WB7 carry letter state through
        mid-token punctuation, WB4 ignores ``Extend``/``Format``/``ZWJ``, and
        WB15-WB16 carry regional-indicator parity. Restarting inside any of
        those runs is unsafe. We restart where both ICU iterators have emitted
        a boundary, or immediately after an ICU ``CR``, ``LF`` or ``Sep`` hard
        break. At the joint boundary both iterators are in accepting reset
        positions. The hard-break alternative resets the sentence rules and
        the word rules regardless of their preceding state, so segmenting the
        suffix produces the same later boundaries as uninterrupted iteration.

        The restart precedes every token that a future predicate can inspect,
        plus one full sentence interval. That extra interval preserves the
        character before the first retained token (notably ``ws.before``) and
        makes the retained tokenization independent of the artificial buffer
        start. Complete whitespace-delimited runs are retained because
        ``run-1`` and ``run.shape.cased`` inspect the whole run.

        Exact exception rules add their declared finite character lookbehind.
        The restart is strictly earlier than that reach, preserving the
        anchored matcher's left-edge guard as well as every declared surface
        and left condition.
        A rule with unbounded left context is the one intentional fallback: the
        prefix is kept until flush/close or a mandatory segment reset, because
        discarding it could change a later inventory match.
        """
        if not force and len(text) <= _STREAM_WINDOW:
            return
        inventory_reach = self._inventory_left_context()
        if inventory_reach is None or not candidates:
            return

        needed = max(0, len(text) - inventory_reach)
        if toks:
            first = max(0, len(toks) - max(1, self._left_tokens))
            needed = min(needed, toks[first]["start"])
            trailing_run = toks[-1]["run"]
            needed = min(
                needed,
                min(token["start"] for token in toks if token["run"] == trailing_run),
            )
        for item in self._pending:
            local_offset = item["offset"] - self._base_offset
            pivot = self._cache.index_after(toks, local_offset)
            if toks:
                first = max(0, pivot - max(1, self._left_tokens))
                needed = min(needed, toks[first]["start"] if first < len(toks) else len(text))
            if pivot:
                run = toks[pivot - 1]["run"]
                needed = min(
                    needed,
                    min(token["start"] for token in toks if token["run"] == run),
                )
        for span in self._protected:
            if span["end"] > self._base_offset + needed:
                needed = min(needed, max(0, span["start"] - self._base_offset))

        word_boundaries = {0, len(text)}
        for token in toks:
            word_boundaries.add(token["start"])
            word_boundaries.add(token["end"])
        settled = [
            span["end"]
            for span in candidates
            if self._base_offset + span["end"] <= self._emitted_through
            and span["end"] < needed
            and (
                span["end"] in word_boundaries
                or any(
                    char_classes(char, "sentence_break")[0] in {"CR", "LF", "Sep"}
                    for char in span["text"]
                )
            )
        ]
        if not settled:
            return
        drop = settled[-1]
        if drop <= 0:
            return
        self._text = text[drop:]
        self._base_offset += drop
        self._protected = [item for item in self._protected if item["end"] > self._base_offset]
        self._cache.clear()

    def _evaluate(self, *, closed: bool) -> list[BreakDecision]:
        text = self._text
        with _offset_map_scope(text):
            return self._evaluate_scoped(text, closed=closed)

    def _evaluate_scoped(self, text: str, *, closed: bool) -> list[BreakDecision]:
        emitted: list[BreakDecision] = []
        pending: list[PendingCandidate] = []
        earlier_pending = False
        protected = self._local_protected()
        combined = _combined_inventory(self._owner.inventories, levels=frozenset({"word"}))
        plain_closed = (
            closed
            and self._owner.base is None
            and not self._owner.before
            and not self._owner.after
            and not self._owner.inventories
            and not protected
        )
        candidates = _raw_break_sentence_spans(text, self._owner.locale)
        toks = (
            []
            if plain_closed
            else tokens(
                text,
                self._owner.locale,
                inventory=combined,
                protected=protected,
            )
        )
        protected_types = _protected_types_by_offset(
            protected, tuple(span["end"] for span in candidates)
        )
        inventory_claims: dict[int, dict[int, list[str]]] = {}
        word_inventories = tuple(
            inventory
            for inventory in self._owner.inventories
            if _inventory_rules(inventory, self._owner.locale, frozenset({"word"}))
        )
        plain_logical_end: int | None = None
        for span in candidates:
            local_offset = span["end"]
            offset = self._base_offset + local_offset
            if offset <= self._emitted_through:
                continue
            tokens_after = len(toks) - self._cache.index_after(toks, local_offset)
            if earlier_pending:
                pending.append(
                    {"offset": offset, "tokens_after": tokens_after, "waiting_on": "order"}
                )
                continue
            if not closed and not _icu_stable(text, local_offset):
                pending.append(
                    {"offset": offset, "tokens_after": tokens_after, "waiting_on": "icu"}
                )
                earlier_pending = True
                continue
            if plain_closed:
                stripped = span["text"].rstrip()
                if stripped:
                    plain_logical_end = span["start"] + len(stripped)
                logical_end = plain_logical_end if plain_logical_end is not None else local_offset
                observed = _ObservedResult(
                    _decision(local_offset, logical_end, "break", "icu", None, 0),
                    None,
                    0,
                    local_offset,
                )
            else:
                observed = _candidate_observed(
                    self._owner,
                    word_inventories,
                    text,
                    local_offset,
                    toks,
                    protected_types[local_offset],
                    closed,
                    self._cache,
                    inventory_claims,
                    candidates,
                )
            if observed.decision is None:
                pending.append(
                    {
                        "offset": offset,
                        "tokens_after": tokens_after,
                        "waiting_on": observed.waiting_on or "model",
                    }
                )
                earlier_pending = True
                continue
            horizon = self._base_offset + observed.horizon
            if self._protection == "watermark" and horizon > self._watermark and not closed:
                pending.append(
                    {"offset": offset, "tokens_after": tokens_after, "waiting_on": "protection"}
                )
                earlier_pending = True
                continue
            self._emitted_through = offset
            self._read_horizon = max(self._read_horizon, horizon)
            decision = dict(observed.decision)
            decision["offset"] += self._base_offset
            decision["end"] += self._base_offset
            emitted.append(cast(BreakDecision, decision))
        self._pending = pending
        reachable_starts: list[int] = []
        if toks:
            reachable_starts.append(toks[max(0, len(toks) - max(1, self._left_tokens))]["start"])
            current_run = toks[-1]["run"]
            reachable_starts.extend(token["start"] for token in toks if token["run"] == current_run)
        if pending:
            for item in pending:
                pivot = _token_index_after(toks, item["offset"] - self._base_offset)
                if toks:
                    reachable_starts.append(
                        toks[max(0, pivot - max(1, self._left_tokens))]["start"]
                    )
                if pivot:
                    previous_run = toks[pivot - 1]["run"]
                    reachable_starts.extend(
                        token["start"] for token in toks if token["run"] == previous_run
                    )
        self._cache.evict_before(min(reachable_starts, default=len(text)))
        if not closed:
            self._compact(text, toks, candidates)
        return emitted

    def feed(
        self,
        chunk: str,
        /,
        *,
        protected: Iterable[ProtectedSpan] = (),
        protected_through: int | None = None,
    ) -> list[BreakDecision]:
        """Append a chunk and return decisions made immutable by this prefix."""
        if self._closed:
            raise RuntimeError("incremental sentence breaker is closed")
        if not isinstance(chunk, str):
            raise TypeError("chunk must be str")
        additions = tuple(protected)
        prospective_length = self._total_length + len(chunk)
        prospective_protected = self._prospective_protected(additions, prospective_length)
        if protected_through is not None:
            if self._protection != "watermark":
                raise ValueError("protected_through requires protection='watermark'")
            if (
                not isinstance(protected_through, int)
                or isinstance(protected_through, bool)
                or not self._watermark <= protected_through <= prospective_length
            ):
                raise ValueError("protected_through must advance within buffered text")
        self._protected = prospective_protected
        if not additions and len(chunk) > _STREAM_WINDOW:
            emitted: list[BreakDecision] = []
            start = 0
            while start < len(chunk):
                part = chunk[start : start + _STREAM_WINDOW]
                self._text += part
                self._total_length += len(part)
                if protected_through is not None:
                    self._watermark = min(protected_through, self._total_length)
                emitted.extend(self._evaluate(closed=False))
                start += len(part)
            return emitted
        self._text += chunk
        self._total_length = prospective_length
        if protected_through is not None:
            self._watermark = protected_through
        return self._evaluate(closed=False)

    def pending(self) -> list[PendingCandidate]:
        """Return snapshots of candidates that still need context or protection."""
        return [dict(item) for item in self._pending]  # type: ignore[misc]

    def flush(self) -> list[BreakDecision]:
        """End the current logical segment without closing the stream.

        Current candidates are decided with END as context. Later input starts
        a new ICU segment, so its decisions equal whole-text decisions for the
        post-flush text alone, shifted by the flushed stream length.
        """
        if self._closed:
            return []
        if self._protection == "watermark":
            self._watermark = self._total_length
        result = self._evaluate(closed=True)
        self._pending = []
        self._base_offset = self._total_length
        self._text = ""
        self._protected = []
        # Cache keys and every eviction threshold are segment-local. A flush
        # starts a new coordinate space, so no prior key can be retained.
        self._cache.clear()
        return result

    def close(self) -> list[BreakDecision]:
        """Flush once and reject later input; repeated calls return an empty list."""
        if self._closed:
            return []
        result = self.flush()
        self._closed = True
        return result

    def _whole(self, text: str, protected: Iterable[ProtectedSpan] = ()) -> list[BreakDecision]:
        """Feed one complete logical segment directly into the closed core."""
        if not isinstance(text, str):
            raise TypeError("chunk must be str")
        protected_items = tuple(protected)
        if len(text) > _WHOLE_WINDOW:
            _validated_protected(protected_items, len(text))
            result: list[BreakDecision] = []
            remaining = list(protected_items)
            start = 0
            while start < len(text):
                end = min(start + _WHOLE_WINDOW, len(text))
                # A protected unit is indivisible. If a nominal window ends
                # inside one, extend through that unit (and through any nested
                # or chained unit reached by the extension). This is the safe
                # boundedness fallback for an individually oversized span.
                while True:
                    extended = max(
                        (
                            int(span["end"])
                            for span in remaining
                            if int(span["start"]) < end < int(span["end"])
                        ),
                        default=end,
                    )
                    if extended == end:
                        break
                    end = extended
                additions = [span for span in remaining if int(span["end"]) <= end]
                remaining = [span for span in remaining if span not in additions]
                self._protected = self._prospective_protected(additions, end)
                part = text[start:end]
                self._text += part
                self._total_length += len(part)
                if end == len(text):
                    result.extend(self.close())
                else:
                    result.extend(self._evaluate(closed=False))
                start = end
            return result
        self._protected = self._prospective_protected(protected_items, len(text))
        self._text = text
        self._total_length = len(text)
        return self.close()


class SentenceOverride:
    """Apply rules or a cartlet model to ICU sentence candidates.

    ``en-tn@1`` is a learned English rule base under
    CC BY-SA 4.0. Its reported development and test figures measure agreement
    with the Google TN corpus splitter on synthetic ``glue2`` concatenations,
    not accuracy on naturally occurring running text. Its witnesses are
    synthesized from each rule's predicates, which include lexical values
    mined from the corpus (e.g. ``lower`` token values); no corpus sentence or
    row was read or copied.

    The locale-default base is:

    ================ =================
    Locale language  Default base
    ================ =================
    ``en``           ``en-tn-cart@1`` (except ``POSIX``)
    every other      ``none``
    ================ =================

    Region and script do not change the English default. The ``POSIX`` variant
    uses ``"none"`` because its ICU word tokens differ from the model profile.
    The English default and the two learned English named bases load the
    locale-fallback abbreviation lexicon's ``break="suppress"`` entries as
    sentence exceptions. Decisions are ordered as ICU candidates, token
    integrity, caller-before rules, exceptions, the base, and caller-after
    rules. Pass ``base="none"`` explicitly for plain ICU sentence boundaries
    without the shipped list. Cartlet is an icukit dependency and is imported
    lazily only when a cartlet model is selected.

    Args:
        locale: ICU locale used for both sentence and word boundaries.
        base: ``None`` selects the locale default in the table above. Otherwise,
            ``"none"`` selects plain ICU, ``"en-tn@1"`` selects the learned
            rule base, ``"en-tn-cart@1"`` selects the learned model, and callers
            may supply a loaded rule set, a :class:`CartletModelRef`, or a path
            to a ``break-rules`` JSON file. Unknown names are refused.
        before: Ordered caller rules that force a decision before inventories
            and the base.
        after: Ordered caller rules that may override the base decision.
        inventories: Exception inventories; word rules merge tokens and
            sentence rules suppress candidates.
        cache: Reuse immutable per-token features in incremental evaluation.

    Example:
        >>> from icukit import break_sentence_spans
        >>> SentenceOverride(base="none").spans("Hello. Next.") == break_sentence_spans(
        ...     "Hello. Next.", "en_US", base="none"
        ... )
        True
    """

    def __init__(
        self,
        locale: str = "en_US",
        /,
        *,
        base: Literal["none"] | str | Path | BreakRuleSet | CartletModelRef | None = None,
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
        locale_default = base is None
        if locale_default:
            base = "en-tn-cart@1" if _uses_english_cartlet_default(locale) else "none"
        selected_inventories = tuple(inventories)
        if (
            isinstance(base, str)
            and base in {"en-tn@1", "en-tn-cart@1"}
            and _uses_english_cartlet_default(locale)
        ):
            shipped = _load_break_exception_inventory(locale)
            if shipped is not None:
                selected_inventories = (shipped, *selected_inventories)
        self.inventories = selected_inventories
        expected = break_rule_identity(locale, inventories=self.inventories)
        if base == "none":
            loaded_base = None
        elif isinstance(base, BreakRuleSet):
            loaded_base = base
        elif isinstance(base, CartletModelRef):
            loaded_base = _load_cartlet_model(base, locale, self.inventories)
        elif base == "en-tn-cart@1":
            loaded_base = _load_cartlet_model(
                CartletModelRef(
                    _EN_TN_CART_PATH,
                    _EN_TN_CART_DIGEST,
                    identity=_CARTLET_IDENTITY,
                    name="en-tn-cart@1",
                ),
                locale,
                self.inventories,
            )
        elif isinstance(base, str) and base in _NAMED_RULE_BASES:
            loaded_base = load_break_rules(
                _NAMED_RULE_BASES[base], locale=locale, inventories=self.inventories
            )
        elif isinstance(base, Path) or (isinstance(base, str) and Path(base).is_file()):
            loaded_base = load_break_rules(base, locale=locale, inventories=self.inventories)
        elif isinstance(base, str):
            raise ValueError(f"unknown sentence-override base {base!r}")
        else:
            raise TypeError(
                "base must be None, 'none', a named base, a BreakRuleSet, "
                "a CartletModelRef, or a break-rules JSON path"
            )
        self.base = loaded_base
        self.before = tuple(before)
        self.after = tuple(after)
        layers = (
            *self.before,
            *((loaded_base,) if isinstance(loaded_base, BreakRuleSet) else ()),
            *self.after,
        )
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
            "base": (
                loaded_base.digest
                if isinstance(loaded_base, BreakRuleSet)
                else loaded_base.ref.digest
                if isinstance(loaded_base, _LoadedCartletModel)
                else "none"
            ),
            "after": [item.digest for item in self.after],
            "features": _FEATURES,
        }
        self.identity = "sha256:" + hashlib.sha256(_canonical(definition)).hexdigest()
        self.lookahead = max(
            (*(item.lookahead for item in layers), loaded_base.lookahead if loaded_base else 0)
        )
        predicates = [
            predicate for rule_set in layers for rule in rule_set._rules for predicate in rule.when
        ]
        if isinstance(loaded_base, _LoadedCartletModel):
            predicates.extend(loaded_base.predicates)
        self._left_tokens = max(
            (
                abs(predicate.at)
                for predicate in predicates
                if isinstance(predicate.at, int) and predicate.at < 0
            ),
            default=0,
        )

    def decide(
        self, text: str, /, *, protected: Iterable[ProtectedSpan] = ()
    ) -> list[BreakDecision]:
        """Return an attributed decision for every raw ICU sentence candidate."""
        if not text:
            return []
        return IncrementalSentenceBreaker(self, "none")._whole(text, protected)

    def spans(self, text: str, /, *, protected: Iterable[ProtectedSpan] = ()) -> list[BreakSpan]:
        """Return the one-best sentence spans; trailing whitespace stays left."""
        decisions = self.decide(text, protected=protected)
        return _decision_spans(text, decisions)

    def segmentations(
        self, text: str, /, *, protected: Iterable[ProtectedSpan] = ()
    ) -> BreakSegmentation:
        """Return one-best spans and each candidate retaining two alternatives."""
        decisions = self.decide(text, protected=protected)
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
        return {"spans": _decision_spans(text, decisions), "boundaries": boundaries}

    def stream(
        self, *, protection: Literal["none", "watermark"] = "none"
    ) -> IncrementalSentenceBreaker:
        """Return an incremental breaker sharing this override's decision core.

        Collation-variant word- and sentence-level exception rules are refused:
        primary-ignorable code points make their surface-match extent unbounded,
        so no bounded incremental hold can decide them safely. Use those rules
        with whole-text methods such as :meth:`decide`, or use exact variants.

        In text without whitespace or punctuation/symbol edges whose
        ``Word_Break`` value is ``Other``, a decision may wait for whitespace,
        :meth:`IncrementalSentenceBreaker.flush`, or
        :meth:`IncrementalSentenceBreaker.close`.
        """
        if protection not in {"none", "watermark"}:
            raise ValueError("protection must be 'none' or 'watermark'")
        if any(
            rule.variant == "collation" and ({"word", "sentence"} & set(rule.levels))
            for inventory in self.inventories
            for rule in inventory._rules
        ):
            raise ValueError(
                "stream() cannot decide collation-variant word- or sentence-level "
                "exception rules incrementally with a bounded hold; use them with "
                "the whole-text API, or use exact variants"
            )
        return IncrementalSentenceBreaker(self, protection)


def _decision_spans(text: str, decisions: Sequence[BreakDecision]) -> list[BreakSpan]:
    """Build spans from the ICU candidate offsets already consumed by the stream."""
    if not decisions:
        return []
    result: list[BreakSpan] = []
    utf8_start = 0
    utf16_start = 0

    def append(start: int, end: int) -> None:
        nonlocal utf8_start, utf16_start
        segment = text[start:end]
        utf8_end = utf8_start + len(segment.encode("utf-8"))
        utf16_end = utf16_start + sum(2 if ord(char) > 0xFFFF else 1 for char in segment)
        span = cast(
            BreakSpan,
            {
                "text": segment,
                "start": start,
                "end": end,
                "codepoint_start": start,
                "codepoint_end": end,
                "utf8_start": utf8_start,
                "utf8_end": utf8_end,
                "utf16_start": utf16_start,
                "utf16_end": utf16_end,
                "types": [],
                "statuses": [],
            },
        )
        result.append(span)
        utf8_start = utf8_end
        utf16_start = utf16_end

    start = 0
    for decision in decisions:
        if decision["decision"] == "break":
            append(start, decision["offset"])
            start = decision["offset"]
    if start < len(text):
        append(start, len(text))
    return result
