"""On-disk detector-table cache behavior and failure totality."""

from __future__ import annotations

import compileall
import hashlib
import importlib
import json
import marshal
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from unittest import mock

import icu
import pytest

from icukit import _tables, cache, ungated
from icukit.detectors import detect
from icukit.engine import clear_detector_caches, flexible_detectors
from icukit.recognize import (
    FlexibleNumberDetector,
    _language_zone_names,
    _locale_negative_currency_wraps_uncached,
    _measure_locale_fragment_uncached,
    _negative_currency_wraps,
    _roman_alphabet,
    _spellout_rulesets,
    _spellout_table,
    _zone_locale_generic_tables_uncached,
    _zone_locale_owner_tables_uncached,
)
from icukit.serialize import detections_to_json


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path):
    cache.configure(enabled=True, directory=tmp_path / "cache")
    cache._reset_counters()
    yield tmp_path / "cache"
    cache.configure(enabled=True)


def test_table_cache_roundtrip_identical(isolated_cache):
    expected = _roman_alphabet("en_US", "%roman-upper")
    cache.flush()
    cache.configure(enabled=True, directory=isolated_cache)
    actual = _roman_alphabet("en_US", "%roman-upper")
    assert actual == expected
    assert cache.cache_info()["tables_loaded"]["detect"] == 1


def test_initial_persisted_set_is_exact_and_marshalable():
    expected = {
        "_zone_locale_owner_tables_uncached": ("en_US",),
        "_zone_locale_generic_tables_uncached": ("en_US",),
        "_measure_locale_fragment_uncached": ("en_US", "meter", True),
        "_roman_alphabet": ("en_US", "%roman-upper"),
        "_locale_negative_currency_wraps_uncached": ("en_US", "USD"),
        "_spellout_rulesets": ("en_US",),
        "_spellout_table": ("en_US", "%spellout-cardinal"),
    }
    functions = {
        function.__name__: function
        for function in (
            _zone_locale_owner_tables_uncached,
            _zone_locale_generic_tables_uncached,
            _measure_locale_fragment_uncached,
            _roman_alphabet,
            _locale_negative_currency_wraps_uncached,
            _spellout_rulesets,
            _spellout_table,
        )
    }
    assert set(_tables._REGISTRY) == set(expected) == set(functions)
    for name, arguments in expected.items():
        value = functions[name](*arguments)
        assert _tables._allowed(value)
        assert marshal.loads(marshal.dumps(value)) == value


def test_measure_surfaces_are_hash_seed_stable():
    script = """
import json
from icukit.recognize import _measure_surfaces
print(json.dumps(_measure_surfaces('en_US', 'square-foot', True, None), ensure_ascii=False))
"""
    outputs = []
    for seed in ("0", "1"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            env={**os.environ, "ICUKIT_CACHE": "0", "PYTHONHASHSEED": seed},
            text=True,
            capture_output=True,
            check=True,
        )
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1]


def test_cache_opt_out_touches_nothing(tmp_path):
    root = tmp_path / "disabled"
    cache.configure(enabled=False, directory=root)
    assert _roman_alphabet("en_US", "%roman-upper")
    cache.flush()
    assert not root.exists()


def test_environment_opt_out_bypasses_loaded_table_memory(monkeypatch):
    expected = _roman_alphabet("en_US", "%roman-upper")
    assert _tables._MEMORY

    monkeypatch.setattr(cache, "_enabled_override", None)
    monkeypatch.setenv("ICUKIT_CACHE", "0")
    actual = _roman_alphabet("en_US", "%roman-upper")

    assert actual == expected
    assert actual is not expected


def test_clear_detector_caches_drops_table_memory_only(isolated_cache):
    _roman_alphabet("en_US", "%roman-upper")
    cache.flush()
    files = tuple(_tables._current_files())
    assert _tables._MEMORY
    assert files

    clear_detector_caches()

    assert not _tables._MEMORY
    assert tuple(_tables._current_files()) == files


@pytest.mark.parametrize("disable", ("configure", "failure"))
def test_cache_info_disabled_does_not_inspect_store(isolated_cache, disable):
    _roman_alphabet("en_US", "%roman-upper")
    cache.flush()
    if disable == "configure":
        cache.configure(enabled=False, directory=isolated_cache)
    else:
        cache._disable("test failure")

    with (
        mock.patch.object(_tables, "_current_files", wraps=_tables._current_files) as listing,
        mock.patch.object(_tables, "_read", wraps=_tables._read) as read,
    ):
        info = cache.cache_info()

    assert not info["enabled"]
    assert info["entries"] == 0
    assert info["bytes"] == 0
    listing.assert_not_called()
    read.assert_not_called()


def test_cache_info_environment_opt_out_does_not_inspect_store(tmp_path):
    script = """
import json
from unittest import mock
from icukit import _tables, cache
with (
    mock.patch.object(_tables, '_current_files', wraps=_tables._current_files) as listing,
    mock.patch.object(_tables, '_read', wraps=_tables._read) as read,
):
    info = cache.cache_info()
print(json.dumps([
    info['enabled'], info['entries'], info['bytes'], listing.call_count, read.call_count,
]))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={
            **os.environ,
            "ICUKIT_CACHE": "0",
            "ICUKIT_CACHE_DIR": str(tmp_path / "environment-disabled"),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(result.stdout) == [False, 0, 0, 0, 0]


def test_ik_detect_no_cache_touches_nothing(tmp_path):
    root = tmp_path / "detect-disabled"
    environment = {**os.environ, "ICUKIT_CACHE_DIR": str(root)}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "icukit.cli",
            "detect",
            "--no-cache",
            "--flexible",
            "--locales",
            "",
            "-t",
            "five",
        ],
        env=environment,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert not root.exists()


def test_table_store_shared_across_gangs():
    first = FlexibleNumberDetector("en_US")
    computed = cache.cache_info()["tables_computed"]["detect"]
    second = FlexibleNumberDetector("en_US")
    assert first._roman_alphabets == second._roman_alphabets
    info = cache.cache_info()
    assert info["tables_computed"]["detect"] == computed
    assert info["table_detect_hits"] == 1
    assert info["detect_hits"] == 0


def test_table_key_fields_from_sources():
    key = _tables.table_key()
    expected_tz = hashlib.sha256(
        "\n".join(sorted(str(zone) for zone in icu.TimeZone.createEnumeration())).encode()
    ).hexdigest()
    assert key.schema == _tables.SCHEMA
    assert key.icukit == importlib.import_module("icukit").__version__
    assert key.code == _tables._code_hash()
    assert key.icu == icu.ICU_VERSION
    assert key.pyicu == icu.VERSION
    assert key.pyicu_dist == importlib.metadata.version("icukit-pyicu")
    assert key.unicode == icu.UNICODE_VERSION
    assert key.cldr == icu.ResourceBundle("", icu.Locale("root")).get("Version").getString()
    assert key.tz == expected_tz
    assert key.python_tag == sys.implementation.cache_tag
    assert key.marshal == marshal.version
    assert key.py_unicode == importlib.import_module("unicodedata").unidata_version
    assert json.loads(key.icu_env) == {
        "ICU_DATA": os.environ.get("ICU_DATA", ""),
        "ICU_TIMEZONE_FILES_DIR": os.environ.get("ICU_TIMEZONE_FILES_DIR", ""),
    }
    assert key.default_locale == icu.Locale.getDefault().getName()


def test_tz_field_tracks_enumeration(monkeypatch):
    monkeypatch.setattr(_tables, "_tz_hash", lambda: "changed")
    _tables._reconfigure()
    assert _tables.table_key().tz == "changed"


def test_corrupt_table_file_rebuilds(isolated_cache):
    expected = _roman_alphabet("en_US", "%roman-upper")
    cache.flush()
    path = _tables._current_files()[0]
    path.write_bytes(b"not a table")
    cache.configure(enabled=True, directory=isolated_cache)
    assert _roman_alphabet("en_US", "%roman-upper") == expected
    cache.flush()
    assert _tables._decode(path.read_bytes(), _tables.table_key()) is not None


def test_concurrent_writers_merge(isolated_cache):
    script = """
import sys
from icukit import cache
from icukit.recognize import _roman_alphabet
_roman_alphabet('en_US', sys.argv[1])
cache.flush()
"""
    environment = {**os.environ, "ICUKIT_CACHE_DIR": str(isolated_cache)}
    processes = [
        subprocess.Popen([sys.executable, "-c", script, ruleset], env=environment)
        for ruleset in ("%roman-upper", "%roman-lower")
    ]
    assert [process.wait() for process in processes] == [0, 0]
    cache.configure(enabled=True, directory=isolated_cache)
    assert _roman_alphabet("en_US", "%roman-upper")
    assert _roman_alphabet("en_US", "%roman-lower")
    assert cache.cache_info()["tables_loaded"]["detect"] == 2


def test_flush_re_read_failure_preserves_existing_shard(isolated_cache, monkeypatch):
    _roman_alphabet("en_US", "%roman-upper")
    cache.flush()
    path = _tables._current_files()[0]
    before = path.read_bytes()
    _roman_alphabet("en_US", "%roman-lower")
    original_read_bytes = Path.read_bytes

    def fail_re_read(candidate):
        if candidate == path:
            raise OSError("transient re-read failure")
        return original_read_bytes(candidate)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", fail_re_read)
        cache.flush()

    assert "transient re-read failure" in cache.cache_info()["disabled_reason"]
    after = path.read_bytes()
    entries = _tables._decode(after, _tables.table_key())
    assert entries is not None
    assert ("_roman_alphabet", ("en_US", "%roman-upper")) in entries
    assert ("_roman_alphabet", ("en_US", "%roman-lower")) not in entries
    assert after == before


def test_verify_same_is_exact():
    assert not _tables._same({"a": 1}, {"a": True})
    assert not _tables._same({"a": 1, "b": 2}, {"b": 2, "a": 1})
    assert _tables._same((1, frozenset({"a", "b"})), (1, frozenset({"b", "a"})))


def _run_compile(root: Path, *arguments: str):
    return subprocess.run(
        [sys.executable, "-m", "icukit.cli", "compile", "--cache-dir", str(root), *arguments],
        text=True,
        capture_output=True,
    )


def test_ik_compile_verify(isolated_cache):
    _roman_alphabet("en_US", "%roman-upper")
    cache.flush()
    result = _run_compile(isolated_cache, "--verify")
    assert result.returncode == 0, result.stderr


def test_ik_compile_verify_catches_poisoned_entry(isolated_cache):
    _language_zone_names("en", ("en_US",))
    cache.flush()
    key = _tables.table_key()
    path = next(
        path for path in _tables._current_files() if "zone_locale_owner_tables" in str(path)
    )
    entries = _tables._read(path, key, "test")
    entry = next(iter(entries))
    entries[entry] = ("Poisoned Zone Name",)
    path.write_bytes(_tables._encode(entries, key))
    result = _run_compile(isolated_cache, "--verify")
    assert result.returncode == 1
    assert "mismatch" in result.stderr


def test_ik_compile_verify_rejects_corrupt_shard(isolated_cache):
    _roman_alphabet("en_US", "%roman-upper")
    cache.flush()
    path = _tables._current_files()[0]
    data = bytearray(path.read_bytes())
    data[-1] ^= 0xFF
    path.write_bytes(data)

    result = _run_compile(isolated_cache, "--verify", "--json")

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["entries_verified"] == 0
    assert report["verification_failures"] == 1
    assert str(path) in result.stderr


def test_key_sources_total(monkeypatch):
    def missing(_distribution):
        raise importlib.metadata.PackageNotFoundError("missing")

    monkeypatch.setattr(importlib.metadata, "version", missing)
    _tables._reconfigure()
    gang = flexible_detectors("en_US", locales=())
    text = "at -5 now"
    with ungated():
        expected = detections_to_json(detect(text, gang.detectors))
    assert detections_to_json(gang.detect(text)) == expected
    info = cache.cache_info()
    assert not info["enabled"]
    assert "TableKey.pyicu_dist" in info["disabled_reason"]


def test_code_hash_sourceless_and_zip(tmp_path, monkeypatch):
    source_root = tmp_path / "source"
    package = source_root / "cache_fixture_source"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE = 1\n")
    (package / "module.py").write_text("VALUE = 2\n")
    monkeypatch.syspath_prepend(str(source_root))
    importlib.import_module("cache_fixture_source")
    assert _tables._code_hash("cache_fixture_source")

    assert compileall.compile_dir(package, quiet=1, legacy=True)
    (package / "__init__.py").unlink()
    (package / "module.py").unlink()
    importlib.invalidate_caches()
    sys.modules.pop("cache_fixture_source", None)
    importlib.import_module("cache_fixture_source")
    assert _tables._code_hash("cache_fixture_source")

    zip_root = tmp_path / "fixture.zip"
    with zipfile.ZipFile(zip_root, "w") as archive:
        archive.writestr("cache_fixture_zip/__init__.py", "VALUE = 3\n")
        archive.writestr("cache_fixture_zip/data/value.txt", "data")
    monkeypatch.syspath_prepend(str(zip_root))
    importlib.import_module("cache_fixture_zip")
    assert _tables._code_hash("cache_fixture_zip")

    empty = source_root / "cache_fixture_empty"
    empty.mkdir()
    importlib.invalidate_caches()
    importlib.import_module("cache_fixture_empty")
    with pytest.raises(ValueError, match="no module files"):
        _tables._code_hash("cache_fixture_empty")
    code_hash = _tables._code_hash
    monkeypatch.setattr(_tables, "_code_hash", lambda: code_hash("cache_fixture_empty"))
    _tables._reconfigure()
    assert _tables.table_key().code == "unknown"
    assert "TableKey.code" in cache.cache_info()["disabled_reason"]


def test_code_field_tracks_bytecode_in_mixed_install(tmp_path, monkeypatch):
    source_root = tmp_path / "source"
    package = source_root / "cache_fixture_mixed"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE = 1\n")
    (package / "source_only.py").write_text("VALUE = 2\n")
    bytecode_only = package / "bytecode_only.py"
    bytecode_only.write_text("VALUE = 3\n")
    assert compileall.compile_file(bytecode_only, quiet=1, legacy=True)
    bytecode_only.unlink()
    monkeypatch.syspath_prepend(str(source_root))
    importlib.import_module("cache_fixture_mixed")

    code_hash = _tables._code_hash
    monkeypatch.setattr(_tables, "_code_hash", lambda: code_hash("cache_fixture_mixed"))
    _tables._reconfigure()
    before = _tables.table_key().code

    bytecode_only.write_text("VALUE = 4\n")
    assert compileall.compile_file(bytecode_only, quiet=1, legacy=True, force=True)
    bytecode_only.unlink()
    importlib.invalidate_caches()
    _tables._reconfigure()
    after = _tables.table_key().code

    assert after != before


def test_writes_batched_and_sharded(monkeypatch):
    replacements = []
    original = _tables.os.replace

    def replace(source, target):
        replacements.append(Path(target))
        return original(source, target)

    monkeypatch.setattr(_tables.os, "replace", replace)
    _negative_currency_wraps("en_US", "USD")
    _negative_currency_wraps("en_US", "EUR")
    assert replacements == []
    cache.flush()
    assert len(replacements) == 1
    assert replacements[0].name == "en.tables"
    assert list(replacements[0].parent.glob("*.tables")) == [replacements[0]]


def test_queue_snapshots_mutable_results(isolated_cache):
    @_tables.persisted
    def mutable_fixture(locale: str) -> list[str]:
        return [locale]

    name = mutable_fixture.__qualname__
    try:
        value = mutable_fixture("en_US")
        value.append("poison")
        cache.flush()
        cache.configure(enabled=True, directory=isolated_cache)
        assert mutable_fixture("en_US") == ["en_US"]
    finally:
        _tables._REGISTRY.pop(name, None)


def test_root_mode_is_private(isolated_cache):
    _roman_alphabet("en_US", "%roman-upper")
    cache.flush()
    assert isolated_cache.stat().st_mode & 0o777 == 0o700


def test_compile_list_prune_and_clear(isolated_cache):
    _roman_alphabet("en_US", "%roman-upper")
    cache.flush()
    obsolete = isolated_cache / "tables-v1" / ("0" * 64)
    obsolete.mkdir()
    listed = _run_compile(isolated_cache, "--list", "--json")
    assert listed.returncode == 0, listed.stderr
    assert json.loads(listed.stdout)["entries"]
    pruned = _run_compile(isolated_cache, "--prune", "--json")
    assert pruned.returncode == 0, pruned.stderr
    assert not obsolete.exists()
    cleared = _run_compile(isolated_cache, "--clear", "--json")
    assert cleared.returncode == 0, cleared.stderr
    assert not (isolated_cache / "tables-v1").exists()


@pytest.mark.parametrize("language", ("en_US.UTF-8", "de_DE.UTF-8"))
def test_default_locale_field_follows_lang(language, tmp_path):
    script = """
import json
import icu
from icukit._tables import table_key
print(json.dumps([table_key().default_locale, icu.Locale.getDefault().getName()]))
"""
    environment = {
        **os.environ,
        "LANG": language,
        "ICUKIT_CACHE_DIR": str(tmp_path / language),
    }
    result = subprocess.run(
        [sys.executable, "-c", script], env=environment, text=True, capture_output=True, check=True
    )
    key_locale, icu_default = json.loads(result.stdout)
    assert key_locale == icu_default


def test_default_locale_field_tracks_set_default():
    original = icu.Locale.getDefault()
    changed = icu.Locale("fr_FR" if original.getName() != "fr_FR" else "en_US")
    try:
        before = _tables.table_key()
        icu.Locale.setDefault(changed)
        after = _tables.table_key()
        assert after.default_locale == changed.getName()
        assert after.default_locale != before.default_locale
        assert after.digest() != before.digest()
    finally:
        icu.Locale.setDefault(original)
        _tables._reconfigure()


def test_flush_uses_key_queued_before_default_locale_change(isolated_cache):
    original = icu.Locale.getDefault()
    en_us = icu.Locale("en_US")
    try:
        icu.Locale.setDefault(en_us)
        upper = _roman_alphabet("en_US", "%roman-upper")
        cache.flush()
        lower = _roman_alphabet("en_US", "%roman-lower")

        icu.Locale.setDefault(icu.Locale("fr_FR"))
        cache.flush()
        icu.Locale.setDefault(en_us)

        cache.configure(enabled=True, directory=isolated_cache)
        cache._reset_counters()
        assert _roman_alphabet("en_US", "%roman-upper") == upper
        assert _roman_alphabet("en_US", "%roman-lower") == lower
        assert cache.cache_info()["tables_loaded"]["detect"] == 2
    finally:
        icu.Locale.setDefault(original)
        _tables._reconfigure()


def test_unwritable_root_detect_unchanged(tmp_path):
    root = tmp_path / "file-not-directory"
    root.write_text("occupied")
    cache.configure(enabled=True, directory=root)
    clear_detector_caches()
    gang = flexible_detectors("en_US", locales=())
    cache.flush()
    with ungated():
        expected = detections_to_json(detect("at -5", gang.detectors))
    assert detections_to_json(gang.detect("at -5")) == expected
    reason = cache.cache_info()["disabled_reason"]
    assert str(root) in reason
    assert reason.startswith(("read ", "mkdir "))


def test_no_flock_detect_unchanged(monkeypatch):
    def unavailable(_handle):
        raise OSError("flock unavailable")

    monkeypatch.setattr(_tables, "_lock_file", unavailable)
    clear_detector_caches()
    gang = flexible_detectors("en_US", locales=())
    cache.flush()
    with ungated():
        expected = detections_to_json(detect("at -5", gang.detectors))
    assert detections_to_json(gang.detect("at -5")) == expected
    assert "flock unavailable" in cache.cache_info()["disabled_reason"]
