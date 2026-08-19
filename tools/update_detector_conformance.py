#!/usr/bin/env python3
"""Update or check the ICU-version-pinned detector conformance inventory."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

import icu

sys.path.insert(0, str(Path(__file__).parents[1]))

from icukit.conformance import build_inventory, canonical_json

PINNED_ICU = "78.3"
GOLDEN = Path(__file__).parents[1] / "tests/data/detector_conformance_icu78_3_unicode17_0.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("ci", "full"), required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.check and icu.ICU_VERSION != PINNED_ICU:
        print(
            f"detector conformance golden requires ICU {PINNED_ICU}; found {icu.ICU_VERSION}; skip"
        )
        return 0
    actual = canonical_json(build_inventory(args.profile))
    if args.write:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(actual, encoding="utf-8")
        print(f"wrote {GOLDEN}")
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
