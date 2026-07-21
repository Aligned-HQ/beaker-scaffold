"""Runnable smoke solution for the scaffold.

Replace this placeholder analysis with the real reference workflow. The
implementation deliberately derives its output from the visible input rather
than storing expected values.
"""
from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path


WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/workspace"))
DATA_DIR = Path(os.environ.get("DATA_DIR", str(WORKSPACE_DIR / "data")))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(WORKSPACE_DIR / "output")))


def read_values(path: Path) -> list[float]:
    with path.open(newline="") as handle:
        rows = csv.DictReader(handle)
        if rows.fieldnames != ["sample_id", "value"]:
            raise ValueError("input.csv must have sample_id,value columns")
        values = [float(row["value"]) for row in rows]
    if not values:
        raise ValueError("input.csv contains no observations")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("input.csv contains a non-finite value")
    return values


def summarize(values: list[float]) -> dict[str, int | float]:
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return {
        "n_observations": len(values),
        "mean_value": mean,
        "std_value": math.sqrt(variance),
        "minimum": min(values),
        "maximum": max(values),
    }


def main() -> None:
    input_path = DATA_DIR / "input.csv"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = summarize(read_values(input_path))

    (OUTPUT_DIR / "result.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )


if __name__ == "__main__":
    main()
