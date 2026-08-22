"""Tests for the abbreviation lexicon grammar and loader."""

from pathlib import Path

import pytest

from icukit.abbreviations import (
    BREAK_AMBIGUOUS,
    BREAK_SUPPRESS,
    AbbreviationLexicon,
    Entry,
    Expansion,
    Pattern,
    available_locales,
    load_lexicon,
    load_lexicon_file,
    parse_lexicon,
)
from icukit.errors import AbbreviationError

_DATA_DIR = Path(__file__).parent.parent / "icukit" / "data" / "abbreviations"
_RNG_PATH = _DATA_DIR / "abbreviations.rng"
_EN_PATH = _DATA_DIR / "en.xml"
_INVALID_FIXTURE = Path(__file__).parent / "data" / "abbreviations_invalid.xml"

# Enumerated vocabularies the grammar is expected to enforce. Kept here so the
# loader tests and the grammar stay in agreement about the controlled sets.
_SENSES = {
    "title",
    "saint",
    "thoroughfare",
    "place",
    "compass",
    "month",
    "weekday",
    "region",
    "organization",
    "number",
    "given-name",
    "time",
    "era",
    "phrase",
    "other",
}
_CUES = {
    "precedes-name",
    "follows-name",
    "precedes-number",
    "address",
    "date",
    "measurement",
}
_KINDS = {"single-initial", "multi-part-initials", "uncased-latin"}
_BREAKS = {BREAK_SUPPRESS, BREAK_AMBIGUOUS}


def _relaxng():
    """Compile the RELAX NG grammar, skipping if lxml is unavailable."""
    lxml_etree = pytest.importorskip("lxml.etree")
    return lxml_etree, lxml_etree.RelaxNG(lxml_etree.parse(str(_RNG_PATH)))


class TestGrammarValidation:
    """The RELAX NG grammar accepts en.xml and rejects malformed input."""

    def test_en_xml_is_valid(self):
        lxml_etree, rng = _relaxng()
        doc = lxml_etree.parse(str(_EN_PATH))
        assert rng.validate(doc), rng.error_log

    def test_invalid_fixture_is_rejected(self):
        # Proves the grammar constrains: a raw-regex @kind and an out-of-vocab
        # @sense must not validate.
        lxml_etree, rng = _relaxng()
        doc = lxml_etree.parse(str(_INVALID_FIXTURE))
        assert not rng.validate(doc)

    @pytest.mark.parametrize(
        "xml",
        [
            # Raw regex smuggled into @kind (the seed's broken ":re" form).
            '<abbreviations xml:lang="en"><pattern kind="[A-Z]."'
            ' break="suppress"/></abbreviations>',
            # A pattern may carry no text content, so a regex cannot hide there.
            '<abbreviations xml:lang="en"><pattern kind="single-initial"'
            ' break="suppress">[A-Z].</pattern></abbreviations>',
            # Out-of-vocabulary @break.
            '<abbreviations xml:lang="en"><entry break="maybe">'
            "<surface>Dr.</surface></entry></abbreviations>",
            # Missing required @break.
            '<abbreviations xml:lang="en"><entry><surface>Dr.</surface></entry></abbreviations>',
            # Missing required <surface>.
            '<abbreviations xml:lang="en"><entry break="suppress">'
            '<expansion sense="title">Doctor</expansion></entry></abbreviations>',
            # Out-of-vocabulary @sense.
            '<abbreviations xml:lang="en"><entry break="suppress"><surface>Dr.</surface>'
            '<expansion sense="streetish">Drive</expansion></entry></abbreviations>',
            # Out-of-vocabulary @cue.
            '<abbreviations xml:lang="en"><entry break="suppress"><surface>No.</surface>'
            '<expansion sense="number" cue="whenever">Number</expansion></entry></abbreviations>',
            # Out-of-vocabulary @also.
            '<abbreviations xml:lang="en"><entry break="suppress" also="nickname">'
            "<surface>Jun.</surface></entry></abbreviations>",
            # Unknown child element.
            '<abbreviations xml:lang="en"><widget/></abbreviations>',
            # Missing required xml:lang.
            '<abbreviations><entry break="suppress"><surface>Dr.</surface></entry></abbreviations>',
        ],
    )
    def test_grammar_rejects_malformed(self, xml):
        lxml_etree, rng = _relaxng()
        doc = lxml_etree.fromstring(xml.encode("utf-8"))
        assert not rng.validate(doc), f"grammar wrongly accepted: {xml}"

    def test_grammar_accepts_typed_pattern(self):
        lxml_etree, rng = _relaxng()
        xml = (
            '<abbreviations xml:lang="en">'
            '<pattern kind="multi-part-initials" break="suppress"/>'
            "</abbreviations>"
        )
        doc = lxml_etree.fromstring(xml.encode("utf-8"))
        assert rng.validate(doc), rng.error_log


class TestLoader:
    """The loader parses en.xml into the typed model."""

    def test_load_lexicon_defaults_to_english(self):
        lex = load_lexicon()
        assert isinstance(lex, AbbreviationLexicon)
        assert lex.language == "en"
        assert lex.status == "draft"
        assert lex.entries
        assert lex.patterns

    def test_available_locales_includes_english(self):
        assert "en" in available_locales()

    def test_model_types(self):
        lex = load_lexicon("en")
        assert all(isinstance(e, Entry) for e in lex.entries)
        assert all(isinstance(p, Pattern) for p in lex.patterns)
        for entry in lex.entries:
            assert all(isinstance(x, Expansion) for x in entry.expansions)

    def test_vocabularies_are_within_the_grammar_sets(self):
        # Every parsed value stays inside the documented controlled vocab.
        lex = load_lexicon("en")
        for entry in lex.entries:
            assert entry.break_behavior in _BREAKS
            assert entry.also in (None, "proper-name", "common-word")
            for exp in entry.expansions:
                assert exp.sense in _SENSES
                assert exp.cue in (None, *_CUES)
        for pattern in lex.patterns:
            assert pattern.kind in _KINDS
            assert pattern.break_behavior in _BREAKS

    def test_surfaces_are_unique(self):
        lex = load_lexicon("en")
        surfaces = lex.surfaces()
        assert len(surfaces) == len(set(surfaces))

    def test_saint_street_is_ambiguous(self):
        lex = load_lexicon("en")
        entry = lex.get("St.")
        assert entry is not None
        assert "St." in lex
        assert entry.is_ambiguous_expansion
        values = {e.value for e in entry.expansions}
        assert values == {"Saint", "Street"}
        senses = {e.sense for e in entry.expansions}
        assert senses == {"saint", "thoroughfare"}

    def test_doctor_drive_is_ambiguous(self):
        lex = load_lexicon("en")
        entry = lex.get("Dr.")
        assert entry is not None
        values = {e.value for e in entry.expansions}
        assert values == {"Doctor", "Drive"}

    def test_number_word_is_break_ambiguous(self):
        # "No." can be the word "No" ending a sentence.
        lex = load_lexicon("en")
        entry = lex.get("No.")
        assert entry is not None
        assert entry.break_behavior == BREAK_AMBIGUOUS
        assert entry.is_break_ambiguous
        assert entry.also == "common-word"

    def test_proper_name_flag(self):
        lex = load_lexicon("en")
        entry = lex.get("Jun.")
        assert entry is not None
        assert entry.also == "proper-name"
        assert [e.value for e in entry.expansions] == ["June"]

    def test_suppress_entry_may_have_no_expansion(self):
        lex = load_lexicon("en")
        entry = lex.get("Ms.")
        assert entry is not None
        assert entry.break_behavior == BREAK_SUPPRESS
        assert entry.expansions == ()
        assert not entry.is_ambiguous_expansion

    def test_patterns_are_typed_kinds(self):
        lex = load_lexicon("en")
        kinds = {p.kind for p in lex.patterns}
        assert kinds == _KINDS
        single = next(p for p in lex.patterns if p.kind == "single-initial")
        assert single.break_behavior == BREAK_AMBIGUOUS


class TestLoaderErrors:
    """The loader parses safely and reports problems as AbbreviationError."""

    def test_unknown_language_raises(self):
        with pytest.raises(AbbreviationError):
            load_lexicon("zz")

    def test_missing_file_raises(self):
        with pytest.raises(AbbreviationError):
            load_lexicon_file(Path("/nonexistent/does-not-exist.xml"))

    def test_wrong_root_raises(self):
        with pytest.raises(AbbreviationError):
            parse_lexicon('<lexicon xml:lang="en"/>')

    def test_missing_lang_raises(self):
        with pytest.raises(AbbreviationError):
            parse_lexicon("<abbreviations/>")

    def test_malformed_xml_raises(self):
        with pytest.raises(AbbreviationError):
            parse_lexicon("<abbreviations xml:lang='en'><entry></abbreviations>")

    def test_doctype_is_forbidden(self):
        # XXE / entity-expansion defense: a DOCTYPE must be refused outright.
        xml = '<!DOCTYPE x [<!ENTITY e "boom">]><abbreviations xml:lang="en"/>'
        with pytest.raises(AbbreviationError):
            parse_lexicon(xml)

    def test_external_entity_is_forbidden(self):
        xml = (
            '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>'
            '<abbreviations xml:lang="en"><entry break="suppress">'
            "<surface>&e;</surface></entry></abbreviations>"
        )
        with pytest.raises(AbbreviationError):
            parse_lexicon(xml)

    def test_load_invalid_fixture_still_parses_structurally(self):
        # The invalid fixture violates the grammar's vocabularies but is well
        # formed XML, so the (grammar-free) loader parses it; validation is the
        # grammar's job, exercised in TestGrammarValidation.
        lex = load_lexicon_file(_INVALID_FIXTURE)
        assert lex.language == "en"
        assert lex.get("Dr.") is not None
