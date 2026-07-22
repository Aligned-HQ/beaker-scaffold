#!/usr/bin/env python3
"""Verify the Markdown skill reports and status file before submission."""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SKILLS = ("task-fixer", "task-review", "trajectory-review")
VALID_STATUSES = {"Not Run", "Run", "Pass", "Fail"}


@dataclass(frozen=True)
class Report:
    skill: str
    status: str
    run_id: str
    runner: str
    target: str
    started: datetime
    ended: datetime
    skill_sha256: str
    path: Path


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


def parse_timestamp(value: str, field: str, path: Path, errors: list[str]) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{path}: invalid {field}: {value!r}")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{path}: {field} has no timezone")
        return None
    return parsed


def markdown_table_rows(text: str) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) < 2 or set(parts[0]) <= {"-", ":"}:
            continue
        rows[parts[0]] = parts[1:]
    return rows


def unformat(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`"):
        value = value[1:-1]
    return value.strip()


def parse_status_file(path: Path, errors: list[str]) -> dict[str, dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read {path}: {exc}")
        return {}
    if not text.startswith("# Skill status"):
        errors.append(f"{path} has an invalid header")
    rows: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 5:
            errors.append(f"{path}: malformed status row: {line}")
            continue
        skill = unformat(parts[0])
        rows[skill] = {
            "status": unformat(parts[1]),
            "last_run": unformat(parts[2]),
            "target": unformat(parts[3]),
            "report": parts[4],
        }
    for skill in SKILLS:
        if skill not in rows:
            errors.append(f"{path}: missing status row for {skill}")
        elif rows[skill]["status"] not in VALID_STATUSES:
            errors.append(
                f"{path}: invalid status for {skill}: {rows[skill]['status']!r}"
            )
    return rows


def report_field(rows: dict[str, list[str]], field: str) -> str | None:
    values = rows.get(field)
    if not values:
        return None
    return unformat(values[0])


def parse_report(path: Path, skill: str, errors: list[str]) -> Report | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read {path}: {exc}")
        return None

    heading = f"# Skill report: {skill}"
    if not text.startswith(heading):
        errors.append(f"{path}: missing heading {heading!r}")

    status_match = re.search(r"^\*\*Status:\*\*\s+(Not Run|Run|Pass|Fail)\s*$", text, re.MULTILINE)
    if not status_match:
        errors.append(f"{path}: missing Markdown status")
        status = "Fail"
    else:
        status = status_match.group(1)

    rows = markdown_table_rows(text)
    required = ("Run ID", "Skill", "Runner", "Target", "Started (UTC)", "Finished (UTC)", "Exit code", "Skill SHA-256")
    missing = [field for field in required if report_field(rows, field) is None]
    if missing:
        errors.append(f"{path}: missing report fields: {', '.join(missing)}")
        return None

    report_skill = report_field(rows, "Skill") or ""
    if report_skill != skill:
        errors.append(f"{path}: report names skill {report_skill!r}, expected {skill!r}")

    started = parse_timestamp(report_field(rows, "Started (UTC)") or "", "Started (UTC)", path, errors)
    ended = parse_timestamp(report_field(rows, "Finished (UTC)") or "", "Finished (UTC)", path, errors)
    if started is None or ended is None:
        return None
    if ended < started:
        errors.append(f"{path}: Finished (UTC) precedes Started (UTC)")

    try:
        int(report_field(rows, "Exit code") or "")
    except ValueError:
        errors.append(f"{path}: Exit code is not an integer")

    return Report(
        skill=skill,
        status=status,
        run_id=report_field(rows, "Run ID") or "",
        runner=report_field(rows, "Runner") or "",
        target=report_field(rows, "Target") or "",
        started=started,
        ended=ended,
        skill_sha256=report_field(rows, "Skill SHA-256") or "",
        path=path,
    )


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
        "--status",
        default="skill-status.md",
        help="status Markdown file, relative to this repository (default: skill-status.md)",
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
                    errors.append(f"{task_rel}/task.toml must set [environment].allow_internet = false")

    trajectory_rel: str | None = None
    if args.trajectory:
        trajectory_path = resolve_inside(root, args.trajectory)
        if trajectory_path is None or not trajectory_path.is_dir():
            errors.append(f"trajectory directory is missing or outside the repository: {args.trajectory}")
        else:
            trajectory_rel = relative_to_root(root, trajectory_path)

    status_path = resolve_inside(root, args.status)
    if status_path is None or not status_path.is_file():
        errors.append(f"status file is missing or outside the repository: {args.status}")
        status_rows: dict[str, dict[str, str]] = {}
    else:
        status_rows = parse_status_file(status_path, errors)

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

    reports: dict[str, Report] = {}
    for skill in SKILLS:
        report_path = root / "skill-reports" / f"{skill}.md"
        if not report_path.is_file():
            errors.append(f"missing skill report: {relative_to_root(root, report_path)}")
            continue
        report = parse_report(report_path, skill, errors)
        if report is None:
            continue
        reports[skill] = report
        row = status_rows.get(skill)
        if row is None:
            continue
        if row["status"] != report.status:
            errors.append(
                f"{relative_to_root(root, status_path)}: {skill} status {row['status']!r} "
                f"does not match report status {report.status!r}"
            )
        if row["status"] != "Pass":
            errors.append(f"{skill} status is {row['status']!r}; a passing report is required")
        if row["last_run"] != report.ended.strftime("%Y-%m-%dT%H:%M:%SZ"):
            errors.append(f"{skill}: status timestamp does not match the report")
        if report.skill_sha256 != current_hashes.get(skill, ""):
            errors.append(f"{skill}: report used an outdated skill hash")

        expected_target = task_rel
        if skill == "trajectory-review" and trajectory_rel is not None:
            expected_target = trajectory_rel
        if skill == "trajectory-review" and trajectory_rel is None:
            target_matches = report.target == task_rel or report.target.startswith("trajectories/")
        else:
            target_matches = report.target == expected_target
        if not target_matches:
            errors.append(
                f"{skill}: report target {report.target!r} does not match the required target"
            )

    if reports.get("task-fixer") and reports.get("task-review"):
        if reports["task-fixer"].ended > reports["task-review"].started:
            errors.append("task-fixer must finish before task-review starts")
    if reports.get("task-review") and reports.get("trajectory-review"):
        if reports["task-review"].ended > reports["trajectory-review"].started:
            errors.append("task-review must finish before trajectory-review starts")

    if errors:
        print("Skill report check: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Skill report check: PASS")
    for skill in SKILLS:
        report = reports[skill]
        print(f"- {skill}: {report.status} ({relative_to_root(root, report.path)})")
    print(f"- status: {relative_to_root(root, status_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
