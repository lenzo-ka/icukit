from pathlib import Path

from eval import CLASSES, evaluate, load_oracle


def test_vendored_oracle_report_structure() -> None:
    oracle = load_oracle()
    report = evaluate(oracle)

    assert set(report["classes"]) == set(CLASSES)
    for name in CLASSES:
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
