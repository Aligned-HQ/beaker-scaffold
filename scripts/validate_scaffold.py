#!/usr/bin/env python3
"""Validate the editable task scaffold before an authoring or review run.

The checker is deliberately static and dependency-free. It catches missing
layout files, invalid TOML, common Docker build-context mistakes, leaked host
paths, missing canonical environment variables, and reward-file hazards. It is
not a replacement for task-fixer, task-review, Harbor, or trajectory-review.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import stat
import sys
import tomllib
from pathlib import Path
from typing import Any


REQUIRED_FILES = (
    "README.md",
    "instruction.md",
    "task.toml",
    "environment/Dockerfile",
    "solution/solve.sh",
    "solution/process.md",
    "tests/Dockerfile",
    "tests/test.sh",
    "tests/test_outputs.py",
)

CANONICAL_VARS = (
    "WORKSPACE_DIR",
    "DATA_DIR",
    "OUTPUT_DIR",
    "SOLUTION_DIR",
    "TESTS_DIR",
    "LOG_DIR",
)

PLACEHOLDER_MARKERS = (
    "TEMPLATE ONLY",
    "TODO",
    "REPLACE_ME",
    "Replace with",
    "Replace this",
    "replace-me/",
    "<task",
    "<project",
)

HOST_PATH_RE = re.compile(r"/(?:Users|Volumes|home)/[^\s'\"`]+")
BAD_ENV_COPY_RE = re.compile(r"^\s*COPY\s+(?:environment|tests|solution)(?:/|\s)", re.MULTILINE)
RUNTIME_INSTALL_RE = re.compile(
    r"(?:apt-get\s+install|pip\s+install|curl\s+.*(?:sh|bash))", re.IGNORECASE
)
DOCKER_FROM_RE = re.compile(
    r"^\s*FROM(?:\s+--platform=(?P<platform>\S+))?\s+(?P<image>\S+)",
    re.IGNORECASE,
)

ALLOWED_ROOT_KEYS = {
    "schema_version",
    "artifacts",
    "task",
    "metadata",
    "verifier",
    "agent",
    "environment",
    "solution",
    "source",
}
ALLOWED_TABLE_KEYS = {
    "task": {"name", "description", "multi_step_reward_strategy"},
    "metadata": {
        "author_name",
        "author_email",
        "author_organization",
        "difficulty_explanation",
        "solution_explanation",
        "verification_explanation",
        "category",
        "tags",
        "expert_time_estimate_hours",
    },
    "verifier": {"timeout_sec", "env", "user", "environment_mode", "environment"},
    "agent": {"timeout_sec", "user"},
    "environment": {
        "build_timeout_sec",
        "docker_image",
        "cpus",
        "memory_mb",
        "storage_mb",
        "gpus",
        "gpu_types",
        "allow_internet",
        "env",
        "skills_dir",
        "mcp_servers",
        "healthcheck",
    },
    "solution": {"env"},
}


class Checker:
    def __init__(self, root: Path, strict: bool) -> None:
        self.root = root
        self.task = root / "task"
        self.strict = strict
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        if self.strict:
            self.errors.append(message)
        else:
            self.warnings.append(message)

    def check_layout(self) -> None:
        if not self.task.is_dir():
            self.error("missing task/ directory")
            return
        for relative in REQUIRED_FILES:
            path = self.task / relative
            if not path.is_file():
                self.error(f"missing required file: task/{relative}")
        for relative in ("environment/data", "tests/data"):
            path = self.task / relative
            if not path.is_dir():
                self.error(f"missing required directory: task/{relative}")
            elif (
                not any(child.name != ".gitkeep" for child in path.iterdir())
                and relative == "environment/data"
                and not (self.task / "environment/generate_data.py").is_file()
            ):
                self.warn(f"{relative} has no vendored input/fixture yet")

    def check_toml(self) -> dict[str, Any]:
        path = self.task / "task.toml"
        if not path.is_file():
            return {}
        try:
            config = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            self.error(f"task/task.toml is invalid TOML: {exc}")
            return {}

        for key in config:
            if key not in ALLOWED_ROOT_KEYS:
                self.error(f"task/task.toml has an unrecognized root field: {key}")
        for section_name, allowed in ALLOWED_TABLE_KEYS.items():
            section = config.get(section_name)
            if not isinstance(section, dict):
                continue
            for key in section:
                if key not in allowed:
                    self.error(
                        f"task/task.toml has an unrecognized field: [{section_name}].{key}"
                    )

        if config.get("schema_version") != "1.1":
            self.warn('task/task.toml should declare schema_version = "1.1"')
        artifacts = config.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            self.error("task/task.toml must have a non-empty top-level artifacts list")
        else:
            for artifact in artifacts:
                if not isinstance(artifact, str) or not artifact.startswith(
                    "/workspace/output/"
                ):
                    self.error(f"artifact is not a canonical output path: {artifact!r}")

        task_config = config.get("task", {})
        if (
            not isinstance(task_config, dict)
            or not task_config.get("name")
            or not task_config.get("description")
        ):
            self.error("task/task.toml needs [task].name and [task].description")

        metadata = config.get("metadata", {})
        if not isinstance(metadata, dict):
            self.error("[metadata] must be a TOML table")
        else:
            for key in (
                "difficulty_explanation",
                "solution_explanation",
                "verification_explanation",
            ):
                if not str(metadata.get(key, "")).strip():
                    self.error(f"[metadata].{key} must not be empty")
            estimate = metadata.get("expert_time_estimate_hours", 0)
            if not isinstance(estimate, (int, float)) or estimate <= 0:
                self.error("[metadata].expert_time_estimate_hours must be positive")
            if not metadata.get("tags"):
                self.warn("[metadata].tags is empty")

        verifier = config.get("verifier", {})
        agent = config.get("agent", {})
        environment = config.get("environment", {})
        if not isinstance(verifier, dict) or verifier.get("environment_mode") != "separate":
            self.warn('default scaffold expects [verifier].environment_mode = "separate"')
        for section_name, section in (("verifier", verifier), ("agent", agent)):
            try:
                valid_timeout = isinstance(section, dict) and float(
                    section.get("timeout_sec", 0)
                ) > 0
            except (TypeError, ValueError):
                valid_timeout = False
            if not valid_timeout:
                self.error(f"[{section_name}].timeout_sec must be positive")
        for key in ("build_timeout_sec", "cpus", "memory_mb", "storage_mb"):
            try:
                valid_resource = isinstance(environment, dict) and float(
                    environment.get(key, 0)
                ) > 0
            except (TypeError, ValueError):
                valid_resource = False
            if not valid_resource:
                self.error(f"[environment].{key} must be positive")
        if not isinstance(environment, dict) or environment.get("allow_internet") is not False:
            self.error("client policy requires [environment].allow_internet = false")
        return config

    def check_executables(self) -> None:
        for relative in ("solution/solve.sh", "tests/test.sh"):
            path = self.task / relative
            if path.is_file() and not (path.stat().st_mode & stat.S_IXUSR):
                self.error(f"{relative} is not executable")

    def check_dockerfiles(self) -> None:
        environment_path = self.task / "environment/Dockerfile"
        tests_path = self.task / "tests/Dockerfile"
        for dockerfile_path in (environment_path, tests_path):
            if not dockerfile_path.is_file():
                continue
            text = dockerfile_path.read_text(encoding="utf-8")
            from_lines = [
                (line_number, match.group("platform"))
                for line_number, line in enumerate(text.splitlines(), 1)
                if (match := DOCKER_FROM_RE.match(line))
            ]
            if not from_lines:
                self.error(f"{dockerfile_path.relative_to(self.root)} has no FROM instruction")
            for line_number, platform in from_lines:
                if platform != "linux/amd64":
                    self.error(
                        f"{dockerfile_path.relative_to(self.root)}:{line_number} must use "
                        "FROM --platform=linux/amd64 for Modal"
                    )

        if environment_path.is_file():
            text = environment_path.read_text(encoding="utf-8")
            for variable in CANONICAL_VARS:
                if variable not in text:
                    self.warn(f"environment/Dockerfile does not define or reference {variable}")
            if "COPY data/" not in text:
                self.warn("environment/Dockerfile does not visibly copy data/ into the runtime image")
            if BAD_ENV_COPY_RE.search(text):
                self.error(
                    "environment/Dockerfile uses a context-prefixed COPY for environment/tests/solution"
                )
            if re.search(r"^\s*COPY\s+(?:solution|tests)(?:/|\s)", text, re.MULTILINE):
                self.error("environment/Dockerfile copies solution/ or tests/ into the agent image")
        if tests_path.is_file():
            text = tests_path.read_text(encoding="utf-8")
            for fragment in ("COPY test.sh", "COPY test_outputs.py", "TESTS_DIR", "LOG_DIR"):
                if fragment not in text:
                    self.warn(f"tests/Dockerfile is missing the expected fragment: {fragment}")
            if "COPY data/" not in text:
                self.warn("tests/Dockerfile does not copy verifier data/")

    def check_scripts(self) -> None:
        solve = self.task / "solution/solve.sh"
        verifier = self.task / "tests/test.sh"
        if solve.is_file():
            text = solve.read_text(encoding="utf-8")
            if "SOLUTION_DIR" not in text:
                self.warn("solution/solve.sh does not use SOLUTION_DIR")
        if verifier.is_file():
            text = verifier.read_text(encoding="utf-8")
            for fragment in ("LOG_DIR", "reward.txt", "pytest"):
                if fragment not in text:
                    self.error(f"tests/test.sh is missing reward/verifier handling: {fragment}")
            if RUNTIME_INSTALL_RE.search(text):
                self.error(
                    "tests/test.sh appears to install packages or execute a network bootstrap at verification time"
                )
            if "set -e" in text and "PIPESTATUS" not in text and "if " not in text:
                self.warn("tests/test.sh uses set -e without an obvious failure-safe reward path")

    def check_paths_and_markers(self) -> None:
        candidates = [
            self.task / "instruction.md",
            self.task / "task.toml",
            self.task / "README.md",
            self.task / "environment/Dockerfile",
            self.task / "solution/solve.sh",
            self.task / "solution/solve.py",
            self.task / "solution/process.md",
            self.task / "tests/Dockerfile",
            self.task / "tests/test.sh",
            self.task / "tests/test_outputs.py",
        ]
        for path in candidates:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            match = HOST_PATH_RE.search(text)
            if match:
                self.error(
                    f"machine-local absolute path in {path.relative_to(self.root)}: {match.group(0)}"
                )
            for marker in PLACEHOLDER_MARKERS:
                if marker in text:
                    self.warn(
                        f"placeholder marker {marker!r} remains in {path.relative_to(self.root)}"
                    )
        instruction_path = self.task / "instruction.md"
        if instruction_path.is_file():
            text = instruction_path.read_text(encoding="utf-8")
            for path_marker in ("/workspace/data", "/workspace/output"):
                if path_marker not in text:
                    self.warn(f"instruction.md does not mention {path_marker}")

    def check_duplicate_public_data(self) -> None:
        environment_data = self.task / "environment/data"
        verifier_data = self.task / "tests/data"
        if not environment_data.is_dir() or not verifier_data.is_dir():
            return
        for source in environment_data.iterdir():
            target = verifier_data / source.name
            if source.is_file() and target.is_file() and source.name != ".gitkeep":
                source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
                target_hash = hashlib.sha256(target.read_bytes()).hexdigest()
                if source_hash != target_hash:
                    self.warn(
                        f"duplicated public fixture differs: {source.relative_to(self.root)} vs {target.relative_to(self.root)}"
                    )

    def run(self) -> int:
        self.check_layout()
        self.check_toml()
        self.check_executables()
        self.check_dockerfiles()
        self.check_scripts()
        self.check_paths_and_markers()
        self.check_duplicate_public_data()
        for warning in self.warnings:
            print(f"WARN: {warning}")
        for error in self.errors:
            print(f"ERROR: {error}")
        if self.errors:
            print(
                f"\nScaffold check failed: {len(self.errors)} error(s), {len(self.warnings)} warning(s)."
            )
            return 1
        print(f"Scaffold check passed: {len(self.warnings)} warning(s).")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root containing task/",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat scaffold warnings and placeholder markers as errors",
    )
    args = parser.parse_args(argv)
    return Checker(args.root.resolve(), args.strict).run()


if __name__ == "__main__":
    sys.exit(main())
