"""Resolve a universe of overlapping detections into a best non-overlapping sequence."""

from icukit.abbreviation_recognize import AbbreviationDetector, AbbreviationExpansion
from icukit.detectors import (
    Capture,
    NumberFormatSpec,
    NumberValue,
    ValueDetection,
    all_detectors,
)
from icukit.resolve import Resolution, resolve, resolve_text, weight


def _det(start, end, type_, captures=()):
    caps = tuple(Capture(name, start, end, "x", form="numeric") for name in captures)
    return ValueDetection(
        text="x" * (end - start),
        start=start,
        end=end,
        type=type_,
        value=NumberValue(decimal="0"),
        captures=caps,
        spec=NumberFormatSpec("und", "decimal"),
    )


def test_weight_is_length_times_specificity():
    # length 8, one capture -> 8 * (1 + 1) = 16
    assert weight(_det(0, 8, "date:yMd", captures=("y",))) == 16
    # a longer, richer match outscores a short bare one
    long_rich = _det(0, 8, "date:yMd", captures=("y", "M", "d"))
    short_bare = _det(6, 8, "number:decimal", captures=("integer",))
    assert weight(long_rich) > weight(short_bare)


def test_best_cover_prefers_the_long_specific_reading_over_fragments():
    date = _det(0, 8, "date:yMd", captures=("y", "M", "d"))
    frags = [
        _det(0, 1, "number:decimal", captures=("integer",)),
        _det(2, 3, "number:decimal", captures=("integer",)),
        _det(6, 8, "number:decimal", captures=("integer",)),
    ]
    result = resolve([date, *frags])
    assert result.best == (date,)
    assert result.covers[0] == result.best
    assert not result.ambiguous


def test_ordering_is_descending_and_collapses_to_one_best():
    date = _det(0, 8, "date:yMd", captures=("y", "M", "d"))
    frags = [_det(0, 1, "number:decimal", captures=("integer",))]
    result = resolve([date, *frags], n=8)
    scores = [sum(weight(d) for d in cover) for cover in result.covers]
    assert scores == sorted(scores, reverse=True)
    assert result.covers[0] == result.best


def test_equal_weight_overlap_is_reported_ambiguous():
    # Two readings of the same span, same structure -> a genuine tie the resolver will not break.
    a = _det(0, 4, "number:decimal", captures=("integer",))
    b = _det(0, 4, "number:percent", captures=("integer",))
    result = resolve([a, b])
    assert result.margin == 0
    assert result.ambiguous
    assert len(result.best) == 1  # one of them, not both (they overlap)


def test_epsilon_accepts_a_fractional_tolerance():
    """The tolerance is a float, and the signatures now say so.

    ``DEFAULT_EPSILON`` has always been ``1.0`` while both parameters were
    annotated ``int``, so a caller reading the signature would have believed a
    fractional tolerance was out of bounds. It is not, and the fraction is doing
    work: weights are integral, so a threshold at ``2.5`` calls a margin of two
    too close and a margin of three decisive, and no integer sits where that
    boundary needs to be -- ``2`` admits neither and ``3`` admits both.
    """
    richer = _det(0, 1, "number:decimal", captures=("integer", "sign"))
    barer = _det(0, 1, "number:percent")
    candidates = [richer, barer]

    assert resolve(candidates).margin == 2
    assert not resolve(candidates).ambiguous  # 2 is outside the default tolerance of 1.0

    inside = resolve(candidates, epsilon=2.5)
    assert inside.ambiguous
    assert inside.best == (richer,)

    assert not resolve(candidates, epsilon=2).ambiguous  # the integer below excludes it
    assert resolve(candidates, epsilon=3).ambiguous  # the integer above admits a margin of 3 too


def test_content_identical_detections_do_not_manufacture_ambiguity():
    # The same detection deposited twice must not read as two competing covers.
    a = _det(0, 4, "number:decimal", captures=("integer",))
    result = resolve([a, a])
    assert result.best == (a,)
    assert not result.ambiguous


def test_abbreviation_expansions_remain_one_resolver_candidate():
    detections = AbbreviationDetector("en").detect("Dr.")
    result = resolve(detections)

    assert len(detections) == 1
    assert result.best == (detections[0],)
    assert detections[0]["value"].expansions == (
        AbbreviationExpansion("Doctor", "title", "precedes-name"),
        AbbreviationExpansion("Drive", "thoroughfare", "address"),
    )


def test_equal_span_ties_resolve_deterministically():
    # Two equal-weight readings of the same span: the winner must not depend on input order.
    a = _det(0, 4, "number:decimal", captures=("integer",))
    b = _det(0, 4, "number:percent", captures=("integer",))
    forward = resolve([a, b]).best
    backward = resolve([b, a]).best
    assert forward == backward


def test_empty_universe_resolves_to_nothing():
    result = resolve([])
    assert isinstance(result, Resolution)
    assert result.best == ()
    assert not result.ambiguous


def test_resolve_text_on_real_mixed_content():
    gang = all_detectors("en_US", ["yMd"], currencies=["USD"])
    result = resolve_text("on 1/3/2026 we paid $1,234.50", gang.detectors)

    # the best sequence is the two real entities, with every digit fragment dropped
    assert [(d["type"], d["text"]) for d in result.best] == [
        ("date:yMd", "1/3/2026"),
        ("number:currency:USD", "$1,234.50"),
    ]
    assert not result.ambiguous
