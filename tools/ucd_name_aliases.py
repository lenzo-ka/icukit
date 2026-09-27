#!/usr/bin/env python3
"""Snapshot the formal name aliases ICU lacks into ``icukit/data/ucd_name_aliases``.

Unicode's formal name aliases (``NameAliases.txt`` in the UCD) come in five types:
``correction``, ``control``, ``alternate``, ``figment`` and ``abbreviation``. ICU's
name data carries the corrections alone (``U_CHAR_NAME_ALIAS``), so ``BEL``, ``ALERT``,
``LINE FEED``, ``NBSP``, ``BYTE ORDER MARK`` and ``ZWJ`` resolve in neither direction.
This tool reads the others from the pinned UCD file, once, and writes what
:mod:`icukit.ucd_name_aliases` loads; the corrections stay ICU's.

The split is measured, not assumed: the tool runs only under an ICU of the same
Unicode version as the pinned file, and checks there that ICU resolves every
correction alias, in both directions, and none of the others under any of its name
choices (formal names, aliases, and extended labels). The output depends on the two
pinned files alone, so a rerun reproduces it byte for byte.

The data is Unicode's, under the Unicode License v3, whose text is written beside it.

Usage::

    python tools/ucd_name_aliases.py [--aliases PATH] [--license PATH] [--out DIR]

``--aliases`` and ``--license`` read copies already downloaded; their checksums are
checked all the same.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

import icu

UNICODE_VERSION = "17.0.0"
SOURCE_URL = f"https://www.unicode.org/Public/{UNICODE_VERSION}/ucd/NameAliases.txt"
SHA256 = "793f6f1e4d15fd90f05ae66460191dc4d75d1fea90136a25f30dd6a4cb950eac"
# The UCD publishes no license file of its own; its terms point here. The page is not
# versioned, so a new copyright year changes its checksum: download it, read it, pin anew.
LICENSE_URL = "https://www.unicode.org/license.txt"
LICENSE_SHA256 = "e7a93b009565cfce55919a381437ac4db883e9da2126fa28b91d12732bc53d96"

OUT_DIR = Path(__file__).parents[1] / "icukit" / "data" / "ucd_name_aliases"

TYPES = ("correction", "control", "alternate", "figment", "abbreviation")
# The type ICU carries, and so the one left out of the snapshot.
ICU_TYPE = "correction"


def _version_key(version: str) -> tuple[int, ...]:
    parts = [int(part) for part in version.split(".") if part.isdigit()]
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def fetch(url: str, sha256: str, path: Path | None) -> bytes:
    if path is None:
        with urllib.request.urlopen(url) as response:
            data = response.read()
    else:
        data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != sha256:
        raise SystemExit(f"checksum mismatch for {url}: {digest} (expected {sha256})")
    return data


def read_aliases(text: str) -> list[tuple[str, str, str]]:
    """``(code point, alias, type)`` for each line of ``NameAliases.txt``, in order."""
    rows = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        code_point, alias, kind = (field.strip() for field in line.split(";"))
        kind = kind.lower()  # the file says type labels compare without regard to case
        if kind not in TYPES:
            raise SystemExit(f"unknown alias type {kind!r} for U+{code_point}")
        rows.append((code_point, alias, kind))
    return rows


_CHOICES = (
    icu.UCharNameChoice.UNICODE_CHAR_NAME,
    icu.UCharNameChoice.CHAR_NAME_ALIAS,
    icu.UCharNameChoice.EXTENDED_CHAR_NAME,
)


def _icu_finds(alias: str, choice) -> int:
    try:
        return icu.Char.charFromName(alias.encode("ascii"), choice)
    except (icu.ICUError, ValueError):
        return -1


def _icu_resolves(code_point: str, alias: str) -> bool:
    """Whether ICU has ``alias`` as the code point's alias, in both directions."""
    char = chr(int(code_point, 16))
    choice = icu.UCharNameChoice.CHAR_NAME_ALIAS
    return _icu_finds(alias, choice) == ord(char) and icu.Char.charName(char, choice) == alias


def _icu_knows(alias: str) -> bool:
    """Whether ICU finds any character by ``alias``, under any of its name choices."""
    return any(_icu_finds(alias, choice) != -1 for choice in _CHOICES)


def check_icu(rows: list[tuple[str, str, str]]) -> None:
    """Refuse unless ICU resolves exactly the correction aliases (see the docstring):
    each correction as its code point's alias, and none of the others as any name."""
    wrong = [
        f"U+{code_point} {alias} ({kind})"
        for code_point, alias, kind in rows
        if (_icu_resolves(code_point, alias) if kind == ICU_TYPE else _icu_knows(alias))
        != (kind == ICU_TYPE)
    ]
    if wrong:
        raise SystemExit(
            "ICU does not carry exactly the correction aliases; the snapshot would be "
            "wrong: " + "; ".join(wrong)
        )


def render(rows: list[tuple[str, str, str]]) -> str:
    kept = [row for row in rows if row[2] != ICU_TYPE]
    header = (
        "# Unicode formal name aliases ICU does not carry: code point, alias, type\n"
        f"# unicode-version\t{UNICODE_VERSION}\n"
        f"# source\t{SOURCE_URL}\n"
        f"# sha256\t{SHA256}\n"
        "# Generated by tools/ucd_name_aliases.py; do not edit.\n"
    )
    return header + "".join(f"{cp}\t{alias}\t{kind}\n" for cp, alias, kind in kept)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--aliases", type=Path, help="a downloaded copy of NameAliases.txt")
    parser.add_argument("--license", type=Path, help="a downloaded copy of the license")
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    if _version_key(icu.UNICODE_VERSION) != _version_key(UNICODE_VERSION):
        raise SystemExit(
            f"ICU's Unicode is {icu.UNICODE_VERSION}, the pinned file's {UNICODE_VERSION}; "
            "run under an ICU of the file's Unicode version"
        )
    rows = read_aliases(fetch(SOURCE_URL, SHA256, args.aliases).decode("utf-8"))
    check_icu(rows)
    license_text = fetch(LICENSE_URL, LICENSE_SHA256, args.license)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "NameAliases.tsv").write_text(render(rows), encoding="utf-8", newline="\n")
    (args.out / "LICENSE").write_bytes(license_text)
    counts = {kind: sum(1 for row in rows if row[2] == kind) for kind in TYPES}
    print(
        f"{counts}; {len(rows) - counts[ICU_TYPE]} written -> {args.out}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
