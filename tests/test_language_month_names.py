"""Month names of every locale of the language."""

import pytest

from icukit.recognize import FlexibleTextDateDetector


def _dates(text, **options):
    detector = FlexibleTextDateDetector("en_US", **options)
    return [(d["text"], d["value"].fields) for d in detector.detect(text)]


@pytest.mark.parametrize(
    "text, fields",
    [
        ("Sept 2004", (("y", 2004), ("M", 9))),
        ("Sept 5, 2010", (("y", 2010), ("M", 9), ("d", 5))),
        ("5 Sept 2010", (("y", 2010), ("M", 9), ("d", 5))),
    ],
)
def test_another_locales_month_name_reads(text, fields):
    # "Sept" is en_GB's abbreviated September; en_US writes "Sep".
    assert _dates(text) == [(text, fields)]


def test_the_choice_of_locales_governs_the_month_names():
    assert _dates("Sept 2004", locales=()) == []
