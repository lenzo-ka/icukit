from pathlib import Path

from eval import evaluate, load_oracle


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
