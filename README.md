# Beaker scientific-workflow scaffold

This repository is a starter project for a reproducible scientific-computing task in the terminal-bench style. It is deliberately editable: the files under `task/` contain a placeholder content so the container and verifier wiring can be exercised, but the placeholder task is not a publishable benchmark until all the
placeholder content is replaced with a real scientific task.

The maximum runtime for a task is 60 minutes. Keep the task workflow and its
configured timeouts within this limit.



## Quick start

1. Clone the repository into a new project directory:

   ```bash
   git clone https://github.com/Aligned-HQ/beaker-scaffold.git <task-project>
   cd <task-project>
   ```

2. Check your local authoring setup:

   ```bash
   ./scripts/check-setup.sh
   ```

   This checks Python 3.11+, Git, Make, ripgrep, Codex or Claude Code, Harbor,
   Modal, Docker, the vendored runner, the rubric, and the mirrored skills.

**2b.** If the check reports a missing or outdated dependency, install or update
it with your approved package manager, then run the check again. For example,
update the Modal Python SDK with:

```bash
python3 -m pip install --upgrade modal
```

Install or update Docker Desktop/Engine, Harbor, Codex or Claude Code, Git,
Make, and ripgrep using the package source approved for your workstation. Start
the Docker daemon before continuing. These downloads are for the authoring
machine; task environments must still run without internet access.

The runner uses Rich for terminal panels, tables, and transfer progress. Install
its pinned host-side dependency with:

```bash
python3 -m pip install -r requirements.txt
```

3. Edit `task/instruction.md`, `task/task.toml`, `task/environment/`,
   `task/solution/`, and `task/tests/`. Keep the prompt, artifacts, solver, and
   verifier as one contract.
4. Run the task-fixer script:

   ```bash
   ./scripts/run-task-fixer.sh task
   ```

   The skill wrappers give task-fixer and task-review Docker-capable execution
   by default so they can inspect the task images: Codex uses its Docker-capable
   sandbox and Claude Code uses its bypass-permissions mode. Use
   `./scripts/run-task-fixer.sh task --docker-access off` for a static-only
   run, or `--docker-access on` to make the setting explicit. If dependencies
   are not already available in an approved offline source, vendor them on the
   authoring machine with the helper documented in the task-fixer skill, then
   install them in the Dockerfile with `--no-index --find-links`.

5. Run the task-review script:

   ```bash
   ./scripts/run-task-review.sh task
   ```

6. If task-review reports a failure, edit the task files to address the
   evidence, rerun task-review, and repeat until the task passes. If a change
   affects paths, dependencies, or container wiring, rerun task-fixer first.
7. Run the local Docker smoke test:

   ```bash
   ./harbor_runner.py task --no-remote --smoke-test
   ```

8. Run the Harbor task runner. The default submits the single task to the
   Workbench Harbor service; use `--no-remote` for a local Modal run.
   Do not put API keys in task files or commit an `.env` file.

   ```bash
   # Default: Workbench remote run; create .env first and add the runner token.
   cp .env.example .env # first time only
   ./harbor_runner.py task
   ```

   Each user must use their own scoped `WORKBENCH_RUNNER_TOKEN`; never share one token
   across users. See the authoring guide for acquiring a token.


9. Review the completed trajectory:

   ```bash
   ./scripts/run-trajectory-review.sh trajectories
   ```

   The runner clears and replaces the direct `trajectories/` output only after
   a successful, exception-free run. The average Claude/Codex/Gemini pass rate
   must be strictly below 50% (Oracle is ignored), meaning the agents fail
   more than half the time on average. If the rate is 50% or higher, make the
   scientific task harder and rerun the authoring sequence before submitting.

10. Run the final strict scaffold validation:

    ```bash
    python3 scripts/validate_scaffold.py --strict
    ```

11. Before uploading, verify the skill reports and status, then upload and submit the
    task on Workbench:

    ```bash
    ./scripts/verify-skill-runs.sh \
      --task task \
      --trajectory trajectories
    ```

    Package the submission directories together:

    ```bash
    ./scripts/package-submission.sh
    ```

    If `submission/` already exists, the script asks for confirmation before
    replacing it. Packaging validates the archived trial evidence in
    `trajectories/` (including `summary.json` or the direct agent trial
    folders); it does not require the local Harbor job-output directory. The
    average Claude/Codex/Gemini pass rate should be strictly below 50%; Oracle
    is ignored. If the task does not meet that criterion, packaging prints a
    red warning but still creates `submission/` so the result can be inspected.
    Upload the resulting `submission/` directory to Workbench.

## Layout

```text
.
├── README.md                         # project-level handoff
├── harbor_runner.py                  # Docker smoke test and isolated Modal/Harbor runner
├── authoring-guide.md                 # task-fixer/review/trajectory workflow
├── task_implemention.toml             # rubric consumed by task-review
├── scripts/
│   ├── check-setup.sh                # local toolchain and Docker check
│   ├── validate_scaffold.py           # fast static contract check
│   ├── test_harbor_runner.py          # runner isolation regression checks
│   ├── test_package_submission.py     # trajectory packaging regression checks
│   ├── run-skill.sh                   # shared agent-skill runner
│   ├── run-task-fixer.sh              # task-fixer entrypoint
│   ├── run-task-review.sh             # task-review entrypoint
│   ├── run-trajectory-review.sh       # trajectory-review entrypoint
│   ├── package-submission.sh          # assemble the Workbench submission
│   └── verify-skill-runs.sh            # submission report/status checker
├── skill-reports/                     # latest Markdown result from each skill
│   ├── task-fixer.md
│   ├── task-review.md
│   └── trajectory-review.md
├── skill-status.md                    # overwritten latest status for each skill
├── task/
│   ├── README.md                      # maintainer notes for this task
│   ├── instruction.md                 # agent-facing scientific contract
│   ├── task.toml                      # Harbor metadata and resources
│   ├── environment/
│   │   ├── Dockerfile                 # agent runtime image only
│   │   └── data/                      # public runtime inputs
│   ├── solution/
│   │   ├── solve.sh                   # Oracle entrypoint
│   │   ├── solve.py                   # derivation, not a stored answer
│   │   └── process.md                 # intended expert workflow
│   └── tests/
│       ├── Dockerfile                 # isolated verifier image
│       ├── test.sh                    # verifier entrypoint/reward writer
│       ├── test_outputs.py            # executable scientific assertions
│       └── data/                      # verifier-only fixtures or truth
└── trajectories/
    └── README.md                      # archive contract; no fake runs
```

## Skill reports

Each skill wrapper overwrites its Markdown result in `skill-reports/`. The
shared `skill-status.md` file is overwritten at the start and end of every run;
the current skill is marked `Run` while active and `Pass` or `Fail` when it
finishes. The final checker reads these reports and requires passing
task-fixer, task-review, and trajectory-review results in order. The task-fixer
report retains the final handoff rather than the agent's intermediate tool
transcript. The task-review report retains the practitioner-plausibility section
through its verdicts, top fixes, and N/A notes; trajectory-review retains its
complete verdict.

## Authoring boundary

The agent should see the scientific question, public inputs, constraints, and exact output schema in `task/instruction.md`. It should not see the reference solution, hidden truth, or verifier-only fixtures. Put agent inputs in `task/environment/data/`; put hidden references in `task/tests/data/` and copy them only into the separate verifier image. Keep all paths rooted in Harbor's canonical variables: `WORKSPACE_DIR`, `DATA_DIR`, `OUTPUT_DIR`, `SOLUTION_DIR`, `TESTS_DIR`, and `LOG_DIR`.

The starter `task/` uses `input.csv` and a simple summary only to prove that the mounts, output paths, and reward file work. Replace that contract before asking agents to solve the task. The finished task should represent a real expert workflow with meaningful method choices, intermediate validation, and a substantive machine-checkable result; a long schema or a toy transform is not enough.


## Authoring checklist
The detailed checklist and common failure modes are in [`authoring-guide.md`](authoring-guide.md).
