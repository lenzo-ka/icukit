# icukit API Reference

Version: 0.4.0

## Root API index

Names exported by `icukit.__all__` (the `from icukit import ...` surface):

- [`__version__`](#root-api-index) — constant, `icukit`
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
- [`DetectorSet`](#icukitdetectors) — class, `icukit.detectors`
- [`ValueDetection`](#icukitdetectors) — class, `icukit.detectors`
- [`DateTimeValue`](#icukitdetectors) — class, `icukit.detectors`
- [`MeasureValue`](#icukitdetectors) — class, `icukit.detectors`
- [`NumberValue`](#icukitdetectors) — class, `icukit.detectors`
- [`RelativeDateValue`](#icukitdetectors) — class, `icukit.detectors`
- [`detect`](#icukitdetectors) — function, `icukit.detectors`
- [`date_detectors`](#icukitdetectors) — function, `icukit.detectors`
- [`number_detectors`](#icukitdetectors) — function, `icukit.detectors`
- [`all_detectors`](#icukitdetectors) — function, `icukit.detectors`
- [`generated_detectors`](#icukitengine) — function, `icukit.engine`
- [`generated_detectors_report`](#icukitengine) — function, `icukit.engine`
- [`detection_to_dict`](#icukitserialize) — function, `icukit.serialize`
- [`detections_to_json`](#icukitserialize) — function, `icukit.serialize`
- [`ABBREVIATION_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`COMPACT_NUMBER_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`DATE_INTERVAL_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`DATE_TIME_SKELETON_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`RELATIVE_DATE_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`SCIENTIFIC_NUMBER_FAMILY`](#icukitengine) — constant, `icukit.engine`
- [`SPELLOUT_NUMBER_FAMILY`](#icukitengine) — constant, `icukit.engine`
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

Post-filter ICU sentence spans using one compiled abbreviation lexicon.

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

Load and compile the language lexicon, or return ``None`` when absent.

Locale variants use their ICU language subtag, making ``en_US`` consume
the packaged ``en`` lexicon while unsupported languages degrade cleanly.

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

#### `AbbreviationExpansion(text: 'str', sense: 'str', cue: 'str | None' = None) -> None`

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

#### `Expansion(value: 'str', sense: 'str', cue: 'str | None' = None) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### class `Pattern`

A productive abbreviation family, named by a typed ``kind``.

A pattern never carries a raw regular expression: the grammar admits only
an enumerated ``kind`` (``single-initial``, ``multi-part-initials``,
``uncased-latin``), and a later compiler owns the boundary semantics.

#### `Pattern(kind: 'str', break_behavior: 'str') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `available_locales() -> 'tuple[str, ...]'`

Return the language codes with a packaged abbreviation lexicon.

### `load_lexicon(language: 'str' = 'en') -> 'AbbreviationLexicon'`

Load the packaged abbreviation lexicon for ``language`` (e.g. ``"en"``).

Raises :class:`~icukit.errors.AbbreviationError` if no lexicon is shipped
for the requested language.

### `load_lexicon_file(path: 'str | Path') -> 'AbbreviationLexicon'`

Load and parse an abbreviation lexicon from an XML file path.

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
sentences, words, lines, or grapheme clusters using ICU's BreakIterator.
Structured span offsets are Python code-point indices into the source text.

Key Features:
    * Locale-aware sentence segmentation
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
words, lines, or grapheme clusters based on locale-specific rules.

Example:
    >>> breaker = Breaker('en')
    >>> list(breaker.iter_sentences('Hello. World.'))
    ['Hello. ', 'World.']
    >>> breaker.break_words('Hello, world!', skip_punctuation=True)
    ['Hello', 'world']

#### `Breaker(locale: 'str' = 'en_US')`

Initialize a Breaker instance.

Args:
    locale: Locale code for language-specific rules (e.g., 'en', 'en_US', 'ja').

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

Return every sentence segment as a structured span.

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

Yield every sentence segment with code-point offsets.

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

### `break_sentence_spans(text: 'str', locale: 'str' = 'en_US') -> 'list[BreakSpan]'`

Return every sentence segment with code-point offsets.

### `break_sentences(text: 'str', locale: 'str' = 'en_US', skip_empty: 'bool' = True) -> 'list[str]'`

Break text into sentences.

Convenience function that creates a Breaker for one-off use.

Args:
    text: The text to segment.
    locale: Locale code for language-specific rules.
    skip_empty: If True, empty sentences are excluded.

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

D1 detectors: invert ICU formatters to find typed values in running text.

A *detector* here wraps the invertible class -- the value kinds where an ICU parser
inverts the formatter (dates, times, datetimes, decimal numbers, currency, percent).
Each accepted match is a :class:`ValueDetection` that carries the full generative
structure of the parse::

    surface  <->  (spec, value, captures)

governed by the invariant ``reformat(spec, value) == surface`` -- which is also the
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

#### `DateDetector(locale: 'str', skeleton: 'str', tz: 'str' = 'GMT') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`



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

A runnable D1 detector.

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

#### `DetectorSet(detectors: 'tuple[Detector, ...]') -> None`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`



#### `names() -> 'tuple[str, ...]'`



#### `with_(*more: 'Detector') -> 'DetectorSet'`

Return a new gang with ``more`` detectors added (deduplicated by type).

#### `without(*types: 'str') -> 'DetectorSet'`

Return a new gang with the named detector types removed.

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



### class `NumberFormatSpec`

The generative recipe for a numeric detection.

``grouping_sizes`` are Known from the formatter (e.g. ``(3,)`` for en_US,
``(2, 3)`` for hi_IN Indian grouping), not read off one value; ``None`` when the
formatter groups by no fixed size. ``min_fraction``/``max_fraction`` are the
formatter's configured fraction-digit bounds.

#### `NumberFormatSpec(locale: 'str', kind: "Literal['decimal', 'currency', 'percent', 'scientific']", currency: 'str | None' = None, min_fraction: 'int | None' = None, max_fraction: 'int | None' = None, grouping_sizes: 'tuple[int, ...] | None' = None) -> None`

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

### `all_detectors(locale: 'str', skeletons: 'Iterable[str]', *, currencies: 'Iterable[str]' = (), flexible: 'bool' = False, abbreviations: 'bool' = False) -> 'DetectorSet'`

Date detectors for ``skeletons`` plus the decimal, percent, and currency detectors.

A convenience composition of :func:`date_detectors` and :func:`number_detectors` for
``locale`` into one gang.

### `date_detectors(locale: 'str', skeletons: 'Iterable[str]', *, flexible: 'bool' = False) -> 'DetectorSet'`

A gang of date detectors for ``locale``, one per skeleton.

``skeletons`` are ICU date-time skeletons (``"yMd"``, ``"yMMMd"``); each becomes a
:class:`DateDetector`. Members are deduplicated by type, so a repeated skeleton is
harmless. A skeleton whose pattern carries an uninvertible field raises (see
:class:`DateDetector`). When ``flexible`` is true, the gang additionally contains
only a :class:`~icukit.recognize.FlexibleTextDateDetector`; it does not add the
flexible numeric-date or other flexible date recognizers.

### `detect(text: 'str', detectors: 'list[Detector] | tuple[Detector, ...]') -> 'list[ValueDetection]'`

Run every detector over ``text`` and return the merged detections.

Detections are returned in a fully deterministic order (start ascending, longer
extent first, then type, then value key) independent of ``detectors`` order.
Detections from different detectors may overlap -- H3 deposits them; resolving
overlap is H4.

Each detector runs its own scan here (multi-pass), so a gang trivially equals the
merge of its members. The single-pass variant §12.5 describes -- one shared scan
with per-member resume cursors and a freshly cleared calendar per (member, start)
attempt -- is a deferred efficiency optimization, not yet built; its equivalence
to this merge is the invariant that variant must preserve.

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

### Constants and type aliases

#### `ABBREVIATION_FAMILY` (constant)

`<icukit.engine.Family>`

#### `COMPACT_NUMBER_FAMILY` (constant)

`<icukit.engine.Family>`

#### `DATE_INTERVAL_FAMILY` (constant)

`<icukit.engine.Family>`

#### `DATE_TIME_SKELETON_FAMILY` (constant)

`<icukit.engine.Family>`

#### `DEFAULT_FAMILIES` (constant)

`(<icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>, <icukit.engine.Family>)`

inverter. Abbreviations use their typed lexicon.

#### `RELATIVE_DATE_FAMILY` (constant)

`<icukit.engine.Family>`

#### `SCIENTIFIC_NUMBER_FAMILY` (constant)

`<icukit.engine.Family>`

#### `SPELLOUT_NUMBER_FAMILY` (constant)

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

### `generated_detectors(locale: 'str', families: 'Iterable[Family]' = (Family(name='abbreviation'), Family(name='date-time-skeleton'), Family(name='date-interval'), Family(name='compact-number'), Family(name='relative-date'), Family(name='scientific-number'), Family(name='spellout-number'))) -> 'DetectorSet'`

Derive all invertible detectors introspectively registered for ``locale``.

### `generated_detectors_report(locale: 'str', families: 'Iterable[Family]' = (Family(name='abbreviation'), Family(name='date-time-skeleton'), Family(name='date-interval'), Family(name='compact-number'), Family(name='relative-date'), Family(name='scientific-number'), Family(name='spellout-number'))) -> 'GenerationReport'`

Derive detectors for ``locale`` and report specs that could not be inverted.

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

### class `FlexibleCompactDetector`

Recognize a flexible number with reflectively derived ICU compact affixes.

#### `FlexibleCompactDetector(locale: 'str', width: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping flexible compact numbers in source order.

### class `FlexibleCurrencyDetector`

Recognize a locale currency symbol before or after a flexible number.

#### `FlexibleCurrencyDetector(locale: 'str', currency: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping flexible currency candidates in source order.

### class `FlexibleCurrencyNameDetector`

Recognize flexible numbers adjacent to reflective spelled currency names.

#### `FlexibleCurrencyNameDetector(locale: 'str', currency: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping spelled-currency candidates in source order.

### class `FlexibleDateDetector`

Recognize flexible numeric dates using a locale's CLDR short-date structure.

The stable ``date:flexible`` type distinguishes recall candidates from strict,
skeleton-specific date detections. Two-digit years retain their observed value;
this detector deposits one maximal candidate rather than expanding a century.

#### `FlexibleDateDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping flexible numeric dates in source order.

### class `FlexibleDateIntervalDetector`

Recognize date/time interval surfaces by inverting ICU DateIntervalFormat recipes.

#### `FlexibleDateIntervalDetector(locale: 'str', skeleton: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping date-interval candidates in source order.

### class `FlexibleFractionDetector`

Recognize ``N/D`` fractions, optionally with a leading whole part ``W N/D``.

The ``fraction:flexible`` type marks recall candidates. Locale digits are reflective;
the fraction slash is the mathematical solidus (``/`` or U+2044), not locale data.
The value is a :class:`NumberValue` whose ``decimal`` is computed with ``Decimal``:
a terminating fraction is exact (``1/2`` -> ``"0.5"``, ``3 1/2`` -> ``"3.5"``); a
non-terminating one is quantized to twelve fractional digits (``1/3`` ->
``"0.333333333333"``). A zero denominator is rejected.

#### `FlexibleFractionDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping flexible fractions in source order.

### class `FlexibleMeasureDetector`

Recognize a flexible number followed by a reflectively derived ICU unit surface.

#### `FlexibleMeasureDetector(locale: 'str', unit: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping flexible measure candidates in source order.

### class `FlexibleNumberDetector`

Recognize flexible decimal-number spellings using locale symbols from CLDR.

#### `FlexibleNumberDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping flexible decimal candidates in source order.

### class `FlexibleOrdinalDetector`

Recognize ordinal numerals (``1st``, ``第21``) using reflective CLDR affixes.

The ``ordinal:flexible`` type marks recall candidates. Ordinal affixes are obtained
reflectively by *forward* formatting: a candidate integer is rendered with every
public ``icu.RuleBasedNumberFormat`` ``ORDINAL`` rule set, and the prefix and suffix
are the non-digit parts around each rendering. No affix is hard-coded, and no fragile
ordinal *parse* is attempted. A surface is accepted only when its affixes match a pair
ICU generates for the parsed value, so ``21th`` is rejected while ``21st`` is not.

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

Return greedy, non-overlapping flexible ordinals in source order.

### class `FlexiblePercentDetector`

Recognize flexible numbers adjacent to the locale's percent symbol.

#### `FlexiblePercentDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping flexible percent candidates in source order.

### class `FlexibleRelativeDateDetector`

Recognize relative dates by inverting locale-relative ICU formatting.

#### `FlexibleRelativeDateDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping relative-date candidates in source order.

### class `FlexibleScientificDetector`

Recognize scientific notation using locale symbols reflected from ICU.

#### `FlexibleScientificDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping scientific numbers in source order.

### class `FlexibleSpelloutDetector`

Recognize canonical ICU spelled-out cardinals derived from locale RBNF data.

A lone token is suppressed only when it is one of the ambiguous unit words obtained
by formatting 0 through 9. Larger lone magnitudes and every multi-token canonical
surface remain eligible for deposit-and-hold alongside other detector candidates.

#### `FlexibleSpelloutDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping spelled-out cardinals in source order.

### class `FlexibleTextDateDetector`

Recognize textual-month dates licensed by CLDR date patterns and symbols.

#### `FlexibleTextDateDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping textual-date candidates in source order.

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
seconds are exactly two digits in 0-59.

#### `FlexibleTimeDetector(locale: 'str') -> 'None'`

Initialize self.  See help(type(self)) for accurate signature.

#### `detect(text: 'str') -> 'list[ValueDetection]'`

Return greedy, non-overlapping flexible clock times in source order.

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

See ``design/H4-resolution/design.md``. The detectors DEPOSIT every candidate they find --
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

### class `Resolution`

The weighed reading of a universe of detections.

``best`` is the maximum-weight non-overlapping sequence in source order. ``covers`` is the
n-best ordering of covers by descending score, with ``covers[0] == best``. ``margin`` is the
score gap between the top two covers; ``ambiguous`` is true when that gap is below the
refusal threshold, meaning the resolver declines to commit between them.

#### `Resolution(best: 'tuple[ValueDetection, ...]', covers: 'tuple[tuple[ValueDetection, ...], ...]', margin: 'int', ambiguous: 'bool') -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `resolve(detections: 'list[ValueDetection] | tuple[ValueDetection, ...]', *, n: 'int' = 8, epsilon: 'int' = 1.0) -> 'Resolution'`

Weigh a universe of (possibly overlapping) detections into a :class:`Resolution`.

Returns the maximum-weight non-overlapping ``best`` sequence, the ``n``-best ordering of
covers, and an ``ambiguous`` flag when the top two covers are within ``epsilon``.

### `resolve_text(text: 'str', detectors: 'list[Detector] | tuple[Detector, ...]', *, n: 'int' = 8, epsilon: 'int' = 1.0) -> 'Resolution'`

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

## icukit.serialize

recognition-output serializer — converts typed ValueDetection candidates to plain JSON;
no external deps; reusable by downstream consumers.

### `detection_to_dict(detection: 'ValueDetection') -> 'dict'`

Convert one typed detection to an ordered, plain JSON-native dictionary.

### `detections_to_json(detections) -> 'list[dict]'`

Convert typed detections to a list containing only JSON-native values.

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

Args:
    text: String to check.

Returns:
    Dict with check results:
    - 'flags': Raw check result flags
    - 'is_suspicious': True if any issues detected
    - 'mixed_script': Contains mixed scripts
    - 'restriction_level': Restriction level issue
    - 'invisible': Contains invisible characters
    - 'mixed_numbers': Contains mixed number systems

Example:
    >>> result = check_string("pаypal")  # Cyrillic 'а'
    >>> result['is_suspicious']
    True
    >>> result['mixed_script']
    True

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

## icukit.unicode

Unicode text normalization and character properties.

Normalize text to standard Unicode forms (NFC, NFD, NFKC, NFKD) and
query Unicode character properties like names and categories.

Key Features:
    * Normalize text to NFC, NFD, NFKC, NFKD forms
    * Get Unicode character names
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

        >>> from icukit import get_char_name, get_char_category
        >>>
        >>> get_char_name('α')
        'GREEK SMALL LETTER ALPHA'
        >>> get_char_name('😀')
        'GRINNING FACE'
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

### `decode_unicode_escapes(text: 'str') -> 'str'`

Decode Unicode escape sequences in text.

Recognizes ``\uXXXX``, ``\UXXXXXXXX``, ``\xXX``, and ``U+XXXX`` through
``U+XXXXXX`` notation. Invalid Python-style escapes leave the post-``U+``
conversion text unchanged.

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
    Dict with character info: codepoint, name, category, script, etc.

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

### `get_char_name(char: 'str') -> 'str'`

Get the Unicode name of a character.

Args:
    char: A single character.

Returns:
    Unicode character name.

Raises:
    ValueError: If input is not a single character.

Example:
    >>> get_char_name('A')
    'LATIN CAPITAL LETTER A'
    >>> get_char_name('α')
    'GREEK SMALL LETTER ALPHA'
    >>> get_char_name('你')
    'CJK UNIFIED IDEOGRAPH-4F60'
    >>> get_char_name('😀')
    'GRINNING FACE'

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

## icukit.errors

Exception classes for icukit.

### class `AbbreviationError`

Error related to loading or parsing an abbreviation lexicon.

### class `AlphaIndexError`

Error related to alphabetic index operations.

### class `BidiError`

Error related to bidirectional text operations.

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
