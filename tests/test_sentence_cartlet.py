from __future__ import annotations

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


@pytest.mark.parametrize("locale", ["en", "en_US", "en_GB", "en_Latn_US", "en-Latn-GB"])
def test_english_locale_default_is_named_cartlet_model(locale: str) -> None:
    default = SentenceOverride(locale)
    decisions = default.decide("Mr. Smith arrived. Next.")

    assert signature(SentenceOverride).parameters["base"].default is None
    assert default.identity != SentenceOverride(locale, base="none").identity
    assert default.base.ref.name == "en-tn-cart@1"
    assert all(item["layer"] == "model" for item in decisions)
    assert all(str(item["id"]).startswith("en-tn-cart@1#leaf:") for item in decisions)


def test_default_identity_matches_explicit_named_model_for_canonical_locale() -> None:
    assert SentenceOverride().identity == SentenceOverride(base="en-tn-cart@1").identity


def test_non_english_locale_default_is_plain_icu() -> None:
    text = "M. Dupont est arrivé. Ensuite, il est parti."
    default = SentenceOverride("fr_FR")
    plain = SentenceOverride("fr_FR", base="none")

    assert default.identity == plain.identity
    assert default.decide(text) == plain.decide(text)
    assert default.spans(text) == plain.spans(text)


@pytest.mark.parametrize(
    ("locale", "base"),
    [("en_US", "en-tn-cart@1"), ("fr_FR", "none")],
)
def test_stream_uses_resolved_locale_default(locale: str, base: str) -> None:
    text = "Mr. Smith arrived. Next."
    default = SentenceOverride(locale)
    explicit = SentenceOverride(locale, base=base)

    default_stream = default.stream()
    explicit_stream = explicit.stream()
    streamed = default_stream.feed("Mr. S") + default_stream.feed("mith arrived. Next.")
    streamed += default_stream.close()
    explicit_decisions = explicit_stream.feed(text) + explicit_stream.close()

    assert streamed == default.decide(text)
    assert streamed == explicit_decisions


def test_cartlet_model_ref_and_named_base_are_digest_bound() -> None:
    named = SentenceOverride(base="en-tn-cart@1")
    explicit = SentenceOverride(
        base=CartletModelRef(MODEL_PATH, MODEL_DIGEST, name="explicit-cart")
    )

    named_decisions = named.decide("Mr. Smith arrived.")
    explicit_decisions = explicit.decide("Mr. Smith arrived.")
    assert [item["decision"] for item in explicit_decisions] == [
        item["decision"] for item in named_decisions
    ]
    assert all(item["layer"] == "model" for item in explicit_decisions)
    assert all(str(item["id"]).startswith("explicit-cart#leaf:") for item in explicit_decisions)
    assert all(str(item["id"]).startswith("en-tn-cart@1#leaf:") for item in named_decisions)

    with pytest.raises(BreakRuleLoadError, match="DIGEST_MISMATCH"):
        SentenceOverride(base=CartletModelRef(MODEL_PATH, "0" * 64))


def test_cartlet_model_identity_refuses_mismatch() -> None:
    identity = dict(sentence_override_module._CARTLET_IDENTITY)
    identity["unicode"] = "0.0"
    with pytest.raises(BreakRuleLoadError, match="IDENTITY_MISMATCH"):
        SentenceOverride(base=CartletModelRef(MODEL_PATH, MODEL_DIGEST, identity=identity))


def test_cartlet_lazy_decision_matches_close_and_waits_for_unseen_token() -> None:
    override = SentenceOverride(base="en-tn-cart@1")
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
    override = SentenceOverride(base="en-tn-cart@1")

    def refuse_predict(*args, **kwargs):
        raise AssertionError("icukit must use cartlet.predict_path for attribution")

    monkeypatch.setattr(override.base.model, "predict", refuse_predict)
    decisions = override.decide("Mr. Smith arrived.")
    assert decisions[0]["layer"] == "model"
    assert str(decisions[0]["id"]).startswith("en-tn-cart@1#leaf:")


def test_cartlet_closed_vector_has_explicit_values_at_every_position(monkeypatch) -> None:
    override = SentenceOverride(base="en-tn-cart@1")
    original = override.base.model.predict_path

    def inspect_vector(vector):
        assert all(vector[index] is not None for index in range(len(vector)))
        return original(vector)

    monkeypatch.setattr(override.base.model, "predict_path", inspect_vector)
    assert override.decide("Mr. Smith arrived.")


def test_cartlet_incremental_unseen_feature_raises_feature_not_yet(monkeypatch) -> None:
    override = SentenceOverride(base="en-tn-cart@1")
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
