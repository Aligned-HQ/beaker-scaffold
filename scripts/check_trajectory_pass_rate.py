#!/usr/bin/env python3
"""Cross-check trajectory pass rates against raw Harbor trial results."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


AGENTS = ("claude", "codex", "gemini")
RUN_ID_RE = re.compile(r"^# Harbor Run Summary:\s*(\S+)\s*$", re.MULTILINE)
COUNT_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")


@dataclass(frozen=True)
class Counts:
    passed: int
    trials: int


class PassRateError(Exception):
    """A malformed or inconsistent pass-rate input."""


def table_cells(line: str) -> list[str] | None:
    if "|" not in line:
        return None
    return [part.strip() for part in line.strip().strip("|").split("|")]


def classify(value: object) -> str | None:
    text = str(value).lower()
    if "oracle" in text:
        return "oracle"
    for agent in AGENTS:
        if agent in text:
            return agent
    return None


def parse_summary(path: Path) -> tuple[str, dict[str, Counts]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PassRateError(f"could not read trajectory summary {path}: {exc}") from exc

    run_match = RUN_ID_RE.search(text)
    if run_match is None:
        raise PassRateError(f"trajectory summary is missing its Harbor run ID: {path}")
    run_id = run_match.group(1)

    lines = text.splitlines()
    header_index: int | None = None
    columns: dict[str, int] = {}
    for index, line in enumerate(lines):
        cells = table_cells(line)
        if cells is None or len(cells) < 2:
            continue
        if cells[0].lower() != "task" or cells[1].lower() != "oracle":
            continue
        header_index = index
        for column, cell in enumerate(cells[2:], 2):
            agent = classify(cell)
            if agent in AGENTS:
                if agent in columns:
                    raise PassRateError(f"summary has duplicate {agent} columns")
                columns[agent] = column
        break

    if header_index is None:
        raise PassRateError("summary.md is missing the Task/Oracle result table")
    missing = [agent for agent in AGENTS if agent not in columns]
    if missing:
        raise PassRateError(
            "summary.md is missing agent columns: " + ", ".join(missing)
        )

    totals = {agent: [0, 0] for agent in AGENTS}
    rows = 0
    for line in lines[header_index + 1 :]:
        cells = table_cells(line)
        if cells is None or len(cells) <= max(columns.values()):
            continue
        task_cell = cells[0].strip()
        oracle_cell = cells[1].strip()
        if not task_cell or task_cell == "---" or not oracle_cell:
            continue
        parsed: dict[str, tuple[int, int]] = {}
        for agent, column in columns.items():
            match = COUNT_RE.match(cells[column])
            if match is None:
                raise PassRateError(
                    f"summary has an invalid {agent} pass count for task {task_cell!r}"
                )
            parsed[agent] = (int(match.group(1)), int(match.group(2)))
        rows += 1
        for agent, (passed, trials) in parsed.items():
            totals[agent][0] += passed
            totals[agent][1] += trials

    if not rows or any(trials == 0 for _, trials in totals.values()):
        raise PassRateError("summary.md does not contain complete agent pass counts")
    return run_id, {
        agent: Counts(passed, trials)
        for agent, (passed, trials) in totals.items()
    }


def json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PassRateError(f"could not read Harbor result {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PassRateError(f"Harbor result is not a JSON object: {path}")
    return value


def config_agent_names(job_dir: Path, result_paths: list[Path]) -> list[str]:
    values: list[str] = []
    config_paths = [job_dir / "config.json"]
    config_paths.extend(result.parent / "config.json" for result in result_paths)
    seen: set[Path] = set()
    for config_path in config_paths:
        if config_path in seen or not config_path.is_file():
            continue
        seen.add(config_path)
        config = json_object(config_path)
        agent = config.get("agent")
        if isinstance(agent, dict):
            for key in ("name", "id", "label"):
                if agent.get(key):
                    values.append(str(agent[key]))
        agents = config.get("agents")
        if isinstance(agents, list):
            for item in agents:
                if isinstance(item, dict):
                    for key in ("name", "id", "label"):
                        if item.get(key):
                            values.append(str(item[key]))
    return values


def classify_job(job_dir: Path, result_paths: list[Path]) -> str | None:
    labels = [job_dir.name, *config_agent_names(job_dir, result_paths)]
    classified = {agent for label in labels if (agent := classify(label)) is not None}
    if "oracle" in classified:
        return "oracle"
    classified -= {"oracle"}
    if len(classified) > 1:
        raise PassRateError(
            f"Harbor job has conflicting agent identities: {job_dir} ({sorted(classified)})"
        )
    return next(iter(classified), None)


def raw_job_counts(job_dir: Path, result_paths: list[Path]) -> Counts:
    passed = 0
    finished = 0
    unfinished = 0
    for result_path in result_paths:
        result = json_object(result_path)
        if not result.get("finished_at"):
            unfinished += 1
            continue
        finished += 1
        verifier_result = result.get("verifier_result")
        rewards = verifier_result.get("rewards") if isinstance(verifier_result, dict) else None
        reward = rewards.get("reward") if isinstance(rewards, dict) else None
        if isinstance(reward, (int, float)) and not isinstance(reward, bool) and reward > 0:
            passed += 1
    if unfinished:
        raise PassRateError(
            f"Harbor job has {unfinished} unfinished trial(s): {job_dir}"
        )
    if not finished:
        raise PassRateError(f"Harbor job has no finished trials: {job_dir}")
    return Counts(passed, finished)


def collect_raw_counts(jobs_dir: Path, run_id: str) -> dict[str, Counts]:
    if not jobs_dir.is_dir():
        raise PassRateError(f"Harbor jobs directory is missing: {jobs_dir}")

    job_dirs = [
        path
        for path in sorted(jobs_dir.iterdir())
        if path.is_dir() and path.name.startswith(f"{run_id}-")
    ]
    if not job_dirs:
        raise PassRateError(
            f"no raw Harbor job output found for run {run_id!r} in {jobs_dir}"
        )

    raw: dict[str, Counts] = {}
    raw_sources: dict[str, Path] = {}
    for job_dir in job_dirs:
        result_paths = sorted(job_dir.glob("*/result.json"))
        if not result_paths:
            continue
        agent = classify_job(job_dir, result_paths)
        if agent is None or agent == "oracle":
            continue
        if agent in raw:
            raise PassRateError(
                f"multiple raw Harbor jobs found for {agent}: "
                f"{raw_sources[agent]} and {job_dir}"
            )
        raw[agent] = raw_job_counts(job_dir, result_paths)
        raw_sources[agent] = job_dir

    missing = [agent for agent in AGENTS if agent not in raw]
    if missing:
        raise PassRateError(
            "raw Harbor output is missing agent jobs: " + ", ".join(missing)
        )
    return raw


def format_counts(counts: Counts) -> str:
    return f"{counts.passed}/{counts.trials}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--jobs", type=Path, required=True)
    args = parser.parse_args()

    try:
        run_id, summary_counts = parse_summary(args.summary)
        raw_counts = collect_raw_counts(args.jobs, run_id)
        mismatches = [
            f"{agent}: summary {format_counts(summary_counts[agent])}, "
            f"harbor-jobs {format_counts(raw_counts[agent])}"
            for agent in AGENTS
            if summary_counts[agent] != raw_counts[agent]
        ]
        if mismatches:
            raise PassRateError(
                "trajectory summary disagrees with raw Harbor output: "
                + "; ".join(mismatches)
            )
    except PassRateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    rates = [raw_counts[agent].passed / raw_counts[agent].trials for agent in AGENTS]
    average = sum(rates) / len(rates)
    if average >= 0.5:
        print(
            "ERROR: average Claude/Codex/Gemini pass rate must be below 50% "
            f"(raw Harbor output reports {average * 100:.1f}%); make the task "
            "scientifically harder and rerun the agent campaign before submission",
            file=sys.stderr,
        )
        return 1

    rendered = ", ".join(
        f"{agent.title()} {format_counts(raw_counts[agent])} "
        f"({raw_counts[agent].passed / raw_counts[agent].trials * 100:.1f}%)"
        for agent in AGENTS
    )
    print(
        "Trajectory pass-rate check (raw harbor-jobs cross-check): "
        f"{rendered}; average {average * 100:.1f}% (< 50%)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
