#!/usr/bin/env python3
"""Update or check the ICU-version-pinned detector conformance inventory."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

import icu

sys.path.insert(0, str(Path(__file__).parents[1]))

from icukit.conformance import build_inventory, canonical_json

GOLDEN = Path(__file__).parents[1] / "tests/data/detector_conformance_icu78_3_unicode17_0.json"


def pinned_icu() -> str:
    """The ICU version the committed inventory records, read from the file itself.

    Read rather than repeated: a literal here is a second copy of the same fact,
    and the copy that drifts is the one nothing checks.
    """
    return json.loads(GOLDEN.read_text(encoding="utf-8"))["icu_version"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("ci", "full"), required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    pinned = pinned_icu()
    if args.check and icu.ICU_VERSION != pinned:
        # Not "skip": a check that reports success without checking anything is
        # how the version gate went quiet in the first place.
        print(
            f"detector conformance golden records ICU {pinned}; this interpreter has "
            f"ICU {icu.ICU_VERSION}, so the inventory cannot be compared. Rerun on "
            f"ICU {pinned}, or regenerate with --write.",
            file=sys.stderr,
        )
        return 2
    actual = canonical_json(build_inventory(args.profile))
    if args.write:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(actual, encoding="utf-8")
        print(f"wrote {GOLDEN}")
        if icu.ICU_VERSION != pinned:
            icu_slug = icu.ICU_VERSION.replace(".", "_")
            unicode_slug = icu.UNICODE_VERSION.replace(".", "_")
            print(
                f"the file name still records ICU {pinned}; rename it to "
                f"detector_conformance_icu{icu_slug}_unicode{unicode_slug}.json and update "
                f"GOLDEN here and GOLDEN_PATH in tests/test_conformance.py to match. "
                f"test_golden_file_name_agrees_with_what_it_records fails until you do.",
                file=sys.stderr,
            )
        return 0
    expected = GOLDEN.read_text(encoding="utf-8")
    if actual == expected:
        print(f"detector conformance matches {GOLDEN}")
        return 0
    print(
        "".join(
            difflib.unified_diff(
                expected.splitlines(True),
                actual.splitlines(True),
                fromfile=str(GOLDEN),
                tofile="current inventory",
            )
        )
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
