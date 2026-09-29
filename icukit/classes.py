"""ICU character classes and fixed-width context windows.

The four base class alphabets are discovered from the linked ICU at import
time. Runtime material can add namespaced extension classes, but it cannot
replace any ICU value.

Example:
    >>> char_classes("Mr. 5", "sentence_break")
    ['Upper', 'Lower', 'ATerm', 'Sp', 'Numeric']
    >>> class_window("Mr. Smith", 3, before=3, after=2).before[-1].text
    '.'
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import cache
from typing import Literal

import icu

from .material import (
    LocaleMaterial,
    MaterialLoadError,
    MaterialRefusal,
    _ambiguous_refinements,
    _require_loaded,
)

__all__ = ["Prop", "ClassPoint", "ClassWindow", "char_classes", "class_window"]

Prop = Literal["word_break", "sentence_break", "general_category", "script"]
"""A supported ICU character-property alphabet."""

_PROPERTY_IDS: dict[Prop, int] = {
    "word_break": icu.UProperty.WORD_BREAK,
    "sentence_break": icu.UProperty.SENTENCE_BREAK,
    "general_category": icu.UProperty.GENERAL_CATEGORY,
    "script": icu.UProperty.SCRIPT,
}
_LONG = icu.UPropertyNameChoice.LONG_PROPERTY_NAME
_SHORT = icu.UPropertyNameChoice.SHORT_PROPERTY_NAME


def _property_values(
    prop_id: int,
    choice: int,
    *,
    get_min_value: Callable[[int], int] = icu.Char.getIntPropertyMinValue,
    get_max_value: Callable[[int], int] = icu.Char.getIntPropertyMaxValue,
    get_value_name: Callable[[int, int, int], str] = icu.Char.getPropertyValueName,
) -> tuple[str, ...]:
    """Enumerate one property alphabet through the supplied ICU accessors."""
    minimum = get_min_value(prop_id)
    maximum = get_max_value(prop_id)
    return tuple(get_value_name(prop_id, value, choice) for value in range(minimum, maximum + 1))


# Kept private because the alphabet is an implementation identity, not a new
# mutable registry.  Tests intentionally inspect it to prove runtime discovery.
_PROPERTY_ALPHABETS = {
    name: _property_values(prop_id, _LONG) for name, prop_id in _PROPERTY_IDS.items()
}


def _canonical_property(prop: str) -> Prop:
    """Resolve any ICU property alias to one of the four supported names."""
    try:
        prop_id = icu.Char.getPropertyEnum(prop)
    except icu.ICUError as error:
        raise ValueError(f"unknown character property: {prop!r}") from error
    for name, supported_id in _PROPERTY_IDS.items():
        if prop_id == supported_id:
            return name
    raise ValueError(f"unsupported character property: {prop!r}")


def _value_name(char: str, prop: Prop, choice: int = _LONG) -> str:
    prop_id = _PROPERTY_IDS[prop]
    value = icu.Char.getIntPropertyValue(ord(char), prop_id)
    return icu.Char.getPropertyValueName(prop_id, value, choice)


def _canonical_value(prop: str, alias: str) -> str:
    """Resolve a property value alias to its property-qualified long name."""
    canonical = _canonical_property(prop)
    prop_id = _PROPERTY_IDS[canonical]
    try:
        value = icu.Char.getPropertyValueEnum(prop_id, alias)
        return icu.Char.getPropertyValueName(prop_id, value, _LONG)
    except icu.ICUError as error:
        raise ValueError(f"unknown {canonical} value: {alias!r}") from error


_IDENTITY_DEFINITION = {
    "schema": "icukit.classes@1",
    "icu": icu.ICU_VERSION,
    "unicode": icu.UNICODE_VERSION,
    "properties": {name: list(values) for name, values in _PROPERTY_ALPHABETS.items()},
}
_CLASS_IDENTITY = (
    "sha256:"
    + hashlib.sha256(
        json.dumps(
            _IDENTITY_DEFINITION, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
)


@dataclass(frozen=True)
class ClassPoint:
    """The four ICU classes of one code point, with code-point offsets."""

    text: str
    start: int
    end: int
    word_break: str
    sentence_break: str
    general_category: str
    script: str
    extension_classes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClassWindow:
    """A fixed-width character-class window around a code-point boundary.

    ``before`` and ``after`` always contain their requested number of entries.
    Missing entries use ``<BOS>`` or ``<EOS>`` at a known text edge and
    ``<PAD>`` when the supplied text is only a cutout. ``identity`` describes
    the long-name feature definition and therefore does not change with
    ``names="short"``.
    """

    offset: int
    before: tuple[ClassPoint, ...]
    after: tuple[ClassPoint, ...]
    identity: str


def _class_materials(material: Iterable[LocaleMaterial]) -> tuple[LocaleMaterial, ...]:
    """Validate and canonically order class-like material for composition."""
    loaded = tuple(
        item
        for raw in material
        if (item := _require_loaded(raw)).kind in {"char-classes", "shape-refinement", "classlike"}
    )
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    refusals = []
    for item in loaded:
        if item.id in seen_ids:
            refusals.append(MaterialRefusal("DUPLICATE_ID", f"duplicate material id {item.id!r}"))
        elif item.id is not None:
            seen_ids.add(item.id)
        for extension in (*item.classes, *item.shape_refinements):
            if extension.name in seen_names:
                refusals.append(
                    MaterialRefusal("DUPLICATE_ID", f"duplicate extension id {extension.name!r}")
                )
            else:
                seen_names.add(extension.name)
    if not refusals:
        refusals.extend(
            _ambiguous_refinements(
                tuple(extension for item in loaded for extension in item.classes),
                tuple(refinement for item in loaded for refinement in item.shape_refinements),
            )
        )
    if refusals:
        raise MaterialLoadError(refusals)
    return tuple(sorted(loaded, key=lambda item: (item.digest, item.id or "")))


@cache
def _unicode_set(pattern: str) -> icu.UnicodeSet:
    result = icu.UnicodeSet(pattern)
    result.freeze()
    return result


def _extension_classes(char: str, material: Iterable[LocaleMaterial]) -> tuple[str, ...]:
    """Return the additive classes matching one code point."""
    matches = []
    for item in _class_materials(material):
        for extension in item.classes:
            if (
                extension.unicode_set is not None
                and _unicode_set(extension.unicode_set).contains(char)
            ) or char in extension.members:
                matches.append(extension.name)
    return tuple(sorted(matches))


def _identity(materials: tuple[LocaleMaterial, ...]) -> str:
    if not materials:
        return _CLASS_IDENTITY
    definition = {
        "base": _IDENTITY_DEFINITION,
        "material": [item.digest for item in materials],
    }
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                definition, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
    )


def char_classes(
    text: str,
    prop: Prop = "general_category",
    /,
    *,
    material: Iterable[LocaleMaterial] = (),
) -> list[str]:
    """Return one canonical long ICU property value name per code point.

    ICU aliases for the property name are accepted and resolved within the
    property, so a short alias cannot collide with another property alphabet.

    Example:
        >>> char_classes("Mr. 5", "sentence_break")
        ['Upper', 'Lower', 'ATerm', 'Sp', 'Numeric']
        >>> char_classes("A", "gc")
        ['Uppercase_Letter']
    """
    _class_materials(material)
    canonical = _canonical_property(prop)
    return [_value_name(char, canonical) for char in text]


def _point(text: str, index: int, choice: int, materials: tuple[LocaleMaterial, ...]) -> ClassPoint:
    char = text[index]
    return ClassPoint(
        char,
        index,
        index + 1,
        _value_name(char, "word_break", choice),
        _value_name(char, "sentence_break", choice),
        _value_name(char, "general_category", choice),
        _value_name(char, "script", choice),
        _extension_classes(char, materials),
    )


def _padding(offset: int, value: str) -> ClassPoint:
    return ClassPoint("", offset, offset, value, value, value, value, ())


def class_window(
    text: str,
    offset: int,
    /,
    *,
    before: int = 3,
    after: int = 3,
    material: Iterable[LocaleMaterial] = (),
    text_starts: bool = True,
    text_ends: bool = True,
    names: Literal["long", "short"] = "long",
) -> ClassWindow:
    """Return ICU classes immediately before and after ``offset``.

    Args:
        text: Source text for the window.
        offset: Code-point boundary in ``text``.
        before: Number of entries before the boundary.
        after: Number of entries after the boundary.
        material: Validated additive character-class material.
        text_starts: Whether index zero is the start of the complete text.
        text_ends: Whether ``len(text)`` is the end of the complete text.
        names: Return ICU long or short value names.

    Example:
        >>> point = class_window("Mr. Smith", 3, before=3, after=2).before[-1]
        >>> (point.text, point.word_break, point.sentence_break)
        ('.', 'MidNumLet', 'ATerm')
    """
    if not isinstance(offset, int) or isinstance(offset, bool) or not 0 <= offset <= len(text):
        raise ValueError("offset must be a code-point boundary within text")
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in (before, after)
    ):
        raise ValueError("before and after must be nonnegative integers")
    if names not in {"long", "short"}:
        raise ValueError("names must be 'long' or 'short'")
    choice = _LONG if names == "long" else _SHORT
    materials = _class_materials(material)

    before_points = [
        _point(text, index, choice, materials) for index in range(max(0, offset - before), offset)
    ]
    before_padding = before - len(before_points)
    if before_padding:
        before_points[:0] = [_padding(0, "<BOS>" if text_starts else "<PAD>")] * before_padding

    after_points = [
        _point(text, index, choice, materials)
        for index in range(offset, min(len(text), offset + after))
    ]
    after_padding = after - len(after_points)
    if after_padding:
        after_points.extend(
            [_padding(len(text), "<EOS>" if text_ends else "<PAD>")] * after_padding
        )
    return ClassWindow(offset, tuple(before_points), tuple(after_points), _identity(materials))
