#!/usr/bin/env python3
"""Snapshot CLDR's per-locale names of symbols into ``icukit/data/cldr_symbols``.

ICU names currency and unit symbols and % ‰ ‱ per locale, but other characters
only in English (their Unicode names), and it does not ship CLDR's annotations,
where the per-locale names of symbols live. This tool reads them from the pinned
CLDR release, once, and writes what :mod:`icukit.cldr_symbols` loads.

What is kept, for each CLDR locale in ``common/annotations`` and
``common/annotationsDerived``:

* every annotated character or sequence that is not an emoji. The emoji test is
  ICU's own: a string is an emoji when ICU gives it the ``RGI_Emoji`` property
  (UTS #51's recommended set, which holds every default-emoji-presentation
  character and every emoji sequence), or when any non-ASCII code point in it is
  ``Emoji_Presentation`` or ``Emoji_Component`` (ZWJ, VS16, keycap, skin tone,
  regional indicator, tag: the parts only emoji sequences are made of). A
  character whose default presentation is text stays a symbol even where it can
  also be shown as an emoji ("©", "↔"), since in text it is a symbol;
* its ``type="tts"`` name and its keywords, at ICU's own draft threshold: values
  marked ``provisional`` or ``unconfirmed`` are left out, as ICU leaves them out of
  its data;
* only what differs from what the locale inherits. CLDR resolves each value
  through the locale's parent (``parentLocales`` in supplementalData.xml, or the
  locale with its last subtag removed; en_GB → en_001 → en → root), and "∅∅∅"
  removes an inherited value. A value equal to the inherited one is dropped, so the
  loader resolves the same chain to rebuild it.

Usage::

    python tools/cldr_symbol_names.py [--zip PATH]

``--zip`` reads a copy of the release already downloaded; its checksum is checked
all the same.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import icu

CLDR_VERSION = "48"
SOURCE_URL = f"https://unicode.org/Public/cldr/{CLDR_VERSION}/cldr-common-{CLDR_VERSION}.zip"
SHA256 = "06c7c698d6fd8d67cefac15a0206b0109b00e0ef1636f86f84449fa959561f74"

OUT_DIR = Path(__file__).parents[1] / "icukit" / "data" / "cldr_symbols"

REMOVED = "∅∅∅"
# ICU builds its data at CLDR's "contributed" level; these are below it.
_BELOW_ICU_DRAFT = {"provisional", "unconfirmed"}

_P = icu.UProperty


def is_emoji(text: str) -> bool:
    """Whether ICU takes ``text`` for an emoji (see the module docstring)."""
    if icu.Char.hasBinaryProperty(text, _P.RGI_EMOJI):
        return True
    return any(
        ord(c) > 0x7F
        and (
            icu.Char.hasBinaryProperty(c, _P.EMOJI_PRESENTATION)
            or icu.Char.hasBinaryProperty(c, _P.EMOJI_COMPONENT)
        )
        for c in text
    )


def read_annotations(xml: bytes) -> dict[str, dict[str, str]]:
    """``{cp: {"tts": name, "keywords": "a | b"}}`` from one annotations file."""
    entries: dict[str, dict[str, str]] = {}
    for node in ET.fromstring(xml).iter("annotation"):
        if node.get("draft") in _BELOW_ICU_DRAFT:
            continue
        field = "tts" if node.get("type") == "tts" else "keywords"
        entries.setdefault(node.get("cp"), {})[field] = (node.text or "").strip()
    return entries


def read_parents(xml: bytes) -> dict[str, str]:
    """CLDR's default ``parentLocales``, child to parent."""
    parents = {}
    for group in ET.fromstring(xml).iter("parentLocales"):
        if group.get("component"):
            continue
        for node in group.iter("parentLocale"):
            for child in node.get("locales").split():
                parents[child] = node.get("parent")
    return parents


def parent_of(locale: str, parents: dict[str, str]) -> str | None:
    """The locale ``locale`` inherits from, CLDR's way; None for root."""
    if locale in parents:
        return parents[locale]
    if "_" in locale:
        return locale.rsplit("_", 1)[0]
    return None if locale == "root" else "root"


def extract(
    files: dict[str, list[bytes]], parents: dict[str, str]
) -> dict[str, dict[str, dict[str, str]]]:
    """Each locale's non-emoji symbol values that differ from what it inherits.

    ``files`` gives each locale's annotation files, derived first: a value in
    ``annotations`` overrides the same one in ``annotationsDerived``. A value in
    the result is the locale's own; "∅∅∅" records a removal of an inherited one.
    """
    own: dict[str, dict[str, dict[str, str]]] = {}
    for locale, blobs in files.items():
        merged: dict[str, dict[str, str]] = {}
        for blob in blobs:
            for cp, fields in read_annotations(blob).items():
                if not is_emoji(cp):
                    merged.setdefault(cp, {}).update(fields)
        own[locale] = merged

    resolved_cache: dict[str, dict[tuple[str, str], str]] = {}

    def resolved(locale: str | None) -> dict[tuple[str, str], str]:
        if locale is None:
            return {}
        if locale not in resolved_cache:
            values = dict(resolved(parent_of(locale, parents)))
            for cp, fields in own.get(locale, {}).items():
                for field, value in fields.items():
                    if value == REMOVED:
                        values.pop((cp, field), None)
                    else:
                        values[(cp, field)] = value
            resolved_cache[locale] = values
        return resolved_cache[locale]

    deltas: dict[str, dict[str, dict[str, str]]] = {}
    for locale in sorted(own):
        inherited = resolved(parent_of(locale, parents))
        mine = resolved(locale)
        delta: dict[str, dict[str, str]] = {}
        for key in sorted(set(inherited) | set(mine)):
            if inherited.get(key) != mine.get(key):
                cp, field = key
                delta.setdefault(cp, {})[field] = mine.get(key, REMOVED)
        if delta:
            deltas[locale] = delta
    return deltas


def _header(what: str) -> str:
    return (
        f"# {what}\n"
        f"# cldr-version\t{CLDR_VERSION}\n"
        f"# source\t{SOURCE_URL}\n"
        f"# sha256\t{SHA256}\n"
        "# Generated by tools/cldr_symbol_names.py; do not edit.\n"
    )


def _code_points(cp: str) -> tuple[int, ...]:
    return tuple(ord(c) for c in cp)


def write(deltas, parents, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.tsv"):
        stale.unlink()
    lines = [f"{child}\t{parent}\n" for child, parent in sorted(parents.items())]
    (out_dir / "_parents.tsv").write_text(
        _header("CLDR parentLocales: child, parent") + "".join(lines), encoding="utf-8"
    )
    for locale, delta in deltas.items():
        lines = []
        for cp in sorted(delta, key=_code_points):
            fields = delta[cp]
            lines.append(f"{cp}\t{fields.get('tts', '')}\t{fields.get('keywords', '')}\n")
        (out_dir / f"{locale}.tsv").write_text(
            _header(f"CLDR symbol names for {locale}: symbol, tts name, keywords") + "".join(lines),
            encoding="utf-8",
        )


def load_release(path: Path | None) -> bytes:
    if path is None:
        with urllib.request.urlopen(SOURCE_URL) as response:
            data = response.read()
    else:
        data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise SystemExit(f"checksum mismatch: {digest} (expected {SHA256})")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--zip", type=Path, help="a downloaded copy of the release zip")
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    archive = zipfile.ZipFile(io.BytesIO(load_release(args.zip)))
    files: dict[str, list[bytes]] = {}
    for directory in ("annotationsDerived", "annotations"):
        prefix = f"common/{directory}/"
        for name in sorted(archive.namelist()):
            if name.startswith(prefix) and name.endswith(".xml"):
                locale = name[len(prefix) : -len(".xml")]
                files.setdefault(locale, []).append(archive.read(name))
    parents = read_parents(archive.read("common/supplemental/supplementalData.xml"))
    deltas = extract(files, parents)
    write(deltas, parents, args.out)
    total = sum(len(d) for d in deltas.values())
    print(f"{len(deltas)} locales, {total} symbol entries -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
