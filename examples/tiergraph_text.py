"""H1 proof of concept: text -> canonical tiergraph JSON, with one crossing detector.

This is a development/example integration, NOT part of the installed icukit package.
It requires tiergraph (Python >= 3.12) and is exercised only in the >= 3.12 CI job.

What it demonstrates
--------------------
Segmentation and one format-span detector, emitted into a single tiergraph document:

  * an ``atom`` tier of extended grapheme clusters carrying their exact surface text,
  * ``sentence`` and ``word-break`` tiers from ICU segmentation,
  * a ``formatted-date`` tier from a windowed ``SimpleDateFormat`` detector,
  * extents as per-atom membership edges (tiergraph stores no coordinates),

such that a formatted date can *cross* a word token -- overlap it without either
containing the other -- which no tokenizer can produce (see the module test).

Scope: this detects the EXTENTS and TYPE of canonical formatter output, not date
VALUES, not candidate resolution, not locale coverage. It accepts exactly one explicit
date pattern and one explicit locale.

Round-trip: the ordered ``atom`` surfaces reconstruct the source byte-for-byte after a
full ``dumps`` / ``loads`` cycle.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import icu
from tiergraph import (
    AttributeDeclaration,
    AttributeDomain,
    AttributeValue,
    BipartiteRelationDeclaration,
    Graph,
    Item,
    ItemRef,
    NamespaceDeclaration,
    QualifiedName,
    RelationInstance,
    SimpleRelationDeclaration,
    Tier,
    TierDeclaration,
    XsdType,
)
from tiergraph import dumps as tiergraph_dumps

from icukit.breaker import break_grapheme_spans, break_sentence_spans, break_word_spans

# --------------------------------------------------------------------------- names

NS = "urn:tiergraph:profile:text:icu:v1"  # FINAL wire identity -- not a placeholder.


def _n(local: str) -> QualifiedName:
    return QualifiedName(NS, local)


# Tier names double as their item-type names (one SimpleRelationDeclaration per tier).
ATOM = _n("atom")
SENTENCE = _n("sentence")
WORD_BREAK = _n("word-break")
FORMATTED_DATE = _n("formatted-date")

# Coverage relations: atom (left) is covered by a span (right). One per span tier,
# because a bipartite declaration fixes a single left/right type pair.
ATOM_IN_SENTENCE = _n("atom-in-sentence")
ATOM_IN_WORD_BREAK = _n("atom-in-word-break")
ATOM_IN_DATE = _n("atom-in-date")

# Type declaration names (distinct from the coverage relation names above).
TYPES_ATOM = _n("type-atom")
TYPES_SENTENCE = _n("type-sentence")
TYPES_WORD_BREAK = _n("type-word-break")
TYPES_DATE = _n("type-formatted-date")


class BuilderRefusal(Exception):
    """A successful ICU parse or a segmentation extent violates a graph invariant.

    Raised only for an *ostensibly successful* result with an invalid endpoint
    (reversed, surrogate-interior, or mid-grapheme). A parse *miss* is never a
    refusal -- the scan simply continues. Carries the offending boundary so the CLI
    can report it and emit no partial document.
    """


# ------------------------------------------------------------------- offset maps


def _boundary_maps(text: str) -> tuple[list[int], dict[int, int]]:
    """Independent code-point<->UTF-16 boundary maps for ``text``.

    Returns ``(cp_to_utf16, utf16_to_cp)`` where ``cp_to_utf16[i]`` is the UTF-16
    offset of code point ``i`` (``i`` in ``0..len(text)``) and ``utf16_to_cp`` maps a
    UTF-16 offset back to a code point ONLY at valid code-point boundaries. A UTF-16
    offset interior to a surrogate pair is absent from ``utf16_to_cp`` by construction
    -- callers must treat a miss as "not a valid boundary", never round to a neighbor.

    These are built directly rather than by inverting ``icukit._offsets.codepoint_map``
    (which is UTF-16 -> code-point only and aliases surrogate interiors): a detector
    needs both directions and the reverse of a lossy map reintroduces the F1 class.
    """
    cp_to_utf16 = [0] * (len(text) + 1)
    for i, ch in enumerate(text):
        cp_to_utf16[i + 1] = cp_to_utf16[i] + (2 if ord(ch) > 0xFFFF else 1)
    utf16_to_cp = {u: i for i, u in enumerate(cp_to_utf16)}
    return cp_to_utf16, utf16_to_cp


# ------------------------------------------------------------------- the detector


@dataclass(frozen=True)
class DateSpan:
    start: int  # code-point index, inclusive
    end: int  # code-point index, exclusive


def _make_formatter(locale: str, pattern: str) -> icu.SimpleDateFormat:
    """Non-lenient, UTC-pinned formatter so exact reformat is host-timezone independent."""
    try:
        loc = icu.Locale(locale)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"invalid locale {locale!r}: {exc}") from exc
    # ICU accepts/falls back on unknown locale ids rather than refusing; validate
    # against the available date-formatting locales instead of trusting Locale().
    available = {loc_id for loc_id in icu.Locale.getAvailableLocales()}
    if loc.getBaseName() not in available and loc.getLanguage() not in {
        icu.Locale(x).getLanguage() for x in available
    }:
        raise ValueError(f"unsupported locale {locale!r}")
    try:
        fmt = icu.SimpleDateFormat(pattern, loc)
    except icu.ICUError as exc:
        raise ValueError(f"invalid pattern {pattern!r}: {exc}") from exc
    fmt.setLenient(False)
    fmt.setTimeZone(icu.TimeZone.getGMT())
    return fmt


def detect_dates(text: str, locale: str, pattern: str) -> list[DateSpan]:
    """Windowed date detection over ``text`` with exact-reformat acceptance.

    Scans every grapheme-cluster start. For each: a parse miss or no progress simply
    continues (never a refusal, C1). On a successful parse the endpoint is converted
    back to a code point; a surrogate-interior or non-grapheme endpoint is a refusal
    (C2/C3). An accepted span must reproduce the formatter's canonical output exactly
    -- this rejects leading-space and short-year coercions ICU would otherwise permit.
    """
    fmt = _make_formatter(locale, pattern)
    us = icu.UnicodeString(text)
    cp_to_utf16, utf16_to_cp = _boundary_maps(text)
    grapheme_starts = sorted({g["start"] for g in break_grapheme_spans(text, locale)})
    grapheme_boundaries = {g["start"] for g in break_grapheme_spans(text, locale)} | {
        g["end"] for g in break_grapheme_spans(text, locale)
    }

    seen: set[tuple[int, int]] = set()
    out: list[DateSpan] = []
    for start_cp in grapheme_starts:
        start_u16 = cp_to_utf16[start_cp]
        pos = icu.ParsePosition(start_u16)
        cal = icu.GregorianCalendar(icu.TimeZone.getGMT(), icu.Locale(locale))
        cal.clear()
        try:
            fmt.parse(us, cal, pos)
        except icu.ICUError:
            continue  # parse miss -> continue (C1)
        if pos.getErrorIndex() != -1 or pos.getIndex() <= start_u16:
            continue  # miss / no progress -> continue (C1)

        end_u16 = pos.getIndex()
        # SUCCESS with an endpoint we cannot place on a code-point boundary is fatal.
        if end_u16 not in utf16_to_cp:
            raise BuilderRefusal(
                f"date parse succeeded but ended at UTF-16 offset {end_u16} "
                f"interior to a surrogate pair (start code point {start_cp})"
            )
        end_cp = utf16_to_cp[end_u16]
        # SUCCESS ending inside a grapheme cluster is the invariant we assert against.
        if end_cp not in grapheme_boundaries:
            raise BuilderRefusal(
                f"date parse succeeded but ended at code point {end_cp}, "
                f"interior to a grapheme cluster (start code point {start_cp})"
            )
        # Exact-reformat acceptance: consumed text must be canonical formatter output.
        if fmt.format(cal) != text[start_cp:end_cp]:
            continue  # permissive coercion -> not accepted (not fatal)

        key = (start_cp, end_cp)
        if key not in seen:
            seen.add(key)
            out.append(DateSpan(start_cp, end_cp))
    out.sort(key=lambda d: (d.start, d.end))
    return out


# -------------------------------------------------------------------- the builder


def _atom_index_maps(
    graphemes: list[dict],
) -> tuple[dict[int, int], dict[int, int]]:
    """Maps from code-point boundary to atom index.

    ``start_to_atom[cp]`` gives the atom whose cluster starts at code point ``cp``;
    ``end_to_after[cp]`` gives the atom index just past the cluster ending at ``cp``
    (so a span ``[s, e)`` covers atoms ``start_to_atom[s] .. end_to_after[e] - 1``).
    """
    start_to_atom = {g["start"]: k for k, g in enumerate(graphemes)}
    end_to_after = {g["end"]: k + 1 for k, g in enumerate(graphemes)}
    return start_to_atom, end_to_after


def _coverage_edges(
    relation: QualifiedName,
    span_tier: QualifiedName,
    spans: list[tuple[int, int]],
    start_to_atom: dict[int, int],
    end_to_after: dict[int, int],
) -> list[RelationInstance]:
    """One edge per covered atom (no duplicates). Refuses a non-atom-boundary extent."""
    edges: list[RelationInstance] = []
    for span_index, (s_cp, e_cp) in enumerate(spans):
        if s_cp not in start_to_atom or e_cp not in end_to_after:
            raise BuilderRefusal(
                f"{relation.local_name} extent [{s_cp}, {e_cp}) does not lie on atom boundaries"
            )
        first = start_to_atom[s_cp]
        stop = end_to_after[e_cp]
        if stop <= first:
            raise BuilderRefusal(
                f"{relation.local_name} extent [{s_cp}, {e_cp}) is empty or reversed"
            )
        for atom_index in range(first, stop):
            edges.append(
                RelationInstance(
                    relation,
                    ItemRef(ATOM, atom_index),
                    ItemRef(span_tier, span_index),
                )
            )
    return edges


def build_graph(text: str, locale: str, pattern: str) -> Graph:
    """Build the four-tier H1 graph for ``text``."""
    graphemes = break_grapheme_spans(text, locale)
    sentences = [(s["start"], s["end"]) for s in break_sentence_spans(text, locale)]
    words = [(w["start"], w["end"]) for w in break_word_spans(text, locale)]
    dates = [(d.start, d.end) for d in detect_dates(text, locale, pattern)]

    start_to_atom, end_to_after = _atom_index_maps(graphemes)

    # atom tier carries surface text as an item attribute (a namespaced pair).
    atom_items = tuple(Item(attributes=(_surface_attr(g["text"]),)) for g in graphemes)
    sentence_items = tuple(Item() for _ in sentences)
    word_items = tuple(Item() for _ in words)
    date_items = tuple(Item() for _ in dates)

    tiers = (
        Tier(TierDeclaration(ATOM, "Grapheme-cluster atoms"), atom_items),
        Tier(TierDeclaration(SENTENCE, "ICU sentence spans"), sentence_items),
        Tier(TierDeclaration(WORD_BREAK, "ICU word-break spans"), word_items),
        Tier(TierDeclaration(FORMATTED_DATE, "Detected formatted dates"), date_items),
    )

    relation_declarations = (
        SimpleRelationDeclaration(TYPES_ATOM, ATOM, ATOM),
        SimpleRelationDeclaration(TYPES_SENTENCE, SENTENCE, SENTENCE),
        SimpleRelationDeclaration(TYPES_WORD_BREAK, WORD_BREAK, WORD_BREAK),
        SimpleRelationDeclaration(TYPES_DATE, FORMATTED_DATE, FORMATTED_DATE),
        BipartiteRelationDeclaration(ATOM_IN_SENTENCE, ATOM, SENTENCE, acyclic=True),
        BipartiteRelationDeclaration(ATOM_IN_WORD_BREAK, ATOM, WORD_BREAK, acyclic=True),
        BipartiteRelationDeclaration(ATOM_IN_DATE, ATOM, FORMATTED_DATE, acyclic=True),
    )

    relations = (
        *_coverage_edges(ATOM_IN_SENTENCE, SENTENCE, sentences, start_to_atom, end_to_after),
        *_coverage_edges(ATOM_IN_WORD_BREAK, WORD_BREAK, words, start_to_atom, end_to_after),
        *_coverage_edges(ATOM_IN_DATE, FORMATTED_DATE, dates, start_to_atom, end_to_after),
    )

    attribute_declarations = (AttributeDeclaration(_SURFACE, AttributeDomain.ITEM, XsdType.STRING),)

    return Graph(
        (NamespaceDeclaration("text", NS),),
        tiers,
        relation_declarations,
        relations,
        attribute_declarations,
    )


# --------------------------------------------------------- surface attribute helper

_SURFACE = _n("surface")


def _surface_attr(surface: str) -> AttributeValue:
    return AttributeValue(_SURFACE, XsdType.STRING, surface)


# ----------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit text as canonical tiergraph JSON.")
    parser.add_argument("text", nargs="?", help="source text (default: read stdin)")
    parser.add_argument("--locale", default="en_US")
    parser.add_argument("--pattern", default="M/d/yyyy")
    args = parser.parse_args(argv)

    text = args.text if args.text is not None else sys.stdin.read()

    try:
        graph = build_graph(text, args.locale, args.pattern)
    except ValueError as exc:  # configuration
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
    except BuilderRefusal as exc:  # graph invariant
        print(f"refused: {exc}", file=sys.stderr)
        return 3

    sys.stdout.write(tiergraph_dumps(graph))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
