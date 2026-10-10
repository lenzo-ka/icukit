"""Load bounded behavior options owned by icukit.

A behavior schema is either the shared ``behavior-schema`` envelope or a bare
``sections.icukit`` object. The four option groups map directly to public icukit
keyword arguments: sentence breaking, detector selection, detector streaming, and
regular-expression resource limits.
"""

from __future__ import annotations

import inspect
import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import NamedTuple, cast

import icu

from .breaker import Breaker
from .regex import UnicodeRegex

__all__ = [
    "BEHAVIOR_KIND",
    "BEHAVIOR_OPTION_NAMES",
    "BEHAVIOR_SCHEMA_VERSION",
    "BehaviorLoadError",
    "BehaviorRefusal",
    "BehaviorSchema",
    "load_behavior_schema",
]

BEHAVIOR_SCHEMA_VERSION = 1
BEHAVIOR_KIND = "behavior-schema"

_TOP_KEYS = frozenset(
    {"schema_version", "kind", "name", "version", "extends", "provenance", "sections"}
)
_SECTION_KEYS = frozenset({"schema_version", "sentence", "detection", "stream", "regex"})
_SECTIONS = ("frend", "icukit")
_PROVENANCE_KEYS = frozenset({"source", "note"})
_NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
_SENTENCE_BASES = frozenset({"none", "en-tn@1", "en-tn-cart@1", "en-real-cart@1"})

_MAX_BYTES = 65_536
_MAX_DEPTH = 16
_MAX_VALUES = 4_096
_MAX_STRING = 256

_SENTENCE_KEYS = ["base"]
if "max_sentence_chars" in inspect.signature(Breaker).parameters:
    _SENTENCE_KEYS.append("max_sentence_chars")

_REGEX_KEYS = []
_regex_parameters = inspect.signature(UnicodeRegex).parameters
for _key in ("time_limit", "stack_limit"):
    if _key in _regex_parameters:
        _REGEX_KEYS.append(_key)

BEHAVIOR_OPTION_NAMES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "sentence": tuple(_SENTENCE_KEYS),
        "detection": ("currencies", "flexible", "guarded", "locales", "skeletons", "units"),
        "stream": ("boundary", "max_pending_chars"),
        "regex": tuple(_REGEX_KEYS),
    }
)
"""Schema-settable public keyword names, grouped by their receiving API.

The main-branch names are ``sentence.base``; ``detection.currencies``,
``detection.flexible``, ``detection.guarded``, ``detection.locales``,
``detection.skeletons``, and ``detection.units``; and ``stream.boundary`` and
``stream.max_pending_chars``. Regex resource-limit and sentence-length names appear
when their receiving public APIs provide them.
"""


class BehaviorRefusal(NamedTuple):
    """One reason a behavior schema was refused."""

    code: str
    detail: str


class BehaviorLoadError(ValueError):
    """Every refusal found in one transactional behavior-schema phase."""

    def __init__(self, refusals: Sequence[BehaviorRefusal]) -> None:
        self.refusals = tuple(refusals)
        super().__init__("; ".join(f"{item.code}: {item.detail}" for item in self.refusals))


@dataclass(frozen=True)
class BehaviorSchema:
    """One immutable, validated icukit behavior section.

    ``name``, ``version``, ``extends``, and ``provenance`` describe a full envelope;
    they are neutral values for a bare section. ``digest`` always identifies the
    complete loader input: the whole envelope when present, otherwise the bare section.

    Each option-group mapping can be spread into the corresponding public API. For
    example, pass ``detection`` to :func:`icukit.reader_set`, then pass ``stream`` to
    :meth:`icukit.DetectorSet.stream`.
    """

    digest: str
    name: str | None
    version: int | None
    extends: tuple[str, ...]
    provenance: Mapping[str, str]
    section: Mapping[str, object]

    @property
    def sentence(self) -> Mapping[str, object]:
        """Keyword arguments for :class:`icukit.Breaker`."""
        return cast(Mapping[str, object], self.section.get("sentence", _EMPTY))

    @property
    def detection(self) -> Mapping[str, object]:
        """Keyword arguments for :func:`icukit.reader_set`."""
        return cast(Mapping[str, object], self.section.get("detection", _EMPTY))

    @property
    def stream(self) -> Mapping[str, object]:
        """Keyword arguments for :meth:`icukit.DetectorSet.stream`."""
        return cast(Mapping[str, object], self.section.get("stream", _EMPTY))

    @property
    def regex(self) -> Mapping[str, object]:
        """Keyword arguments for :class:`icukit.UnicodeRegex`."""
        return cast(Mapping[str, object], self.section.get("regex", _EMPTY))


_EMPTY: Mapping[str, object] = MappingProxyType({})


class _InvalidJSON(ValueError):
    pass


def _refuse(code: str, detail: str) -> BehaviorRefusal:
    return BehaviorRefusal(code, detail)


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidJSON(f"duplicate object key {key!r}")
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise _InvalidJSON(f"non-finite number {value!r}")


def _float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise _InvalidJSON(f"non-finite number {value!r}")
    return parsed


def _bounded_plain(
    value: object,
    *,
    depth: int = 1,
    budget: list[int] | None = None,
    open_ids: tuple[int, ...] = (),
) -> object:
    if budget is None:
        budget = [_MAX_VALUES]
    if depth > _MAX_DEPTH:
        raise _InvalidJSON(f"JSON depth exceeds {_MAX_DEPTH}")
    budget[0] -= 1
    if budget[0] < 0:
        raise _InvalidJSON(f"JSON contains more than {_MAX_VALUES} values")
    if isinstance(value, str):
        if len(value) > _MAX_STRING:
            raise _InvalidJSON(f"JSON string exceeds {_MAX_STRING} code points")
        return str(value)
    if isinstance(value, Mapping):
        if id(value) in open_ids:
            raise _InvalidJSON("the mapping contains itself")
        nested_ids = (*open_ids, id(value))
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise _InvalidJSON(f"object key must be a string, got {key!r}")
            if len(key) > _MAX_STRING:
                raise _InvalidJSON(f"JSON string exceeds {_MAX_STRING} code points")
            result[str(key)] = _bounded_plain(
                item,
                depth=depth + 1,
                budget=budget,
                open_ids=nested_ids,
            )
        return result
    if isinstance(value, (list, tuple)):
        if id(value) in open_ids:
            raise _InvalidJSON("the sequence contains itself")
        nested_ids = (*open_ids, id(value))
        return [
            _bounded_plain(
                item,
                depth=depth + 1,
                budget=budget,
                open_ids=nested_ids,
            )
            for item in value
        ]
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _InvalidJSON("non-finite number")
        return value
    raise _InvalidJSON(f"value is not a JSON type: {type(value).__name__}")


def _canonical(data: Mapping[str, object]) -> bytes:
    return json.dumps(
        data,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _read(
    source: Mapping[str, object] | str | os.PathLike[str],
) -> tuple[Mapping[str, object], bytes, str]:
    try:
        if isinstance(source, (str, os.PathLike)):
            shown = os.fspath(source)
            try:
                with open(source, "rb") as stream:
                    raw = stream.read(_MAX_BYTES + 1)
            except OSError as error:
                raise BehaviorLoadError([_refuse("INVALID_JSON", f"{shown}: {error}")]) from error
            if len(raw) > _MAX_BYTES:
                raise BehaviorLoadError(
                    [
                        _refuse(
                            "TOO_LARGE",
                            f"{shown} exceeds {_MAX_BYTES} bytes; behavior files are capped at "
                            f"{_MAX_BYTES} bytes",
                        )
                    ]
                )
            parsed = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_object,
                parse_constant=_constant,
                parse_float=_float,
            )
        elif isinstance(source, Mapping):
            shown = "<mapping>"
            parsed = _bounded_plain(source)
        else:
            raise _InvalidJSON("top level is not an object")
        if not isinstance(parsed, Mapping):
            raise _InvalidJSON("top level is not an object")
        plain = cast(Mapping[str, object], _bounded_plain(parsed))
        canonical = _canonical(plain)
        if len(canonical) > _MAX_BYTES:
            raise BehaviorLoadError(
                [
                    _refuse(
                        "TOO_LARGE",
                        f"{shown} exceeds {_MAX_BYTES} canonical JSON bytes; behavior inputs are "
                        f"capped at {_MAX_BYTES} bytes",
                    )
                ]
            )
        return plain, canonical, shown
    except BehaviorLoadError:
        raise
    except (UnicodeError, json.JSONDecodeError, _InvalidJSON, RecursionError) as error:
        shown = os.fspath(source) if isinstance(source, (str, os.PathLike)) else "<mapping>"
        raise BehaviorLoadError([_refuse("INVALID_JSON", f"{shown}: {error}")]) from error


def _envelope(data: Mapping[str, object], shown: str) -> list[BehaviorRefusal]:
    errors: list[BehaviorRefusal] = []
    keys = set(data)
    for key in sorted(_TOP_KEYS - keys):
        errors.append(_refuse("INVALID_KEY", f"{shown}: missing top-level key {key!r}"))
    for key in sorted(keys - _TOP_KEYS):
        errors.append(_refuse("INVALID_KEY", f"{shown}: unknown top-level key {key!r}"))
    schema_version = data.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != BEHAVIOR_SCHEMA_VERSION
    ):
        errors.append(
            _refuse(
                "INVALID_SCHEMA_VERSION",
                f"{shown}: top-level field 'schema_version' must be integer 1, got "
                f"{schema_version!r}",
            )
        )
    kind = data.get("kind")
    if kind != BEHAVIOR_KIND:
        errors.append(
            _refuse(
                "INVALID_KIND",
                f"{shown}: top-level field 'kind' must be {BEHAVIOR_KIND!r}, got {kind!r}",
            )
        )
    name = data.get("name")
    if not isinstance(name, str) or _NAME_RE.fullmatch(name) is None:
        errors.append(
            _refuse(
                "INVALID_VALUE",
                f"{shown}: top-level field 'name' must match [a-z0-9][a-z0-9-]{{0,63}}",
            )
        )
    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version <= 0:
        errors.append(
            _refuse(
                "INVALID_VALUE",
                f"{shown}: top-level field 'version' must be a positive integer, got {version!r}",
            )
        )
    extends = data.get("extends")
    if not isinstance(extends, list) or any(
        not isinstance(parent, str) or _NAME_RE.fullmatch(parent) is None for parent in extends
    ):
        errors.append(
            _refuse("INVALID_EXTENDS", f"{shown}: extends must be a list of behavior names")
        )
    else:
        seen: set[str] = set()
        for parent in extends:
            if parent in seen:
                errors.append(
                    _refuse(
                        "INVALID_EXTENDS",
                        f"{shown}: extends lists {parent!r} twice; name each parent once",
                    )
                )
            seen.add(parent)
    provenance = data.get("provenance")
    if not isinstance(provenance, Mapping):
        errors.append(_refuse("INVALID_PROVENANCE", f"{shown}: provenance must be an object"))
    else:
        for key in sorted(set(provenance) - _PROVENANCE_KEYS):
            errors.append(
                _refuse("INVALID_PROVENANCE", f"{shown}: provenance has unknown key {key!r}")
            )
        source = provenance.get("source")
        if not isinstance(source, str) or not source:
            errors.append(
                _refuse(
                    "INVALID_PROVENANCE",
                    f"{shown}: provenance.source must be a non-empty string",
                )
            )
        if "note" in provenance and not isinstance(provenance.get("note"), str):
            errors.append(
                _refuse("INVALID_PROVENANCE", f"{shown}: provenance.note must be a string")
            )
    sections = data.get("sections")
    if not isinstance(sections, Mapping):
        errors.append(_refuse("INVALID_VALUE", f"{shown}: sections must be an object"))
    else:
        for section in sorted(set(sections) - set(_SECTIONS)):
            errors.append(
                _refuse(
                    "INVALID_KEY",
                    f"{shown}: sections: unknown section {section!r}; known sections: "
                    f"{', '.join(_SECTIONS)}",
                )
            )
        for section, value in sections.items():
            if section in _SECTIONS and not isinstance(value, Mapping):
                errors.append(
                    _refuse("INVALID_VALUE", f"{shown}: sections.{section} must be an object")
                )
    return errors


def _positive_int(value: object, name: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        suffix = " or null" if optional else ""
        return f"{name} must be a positive integer{suffix}, got {value!r}"
    return None


def _string_list(value: object, name: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        suffix = " or null" if optional else ""
        return f"{name} must be a list of non-empty strings{suffix}"
    if len(set(value)) != len(value):
        return f"{name} must not contain repeated values"
    return None


def _value_reason(group: str, key: str, value: object) -> str | None:
    name = f"{group}.{key}"
    if group == "sentence":
        if key == "base":
            if value is None or value in _SENTENCE_BASES:
                return None
            return f"{name} must be null or a named base, got {value!r}"
        return _positive_int(value, name, optional=True)
    if group == "detection":
        if key in {"flexible", "guarded"}:
            return None if isinstance(value, bool) else f"{name} must be a bool, got {value!r}"
        reason = _string_list(value, name, optional=key == "locales")
        if reason is not None or value is None:
            return reason
        values = cast(list[str], value)
        if key == "currencies":
            from .recognize import _iso_currency_codes

            unknown = [item for item in values if item not in _iso_currency_codes()]
            if unknown:
                return f"{name} has unknown ISO 4217 code {unknown[0]!r}"
        elif key == "units":
            for item in values:
                try:
                    known = icu.MeasureUnit.forIdentifier(item).getIdentifier() == item
                except icu.ICUError:
                    known = False
                if not known:
                    return f"{name} has unknown ICU measure unit {item!r}"
        elif key == "locales":
            available = set(icu.Locale.getAvailableLocales())
            for item in values:
                if icu.Locale(item).getName() != item or item not in available:
                    return f"{name} has unknown or noncanonical ICU locale {item!r}"
        return None
    if group == "stream":
        if key == "boundary":
            if value in {"paragraph", "line", "explicit"}:
                return None
            return f"{name} must be 'paragraph', 'line', or 'explicit', got {value!r}"
        return _positive_int(value, name)
    if group == "regex":
        return _positive_int(value, name, optional=True)
    raise AssertionError(group)


def _icukit_section(data: Mapping[str, object], shown: str) -> list[BehaviorRefusal]:
    errors: list[BehaviorRefusal] = []
    for key in sorted(set(data) - _SECTION_KEYS):
        errors.append(
            _refuse(
                "INVALID_KEY",
                f"{shown}: sections.icukit: unknown key {key!r}; known keys: "
                f"{', '.join(sorted(_SECTION_KEYS - {'schema_version'}))}",
            )
        )
    version = data.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version != 1:
        errors.append(
            _refuse(
                "INVALID_SCHEMA_VERSION",
                f"{shown}: sections.icukit.schema_version must be integer 1, got {version!r}",
            )
        )
    for group, allowed in BEHAVIOR_OPTION_NAMES.items():
        if group not in data:
            continue
        raw = data[group]
        if not isinstance(raw, Mapping):
            errors.append(
                _refuse("INVALID_VALUE", f"{shown}: sections.icukit.{group} must be an object")
            )
            continue
        for key in sorted(set(raw) - set(allowed)):
            known = ", ".join(allowed) or "(none on this icukit version)"
            errors.append(
                _refuse(
                    "INVALID_KEY",
                    f"{shown}: sections.icukit.{group}: unknown key {key!r}; known keys: {known}",
                )
            )
        for key in sorted(set(raw) & set(allowed)):
            reason = _value_reason(group, key, raw[key])
            if reason is not None:
                errors.append(
                    _refuse("INVALID_VALUE", f"{shown}: sections.icukit.{group}.{key}: {reason}")
                )
    return errors


def load_behavior_schema(
    source: Mapping[str, object] | str | os.PathLike[str], /
) -> BehaviorSchema:
    """Load one full behavior envelope or bare icukit section.

    File and mapping inputs share the same 64 KiB, 16-level, 4,096-value, and
    256-code-point string caps. A full envelope is digested in full even though icukit
    interprets only ``sections.icukit``. An absent icukit section is neutral.

    Unknown options are refused. This excludes file paths, regular-expression patterns,
    exception policies, and process settings; sentence bases must use a published name.
    """
    data, canonical, shown = _read(source)
    envelope = any(key in data for key in _TOP_KEYS - {"schema_version"})
    name: str | None = None
    version: int | None = None
    extends: tuple[str, ...] = ()
    provenance: Mapping[str, str] = MappingProxyType({})
    section_present = True
    if envelope:
        errors = _envelope(data, shown)
        if errors:
            raise BehaviorLoadError(errors)
        name = cast(str, data["name"])
        version = cast(int, data["version"])
        extends = tuple(cast(list[str], data["extends"]))
        provenance = cast(Mapping[str, str], _freeze(data["provenance"]))
        sections = cast(Mapping[str, object], data["sections"])
        raw_section = sections.get("icukit")
        if raw_section is None:
            section: Mapping[str, object] = MappingProxyType({})
            section_present = False
        else:
            section = cast(Mapping[str, object], raw_section)
    else:
        section = data
    if section_present:
        errors = _icukit_section(section, shown)
        if errors:
            raise BehaviorLoadError(errors)
    digest = "sha256:" + sha256(canonical).hexdigest()
    return BehaviorSchema(
        digest,
        name,
        version,
        extends,
        provenance,
        cast(Mapping[str, object], _freeze(section)),
    )
