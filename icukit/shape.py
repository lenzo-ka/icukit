"""Versioned ICU word-shape schemes.

The built-in schemes are deliberately fixed and identified by a digest of
their canonical definition and the linked ICU/Unicode versions. Shape
extensions arrive later with locale-material support.

Example:
    >>> shape("U.S.")
    'A.A.'
    >>> shape("U.S.", "cased@1")
    'X.X.'
"""

from __future__ import annotations

import hashlib
import json
from typing import TypedDict

import icu

__all__ = ["ShapeSchemeInfo", "shape", "shape_scheme"]


class ShapeSchemeInfo(TypedDict):
    """Stable metadata identifying a shape scheme and its Unicode runtime."""

    name: str
    version: int
    icu: str
    unicode: str
    extensions: list[str]
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


def _category(char: str) -> str:
    value = icu.Char.getIntPropertyValue(ord(char), _GC)
    return icu.Char.getPropertyValueName(_GC, value, _LONG)


def _identity_digest(definition: dict[str, object], icu_version: str, unicode_version: str) -> str:
    identity = {
        "definition": definition,
        "icu": icu_version,
        "unicode": unicode_version,
    }
    digest = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return f"sha256:{digest}"


def shape_scheme(scheme: str = "coarse@1", /) -> ShapeSchemeInfo:
    """Describe a built-in shape scheme and return its stable identity digest.

    The digest covers canonical JSON containing the scheme definition plus the
    linked ICU and Unicode versions.
    """
    definition = _definition(scheme)
    return {
        "name": str(definition["name"]),
        "version": int(definition["version"]),
        "icu": icu.ICU_VERSION,
        "unicode": icu.UNICODE_VERSION,
        "extensions": [],
        "digest": _identity_digest(definition, icu.ICU_VERSION, icu.UNICODE_VERSION),
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


def shape(text: str, scheme: str = "coarse@1", /) -> str:
    """Return the versioned ICU shape of ``text``.

    ``coarse@1`` collapses letter and digit runs; ``cased@1`` distinguishes
    letter case and caps each same-symbol run at four. Combining marks directly
    following a letter or digit run are absorbed.

    Example:
        >>> shape("Mr. Smith")
        'A. A'
        >>> shape("Mr. Smith", "cased@1")
        'Xx. Xxxxx'
    """
    _definition(scheme)
    normalized = _NFC.normalize(text)
    if (
        scheme == "coarse@1"
        and len(normalized) == 1
        and _category(normalized) == "Uppercase_Letter"
    ):
        return "<Lu>"

    result: list[str] = []
    run_symbol: str | None = None
    run_length = 0
    absorbable = False
    for char in normalized:
        category = _category(char)
        if category.endswith("_Mark") and absorbable:
            continue
        symbol = _symbol(category, scheme)
        if symbol is None:
            result.append(char)
            run_symbol = None
            run_length = 0
            absorbable = False
            continue
        is_letter_or_digit = category.endswith("_Letter") or category == "Decimal_Number"
        if symbol == run_symbol:
            run_length += 1
            if scheme == "cased@1" and run_length <= 4:
                result.append(symbol)
        else:
            result.append(symbol)
            run_symbol = symbol
            run_length = 1
        absorbable = is_letter_or_digit
    return "".join(result)
