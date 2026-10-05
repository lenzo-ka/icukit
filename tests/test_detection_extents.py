import pytest

from icukit import DEFAULT_READER_CAP_CHARS, Extent, extent_report
from icukit.detectors import NumberDetector
from icukit.engine import reader_set
from icukit.stream import _extent_violations


def test_extent_literal():
    assert NumberDetector("en_US", "decimal").extent() == Extent(
        chunks=2,
        joins=frozenset(),
        join_chars="",
        cap_chars=None,
        left_chunks=None,
        left_joins=frozenset(),
        left_join_chars=r"[\p{Nd}\p{Sm}]",
        source='ICU DecimalFormatSymbols en_US: grouping "," and affixes hold no White_Space',
    )


@pytest.mark.parametrize("locale", ["en_US", "de_DE", "fr_FR", "ja_JP", "zh_CN", "th_TH", "ar_EG"])
def test_extent_declared_for_every_reader(locale):
    detectors = reader_set(locale, flexible=True, guarded=True)
    report = extent_report(detectors)
    assert len(report) == len(detectors.detectors)
    assert all(row.extent.source for row in report)
    assert all(
        row.cap_chars == DEFAULT_READER_CAP_CHARS for row in report if row.extent.chunks is None
    )


@pytest.mark.parametrize(
    ("locale", "text"),
    [
        ("en_US", "I paid 1,234 and 56 more."),
        ("en_US", "5 May 2024 at 2:30 PM"),
        ("en_US", "ten thousand dollars and 12 kg"),
        ("fr_FR", "de 1 à 2 – 3 – 4 x"),
        ("ja_JP", "2024年5月3日 12時30分"),
    ],
)
def test_extent_sound_on_fixtures(locale, text):
    detectors = reader_set(locale, flexible=True, guarded=True)
    assert _extent_violations(text, detectors.detect(text), detectors) == ()


def test_signed_number_within_declared_extent():
    detectors = reader_set("en_US", flexible=True, guarded=True)
    text = "x -5 y and -1,234.5 z"
    assert _extent_violations(text, detectors.detect(text), detectors.detectors) == ()
