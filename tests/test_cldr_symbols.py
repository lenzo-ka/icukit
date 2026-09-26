"""CLDR's per-locale names of symbols, as the ``symbol`` abbreviation kind lists them."""

import importlib.util
import sys
from pathlib import Path

import icu
import pytest

from icukit import cldr_symbols, icu_abbreviations
from icukit.cldr_symbols import (
    cldr_locale,
    cldr_symbol_names,
    icu_cldr_version,
    snapshot_cldr_version,
)

# The module, not the function of the same name the package exports.
abbreviations = sys.modules["icukit.icu_abbreviations"]

TOOL = Path(__file__).parents[1] / "tools" / "cldr_symbol_names.py"

# What the rows' source is under the ICU running the tests: "cldr" when ICU's CLDR is
# the snapshot's, and the snapshot's CLDR named otherwise.
_SOURCE = (
    "cldr" if snapshot_cldr_version() == icu_cldr_version() else f"cldr-{snapshot_cldr_version()}"
)


def _symbol(locale, surface, **options):
    rows = [
        row
        for row in icu_abbreviations(locale, kinds=["symbol"], **options)
        if row.surface == surface
    ]
    assert len(rows) == 1, rows
    return rows[0]


@pytest.mark.parametrize(
    "locale, surface, key, name",
    [
        ("en_US", "&", "U+0026", "ampersand"),
        ("de_DE", "&", "U+0026", "Et-Zeichen"),
        ("fr_FR", "±", "U+00B1", "plus-moins"),
        ("ja_JP", "→", "U+2192", "右向矢印"),
        ("en_US", "©", "U+00A9", "copyright"),
        ("en_US", "°", "U+00B0", "degree"),
    ],
)
def test_a_symbol_is_named_in_the_language_tts_name_first(locale, surface, key, name):
    row = _symbol(locale, surface)
    assert (row.kind, row.key, row.width, row.source) == ("symbol", key, "cldr", _SOURCE)
    assert row.expansions[0] == name


def test_the_keywords_follow_the_name():
    assert _symbol("en_US", "&").expansions == ("ampersand", "and", "et")


def test_a_locale_inherits_the_names_it_does_not_give():
    # en_GB gives none for "&": it inherits en's through en_001.
    assert _symbol("en_GB", "&", locales=()).expansions[0] == "ampersand"
    # Each value is inherited on its own: for "↚" en_001 overrides en's name and
    # keywords, and en_GB takes en_001's name but gives its own keywords.
    assert _symbol("en_US", "↚", locales=()).expansions == (
        "leftwards arrow stroke",
        "arrow",
        "leftwards",
        "stroke",
    )
    assert _symbol("en_AU", "↚", locales=()).expansions == ("leftwards arrow with stroke",)
    assert _symbol("en_GB", "↚", locales=()).expansions == (
        "leftwards arrow with stroke",
        "arrow",
        "leftwards",
        "stroke",
    )


def _names(locale):
    return {cp: tts for cp, tts, _words in cldr_symbol_names(locale)}


def test_a_script_locale_does_not_inherit_the_language_default_script():
    # CLDR's parentLocales sends sr_Latn to root, not to Cyrillic sr.
    cyrillic = _names("sr_RS")
    latin = _names("sr_Latn_RS")
    assert cyrillic["&"] != latin["&"]
    assert all(ord(c) < 0x400 for c in latin["&"])


@pytest.mark.parametrize(
    "locale, cldr, reads_as",
    [
        ("zh_TW", "zh_Hant_TW", "zh_Hant"),
        ("zh_HK", "zh_Hant_HK", "zh_Hant_HK"),
        ("sr_ME", "sr_Latn_ME", "sr_Latn"),
        ("zh_CN", "zh_CN", "zh"),
        ("en_GB", "en_GB", "en_GB"),
        ("iw_IL", "he_IL", "he"),
    ],
)
def test_a_locale_reads_the_cldr_locale_its_script_names(locale, cldr, reads_as):
    assert cldr_locale(locale) == cldr
    assert cldr_symbol_names(locale) == cldr_symbol_names(reads_as)


def test_traditional_chinese_and_latin_serbian_are_not_their_default_scripts():
    assert _names("zh_TW")["&"] != _names("zh")["&"]
    assert _names("sr_ME")["&"] != _names("sr")["&"]
    # The language-wide list for zh_TW names its own locale's symbols first.
    assert _symbol("zh_TW", "&").expansions[0] == _names("zh_Hant")["&"]


def test_a_script_not_the_languages_likely_one_inherits_from_root():
    # CLDR's nonlikelyScript rule: ru_Latn is not ru's child, so it has no Cyrillic
    # names, and CLDR gives it none of its own.
    assert cldr_locale("ru_Latn") == "ru_Latn"
    assert "&" in _names("ru")
    assert cldr_symbol_names("ru_Latn") == ()


def test_the_kind_lists_no_emoji():
    rows = icu_abbreviations("en_US", kinds=["symbol"])
    assert len(rows) > 100
    rgi_emoji = icu.UnicodeSet("[:RGI_Emoji:]")
    for row in rows:
        assert not rgi_emoji.contains(row.surface), row
        for c in row.surface:
            assert not icu.Char.hasBinaryProperty(c, icu.UProperty.EMOJI_PRESENTATION), row
    surfaces = {row.surface for row in rows}
    assert "😀" not in surfaces and "👍" not in surfaces


def test_a_symbol_is_listed_once_in_the_kind_and_kept_in_the_others():
    rows = icu_abbreviations("en_US", kinds=["symbol"])
    keys = [(row.surface, row.key) for row in rows]
    assert len(keys) == len(set(keys))
    assert _symbol("en_US", "%").expansions[0] == "percent"


def test_the_rows_say_whether_icu_and_the_snapshot_share_a_cldr():
    assert snapshot_cldr_version()
    assert {row.source for row in icu_abbreviations("en_US", kinds=["symbol"])} == {_SOURCE}


@pytest.mark.skipif(
    snapshot_cldr_version() != icu_cldr_version(),
    reason="ICU's CLDR is not the snapshot's; the rows say so, and the snapshot can be "
    "remade with tools/cldr_symbol_names.py",
)
def test_icu_and_the_snapshot_record_the_same_cldr():
    assert snapshot_cldr_version() == icu_cldr_version()


@pytest.fixture
def fixture_snapshot(tmp_path, monkeypatch):
    """A small snapshot: root, a parent, and children that remove its values."""
    header = "# cldr-version\t48\n"
    files = {
        "_parents.tsv": header + "xx_YY\txx\n",
        "xx.tsv": header + "&\tamp\tand | et\n±\tplus-minus\tsign\n",
        # Removes the parent's tts name for "&", and keeps its keywords.
        "xx_ZZ.tsv": header + "&\t∅∅∅\t\n",
        # Removes the parent's keywords for "&", and both values of "±".
        "xx_YY.tsv": header + "&\t\t∅∅∅\n±\t∅∅∅\t∅∅∅\n",
    }
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    caches = (
        cldr_symbols._parents,
        cldr_symbols._own,
        cldr_symbols._resolved,
        cldr_symbols.cldr_symbol_names,
    )
    for cached in caches:
        cached.cache_clear()
    monkeypatch.setattr(cldr_symbols, "_DATA_DIR", tmp_path)
    yield
    monkeypatch.undo()
    for cached in caches:
        cached.cache_clear()


def test_a_child_removes_what_it_marks_removed(fixture_snapshot):
    assert cldr_symbol_names("xx") == (
        ("&", "amp", ("and", "et")),
        ("±", "plus-minus", ("sign",)),
    )
    assert cldr_symbol_names("xx_ZZ") == (
        ("&", "", ("and", "et")),
        ("±", "plus-minus", ("sign",)),
    )
    assert cldr_symbol_names("xx_YY") == (("&", "amp", ()),)


@pytest.fixture
def fresh_symbol_rows():
    abbreviations._symbol_rows.cache_clear()
    yield
    abbreviations._symbol_rows.cache_clear()


def test_another_cldr_in_icu_still_lists_the_names_and_says_so(monkeypatch, fresh_symbol_rows):
    monkeypatch.setattr(abbreviations, "icu_cldr_version", lambda: "999")
    row = _symbol("en_US", "&")
    assert row.expansions[0] == "ampersand"
    assert row.source == f"cldr-{snapshot_cldr_version()}"


# The snapshot tool, on a fixture: no network.


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("cldr_symbol_names", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ldml(*annotations):
    body = "".join(annotations)
    return f"<ldml><annotations>{body}</annotations></ldml>".encode()


def test_the_tool_keeps_symbols_and_drops_emoji_and_what_is_inherited(tool):
    files = {
        "xx": [
            _ldml(
                '<annotation cp="&amp;">and | amp</annotation>',
                '<annotation cp="&amp;" type="tts">amp</annotation>',
                '<annotation cp="©" type="tts">copy</annotation>',
                '<annotation cp="😀" type="tts">grin</annotation>',
                '<annotation cp="👍🏽" type="tts">thumbs</annotation>',
                '<annotation cp="±" type="tts" draft="unconfirmed">pm</annotation>',
                '<annotation cp="→" type="tts">arrow</annotation>',
            )
        ],
        "xx_YY": [
            _ldml(
                '<annotation cp="&amp;" type="tts">amp</annotation>',
                '<annotation cp="©" type="tts">copyright</annotation>',
                '<annotation cp="→" type="tts">∅∅∅</annotation>',
            )
        ],
        "xx_Zzzz": [_ldml('<annotation cp="#" type="tts">hash</annotation>')],
    }
    deltas = tool.extract(files, {"xx_Zzzz": "root"})
    assert deltas["xx"] == {
        "&": {"keywords": "and | amp", "tts": "amp"},
        "©": {"tts": "copy"},
        "→": {"tts": "arrow"},
    }
    # "&" is inherited unchanged; "©" changes; "→" is removed.
    assert deltas["xx_YY"] == {"©": {"tts": "copyright"}, "→": {"tts": "∅∅∅"}}
    assert deltas["xx_Zzzz"] == {"#": {"tts": "hash"}}


def test_the_tool_reads_the_default_parent_locales(tool):
    xml = (
        b"<supplementalData><parentLocales>"
        b'<parentLocale parent="en_001" locales="en_GB en_AU"/>'
        b'</parentLocales><parentLocales component="collations">'
        b'<parentLocale parent="zh_Hant" locales="yue"/>'
        b"</parentLocales></supplementalData>"
    )
    parents = tool.read_parents(xml)
    assert parents == {"en_GB": "en_001", "en_AU": "en_001"}
    assert [tool.parent_of(x, parents) for x in ("en_GB", "en_001", "en", "root")] == [
        "en_001",
        "en",
        "root",
        None,
    ]


@pytest.mark.parametrize(
    "text, emoji",
    [
        ("©", False),
        ("↔", False),
        ("#", False),
        ("😀", True),
        ("#️⃣", True),
        ("🇺🇸", True),
        ("©️", True),
        ("👍🏽", True),
    ],
)
def test_the_tools_emoji_test_is_icus(tool, text, emoji):
    assert tool.is_emoji(text) is emoji


def test_the_tool_refuses_an_icu_older_than_the_snapshots(tool, tmp_path, monkeypatch):
    (tmp_path / "_parents.tsv").write_text("# icu-version\t999.0\n", encoding="utf-8")
    assert tool.recorded_icu_version(tmp_path) == "999.0"
    monkeypatch.setattr(sys, "argv", ["cldr_symbol_names.py", "--out", str(tmp_path)])
    with pytest.raises(SystemExit, match="older than the snapshot's ICU 999.0"):
        tool.main()


def test_the_snapshot_records_the_icu_and_unicode_it_was_made_under(tool):
    header = (tool.OUT_DIR / "_parents.tsv").read_text(encoding="utf-8")
    assert "# icu-version\t" in header and "# unicode-version\t" in header
