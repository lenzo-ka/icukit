"""Introspective formatter-family generation tests."""

import icu

from icukit.detectors import DateDetector
from icukit.engine import (
    DATE_INTERVAL_FAMILY,
    DATE_TIME_SKELETON_FAMILY,
    generated_detectors,
    generated_detectors_report,
)


def _instant() -> float:
    calendar = icu.Calendar.createInstance(
        icu.TimeZone.getGMT(), icu.Locale("en_US@calendar=gregorian")
    )
    calendar.clear()
    calendar.set(2024, 2, 24)
    return calendar.getTime()


def test_generated_dates_include_introspected_partial_skeletons():
    gang = generated_detectors("en_US")
    skeletons = set(icu.DateTimePatternGenerator.createInstance(icu.Locale("en_US")).getSkeletons())

    assert "date:Md" in gang.names()
    wide_month_year = next(
        skeleton
        for skeleton in skeletons
        if "y" in skeleton and "MMMM" in skeleton and "date:" + skeleton in gang.names()
    )
    surfaces = {
        detector.type: detector._df.format(_instant())
        for detector in gang.detectors
        if isinstance(detector, DateDetector)
    }

    md = next(item for item in gang.detect(surfaces["date:Md"]) if item["type"] == "date:Md")
    assert dict(md["value"].fields) == {"M": 3, "d": 24}
    assert any(
        item["type"] == f"date:{wide_month_year}"
        for item in gang.detect(surfaces[f"date:{wide_month_year}"])
    )


def test_unmodeled_skeletons_are_reported_and_skipped():
    report = generated_detectors_report("en_US")
    skipped = {item.spec for item in report.skipped}

    assert {"Gy", "yQQQ", "yw", "Bh"} <= skipped
    assert not ({"date:Gy", "date:yQQQ", "date:yw", "date:Bh"} & set(report.detectors.names()))
    assert DATE_TIME_SKELETON_FAMILY.invert("Gy", "en_US") is None
    assert all(item.reason for item in report.skipped)


def test_generation_reflects_a_non_english_locale():
    locale = "th_TH"
    local_skeletons = tuple(DATE_TIME_SKELETON_FAMILY.enumerate(locale))
    english_skeletons = tuple(DATE_TIME_SKELETON_FAMILY.enumerate("en_US"))
    gang = generated_detectors(locale)

    assert gang.names()
    assert local_skeletons != english_skeletons
    date_names = {
        name for name in gang.names() if name.startswith("date:") and name != "date:relative"
    }
    compact_names = {name for name in gang.names() if name.startswith("number:compact:")}
    assert date_names <= {f"date:{skeleton}" for skeleton in local_skeletons}
    assert compact_names


def test_generated_detectors_include_reflective_compact_numbers():
    gang = generated_detectors("en_US")

    assert "number:compact:short" in gang.names()
    detection = next(item for item in gang.detect("1.2M") if item["type"] == "number:compact:short")
    assert detection["value"].decimal == "1200000"


def test_generated_detectors_include_reflective_scientific_numbers():
    gang = generated_detectors("en_US")

    assert "number:scientific" in gang.names()
    detector = next(item for item in gang.detectors if item.type == "number:scientific")
    detection = detector.detect("1.2345E4")[0]
    assert detection["value"].decimal == "12345"


def test_generated_detectors_include_reflective_spellout_numbers():
    gang = generated_detectors("en_US")

    detector = next(item for item in gang.detectors if item.type == "number:spellout")
    detection = detector.detect("twenty-three")[0]
    assert detection["value"].decimal == "23"


def test_generated_detectors_include_reflective_relative_dates():
    gang = generated_detectors("en_US")

    assert "date:relative" in gang.names()
    detection = next(item for item in gang.detect("3 days ago") if item["type"] == "date:relative")
    assert (detection["value"].offset, detection["value"].unit) == (-3, "day")

    spanish = generated_detectors("es")
    assert "date:relative" in spanish.names()
    detection = next(item for item in spanish.detect("ayer") if item["type"] == "date:relative")
    assert (detection["value"].offset, detection["value"].unit) == (-1, "day")


def test_generated_detectors_include_and_report_reflective_date_intervals():
    report = generated_detectors_report("en_US")
    names = set(report.detectors.names())

    assert "date-interval:Hm" in names
    assert DATE_INTERVAL_FAMILY.invert("y", "en_US") is not None
    assert any(item.family == "date-interval" for item in report.skipped)
    assert all(item.reason for item in report.skipped if item.family == "date-interval")


def test_localized_literal_skeletons_are_not_wrongly_skipped():
    # A localized pattern interleaves modeled fields with locale literal text (Japanese
    # "y年M月d日"). That literal text is alphabetic under Unicode but is not a CLDR field,
    # so it must not push an otherwise invertible skeleton into the skipped set.
    gang = generated_detectors("ja_JP")

    assert "date:MMMd" in gang.names()  # partial date, month + day + literals
    assert "date:yMMMd" in gang.names()

    detector = next(d for d in gang.detectors if d.type == "date:yMMMd")
    surface = detector._df.format(_instant())
    hit = next(item for item in gang.detect(surface) if item["type"] == "date:yMMMd")
    assert hit["text"] == surface  # reformat == surface still holds through the literals
    assert dict(hit["value"].fields) == {"y": 2024, "M": 3, "d": 24}

    # Era/quarter/etc. remain correctly refused even in this locale.
    report = generated_detectors_report("ja_JP")
    assert any(item.spec == "Gy" for item in report.skipped)


def test_generation_is_deterministic_and_deduplicated():
    first = generated_detectors("en_US").names()
    second = generated_detectors("en_US").names()

    assert first == second
    assert len(first) == len(set(first))


def test_generated_detectors_register_abbreviations_only_with_a_lexicon():
    assert "abbreviation" in generated_detectors("en").names()
    assert "abbreviation" not in generated_detectors("fr").names()
