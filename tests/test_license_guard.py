from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
import xml.etree.ElementTree as ET
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path

import pytest

from tools.provenance import refresh_hashes, validate_repository

ROOT = Path(__file__).parents[1]
DATA_REL = Path("icukit/data")
MANIFEST_REL = DATA_REL / "PROVENANCE.json"


def _read_manifest(root: Path) -> dict:
    return json.loads((root / MANIFEST_REL).read_text(encoding="utf-8"))


def _write_manifest(root: Path, manifest: dict) -> None:
    (root / MANIFEST_REL).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _replace_pyproject(root: Path, old: str, new: str) -> None:
    path = root / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _planted_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "icukit").mkdir(parents=True)
    shutil.copytree(ROOT / DATA_REL, root / DATA_REL)
    shutil.copy2(ROOT / "pyproject.toml", root / "pyproject.toml")
    shutil.copy2(ROOT / "LICENSE", root / "LICENSE")
    return root


def _entry(root: Path, path: str) -> tuple[dict, dict]:
    manifest = _read_manifest(root)
    return manifest, next(item for item in manifest["files"] if item["path"] == path)


def _record_changed_bytes(root: Path, relative: str) -> tuple[dict, dict]:
    manifest, entry = _entry(root, relative)
    entry["sha256"] = hashlib.sha256((root / DATA_REL / relative).read_bytes()).hexdigest()
    return manifest, entry


def _assert_unclassified_corpus_is_rejected(root: Path, relative: str) -> None:
    assert any(
        f"icukit/data/{relative}: content names known internal corpus" in error
        and "without a valid corpus_reference" in error
        for error in _errors(root)
    )


def _plant_share_alike_file(root: Path, artifact_class: str) -> None:
    data_path = root / DATA_REL / "exceptions/planted.json"
    data_path.write_text("{}\n", encoding="utf-8")
    notice = "PLANTED-CC-BY-SA-LICENSE"
    notice_path = root / notice
    notice_path.write_text("Planted CC BY-SA 4.0 test notice.\n", encoding="utf-8")
    manifest = _read_manifest(root)
    manifest["notices"][notice] = {
        "spdx": "cc-by-sa-4.0",
        "sha256": hashlib.sha256(notice_path.read_bytes()).hexdigest(),
    }
    manifest["files"].append(
        {
            "path": "exceptions/planted.json",
            "sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
            "source": "planted CC BY-SA fixture",
            "spdx": "cc-by-sa-4.0",
            "class": artifact_class,
            "notice": notice,
        }
    )
    _replace_pyproject(
        root,
        'license = "BSD-2-Clause AND Unicode-3.0"',
        'license = "BSD-2-Clause AND Unicode-3.0 AND cc-by-sa-4.0"',
    )
    _replace_pyproject(root, '    "LICENSE",\n', f'    "LICENSE",\n    "{notice}",\n')
    _write_manifest(root, manifest)


def _errors(root: Path) -> list[str]:
    return validate_repository(root)


def _wheel_data_members(members: set[str]) -> set[str]:
    return {
        member
        for member in members
        if member.startswith("icukit/data/") and not member.endswith("/")
    }


def _wheel_has_license(members: set[str], notice: str) -> bool:
    return any(
        re.fullmatch(r"[^/]+\.dist-info/licenses/" + re.escape(notice), member)
        for member in members
    )


def _assert_archive_data_agree(
    expected: set[str], wheel_data: set[str], sdist_data: set[str]
) -> None:
    assert wheel_data == expected
    assert sdist_data == expected
    assert sdist_data == wheel_data


def _assert_notice_hash(contents: bytes, expected: str) -> None:
    assert hashlib.sha256(contents).hexdigest() == expected


def _assert_manifest_bytes(contents: bytes, expected: bytes) -> None:
    assert contents == expected


def _assert_distribution_metadata(
    contents: bytes, expected_expression: str, expected_license_files: list[str]
) -> None:
    metadata = BytesParser(policy=policy.default).parsebytes(contents)
    assert metadata["License-Expression"] == expected_expression
    assert metadata.get_all("License-File", []) == expected_license_files


def test_shipped_data_provenance_and_license_metadata_are_valid() -> None:
    assert _errors(ROOT) == []


def test_unknown_class_label_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    entry["class"] = "internal-only"
    _write_manifest(root, manifest)
    assert any("invalid class 'internal-only'" in error for error in _errors(root))


def test_derived_shippable_without_nonempty_term_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    entry["class"] = "derived-shippable"
    entry["term"] = ""
    _write_manifest(root, manifest)
    assert any("derived-shippable requires a nonempty term" in error for error in _errors(root))


def test_share_alike_class_requires_share_alike_spdx(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    entry["class"] = "shippable-share-alike"
    entry["notice"] = "LICENSE"
    _write_manifest(root, manifest)
    assert any("requires a CC-BY-SA-* SPDX id" in error for error in _errors(root))


def test_share_alike_class_requires_notice(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    entry.update({"class": "shippable-share-alike", "spdx": "CC-BY-SA-4.0"})
    manifest["notices"]["LICENSE"]["spdx"] = "CC-BY-SA-4.0"
    _replace_pyproject(
        root,
        'license = "BSD-2-Clause AND Unicode-3.0"',
        'license = "BSD-2-Clause AND Unicode-3.0 AND CC-BY-SA-4.0"',
    )
    _write_manifest(root, manifest)
    assert any("shippable-share-alike requires a notice" in error for error in _errors(root))


def test_shippable_class_rejects_share_alike_spdx(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    entry.update({"spdx": "CC-BY-SA-4.0", "notice": "LICENSE"})
    manifest["notices"]["LICENSE"]["spdx"] = "CC-BY-SA-4.0"
    _replace_pyproject(
        root,
        'license = "BSD-2-Clause AND Unicode-3.0"',
        'license = "BSD-2-Clause AND Unicode-3.0 AND CC-BY-SA-4.0"',
    )
    _write_manifest(root, manifest)
    assert any("shippable must not use a share-alike SPDX id" in error for error in _errors(root))


def test_shippable_class_rejects_lowercase_share_alike_spdx(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    _plant_share_alike_file(root, "shippable")
    assert any("shippable must not use a share-alike SPDX id" in error for error in _errors(root))


def test_share_alike_class_accepts_lowercase_share_alike_spdx(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    _plant_share_alike_file(root, "shippable-share-alike")
    assert _errors(root) == []


def test_removing_only_notice_file_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    notice = "icukit/data/ucd_name_aliases/LICENSE"
    (root / notice).unlink()
    assert f"manifest notice does not exist: {notice}" in _errors(root)


def test_removing_only_license_files_item_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    notice = "LICENSE"
    _replace_pyproject(root, f'    "{notice}",\n', "")
    assert f"manifest notice is absent from license-files: {notice}" in _errors(root)


def test_root_license_is_required_independently_of_entries(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    notice = "icukit/data/abbreviations/BSD-LICENSE"
    shutil.copy2(root / "LICENSE", root / notice)
    _replace_pyproject(
        root,
        '    "LICENSE",\n',
        f'    "{notice}",\n',
    )
    _replace_pyproject(
        root,
        '    "data/abbreviations/*.rng",\n',
        '    "data/abbreviations/*.rng",\n    "data/abbreviations/BSD-LICENSE",\n',
    )
    manifest = _read_manifest(root)
    del manifest["notices"]["LICENSE"]
    manifest["notices"][notice] = {
        "spdx": "BSD-2-Clause",
        "sha256": hashlib.sha256((root / notice).read_bytes()).hexdigest(),
    }
    for entry in manifest["files"]:
        if entry["notice"] is None:
            entry["notice"] = notice
    manifest["files"].append(
        {
            "path": "abbreviations/BSD-LICENSE",
            "sha256": hashlib.sha256((root / notice).read_bytes()).hexdigest(),
            "source": "third-party holder",
            "spdx": "BSD-2-Clause",
            "class": "shippable",
            "notice": notice,
        }
    )
    _write_manifest(root, manifest)
    errors = _errors(root)
    assert "manifest notices must include LICENSE as BSD-2-Clause" in errors
    assert "project license-files must include LICENSE" in errors


def test_missing_notices_table_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest = _read_manifest(root)
    del manifest["notices"]
    _write_manifest(root, manifest)
    assert "icukit/data/PROVENANCE.json: 'notices' must be an object" in _errors(root)


def test_license_files_item_without_notice_mapping_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest = _read_manifest(root)
    del manifest["notices"]["LICENSE"]
    _write_manifest(root, manifest)
    assert "license-files item is absent from manifest notices: LICENSE" in _errors(root)


def test_changed_notice_text_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    (root / "LICENSE").write_text("replacement\n", encoding="utf-8")
    assert "LICENSE: notice sha256 mismatch" in _errors(root)


def test_entry_notice_label_must_match_spdx(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    entry["notice"] = "icukit/data/cldr_symbols/LICENSE"
    _write_manifest(root, manifest)
    assert any("is labeled Unicode-3.0, not BSD-2-Clause" in error for error in _errors(root))


def test_bsd_entry_may_use_its_own_bsd_notice(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    notice = "icukit/data/abbreviations/BSD-LICENSE"
    shutil.copy2(root / "LICENSE", root / notice)
    _replace_pyproject(root, '    "LICENSE",\n', f'    "LICENSE",\n    "{notice}",\n')
    _replace_pyproject(
        root,
        '    "data/abbreviations/*.rng",\n',
        '    "data/abbreviations/*.rng",\n    "data/abbreviations/BSD-LICENSE",\n',
    )
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    manifest["notices"][notice] = {
        "spdx": "BSD-2-Clause",
        "sha256": hashlib.sha256((root / notice).read_bytes()).hexdigest(),
    }
    entry["notice"] = notice
    manifest["files"].append(
        {
            "path": "abbreviations/BSD-LICENSE",
            "sha256": hashlib.sha256((root / notice).read_bytes()).hexdigest(),
            "source": "third-party holder",
            "spdx": "BSD-2-Clause",
            "class": "shippable",
            "notice": notice,
        }
    )
    _write_manifest(root, manifest)
    assert _errors(root) == []


def test_missing_bsd_expression_term_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    _replace_pyproject(root, "BSD-2-Clause AND Unicode-3.0", "Unicode-3.0")
    assert "SPDX id is absent from project license expression: BSD-2-Clause" in _errors(root)


def test_unused_expression_term_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    _replace_pyproject(root, "BSD-2-Clause AND Unicode-3.0", "BSD-2-Clause AND Unicode-3.0 AND MIT")
    assert "project license term has no provenance use: MIT" in _errors(root)


def test_notice_spdx_must_occur_in_expression(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    notice = "EXTRA-LICENSE"
    shutil.copy2(root / "LICENSE", root / notice)
    manifest = _read_manifest(root)
    manifest["notices"][notice] = {
        "spdx": "MIT",
        "sha256": hashlib.sha256((root / notice).read_bytes()).hexdigest(),
    }
    _replace_pyproject(root, '    "LICENSE",\n', f'    "LICENSE",\n    "{notice}",\n')
    _write_manifest(root, manifest)
    assert "SPDX id is absent from project license expression: MIT" in _errors(root)


@pytest.mark.parametrize(
    "expression",
    [
        "BSD-2-Clause OR Unicode-3.0",
        "(BSD-2-Clause OR Unicode-3.0)",
        "BSD-2-Clause WITH LLVM-exception",
        "BSD-2-Clause AND (Unicode-3.0 WITH LLVM-exception)",
    ],
)
def test_non_conjunction_license_expression_is_rejected(tmp_path: Path, expression: str) -> None:
    root = _planted_tree(tmp_path)
    _replace_pyproject(root, "BSD-2-Clause AND Unicode-3.0", expression)
    assert "project license expression must be an AND-only conjunction" in _errors(root)


@pytest.mark.parametrize(
    "expression",
    [
        "(BSD-2-Clause AND Unicode-3.0)",
        "BSD-2-Clause AND (Unicode-3.0)",
        "((BSD-2-Clause) AND (Unicode-3.0))",
        "bsd-2-clause AND unicode-3.0",
        "BSD-2-Clause AND LicenseRef-OR-internal AND Unicode-3.0",
    ],
)
def test_supported_license_expression_spellings_are_accepted(
    tmp_path: Path, expression: str
) -> None:
    root = _planted_tree(tmp_path)
    _replace_pyproject(root, "BSD-2-Clause AND Unicode-3.0", expression)
    if "LicenseRef" in expression:
        manifest = _read_manifest(root)
        notice = "LICENSE-OR-internal"
        shutil.copy2(root / "LICENSE", root / notice)
        manifest["notices"][notice] = {
            "spdx": "LicenseRef-OR-internal",
            "sha256": hashlib.sha256((root / notice).read_bytes()).hexdigest(),
        }
        _replace_pyproject(root, '    "LICENSE",\n', f'    "LICENSE",\n    "{notice}",\n')
        _write_manifest(root, manifest)
    assert _errors(root) == []


def test_duplicate_expression_term_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    _replace_pyproject(
        root,
        "BSD-2-Clause AND Unicode-3.0",
        "BSD-2-Clause AND Unicode-3.0 AND BSD-2-Clause",
    )
    assert "project license expression contains duplicate terms" in _errors(root)


def test_duplicate_entry_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    manifest["files"].append(entry.copy())
    _write_manifest(root, manifest)
    assert any("duplicate provenance entry:" in error for error in _errors(root))


@pytest.mark.parametrize("unsafe", ["../LICENSE", "/tmp/LICENSE", "foo/../LICENSE"])
def test_unsafe_entry_path_is_rejected(tmp_path: Path, unsafe: str) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    entry["path"] = unsafe
    _write_manifest(root, manifest)
    assert any("unsafe or noncanonical path" in error for error in _errors(root))


def test_invalid_manifest_json_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    (root / MANIFEST_REL).write_text("{", encoding="utf-8")
    assert any("cannot read icukit/data/PROVENANCE.json" in error for error in _errors(root))


def test_non_object_manifest_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    (root / MANIFEST_REL).write_text("[]\n", encoding="utf-8")
    assert "icukit/data/PROVENANCE.json: manifest must be an object" in _errors(root)


def test_non_array_files_table_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest = _read_manifest(root)
    manifest["files"] = {}
    _write_manifest(root, manifest)
    assert "icukit/data/PROVENANCE.json: 'files' must be an array" in _errors(root)


def test_malformed_entry_is_rejected_by_validation(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest = _read_manifest(root)
    manifest["files"].append({"source": "broken"})
    _write_manifest(root, manifest)
    assert any("must be an object with a string path" in error for error in _errors(root))


@pytest.mark.parametrize("version", [None, 2])
def test_missing_or_unsupported_schema_version_is_rejected(
    tmp_path: Path, version: int | None
) -> None:
    root = _planted_tree(tmp_path)
    manifest = _read_manifest(root)
    if version is None:
        del manifest["schema_version"]
    else:
        manifest["schema_version"] = version
    _write_manifest(root, manifest)
    assert any("unsupported schema_version" in error for error in _errors(root))


def test_unknown_manifest_key_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest = _read_manifest(root)
    manifest["typo"] = True
    _write_manifest(root, manifest)
    assert "manifest has unknown keys: typo" in _errors(root)


def test_unknown_entry_key_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    entry["clas"] = entry["class"]
    _write_manifest(root, manifest)
    assert any("unknown entry keys: clas" in error for error in _errors(root))


def test_missing_entry_key_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    del entry["source"]
    _write_manifest(root, manifest)
    assert any("missing entry keys: source" in error for error in _errors(root))


def test_malformed_entry_is_reported_by_refresh_instead_of_crashing(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest = _read_manifest(root)
    manifest["files"].append({"source": "broken"})
    _write_manifest(root, manifest)
    assert any("must be an object with a string path" in error for error in refresh_hashes(root))


def test_notice_mapping_requires_safe_path(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest = _read_manifest(root)
    manifest["notices"]["../LICENSE"] = {
        "spdx": "BSD-2-Clause",
        "sha256": "0" * 64,
    }
    _write_manifest(root, manifest)
    assert any("unsafe or noncanonical notice path" in error for error in _errors(root))


def test_notice_mapping_requires_spdx(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest = _read_manifest(root)
    manifest["notices"]["LICENSE"]["spdx"] = ""
    _write_manifest(root, manifest)
    assert "LICENSE: notice SPDX id must be a nonempty string" in _errors(root)


@pytest.mark.parametrize("field", ["source", "spdx"])
def test_entry_requires_nonempty_declared_metadata(tmp_path: Path, field: str) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    entry[field] = ""
    _write_manifest(root, manifest)
    assert any(f"{field} must be a nonempty string" in error for error in _errors(root))


def test_entry_requires_valid_notice_value(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    entry["notice"] = 3
    _write_manifest(root, manifest)
    assert any(
        "notice must be a repository-relative path or null" in error for error in _errors(root)
    )


def test_entry_notice_must_be_in_notice_table(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    entry["notice"] = "MISSING-LICENSE"
    _write_manifest(root, manifest)
    assert any(
        "notice is absent from manifest notices: MISSING-LICENSE" in error
        for error in _errors(root)
    )


def test_entry_notice_path_must_be_safe(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    entry["notice"] = "../LICENSE"
    _write_manifest(root, manifest)
    assert any(
        "unsafe or noncanonical notice path '../LICENSE'" in error for error in _errors(root)
    )


def test_license_files_must_be_an_array_of_strings(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    _replace_pyproject(
        root,
        "license-files = [\n"
        '    "LICENSE",\n'
        '    "icukit/data/cldr_symbols/LICENSE",\n'
        '    "icukit/data/ucd_name_aliases/LICENSE",\n'
        "]",
        'license-files = "invalid"',
    )
    assert "project license-files must be an array of strings" in _errors(root)


def test_license_files_glob_is_rejected_clearly(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    _replace_pyproject(
        root,
        '    "icukit/data/cldr_symbols/LICENSE",\n',
        '    "icukit/data/*/LICENSE",\n',
    )
    assert (
        "project license-files item must be a literal path, not a glob: icukit/data/*/LICENSE"
    ) in _errors(root)


def test_empty_license_expression_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    _replace_pyproject(root, 'license = "BSD-2-Clause AND Unicode-3.0"', 'license = ""')
    assert "project license expression must be a nonempty string" in _errors(root)


def test_wrong_hash_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    entry["sha256"] = "0" * 64
    changed = entry["path"]
    _write_manifest(root, manifest)
    assert f"{changed}: sha256 mismatch" in _errors(root)


def test_orphan_packaged_artifact_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    path = root / DATA_REL / "exceptions/unrecorded.json"
    path.write_text("{}\n", encoding="utf-8")
    assert "missing provenance entry: exceptions/unrecorded.json" in _errors(root)


def test_orphan_entry_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    orphan = entry.copy()
    orphan["path"] = "abbreviations/missing.xml"
    manifest["files"].append(orphan)
    _write_manifest(root, manifest)
    assert "orphan provenance entry: abbreviations/missing.xml" in _errors(root)


def test_non_shipping_data_file_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    (root / DATA_REL / "silently-omitted.txt").write_text("data\n", encoding="utf-8")
    assert "data file is not selected by package-data: silently-omitted.txt" in _errors(root)


def test_package_data_outside_data_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    _replace_pyproject(root, '    "py.typed",\n', '    "py.typed",\n    "resources/*.tsv",\n')
    assert any(
        "package-data pattern outside data/ is not allowed" in error for error in _errors(root)
    )


def test_single_star_is_anchored_and_does_not_cross_segments(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    _replace_pyproject(
        root, '    "data/exceptions/*.json",\n', '    "data/exceptions/*.json",\n    "data/*",\n'
    )
    nested = root / DATA_REL / "data/planted.txt"
    nested.parent.mkdir()
    nested.write_text("value\n", encoding="utf-8")
    assert "data file is not selected by package-data: data/planted.txt" in _errors(root)


def test_double_star_selects_zero_or_more_segments(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    _replace_pyproject(
        root,
        '    "data/cldr_symbols/*.tsv",\n',
        '    "data/cldr_symbols/**/*.tsv",\n',
    )
    nested = root / DATA_REL / "cldr_symbols/nested/planted.tsv"
    nested.parent.mkdir()
    nested.write_text("value\n", encoding="utf-8")
    manifest, template = _entry(root, "cldr_symbols/af.tsv")
    planted = template.copy()
    planted.update(
        {
            "path": "cldr_symbols/nested/planted.tsv",
            "sha256": hashlib.sha256(nested.read_bytes()).hexdigest(),
        }
    )
    manifest["files"].append(planted)
    _write_manifest(root, manifest)
    assert _errors(root) == []


def test_dotfiles_and_pycache_are_ignored_local_state(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    (root / DATA_REL / ".DS_Store").write_bytes(b"local")
    cache = root / DATA_REL / "__pycache__"
    cache.mkdir()
    (cache / "local.pyc").write_bytes(b"local")
    assert _errors(root) == []


def test_other_dotfile_is_not_selected_by_package_data_star(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    (root / DATA_REL / "exceptions/.planted.json").write_text("{}\n", encoding="utf-8")
    assert _errors(root) == ["data file is not selected by package-data: exceptions/.planted.json"]


def test_only_top_level_provenance_manifest_is_excluded(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    nested = root / DATA_REL / "exceptions/PROVENANCE.json"
    nested.write_text("{}\n", encoding="utf-8")
    manifest, entry = _entry(root, "abbreviations/abbreviations.rng")
    planted = entry.copy()
    planted.update(
        {
            "path": "exceptions/PROVENANCE.json",
            "sha256": hashlib.sha256(nested.read_bytes()).hexdigest(),
        }
    )
    manifest["files"].append(planted)
    _write_manifest(root, manifest)
    assert _errors(root) == []


def test_internal_corpus_in_json_key_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    path = root / DATA_REL / "exceptions/examples-en.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["EN_WITH_TYPES"] = "planted key"
    path.write_text(json.dumps(document), encoding="utf-8")
    manifest, _ = _record_changed_bytes(root, "exceptions/examples-en.json")
    _write_manifest(root, manifest)
    _assert_unclassified_corpus_is_rejected(root, "exceptions/examples-en.json")


def test_internal_corpus_in_nested_json_value_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    path = root / DATA_REL / "exceptions/examples-en.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["planted"] = {"anything": [{"nested": "Sproat corpus"}]}
    path.write_text(json.dumps(document), encoding="utf-8")
    manifest, _ = _record_changed_bytes(root, "exceptions/examples-en.json")
    _write_manifest(root, manifest)
    _assert_unclassified_corpus_is_rejected(root, "exceptions/examples-en.json")


def test_internal_corpus_in_uppercase_json_suffix_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    _replace_pyproject(
        root,
        '    "data/exceptions/*.json",\n',
        '    "data/exceptions/*.json",\n    "data/exceptions/*.JSON",\n',
    )
    path = root / DATA_REL / "exceptions/planted.JSON"
    path.write_text('{"anything": "en_with_types"}\n', encoding="utf-8")
    manifest, template = _entry(root, "exceptions/examples-en.json")
    planted = template.copy()
    planted.update(
        {
            "path": "exceptions/planted.JSON",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
    manifest["files"].append(planted)
    _write_manifest(root, manifest)
    _assert_unclassified_corpus_is_rejected(root, "exceptions/planted.JSON")


def test_duplicate_source_in_manifest_entry_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    path = root / MANIFEST_REL
    text = path.read_text(encoding="utf-8")
    original = '      "source": "curated by hand",'
    duplicate = '      "source": "en_with_types",\n' + original
    assert original in text
    path.write_text(text.replace(original, duplicate, 1), encoding="utf-8")
    assert "icukit/data/PROVENANCE.json: duplicate JSON key 'source'" in _errors(root)


def test_duplicate_source_in_shipped_json_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    path = root / DATA_REL / "exceptions/examples-en.json"
    text = path.read_text(encoding="utf-8")
    original = '  "schema_version": 1,'
    duplicate = original + '\n  "source": "en_with_types",\n  "source": "curated by hand",'
    assert original in text
    path.write_text(text.replace(original, duplicate, 1), encoding="utf-8")
    manifest = _read_manifest(root)
    entry = next(
        item for item in manifest["files"] if item["path"] == "exceptions/examples-en.json"
    )
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _write_manifest(root, manifest)
    assert "icukit/data/exceptions/examples-en.json: duplicate JSON key 'source'" in _errors(root)


def test_internal_corpus_in_source_url_attribute_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    path = root / DATA_REL / "abbreviations/en.xml"
    tree = ET.parse(path)
    tree.getroot().set("source_url", "en_with_types census")
    tree.write(path, encoding="utf-8", xml_declaration=True)
    manifest, _ = _record_changed_bytes(root, "abbreviations/en.xml")
    _write_manifest(root, manifest)
    _assert_unclassified_corpus_is_rejected(root, "abbreviations/en.xml")


def test_internal_corpus_in_tsv_comment_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    relative = "cldr_symbols/af.tsv"
    path = root / DATA_REL / relative
    path.write_text(path.read_text(encoding="utf-8") + "# en_with_types census\n", encoding="utf-8")
    manifest, _ = _record_changed_bytes(root, relative)
    _write_manifest(root, manifest)
    _assert_unclassified_corpus_is_rejected(root, relative)


def test_internal_corpus_in_non_utf8_file_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    relative = "cldr_symbols/af.tsv"
    path = root / DATA_REL / relative
    path.write_bytes(path.read_bytes() + b"\xff EN_WITH_TYPES\n")
    manifest, _ = _record_changed_bytes(root, relative)
    _write_manifest(root, manifest)
    _assert_unclassified_corpus_is_rejected(root, relative)


def test_reviewed_corpus_mention_is_accepted(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    relative = "abbreviations/en.xml"
    path = root / DATA_REL / relative
    path.write_text(
        path.read_text(encoding="utf-8") + "\n<!-- measured against en_with_types -->\n",
        encoding="utf-8",
    )
    manifest, entry = _record_changed_bytes(root, relative)
    entry["corpus_reference"] = {
        "kind": "mention",
        "note": "the comment records measurement context, not the file's source",
    }
    _write_manifest(root, manifest)
    assert _errors(root) == []


def test_derived_corpus_reference_on_non_share_alike_class_is_rejected(
    tmp_path: Path,
) -> None:
    root = _planted_tree(tmp_path)
    path = root / DATA_REL / "abbreviations/en.xml"
    path.write_text(
        path.read_text(encoding="utf-8") + "\n<!-- derived from en_with_types -->\n",
        encoding="utf-8",
    )
    manifest, entry = _record_changed_bytes(root, "abbreviations/en.xml")
    entry["corpus_reference"] = {"kind": "derived"}
    _write_manifest(root, manifest)
    assert any(
        "derived corpus_reference requires class shippable-share-alike" in error
        for error in _errors(root)
    )


def test_invalid_shipped_json_is_rejected(tmp_path: Path) -> None:
    root = _planted_tree(tmp_path)
    path = root / DATA_REL / "exceptions/examples-en.json"
    path.write_text("{", encoding="utf-8")
    manifest = _read_manifest(root)
    entry = next(
        item for item in manifest["files"] if item["path"] == "exceptions/examples-en.json"
    )
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _write_manifest(root, manifest)
    assert any(
        "icukit/data/exceptions/examples-en.json: invalid JSON" in error for error in _errors(root)
    )


def test_wheel_data_universe_is_every_file_below_data() -> None:
    members = {
        "icukit/module.py",
        "icukit/data/",
        "icukit/data/planted.py",
        "icukit/data/nested/planted.tsv",
    }
    assert _wheel_data_members(members) == {
        "icukit/data/planted.py",
        "icukit/data/nested/planted.tsv",
    }


def test_wheel_license_must_be_in_dist_info_license_directory() -> None:
    assert not _wheel_has_license({"icukit/data/licenses/LICENSE"}, "LICENSE")
    assert _wheel_has_license({"icukit-1.0.dist-info/licenses/LICENSE"}, "LICENSE")


def test_archive_data_agreement_rejects_extra_sdist_member() -> None:
    expected = {"icukit/data/PROVENANCE.json"}
    with pytest.raises(AssertionError):
        _assert_archive_data_agree(
            expected,
            expected,
            expected | {"icukit/data/unrecorded.tsv"},
        )


def test_archive_notice_hash_rejects_changed_bytes() -> None:
    with pytest.raises(AssertionError):
        _assert_notice_hash(b"changed", hashlib.sha256(b"expected").hexdigest())


def test_archive_manifest_rejects_changed_bytes() -> None:
    with pytest.raises(AssertionError):
        _assert_manifest_bytes(b"changed", b"expected")


@pytest.mark.parametrize(
    "metadata",
    [
        b"Metadata-Version: 2.4\nLicense-Expression: BSD-2-Clause\n"
        b"License-File: LICENSE\nLicense-File: THIRD-PARTY\n\n",
        b"Metadata-Version: 2.4\nLicense-Expression: BSD-2-Clause AND Unicode-3.0\n"
        b"License-File: LICENSE\n\n",
    ],
)
def test_distribution_metadata_must_match_source(metadata: bytes) -> None:
    with pytest.raises(AssertionError):
        _assert_distribution_metadata(
            metadata,
            "BSD-2-Clause AND Unicode-3.0",
            ["LICENSE", "THIRD-PARTY"],
        )


def test_wheel_and_sdist_match_and_hash_manifest_data(tmp_path: Path) -> None:
    output = tmp_path / "dist"
    if importlib.util.find_spec("build") is not None:
        command = [sys.executable, "-m", "build", "--outdir", str(output)]
    elif uv := shutil.which("uv"):
        command = [uv, "build", "--out-dir", str(output)]
    elif os.environ.get("CI"):
        pytest.fail("CI requires python-build or uv to build both distributions")
    else:
        pytest.skip("neither python-build nor uv is available to build both distributions")
    subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)

    wheels = list(output.glob("*.whl"))
    sdists = list(output.glob("*.tar.gz"))
    assert len(wheels) == 1
    assert len(sdists) == 1
    manifest = _read_manifest(ROOT)
    manifest_bytes = (ROOT / MANIFEST_REL).read_bytes()
    entries = {entry["path"]: entry for entry in manifest["files"]}
    expected_data = {f"icukit/data/{path}" for path in entries} | {"icukit/data/PROVENANCE.json"}
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    expected_expression = project["license"]
    expected_license_files = project["license-files"]

    with zipfile.ZipFile(wheels[0]) as archive:
        members = set(archive.namelist())
        wheel_data = _wheel_data_members(members)
        metadata_member = next(
            member for member in members if re.fullmatch(r"[^/]+\.dist-info/METADATA", member)
        )
        _assert_distribution_metadata(
            archive.read(metadata_member), expected_expression, expected_license_files
        )
        for relative, entry in entries.items():
            assert (
                hashlib.sha256(archive.read(f"icukit/data/{relative}")).hexdigest()
                == entry["sha256"]
            )
        _assert_manifest_bytes(archive.read(MANIFEST_REL.as_posix()), manifest_bytes)
        for notice, record in manifest["notices"].items():
            assert _wheel_has_license(members, notice), notice
            member = next(
                member
                for member in members
                if re.fullmatch(r"[^/]+\.dist-info/licenses/" + re.escape(notice), member)
            )
            _assert_notice_hash(archive.read(member), record["sha256"])

    with tarfile.open(sdists[0]) as archive:
        members = set(archive.getnames())
        top = next(iter(members)).split("/", 1)[0]
        sdist_data = {
            member.removeprefix(f"{top}/")
            for member in members
            if member.startswith(f"{top}/icukit/data/") and archive.getmember(member).isfile()
        }
        _assert_archive_data_agree(expected_data, wheel_data, sdist_data)
        pkg_info = archive.extractfile(f"{top}/PKG-INFO")
        assert pkg_info is not None
        _assert_distribution_metadata(pkg_info.read(), expected_expression, expected_license_files)
        for relative, entry in entries.items():
            member = f"{top}/icukit/data/{relative}"
            extracted = archive.extractfile(member)
            assert extracted is not None
            assert hashlib.sha256(extracted.read()).hexdigest() == entry["sha256"]
        manifest_member = archive.extractfile(f"{top}/{MANIFEST_REL.as_posix()}")
        assert manifest_member is not None
        _assert_manifest_bytes(manifest_member.read(), manifest_bytes)
        for notice, record in manifest["notices"].items():
            member = f"{top}/{notice}"
            assert member in members
            extracted = archive.extractfile(member)
            assert extracted is not None
            _assert_notice_hash(extracted.read(), record["sha256"])
