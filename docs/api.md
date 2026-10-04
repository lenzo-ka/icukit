# icukit API Reference

Version: 0.8.0

## Root API index

Names exported by `icukit.__all__` (the `from icukit import ...` surface):

- [`__version__`](#root-api-index) — constant, `icukit`
- [`AvailabilityRow`](#icukitavailability) — class, `icukit.availability`
- [`availability`](#icukitavailability) — function, `icukit.availability`
- [`available_languages`](#icukitavailability) — function, `icukit.availability`
- [`FlexibleCompactDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleCurrencyDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleCurrencyNameDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleDateDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleDateIntervalDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleFractionDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleMeasureDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleNumberDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleOrdinalDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexiblePercentDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleRelativeDateDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleScientificDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleSpelloutDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleTimeDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleTextDateDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleBareHourDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleLoneSpelloutDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleLowercaseRomanDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleMonthNameDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleShortYearDateDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleWeekdayNameDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleNumberRangeDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`AlphanumericRunsDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`AlphanumericRunsValue`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleDateTimeDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleMixedMeasureDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`FlexibleNumericDurationDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`LetterNameDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`PluralNumeralDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`SingleLetterWordDetector`](#icukitrecognize) — class, `icukit.recognize`
- [`DetectorSet`](#icukitdetectors) — class, `icukit.detectors`
- [`CompiledDetectorSet`](#icukitcompiled) — class, `icukit.compiled`
- [`ReaderSpec`](#icukitcompiled) — class, `icukit.compiled`
- [`CompileKey`](#icukitcompiled) — class, `icukit.compiled`
- [`CompileStats`](#icukitcompiled) — class, `icukit.compiled`
- [`TableKey`](#icukitcompiled) — class, `icukit.compiled`
- [`LaneGate`](#start-gates) — class, `icukit`
- [`compile_detectors`](#icukitcompiled) — function, `icukit.compiled`
- [`GatedDetector`](#icukitdetectors) — class, `icukit.detectors`
- [`StartGate`](#start-gates) — class, `icukit`
- [`candidate_starts`](#start-gates) — function, `icukit`
- [`ungated`](#start-gates) — function, `icukit`
- [`ABBREVIATION_KINDS`](#icukiticu-abbreviations) — constant, `icukit.icu_abbreviations`
- [`IcuAbbreviation`](#icukiticu-abbreviations) — class, `icukit.icu_abbreviations`
- [`icu_abbreviations`](#icukiticu-abbreviations) — function, `icukit.icu_abbreviations`
- [`detector_key`](#icukitdetectors) — function, `icukit.detectors`
- [`ValueDetection`](#icukitdetectors) — class, `icukit.detectors`
- [`DateTimeValue`](#icukitdetectors) — class, `icukit.detectors`
- [`MeasureValue`](#icukitdetectors) — class, `icukit.detectors`
- [`UnitValue`](#icukitdetectors) — class, `icukit.detectors`
- [`NumberValue`](#icukitdetectors) — class, `icukit.detectors`
- [`NumberRangeSpec`](#icukitdetectors) — class, `icukit.detectors`
- [`NumberRangeValue`](#icukitdetectors) — class, `icukit.detectors`
- [`ApproximateValue`](#icukitdetectors) — class, `icukit.detectors`
- [`RelativeDateValue`](#icukitdetectors) — class, `icukit.detectors`
- [`detect`](#icukitdetectors) — function, `icukit.detectors`
- [`date_detectors`](#icukitdetectors) — function, `icukit.detectors`
- [`number_detectors`](#icukitdetectors) — function, `icukit.detectors`
- [`all_detectors`](#icukitdetectors) — function, `icukit.detectors`
- [`generated_detectors`](#icukitengine) — function, `icukit.engine`
- [`generated_detectors_report`](#icukitengine) — function, `icukit.engine`
- [`range_detectors`](#icukitengine) — function, `icukit.engine`
- [`reader_set`](#icukitengine) — function, `icukit.engine`
- [`flexible_detectors`](#icukitengine) — function, `icukit.engine`
- [`flexible_detectors_report`](#icukitengine) — function, `icukit.engine`
- [`clear_detector_caches`](#icukitengine) — function, `icukit.engine`
- [`detection_to_dict`](#icukitserialize) — function, `icukit.serialize`
- [`detections_to_json`](#icukitserialize) — function, `icukit.serialize`
- [`ABBREVIATION_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`BARE_HOUR_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`COMPACT_NUMBER_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`DATE_INTERVAL_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`DATE_TIME_SKELETON_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`DEFAULT_FAMILIES`](#icukitengine) — constant, `icukit.engine`
- [`GUARDED_FAMILIES`](#icukitengine) — constant, `icukit.engine`
- [`LONE_SPELLOUT_NUMBER_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`LOWERCASE_ROMAN_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`MONTH_NAME_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`RELATIVE_DATE_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`SCIENTIFIC_NUMBER_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`NUMBER_RANGE_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`SHORT_YEAR_ERA_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`SHORT_YEAR_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`SHORT_YEAR_INTERVAL_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`SPELLOUT_NUMBER_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`WEEKDAY_NAME_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`Family`](#icukitengine) — class, `icukit.engine`
- [`DateIntervalSpec`](#icukitdetectors) — class, `icukit.detectors`
- [`DateIntervalValue`](#icukitdetectors) — class, `icukit.detectors`
- [`AbbreviationBoundary`](#icukitabbreviation-breaker) — class, `icukit.abbreviation_breaker`
- [`AbbreviationDetector`](#icukitabbreviation-recognize) — class, `icukit.abbreviation_recognize`
- [`AbbreviationExpansion`](#icukitabbreviation-recognize) — class, `icukit.abbreviation_recognize`
- [`AbbreviationLexicon`](#icukitabbreviations) — class, `icukit.abbreviations`
- [`AbbreviationProvenance`](#icukitabbreviation-breaker) — class, `icukit.abbreviation_breaker`
- [`AbbreviationSegmentation`](#icukitabbreviation-breaker) — class, `icukit.abbreviation_breaker`
- [`AbbreviationSentenceBreaker`](#icukitabbreviation-breaker) — class, `icukit.abbreviation_breaker`
- [`AbbreviationSpec`](#icukitabbreviation-recognize) — class, `icukit.abbreviation_recognize`
- [`AbbreviationValue`](#icukitabbreviation-recognize) — class, `icukit.abbreviation_recognize`
- [`CompiledLexicon`](#icukitabbreviation-compile) — class, `icukit.abbreviation_compile`
- [`Entry`](#icukitabbreviations) — class, `icukit.abbreviations`
- [`Expansion`](#icukitabbreviations) — class, `icukit.abbreviations`
- [`Pattern`](#icukitabbreviations) — class, `icukit.abbreviations`
- [`PatternMatch`](#icukitabbreviation-compile) — class, `icukit.abbreviation_compile`
- [`abbreviation_detectors`](#icukitabbreviation-recognize) — function, `icukit.abbreviation_recognize`
- [`reformat_abbreviation`](#icukitabbreviation-recognize) — function, `icukit.abbreviation_recognize`
- [`available_locales`](#icukitabbreviations) — function, `icukit.abbreviations`
- [`compile_lexicon`](#icukitabbreviation-compile) — function, `icukit.abbreviation_compile`
- [`load_lexicon`](#icukitabbreviations) — function, `icukit.abbreviations`
- [`load_lexicon_file`](#icukitabbreviations) — function, `icukit.abbreviations`
- [`parse_lexicon`](#icukitabbreviations) — function, `icukit.abbreviations`
- [`ICUKitError`](#icukiterrors) — class, `icukit.errors`
- [`LocaleError`](#icukiterrors) — class, `icukit.errors`
- [`FormatError`](#icukiterrors) — class, `icukit.errors`
- [`ParseError`](#icukiterrors) — class, `icukit.errors`
- [`PatternError`](#icukiterrors) — class, `icukit.errors`
- [`TransliteratorError`](#icukiterrors) — class, `icukit.errors`
- [`ScriptError`](#icukiterrors) — class, `icukit.errors`
- [`NormalizationError`](#icukiterrors) — class, `icukit.errors`
- [`RegionError`](#icukiterrors) — class, `icukit.errors`
- [`TimezoneError`](#icukiterrors) — class, `icukit.errors`
- [`CalendarError`](#icukiterrors) — class, `icukit.errors`
- [`CollatorError`](#icukiterrors) — class, `icukit.errors`
- [`BidiError`](#icukiterrors) — class, `icukit.errors`
- [`BreakerError`](#icukiterrors) — class, `icukit.errors`
- [`MessageError`](#icukiterrors) — class, `icukit.errors`
- [`ListFormatError`](#icukiterrors) — class, `icukit.errors`
- [`DateTimeError`](#icukiterrors) — class, `icukit.errors`
- [`MeasureError`](#icukiterrors) — class, `icukit.errors`
- [`SearchError`](#icukiterrors) — class, `icukit.errors`
- [`SpoofError`](#icukiterrors) — class, `icukit.errors`
- [`IDNAError`](#icukiterrors) — class, `icukit.errors`
- [`AlphaIndexError`](#icukiterrors) — class, `icukit.errors`
- [`AbbreviationError`](#icukiterrors) — class, `icukit.errors`
- [`PluralError`](#icukiterrors) — class, `icukit.errors`
- [`DurationError`](#icukiterrors) — class, `icukit.errors`
- [`DisplayNameError`](#icukiterrors) — class, `icukit.errors`
- [`MeasureFormatter`](#icukitmeasure) — class, `icukit.measure`
- [`format_measure`](#icukitmeasure) — function, `icukit.measure`
- [`format_preferred`](#icukitmeasure) — function, `icukit.measure`
- [`convert_units`](#icukitmeasure) — function, `icukit.measure`
- [`can_convert`](#icukitmeasure) — function, `icukit.measure`
- [`get_unit_info`](#icukitmeasure) — function, `icukit.measure`
- [`get_units_by_type`](#icukitmeasure) — function, `icukit.measure`
- [`resolve_unit`](#icukitmeasure) — function, `icukit.measure`
- [`get_unit_abbreviation`](#icukitmeasure) — function, `icukit.measure`
- [`list_units`](#icukitmeasure) — function, `icukit.measure`
- [`list_unit_types`](#icukitmeasure) — function, `icukit.measure`
- [`WIDTH_WIDE`](#icukitmeasure) — constant, `icukit.measure`
- [`WIDTH_SHORT`](#icukitmeasure) — constant, `icukit.measure`
- [`WIDTH_NARROW`](#icukitmeasure) — constant, `icukit.measure`
- [`discover_features`](#icukitdiscover) — function, `icukit.discover`
- [`search_features`](#icukitdiscover) — function, `icukit.discover`
- [`flatten_extended`](#icukitformatters) — function, `icukit.formatters`
- [`format_json`](#icukitformatters) — function, `icukit.formatters`
- [`format_output`](#icukitformatters) — function, `icukit.formatters`
- [`format_simple_list`](#icukitformatters) — function, `icukit.formatters`
- [`format_tsv`](#icukitformatters) — function, `icukit.formatters`
- [`print_output`](#icukitformatters) — function, `icukit.formatters`
- [`print_record`](#icukitformatters) — function, `icukit.formatters`
- [`get_api_exports`](#icukitdiscover) — function, `icukit.discover`
- [`get_api_info`](#icukitdiscover) — function, `icukit.discover`
- [`get_cli_commands`](#icukitdiscover) — function, `icukit.discover`
- [`DateTimeFormatter`](#icukitdatetime) — class, `icukit.datetime`
- [`format_datetime`](#icukitdatetime) — function, `icukit.datetime`
- [`format_relative`](#icukitdatetime) — function, `icukit.datetime`
- [`parse_datetime`](#icukitdatetime) — function, `icukit.datetime`
- [`STYLE_FULL`](#icukitdatetime) — constant, `icukit.datetime`
- [`STYLE_LONG`](#icukitdatetime) — constant, `icukit.datetime`
- [`STYLE_MEDIUM`](#icukitdatetime) — constant, `icukit.datetime`
- [`STYLE_SHORT`](#icukitdatetime) — constant, `icukit.datetime`
- [`STYLE_NONE`](#icukitdatetime) — constant, `icukit.datetime`
- [`PATTERNS`](#icukitdatetime) — constant, `icukit.datetime`
- [`list_pattern_symbols`](#icukitdatetime) — function, `icukit.datetime`
- [`WIDTH_ABBREVIATED`](#icukitdatetime) — constant, `icukit.datetime`
- [`get_month_names`](#icukitdatetime) — function, `icukit.datetime`
- [`get_weekday_names`](#icukitdatetime) — function, `icukit.datetime`
- [`get_era_names`](#icukitdatetime) — function, `icukit.datetime`
- [`get_am_pm_strings`](#icukitdatetime) — function, `icukit.datetime`
- [`get_date_symbols`](#icukitdatetime) — function, `icukit.datetime`
- [`ListFormatter`](#icukitlist-format) — class, `icukit.list_format`
- [`format_list`](#icukitlist-format) — function, `icukit.list_format`
- [`STYLE_AND`](#icukitlist-format) — constant, `icukit.list_format`
- [`STYLE_OR`](#icukitlist-format) — constant, `icukit.list_format`
- [`STYLE_UNIT`](#icukitlist-format) — constant, `icukit.list_format`
- [`MessageFormatter`](#icukitmessage) — class, `icukit.message`
- [`format_message`](#icukitmessage) — function, `icukit.message`
- [`Breaker`](#icukitbreaker) — class, `icukit.breaker`
- [`BreakSpan`](#icukitbreaker) — class, `icukit.breaker`
- [`RuleBreaker`](#icukitbreaker) — class, `icukit.breaker`
- [`default_rules`](#icukitbreaker) — function, `icukit.breaker`
- [`break_sentences`](#icukitbreaker) — function, `icukit.breaker`
- [`break_words`](#icukitbreaker) — function, `icukit.breaker`
- [`break_lines`](#icukitbreaker) — function, `icukit.breaker`
- [`break_graphemes`](#icukitbreaker) — function, `icukit.breaker`
- [`break_word_spans`](#icukitbreaker) — function, `icukit.breaker`
- [`break_sentence_spans`](#icukitbreaker) — function, `icukit.breaker`
- [`break_line_spans`](#icukitbreaker) — function, `icukit.breaker`
- [`break_grapheme_spans`](#icukitbreaker) — function, `icukit.breaker`
- [`BREAK_SENTENCE`](#icukitbreaker) — constant, `icukit.breaker`
- [`BREAK_WORD`](#icukitbreaker) — constant, `icukit.breaker`
- [`BREAK_LINE`](#icukitbreaker) — constant, `icukit.breaker`
- [`BREAK_CHARACTER`](#icukitbreaker) — constant, `icukit.breaker`
- [`Prop`](#icukitclasses) — alias, `icukit.classes`
- [`ClassPoint`](#icukitclasses) — class, `icukit.classes`
- [`ClassWindow`](#icukitclasses) — class, `icukit.classes`
- [`char_classes`](#icukitclasses) — function, `icukit.classes`
- [`class_window`](#icukitclasses) — function, `icukit.classes`
- [`CVLetterCounts`](#icukitshape) — class, `icukit.shape`
- [`ShapeSchemeInfo`](#icukitshape) — class, `icukit.shape`
- [`cvletters_counts`](#icukitshape) — function, `icukit.shape`
- [`shape`](#icukitshape) — function, `icukit.shape`
- [`shape_scheme`](#icukitshape) — function, `icukit.shape`
- [`ProtectedSpan`](#icukittokens) — class, `icukit.tokens`
- [`TOKEN_PROFILE`](#icukittokens) — constant, `icukit.tokens`
- [`Token`](#icukittokens) — class, `icukit.tokens`
- [`tokens`](#icukittokens) — function, `icukit.tokens`
- [`token_features`](#icukittokens) — function, `icukit.tokens`
- [`OverlappingProtectedSpans`](#icukiterrors) — class, `icukit.errors`
- [`BreakRuleIdentity`](#icukitsentence-override) — class, `icukit.sentence_override`
- [`BreakPredicate`](#icukitsentence-override) — class, `icukit.sentence_override`
- [`BreakRule`](#icukitsentence-override) — class, `icukit.sentence_override`
- [`BreakRuleSet`](#icukitsentence-override) — class, `icukit.sentence_override`
- [`BreakDecision`](#icukitsentence-override) — class, `icukit.sentence_override`
- [`BreakBoundary`](#icukitsentence-override) — class, `icukit.sentence_override`
- [`BreakSegmentation`](#icukitsentence-override) — class, `icukit.sentence_override`
- [`CartletModelRef`](#icukitsentence-override) — class, `icukit.sentence_override`
- [`PendingCandidate`](#icukitsentence-override) — class, `icukit.sentence_override`
- [`IncrementalSentenceBreaker`](#icukitsentence-override) — class, `icukit.sentence_override`
- [`SentenceOverride`](#icukitsentence-override) — class, `icukit.sentence_override`
- [`break_rule_identity`](#icukitsentence-override) — function, `icukit.sentence_override`
- [`load_break_rules`](#icukitsentence-override) — function, `icukit.sentence_override`
- [`BreakRuleLoadError`](#icukiterrors) — class, `icukit.errors`
- [`LateProtectedSpan`](#icukiterrors) — class, `icukit.errors`
- [`get_base_direction`](#icukitbidi) — function, `icukit.bidi`
- [`get_bidi_info`](#icukitbidi) — function, `icukit.bidi`
- [`strip_bidi_controls`](#icukitbidi) — function, `icukit.bidi`
- [`has_bidi_controls`](#icukitbidi) — function, `icukit.bidi`
- [`list_bidi_controls`](#icukitbidi) — function, `icukit.bidi`
- [`DIRECTION_LTR`](#icukitbidi) — constant, `icukit.bidi`
- [`DIRECTION_RTL`](#icukitbidi) — constant, `icukit.bidi`
- [`DIRECTION_MIXED`](#icukitbidi) — constant, `icukit.bidi`
- [`DIRECTION_NEUTRAL`](#icukitbidi) — constant, `icukit.bidi`
- [`sort_strings`](#icukitcollator) — function, `icukit.collator`
- [`compare_strings`](#icukitcollator) — function, `icukit.collator`
- [`get_sort_key`](#icukitcollator) — function, `icukit.collator`
- [`list_collation_types`](#icukitcollator) — function, `icukit.collator`
- [`get_collator_info`](#icukitcollator) — function, `icukit.collator`
- [`STRENGTH_PRIMARY`](#icukitcollator) — constant, `icukit.collator`
- [`STRENGTH_SECONDARY`](#icukitcollator) — constant, `icukit.collator`
- [`STRENGTH_TERTIARY`](#icukitcollator) — constant, `icukit.collator`
- [`STRENGTH_QUATERNARY`](#icukitcollator) — constant, `icukit.collator`
- [`STRENGTH_IDENTICAL`](#icukitcollator) — constant, `icukit.collator`
- [`Transliterator`](#icukittransliterator) — class, `icukit.transliterator`
- [`CommonTransliterators`](#icukittransliterator) — class, `icukit.transliterator`
- [`transliterate`](#icukittransliterator) — function, `icukit.transliterator`
- [`list_transliterators`](#icukittransliterator) — function, `icukit.transliterator`
- [`get_transliterator_info`](#icukittransliterator) — function, `icukit.transliterator`
- [`list_transliterators_info`](#icukittransliterator) — function, `icukit.transliterator`
- [`UnicodeRegex`](#icukitregex) — class, `icukit.regex`
- [`regex_find`](#icukitregex) — function, `icukit.regex`
- [`regex_fullmatch`](#icukitregex) — function, `icukit.regex`
- [`regex_replace`](#icukitregex) — function, `icukit.regex`
- [`regex_search`](#icukitregex) — function, `icukit.regex`
- [`regex_split`](#icukitregex) — function, `icukit.regex`
- [`parse_substitution`](#icukitregex) — function, `icukit.regex`
- [`list_unicode_properties`](#icukitregex) — function, `icukit.regex`
- [`list_unicode_categories`](#icukitregex) — function, `icukit.regex`
- [`list_unicode_scripts`](#icukitregex) — function, `icukit.regex`
- [`CASE_INSENSITIVE`](#icukitregex) — constant, `icukit.regex`
- [`MULTILINE`](#icukitregex) — constant, `icukit.regex`
- [`DOTALL`](#icukitregex) — constant, `icukit.regex`
- [`COMMENTS`](#icukitregex) — constant, `icukit.regex`
- [`detect_script`](#icukitscript) — function, `icukit.script`
- [`detect_scripts`](#icukitscript) — function, `icukit.script`
- [`get_char_script`](#icukitscript) — function, `icukit.script`
- [`get_script_info`](#icukitscript) — function, `icukit.script`
- [`is_cased`](#icukitscript) — function, `icukit.script`
- [`is_rtl`](#icukitscript) — function, `icukit.script`
- [`list_scripts`](#icukitscript) — function, `icukit.script`
- [`list_scripts_info`](#icukitscript) — function, `icukit.script`
- [`normalize`](#icukitunicode) — function, `icukit.unicode`
- [`is_normalized`](#icukitunicode) — function, `icukit.unicode`
- [`decode_unicode_escapes`](#icukitunicode) — function, `icukit.unicode`
- [`encode_unicode_escapes`](#icukitunicode) — function, `icukit.unicode`
- [`get_char_name`](#icukitunicode) — function, `icukit.unicode`
- [`get_char_aliases`](#icukitunicode) — function, `icukit.unicode`
- [`get_char_names`](#icukitunicode) — function, `icukit.unicode`
- [`char_from_name`](#icukitunicode) — function, `icukit.unicode`
- [`get_char_category`](#icukitunicode) — function, `icukit.unicode`
- [`get_char_info`](#icukitunicode) — function, `icukit.unicode`
- [`list_categories`](#icukitunicode) — function, `icukit.unicode`
- [`list_blocks`](#icukitunicode) — function, `icukit.unicode`
- [`get_block_characters`](#icukitunicode) — function, `icukit.unicode`
- [`get_category_characters`](#icukitunicode) — function, `icukit.unicode`
- [`NFC`](#icukitunicode) — constant, `icukit.unicode`
- [`NFD`](#icukitunicode) — constant, `icukit.unicode`
- [`NFKC`](#icukitunicode) — constant, `icukit.unicode`
- [`NFKD`](#icukitunicode) — constant, `icukit.unicode`
- [`list_regions`](#icukitregion) — function, `icukit.region`
- [`list_regions_info`](#icukitregion) — function, `icukit.region`
- [`get_region_info`](#icukitregion) — function, `icukit.region`
- [`get_contained_regions`](#icukitregion) — function, `icukit.region`
- [`list_region_types`](#icukitregion) — function, `icukit.region`
- [`search_all`](#icukitsearch) — function, `icukit.search`
- [`search_first`](#icukitsearch) — function, `icukit.search`
- [`search_count`](#icukitsearch) — function, `icukit.search`
- [`search_replace`](#icukitsearch) — function, `icukit.search`
- [`StringSearcher`](#icukitsearch) — class, `icukit.search`
- [`Detection`](#icukitdetect) — class, `icukit.detect`
- [`regex_detect`](#icukitdetect) — function, `icukit.detect`
- [`collation_detect`](#icukitdetect) — function, `icukit.detect`
- [`Condition`](#icukitexceptions) — alias, `icukit.exceptions`
- [`ExceptionContextBounds`](#icukitexceptions) — class, `icukit.exceptions`
- [`ExceptionInventory`](#icukitexceptions) — class, `icukit.exceptions`
- [`ExceptionPolicy`](#icukitexceptions) — class, `icukit.exceptions`
- [`ExceptionRule`](#icukitexceptions) — class, `icukit.exceptions`
- [`LoadedExceptionInventory`](#icukitexceptions) — class, `icukit.exceptions`
- [`NamedListCondition`](#icukitexceptions) — class, `icukit.exceptions`
- [`Provenance`](#icukitexceptions) — class, `icukit.exceptions`
- [`SkipSpec`](#icukitexceptions) — class, `icukit.exceptions`
- [`UnicodeSetCondition`](#icukitexceptions) — class, `icukit.exceptions`
- [`Witnesses`](#icukitexceptions) — class, `icukit.exceptions`
- [`load_exception_inventory`](#icukitexceptions) — function, `icukit.exceptions`
- [`compose_inventories`](#icukitexceptions) — function, `icukit.exceptions`
- [`example_exception_inventory`](#icukitexceptions) — function, `icukit.exceptions`
- [`merge_retypes`](#icukitexceptions) — function, `icukit.exceptions`
- [`ExceptionConflictError`](#icukiterrors) — class, `icukit.errors`
- [`ExceptionLoadError`](#icukiterrors) — class, `icukit.errors`
- [`RuleRefusal`](#icukiterrors) — class, `icukit.errors`
- [`RuleLoadError`](#icukiterrors) — class, `icukit.errors`
- [`LocaleMaterial`](#icukitmaterial) — class, `icukit.material`
- [`ClassExtension`](#icukitmaterial) — class, `icukit.material`
- [`MaterialLoadError`](#icukitmaterial) — class, `icukit.material`
- [`MaterialRefusal`](#icukitmaterial) — class, `icukit.material`
- [`ShapeRefinement`](#icukitmaterial) — class, `icukit.material`
- [`load_locale_material`](#icukitmaterial) — function, `icukit.material`
- [`are_confusable`](#icukitspoof) — function, `icukit.spoof`
- [`get_confusable_type`](#icukitspoof) — function, `icukit.spoof`
- [`get_skeleton`](#icukitspoof) — function, `icukit.spoof`
- [`check_string`](#icukitspoof) — function, `icukit.spoof`
- [`get_confusable_info`](#icukitspoof) — function, `icukit.spoof`
- [`SpoofChecker`](#icukitspoof) — class, `icukit.spoof`
- [`CONFUSABLE_NONE`](#icukitspoof) — constant, `icukit.spoof`
- [`CONFUSABLE_SINGLE_SCRIPT`](#icukitspoof) — constant, `icukit.spoof`
- [`CONFUSABLE_MIXED_SCRIPT`](#icukitspoof) — constant, `icukit.spoof`
- [`CONFUSABLE_WHOLE_SCRIPT`](#icukitspoof) — constant, `icukit.spoof`
- [`idna_encode`](#icukitidna) — function, `icukit.idna`
- [`idna_decode`](#icukitidna) — function, `icukit.idna`
- [`idna_encode_label`](#icukitidna) — function, `icukit.idna`
- [`idna_decode_label`](#icukitidna) — function, `icukit.idna`
- [`is_ascii_domain`](#icukitidna) — function, `icukit.idna`
- [`IDNAConverter`](#icukitidna) — class, `icukit.idna`
- [`create_index_buckets`](#icukitalpha-index) — function, `icukit.alpha_index`
- [`get_bucket_labels`](#icukitalpha-index) — function, `icukit.alpha_index`
- [`get_bucket_for_name`](#icukitalpha-index) — function, `icukit.alpha_index`
- [`AlphabeticIndex`](#icukitalpha-index) — class, `icukit.alpha_index`
- [`list_timezones`](#icukittimezone) — function, `icukit.timezone`
- [`list_timezones_info`](#icukittimezone) — function, `icukit.timezone`
- [`get_timezone_info`](#icukittimezone) — function, `icukit.timezone`
- [`get_timezone_offset`](#icukittimezone) — function, `icukit.timezone`
- [`get_equivalent_timezones`](#icukittimezone) — function, `icukit.timezone`
- [`list_calendars`](#icukitcalendar) — function, `icukit.calendar`
- [`list_calendars_info`](#icukitcalendar) — function, `icukit.calendar`
- [`get_calendar_info`](#icukitcalendar) — function, `icukit.calendar`
- [`is_valid_calendar`](#icukitcalendar) — function, `icukit.calendar`
- [`list_locales`](#icukitlocale) — function, `icukit.locale`
- [`list_locales_info`](#icukitlocale) — function, `icukit.locale`
- [`list_languages`](#icukitlocale) — function, `icukit.locale`
- [`parse_locale`](#icukitlocale) — function, `icukit.locale`
- [`get_locale_info`](#icukitlocale) — function, `icukit.locale`
- [`get_locale_attributes`](#icukitlocale) — function, `icukit.locale`
- [`get_locale_scripts`](#icukitlocale) — function, `icukit.locale`
- [`get_locale_extended`](#icukitlocale) — function, `icukit.locale`
- [`add_likely_subtags`](#icukitlocale) — function, `icukit.locale`
- [`minimize_subtags`](#icukitlocale) — function, `icukit.locale`
- [`canonicalize_locale`](#icukitlocale) — function, `icukit.locale`
- [`get_display_name`](#icukitlocale) — function, `icukit.locale`
- [`get_language_display_name`](#icukitlocale) — function, `icukit.locale`
- [`is_valid_locale`](#icukitlocale) — function, `icukit.locale`
- [`get_default_locale`](#icukitlocale) — function, `icukit.locale`
- [`get_exemplar_characters`](#icukitlocale) — function, `icukit.locale`
- [`get_exemplar_info`](#icukitlocale) — function, `icukit.locale`
- [`list_exemplar_types`](#icukitlocale) — function, `icukit.locale`
- [`EXEMPLAR_STANDARD`](#icukitlocale) — constant, `icukit.locale`
- [`EXEMPLAR_AUXILIARY`](#icukitlocale) — constant, `icukit.locale`
- [`EXEMPLAR_INDEX`](#icukitlocale) — constant, `icukit.locale`
- [`EXEMPLAR_PUNCTUATION`](#icukitlocale) — constant, `icukit.locale`
- [`get_number_symbols`](#icukitlocale) — function, `icukit.locale`
- [`format_number`](#icukitlocale) — function, `icukit.locale`
- [`format_currency`](#icukitlocale) — function, `icukit.locale`
- [`format_percent`](#icukitlocale) — function, `icukit.locale`
- [`format_scientific`](#icukitlocale) — function, `icukit.locale`
- [`format_spellout`](#icukitlocale) — function, `icukit.locale`
- [`format_ordinal`](#icukitlocale) — function, `icukit.locale`
- [`COMPACT_SHORT`](#icukitlocale) — constant, `icukit.locale`
- [`COMPACT_LONG`](#icukitlocale) — constant, `icukit.locale`
- [`get_plural_category`](#icukitplural) — function, `icukit.plural`
- [`get_ordinal_category`](#icukitplural) — function, `icukit.plural`
- [`list_plural_categories`](#icukitplural) — function, `icukit.plural`
- [`list_ordinal_categories`](#icukitplural) — function, `icukit.plural`
- [`get_plural_rules_info`](#icukitplural) — function, `icukit.plural`
- [`CATEGORY_ZERO`](#icukitplural) — constant, `icukit.plural`
- [`CATEGORY_ONE`](#icukitplural) — constant, `icukit.plural`
- [`CATEGORY_TWO`](#icukitplural) — constant, `icukit.plural`
- [`CATEGORY_FEW`](#icukitplural) — constant, `icukit.plural`
- [`CATEGORY_MANY`](#icukitplural) — constant, `icukit.plural`
- [`CATEGORY_OTHER`](#icukitplural) — constant, `icukit.plural`
- [`TYPE_CARDINAL`](#icukitplural) — constant, `icukit.plural`
- [`TYPE_ORDINAL`](#icukitplural) — constant, `icukit.plural`
- [`NumberParser`](#icukitparse) — class, `icukit.parse`
- [`parse_number`](#icukitparse) — function, `icukit.parse`
- [`parse_currency`](#icukitparse) — function, `icukit.parse`
- [`parse_percent`](#icukitparse) — function, `icukit.parse`
- [`DurationFormatter`](#icukitduration) — class, `icukit.duration`
- [`format_duration`](#icukitduration) — function, `icukit.duration`
- [`parse_iso_duration`](#icukitduration) — function, `icukit.duration`
- [`DURATION_WIDTH_WIDE`](#icukitduration) — constant, `icukit.duration`
- [`DURATION_WIDTH_SHORT`](#icukitduration) — constant, `icukit.duration`
- [`DURATION_WIDTH_NARROW`](#icukitduration) — constant, `icukit.duration`
- [`DisplayNames`](#icukitdisplayname) — class, `icukit.displayname`
- [`get_language_name`](#icukitdisplayname) — function, `icukit.displayname`
- [`get_script_name`](#icukitdisplayname) — function, `icukit.displayname`
- [`get_region_name`](#icukitdisplayname) — function, `icukit.displayname`
- [`get_currency_name`](#icukitdisplayname) — function, `icukit.displayname`
- [`get_currency_symbol`](#icukitdisplayname) — function, `icukit.displayname`
- [`get_locale_name`](#icukitdisplayname) — function, `icukit.displayname`
- [`CompactFormatter`](#icukitcompact) — class, `icukit.compact`
- [`format_compact`](#icukitlocale) — function, `icukit.locale`
- [`COMPACT_STYLE_SHORT`](#icukitcompact) — constant, `icukit.compact`
- [`COMPACT_STYLE_LONG`](#icukitcompact) — constant, `icukit.compact`

## Start gates

Start gates skip grapheme starts at which a detector lane cannot read or raise. They are sound over-approximations: admitting an extra start only costs time, while rejecting a non-miss start is a bug. `StartGate` admits literal `chars`, case-folded first characters in `folded`, and named ICU property `tests`. A lane whose safe opening set is not known declares `None` and remains ungated.

`GatedDetector.start_gates()` maps stable lane names to their gates. Third-party detectors can use `candidate_starts(text, locale, gate)` in their own scans. Set `ICUKIT_GATES=0` before importing icukit to disable gates for the process, or use `ungated()` for a context-local comparison.

## icukit.abbreviation_breaker

Sentence-break post-filter driven by an abbreviation lexicon.

### class `AbbreviationBoundary`

An ambiguous boundary retaining both possible readings.

### class `AbbreviationProvenance`

The lexicon decision responsible for merging a boundary.

### class `AbbreviationSegmentation`

Primary segmentation plus deposited ambiguous boundaries.

#### `AbbreviationSegmentation(spans: 'list[BreakSpan]', ambiguous_boundaries: 'list[AbbreviationBoundary]') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `AbbreviationSentenceBreaker`

Post-filter raw ICU sentence spans with a separate abbreviation lexicon.

For English, :class:`Breaker` and :class:`SentenceOverride` apply token
integrity and shipped suppress entries to ICU candidates by default. This
class remains the explicit alternative that also deposits ambiguous
boundaries; ``base="none"`` on those APIs gives raw ICU without the list.

#### `AbbreviationSentenceBreaker(locale: 'str' = 'en_US', lexicon: 'AbbreviationLexicon | CompiledLexicon | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `segmentations(text: 'str') -> 'AbbreviationSegmentation'`

Return maximally merged spans and every ambiguous boundary.

#### `spans(text: 'str') -> 'list[BreakSpan]'`

Return the primary maximally merged sentence spans.

## icukit.abbreviation_compile

Compile abbreviation lexicons into a shared consumer-facing view.

### class `CompiledLexicon`

One immutable, anti-drift view shared by abbreviation consumers.

``uncased-latin`` is deliberately conservative: a single dotted lowercase
segment must be backed by a literal entry (case-insensitively), while a
multi-part dotted lowercase surface is productive.

#### `CompiledLexicon(lexicon: 'AbbreviationLexicon', entries: 'dict[str, Entry]', suppress: 'frozenset[str]', ambiguous: 'frozenset[str]', classified_surfaces: 'frozenset[str]', patterns: 'dict[str, Pattern]') -> None`

Initialize self.  See help(type(self)) for accurate signature.

#### `classify(surface: 'str') -> 'tuple[str | None, str | None]'`

Return ``(behavior, provenance)``, preferring a literal entry.

#### `pattern_kind(surface: 'str') -> 'str | None'`

Return the matching productive kind, unless a literal wins.

### class `PatternMatch`

The behavior and typed pattern kind that classified a surface.

#### `PatternMatch(behavior: 'str', kind: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `compile_lexicon(locale: 'str' = 'en') -> 'CompiledLexicon | None'`

Load and compile the locale's lexicon, or return ``None`` when absent.

The lexicon follows ICU's locale fallback (see
:func:`~icukit.abbreviations.load_locale_lexicon`): ``en_US`` reads the
packaged ``en`` lexicon with its ``en_US`` overlay, ``en_GB`` reads ``en``,
and unsupported languages degrade cleanly.

## icukit.abbreviation_recognize

Lexicon-driven abbreviation recognition.

### class `AbbreviationDetector`

Deposit one structural candidate for each recognized abbreviation surface.

Surface identity upholds ``reformat_abbreviation(spec, value) == text``.
Expansions are typed annotations on that candidate, never reformat operands.

#### `AbbreviationDetector(locale: 'str' = 'en', lexicon: 'AbbreviationLexicon | CompiledLexicon | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Scan token starts and return all co-located readings.

### class `AbbreviationExpansion`

One annotated expansion of an abbreviation surface.

``type`` is ``"expansion"`` when ``text`` is read as words, or ``"spell-out"``
when the surface is spelled out and ``text`` lists the characters to name,
separated by spaces (``MD`` -> ``M D``).

#### `AbbreviationExpansion(text: 'str', sense: 'str', cue: 'str | None' = None, type: 'str' = 'expansion') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `AbbreviationSpec`

The requested locale and source lexicon language.

#### `AbbreviationSpec(locale: 'str', source: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `AbbreviationValue`

An abbreviation surface and all of its co-located expansion annotations.

#### `AbbreviationValue(surface: 'str', expansions: 'tuple[AbbreviationExpansion, ...]' = (), also: 'str | None' = None, break_behavior: 'str' = 'suppress') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `abbreviation_detectors(locale: 'str' = 'en') -> 'DetectorSet'`

Return the locale's abbreviation detector gang, empty when unsupported.

### `reformat_abbreviation(spec: 'AbbreviationSpec', value: 'AbbreviationValue') -> 'str'`

Return the recognized surface; expansions are annotations, not reformats.

## icukit.abbreviations

Per-locale abbreviation lexicons.

An abbreviation lexicon records, for one language, the abbreviations that
should not falsely end a sentence and the (possibly ambiguous) expansions they
stand for. Lexicons are authored as XML validated by a RELAX NG grammar of
CLDR lineage (``abbreviations.rng``) and shipped alongside this module under
``data/abbreviations/``.

Two downstream consumers are served, though neither lives here:

    * a sentence breaker, which turns ``break="suppress"`` surfaces into
      break-exceptions and ``break="ambiguous"`` surfaces into deposited
      alternatives; and
    * an abbreviation recognizer, which deposits one detection per surface
      carrying every ``<expansion>`` reading as an annotation, never forcing one.

This module only PARSES a lexicon into a typed, immutable model. Ambiguity is
preserved: an entry keeps every expansion, and ``break`` distinguishes a
surface that never ends a sentence from one that merely might.

Parsing uses the Python standard library ``xml.etree`` at runtime (no lxml
dependency). The parser forbids DTDs and entity declarations, so external
entity (XXE) and entity-expansion attacks cannot reach the lexicon. RELAX NG
validation is a development/test concern and lives in the test suite.

Example:
    >>> from icukit.abbreviations import load_lexicon
    >>> lex = load_lexicon("en")
    >>> entry = lex.get("St.")
    >>> [e.value for e in entry.expansions]
    ['Saint', 'Street']
    >>> entry.is_ambiguous_expansion
    True

### Constants and type aliases

#### `BREAK_AMBIGUOUS` (constant)

`'ambiguous'`

#### `BREAK_SUPPRESS` (constant)

`'suppress'`

``break`` values (the attribute name is a Python keyword, hence the aliases).

### class `AbbreviationLexicon`

The parsed abbreviation lexicon of one language.

Entries are keyed by surface for lookup while preserving document order.

#### `AbbreviationLexicon(language: 'str', entries: 'tuple[Entry, ...]' = (), patterns: 'tuple[Pattern, ...]' = (), status: 'str | None' = None) -> None`

Initialize self.  See help(type(self)) for accurate signature.

#### `get(surface: 'str') -> 'Entry | None'`

Return the entry for ``surface``, or ``None`` if there is none.

#### `surfaces() -> 'tuple[str, ...]'`

All entry surfaces, in document order.

### class `Entry`

A single abbreviation surface and its expansions.

``break_behavior`` is ``"suppress"`` when the trailing period always
belongs to the abbreviation (never a sentence end) or ``"ambiguous"`` when
the surface may also legitimately end a sentence. ``also`` flags a
competing non-abbreviation reading (``proper-name``, ``common-word``).

#### `Entry(surface: 'str', break_behavior: 'str', expansions: 'tuple[Expansion, ...]' = (), also: 'str | None' = None) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `Expansion`

One expansion reading of an abbreviation surface.

``sense`` names the semantic class of the expansion (``title``, ``saint``,
``thoroughfare``, ...). ``cue`` is an optional positional hint that favors
this reading (e.g. ``precedes-number``); it is advisory, never a rule.
``type`` is how the expansion is spoken: ``"expansion"`` reads ``value`` as
words, and ``"spell-out"`` spells the surface out, with ``value`` listing
the characters to name, separated by spaces (``MD`` -> ``M D``).

#### `Expansion(value: 'str', sense: 'str', cue: 'str | None' = None, type: 'str' = 'expansion') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `Pattern`

A productive abbreviation family, named by a typed ``kind``.

A pattern never carries a raw regular expression: the grammar admits only
an enumerated ``kind`` (``single-initial``, ``multi-part-initials``,
``uncased-latin``), and a later compiler owns the boundary semantics.

#### `Pattern(kind: 'str', break_behavior: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `available_locales() -> 'tuple[str, ...]'`

Return the locale ids with a packaged abbreviation lexicon.

### `load_lexicon(language: 'str' = 'en') -> 'AbbreviationLexicon'`

Load the packaged abbreviation lexicon for ``language`` (e.g. ``"en"``).

Raises :class:`~icukit.errors.AbbreviationError` if no lexicon is shipped
for the requested language.

### `load_lexicon_file(path: 'str | Path') -> 'AbbreviationLexicon'`

Load and parse an abbreviation lexicon from an XML file path.

### `load_locale_lexicon(locale: 'str') -> 'AbbreviationLexicon'`

Load the lexicon for ``locale``, overlaying each packaged regional lexicon.

Every packaged lexicon on :func:`locale_chain` contributes, from the most
general to the most specific: ``en_US`` reads ``en.xml`` with ``en_US.xml``
over it, and ``en_GB`` reads ``en.xml`` alone unless an ``en_001.xml`` or
``en_GB.xml`` is packaged. Raises :class:`~icukit.errors.AbbreviationError`
when no lexicon on the chain is packaged.

### `locale_chain(locale: 'str') -> 'tuple[str, ...]'`

Return ``locale`` and its ICU fallback parents, most specific first, without root.

The chain is ICU's own: a locale whose resource bundle names a CLDR parent
(``en_GB`` -> ``en_001``) falls back to it, and any other drops its last
subtag (``en_US`` -> ``en``). A parent is honored only when the locale
declares it itself: ``zh_Hant_TW`` inherits ``zh_Hant``'s parent, which
belongs to ``zh_Hant``.

### `merge_lexicons(general: 'AbbreviationLexicon', specific: 'AbbreviationLexicon') -> 'AbbreviationLexicon'`

Overlay ``specific`` (a regional lexicon) on ``general`` (its parent).

An entry whose surface the parent also lists keeps the parent's expansions
and adds the child's after them, and the child's ``break`` and ``also``
govern. A surface only the child lists is appended. A pattern kind the child
declares replaces the parent's. The merged lexicon reports the child's
language.

### `parse_lexicon(xml_text: 'str') -> 'AbbreviationLexicon'`

Parse abbreviation-lexicon XML text into an ``AbbreviationLexicon``.

The input is parsed with DTDs and entities forbidden. Structural rules
beyond the grammar (a present surface, a nonempty expansion value) are
checked here so the model is always well formed; RELAX NG validation of
the full controlled vocabularies is exercised by the test suite.

## icukit.alpha_index

Alphabetic index buckets for sorted lists using ICU's AlphabeticIndex.

Creates locale-aware A-Z style index buckets for organizing sorted lists
like contacts, glossaries, or directory listings.

Example:
    >>> from icukit import create_index_buckets
    >>> buckets = create_index_buckets(["Alice", "Bob", "Carol", "Zebra"], "en_US")
    >>> buckets
    {'A': ['Alice'], 'B': ['Bob'], 'C': ['Carol'], 'Z': ['Zebra']}

### class `AlphabeticIndex`

Reusable alphabetic index for organizing items into buckets.

Useful when you need to add items incrementally or access
bucket information multiple times.

Example:
    >>> index = AlphabeticIndex("en_US")
    >>> index.add("Alice")
    >>> index.add("Bob")
    >>> index.add("Zebra")
    >>> index.get_buckets()
    {'A': ['Alice'], 'B': ['Bob'], 'Z': ['Zebra']}

#### `AlphabeticIndex(locale: 'str' = 'en_US')`

Create an alphabetic index for the given locale.

Args:
    locale: Locale for bucket labels and sorting.

#### `add(name: 'str', data: 'Any' = None) -> 'AlphabeticIndex'`

Add an item to the index.

Args:
    name: Name/label for the item.
    data: Optional associated data (not returned by get_buckets).

Returns:
    Self for chaining.

#### `add_many(names: 'list[str]') -> 'AlphabeticIndex'`

Add multiple items to the index.

Args:
    names: List of names to add.

Returns:
    Self for chaining.

#### `clear() -> 'AlphabeticIndex'`

Clear all records from the index.

Returns:
    Self for chaining.

#### `get_bucket_for(name: 'str') -> 'str'`

Get the bucket label for a name without adding it.

Args:
    name: Name to look up.

Returns:
    Bucket label.

#### `get_buckets() -> 'dict[str, list[str]]'`

Get all non-empty buckets with their items.

Returns:
    Dict mapping bucket labels to lists of items.

#### `get_labels() -> 'list[str]'`

Get all bucket labels for this locale.

Returns:
    List of bucket label strings.

### `create_index_buckets(items: 'list[str]', locale: 'str' = 'en_US') -> 'dict[str, list[str]]'`

Create alphabetic index buckets for a list of items.

Organizes items into locale-appropriate alphabetic buckets (like A-Z
in English, or あかさたな in Japanese).

Args:
    items: List of strings to organize into buckets.
    locale: Locale for bucket labels and sorting rules.

Returns:
    Dict mapping bucket labels to lists of items in each bucket.

Example:
    >>> create_index_buckets(["Apple", "Banana", "Bob", "Zebra"], "en_US")
    {'A': ['Apple'], 'B': ['Banana', 'Bob'], 'Z': ['Zebra']}

### `get_bucket_for_name(name: 'str', locale: 'str' = 'en_US') -> 'str'`

Get the bucket label for a given name.

Args:
    name: Name to look up.
    locale: Locale for bucket determination.

Returns:
    Bucket label for the name.

Example:
    >>> get_bucket_for_name("Alice", "en_US")
    'A'
    >>> get_bucket_for_name("山田", "ja_JP")
    'や'

### `get_bucket_labels(locale: 'str' = 'en_US') -> 'list[str]'`

Get the bucket labels for a locale.

Returns the alphabetic index labels used for the given locale
(e.g., A-Z for English, あかさたな for Japanese).

Args:
    locale: Locale code.

Returns:
    List of bucket label strings.

Example:
    >>> get_bucket_labels("en_US")[:5]
    ['A', 'B', 'C', 'D', 'E']
    >>> get_bucket_labels("ja_JP")[:5]
    ['あ', 'か', 'さ', 'た', 'な']

## icukit.availability

Report reader availability for a locale and identify each usable source.

### class `AvailabilityRow`

One enumerated reader specification and the source that contributes to it.

For a ``user`` row, ``provenance`` is the material's own
``provenance.source``: verbatim user text that icukit does not interpret. icukit
computes and reports no measured shares.

#### `AvailabilityRow(locale: 'str', family: 'str', spec: 'str', type: 'str | None', source: 'str | None', served_by: 'str | None', material: 'str | None', provenance: 'str | None', reason: 'str | None') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `availability(locale: 'str', *, material: 'Iterable[LocaleMaterial]' = (), guarded: 'bool' = False) -> 'tuple[AvailabilityRow, ...]'`

Report the default generated and flexible selections for ``locale``.

Flexible rows use the default locales, currencies, and units; ``guarded=True``
includes the guarded families. ICU/CLDR, shipped curated tables, and explicitly
supplied user material are separate rows. A row with no source means there is no
usable reader: it was not built, or it was built with nothing to read.

### `available_languages() -> 'tuple[str, ...]'`

Return the distinct ICU language identifiers covered by availability reports.

## icukit.bidi

Bidirectional text handling.

ICU's BiDi implementation provides the Unicode Bidirectional Algorithm (UBA)
for handling mixed left-to-right and right-to-left text.

Key Features:
    * Detect text direction (LTR, RTL, mixed)
    * Get paragraph embedding level
    * Strip invisible bidi control characters
    * List bidi control characters

Example:
    >>> from icukit import get_bidi_info, strip_bidi_controls
    >>> get_bidi_info('Hello שלום')
    {'direction': 'mixed', 'base_direction': 'ltr', 'has_rtl': True, 'has_ltr': True}
    >>> strip_bidi_controls('hello\u200fworld')
    'helloworld'

### Constants and type aliases

#### `DIRECTION_LTR` (constant)

`'ltr'`

Direction constants

#### `DIRECTION_MIXED` (constant)

`'mixed'`

#### `DIRECTION_NEUTRAL` (constant)

`'neutral'`

#### `DIRECTION_RTL` (constant)

`'rtl'`

### `get_base_direction(text: 'str') -> 'str'`

Get the base direction of text using the first strong directional character.

Args:
    text: Text to analyze.

Returns:
    Direction string: 'ltr', 'rtl', or 'neutral' if no strong characters.

Example:
    >>> get_base_direction('Hello')
    'ltr'
    >>> get_base_direction('שלום')
    'rtl'
    >>> get_base_direction('123')
    'neutral'

### `get_bidi_info(text: 'str') -> 'dict'`

Get bidirectional text information.

Args:
    text: Text to analyze.

Returns:
    Dictionary with:
        - direction: 'ltr', 'rtl', 'mixed', or 'neutral'
        - base_direction: 'ltr', 'rtl', or 'neutral'
        - has_rtl: True if text contains RTL characters
        - has_ltr: True if text contains LTR characters
        - bidi_control_count: Number of bidi control characters

Example:
    >>> get_bidi_info('Hello שלום')
    {'direction': 'mixed', 'base_direction': 'ltr', 'has_rtl': True, ...}

### `has_bidi_controls(text: 'str') -> 'bool'`

Check if text contains any bidirectional control characters.

Args:
    text: Text to check.

Returns:
    True if text contains bidi controls, False otherwise.

Example:
    >>> has_bidi_controls('hello world')
    False
    >>> has_bidi_controls('hello\u200fworld')
    True

### `list_bidi_controls() -> 'list[dict]'`

List all bidirectional control characters.

Returns:
    List of dicts with char, codepoint, abbrev, and name.

Example:
    >>> controls = list_bidi_controls()
    >>> controls[0]
    {'char': '\u200e', 'codepoint': 'U+200E', 'abbrev': 'LRM', 'name': 'Left-to-Right Mark'}

### `strip_bidi_controls(text: 'str') -> 'str'`

Remove all bidirectional control characters from text.

Useful for security (preventing bidi-based text spoofing attacks like
CVE-2021-42574 "Trojan Source") and cleaning text for processing.

Args:
    text: Text to clean.

Returns:
    Text with bidi controls removed.

Example:
    >>> strip_bidi_controls('hello\u200fworld')
    'helloworld'
    >>> strip_bidi_controls('a\u202eb\u202cc')
    'abc'

## icukit.breaker

Text segmentation using ICU BreakIterator.

This module provides text segmentation capabilities for breaking text into
sentences, words, lines, or grapheme clusters. ICU supplies every level's
boundaries; the English sentence default also applies token integrity and the
shipped abbreviation list.
Structured span offsets are Python code-point indices into the source text.

Key Features:
    * Locale-aware sentence segmentation with an English abbreviation list
    * Word tokenization with optional punctuation filtering
    * Line break detection
    * Grapheme cluster iteration (user-perceived characters)
    * Memory-efficient iteration over large texts

Example:
    >>> from icukit import break_sentences, break_words
    >>> break_sentences('Hello world. How are you?', 'en')
    ['Hello world. ', 'How are you?']
    >>> break_words('Hello, world!', 'en', skip_punctuation=True)
    ['Hello', 'world']

### Constants and type aliases

#### `BREAK_CHARACTER` (constant)

`'character'`

#### `BREAK_LINE` (constant)

`'line'`

#### `BREAK_SENTENCE` (constant)

`'sentence'`

Break type constants

#### `BREAK_WORD` (constant)

`'word'`

### class `BreakSpan`

A segment with offsets into its source text in three index spaces.

``start`` and ``end`` remain compatibility aliases for the explicitly named
``codepoint_start`` and ``codepoint_end``. ``utf8_*`` values count bytes;
``utf16_*`` values count code units.

``break_type``, present only for line spans, describes the break at the
span's end boundary.

### class `Breaker`

Text segmentation using ICU BreakIterator.

A versatile text segmentation tool that can break text into sentences,
words, lines, or grapheme clusters based on locale-specific rules. English
sentence breaking applies token integrity and shipped abbreviation
suppressions to ICU candidates by default; ``base="none"`` keeps raw ICU
sentence boundaries without the list. The learned ``"en-tn@1"`` rules and
``"en-tn-cart@1"`` model are opt-in. Other levels and non-English defaults
remain ICU behavior.

Example:
    >>> breaker = Breaker('en')
    >>> list(breaker.iter_sentences('Hello. World.'))
    ['Hello. ', 'World.']
    >>> breaker.break_words('Hello, world!', skip_punctuation=True)
    ['Hello', 'world']

#### `Breaker(locale: 'str' = 'en_US', *, base: "Literal['none', 'en-tn@1', 'en-tn-cart@1'] | None" = None)`

Initialize a Breaker instance.

Args:
    locale: Locale code for language-specific rules (e.g., 'en', 'en_US', 'ja').
    base: Sentence base only. ``None`` selects ICU plus token integrity
        and the shipped list for English except POSIX, and raw ICU
        otherwise. ``"none"`` selects raw ICU without the list;
        ``"en-tn@1"`` and ``"en-tn-cart@1"`` are opt-in English bases.

Raises:
    BreakerError: If the locale is invalid.

#### `break_grapheme_spans(text: 'str') -> 'list[BreakSpan]'`

Return every grapheme cluster as a structured span.

#### `break_graphemes(text: 'str') -> 'list[str]'`

Break text into grapheme clusters (user-perceived characters).

Useful for correctly handling emoji, combining characters, etc.

Args:
    text: The text to segment.

Returns:
    List of grapheme clusters.

Example:
    >>> breaker = Breaker('en')
    >>> breaker.break_graphemes('e\u0301')  # e + combining accent
    ['é']

#### `break_line_spans(text: 'str') -> 'list[BreakSpan]'`

Return every line-break segment as a structured span.

#### `break_lines(text: 'str') -> 'list[str]'`

Find line break opportunities in text.

Returns segments where line breaks can occur (for text wrapping).

Args:
    text: The text to analyze.

Returns:
    List of segments at line break boundaries.

#### `break_sentence_spans(text: 'str') -> 'list[BreakSpan]'`

Return sentence spans from the selected locale-default or named base.

#### `break_sentences(text: 'str', skip_empty: 'bool' = True) -> 'list[str]'`

Break text into sentences.

Args:
    text: The text to segment.
    skip_empty: If True, empty sentences are excluded.

Returns:
    List of sentence strings.

Example:
    >>> breaker = Breaker('en')
    >>> breaker.break_sentences('Hello world. How are you?')
    ['Hello world. ', 'How are you?']

#### `break_word_spans(text: 'str', skip_whitespace: 'bool' = False, skip_punctuation: 'bool' = False) -> 'list[BreakSpan]'`

Return word spans, optionally excluding whitespace or punctuation.

#### `break_words(text: 'str', skip_whitespace: 'bool' = True, skip_punctuation: 'bool' = False) -> 'list[str]'`

Break text into words.

Args:
    text: The text to tokenize.
    skip_whitespace: If True, whitespace tokens are excluded (default True).
    skip_punctuation: If True, punctuation tokens are excluded.

Returns:
    List of word/token strings.

Example:
    >>> breaker = Breaker('en')
    >>> breaker.break_words('Hello, world!')
    ['Hello', ',', 'world', '!']
    >>> breaker.break_words('Hello, world!', skip_punctuation=True)
    ['Hello', 'world']

#### `iter_grapheme_spans(text: 'str') -> 'Iterator[BreakSpan]'`

Yield every grapheme cluster with code-point offsets.

#### `iter_graphemes(text: 'str') -> 'Iterator[str]'`

Iterate over grapheme clusters.

Args:
    text: The text to segment.

Yields:
    Individual grapheme clusters.

#### `iter_line_spans(text: 'str') -> 'Iterator[BreakSpan]'`

Yield line segments; break type describes each end boundary.

#### `iter_lines(text: 'str') -> 'Iterator[str]'`

Iterate over line break segments.

Args:
    text: The text to analyze.

Yields:
    Segments at line break boundaries.

#### `iter_sentence_spans(text: 'str') -> 'Iterator[BreakSpan]'`

Yield sentence spans from the locale default or selected named base.

The English default is ICU plus token integrity and the shipped list;
non-English and POSIX defaults are raw ICU.

#### `iter_sentences(text: 'str', skip_empty: 'bool' = True) -> 'Iterator[str]'`

Iterate over sentences in text.

Memory-efficient sentence iteration.

Args:
    text: The text to segment.
    skip_empty: If True, skip empty sentences.

Yields:
    Individual sentence strings.

#### `iter_word_spans(text: 'str', skip_whitespace: 'bool' = False, skip_punctuation: 'bool' = False) -> 'Iterator[BreakSpan]'`

Yield word spans, optionally excluding whitespace or punctuation.

#### `iter_words(text: 'str', skip_whitespace: 'bool' = True, skip_punctuation: 'bool' = False) -> 'Iterator[str]'`

Iterate over words in text.

Args:
    text: The text to tokenize.
    skip_whitespace: If True, skip whitespace tokens.
    skip_punctuation: If True, skip punctuation tokens.

Yields:
    Individual word/token strings.

#### `tokenize_sentence_spans(text: 'str', skip_whitespace: 'bool' = True, skip_punctuation: 'bool' = False) -> 'list[list[BreakSpan]]'`

Break into sentences containing filtered word spans.

Word offsets remain relative to *text*, not to each sentence substring.
Empty tokenized sentences are omitted, matching :meth:`tokenize_sentences`.

#### `tokenize_sentences(text: 'str', skip_whitespace: 'bool' = True, skip_punctuation: 'bool' = False) -> 'list[list[str]]'`

Break text into sentences, then tokenize each sentence.

Args:
    text: The text to process.
    skip_whitespace: If True, skip whitespace tokens.
    skip_punctuation: If True, skip punctuation tokens.

Returns:
    List of sentences, where each sentence is a list of tokens.

Example:
    >>> breaker = Breaker('en')
    >>> breaker.tokenize_sentences('Hello world. How are you?')
    [['Hello', 'world', '.'], ['How', 'are', 'you', '?']]

### class `RuleBreaker`

Text segmentation using a custom ICU RBBI rule set.

Span types are fully caller-defined through ``status_types``. RuleBreaker
makes no assumptions about ICU's standard word-status meanings.

#### `RuleBreaker(rules: 'str', status_types: 'dict[int, str] | None' = None)`

Validate a custom rule set for subsequent segmentation.

Args:
    rules: ICU RuleBasedBreakIterator rule source.
    status_types: Optional mapping from numeric rule statuses to type names.

Raises:
    BreakerError: If ICU cannot compile the rules.

#### `iter_spans(text: 'str') -> 'Iterator[BreakSpan]'`

Yield every custom-rule segment with offsets and raw statuses.

#### `spans(text: 'str') -> 'list[BreakSpan]'`

Return every custom-rule segment as a structured span.

#### `tokens(text: 'str') -> 'list[str]'`

Return every custom-rule segment as text.

### `break_grapheme_spans(text: 'str', locale: 'str' = 'en_US') -> 'list[BreakSpan]'`

Return every grapheme cluster with code-point offsets.

### `break_graphemes(text: 'str', locale: 'str' = 'en_US') -> 'list[str]'`

Break text into grapheme clusters.

Args:
    text: The text to segment.
    locale: Locale code for language-specific rules.

Returns:
    List of grapheme clusters.

Example:
    >>> break_graphemes('👨‍👩‍👧‍👦')  # Family emoji
    ['👨‍👩‍👧‍👦']

### `break_line_spans(text: 'str', locale: 'str' = 'en_US') -> 'list[BreakSpan]'`

Return line segments whose break type describes their end boundary.

### `break_lines(text: 'str', locale: 'str' = 'en_US') -> 'list[str]'`

Find line break opportunities in text.

Args:
    text: The text to analyze.
    locale: Locale code for language-specific rules.

Returns:
    List of segments at line break boundaries.

### `break_sentence_spans(text: 'str', locale: 'str' = 'en_US', *, base: "Literal['none', 'en-tn@1', 'en-tn-cart@1'] | None" = None) -> 'list[BreakSpan]'`

Return sentence spans from the locale default or selected base.

The English default is ICU plus token integrity and the shipped list;
non-English and POSIX defaults are raw ICU.

### `break_sentences(text: 'str', locale: 'str' = 'en_US', skip_empty: 'bool' = True, *, base: "Literal['none', 'en-tn@1', 'en-tn-cart@1'] | None" = None) -> 'list[str]'`

Break text into sentences.

Convenience function that creates a Breaker for one-off use.

Args:
    text: The text to segment.
    locale: Locale code for language-specific rules.
    skip_empty: If True, empty sentences are excluded.
    base: Sentence base; ``None`` selects ICU plus token integrity and the
        shipped list for English except POSIX, and raw ICU otherwise.
        ``"none"`` selects raw ICU without the list.

Returns:
    List of sentence strings.

Example:
    >>> break_sentences('Hello. World.', 'en')
    ['Hello. ', 'World.']

### `break_word_spans(text: 'str', locale: 'str' = 'en_US', skip_whitespace: 'bool' = False, skip_punctuation: 'bool' = False) -> 'list[BreakSpan]'`

Return word spans, optionally excluding whitespace or punctuation.

### `break_words(text: 'str', locale: 'str' = 'en_US', skip_whitespace: 'bool' = True, skip_punctuation: 'bool' = False) -> 'list[str]'`

Break text into words.

Convenience function that creates a Breaker for one-off use.

Args:
    text: The text to tokenize.
    locale: Locale code for language-specific rules.
    skip_whitespace: If True, whitespace tokens are excluded.
    skip_punctuation: If True, punctuation tokens are excluded.

Returns:
    List of word/token strings.

Example:
    >>> break_words('Hello, world!', 'en', skip_punctuation=True)
    ['Hello', 'world']

### `default_rules(kind: 'str' = 'word', locale: 'str' = 'en_US') -> 'str'`

Return the standard ICU rules to use as a tailoring base.

This is a starting point for extending a rule set with custom exceptions.
Locale dictionary and keyword behavior (for example, CJK dictionary
breaking or ``lw=`` line-breaking options) is not represented in the rule
text, so a :class:`RuleBreaker` compiled from the result is not necessarily
a behavior-faithful clone of the locale iterator.

Args:
    kind: Iterator kind: ``word``, ``sentence``, ``line``, or ``grapheme``.
    locale: Locale code for the standard rule set.

Returns:
    The ICU rule source for the requested standard iterator.

Raises:
    BreakerError: If the kind is unsupported, ICU cannot load the rules, or
        the locale factory returns an iterator without extractable rules.

## icukit.cache

Process-level settings and observability for detector caches.

The first use of an expensive, registered detector table stores a local snapshot;
no prebuilt tables ship in the wheel. The root is ``ICUKIT_CACHE_DIR`` when set,
then the platform cache directory. It can instead be selected with
:func:`configure` before readers are built. The root is created with mode ``0700``.

The directory must be trusted. Table files use :mod:`marshal`; their SHA-256
detects accidental damage but does not authenticate crafted input. The key covers
icukit code and data, ICU, PyICU, CLDR, Unicode, Python, the ICU data environment,
the ICU default locale, and a hash of the available time-zone IDs. A residual risk
remains: zone display data can change without the wheel version or zone-ID set
changing. Run ``ik compile --verify`` to recompute and compare every entry.

Only registered, deterministic Python tables are serialized. ICU objects, detector
instances, and application material remain in memory. Disable all disk reads and
writes with ``configure(enabled=False)``, ``ICUKIT_CACHE=0``, or
``ik detect --no-cache``. :func:`flush` writes queued marshal snapshots explicitly;
process exit is only a fallback.

### Constants and type aliases

#### `StrPath` (type alias)

`str | os.PathLike[str]`

### `cache_enabled() -> 'bool'`

Return whether all detector caches are enabled for this call.

An explicit :func:`configure` override wins. Until one is set, the
``ICUKIT_CACHE`` environment variable is read on every call so changing it to or
from ``"0"`` takes effect without re-importing :mod:`icukit.cache`.

### `cache_info() -> 'dict'`

Return process settings, table-store counts, and compile reuse counters.

``detect_hits`` counts compiled detects that made a compatible per-text scan plan
available to the detect phase, not the number of readers or starts that used it.
``table_detect_hits`` counts persisted table entries reused during the detect phase.
``compiled_reuse`` counts gangs observed reusing their implicit compiled object.

### `configure(*, enabled: 'bool | None' = None, directory: 'StrPath | None' = None) -> 'None'`

Configure the process cache before constructing readers.

Passing ``True`` or ``False`` for ``enabled`` overrides ``ICUKIT_CACHE`` for the
in-process detector caches and the table store. Without an override, the
environment is read at each cache operation. Passing ``None`` leaves the
corresponding setting unchanged. Reconfiguration drops process-local table
snapshots so a newly selected directory is populated from the real table builders.
A configured directory must be trusted because table files use :mod:`marshal`.

### `flush() -> 'None'`

Write every queued table snapshot now.

## icukit.calendar

Calendar system information.

Query available calendar systems (Gregorian, Buddhist, Hebrew, Islamic, etc.)
and their properties.

Key Features:
    * List all available calendar types
    * Get calendar info (type, description)
    * 17+ calendar systems supported

Calendar Types:
    * gregorian - Gregorian calendar (default Western calendar)
    * buddhist - Thai Buddhist calendar
    * chinese - Chinese lunar calendar
    * coptic - Coptic calendar (Egypt)
    * ethiopic - Ethiopian calendar
    * hebrew - Hebrew/Jewish calendar
    * indian - Indian National calendar
    * islamic - Islamic/Hijri calendar (various variants)
    * japanese - Japanese Imperial calendar
    * persian - Persian/Jalali calendar
    * roc - Republic of China (Taiwan) calendar

Example:
    List and query calendars::

        >>> from icukit import list_calendars, get_calendar_info
        >>>
        >>> # List all calendar types
        >>> cals = list_calendars()
        >>> 'hebrew' in cals
        True
        >>>
        >>> # Get info about a calendar
        >>> info = get_calendar_info('islamic')
        >>> info['type']
        'islamic'

### `get_calendar_info(cal_type: 'str') -> 'dict[str, Any] | None'`

Get information about a calendar type.

Args:
    cal_type: Calendar type name (e.g., 'gregorian', 'hebrew').

Returns:
    Dict with calendar info, or None if not found.

Example:
    >>> info = get_calendar_info('hebrew')
    >>> info['type']
    'hebrew'

### `is_valid_calendar(cal_type: 'str') -> 'bool'`

Check if a calendar type is valid.

Args:
    cal_type: Calendar type to check.

Returns:
    True if valid, False otherwise.

Example:
    >>> is_valid_calendar('gregorian')
    True
    >>> is_valid_calendar('invalid')
    False

### `list_calendars() -> 'list[str]'`

List all available calendar types.

Returns:
    List of calendar type names sorted alphabetically.

Example:
    >>> cals = list_calendars()
    >>> 'gregorian' in cals
    True
    >>> 'hebrew' in cals
    True

### `list_calendars_info() -> 'list[dict[str, Any]]'`

List all calendars with their info.

Returns:
    List of dicts with calendar info.

Example:
    >>> cals = list_calendars_info()
    >>> greg = next(c for c in cals if c['type'] == 'gregorian')
    >>> 'Western' in greg['description']
    True

## icukit.classes

ICU character classes and fixed-width context windows.

The four base class alphabets are discovered from the linked ICU at import
time. Runtime material can add namespaced extension classes, but it cannot
replace any ICU value.

Example:
    >>> char_classes("Mr. 5", "sentence_break")
    ['Upper', 'Lower', 'ATerm', 'Sp', 'Numeric']
    >>> class_window("Mr. Smith", 3, before=3, after=2).before[-1].text
    '.'

### Constants and type aliases

#### `Prop` (type alias)

`Literal['word_break', 'sentence_break', 'general_category', 'script']`

A supported ICU character-property alphabet.

### class `ClassPoint`

The four ICU classes of one code point, with code-point offsets.

#### `ClassPoint(text: 'str', start: 'int', end: 'int', word_break: 'str', sentence_break: 'str', general_category: 'str', script: 'str', extension_classes: 'tuple[str, ...]' = ()) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `ClassWindow`

A fixed-width character-class window around a code-point boundary.

``before`` and ``after`` always contain their requested number of entries.
Missing entries use ``<BOS>`` or ``<EOS>`` at a known text edge and
``<PAD>`` when the supplied text is only a cutout. ``identity`` describes
the long-name feature definition and therefore does not change with
``names="short"``.

#### `ClassWindow(offset: 'int', before: 'tuple[ClassPoint, ...]', after: 'tuple[ClassPoint, ...]', identity: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `char_classes(text: 'str', prop: 'Prop' = 'general_category', /, *, material: 'Iterable[LocaleMaterial]' = ()) -> 'list[str]'`

Return one canonical long ICU property value name per code point.

ICU aliases for the property name are accepted and resolved within the
property, so a short alias cannot collide with another property alphabet.

Example:
    >>> char_classes("Mr. 5", "sentence_break")
    ['Upper', 'Lower', 'ATerm', 'Sp', 'Numeric']
    >>> char_classes("A", "gc")
    ['Uppercase_Letter']

### `class_window(text: 'str', offset: 'int', /, *, before: 'int' = 3, after: 'int' = 3, material: 'Iterable[LocaleMaterial]' = (), text_starts: 'bool' = True, text_ends: 'bool' = True, names: "Literal['long', 'short']" = 'long') -> 'ClassWindow'`

Return ICU classes immediately before and after ``offset``.

Args:
    text: Source text for the window.
    offset: Code-point boundary in ``text``.
    before: Number of entries before the boundary.
    after: Number of entries after the boundary.
    material: Validated additive character-class material.
    text_starts: Whether index zero is the start of the complete text.
    text_ends: Whether ``len(text)`` is the end of the complete text.
    names: Return ICU long or short value names.

Example:
    >>> point = class_window("Mr. Smith", 3, before=3, after=2).before[-1]
    >>> (point.text, point.word_break, point.sentence_break)
    ('.', 'MidNumLet', 'ATerm')

## icukit.cldr_symbols

CLDR's per-locale names of symbols ("&": "ampersand", "Et-Zeichen", "esperluette").

ICU names currency and unit symbols and % ‰ ‱ per locale, but other characters only in
English, by their Unicode names, and it does not ship CLDR's annotations, where the
per-locale names live. This module reads them from a snapshot of those annotations
(``data/cldr_symbols``), made by ``tools/cldr_symbol_names.py`` from a pinned CLDR
release whose version, URL, and checksum each file's header records. The snapshot
holds the symbols that are not emoji, each with its text-to-speech name and keywords,
and for each CLDR locale only what differs from what the locale inherits; the lookup
here resolves the same inheritance CLDR does (en_GB from en_001, en_001 from en, en
from root) to rebuild a locale's names.

### `cldr_locale(locale: 'str') -> 'str'`

``locale`` as CLDR names the locale whose data it reads ("zh_TW": "zh_Hant_TW").

ICU's alias resolution first ("iw": "he", "sh": "sr_Latn"), then the script ICU's
likely subtags give it, kept only where it is not the language's own likely script:
zh_TW is Traditional (zh_Hant_TW) and sr_ME Latin (sr_Latn_ME), while en_GB stays
en_GB, so that its parentLocales entry (en_001) applies. The region and variant are
the locale's own.

### `cldr_symbol_names(locale: 'str') -> 'tuple[tuple[str, str, tuple[str, ...]], ...]'`

``(symbol, name, keywords)`` for each symbol CLDR names in ``locale``.

``name`` is CLDR's text-to-speech name ("ampersand"), empty where CLDR gives only
keywords; ``keywords`` are CLDR's, in its order. Resolved through CLDR's locale
inheritance from the CLDR locale ``locale`` names (see :func:`cldr_locale`), in code
point order. Empty for a locale CLDR names no symbols in, or when the snapshot is
missing.

### `icu_cldr_version() -> 'str'`

The CLDR version of ICU's own data (root's ``Version``); empty if unreadable.

### `snapshot_cldr_version() -> 'str'`

The CLDR version the snapshot was made from ("48"); empty without a snapshot.

## icukit.collator

Locale-aware string collation and sorting.

ICU's Collator provides Unicode-compliant string comparison that respects
language-specific sorting rules.

Example:
    >>> from icukit import sort_strings
    >>> sort_strings(["café", "cafe", "CAFÉ"], "en_US")
    ['cafe', 'café', 'CAFÉ']
    >>> sort_strings(["Öl", "Ol", "öl"], "de_DE")
    ['Ol', 'Öl', 'öl']

### Constants and type aliases

#### `STRENGTH_IDENTICAL` (constant)

`'identical'`

#### `STRENGTH_PRIMARY` (constant)

`'primary'`

Collation strength levels

#### `STRENGTH_QUATERNARY` (constant)

`'quaternary'`

#### `STRENGTH_SECONDARY` (constant)

`'secondary'`

#### `STRENGTH_TERTIARY` (constant)

`'tertiary'`

### `compare_strings(a: 'str', b: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None) -> 'int'`

Compare two strings using locale-aware collation.

Args:
    a: First string.
    b: Second string.
    locale: Locale for comparison rules.
    strength: Collation strength.

Returns:
    -1 if a < b, 0 if a == b, 1 if a > b.

Example:
    >>> compare_strings("cafe", "café", "en_US")
    -1
    >>> compare_strings("cafe", "café", "en_US", strength="primary")
    0

### `get_collator_info(locale: 'str', *, include_extended: 'bool' = False) -> 'dict'`

Get information about a collator for a locale.

Args:
    locale: Locale identifier.
    include_extended: Include additional details in extended dict.

Returns:
    Dictionary with collator properties.

Example:
    >>> info = get_collator_info("de_DE")
    >>> info["locale"]
    'de_DE'

### `get_sort_key(text: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None) -> 'bytes'`

Get a binary sort key for external sorting.

Sort keys can be compared using standard byte comparison, useful for
database indexing or when sorting needs to be done outside Python.

Args:
    text: String to get sort key for.
    locale: Locale for collation rules.
    strength: Collation strength.

Returns:
    Binary sort key.

Example:
    >>> key_a = get_sort_key("apple", "en_US")
    >>> key_b = get_sort_key("banana", "en_US")
    >>> key_a < key_b
    True

### `list_collation_types() -> 'list[str]'`

List available collation types.

Returns:
    List of collation type names (e.g., standard, phonebook, emoji).

Example:
    >>> types = list_collation_types()
    >>> "phonebook" in types
    True

### `sort_strings(items: 'list[str]', locale: 'str' = 'en_US', *, reverse: 'bool' = False, strength: 'str | None' = None, case_first: 'str | None' = None) -> 'list[str]'`

Sort strings using locale-aware collation.

Args:
    items: List of strings to sort.
    locale: Locale for sorting rules (default: en_US).
    reverse: Sort in descending order.
    strength: Collation strength (primary, secondary, tertiary, quaternary, identical).
    case_first: "upper" or "lower" to control case ordering.

Returns:
    Sorted list of strings.

Example:
    >>> sort_strings(["café", "cafe", "Cafe"], "en_US")
    ['cafe', 'Cafe', 'café']
    >>> sort_strings(["ö", "o", "p"], "de_DE")
    ['o', 'ö', 'p']
    >>> sort_strings(["ö", "o", "p"], "sv_SE")
    ['o', 'p', 'ö']

## icukit.compact

Compact number formatting.

Format large numbers in abbreviated form with locale-appropriate suffixes.

This module provides a standalone interface to compact number formatting.
The core function `format_compact` is defined in `locale.py` alongside
other number formatting functions.

Styles:
    SHORT - "1.2M", "3.5K", "1,2 Mrd." (German)
    LONG  - "1.2 million", "3.5 thousand"

Example:
    >>> from icukit import format_compact
    >>>
    >>> format_compact(1234567)
    '1.2M'
    >>> format_compact(1234567, locale="de_DE")
    '1,2 Mio.'
    >>> format_compact(1234567, style="LONG")
    '1.2 million'
    >>>
    >>> format_compact(3500)
    '3.5K'
    >>> format_compact(3500, locale="ja_JP")
    '3500'  # Japanese uses 万 (10000) not K (1000)

### Constants and type aliases

#### `COMPACT_LONG` (constant)

`'LONG'`

#### `COMPACT_SHORT` (constant)

`'SHORT'`

#### `STYLE_LONG` (constant)

`'LONG'`

#### `STYLE_SHORT` (constant)

`'SHORT'`

Re-export with convenience names

### class `CompactFormatter`

Locale-aware compact number formatter.

Formats large numbers with locale-appropriate abbreviations.

Example:
    >>> fmt = CompactFormatter("en_US")
    >>> fmt.format(1234567)
    '1.2M'
    >>> fmt.format(1234567, style="LONG")
    '1.2 million'

#### `CompactFormatter(locale: 'str' = 'en_US', style: 'str' = 'SHORT')`

Create a CompactFormatter.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP")
    style: Default style (SHORT or LONG)

#### `format(number: 'int | float', style: 'str | None' = None) -> 'str'`

Format a number in compact form.

Args:
    number: Number to format
    style: Style override (SHORT or LONG)

Returns:
    Formatted string (e.g., "1.2M", "1.2 million")

Example:
    >>> fmt.format(1234567)
    '1.2M'
    >>> fmt.format(1234567, style="LONG")
    '1.2 million'

### `format_compact(value: 'int | float', locale_str: 'str' = 'en_US', style: 'str' = 'SHORT') -> 'str'`

Format a number in compact form with locale-appropriate abbreviations.

Args:
    value: Number to format.
    locale_str: Locale for formatting.
    style: COMPACT_SHORT ("1.2M") or COMPACT_LONG ("1.2 million").

Returns:
    Compact formatted string.

Example:
    >>> format_compact(1234567, 'en_US')
    '1.2M'
    >>> format_compact(1234567, 'de_DE')
    '1,2 Mio.'
    >>> format_compact(1234567, 'en_US', COMPACT_LONG)
    '1.2 million'

## icukit.compiled

Compiled detector gangs with one immutable scan plan per input text.

### class `CompileKey`

The table environment and identity of one detector gang.

#### `CompileKey(tables: 'str', locales: 'tuple[str, ...]', readers: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

#### `digest() -> 'str'`

Return SHA-256 over canonical JSON of the fields.

### class `CompileStats`

Measured reader construction/warmup and the resulting lane counts.

#### `CompileStats(build_s: 'float | None', warm_s: 'float', tables_loaded: 'int', tables_computed: 'int', lanes_gated: 'int', lanes_ungated: 'int', table_store: 'str | None') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `CompiledDetectorSet`

A detector gang prepared for shared per-text scanning.

``detectors`` is the immutable source gang. ``key`` and ``stats`` are report
properties; implicit compilation computes them only on first access.

#### `CompiledDetectorSet(detectors: 'DetectorSet') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Detect with a context-local immutable scan plan, resetting it on every exit.

#### `gate_report() -> 'tuple[LaneGate, ...]'`

Return one gate status row for every declared scan lane.

#### `warm() -> 'CompiledDetectorSet'`

Force lazy sub-readers and zone tables under the build phase.

### class `ReaderSpec`

A declarative detector gang whose construction is measured by compilation.

#### `ReaderSpec(locale: 'str', guarded: 'bool' = False, flexible: 'bool' = False, locales: 'tuple[str, ...] | None' = None, currencies: 'tuple[str, ...]' = (), units: 'tuple[str, ...]' = (), skeletons: 'tuple[str, ...] | None' = None, material: 'tuple[LocaleMaterial, ...]' = ()) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `TableKey`

Every environment field on which a persisted table can depend.

``code`` hashes loader-read package modules (source, or bytecode for a
sourceless install) and packaged data, including zip imports. ``tz`` hashes
the sorted ICU zone-ID enumeration. ``icu_env`` records ``ICU_DATA`` and
``ICU_TIMEZONE_FILES_DIR``. ``default_locale`` separates ICU fallback results
created under different process defaults.

#### `TableKey(schema: 'int', icukit: 'str', code: 'str', icu: 'str', pyicu: 'str', pyicu_dist: 'str', unicode: 'str', cldr: 'str', tz: 'str', python_tag: 'str', marshal: 'int', py_unicode: 'str', icu_env: 'str', default_locale: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

#### `digest() -> 'str'`

Return SHA-256 over the canonical fields.

#### `json() -> 'str'`

Return the canonical JSON stored beside every payload.

### `compile_detectors(detectors: 'DetectorSet | Iterable[Detector] | ReaderSpec', *, warm: 'bool' = True) -> 'CompiledDetectorSet'`

Compile a detector gang, measuring construction only for a :class:`ReaderSpec`.

## icukit.conformance

Round-trip conformance inventory for ICU-backed value detectors.

### Constants and type aliases

#### `CI_MATRIX` (constant)

`{'date_skeletons': ['yMd', 'yMMMd', 'yMMMEd', 'Hm'], 'envelopes': ['bare', 'embedded', 'astral_prefix', 'combining_prefix', 'adjacent', 'rtl_embedded'], 'locales': [{'currency': 'USD', 'id': 'en_US'}, {'currency': 'EUR', 'id': 'de_DE'}, {'currency': 'INR', 'id': 'hi_IN'}, {'currency': 'THB', 'id': 'th_TH'}, {'currency': 'IRR', 'id': 'fa_IR'}, {'currency': 'RUB', 'id': 'ru_RU'}], 'numbers': {'currency': ['1234.5'], 'decimal': ['1234567.5', '-1234567.5'], 'percent': ['0.07']}}`

#### `FULL_MATRIX` (constant)

`{'date_skeletons': ['yMd', 'yMMMd', 'yMMMEd', 'Hm'], 'envelopes': ['bare', 'embedded', 'astral_prefix', 'combining_prefix', 'adjacent', 'rtl_embedded'], 'locales': [{'currency': 'USD', 'id': 'en_US'}, {'currency': 'EUR', 'id': 'de_DE'}, {'currency': 'INR', 'id': 'hi_IN'}, {'currency': 'THB', 'id': 'th_TH'}, {'currency': 'IRR', 'id': 'fa_IR'}, {'currency': 'RUB', 'id': 'ru_RU'}], 'numbers': {'currency': ['1234.5'], 'decimal': ['1234567.5', '-1234567.5'], 'percent': ['0.07']}}`

This copy is intentional: it is the single seam at which the exhaustive profile grows.

#### `Profile` (type alias)

`Literal['ci', 'full']`

### class `Cell`

Cell(locale: 'str', category: 'str', params: 'str', value: 'str', envelope: 'str', currency: 'str | None' = None)

#### `Cell(locale: 'str', category: 'str', params: 'str', value: 'str', envelope: 'str', currency: 'str | None' = None) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `Outcome`

Outcome(reason: 'str', detail: 'str' = '', surface: 'str' = '')

#### `Outcome(reason: 'str', detail: 'str' = '', surface: 'str' = '') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `build_inventory(profile: 'Profile' = 'ci') -> 'dict'`

Build the stable, JSON-compatible defect inventory for ``profile``.

### `canonical_json(value: 'dict') -> 'str'`

Serialize an inventory in its committed canonical representation.

### `classify(cell: 'Cell') -> 'Outcome'`

Format, detect, and classify one matrix cell.

### `compare_expected(detection, text: 'str', expected_value: 'DateTimeValue | NumberValue', expected_captures: 'tuple[Capture, ...]', expected_spec: 'DateFormatSpec | NumberFormatSpec', surface: 'str') -> 'Outcome'`

Compare a detection with a complete independently constructed oracle record.

### `iter_cells(profile: 'Profile' = 'ci') -> 'list[Cell]'`



### `matrix(profile: 'Profile' = 'ci') -> 'dict'`

Return the data definition for a conformance profile.

### `matrix_digest(profile: 'Profile' = 'ci') -> 'str'`



## icukit.datetime

Locale-aware date and time formatting.

ICU's DateFormat provides sophisticated date/time formatting that adapts to
different locales and cultural conventions.

Styles:
    FULL   - Monday, January 15, 2024 at 3:45:30 PM Eastern Standard Time
    LONG   - January 15, 2024 at 3:45:30 PM EST
    MEDIUM - Jan 15, 2024, 3:45:30 PM
    SHORT  - 1/15/24, 3:45 PM

Pattern symbols:
    y - Year (yyyy=2024, yy=24)
    M - Month (M=1, MM=01, MMM=Jan, MMMM=January)
    d - Day of month (d=1, dd=01)
    E - Day of week (E=Mon, EEEE=Monday)
    h - Hour 1-12
    H - Hour 0-23
    m - Minute
    s - Second
    a - AM/PM
    z - Time zone (PST)
    Z - Time zone offset (-0800)

Example:
    >>> from icukit import DateTimeFormatter
    >>> from datetime import datetime
    >>>
    >>> fmt = DateTimeFormatter("en_US")
    >>> now = datetime.now()
    >>> print(fmt.format(now, style="SHORT"))
    1/15/24, 3:45 PM
    >>> print(fmt.format(now, pattern="EEEE, MMMM d, yyyy"))
    Monday, January 15, 2024
    >>>
    >>> fmt_de = DateTimeFormatter("de_DE")
    >>> print(fmt_de.format(now, style="LONG"))
    15. Januar 2024 um 15:45:30 MEZ

### Constants and type aliases

#### `PATTERNS` (constant)

`{'EU_DATE': 'dd/MM/yyyy', 'ISO_DATE': 'yyyy-MM-dd', 'ISO_DATETIME': "yyyy-MM-dd'T'HH:mm:ss", 'ISO_TIME': 'HH:mm:ss', 'LONG_DATE': 'EEEE, MMMM d, yyyy', 'TIME_12H': 'h:mm a', 'TIME_24H': 'HH:mm', 'US_DATE': 'MM/dd/yyyy'}`

Common named patterns

#### `SECONDS_PER_DAY` (constant)

`86400`

#### `SECONDS_PER_HOUR` (constant)

`3600`

#### `SECONDS_PER_MINUTE` (constant)

`60`

Time duration constants (seconds)

#### `SECONDS_PER_MONTH` (constant)

`2592000`

#### `SECONDS_PER_WEEK` (constant)

`604800`

#### `SECONDS_PER_YEAR` (constant)

`31536000`

#### `STYLE_FULL` (constant)

`'FULL'`

Style constants

#### `STYLE_LONG` (constant)

`'LONG'`

#### `STYLE_MEDIUM` (constant)

`'MEDIUM'`

#### `STYLE_NONE` (constant)

`'NONE'`

#### `STYLE_SHORT` (constant)

`'SHORT'`

#### `WIDTH_ABBREVIATED` (constant)

`'ABBREVIATED'`

#### `WIDTH_WIDE` (constant)

`'WIDE'`

Width constants for symbol names (matching measure.py convention)

### class `DateTimeFormatter`

Locale-aware date/time formatter.

Provides formatting with predefined styles or custom patterns,
relative time formatting, and date interval formatting.

Example:
    >>> fmt = DateTimeFormatter("fr_FR")
    >>> fmt.format(datetime.now(), style="LONG")
    '15 janvier 2024 à 15:45:30 UTC−5'
    >>> fmt.format_relative(days=-1)
    'hier'
    >>>
    >>> # Different calendar systems
    >>> fmt = DateTimeFormatter("en_US", calendar="hebrew")
    >>> fmt.format(datetime(2024, 1, 15), pattern="yyyy-MM-dd")
    '5784-04-05'

#### `DateTimeFormatter(locale: 'str' = 'en_US', calendar: 'str | None' = None)`

Create a DateTimeFormatter for the given locale.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP")
    calendar: Calendar system (e.g., "gregorian", "buddhist", "hebrew",
             "islamic", "japanese", "chinese", "persian")

#### `format(dt: 'datetime | date | time', style: 'str | None' = None, date_style: 'str | None' = None, time_style: 'str | None' = None, pattern: 'str | None' = None) -> 'str'`

Format a date/time value.

Args:
    dt: Date/time to format
    style: Combined style (FULL, LONG, MEDIUM, SHORT) for both date and time
    date_style: Date style (overrides style for date part)
    time_style: Time style (overrides style for time part, NONE for date-only)
    pattern: Custom ICU pattern (overrides all styles)

Returns:
    Formatted string

Example:
    >>> fmt.format(now, style="SHORT")
    '1/15/24, 3:45 PM'
    >>> fmt.format(now, date_style="LONG", time_style="NONE")
    'January 15, 2024'
    >>> fmt.format(now, pattern="yyyy-MM-dd")
    '2024-01-15'

#### `format_interval(start: 'datetime | date', end: 'datetime | date', skeleton: 'str' = 'yMMMd') -> 'str'`

Format a date/time interval.

Args:
    start: Start date/time
    end: End date/time
    skeleton: Format skeleton (e.g., "yMMMd", "MMMd", "Hm")

Returns:
    Formatted interval (e.g., "Jan 15 – 20, 2024")

Example:
    >>> start = date(2024, 1, 15)
    >>> end = date(2024, 1, 20)
    >>> fmt.format_interval(start, end)
    'Jan 15 – 20, 2024'

#### `format_relative(delta: 'int | timedelta | None' = None, days: 'int' = 0, hours: 'int' = 0, minutes: 'int' = 0, seconds: 'int' = 0) -> 'str'`

Format relative time.

Args:
    delta: Time delta (int for days, or timedelta object)
    days: Days offset (can combine with delta)
    hours: Hours offset
    minutes: Minutes offset
    seconds: Seconds offset

Returns:
    Relative time string (e.g., "yesterday", "in 2 hours", "3 days ago")

Example:
    >>> fmt.format_relative(days=-1)
    'yesterday'
    >>> fmt.format_relative(hours=2)
    'in 2 hours'
    >>> fmt.format_relative(timedelta(days=-7))
    '1 week ago'

#### `parse(text: 'str', pattern: 'str | None' = None) -> 'datetime'`

Parse a date/time string.

Args:
    text: String to parse
    pattern: Expected format pattern (optional, tries common formats if not given)

Returns:
    Parsed datetime

Raises:
    DateTimeError: If parsing fails

### `format_datetime(dt: 'datetime | date | time', locale: 'str' = 'en_US', calendar: 'str | None' = None, **kwargs) -> 'str'`

Format a date/time value (convenience function).

Args:
    dt: Date/time to format
    locale: Locale code
    calendar: Calendar system (e.g., "hebrew", "islamic", "buddhist")
    **kwargs: Passed to DateTimeFormatter.format()

Returns:
    Formatted string

### `format_relative(delta: 'int | timedelta | None' = None, locale: 'str' = 'en_US', calendar: 'str | None' = None, **kwargs) -> 'str'`

Format relative time (convenience function).

Args:
    delta: Time delta
    locale: Locale code
    calendar: Calendar system
    **kwargs: Passed to DateTimeFormatter.format_relative()

Returns:
    Relative time string

### `get_am_pm_strings(locale: 'str' = 'en_US', calendar: 'str | None' = None) -> 'list[str]'`

Get localized AM/PM strings.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
    calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

Returns:
    List of 2 strings: [AM, PM] or locale equivalent.

Example:
    >>> get_am_pm_strings("en_US")
    ['AM', 'PM']
    >>> get_am_pm_strings("ja_JP")
    ['午前', '午後']
    >>> get_am_pm_strings("zh_CN")
    ['上午', '下午']

### `get_date_symbols(locale: 'str' = 'en_US', calendar: 'str | None' = None) -> 'dict'`

Get all date/time symbols for a locale.

Returns a comprehensive dict of all localized date/time symbols including
month names, weekday names, era names, and AM/PM strings.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
    calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

Returns:
    Dict with all date symbols organized by category.

Example:
    >>> symbols = get_date_symbols("fr_FR")
    >>> symbols["months"]["wide"]
    ['janvier', 'février', ..., 'décembre']
    >>> symbols["weekdays"]["abbreviated"]
    ['dim.', 'lun.', 'mar.', ...]
    >>> symbols["am_pm"]
    ['AM', 'PM']

### `get_era_names(locale: 'str' = 'en_US', width: 'str' = 'WIDE', calendar: 'str | None' = None) -> 'list[str]'`

Get localized era names.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
    width: Name width - WIDTH_WIDE ("Before Christ") or WIDTH_ABBREVIATED ("BC").
    calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

Returns:
    List of era names (typically 2 for Gregorian: BC/AD or equivalent).

Example:
    >>> get_era_names("en_US")
    ['Before Christ', 'Anno Domini']
    >>> get_era_names("en_US", WIDTH_ABBREVIATED)
    ['BC', 'AD']
    >>> get_era_names("ja_JP")
    ['紀元前', '西暦']

### `get_month_names(locale: 'str' = 'en_US', width: 'str' = 'WIDE', calendar: 'str | None' = None) -> 'list[str]'`

Get localized month names.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
    width: Name width - WIDTH_WIDE ("January") or WIDTH_ABBREVIATED ("Jan").
    calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

Returns:
    List of 12 month names (January-December or equivalent).

Example:
    >>> get_month_names("en_US")
    ['January', 'February', 'March', ..., 'December']
    >>> get_month_names("de_DE", WIDTH_ABBREVIATED)
    ['Jan.', 'Feb.', 'März', ..., 'Dez.']
    >>> get_month_names("ja_JP")
    ['1月', '2月', '3月', ..., '12月']

### `get_weekday_names(locale: 'str' = 'en_US', width: 'str' = 'WIDE', calendar: 'str | None' = None) -> 'dict'`

Get localized weekday names.

Returns weekday names in standard Sunday-Saturday order, along with
metadata about which day is the first day of the week for this locale.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP").
    width: Name width - WIDTH_WIDE ("Sunday") or WIDTH_ABBREVIATED ("Sun").
    calendar: Calendar system (e.g., "gregorian", "hebrew", "islamic").

Returns:
    Dict with:
        - names: List of 7 weekday names (Sunday-Saturday order)
        - first_day_index: Index of locale's first day (0=Sunday, 1=Monday, etc.)
        - first_day: Name of locale's first day of week

Example:
    >>> get_weekday_names("en_US")
    {'names': ['Sunday', 'Monday', ...], 'first_day_index': 0, 'first_day': 'Sunday'}
    >>> get_weekday_names("de_DE")
    {'names': ['Sonntag', 'Montag', ...], 'first_day_index': 1, 'first_day': 'Montag'}
    >>> get_weekday_names("ja_JP", WIDTH_ABBREVIATED)
    {'names': ['日', '月', '火', ...], 'first_day_index': 0, 'first_day': '日'}

### `list_pattern_symbols() -> 'list[dict[str, str]]'`

List the date/time pattern symbols, with a name and an example for each.

These are the field symbols accepted in a custom ``pattern`` by
:meth:`DateTimeFormatter.format` and by the named patterns in ``PATTERNS``.

Returns:
    List of dicts with keys ``symbol``, ``name``, and ``example``, in reference
    order. Each call returns fresh dicts, so a caller may modify the result.

Example:
    >>> symbols = list_pattern_symbols()
    >>> symbols[0]['symbol']
    'y'
    >>> next(s['name'] for s in symbols if s['symbol'] == 'G')
    'Era'

### `parse_datetime(text: 'str', locale: 'str' = 'en_US', calendar: 'str | None' = None, pattern: 'str | None' = None) -> 'datetime'`

Parse a date/time string (convenience function).

Args:
    text: String to parse
    locale: Locale code
    calendar: Calendar system
    pattern: Expected format pattern

Returns:
    Parsed datetime

## icukit.detect

Typed-span detectors over icukit's offset-correct surfaces.

A *detector* finds typed spans in running text -- unanchored, partial, and tolerant of
finding nothing -- as opposed to a *parser*, which is anchored and total (requires the whole
input to be one value). This module wires two ICU capabilities that already ship in icukit
into a single detector seam that produces :class:`Detection` spans:

* :func:`regex_detect` -- ICU regular expressions with **bounded** lookbehind/lookahead used
  as context conditions (F8). The regex *match* is the detection; lookaround conditions it
  without being consumed, so a rule can assert left/right context yet emit only the span it
  is about (e.g. the abbreviation period in ``Fig. 5``). ICU refuses *unbounded* lookbehind
  at compile time, so a rule needing unbounded left context is rejected rather than hosted.

* :func:`collation_detect` -- ICU collation-aware search (F9). At ``primary`` strength the
  case and accent variants of a term collapse to one inventory entry, so a single query for
  ``fig.`` matches ``fig.``, ``Fig.``, and ``FIG.`` alike.

Both return :class:`Detection` dicts whose ``start``/``end`` are **code-point** offsets into
the source -- the same convention as :class:`icukit.breaker.BreakSpan` -- so detections
compose with segmentation spans (they may nest within, or cross, a token).

This is the producer side of the seam. Consuming detections to suppress or retype
segmentation boundaries (the exception layer) is a separate, larger piece of work.

### class `Detection`

One typed span found by a detector.

``start``/``end`` are code-point indices into the source text, half-open
(``text[start:end] == text``), matching :class:`icukit.breaker.BreakSpan`.

### `collation_detect(text: 'str', term: 'str', type: 'str', *, locale: 'str' = 'en_US', strength: 'str' = 'primary') -> 'list[Detection]'`

Detect typed spans equal to ``term`` under locale collation.

At ``primary`` strength, case and accent variants collapse, so one query matches every
surface form of the term. Raise ``strength`` to ``secondary``/``tertiary`` to tighten the
match (accent-, then case-sensitive).

Args:
    text: Source text to scan.
    term: Inventory term to match under collation.
    type: Type label carried on every detection.
    locale: Collation locale.
    strength: Collation strength -- ``primary`` (loosest), ``secondary``, ``tertiary``.

Returns:
    Detections in source order (empty if nothing matches).

### `regex_detect(text: 'str', pattern: 'str', type: 'str', *, flags: 'int' = 0) -> 'list[Detection]'`

Detect typed spans with an ICU regex whose match is the span.

``pattern`` may use bounded lookbehind ``(?<=...)`` and lookahead ``(?=...)`` to condition
the match on surrounding context; only the match extent becomes the detection. ICU rejects
unbounded lookbehind at compile time, so a pattern that needs it raises rather than
silently matching -- the seam refuses an unhostable rule rather than hosting it wrong.

Args:
    text: Source text to scan.
    pattern: ICU regex; its match extent is the detected span.
    type: Type label carried on every detection.
    flags: ICU regex flags forwarded to the matcher.

Returns:
    Detections in source order (empty if nothing matches).

Raises:
    Whatever :class:`icukit.regex.UnicodeRegex` raises for an invalid or unhostable
    pattern -- notably a compile error for unbounded lookbehind.

## icukit.detectors

Detectors: find typed values in running text by inverting ICU's formatting.

This module holds what every reader shares -- the value and spec records, the
:class:`ValueDetection` shape, the :class:`Detector` protocol, and the
:class:`DetectorSet` gang -- and the strict readers, :class:`DateDetector` and
:class:`NumberDetector`, where an ICU parser inverts the formatter (dates, times,
datetimes, decimal numbers, currency, percent). The flexible readers, which read the
forms text writes beyond ICU's own, are in :mod:`icukit.recognize`; the assembled sets
are :func:`~icukit.engine.generated_detectors` (a reader for each canonical ICU form)
and :func:`~icukit.engine.flexible_detectors`.

Each accepted match is a :class:`ValueDetection` that carries the structure of the
parse::

    surface  <->  (spec, value, captures)

For the strict readers the invariant ``reformat(spec, value) == surface`` is also the
acceptance test, so a permissive ICU spelling that would not reproduce its own surface
is rejected rather than accepted.

* ``value`` -- an immutable semantic record (:class:`DateTimeValue` / :class:`NumberValue`).
  Numeric values are canonical decimal *strings* derived from the accepted surface, never a
  binary ``float`` (this PyICU's ``Formattable`` has no decimal accessor, so a float would
  otherwise be smuggled in).
* ``captures`` -- the named sub-parts of the match (:class:`Capture`): year/month/day of a
  date, sign/integer/fraction of a number, each with its own source span, resolved value,
  and form (short/wide/numeric/symbol). They reveal *how* the surface decomposes.
* ``spec`` -- the generative recipe (:class:`DateFormatSpec` / :class:`NumberFormatSpec`):
  the parameters sufficient to reproduce the surface. Calendars are *observed*, not assumed
  Gregorian, so a Buddhist or Persian locale round-trips correctly.

Detectors run individually (``detector.detect(text)``) or ganged in an immutable
:class:`DetectorSet`; a gang's result equals the merge of running its members alone.
Everything here is pure icukit over code-point offsets -- no tiergraph.

### class `ApproximateValue`

An amount written with an approximately sign ICU writes ("~3", "≈3", "約3").

#### `ApproximateValue(value: 'NumberValue | MeasureValue') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `Capture`

One named sub-part of a match, revealing the parse structure.

``start``/``end`` are code-point offsets into the *source* text (half-open), so
``text[start:end]`` is this part's surface. ``value`` is the resolved value --
numeric (``day`` -> ``3``) or an enumerated member (``weekday`` -> ``"wednesday"``,
``month`` -> ``1``). ``form`` is how the surface encodes it: ``"numeric"``,
``"short"``, ``"wide"``, ``"narrow"``, or ``"symbol"``.

#### `Capture(name: 'str', start: 'int', end: 'int', text: 'str', value: 'object | None' = None, form: 'str | None' = None) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `CompactFormatSpec`

The locale and width used for a compact-number candidate.

#### `CompactFormatSpec(locale: 'str', width: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `DateDetector`

Detect canonical ICU date surfaces for ``locale`` and ``skeleton``.

The public ``tz`` parameter is deliberately restricted to ``"GMT"``: the current
date specification fixes GMT so date-only parsing cannot acquire host-zone behavior.

A year from a ``y`` field is read only in four or more digits when this locale's
calendar writes its current year that way; a shorter one cannot be told from a
count after a month ("June 200", "August 9", "3/4"). Calendars whose current era
naturally has a short year, such as Japanese and ROC calendars, keep that canonical
short year. A ``yy`` field keeps its two digits.

An era field (``G``, any width) is read where the pattern writes it, in the locale's
own calendar (the Buddhist era in ``th``, the Persian in ``fa``), as ICU formats it;
it is captured as ``era`` and valued ``("G", era)``, ICU's era index, beside the year
of that era ("Mar 15, 2024 BC" is ``(("G", 0), ("y", 2024), ...)``). The year
beside an era keeps the four-digit floor only when ICU writes the current year of
that locale's calendar in four or more digits: a short number before a short era is
as often a count before a unit or a clock ("100 م" is 100 meters in Arabic, "5 م"
five PM, "7 AD units").

``short_years=True`` builds the guarded reader of exactly the readings that floor
refuses: a pattern with an era, read with a year of one to three digits ("Mar 15,
44 BC" is ``(("G", 0), ("y", 44), ...)``, the year as written, never widened to a
century). Its type is ``date:short-year:<skeleton>``, beside the text-date reader's
``date:short-year``, and a pattern without an era refuses it.

#### `DateDetector(locale: 'str', skeleton: 'str', tz: 'str' = 'GMT', *, short_years: 'bool' = False) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`



#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `DateFormatSpec`

The generative recipe for a temporal detection.

``skeleton`` is the caller's canonical skeleton; ``pattern`` is the locale best
pattern actually used; ``calendar`` is observed from the constructed formatter, not
assumed. ``field_forms`` records each present field's form (``("month", "short")``).

#### `DateFormatSpec(locale: 'str', skeleton: 'str', pattern: 'str', calendar: 'str', tz: 'str' = 'GMT', field_forms: 'tuple[tuple[str, str], ...]' = ()) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `DateIntervalSpec`

Generative recipe for a date-interval detection.

``locale`` and ``skeleton`` select the ICU :class:`DateIntervalFormat` that
reproduces the surface.

#### `DateIntervalSpec(locale: 'str', skeleton: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `DateIntervalValue`

A recovered (start, end) civil date/time interval.

Each endpoint is a :class:`DateTimeValue` holding only the fields the interval pins
(shared higher-order fields inherited on both ends), with 1-based months and the
observed calendar.

#### `DateIntervalValue(start: 'DateTimeValue', end: 'DateTimeValue') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `DateTimeValue`

Civil date/time fields recovered from a temporal parse.

``fields`` holds only the fields the pattern actually pins, as ``(name, value)``
pairs in canonical order (e.g. ``(("y", 2569), ("M", 1), ("d", 3))``). ``calendar``
is the *observed* calendar of those fields -- ``"buddhist"`` for ``th_TH`` etc. -- so
the year is the value displayed in that calendar, matching the surface. A moment is
*derivable* from these fields plus the spec's calendar and time zone when a caller
needs one; it is never stored, so the record never implies a time the surface did
not show.

#### `DateTimeValue(fields: 'tuple[tuple[str, int], ...]', calendar: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `Detector`

A runnable detector.

``type`` is the stable label carried on its detections (``date:yMMMd``,
``number:currency:USD``); ``group`` is its coarse family (``date``, ``number``) and
equals the ``type`` prefix. ``detect`` scans the whole text and returns its
detections in source order -- unanchored, partial, tolerant of finding nothing.

#### `Detector(*args, **kwargs)`



#### `detect(text: 'str') -> 'list[ValueDetection]'`



### class `DetectorRefusal`

An ostensibly-successful ICU parse produced an unrepresentable endpoint.

This is *not* a parse miss (a miss is silent and returns no candidate). It signals a
reversed, surrogate-interior, or mid-grapheme endpoint -- an invariant violation the
detector refuses to represent rather than emit wrongly. It carries a stable
``reason`` from :data:`RefusalReason` and the offsets involved.

#### `DetectorRefusal(type: 'str', start: 'int', endpoint: 'int | None', reason: 'RefusalReason', message: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

### class `DetectorSet`

An immutable gang of detectors that runs its members together.

``detect`` returns exactly the merge of running each member individually (the same
result :func:`detect` would give). A gang is a value -- there is no mutable global
registry; selection and grouping are expressed by composing gangs with
:meth:`with_` / :meth:`without`.

A member is identified by its type, its reader class, its locale, the locales it
reads, and any user-material content digest (see :func:`detector_key`), so an en_US
and an en_GB detector of one type share a gang, as do a strict and a flexible reader
of one type, while same-type readers from different materials coexist.

#### `DetectorSet(detectors: 'tuple[Detector, ...]') -> None`

Initialize self.  See help(type(self)) for accurate signature.

#### `compile(*, warm: 'bool' = True) -> 'CompiledDetectorSet'`

Compile this gang explicitly, optionally forcing lazy reader state.

#### `detect(text: 'str') -> 'list[ValueDetection]'`



#### `names() -> 'tuple[str, ...]'`

The members' types, in order; a type repeats once per locale it is built for.

#### `with_(*more: 'Detector') -> 'DetectorSet'`

Return a new gang with ``more`` detectors added.

A detector with the same key as a member (:func:`detector_key`) replaces it in
place.

#### `without(*types: 'str', locale: 'str | None' = None) -> 'DetectorSet'`

Return a new gang with the named detector types removed.

Every locale's member of a type is removed, or only ``locale``'s when given.

### class `GatedDetector`

A detector which declares a sound gate for each start-scanning lane.

#### `GatedDetector(*args, **kwargs)`



#### `detect(text: 'str') -> 'list[ValueDetection]'`



#### `start_gates() -> 'Mapping[str, StartGate | None]'`



### class `MeasureFormatSpec`

The locale, canonical ICU unit, and width used for a measure candidate.

#### `MeasureFormatSpec(locale: 'str', unit: 'str', width: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `MeasureValue`

A numeric value paired with its canonical ICU unit identifier.

#### `MeasureValue(decimal: 'str', unit: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `NumberDetector`

Detect canonical ICU decimal, currency, or percent surfaces.

#### `NumberDetector(locale: 'str', kind: "Literal['decimal', 'currency', 'percent']", currency: 'str | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`



#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `NumberFormatSpec`

The generative recipe for a numeric detection.

``grouping_sizes`` are Known from the formatter (e.g. ``(3,)`` for en_US,
``(2, 3)`` for hi_IN Indian grouping), not read off one value; ``None`` when the
formatter groups by no fixed size. ``min_fraction``/``max_fraction`` are the
formatter's configured fraction-digit bounds.

#### `NumberFormatSpec(locale: 'str', kind: "Literal['decimal', 'currency', 'percent', 'scientific']", currency: 'str | None' = None, min_fraction: 'int | None' = None, max_fraction: 'int | None' = None, grouping_sizes: 'tuple[int, ...] | None' = None) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `NumberRangeSpec`

The locale and form of a number-range or approximately candidate.

``form`` is ``"range"`` (a separator ICU's ``NumberRangeFormatter`` writes) or
``"approximately"``. ``collapse`` is ``"unit"`` when one side's unit is shared with
the other ("$3–5"), else ``"none"``; ``mark`` is the separator or the approximately
sign as written, without the spaces around it.

#### `NumberRangeSpec(locale: 'str', form: 'str', collapse: 'str', mark: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `NumberRangeValue`

A recovered (start, end) range of two amounts, as ICU's NumberRangeFormatter writes.

Each endpoint is a :class:`NumberValue` (a number, a percent's ratio, or a currency
amount) or a :class:`MeasureValue`. A side written without its unit ("$3–5",
"10–15 kg", where ICU collapses the unit onto one side) carries the unit the other
side writes, so both endpoints are whole amounts.

#### `NumberRangeValue(start: 'NumberValue | MeasureValue', end: 'NumberValue | MeasureValue') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `NumberValue`

A numeric value recovered as a canonical decimal string.

``decimal`` is derived from the accepted surface (locale digits and separators
normalized to ASCII), never from a binary ``float``. For a percent it is the ratio
(``"7%"`` -> ``"0.07"``); for a currency, ``currency`` carries the ISO 4217 code.

#### `NumberValue(decimal: 'str', currency: 'str | None' = None) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `RelativeDateSpec`

The locale used to generate a relative-date phrase.

#### `RelativeDateSpec(locale: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `RelativeDateValue`

A signed relative offset in one duration unit.

#### `RelativeDateValue(offset: 'int', unit: 'str', direction: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `SpelloutFormatSpec`

The locale and ICU rule set used for a spelled-out cardinal candidate.

#### `SpelloutFormatSpec(locale: 'str', ruleset: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `UnitValue`

A unit written without an amount, such as a rate's per form ("/s").

``unit`` is the canonical ICU identifier (``per-second``). There is no amount, so
none is recorded.

#### `UnitValue(unit: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `ValueDetection`

A typed detection with formatter structure or recall annotations.

Inherits ``text``/``start``/``end``/``type`` (code-point offsets) and adds ``value``,
``captures``, and ``spec`` (see the module docstring). For the strict,
formatter-inverting detector family, ``reformat(spec, value) == text`` holds for every
accepted detection. Recall recognizers such as ``Flexible*`` and abbreviations instead
deposit structurally valid candidates with an explicit surface or annotation model.
Abbreviation surfaces round-trip by identity; their expansions are annotations, never
reformats.

### `abbreviation_detectors(locale: 'str' = 'en') -> 'DetectorSet'`

The lexicon-backed abbreviation detector, or an empty gang when unavailable.

### `all_detectors(locale: 'str', skeletons: 'Iterable[str]', *, currencies: 'Iterable[str]' = (), flexible: 'bool' = False, abbreviations: 'bool' = False, locales: 'Iterable[str] | None' = None) -> 'DetectorSet'`

Date detectors for ``skeletons`` plus the decimal, percent, and currency detectors.

A convenience composition of :func:`date_detectors` and :func:`number_detectors` for
``locale`` into one gang.

### `date_detectors(locale: 'str', skeletons: 'Iterable[str]', *, flexible: 'bool' = False, locales: 'Iterable[str] | None' = None) -> 'DetectorSet'`

A gang of date detectors for ``locale``, one per skeleton.

``skeletons`` are ICU date-time skeletons (``"yMd"``, ``"yMMMd"``); each becomes a
:class:`DateDetector`. Members are deduplicated by type, so a repeated skeleton is
harmless. A skeleton whose pattern carries an uninvertible field raises (see
:class:`DateDetector`). When ``flexible`` is true, the gang additionally contains
only a :class:`~icukit.recognize.FlexibleTextDateDetector`; it does not add the
flexible numeric-date or other flexible date recognizers. ``locales`` chooses the
other locales of the language that reader reads (every one by default).

### `detect(text: 'str', detectors: 'list[Detector] | tuple[Detector, ...]') -> 'list[ValueDetection]'`

Run every detector over ``text`` and return the merged detections.

Detections are returned in a fully deterministic order (start ascending, longer
extent first, then type, then value key) independent of ``detectors`` order.
Detections from different detectors may overlap: recognition keeps every
candidate, and choosing among overlapping readings is left to the consumer.

Each detector runs its own scan, so a gang's result equals the merge of running its
members alone. A single shared scan would be faster; any such scan must give this
same merge.

### `detector_key(detector: 'Detector') -> 'tuple[str, str, str | None, tuple[str, ...] | None, str | None]'`

A detector's identity: type, class, locale, read locales, and material digest.

The locales are the ones the reader actually reads: a reader with no choice of
locales reads its own locale alone, and a language-wide reader left at its default
(``locales=None``) reads every ICU locale of the language, spelled out. So two
readers share a key only when they are the same kind of reader reading the same
locales -- a strict currency reader and a flexible one of the same type and locale
are two members, not one replacing the other -- while a reader built twice, or once
with ``locales=None`` and once with every locale named, is one member. The digest is
``None`` for ICU and curated readers; material readers carry their content digest so
same-type readers from distinct materials coexist.

### `number_detectors(locale: 'str', *, decimal: 'bool' = True, percent: 'bool' = True, currencies: 'Iterable[str]' = (), flexible: 'bool' = False) -> 'DetectorSet'`

A gang of number detectors for ``locale``.

``decimal`` and ``percent`` add the plain decimal and percent detectors; each ISO code
in ``currencies`` adds a currency detector (type ``number:currency:<ISO>``).
When ``flexible`` is true, the gang additionally contains only a
:class:`~icukit.recognize.FlexibleCurrencyNameDetector` for each requested currency;
it does not add flexible decimal, percent, symbol-currency, compact, scientific,
spellout, fraction, or ordinal recognizers.

## icukit.discover

Discovery utilities for icukit features and capabilities.

This module provides introspection of icukit's API and CLI, helping users
discover available functionality. It dynamically reflects the actual
exports and commands rather than hardcoding them.

Note: Import this module directly (from icukit.discover import ...) rather
than from icukit to avoid circular imports.

### `discover_features() -> 'dict[str, Any]'`

Discover all available features in icukit.

Returns:
    Dictionary with API exports and CLI commands

### `get_api_exports() -> 'list[str]'`

Get all exported API functions and classes.

Returns:
    List of exported names from icukit.__all__

### `get_api_info(name: 'str') -> 'dict[str, Any] | None'`

Get information about an API export.

Args:
    name: Name of the exported function/class

Returns:
    Dictionary with name, type, signature, and docstring, or None if not found

### `get_cli_commands() -> 'dict[str, dict[str, Any]]'`

Get available CLI commands with their details.

Returns:
    Dictionary mapping command names to their info (aliases, minimal_prefix)

### `render_discovery_report() -> 'str'`

Build a formatted discovery report string.

Returns:
    The report as a multi-line string (the caller decides where to print).

### `search_features(query: 'str') -> 'dict[str, list[str]]'`

Search for features matching a query.

Args:
    query: Search term (case-insensitive)

Returns:
    Dictionary with matching API exports and CLI commands

## icukit.displayname

Locale-aware display names.

Get localized names for languages, scripts, regions, currencies, and
calendar types using ICU's display name capabilities.

Example:
    >>> from icukit import get_language_name, get_region_name, get_currency_name
    >>>
    >>> get_language_name("zh", "en")
    'Chinese'
    >>> get_language_name("zh", "de")
    'Chinesisch'
    >>> get_language_name("zh", "ja")
    '中国語'
    >>>
    >>> get_region_name("JP", "en")
    'Japan'
    >>> get_region_name("JP", "ja")
    '日本'
    >>>
    >>> get_currency_name("USD", "en")
    'US Dollar'
    >>> get_currency_name("USD", "ja")
    '米ドル'

### class `DisplayNames`

Locale-aware display names provider.

Provides localized names for languages, scripts, regions, and currencies.

Example:
    >>> names = DisplayNames("de")
    >>> names.language("zh")
    'Chinesisch'
    >>> names.region("JP")
    'Japan'
    >>> names.currency("USD")
    'US-Dollar'

#### `DisplayNames(display_locale: 'str' = 'en_US')`

Create a DisplayNames instance.

Args:
    display_locale: Locale for the display names (e.g., "en", "de", "ja")

#### `currency(currency_code: 'str') -> 'str'`

Get the display name for a currency.

Args:
    currency_code: ISO 4217 currency code (e.g., "USD", "EUR", "JPY")

Returns:
    Localized currency name

Example:
    >>> names = DisplayNames("de")
    >>> names.currency("USD")
    'US-Dollar'

#### `currency_symbol(currency_code: 'str') -> 'str'`

Get the currency symbol.

Args:
    currency_code: ISO 4217 currency code (e.g., "USD", "EUR", "JPY")

Returns:
    Currency symbol (e.g., "$", "€", "¥")

Example:
    >>> names = DisplayNames("en_US")
    >>> names.currency_symbol("USD")
    '$'
    >>> names.currency_symbol("EUR")
    '€'

#### `language(language_code: 'str') -> 'str'`

Get the display name for a language.

Args:
    language_code: ISO 639 language code (e.g., "en", "zh", "ar")

Returns:
    Localized language name

Example:
    >>> names = DisplayNames("de")
    >>> names.language("zh")
    'Chinesisch'

#### `locale(locale_code: 'str') -> 'str'`

Get the display name for a locale.

Args:
    locale_code: Locale code (e.g., "en_US", "zh_Hans_CN", "de_DE")

Returns:
    Localized locale name

Example:
    >>> names = DisplayNames("en")
    >>> names.locale("zh_Hans_CN")
    'Chinese (Simplified, China)'

#### `region(region_code: 'str') -> 'str'`

Get the display name for a region/country.

Args:
    region_code: ISO 3166-1 alpha-2 region code (e.g., "US", "JP", "DE")

Returns:
    Localized region name

Example:
    >>> names = DisplayNames("ja")
    >>> names.region("US")
    'アメリカ合衆国'

#### `script(script_code: 'str') -> 'str'`

Get the display name for a script.

Args:
    script_code: ISO 15924 script code (e.g., "Latn", "Cyrl", "Hans")

Returns:
    Localized script name

Example:
    >>> names = DisplayNames("en")
    >>> names.script("Cyrl")
    'Cyrillic'
    >>> names.script("Hans")
    'Simplified Han'

### `get_currency_name(currency_code: 'str', display_locale: 'str' = 'en_US') -> 'str'`

Get the display name for a currency (convenience function).

Args:
    currency_code: ISO 4217 currency code
    display_locale: Locale for the display name

Returns:
    Localized currency name

Example:
    >>> get_currency_name("USD", "en")
    'US Dollar'
    >>> get_currency_name("USD", "ja")
    '米ドル'

### `get_currency_symbol(currency_code: 'str', display_locale: 'str' = 'en_US') -> 'str'`

Get the currency symbol (convenience function).

Args:
    currency_code: ISO 4217 currency code
    display_locale: Locale for symbol formatting

Returns:
    Currency symbol

Example:
    >>> get_currency_symbol("USD", "en_US")
    '$'
    >>> get_currency_symbol("EUR", "de_DE")
    '€'

### `get_language_name(language_code: 'str', display_locale: 'str' = 'en_US') -> 'str'`

Get the display name for a language (convenience function).

Args:
    language_code: ISO 639 language code
    display_locale: Locale for the display name

Returns:
    Localized language name

Example:
    >>> get_language_name("zh", "en")
    'Chinese'
    >>> get_language_name("zh", "de")
    'Chinesisch'

### `get_locale_name(locale_code: 'str', display_locale: 'str' = 'en_US') -> 'str'`

Get the display name for a locale (convenience function).

Args:
    locale_code: Locale code
    display_locale: Locale for the display name

Returns:
    Localized locale name

Example:
    >>> get_locale_name("zh_Hans_CN", "en")
    'Chinese (Simplified, China)'

### `get_region_name(region_code: 'str', display_locale: 'str' = 'en_US') -> 'str'`

Get the display name for a region/country (convenience function).

Args:
    region_code: ISO 3166-1 alpha-2 region code
    display_locale: Locale for the display name

Returns:
    Localized region name

Example:
    >>> get_region_name("JP", "en")
    'Japan'
    >>> get_region_name("JP", "ja")
    '日本'

### `get_script_name(script_code: 'str', display_locale: 'str' = 'en_US') -> 'str'`

Get the display name for a script (convenience function).

Args:
    script_code: ISO 15924 script code
    display_locale: Locale for the display name

Returns:
    Localized script name

Example:
    >>> get_script_name("Cyrl", "en")
    'Cyrillic'

## icukit.duration

Locale-aware duration formatting.

Format time durations (e.g., "2 hours, 30 minutes") with proper locale
conventions using ICU's MeasureFormat.

Width Styles:
    WIDE   - "2 hours, 30 minutes, 15 seconds"
    SHORT  - "2 hr, 30 min, 15 sec"
    NARROW - "2h 30m 15s"

Example:
    >>> from icukit import format_duration, DurationFormatter
    >>>
    >>> format_duration(3661)  # seconds
    '1 hour, 1 minute, 1 second'
    >>>
    >>> format_duration(3661, locale="de_DE")
    '1 Stunde, 1 Minute und 1 Sekunde'
    >>>
    >>> format_duration(3661, width="SHORT")
    '1 hr, 1 min, 1 sec'
    >>>
    >>> fmt = DurationFormatter("ja_JP", width="NARROW")
    >>> fmt.format(hours=2, minutes=30)
    '2時間30分'

### Constants and type aliases

#### `WIDTH_NARROW` (constant)

`'NARROW'`

#### `WIDTH_SHORT` (constant)

`'SHORT'`

#### `WIDTH_WIDE` (constant)

`'WIDE'`

Width constants

### class `DurationFormatter`

Locale-aware duration formatter.

Formats time durations with proper locale conventions.

Example:
    >>> fmt = DurationFormatter("en_US")
    >>> fmt.format(hours=2, minutes=30)
    '2 hours, 30 minutes'
    >>> fmt.format(seconds=3661)
    '1 hour, 1 minute, 1 second'

#### `DurationFormatter(locale: 'str' = 'en_US', width: 'str' = 'WIDE')`

Create a DurationFormatter.

Args:
    locale: Locale code (e.g., "en_US", "de_DE")
    width: Width style (WIDE, SHORT, NARROW)

#### `format(seconds: 'float | None' = None, minutes: 'float' = 0, hours: 'float' = 0, days: 'float' = 0, weeks: 'float' = 0, months: 'float' = 0, years: 'float' = 0) -> 'str'`

Format a duration.

Args:
    seconds: Total seconds (will be decomposed if other args are 0),
            or just the seconds component if other args are provided
    minutes: Minutes component
    hours: Hours component
    days: Days component
    weeks: Weeks component
    months: Months component
    years: Years component

Returns:
    Formatted duration string

Example:
    >>> fmt.format(seconds=3661)
    '1 hour, 1 minute, 1 second'
    >>> fmt.format(hours=2, minutes=30)
    '2 hours, 30 minutes'

#### `format_iso(iso_string: 'str') -> 'str'`

Format an ISO 8601 duration string.

Args:
    iso_string: ISO 8601 duration (e.g., "P2DT3H30M")

Returns:
    Formatted duration string

Example:
    >>> fmt.format_iso("P2DT3H30M")
    '2 days, 3 hours, 30 minutes'

### `format_duration(seconds: 'float | None' = None, locale: 'str' = 'en_US', width: 'str' = 'WIDE', **kwargs) -> 'str'`

Format a duration (convenience function).

Args:
    seconds: Total seconds (or provide individual components via kwargs)
    locale: Locale code
    width: Width style (WIDE, SHORT, NARROW)
    **kwargs: Individual components (minutes, hours, days, weeks, months, years)

Returns:
    Formatted duration string

Example:
    >>> format_duration(3661)
    '1 hour, 1 minute, 1 second'
    >>> format_duration(3661, locale="de_DE")
    '1 Stunde, 1 Minute und 1 Sekunde'
    >>> format_duration(hours=2, minutes=30)
    '2 hours, 30 minutes'

### `parse_iso_duration(iso_string: 'str') -> 'dict'`

Parse an ISO 8601 duration string.

Args:
    iso_string: ISO 8601 duration (e.g., "P2DT3H30M", "PT1H30M")

Returns:
    Dictionary with duration components (years, months, days, hours, minutes, seconds)

Raises:
    DurationError: If parsing fails

Example:
    >>> parse_iso_duration("P2DT3H30M")
    {'years': 0, 'months': 0, 'weeks': 0, 'days': 2, 'hours': 3, 'minutes': 30, 'seconds': 0}
    >>> parse_iso_duration("PT1H30M15S")
    {'years': 0, 'months': 0, 'weeks': 0, 'days': 0, 'hours': 1, 'minutes': 30, 'seconds': 15}

## icukit.engine

Introspect ICU surfaces and inventories to derive gangs of detectors.

Each :class:`Family` enumerates specifications from ICU or a packaged typed inventory and
attempts to construct one detector per specification. Unsupported specifications are
observable in the generation report, rather than making generation fail or silently
narrowing the enumerated surface. The abbreviation family is inventory-driven because
expansion is intentionally not an invertible formatter operation.

:data:`DEFAULT_FAMILIES` is the default gang. :data:`GUARDED_FAMILIES` generates the
readers of the readings the default readers refuse on purpose -- a lone "one" or
"first", a lowercase Roman numeral, a month or weekday name alone, a bare hour, a date
with a two- or three-digit year, a year range ICU never writes ("1914-1918",
"1893–94") -- each under its own type, so a consumer that wants
every path (a lattice for forced alignment) opts in with
``generated_detectors(locale, (*DEFAULT_FAMILIES, *GUARDED_FAMILIES))`` or adds one
reader to a gang with ``DetectorSet.with_``, and one that does not leaves them out.

:func:`flexible_detectors` assembles the flexible (recall) readers of
:mod:`icukit.recognize` for a locale, each reader that takes a parameter built for the
values it chooses from ICU; ``guarded=True`` adds the guarded readers.

### Constants and type aliases

#### `ABBREVIATION_FAMILY` (constant)

`<icukit.engine.Family>`

#### `BARE_HOUR_FAMILY` (constant)

`<icukit.engine.Family>`

#### `COMPACT_NUMBER_FAMILY` (constant)

`<icukit.engine.Family>`

#### `DATE_INTERVAL_FAMILY` (constant)

`<icukit.engine.Family>`

#### `DATE_TIME_SKELETON_FAMILY` (constant)

`<icukit.engine.Family>`

#### `DEFAULT_FAMILIES` (constant)

`(<icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>)`

note: A measure family belongs here once its ICU surfaces have an introspective
inverter. Abbreviations use their typed lexicon.

#### `GUARDED_FAMILIES` (constant)

`(<icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>)`

The readings the default readers refuse on purpose, each under its own type; not in
DEFAULT_FAMILIES, so a consumer opts in (see the module docstring).

#### `LONE_SPELLOUT_NUMBER_FAMILY` (constant)

`<icukit.engine.Family>`

#### `LOWERCASE_ROMAN_FAMILY` (constant)

`<icukit.engine.Family>`

#### `MONTH_NAME_FAMILY` (constant)

`<icukit.engine.Family>`

#### `NUMBER_RANGE_FAMILY` (constant)

`<icukit.engine.Family>`

#### `RELATIVE_DATE_FAMILY` (constant)

`<icukit.engine.Family>`

#### `SCIENTIFIC_NUMBER_FAMILY` (constant)

`<icukit.engine.Family>`

#### `SHORT_YEAR_ERA_FAMILY` (constant)

`<icukit.engine.Family>`

The skeletons whose patterns write an era, each read with a year of one to three
digits, which the default skeleton readers refuse (see DateDetector); the type is
date:short-year:<skeleton>, one reader per skeleton as in the default family.

#### `SHORT_YEAR_FAMILY` (constant)

`<icukit.engine.Family>`

#### `SHORT_YEAR_INTERVAL_FAMILY` (constant)

`<icukit.engine.Family>`

The interval skeletons whose patterns write a "y" year, each read with a year of one to
three digits, which the default interval readers refuse ("3–5" is not years 3 to 5);
the type is date-interval:short-year:<skeleton>.

#### `SPELLOUT_NUMBER_FAMILY` (constant)

`<icukit.engine.Family>`

#### `WEEKDAY_NAME_FAMILY` (constant)

`<icukit.engine.Family>`

### class `Family`

An introspective formatter family that can derive detectors for its specs.

#### `Family(name: 'str', enumerate: 'Callable[[str], Iterable[Spec]]', invert: 'Callable[[Spec, str], Detector | None]', skip_reason: 'Callable[[Spec, str], str] | None' = None) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `GenerationReport`

Generated detectors together with every specification that was skipped.

#### `GenerationReport(detectors: 'DetectorSet', skipped: 'tuple[SkippedSpec, ...]') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `SkippedSpec`

A formatter specification that its family could not invert.

#### `SkippedSpec(family: 'str', spec: 'Spec', reason: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `clear_detector_caches() -> 'None'`

Clear all process-wide detector-construction caches.

This clears generated and flexible gang memos, shared number readers, derived
per-locale currency, measure, digit, plural, and time-zone tables, and the table
store's loaded values. It does not delete table-store files. Compiled sets and their
text plans belong to individual :class:`DetectorSet` instances, not a process-global
cache, so they are not reset here. Use :func:`icukit.cache.configure` or
``ICUKIT_CACHE=0`` to bypass the gang memo, implicit compilation, and table store.

### `flexible_detectors(locale: 'str', *, locales: 'Iterable[str] | None' = None, currencies: 'Iterable[str] | None' = None, units: 'Iterable[str] | None' = None, guarded: 'bool' = False, material: 'Iterable[LocaleMaterial]' = ()) -> 'DetectorSet'`

A gang of every flexible (recall) reader of :mod:`icukit.recognize` for ``locale``.

It holds the numeric, percent, fraction, ordinal, plural-numeral, scientific,
compact (each ICU width), spell-out (each RBNF spell-out rule set), currency and
currency-name, measure, mixed-measure, numeric-duration, numeric-date, text-date,
date-time, time, relative-date, and date-interval (each skeleton ICU gives an
interval, a zoned one in both the generic and the specific zone family, hmv and
hmz) readers, the letter-name, single-letter-word, and alphanumeric-run readers,
and the number range readers over the set's own number, percent, and currency
readers (``number:range``, ``number:approximately``) and over its measure readers
(``measure:range``, ``measure:approximately``). Where :func:`generated_detectors`
builds a reader of the same type, class, and locales, the two share a key (see
:func:`~icukit.detectors.detector_key`) and the one added last stands, so
``generated_detectors(locale).with_(*flexible_detectors(locale).detectors)`` is the
strict and flexible readers together. Most such pairs are one reader built twice;
the range readers are not: the generated ``number:range`` reads over a number and a
percent reader, and the flexible one that replaces it over the set's own number,
percent, and currency readers.

A reader that takes a parameter is built for each value chosen from ICU:

* ``currencies`` -- each read locale's own currency (en_IN's INR) and each currency
  ``locale`` writes with a symbol of its own rather than its ISO code (en_US's "¥");
  pass ISO codes to choose others.
* ``units`` -- the units CLDR's unit preferences give the world and the regions of
  the read locales, every unit of ICU's ``duration`` and ``digital`` types ("3
  weeks", "2 GB"), and the composed units icukit's curated table chooses; and the
  preferences' mixed units ("foot-and-inch") with each run of CLDR's default
  duration order ("hour-and-minute-and-second"). A unit no read region prefers is
  not read (German text's "°F", "900 MHz" anywhere). Pass ICU unit identifiers,
  single or mixed, to choose others; the full ICU inventory reads more at more
  cost.

``locales`` chooses the other locales of the language the language-wide readers
read, and the locales the currencies and units are chosen from (every one by
default). ``guarded`` adds the readers of the readings the default readers refuse on
purpose (:data:`GUARDED_FAMILIES`), each under its own type. A member that cannot be
built is left out; :func:`flexible_detectors_report` names it and why.

Construction is cached process-wide in a bounded memo keyed by every option; equal
calls return the same frozen set. Calling :func:`icukit.cache.configure` with
``enabled=False`` or setting ``ICUKIT_CACHE=0`` bypasses the gang memo; use
:func:`clear_detector_caches` to clear it. A ``detect`` costs a small multiple of
the generated set's, since the currency and measure readers share the numbers they
read within a text. The shared readings are kept for the 16 texts read last (about
110 bytes per character each for en_US).

### `flexible_detectors_report(locale: 'str', *, locales: 'Iterable[str] | None' = None, currencies: 'Iterable[str] | None' = None, units: 'Iterable[str] | None' = None, guarded: 'bool' = False, material: 'Iterable[LocaleMaterial]' = ()) -> 'GenerationReport'`

The flexible readers for ``locale``, and every spec that could not be built.

See :func:`flexible_detectors`. The frozen report is memoized by the complete,
normalized request. Calling :func:`icukit.cache.configure` with ``enabled=False``
or setting ``ICUKIT_CACHE=0`` bypasses the gang memo;
:func:`clear_detector_caches` clears it explicitly.

### `generated_detectors(locale: 'str', families: 'Iterable[Family]' = (Family(name='abbreviation'), Family(name='date-time-skeleton'), Family(name='date-interval'), Family(name='compact-number'), Family(name='relative-date'), Family(name='scientific-number'), Family(name='spellout-number'), Family(name='number-range')), *, material: 'Iterable[LocaleMaterial]' = ()) -> 'DetectorSet'`

Derive all invertible detectors introspectively registered for ``locale``.

Repeated equal calls return the detector set from the process-wide bounded gang
memo. Calling :func:`icukit.cache.configure` with ``enabled=False`` or setting
``ICUKIT_CACHE=0`` bypasses that memo, and :func:`clear_detector_caches` clears
every detector-construction cache.

### `generated_detectors_report(locale: 'str', families: 'Iterable[Family]' = (Family(name='abbreviation'), Family(name='date-time-skeleton'), Family(name='date-interval'), Family(name='compact-number'), Family(name='relative-date'), Family(name='scientific-number'), Family(name='spellout-number'), Family(name='number-range')), *, material: 'Iterable[LocaleMaterial]' = ()) -> 'GenerationReport'`

Derive detectors for ``locale`` and report specs that could not be inverted.

The immutable report is memoized in-process by the complete request, including
family and material-object identity, so a family must enumerate and build the same
readers each time it is given the same locale. Calling
:func:`icukit.cache.configure` with ``enabled=False`` or setting
``ICUKIT_CACHE=0`` bypasses this gang memo; :func:`clear_detector_caches` clears it
explicitly.

### `range_detectors(locale: 'str', detectors: 'DetectorSet', *, locales: 'Iterable[str] | None' = None) -> 'DetectorSet'`

The number range readers over the amount readers ``detectors`` holds.

A range's endpoints follow the set: one reader over its number, percent, and
currency readers, strict or flexible (``number:range``), and one over its measure
readers (``measure:range``), each also reading the approximately form. So a set that
reads a currency or a unit reads its ranges ("$3–5", "10–15 kg"), and one that does
not, does not. Add them with
``detectors.with_(*range_detectors(locale, detectors).detectors)``: each replaces the
set's own reader of its type, a generated set's ``number:range`` among them.

### `reader_set(locale: 'str', *, guarded: 'bool' = False, flexible: 'bool' = False, locales: 'Iterable[str] | None' = None, currencies: 'Iterable[str]' = (), units: 'Iterable[str]' = (), skeletons: 'Iterable[str] | None' = None, material: 'Iterable[LocaleMaterial]' = ()) -> 'DetectorSet'`

Build the detector gang selected by the corresponding ``ik detect`` options.

``reader_set(locale, flexible=True)`` is the default generated-plus-flexible gang.
The order is part of the public result and matches the command-line detector set.

## icukit.exceptions

Corpus exception rules for ICU text segmentation.

The persisted objects in this module are deliberately JSON-shaped ``TypedDict``
records.  Loading validates and compiles all records transactionally; applications
only ever see the immutable compiled inventory.

### Constants and type aliases

#### `Condition` (type alias)

`UnicodeSetCondition | NamedListCondition`

### class `ExceptionContextBounds`

Maximum code-point reach of a loaded exception inventory.

``right`` is measured after a match's end, and ``left`` before its start.
``max_surface_length`` records the longest declared surface, while
``right_from_match_start`` combines each rule's match extent and right
context. Collation match extent is unbounded because collation-equivalent
text may contain arbitrarily many ignorable code points. ``None`` means
that direction is unbounded, while zero means that no rule inspects beyond
the match. Direction-specific rule IDs identify every source of unbounded
reach.

At runtime, mandatory breaks may provide a nearer dynamic anchor: an
incremental caller's usable horizon in each direction is the minimum of
this static reach and the distance to the next mandatory boundary. This
object remains inventory-only because that dynamic distance depends on the
text being segmented.

#### `ExceptionContextBounds(left: 'int | None', right: 'int | None', max_surface_length: 'int', right_from_match_start: 'int | None', unbounded_rule_ids: 'tuple[str, ...]' = (), unbounded_left_rule_ids: 'tuple[str, ...]' = (), unbounded_right_rule_ids: 'tuple[str, ...]' = ()) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `ExceptionInventory`

dict() -> new empty dictionary
dict(mapping) -> new dictionary initialized from a mapping object's
    (key, value) pairs
dict(iterable) -> new dictionary initialized as if via:
    d = {}
    for k, v in iterable:
        d[k] = v
dict(**kwargs) -> new dictionary initialized with the name=value pairs
    in the keyword argument list.  For example:  dict(one=1, two=2)

### class `ExceptionPolicy`

Choose how matching exception rules affect candidate boundaries.

The defaults preserve each rule's authored effect at its declared level,
require every condition, reject absent context, and combine compatible
overlaps. ``retype_as`` is used by the explicit ``"retype"`` disposition.

``missing_context`` governs an edge of the *complete* text: a condition that
runs off the start or end of the string with no character left to inspect.
The text passed to :meth:`LoadedExceptionInventory.break_spans` is always
taken to be complete. A caller feeding text incrementally must not rely on
this dimension to describe a buffer that is merely unfinished, because a
condition reaching past the end of a partial buffer is undetermined rather
than absent, and either value would decide it prematurely. Such a caller
should withhold a tail of the buffer and break only the prefix whose context
has already arrived.

``mandatory_breaks`` controls whitespace-skipping conditions. ``"barrier"``
prevents them from inspecting or crossing an ICU mandatory line-break
sequence, while ``"cross"`` preserves the former cross-line behavior. A
barrier-blocked condition is false regardless of ``missing_context``; a rule
at a line start therefore behaves differently from the same rule at the true
start of the complete text.

#### `ExceptionPolicy(disposition: "Literal['rule', 'suppress', 'retype', 'mark']" = 'rule', conditions: "Literal['all', 'any']" = 'all', missing_context: "Literal['fail', 'match']" = 'fail', mandatory_breaks: "Literal['barrier', 'cross']" = 'barrier', overlap: "Literal['combine', 'first', 'error']" = 'combine', retype_as: 'str' = 'exception:match') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `ExceptionRule`

dict() -> new empty dictionary
dict(mapping) -> new dictionary initialized from a mapping object's
    (key, value) pairs
dict(iterable) -> new dictionary initialized as if via:
    d = {}
    for k, v in iterable:
        d[k] = v
dict(**kwargs) -> new dictionary initialized with the name=value pairs
    in the keyword argument list.  For example:  dict(one=1, two=2)

### class `LoadedExceptionInventory`

An immutable, validated exception inventory.

#### `LoadedExceptionInventory(corpus: 'str', named_lists: 'dict[str, tuple[str, ...]]', _rules: 'tuple[_CompiledRule, ...]') -> None`

Initialize self.  See help(type(self)) for accurate signature.

#### `apply(text: 'str', level: 'Level', locale: 'str' = 'en_US', *, policy: 'ExceptionPolicy | None' = None) -> 'list[BreakSpan]'`

Alias for :meth:`break_spans`.

#### `break_spans(text: 'str', level: 'Level', locale: 'str' = 'en_US', *, policy: 'ExceptionPolicy | None' = None) -> 'list[BreakSpan]'`

Segment ``text`` and apply matching rules under ``policy``.

### class `NamedListCondition`

dict() -> new empty dictionary
dict(mapping) -> new dictionary initialized from a mapping object's
    (key, value) pairs
dict(iterable) -> new dictionary initialized as if via:
    d = {}
    for k, v in iterable:
        d[k] = v
dict(**kwargs) -> new dictionary initialized with the name=value pairs
    in the keyword argument list.  For example:  dict(one=1, two=2)

### class `Provenance`

dict() -> new empty dictionary
dict(mapping) -> new dictionary initialized from a mapping object's
    (key, value) pairs
dict(iterable) -> new dictionary initialized as if via:
    d = {}
    for k, v in iterable:
        d[k] = v
dict(**kwargs) -> new dictionary initialized with the name=value pairs
    in the keyword argument list.  For example:  dict(one=1, two=2)

### class `SkipSpec`

dict() -> new empty dictionary
dict(mapping) -> new dictionary initialized from a mapping object's
    (key, value) pairs
dict(iterable) -> new dictionary initialized as if via:
    d = {}
    for k, v in iterable:
        d[k] = v
dict(**kwargs) -> new dictionary initialized with the name=value pairs
    in the keyword argument list.  For example:  dict(one=1, two=2)

### class `UnicodeSetCondition`

dict() -> new empty dictionary
dict(mapping) -> new dictionary initialized from a mapping object's
    (key, value) pairs
dict(iterable) -> new dictionary initialized as if via:
    d = {}
    for k, v in iterable:
        d[k] = v
dict(**kwargs) -> new dictionary initialized with the name=value pairs
    in the keyword argument list.  For example:  dict(one=1, two=2)

### class `Witnesses`

dict() -> new empty dictionary
dict(mapping) -> new dictionary initialized from a mapping object's
    (key, value) pairs
dict(iterable) -> new dictionary initialized as if via:
    d = {}
    for k, v in iterable:
        d[k] = v
dict(**kwargs) -> new dictionary initialized with the name=value pairs
    in the keyword argument list.  For example:  dict(one=1, two=2)

### `compose_inventories(layers: 'Sequence[ExceptionInventory]', *, disable: 'Sequence[str]' = (), require_finite_context: 'bool' = False) -> 'LoadedExceptionInventory'`

Compose ordered inventories, then validate and atomically publish the result.

Later layers replace rules with the same ID and named lists with the same name.
Disabled IDs are removed after composition. The composed corpus label joins layer
corpus names with ``" + "``. Loading is opt-in and does not alter default breakers.
Set ``require_finite_context`` to refuse rules with unbounded context reach.

### `example_exception_inventory() -> 'ExceptionInventory'`

Return electable example rules; they are never loaded or applied by default.

### `load_exception_inventory(inventory: 'ExceptionInventory', *, require_finite_context: 'bool' = False) -> 'LoadedExceptionInventory'`

Validate, compile, witness-test, and atomically publish an inventory.

Set ``require_finite_context`` to refuse rules with unbounded context reach.

### `merge_retypes(text: 'str', base_spans: 'list[BreakSpan]', detections: 'list[Detection]') -> 'list[BreakSpan]'`

Retype owning spans by containment; never split, replace, or coalesce them.

## icukit.formatters

Output formatters for rendering structured data.

This module provides formatters for rendering data as JSON, TSV, or the
human-readable output used by icukit's command-line interface.

Usage:
    data = [{"id": "foo", "value": 1}, {"id": "bar", "value": 2}]

    # TSV output (default)
    print(format_tsv(data))

    # JSON output
    print(format_json(data))

    # Auto-format based on args
    print(format_output(data, as_json=args.json))

### `flatten_extended(data: 'Sequence[dict[str, Any]]', extended_columns: 'list[str]') -> 'list[dict[str, Any]]'`

Copy rows and promote selected ``extended`` values to top-level keys.

Args:
    data: Rows to copy. Each row may contain an ``extended`` mapping.
    extended_columns: Keys to read from each row's ``extended`` mapping. A missing
        key is promoted with the value ``None``. Nested dictionaries are rendered
        as comma-separated ``key=value`` pairs in their iteration order.

Returns:
    New shallow copies with the requested keys promoted. Input rows are not
    mutated, and the ``extended`` key is retained in each copied row.

### `format_json(data: 'Any', indent: 'int | None' = 2) -> 'str'`

Serialize data as JSON text.

Args:
    data: Data to serialize. Values unsupported by JSON are converted to strings.
    indent: Number of spaces to use for each indentation level, or ``None`` for
        compact output.

Returns:
    JSON text containing non-ASCII characters without ASCII escaping.

### `format_output(data: 'Any', as_json: 'bool' = False, columns: 'list[str] | None' = None, headers: 'bool' = True) -> 'str'`

Render data as JSON or as icukit's human-readable command output.

Args:
    data: Data to render. In non-JSON mode, non-empty sequences of mappings become
        TSV, non-empty sequences of strings become newline-separated text, and
        mappings become sorted labeled sections, with a newline before each label.
        Other values fall back to JSON.
    as_json: Render as JSON. The shape of *data* is preserved exactly: a sequence
        renders as a JSON array at every length, including one and zero, so a
        consumer never has to branch on cardinality. Use :func:`print_record` for
        a command that yields exactly one thing by nature.
    columns: Columns to include in TSV output, in order.
    headers: Include a TSV header when more than one column is rendered.

Returns:
    Formatted text without a trailing newline.

### `format_simple_list(data: 'Sequence[Any]') -> 'str'`

Render a sequence as newline-separated text.

Args:
    data: Items to render. Each item is converted to a string.

Returns:
    Newline-separated text without a trailing newline, or an empty string when
    *data* is empty.

### `format_tsv(data: 'Sequence[dict[str, Any]]', columns: 'list[str] | None' = None, headers: 'bool' = True) -> 'str'`

Render a sequence of mappings as tab-separated text.

Args:
    data: Rows to render. Missing columns and empty values are displayed as ``-``.
    columns: Columns to include, in order. By default, use the first row's keys.
    headers: Include a header when rendering more than one column. Single-column
        output never includes a header.

Returns:
    TSV text without a trailing newline, or an empty string when *data* is empty.

### `print_output(data: 'Any', as_json: 'bool' = False, columns: 'list[str] | None' = None, headers: 'bool' = True, file: 'TextIO | None' = None, extended_columns: 'list[str] | None' = None) -> 'None'`

Render data and write it followed by a newline.

Args:
    data: Data accepted by :func:`format_output`.
    as_json: Render as JSON.
    columns: Base columns to include in TSV output, in order.
    headers: Include a TSV header when more than one column is rendered.
    file: Text stream to write to. Defaults to standard output.
    extended_columns: Keys from each row's ``extended`` mapping to append as TSV
        columns. Nested mapping values are rendered as comma-separated ``key=value``
        pairs. This transformation is not applied to JSON output.

### `print_record(record: 'dict[str, Any]', as_json: 'bool' = False, columns: 'list[str] | None' = None, headers: 'bool' = True, file: 'TextIO | None' = None, extended_columns: 'list[str] | None' = None) -> 'None'`

Render one record and write it followed by a newline.

Use this where a command yields exactly one thing by nature — one unit's
information, one parse result, one comparison — rather than a collection that
happens to hold a single item. A collection belongs in :func:`print_output`,
which renders it as a JSON array at every length.

Args:
    record: The single record to render.
    as_json: Render as a bare JSON object rather than a one-row table.
    columns: Columns to include in TSV output, in order.
    headers: Include a TSV header when more than one column is rendered.
    file: Text stream to write to. Defaults to standard output.
    extended_columns: Keys from the record's ``extended`` mapping to append as TSV
        columns. This transformation is not applied to JSON output.

## icukit.icu_abbreviations

Every abbreviation ICU writes for a language, with the expansions ICU gives it.

Generated from ICU at call time, not stored: for each kind of short form ICU formats,
the short and narrow surfaces, and the long forms ICU writes for the same thing. A
consumer that speaks text (a TTS front end) can expand what it reads from here
without keeping its own list.

Kinds:

    * ``unit``: unit symbols ("km") with the unit's wide names ("kilometers");
    * ``per-unit``: a rate's per form ("/km²") with its wide form ("per square
      kilometer");
    * ``month`` and ``weekday``: abbreviated and narrow names ("Sep") with the wide
      name ("September");
    * ``era``: abbreviated names and their variants ("BC", "BCE") with the wide names
      ("Before Christ", "Before Common Era");
    * ``day-period``: "AM", "PM", with a wide form where the language has one;
    * ``time-zone``: zone abbreviations ("EST", "ET") with the long names ("Eastern
      Standard Time", "Eastern Time");
    * ``currency``: symbols and ISO codes ("$", "USD") with the currency's names ("US
      dollars");
    * ``compact``: compact-number suffixes ("K") with the long ones ("thousand");
    * ``relative-unit``: relative-time unit abbreviations ("hr.", "mo") with the long
      ones ("hours", "months");
    * ``territory``: region codes ("US", "EU", "UN") and CLDR's short territory names
      ("UK") with the territory's names ("United States", "European Union");
    * ``symbol``: symbols that are not emoji ("&", "±", "→", "©") with CLDR's names for
      them in the language, its text-to-speech name first ("ampersand"), then its
      keywords ("and", "et"). ICU names only currency and unit symbols and % ‰ ‱ per
      locale, and those stay listed under their own kinds as well; these come from a
      snapshot of CLDR's annotations (see :mod:`icukit.cldr_symbols`), so their
      ``width`` is "cldr" and their ``source`` "cldr" ("cldr-<version>", naming the
      snapshot's CLDR, when ICU's own CLDR is another).

``key`` names what the surface stands for in ICU's terms: a unit identifier, a month
or weekday number (ICU's, Sunday 1), an era index, a zone's long name (one
abbreviation serves many zone IDs), an ISO 4217 code, a power of ten, a relative
unit, a region code, or a symbol's code points ("U+0026"). ``expansions`` are ICU's
long forms, singular and
plural where they differ, in the order ICU gave them; empty where ICU writes no longer
form (English "AM"). The locales read are the locale's language's, or the ones a
caller chooses, as for the readers.

Example:
    >>> from icukit import icu_abbreviations
    >>> [a.expansions for a in icu_abbreviations("en_US", kinds=["unit"]) if a.surface == "km"]
    [('kilometer', 'kilometers')]

### Constants and type aliases

#### `ABBREVIATION_KINDS` (constant)

`('unit', 'per-unit', 'month', 'weekday', 'era', 'day-period', 'time-zone', 'currency', 'compact', 'relative-unit', 'territory', 'symbol')`

### class `IcuAbbreviation`

One short form ICU writes, with the long forms ICU gives the same thing.

#### `IcuAbbreviation(surface: 'str', kind: 'str', key: 'str', width: 'str', expansions: 'tuple[str, ...]', source: 'str' = 'icu') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `icu_abbreviations(locale: 'str', *, locales: 'Iterable[str] | None' = None, kinds: 'Iterable[str] | None' = None) -> 'tuple[IcuAbbreviation, ...]'`

The short forms ICU writes in ``locale``'s language, with their expansions.

``locales`` chooses the other locales of the language read, as for the readers
(``None``: all of them); ``kinds`` narrows the kinds (see ``ABBREVIATION_KINDS``).
A kind's rows are generated once per locale and choice, then cached.

## icukit.idna

Internationalized Domain Name (IDNA) encoding and decoding.

Converts between Unicode domain names and ASCII-compatible encoding
(Punycode), following the IDNA standard.

Example:
    >>> from icukit import idna_encode, idna_decode
    >>> idna_encode("münchen.de")
    'xn--mnchen-3ya.de'
    >>> idna_decode("xn--mnchen-3ya.de")
    'münchen.de'

### class `IDNAConverter`

Reusable IDNA converter for batch operations.

Example:
    >>> converter = IDNAConverter()
    >>> converter.encode("münchen.de")
    'xn--mnchen-3ya.de'
    >>> converter.decode("xn--mnchen-3ya.de")
    'münchen.de'

#### `IDNAConverter()`

Create a new IDNA converter.

#### `decode(domain: 'str') -> 'str'`

Decode ASCII domain to Unicode.

#### `decode_label(label: 'str') -> 'str'`

Decode single label to Unicode.

#### `encode(domain: 'str') -> 'str'`

Encode Unicode domain to ASCII.

#### `encode_label(label: 'str') -> 'str'`

Encode single label to ASCII.

### `idna_decode(domain: 'str') -> 'str'`

Decode an ASCII (Punycode) domain name to Unicode.

Converts ASCII-encoded domain names back to their Unicode representation.

Args:
    domain: ASCII-encoded domain name (e.g., "xn--mnchen-3ya.de").

Returns:
    Unicode domain name (e.g., "münchen.de").

Raises:
    IDNAError: If decoding fails.

Example:
    >>> idna_decode("xn--mnchen-3ya.de")
    'münchen.de'
    >>> idna_decode("xn--r8jz45g.jp")
    '例え.jp'

### `idna_decode_label(label: 'str') -> 'str'`

Decode a single ASCII domain label to Unicode.

Args:
    label: ASCII-encoded label (e.g., "xn--mnchen-3ya").

Returns:
    Unicode label (e.g., "münchen").

Example:
    >>> idna_decode_label("xn--mnchen-3ya")
    'münchen'

### `idna_encode(domain: 'str') -> 'str'`

Encode a Unicode domain name to ASCII (Punycode).

Converts internationalized domain names to ASCII-compatible encoding
that can be used in DNS lookups and URLs.

Args:
    domain: Unicode domain name (e.g., "münchen.de", "例え.jp").

Returns:
    ASCII-encoded domain name (e.g., "xn--mnchen-3ya.de").

Raises:
    IDNAError: If encoding fails.

Example:
    >>> idna_encode("münchen.de")
    'xn--mnchen-3ya.de'
    >>> idna_encode("例え.jp")
    'xn--r8jz45g.jp'

### `idna_encode_label(label: 'str') -> 'str'`

Encode a single domain label to ASCII.

A label is a single component of a domain name (between dots).

Args:
    label: Unicode label (e.g., "münchen").

Returns:
    ASCII-encoded label (e.g., "xn--mnchen-3ya").

Example:
    >>> idna_encode_label("münchen")
    'xn--mnchen-3ya'

### `is_ascii_domain(domain: 'str') -> 'bool'`

Check if a domain name is already ASCII-only.

Args:
    domain: Domain name to check.

Returns:
    True if the domain contains only ASCII characters.

Example:
    >>> is_ascii_domain("example.com")
    True
    >>> is_ascii_domain("münchen.de")
    False

## icukit.list_format

Locale-aware list formatting.

ICU's ListFormatter formats lists of items with appropriate conjunctions
and separators for each locale.

Key Features:
    * Locale-aware conjunctions ("and", "oder", "と", etc.)
    * Multiple styles: and, or, unit
    * Handles two-item special case
    * Oxford comma where appropriate

Example:
    >>> from icukit import format_list
    >>> format_list(['apples', 'oranges', 'bananas'], 'en')
    'apples, oranges, and bananas'
    >>> format_list(['Äpfel', 'Orangen', 'Bananen'], 'de')
    'Äpfel, Orangen und Bananen'

### Constants and type aliases

#### `STYLE_AND` (constant)

`'and'`

List format styles

#### `STYLE_OR` (constant)

`'or'`

#### `STYLE_UNIT` (constant)

`'unit'`

### class `ListFormatter`

Locale-aware list formatter.

Formats lists of items with appropriate conjunctions and separators.

Example:
    >>> lf = ListFormatter('en', style='and')
    >>> lf.format(['apples', 'oranges', 'bananas'])
    'apples, oranges, and bananas'

#### `ListFormatter(locale: 'str' = 'en_US', style: 'str' = 'and')`

Initialize a ListFormatter.

Args:
    locale: Locale for formatting rules.
    style: List style - 'and', 'or', or 'unit'.

Raises:
    ListFormatError: If locale or style is invalid.

#### `format(items: 'list[str]') -> 'str'`

Format a list of items.

Args:
    items: List of strings to format.

Returns:
    Formatted string with locale-appropriate conjunctions.

Example:
    >>> lf = ListFormatter('en')
    >>> lf.format(['a', 'b', 'c'])
    'a, b, and c'

### `format_list(items: 'list[str]', locale: 'str' = 'en_US', style: 'str' = 'and') -> 'str'`

Format a list of items with locale-appropriate conjunctions.

Args:
    items: List of strings to format.
    locale: Locale for formatting rules.
    style: List style - 'and', 'or', or 'unit'.

Returns:
    Formatted string.

Example:
    >>> format_list(['apples', 'oranges', 'bananas'], 'en')
    'apples, oranges, and bananas'

    >>> format_list(['apples', 'oranges', 'bananas'], 'en', style='or')
    'apples, oranges, or bananas'

    >>> format_list(['Äpfel', 'Orangen'], 'de')
    'Äpfel und Orangen'

## icukit.locale

Locale parsing and information.

Parse, validate, and query locale identifiers (language + region + script).
Integrates with other icukit domain objects (region, script, calendar, timezone).

Key Features:
    * Parse locale strings (BCP 47 and ICU format)
    * Get display names for languages, regions, scripts
    * List available locales
    * Add likely subtags (e.g., 'zh' -> 'zh_Hans_CN')
    * Query locale components

Locale Format:
    Locales follow the pattern: language[_Script][_REGION][@keywords]

    Examples:
        * 'en' - English
        * 'en_US' - English (United States)
        * 'zh_Hans' - Chinese (Simplified)
        * 'zh_Hans_CN' - Chinese (Simplified, China)
        * 'sr_Latn_RS' - Serbian (Latin, Serbia)
        * 'en_US@calendar=hebrew' - English (US) with Hebrew calendar

Example:
    Parse and query locales::

        >>> from icukit import parse_locale, get_locale_info, list_locales
        >>>
        >>> # Parse a locale
        >>> info = parse_locale('el_GR')
        >>> info['language']
        'el'
        >>> info['region']
        'GR'
        >>>
        >>> # Get display names
        >>> info = get_locale_info('ja_JP')
        >>> info['display_name']
        'Japanese (Japan)'
        >>>
        >>> # Add likely subtags
        >>> from icukit import add_likely_subtags
        >>> add_likely_subtags('zh')
        'zh_Hans_CN'

### Constants and type aliases

#### `COMPACT_LONG` (constant)

`'LONG'`

#### `COMPACT_SHORT` (constant)

`'SHORT'`

Compact style constants

#### `EXEMPLAR_AUXILIARY` (constant)

`'auxiliary'`

#### `EXEMPLAR_INDEX` (constant)

`'index'`

#### `EXEMPLAR_PUNCTUATION` (constant)

`'punctuation'`

#### `EXEMPLAR_STANDARD` (constant)

`'standard'`

Exemplar set type constants

### `add_likely_subtags(locale_str: 'str') -> 'str'`

Add likely subtags to a locale identifier.

Expands a minimal locale to include likely script and region.

Args:
    locale_str: Minimal locale string (e.g., 'zh', 'sr').

Returns:
    Expanded locale string.

Example:
    >>> add_likely_subtags('zh')
    'zh_Hans_CN'
    >>> add_likely_subtags('sr')
    'sr_Cyrl_RS'

### `canonicalize_locale(locale_str: 'str') -> 'str'`

Canonicalize a locale identifier.

Converts to canonical form (e.g., deprecated codes to current ones).

Args:
    locale_str: Locale string.

Returns:
    Canonical locale string.

Example:
    >>> canonicalize_locale('iw')  # deprecated Hebrew code
    'he'

### `format_compact(value: 'int | float', locale_str: 'str' = 'en_US', style: 'str' = 'SHORT') -> 'str'`

Format a number in compact form with locale-appropriate abbreviations.

Args:
    value: Number to format.
    locale_str: Locale for formatting.
    style: COMPACT_SHORT ("1.2M") or COMPACT_LONG ("1.2 million").

Returns:
    Compact formatted string.

Example:
    >>> format_compact(1234567, 'en_US')
    '1.2M'
    >>> format_compact(1234567, 'de_DE')
    '1,2 Mio.'
    >>> format_compact(1234567, 'en_US', COMPACT_LONG)
    '1.2 million'

### `format_currency(value: 'float', locale_str: 'str' = 'en_US', currency: 'str' = None) -> 'str'`

Format a value as currency.

Args:
    value: Amount to format.
    locale_str: Locale for formatting.
    currency: Optional currency code (e.g., 'EUR'). If None, uses locale default.

Returns:
    Formatted currency string.

Example:
    >>> format_currency(1234.56, 'en_US')
    '$1,234.56'
    >>> format_currency(1234.56, 'de_DE')
    '1.234,56 €'
    >>> format_currency(1234.56, 'en_US', 'EUR')
    '€1,234.56'

### `format_number(value: 'float', locale_str: 'str' = 'en_US') -> 'str'`

Format a number according to locale conventions.

Args:
    value: Number to format.
    locale_str: Locale for formatting.

Returns:
    Formatted number string.

Example:
    >>> format_number(1234567.89, 'en_US')
    '1,234,567.89'
    >>> format_number(1234567.89, 'de_DE')
    '1.234.567,89'

### `format_ordinal(value: 'int', locale_str: 'str' = 'en_US') -> 'str'`

Format a number as an ordinal.

Args:
    value: Integer to format.
    locale_str: Locale for formatting.

Returns:
    Ordinal string.

Example:
    >>> format_ordinal(1, 'en_US')
    '1st'
    >>> format_ordinal(2, 'en_US')
    '2nd'
    >>> format_ordinal(1, 'de_DE')
    '1.'

### `format_percent(value: 'float', locale_str: 'str' = 'en_US') -> 'str'`

Format a value as a percentage.

Args:
    value: Decimal value (0.15 = 15%).
    locale_str: Locale for formatting.

Returns:
    Formatted percentage string.

Example:
    >>> format_percent(0.15, 'en_US')
    '15%'
    >>> format_percent(0.15, 'de_DE')
    '15 %'

### `format_scientific(value: 'float', locale_str: 'str' = 'en_US') -> 'str'`

Format a value in scientific notation.

Args:
    value: Number to format.
    locale_str: Locale for formatting.

Returns:
    Formatted scientific notation string.

Example:
    >>> format_scientific(1234567.89, 'en_US')
    '1.234568E6'

### `format_spellout(value: 'int', locale_str: 'str' = 'en_US') -> 'str'`

Spell out a number in words.

Args:
    value: Integer to spell out.
    locale_str: Locale for spelling.

Returns:
    Number spelled out in words.

Example:
    >>> format_spellout(42, 'en_US')
    'forty-two'
    >>> format_spellout(42, 'de_DE')
    'zwei­und­vierzig'

### `get_default_locale() -> 'str'`

Get the system default locale.

Returns:
    Default locale identifier.

Example:
    >>> get_default_locale()
    'en_US'  # or whatever the system default is

### `get_display_name(locale_str: 'str', display_locale: 'str' = 'en') -> 'str'`

Get the display name for a locale.

Args:
    locale_str: Locale to get display name for.
    display_locale: Locale for the display name.

Returns:
    Display name string.

Example:
    >>> get_display_name('el_GR')
    'Greek (Greece)'
    >>> get_display_name('el_GR', 'el')
    'Ελληνικά (Ελλάδα)'

### `get_exemplar_characters(locale_str: 'str' = 'en_US', exemplar_type: 'str' = 'standard') -> 'str'`

Get exemplar characters for a locale.

Exemplar characters are the characters commonly used in a locale's
writing system.

Args:
    locale_str: Locale code (e.g., "en_US", "de_DE", "ja_JP").
    exemplar_type: Type of exemplar set:
        - "standard" - Main characters used in the locale
        - "auxiliary" - Characters for borrowed/foreign words
        - "index" - Characters for alphabetic indexes (A-Z sidebar)
        - "punctuation" - Punctuation characters

Returns:
    String representation of the exemplar character set (ICU UnicodeSet format).

Example:
    >>> get_exemplar_characters("de_DE")
    '[a-zßäöü]'
    >>> get_exemplar_characters("de_DE", "index")
    '[A-Z]'
    >>> get_exemplar_characters("ja_JP", "index")
    '[あかさたなはまやらわ]'

### `get_exemplar_info(locale_str: 'str' = 'en_US') -> 'dict[str, str]'`

Get all exemplar character sets for a locale.

Args:
    locale_str: Locale code.

Returns:
    Dictionary mapping exemplar type to character set string.

Example:
    >>> info = get_exemplar_info("de_DE")
    >>> info["standard"]
    '[a-zßäöü]'
    >>> info["index"]
    '[A-Z]'

### `get_language_display_name(language: 'str', display_locale: 'str' = 'en') -> 'str'`

Get the display name for a language code.

Args:
    language: ISO 639 language code.
    display_locale: Locale for the display name.

Returns:
    Display name string.

Example:
    >>> get_language_display_name('el')
    'Greek'
    >>> get_language_display_name('ja')
    'Japanese'

### `get_locale_attributes(locale_str: 'str', display_locale: 'str' = 'en') -> 'dict[str, Any]'`

Get comprehensive locale attributes.

Returns detailed information including currency, measurement system,
quote delimiters, and more.

Args:
    locale_str: Locale identifier.
    display_locale: Locale for display names.

Returns:
    Dict with comprehensive locale attributes.

Example:
    >>> attrs = get_locale_attributes('en_US')
    >>> attrs['currency']
    'USD'
    >>> attrs['measurement_system']
    'US'
    >>> attrs['quote_start']
    '"'

### `get_locale_extended(locale_str: 'str') -> 'dict[str, Any]'`

Get extended locale attributes.

Args:
    locale_str: Locale string.

Returns:
    Dict with extended attributes (calendar, currency, RTL, index_labels, etc.)

Example:
    >>> ext = get_locale_extended('ja_JP')
    >>> ext['currency']
    'JPY'
    >>> ext['calendar']
    'gregorian'
    >>> ext['index_labels'][:3]
    ['あ', 'か', 'さ']

### `get_locale_info(locale_str: 'str', display_locale: 'str' = 'en', extended: 'bool' = False) -> 'dict[str, Any]'`

Get detailed information about a locale.

Args:
    locale_str: Locale string to get info for.
    display_locale: Locale for display names.
    extended: Include extended attributes (calendar, currency, etc.)

Returns:
    Dict with locale info including display names and scripts.

Example:
    >>> info = get_locale_info('ja_JP')
    >>> info['display_name']
    'Japanese (Japan)'
    >>> info['scripts']
    ['Han', 'Hiragana', 'Katakana']
    >>> info = get_locale_info('ja_JP', extended=True)
    >>> info['extended']['currency']
    'JPY'

### `get_locale_scripts(locale_str: 'str') -> 'list[str]'`

Get the scripts used by a locale.

Derives scripts from the locale's exemplar character set.

Args:
    locale_str: Locale string.

Returns:
    List of script names used by the locale.

Example:
    >>> get_locale_scripts('ja_JP')
    ['Han', 'Hiragana', 'Katakana']
    >>> get_locale_scripts('en_US')
    ['Latin']

### `get_number_symbols(locale_str: 'str' = 'en_US') -> 'dict[str, str]'`

Get number formatting symbols for a locale.

Returns the symbols used for formatting numbers, including decimal
separator, grouping separator, percent sign, and more.

Args:
    locale_str: Locale code (e.g., "en_US", "de_DE", "ar_SA").

Returns:
    Dict with number formatting symbols:
        - decimal: Decimal separator ("." or ",")
        - grouping: Grouping/thousands separator ("," or "." or " ")
        - percent: Percent sign
        - per_mille: Per-mille sign (‰)
        - plus: Plus sign
        - minus: Minus sign
        - exponential: Exponential sign (E)
        - infinity: Infinity symbol (∞)
        - nan: Not-a-number symbol
        - currency: Default currency symbol for locale

Example:
    >>> get_number_symbols("en_US")
    {'decimal': '.', 'grouping': ',', 'percent': '%', ...}
    >>> get_number_symbols("de_DE")
    {'decimal': ',', 'grouping': '.', 'percent': '%', ...}
    >>> get_number_symbols("fr_FR")
    {'decimal': ',', 'grouping': ' ', 'percent': '%', ...}

### `is_valid_locale(locale_str: 'str') -> 'bool'`

Check if a locale string is valid.

Args:
    locale_str: Locale string to validate.

Returns:
    True if valid, False otherwise.

Example:
    >>> is_valid_locale('en_US')
    True
    >>> is_valid_locale('xx_YY')
    False

### `list_exemplar_types() -> 'list[str]'`

List available exemplar character set types.

Returns:
    List of exemplar type names.

Example:
    >>> list_exemplar_types()
    ['standard', 'auxiliary', 'index', 'punctuation']

### `list_languages() -> 'list[str]'`

List all available language codes.

Returns:
    List of ISO 639 language codes sorted alphabetically.

Example:
    >>> langs = list_languages()
    >>> 'en' in langs
    True
    >>> 'el' in langs
    True

### `list_locales() -> 'list[str]'`

List all available locale identifiers.

Returns:
    List of locale identifiers sorted alphabetically.

Example:
    >>> locales = list_locales()
    >>> 'en_US' in locales
    True
    >>> len(locales)
    851

### `list_locales_info(display_locale: 'str' = 'en') -> 'list[dict[str, Any]]'`

List all locales with their info.

Args:
    display_locale: Locale for display names.

Returns:
    List of dicts with locale info.

Example:
    >>> locales = list_locales_info()
    >>> el = next(l for l in locales if l['id'] == 'el_GR')
    >>> el['display_name']
    'Greek (Greece)'

### `minimize_subtags(locale_str: 'str') -> 'str'`

Remove likely subtags from a locale identifier.

Minimizes a locale to the shortest unambiguous form.

Args:
    locale_str: Full locale string.

Returns:
    Minimized locale string.

Example:
    >>> minimize_subtags('zh_Hans_CN')
    'zh'
    >>> minimize_subtags('en_Latn_US')
    'en'

### `parse_locale(locale_str: 'str') -> 'dict[str, Any]'`

Parse a locale string into components.

Args:
    locale_str: Locale string (e.g., 'en_US', 'zh-Hans-CN', 'sr_Latn_RS').

Returns:
    Dict with parsed components.

Example:
    >>> info = parse_locale('zh_Hans_CN')
    >>> info['language']
    'zh'
    >>> info['script']
    'Hans'
    >>> info['region']
    'CN'

## icukit.material

Load witness-checked locale material supplied by an application at runtime.

### Constants and type aliases

#### `LABEL_KEYS` (constant)

`frozenset({'class', 'end', 'scheme', 'start', 'text'})`

#### `REQUIRED_WITNESS_KEYS` (constant)

`frozenset({'id', 'locale', 'text'})`

#### `VALUE_KEYS` (constant)

`frozenset({'end', 'start', 'text', 'type', 'value'})`

#### `WITNESS_KEYS` (constant)

`frozenset({'id', 'labels', 'locale', 'text', 'text_sha256', 'x-icukit'})`

### class `ClassExtension`

One namespaced, additive character class.

#### `ClassExtension(name: 'str', unicode_set: 'str | None' = None, members: 'tuple[str, ...]' = ()) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `LocaleMaterial`

Immutable, validated locale material identified by its content digest.

Reader material uses ``rules`` and ``rulesets``. Character material uses
``id``, ``status``, ``classes``, and ``shape_refinements``. The unused
fields are empty so all kinds pass through one sealed loader type.

#### `LocaleMaterial(kind: 'str', locale: 'str', digest: 'str', rules: 'str', rulesets: 'tuple[str, ...]', provenance: 'Mapping[str, str]', id: 'str | None' = None, status: 'str | None' = None, classes: 'tuple[ClassExtension, ...]' = (), shape_refinements: 'tuple[ShapeRefinement, ...]' = ()) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `MaterialLoadError`

Every refusal found while transactionally loading locale material.

#### `MaterialLoadError(refusals: 'list[MaterialRefusal] | tuple[MaterialRefusal, ...]') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

### class `MaterialRefusal`

One reason a locale material file was refused.

### class `ShapeRefinement`

A new shape symbol selected by a base or extension class.

#### `ShapeRefinement(name: 'str', class_name: 'str', symbol: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `load_locale_material(material: 'Mapping[str, object] | str | os.PathLike[str]', /) -> 'LocaleMaterial'`

Parse, validate, witness-check, and atomically return locale material.

## icukit.measure

Locale-aware unit measurement formatting.

ICU's MeasureFormat formats measurements with proper unit names and
locale-specific conventions.

Unit Types:
    length      - meter, kilometer, mile, foot, inch, yard, etc.
    mass        - gram, kilogram, pound, ounce, etc.
    temperature - celsius, fahrenheit, kelvin
    speed       - kilometer-per-hour, mile-per-hour, meter-per-second
    volume      - liter, milliliter, gallon, cup, tablespoon
    area        - square-meter, square-kilometer, acre, hectare
    duration    - second, minute, hour, day, week, month, year
    pressure    - hectopascal, millibar, inch-ofhg
    energy      - joule, kilocalorie, kilojoule
    power       - watt, kilowatt, horsepower
    digital     - byte, kilobyte, megabyte, gigabyte, terabyte

Width Styles:
    WIDE   - "5 kilometers" (full unit names)
    SHORT  - "5 km" (abbreviated)
    NARROW - "5km" (minimal, no space)

Example:
    >>> from icukit import MeasureFormatter
    >>>
    >>> fmt = MeasureFormatter("en_US")
    >>> fmt.format(5.5, "kilometer")
    '5.5 kilometers'
    >>> fmt.format(100, "fahrenheit", width="SHORT")
    '100°F'
    >>>
    >>> fmt_de = MeasureFormatter("de_DE")
    >>> fmt_de.format(5.5, "kilometer")
    '5,5 Kilometer'

### Constants and type aliases

#### `WIDTH_NARROW` (constant)

`'NARROW'`

#### `WIDTH_SHORT` (constant)

`'SHORT'`

#### `WIDTH_WIDE` (constant)

`'WIDE'`

Width constants

### class `MeasureFormatter`

Locale-aware measurement formatter.

Example:
    >>> fmt = MeasureFormatter("en_US")
    >>> fmt.format(5.5, "kilometer")
    '5.5 kilometers'
    >>> fmt.format(100, "fahrenheit", width="SHORT")
    '100°F'

#### `MeasureFormatter(locale: 'str' = 'en_US', width: 'str' = 'WIDE')`

Create a MeasureFormatter.

Args:
    locale: Locale code (e.g., "en_US", "de_DE")
    width: Default width style (WIDE, SHORT, NARROW)

#### `convert(value: 'float | int', from_unit: 'str', to_unit: 'str') -> 'float'`

Convert a value using a limited set of explicit conversion factors.

This helper is not reflective or ICU-driven. PyICU does not expose ICU's
general unit converter, so only the pairs listed by this implementation are
supported. Unit compatibility reported by :func:`can_convert` does not imply
that this helper can convert a particular pair.

Args:
    value: Numeric value to convert
    from_unit: Source unit or abbreviation (e.g., "kilometer", "km")
    to_unit: Target unit or abbreviation (e.g., "mile", "mi")

Returns:
    Converted value

Example:
    >>> fmt.convert(10, "kilometer", "mile")
    6.21371...
    >>> fmt.convert(10, "km", "mi")  # abbreviations work too
    6.21371...
    >>> fmt.convert(100, "celsius", "fahrenheit")
    212.0

#### `convert_and_format(value: 'float | int', from_unit: 'str', to_unit: 'str', width: 'str | None' = None) -> 'str'`

Convert with the limited explicit factors and format the result.

Args:
    value: Numeric value to convert
    from_unit: Source unit
    to_unit: Target unit
    width: Width style for formatting

Returns:
    Formatted converted measurement

Example:
    >>> fmt.convert_and_format(10, "kilometer", "mile")
    '6.21371 miles'

#### `format(value: 'float | int', unit: 'str', width: 'str | None' = None) -> 'str'`

Format a measurement.

Args:
    value: Numeric value
    unit: Unit name or abbreviation (e.g., "kilometer", "km", "fahrenheit", "F")
    width: Width style (WIDE, SHORT, NARROW), overrides default

Returns:
    Formatted measurement string

Example:
    >>> fmt.format(5.5, "kilometer")
    '5.5 kilometers'
    >>> fmt.format(5.5, "km")  # abbreviation works too
    '5.5 kilometers'
    >>> fmt.format(100, "fahrenheit", width="SHORT")
    '100°F'

#### `format_for_usage(value: 'float | int', unit: 'str', usage: 'str' = 'default', width: 'str | None' = None) -> 'str'`

Format a measurement in the locale's preferred unit for a usage.

ICU and CLDR choose the output unit from ``locale`` and ``usage``. This returns
formatted text, not a numeric conversion to a caller-specified target unit.
If ICU does not recognize a nonempty usage, it falls back to the locale's
default unit preferences.

Args:
    value: Numeric value
    unit: Source unit
    usage: Nonempty usage context ("default", "road", "person-height", etc.)
    width: Width style

Returns:
    Locale- and usage-preferred formatted measurement

Example:
    >>> fmt_us = MeasureFormatter("en_US")
    >>> fmt_us.format_for_usage(100, "kilometer", usage="road")
    '62 miles'
    >>> fmt_de = MeasureFormatter("de_DE")
    >>> fmt_de.format_for_usage(100, "kilometer", usage="road")
    '100 Kilometer'

#### `format_range(low: 'float | int', high: 'float | int', unit: 'str', width: 'str | None' = None) -> 'str'`

Format a measurement range.

Args:
    low: Low value
    high: High value
    unit: Unit name or abbreviation
    width: Width style

Returns:
    Formatted range (e.g., "5-10 kilometers")

#### `format_sequence(measures: 'list[tuple[float | int, str]]', width: 'str | None' = None) -> 'str'`

Format a sequence of measurements (compound units).

Args:
    measures: List of (value, unit) tuples
    width: Width style

Returns:
    Formatted compound measurement

Example:
    >>> fmt.format_sequence([(5, "foot"), (10, "inch")])
    '5 feet, 10 inches'
    >>> fmt.format_sequence([(1, "hour"), (30, "minute")])
    '1 hour, 30 minutes'

### `can_convert(from_unit: 'str', to_unit: 'str') -> 'bool'`

Check whether ICU classifies two units as the same unit type.

This checks compatibility only; it does not guarantee that the limited
:meth:`MeasureFormatter.convert` helper supports the pair.

Args:
    from_unit: Source unit name or abbreviation
    to_unit: Target unit name or abbreviation

Returns:
    True if the units have the same ICU unit type, False otherwise

Example:
    >>> can_convert("kilometer", "mile")
    True
    >>> can_convert("kilometer", "celsius")
    False

### `convert_units(value: 'float | int', from_unit: 'str', to_unit: 'str') -> 'float'`

Convert a value using the limited explicit factors.

This convenience function is not reflective or ICU-driven. See
:meth:`MeasureFormatter.convert` for the supported-pair behavior.

Args:
    value: Numeric value to convert
    from_unit: Source unit (e.g., "kilometer")
    to_unit: Target unit (e.g., "mile")

Returns:
    Converted value

Example:
    >>> convert_units(10, "kilometer", "mile")
    6.21371...
    >>> convert_units(100, "celsius", "fahrenheit")
    212.0

### `format_measure(value: 'float | int', unit: 'str', locale: 'str' = 'en_US', width: 'str' = 'WIDE') -> 'str'`

Format a measurement (convenience function).

Args:
    value: Numeric value
    unit: Unit name
    locale: Locale code
    width: Width style (WIDE, SHORT, NARROW)

Returns:
    Formatted measurement string

### `format_preferred(value: 'float | int', unit: 'str', locale: 'str', usage: 'str') -> 'str'`

Format a measurement in ICU's locale- and usage-preferred unit.

ICU and CLDR choose the output unit. The result is formatted text, not a numeric
conversion to a caller-specified target unit. If ICU does not recognize a
nonempty usage, it falls back to the locale's default unit preferences.

Args:
    value: Numeric value
    unit: Source unit name or abbreviation
    locale: Locale code
    usage: Nonempty usage context (for example, "road" or "person-height")

Returns:
    Locale- and usage-preferred formatted measurement

Example:
    >>> format_preferred(100, "kilometer", "en_US", "road")
    '62 mi'

### `get_unit_abbreviation(unit: 'str', locale: 'str' = 'en_US') -> 'str'`

Get the abbreviation for a unit.

Args:
    unit: Unit name (e.g., "kilometer")
    locale: Locale for abbreviation

Returns:
    Abbreviated form (e.g., "km")

### `get_unit_info(unit: 'str') -> 'dict'`

Get information about a unit.

Args:
    unit: Unit name or abbreviation

Returns:
    Dict with unit info: type, identifier, complexity

Example:
    >>> get_unit_info("mile")
    {'identifier': 'mile', 'type': 'length', 'complexity': 'single'}

### `get_units_by_type() -> 'dict[str, list[str]]'`

Get all units organized by type.

Returns:
    Dict mapping unit type to list of unit names.

Example:
    >>> units = get_units_by_type()
    >>> "meter" in units["length"]
    True

### `list_unit_types() -> 'list[str]'`

List available unit types.

Returns:
    List of unit type names (length, mass, temperature, etc.)

### `list_units(unit_type: 'str | None' = None) -> 'list[str]'`

List available units.

Args:
    unit_type: Optional type to filter by (e.g., "length", "mass")

Returns:
    List of unit names

### `resolve_unit(unit: 'str') -> 'str'`

Resolve a unit name or abbreviation to the canonical ICU unit name.

Args:
    unit: Unit name or abbreviation (e.g., "km", "kilometer", "mi")

Returns:
    Canonical ICU unit name (e.g., "kilometer", "mile")

Example:
    >>> resolve_unit("km")
    'kilometer'
    >>> resolve_unit("kilometer")
    'kilometer'

## icukit.message

ICU MessageFormat for localized string formatting.

MessageFormat provides locale-aware string formatting with support for
plurals, selects, and number/date formatting within messages.

Key Features:
    * Placeholder substitution: {name}
    * Number formatting: {count, number}
    * Plural rules: {count, plural, one {# item} other {# items}}
    * Select/gender: {gender, select, male {He} female {She} other {They}}
    * Nested formatting

Example:
    >>> from icukit import format_message
    >>> format_message('Hello, {name}!', {'name': 'World'}, 'en')
    'Hello, World!'
    >>> format_message('{count, plural, one {# item} other {# items}}',
    ...                {'count': 5}, 'en')
    '5 items'

### class `MessageFormatter`

ICU MessageFormat wrapper for localized string formatting.

Supports ICU message syntax including:
    - Simple placeholders: {name}
    - Number: {count, number} or {price, number, currency}
    - Date: {date, date, short|medium|long|full}
    - Time: {time, time, short|medium|long|full}
    - Plural: {count, plural, =0 {none} one {# item} other {# items}}
    - Select: {gender, select, male {He} female {She} other {They}}
    - SelectOrdinal: {pos, selectordinal, one {#st} two {#nd} few {#rd} other {#th}}

Example:
    >>> mf = MessageFormatter('{count, plural, one {# cat} other {# cats}}', 'en')
    >>> mf.format({'count': 1})
    '1 cat'
    >>> mf.format({'count': 5})
    '5 cats'

#### `MessageFormatter(pattern: 'str', locale: 'str' = 'en_US')`

Initialize a MessageFormatter.

Args:
    pattern: ICU message format pattern.
    locale: Locale for formatting rules.

Raises:
    MessageError: If the pattern is invalid.

#### `format(args: 'dict[str, Any]') -> 'str'`

Format the message with the given arguments.

Args:
    args: Dictionary mapping placeholder names to values.

Returns:
    Formatted string.

Raises:
    MessageError: If formatting fails.

Example:
    >>> mf = MessageFormatter('Hello, {name}!', 'en')
    >>> mf.format({'name': 'World'})
    'Hello, World!'

### `format_message(pattern: 'str', args: 'dict[str, Any]', locale: 'str' = 'en_US') -> 'str'`

Format a message with the given arguments.

Convenience function that creates a MessageFormatter for one-off use.

Args:
    pattern: ICU message format pattern.
    args: Dictionary mapping placeholder names to values.
    locale: Locale for formatting rules.

Returns:
    Formatted string.

Example:
    >>> format_message('Hello, {name}!', {'name': 'World'}, 'en')
    'Hello, World!'

    >>> format_message(
    ...     '{count, plural, one {# item} other {# items}}',
    ...     {'count': 5},
    ...     'en'
    ... )
    '5 items'

    >>> format_message(
    ...     '{gender, select, male {He} female {She} other {They}} said hi',
    ...     {'gender': 'female'},
    ...     'en'
    ... )
    'She said hi'

## icukit.parse

Locale-aware parsing of numbers, currencies, and percentages.

ICU's NumberFormat can parse locale-formatted strings back to numeric values,
handling locale-specific conventions like decimal separators, grouping
separators, and currency symbols.

Example:
    >>> from icukit import parse_number, parse_currency, parse_percent
    >>>
    >>> parse_number("1,234.56", "en_US")
    1234.56
    >>> parse_number("1.234,56", "de_DE")
    1234.56
    >>>
    >>> parse_currency("$1,234.56", "en_US")
    {'value': 1234.56, 'currency': 'USD'}
    >>> parse_currency("€1.234,56", "de_DE")
    {'value': 1234.56, 'currency': 'EUR'}
    >>>
    >>> parse_percent("50%", "en_US")
    0.5

### class `NumberParser`

Locale-aware number parser.

Parses numbers, currencies, and percentages according to locale conventions.

Example:
    >>> parser = NumberParser("de_DE")
    >>> parser.parse_number("1.234,56")
    1234.56
    >>> parser.parse_currency("€1.234,56")
    {'value': 1234.56, 'currency': 'EUR'}

#### `NumberParser(locale: 'str' = 'en_US')`

Create a NumberParser for the given locale.

Args:
    locale: Locale code (e.g., "en_US", "de_DE", "ja_JP")

#### `parse_currency(text: 'str', lenient: 'bool' = True) -> 'dict'`

Parse a locale-formatted currency string.

Args:
    text: Currency string to parse (e.g., "$1,234.56" or "€1.234,56")
    lenient: If True, be lenient with formatting variations

Returns:
    Dictionary with 'value' (float) and 'currency' (ISO code)

Raises:
    ParseError: If parsing fails

Example:
    >>> parser = NumberParser("en_US")
    >>> parser.parse_currency("$1,234.56")
    {'value': 1234.56, 'currency': 'USD'}

#### `parse_number(text: 'str', lenient: 'bool' = True) -> 'float'`

Parse a locale-formatted number string.

Args:
    text: Number string to parse (e.g., "1,234.56" or "1.234,56")
    lenient: If True, be lenient with formatting variations

Returns:
    Parsed numeric value

Raises:
    ParseError: If parsing fails

Example:
    >>> parser = NumberParser("en_US")
    >>> parser.parse_number("1,234.56")
    1234.56
    >>> parser = NumberParser("de_DE")
    >>> parser.parse_number("1.234,56")
    1234.56

#### `parse_percent(text: 'str', lenient: 'bool' = True) -> 'float'`

Parse a locale-formatted percentage string.

Args:
    text: Percentage string to parse (e.g., "50%" or "50 %")
    lenient: If True, be lenient with formatting variations

Returns:
    Parsed value as decimal (50% → 0.5)

Raises:
    ParseError: If parsing fails

Example:
    >>> parser = NumberParser("en_US")
    >>> parser.parse_percent("50%")
    0.5
    >>> parser.parse_percent("125%")
    1.25

### `parse_currency(text: 'str', locale: 'str' = 'en_US', lenient: 'bool' = True) -> 'dict'`

Parse a locale-formatted currency string (convenience function).

Args:
    text: Currency string to parse
    locale: Locale code
    lenient: If True, be lenient with formatting variations

Returns:
    Dictionary with 'value' and 'currency'

Example:
    >>> parse_currency("$1,234.56", "en_US")
    {'value': 1234.56, 'currency': 'USD'}
    >>> parse_currency("€1.234,56", "de_DE")
    {'value': 1234.56, 'currency': 'EUR'}

### `parse_number(text: 'str', locale: 'str' = 'en_US', lenient: 'bool' = True) -> 'float'`

Parse a locale-formatted number string (convenience function).

Args:
    text: Number string to parse
    locale: Locale code
    lenient: If True, be lenient with formatting variations

Returns:
    Parsed numeric value

Example:
    >>> parse_number("1,234.56", "en_US")
    1234.56
    >>> parse_number("1.234,56", "de_DE")
    1234.56

### `parse_percent(text: 'str', locale: 'str' = 'en_US', lenient: 'bool' = True) -> 'float'`

Parse a locale-formatted percentage string (convenience function).

Args:
    text: Percentage string to parse
    locale: Locale code
    lenient: If True, be lenient with formatting variations

Returns:
    Parsed value as decimal (50% → 0.5)

Example:
    >>> parse_percent("50%", "en_US")
    0.5

## icukit.plural

Locale-aware plural rules.

ICU's PluralRules determines which plural category (one, two, few, many, other)
a number falls into for a given locale.

Plural Categories:
    zero  - For 0 in some languages (Arabic)
    one   - Singular form (1 in English, but more complex in other languages)
    two   - Dual form (Arabic, Hebrew, Slovenian)
    few   - Paucal form (2-4 in Slavic languages)
    many  - "Many" category (5+ in Slavic, 11-99 in Maltese)
    other - General plural (default fallback)

Example:
    >>> from icukit import get_plural_category, list_plural_categories
    >>>
    >>> get_plural_category(1, "en")
    'one'
    >>> get_plural_category(2, "en")
    'other'
    >>> get_plural_category(1, "ru")
    'one'
    >>> get_plural_category(2, "ru")
    'few'
    >>> get_plural_category(5, "ru")
    'many'
    >>>
    >>> list_plural_categories("ar")
    ['zero', 'one', 'two', 'few', 'many', 'other']

### Constants and type aliases

#### `CATEGORY_FEW` (constant)

`'few'`

#### `CATEGORY_MANY` (constant)

`'many'`

#### `CATEGORY_ONE` (constant)

`'one'`

#### `CATEGORY_OTHER` (constant)

`'other'`

#### `CATEGORY_TWO` (constant)

`'two'`

#### `CATEGORY_ZERO` (constant)

`'zero'`

Category constants

#### `TYPE_CARDINAL` (constant)

`'cardinal'`

Type constants

#### `TYPE_ORDINAL` (constant)

`'ordinal'`

### `get_ordinal_category(number: 'int | float', locale: 'str' = 'en_US') -> 'str'`

Get the ordinal category for a number.

Ordinal categories are used for "1st", "2nd", "3rd", etc.

Args:
    number: The number to categorize
    locale: Locale code

Returns:
    Ordinal category: "zero", "one", "two", "few", "many", or "other"

Example:
    >>> get_ordinal_category(1, "en")
    'one'
    >>> get_ordinal_category(2, "en")
    'two'
    >>> get_ordinal_category(3, "en")
    'few'
    >>> get_ordinal_category(4, "en")
    'other'

### `get_plural_category(number: 'int | float', locale: 'str' = 'en_US') -> 'str'`

Get the plural category for a number.

Args:
    number: The number to categorize
    locale: Locale code (e.g., "en_US", "ru", "ar")

Returns:
    Plural category: "zero", "one", "two", "few", "many", or "other"

Example:
    >>> get_plural_category(1, "en")
    'one'
    >>> get_plural_category(2, "en")
    'other'
    >>> get_plural_category(2, "ru")
    'few'
    >>> get_plural_category(5, "ru")
    'many'

### `get_plural_rules_info(locale: 'str' = 'en_US') -> 'dict'`

Get detailed plural rules information for a locale.

Args:
    locale: Locale code

Returns:
    Dictionary with:
        - locale: The locale code
        - cardinal_categories: List of cardinal plural categories
        - ordinal_categories: List of ordinal plural categories
        - examples: Sample numbers for each cardinal category

Example:
    >>> info = get_plural_rules_info("ru")
    >>> info["cardinal_categories"]
    ['one', 'few', 'many', 'other']

### `list_ordinal_categories(locale: 'str' = 'en_US') -> 'list[str]'`

List the ordinal categories used by a locale.

Args:
    locale: Locale code

Returns:
    List of ordinal category names used by this locale

Example:
    >>> list_ordinal_categories("en")
    ['one', 'two', 'few', 'other']

### `list_plural_categories(locale: 'str' = 'en_US') -> 'list[str]'`

List the plural categories used by a locale.

Args:
    locale: Locale code

Returns:
    List of category names used by this locale (subset of
    ["zero", "one", "two", "few", "many", "other"])

Example:
    >>> list_plural_categories("en")
    ['one', 'other']
    >>> list_plural_categories("ru")
    ['one', 'few', 'many', 'other']
    >>> list_plural_categories("ar")
    ['zero', 'one', 'two', 'few', 'many', 'other']

## icukit.recognize

Flexible, CLDR-derived recognizers for non-canonical value surfaces.

Recognizers are the recall-oriented counterpart to the strict detectors in
:mod:`icukit.detectors`. They deposit structurally valid candidates without requiring the
surface to equal ICU's canonical formatting; the existing resolver can then select among
those candidates unchanged.

### class `AlphanumericRunsDetector`

Read a word that mixes letters and digits as its runs.

"3D" is digits "3" then letters "D", "5pm" is "5" then "pm", and "2Q22" is "2", "Q",
"22": the path a speaker takes when a token has no reading of its own ("three d",
"five p m"). It spans one ICU word with at least one digit and one letter, and it is
an alternative beside any other reading of the word, never a replacement for one.
Each run is a ``digits``, ``letters``, or ``separator`` capture in source order; a
combining mark or format character stays in the run it extends. A word whose letters
are in a script ICU breaks between letters (Thai, Lao, Khmer, Myanmar) has no runs
reading, since ICU's dictionary segmentation does not separate its digits into a
word of their own.

#### `AlphanumericRunsDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return one runs reading per mixed letter-and-digit word, in source order.

### class `AlphanumericRunsValue`

A token read as its runs: ``(("digits", "3"), ("letters", "D"))`` for "3D".

#### `AlphanumericRunsValue(runs: 'tuple[tuple[str, str], ...]') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `FlexibleCompactDetector`

Recognize a flexible number with reflectively derived ICU compact affixes.

``fold_symbol_case`` licenses case variants of single-letter compact symbols when
enclosing context disambiguates them. It is off by default because bare lowercase
symbols collide with unit abbreviations.

#### `FlexibleCompactDetector(locale: 'str', width: 'str', *, fold_symbol_case: 'bool' = False) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping flexible compact numbers in source order.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleCurrencyDetector`

Recognize a reflective currency symbol or name around a scaled flexible number.

#### `FlexibleCurrencyDetector(locale: 'str', currency: 'str', *, locales: 'Iterable[str] | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping flexible currency candidates in source order.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleCurrencyNameDetector`

Recognize flexible numbers adjacent to reflective spelled currency names.

#### `FlexibleCurrencyNameDetector(locale: 'str', currency: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping spelled-currency candidates in source order.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleDateDetector`

Recognize flexible numeric dates using CLDR short-date structures.

The stable ``date:flexible`` type distinguishes recall candidates from strict,
skeleton-specific date detections. Two-digit years retain their observed value;
this detector deposits one maximal candidate rather than expanding a century.

Every numeric short-date structure CLDR gives a locale of the same language is
read, the locale's own included, and each distinct valid date is deposited: en_US
reads "03/05/2013" both month first (its own pattern) and day first (en_GB's), and
reads "31.12.2012" through en_CH's dotted pattern. Each reading's spec names the
pattern it came from. A year written first must have four digits, since a leading
two-digit year cannot be told from a day ("10-12-14").

A date with its era reads as CLDR's ``GyMd`` patterns write it ("3/5/2024 AD",
"15/03/44 BC"), the era's names the language's (see ``_language_eras``); the value
leads with ``("G", era)``.

#### `FlexibleDateDetector(locale: 'str', *, locales: 'Iterable[str] | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return every structure's flexible numeric dates, distinct, in source order.

A date with its era is its own reading, beside the date without it.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleDateIntervalDetector`

Recognize date/time interval surfaces by inverting ICU DateIntervalFormat recipes.

Each greatest-difference field's recipe is CLDR's interval pattern when
``DateIntervalInfo`` has one, else the pattern recovered from ``DateIntervalFormat``'s
own output (see :func:`_recovered_interval_parts`). A 12-hour side's AM/PM marker is
parsed into the value, which keeps 24-hour ``H``; a time zone's text is parsed, gated
against ICU's rendering of that zone, and captured as ``time-zone``: the text as
written, the value the parsed zone's IANA ID ("ET" -> "America/New_York"; a GMT
offset, which has none, keeps ICU's custom ID, "GMT-08:00"). Zone text another
locale of the language writes, or that names different zones in its locales, is
read once per zone, each gated in its own zone (see :meth:`_read`).

A year from a ``y`` field is read only in four or more digits, as
:class:`~icukit.detectors.DateDetector` reads it: a shorter one cannot be told from
a count ("3–5", "pp. 12–15" in the year interval). Since the gate holds each side
to ICU's own rendering, a year under four digits is a year under 1000. A ``yy``
field keeps its two digits. ``short_years=True`` builds the guarded reader of
exactly the readings that floor refuses, typed ``date-interval:short-year:<skeleton>``
(as ``date:short-year:<skeleton>`` is the date reader's); a skeleton whose pattern
has no ``y`` field refuses it.

#### `FlexibleDateIntervalDetector(locale: 'str', skeleton: 'str', *, short_years: 'bool' = False) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping date-interval candidates in source order.

A span whose zone text names several zones is read once per zone, the reader's
own locale's zone first.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleFractionDetector`

Recognize signed ``N/D`` fractions and NFKC-decomposable vulgar fractions.

The ``fraction:flexible`` type marks recall candidates. Locale digits are reflective;
the fraction slash is the mathematical solidus (``/`` or U+2044), not locale data.
A fraction made plural ("3/4s") spans its suffix, with ``suffix`` (and
``apostrophe``) captures, as :class:`PluralNumeralDetector` reads a numeral.
The value is a :class:`NumberValue` whose ``decimal`` is computed with ``Decimal``:
a terminating fraction is exact (``1/2`` -> ``"0.5"``, ``3 1/2`` -> ``"3.5"``); a
non-terminating one is quantized to twelve fractional digits (``1/3`` ->
``"0.333333333333"``). A zero denominator is rejected.

#### `FlexibleFractionDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping flexible fractions in source order.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleMeasureDetector`

Recognize a flexible number followed by a reflectively derived ICU unit surface.

The surfaces are the unit's short, narrow, and wide forms as ICU formats them
("5 km", "5km", "5 kilometers"), in every locale of the language (en_GB's "5
kilometres" reads in en_US text; see :func:`_language_locales`), for an amount in
each of that locale's plural categories (see :func:`_plural_samples`), each also in
the spellings ICU equates with it (see :func:`_unit_surface_variants`: "km2", 12").
A rate ("1.0/km²", "3 per square kilometer") is read through CLDR's per-unit
pattern, with the value's unit ``per-<unit>``; a symbol-only per form follows the
number directly. A per form written without an amount ("/s", "per second") reads as
a :class:`~icukit.detectors.UnitValue` of the rate's unit, where no digit is
written right before it.

#### `FlexibleMeasureDetector(locale: 'str', unit: 'str', *, locales: 'Iterable[str] | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return flexible measure candidates in source order, a bare per form beside them.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleMixedMeasureDetector`

Recognize a mixed-unit measure, such as feet and inches: "5'10"", "5 ft, 10 in".

``unit`` is an ICU mixed-unit identifier of two or more components (``foot-and-inch``,
``pound-and-ounce``, ``hour-and-minute-and-second``). Everything is read from ICU:
each component's surfaces as :class:`FlexibleMeasureDetector` reads a single unit,
and, for each adjacent pair (itself an ICU mixed unit), the joiner from ICU's own
formatting of the pair at each width ("5′ 10″", "5 ft, 10 in"), optional where the
joiner is only a space, and the factor between the two (1.5 feet formats as 1 foot
6 inches). The value is the whole quantity in the smallest component, which is exact
("5'10"" is 70 inches; "1 hr, 15 min, 27 sec" is 4527 seconds).

#### `FlexibleMixedMeasureDetector(locale: 'str', unit: 'str', *, locales: 'Iterable[str] | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping mixed-unit measures in source order.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleNumberDetector`

Recognize flexible decimal spellings and Roman cardinals from ICU data.

Beside the locale's own grouping, a number reads in each other grouping ICU gives a
locale of the language ("250 000" as en_ZA formats it, "1'234'567" as en_CH,
"12,34,567" as en_IN), as an extra reading: "12 100" still reads "12" and "100",
and also 12100. A grouping whose separator is the locale's decimal separator is not
read that way, since it would reread every decimal number; instead the language's
other decimal styles (en_DE's "1.234,56", en_ZA's "1 234,56") are read only where the
locale's own styles do not already read the text: "1,5" reads 1.5 and "1.234,56"
1234.56, while "1,234" stays 1234 alone.

``accept_single_letter_roman`` defaults to true because corpora use ``I`` as the
cardinal one. Lowercase Roman numerals are opt-in because their surfaces collide with
unit abbreviations and common words; :class:`FlexibleLowercaseRomanDetector` reads
them as their own type, ``number:cardinal:roman-lower``.

#### `FlexibleNumberDetector(locale: 'str', *, accept_single_letter_roman: 'bool' = True, accept_lowercase_roman: 'bool' = False, locales: 'Iterable[str] | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping flexible decimal candidates in source order.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleNumberRangeDetector`

Recognize a range of two amounts as ICU's ``NumberRangeFormatter`` writes it.

The endpoints are read by the endpoint readers passed in -- by default this
locale's :class:`FlexibleNumberDetector` and :class:`FlexiblePercentDetector`; in
:func:`~icukit.engine.flexible_detectors`, the set's own number, percent, and
currency readers, and in a second reader its measure readers -- each on its side of
the separator, so each reads its amount as it reads it alone. The separator is one
ICU writes in some locale of the language ("3–5", ja_JP "3～5"), with or without
spaces around it. A side may leave its unit to the other where ICU writes a range
of that unit once ("$3–5", "10–15 kg", "10–15%"; see
:func:`_range_collapse_sides`), or both may write it ("$3.00 – $5.00"). The value is
a :class:`~icukit.detectors.NumberRangeValue` of two whole amounts. The captures are
the "start" and "end" amounts, each with its value, and the "separator"; immediately
after each endpoint capture are that endpoint reader's own captures, prefixed with
``"start."`` or ``"end."`` (for example ``"start.integer"``). Where the range reads
a minus sign before a start its reader read without one, that sign is captured as
``"start.sign"``. Approximately readings likewise put ``"value.*"`` captures
immediately after ``"value"``.

``form`` chooses what the reader reads, under its own type ``<group>:<form>``:

* ``"range"`` -- the separators ICU writes (``number:range``, ``measure:range``),
  a hyphen-minus only where ICU writes one (es_ES "3-5").
* ``"approximately"`` -- one amount after ICU's approximately sign ("~3", "≈3",
  "約3"), an :class:`~icukit.detectors.ApproximateValue`. A sign that is the
  locale's minus sign is left out. Where ICU writes the sign after a currency
  symbol ("US$~3.00" in some locales), that form is not read.

The endpoints' own readings are not touched: es_ES "3-5" still reads "-5" as a
negative number beside the range. No endpoint is one number of a longer run
joined by a separator, a hyphen, a colon, a slash, or a period ("14-3-3",
"2:07–4:07"). An endpoint is looked for within 48 characters of the separator.

#### `FlexibleNumberRangeDetector(locale: 'str', endpoints: 'Iterable[object] | Callable[[], Iterable[object]] | None' = None, *, form: 'str' = 'range', locales: 'Iterable[str] | None' = None, group: 'str | None' = None) -> 'None'`

``endpoints`` may be a callable returning them, called on the first
:meth:`detect`, so a set that never reads a range never builds them; ``group``
then names their group, which the type carries.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return every range (or approximately) reading in source order.

### class `FlexibleOrdinalDetector`

Recognize ordinal numerals (``1st``, ``第21``) using reflective CLDR affixes.

The ``ordinal:flexible`` type marks recall candidates. Ordinal affixes are obtained
reflectively by *forward* formatting: a candidate integer is rendered with every
public ``icu.RuleBasedNumberFormat`` ``ORDINAL`` rule set, and the prefix and suffix
are the non-digit parts around each rendering. No affix is hard-coded, and no fragile
ordinal *parse* is attempted. A surface is accepted only when its affixes match a pair
ICU generates for the parsed value, so ``21th`` is rejected while ``21st`` is not.

A grouped integer ("1,000th") is accepted when ICU renders the same surface for its
value. An ordinal suffix ICU writes in another locale is also read when it cannot be
mistaken for this locale's letters ("1º" in English text; see
:func:`_foreign_ordinal_suffixes`).

An uppercase Roman numeral is read as an ordinal when it carries this locale's own
ordinal suffix for its value ("Ist", "IInd", "XIVth") or a punctuation-only ordinal
marker ICU writes in some locale ("V.", "X."; see
:func:`_punctuation_ordinal_markers`). The integer capture's form is ``roman``.

Known limitation: as a defensive cross-locale constraint, RBNF ordinal formatting is
treated as reliable only through the signed-32-bit boundary (``2^31 - 1``). Above that
boundary it can return an incorrect suffix, and for very large integers it can raise
an ICU or ``SystemError`` exception. Such inputs are not deposited. Future
large-ordinal correctness awaits PyICU exposing ordinal plural rules (absent in 78.3),
or embedding CLDR ordinal-plural data; the affix can then be derived reflectively from
the ordinal plural category.

#### `FlexibleOrdinalDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return flexible ordinals in source order: digit ordinals, then Roman ones.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexiblePercentDetector`

Recognize flexible numbers adjacent to the locale's percent symbol.

The percent may also be written as a wide name ICU gives the percent unit in any
locale of the language ("5 percent", "5 per cent"), after the number.

#### `FlexiblePercentDetector(locale: 'str', *, locales: 'Iterable[str] | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping flexible percent candidates in source order.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleRelativeDateDetector`

Recognize relative dates by inverting locale-relative ICU formatting.

#### `FlexibleRelativeDateDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping relative-date candidates in source order.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleScientificDetector`

Recognize scientific notation using locale symbols reflected from ICU.

#### `FlexibleScientificDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping scientific numbers in source order.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleSpelloutDetector`

Recognize canonical ICU spelled-out numbers derived from locale RBNF data.

The cardinal rule set by default; ``ruleset`` chooses another the locale has (see
:func:`_spellout_rulesets`): "%spellout-ordinal" ("twenty-first"),
"%spellout-numbering-year" ("nineteen ninety-nine"), "%spellout-cardinal-verbose"
("one hundred and one"). The type is ``number:spellout`` for the default and
``number:spellout:<rule set>`` otherwise ("number:spellout:ordinal").

A lone token is suppressed only when it is one of the ambiguous unit words obtained
by formatting 0 through 9 ("one", "first"). Larger lone magnitudes and every
multi-token canonical surface remain eligible for deposit-and-hold alongside other
detector candidates.

#### `FlexibleSpelloutDetector(locale: 'str', *, ruleset: 'str | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping spelled-out cardinals in source order.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleTextDateDetector`

Recognize textual-month dates licensed by CLDR date patterns and symbols.

The structures are the locale's own medium, long, and full patterns (with their
year-optional subsets), plus the day-month-year, month-year, day-month, and
weekday-day-month-year patterns CLDR gives every locale of the same language, so
en_US reads en_GB's "1 July", "23 October 2014", and "Thursday, 2 May 2013". An
abbreviated month may carry a period where the locale's abbreviation lexicon lists
the month that way ("Oct. 2006", "Jan. 1").

A year in a date is read in four digits. A two- or three-digit one is read only
beside an era ("5 March 44 BC"), since without one it cannot be told from a count
after a date ("5 June 200 attendees"); those dates are read under their own type by
:class:`FlexibleShortYearDateDetector`.

A year beside an era abbreviation CLDR gives the language ("500 BC") is read as a
year with its era, in the order the language's CLDR ``yG`` pattern writes them (year
first in English, so "Vancouver, BC 2010" is not 2010 BC). The era names are
Gregorian, so the value is a Gregorian year: ``G`` (0 before the epoch, 1 after, as
ICU numbers them) and ``y``, with ``era`` and ``y`` captures.

#### `FlexibleTextDateDetector(locale: 'str', *, locales: 'Iterable[str] | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return textual-date, day-month, and era-year candidates in source order.

Each kind is its own pass, so their readings may overlap ("5 May 2000 AD" gives
the date and "2000 AD"); none takes a start from another.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `FlexibleTimeDetector`

Recognize clock times using a locale's CLDR short-time structure.

The ``time:flexible`` type marks recall candidates for hours:minutes, an optional
``:seconds``, and an optional day period (am/pm). All are reflective: the time
separator, the 12- vs 24-hour convention, and whether the day period is written
before or after the time come from the locale's short-time pattern
(``icu.DateFormat.createTimeInstance(kShort)``), and the day-period strings come from
``icu.DateFormatSymbols.getAmPmStrings`` -- nothing is hard-coded per locale. A
pattern whose am/pm field precedes the hour (``ko_KR`` ``"a h:mm"``) is read with the
day period as a prefix; a field after the hour is read as a suffix, and a pattern
without an am/pm field does not license one.

A bare hour is read directly as a 24-hour ``H`` (so ``15:45`` is recognized in a
12-hour locale); a day period is only consumed when the hour reads 1-12, and the
reading is then converted to 24-hour ``H`` (12 AM -> 0, 12 PM -> 12). Minutes and
seconds are exactly two digits in 0-59. An hour with no minutes reads only with a
day period after it ("5pm", "10 a.m."), where the locale writes the period after
the time, and its value then carries ``H`` alone.

The day-period forms are ICU's, at every width, for every CLDR locale of the same
language (see :func:`_language_day_periods`), so en_US also reads en_CA's "a.m.".
Likewise the hour-minute separator may be any the language's CLDR patterns use
("7.30pm"; see :func:`_language_time_separators`), and a time may be followed by a
time-zone abbreviation ICU writes for the language ("10 PM ET", "18:00 UTC"; see
:func:`_language_zone_abbreviations`), or by ICU's ISO 8601 "Z" written against it
("12:00:00Z"), captured as ``time-zone``. The capture's text is the zone as written;
its value is the IANA ID of the zone ICU parses it as, or of the zone that writes it
where that zone does not (see :func:`_zone_readings`): "Eastern Standard Time", "New
York Time", "EST" and "ET" are all "America/New_York" in en_US, "GMT" and "Z" are
"Etc/GMT", and "UTC" is "Etc/UTC". A name that
names several zones in the locales of the language gives one reading per zone:
"IST" is Europe/Dublin (en_IE) and Asia/Kolkata (en_IN).

A time may end in the locale's hour symbol ("10:30h", "10:30 Std."), and the symbol
CLDR writes attached may stand between hour and minutes ("10h30"); both forms come
from :func:`_hour_unit_forms`. Composing a clock time with a unit symbol this way
is hand-rolled, as CLDR has no pattern for it; the symbol is captured as
``hour-unit``.

#### `FlexibleTimeDetector(locale: 'str', *, locales: 'Iterable[str] | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return flexible clock times in source order.

A time followed by an hour symbol or a time-zone abbreviation is read both with and
without it ("10:30" and "10:30 hr"; "10 PM" and "10 PM ET"), so neither span
replaces the other. A zone name that names several zones is read once per zone
("10 PM IST": Europe/Dublin and Asia/Kolkata), the locale's own zone first.

#### `on_date(text: 'str', time: 'ValueDetection', fields) -> 'list[ValueDetection]'`

``time``'s readings once it is known to fall on the date ``fields`` give.

A zone is read as ICU writes it that day: "10:00 PM IST" is Irish summer time on
July 5 but not on January 5. ``fields`` are a date's ``(letter, value)`` pairs.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `LetterNameDetector`

Recognize an isolated ASCII Latin letter as its locale's letter name.

CLDR supplies alphabet repertoires but not the spoken names of their members, so
supported locales use a small lexical table. Unsupported locale languages produce no
candidates.

A letter may carry a plural or possessive suffix ("C's", "Cs"): the detection then
spans the whole token, with the letter in the ``letter`` capture and the rest in a
``suffix`` capture.

#### `LetterNameDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return isolated letter-name candidates in source order.

### class `MaterialLoneSpelloutDetector`

Recognize lone unit words with a validated material's spell-out rules.

#### `MaterialLoneSpelloutDetector(locale: 'str', material, *, ruleset: 'str | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return the lone unit words the default material reader refuses.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `MaterialSpelloutDetector`

Recognize spell-out rules supplied by a validated locale material file.

#### `MaterialSpelloutDetector(locale: 'str', material, *, ruleset: 'str | None' = None) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping spelled-out cardinals in source order.

#### `start_gates() -> 'Mapping[str, StartGate | None]'`

Return this reader's stable lane names and sound start gates.

### class `PluralNumeralDetector`

Recognize a numeral made plural: "1990s", "1990's", "'90s", "100s", "the 20s".

The value is the written number (``1990``, and ``90`` for "'90s", whose century is
elided), never a guessed decade or century: whether "1900s" is a decade or a century,
and whether "100s" is "hundreds" or "one hundreds", is for verbalization to offer.
Captures: ``number``, the ``suffix``, an ``apostrophe`` before the suffix if written,
and an ``elision`` apostrophe before the number if written. Digits are read by ICU's
digit values, so a locale's native digits count; the suffix letters are a small
per-language table, since CLDR has none, and a language without an entry has no
readings.

#### `PluralNumeralDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return plural-numeral readings in source order.

### class `SingleLetterWordDetector`

Recognize an isolated letter that is a word in its locale.

CLDR does not supply word lists, so supported locales use a small case-sensitive
lexical set. Unsupported locale languages produce no candidates.

#### `SingleLetterWordDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return isolated one-letter word candidates in source order.

## icukit.regex

Unicode regular expression utilities using ICU.

This module provides powerful Unicode-aware regular expression capabilities that go
far beyond Python's standard re module. It supports the full range of Unicode
properties, scripts, and categories for sophisticated text matching and manipulation.

Key Features:
    * Full Unicode property support (\\p{Property} syntax)
    * Script-based matching (\\p{Script=Name})
    * Unicode category matching (\\p{Category})
    * True Unicode-aware case-insensitive matching
    * Character class operations with Unicode sets
    * Efficient find, replace, and split operations
    * Indexed capture groups with text and code-point spans. ICU named groups remain
      available in patterns, backreferences, and replacements, but PyICU does not
      expose name-based capture lookup, so match results key groups by their 1-based
      numeric index.

Unicode Properties:
    The module supports all Unicode properties including:

    * **General Categories**: \\p{L} (letters), \\p{N} (numbers), \\p{P} (punctuation)
    * **Scripts**: \\p{Script=Latin}, \\p{Script=Han}, \\p{Script=Arabic}
    * **Blocks**: \\p{InBasicLatin}, \\p{InCJKUnifiedIdeographs}
    * **Binary Properties**: \\p{Alphabetic}, \\p{Emoji}, \\p{WhiteSpace}
    * **Derived Properties**: \\p{Changes_When_Lowercased}, \\p{ID_Start}

Example:
    Basic pattern matching::

        >>> from icukit import UnicodeRegex
        >>>
        >>> # Match Greek characters
        >>> regex = UnicodeRegex(r'\\p{Script=Greek}+')
        >>> matches = regex.find_all('Hello Αθήνα World')
        >>> for match in matches:
        ...     print(f"Found: {match['text']} at {match['start']}-{match['end']}")
        Found: Αθήνα at 6-11

        >>> # Match any letter in any script
        >>> regex = UnicodeRegex(r'\\p{L}+')
        >>> words = regex.find_all('Hello κόσμος 世界')
        >>> print([m['text'] for m in words])
        ['Hello', 'κόσμος', '世界']

    Advanced Unicode matching::

        >>> # Match emoji
        >>> regex = UnicodeRegex(r'\\p{Emoji}+')
        >>> emojis = regex.find_all('Hello 👋 World 🌍!')
        >>> print([m['text'] for m in emojis])
        ['👋', '🌍']

        >>> # Match text by script with proper boundaries
        >>> regex = UnicodeRegex(r'\\b\\p{Script=Greek}+\\b')
        >>> greek = regex.find_all('The word Αθήνα means Athens')
        >>> print(greek[0]['text'])
        'Αθήνα'

    Search and replace::

        >>> # Replace all digits with X
        >>> regex = UnicodeRegex(r'\\p{N}+')
        >>> result = regex.replace('Order #12345 costs $678.90', 'XXX')
        >>> print(result)
        'Order #XXX costs $XXX.XXX'

        >>> # Use capture groups in replacement
        >>> regex = UnicodeRegex(r'(\\w+)@(\\w+\\.\\w+)')
        >>> result = regex.replace('Contact: john@example.com', r'\\1 at \\2')
        >>> print(result)
        'Contact: john at example.com'

Note:
    ICU regex syntax differs from Python's re module in several ways:
    - Use \\p{Property} instead of Unicode categories
    - Different escape sequences (use \\\\\\\\ for backslash in patterns)
    - More comprehensive Unicode support
    - Some metacharacters behave differently

See Also:
    * :func:`regex_find`: Convenience function for finding matches
    * :func:`regex_replace`: Convenience function for replacements
    * :func:`regex_split`: Convenience function for splitting

### Constants and type aliases

#### `CASE_INSENSITIVE` (constant)

`2`

Flags

#### `COMMENTS` (constant)

`4`

#### `DOTALL` (constant)

`32`

#### `MULTILINE` (constant)

`8`

### class `UnicodeRegex`

Unicode-aware regular expression operations using ICU.

A powerful regex engine that provides full Unicode support, going beyond
Python's standard re module. It uses ICU's regex engine which implements
Unicode Technical Standard #18 for Unicode Regular Expressions.

The class provides methods for finding, matching, replacing, and splitting
text using Unicode-aware patterns. All operations return detailed match
information including positions and captured groups.

Attributes:
    pattern (str): The regex pattern string.
    flags (int): Combination of regex flags (CASE_INSENSITIVE, MULTILINE, etc.).

Pattern Syntax:
    ICU regex supports extensive Unicode property matching:

    * ``\\p{L}`` - Any letter
    * ``\\p{Script=Greek}`` - Greek script characters
    * ``\\p{Block=BasicLatin}`` - Characters in Basic Latin block
    * ``\\p{Emoji}`` - Emoji characters
    * ``\\P{...}`` - Negation (NOT the property)
    * ``\\b`` - Word boundary (Unicode-aware)
    * ``\\w``, ``\\d``, ``\\s`` - Unicode-aware word, digit, space

Example:
    Creating and using a Unicode regex::

        >>> # Match words in different scripts
        >>> regex = UnicodeRegex(r'\\b\\w+\\b')
        >>> matches = regex.find_all('Hello κόσμος 世界')
        >>> print([m['text'] for m in matches])
        ['Hello', 'κόσμος', '世界']

        >>> # Case-insensitive Unicode matching
        >>> regex = UnicodeRegex(r'café', CASE_INSENSITIVE)
        >>> print(regex.search('CAFÉ'))
        True

        >>> # Complex pattern with properties
        >>> # Match: letter, followed by digits, in parentheses
        >>> regex = UnicodeRegex(r'\\((\\p{L}+)(\\p{N}+)\\)')
        >>> match = regex.find('Code (A123) here')
        >>> print(match['groups'])
        {1: {'text': 'A', 'start': 6, 'end': 7}, 2: {'text': '123', 'start': 7, 'end': 10}}

#### `UnicodeRegex(pattern: 'str', flags: 'int' = 0)`

Initialize a Unicode regex.

Args:
    pattern: ICU regex pattern.
    flags: Regex flags (CASE_INSENSITIVE, MULTILINE, etc.).

Raises:
    PatternError: If the pattern is invalid.

#### `find(text: 'str', start: 'int' = 0) -> 'dict[str, Any] | None'`

Find first match in text.

``groups`` maps every declared capture group's 1-based numeric index to a
record containing ``text``, ``start``, and ``end``. Positions are Python
code-point indices. A group that did not participate has ``None`` for all
three fields; a group that matched an empty string has ``text == ""`` and
equal non-``None`` positions. Test participation with
``group["text"] is None``, not truthiness. Named groups are returned by
numeric index because PyICU exposes no name lookup. When a quantified group
captures repeatedly, ICU reports only its final captured instance; earlier
instances are not retrievable through this API.

For a complete scan, prefer ``find_all`` or ``iter_matches``, which handle
progress themselves. When driving ``find`` manually, advance like this::

    if match["start"] == match["end"]:
        if match["end"] == len(text):
            break
        start = match["end"] + 1
    else:
        start = match["end"]

Reusing an unchanged zero-width ``end`` returns the same match forever. The
terminal check must come before the increment, so the loop ends rather than
constructing ``len(text) + 1``. Adding one advances exactly one code point
and cannot land inside a surrogate pair, because these positions are
code-point indices.

Args:
    text: Text to search.
    start: Non-negative Python code-point index at which searching begins. A
        value greater than ``len(text)`` returns ``None``.

Returns:
    Match dict with text, start, end, and groups, or None if no match.

#### `find_all(text: 'str') -> 'list[dict[str, Any]]'`

Find all matches in text.

Args:
    text: Text to search.

Returns:
    List of match dictionaries.

#### `iter_matches(text: 'str') -> 'Iterator[dict[str, Any]]'`

Iterate over matches.

Args:
    text: Text to search.

Yields:
    Match dictionaries.

#### `match(text: 'str') -> 'bool'`

Check if pattern matches entire text.

Args:
    text: Text to match.

Returns:
    True if entire text matches.

#### `replace(text: 'str', replacement: 'str', limit: 'int' = -1) -> 'str'`

Replace matches with replacement text.

Args:
    text: Text to process.
    replacement: Replacement string (supports $1, $2 for groups).
    limit: Maximum replacements (-1 for all).

Returns:
    Text with replacements made.

#### `replace_with_callback(text: 'str', callback) -> 'str'`

Replace matches using a callback function.

Args:
    text: Text to process.
    callback: Function that takes match dict and returns replacement.

Returns:
    Text with replacements made.

#### `search(text: 'str') -> 'bool'`

Check if pattern exists anywhere in text.

Args:
    text: Text to search.

Returns:
    True if pattern found.

#### `split(text: 'str', limit: 'int' = -1) -> 'list[str]'`

Split text by pattern.

Args:
    text: Text to split.
    limit: Maximum splits (-1 for unlimited).

Returns:
    List of split parts.

#### `validate() -> 'bool'`

Check if the pattern is valid.

Returns:
    True if pattern is valid.

### `list_unicode_categories() -> 'list[dict[str, str]]'`

List Unicode general categories with structured info.

Returns:
    List of dicts with 'code' and 'description' keys.

### `list_unicode_properties() -> 'list[dict[str, Any]]'`

List Unicode properties with structured info for TSV/JSON output.

Returns:
    List of dicts with 'category', 'pattern', and 'description' keys.

### `list_unicode_scripts() -> 'list[dict[str, str]]'`

List Unicode scripts with structured info.

Returns:
    List of dicts with 'name' and 'pattern' keys.

### `parse_substitution(expr: 'str') -> 'tuple[str, str, bool, bool]'`

Parse a sed-style ``s/pattern/replacement/flags`` expression.

The delimiter may be any character. Recognized flags are ``g`` (global)
and ``i`` (ignore case); other flags are ignored.

Args:
    expr: Substitution expression to parse.

Returns:
    Pattern, replacement, global flag, and ignore-case flag.

Raises:
    ValueError: If the expression is malformed.

### `regex_find(pattern: 'str', text: 'str', flags: 'int' = 0) -> 'list[dict[str, Any]]'`

Find all matches of pattern in text.

Args:
    pattern: ICU regex pattern.
    text: Text to search.
    flags: Regex flags.

Returns:
    List of match dictionaries.

### `regex_fullmatch(pattern: 'str', text: 'str', flags: 'int' = 0) -> 'bool'`

Test whether a pattern matches the entire stripped text.

The pattern is wrapped with ``^`` and ``$`` exactly as supplied.

Args:
    pattern: ICU regex pattern.
    text: Text to strip and match.
    flags: Regex flags.

Returns:
    True if the anchored pattern produces a match.

### `regex_replace(pattern: 'str', text: 'str', replacement: 'str', flags: 'int' = 0, limit: 'int' = -1) -> 'str'`

Replace pattern matches in text.

Args:
    pattern: ICU regex pattern.
    text: Text to process.
    replacement: Replacement string.
    flags: Regex flags.
    limit: Maximum replacements.

Returns:
    Text with replacements.

### `regex_search(pattern: 'str', text: 'str', flags: 'int' = 0) -> 'bool'`

Test whether a pattern occurs anywhere in text.

Args:
    pattern: ICU regex pattern.
    text: Text to search.
    flags: Regex flags.

Returns:
    True if at least one match is found.

### `regex_split(pattern: 'str', text: 'str', flags: 'int' = 0, limit: 'int' = -1) -> 'list[str]'`

Split text by pattern.

Args:
    pattern: ICU regex pattern.
    text: Text to split.
    flags: Regex flags.
    limit: Maximum splits.

Returns:
    List of split parts.

## icukit.region

Geographic region and territory information.

Query countries, territories, continents, and their relationships
using ICU's region data.

Key Features:
    * List all regions by type (territory, continent, etc.)
    * Get region info (code, numeric code, containing region)
    * Query containment hierarchy (which regions contain which)

Region Types:
    * TERRITORY - Countries and territories (US, FR, JP, etc.)
    * CONTINENT - Continents (Africa, Americas, Asia, Europe, Oceania)
    * SUBCONTINENT - Subcontinental regions (Northern America, Western Europe)
    * GROUPING - Economic/political groupings (EU, UN, etc.)
    * WORLD - The world (001)

Example:
    List and query regions::

        >>> from icukit import list_regions, get_region_info
        >>>
        >>> # List all territories (countries)
        >>> territories = list_regions('territory')
        >>> len(territories)
        257
        >>>
        >>> # Get info about a region
        >>> info = get_region_info('US')
        >>> info['name']
        'United States'
        >>> info['numeric_code']
        840
        >>> info['containing_region']
        '021'  # Northern America

### `get_contained_regions(code: 'str') -> 'list[str]'`

Get regions directly contained by a region.

Args:
    code: Region code (e.g., '001' for World, '019' for Americas).

Returns:
    List of contained region codes.

Example:
    >>> # What's in the Americas?
    >>> get_contained_regions('019')
    ['005', '013', '021', '029']  # South/Central/North America, Caribbean

### `get_region_info(code: 'str', extended: 'bool' = False) -> 'dict[str, Any] | None'`

Get information about a region.

Args:
    code: Region code (e.g., 'US', 'FR', '001' for World).
    extended: Include extended attributes (contained_regions).

Returns:
    Dict with region info, or None if not found.

Example:
    >>> info = get_region_info('US')
    >>> info['code']
    'US'
    >>> info['numeric_code']
    840
    >>> info['type']
    'territory'
    >>> info = get_region_info('019', extended=True)
    >>> 'contained_regions' in info['extended']
    True

### `list_region_types() -> 'list[dict[str, str]]'`

List available region types.

Returns:
    List of dicts with type name and description.

Example:
    >>> types = list_region_types()
    >>> types[0]
    {'type': 'continent', 'description': 'Continents (Africa, Americas, ...)'}

### `list_regions(region_type: 'str' = 'territory') -> 'list[str]'`

List all regions of a given type.

Args:
    region_type: Type of regions to list. One of:
        'territory', 'continent', 'subcontinent', 'grouping', 'world'.
        Defaults to 'territory' (countries).

Returns:
    List of region codes sorted alphabetically.

Raises:
    RegionError: If region_type is invalid.

Example:
    >>> territories = list_regions('territory')
    >>> 'US' in territories
    True
    >>> continents = list_regions('continent')
    >>> len(continents)
    5

### `list_regions_info(region_type: 'str' = 'territory') -> 'list[dict[str, Any]]'`

List all regions with their info.

Args:
    region_type: Type of regions to list.

Returns:
    List of dicts with region info.

Example:
    >>> regions = list_regions_info('territory')
    >>> us = next(r for r in regions if r['code'] == 'US')
    >>> us['numeric_code']
    840

## icukit.resolve

Resolve a universe of overlapping detections into a best non-overlapping sequence.

The detectors DEPOSIT every candidate they find --
running them on ``1/3/2026`` yields a ``date:yMd`` over the whole span alongside the digit
fragments ``1``, ``3``, ``26``. This module weighs that universe into the maximum-weight
non-overlapping cover (1-best), or an ordering of covers that collapses to 1-best.

The weight is span length times specificity: a longer coherent match is far less likely to
be coincidental, and a match that commits to more structure (more captures) and still fits is
stronger evidence. The two axes usually agree; where they diverge the scalar weight forces the
call. Preference is soft -- when the top two covers are within a margin the resolver reports
the contest as ambiguous rather than guessing.

This is additive: :func:`~icukit.detectors.detect` is unchanged; resolution is an opt-in layer.

### Constants and type aliases

#### `DEFAULT_EPSILON` (constant)

`1.0`

Margin below which the top two covers are reported as a contest rather than a winner.

A float, and the parameters taking it are annotated float. Weights are integral, so a
threshold that separates one margin from the next is only expressible as a fraction, and
narrowing the signature to ``int`` would tell a caller that such a threshold is out of
bounds when it is the only way to ask the question.


### class `Resolution`

The weighed reading of a universe of detections.

``best`` is the maximum-weight non-overlapping sequence in source order. ``covers`` is the
n-best ordering of covers by descending score, with ``covers[0] == best``. ``margin`` is the
score gap between the top two covers; ``ambiguous`` is true when that gap is below the
refusal threshold, meaning the resolver declines to commit between them.

#### `Resolution(best: 'tuple[ValueDetection, ...]', covers: 'tuple[tuple[ValueDetection, ...], ...]', margin: 'int', ambiguous: 'bool') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `resolve(detections: 'list[ValueDetection] | tuple[ValueDetection, ...]', *, n: 'int' = 8, epsilon: 'float' = 1.0) -> 'Resolution'`

Weigh a universe of (possibly overlapping) detections into a :class:`Resolution`.

Returns the maximum-weight non-overlapping ``best`` sequence, the ``n``-best ordering of
covers, and an ``ambiguous`` flag when the top two covers are within ``epsilon``.

### `resolve_text(text: 'str', detectors: 'list[Detector] | tuple[Detector, ...]', *, n: 'int' = 8, epsilon: 'float' = 1.0) -> 'Resolution'`

Run every detector over ``text`` and resolve the deposited universe in one call.

### `weight(detection: 'ValueDetection') -> 'int'`

A candidate's score: span length (code points) times specificity.

Specificity is one plus the capture count -- the structure the reading commits to -- so a
richer match wins an equal-length contest while length carries the unequal ones.

## icukit.script

Unicode script detection and properties.

Detect the writing system (script) of text and query script properties.
Scripts include Latin, Greek, Cyrillic, Han, Arabic, Hebrew, and many more.

Key Features:
    * Detect script of text or individual characters
    * Check if script has case distinctions (upper/lowercase)
    * Check if script is right-to-left
    * List all available scripts

Example:
    Detect script of text::

        >>> from icukit import detect_script, is_rtl
        >>>
        >>> detect_script('Hello')
        'Latin'
        >>> detect_script('Ελληνικά')
        'Greek'
        >>> detect_script('你好')
        'Han'
        >>>
        >>> is_rtl('Hello')
        False
        >>> is_rtl('مرحبا')
        True

    Query script properties::

        >>> from icukit import get_script_info, list_scripts
        >>>
        >>> info = get_script_info('Greek')
        >>> info['is_cased']
        True
        >>> info['is_rtl']
        False
        >>>
        >>> scripts = list_scripts()
        >>> len(scripts)
        160

### `detect_script(text: 'str') -> 'str'`

Detect the primary script of text.

Analyzes the first character to determine the script. For mixed-script
text, use detect_scripts() to get all scripts present.

Args:
    text: Text to analyze.

Returns:
    Script name (e.g., 'Latin', 'Greek', 'Han').

Example:
    >>> detect_script('Hello')
    'Latin'
    >>> detect_script('Ελληνικά')
    'Greek'
    >>> detect_script('你好世界')
    'Han'
    >>> detect_script('مرحبا')
    'Arabic'

### `detect_scripts(text: 'str') -> 'list[str]'`

Detect all scripts present in text.

Args:
    text: Text to analyze.

Returns:
    List of unique script names found, in order of first occurrence.

Example:
    >>> detect_scripts('Hello Ελληνικά')
    ['Latin', 'Common', 'Greek']
    >>> detect_scripts('abc123')
    ['Latin', 'Common']

### `get_char_script(char: 'str') -> 'str'`

Get the script of a single character.

Args:
    char: A single character.

Returns:
    Script name.

Raises:
    ValueError: If input is not a single character.

Example:
    >>> get_char_script('α')
    'Greek'
    >>> get_char_script('A')
    'Latin'
    >>> get_char_script('你')
    'Han'

### `get_script_info(script: 'str', extended: 'bool' = False) -> 'dict[str, Any] | None'`

Get information about a script.

Args:
    script: Script name (e.g., 'Greek', 'Latin') or code (e.g., 'Grek', 'Latn').
    extended: Include extended attributes (sample_char).

Returns:
    Dict with script info, or None if not found.

Raises:
    ScriptError: If script name/code is invalid.

Example:
    >>> info = get_script_info('Greek')
    >>> info['code']
    'Grek'
    >>> info['is_cased']
    True
    >>> info = get_script_info('Arabic', extended=True)
    >>> info['extended']['sample_char']
    'ب'

### `is_cased(script: 'str') -> 'bool'`

Check if a script has case distinctions.

Cased scripts have uppercase and lowercase letter variants.
Examples: Latin, Greek, Cyrillic are cased. Han, Arabic, Hebrew are not.

Args:
    script: Script name or code.

Returns:
    True if script has case distinctions.

Raises:
    ScriptError: If script is invalid.

Example:
    >>> is_cased('Latin')
    True
    >>> is_cased('Greek')
    True
    >>> is_cased('Han')
    False
    >>> is_cased('Arabic')
    False

### `is_rtl(text: 'str') -> 'bool'`

Check if text is in a right-to-left script.

RTL scripts include Arabic, Hebrew, Syriac, etc.

Args:
    text: Text to check.

Returns:
    True if the primary script is right-to-left.

Example:
    >>> is_rtl('Hello')
    False
    >>> is_rtl('مرحبا')
    True
    >>> is_rtl('שלום')
    True

### `list_scripts() -> 'list[str]'`

List all available Unicode scripts.

Returns:
    List of script names sorted alphabetically.

Example:
    >>> scripts = list_scripts()
    >>> 'Latin' in scripts
    True
    >>> 'Greek' in scripts
    True

### `list_scripts_info() -> 'list[dict[str, Any]]'`

List all scripts with their properties.

Returns:
    List of dicts with script info: code, name, is_cased, is_rtl.

Example:
    >>> scripts = list_scripts_info()
    >>> greek = next(s for s in scripts if s['name'] == 'Greek')
    >>> greek['is_cased']
    True

## icukit.search

Locale-aware text search using ICU's StringSearch.

ICU's StringSearch provides collation-based searching that respects
language-specific rules, allowing matches like "café" to match "cafe"
when using accent-insensitive comparison.

Example:
    >>> from icukit import search_all, search_first
    >>> search_all("cafe", "Visit the café. The CAFE is open.", "fr_FR", strength="primary")
    [{'start': 10, 'end': 14, 'text': 'café'}, {'start': 20, 'end': 24, 'text': 'CAFE'}]
    >>> search_first("cafe", "The café is here", strength="primary")
    {'start': 4, 'end': 8, 'text': 'café'}

### Constants and type aliases

#### `STRENGTH_IDENTICAL` (constant)

`'identical'`

#### `STRENGTH_PRIMARY` (constant)

`'primary'`

Search strength levels (reuse collator terminology)

#### `STRENGTH_QUATERNARY` (constant)

`'quaternary'`

#### `STRENGTH_SECONDARY` (constant)

`'secondary'`

#### `STRENGTH_TERTIARY` (constant)

`'tertiary'`

### class `StringSearcher`

Reusable locale-aware string searcher.

Useful when searching the same pattern across multiple texts,
or when you need more control over the search process.

Example:
    >>> searcher = StringSearcher("café", "en_US", strength="primary")
    >>> searcher.find_all("I love cafe and CAFÉ")
    [{'start': 7, 'end': 11, 'text': 'cafe'}, {'start': 16, 'end': 20, 'text': 'CAFÉ'}]
    >>> searcher.contains("No coffee here")
    False

#### `StringSearcher(pattern: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None)`

Create a reusable searcher for the given pattern.

Args:
    pattern: The string to search for.
    locale: Locale for collation rules.
    strength: Collation strength.

#### `contains(text: 'str') -> 'bool'`

Check if the pattern exists in text.

#### `count(text: 'str') -> 'int'`

Count matches of the pattern in text.

#### `find_all(text: 'str') -> 'list[dict[str, Any]]'`

Find all matches of the pattern in text.

#### `find_first(text: 'str') -> 'dict[str, Any] | None'`

Find the first match of the pattern in text.

#### `replace(text: 'str', replacement: 'str', count: 'int' = 0) -> 'str'`

Replace matches with replacement string.

### `search_all(pattern: 'str', text: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None) -> 'list[dict[str, Any]]'`

Find all occurrences of pattern in text using locale-aware matching.

Args:
    pattern: The string to search for.
    text: The text to search in.
    locale: Locale for collation rules (default: en_US).
    strength: Collation strength:
        - "primary" - Base letters only (café=cafe=CAFE)
        - "secondary" - Base + accents (cafe=CAFE, but café≠cafe)
        - "tertiary" - Base + accents + case (default, exact match)
        - "quaternary" - Tertiary + punctuation differences
        - "identical" - Bit-for-bit identical

Returns:
    List of match dicts with 'start', 'end', and 'text' keys.

Example:
    >>> search_all("cafe", "The café and CAFE", "en_US", strength="primary")
    [{'start': 4, 'end': 8, 'text': 'café'}, {'start': 13, 'end': 17, 'text': 'CAFE'}]

### `search_count(pattern: 'str', text: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None) -> 'int'`

Count occurrences of pattern in text.

Args:
    pattern: The string to search for.
    text: The text to search in.
    locale: Locale for collation rules (default: en_US).
    strength: Collation strength (see search_all).

Returns:
    Number of matches found.

Example:
    >>> search_count("cafe", "café, Cafe, CAFE", strength="primary")
    3

### `search_first(pattern: 'str', text: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None) -> 'dict[str, Any] | None'`

Find the first occurrence of pattern in text.

Args:
    pattern: The string to search for.
    text: The text to search in.
    locale: Locale for collation rules (default: en_US).
    strength: Collation strength (see search_all).

Returns:
    Match dict with 'start', 'end', 'text', or None if not found.

Example:
    >>> search_first("café", "Visit the cafe today", strength="primary")
    {'start': 10, 'end': 14, 'text': 'cafe'}

### `search_replace(pattern: 'str', text: 'str', replacement: 'str', locale: 'str' = 'en_US', *, strength: 'str | None' = None, count: 'int' = 0) -> 'str'`

Replace occurrences of pattern in text using locale-aware matching.

Args:
    pattern: The string to search for.
    text: The text to search in.
    replacement: The replacement string.
    locale: Locale for collation rules (default: en_US).
    strength: Collation strength (see search_all).
    count: Maximum replacements (0 = unlimited).

Returns:
    Text with replacements made.

Example:
    >>> search_replace("cafe", "Visit the café", "tea", strength="primary")
    'Visit the tea'

## icukit.sentence_override

Whole-text and incremental sentence-break overrides.

ICU always supplies the candidate boundaries: this module can retain or
suppress them, but never add one. For English (language ``en``, with any region
or script, except the ``POSIX`` variant), the locale default applies token
integrity and the locale's shipped abbreviation suppressions to ICU candidates.
With no caller inventories or rules, other locale defaults and explicit
``base="none"`` are exactly ICU's current sentence output, without that list.
Caller layers still apply over ``base="none"``. The English named bases
``"en-tn@1"`` and ``"en-tn-cart@1"`` apply the same list before their rules or
model. Whole-text and incremental operation share the same prefix-aware
candidate evaluator.

Example:
    >>> override = SentenceOverride()
    >>> [(item["offset"], item["layer"]) for item in override.decide("Hi. Bye.")]
    [(4, 'icu'), (8, 'icu')]

### class `BreakBoundary`

An open sentence boundary carrying both readings.

### class `BreakDecision`

The attributed decision for one ICU sentence candidate.

A cartlet model decision appends the root-relative path ID of the leaf it
reached as ``"<model>#leaf:<path>"`` (for example,
``"en-tn-cart@1#leaf:RRRRRRRRLR"``). The path spells each branch from the
root: ``L``/``R`` for binary splits, ``D`` for a switch default, and
``C<length>:<key>`` for a matched switch case.

### class `BreakPredicate`

dict() -> new empty dictionary
dict(mapping) -> new dictionary initialized from a mapping object's
    (key, value) pairs
dict(iterable) -> new dictionary initialized as if via:
    d = {}
    for k, v in iterable:
        d[k] = v
dict(**kwargs) -> new dictionary initialized with the name=value pairs
    in the keyword argument list.  For example:  dict(one=1, two=2)

### class `BreakRule`

One ordered sentence candidate rule.

Authored witnesses validate the containing rule set as one isolated rule
layer. Loader inventories contribute word-level token merges only; their
sentence-level suppression rules and all deployment layers are excluded.

``run-1`` is the complete left whitespace run truncated at the candidate.
Its text, lower-case text, length, shapes, first/last character classes,
leading-whitespace flag, and run shape are all derived from that same
truncated run, never from only its final token.

A forward character position ``c+n`` has horizon equal to the number of
right tokens ending at or before that code point, plus one when the code
point is inside a right token, with a minimum of one. It is readable when
that horizon is at most ``lookahead``. Thus the gap after token ``+k`` is
readable at lookahead ``k``, while the first code point of token ``+(k+1)``
is ``<BEYOND>``. At or past the end of the text, its horizon is the lesser
of eight and one more than the number of right tokens; a readable position
returns ``<EOS>``. ``tokens_read`` records this horizon, including ``k``
rather than ``k+1`` for a gap after token ``+k``. Every ``c+n`` predicate
therefore requires a declared lookahead of at least one.

### class `BreakRuleIdentity`

Runtime identity against which a break-rule artifact was authored.

### class `BreakRuleSet`

An immutable, validated ordered set of flat break rules.

#### `BreakRuleSet(id: 'str', locale: 'str', status: "Literal['experimental']", features: 'str', runtime_identity: 'Mapping[str, str]', digest: 'str', _rules: 'tuple[_CompiledBreakRule, ...]', provenance: 'Mapping[str, object] | None' = None) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `BreakSegmentation`

Primary sentence spans plus every boundary left open by a rule.

### class `CartletModelRef`

A digest- and runtime-bound reference to a cartlet model.

Constructing a reference does not import cartlet. The dependency is
imported only when a :class:`SentenceOverride` uses this reference. Model
evaluation requires cartlet 0.8 or later.
Models use ``icukit.features@1`` and are tied to the ICU, Unicode, and
tokenizer identity under which those features were measured.

#### `CartletModelRef(path: 'str | Path', digest: 'str', identity: 'Mapping[str, str]' = <factory>, features: 'str' = 'icukit.features@1', name: 'str' = 'cartlet') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `IncrementalSentenceBreaker`

Incrementally decide ICU sentence candidates with immutable output.

Instances are created by :meth:`SentenceOverride.stream`. Offsets are code
points in all text supplied so far. ``flush()`` treats the current end as
END but permits later input; ``close()`` also prevents further input.

Example:
    >>> stream = SentenceOverride().stream()
    >>> result = stream.feed("Hello. N") + stream.feed("ext.") + stream.close()
    >>> result  # doctest: +NORMALIZE_WHITESPACE
    [{'offset': 7, 'end': 6, 'decision': 'break', 'alternatives': ('break',),
      'layer': 'icu', 'id': None, 'tokens_read': 0},
     {'offset': 12, 'end': 12, 'decision': 'break', 'alternatives': ('break',),
      'layer': 'icu', 'id': None, 'tokens_read': 0}]

#### `IncrementalSentenceBreaker(owner: 'SentenceOverride', protection: "Literal['none', 'watermark']") -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `close() -> 'list[BreakDecision]'`

Flush once and reject later input; repeated calls return an empty list.

#### `feed(chunk: 'str', /, *, protected: 'Iterable[ProtectedSpan]' = (), protected_through: 'int | None' = None) -> 'list[BreakDecision]'`

Append a chunk and return decisions made immutable by this prefix.

#### `flush() -> 'list[BreakDecision]'`

End the current logical segment without closing the stream.

Current candidates are decided with END as context. Later input starts
a new ICU segment, so its decisions equal whole-text decisions for the
post-flush text alone, shifted by the flushed stream length.

#### `pending() -> 'list[PendingCandidate]'`

Return snapshots of candidates that still need context or protection.

### class `PendingCandidate`

An ICU candidate awaiting stable context, a rule feature, or protection.

### class `SentenceOverride`

Apply token integrity, exceptions, rules, or a model to ICU candidates.

``en-tn@1`` is a learned English rule base under
CC BY-SA 4.0. Its reported development and test figures measure agreement
with the Google TN corpus splitter on synthetic ``glue2`` concatenations,
not accuracy on naturally occurring running text. Its witnesses are
synthesized from each rule's predicates, which include lexical values
mined from the corpus (e.g. ``lower`` token values); no corpus sentence or
row was read or copied.

The locale default is:

================ =========================================================
Locale language  Default
================ =========================================================
``en``           ICU + token integrity + shipped list (except ``POSIX``)
every other      raw ICU
================ =========================================================

Region and script do not change the English default. The ``POSIX`` variant
uses raw ICU. The English default and the two named English bases load the
locale-fallback abbreviation lexicon's ``break="suppress"`` entries as
sentence exceptions. Decisions are ordered as ICU candidates, token
integrity, caller-before rules, exceptions, the optional base, and
caller-after rules. With no caller inventories or rules, pass
``base="none"`` explicitly for raw ICU sentence boundaries without the
shipped list; caller layers still apply over it. Cartlet is an icukit
dependency and is imported lazily only when ``"en-tn-cart@1"`` or a
:class:`CartletModelRef` is selected.

Args:
    locale: ICU locale used for both sentence and word boundaries.
    base: ``None`` selects the locale default in the table above. Otherwise,
        ``"none"`` selects raw ICU, ``"en-tn@1"`` selects the learned rule
        base, ``"en-tn-cart@1"`` selects the learned model, and callers may
        supply a loaded rule set, a :class:`CartletModelRef`, or a path to a
        ``break-rules`` JSON file. Unknown names are refused.
    before: Ordered caller rules that force a decision before inventories
        and the base.
    after: Ordered caller rules that may override the base decision.
    inventories: Exception inventories; word rules merge tokens and
        sentence rules suppress candidates.
    cache: Reuse immutable per-token features in incremental evaluation.

Example:
    >>> override = SentenceOverride()
    >>> [(item["offset"], item["layer"]) for item in override.decide("Hello. Next.")]
    [(7, 'icu'), (12, 'icu')]

#### `SentenceOverride(locale: 'str' = 'en_US', /, *, base: "Literal['none'] | str | Path | BreakRuleSet | CartletModelRef | None" = None, before: 'Sequence[BreakRuleSet]' = (), after: 'Sequence[BreakRuleSet]' = (), inventories: 'Sequence[LoadedExceptionInventory]' = (), cache: 'bool' = True) -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `decide(text: 'str', /, *, protected: 'Iterable[ProtectedSpan]' = ()) -> 'list[BreakDecision]'`

Return an attributed decision for every raw ICU sentence candidate.

#### `segmentations(text: 'str', /, *, protected: 'Iterable[ProtectedSpan]' = ()) -> 'BreakSegmentation'`

Return one-best spans and each candidate retaining two alternatives.

#### `spans(text: 'str', /, *, protected: 'Iterable[ProtectedSpan]' = ()) -> 'list[BreakSpan]'`

Return the one-best sentence spans; trailing whitespace stays left.

#### `stream(*, protection: "Literal['none', 'watermark']" = 'none') -> 'IncrementalSentenceBreaker'`

Return an incremental breaker sharing this override's decision core.

Collation-variant word- and sentence-level exception rules are refused:
primary-ignorable code points make their surface-match extent unbounded,
so no bounded incremental hold can decide them safely. Use those rules
with whole-text methods such as :meth:`decide`, or use exact variants.

In text without whitespace or punctuation/symbol edges whose
``Word_Break`` value is ``Other``, a decision may wait for whitespace,
:meth:`IncrementalSentenceBreaker.flush`, or
:meth:`IncrementalSentenceBreaker.close`.

### `break_rule_identity(locale: 'str' = 'en_US', /, *, inventories: 'Sequence[LoadedExceptionInventory]' = ()) -> 'BreakRuleIdentity'`

Return the runtime identity an authored break-rule set must declare.

The token profile binds the explicit :data:`icukit.tokens.TOKEN_PROFILE`
version, locale, word-level exception inventory material, protected-span
policy, and built-in shape definitions. Sentence-only exception rules are
recorded in :attr:`SentenceOverride.identity` but do not enter this token
profile because they cannot change model features. The profile version is
bumped when the golden tokenizer behavior changes; it is not a proof
derived from implementation text. Fixtures should call this function
instead of hard-coding versions.

### `load_break_rules(source: 'str | Path | Mapping[str, object]', /, *, locale: 'str' = 'en_US', inventories: 'Sequence[LoadedExceptionInventory]' = ()) -> 'BreakRuleSet'`

Load, validate, identity-check, and witness-test flat break rules.

``source`` may be a parsed JSON object or a path to a ``break-rules`` JSON
file. Witnesses execute transactionally after compilation; no partially
validated rule set is returned. An object witness may add an integer
``offset`` and a ``decision`` of ``break``, ``no-break``, or ``ambiguous``
to pin the candidate and result. A ``no_match`` witness always requires
that its rule decide no candidate anywhere in the text. Witnesses evaluate
the loaded set as one isolated rule layer: ``inventories`` contribute only
word-level token merges, while sentence-level inventory suppression and
all other deployment layers are excluded. Callers compose those layers at
deployment, where each candidate's attribution reports the deciding one.

## icukit.serialize

recognition-output serializer — converts typed ValueDetection candidates to plain JSON;
no external deps; reusable by downstream consumers.

### `detection_to_dict(detection: 'ValueDetection') -> 'dict'`

Convert one typed detection to an ordered, plain JSON-native dictionary.

### `detections_to_json(detections) -> 'list[dict]'`

Convert typed detections to a list containing only JSON-native values.

## icukit.shape

Versioned ICU word-shape schemes.

The built-in schemes are deliberately fixed and identified by a digest of
their canonical definition and the linked ICU/Unicode versions. Experimental
runtime material can add namespaced symbols without redefining them.

Example:
    >>> shape("U.S.")
    'A.A.'
    >>> shape("U.S.", "cased@1")
    'X.X.'

### class `CVLetterCounts`

Uncapped orthographic consonant-vowel letter counts.

``letters`` counts code points labeled ``V``, ``C``, ``Y``, or ``L``, plus
letters that a namespaced shape refinement relabels (still letters);
``vowels`` counts ``V``; ``consonants`` counts ``C`` and ``Y``; and
``has_vowel`` reports whether ``vowels`` is positive.

### class `ShapeSchemeInfo`

Stable metadata identifying a shape scheme and its Unicode runtime.

### `cvletters_counts(text: 'str', /, *, locale: 'str | None' = None, material: 'Iterable[LocaleMaterial]' = ()) -> 'CVLetterCounts'`

Count uncapped ``cvletters@1`` labels in ``text``.

``Y`` counts as a consonant. ``L`` contributes only to ``letters``, so
``letters > vowels + consonants`` reports letters for which no vowel policy
is available. Digits, absorbed marks, and other characters are excluded.

### `shape(text: 'str', scheme: 'str' = 'coarse@1', /, *, locale: 'str | None' = None, material: 'Iterable[LocaleMaterial]' = ()) -> 'str'`

Return the versioned ICU shape of ``text``.

``coarse@1`` collapses letter and digit runs; ``cased@1`` distinguishes
letter case and caps each same-symbol run at four. ``cvletters@1`` is an
approximate orthographic shape of vowel and consonant letters, not phones;
its curated Latin table requires an ``en``-descendant ``locale``. Other
alphabetic letters are ``L`` unless material supplies a label. Combining
marks directly following a letter or digit run are absorbed unless ICU or a
refinement labels them. Validated namespaced shape refinements take
precedence and collapse adjacent uses as one run. An extended scheme name
checks the supplied material's ids and digest prefixes; the name is a label,
not proof of material identity.

Example:
    >>> shape("Mr. Smith")
    'A. A'
    >>> shape("Mr. Smith", "cased@1")
    'Xx. Xxxxx'

### `shape_scheme(scheme: 'str' = 'coarse@1', /, *, locale: 'str | None' = None, material: 'Iterable[LocaleMaterial]' = ()) -> 'ShapeSchemeInfo'`

Describe a shape scheme and return its stable identity digest.

The digest covers canonical JSON containing the scheme definition plus the
linked ICU and Unicode versions. With material, it also covers every
material digest and reports each extension's id and digest. Its extended
name is a label containing each material id and 12-hex digest prefix. Passing
that label back checks those prefixes against the supplied material as a guard
against an obvious mismatch; the full extension digests and this record's
digest, rather than the label, are identities.
``locale`` is accepted for symmetry with :func:`shape` but does not affect
scheme metadata or its digest.

## icukit.spoof

Confusable and homoglyph detection using ICU's SpoofChecker.

ICU's SpoofChecker detects visually confusable strings that could be used
in phishing or spoofing attacks (e.g., Cyrillic "а" vs Latin "a").

Example:
    >>> from icukit import are_confusable, get_skeleton
    >>> are_confusable("paypal", "pаypal")  # Cyrillic 'а'
    True
    >>> get_skeleton("pаypal")
    'paypal'

### Constants and type aliases

#### `CONFUSABLE_MIXED_SCRIPT` (constant)

`2`

#### `CONFUSABLE_NONE` (constant)

`0`

Confusable result flags (bitmask values from ICU)

#### `CONFUSABLE_SINGLE_SCRIPT` (constant)

`1`

#### `CONFUSABLE_WHOLE_SCRIPT` (constant)

`4`

### class `SpoofChecker`

Reusable spoof checker for multiple operations.

Example:
    >>> checker = SpoofChecker()
    >>> checker.are_confusable("paypal", "pаypal")
    True
    >>> checker.get_skeleton("pаypal")
    'paypal'

#### `SpoofChecker()`

Create a new SpoofChecker.

#### `are_confusable(string1: 'str', string2: 'str') -> 'bool'`

Check if two strings are confusable.

#### `check(text: 'str') -> 'dict[str, Any]'`

Check string for spoofing issues.

Reports the same record as :func:`check_string`, including the caveat that
``mixed_script`` and ``whole_script`` are pairwise flags a single-string
check does not set.

#### `get_confusable_type(string1: 'str', string2: 'str') -> 'int'`

Get confusability type between two strings.

#### `get_skeleton(text: 'str') -> 'str'`

Get skeleton form of a string.

### `are_confusable(string1: 'str', string2: 'str') -> 'bool'`

Check if two strings are visually confusable.

Two strings are confusable if they could be mistaken for each other,
such as when one uses lookalike characters from different scripts.

Args:
    string1: First string to compare.
    string2: Second string to compare.

Returns:
    True if the strings are confusable, False otherwise.

Example:
    >>> are_confusable("paypal", "pаypal")  # Second has Cyrillic 'а'
    True
    >>> are_confusable("hello", "world")
    False

### `check_string(text: 'str') -> 'dict[str, Any]'`

Check a string for potential spoofing issues.

Analyzes the string for mixed scripts, invisible characters,
and other potential security issues.

This is a check of one string on its own, which is not the same question as
:func:`are_confusable`. The confusability flags answer "could these two be
mistaken for each other", and ICU only sets them when it is given a pair, so
``mixed_script`` and ``whole_script`` stay False here even for a string built
from lookalike characters. What catches such a string is ``restriction_level``:
ICU's default identifier profile rejects it for mixing scripts at all.

Args:
    text: String to check.

Returns:
    Dict with check results:
    - 'flags': Raw check result flags
    - 'is_suspicious': True if any issues detected
    - 'mixed_script': Confusable with another string across scripts, which a
      single-string check does not determine; see :func:`are_confusable`
    - 'whole_script': Whole-script confusable, likewise pairwise
    - 'restriction_level': Fails ICU's identifier restriction level
    - 'invisible': Contains invisible characters
    - 'mixed_numbers': Contains mixed number systems
    - 'hidden_overlay': Contains a combining mark hidden by the base character

Example:
    >>> result = check_string("pаypal")  # Cyrillic 'а'
    >>> result['is_suspicious']
    True
    >>> result['restriction_level']  # mixes Latin and Cyrillic
    True
    >>> result['mixed_script']  # pairwise flag, not set by a single-string check
    False

### `get_confusable_info(string1: 'str', string2: 'str') -> 'dict[str, Any]'`

Get detailed confusability information between two strings.

Args:
    string1: First string to compare.
    string2: Second string to compare.

Returns:
    Dict with confusability details:
    - 'confusable': Whether strings are confusable
    - 'type': Confusability type flags
    - 'type_names': List of type names
    - 'skeleton1': Skeleton of first string
    - 'skeleton2': Skeleton of second string
    - 'same_skeleton': Whether skeletons match

Example:
    >>> info = get_confusable_info("paypal", "pаypal")
    >>> info['confusable']
    True
    >>> info['type_names']
    ['mixed_script']

### `get_confusable_type(string1: 'str', string2: 'str') -> 'int'`

Get the type of confusability between two strings.

Args:
    string1: First string to compare.
    string2: Second string to compare.

Returns:
    Bitmask indicating confusability type:
    - CONFUSABLE_NONE (0): Not confusable
    - CONFUSABLE_SINGLE_SCRIPT (1): Confusable within same script
    - CONFUSABLE_MIXED_SCRIPT (2): Confusable across scripts
    - CONFUSABLE_WHOLE_SCRIPT (4): Entire string looks like different script

Example:
    >>> get_confusable_type("paypal", "pаypal")
    2  # CONFUSABLE_MIXED_SCRIPT

### `get_skeleton(text: 'str') -> 'str'`

Get the skeleton form of a string for confusability comparison.

The skeleton is a normalized form where visually similar characters
are mapped to a common representation. Two strings with the same
skeleton are confusable.

Args:
    text: String to get skeleton for.

Returns:
    Skeleton string.

Example:
    >>> get_skeleton("pаypal")  # Cyrillic 'а'
    'paypal'
    >>> get_skeleton("paypal")
    'paypal'

## icukit.timezone

Timezone information and utilities.

Query timezone data including offsets, DST rules, and display names.

Key Features:
    * List all available timezones (637+)
    * Get timezone info (offset, DST, display name)
    * Query equivalent timezone IDs
    * Get current offset for a timezone

Example:
    List and query timezones::

        >>> from icukit import list_timezones, get_timezone_info
        >>>
        >>> # List all timezones
        >>> tzs = list_timezones()
        >>> len(tzs)
        637
        >>>
        >>> # Get info about a timezone
        >>> info = get_timezone_info('America/New_York')
        >>> info['offset_hours']
        -5.0
        >>> info['uses_dst']
        True

### `get_equivalent_timezones(tz_id: 'str') -> 'list[str]'`

Get equivalent timezone IDs for a timezone.

Args:
    tz_id: Timezone ID.

Returns:
    List of equivalent timezone IDs.

Example:
    >>> equivs = get_equivalent_timezones('America/New_York')
    >>> 'US/Eastern' in equivs
    True

### `get_timezone_info(tz_id: 'str', extended: 'bool' = False) -> 'dict[str, Any] | None'`

Get information about a timezone.

Args:
    tz_id: Timezone ID (e.g., 'America/New_York', 'Europe/London').
    extended: Include extended attributes (region, windows_id, equivalent_ids).

Returns:
    Dict with timezone info, or None if not found.

Example:
    >>> info = get_timezone_info('America/New_York')
    >>> info['id']
    'America/New_York'
    >>> info['display_name']
    'Eastern Standard Time'
    >>> info = get_timezone_info('America/New_York', extended=True)
    >>> info['extended']['region']
    'US'

### `get_timezone_offset(tz_id: 'str') -> 'float'`

Get the current UTC offset for a timezone in hours.

Args:
    tz_id: Timezone ID.

Returns:
    Offset in hours (negative for west of UTC).

Raises:
    TimezoneError: If timezone is not found.

Example:
    >>> get_timezone_offset('America/New_York')
    -5.0  # or -4.0 during DST

### `list_timezones(country: 'str | None' = None) -> 'list[str]'`

List all available timezone IDs.

Args:
    country: Optional ISO 3166 country code to filter by (e.g., 'US', 'DE').

Returns:
    List of timezone IDs sorted alphabetically.

Example:
    >>> tzs = list_timezones()
    >>> 'America/New_York' in tzs
    True
    >>> us_tzs = list_timezones('US')
    >>> 'America/New_York' in us_tzs
    True

### `list_timezones_info(country: 'str | None' = None) -> 'list[dict[str, Any]]'`

List all timezones with their info.

Args:
    country: Optional country code to filter by.

Returns:
    List of dicts with timezone info.

Example:
    >>> tzs = list_timezones_info()
    >>> nyc = next(t for t in tzs if t['id'] == 'America/New_York')
    >>> nyc['uses_dst']
    True

## icukit.tokens

ICU word tokens, caller-protected units, and token features.

Token-scoped protected spans can join ICU word segments and intervening
whitespace into one unit. Hint spans are validated but intentionally do not
change tokenization; the sentence-break rule layer will consume them later.
Locale-material extensions are likewise deferred to that later integration.

Example:
    >>> [(token["text"], token["run"]) for token in tokens("the U.S. Then", "en_US")]
    [('the', 0), ('U.S', 1), ('.', 1), ('Then', 2)]

### Constants and type aliases

#### `TOKEN_PROFILE` (constant)

`'icukit.tokens@1'`

Bump this whenever the observable ``tokens()`` policy changes.  The sentence
override includes it in authored-rule identities, and a golden test below the
API pins representative punctuation, astral, protection, and inventory cases.

### class `ProtectedSpan`

A caller-owned code-point span used as a token unit or a later hint.

### class `Token`

A non-whitespace ICU word segment or protected token unit.

``protected`` is the lexicographically first type on a protected token;
``protected_types`` is the sorted tuple of every type on equal-extent
protected spans.

### `token_features(toks: 'Sequence[Token]', i: 'int', text: 'str', /, *, locale: 'str | None' = None, material: 'Iterable[LocaleMaterial]' = ()) -> 'dict[str, str | int | bool]'`

Return token features, including orthographic consonant-vowel counts.

``run.shape.cased`` covers the complete whitespace-delimited run containing
the token. ``lex`` is reserved and is currently always ``"none"``. The
``shape.cvletters`` and four ``cvletters.*`` values describe the token
surface. Pass ``locale`` to enable the curated English letter table for an
``en`` descendant; without a policy, alphabetic letters are labeled ``L``.

### `tokens(text: 'str', locale: 'str', /, *, inventory: 'LoadedExceptionInventory | None' = None, protected: 'Iterable[ProtectedSpan]' = ()) -> 'list[Token]'`

Return ICU non-whitespace word segments with whitespace-run indexes.

Token-scoped protected spans take precedence over inventory word merges and
ICU segmentation. Nested spans use the outermost unit; partial overlaps are
refused; equal extents produce one token carrying all sorted types.

Example:
    >>> spans = [{"start": 5, "end": 9, "type": "range"}]
    >>> token = tokens("from 5-10 m", "en_US", protected=spans)[1]
    >>> (token["text"], token["run"], token["protected"])
    ('5-10', 1, 'range')

## icukit.transliterator

Text transliteration using ICU Transliterator.

This module provides powerful text transformation capabilities through ICU's
transliteration engine. It supports conversion between writing systems,
normalization, and custom transformation rules.

Key Features:
    * Script-to-script conversion (Latin <-> Cyrillic <-> Greek <-> Arabic, etc.)
    * Text normalization (accent removal, case conversion, etc.)
    * Built-in transliterators for common transformations
    * Custom rule-based transliterators
    * Transliterator chaining and filtering
    * Bidirectional transformations

Common Transliterators:
    * Script Conversions: Latin-Greek, Latin-Arabic, Latin-Cyrillic,
      Han-Latin, Hiragana-Katakana, and many more
    * Normalizations: NFD, NFC, NFKD, NFKC, Lower, Upper, Title
    * Specialized: Any-Publishing (ASCII-safe), Any-Accents (remove accents)

### class `CommonTransliterators`

Common pre-configured transliterators for frequent use cases.

#### `normalize(text: 'str', form: 'str' = 'NFC') -> 'str'`

Normalize Unicode text to a standard form (NFC, NFD, NFKC, NFKD).

#### `remove_accents(text: 'str') -> 'str'`

Remove accents and diacritical marks from text.

#### `to_ascii(text: 'str') -> 'str'`

Convert text to ASCII representation.

#### `to_latin(text: 'str') -> 'str'`

Convert text from any script to Latin script.

#### `to_lower(text: 'str') -> 'str'`

Convert text to lowercase using Unicode rules.

#### `to_title(text: 'str') -> 'str'`

Convert text to title case using Unicode rules.

#### `to_upper(text: 'str') -> 'str'`

Convert text to uppercase using Unicode rules.

### class `Transliterator`

Text transliteration using ICU's transformation engine.

Transliterators transform text from one writing system to another or apply
other text transformations like normalization or case mapping.

#### `Transliterator(transliterator_id: 'str', reverse: 'bool' = False)`

Initialize a Transliterator.

Args:
    transliterator_id: ICU transliterator ID (e.g., 'Latin-Greek').
    reverse: If True, creates the inverse transliterator.

Raises:
    TransliteratorError: If the transliterator ID is not available.

#### `create_inverse() -> 'Transliterator'`

Create the inverse of this transliterator.

Returns:
    A new Transliterator that reverses this one's transformation.

Raises:
    TransliteratorError: If this transliterator has no inverse.

#### `get_source_set() -> 'set[str]'`

Get the set of characters this transliterator can convert.

Raises:
    TransliteratorError: If the source set cannot be computed.

#### `get_target_set() -> 'set[str]'`

Get the set of characters this transliterator can produce.

Raises:
    TransliteratorError: If the target set cannot be computed.

#### `transliterate(text: 'str') -> 'str'`

Transform text using this transliterator.

Args:
    text: The text to transform.

Returns:
    The transformed text.

Raises:
    TransliteratorError: If the transformation fails.

### `get_transliterator_info(transliterator_id: 'str') -> 'dict[str, Any] | None'`

Get detailed information about a transliterator.

Args:
    transliterator_id: ICU transliterator ID.

Returns:
    Dictionary with transliterator info, or None if the ID is invalid:
        - id: The transliterator ID
        - source: Source script (parsed from ID)
        - target: Target script (parsed from ID)
        - variant: Variant name if any
        - reversible: Whether inverse is available
        - elements: Number of sub-transliterators
        - max_context: Maximum context length needed

### `list_transliterators() -> 'list[str]'`

Get list of all available transliterator IDs.

Returns:
    Sorted list of transliterator ID strings.

### `list_transliterators_info() -> 'list[dict[str, Any]]'`

Get detailed info for all available transliterators.

Returns:
    List of info dicts for each transliterator.

### `transliterate(text: 'str', transliterator_id: 'str', reverse: 'bool' = False) -> 'str'`

Transliterate text using the specified transliterator.

Args:
    text: Text to transliterate.
    transliterator_id: ICU transliterator ID (e.g., 'Latin-Cyrillic').
    reverse: If True, uses the inverse transformation.

Returns:
    Transliterated text.

## icukit.ucd_name_aliases

Unicode's formal name aliases that ICU does not carry ("BEL", "ALERT", "NBSP", "ZWJ").

Unicode gives some characters formal name aliases (``NameAliases.txt`` in the UCD), of
five types: ``correction``, ``control``, ``alternate``, ``figment`` and
``abbreviation``. ICU's name data carries the corrections alone, which
:mod:`icukit.unicode` reads from ICU; this module reads the other four types from a
snapshot of the UCD file (``data/ucd_name_aliases``), made by
``tools/ucd_name_aliases.py`` from the file of ICU's Unicode version, pinned by URL and
checksum, which the snapshot's header records.

Unicode's stability policy never changes or removes a formal name alias once
published, so under an ICU of a later Unicode the snapshot's aliases all still hold,
and only the aliases published since are missing. Under an ICU of an earlier Unicode,
the aliases of code points that ICU does not know as assigned are left out, so that
no alias names a character ICU does not have.

### Constants and type aliases

#### `ALIAS_TYPES` (constant)

`('correction', 'control', 'alternate', 'figment', 'abbreviation')`

The types of formal name alias, in the order ``NameAliases.txt`` defines them.

### `icu_unicode_version() -> 'str'`

The Unicode version of ICU's data ("17.0").

### `snapshot_unicode_version() -> 'str'`

The Unicode version of the snapshot's ``NameAliases.txt`` ("17.0.0"); empty
without a snapshot.

### `ucd_name_aliases() -> 'tuple[tuple[int, str, str], ...]'`

``(code point, alias, type)`` for each alias in the snapshot, in the file's order.

The snapshot holds every type but ``correction``, which ICU carries. Under an ICU of
an earlier Unicode than the snapshot's, the aliases of code points ICU does not know
as assigned are left out. Empty when the snapshot is missing.

## icukit.unicode

Unicode text normalization and character properties.

Normalize text to standard Unicode forms (NFC, NFD, NFKC, NFKD) and
query Unicode character properties like names and categories.

Key Features:
    * Normalize text to NFC, NFD, NFKC, NFKD forms
    * Get Unicode character names, name aliases (of every type) and extended names
    * Look up a character by its name
    * Get character categories and properties
    * Check normalization status

Normalization Forms:
    * NFC - Canonical decomposition, then canonical composition (default)
    * NFD - Canonical decomposition
    * NFKC - Compatibility decomposition, then canonical composition
    * NFKD - Compatibility decomposition

Example:
    Normalize text::

        >>> from icukit import normalize
        >>>
        >>> # Composed vs decomposed forms
        >>> text = 'café'  # may be composed or decomposed
        >>> normalize(text, 'NFC')  # composed: é is one codepoint
        'café'
        >>> normalize(text, 'NFD')  # decomposed: e + combining accent
        'café'
        >>>
        >>> # Compatibility normalization
        >>> normalize('ﬁ', 'NFKC')  # ligature to separate chars
        'fi'

    Character properties::

        >>> from icukit import char_from_name, get_char_name, get_char_category
        >>>
        >>> get_char_name('α')
        'GREEK SMALL LETTER ALPHA'
        >>> get_char_name('😀')
        'GRINNING FACE'
        >>> char_from_name('GREEK SMALL LETTER ALPHA')
        'α'
        >>>
        >>> get_char_category('A')
        'Lu'  # Letter, uppercase
        >>> get_char_category('5')
        'Nd'  # Number, decimal digit

### Constants and type aliases

#### `NFC` (constant)

`'NFC'`

Normalization form constants

#### `NFD` (constant)

`'NFD'`

#### `NFKC` (constant)

`'NFKC'`

#### `NFKD` (constant)

`'NFKD'`

### `char_from_name(name: 'str', choice: 'str' = 'any') -> 'str'`

Look up the character a Unicode name names.

The lookup is ICU's, exact apart from case: ICU matches names without regard to
case, and nothing looser is added here -- no trimming, no collapsing of spaces or
hyphens. ``choice`` selects the names searched:

* ``unicode`` -- formal names, including the algorithmic ones such as
  ``HANGUL SYLLABLE GAG`` and ``CJK UNIFIED IDEOGRAPH-4F60``.
* ``alias`` -- formal name aliases only, of every type :func:`get_char_aliases`
  lists: ``LATIN CAPITAL LETTER GHA`` (a correction, ICU's), ``ALERT``, ``BEL``,
  ``NBSP``, ``BYTE ORDER MARK``. The types ICU does not carry are read from a
  snapshot of the UCD, and matched as ICU matches, without regard to ASCII case.
* ``extended`` -- formal names and the labels :func:`get_char_name` gives for
  ``extended``, such as ``<control-0007>``.
* ``any`` (the default) -- all of the above. Unicode keeps names and aliases in
  one namespace, so no name is both one character's name and another's alias.

Args:
    name: A character name.
    choice: ``any`` (the default), ``unicode``, ``alias``, or ``extended``.

Returns:
    The named character.

Raises:
    ValueError: If no character has that name among the names searched, or choice
        is not one of the four.
    TypeError: If name is not a str.

Example:
    >>> char_from_name('GREEK SMALL LETTER ALPHA')
    'α'
    >>> char_from_name('greek small letter alpha')
    'α'
    >>> char_from_name('LATIN CAPITAL LETTER GHA')
    'Ƣ'
    >>> char_from_name('<control-0007>')
    '\x07'
    >>> char_from_name('bel')
    '\x07'

### `decode_unicode_escapes(text: 'str') -> 'str'`

Decode Unicode escape sequences in text.

Each escape Python's ``unicode_escape`` codec knows decodes as it does there
(``\uXXXX``, ``\UXXXXXXXX``, ``\xXX`` as code point ``U+00XX``, octal,
``\N{NAME}``, and ``\n``, ``\t``, ``\\`` and the other single-character
escapes), and ``U+XXXX`` through ``U+XXXXXX`` is the character it names. Every
other character, including non-ASCII text and an escape that does not parse, is
left as written.

### `encode_unicode_escapes(text: 'str', format: 'str' = 'uplus') -> 'str'`

Encode text in one of the CLI's five Unicode escape formats.

Args:
    text: Text to encode. Escape sequences are decoded before encoding.
    format: One of ``u``, ``U``, ``x``, ``uplus``, or ``char``.

Returns:
    Encoded text, or decoded text for the ``char`` format.

Raises:
    ValueError: If format is not supported.

### `get_block_characters(block_name: 'str') -> 'list[str]'`

Get all characters in a specific Unicode block.

Args:
    block_name: Name of the block (e.g., 'Basic Latin').

Returns:
    List of characters in the block.

Raises:
    ValueError: If block name is invalid.

### `get_category_characters(category_code: 'str') -> 'list[str]'`

Get all characters in a specific Unicode general category.

Args:
    category_code: Two-letter category code (e.g., 'Lu', 'Nd').

Returns:
    List of characters in the category.

Raises:
    ValueError: If category code is invalid.

### `get_char_aliases(char: 'str') -> 'list[dict[str, str]]'`

Get every formal name alias of a character, with its type.

Unicode's formal name aliases (``NameAliases.txt``) are of five types, and a code
point can have several, of several types:

* ``correction`` -- a corrected name, as :func:`get_char_name` gives for ``alias``
  (``LATIN CAPITAL LETTER GHA`` for U+01A2);
* ``control`` -- the ISO 6429 and other common names of a control (``ALERT``,
  ``LINE FEED``);
* ``alternate`` -- a widely used other name of a format character
  (``BYTE ORDER MARK``);
* ``figment`` -- a label for a C1 control that no standard approved
  (``PADDING CHARACTER``);
* ``abbreviation`` -- a common abbreviation (``BEL``, ``NBSP``, ``ZWJ``, ``VS1``).

The corrections are ICU's. ICU carries no other type, so those come from a snapshot
of the UCD file of ICU's Unicode version (see :mod:`icukit.ucd_name_aliases`).

Args:
    char: A single character.

Returns:
    A list of dicts, one per alias, each with the ``alias`` and its ``type``: the
    correction first and the rest in the UCD file's order; empty where there is none.

Raises:
    ValueError: If input is not a single character.

Example:
    >>> get_char_aliases('\x07')
    [{'alias': 'ALERT', 'type': 'control'}, {'alias': 'BEL', 'type': 'abbreviation'}]
    >>> get_char_aliases('Ƣ')
    [{'alias': 'LATIN CAPITAL LETTER GHA', 'type': 'correction'}]
    >>> get_char_aliases('A')
    []

### `get_char_category(char: 'str') -> 'str'`

Get the Unicode general category of a character.

Categories are two-letter codes like 'Lu' (Letter, uppercase),
'Ll' (Letter, lowercase), 'Nd' (Number, decimal digit), etc.

Args:
    char: A single character.

Returns:
    Two-letter category code.

Raises:
    ValueError: If input is not a single character.

Example:
    >>> get_char_category('A')
    'Lu'
    >>> get_char_category('a')
    'Ll'
    >>> get_char_category('5')
    'Nd'
    >>> get_char_category(' ')
    'Zs'
    >>> get_char_category('!')
    'Po'

### `get_char_info(char: 'str') -> 'dict[str, Any]'`

Get comprehensive information about a character.

Args:
    char: A single character.

Returns:
    Dict with character info: codepoint, name, category, script, etc. ``name`` is
    the formal name, ``alias`` the formal name alias (empty where there is none),
    and ``extended_name`` the extended name, which names every code point, as
    :func:`get_char_name` describes each; ``aliases`` is every formal name alias
    with its type, as :func:`get_char_aliases` lists them.

Raises:
    ValueError: If input is not a single character.

Example:
    >>> info = get_char_info('α')
    >>> info['name']
    'GREEK SMALL LETTER ALPHA'
    >>> info['category']
    'Ll'
    >>> info['codepoint']
    'U+03B1'

### `get_char_name(char: 'str', choice: 'str' = 'unicode') -> 'str'`

Get a Unicode name of a character.

ICU keeps three names for a code point, and ``choice`` selects one:

* ``unicode`` -- the formal name (the Unicode ``Name`` property). Empty for a code
  point that has none: a control, a surrogate, a noncharacter, a private-use or an
  unassigned code point.
* ``alias`` -- the formal name alias Unicode published to correct a mistaken name,
  such as ``LATIN CAPITAL LETTER GHA`` for U+01A2, whose formal name
  ``LATIN CAPITAL LETTER OI`` stays fixed by the stability policy: ICU's alias,
  the one that supersedes the name. Empty where there is none, which is almost
  everywhere. The other types of alias (``ALERT`` and ``BEL`` for U+0007,
  ``NBSP`` for U+00A0), of which a code point can have several, are in
  :func:`get_char_aliases`.
* ``extended`` -- the formal name where there is one, and otherwise a label that
  names the code point by its type, such as ``<control-0007>``,
  ``<noncharacter-FFFF>`` or ``<unassigned-D7A4>``. Never empty.

Args:
    char: A single character.
    choice: ``unicode`` (the default), ``alias``, or ``extended``.

Returns:
    The chosen name, or an empty string where ICU has none of that kind.

Raises:
    ValueError: If input is not a single character, or choice is not one of the
        three.

Example:
    >>> get_char_name('A')
    'LATIN CAPITAL LETTER A'
    >>> get_char_name('α')
    'GREEK SMALL LETTER ALPHA'
    >>> get_char_name('你')
    'CJK UNIFIED IDEOGRAPH-4F60'
    >>> get_char_name('😀')
    'GRINNING FACE'
    >>> get_char_name('Ƣ', 'alias')
    'LATIN CAPITAL LETTER GHA'
    >>> get_char_name('\x07', 'extended')
    '<control-0007>'

### `get_char_names(char: 'str') -> 'dict[str, str]'`

Get all three of ICU's names for a character.

Args:
    char: A single character.

Returns:
    Dict with the ``unicode``, ``alias`` and ``extended`` names, as
    :func:`get_char_name` returns each.

Raises:
    ValueError: If input is not a single character.

Example:
    >>> names = get_char_names('Ƣ')
    >>> names['unicode'], names['alias']
    ('LATIN CAPITAL LETTER OI', 'LATIN CAPITAL LETTER GHA')

### `is_normalized(text: 'str', form: 'str' = 'NFC') -> 'bool'`

Check if text is already in the specified normalization form.

Args:
    text: Text to check.
    form: Normalization form to check against.

Returns:
    True if text is already normalized.

Example:
    >>> is_normalized('café', 'NFC')
    True
    >>> is_normalized('café', 'NFD')
    False  # if 'é' is composed

### `list_blocks() -> 'list[dict[str, Any]]'`

List all Unicode blocks.

Returns:
    List of dicts with block names and ranges.

Example:
    >>> blocks = list_blocks()
    >>> basic_latin = next(b for b in blocks if b['name'] == 'Basic Latin')
    >>> basic_latin['range']
    'U+0000-U+007F'

### `list_categories() -> 'list[dict[str, str]]'`

List all Unicode general categories.

Returns:
    List of dicts with category code and description.

Example:
    >>> cats = list_categories()
    >>> next(c for c in cats if c['code'] == 'Lu')
    {'code': 'Lu', 'description': 'Letter, uppercase'}

### `normalize(text: 'str', form: 'str' = 'NFC') -> 'str'`

Normalize Unicode text to a standard form.

Args:
    text: Text to normalize.
    form: Normalization form - 'NFC', 'NFD', 'NFKC', or 'NFKD'.
          Defaults to 'NFC'.

Returns:
    Normalized text.

Raises:
    NormalizationError: If form is invalid.

Example:
    >>> # NFC: Canonical composition (default)
    >>> normalize('café')
    'café'
    >>>
    >>> # NFD: Canonical decomposition
    >>> len(normalize('é', 'NFC'))
    1
    >>> len(normalize('é', 'NFD'))
    2
    >>>
    >>> # NFKC/NFKD: Compatibility normalization
    >>> normalize('ﬁ', 'NFKC')  # fi ligature
    'fi'
    >>> normalize('①', 'NFKC')  # circled digit
    '1'

## icukit.unit_surfaces

Curated unit surfaces: the unit forms a language writes that ICU does not.

ICU and CLDR give the unit forms the measure reader inverts, and
:func:`~icukit.icu_abbreviations` lists. A few forms English writes appear in no
English locale's ICU output ("500cc", "185 lbs", "78 rpm"); this module reads a small,
hand-rolled table (``data/unit_surfaces/<language>.tsv``) mapping each to the ICU unit
it names. Only the mapping is curated: the unit, the value, and the expansions stay
ICU's. The same table names the units ICU composes from an SI prefix that are worth
building ("kilovolt"), since ICU composes any prefix onto any unit and some
compositions are false readings ("cc" is ICU's centicentury), and a few currency
surfaces the currency reader does not take from ICU ("Rs" as the Indian rupee).

### `curated_composed_units(language: 'str') -> 'tuple[str, ...]'`

The ICU units composed from an SI prefix that ``language``'s table chooses.

### `curated_currency_surfaces(language: 'str') -> 'tuple[tuple[str, str], ...]'`

``(surface, ISO 4217 code)`` for the curated currency surfaces of ``language``.

English: "Rs" and "Rs." as the Indian rupee (what English text means by them), and
"Rs" as the five rupees ICU itself writes it for (Pakistani, Mauritian, Seychellois,
Sri Lankan, Nepalese).

### `curated_unit_surfaces(language: 'str') -> 'tuple[tuple[str, str], ...]'`

``(surface, ICU unit)`` for the curated unit surfaces of ``language``.

A rate's per form maps to ``per-<unit>`` ("per km²": ``per-square-kilometer``).
Empty for a language with no table.

## icukit.errors

Exception classes for icukit.

### class `AbbreviationError`

Error related to loading or parsing an abbreviation lexicon.

### class `AlphaIndexError`

Error related to alphabetic index operations.

### class `BidiError`

Error related to bidirectional text operations.

### class `BreakRuleLoadError`

Transactional sentence-break rule-set load failure.

#### `BreakRuleLoadError(refusals: 'list[RuleRefusal]')`

Initialize self.  See help(type(self)) for accurate signature.

### class `BreakerError`

Error related to text breaking operations.

### class `CalendarError`

Error related to calendar operations.

### class `CollatorError`

Error related to collation operations.

### class `DateTimeError`

Error related to date/time formatting operations.

### class `DisplayNameError`

Error related to display name operations.

### class `DurationError`

Error related to duration formatting operations.

### class `ExceptionConflictError`

Incompatible exception effects target the same runtime span.

### class `ExceptionLoadError`

Transactional exception-inventory load failure.

#### `ExceptionLoadError(refusals: 'list[RuleRefusal]')`

Initialize self.  See help(type(self)) for accurate signature.

### class `FormatError`

Error related to formatting operations.

### class `ICUKitError`

Base exception for all icukit errors.

### class `IDNAError`

Error related to IDNA encoding/decoding.

### class `LateProtectedSpan`

A protected span arrived after streaming output made it unsafe.

### class `ListFormatError`

Error related to list formatting operations.

### class `LocaleError`

Error related to locale operations.

### class `MeasureError`

Error related to measurement formatting operations.

### class `MessageError`

Error related to message formatting operations.

### class `NormalizationError`

Error related to Unicode normalization.

### class `OverlappingProtectedSpans`

Token-scoped protected spans overlap without one containing the other.

### class `ParseError`

Error related to parsing operations.

### class `PatternError`

Error related to patterns (regex, date format, etc.).

### class `PluralError`

Error related to plural rules operations.

### class `RegionError`

Error related to region operations.

### class `RuleLoadError`

Base class for exception-rule load failures.

### class `RuleRefusal`

One stable, machine-readable exception-rule refusal.

#### `RuleRefusal(rule_id: 'str', reason: 'str', detail: 'str' = '') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `ScriptError`

Error related to script detection operations.

### class `SearchError`

Error related to locale-aware search operations.

### class `SpoofError`

Error related to spoof/confusable detection.

### class `TimezoneError`

Error related to timezone operations.

### class `TransliteratorError`

Error related to transliteration operations.
