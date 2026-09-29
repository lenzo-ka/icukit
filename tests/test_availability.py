"""Availability API, command, and generated-document conformance."""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from icukit import detector_key, flexible_detectors
from icukit.availability import availability
from icukit.material import load_locale_material
from icukit.serialize import detections_to_json

ROOT = Path(__file__).parent.parent
FIXTURE = ROOT / "tests" / "data" / "material" / "qaa-spellout.json"
availability_module = importlib.import_module("icukit.availability")


def _yo_material(tmp_path: Path, *, source: str | None = None):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document["locale"] = "yo"
    if source is not None:
        document["provenance"]["source"] = source
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
        "letter-name": (
            "built, but icukit has no curated letter-name table for de, so it reads nothing"
        ),
        "plural-numeral": (
            "built, but icukit has no curated plural-numeral suffix table for de, "
            "so it reads nothing"
        ),
        "single-letter-word": (
            "built, but icukit has no curated single-letter-word table for de, so it reads nothing"
        ),
    }
    for family, reason in expected.items():
        family_rows = [row for row in rows if row.family == family]
        assert family_rows == [
            availability_module.AvailabilityRow(
                "de", family, family, None, None, None, None, None, reason
            )
        ]


# The ordered flexible gangs and their ordered readings of one text, recorded before
# availability reporting was added: (member count, sha256 of the ordered first four
# detector_key components, sha256 of the ordered detections_to_json output).
_GANG_TEXT = "twenty-one; $45.50; 3 kg; 12%"
_GANGS_BEFORE = {
    ("en_US", False): (
        362,
        "f6ea8158e6897683b8f595326a80c87b796d14bbbd9144b8755c425e1cb013b6",
        "823c4241f43fe0e73e7c7c6f15f9780e5301cbd33a96f393ba7857b1cd05aa58",
    ),
    ("en_US", True): (
        415,
        "828b43ca44fee37fd8ef49a5baec2121281c7292ddd96e7ddd282322c30a5d3b",
        "2d14df990633d737cfa578a6db989d8c30c8c9a890122042836ad393df932e1d",
    ),
    ("de", False): (
        219,
        "55aed956384fe5ec390f776a4e5c5f7c83751eb2eca243a79bfcb42a6e264e61",
        "8b0e7b6cbfe7f449406bf79b1eb2a0f98674f7c83675b4ce9eebb25d266da78e",
    ),
    ("de", True): (
        286,
        "02d4245422dd1193f68a2fab44242abd93a54e3bc05f01523a13679da1e7a2ab",
        "0c131cc9d1dd95331487a9a97ef5b6a7e9e8b7acf6a11b2de0492888358651f9",
    ),
    ("ja_JP", False): (
        205,
        "6fe3f6376118b67bfeb44fe110734e220056f414f0e390a8dd74734b5bba2072",
        "32eb8f4e413a32659b3e7f7721cd2525ef57ff02f07e8374f5ff85a9d6dafc7f",
    ),
    ("ja_JP", True): (
        261,
        "f04836f9531d46d6fcbe3998a6f91b48f6c0e440a656b89bc7a238781fc7e96f",
        "870c7f6008e3d09cd73d12505bfa9e119062af7789c67cc7a6008618ab0f3087",
    ),
    ("yo", False): (
        201,
        "544504488e60ae39d2f39a7cbca00fc4f44d80811880650a8e798161411b3f32",
        "c1b899734e4fb802a42bd8dc7fcc41a5caf8eddfed633948ce09a35e5d293577",
    ),
    ("yo", True): (
        251,
        "9c241f5b052a71f75281326db82834103648ce04bc3e24f925a0f38b2695c2e0",
        "8cbedd85266bbce9b50e09dd7c91d3b6f45c7c3f613ae49533384e0ef837baf0",
    ),
}


@pytest.mark.parametrize(("locale", "guarded"), sorted(_GANGS_BEFORE))
def test_availability_does_not_change_ordered_flexible_gangs_or_readings(locale, guarded):
    gang = flexible_detectors(locale, guarded=guarded)
    keys = [detector_key(item) for item in gang.detectors]
    assert all(key[4] is None for key in keys)
    ordered_keys = json.dumps([key[:4] for key in keys])
    readings = json.dumps(detections_to_json(gang.detect(_GANG_TEXT)), ensure_ascii=False)
    assert (
        len(keys),
        hashlib.sha256(ordered_keys.encode()).hexdigest(),
        hashlib.sha256(readings.encode()).hexdigest(),
    ) == _GANGS_BEFORE[(locale, guarded)]


def test_availability_refuses_replaced_material():
    loaded = load_locale_material(FIXTURE)
    forged = replace(loaded, rules=loaded.rules.replace("1: one;", "1: uno;"))
    with pytest.raises(ValueError, match="locale material must come from load_locale_material"):
        availability("qaa", material=[forged])
    # Refused at the boundary, not only where a reader would be built from it.
    with pytest.raises(ValueError, match="locale material must come from load_locale_material"):
        availability("fr", material=[forged])


def test_user_provenance_is_verbatim_and_not_an_icukit_computed_share(tmp_path):
    source = "covers 80% of speakers"
    material = _yo_material(tmp_path, source=source)
    records = [asdict(row) for row in availability("yo", material=[material])]
    user = next(row for row in records if row["source"] == "user")

    assert user["provenance"] == source
    assert [
        (index, key)
        for index, row in enumerate(records)
        for key, value in row.items()
        if value == source
    ] == [(records.index(user), "provenance")]


def test_rows_have_no_measured_share_fields():
    records = [asdict(row) for row in availability("en")]
    expected_keys = set(availability_module.AvailabilityRow.__dataclass_fields__)
    assert records
    assert all(set(record) == expected_keys for record in records)
    assert all("share" not in key for record in records for key in record)
    assert all(
        "measured share" not in value.lower()
        for record in records
        for key, value in record.items()
        if key != "provenance" and isinstance(value, str)
    )


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


def test_cli_json_has_no_measured_share_keys():
    result = _run("yo", "--json")
    assert result.returncode == 0
    expected_keys = set(availability_module.AvailabilityRow.__dataclass_fields__)
    records = [json.loads(line) for line in result.stdout.splitlines()]
    assert records
    assert all(set(record) == expected_keys for record in records)
    assert all("share" not in key for record in records for key in record)
    assert all(
        "measured share" not in value.lower()
        for record in records
        for key, value in record.items()
        if key != "provenance" and isinstance(value, str)
    )
