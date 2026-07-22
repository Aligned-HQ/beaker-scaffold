#!/usr/bin/env python3
"""Dependency-free regression checks for the vendored Harbor runner."""
from __future__ import annotations

import re
import sys
import io
import tarfile
import tempfile
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harbor_runner


def check_run_identity() -> None:
    with tempfile.TemporaryDirectory(prefix="beaker-runner-test-") as raw:
        jobs_dir = Path(raw) / "jobs"
        manifest, app_name = harbor_runner.resolve_modal_run_identity(
            jobs_dir,
            "same-run",
            resume=False,
            archive_only=False,
            dry_run=False,
        )
        assert manifest.is_file()
        assert app_name.startswith("beaker-same-run-")
        assert len(app_name) <= 64

        try:
            harbor_runner.resolve_modal_run_identity(
                jobs_dir,
                "same-run",
                resume=False,
                archive_only=False,
                dry_run=False,
            )
        except SystemExit as exc:
            assert "already claimed" in str(exc)
        else:
            raise AssertionError("a second live process reused the run ID")

        _, resumed_app_name = harbor_runner.resolve_modal_run_identity(
            jobs_dir,
            "same-run",
            resume=True,
            archive_only=False,
            dry_run=False,
        )
        assert resumed_app_name == app_name


def check_names_are_valid_and_unique() -> None:
    run_ids = [harbor_runner.default_run_id() for _ in range(100)]
    assert len(set(run_ids)) == len(run_ids)
    assert all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value) for value in run_ids)
    app_names = [harbor_runner.make_modal_app_name("same-run", value) for value in run_ids]
    assert len(set(app_names)) == len(app_names)
    assert all(len(value) <= 64 for value in app_names)


def check_cleanup_is_targeted() -> None:
    cli_calls: list[str] = []
    sdk_calls: list[str] = []
    original_stop = harbor_runner.stop_modal_app_via_cli
    original_sdk_stop = harbor_runner.stop_modal_app_via_sdk
    original_completed = harbor_runner.SHUTDOWN_MODAL_COMPLETED
    harbor_runner.stop_modal_app_via_cli = lambda app_name: cli_calls.append(app_name) or False
    harbor_runner.stop_modal_app_via_sdk = lambda app_name: sdk_calls.append(app_name) or True
    harbor_runner.SHUTDOWN_MODAL_COMPLETED = False
    try:
        harbor_runner.shutdown_modal_app(True, "beaker-owned-run")
    finally:
        harbor_runner.stop_modal_app_via_cli = original_stop
        harbor_runner.stop_modal_app_via_sdk = original_sdk_stop
        harbor_runner.SHUTDOWN_MODAL_COMPLETED = original_completed
    assert cli_calls == ["beaker-owned-run"]
    assert sdk_calls == ["beaker-owned-run"]


def check_sigterm_enters_cleanup_path() -> None:
    try:
        harbor_runner.handle_sigterm(15, None)
    except KeyboardInterrupt:
        return
    raise AssertionError("SIGTERM handler did not enter the cleanup path")


def check_smoke_mode_wiring() -> None:
    task_root = Path(__file__).resolve().parents[1] / "task"
    project = harbor_runner.load_smoke_project(task_root)
    assert project.solution_dir.is_dir()
    assert project.tests_dir.is_dir()
    assert "OUTPUT_DIR" not in harbor_runner.smoke_project_env(project.task_toml)
    rendered = harbor_runner.redact_smoke_command(
        ["docker", "run", "-e", "API_KEY=not-for-logs", "image"]
    )
    assert "not-for-logs" not in rendered
    assert "<redacted>" in rendered


def check_remote_bundle_wiring() -> None:
    task_root = Path(__file__).resolve().parents[1] / "task"
    archive, digest, size = harbor_runner.build_remote_task_bundle(task_root)
    assert archive.startswith(b"\x1f\x8b")
    assert re.fullmatch(r"sha256:[a-f0-9]{64}", digest)
    assert size == len(archive)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        names = {member.name for member in tar.getmembers()}
    assert all(".git/" not in name for name in names)
    assert all("harbor-jobs/" not in name for name in names)
    assert "task/task.toml" in names
    assert "task/instruction.md" in names
    assert harbor_runner.remote_url("https://example.test/v1", "/v1/harbor/runs/hr_abc") == "https://example.test/v1/harbor/runs/hr_abc"


def check_remote_policy_wiring() -> None:
    args = SimpleNamespace(run=[], n_concurrent=5, default_concurrency=3, repeats=2)
    payload = harbor_runner.remote_agent_payload(args)
    assert all(item["concurrency"] == 5 for item in payload)
    assert sum(item["concurrency"] for item in payload) * args.repeats == 30
    args.repeats = 3
    try:
        harbor_runner.remote_agent_payload(args)
    except harbor_runner.RemoteInputError as exc:
        assert "30-trial" in str(exc)
    else:
        raise AssertionError("remote policy allowed more than 30 total trials")


if __name__ == "__main__":
    check_run_identity()
    check_names_are_valid_and_unique()
    check_cleanup_is_targeted()
    check_sigterm_enters_cleanup_path()
    check_smoke_mode_wiring()
    check_remote_bundle_wiring()
    check_remote_policy_wiring()
    print("Harbor runner isolation checks passed")
