"""Pure group constructors that assemble a common family of detectors into a gang."""

import icu

from icukit.detectors import (
    DateDetector,
    DetectorSet,
    all_detectors,
    date_detectors,
    number_detectors,
)


def test_date_detectors_one_per_skeleton_deduped():
    gang = date_detectors("en_US", ["yMd", "yMMMd", "yMd"])

    assert isinstance(gang, DetectorSet)
    assert gang.names() == ("date:yMd", "date:yMMMd")  # the repeated skeleton collapses


def test_number_detectors_defaults_and_currencies():
    assert number_detectors("en_US").names() == ("number:decimal", "number:percent")

    with_currencies = number_detectors("en_US", percent=False, currencies=["USD", "EUR"])
    assert with_currencies.names() == (
        "number:decimal",
        "number:currency:USD",
        "number:currency:EUR",
    )

    assert number_detectors("en_US", decimal=False, percent=False).names() == ()


def test_all_detectors_composes_dates_and_numbers():
    gang = all_detectors("en_US", ["yMd"], currencies=["USD"])

    assert set(gang.names()) == {
        "date:yMd",
        "number:decimal",
        "number:percent",
        "number:currency:USD",
    }


def test_group_gang_detects_a_date_and_a_number_together():
    calendar = icu.Calendar.createInstance(
        icu.TimeZone.getGMT(), icu.Locale("en_US@calendar=gregorian")
    )
    calendar.clear()
    calendar.set(2026, 0, 3)
    date_surface = DateDetector("en_US", "yMd")._df.format(calendar.getTime())
    number_surface = icu.NumberFormat.createInstance(icu.Locale("en_US")).format(1234)
    text = f"{date_surface} and {number_surface}"

    found = {(d["type"], d["text"]) for d in all_detectors("en_US", ["yMd"]).detect(text)}

    assert ("date:yMd", date_surface) in found
    assert ("number:decimal", number_surface) in found
