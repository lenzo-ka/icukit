"""Load witness-checked locale material supplied by an application at runtime."""

from __future__ import annotations

import hmac
import json
import math
import os
import re
import secrets
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from types import MappingProxyType
from typing import NamedTuple, cast

import icu

__all__ = [
    "LABEL_KEYS",
    "LocaleMaterial",
    "MaterialLoadError",
    "MaterialRefusal",
    "REQUIRED_WITNESS_KEYS",
    "VALUE_KEYS",
    "WITNESS_KEYS",
    "load_locale_material",
]

WITNESS_KEYS = frozenset({"id", "text", "text_sha256", "locale", "labels", "x-icukit"})
REQUIRED_WITNESS_KEYS = frozenset({"id", "text", "locale"})
LABEL_KEYS = frozenset({"start", "end", "text", "class", "scheme"})
VALUE_KEYS = frozenset({"start", "end", "text", "type", "value"})

_TOP_KEYS = frozenset({"schema_version", "kind", "locale", "rules", "provenance", "witnesses"})
_PROVENANCE_KEYS = frozenset({"source", "license", "retrieved", "note"})
_NEAR_MISS_KEYS = frozenset({"id", "text", "locale", "type"})
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_LOCALE_RE = re.compile(
    r"(?!und)[a-z]{2,3}(?:_[A-Z][a-z]{3})?"
    r"(?:_(?:[A-Z]{2}|[0-9]{3})?(?:_[A-Z0-9]{4,8})+|_(?:[A-Z]{2}|[0-9]{3}))?"
)
_INTEGER_RE = re.compile(r"-?(?:0|[1-9][0-9]*)")
_SEAL_KEY = secrets.token_bytes(32)


class MaterialRefusal(NamedTuple):
    """One reason a locale material file was refused."""

    code: str
    detail: str


class MaterialLoadError(ValueError):
    """Every refusal found while transactionally loading locale material."""

    def __init__(self, refusals: list[MaterialRefusal] | tuple[MaterialRefusal, ...]) -> None:
        self.refusals = tuple(refusals)
        super().__init__("; ".join(f"{item.code}: {item.detail}" for item in self.refusals))


@dataclass(frozen=True)
class LocaleMaterial:
    """Immutable, validated locale material identified by its content digest."""

    kind: str
    locale: str
    digest: str
    rules: str
    rulesets: tuple[str, ...]
    provenance: Mapping[str, str] = field(hash=False)
    _seal: str | None = field(default=None, init=False, repr=False, compare=False, hash=False)

    def __deepcopy__(self, memo: dict[int, object]) -> LocaleMaterial:
        """Copy immutable material while preserving its loader seal."""
        copied = type(self)(
            self.kind,
            self.locale,
            self.digest,
            self.rules,
            self.rulesets,
            MappingProxyType(deepcopy(dict(self.provenance), memo)),
        )
        object.__setattr__(copied, "_seal", self._seal)
        memo[id(self)] = copied
        return copied


def _material_seal(material: LocaleMaterial) -> str:
    provenance = json.dumps(
        dict(material.provenance),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    encoded = json.dumps(
        (
            material.kind,
            material.locale,
            material.digest,
            material.rules,
            material.rulesets,
            provenance,
        ),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.digest(_SEAL_KEY, encoded, "sha256").hex()


def _require_loaded(material: object) -> LocaleMaterial:
    """Require a LocaleMaterial the loader returned (or a copy of one), unchanged.

    Material constructed directly, altered with ``dataclasses.replace``, of a subclass
    (which could answer the seal check with one value and later reads with another), or
    with fields overwritten is refused. icukit does not defend against callers that
    call its private functions.
    """
    if type(material) is not LocaleMaterial:
        raise TypeError(f"material must be a LocaleMaterial, got {type(material).__name__}")
    try:
        valid = material._seal is not None and hmac.compare_digest(
            material._seal, _material_seal(material)
        )
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError("locale material must come from load_locale_material and remain unchanged")
    return material


def locale_descends_from(locale: str, ancestor: str) -> bool:
    """Whether a canonical base locale equals or descends from another."""
    return locale == ancestor or locale.startswith(ancestor + "_")


def _refuse(code: str, detail: str) -> MaterialRefusal:
    return MaterialRefusal(code, detail)


class _InvalidJSON(ValueError):
    pass


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidJSON(f"duplicate key {key!r}")
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise _InvalidJSON(f"non-finite number {value}")


_MAX_DEPTH = 64


def _plain_json(value: object, _open: tuple[int, ...] = ()) -> object:
    if isinstance(value, (Mapping, list, tuple)):
        if id(value) in _open:
            raise _InvalidJSON("the mapping contains itself")
        if len(_open) >= _MAX_DEPTH:
            raise _InvalidJSON(f"nesting deeper than {_MAX_DEPTH} levels")
        _open = (*_open, id(value))
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise _InvalidJSON(f"object key must be a string, got {key!r}")
            result[key] = _plain_json(item, _open)
        return result
    if isinstance(value, (list, tuple)):
        return [_plain_json(item, _open) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise _InvalidJSON("non-finite number")
    return value


def _valid_locale(value: object) -> bool:
    return _locale_reason(value) is None


def _locale_reason(value: object) -> str | None:
    if not isinstance(value, str):
        return f"must be a string, got {type(value).__name__}"
    if not value:
        return "must not be empty"
    if not _LOCALE_RE.fullmatch(value):
        return f"{value!r} does not match the locale shape"
    if value in {"und", "root"}:
        return f"{value!r} is a root locale"
    locale = icu.Locale(value)
    if locale.getName() != value:
        return f"{value!r} is not canonical; ICU canonicalizes it to {locale.getName()!r}"
    if locale.getBaseName() != value:
        return f"{value!r} contains locale keywords"
    return None


def _record_name(kind: str, raw: object, index: int) -> str:
    if isinstance(raw, Mapping) and isinstance(raw.get("id"), str):
        return f"{kind} {raw['id']!r}"
    return f"{kind} {index}"


def _key_reasons(
    record: Mapping[str, object],
    *,
    allowed: frozenset[str],
    required: frozenset[str],
    prefix: str,
) -> list[str]:
    reasons = [f"{prefix}: missing field {key!r}" for key in sorted(required - set(record))]
    reasons.extend(f"{prefix}: unknown field {key!r}" for key in sorted(set(record) - allowed))
    return reasons


def _extent_reasons(
    record: Mapping[str, object], text: str, *, allowed: frozenset[str], prefix: str
) -> list[str]:
    reasons = _key_reasons(
        record, allowed=allowed, required=frozenset({"start", "end"}), prefix=prefix
    )
    start = record.get("start")
    end = record.get("end")
    if not isinstance(start, int) or isinstance(start, bool):
        reasons.append(f"{prefix}: start must be an integer, got {start!r}")
    if not isinstance(end, int) or isinstance(end, bool):
        reasons.append(f"{prefix}: end must be an integer, got {end!r}")
    if (
        isinstance(start, int)
        and not isinstance(start, bool)
        and isinstance(end, int)
        and not isinstance(end, bool)
    ):
        if start < 0:
            reasons.append(f"{prefix}: start {start} < 0")
        if start >= end:
            reasons.append(f"{prefix}: start {start} is not less than end {end}")
        if end > len(text):
            reasons.append(f"{prefix}: end {end} > len(text) {len(text)}")
        if 0 <= start < end <= len(text) and "text" in record and record["text"] != text[start:end]:
            reasons.append(
                f"{prefix}: text echo {record['text']!r} does not match "
                f"text[{start}:{end}] {text[start:end]!r}"
            )
    return reasons


def _validate_witness_shape(
    raw: object, material_locale: str | None, index: int, ids: set[str]
) -> list[str]:
    name = _record_name("witness", raw, index)
    if not isinstance(raw, Mapping):
        return [f"{name}: record must be an object, got {type(raw).__name__}"]
    reasons = _key_reasons(raw, allowed=WITNESS_KEYS, required=REQUIRED_WITNESS_KEYS, prefix=name)
    record_id = raw.get("id")
    if not isinstance(record_id, str):
        reasons.append(f"{name}: id must be a string, got {record_id!r}")
    elif not _ID_RE.fullmatch(record_id):
        reasons.append(f"{name}: id {record_id!r} does not match the required pattern")
    elif record_id in ids:
        reasons.append(f"{name}: id {record_id!r} is not unique")
    else:
        ids.add(record_id)

    text = raw.get("text")
    if not isinstance(text, str):
        reasons.append(f"{name}: text must be a string, got {text!r}")
    locale = raw.get("locale")
    locale_reason = _locale_reason(locale)
    if locale_reason is not None:
        reasons.append(f"{name}: locale {locale_reason}")
    elif material_locale is not None and not locale_descends_from(
        cast(str, locale), material_locale
    ):
        reasons.append(f"{name}: locale {locale!r} does not descend from {material_locale!r}")

    if "text_sha256" in raw:
        text_hash = raw["text_sha256"]
        if not isinstance(text_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", text_hash):
            reasons.append(f"{name}: text_sha256 must be 64 lowercase hexadecimal digits")
        elif isinstance(text, str) and text_hash != sha256(text.encode("utf-8")).hexdigest():
            reasons.append(f"{name}: text_sha256 does not match")

    labels = raw.get("labels", [])
    extension = raw.get("x-icukit", {"values": []})
    if not isinstance(labels, list):
        reasons.append(f"{name}: labels must be a list, got {type(labels).__name__}")
        labels = []
    if not isinstance(extension, Mapping):
        reasons.append(f"{name}: x-icukit must be an object, got {type(extension).__name__}")
        values: list[object] = []
    else:
        reasons.extend(
            _key_reasons(
                extension,
                allowed=frozenset({"values"}),
                required=frozenset({"values"}),
                prefix=f"{name} x-icukit",
            )
        )
        raw_values = extension.get("values")
        if not isinstance(raw_values, list):
            reasons.append(
                f"{name} x-icukit: values must be a list, got {type(raw_values).__name__}"
            )
            values = []
        else:
            values = raw_values
    if not labels and not values:
        reasons.append(f"{name}: has no labels or values and witnesses nothing")

    valid_labels: list[Mapping[str, object]] = []
    if isinstance(text, str):
        for label_index, label in enumerate(labels):
            prefix = f"{name} label {label_index}"
            if not isinstance(label, Mapping):
                reasons.append(f"{prefix}: must be an object, got {type(label).__name__}")
                continue
            reasons.extend(_extent_reasons(label, text, allowed=LABEL_KEYS, prefix=prefix))
            if "class" not in label:
                reasons.append(f"{prefix}: missing field 'class'")
            elif not isinstance(label["class"], str) or not label["class"]:
                reasons.append(f"{prefix}: class must be a non-empty string")
            if "scheme" in label and label["scheme"] != "icukit-type":
                reasons.append(f"{prefix}: scheme must be 'icukit-type'")
            valid_labels.append(label)

        for value_index, value in enumerate(values):
            prefix = f"{name} value {value_index}"
            if not isinstance(value, Mapping):
                reasons.append(f"{prefix}: must be an object, got {type(value).__name__}")
                continue
            reasons.extend(_extent_reasons(value, text, allowed=VALUE_KEYS, prefix=prefix))
            if "type" not in value:
                reasons.append(f"{prefix}: missing field 'type'")
            elif not isinstance(value["type"], str) or not value["type"]:
                reasons.append(f"{prefix}: type must be a non-empty string")
            if "value" not in value:
                reasons.append(f"{prefix}: missing field 'value'")
            elif not isinstance(value["value"], Mapping):
                reasons.append(f"{prefix}: value must be an object")
            if not any(
                label.get("start") == value.get("start")
                and label.get("end") == value.get("end")
                and label.get("class") == value.get("type")
                for label in valid_labels
            ):
                reasons.append(
                    f"{prefix}: extent and type do not match any label's extent and class"
                )
    return reasons


def _validate_near_miss_shape(
    raw: object, material_locale: str | None, index: int, ids: set[str]
) -> list[str]:
    name = _record_name("near miss", raw, index)
    if not isinstance(raw, Mapping):
        return [f"{name}: record must be an object, got {type(raw).__name__}"]
    reasons = _key_reasons(raw, allowed=_NEAR_MISS_KEYS, required=_NEAR_MISS_KEYS, prefix=name)
    record_id = raw.get("id")
    if not isinstance(record_id, str):
        reasons.append(f"{name}: id must be a string, got {record_id!r}")
    elif not _ID_RE.fullmatch(record_id):
        reasons.append(f"{name}: id {record_id!r} does not match the required pattern")
    elif record_id in ids:
        reasons.append(f"{name}: id {record_id!r} is not unique")
    else:
        ids.add(record_id)
    text = raw.get("text")
    if not isinstance(text, str):
        reasons.append(f"{name}: text must be a string, got {text!r}")
    item_type = raw.get("type")
    if not isinstance(item_type, str) or not item_type:
        reasons.append(f"{name}: type must be a non-empty string")
    locale = raw.get("locale")
    locale_reason = _locale_reason(locale)
    if locale_reason is not None:
        reasons.append(f"{name}: locale {locale_reason}")
    elif material_locale is not None and not locale_descends_from(
        cast(str, locale), material_locale
    ):
        reasons.append(f"{name}: locale {locale!r} does not descend from {material_locale!r}")
    return reasons


def _envelope(data: Mapping[str, object]) -> list[MaterialRefusal]:
    errors: list[MaterialRefusal] = []
    keys = set(data)
    for key in sorted(_TOP_KEYS - keys):
        errors.append(_refuse("INVALID_KEY", f"missing top-level key {key!r}"))
    for key in sorted(keys - (_TOP_KEYS | {"near_misses"})):
        errors.append(_refuse("INVALID_KEY", f"unknown top-level key {key!r}"))
    version = data.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version != 1:
        errors.append(
            _refuse(
                "INVALID_SCHEMA_VERSION",
                f"top-level field 'schema_version' must be integer 1, got {version!r}",
            )
        )
    kind = data.get("kind")
    if not isinstance(kind, str) or kind not in _KIND_LOADERS:
        errors.append(
            _refuse(
                "INVALID_KIND",
                f"top-level field 'kind' names unregistered kind {kind!r}",
            )
        )
    locale = data.get("locale")
    locale_reason = _locale_reason(locale)
    if locale_reason is not None:
        errors.append(_refuse("INVALID_LOCALE", f"top-level field 'locale' {locale_reason}"))
    rules = data.get("rules")
    if not isinstance(rules, list):
        errors.append(
            _refuse(
                "INVALID_RULES",
                f"top-level field 'rules' must be a list, got {type(rules).__name__}",
            )
        )
    elif not rules:
        errors.append(_refuse("INVALID_RULES", "top-level field 'rules' must not be empty"))
    else:
        for index, line in enumerate(rules):
            if not isinstance(line, str):
                errors.append(
                    _refuse(
                        "INVALID_RULES",
                        f"top-level field 'rules' line {index} must be a string, got {line!r}",
                    )
                )
    provenance = data.get("provenance")
    if not isinstance(provenance, Mapping):
        errors.append(
            _refuse(
                "INVALID_PROVENANCE",
                f"top-level field 'provenance' must be an object, got {type(provenance).__name__}",
            )
        )
    else:
        for reason in _key_reasons(
            provenance,
            allowed=_PROVENANCE_KEYS,
            required=frozenset({"source"}),
            prefix="top-level field 'provenance'",
        ):
            errors.append(_refuse("INVALID_PROVENANCE", reason))
        for key, value in provenance.items():
            if not isinstance(value, str) or (key == "source" and not value):
                errors.append(
                    _refuse(
                        "INVALID_PROVENANCE",
                        f"top-level field 'provenance.{key}' must be "
                        f"{'a non-empty string' if key == 'source' else 'a string'}, got {value!r}",
                    )
                )
    witnesses = data.get("witnesses")
    if not isinstance(witnesses, list):
        errors.append(
            _refuse(
                "INVALID_WITNESS",
                f"top-level field 'witnesses' must be a list, got {type(witnesses).__name__}",
            )
        )
        witnesses = []
    ids: set[str] = set()
    material_locale = locale if _valid_locale(locale) else None
    for index, witness in enumerate(witnesses):
        for reason in _validate_witness_shape(witness, material_locale, index, ids):
            errors.append(_refuse("INVALID_WITNESS", reason))
    near_misses = data.get("near_misses", [])
    if not isinstance(near_misses, list):
        errors.append(
            _refuse(
                "INVALID_NEAR_MISS",
                f"top-level field 'near_misses' must be a list, got {type(near_misses).__name__}",
            )
        )
        near_misses = []
    for index, near_miss in enumerate(near_misses):
        for reason in _validate_near_miss_shape(near_miss, material_locale, index, ids):
            errors.append(_refuse("INVALID_NEAR_MISS", reason))
    if isinstance(witnesses, list) and not witnesses:
        errors.append(_refuse("NO_WITNESS", "at least one witness is required"))
    return errors


def _type_for_ruleset(ruleset: str, cardinal: str) -> str:
    if ruleset == cardinal:
        return "number:spellout"
    return "number:spellout:" + ruleset.lstrip("%").removeprefix("spellout-")


def _rbnf_spellout(
    data: Mapping[str, object], digest: str
) -> tuple[LocaleMaterial | None, list[MaterialRefusal]]:
    from .recognize import MaterialSpelloutDetector
    from .serialize import _to_json

    errors: list[MaterialRefusal] = []
    locale = cast(str, data["locale"])
    rules = "\n".join(cast(list[str], data["rules"]))
    try:
        formatter = icu.RuleBasedNumberFormat(rules, icu.Locale(locale))
    except icu.ICUError as error:
        return None, [_refuse("RBNF_SYNTAX", f"rule text: ICU refused it: {error}")]
    names = tuple(
        formatter.getRuleSetName(index) for index in range(formatter.getNumberOfRuleSetNames())
    )
    cardinal = next(
        (
            name
            for name in names
            if "spellout" in name.casefold()
            and "cardinal" in name.casefold()
            and not any(excluded in name.casefold() for excluded in ("ordinal", "year", "verbose"))
        ),
        None,
    )
    if cardinal is None:
        return None, [_refuse("NO_CARDINAL_RULESET", "no public cardinal spell-out rule set")]
    try:
        surfaces = {formatter.format(value, cardinal).casefold() for value in range(1001)}
    except icu.ICUError as error:
        return None, [
            _refuse("RBNF_SYNTAX", f"rule set {cardinal!r}: ICU formatting failed: {error}")
        ]
    if len(surfaces) != 1001:
        errors.append(
            _refuse(
                "NOT_INJECTIVE",
                f"rule set {cardinal!r}: outputs for 0 through 1000 are not distinct",
            )
        )

    admitted = tuple(
        name
        for name in names
        if any(kind in name.casefold() for kind in ("cardinal", "ordinal", "year"))
    )
    witnesses = cast(list[Mapping[str, object]], data["witnesses"])
    near_misses = cast(list[Mapping[str, object]], data.get("near_misses", []))
    referenced_types = {
        cast(str, label["class"])
        for witness in witnesses
        for label in cast(list[Mapping[str, object]], witness.get("labels", []))
    } | {
        cast(str, value["type"])
        for witness in witnesses
        for value in cast(
            list[Mapping[str, object]],
            cast(Mapping[str, object], witness.get("x-icukit", {"values": []}))["values"],
        )
    }
    selected = (cardinal,) + tuple(
        name
        for name in admitted
        if name != cardinal and _type_for_ruleset(name, cardinal) in referenced_types
    )
    selected_by_type: dict[str, list[str]] = {}
    for name in selected:
        selected_by_type.setdefault(_type_for_ruleset(name, cardinal), []).append(name)
    for reader_type, rule_sets in selected_by_type.items():
        if len(rule_sets) > 1:
            errors.append(
                _refuse(
                    "AMBIGUOUS_RULESET",
                    f"reader type {reader_type!r} is produced by public rule sets "
                    + ", ".join(repr(name) for name in rule_sets),
                )
            )
    if any(error.code == "AMBIGUOUS_RULESET" for error in errors):
        return None, errors
    types = {_type_for_ruleset(name, cardinal): name for name in selected}
    provisional = LocaleMaterial(
        "rbnf-spellout",
        locale,
        digest,
        rules,
        selected,
        MappingProxyType(dict(cast(Mapping[str, str], data["provenance"]))),
    )
    object.__setattr__(provisional, "_seal", _material_seal(provisional))

    formatters: dict[str, icu.RuleBasedNumberFormat] = {locale: formatter}
    readers_by_locale: dict[str, dict[str, MaterialSpelloutDetector]] = {}
    failed_locales: set[str] = set()

    def tools_for(
        witness_locale: str,
    ) -> tuple[icu.RuleBasedNumberFormat, dict[str, MaterialSpelloutDetector]] | None:
        if witness_locale in failed_locales:
            return None
        if witness_locale in readers_by_locale:
            return formatters[witness_locale], readers_by_locale[witness_locale]
        try:
            locale_formatter = formatters.get(witness_locale)
            if locale_formatter is None:
                locale_formatter = icu.RuleBasedNumberFormat(rules, icu.Locale(witness_locale))
                formatters[witness_locale] = locale_formatter
        except icu.ICUError as error:
            errors.append(
                _refuse(
                    "RBNF_SYNTAX",
                    f"locale {witness_locale!r}: ICU refused the rule text: {error}",
                )
            )
            failed_locales.add(witness_locale)
            return None
        locale_readers = {}
        for name in selected:
            try:
                locale_readers[_type_for_ruleset(name, cardinal)] = MaterialSpelloutDetector(
                    witness_locale, provisional, ruleset=None if name == cardinal else name
                )
            except (icu.ICUError, ValueError) as error:
                errors.append(
                    _refuse(
                        "RBNF_SYNTAX",
                        f"rule set {name!r}"
                        + (f" for locale {witness_locale!r}" if witness_locale != locale else "")
                        + f": material reader construction failed: {error}",
                    )
                )
        if len(locale_readers) != len(selected):
            failed_locales.add(witness_locale)
            return None
        readers_by_locale[witness_locale] = locale_readers
        return locale_formatter, locale_readers

    if tools_for(locale) is None:
        return None, errors
    cardinal_has_value = False
    for witness_index, witness in enumerate(witnesses):
        witness_name = _record_name("witness", witness, witness_index)
        text = cast(str, witness["text"])
        witness_locale = cast(str, witness["locale"])
        witness_tools = tools_for(witness_locale)
        if witness_tools is None:
            continue
        witness_formatter, readers = witness_tools
        labels = cast(list[Mapping[str, object]], witness.get("labels", []))
        values = cast(
            list[Mapping[str, object]],
            cast(Mapping[str, object], witness.get("x-icukit", {"values": []}))["values"],
        )
        for item_index, item in enumerate(labels):
            item_type = cast(str, item["class"])
            if item_type not in types or item_type not in readers:
                errors.append(
                    _refuse(
                        "INVALID_WITNESS",
                        f"{witness_name} label {item_index}: class {item_type!r} "
                        "does not name a reader supplied by this material",
                    )
                )
        for item_index, item in enumerate(values):
            item_type = cast(str, item["type"])
            if item_type not in types or item_type not in readers:
                errors.append(
                    _refuse(
                        "INVALID_WITNESS",
                        f"{witness_name} value {item_index}: type {item_type!r} "
                        "does not name a reader supplied by this material",
                    )
                )
        for value_index, item in enumerate(values):
            item_type = cast(str, item["type"])
            value = cast(Mapping[str, object], item["value"])
            valid_value = (
                set(value) == {"kind", "decimal", "currency"}
                and value.get("kind") == "number"
                and isinstance(value.get("decimal"), str)
                and bool(_INTEGER_RE.fullmatch(cast(str, value.get("decimal"))))
                and value.get("currency") is None
            )
            if not valid_value:
                errors.append(
                    _refuse(
                        "INVALID_WITNESS",
                        f"{witness_name} value {value_index}: field 'value' must be "
                        "{'kind': 'number', 'decimal': '<integer string>', "
                        "'currency': None}",
                    )
                )
                continue
            if item_type == "number:spellout":
                cardinal_has_value = True
            if item_type not in readers:
                continue
            expected = text[cast(int, item["start"]) : cast(int, item["end"])]
            try:
                rendered = witness_formatter.format(
                    int(cast(str, value["decimal"])), types[item_type]
                )
            except (icu.ICUError, ValueError) as error:
                errors.append(
                    _refuse(
                        "WITNESS_FORMAT_FAILED",
                        f"{witness_name} value {value_index}: value {value!r} with rule set "
                        f"{types[item_type]!r}; ICU produced no output ({error}); witness "
                        f"slice is {expected!r}",
                    )
                )
            else:
                if rendered.casefold() != expected.casefold():
                    errors.append(
                        _refuse(
                            "WITNESS_FORMAT_FAILED",
                            f"{witness_name} value {value_index}: value {value!r} with rule set "
                            f"{types[item_type]!r} formats as {rendered!r}, witness slice is "
                            f"{expected!r}",
                        )
                    )
        detections_by_type = {}
        read_failures = {}
        for reader_type, reader in readers.items():
            try:
                detections_by_type[reader_type] = reader.detect(text)
            except (icu.ICUError, ValueError) as error:
                detections_by_type[reader_type] = []
                read_failures[reader_type] = str(error)
        for item_index, item in enumerate((*labels, *values)):
            item_type = cast(str, item.get("class", item.get("type")))
            if item_type not in readers:
                continue
            matches = [
                detection
                for detection in detections_by_type[item_type]
                if detection["start"] == item["start"]
                and detection["end"] == item["end"]
                and detection["type"] == item_type
            ]
            if "value" in item:
                matches = [
                    detection
                    for detection in matches
                    if _to_json(detection["value"]) == item["value"]
                ]
            if not matches:
                expected_value = item.get("value", "<any>")
                actual = [
                    {
                        "extent": (detection["start"], detection["end"]),
                        "type": detection["type"],
                        "value": _to_json(detection["value"]),
                    }
                    for detection in detections_by_type[item_type]
                ]
                if item_type in read_failures:
                    read_result = f"reader failed: {read_failures[item_type]}"
                else:
                    read_result = repr(actual) if actual else "nothing"
                errors.append(
                    _refuse(
                        "WITNESS_READ_FAILED",
                        f"{witness_name} item {item_index}: expected extent "
                        f"({item['start']}, {item['end']}), type {item_type!r}, value "
                        f"{expected_value!r}; reader read {read_result} in that text",
                    )
                )
    if not cardinal_has_value:
        errors.append(
            _refuse("NO_WITNESS", f"rule set {cardinal!r}: has no cardinal value witness")
        )
    for index, near_miss in enumerate(near_misses):
        near_miss_name = _record_name("near miss", near_miss, index)
        item_type = cast(str, near_miss["type"])
        near_miss_locale = cast(str, near_miss["locale"])
        near_miss_tools = tools_for(near_miss_locale)
        if near_miss_tools is None:
            continue
        _, readers = near_miss_tools
        if item_type not in readers:
            errors.append(
                _refuse(
                    "INVALID_NEAR_MISS",
                    f"{near_miss_name}: type {item_type!r} does not name a reader "
                    "supplied by this material",
                )
            )
            continue
        text = cast(str, near_miss["text"])
        try:
            detections = readers[item_type].detect(text)
        except (icu.ICUError, ValueError) as error:
            errors.append(
                _refuse(
                    "NEAR_MISS_READ",
                    f"{near_miss_name}: reader type {item_type!r} failed: {error}",
                )
            )
            continue
        if any(
            detection["start"] == 0 and detection["end"] == len(text) for detection in detections
        ):
            errors.append(
                _refuse(
                    "NEAR_MISS_READ",
                    f"{near_miss_name}: reader type {item_type!r} read the whole text",
                )
            )
    return (None if errors else provisional), errors


_KIND_LOADERS = {"rbnf-spellout": _rbnf_spellout}


def load_locale_material(
    material: Mapping[str, object] | str | os.PathLike[str], /
) -> LocaleMaterial:
    """Parse, validate, witness-check, and atomically return locale material."""
    try:
        if isinstance(material, (str, os.PathLike)):
            with open(material, encoding="utf-8") as stream:
                parsed = json.load(stream, object_pairs_hook=_object, parse_constant=_constant)
        elif isinstance(material, Mapping):
            parsed = _plain_json(material)
        else:
            parsed = material
        if not isinstance(parsed, Mapping):
            raise _InvalidJSON("top level is not an object")
        canonical = json.dumps(
            parsed,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        _InvalidJSON,
        TypeError,
        ValueError,
        RecursionError,
    ) as error:
        raise MaterialLoadError([_refuse("INVALID_JSON", str(error))]) from error
    data = cast(Mapping[str, object], parsed)
    errors = _envelope(data)
    if errors:
        raise MaterialLoadError(errors)
    digest = "sha256:" + sha256(canonical).hexdigest()
    loaded, errors = _KIND_LOADERS[cast(str, data["kind"])](data, digest)
    if errors:
        raise MaterialLoadError(errors)
    if loaded is None:
        raise MaterialLoadError(
            [_refuse("RBNF_SYNTAX", "rule material produced no validated reader")]
        )
    return loaded
