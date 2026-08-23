"""Discriminating tests for the H1 tiergraph text example.

Skipped entirely on Python < 3.12 / when tiergraph is absent (the example is a >= 3.12
dev-only integration). Witnesses avoid non-discriminating invariants: offsets are
asserted as explicit integers and token content, never via ``text[start:end] == surface``
or bare reconstruction, both of which pass on buggy offsets.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("tiergraph", reason="H1 example requires tiergraph (Python >= 3.12)")

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "examples" / "tiergraph_text.py"
sys.path.insert(0, str(REPO_ROOT))

from tiergraph import QualifiedName, dumps, loads  # noqa: E402
from tiergraph.semiring import COUNTING  # noqa: E402

from examples.tiergraph_text import (  # noqa: E402
    NS,
    build_graph,
    detect_dates,
)


def qn(local: str) -> QualifiedName:
    return QualifiedName(NS, local)


def _members(graph, rel_local: str, span_local: str) -> dict[int, frozenset[int]]:
    """Read {span_index: atoms} back from serialized membership edges only."""
    rel, span_tier, atom = qn(rel_local), qn(span_local), qn("atom")
    out: dict[int, set[int]] = {}
    for r in graph.relations:
        if r.declaration == rel and r.left.tier == atom and r.right.tier == span_tier:
            out.setdefault(r.right.index, set()).add(r.left.index)
    return {k: frozenset(v) for k, v in out.items()}


def _crossings(dates, words) -> list[tuple[frozenset[int], frozenset[int]]]:
    pairs = []
    for dm in dates.values():
        for wm in words.values():
            if (dm & wm) and not (dm <= wm) and not (wm <= dm):
                pairs.append((dm, wm))
    return pairs


def _count_via_semiring(n: int) -> int:
    acc = COUNTING.zero
    for _ in range(n):
        acc = COUNTING.add(acc, COUNTING.one)
    return acc


def _atom_surfaces(graph) -> list[str]:
    tier = next(t for t in graph.tiers if t.declaration.name == qn("atom"))
    return [item.attributes[0].lexical for item in tier.items]


def _roundtrip(src: str, locale: str = "en_US", pattern: str = "M/d/yyyy"):
    return loads(dumps(build_graph(src, locale, pattern)))


# --------------------------------------------------------------- detector extents


def test_detector_extents_explicit():
    assert [(d.start, d.end) for d in detect_dates("Meet 1/3/2026pm", "en_US", "M/d/yyyy")] == [
        (5, 13)
    ]
    assert [(d.start, d.end) for d in detect_dates("Meet 1/3/2026 pm", "en_US", "M/d/yyyy")] == [
        (5, 13)
    ]
    # The permissive " 3.5" parse is rejected by exact-reformat; only "3.5" [4,7) survives.
    assert [(d.start, d.end) for d in detect_dates("due 3.5.2026 ok", "en_US", "M.d")] == [(4, 7)]


def test_astral_offsets_explicit():
    # 👍 is one grapheme but two UTF-16 units; a leak would shift the date off [3,11).
    src = "A👍 1/3/2026pm"
    assert [(d.start, d.end) for d in detect_dates(src, "en_US", "M/d/yyyy")] == [(3, 11)]
    g = _roundtrip(src)
    assert _atom_surfaces(g) == list("A👍 1/3/2026pm")
    assert _members(g, "atom-in-date", "formatted-date") == {
        0: frozenset({3, 4, 5, 6, 7, 8, 9, 10})
    }
    words = _members(g, "atom-in-word-break", "word-break")
    assert words[7] == frozenset({7, 8, 9, 10, 11, 12})  # "2026pm" glued token


# ------------------------------------------------------------- crossing / nesting


def test_crossing_headline():
    g = _roundtrip("Meet 1/3/2026pm")
    dates = _members(g, "atom-in-date", "formatted-date")
    words = _members(g, "atom-in-word-break", "word-break")
    assert dates == {0: frozenset({5, 6, 7, 8, 9, 10, 11, 12})}
    pairs = _crossings(dates, words)
    assert len(pairs) == 1
    dm, wm = pairs[0]
    assert dm == frozenset({5, 6, 7, 8, 9, 10, 11, 12})
    assert wm == frozenset({9, 10, 11, 12, 13, 14})  # "2026pm"
    assert dm & wm == frozenset({9, 10, 11, 12})  # genuine overlap
    assert not (dm <= wm) and not (wm <= dm)  # neither contains the other
    assert _count_via_semiring(len(pairs)) == 1


def test_nesting_control():
    g = _roundtrip("Meet 1/3/2026 pm")
    dates = _members(g, "atom-in-date", "formatted-date")
    words = _members(g, "atom-in-word-break", "word-break")
    assert _count_via_semiring(len(_crossings(dates, words))) == 0


# --------------------------------------------------- C4: edge uniqueness + count


def test_edge_uniqueness_and_exact_coverage():
    g = _roundtrip("A👍 1/3/2026pm")
    tuples = [
        (
            r.declaration.local_name,
            r.left.tier.local_name,
            r.left.index,
            r.right.tier.local_name,
            r.right.index,
        )
        for r in g.relations
    ]
    # No duplicate edges (set conversion would hide a producer that doubles them).
    assert len(tuples) == len(set(tuples))
    # Exact per-relation counts: one edge per covered atom.
    by_rel: dict[str, int] = {}
    for t in tuples:
        by_rel[t[0]] = by_rel.get(t[0], 0) + 1
    assert by_rel == {"atom-in-sentence": 13, "atom-in-word-break": 13, "atom-in-date": 8}


# --------------------------------------------- C5: mutation catches producer defect


def test_mutation_of_product_breaks_crossing():
    """Oracle fixed; mutate the PRODUCED graph and prove the crossing test reacts."""
    g = _roundtrip("Meet 1/3/2026pm")
    dates = _members(g, "atom-in-date", "formatted-date")
    words = _members(g, "atom-in-word-break", "word-break")
    assert len(_crossings(dates, words)) == 1  # oracle

    # Drop the two date atoms that lie outside the word -> date becomes a subset (nests).
    shrunk = {0: dates[0] - {5, 6, 7, 8}}
    assert len(_crossings(shrunk, words)) == 0
    # Widen the word to swallow the date -> also nests.
    swollen = {k: v | dates[0] for k, v in words.items()}
    assert len(_crossings(dates, swollen)) == 0


# ------------------------------------------------------------ round-trip from wire


@pytest.mark.parametrize(
    "src",
    [
        "",
        "no date here",
        "Meet 1/3/2026pm",
        "A👍 1/3/2026pm",
        "é",
        "🇬🇧 flag",
        "👨‍👩‍👧 family",
        "世界 2026",
    ],
)
def test_roundtrip_from_wire(src):
    g = _roundtrip(src)
    assert "".join(_atom_surfaces(g)) == src


def test_decomposed_grapheme_is_one_atom():
    # "e" + combining acute: two code points, ONE grapheme -> proves grapheme atoms,
    # not code-point atoms (a precomposed "é" would prove nothing).
    g = _roundtrip("é")
    surfaces = _atom_surfaces(g)
    assert surfaces == ["é"]
    assert len(surfaces[0]) == 2  # two code points in one atom


# ------------------------------------------------------- canonical-only acceptance


def test_canonical_only_scan_no_leading_space_dup():
    assert [(d.start, d.end) for d in detect_dates("Meet 1/3/2026pm", "en_US", "M/d/yyyy")] == [
        (5, 13)
    ]


def test_suggested_range_falsifier():
    # PLAN's original figure must stay unproven: no strict hit for either hyphen.
    for dash in ["-", "–"]:
        src = f"Jan 3{dash}5, 2026"
        assert detect_dates(src, "en_US", "MMM d, yyyy") == []


# ---------------------------------------------------------------- wire contract


def test_wire_contract():
    graph = build_graph("Meet 1/3/2026pm", "en_US", "M/d/yyyy")
    j = dumps(graph)
    assert j.endswith("\n")
    data = json.loads(j)
    # canonical: sorted keys + 2-space indent (re-dump matches)
    assert json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n" == j
    # tier order is atom, sentence, word-break, formatted-date
    order = [tier.declaration.name.local_name for tier in graph.tiers]
    assert order == ["atom", "sentence", "word-break", "formatted-date"]
    # The integration installs tiergraph main unpinned. Assert its current canonical
    # spelling is deterministic without pinning a particular wire-format version.
    assert dumps(loads(j)) == j
    assert loads(j) == graph


# ------------------------------------------------------------------ CLI behavior


def _run(args, stdin: str = ""):
    pythonpath = os.environ.get("PYTHONPATH")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(filter(None, (str(REPO_ROOT), pythonpath)))
    return subprocess.run(
        [sys.executable, str(EXAMPLE), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )


def test_cli_no_date_is_empty_success():
    r = _run(["no date here"])
    assert r.returncode == 0
    graph = loads(r.stdout)
    date_tier = next(tier for tier in graph.tiers if tier.declaration.name == qn("formatted-date"))
    assert date_tier.items == ()


def test_cli_midgrapheme_refuses_without_stdout():
    r = _run(["1́", "--pattern", "M"])
    assert r.returncode == 3
    assert r.stdout == ""
    assert "grapheme" in r.stderr


def test_cli_invalid_locale_is_config_error():
    r = _run(["Meet 1/3/2026pm", "--locale", "zz_ZZ_bogus"])
    assert r.returncode == 2
    assert r.stdout == ""


# ---------------------------------------------------------- CLI graph structure


def test_cli_stdout_has_expected_graph_structure():
    r = _run(["Meet 1/3/2026pm", "--locale", "en_US", "--pattern", "M/d/yyyy"])
    assert r.returncode == 0
    graph = loads(r.stdout)
    expected = build_graph("Meet 1/3/2026pm", "en_US", "M/d/yyyy")

    assert graph == expected
    assert loads(dumps(graph)) == graph
    assert _atom_surfaces(graph) == list("Meet 1/3/2026pm")
    assert [(tier.declaration.name.local_name, len(tier.items)) for tier in graph.tiers] == [
        ("atom", 15),
        ("sentence", 1),
        ("word-break", 7),
        ("formatted-date", 1),
    ]
    assert _members(graph, "atom-in-sentence", "sentence") == {0: frozenset(range(15))}
    assert _members(graph, "atom-in-date", "formatted-date") == {0: frozenset(range(5, 13))}
    assert _members(graph, "atom-in-word-break", "word-break")[6] == frozenset(range(9, 15))
