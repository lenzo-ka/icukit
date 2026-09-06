from pathlib import Path

import pytest

from eval import evaluate, evaluate_competing, load_competing, load_oracle
from eval.runner import format_report


def test_vendored_oracle_report_structure() -> None:
    oracle = load_oracle()
    report = evaluate(oracle)

    assert list(report["classes"]) == list(oracle)
    for name in oracle:
        metrics = report["classes"][name]
        assert metrics["total"] == len(oracle[name])
        assert metrics["total"] > 0
        assert 0 <= metrics["recognized_strict"] <= metrics["recognized_lenient"]
        assert metrics["recognized_lenient"] <= metrics["total"]
        assert 0.0 <= metrics["recall_strict"] <= 1.0
        assert 0.0 <= metrics["recall_lenient"] <= 1.0

    assert report["overall"]["total"] == sum(len(pairs) for pairs in oracle.values())


def test_loader_splits_only_first_tilde_and_skips_comments(tmp_path: Path) -> None:
    table = tmp_path / "table.txt"
    table.write_text("# comment\n\n1~one~variant\n", encoding="utf-8")

    from eval.loader import load_table

    assert load_table(table) == [("1", "one~variant")]


def test_oracle_classes_come_from_table_filenames(tmp_path: Path) -> None:
    (tmp_path / "ordinal.txt").write_text("1st~first\n", encoding="utf-8")
    (tmp_path / "cardinal.txt").write_text("1~one\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("not an oracle table\n", encoding="utf-8")

    assert load_oracle(tmp_path) == {
        "cardinal": [("1", "one")],
        "ordinal": [("1st", "first")],
    }


def test_evaluate_accepts_an_oracle_subset() -> None:
    report = evaluate({"cardinal": [("1", "one")]})

    assert list(report["classes"]) == ["cardinal"]
    assert report["overall"]["total"] == 1


def test_evaluate_reports_unsupported_classes_without_scoring_them() -> None:
    report = evaluate({"cardinal": [("1", "one")], "telephone": [("911", "nine one one")]})

    assert report["unsupported_classes"] == ["telephone"]
    assert list(report["classes"]) == ["cardinal"]
    assert report["overall"]["total"] == 1
    assert "unsupported/unscored: telephone" in format_report(report)


def test_vendored_competing_readings_are_all_required_on_one_span() -> None:
    records = load_competing()

    assert {record["input"] for record in records} == {
        "I",
        "M",
        "a",
        "II",
        "cat",
        "x_I",
        "I'm",
    }
    characterized = {record["input"] for record in records if "characterizes" in record}
    assert characterized == set()
    assert evaluate_competing(records) == {
        "criterion": "expected spans present; forbidden spans absent; exact records have no others",
        "total": 7,
        "recognized": 7,
        "characterizing_records": 0,
        "recall": 1.0,
    }


def test_competing_record_fails_when_one_expected_candidate_is_absent() -> None:
    report = evaluate_competing(
        [
            {
                "input": "M",
                "expected": [
                    {"type": "letter:name", "start": 0, "end": 1},
                    {"type": "word:single-letter", "start": 0, "end": 1},
                ],
                "forbidden": [],
            }
        ]
    )

    assert report["recognized"] == 0


def test_competing_record_fails_when_a_forbidden_candidate_is_present() -> None:
    report = evaluate_competing(
        [
            {
                "input": "I",
                "expected": [{"type": "letter:name", "start": 0, "end": 1}],
                "forbidden": [{"type": "number:cardinal:roman", "start": 0, "end": 1}],
            }
        ]
    )

    assert report["recognized"] == 0


def test_exact_competing_record_rejects_real_extra_candidates() -> None:
    record = {
        "input": "I",
        "expected": [{"type": "letter:name", "start": 0, "end": 1}],
        "forbidden": [],
    }

    assert evaluate_competing([record])["recognized"] == 1
    assert evaluate_competing([{**record, "exact": True}])["recognized"] == 0


def test_competing_record_requires_an_expectation() -> None:
    with pytest.raises(ValueError, match="no expectations"):
        evaluate_competing([{"input": "I", "expected": [], "forbidden": []}])


def test_format_report_includes_competing_readings() -> None:
    report = evaluate(load_oracle())
    report["competing_readings"] = evaluate_competing(load_competing())

    assert "competing      7/7       100.0%" in format_report(report)
