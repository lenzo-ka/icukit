"""Load the vendored NeMo text-normalization oracle tables."""

from __future__ import annotations

from pathlib import Path

DEFAULT_DATA_DIR = Path(__file__).parent / "data" / "nemo"


def load_table(path: Path) -> list[tuple[str, str]]:
    """Load written/spoken pairs from one tilde-delimited oracle table."""
    pairs: list[tuple[str, str]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "~" not in line:
            raise ValueError(f"{path}:{line_number}: expected written~spoken pair")
        written, spoken = line.split("~", 1)
        pairs.append((written, spoken))
    return pairs


def load_oracle(data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, list[tuple[str, str]]]:
    """Load every evaluation class from an oracle directory."""
    return {path.stem: load_table(path) for path in sorted(data_dir.glob("*.txt"))}
