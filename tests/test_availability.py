"""Availability API, command, and generated-document conformance."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from icukit import detector_key, flexible_detectors
from icukit.availability import availability
from icukit.material import load_locale_material

ROOT = Path(__file__).parent.parent
FIXTURE = ROOT / "tests" / "data" / "material" / "qaa-spellout.json"
availability_module = importlib.import_module("icukit.availability")

FLEXIBLE_HEAD_SNAPSHOTS = {
    ("en_US", False): (362, "d39112927a4996895c93fff13084f45903b47f0874d0630bf3866b6decfc30a0"),
    ("en_US", True): (415, "bc7ee5fb5a30829e3fd253d3217f9611ba05fb9e3344e9b026036428b6c30420"),
    ("de", False): (219, "c9fc2089aafb55b22fa5b5a20b520da5b0d10d452c8ed64e2731b7ce1824b179"),
    ("de", True): (286, "76c64c9736dfcf0fedd172012a454f472c84b38e95522bfb6e57d763bc456df1"),
    ("ja_JP", False): (205, "1bce7b93d2af951260c325fe471067aca17d559b398434dc6aeb6f6a80c6a77f"),
    ("ja_JP", True): (261, "7916977f7a9b79dc9ec01dc15ed2eb2c1315ab6cc0e61059b4c963cd044b567d"),
    ("yo", False): (201, "7cc6a0706d430c7bbedff9085958e22940032e0bb4a426f997246dd695b8760d"),
    ("yo", True): (251, "84f600c82de1c4c94ae6c553279e0313a29849a8e33e4a320441b1a474a0bf29"),
}


def _yo_material(tmp_path: Path):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document["locale"] = "yo"
    for witness in document["witnesses"]:
        witness["locale"] = "yo"
    for near_miss in document["near_misses"]:
        near_miss["locale"] = "yo"
    path = tmp_path / "yo-spellout.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return load_locale_material(path)


def _cardinal(rows):
    return [
        row for row in rows if row.family == "spellout-number" and row.spec == "%spellout-cardinal"
    ]


def test_b14_icu_user_and_served_by_rows(tmp_path):
    yo_icu = next(row for row in _cardinal(availability("yo")) if row.source == "icu")
    assert yo_icu.served_by == "en"

    material = _yo_material(tmp_path)
    rows = _cardinal(availability("yo", material=[material]))
    assert any(row.source == "icu" and row.served_by == "en" for row in rows)
    assert any(
        row.source == "user"
        and row.material == material.digest
        and row.provenance == material.provenance["source"]
        for row in rows
    )

    assert all(row.served_by is None for row in availability("fr") if row.source == "icu")


def test_b14_empty_actual_locale_is_root(monkeypatch):
    monkeypatch.setattr(availability_module, "_actual_spellout_locale", lambda locale: "")
    row = next(row for row in _cardinal(availability("en")) if row.source == "icu")
    assert row.served_by == "root"


def test_b15_curated_measure_is_beside_icu():
    all_rows = availability("en")
    rows = [row for row in all_rows if row.family == "measure"]
    curated = next(
        row
        for row in rows
        if row.source == "curated" and row.provenance == "icukit/data/unit_surfaces/en.tsv"
    )
    assert any(row.source == "icu" and row.spec == curated.spec for row in rows)
    for family in ("letter-name", "single-letter-word"):
        family_rows = [row for row in all_rows if row.family == family]
        assert {row.source for row in family_rows} == {"curated"}
        assert all(
            row.provenance == "icukit/recognize.py"
            for row in family_rows
            if row.source == "curated"
        )
    plural_rows = [row for row in all_rows if row.family == "plural-numeral"]
    assert {row.source for row in plural_rows} == {"icu", "curated"}


def test_inline_curated_families_are_unavailable_without_a_language_table():
    rows = availability("de")
    expected = {
        "letter-name": "icukit has no curated letter-name table for de",
        "plural-numeral": "icukit has no curated plural-numeral suffix table for de",
        "single-letter-word": "icukit has no curated single-letter-word table for de",
    }
    for family, reason in expected.items():
        family_rows = [row for row in rows if row.family == family]
        assert family_rows == [
            availability_module.AvailabilityRow(
                "de", family, family, None, None, None, None, None, reason
            )
        ]


def test_availability_does_not_change_flexible_gang_membership():
    for (locale, guarded), expected in FLEXIBLE_HEAD_SNAPSHOTS.items():
        serialized = sorted(
            json.dumps(detector_key(detector), ensure_ascii=False, separators=(",", ":"))
            for detector in flexible_detectors(locale, guarded=guarded).detectors
        )
        digest = sha256(
            json.dumps(serialized, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()

        assert (len(serialized), digest) == expected


def test_skipped_specs_and_row_shape_have_no_evaluation_figures():
    rows = availability("en")
    assert any(row.source is None and row.type is None and row.reason for row in rows)
    forbidden = {"share", "shares", "percent", "percentage", "recall"}
    assert forbidden.isdisjoint(asdict(rows[0]))


def _run(*arguments):
    return subprocess.run(
        [sys.executable, "-m", "icukit.cli", "languages", *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_locale_json_and_material():
    yo = _run("yo", "--json")
    assert yo.returncode == 0
    rows = [json.loads(line) for line in yo.stdout.splitlines()]
    assert any(
        row["family"] == "spellout-number"
        and row["spec"] == "%spellout-cardinal"
        and row["source"] == "icu"
        and row["served_by"] == "en"
        for row in rows
    )

    qaa = _run("qaa", "--material", str(FIXTURE), "--json")
    assert qaa.returncode == 0
    assert any(json.loads(line)["source"] == "user" for line in qaa.stdout.splitlines())


def test_cli_reports_every_material_refusal_and_all_languages(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema_version": 1, "extra": true}', encoding="utf-8")
    refused = _run("qaa", "--material", str(bad), "--json")
    assert refused.returncode != 0
    assert "INVALID_KEY" in refused.stderr
    assert "INVALID_KIND" in refused.stderr

    listed = _run()
    assert listed.returncode == 0
    assert any(line.startswith("yo\t") for line in listed.stdout.splitlines())


def test_cli_json_has_no_evaluation_keys():
    result = _run("yo", "--json")
    assert result.returncode == 0
    forbidden = {"share", "shares", "percentage", "recall"}
    assert all(forbidden.isdisjoint(json.loads(line)) for line in result.stdout.splitlines())
