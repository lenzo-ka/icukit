from __future__ import annotations

import re
from inspect import signature
from pathlib import Path

import pytest

import icukit.sentence_override as sentence_override_module
from icukit import BreakRuleLoadError, CartletModelRef, SentenceOverride

MODEL_PATH = (
    Path(sentence_override_module.__file__).with_name("data")
    / "break_rules"
    / "en"
    / "sentence-tn-cart.json.gz"
)
MODEL_DIGEST = "sha256:a390141818133a9fe7cbaa2b18a409d367c50996b93f9167851395a90e4eef6d"
REAL_MODEL_PATH = MODEL_PATH.with_name("sentence-real-cart.json.gz")
REAL_MODEL_DIGEST = "sha256:be9fa4df8bee3f1fe886f28a40f706a28732091ee9975675aa52ba7c03de3366"


def _bare_cartlet() -> SentenceOverride:
    """Load the model without the named deployment base's exception list."""
    return SentenceOverride(base=CartletModelRef(MODEL_PATH, MODEL_DIGEST, name="en-tn-cart@1"))


@pytest.mark.parametrize("locale", ["en", "en_US", "en_GB", "en_Latn_US", "en-Latn-GB"])
def test_english_locale_default_uses_shipped_exceptions_without_cartlet(locale: str) -> None:
    default = SentenceOverride(locale)
    decisions = default.decide("Mr. Smith arrived. Next.")

    assert signature(SentenceOverride).parameters["base"].default is None
    assert default.identity != SentenceOverride(locale, base="none").identity
    assert default.base is None
    assert (decisions[0]["decision"], decisions[0]["layer"], decisions[0]["id"]) == (
        "no-break",
        "exceptions",
        "abbreviation:Mr.",
    )
    assert all(item["layer"] == "icu" for item in decisions[1:])
    assert all(item["layer"] != "model" for item in decisions)


@pytest.mark.parametrize("base", ["en-tn@1", "en-tn-cart@1", "en-real-cart@1"])
def test_named_english_bases_still_load_shipped_exceptions(base: str) -> None:
    named = SentenceOverride("en_US", base=base)
    decisions = named.decide("Mr. Smith arrived. Next.")

    assert (decisions[0]["decision"], decisions[0]["layer"], decisions[0]["id"]) == (
        "no-break",
        "exceptions",
        "abbreviation:Mr.",
    )
    expected_layer = "rules" if base == "en-tn@1" else "model"
    assert expected_layer in {item["layer"] for item in decisions[1:]}


@pytest.mark.parametrize("locale", ["en_US_POSIX", "en_US_POSIX_FOO", "en_POSIX"])
def test_english_posix_variant_default_is_plain_icu_and_learned_bases_refuse(
    locale: str,
) -> None:
    default = SentenceOverride(locale)
    plain = SentenceOverride(locale, base="none")

    assert default.base is None
    assert default.identity == plain.identity
    assert default.decide("Mr. Smith arrived. Next.") == plain.decide("Mr. Smith arrived. Next.")
    for base in ("en-tn-cart@1", "en-real-cart@1", "en-tn@1"):
        with pytest.raises(BreakRuleLoadError, match="IDENTITY_MISMATCH"):
            SentenceOverride(locale, base=base)


def test_named_model_refuses_runtime_icu_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(sentence_override_module.icu, "ICU_VERSION", "0.0")

    with pytest.raises(BreakRuleLoadError, match="IDENTITY_MISMATCH"):
        SentenceOverride("en_GB", base="en-tn-cart@1")

    with pytest.raises(BreakRuleLoadError, match="IDENTITY_MISMATCH"):
        SentenceOverride("en_GB", base="en-real-cart@1")


def test_real_text_model_is_version_bound_and_uses_reduced_flat_schema(monkeypatch) -> None:
    override = SentenceOverride("en_US", base="en-real-cart@1")

    assert override.base.ref.path == REAL_MODEL_PATH
    assert override.base.ref.digest == REAL_MODEL_DIGEST
    assert override.base.feature_names == (
        "ws.before@-3",
        "text@run-1",
        "shape.cased@1",
        "sentence_break.first@1",
        "script@c-6",
        "sentence_break@c-4",
        "general_category@c-4",
        "general_category@c-3",
    )

    def refuse_cartlet_path(*args, **kwargs):
        raise AssertionError("the compiled real-text tree must use the flat evaluator")

    monkeypatch.setattr(override.base.model, "predict_path", refuse_cartlet_path)
    decisions = override.decide("Hon. Alice spoke. Next item.")
    assert [(item["offset"], item["layer"]) for item in decisions] == [
        (5, "exceptions"),
        (18, "model"),
        (28, "model"),
    ]
    assert all(
        item["id"].startswith("en-real-cart@1#leaf:")
        for item in decisions
        if item["layer"] == "model"
    )


def test_real_text_model_refuses_unknown_deployment_version(monkeypatch) -> None:
    from cartlet import DecisionTree

    original = DecisionTree.load_model

    def stale(self, *args, **kwargs):
        document = original(self, *args, **kwargs)
        document["metadata"]["deployment"]["version"] = 0
        return document

    monkeypatch.setattr(DecisionTree, "load_model", stale)
    with pytest.raises(BreakRuleLoadError, match="MODEL_VERSION_MISMATCH"):
        SentenceOverride("en_US", base="en-real-cart@1")


def test_default_never_loads_or_consults_cartlet_in_whole_text_or_stream(monkeypatch) -> None:
    def refused(*args, **kwargs):
        raise AssertionError("the English locale default must not load cartlet")

    monkeypatch.setattr(sentence_override_module, "_load_cartlet_model", refused)
    text = "He met Mr. Smith today. He left."
    default = SentenceOverride("en_US")
    decisions = default.decide(text)
    stream = default.stream()
    streamed = stream.feed("He met Mr. S")
    streamed += stream.feed("mith today. He left.")
    streamed += stream.close()

    assert default.base is None
    assert default.inventories
    assert all(
        rule.variant == "exact" for inventory in default.inventories for rule in inventory._rules
    )
    assert all(item["layer"] != "model" for item in decisions)
    assert streamed == decisions


def test_non_english_locale_default_is_plain_icu() -> None:
    text = "M. Dupont est arrivé. Ensuite, il est parti."
    default = SentenceOverride("fr_FR")
    plain = SentenceOverride("fr_FR", base="none")

    assert default.identity == plain.identity
    assert default.decide(text) == plain.decide(text)
    assert default.spans(text) == plain.spans(text)


@pytest.mark.parametrize("locale", ["en_US", "fr_FR"])
def test_stream_uses_locale_default(locale: str) -> None:
    text = "Mr. Smith arrived. Next."
    default = SentenceOverride(locale)

    default_stream = default.stream()
    streamed = default_stream.feed("Mr. S") + default_stream.feed("mith arrived. Next.")
    streamed += default_stream.close()

    assert streamed == default.decide(text)
    if locale == "fr_FR":
        assert streamed == SentenceOverride(locale, base="none").decide(text)


def test_cartlet_model_ref_and_named_base_are_digest_bound() -> None:
    named = SentenceOverride(base="en-tn-cart@1")
    explicit = SentenceOverride(
        base=CartletModelRef(MODEL_PATH, MODEL_DIGEST, name="explicit-cart")
    )

    named_decisions = named.decide("Hello. Next.")
    explicit_decisions = explicit.decide("Hello. Next.")
    assert [item["decision"] for item in explicit_decisions] == [
        item["decision"] for item in named_decisions
    ]
    assert all(item["layer"] == "model" for item in explicit_decisions)
    assert all(str(item["id"]).startswith("explicit-cart#leaf:") for item in explicit_decisions)
    assert all(str(item["id"]).startswith("en-tn-cart@1#leaf:") for item in named_decisions)

    with pytest.raises(BreakRuleLoadError, match="DIGEST_MISMATCH"):
        SentenceOverride(base=CartletModelRef(MODEL_PATH, "0" * 64))


def test_cartlet_leaf_id_is_root_relative_path() -> None:
    decisions = SentenceOverride(base="en-tn-cart@1").decide("Hello. Next.")

    assert all(re.fullmatch(r"en-tn-cart@1#leaf:[LR]+", item["id"]) for item in decisions)
    assert {item["offset"]: (item["id"], item["decision"]) for item in decisions} == {
        7: ("en-tn-cart@1#leaf:RRRRRRRRLR", "break"),
        12: ("en-tn-cart@1#leaf:RRRRRRRRR", "no-break"),
    }


def test_cartlet_model_identity_refuses_mismatch() -> None:
    identity = dict(sentence_override_module._CARTLET_IDENTITY)
    identity["unicode"] = "0.0"
    with pytest.raises(BreakRuleLoadError, match="IDENTITY_MISMATCH"):
        SentenceOverride(base=CartletModelRef(MODEL_PATH, MODEL_DIGEST, identity=identity))


def test_cartlet_lazy_decision_matches_close_and_waits_for_unseen_token() -> None:
    override = _bare_cartlet()
    text = "Mr. Smith arrived. Next."
    stream = override.stream()

    assert stream.feed("Mr. S") == []
    assert next(item for item in stream.pending() if item["offset"] == 4)["waiting_on"] == ("model")
    streamed = stream.feed("mith arrived. N")
    streamed += stream.feed("ext.")
    streamed += stream.close()

    assert streamed == override.decide(text)
    assert stream.pending() == []


def test_cartlet_traverses_lazy_sequence_only_by_len_and_getitem(monkeypatch) -> None:
    class GuardedVector(sentence_override_module._CartletFeatureVector):
        def __iter__(self):
            raise AssertionError("cartlet iterated the lazy feature vector")

        def __contains__(self, value):
            raise AssertionError("cartlet searched the lazy feature vector")

        def count(self, value):
            raise AssertionError("cartlet counted the lazy feature vector")

        def index(self, value, start=0, stop=None):
            raise AssertionError("cartlet searched the lazy feature vector")

    monkeypatch.setattr(sentence_override_module, "_CartletFeatureVector", GuardedVector)
    override = _bare_cartlet()

    def refuse_predict(*args, **kwargs):
        raise AssertionError("icukit must use cartlet.predict_path for attribution")

    monkeypatch.setattr(override.base.model, "predict", refuse_predict)
    decisions = override.decide("Mr. Smith arrived.")
    assert decisions[0]["layer"] == "model"
    assert str(decisions[0]["id"]).startswith("en-tn-cart@1#leaf:")


def test_sentence_override_tokenization_work_scales_linearly(monkeypatch) -> None:
    original = sentence_override_module.tokens
    token_records = 0

    def counted(*args, **kwargs):
        nonlocal token_records
        result = original(*args, **kwargs)
        token_records += len(result)
        return result

    monkeypatch.setattr(sentence_override_module, "tokens", counted)
    override = _bare_cartlet()
    sentence = "Alpha beta gamma. "

    override.decide(sentence * 16)
    short_work = token_records
    token_records = 0
    override.decide(sentence * 128)
    long_work = token_records

    assert long_work <= short_work * 10


def test_cartlet_closed_vector_has_explicit_values_at_every_position(monkeypatch) -> None:
    override = SentenceOverride(base="en-tn-cart@1")
    original = override.base.model.predict_path

    def inspect_vector(vector):
        assert all(vector[index] is not None for index in range(len(vector)))
        return original(vector)

    monkeypatch.setattr(override.base.model, "predict_path", inspect_vector)
    assert override.decide("Mr. Smith arrived.")


def test_cartlet_incremental_unseen_feature_raises_feature_not_yet(monkeypatch) -> None:
    override = _bare_cartlet()
    original = override.base.model.predict_path
    raised = False

    def observe_feature_not_yet(vector):
        nonlocal raised
        try:
            return original(vector)
        except sentence_override_module._FeatureNotYet:
            raised = True
            raise

    monkeypatch.setattr(override.base.model, "predict_path", observe_feature_not_yet)
    stream = override.stream()
    assert stream.feed("Mr. S") == []
    assert raised
    assert next(item for item in stream.pending() if item["offset"] == 4)["waiting_on"] == "model"
