"""Tests for number readers shared by flexible composite detectors."""

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from textwrap import dedent
from threading import Barrier, BrokenBarrierError, Lock

import pytest

import icukit.recognize as recognize
from icukit.engine import flexible_detectors, generated_detectors
from icukit.recognize import (
    FlexibleCurrencyDetector,
    FlexibleLowercaseRomanDetector,
    FlexibleMixedMeasureDetector,
    FlexibleNumberDetector,
    FlexibleNumberRangeDetector,
)
from icukit.serialize import detections_to_json


def _default_gang(locale, locales=None):
    return generated_detectors(locale).with_(*flexible_detectors(locale, locales=locales).detectors)


def _number_composites(gang):
    """Yield every direct or nested composite with a number-reader call site."""
    pending = list(gang.detectors)
    seen = set()
    while pending:
        detector = pending.pop()
        if id(detector) in seen:
            continue
        seen.add(id(detector))
        if hasattr(detector, "_number") or isinstance(detector, FlexibleNumberRangeDetector):
            yield detector
        if isinstance(detector, FlexibleCurrencyDetector):
            pending.extend(detector._compact)
        if isinstance(detector, FlexibleMixedMeasureDetector):
            pending.extend(detector._components)


def _reader_and_main_key(composite):
    """Return a composite reader and the key from that call site's main arguments."""
    if isinstance(composite, FlexibleNumberRangeDetector):
        reader = composite._bare_reader()
        reference = FlexibleNumberDetector(composite.locale, locales=composite.locales)
    elif isinstance(composite, FlexibleLowercaseRomanDetector):
        reader = composite._number
        reference = FlexibleNumberDetector(
            composite.locale,
            accept_single_letter_roman=composite.accept_single_letter_roman,
            accept_lowercase_roman=True,
        )
        reference._roman_rule_sets = tuple(
            name for name in reference._roman_rule_sets if "lower" in name.casefold()
        )
    else:
        reader = composite._number
        reference = FlexibleNumberDetector(composite.locale)
    return reader, recognize._number_reader_key(reference)


def test_number_reader_built_once_per_key(monkeypatch):
    recognize._clear_shared_number_reader_cache()
    original_init = FlexibleNumberDetector.__init__
    constructed = []

    def record_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        constructed.append(self)

    monkeypatch.setattr(FlexibleNumberDetector, "__init__", record_init)
    generated_detectors("en_US").with_(*flexible_detectors("en_US").detectors)

    keys = {recognize._number_reader_key(reader) for reader in constructed}
    assert len(constructed) == len(keys) == 1


def test_shared_number_reader_concurrent_cold_miss_single_instance(monkeypatch):
    recognize._clear_shared_number_reader_cache()
    original_init = FlexibleNumberDetector.__init__
    callers_ready = Barrier(2)
    cold_misses = Barrier(2)
    constructions = []
    constructions_lock = Lock()

    def blocked_init(self, *args, **kwargs):
        with constructions_lock:
            constructions.append(self)
        try:
            cold_misses.wait(timeout=0.5)
        except BrokenBarrierError:
            pass
        original_init(self, *args, **kwargs)

    def build():
        callers_ready.wait()
        return recognize._shared_number_reader("en_US", None, True, False)

    monkeypatch.setattr(FlexibleNumberDetector, "__init__", blocked_init)
    with ThreadPoolExecutor(max_workers=2) as pool:
        readers = tuple(future.result() for future in (pool.submit(build), pool.submit(build)))

    assert readers[0] is readers[1]
    assert len(constructions) == 1
    recognize._clear_shared_number_reader_cache()


@pytest.mark.parametrize(
    ("locale", "locales"),
    [
        ("en_US", None),
        ("de_DE", None),
        ("de_CH", None),
        ("fr_CH", None),
        ("hi_IN", None),
        ("de_CH", ("de_CH", "de_LI")),
        ("de_CH", ["de_CH", "de_LI"]),
    ],
)
def test_shared_number_reader_key_property(locale, locales):
    composites = list(_number_composites(_default_gang(locale, locales)))

    assert composites
    for composite in composites:
        reader, expected_key = _reader_and_main_key(composite)
        assert recognize._number_reader_key(reader) == expected_key, type(composite).__name__


@pytest.mark.parametrize("locales", [["de_DE", "de_LI"], ("de_DE", "de_LI")])
def test_top_level_number_reader_receives_locales(locales):
    expected = recognize._number_reader_key(
        FlexibleNumberDetector("de_CH", locales=("de_DE", "de_LI"))
    )
    members = [
        member
        for member in flexible_detectors("de_CH", locales=locales).detectors
        if member.type == "number:decimal"
    ]

    assert members
    assert all(recognize._number_reader_key(member) == expected for member in members)


def test_shared_number_reader_matches_unshared_reference():
    script = dedent(
        """
        import json

        import icukit.engine as engine
        import icukit.recognize as recognize
        from icukit.serialize import detections_to_json

        def unshared(locale, locales, accept_single_letter_roman, accept_lowercase_roman):
            return recognize.FlexibleNumberDetector(
                locale,
                locales=locales,
                accept_single_letter_roman=accept_single_letter_roman,
                accept_lowercase_roman=accept_lowercase_roman,
            )

        recognize._shared_number_reader = unshared
        engine._shared_number_reader = unshared
        cases = (
            ("fr_CH", "1,5 CHF"),
            ("de_CH", "1'234.5"),
            ("hi_IN", "1,23,456"),
        )
        output = []
        for locale, text in cases:
            gang = engine.generated_detectors(locale).with_(
                *engine.flexible_detectors(locale).detectors
            )
            output.append([locale, text, detections_to_json(gang.detect(text))])
        lower = recognize.FlexibleLowercaseRomanDetector("en_US")
        output.append(["en_US", "xiv", detections_to_json(lower.detect("xiv"))])
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
        """
    )
    reference = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    cases = (
        ("fr_CH", "1,5 CHF"),
        ("de_CH", "1'234.5"),
        ("hi_IN", "1,23,456"),
    )
    actual = []
    for locale, text in cases:
        actual.append([locale, text, detections_to_json(_default_gang(locale).detect(text))])
    lower = FlexibleLowercaseRomanDetector("en_US")
    actual.append(["en_US", "xiv", detections_to_json(lower.detect("xiv"))])

    assert actual == json.loads(reference.stdout)


def test_shared_number_reader_list_locales():
    recognize._clear_shared_number_reader_cache()
    from_list = recognize._shared_number_reader("de_CH", ["de_CH", "de_LI"], True, False)
    from_tuple = recognize._shared_number_reader("de_CH", ("de_CH", "de_LI"), True, False)

    assert from_list is from_tuple
    assert recognize._number_reader_key(from_list) == recognize._number_reader_key(from_tuple)


def test_shared_number_reader_distinct_locales():
    recognize._clear_shared_number_reader_cache()
    de_de = recognize._shared_number_reader("de_DE", None, True, False)
    de_ch = recognize._shared_number_reader("de_CH", None, True, False)

    assert de_de is not de_ch
    assert recognize._number_reader_key(de_de) != recognize._number_reader_key(de_ch)


def test_lowercase_roman_copy_does_not_mutate_shared_reader():
    recognize._clear_shared_number_reader_cache()
    shared = recognize._shared_number_reader("en_US", None, True, True)
    rule_sets = shared._roman_rule_sets

    lowercase = FlexibleLowercaseRomanDetector("en_US")

    assert lowercase._number is not shared
    assert shared._roman_rule_sets == rule_sets
    assert all("lower" in name.casefold() for name in lowercase._number._roman_rule_sets)
    assert any("lower" not in name.casefold() for name in shared._roman_rule_sets)


@pytest.mark.parametrize("order", [(False, True), (True, False)])
def test_lowercase_roman_single_letter_flag_is_distinct_in_both_orders(order):
    recognize._clear_shared_number_reader_cache()
    readers = {
        flag: FlexibleLowercaseRomanDetector("en_US", accept_single_letter_roman=flag)
        for flag in order
    }

    assert recognize._number_reader_key(readers[False]._number) != recognize._number_reader_key(
        readers[True]._number
    )
    for surface in ("i", "v"):
        assert readers[False].detect(surface) == []
        assert readers[True].detect(surface)


@pytest.mark.parametrize("locale", ["en_US", "de_DE", "hi_IN"])
def test_cached_roman_alphabets_match_formatter(locale):
    number = FlexibleNumberDetector(locale, accept_lowercase_roman=True)

    for rule_set, alphabet in number._roman_alphabets.items():
        expected = frozenset(
            character
            for value in range(1, 4000)
            for character in number._roman.format(value, rule_set)
            if recognize._is_word_character(character)
        )
        assert recognize._roman_alphabet(locale, rule_set) == expected
        assert alphabet == expected
