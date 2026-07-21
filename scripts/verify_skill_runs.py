#!/usr/bin/env python3
"""Verify the skill-run audit chain before a task is submitted.

The audit is compliance evidence, not a tamper-proof signature. It does make
the expected skill order, target, skill revision, transcript, and exit status
machine-checkable in a submitted checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


FIELDS = (
    "run_id",
    "started_at_utc",
    "ended_at_utc",
    "skill",
    "runner",
    "status",
    "exit_code",
    "target",
    "skill_sha256",
    "output_log",
    "output_sha256",
)
SKILLS = ("task-fixer", "task-review", "trajectory-review")
AUDIT_HEADER = "# " + "\t".join(FIELDS)


@dataclass(frozen=True)
class Record:
    values: dict[str, str]
    line_number: int
    started: datetime
    ended: datetime


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_inside(root: Path, value: str) -> Path | None:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def relative_to_root(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def parse_timestamp(value: str, field: str, line_number: int) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"line {line_number}: invalid {field}: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"line {line_number}: {field} has no timezone")
    return parsed


def parse_records(log_path: Path, errors: list[str]) -> list[Record]:
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        errors.append(f"cannot read {log_path}: {exc}")
        return []

    if not lines or lines[0] != AUDIT_HEADER:
        errors.append(f"{log_path} has an invalid or missing audit header")
        return []

    records: list[Record] = []
    for line_number, line in enumerate(lines[1:], start=2):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != len(FIELDS):
            errors.append(
                f"line {line_number}: expected {len(FIELDS)} tab-separated fields, got {len(parts)}"
            )
            continue
        values = dict(zip(FIELDS, parts))
        try:
            started = parse_timestamp(values["started_at_utc"], "started_at_utc", line_number)
            ended = parse_timestamp(values["ended_at_utc"], "ended_at_utc", line_number)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if ended < started:
            errors.append(f"line {line_number}: ended_at_utc precedes started_at_utc")
        try:
            int(values["exit_code"])
        except ValueError:
            errors.append(f"line {line_number}: exit_code is not an integer")
        records.append(Record(values, line_number, started, ended))
    return records


def latest_pass(
    records: list[Record],
    skill: str,
    target_match,
    root: Path,
    current_hash: str,
    errors: list[str],
) -> Record | None:
    candidates = [
        record
        for record in records
        if record.values["skill"] == skill
        and record.values["status"] == "COMPLETED"
        and record.values["exit_code"] == "0"
        and target_match(record.values["target"])
    ]
    if not candidates:
        errors.append(f"no successful {skill} run was recorded for the required target")
        return None

    record = max(candidates, key=lambda item: item.ended)
    values = record.values
    if values["skill_sha256"] != current_hash:
        errors.append(
            f"line {record.line_number}: {skill} used skill hash {values['skill_sha256']}, "
            f"but the current skill hash is {current_hash}"
        )

    output_path = resolve_inside(root, values["output_log"])
    if output_path is None or not output_path.is_file():
        errors.append(
            f"line {record.line_number}: transcript is missing or outside the repository: "
            f"{values['output_log']}"
        )
    else:
        actual_output_hash = sha256_file(output_path)
        if actual_output_hash != values["output_sha256"]:
            errors.append(
                f"line {record.line_number}: transcript hash does not match {values['output_log']}"
            )
        transcript = output_path.read_text(encoding="utf-8", errors="replace")
        if f"run_id={values['run_id']}" not in transcript:
            errors.append(f"line {record.line_number}: transcript lacks its run_id")
        if f"skill={skill}" not in transcript:
            errors.append(f"line {record.line_number}: transcript lacks its skill name")

    target_path = resolve_inside(root, values["target"])
    if target_path is None or not target_path.is_dir():
        errors.append(
            f"line {record.line_number}: recorded target is missing or outside the repository: "
            f"{values['target']}"
        )
    return record


def describe(record: Record | None) -> str:
    if record is None:
        return "missing"
    values = record.values
    return f"COMPLETED line {record.line_number} ({values['started_at_utc']} -> {values['ended_at_utc']})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task",
        default="task",
        help="task directory, relative to this repository (default: task)",
    )
    parser.add_argument(
        "--trajectory",
        help="specific trajectory/run directory that trajectory-review must have reviewed",
    )
    parser.add_argument(
        "--log",
        default="skill-runs.log",
        help="audit log path, relative to this repository (default: skill-runs.log)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    errors: list[str] = []

    task_path = resolve_inside(root, args.task)
    if task_path is None or not task_path.is_dir():
        errors.append(f"task directory is missing or outside the repository: {args.task}")
        task_rel = ""
    else:
        task_rel = relative_to_root(root, task_path)
        task_toml = task_path / "task.toml"
        if not task_toml.is_file():
            errors.append(f"task.toml is missing from {task_rel}")
        else:
            try:
                task_config = tomllib.loads(task_toml.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError) as exc:
                errors.append(f"could not read {task_rel}/task.toml: {exc}")
            else:
                environment = task_config.get("environment", {})
                if not isinstance(environment, dict) or environment.get("allow_internet") is not False:
                    errors.append(
                        f"{task_rel}/task.toml must set [environment].allow_internet = false"
                    )

    trajectory_path = None
    trajectory_rel = None
    if args.trajectory:
        trajectory_path = resolve_inside(root, args.trajectory)
        if trajectory_path is None or not trajectory_path.is_dir():
            errors.append(
                f"trajectory directory is missing or outside the repository: {args.trajectory}"
            )
        else:
            trajectory_rel = relative_to_root(root, trajectory_path)

    log_path = resolve_inside(root, args.log)
    if log_path is None or not log_path.is_file():
        errors.append(f"audit log is missing or outside the repository: {args.log}")
        records: list[Record] = []
    else:
        records = parse_records(log_path, errors)

    current_hashes: dict[str, str] = {}
    for skill in SKILLS:
        agents_file = root / ".agents" / "skills" / skill / "SKILL.md"
        claude_file = root / ".claude" / "skills" / skill / "SKILL.md"
        if not agents_file.is_file() or not claude_file.is_file():
            errors.append(f"missing skill mirror for {skill}")
            continue
        agents_hash = sha256_file(agents_file)
        claude_hash = sha256_file(claude_file)
        if agents_hash != claude_hash:
            errors.append(f".agents and .claude copies differ for {skill}")
        current_hashes[skill] = agents_hash

    def task_target(target: str) -> bool:
        return target == task_rel

    def trajectory_target(target: str) -> bool:
        if trajectory_rel is not None:
            return target == trajectory_rel
        return target == task_rel or target.startswith("trajectories/")

    fixer = latest_pass(
        records, "task-fixer", task_target, root, current_hashes.get("task-fixer", ""), errors
    ) if "task-fixer" in current_hashes else None
    review = latest_pass(
        records, "task-review", task_target, root, current_hashes.get("task-review", ""), errors
    ) if "task-review" in current_hashes else None
    trajectory = latest_pass(
        records,
        "trajectory-review",
        trajectory_target,
        root,
        current_hashes.get("trajectory-review", ""),
        errors,
    ) if "trajectory-review" in current_hashes else None

    if fixer and review and fixer.ended > review.started:
        errors.append("task-fixer must finish before the successful task-review run starts")
    if review and trajectory and review.ended > trajectory.started:
        errors.append("task-review must finish before the successful trajectory-review run starts")

    if errors:
        print("Skill audit check: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Skill audit check: PASS")
    print(f"- task-fixer: {describe(fixer)}")
    print(f"- task-review: {describe(review)}")
    print(f"- trajectory-review: {describe(trajectory)}")
    print(f"- audit log: {relative_to_root(root, log_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
