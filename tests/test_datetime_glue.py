"""A date and a time joined as CLDR's date-time patterns join them."""

import pytest

from icukit.recognize import FlexibleDateTimeDetector, _language_datetime_glue


def _readings(text):
    return [(d["text"], d["value"].fields) for d in FlexibleDateTimeDetector("en_US").detect(text)]


def test_the_glue_is_cldrs():
    assert (True, ", ", "{1}, {0}") in _language_datetime_glue("en")
    assert (True, " at ", "{1} 'at' {0}") in _language_datetime_glue("en")


@pytest.mark.parametrize(
    "text, fields",
    [
        ("Mar 5, 2024, 2:07 PM", (("y", 2024), ("M", 3), ("d", 5), ("H", 14), ("m", 7))),
        ("5 March 2024 at 14:07", (("y", 2024), ("M", 3), ("d", 5), ("H", 14), ("m", 7))),
    ],
)
def test_a_date_and_time_read_whole(text, fields):
    assert _readings(text) == [(text, fields)]


def test_a_time_with_its_zone_reads_both_ways():
    texts = [text for text, _fields in _readings("July 4, 1999 at 12:05:00 AM EDT")]
    assert texts == ["July 4, 1999 at 12:05:00 AM", "July 4, 1999 at 12:05:00 AM EDT"]


def test_each_date_reading_is_composed():
    # "3/5/24" reads as March 5 and as 3 May; each joins the time.
    months = sorted(dict(fields)["M"] for _text, fields in _readings("3/5/24, 14:07"))
    assert months == [3, 5]


@pytest.mark.parametrize("text", ["March 5, 2024", "see 2:07 PM, Mar 5", "Mar 5, 2024; 2:07 PM"])
def test_what_no_glue_joins_is_not_read(text):
    assert _readings(text) == []


def test_the_spec_composes_the_patterns_as_cldr_does():
    detection = FlexibleDateTimeDetector("en_US").detect("Mar 5, 2024, 2:07 PM")[0]
    assert detection["spec"].pattern.startswith("MMM d, y, ")
