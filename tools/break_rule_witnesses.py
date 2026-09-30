#!/usr/bin/env python3
"""Build deterministic predicate-derived witnesses for the English TN rules.

The search never reads corpus rows or corpus text. It uses short template words
and lexical values present in the rules. A match witness must reach its rule in
the complete ordered list. Its near miss uses the same text construction with
one predicate falsified, and the target rule must decide no candidate anywhere.
The public loader performs the same checks again on the output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from functools import cache
from pathlib import Path
from typing import Any

from icukit import break_rule_identity, char_classes, load_break_rules, tokens
from icukit.breaker import break_sentence_spans
from icukit.sentence_override import (
    _compile_rule,
    _CompiledBreakRule,
    _FeatureNotYet,
    _match_observed_rule,
    _observed_feature_value,
    _predicate_matches,
    _TokenFeatureCache,
)

DEFAULT_MODEL = Path("/Users/lenzo/covgap-data/breaks/models/m1c/sweep/b-glue2-k1-r200.json")
DEFAULT_OUTPUT = Path("icukit/data/break_rules/en/sentence-tn.json")
DEFAULT_RECEIPT = Path("icukit/data/break_rules/en/RECEIPT.json")
MINER_DIGEST = "ab44dc37951ebbbad6f38798af3a677081ec439e46d4246573f3f3829ecbc24c"
FIDELITY_FIELDS = ("id", "effect", "lookahead", "when", "receipt")
COMPILE_NO_MATCH = "No candidate here"

# A few predicates depend on ICU splitting punctuation into multiple tokens.
# These authored templates make that token geometry explicit; they are not
# quotations or adaptations of corpus sentences.
SPECIAL_TEXTS = {
    "en.sb.0029": "alpha beta,x ed. Author",
    "en.sb.0055": "alpha beta Alpha 2024. Alice",
    "en.sb.0058": "alpha a. 123. Alice",
    "en.sb.0060": 'alpha an ". Author',
    "en.sb.0088": "alpha beta gamma: J. Author",
    "en.sb.0101": "alpha beta gamma word.\nabc1",
    "en.sb.0127": "alpha beta Bravo, Alice.\nabc1",
    "en.sb.0128": "alpha beta,x R. Author",
    "en.sb.0133": "alpha beta gamma word). Alexanders",
    "en.sb.0137": "alpha beta,x P. Author",
    "en.sb.0144": "alpha beta 1 W.\na B",
    "en.sb.0152": "alpha beta 1 Alice.\nauthors",
    "en.sb.0155": "alpha beta gamma aa). A123456789",
    "en.sb.0161": "alpha beta 1 Alice.\nthe",
    "en.sb.0164": "alpha beta Ab II. Author",
    "en.sb.0166": "alpha beta ,authors Alice.\nauthor1",
    "en.sb.0170": "alpha beta an word.\nab1",
    "en.sb.0179": "alpha beta word. ). A1234567890",
    "en.sb.0183": "alpha beta B. Alice.\nauthor",
    "en.sb.0185": "alpha beta,x S. Author",
    "en.sb.0191": "alpha beta an Alice.\nauthor continues",
    "en.sb.0196": "alpha beta,x I. Author",
}


def _shape_surface(value: str) -> str:
    return "".join({"X": "A", "x": "a", "d": "1", "a": "b"}.get(char, char) for char in value)


def _coarse_surface(value: str) -> str:
    if value == "<Lu>":
        return "I"
    return "".join({"A": "word", "N": "1", "¤": "$"}.get(char, char) for char in value)


def _values(rule: dict[str, Any], at: int | str, feature: str) -> list[Any]:
    found: list[Any] = []
    for predicate in rule["when"]:
        if predicate["at"] == at and predicate["f"] == feature and "in" in predicate:
            found.extend(predicate["in"])
    return found


_CHAR_VOCABULARY = 'aA1"():,.-!? '


@cache
def _char_matches(char: str, feature: str, value: str) -> bool:
    if value in {"<BOS>", "<EOS>", "<BEYOND>"}:
        return False
    if feature == "text":
        return char == value
    if feature == "extension_classes":
        return False
    return char_classes(char, feature)[0] == value


def _constrained_chars(rule: dict[str, Any], side: str, base: str) -> str | None:
    constraints: dict[int, list[tuple[str, str]]] = {}
    sign = "+" if side == "right" else "-"
    for predicate in rule["when"]:
        at = predicate["at"]
        if not isinstance(at, str) or not at.startswith(f"c{sign}") or "in" not in predicate:
            continue
        distance = int(at[2:])
        values = [str(value) for value in predicate["in"]]
        if any(value in {"<BOS>", "<EOS>", "<BEYOND>"} for value in values):
            continue
        constraints.setdefault(distance, []).extend(
            (str(predicate["f"]), value) for value in values
        )
    if not constraints:
        return None
    width = max(8, len(base))
    chars = list((base + "authorzz")[:width])
    for distance, requirements in constraints.items():
        index = distance - 1 if side == "right" else width + 1 - distance
        candidates = [
            char
            for char in _CHAR_VOCABULARY
            if all(_char_matches(char, feature, value) for feature, value in requirements)
        ]
        if not candidates:
            return None
        chars[index] = candidates[0]
    return "".join(chars)


def _token_surfaces(rule: dict[str, Any], at: int) -> list[str]:
    choices: list[str] = []
    for value in _values(rule, at, "text"):
        choices.append(str(value))
    for value in _values(rule, at, "lower"):
        choices.extend((str(value), str(value).capitalize()))
    for feature in ("shape.cased", "run.shape.cased"):
        for value in _values(rule, at, feature):
            choices.append(_shape_surface(str(value)))
    for value in _values(rule, at, "shape.coarse"):
        choices.append(_coarse_surface(str(value)))
    for value in _values(rule, at, "general_category.last"):
        choices.append(
            {
                "Lowercase_Letter": "word",
                "Uppercase_Letter": "USA",
                "Decimal_Number": "word1",
            }[str(value)]
        )
    for value in _values(rule, at, "sentence_break.first"):
        choices.append({"Upper": "Alpha", "Lower": "alpha"}[str(value)])
    for value in _values(rule, at, "word_break.first"):
        choices.append({"ALetter": "alpha"}[str(value)])
    minimum = max(
        (
            int(item["ge"])
            for item in rule["when"]
            if item["at"] == at and item["f"] == "len" and "ge" in item
        ),
        default=1,
    )
    maximum = min(
        (
            int(item["le"])
            for item in rule["when"]
            if item["at"] == at and item["f"] == "len" and "le" in item
        ),
        default=24,
    )
    choices.extend(("a" * minimum, "author"[:maximum], "word"[:maximum]))
    return list(dict.fromkeys(item for item in choices if minimum <= len(item) <= maximum))


def _run_surfaces(rule: dict[str, Any]) -> list[str]:
    choices: list[str] = []
    for value in _values(rule, "run-1", "text"):
        choices.append(str(value))
    for feature in ("shape.cased", "run.shape.cased"):
        for value in _values(rule, "run-1", feature):
            choices.append(_shape_surface(str(value)))
    for value in _values(rule, "run-1", "shape.coarse"):
        choices.append(_coarse_surface(str(value)))
    for value in _token_surfaces(rule, -1):
        choices.extend((str(value), f"ended.{value}"))
    choices.extend(
        (
            "Dr.",
            "Alice.",
            "ended.",
            "1999.",
            'ended."',
        )
    )
    constrained = _constrained_chars(rule, "left", "author.")
    if constrained is not None:
        choices[0:0] = (constrained, constrained.rstrip() + ".")
    return list(dict.fromkeys(choices))


def _right_surfaces(rule: dict[str, Any]) -> list[str]:
    choices = _token_surfaces(rule, 1)
    bases = list(choices) or ["authorzz"]
    for base in bases:
        constrained = _constrained_chars(rule, "right", base)
        if constrained is not None:
            choices.insert(0, constrained)
    for predicate in rule["when"]:
        at = predicate["at"]
        if not isinstance(at, str) or not at.startswith("c+") or "in" not in predicate:
            continue
        distance = int(at[2:])
        if "<BEYOND>" in predicate["in"]:
            choices.insert(0, "a" * max(1, distance - 2) + " B")
    choices.extend(('"Author', "authors"))
    return list(dict.fromkeys(choices))


def _all_surfaces(rules: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    left = [surface for rule in rules for surface in _run_surfaces(rule)]
    right = [surface for rule in rules for surface in _right_surfaces(rule)]
    right.extend(
        (
            "Alice",
            "author",
            "the",
            "word",
            "word1",
            "USA",
            '"',
            "&",
            "(note",
            "(2024).",
            "2024",
        )
    )
    return list(dict.fromkeys(left)), list(dict.fromkeys(right))


def _prefixes(rule: dict[str, Any]) -> list[str]:
    slots = {position: _token_surfaces(rule, position) for position in (-3, -2, -1)}
    # The candidate run is appended after this prefix and ordinarily supplies
    # token -1.  Therefore the final two prefix tokens are -2 and -3.
    base = {
        -4: "alpha",
        -3: slots[-3][0] if slots[-3] else "beta",
        -2: slots[-2][0] if slots[-2] else "gamma",
    }
    candidates = [f"{base[-4]} {base[-3]} {base[-2]}", "alpha beta gamma"]
    # A token whose ``ws.before`` is false is placed in the first run or joined
    # to its predecessor.  Both forms are tried because ICU may split punctuation.
    for position in (-3, -2):
        needs_false = False in _values(rule, position, "ws.before")
        needs_true = True in _values(rule, position, "ws.before")
        if needs_false:
            words = [base[-4], base[-3], base[-2]]
            index = position + 4
            if index == 0:
                candidates.append(" ".join(words))
            else:
                candidates.append(
                    " ".join(
                        words[: index - 1] + [words[index - 1] + words[index]] + words[index + 1 :]
                    )
                )
        if needs_true:
            candidates.append(" ".join((base[-4], base[-3], base[-2])))
    return list(dict.fromkeys(candidates))


def _compile(rules: list[dict[str, Any]]) -> tuple[_CompiledBreakRule, ...]:
    compiled: list[_CompiledBreakRule] = []
    for raw in rules:
        compilable = deepcopy(raw)
        compilable["witnesses"] = {"match": ["Authored."], "no_match": [COMPILE_NO_MATCH]}
        rule, errors = _compile_rule(compilable)
        if errors or rule is None:
            raise RuntimeError(f"cannot compile {raw.get('id')}: {errors}")
        compiled.append(rule)
    return tuple(compiled)


def _candidate_text(prefix: str, left: str, right: str, separator: str = " ") -> str:
    start = f"{prefix} " if prefix else ""
    return f"{start}{left}{separator}{right} continues"


def canonical_rule_digest(rules: list[dict[str, Any]]) -> str:
    """Digest the ordered semantic/count fields shared by source and artifact."""
    fields = []
    for rule in rules:
        values = [rule[field] for field in FIDELITY_FIELDS[:-1]]
        values.append({key: rule["receipt"][key] for key in ("n", "n_break")})
        fields.append(values)
    canonical = json.dumps(fields, ensure_ascii=False, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def _mutation_variants(text: str, offset: int):
    replacements = ("x", "A", "1", "word", "authors", "ZZZZZZZZZZZZ", '"', "&")
    spans = [(match.start(), match.end()) for match in re.finditer(r"[^\s]+", text)]
    for start, end in spans:
        if start < offset < end:
            continue
        for replacement in replacements:
            if text[start:end] == replacement:
                continue
            delta = len(replacement) - (end - start)
            yield text[:start] + replacement + text[end:], offset + (delta if end <= offset else 0)
    for index, original in enumerate(text):
        for replacement in ("a", "A", "1", "x", " ", "\n", ".", ",", '"'):
            if replacement == original:
                continue
            yield text[:index] + replacement + text[index + 1 :], offset
    for index in range(len(text)):
        if index == offset - 1:
            continue
        yield text[:index] + text[index + 1 :], offset - int(index < offset)


def _predicate_truths(rule: _CompiledBreakRule, text: str, offset: int) -> tuple[bool, ...] | None:
    toks = tokens(text, "en_US")
    if offset not in {span["end"] for span in break_sentence_spans(text, "en_US", base="none")}:
        return None
    if any(token["start"] < offset < token["end"] for token in toks):
        return None
    cache = _TokenFeatureCache(True)
    truths = []
    for predicate in rule.when:
        try:
            value, _, _ = _observed_feature_value(
                predicate, rule, text, offset, toks, (), "en_US", (), True, cache
            )
        except _FeatureNotYet:
            return None
        truths.append(_predicate_matches(value, predicate))
    return tuple(truths)


def _target_matches_anywhere(rule: _CompiledBreakRule, text: str) -> bool:
    toks = tokens(text, "en_US")
    for span in break_sentence_spans(text, "en_US", base="none"):
        offset = span["end"]
        if any(token["start"] < offset < token["end"] for token in toks):
            continue
        matched, _, _ = _match_observed_rule(
            rule, text, offset, toks, (), "en_US", (), True, _TokenFeatureCache(True)
        )
        if matched:
            return True
    return False


def _near_miss(rule: _CompiledBreakRule, match: dict[str, object]) -> dict[str, object] | None:
    text = str(match["text"])
    offset = int(match["offset"])
    seen: set[tuple[str, int]] = set()
    for mutated, mutated_offset in _mutation_variants(text, offset):
        key = (mutated, mutated_offset)
        if key in seen:
            continue
        seen.add(key)
        truths = _predicate_truths(rule, mutated, mutated_offset)
        if truths is None or truths.count(False) != 1:
            continue
        if not _target_matches_anywhere(rule, mutated):
            return {"text": mutated, "offset": mutated_offset}
    return None


def _find_witnesses(rules: list[dict[str, Any]]) -> dict[str, dict[str, object]]:
    compiled = _compile(rules)
    wanted = {rule.id for rule in compiled}
    found: dict[str, dict[str, object]] = {}
    compiled_by_id = {rule.id: (index, rule) for index, rule in enumerate(compiled)}

    def try_text(text: str, target_id: str) -> None:
        target_index, target = compiled_by_id[target_id]
        toks = tokens(text, "en_US")
        offsets = [span["end"] for span in break_sentence_spans(text, "en_US", base="none")]
        for offset in offsets:
            if offset == len(text) or any(token["start"] < offset < token["end"] for token in toks):
                continue
            cache = _TokenFeatureCache(True)
            matched, _, _ = _match_observed_rule(
                target, text, offset, toks, (), "en_US", (), True, cache
            )
            if not matched:
                continue
            shadowed = False
            for earlier in compiled[:target_index]:
                earlier_match, _, _ = _match_observed_rule(
                    earlier, text, offset, toks, (), "en_US", (), True, cache
                )
                if earlier_match:
                    shadowed = True
                    break
            if not shadowed:
                found[target_id] = {
                    "text": text,
                    "offset": offset,
                    "decision": target.effect,
                }
                return

    # Give every rule a mechanically tailored token context.  Small generic
    # side pools cover predicates that constrain only one side of the cut.
    by_id = {str(rule["id"]): rule for rule in rules}
    generic_left = ["Dr.", "Alice.", "ended."]
    generic_right = ["Alice", "author", "word"]
    for rule_id in sorted(wanted):
        raw = by_id[rule_id]
        if rule_id in SPECIAL_TEXTS:
            try_text(SPECIAL_TEXTS[rule_id], rule_id)
            if rule_id in found:
                continue
        lefts = list(dict.fromkeys((*_run_surfaces(raw), *generic_left)))
        rights = list(dict.fromkeys((*_right_surfaces(raw), *generic_right)))
        prefixes = _prefixes(raw)
        if any(
            predicate["at"] == "c-8" and "<BOS>" in predicate.get("in", [])
            for predicate in raw["when"]
        ):
            prefixes.insert(0, "")
        for prefix in prefixes:
            for left in lefts:
                for right in rights:
                    for separator in (" ", "\n"):
                        try_text(_candidate_text(prefix, left, right, separator), rule_id)
                    if rule_id in found:
                        break
                if rule_id in found:
                    break
            if rule_id in found:
                break
    return found


def build(model_path: Path, output_path: Path, receipt_path: Path = DEFAULT_RECEIPT) -> None:
    measured = json.loads(model_path.read_text(encoding="utf-8"))
    rules = deepcopy(measured["rules"])
    witnesses = _find_witnesses(rules)
    missing = [str(rule["id"]) for rule in rules if rule["id"] not in witnesses]
    if missing:
        raise SystemExit("shadowed or unsynthesized rules: " + ", ".join(missing))
    compiled = {rule.id: rule for rule in _compile(rules)}
    near_misses = {
        rule_id: _near_miss(compiled[rule_id], witness) for rule_id, witness in witnesses.items()
    }
    missing_near_misses = [rule_id for rule_id, witness in near_misses.items() if witness is None]
    if missing_near_misses:
        raise SystemExit("near misses not synthesized: " + ", ".join(missing_near_misses))

    shipped_rules = []
    for rule in rules:
        shipped_rules.append(
            {
                "id": rule["id"],
                "effect": rule["effect"],
                "lookahead": rule["lookahead"],
                "when": rule["when"],
                "receipt": {
                    "n": rule["receipt"]["n"],
                    "n_break": rule["receipt"]["n_break"],
                },
                "witnesses": {
                    "match": [witnesses[str(rule["id"])]],
                    "no_match": [near_misses[str(rule["id"])]],
                },
            }
        )
    artifact = {
        "schema_version": 1,
        "kind": "break-rules",
        "id": "icukit/en/sentence-tn",
        "locale": "en",
        "status": "experimental",
        "features": "icukit.features@1",
        "identity": break_rule_identity("en_US"),
        "provenance": {
            "source": "google/tn-en_with_types",
            "pools": ["training"],
            "derivation": f"sb-decision-list@sha256:{MINER_DIGEST}",
            "license": {"spdx": "CC-BY-SA-4.0", "class": "shippable-share-alike"},
        },
        "training": {"k": measured["training"]["k"]},
        "rules": shipped_rules,
    }
    # The public loader is the final authority on identity, order, and witnesses.
    load_break_rules(artifact)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["rule_fidelity"] = {
        "canonicalization": (
            "UTF-8 compact JSON of the ordered list of (id, effect, lookahead, when, receipt)"
        ),
        "source_model_digest": canonical_rule_digest(rules),
    }
    receipt_path.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args()
    build(args.model, args.output, args.receipt)


if __name__ == "__main__":
    main()
