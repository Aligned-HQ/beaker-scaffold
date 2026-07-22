---
name: trajectory-review
description: Review the latest Harbor 3-agent trajectory run for a task and decide whether failures are genuine scientific failures rather than structural task bugs, prompt-test mismatches, tolerance problems, missing or misnamed keys, or other clerical issues. Use when asked to inspect completed_trajectories, harbor-jobs, 3x agent runs, pass/fail trajectories, or whether a task failure is acceptable.
argument-hint: <task-or-run-path>
---

# Trajectory Review

Review a Harbor 3-agent run for a task. The goal is not to fix the task; it is
to decide whether observed failures are legitimate scientific failures by the
agent, or evidence that the task should be sent back to `task-fixer`.

## Client deployment gates

The client permits no internet access in task environments and caps every final
runtime or verifier image at **2 GB (2,000,000,000 bytes)**. Check these gates
alongside the trajectory evidence:

- `task.toml` must set `[environment].allow_internet = false`.
- Trial logs and task files must show no live API, download, package-install, or
  remote-database dependency during task or verifier execution.
- Use recorded `docker image inspect --format '{{.Size}}' <image-tag>` evidence
  when available. An image over the byte cap is a structural task failure.
- If the run contains no image-size evidence, the deployment gate is
  **INCONCLUSIVE**; do not infer that the cap is satisfied from a passing trial.
- If the installed Harbor agent cannot bootstrap without its online CLI download,
  classify that path as infrastructure-blocked. Do not recommend enabling
  internet access; the client must supply an approved offline/preinstalled
  adapter.

## Inputs

- A task folder, a completed trajectory folder, or a Harbor job/run id.
- Typical completed run layout:
  `completed_trajectories/agent-runs-YYYYMMDD-HHMMSS/`
- Full trial logs may live in `harbor-jobs/<same job name>-<agent>/` even when
  `completed_trajectories/.../jobs/` contains only job-level metadata.

## Workflow

1. **Find the latest relevant 3-agent run.**
   - If the user gives a completed trajectory folder, use it directly.
   - If the user gives a task folder, identify the task name/id from
     `task.toml` and search `completed_trajectories/` and `harbor-jobs/` for the
     latest `agent-runs-*` folder containing that task.
   - Prefer a run with the expected three job directories/logs for Gemini,
     Codex, and Claude. If multiple runs match, use the newest timestamp unless
     the user specifies otherwise.

2. **Read the job-level summary first.**
   - Read `summary.md` when present.
   - Read each agent job `result.json` and note:
     - number of trials,
     - rewards,
     - errored trials,
     - exception stats,
     - pass@k when present.
   - Read the resolved task configuration and record `allow_internet`; collect
     any available runtime/verifier image-size evidence.
   - Map failed trial ids from `reward_stats["0.0"]` and exception stats to
     their trial directories.

3. **Collect failure evidence from each failed trial.**
   - Read `trial.log`, `result.json`, `verifier/pytest.log`,
     `verifier/test-stdout.txt`, `verifier/reward.txt`, and artifact
     `manifest.json` when present.
   - Read only the relevant parts of agent trajectories:
     `agent/*.txt`, `agent/*.jsonl`, or `agent/trajectory.json`. Search for the
     output filenames, failed keys, exception messages, and final commands
     before loading large traces.
   - Compare failed trial artifacts with at least one passing trial artifact
     from the same run when available.

4. **Classify each failure.**
   - **Scientific failure**: the agent produced the required files and schema,
     but failed substantive scientific/numeric criteria that are clearly stated
     or implied by the task, such as wrong model selection, poor fit,
     nonphysical result, incorrect uncertainty, inadequate validation, or an
     unsupported scientific claim.
   - **Structural task bug**: missing runtime data, Docker build/copy failure,
     missing dependencies, wrong user/permissions, missing output artifacts,
     reward-file problems, no trial result, task not loaded into `lock.json`,
     verifier image missing files, agent could not run the provided tools,
     network-dependent setup under the client's offline policy, or a runtime/
     verifier image larger than 2 GB.
   - **Prompt-test mismatch**: verifier requires a filename, column, key,
     config value, hidden assumption, external source, algorithm, or output
     field that is not disclosed in `instruction.md` or visible data.
   - **Tolerance failure**: values are scientifically reasonable and align with
     task wording, but tests use overly tight absolute/relative thresholds,
     brittle seeds, exact optimizer path expectations, or unstable ordering.
   - **Clerical failure**: missing or misnamed JSON keys, CSV headers, artifact
     filenames, units, boolean fields, or report fields where the scientific
     result is otherwise present and the prompt/test contract is ambiguous or
     inconsistent.

5. **Use cross-agent evidence.**
   - If two agents pass and one fails, inspect whether the failing agent simply
     made a scientific mistake or whether tests reward one narrow formatting
     path.
   - If all three fail similarly, strongly suspect structural bug, prompt-test
     mismatch, excessive tolerance, missing data, or an underspecified task.
   - If all three pass except rare stochastic failures, check for brittle
     randomness or tolerance issues before calling the task robust.
   - Passing peer trials are evidence that the task can be solved, but they do
     not by themselves prove the failed trial is scientific; still compare the
     failure mode against the prompt and verifier.

6. **Check the task contract against the verifier.**
   - Read `instruction.md`, `task.toml`, and `tests/test_outputs.py`.
   - Confirm `[environment].allow_internet = false` and inspect task scripts and
     Dockerfiles for network operations or runtime installation steps.
   - Confirm the final runtime and verifier image sizes are each at most
     `2000000000` bytes when size evidence exists. Missing evidence leaves the
     client deployment gate INCONCLUSIVE, not passing.
   - Confirm every verifier-required output file, JSON key, CSV column, unit,
     threshold concept, and task-specific environment variable is disclosed or
     inferable.
   - Do not accept tests that grade prose wording, section names, keywords, word
     counts, tone, or report text instead of scientific evidence.
   - Do not treat missing/misnamed keys as scientific failures unless the prompt
     clearly specified the exact schema and passing trials demonstrate it is
     reasonable.

7. **Decide the disposition.**
   - **PASS trajectory review** only when failures are genuine scientific agent
     failures, or when enough agents pass and remaining failures are clearly
     agent-side scientific mistakes.
   - **FAIL trajectory review** when any failure indicates structural task
     breakage, prompt-test mismatch, brittle tolerance, hidden schema, or
     clerical contract ambiguity, an internet-policy violation, or an image over
     the client cap. Recommend `task-fixer` and cite the files.
   - **INCONCLUSIVE** when full trial logs/artifacts are missing or the required
     image-size evidence is absent. State exactly which paths or measurements
     are needed.

## Output Format

Start with `**Status:** PASS` when the verdict is `PASS`. Start with
`**Status:** FAIL` when the verdict is `FAIL` or `INCONCLUSIVE`; retain the
specific verdict below. The project wrapper saves the complete Markdown result
as `skill-reports/trajectory-review.md`.

Then start with the verdict:

- `PASS`: failures are scientific.
- `FAIL`: task needs repair before review/upload.
- `INCONCLUSIVE`: not enough trajectory evidence.

Then include:

- Run path and timestamp reviewed.
- Per-agent pass/fail table with trial ids and rewards.
- Failure classification for each failed trial.
- Evidence with file paths and concise line/log references.
- Specific `task-fixer` recommendations when verdict is `FAIL`.

Keep the report focused on failure evidence. Do not rewrite the task or modify
files unless the user explicitly asks for fixes.
