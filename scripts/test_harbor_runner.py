#!/usr/bin/env python3
"""Dependency-free regression checks for the vendored Harbor runner."""
from __future__ import annotations

import re
import sys
import io
import contextlib
import json
import os
import tarfile
import tempfile
from dataclasses import replace
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


def check_jobs_dir_is_cleared_for_new_runs() -> None:
    with tempfile.TemporaryDirectory(prefix="beaker-jobs-cleanup-test-") as raw:
        jobs_dir = Path(raw) / "harbor-jobs"
        jobs_dir.mkdir()
        (jobs_dir / "old-run.log").write_text("old", encoding="utf-8")
        nested = jobs_dir / "old-job"
        nested.mkdir()
        (nested / "result.json").write_text("{}", encoding="utf-8")
        symlink = jobs_dir / "old-link"
        symlink.symlink_to(jobs_dir / "old-run.log")

        harbor_runner.clear_harbor_jobs_dir(jobs_dir)

        assert list(jobs_dir.iterdir()) == []


def check_snapshot_results_map_to_original_task() -> None:
    with tempfile.TemporaryDirectory(prefix="beaker-archive-mapping-test-") as raw:
        root = Path(raw)
        original_task = root / "task"
        original_task.mkdir()
        jobs_dir = root / "harbor-jobs"
        job_dir = jobs_dir / "run-claude-opus"
        trial_dir = job_dir / "run.agent__trial"
        trial_dir.mkdir(parents=True)
        snapshot = jobs_dir / "run.agent-task-snapshot"
        result_path = trial_dir / "result.json"
        result_path.write_text(
            json.dumps(
                {
                    "task_id": {"path": str(snapshot)},
                    "finished_at": "2026-07-22T21:19:06Z",
                    "verifier_result": {"rewards": {"reward": 1.0}},
                }
            ),
            encoding="utf-8",
        )
        result = harbor_runner.JobResult(
            agent="claude-code",
            model="anthropic/claude-opus-4-7",
            label="claude-opus",
            job_name="run-claude-opus",
            n_trials_expected=1,
            returncode=0,
            elapsed_sec=1.0,
            job_dir=str(job_dir),
            runner_log=str(jobs_dir / "run-claude-opus.runner.log"),
            resumed=False,
        )

        archives = harbor_runner.collect_trial_archives([result], [original_task])

        assert list(archives) == [original_task.resolve()]
        assert len(archives[original_task.resolve()]) == 1
        assert archives[original_task.resolve()][0].agent == "claude-code"


def check_successful_archive_uses_agent_names_and_oracle() -> None:
    with tempfile.TemporaryDirectory(prefix="beaker-trajectory-archive-test-") as raw:
        root = Path(raw)
        original_task = root / "task"
        original_task.mkdir()
        (original_task / "instruction.md").write_text("task", encoding="utf-8")
        jobs_dir = root / "harbor-jobs"
        run_id = "archive-test"
        snapshot = jobs_dir / f"{run_id}.agent-task-snapshot"
        oracle_snapshot = jobs_dir / f"{run_id}.oracle-task-snapshot"
        agent_specs = [
            ("claude-code", "claude-opus", "anthropic/claude-opus-4-7"),
            ("codex", "codex-gpt-5-5", "openai/gpt-5.5"),
            ("gemini-cli", "gemini-3-1-pro-preview", "google/gemini-3.1-pro-preview"),
        ]
        results = []
        for agent, label, model in agent_specs:
            job_name = f"{run_id}-{label}"
            job_dir = jobs_dir / job_name
            trial_dir = job_dir / f"{run_id}.agent__{agent}"
            trial_dir.mkdir(parents=True)
            (trial_dir / "result.json").write_text(
                json.dumps(
                    {
                        "task_id": {"path": str(snapshot)},
                        "finished_at": "2026-07-22T21:19:06Z",
                        "verifier_result": {"rewards": {"reward": 1.0}},
                    }
                ),
                encoding="utf-8",
            )
            results.append(
                harbor_runner.JobResult(
                    agent=agent,
                    model=model,
                    label=label,
                    job_name=job_name,
                    n_trials_expected=1,
                    returncode=0,
                    elapsed_sec=1.0,
                    job_dir=str(job_dir),
                    runner_log=str(jobs_dir / f"{job_name}.runner.log"),
                    resumed=False,
                )
            )

        oracle_dir = jobs_dir / f"{run_id}-oracle"
        oracle_trial_dir = oracle_dir / f"{run_id}.oracle__trial"
        oracle_trial_dir.mkdir(parents=True)
        (oracle_dir / "config.json").write_text(
            json.dumps({"agents": [{"name": "oracle"}]}),
            encoding="utf-8",
        )
        (oracle_trial_dir / "result.json").write_text(
            json.dumps(
                {
                    "task_id": {"path": str(oracle_snapshot)},
                    "finished_at": "2026-07-22T21:19:06Z",
                    "verifier_result": {"rewards": {"reward": 1.0}},
                }
            ),
            encoding="utf-8",
        )

        summary_path = harbor_runner.write_summary(jobs_dir, original_task, run_id, results)
        markdown_path = harbor_runner.write_markdown_summary(
            jobs_dir=jobs_dir,
            tasks=[original_task],
            results=results,
            run_id=run_id,
        )
        destination = root / "trajectories"
        destination.mkdir()
        (destination / "stale-run.marker").write_text("old", encoding="utf-8")
        moved = harbor_runner.archive_completed_task_runs(
            tasks=[original_task],
            results=results,
            summary_path=summary_path,
            markdown_summary_path=markdown_path,
            run_id=run_id,
            destination_root=destination,
        )

        trajectory_root = destination
        assert moved == [destination]
        assert all((trajectory_root / agent).is_dir() for agent, _, _ in agent_specs)
        assert (trajectory_root / "oracle").is_dir()
        assert not (trajectory_root / "stale-run.marker").exists()
        trajectory_summary = trajectory_root / "summary.md"
        assert trajectory_summary.is_file()
        summary_text = trajectory_summary.read_text(encoding="utf-8")
        assert "| Task | Oracle | claude-code | codex | gemini-cli | Status |" in summary_text
        assert "| task | pass, reward 1 |" in summary_text

        retained = trajectory_root / "previous-success.marker"
        retained.write_text("keep", encoding="utf-8")
        partial_result = replace(results[0], n_trials_expected=2)
        harbor_runner.archive_completed_task_runs(
            tasks=[original_task],
            results=[partial_result],
            summary_path=summary_path,
            markdown_summary_path=markdown_path,
            run_id="partial-follow-up",
            destination_root=destination,
        )
        assert retained.is_file()
        assert (trajectory_root / "partial-follow-up").is_dir()


def check_remote_archive_promotion_uses_direct_layout() -> None:
    with tempfile.TemporaryDirectory(prefix="beaker-remote-archive-test-") as raw:
        root = Path(raw)
        destination = root / "trajectories"
        archive = destination / "hr_remote-run"
        source = archive / "example-task" / "trajectories"
        (source / "oracle" / "trial-0").mkdir(parents=True)
        (source / "claude-code" / "trial-0").mkdir(parents=True)
        (source / "summary.md").write_text("# remote summary\n", encoding="utf-8")
        (destination / ".hr_remote-run.sha256").write_text("sha256:test\n", encoding="utf-8")
        (destination / "stale-output").mkdir(parents=True)
        (destination / "stale-output" / "old.txt").write_text("old", encoding="utf-8")

        promoted = harbor_runner.promote_remote_trajectory_archive(archive, destination)

        assert promoted == destination.resolve()
        assert (destination / "summary.md").is_file()
        assert (destination / "oracle" / "trial-0").is_dir()
        assert (destination / "claude-code" / "trial-0").is_dir()
        assert not archive.exists()
        assert not (destination / ".hr_remote-run.sha256").exists()
        assert not (destination / "stale-output").exists()


def check_remote_partial_archive_matches_local_layout() -> None:
    with tempfile.TemporaryDirectory(prefix="beaker-remote-partial-archive-test-") as raw:
        root = Path(raw)
        destination = root / "trajectories"
        archive = destination / "hr_remote-run"
        source = archive / "example-task" / "trajectories"
        (source / "oracle" / "trial-0").mkdir(parents=True)
        (source / "codex" / "trial-0").mkdir(parents=True)
        (source / "summary.md").write_text("# partial remote summary\n", encoding="utf-8")
        (destination / ".hr_remote-run.sha256").write_text("sha256:test\n", encoding="utf-8")
        (destination / "previous-success").mkdir(parents=True)

        preserved = harbor_runner.preserve_remote_trajectory_archive(
            archive,
            destination,
            "example-task",
        )

        assert preserved == archive.resolve()
        assert (archive / "summary.md").is_file()
        assert (archive / "example-task" / "trajectories" / "oracle").is_dir()
        assert (archive / "example-task" / "trajectories" / "codex").is_dir()
        assert (destination / "previous-success").is_dir()
        assert not (destination / ".hr_remote-run.sha256").exists()


def check_remote_archive_flag_matches_local_behavior() -> None:
    original_request = harbor_runner.remote_json_request
    original_poll = harbor_runner.poll_remote_status
    requests: list[str] = []

    with tempfile.TemporaryDirectory(prefix="beaker-remote-no-archive-test-") as raw:
        root = Path(raw)
        task_root = root / "task"
        task_root.mkdir()
        (task_root / "task.toml").write_text("", encoding="utf-8")
        (task_root / "instruction.md").write_text("task\n", encoding="utf-8")
        for directory in ("solution", "tests", "environment"):
            (task_root / directory).mkdir()
        jobs_dir = root / "harbor-jobs"
        trajectories_dir = root / "trajectories"

        def fake_remote_json_request(
            method: str,
            url: str,
            token: str,
            **kwargs: object,
        ) -> tuple[int, dict[str, object], dict[str, str]]:
            requests.append(url)
            if method == "POST" and url.endswith("/runs"):
                return 201, {"run_id": "hr_123456789012", "state": "UPLOADING"}, {}
            if method == "POST" and url.endswith(":start"):
                return 200, {"state": "QUEUED"}, {}
            if method == "GET" and url.endswith("/results"):
                return 200, {"summary": {"exception_count": 0}}, {}
            raise AssertionError(f"unexpected remote request: {method} {url}")

        def fake_poll_remote_status(*args: object, **kwargs: object) -> dict[str, object]:
            return {"state": "COMPLETE", "terminal_reason": None}

        args = SimpleNamespace(
            env="modal",
            archive_only=False,
            oracle_sort=False,
            dry_run=False,
            env_file=[],
            agent_env=[],
            verifier_env=[],
            environment_kwarg=[],
            agent_kwarg=[],
            artifact=[],
            modal_secret=[],
            workbench_token="test-token",
            remote_poll_min=0.25,
            remote_poll_max=1.0,
            remote_progress_interval_sec=30.0,
            service_url="https://example.test/v1",
            run=[],
            n_concurrent=None,
            default_concurrency=3,
            repeats=1,
            jobs_dir=jobs_dir,
            run_id="remote-no-archive",
            resume=False,
            archive_completed=False,
            cancel_on_interrupt=True,
            pass_threshold=1.0,
            completed_trajectories_dir=trajectories_dir,
        )

        harbor_runner.remote_json_request = fake_remote_json_request  # type: ignore[assignment]
        harbor_runner.poll_remote_status = fake_poll_remote_status  # type: ignore[assignment]
        try:
            assert harbor_runner.run_remote(task_root, args) == 0
        finally:
            harbor_runner.remote_json_request = original_request
            harbor_runner.poll_remote_status = original_poll

    assert not any(url.endswith("/trajectories") for url in requests)
    assert not trajectories_dir.exists()


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


def check_network_split_snapshots() -> None:
    task_root = Path(__file__).resolve().parents[1] / "task"
    original_sleep = harbor_runner.time.sleep
    harbor_runner.time.sleep = lambda _seconds: None
    try:
        with tempfile.TemporaryDirectory(prefix="beaker-snapshot-test-") as raw:
            jobs_dir = Path(raw) / "jobs"
            oracle = harbor_runner.snapshot_task_root(
                task_root,
                jobs_dir,
                "snapshot-test",
                snapshot_label="oracle-task-snapshot",
                allow_internet=False,
            )
            agent = harbor_runner.snapshot_task_root(
                oracle,
                jobs_dir,
                "snapshot-test",
                snapshot_label="agent-task-snapshot",
                allow_internet=True,
            )
            assert oracle != agent
            assert harbor_runner.load_toml(oracle / "task.toml")["environment"]["allow_internet"] is False
            assert harbor_runner.load_toml(agent / "task.toml")["environment"]["allow_internet"] is True
    finally:
        harbor_runner.time.sleep = original_sleep


def check_oracle_spinner() -> None:
    class TTYBuffer(io.StringIO):
        def isatty(self) -> bool:
            return True

    output = TTYBuffer()
    display = harbor_runner.OracleProgressDisplay(output)
    display.update("Oracle progress: 0/1 result(s) finished (0.0%)")
    display.update("Oracle progress: 1/1 result(s) finished (100.0%)")
    display.finish()
    rendered = output.getvalue()
    assert "Oracle [|] progress: 0/1" in rendered
    assert "Oracle [/] progress: 1/1" in rendered
    assert "\033[K" in rendered


def check_agent_progress_order() -> None:
    specs = [
        SimpleNamespace(job_name="claude", label="claude-opus"),
        SimpleNamespace(job_name="codex", label="codex-gpt-5-5"),
        SimpleNamespace(job_name="gemini", label="gemini-pro"),
    ]
    output = io.StringIO()
    reporter = harbor_runner.ProgressReporter(specs, output)
    reporter.report(specs[2], "gemini update")
    block = output.getvalue().split("=============", 1)[0]
    assert block.index("claude-opus:") < block.index("codex-gpt-5-5:")
    assert block.index("codex-gpt-5-5:") < block.index("gemini-pro:")
    assert "gemini-pro: gemini update" in block


def check_remote_defaults_load_dotenv() -> None:
    keys = ("WORKBENCH_HARBOR_SERVICE_URL", "WORKBENCH_RUNNER_TOKEN")
    missing = object()
    original_values = {key: os.environ.get(key, missing) for key in keys}
    original_cwd = Path.cwd()
    original_run_remote = harbor_runner.run_remote
    seen: dict[str, object] = {}

    with tempfile.TemporaryDirectory(prefix="beaker-dotenv-test-") as raw:
        root = Path(raw)
        task_root = root / "task"
        task_root.mkdir()
        (task_root / "task.toml").write_text("", encoding="utf-8")
        (task_root / "instruction.md").write_text("task\n", encoding="utf-8")
        (root / ".env").write_text(
            "WORKBENCH_HARBOR_SERVICE_URL=\"https://example.test/v1\"\n"
            "export WORKBENCH_RUNNER_TOKEN=dotenv-token # local credential\n",
            encoding="utf-8",
        )

        def fake_run_remote(task: Path, args: object) -> int:
            seen["task"] = task
            seen["args"] = args
            return 0

        os.environ.pop("WORKBENCH_HARBOR_SERVICE_URL", None)
        os.environ.pop("WORKBENCH_RUNNER_TOKEN", None)
        harbor_runner.run_remote = fake_run_remote  # type: ignore[assignment]
        os.chdir(root)
        try:
            assert harbor_runner.main(["task"]) == 0
        finally:
            os.chdir(original_cwd)
            harbor_runner.run_remote = original_run_remote

    for key, value in original_values.items():
        if value is missing:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    args = seen["args"]
    assert seen["task"] == task_root.resolve()
    assert getattr(args, "service_url") == "https://example.test/v1"
    assert getattr(args, "workbench_token") == "dotenv-token"
    assert getattr(args, "cancel_on_interrupt") is True


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


def check_remote_progress_reporting() -> None:
    status = {
        "state": "AGENTS_RUNNING",
        "updated_at": "2026-07-22T12:34:56.000Z",
        "terminal_reason": None,
        "oracle": {"state": "PASS", "reward": 1.0, "exception": None},
        "agents": [
            {
                "id": "claude-opus",
                "state": "RUNNING",
                "expected_trials": 9,
                "finished_trials": 2,
                "pass_count": 1,
                "fail_count": 1,
                "exception_count": 0,
                "job_id": "hr_abc-claude-opus",
            }
        ],
    }
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        signature = harbor_runner.print_remote_progress(
            status,
            None,
            elapsed_sec=65,
        )
        same_signature = harbor_runner.print_remote_progress(
            status,
            signature,
            elapsed_sec=95,
            force=True,
        )
    rendered = output.getvalue()
    assert signature == same_signature
    assert "remote state: AGENTS_RUNNING" in rendered
    assert "remote heartbeat: AGENTS_RUNNING" in rendered
    assert "server updated: 2026-07-22T12:34:56.000Z" in rendered
    assert "agent claude-opus: RUNNING 2/9 trials" in rendered
    assert "totals: 2/9 trials finished, 1 pass, 1 fail, 0 exception" in rendered


if __name__ == "__main__":
    check_run_identity()
    check_names_are_valid_and_unique()
    check_cleanup_is_targeted()
    check_jobs_dir_is_cleared_for_new_runs()
    check_snapshot_results_map_to_original_task()
    check_successful_archive_uses_agent_names_and_oracle()
    check_remote_archive_promotion_uses_direct_layout()
    check_remote_partial_archive_matches_local_layout()
    check_remote_archive_flag_matches_local_behavior()
    check_sigterm_enters_cleanup_path()
    check_smoke_mode_wiring()
    check_network_split_snapshots()
    check_oracle_spinner()
    check_agent_progress_order()
    check_remote_defaults_load_dotenv()
    check_remote_bundle_wiring()
    check_remote_policy_wiring()
    check_remote_progress_reporting()
    print("Harbor runner isolation checks passed")
