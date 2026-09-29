#!/usr/bin/env python3
"""Maintain and validate the provenance manifest for data under ``icukit/data``.

The ``project.license-files`` entries are deliberately restricted to literal,
repository-relative paths. Although packaging metadata permits globs, this guard
refuses them so every shipped notice has one unambiguous manifest record. Refreshing
hashes acknowledges only that bytes changed: provenance must be re-reviewed first.
TSV and XML comments are content rather than declarations and are not scanned.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import sys
import tomllib
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import Any

DATA_REL = Path("icukit/data")
MANIFEST_NAME = "PROVENANCE.json"
SCHEMA_VERSION = 1
ALLOWED_CLASSES = frozenset({"shippable", "shippable-share-alike", "derived-shippable"})
REQUIRED_ENTRY_KEYS = frozenset({"path", "sha256", "source", "spdx", "class", "notice"})
OPTIONAL_ENTRY_KEYS = frozenset({"term", "note"})
PROVENANCE_KEYS = frozenset(
    {
        "source",
        "sources",
        "corpus",
        "origin",
        "dataset",
        "provenance",
        "derived_from",
        "data_source",
    }
)
CORPUS_IDS = (
    "google/tn-",
    "en_with_types",
    "tn-corpus",
    "sproat",
    "kaggle",
    "en_train",
    "text normalization",
)
SPDX_TERM = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]*")
SHARE_ALIKE = re.compile(r"CC-BY-SA-.+", re.IGNORECASE)
LICENSE_TITLES = {
    "bsd-2-clause": "BSD 2-Clause License",
    "cc-by-sa-4.0": "Attribution-ShareAlike 4.0 International",
    "unicode-3.0": "UNICODE LICENSE V3",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _DuplicateJSONKeyError(ValueError):
    pass


def _read_json(path: Path, display_path: Path) -> Any:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, child in pairs:
            if key in value:
                raise _DuplicateJSONKeyError(f"{display_path}: duplicate JSON key {key!r}")
            value[key] = child
        return value

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)


def _safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and path.as_posix() == value


def _read_project(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        document = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        project = document["project"]
        patterns = document["tool"]["setuptools"]["package-data"]["icukit"]
        if not isinstance(patterns, list) or not all(isinstance(item, str) for item in patterns):
            raise TypeError("tool.setuptools.package-data.icukit must be an array of strings")
        return {"project": project, "patterns": patterns}, []
    except (OSError, KeyError, tomllib.TOMLDecodeError, TypeError) as error:
        return None, [f"cannot read project packaging metadata: {error}"]


def _is_ignored_local_path(relative: PurePosixPath) -> bool:
    return (
        ".DS_Store" in relative.parts
        or "__pycache__" in relative.parts
        or relative.suffix == ".pyc"
    )


def _setuptools_match(path: str, pattern: str) -> bool:
    """Match setuptools' anchored globbing, including its leading-dot rule."""
    path_parts = path.split("/")
    pattern_parts = pattern.split("/")

    def match(path_index: int, pattern_index: int) -> bool:
        if pattern_index == len(pattern_parts):
            return path_index == len(path_parts)
        pattern_part = pattern_parts[pattern_index]
        if pattern_part == "**":
            return match(path_index, pattern_index + 1) or (
                path_index < len(path_parts)
                and not path_parts[path_index].startswith(".")
                and match(path_index + 1, pattern_index)
            )
        return (
            path_index < len(path_parts)
            and (not path_parts[path_index].startswith(".") or pattern_part.startswith("."))
            and fnmatch.fnmatchcase(path_parts[path_index], pattern_part)
            and match(path_index + 1, pattern_index + 1)
        )

    return match(0, 0)


def _package_data_paths(root: Path, patterns: list[str]) -> tuple[set[str], list[str]]:
    """Return selected and unselected manifest-relative files under ``icukit/data``."""
    data = root / DATA_REL
    data_patterns = [pattern for pattern in patterns if pattern.startswith("data/")]
    selected: set[str] = set()
    unselected: list[str] = []
    for path in data.rglob("*"):
        if not path.is_file():
            continue
        relative = PurePosixPath(path.relative_to(data).as_posix())
        if _is_ignored_local_path(relative):
            continue
        package_relative = f"data/{relative.as_posix()}"
        if any(_setuptools_match(package_relative, pattern) for pattern in data_patterns):
            if relative.as_posix() != MANIFEST_NAME:
                selected.add(relative.as_posix())
        else:
            unselected.append(relative.as_posix())
    return selected, sorted(unselected)


def _load_manifest(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    path = root / DATA_REL / MANIFEST_NAME
    try:
        manifest = _read_json(path, DATA_REL / MANIFEST_NAME)
    except _DuplicateJSONKeyError as error:
        return None, [str(error)]
    except (OSError, json.JSONDecodeError) as error:
        return None, [f"cannot read {DATA_REL / MANIFEST_NAME}: {error}"]
    if not isinstance(manifest, dict):
        return None, [f"{DATA_REL / MANIFEST_NAME}: manifest must be an object"]
    errors: list[str] = []
    unknown = set(manifest) - {"schema_version", "notices", "files"}
    if unknown:
        errors.append(f"manifest has unknown keys: {', '.join(sorted(unknown))}")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"unsupported schema_version: {manifest.get('schema_version')!r}; "
            f"expected {SCHEMA_VERSION}"
        )
    if not isinstance(manifest.get("notices"), dict):
        errors.append(f"{DATA_REL / MANIFEST_NAME}: 'notices' must be an object")
    if not isinstance(manifest.get("files"), list):
        errors.append(f"{DATA_REL / MANIFEST_NAME}: 'files' must be an array")
    if errors:
        return None, errors
    return manifest, []


def _strings_below(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _strings_below(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings_below(child)


def _declared_provenance_strings(
    value: Any, keys: tuple[str, ...] = ()
) -> Iterator[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_keys = (*keys, str(key))
            if str(key).casefold() in PROVENANCE_KEYS:
                for string in _strings_below(child):
                    yield ".".join(child_keys), string
            else:
                yield from _declared_provenance_strings(child, child_keys)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _declared_provenance_strings(child, (*keys, str(index)))


def _license_terms(expression: Any) -> tuple[dict[str, str], str | None]:
    if not isinstance(expression, str) or not expression.strip():
        return {}, "project license expression must be a nonempty string"
    expression = expression.strip()
    tokens = re.findall(r"[()]|[A-Za-z0-9][A-Za-z0-9.-]*", expression)
    if "".join(tokens) != re.sub(r"\s+", "", expression):
        return {}, "project license expression must be an AND-only conjunction"

    terms: list[str] = []
    position = 0

    def parse_group() -> bool:
        nonlocal position
        if position >= len(tokens):
            return False
        if tokens[position] == "(":
            position += 1
            if not parse_conjunction() or position >= len(tokens) or tokens[position] != ")":
                return False
            position += 1
            return True
        term = tokens[position]
        if not SPDX_TERM.fullmatch(term) or term in {"AND", "OR", "WITH"}:
            return False
        terms.append(term)
        position += 1
        return True

    def parse_conjunction() -> bool:
        nonlocal position
        if not parse_group():
            return False
        while position < len(tokens) and tokens[position] == "AND":
            position += 1
            if not parse_group():
                return False
        return True

    if not parse_conjunction() or position != len(tokens):
        return {}, "project license expression must be an AND-only conjunction"
    folded = {term.casefold(): term for term in terms}
    if len(terms) != len(folded):
        return folded, "project license expression contains duplicate terms"
    return folded, None


def _corpus_error(source: str) -> bool:
    lowered = source.casefold()
    return any(corpus_id in lowered for corpus_id in CORPUS_IDS)


def _share_alike_corpus_allowed(
    entry: dict[str, Any] | None, notices: dict[str, dict[str, str]]
) -> bool:
    """Whether a hash-pinned CC BY-SA artifact has attribution and legal code."""
    if entry is None or entry.get("class") != "shippable-share-alike":
        return False
    spdx = entry.get("spdx")
    attribution = entry.get("notice")
    legal_code = (
        str(PurePosixPath(attribution).with_name("LICENSE"))
        if isinstance(attribution, str)
        else None
    )
    return (
        isinstance(spdx, str)
        and SHARE_ALIKE.fullmatch(spdx) is not None
        and isinstance(attribution, str)
        and PurePosixPath(attribution).name == "NOTICE"
        and attribution in notices
        and legal_code in notices
        and notices[attribution]["spdx"].casefold() == spdx.casefold()
        and notices[legal_code]["spdx"].casefold() == spdx.casefold()
    )


def validate_repository(root: Path) -> list[str]:
    """Return every provenance or licensing error below a repository root."""
    root = root.resolve()
    manifest, errors = _load_manifest(root)
    if manifest is None:
        return errors
    metadata, metadata_errors = _read_project(root)
    errors.extend(metadata_errors)
    if metadata is None:
        return errors

    for pattern in metadata["patterns"]:
        if pattern != "py.typed" and not pattern.startswith("data/"):
            errors.append(
                "package-data pattern outside data/ is not allowed (extend the guard before "
                f"shipping it): {pattern}"
            )

    entries: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(manifest["files"]):
        label = f"manifest entry {index}"
        if not isinstance(raw, dict) or not isinstance(raw.get("path"), str):
            errors.append(f"{label}: must be an object with a string path")
            continue
        path = raw["path"]
        if not _safe_relative_path(path):
            errors.append(f"{label}: unsafe or noncanonical path {path!r}")
            continue
        if path in entries:
            errors.append(f"duplicate provenance entry: {path}")
            continue
        entries[path] = raw
        unknown = set(raw) - REQUIRED_ENTRY_KEYS - OPTIONAL_ENTRY_KEYS
        missing = REQUIRED_ENTRY_KEYS - set(raw)
        if unknown:
            errors.append(f"{path}: unknown entry keys: {', '.join(sorted(unknown))}")
        if missing:
            errors.append(f"{path}: missing entry keys: {', '.join(sorted(missing))}")

    actual, unselected = _package_data_paths(root, metadata["patterns"])
    for path in unselected:
        errors.append(f"data file is not selected by package-data: {path}")
    recorded = set(entries)
    for path in sorted(actual - recorded):
        errors.append(f"missing provenance entry: {path}")
    for path in sorted(recorded - actual):
        errors.append(f"orphan provenance entry: {path}")

    raw_notices: dict[Any, Any] = manifest["notices"]
    notices: dict[str, dict[str, str]] = {}
    for notice, record in raw_notices.items():
        if not isinstance(notice, str) or not _safe_relative_path(notice):
            errors.append(f"unsafe or noncanonical notice path: {notice!r}")
            continue
        if not isinstance(record, dict) or set(record) != {"spdx", "sha256"}:
            errors.append(f"{notice}: notice record must contain exactly spdx and sha256")
            continue
        spdx = record.get("spdx")
        digest = record.get("sha256")
        if not isinstance(spdx, str) or not spdx.strip():
            errors.append(f"{notice}: notice SPDX id must be a nonempty string")
            continue
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append(f"{notice}: notice sha256 must be 64 lowercase hexadecimal characters")
            continue
        notices[notice] = {"spdx": spdx, "sha256": digest}

    if "LICENSE" not in notices or notices["LICENSE"]["spdx"].casefold() != "bsd-2-clause":
        errors.append("manifest notices must include LICENSE as BSD-2-Clause")

    used_spdx: set[str] = {"BSD-2-Clause"}
    for relative, entry in sorted(entries.items()):
        data_path = root / DATA_REL / relative
        artifact_class = entry.get("class")
        spdx = entry.get("spdx")
        notice = entry.get("notice")
        source = entry.get("source")
        if artifact_class not in ALLOWED_CLASSES:
            errors.append(f"{relative}: invalid class {artifact_class!r}")
        if artifact_class == "derived-shippable" and (
            not isinstance(entry.get("term"), str) or not entry["term"].strip()
        ):
            errors.append(f"{relative}: derived-shippable requires a nonempty term")
        if artifact_class == "shippable-share-alike":
            if not isinstance(spdx, str) or not SHARE_ALIKE.fullmatch(spdx):
                errors.append(f"{relative}: shippable-share-alike requires a CC-BY-SA-* SPDX id")
            if not isinstance(notice, str) or not notice:
                errors.append(f"{relative}: shippable-share-alike requires a notice")
            elif not _share_alike_corpus_allowed(entry, notices):
                errors.append(
                    f"{relative}: shippable-share-alike requires a hashed attribution NOTICE "
                    "and sibling LICENSE with matching SPDX ids"
                )
        if artifact_class == "shippable" and isinstance(spdx, str) and SHARE_ALIKE.fullmatch(spdx):
            errors.append(f"{relative}: shippable must not use a share-alike SPDX id")
        for field in ("source", "spdx"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                errors.append(f"{relative}: {field} must be a nonempty string")
        if isinstance(spdx, str) and spdx.strip():
            used_spdx.add(spdx)
        for field in ("source", "note", "term"):
            for declaration in _strings_below(entry.get(field)):
                if _corpus_error(declaration) and not _share_alike_corpus_allowed(entry, notices):
                    errors.append(
                        f"{relative}:{field}: declared provenance names known internal corpus "
                        f"{declaration!r}"
                    )
        if "notice" not in entry or (notice is not None and not isinstance(notice, str)):
            errors.append(f"{relative}: notice must be a repository-relative path or null")
        else:
            effective_notice = "LICENSE" if notice is None else notice
            if isinstance(effective_notice, str) and not _safe_relative_path(effective_notice):
                errors.append(
                    f"{relative}: unsafe or noncanonical notice path {effective_notice!r}"
                )
            elif effective_notice not in notices:
                errors.append(
                    f"{relative}: notice is absent from manifest notices: {effective_notice}"
                )
            elif notices[effective_notice]["spdx"].casefold() != str(spdx).casefold():
                errors.append(
                    f"{relative}: notice {effective_notice} is labeled "
                    f"{notices[effective_notice]['spdx']}, "
                    f"not {spdx}"
                )
        if data_path.is_file() and entry.get("sha256") != _sha256(data_path):
            errors.append(f"{relative}: sha256 mismatch")

    project = metadata["project"]
    license_files_value = project.get("license-files")
    if not isinstance(license_files_value, list) or not all(
        isinstance(item, str) for item in license_files_value
    ):
        errors.append("project license-files must be an array of strings")
        license_files: set[str] = set()
    else:
        license_files = set(license_files_value)
        for item in sorted(license_files):
            if any(character in item for character in "*?[]"):
                errors.append(
                    f"project license-files item must be a literal path, not a glob: {item}"
                )
            elif not _safe_relative_path(item):
                errors.append(f"project license-files item is unsafe or noncanonical: {item}")
    if "LICENSE" not in license_files:
        errors.append("project license-files must include LICENSE")
    for notice in sorted(notices):
        if notice not in license_files:
            errors.append(f"manifest notice is absent from license-files: {notice}")
        notice_path = root / notice
        if not notice_path.is_file():
            errors.append(f"manifest notice does not exist: {notice}")
        else:
            try:
                notice_text = notice_path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeDecodeError) as error:
                errors.append(f"{notice}: notice must be UTF-8 text: {error}")
            else:
                lines = notice_text.splitlines()
                if len(lines) < 2 or not any(line.strip() for line in lines):
                    errors.append(f"{notice}: notice must be nonempty multi-line text")
                if PurePosixPath(notice).name == "LICENSE" and lines:
                    expected_title = LICENSE_TITLES.get(notices[notice]["spdx"].casefold())
                    if expected_title is None or lines[0].strip() != expected_title:
                        errors.append(f"{notice}: legal-code first line must be its license title")
            if notices[notice]["sha256"] != _sha256(notice_path):
                errors.append(f"{notice}: notice sha256 mismatch")
    for notice in sorted(license_files - set(notices)):
        errors.append(f"license-files item is absent from manifest notices: {notice}")

    expression_terms, expression_error = _license_terms(project.get("license"))
    if expression_error:
        errors.append(expression_error)
    else:
        all_spdx = used_spdx | {record["spdx"] for record in notices.values()}
        folded_spdx = {spdx.casefold(): spdx for spdx in all_spdx}
        for folded in sorted(set(folded_spdx) - set(expression_terms)):
            spdx = folded_spdx[folded]
            errors.append(f"SPDX id is absent from project license expression: {spdx}")
        for folded in sorted(set(expression_terms) - set(folded_spdx)):
            errors.append(f"project license term has no provenance use: {expression_terms[folded]}")

    for relative in sorted(actual):
        if not relative.endswith(".json"):
            continue
        json_path = root / DATA_REL / relative
        try:
            value = _read_json(json_path, json_path.relative_to(root))
        except _DuplicateJSONKeyError as error:
            errors.append(str(error))
            continue
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{json_path.relative_to(root)}: invalid JSON: {error}")
            continue
        for key, source in _declared_provenance_strings(value):
            corpus_exception = key == "provenance" and _share_alike_corpus_allowed(
                entries.get(relative), notices
            )
            if _corpus_error(source) and not corpus_exception:
                errors.append(
                    f"{json_path.relative_to(root)}:{key}: declared provenance names known "
                    f"internal corpus {source!r}"
                )
    for relative in sorted(actual):
        suffix = PurePosixPath(relative).suffix.casefold()
        if suffix in {".json", ".tsv"}:
            continue
        xml_path = root / DATA_REL / relative
        try:
            tree = ET.parse(xml_path)
        except (OSError, ET.ParseError) as error:
            if suffix in {".xml", ".rng"}:
                errors.append(f"{xml_path.relative_to(root)}: invalid XML: {error}")
            continue
        for element in tree.iter():
            element_name = element.tag.rsplit("}", 1)[-1]
            provenance_element = element_name.casefold() in PROVENANCE_KEYS
            if provenance_element:
                declarations = [(element_name, "".join(element.itertext()))]
                declarations.extend(
                    (f"{element_name}:@{attribute.rsplit('}', 1)[-1]}", source)
                    for attribute, source in element.attrib.items()
                )
                for declaration, source in declarations:
                    if _corpus_error(source):
                        errors.append(
                            f"{xml_path.relative_to(root)}:{declaration}: declared provenance "
                            f"names known internal corpus {source!r}"
                        )
            for attribute, source in element.attrib.items():
                local_name = attribute.rsplit("}", 1)[-1]
                if (
                    not provenance_element
                    and local_name.casefold() in PROVENANCE_KEYS
                    and _corpus_error(source)
                ):
                    errors.append(
                        f"{xml_path.relative_to(root)}:@{local_name}: declared provenance names "
                        f"known internal corpus {source!r}"
                    )
    return errors


def refresh_hashes(root: Path) -> list[str]:
    """Refresh known hashes, refusing malformed, missing, or orphan entries."""
    root = root.resolve()
    manifest, errors = _load_manifest(root)
    if manifest is None:
        return errors
    metadata, metadata_errors = _read_project(root)
    errors.extend(metadata_errors)
    if metadata is None:
        return errors
    entries: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(manifest["files"]):
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            errors.append(f"manifest entry {index}: must be an object with a string path")
            continue
        path = entry["path"]
        if not _safe_relative_path(path):
            errors.append(f"manifest entry {index}: unsafe or noncanonical path {path!r}")
        elif path in entries:
            errors.append(f"duplicate provenance entry: {path}")
        else:
            entries[path] = entry
    actual, unselected = _package_data_paths(root, metadata["patterns"])
    errors.extend(f"data file is not selected by package-data: {path}" for path in unselected)
    recorded = set(entries)
    errors.extend(f"missing provenance entry: {path}" for path in sorted(actual - recorded))
    errors.extend(f"orphan provenance entry: {path}" for path in sorted(recorded - actual))
    if errors:
        return errors
    validation_errors = validate_repository(root)
    non_hash_errors = [
        error for error in validation_errors if not error.endswith(": sha256 mismatch")
    ]
    if non_hash_errors:
        return non_hash_errors
    for relative, entry in entries.items():
        entry["sha256"] = _sha256(root / DATA_REL / relative)
    for notice, record in manifest["notices"].items():
        record["sha256"] = _sha256(root / notice)
    manifest["files"] = [entries[path] for path in sorted(entries)]
    (root / DATA_REL / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return validate_repository(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate without rewriting hashes")
    parser.add_argument("--root", type=Path, default=Path(__file__).parents[1])
    args = parser.parse_args(argv)
    errors = validate_repository(args.root) if args.check else refresh_hashes(args.root)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    manifest, _ = _load_manifest(args.root)
    action = "checked" if args.check else "refreshed"
    print(f"{action} {len(manifest['files']) if manifest else 0} provenance entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
