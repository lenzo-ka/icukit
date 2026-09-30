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
from .material import LocaleMaterial, ShapeRefinement, locale_descends_from

__all__ = ["CVLetterCounts", "ShapeSchemeInfo", "cvletters_counts", "shape", "shape_scheme"]


class CVLetterCounts(TypedDict):
    """Uncapped orthographic consonant-vowel letter counts.

    ``letters`` counts code points labeled ``V``, ``C``, ``Y``, or ``L``, plus
    letters that a namespaced shape refinement relabels (still letters);
    ``vowels`` counts ``V``; ``consonants`` counts ``C`` and ``Y``; and
    ``has_vowel`` reports whether ``vowels`` is positive.
    """

    letters: int
    vowels: int
    consonants: int
    has_vowel: bool


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
    "cvletters@1": {
        "name": "cvletters",
        "version": 1,
        "normalization": "ICU NFC",
        "indic_syllabic_category": {
            "scope": ["*_Letter", "*_Mark"],
            "Vowel|Vowel_Independent|Vowel_Dependent": "V",
            "Consonant*": "C",
        },
        "english_latin": {
            "locale": "en descendants",
            "match": "case-insensitive NFD base letter",
            "V": ["a", "e", "i", "o", "u"],
            "Y": ["y", "w"],
            "C": [
                "b",
                "c",
                "d",
                "f",
                "g",
                "h",
                "j",
                "k",
                "l",
                "m",
                "n",
                "p",
                "q",
                "r",
                "s",
                "t",
                "v",
                "x",
                "z",
            ],
        },
        "unknown_letter": "L",
        "runs": {"letter_symbols_cap": 4, "other_symbols": "collapse"},
        "non_letters": {
            "Decimal_Number": "N (collapse run)",
            "Currency_Symbol": "¤",
            "absorb_unlabeled_marks_after": ["letter", "digit"],
            "other": "verbatim",
        },
    },
}
_GC = icu.UProperty.GENERAL_CATEGORY
_INSC = icu.UProperty.INDIC_SYLLABIC_CATEGORY
_SCRIPT = icu.UProperty.SCRIPT
_LONG = icu.UPropertyNameChoice.LONG_PROPERTY_NAME
_NFC = icu.Normalizer2.getNFCInstance()
_NFD = icu.Normalizer2.getNFDInstance()
_ROOT = icu.Locale.getRoot()
_CVLETTERS_LABEL_SYMBOLS = frozenset({"V", "C", "Y"})
_CVLETTERS_LETTER_SYMBOLS = frozenset({"V", "C", "Y", "L"})

# Curated per icukit BASIS ``source``: ICU and CLDR do not define a vowel-letter
# property for alphabets. Y is ambiguous in words such as "gym" and "fly"; W is
# ambiguous in English digraphs and Welsh loans such as "cwm" and "crwth".
_ENGLISH_CVLETTERS = {
    **dict.fromkeys("aeiou", "V"),
    **dict.fromkeys("yw", "Y"),
    **dict.fromkeys("bcdfghjklmnpqrstvxz", "C"),
}


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
    locale: str | None = None,
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
    ``locale`` is accepted for symmetry with :func:`shape` but does not affect
    scheme metadata or its digest.
    """
    del locale
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
    char: str, scheme: str, materials: tuple[LocaleMaterial, ...]
) -> ShapeRefinement | None:
    category = _category(char)
    extension_classes = set(_extension_classes(char, materials))
    matches = sorted(
        (refinement.name, refinement)
        for item in materials
        for refinement in item.shape_refinements
        if scheme == "cvletters@1" or refinement.symbol not in _CVLETTERS_LABEL_SYMBOLS
        if refinement.class_name == category or refinement.class_name in extension_classes
    )
    return matches[0][1] if matches else None


def _property_value(char: str, prop: int) -> str:
    value = icu.Char.getIntPropertyValue(ord(char), prop)
    return icu.Char.getPropertyValueName(prop, value, _LONG)


def _cvletters_base_symbol(char: str, category: str, locale: str | None) -> str | None:
    if category.endswith(("_Letter", "_Mark")):
        indic_category = _property_value(char, _INSC)
        if indic_category in {"Vowel", "Vowel_Independent", "Vowel_Dependent"}:
            return "V"
        if indic_category.startswith("Consonant"):
            return "C"
    if not category.endswith("_Letter"):
        return None
    if (
        locale is not None
        and locale_descends_from(locale, "en")
        and _property_value(char, _SCRIPT) == "Latin"
    ):
        base = _NFD.normalize(char)[0]
        label = _ENGLISH_CVLETTERS.get(str(icu.UnicodeString(base).toLower(_ROOT)))
        if label is not None:
            return label
    return "L"


def _cvletters_shape_counts_selections(
    text: str,
    locale: str | None,
    materials: tuple[LocaleMaterial, ...],
) -> tuple[str, CVLetterCounts, frozenset[str]]:
    normalized = _NFC.normalize(text)
    selected: set[str] = set()
    letters = vowels = consonants = 0
    result: list[str] = []
    run_symbol: str | None = None
    run_length = 0
    absorbable = False
    for char in normalized:
        category = _category(char)
        refinement = _selected_refinement(char, "cvletters@1", materials)
        label_refinement = refinement is not None and refinement.symbol in _CVLETTERS_LABEL_SYMBOLS
        if refinement is not None and not label_refinement:
            symbol = refinement.symbol
            selected.add(refinement.name)
        else:
            symbol = _cvletters_base_symbol(char, category, locale)
            if label_refinement and symbol == "L":
                symbol = refinement.symbol
                selected.add(refinement.name)

        if symbol in _CVLETTERS_LETTER_SYMBOLS:
            letters += 1
            if symbol == "V":
                vowels += 1
            elif symbol in {"C", "Y"}:
                consonants += 1
        elif refinement is not None and not label_refinement and category.endswith("_Letter"):
            letters += 1

        if category.endswith("_Mark") and absorbable and symbol is None:
            continue
        if symbol is None:
            symbol = _symbol(category, "coarse@1")
        if symbol is None:
            result.append(char)
            run_symbol = None
            run_length = 0
            absorbable = False
            continue
        is_letter_or_digit = category.endswith("_Letter") or category == "Decimal_Number"
        if symbol == run_symbol:
            run_length += 1
            if symbol in _CVLETTERS_LETTER_SYMBOLS and run_length <= 4:
                result.append(symbol)
        else:
            result.append(symbol)
            run_symbol = symbol
            run_length = 1
        absorbable = is_letter_or_digit
    counts: CVLetterCounts = {
        "letters": letters,
        "vowels": vowels,
        "consonants": consonants,
        "has_vowel": vowels > 0,
    }
    return "".join(result), counts, frozenset(selected)


def _shape_with_selections(
    text: str,
    scheme: str,
    materials: tuple[LocaleMaterial, ...],
    *,
    locale: str | None = None,
) -> tuple[str, frozenset[str]]:
    """Return a shape and the refinements that actually selected its code points."""
    if scheme == "cvletters@1":
        result, _counts, selected = _cvletters_shape_counts_selections(text, locale, materials)
        return result, selected
    normalized = _NFC.normalize(text)
    selected: set[str] = set()
    if (
        scheme == "coarse@1"
        and len(normalized) == 1
        and _category(normalized) == "Uppercase_Letter"
        and _selected_refinement(normalized, scheme, materials) is None
    ):
        return "<Lu>", frozenset()

    result: list[str] = []
    run_symbol: str | None = None
    run_length = 0
    absorbable = False
    for char in normalized:
        category = _category(char)
        refinement = _selected_refinement(char, scheme, materials)
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
    locale: str | None = None,
    material: Iterable[LocaleMaterial] = (),
) -> str:
    """Return the versioned ICU shape of ``text``.

    ``coarse@1`` collapses letter and digit runs; ``cased@1`` distinguishes
    letter case and caps each same-symbol run at four. ``cvletters@1`` is an
    approximate orthographic shape of vowel and consonant letters, not phones;
    its curated Latin table requires an ``en``-descendant ``locale``. Other
    alphabetic letters are ``L`` unless material supplies a label. Combining
    marks directly following a letter or digit run are absorbed unless ICU or a
    refinement labels them. Validated namespaced shape refinements take
    precedence and collapse adjacent uses as one run. An extended scheme name
    checks the supplied material's ids and digest prefixes; the name is a label,
    not proof of material identity.

    Example:
        >>> shape("Mr. Smith")
        'A. A'
        >>> shape("Mr. Smith", "cased@1")
        'Xx. Xxxxx'
    """
    materials = _class_materials(material)
    scheme = _resolve_scheme(scheme, materials)
    result, _ = _shape_with_selections(text, scheme, materials, locale=locale)
    return result


def cvletters_counts(
    text: str,
    /,
    *,
    locale: str | None = None,
    material: Iterable[LocaleMaterial] = (),
) -> CVLetterCounts:
    """Count uncapped ``cvletters@1`` labels in ``text``.

    ``Y`` counts as a consonant. ``L`` contributes only to ``letters``, so
    ``letters > vowels + consonants`` reports letters for which no vowel policy
    is available. Digits, absorbed marks, and other characters are excluded.
    """
    materials = _class_materials(material)
    _result, counts, _selected = _cvletters_shape_counts_selections(text, locale, materials)
    return counts
