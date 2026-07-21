# Authoring guide

## Motivation and intended flow

These tasks are being created to train and evaluate AI systems on realistic
scientific workflows in the drug discovery pipeline. A good task captures work that a researcher could plausibly perform in their own lab or analysis pipeline, including real data, method choices, validation, and a meaningful scientific result.

The task author creates three connected pieces:

1. `instruction.md` describes the scientific question, available inputs,
   constraints, and exact outputs that an agent must produce.
2. The reference workflow in `task/solution/`—normally `solve.py`, together
   with `solve.sh` and `process.md`—shows how an expert would solve the task.
3. The verifier in `task/tests/` checks independent, substantive properties of
   the submitted outputs.

Before asking models to solve the task, we run the reference workflow against
the tests to confirm that the task and its evaluation are working as intended.
We then give the same instruction and public task environment to three
different agents. Each agent must create its own solution without seeing the
reference implementation, hidden truth, or verifier-only fixtures. The agents'
outputs are evaluated by the tests and their work is reviewed afterward.

The target difficulty is important: a human expert with the stated data and
instruction should be able to produce a correct solution, while the task
should be difficult enough that the agents may fail or disagree. This exposes
where scientific reasoning, method selection, implementation, and validation
remain challenging for the models.

The instruction is the agent's entire scientific specification. Tests must not
require files, fields, keys, methods, thresholds, units, or other properties
that the instruction does not ask the agent to produce. If a property matters
to the evaluation, state it clearly in `instruction.md`; otherwise an agent
failure may reflect an underspecified task rather than a genuine scientific
failure.

 Follow these steps in order; the sections under step 3 explain how to build a scientifically credible, hermetic task before running the fixer and reviews.

## 1. Clone the repository

Create a new task project from the scaffold and choose a concise task slug:

```bash
git clone https://github.com/Aligned-HQ/beaker-scaffold.git <task-project>
cd <task-project>
```

Keep the task in its own checkout. The skill wrappers, audit log, transcripts,
Harbor evidence, and trajectory archive are all part of the handoff.

## 2. Check the local authoring toolchain

Before editing a task, run the project setup check:

```bash
./scripts/check-setup.sh
```

It checks Python 3.11+, Git, make, ripgrep, hashing utilities, Claude Code or
Codex, Harbor, Docker and its reachable daemon, the vendored
`harbor_runner.py` and its local Docker smoke mode, the project-level
`task_implemention.toml` rubric, the mirrored skills, the skill wrappers, the
audit log, and the non-strict scaffold contract. It does not install software,
build images, authenticate services, or make network calls.

The Harbor runner, Docker smoke test, and task-review rubric are part of this
repository, so the documented commands use them directly.

The check also reminds authors to measure built runtime and verifier images with
`docker image inspect`; the 2 GB image policy cannot be established until the
task images have actually been built.

For Modal runs, both task Dockerfiles must make the target explicit on every
base image line:

```dockerfile
FROM --platform=linux/amd64 python:3.12-slim
```

## 2b. Install or update required tools and libraries

`check-setup.sh` is intentionally read-only: it reports missing tools but does
not install packages or contact network services. If it reports a failure,
install or update the missing dependency using the package source approved for
your workstation, then rerun the check. For example:

```bash
python3 -m pip install --upgrade modal
./scripts/check-setup.sh
```

Install or update Docker Desktop/Engine, Harbor, Codex or Claude Code, Git,
Make, and ripgrep as needed. Start the Docker daemon before running image
checks. These downloads are for the authoring machine; the task environment
must still declare `allow_internet = false` and work without internet access.

## 3. Edit the task bundle

### 3.1 Decide whether the workflow is worth benchmarking

Before writing files, name the real practitioner and the decision supported by the result. Each task should represent a realistic scientific workflow that the agent might encounter in a real-world scenario in the drug discovery pipeline. The tasks should focus on the part of the pipeline you claimed the task for. The work should plausibly take an expert several focused hours because of scientific judgment, competing methods, uncertainty, and validation—not because of a large amount of formatting.

The task should have:

- a concrete research objective and a meaningful audience;
- public or vendored inputs that are realistic enough to support that objective;
- several plausible approaches, with intermediate observations that influence later choices;
- at least one substantive machine-checkable output, normally alongside a memo, diagnostic, or decision log;
- a deterministic or explicitly controlled evaluation that does not depend on a live service.

Do not turn a textbook calculation, a row-count exercise, or a schema puzzle into a scientific story. Do not compensate for an easy task by making the prompt long or the output schema enormous.

### 3.2 Fill the task bundle

The required task layout is:

```text
task/
├── instruction.md
├── task.toml
├── README.md
├── environment/
│   ├── Dockerfile
│   └── data/
├── solution/
│   ├── solve.sh
│   ├── solve.py or another real implementation
│   └── process.md
└── tests/
    ├── Dockerfile
    ├── test.sh
    ├── test_outputs.py
    └── data/
```

`solution/process.md` is required even when the reference implementation is short. It should explain the intended domain workflow, decisions, validation, and output generation without revealing hidden answers. A long implementation belongs in a separate file, not a heredoc in `solve.sh`.

Use `task/environment/data/` for files the agent is allowed to inspect. Use `task/tests/data/` for verifier-only truth or fixtures. If a verifier needs a public input, duplicate it deliberately and check that the copies byte-match. Never copy `solution/`, hidden answer files, or `tests/` into the agent runtime image.

### 3.3 Write the agent contract

`instruction.md` should state the end state in concise prose:

1. What scientific question is being answered?
2. Which input files are available at absolute paths, and what are their formats, units, and important columns or dimensions?
3. Which constraints matter scientifically?
4. Which exact output paths and schemas must be produced?

Leave meaningful method selection to the agent. Avoid an ordered recipe, exact reference equations when deriving them is the substance of the task, prescribed library calls, hidden thresholds, feature-engineering recipes, or instructions to reproduce the reference solution. Every filename, key, column, unit, environment variable, and output checked by the verifier must be stated in the prompt or be obvious from visible data.


### 3.4 Make the runtime hermetic

In `environment/Dockerfile`:

- define `WORKSPACE_DIR`, `DATA_DIR`, `OUTPUT_DIR`, `OUTPUT_PATH`, `SOLUTION_DIR`, `TESTS_DIR`, and `LOG_DIR` once;
- use paths relative to the Docker build context (`COPY data/ ${DATA_DIR}/`);
- install only agent-facing dependencies, with pinned Python package versions;
- install the bootstrap toolchain (`curl`, `ca-certificates`, `ripgrep`, and `git`) in the final image stage when installed-agent runs are expected;
- create the configured non-root `agent` user in the final stage and give it write access to the workspace and output directories;
- never copy `solution/`, `tests/`, expected outputs, or hidden truth into the image;
- remove apt lists after `apt-get install`.

Every `FROM` line must explicitly use `--platform=linux/amd64`; this is checked
by `harbor_runner.py` before it invokes Harbor. If `[environment].docker_image`
is used instead, the runner inspects the registry manifest and rejects an OCI
index or any platform other than Linux/amd64.

For generated data, check in a deterministic generator such as `environment/generate_data.py`, run it in a builder stage, and copy only the generated public inputs into the final runtime stage. Do not generate hidden answers into the agent image.

### 3.5 Isolate and harden the verifier

The scaffold defaults to `environment_mode = "separate"`. The verifier build context is `task/tests/`, so its Dockerfile must use `COPY` paths relative to that directory:

```dockerfile
COPY test.sh ${TESTS_DIR}/test.sh
COPY test_outputs.py ${TESTS_DIR}/test_outputs.py
COPY data/ ${TESTS_DIR}/data/
```

Pre-install verifier dependencies in `tests/Dockerfile`; do not run `apt-get`, `pip install`, `curl ... | sh`, or other network-dependent setup from `tests/test.sh`. The verifier may be started after the agent container is gone, so every non-artifact file it reads must be baked into the verifier image or be a declared persistent input.

`tests/test_outputs.py` should execute the submitted outputs or pipeline and assert independent scientific facts: numeric ranges, relationships, model residuals, held-out performance, physical constraints, data-derived consistency, or similar evidence. It should not grep source code or grade report wording. Tolerances must admit independent correct methods and reject scientifically wrong ones; explain their calibration in `verification_explanation` in `task.toml`.

`tests/test.sh` must write the reward even when pytest fails. The robust pattern is:

```bash
#!/usr/bin/env bash
set -uo pipefail

TESTS_DIR="${TESTS_DIR:-/tests}"
LOG_DIR="${LOG_DIR:-/logs/verifier}"
mkdir -p "${LOG_DIR}"

python3 -m pytest "${TESTS_DIR}/test_outputs.py" -rA \
  2>&1 | tee "${LOG_DIR}/pytest.log"
status=${PIPESTATUS[0]}
if [ "${status}" -eq 0 ]; then
  echo 1 > "${LOG_DIR}/reward.txt"
else
  echo 0 > "${LOG_DIR}/reward.txt"
fi
exit "${status}"
```

Add CTRF output when the runner or Harbor campaign consumes it. Keep the exact output filenames in `task.toml` artifacts, and make the solution write those files under `OUTPUT_DIR`.

### 3.6 Complete `task.toml` deliberately

Use only fields supported by the Harbor version used by the runner. The review rubric recognizes these sections and fields:

- root: `schema_version`, `task`, `metadata`, `verifier`, `agent`, `environment`, `solution`, `source`, and `artifacts`;
- `[task]`: `name`, `description`;
- `[metadata]`: author fields, `category`, `tags`, `expert_time_estimate_hours`, and the three explanation fields;
- `[verifier]`: timeout, user, env, `environment_mode`, and optional verifier environment settings;
- `[agent]`: timeout and user;
- `[environment]`: build timeout, image/resources, internet, env, skills/MCP, and healthcheck settings;
- `[solution]`: env.

The scaffold intentionally uses a namespaced placeholder task name, a non-zero time estimate, concrete resource defaults, populated tags, and non-empty explanation text so an author can see the complete shape. Replace those values with task-specific facts. Do not add invented fields such as `prerequisites`, `estimated_difficulty`, `notes`, or an informal `skills` list.

The three explanation fields have different jobs:

- `difficulty_explanation` names the scientific bottleneck, why it is hard for an expert, how realistic the data are, and who would do the work;
- `solution_explanation` summarizes the reference strategy and key insights without pretending that a different implementation was used;
- `verification_explanation` describes every substantive check and justifies numeric bounds or tolerances, including evidence that alternative correct approaches fit.

Set timeouts and CPU, memory, storage, and GPU resources from the actual workflow. A slow computer is not a substitute for scientific difficulty.

## 4. Run the task-fixer script

Run `task-fixer` after the first complete edit of the task. The fixer should
survey the entire task and correct only task-local reproducibility and
reviewability issues:

- missing required layout files;
- hardcoded workstation or staging paths;
- data not copied into the final runtime stage;
- wrong Docker build-context prefixes;
- missing runtime or verifier dependencies;
- missing configured users or output permissions;
- artifact declarations that do not match produced files;
- missing `solution/process.md`;
- verifier installs or missing reward handling;
- leaked task-local `.claude/`, `.agents/`, `task_implementation.toml`, caches, or `.DS_Store` files.

Use the project wrapper so the run is recorded in the audit log:

```bash
./scripts/run-task-fixer.sh task
```

## 5. Run the task-review script

Run `task-review` after the fixer. It must read every criterion in the
repository rubric and provide a PASS / FAIL / N/A scorecard with file-and-line
evidence. Pay particular attention to:

- practitioner plausibility and real scientific value;
- the task difficulty and tool usage/agent behavior
- a concise prompt with no solution recipe;
- actual computation in the reference solution;
- 1:1 instruction-to-test alignment;
- deterministic, secure, anti-cheat-resistant evaluation;
- reviewable explanations and calibrated tolerances;
- valid metadata, task name, resources, artifacts, and Docker layout.

```bash
./scripts/run-task-review.sh task
```

## 6. Edit until task-review passes

If the review reports a failure, edit the task files to address the cited
evidence and rerun the review. Repeat until the task passes. If an edit affects
paths, dependencies, Docker build contexts, users, artifacts, or reward
handling, rerun `task-fixer` before running `task-review` again.

The wrappers record UTC timestamps, the exact local skill revision, runner, exit
status, and hashes for captured transcripts in `skill-runs.log`. The eventual
submission check requires successful fixer → review → trajectory-review runs in
that order. This is compliance evidence rather than a tamper-proof signature,
so keep the transcript directory and inspect the final diff before upload.

Do not treat an Oracle pass as proof that the task is good. The reference
solution can pass a broken verifier.

## 7. Run the Docker smoke test

After task-review passes, run the local smoke test. It builds the task's
`environment/Dockerfile`, runs `solution/solve.sh`, runs `tests/test.sh` in an
offline Linux/amd64 Docker container, and preserves verifier logs and copied
outputs under `task/.runner-logs/`:

```bash
./harbor_runner.py task --smoke-test
```

The smoke mode does not build or run the separate Harbor verifier image and does
not start an agent or Modal job. Use it to catch local packaging, path,
solution, and reward-wiring errors before the remote run. Because the smoke
test runs the verifier script inside the environment image, any dependency it
needs must be available there; the Harbor run remains the authoritative check
for the separate verifier image.

## 8. Run the Harbor task runner

Configure Modal control-plane credentials and provider credentials through your
approved secret mechanism before starting. Do not put API keys in task files or
commit an `.env` file.

```bash
./harbor_runner.py task
# Example credential plumbing; pass names, not secret values.
./harbor_runner.py task --modal-secret openai-api-key \
  --modal-secret anthropic-api-key --modal-secret google-api-key
```

The Modal control-plane token and the provider credentials are separate. Keep
the former in the normal Modal CLI/SDK credential store and the latter in
named Modal Secrets; the runner only passes secret names to Harbor. The
`--env-file` and `--agent-env` options remain available for non-secret
configuration, but values supplied there may be captured by Harbor's resolved
job configuration and should not be used for provider keys.

The runner gives each live run a random, per-run Modal App name and stores the
ownership record in `harbor-jobs/<run-id>.modal-run.json`. The Oracle and agent
jobs for one run share that app so they can be stopped together; different
users never share the default Harbor app. On normal completion, Ctrl-C, or
SIGTERM, the runner stops only the recorded app, which terminates its running
containers. It uses the Modal CLI when available and the Modal Python SDK as a
fallback. Do not disable `--shutdown-modal` in a shared workspace unless an
external owner is responsible for cleanup. A hard kill (`SIGKILL`) or host
power loss cannot execute local cleanup, so retain Harbor/Modal lifetime
limits as the final safety net.

The default run ID includes a random suffix. Use `--run-id ID --resume` to
resume an interrupted Harbor run; starting another live run with an already
claimed ID is rejected.

## 9. Run the trajectory-review script

After the Harbor campaign completes, review the archived trajectory. Replace
`<run-id>` with the identifier printed by the runner:

```bash
./scripts/run-trajectory-review.sh trajectories/<run-id>
```

The trajectory review distinguishes genuine scientific failures from structural
task bugs, prompt/test mismatches, tolerance problems, missing keys, and other
clerical issues. Keep the complete trajectory archive with the submission.

## 10. Run strict scaffold validation

Run the final strict static check after the trajectory review:

```bash
python3 scripts/validate_scaffold.py --strict
```

The setup check in step 2 already runs the non-strict contract check. The
strict mode rejects scaffold markers and requires real input data or a checked-
in deterministic generator. Resolve every failure before handoff.

## 11. Upload and submit on Workbench

Before uploading, verify the skill-run audit:

```bash
./scripts/verify-skill-runs.sh \
  --task task \
  --trajectory trajectories/<run-id>
```

Remove generated caches, check that all intended inputs are tracked, and
inspect the final diff. The project should read coherently from prompt to
solution process to verifier to trajectory evidence. Then upload and submit the
task on Workbench. If a non-specialist cannot tell what a successful result
means, improve the task README and metadata rather than adding more test code.
