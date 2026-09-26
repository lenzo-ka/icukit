"""
CLDR's per-locale names of symbols ("&": "ampersand", "Et-Zeichen", "esperluette").

ICU names currency and unit symbols and % ‰ ‱ per locale, but other characters only in
English, by their Unicode names, and it does not ship CLDR's annotations, where the
per-locale names live. This module reads them from a snapshot of those annotations
(``data/cldr_symbols``), made by ``tools/cldr_symbol_names.py`` from a pinned CLDR
release whose version, URL, and checksum each file's header records. The snapshot
holds the symbols that are not emoji, each with its text-to-speech name and keywords,
and for each CLDR locale only what differs from what the locale inherits; the lookup
here resolves the same inheritance CLDR does (en_GB from en_001, en_001 from en, en
from root) to rebuild a locale's names.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import icu

__all__ = ["cldr_locale", "cldr_symbol_names", "icu_cldr_version", "snapshot_cldr_version"]

_DATA_DIR = Path(__file__).parent / "data" / "cldr_symbols"
_REMOVED = "∅∅∅"


def _read(path: Path) -> tuple[dict[str, str], list[list[str]]]:
    """A snapshot file's header fields and its rows."""
    header: dict[str, str] = {}
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            name, _tab, value = line[2:].partition("\t")
            if value:
                header[name] = value
        elif line:
            rows.append(line.split("\t"))
    return header, rows


@cache
def _parents() -> tuple[dict[str, str], dict[str, str]]:
    path = _DATA_DIR / "_parents.tsv"
    if not path.is_file():
        return {}, {}
    header, rows = _read(path)
    return header, {child: parent for child, parent in rows}


def snapshot_cldr_version() -> str:
    """The CLDR version the snapshot was made from ("48"); empty without a snapshot."""
    return _parents()[0].get("cldr-version", "")


@cache
def icu_cldr_version() -> str:
    """The CLDR version of ICU's own data (root's ``Version``); empty if unreadable."""
    try:
        return icu.ResourceBundle("ICUDATA", icu.Locale("root")).getStringEx("Version")
    except icu.ICUError:
        return ""


@cache
def _likely_script(language: str) -> str:
    """The script ICU's likely subtags give ``language`` ("Hans" for zh); empty if none."""
    try:
        return icu.Locale(language).addLikelySubtags().getScript()
    except icu.ICUError:
        return ""


@cache
def cldr_locale(locale: str) -> str:
    """``locale`` as CLDR names the locale whose data it reads ("zh_TW": "zh_Hant_TW").

    ICU's alias resolution first ("iw": "he", "sh": "sr_Latn"), then the script ICU's
    likely subtags give it, kept only where it is not the language's own likely script:
    zh_TW is Traditional (zh_Hant_TW) and sr_ME Latin (sr_Latn_ME), while en_GB stays
    en_GB, so that its parentLocales entry (en_001) applies. The region and variant are
    the locale's own.
    """
    if locale in ("", "root", "und"):
        return "root"
    canonical = icu.Locale.createCanonical(locale)
    language = canonical.getLanguage()
    if not language or language == "und":
        return "root"
    try:
        script = icu.Locale(canonical.getName()).addLikelySubtags().getScript()
    except icu.ICUError:
        script = canonical.getScript()
    parts = [language]
    if script and script != _likely_script(language):
        parts.append(script)
    parts += [part for part in (canonical.getCountry(), canonical.getVariant()) if part]
    return "_".join(parts)


def _parent(locale: str) -> str | None:
    """The locale ``locale`` inherits from, CLDR's way; None for root.

    CLDR's parentLocales where they name the locale; otherwise a language and a script
    that is not the language's likely one inherit from root (CLDR's "nonlikelyScript"
    rule: ru_Latn does not take ru's Cyrillic names), and any other locale from itself
    with its last subtag removed.
    """
    parents = _parents()[1]
    if locale in parents:
        return parents[locale]
    if "_" in locale:
        parts = locale.split("_")
        if len(parts) == 2 and len(parts[1]) == 4 and parts[1] != _likely_script(parts[0]):
            return "root"
        return locale.rsplit("_", 1)[0]
    return None if locale == "root" else "root"


@cache
def _own(locale: str) -> tuple[tuple[str, str, str], ...]:
    path = _DATA_DIR / f"{locale}.tsv"
    if not path.is_file():
        return ()
    return tuple((cp, tts, keywords) for cp, tts, keywords in _read(path)[1])


@cache
def _resolved(locale: str | None) -> dict[str, tuple[str, str]]:
    if locale is None:
        return {}
    names = dict(_resolved(_parent(locale)))
    for cp, tts, keywords in _own(locale):
        inherited_tts, inherited_keywords = names.get(cp, ("", ""))
        tts = "" if tts == _REMOVED else tts or inherited_tts
        keywords = "" if keywords == _REMOVED else keywords or inherited_keywords
        if tts or keywords:
            names[cp] = (tts, keywords)
        else:
            names.pop(cp, None)
    return names


@cache
def cldr_symbol_names(locale: str) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """``(symbol, name, keywords)`` for each symbol CLDR names in ``locale``.

    ``name`` is CLDR's text-to-speech name ("ampersand"), empty where CLDR gives only
    keywords; ``keywords`` are CLDR's, in its order. Resolved through CLDR's locale
    inheritance from the CLDR locale ``locale`` names (see :func:`cldr_locale`), in code
    point order. Empty for a locale CLDR names no symbols in, or when the snapshot is
    missing.
    """
    rows = []
    for cp, (tts, keywords) in sorted(
        _resolved(cldr_locale(locale)).items(), key=lambda item: [ord(c) for c in item[0]]
    ):
        words = tuple(word.strip() for word in keywords.split("|") if word.strip())
        rows.append((cp, tts, words))
    return tuple(rows)
