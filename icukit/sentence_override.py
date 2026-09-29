"""Experimental whole-text and incremental sentence-break overrides.

ICU always supplies the candidate boundaries: this module can retain or
suppress them, but never add one. ``base="none"`` is the default and is exactly
ICU's current sentence output. Whole-text and incremental operation share the
same prefix-aware candidate evaluator.

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
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Literal, NotRequired, TypedDict, cast

import icu

from .breaker import BreakSpan, break_sentence_spans, break_word_spans
from .classes import ClassPoint, char_classes, class_window
from .errors import BreakRuleLoadError, LateProtectedSpan, OverlappingProtectedSpans, RuleRefusal
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
    "CartletModelRef",
    "IncrementalSentenceBreaker",
    "PendingCandidate",
    "SentenceOverride",
    "break_rule_identity",
    "load_break_rules",
]

Effect = Literal["break", "no-break", "ambiguous"]
Layer = Literal["icu", "token", "before", "exceptions", "rules", "model", "after"]
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
    "token_profile": "sha256:14989ce05e894b86c0502fb563c1d0e89399c2bd39dd835bba7cfa2422e7c451",
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
    """A digest- and runtime-bound reference to an experimental cartlet model.

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
    expected_identity = break_rule_identity(locale, inventories=inventories)
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
    # Keep this import lazy so the unchanged base="none" path does not pay the
    # cartlet import cost. Packaging enforces the hard cartlet>=0.7 dependency.
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

    @staticmethod
    def _key(toks: Sequence[Token], index: int, text: str) -> tuple[object, ...]:
        token = toks[index]
        run = token["run"]
        run_tokens = [item for item in toks if item["run"] == run]
        run_start = min(item["start"] for item in run_tokens)
        run_end = max(item["end"] for item in run_tokens)
        return (
            token["start"],
            token["end"],
            token["text"],
            run,
            text[run_start:run_end],
            token.get("protected_types", ()),
        )

    def get(self, toks: Sequence[Token], index: int, text: str) -> dict[str, str | int | bool]:
        if not self.enabled:
            return token_features(toks, index, text)
        key = self._key(toks, index, text)
        if key not in self.values:
            self.values[key] = token_features(toks, index, text)
        return self.values[key]

    def evict_before(self, offset: int) -> None:
        self.values = {
            key: value for key, value in self.values.items() if cast(int, key[1]) >= offset
        }

    def clear(self) -> None:
        self.values.clear()


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
    pivot = _token_index_after(toks, offset)
    if at == "run-1":
        if pivot == 0:
            return _sentinel_features("<BOS>").get(predicate.feature, "<BOS>"), 0, offset
        previous = toks[pivot - 1]
        same_run = [
            item for item in toks if item["run"] == previous["run"] and item["end"] <= offset
        ]
        completion_horizons = tuple(
            _token_completion_horizon(item, text, locale, inventories, closed) for item in same_run
        )
        if any(item is None for item in completion_horizons):
            raise _FeatureNotYet
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
        return (
            features.get(predicate.feature, "<UNKNOWN>"),
            0,
            max((offset, *(cast(int, item) for item in completion_horizons))),
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
            cache.get(toks, index, text).get(predicate.feature, "<UNKNOWN>"),
            max(at, 0),
            max(offset, completion_horizon),
        )
    distance = int(cast(str, at)[1:])
    index = offset + distance - 1 if distance > 0 else offset + distance
    if distance > 0:
        right = toks[pivot:]
        horizon = _forward_character_horizon(index, text, right)
        if index >= len(text) and not closed:
            raise _FeatureNotYet
        completed_tokens = tuple(token for token in right if token["end"] <= index)
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
    containing = next((token for token in toks if token["start"] <= index < token["end"]), None)
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
        tokens_read = min(
            sum(1 for token in toks[pivot:] if token["start"] <= index), rule.lookahead
        )
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


def _combined_inventory(
    inventories: Sequence[LoadedExceptionInventory],
) -> LoadedExceptionInventory | None:
    if not inventories:
        return None
    return LoadedExceptionInventory(
        " + ".join(item.corpus for item in inventories),
        {key: value for item in inventories for key, value in item.named_lists.items()},
        tuple(rule for item in inventories for rule in item._rules),
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


def _inventory_anchor(toks: Sequence[Token], offset: int, lookahead: int) -> int:
    """End of the furthest word a candidate's flat rules may inspect."""
    if lookahead <= 0:
        return offset
    pivot = _token_index_after(toks, offset)
    read = toks[pivot : pivot + lookahead]
    return read[-1]["end"] if read else offset


def _candidate_observed(
    owner: SentenceOverride,
    text: str,
    offset: int,
    protected: Sequence[ProtectedSpan],
    closed: bool,
    cache: _TokenFeatureCache,
) -> _ObservedResult:
    combined = _combined_inventory(owner.inventories)
    toks = tokens(text, owner.locale, inventory=combined, protected=protected)
    covering = tuple(
        sorted({item["type"] for item in protected if item["start"] < offset < item["end"]})
    )
    containing = next((token for token in toks if token["start"] < offset < token["end"]), None)
    end = containing["end"] if containing is not None else _logical_end(toks, offset)
    word_inventories = tuple(
        inventory
        for inventory in owner.inventories
        if _inventory_rules(inventory, owner.locale, frozenset({"word"}))
    )
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
        covering,
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

    anchor = _inventory_anchor(toks, offset, owner.lookahead)
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
        rule_ids = _inventory_claims(inventory, text, owner.locale).get(offset)
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
            covering,
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
            covering,
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
        covering,
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


def _decide_core(
    text: str,
    locale: str,
    inventories: Sequence[LoadedExceptionInventory],
    before: Sequence[BreakRuleSet],
    base: BreakRuleSet | _LoadedCartletModel | None,
    after: Sequence[BreakRuleSet],
    protected: Iterable[ProtectedSpan],
) -> list[BreakDecision]:
    protected_items = tuple(protected)
    owner = SentenceOverride.__new__(SentenceOverride)
    owner.locale = locale
    owner.inventories = tuple(inventories)
    owner.before = tuple(before)
    owner.base = base
    owner.after = tuple(after)
    rule_layers = (
        *owner.before,
        *((base,) if isinstance(base, BreakRuleSet) else ()),
        *owner.after,
    )
    owner.lookahead = max(
        (*(item.lookahead for item in rule_layers), base.lookahead if base is not None else 0)
    )
    cache = _TokenFeatureCache(True)
    result: list[BreakDecision] = []
    for span in break_sentence_spans(text, locale):
        observed = _candidate_observed(owner, text, span["end"], protected_items, True, cache)
        if observed.decision is None:
            raise AssertionError("closed candidate remained pending")
        result.append(observed.decision)
    return result


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
        self._segment_start = 0
        self._protected: list[ProtectedSpan] = []
        self._emitted: set[int] = set()
        self._emitted_candidates: list[int] = []
        self._read_horizon = 0
        self._watermark = 0
        self._pending: list[PendingCandidate] = []
        self._closed = False
        self._cache = _TokenFeatureCache(owner.cache)
        self.lookahead = owner.lookahead

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
            elif span["start"] < self._read_horizon or any(
                span["start"] < offset < span["end"] for offset in self._emitted_candidates
            ):
                raise LateProtectedSpan(
                    f"protected span [{span['start']}, {span['end']}) arrived after emitted context"
                )
        return items

    def _evaluate(self, *, closed: bool) -> list[BreakDecision]:
        emitted: list[BreakDecision] = []
        pending: list[PendingCandidate] = []
        earlier_pending = False
        segment_start = self._segment_start
        text = self._text[segment_start:]
        protected = [
            cast(
                ProtectedSpan,
                {
                    **item,
                    "start": item["start"] - segment_start,
                    "end": item["end"] - segment_start,
                },
            )
            for item in self._protected
            if item["start"] >= segment_start
        ]
        combined = _combined_inventory(self._owner.inventories)
        toks = tokens(
            text,
            self._owner.locale,
            inventory=combined,
            protected=protected,
        )
        for span in break_sentence_spans(text, self._owner.locale):
            local_offset = span["end"]
            offset = segment_start + local_offset
            if offset in self._emitted:
                continue
            tokens_after = sum(1 for token in toks if token["start"] >= local_offset)
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
            observed = _candidate_observed(
                self._owner,
                text,
                local_offset,
                protected,
                closed,
                self._cache,
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
            horizon = segment_start + observed.horizon
            if self._protection == "watermark" and horizon > self._watermark and not closed:
                pending.append(
                    {"offset": offset, "tokens_after": tokens_after, "waiting_on": "protection"}
                )
                earlier_pending = True
                continue
            self._emitted.add(offset)
            self._emitted_candidates.append(offset)
            self._read_horizon = max(self._read_horizon, horizon)
            decision = dict(observed.decision)
            decision["offset"] += segment_start
            decision["end"] += segment_start
            emitted.append(cast(BreakDecision, decision))
        self._pending = pending
        reachable_starts: list[int] = []
        if toks:
            reachable_starts.append(toks[max(0, len(toks) - 3)]["start"])
            current_run = toks[-1]["run"]
            reachable_starts.extend(token["start"] for token in toks if token["run"] == current_run)
        if pending:
            for item in pending:
                pivot = _token_index_after(toks, item["offset"] - segment_start)
                if toks:
                    reachable_starts.append(toks[max(0, pivot - 3)]["start"])
                if pivot:
                    previous_run = toks[pivot - 1]["run"]
                    reachable_starts.extend(
                        token["start"] for token in toks if token["run"] == previous_run
                    )
        self._cache.evict_before(min(reachable_starts, default=len(text)))
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
        prospective_text = self._text + chunk
        prospective_protected = self._prospective_protected(protected, len(prospective_text))
        if protected_through is not None:
            if self._protection != "watermark":
                raise ValueError("protected_through requires protection='watermark'")
            if (
                not isinstance(protected_through, int)
                or isinstance(protected_through, bool)
                or not self._watermark <= protected_through <= len(prospective_text)
            ):
                raise ValueError("protected_through must advance within buffered text")
        self._text = prospective_text
        self._protected = prospective_protected
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
            self._watermark = len(self._text)
        result = self._evaluate(closed=True)
        self._pending = []
        self._segment_start = len(self._text)
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


class SentenceOverride:
    """Apply opt-in rules or a cartlet model to ICU sentence candidates.

    ``en-tn@1`` is a learned, experimental, opt-in English rule base under
    CC BY-SA 4.0. Its reported development and test figures measure agreement
    with the Google TN corpus splitter on synthetic ``glue2`` concatenations,
    not accuracy on naturally occurring running text. The unchanged default is
    always ``base="none"``.

    ``en-tn-cart@1`` is the experimental cartlet counterpart. It is also
    opt-in. Cartlet is an icukit dependency, imported lazily when this path is
    selected.

    Args:
        locale: ICU locale used for both sentence and word boundaries.
        base: ``"none"`` (the unchanged ICU default), the opt-in learned base
            ``"en-tn@1"``, the opt-in ``"en-tn-cart@1"`` model, a loaded
            rule set, a :class:`CartletModelRef`, or a path to a
            ``break-rules`` JSON file. Unknown names are refused.
        before: Ordered caller rules that force a decision before inventories
            and the base.
        after: Ordered caller rules that may override the base decision.
        inventories: Exception inventories; word rules merge tokens and
            sentence rules suppress candidates.
        cache: Reuse immutable per-token features in incremental evaluation.

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
        base: Literal["none"] | str | Path | BreakRuleSet | CartletModelRef = "none",
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
        elif isinstance(base, CartletModelRef):
            loaded_base = _load_cartlet_model(base, locale, self.inventories)
        elif base == "en-tn-cart@1":
            loaded_base = _load_cartlet_model(
                CartletModelRef(
                    _EN_TN_CART_PATH,
                    _EN_TN_CART_DIGEST,
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
                "base must be 'none', a named base, a BreakRuleSet, a CartletModelRef, "
                "or a break-rules JSON path"
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
