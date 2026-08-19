"""Recall evaluation harness for vendored text-normalization oracles."""

from __future__ import annotations

from .loader import CLASSES, load_oracle
from .runner import evaluate, format_report, write_report

__all__ = ["CLASSES", "evaluate", "format_report", "load_oracle", "write_report"]
