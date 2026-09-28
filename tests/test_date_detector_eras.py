"""The strict date detector reads an era where the locale's pattern writes one."""

import icu
import pytest

from icukit.detectors import DateDetector, _date_form, _pattern_runs, date_detectors


def _surface(detector, era=None, year=2024, month=2, day=5):
    """ICU's own text for a date in the detector's locale and calendar (month 0-based)."""
    calendar = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(detector.locale))
    calendar.clear()
    if era is not None:
        calendar.set(icu.Calendar.ERA, era)
    calendar.set(icu.Calendar.YEAR, year)
    calendar.set(icu.Calendar.MONTH, month)
    calendar.set(icu.Calendar.DATE, day)
    return detector._df.format(calendar.getTime()), calendar


def _era_width(pattern):
    return next(width for letter, width in _pattern_runs(pattern) if letter == "G")


# th's year pattern carries the Buddhist era; lrc, mzn, and ps write the Persian one.
@pytest.mark.parametrize("locale", ["th", "lrc", "mzn", "ps"])
@pytest.mark.parametrize("skeleton", ["y", "GyMMMd", "GyMd"])
def test_a_locale_whose_pattern_writes_an_era_reads_it(locale, skeleton):
    detector = DateDetector(locale, skeleton)
    today = icu.Calendar.createInstance(icu.TimeZone.getGMT(), icu.Locale(locale))
    year = today.get(icu.Calendar.YEAR)
    surface, calendar = _surface(detector, year=year)
    hits = [d for d in detector.detect(surface) if d["text"] == surface]
    assert len(hits) == 1
    value = hits[0]["value"]
    assert value.calendar == today.getType()
    fields = dict(value.fields)
    assert fields["G"] == calendar.get(icu.Calendar.ERA)
    assert fields["y"] == year


@pytest.mark.parametrize("locale", ["th", "lrc", "mzn", "ps"])
def test_a_gang_with_an_era_pattern_builds(locale):
    gang = date_detectors(locale, ["y", "yMd", "yMMMd", "GyMMMd"])
    assert "date:y" in gang.names()


@pytest.mark.parametrize("year", [2024, 1066])
def test_a_four_digit_year_before_the_common_era_reads_by_default(year):
    detector = DateDetector("en", "GyMMMd")
    surface, _ = _surface(detector, era=0, year=year, month=2, day=15)
    hits = [d for d in detector.detect(surface) if d["text"] == surface]
    assert [dict(d["value"].fields) for d in hits] == [{"G": 0, "y": year, "M": 3, "d": 15}]


def test_a_short_year_beside_an_era_is_the_guarded_readers():
    default = DateDetector("en", "GyMMMd")
    guarded = DateDetector("en", "GyMMMd", short_years=True)
    assert guarded.type == "date:short-year:GyMMMd"
    short, _ = _surface(default, era=0, year=44, month=2, day=15)
    assert default.detect(short) == []
    hits = [d for d in guarded.detect(short) if d["text"] == short]
    # The year as written: 44 BC, never widened to 2044.
    assert [dict(d["value"].fields) for d in hits] == [{"G": 0, "y": 44, "M": 3, "d": 15}]
    long, _ = _surface(default, era=0, year=2024, month=2, day=15)
    assert guarded.detect(long) == []


def test_the_guarded_short_year_reader_needs_an_era():
    with pytest.raises(ValueError):
        DateDetector("en", "yMMMd", short_years=True)


# A short number before a short era is as often a count or a clock: 100 meters and five
# PM in Arabic, and the like.
@pytest.mark.parametrize(
    "locale, text, surface",
    [
        ("ar", "طوله 100 م", "100 م"),
        ("ar", "الساعة 5 م", "5 م"),
        ("id", "jaraknya 5 M", "5 M"),
        ("en", "I have 7 AD units", "7 AD"),
        ("en", "Route 99 BC", "99 BC"),
        ("en", "the AD campaign ran 3 AD spots", "3 AD"),
    ],
)
def test_a_short_number_before_an_era_is_a_date_only_when_guarded(locale, text, surface):
    from icukit.engine import DEFAULT_FAMILIES, GUARDED_FAMILIES, generated_detectors

    def dates(families):
        gang = generated_detectors(locale, families)
        return {d["text"] for d in gang.detect(text) if d["type"].startswith("date")}

    # Only where this ICU writes the era as the text does.
    era = icu.SimpleDateFormat("G", icu.Locale(locale))
    if surface.split()[-1] not in list(era.getDateFormatSymbols().getEras()):
        pytest.skip("this ICU writes the locale's era otherwise")
    assert dates(DEFAULT_FAMILIES) == set()
    assert surface in dates((*DEFAULT_FAMILIES, *GUARDED_FAMILIES))


@pytest.mark.parametrize("skeleton", ["GyMMMd", "GGGGyMMMMd", "GGGGGyMd"])
def test_the_era_capture_is_icus_era_text_in_the_patterns_width(skeleton):
    detector = DateDetector("en", skeleton)
    surface, calendar = _surface(detector, era=1)
    (hit,) = [d for d in detector.detect(surface) if d["text"] == surface]
    (era,) = [c for c in hit["captures"] if c.name == "era"]
    position = icu.FieldPosition(icu.DateFormat.kEraField)
    detector._df.format(calendar.getTime(), position)
    assert era.text == surface[position.getBeginIndex() : position.getEndIndex()]
    assert era.value == 1
    assert era.form == _date_form("G", _era_width(detector.pattern))
    assert ("G", era.form) in hit["spec"].field_forms


def test_an_era_is_read_only_where_the_pattern_writes_it():
    detector = DateDetector("en", "GyMMMd")
    surface, calendar = _surface(detector, era=1)
    position = icu.FieldPosition(icu.DateFormat.kEraField)
    detector._df.format(calendar.getTime(), position)
    era = surface[position.getBeginIndex() : position.getEndIndex()]
    assert detector.detect(era) == []
    assert detector.detect(f"in {era} times") == []


def test_the_refusal_no_longer_names_the_era():
    with pytest.raises(ValueError) as error:
        DateDetector("en", "yQQQ")
    assert "era" not in str(error.value)
    assert "quarter" in str(error.value)


def test_a_number_without_the_era_is_not_parsed_as_a_date():
    # A lenient parse let the era go missing and ran from "1" into the Tamil letters,
    # ending inside a grapheme; the text holds no date of this pattern.
    detector = DateDetector("ta", "GyMEd")
    assert detector.detect("1,234.56 சிங்கப்பூர் டாலர்கள்") == []
