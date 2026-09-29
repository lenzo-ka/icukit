"""Versioned ICU word-shape schemes.

The built-in schemes are deliberately fixed and identified by a digest of
their canonical definition and the linked ICU/Unicode versions. Experimental
runtime material can add namespaced symbols without redefining them.

Example:
    >>> shape("U.S.")
    'A.A.'
    >>> shape("U.S.", "cased@1")
    'X.X.'
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import TypedDict

import icu

from .classes import _class_materials, _extension_classes
from .material import LocaleMaterial, ShapeRefinement

__all__ = ["ShapeSchemeInfo", "shape", "shape_scheme"]


class ShapeSchemeInfo(TypedDict):
    """Stable metadata identifying a shape scheme and its Unicode runtime."""

    name: str
    version: int
    icu: str
    unicode: str
    extensions: list[dict[str, str]]
    digest: str


_DEFINITIONS = {
    "coarse@1": {
        "name": "coarse",
        "version": 1,
        "normalization": "ICU NFC",
        "single_uppercase_letter": "<Lu>",
        "classes": {
            "Decimal_Number": "N",
            "*_Letter": "A",
            "Currency_Symbol": "¤",
        },
        "runs": "collapse",
        "absorb_marks_after": ["A", "N"],
        "other": "verbatim",
    },
    "cased@1": {
        "name": "cased",
        "version": 1,
        "normalization": "ICU NFC",
        "classes": {
            "Uppercase_Letter|Titlecase_Letter": "X",
            "Lowercase_Letter": "x",
            "Modifier_Letter|Other_Letter": "a",
            "Decimal_Number": "d",
            "Currency_Symbol": "¤",
        },
        "runs": {"cap": 4},
        "absorb_marks_after": ["X", "x", "a", "d"],
        "other": "verbatim",
    },
}
_GC = icu.UProperty.GENERAL_CATEGORY
_LONG = icu.UPropertyNameChoice.LONG_PROPERTY_NAME
_NFC = icu.Normalizer2.getNFCInstance()


def _definition(scheme: str) -> dict[str, object]:
    try:
        return _DEFINITIONS[scheme]
    except KeyError as error:
        raise ValueError(f"unknown shape scheme: {scheme!r}") from error


def _extended_name(scheme: str, materials: tuple[LocaleMaterial, ...]) -> str:
    return scheme + "".join(
        f"+{item.id}@{item.digest.removeprefix('sha256:')[:12]}" for item in materials
    )


def _resolve_scheme(scheme: str, materials: tuple[LocaleMaterial, ...]) -> str:
    if scheme in _DEFINITIONS:
        return scheme
    for base_scheme in _DEFINITIONS:
        if materials and scheme == _extended_name(base_scheme, materials):
            return base_scheme
    raise ValueError(f"unknown shape scheme or material mismatch: {scheme!r}")


def _category(char: str) -> str:
    value = icu.Char.getIntPropertyValue(ord(char), _GC)
    return icu.Char.getPropertyValueName(_GC, value, _LONG)


def _identity_digest(
    definition: dict[str, object],
    icu_version: str,
    unicode_version: str,
    material_digests: tuple[str, ...] = (),
) -> str:
    identity = {
        "definition": definition,
        "icu": icu_version,
        "unicode": unicode_version,
    }
    if material_digests:
        identity["material"] = list(material_digests)
    digest = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return f"sha256:{digest}"


def shape_scheme(
    scheme: str = "coarse@1",
    /,
    *,
    material: Iterable[LocaleMaterial] = (),
) -> ShapeSchemeInfo:
    """Describe a shape scheme and return its stable identity digest.

    The digest covers canonical JSON containing the scheme definition plus the
    linked ICU and Unicode versions. With material, it also covers every
    material digest and reports each extension's id and digest. Its extended
    name is a label containing each material id and 12-hex digest prefix. Passing
    that label back checks those prefixes against the supplied material as a guard
    against an obvious mismatch; the full extension digests and this record's
    digest, rather than the label, are identities.
    """
    materials = _class_materials(material)
    base_scheme = _resolve_scheme(scheme, materials)
    definition = _definition(base_scheme)
    extended = _extended_name(base_scheme, materials)
    return {
        "name": str(definition["name"]) if not materials else extended,
        "version": int(definition["version"]),
        "icu": icu.ICU_VERSION,
        "unicode": icu.UNICODE_VERSION,
        "extensions": [{"id": item.id or "", "digest": item.digest} for item in materials],
        "digest": _identity_digest(
            definition,
            icu.ICU_VERSION,
            icu.UNICODE_VERSION,
            tuple(item.digest for item in materials),
        ),
    }


def _symbol(category: str, scheme: str) -> str | None:
    if scheme == "coarse@1":
        if category == "Decimal_Number":
            return "N"
        if category.endswith("_Letter"):
            return "A"
    else:
        if category in {"Uppercase_Letter", "Titlecase_Letter"}:
            return "X"
        if category == "Lowercase_Letter":
            return "x"
        if category in {"Modifier_Letter", "Other_Letter"}:
            return "a"
        if category == "Decimal_Number":
            return "d"
    if category == "Currency_Symbol":
        return "¤"
    return None


def _selected_refinement(
    char: str, materials: tuple[LocaleMaterial, ...]
) -> ShapeRefinement | None:
    category = _category(char)
    extension_classes = set(_extension_classes(char, materials))
    matches = sorted(
        (refinement.name, refinement)
        for item in materials
        for refinement in item.shape_refinements
        if refinement.class_name == category or refinement.class_name in extension_classes
    )
    return matches[0][1] if matches else None


def _shape_with_selections(
    text: str, scheme: str, materials: tuple[LocaleMaterial, ...]
) -> tuple[str, frozenset[str]]:
    """Return a shape and the refinements that actually selected its code points."""
    normalized = _NFC.normalize(text)
    selected: set[str] = set()
    if (
        scheme == "coarse@1"
        and len(normalized) == 1
        and _category(normalized) == "Uppercase_Letter"
        and _selected_refinement(normalized, materials) is None
    ):
        return "<Lu>", frozenset()

    result: list[str] = []
    run_symbol: str | None = None
    run_length = 0
    absorbable = False
    for char in normalized:
        category = _category(char)
        refinement = _selected_refinement(char, materials)
        if refinement is not None:
            selected.add(refinement.name)
        if category.endswith("_Mark") and absorbable and refinement is None:
            continue
        symbol = refinement.symbol if refinement is not None else _symbol(category, scheme)
        if symbol is None:
            result.append(char)
            run_symbol = None
            run_length = 0
            absorbable = False
            continue
        is_letter_or_digit = category.endswith("_Letter") or category == "Decimal_Number"
        if symbol == run_symbol:
            run_length += 1
            if refinement is None and scheme == "cased@1" and run_length <= 4:
                result.append(symbol)
        else:
            result.append(symbol)
            run_symbol = symbol
            run_length = 1
        absorbable = is_letter_or_digit
    return "".join(result), frozenset(selected)


def shape(
    text: str,
    scheme: str = "coarse@1",
    /,
    *,
    material: Iterable[LocaleMaterial] = (),
) -> str:
    """Return the versioned ICU shape of ``text``.

    ``coarse@1`` collapses letter and digit runs; ``cased@1`` distinguishes
    letter case and caps each same-symbol run at four. Combining marks directly
    following a letter or digit run are absorbed. Validated shape-refinement
    material selects a namespaced symbol before absorption or the base scheme
    and collapses adjacent uses of that symbol as one run. A refined
    punctuation symbol does not make punctuation absorb following marks. An
    extended scheme name checks the supplied material's ids and digest prefixes.
    The name is a label and is not proof of material identity.

    Example:
        >>> shape("Mr. Smith")
        'A. A'
        >>> shape("Mr. Smith", "cased@1")
        'Xx. Xxxxx'
    """
    materials = _class_materials(material)
    scheme = _resolve_scheme(scheme, materials)
    result, _ = _shape_with_selections(text, scheme, materials)
    return result
