"""Command-line entry point for the recall evaluation harness."""

from __future__ import annotations

from .competing import evaluate_competing, load_competing
from .loader import load_oracle
from .runner import DEFAULT_BASELINE, evaluate, format_report, write_report


def main() -> None:
    """Run the vendored oracle, print its report, and update the baseline JSON."""
    report = evaluate(load_oracle())
    report["competing_readings"] = evaluate_competing(load_competing())
    write_report(report)
    print(format_report(report))
    print(f"\nWrote {DEFAULT_BASELINE}")


if __name__ == "__main__":
    main()
