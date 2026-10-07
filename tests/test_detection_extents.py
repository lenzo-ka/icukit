import pytest

from icukit import DEFAULT_READER_CAP_CHARS, Extent, extent_report
from icukit.detectors import NumberDetector
from icukit.engine import reader_set
from icukit.stream import _extent_violations


def test_extent_literal():
    assert NumberDetector("en_US", "decimal").extent() == Extent(
        chunks=2,
        joins=frozenset(),
        join_chars=r"[\p{N}\p{S}\p{Cf}]",
        cap_chars=None,
        left_chunks=None,
        left_joins=frozenset(),
        left_join_chars=r"[\p{Nd}\p{Sm}\p{Cf}]",
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


@pytest.mark.parametrize(
    ("locale", "text"),
    [
        ("af_ZA", "-42,50 euro"),
        ("agq_CM", "-42,50€"),
        ("agq_CM", "-42,50 Bɔ̀ŋ è Bèletì"),
        ("agq_CM", "tsuʔumè 7 ndzɔ̀ŋɔ̀chwaʔàkaa wo 2024"),
        ("af_ZA", "12:05:00\u202fvm. Noord-Amerikaanse oostelike dagligtyd"),
        ("af_ZA", "1 500e."),
        ("af_ZA", "1\u00a0000ste"),
        ("af_ZA", "n.C. 2024-12-25, Wo."),
        ("af_ZA", "-9:30:00\u202fvm. GMT-5"),
        ("ja_JP", "-42.50\u30e6\u30fc\u30ed"),
        (
            "tg_TJ",
            "\u041c\u0430\u0440\u0442\u0438 2024 \u2013 \u0410\u043f\u0440\u0435\u043b\u0438 2025",
        ),
        ("yo_NG", "\u200f2024 Oshù Ɛrɛ̀nà 5\u2009–\u20092025 Oshù Ìgbé 9"),
    ],
)
def test_report_extent_regressions(locale, text):
    detectors = reader_set(locale, flexible=True, guarded=True)
    assert _extent_violations(text, detectors.detect(text), detectors) == ()
