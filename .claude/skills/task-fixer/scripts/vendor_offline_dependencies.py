#!/usr/bin/env python3
"""Vendor and verify a Linux/amd64 wheelhouse for an offline task image.

Downloading is an authoring-time operation.  The resulting wheelhouse is
intended to be copied into a task Docker build and consumed with pip's
``--no-index --find-links`` options; this helper never belongs in the task
runtime image.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn


DEFAULT_PLATFORM = "manylinux2014_x86_64"
MANIFEST_NAME = "wheelhouse-manifest.json"
REQUIREMENTS_NAME = "requirements.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download or verify pinned binary dependencies for a Linux/amd64 "
            "offline Docker build. Run download mode on an approved "
            "authoring machine, not inside the task image."
        )
    )
    parser.add_argument("packages", nargs="*", metavar="PACKAGE")
    parser.add_argument(
        "--task",
        required=True,
        type=Path,
        help="task directory; the output wheelhouse must be inside it",
    )
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="task-local wheelhouse directory to create or verify",
    )
    parser.add_argument(
        "--requirements",
        action="append",
        type=Path,
        default=[],
        help="additional pinned requirements file(s) to vendor",
    )
    parser.add_argument(
        "--python-version",
        default="3.12",
        help="target Python version, for example 3.12 (default: 3.12)",
    )
    parser.add_argument(
        "--platform",
        default=DEFAULT_PLATFORM,
        help=f"target pip platform (default: {DEFAULT_PLATFORM})",
    )
    parser.add_argument(
        "--implementation",
        default="cp",
        help="target Python implementation for pip (default: cp)",
    )
    parser.add_argument(
        "--abi",
        help="target ABI; defaults to cp<python version> for CPython",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable whose pip should perform the operation",
    )
    parser.add_argument(
        "--find-links",
        action="append",
        type=Path,
        default=[],
        help="approved local wheel directory to use as an additional source",
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="vendor only from --find-links directories; never contact an index",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="remove existing wheelhouse wheels and generated metadata first",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="resolve requirements from the existing wheelhouse without indexes",
    )
    return parser.parse_args()


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def read_requirement_file(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        fail(f"could not read requirements file {path}: {error}")

    requirements: list[str] = []
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            fail(
                f"{path}:{line_number} contains a pip option; keep indexes and "
                "trusted-host settings outside the task requirements"
            )
        requirements.append(line)
    return requirements


def collect_requirements(args: argparse.Namespace) -> list[str]:
    requirements: list[str] = []
    for path in args.requirements:
        requirements.extend(read_requirement_file(path))
    requirements.extend(args.packages)
    unique: list[str] = []
    for requirement in requirements:
        if requirement not in unique:
            unique.append(requirement)
    for requirement in unique:
        if "==" not in requirement:
            fail(
                f"requirement is not exactly pinned: {requirement!r}; use a "
                "form such as package==1.2.3"
            )
    return unique


def target_abi(args: argparse.Namespace) -> str:
    if args.abi:
        return args.abi
    digits = re.sub(r"[^0-9]", "", args.python_version)
    if args.implementation == "cp" and len(digits) >= 2:
        return f"cp{digits}"
    return "none"


def validate_target(args: argparse.Namespace) -> None:
    platform = args.platform.lower()
    if "x86_64" not in platform and "amd64" not in platform:
        fail(
            f"unsupported target platform {args.platform!r}; this client accepts "
            "Linux/amd64 wheels only"
        )
    if any(token in platform for token in ("aarch64", "arm64", "armv7", "ppc64", "s390x")):
        fail(f"unsupported non-amd64 target platform {args.platform!r}")


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    task = args.task.resolve()
    out = args.out.resolve()
    if not task.is_dir():
        fail(f"task directory does not exist: {task}")
    try:
        out.relative_to(task)
    except ValueError:
        fail(f"wheelhouse output must be inside the task directory: {out}")
    return task, out


def requirements_path(out: Path) -> Path:
    return out / REQUIREMENTS_NAME


def generated_paths(out: Path) -> list[Path]:
    return [requirements_path(out), out / MANIFEST_NAME]


def clean_wheelhouse(out: Path) -> None:
    if not out.exists():
        return
    for path in out.iterdir():
        if path.suffix == ".whl" or path in generated_paths(out):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


def pip_common_args(args: argparse.Namespace) -> list[str]:
    return [
        "--disable-pip-version-check",
        "--only-binary",
        ":all:",
        "--platform",
        args.platform,
        "--python-version",
        args.python_version,
        "--implementation",
        args.implementation,
        "--abi",
        target_abi(args),
    ]


def source_args(args: argparse.Namespace) -> list[str]:
    arguments: list[str] = []
    for source in args.find_links:
        source_path = source.expanduser().resolve()
        if not source_path.is_dir():
            fail(f"local --find-links directory does not exist: {source_path}")
        arguments.extend(["--find-links", str(source_path)])
    if args.no_index:
        arguments.append("--no-index")
    return arguments


def run_pip(args: argparse.Namespace, pip_args: list[str]) -> None:
    command = [args.python, "-m", "pip", *pip_args]
    print("Running: " + " ".join(command[:6]) + " ...")
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        fail(f"could not run {args.python!r}; install Python and pip on the authoring host")
    except subprocess.CalledProcessError as error:
        fail(
            f"pip exited with status {error.returncode}. Use an approved package "
            "index or provide a complete local wheelhouse, then rerun this helper"
        )


def write_requirements(out: Path, requirements: list[str]) -> None:
    try:
        requirements_path(out).write_text(
            "".join(f"{requirement}\n" for requirement in requirements),
            encoding="utf-8",
        )
    except OSError as error:
        fail(f"could not write {requirements_path(out)}: {error}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(out: Path, args: argparse.Namespace, requirements: list[str]) -> None:
    wheels = []
    for path in sorted(out.glob("*.whl")):
        wheels.append({"name": path.name, "sha256": sha256(path)})
    manifest = {
        "format": 1,
        "target": {
            "platform": args.platform,
            "python_version": args.python_version,
            "implementation": args.implementation,
            "abi": target_abi(args),
        },
        "requirements": requirements,
        "wheels": wheels,
    }
    try:
        (out / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        fail(f"could not write {out / MANIFEST_NAME}: {error}")


def vendor(args: argparse.Namespace, out: Path, requirements: list[str]) -> None:
    if not requirements:
        fail("provide at least one pinned package or --requirements file")
    out.mkdir(parents=True, exist_ok=True)
    if args.clean:
        clean_wheelhouse(out)
    write_requirements(out, requirements)
    run_pip(
        args,
        [
            "download",
            "--dest",
            str(out),
            *source_args(args),
            *pip_common_args(args),
            *requirements,
        ],
    )
    wheels = sorted(out.glob("*.whl"))
    if not wheels:
        fail(f"pip completed without producing wheels in {out}")
    write_manifest(out, args, requirements)
    print(f"Vendored {len(wheels)} wheel(s) in {out}")
    print(f"Requirements: {requirements_path(out)}")
    print(f"Manifest: {out / MANIFEST_NAME}")


def verify(args: argparse.Namespace, out: Path) -> None:
    requirements = requirements_path(out)
    if not out.is_dir():
        fail(f"wheelhouse directory does not exist: {out}")
    if not requirements.is_file():
        fail(f"missing generated requirements file: {requirements}")
    wheels = sorted(out.glob("*.whl"))
    if not wheels:
        fail(f"wheelhouse contains no .whl files: {out}")

    with tempfile.TemporaryDirectory(prefix="offline-wheelhouse-check-") as temp_dir:
        run_pip(
            args,
            [
                "download",
                "--no-index",
                "--find-links",
                str(out),
                "--dest",
                temp_dir,
                *pip_common_args(args),
                "-r",
                str(requirements),
            ],
        )
    print(f"Verified {len(wheels)} local wheel(s) resolve without an index")


def main() -> int:
    args = parse_args()
    validate_target(args)
    _task, out = resolve_paths(args)
    requirements = collect_requirements(args)
    if args.verify:
        verify(args, out)
    else:
        vendor(args, out, requirements)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
