"""Unicode's formal name aliases of every type, ICU's corrections and the snapshot's rest."""

import hashlib
import importlib.util
from collections import Counter
from pathlib import Path

import icu
import pytest

from icukit import char_from_name, get_char_aliases, get_char_info, get_char_name
from icukit import ucd_name_aliases as module
from icukit.ucd_name_aliases import (
    ALIAS_TYPES,
    icu_unicode_version,
    snapshot_unicode_version,
    ucd_name_aliases,
)

TOOL = Path(__file__).parents[1] / "tools" / "ucd_name_aliases.py"
DATA = Path(module.__file__).parent / "data" / "ucd_name_aliases"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("ucd_name_aliases_tool", TOOL)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


_SAME_UNICODE = module._version_key(snapshot_unicode_version()) == module._version_key(
    icu_unicode_version()
)
same_unicode = pytest.mark.skipif(
    not _SAME_UNICODE,
    reason="ICU's Unicode is not the snapshot's; the snapshot can be remade with "
    "tools/ucd_name_aliases.py",
)


def test_the_snapshot_records_the_tools_pin(tool):
    header, _rows = module._read()
    assert header["unicode-version"] == tool.UNICODE_VERSION
    assert header["source"] == tool.SOURCE_URL
    assert header["sha256"] == tool.SHA256


def test_the_unicode_license_ships_beside_the_data(tool):
    text = (DATA / "LICENSE").read_bytes()
    assert hashlib.sha256(text).hexdigest() == tool.LICENSE_SHA256
    assert text.startswith(b"UNICODE LICENSE V3")


def test_the_snapshot_holds_no_corrections_since_those_are_icus():
    kinds = {kind for _cp, _alias, kind in ucd_name_aliases()}
    assert kinds == set(ALIAS_TYPES) - {"correction"}


@same_unicode
def test_the_snapshot_of_unicode_17_by_type():
    """Pinned to the file: NameAliases.txt 17.0.0 has 481 aliases, 39 of them ICU's."""
    counts = Counter(kind for _cp, _alias, kind in ucd_name_aliases())
    assert counts == {"control": 84, "alternate": 1, "figment": 3, "abbreviation": 354}


@same_unicode
def test_icu_resolves_none_of_the_snapshots_aliases():
    """The one namespace: no snapshot alias is any name or label ICU knows."""
    choices = [
        icu.UCharNameChoice.UNICODE_CHAR_NAME,
        icu.UCharNameChoice.CHAR_NAME_ALIAS,
        icu.UCharNameChoice.EXTENDED_CHAR_NAME,
    ]
    for _cp, alias, _kind in ucd_name_aliases():
        for choice in choices:
            with pytest.raises((icu.ICUError, ValueError)):
                icu.Char.charFromName(alias.encode("ascii"), choice)


def test_every_snapshot_alias_resolves_to_its_code_point():
    for code_point, alias, _kind in ucd_name_aliases():
        assert char_from_name(alias) == chr(code_point)
        assert char_from_name(alias.lower(), "alias") == chr(code_point)


@pytest.mark.parametrize(
    ("name", "code_point"),
    [
        ("BEL", 0x07),
        ("ALERT", 0x07),
        ("LINE FEED", 0x0A),
        ("NBSP", 0xA0),
        ("BYTE ORDER MARK", 0xFEFF),
        ("ZWJ", 0x200D),
        ("padding character", 0x80),
        # A correction: ICU's, found by ICU.
        ("PRESENTATION FORM FOR VERTICAL RIGHT WHITE LENTICULAR BRACKET", 0xFE18),
    ],
)
def test_alias_lookup(name, code_point):
    assert char_from_name(name) == chr(code_point)
    assert char_from_name(name, "alias") == chr(code_point)


def test_get_char_aliases():
    assert get_char_aliases("\x07") == [
        {"alias": "ALERT", "type": "control"},
        {"alias": "BEL", "type": "abbreviation"},
    ]
    assert get_char_aliases("﻿") == [
        {"alias": "BYTE ORDER MARK", "type": "alternate"},
        {"alias": "BOM", "type": "abbreviation"},
        {"alias": "ZWNBSP", "type": "abbreviation"},
    ]
    assert get_char_aliases("︘") == [
        {
            "alias": "PRESENTATION FORM FOR VERTICAL RIGHT WHITE LENTICULAR BRACKET",
            "type": "correction",
        }
    ]
    assert get_char_aliases("A") == []


def test_the_alias_name_choice_stays_the_correction():
    assert get_char_name("\x07", "alias") == ""
    assert get_char_name("Ƣ", "alias") == "LATIN CAPITAL LETTER GHA"


def test_get_char_info_lists_the_aliases():
    assert get_char_info("\xa0")["aliases"] == [{"alias": "NBSP", "type": "abbreviation"}]
    assert get_char_info("Ƣ")["aliases"] == [
        {"alias": "LATIN CAPITAL LETTER GHA", "type": "correction"}
    ]


def test_get_char_aliases_rejects_more_than_one_character():
    with pytest.raises(ValueError, match="single character"):
        get_char_aliases("ab")


@pytest.fixture
def fixture_snapshot(monkeypatch):
    """A snapshot of two rows, one for a code point ICU has never assigned (U+0378)."""
    rows = ((0x0007, "BEL", "abbreviation"), (0x0378, "NOT A CHARACTER", "abbreviation"))

    def install(version):
        monkeypatch.setattr(module, "_read", lambda: ({"unicode-version": version}, rows))
        module.ucd_name_aliases.cache_clear()

    yield install
    module.ucd_name_aliases.cache_clear()


def test_a_newer_icu_keeps_every_alias_of_the_snapshot(fixture_snapshot):
    fixture_snapshot("1.1.0")
    assert [row[1] for row in module.ucd_name_aliases()] == ["BEL", "NOT A CHARACTER"]


def test_an_older_icu_drops_the_aliases_of_what_it_has_not_assigned(fixture_snapshot):
    fixture_snapshot("999.0.0")
    assert [row[1] for row in module.ucd_name_aliases()] == ["BEL"]


def test_the_versions_compare_without_trailing_zeros():
    assert module._version_key("17.0.0") == module._version_key("17.0") == (17,)
    assert module._version_key("16.0") < module._version_key("17.0.0")


def test_the_tool_reads_the_ucd_format(tool):
    text = (
        "# comment\n"
        "\n"
        "0007;ALERT;control\n"
        "0007;BEL;Abbreviation\n"
        "01A2;LATIN CAPITAL LETTER GHA;correction # trailing comment\n"
    )
    rows = tool.read_aliases(text)
    assert rows == [
        ("0007", "ALERT", "control"),
        ("0007", "BEL", "abbreviation"),
        ("01A2", "LATIN CAPITAL LETTER GHA", "correction"),
    ]
    rendered = tool.render(rows)
    assert rendered.endswith("0007\tALERT\tcontrol\n0007\tBEL\tabbreviation\n")
    assert "GHA" not in rendered


def test_the_tool_refuses_an_unknown_type(tool):
    with pytest.raises(SystemExit, match="unknown alias type"):
        tool.read_aliases("0007;BEL;nickname\n")


def test_the_tool_checks_that_icu_carries_exactly_the_corrections(tool):
    tool.check_icu(
        [("01A2", "LATIN CAPITAL LETTER GHA", "correction"), ("0007", "BEL", "abbreviation")]
    )
    with pytest.raises(SystemExit, match="exactly the correction aliases"):
        tool.check_icu([("0007", "BEL", "correction")])
    with pytest.raises(SystemExit, match="exactly the correction aliases"):
        tool.check_icu([("01A2", "LATIN CAPITAL LETTER GHA", "abbreviation")])


def test_the_tool_refuses_a_bad_checksum(tool, tmp_path):
    path = tmp_path / "NameAliases.txt"
    path.write_text("0007;BEL;abbreviation\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="checksum mismatch"):
        tool.fetch(tool.SOURCE_URL, tool.SHA256, path)


@same_unicode
def test_the_snapshot_is_what_the_tool_renders_from_its_own_rows(tool):
    """Byte for byte: rendering the snapshot's rows gives the snapshot back."""
    rows = [(f"{cp:04X}", alias, kind) for cp, alias, kind in module._read()[1]]
    assert tool.render(rows) == (DATA / "NameAliases.tsv").read_text(encoding="utf-8")
