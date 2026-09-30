"""Process-wide detector-construction cache tests."""

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock

import icu
import pytest

import icukit.engine as engine
import icukit.recognize as recognize
from icukit.serialize import detections_to_json


@pytest.fixture(autouse=True)
def clear_caches():
    engine.clear_detector_caches()
    yield
    engine.clear_detector_caches()


def test_equal_gang_calls_return_the_memoized_frozen_report():
    first = engine.flexible_detectors_report(
        "de_CH", locales=["de_DE", "de_LI"], currencies=["CHF", "EUR"], units=["meter"]
    )
    second = engine.flexible_detectors_report(
        "de_CH", locales=("de_LI", "de_DE"), currencies=("CHF", "EUR"), units=("meter",)
    )

    assert first is second
    assert first.detectors is second.detectors


def test_gang_key_preserves_parameter_order_and_family_identity():
    forward = engine.flexible_detectors("en_US", currencies=("USD", "EUR"), units=("meter",))
    reverse = engine.flexible_detectors("en_US", currencies=("EUR", "USD"), units=("meter",))
    assert forward is not reverse

    first_families = tuple(engine.DEFAULT_FAMILIES)
    equal_but_distinct = tuple(
        engine.Family(item.name, item.enumerate, item.invert, item.skip_reason)
        for item in engine.DEFAULT_FAMILIES
    )
    assert first_families == equal_but_distinct
    assert engine.generated_detectors("en_US", first_families) is not engine.generated_detectors(
        "en_US", equal_but_distinct
    )


def test_cache_environment_opt_out_is_read_at_call_time(monkeypatch):
    cached = engine.generated_detectors("en_US")
    assert engine.generated_detectors("en_US") is cached

    monkeypatch.setenv("ICUKIT_CACHE", "0")
    uncached = engine.generated_detectors("en_US")
    assert uncached is not cached

    monkeypatch.delenv("ICUKIT_CACHE")
    assert engine.generated_detectors("en_US") is cached


def test_clear_detector_caches_discards_gangs_and_locale_fragments():
    gang = engine.flexible_detectors("en_US", currencies=("USD",), units=("meter",))
    recognize._measure_surfaces("en_US", "meter", True)
    assert recognize._measure_surfaces.cache_info().currsize

    engine.clear_detector_caches()

    assert recognize._measure_surfaces.cache_info().currsize == 0
    assert engine.flexible_detectors("en_US", currencies=("USD",), units=("meter",)) is not gang
    assert recognize._measure_surfaces.cache_info().currsize == 1


def test_same_gang_key_has_one_concurrent_builder(monkeypatch):
    started = Event()
    release = Event()
    calls = []
    calls_lock = Lock()
    result = object()

    def build(locale, families, materials):
        with calls_lock:
            calls.append((locale, families, materials))
        started.set()
        assert release.wait(timeout=2)
        return result

    monkeypatch.setattr(engine, "_build_generated_detectors_report", build)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(engine.generated_detectors_report, "en_US")
        assert started.wait(timeout=2)
        second = pool.submit(engine.generated_detectors_report, "en_US")
        release.set()

    assert first.result() is second.result() is result
    assert len(calls) == 1


def test_distinct_gang_keys_build_concurrently(monkeypatch):
    builders = Barrier(2)

    def build(locale, families, materials):
        builders.wait(timeout=2)
        return locale

    monkeypatch.setattr(engine, "_build_generated_detectors_report", build)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(
            future.result()
            for future in (
                pool.submit(engine.generated_detectors_report, "en_US"),
                pool.submit(engine.generated_detectors_report, "de_DE"),
            )
        )

    assert set(results) == {"en_US", "de_DE"}


@pytest.mark.parametrize("language", ["en", "ar", "sr", "bs", "zh", "ja", "pt"])
def test_representative_measure_fingerprints_are_exact(language):
    names = [
        name
        for name in sorted(icu.Locale.getAvailableLocales())
        if icu.Locale(name).getLanguage() == language
    ]
    groups = defaultdict(list)
    for name in names:
        groups[recognize._measure_locale_fingerprint(name)].append(name)

    for group in groups.values():
        expected = recognize._measure_locale_fragment_uncached(group[0], "meter", True)
        assert all(
            recognize._measure_locale_fragment_uncached(name, "meter", True) == expected
            for name in group[1:]
        )


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("en", "en_AS"),
        ("ar", "ar_001"),
        ("bs_Cyrl", "bs_Cyrl_BA"),
        ("zh_Hans", "zh_Hans_HK"),
        ("ja", "ja_JP"),
        ("pt", "pt_BR"),
    ],
)
def test_representative_zone_owner_fingerprints_are_exact(left, right):
    assert (
        recognize._zone_locale_fingerprint(left)[:-1]
        == recognize._zone_locale_fingerprint(right)[:-1]
    )
    assert recognize._zone_locale_owner_tables_uncached(
        left
    ) == recognize._zone_locale_owner_tables_uncached(right)


def test_serbian_zone_table_matches_its_unshared_reference():
    assert recognize._zone_locale_tables("sr") == recognize._zone_locale_tables_uncached("sr")


def test_dropping_unit_owner_has_a_real_counterexample():
    world = recognize._measure_locale_fingerprint("en_001")
    india = recognize._measure_locale_fingerprint("en_IN")
    assert world[1:] == india[1:]
    assert world[0] != india[0]
    assert recognize._measure_locale_fragment_uncached(
        "en_001", "kilometer-per-hour", True
    ) != recognize._measure_locale_fragment_uncached("en_IN", "kilometer-per-hour", True)


def test_two_threads_can_detect_with_one_memoized_gang():
    gang = engine.generated_detectors("en_US").with_(
        *engine.flexible_detectors("en_US", currencies=("USD",), units=("meter",)).detectors
    )
    text = "On March 3, 2024 I paid $5.20 for 3 meters and 45% of 1,200."
    expected = detections_to_json(gang.detect(text))

    with ThreadPoolExecutor(max_workers=2) as pool:
        found = tuple(pool.map(lambda _index: detections_to_json(gang.detect(text)), range(2)))

    assert found == (expected, expected)
