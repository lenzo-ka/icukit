from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

import icukit.sentence_override as sentence_override_module
from icukit import BreakRuleLoadError, CartletModelRef, SentenceOverride

requires_cartlet = pytest.mark.skipif(
    importlib.util.find_spec("cartlet") is None,
    reason="cartlet sentence models require the optional cartlet extra",
)

MODEL_PATH = (
    Path(sentence_override_module.__file__).with_name("data")
    / "break_rules"
    / "en"
    / "sentence-tn-cart.json.gz"
)
MODEL_DIGEST = "sha256:662a0def1a7fa8e6cba3da98ea9b1df54d812eb86c3b882e62d248961a4c8f3e"


@requires_cartlet
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
    assert all(item["id"] == "explicit-cart" for item in explicit_decisions)

    with pytest.raises(BreakRuleLoadError, match="DIGEST_MISMATCH"):
        SentenceOverride(base=CartletModelRef(MODEL_PATH, "0" * 64))


@requires_cartlet
def test_cartlet_model_identity_refuses_mismatch() -> None:
    identity = dict(sentence_override_module._CARTLET_IDENTITY)
    identity["unicode"] = "0.0"
    with pytest.raises(BreakRuleLoadError, match="IDENTITY_MISMATCH"):
        SentenceOverride(base=CartletModelRef(MODEL_PATH, MODEL_DIGEST, identity=identity))


@requires_cartlet
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


@requires_cartlet
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
    decisions = SentenceOverride(base="en-tn-cart@1").decide("Mr. Smith arrived.")
    assert decisions[0]["layer"] == "model"


def test_cartlet_extra_is_imported_only_when_model_path_is_used(monkeypatch) -> None:
    assert SentenceOverride().decide("Hello.")
    monkeypatch.setitem(sys.modules, "cartlet", None)
    with pytest.raises(ImportError, match=r"optional dependency.*icukit\[cartlet\]"):
        SentenceOverride(base="en-tn-cart@1")
