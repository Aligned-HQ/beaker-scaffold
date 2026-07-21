"""Executable smoke verifier for the starter task.

Replace this file with independent scientific checks for the real workflow.
The verifier should execute or recompute meaningful outcomes; it should not
grep source files or grade prose wording.
"""
from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

import pytest


OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/workspace/output"))
TESTS_DIR = Path(os.environ.get("TESTS_DIR", "/tests"))
RESULT_PATH = OUTPUT_DIR / "result.json"
INPUT_PATH = TESTS_DIR / "data" / "input.csv"
EXPECTED_KEYS = {
    "n_observations",
    "mean_value",
    "std_value",
    "minimum",
    "maximum",
}


def load_values() -> list[float]:
    with INPUT_PATH.open(newline="") as handle:
        return [float(row["value"]) for row in csv.DictReader(handle)]


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    assert RESULT_PATH.exists(), f"missing output: {RESULT_PATH}"
    return json.loads(RESULT_PATH.read_text())


def test_result_schema_and_finite_values(result: dict[str, object]) -> None:
    assert set(result) == EXPECTED_KEYS
    assert isinstance(result["n_observations"], int)
    for key in EXPECTED_KEYS - {"n_observations"}:
        value = result[key]
        assert isinstance(value, (int, float)) and not isinstance(value, bool)
        assert math.isfinite(float(value))


def test_summary_recomputes_from_independent_fixture(result: dict[str, object]) -> None:
    values = load_values()
    mean = sum(values) / len(values)
    std = math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
    assert result["n_observations"] == len(values)
    assert math.isclose(float(result["mean_value"]), mean, rel_tol=1e-9, abs_tol=1e-12)
    assert math.isclose(float(result["std_value"]), std, rel_tol=1e-9, abs_tol=1e-12)
    assert result["minimum"] == min(values)
    assert result["maximum"] == max(values)

# A real task should add independent scientific assertions here. Do not add
# keyword, heading, word-count, tone, or other prose-content tests.
