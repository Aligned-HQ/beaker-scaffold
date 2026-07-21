---
name: task-fixer
description: Fix a Harbor task folder before review by replacing hardcoded local paths
  with environment-variable based paths, vendoring referenced data into the task, and
  ensuring Python and system dependencies are installed in the correct Dockerfiles.
  Use before task-review when the user asks to fix, prep, repair, normalize, or make
  a task review-ready.
argument-hint: <path/to/task-folder>
---

# Task Fixer

Prepare a Harbor task folder for `task-review`. Make the smallest concrete edits
needed for reproducibility and reviewability.

## Client deployment constraints

These constraints are mandatory for every repaired task in this client environment:

- Set `[environment].allow_internet = false` in `task.toml`. The task runtime and
  verifier must not depend on live APIs, downloads, package installation, remote
  databases, or any other network access.
- The final runtime image and, when `environment_mode = "separate"`, the final
  verifier image must each be no larger than **2 GB (2,000,000,000 bytes)** of
  Docker image size. Measure the built image with `docker image inspect` rather
  than estimating from the Dockerfile alone.
- Vendor public inputs, verifier fixtures, wheels or source distributions needed
  for an offline build, and all executable dependencies through an approved base
  image or local files. Remove package caches and build toolchains from final
  stages when they are not needed at runtime.
- If the Harbor agent bootstrap itself requires an online CLI download, do not
  override the client policy by setting `allow_internet = true`. Record that the
  installed-agent path needs a client-approved offline/preinstalled adapter; an
  Oracle-only pass is not evidence that the task is ready for agent evaluation.

Treat a network dependency or an image over the cap as a task readiness failure,
not as a scientific failure to be hidden by changing the verifier.

## Inputs

- **Target**: a Harbor task folder containing `task.toml`, `instruction.md`,
  `environment/`, `solution/`, and `tests/`.
- **Scope**: task-local files only. Do not repair unrelated repo files.

If the target folder is missing required layout files, stop and report the missing
paths instead of guessing.

## Workflow

1. **Survey the task.**
   - Read `task.toml`, `instruction.md`, `environment/Dockerfile`, `solution/`,
     `tests/`, and any helper Python files under `environment/`.
   - List Dockerfiles: always check `environment/Dockerfile`; also check
     `tests/Dockerfile` when verifier mode is separate or when it exists.
   - Determine verifier mode before editing:
     - `environment_mode = "separate"`: Harbor builds `tests/Dockerfile` and
       runs `/tests/test.sh`; that image must copy `test.sh`, test modules, and
       any `tests/data/` reference files.
     - Shared/default verifier mode: Harbor runs verifier files in the runtime
       environment; `tests/test.sh` must default to `TESTS_DIR=/tests`, and
       verifier dependencies must be installed in `environment/Dockerfile`.
   - Search for local paths, external downloads, imports, subprocess tools, and
     file references before editing.
   - Confirm every runtime input file under `environment/data/` is copied into
     the runtime image by `environment/Dockerfile`, typically with
     `COPY data/ ${DATA_DIR}/`. Defining `DATA_DIR` and creating the directory
     is not enough; if the Dockerfile never copies the data, oracle runs fail
     with all artifacts missing and `Missing required input files`.
   - Compare the prompt contract in `instruction.md` against the verifier tests:
     every input file, output file, environment variable, column name, CLI name,
     and parameter that tests require must be either stated in `instruction.md`,
     provided as task-local data, or be a standard Harbor runtime variable. If a
     test depends on an unstated filename, env var, magic config key, hidden
     schema, or non-obvious output location, either update `instruction.md` to
     expose the requirement or revise the test to match the stated task
     contract. Do not expose hidden reference answers or verifier-only constants.
   - Compare `task.toml` `artifacts` against every file the solution writes and
     every file the verifier expects. Missing artifacts cause passing solutions
     to produce empty verifier mounts or no downloadable outputs.
   - Verify `task.toml` artifact schema is Harbor-compatible. Use a top-level
     `artifacts = ["/workspace/output/..."]` list or supported
     `{ source = "...", destination = "..." }` entries. Do not use
     `[[artifacts]]` tables with `path`/`type`; those can make Harbor skip the
     task during discovery, which later appears as `reward: null` and no trial
     result.
   - Inspect verifier tests for memo/writeup/content checks. Remove tests that
     grade prose contents, keywords, headings, minimum word counts, section
     names, tone, or other clerical adherence in `*.md`, `*.txt`, README-style,
     memo, report, or interpretation artifacts. Verifiers should test the
     scientific result through numeric, structural, executable, or data-derived
     evidence, not whether a writeup says particular words. It is acceptable to
     check that a required writeup artifact exists only when that artifact is
     part of the task contract, but do not inspect its textual content.

2. **Simplify `instruction.md` and create `solution/process.md`.**
   - Remove almost all Markdown from `instruction.md`; keep only formatting that materially improves clarity. Prefer plain paragraphs, short input/output bullets, code formatting for paths and filenames, and math blocks only where needed. Avoid decorative sectioning, long nested bullet lists, tables, excessive headings, horizontal rules, and implementation-style checklists.
   - Use the referenced terminal-bench-science style as the model: concise task statement, compact input listing, output contract, essential scientific model/constraints, and time/anti-cheat notes.
   - De-spoonfeed `instruction.md`: remove exact solving steps, implementation
     recipes, reference-solution equations, threshold formulas, feature
     engineering recipes, hyperparameter schedules, or derivations that the
     agent should compute or infer from the stated problem and data. Keep only
     domain facts, task constraints, definitions, and output requirements needed
     to make the problem well-posed.
   - Move any process, workflow, algorithm, or step-by-step solving content out of `instruction.md` into `solution/process.md`. This includes numbered procedures, prescribed library calls, model-training recipes, threshold-tuning instructions, convergence checklists, and "how to solve" sections.
   - Create `solution/process.md` if it does not exist. It must list the steps one would take to solve the problem, including scientific/computational decisions, tool choices, validation checks, and output generation.
   - Keep `instruction.md` focused on what the agent must accomplish, available inputs, required outputs, constraints, and domain facts needed to understand the task. Do not move hidden answers, expected numeric results, verifier-only constants, or reference-solution shortcuts into `process.md`.
   - After moving process content, make sure `instruction.md`, `solution/process.md`, `solution/solve.*`, and tests still agree on file paths, environment variables, outputs, units, schemas, and required artifacts.

3. **Convert hardcoded paths to environment variables.**
   - Replace machine-local paths such as `/Users/...`, `/Volumes/...`,
     `/tmp/...` task staging paths, and repo checkout paths with task/runtime
     variables.
   - Prefer these names consistently:
     - `WORKSPACE_DIR=/workspace`
     - `DATA_DIR=/workspace/data`
     - `OUTPUT_DIR=/workspace/output`
     - `OUTPUT_PATH=/workspace/output/<expected-file>`
     - `SOLUTION_DIR=/solution`
     - `TESTS_DIR=/tests`
     - `LOG_DIR=/logs/verifier`
   - In Dockerfiles, define stable `ENV` values before they are used and create
     writable directories with `mkdir -p`.
   - In Python, read paths with `os.environ.get(...)` and `pathlib.Path`; keep a
     correct Harbor default so scripts still run without manual exports.
   - Keep Harbor canonical artifact paths in `task.toml` when they are part of
     the runtime contract, but make solution and verifier code agree with them.
   - Make verifier scripts default to Harbor mount points:
     `TESTS_DIR=${TESTS_DIR:-/tests}`, `OUTPUT_DIR=${OUTPUT_DIR:-/workspace/output}`,
     and `LOG_DIR=${LOG_DIR:-/logs/verifier}`. Avoid defaults like
     `/workspace/tests`, which are not where Harbor mounts test files.
   - Even when Harbor paths already look canonical (for example
     `/workspace`, `/solution`, or `/tests`), reference them through the
     exported environment variables above. Never reintroduce literal absolute
     paths inside Dockerfiles or Python helpers.

4. **Vendor data.**
   - Identify every file or dataset mentioned in `instruction.md`, solution code,
     verifier code, Dockerfiles, and helper scripts.
   - Put runtime input data under `environment/data/` and verifier-only reference
     data under `tests/data/`.
   - Ensure `environment/Dockerfile` actually copies runtime data from
     `data/` into `${DATA_DIR}`. Use paths relative to the `environment/` build
     context, not `environment/data/`.
   - Replace network downloads, absolute source-file reads, DOI/API fetches, and
     generated-at-build artifacts with copied local files when feasible.
   - Update Dockerfile `COPY` lines using the correct build context:
     `environment/Dockerfile` copies from paths relative to `environment/`;
     `tests/Dockerfile` copies from paths relative to `tests/`. Avoid
     context-prefixed paths such as `COPY environment/...` from
     `environment/Dockerfile` or `COPY tests/...` / `COPY environment/...`
     from `tests/Dockerfile`; those paths commonly cause Harbor/Modal image
     build `RemoteError`s.
   - In `tests/Dockerfile`, never assume `/tests/test.sh` appears automatically:
     explicitly `COPY test.sh ${TESTS_DIR}/test.sh` and `chmod +x` it. Also copy
     `test_outputs.py` and `tests/data/` if referenced.
   - Do not copy `solution/` or `tests/` into the agent runtime image unless the
     task intentionally exposes them and `task-review` criteria allow it.
   - Do not vendor hidden answer files into the agent image. Keep reference data
     verifier-only or derive it at verification time.
   - Do not preserve task-local `.claude` or `.agents` skill content, a
     task-local `task_implementation.toml`, `__pycache__/`, `*.pyc`, or
     `.DS_Store`, as runtime data or verifier data. Remove them from the task
     folder when present.

5. **Reconcile dependencies.**
   - Parse Python imports in `solution/`, `tests/`, and `environment/` helpers.
     Ignore stdlib imports; map package imports to install names where needed
     (`Bio` -> `biopython`, `sklearn` -> `scikit-learn`, `skimage` ->
     `scikit-image`, `cv2` -> `opencv-python-headless`, `PIL` -> `pillow`,
     `yaml` -> `pyyaml`).
   - Scan shell scripts and Python subprocess calls for required CLIs such as
     `bedtools`, `samtools`, `obabel`, `blastn`, `ffmpeg`, `pandoc`, or `Rscript`.
   - Install runtime dependencies in `environment/Dockerfile`.
   - Install verifier-only dependencies in `tests/Dockerfile` for separate mode,
     or in the runtime Dockerfile only when verifier mode is shared.
   - Do not install verifier dependencies from `tests/test.sh` at runtime.
     Harbor verification must run without internet. Move `pip install pytest`,
     `pytest-json-ctrf`, `numpy`, `pandas`, etc. into the appropriate Dockerfile
     or provide them from an approved local wheelhouse.
   - Pin versions when practical, especially Python packages that affect numeric
     results or commonly break builds.
   - Add system libraries required by Python wheels or CLIs, then clean apt lists.

6. **Reconcile runtime user, artifacts, and executable entrypoints.**
   - If `task.toml` configures `[agent].user = "agent"` or another non-root
     user, verify the final runtime stage of `environment/Dockerfile` creates
     that user and gives it write access to `WORKSPACE_DIR` and `OUTPUT_DIR`.
     Missing runtime users often appear in oracle logs as every artifact missing
     and verifier tests failing only on absent output files.
   - In multi-stage Dockerfiles, perform user creation and `chown` in the final
     stage, not only in a builder stage.

7. **Reconcile artifacts and executable entrypoints.**
   - Ensure every required output path in `task.toml` is produced by the solution
     under `/workspace/output` or `OUTPUT_DIR`. If the solution writes elsewhere
     (`./outputs/...`, `output/`, a timestamped directory), copy or write the
     final contract files to `OUTPUT_DIR`.
   - Ensure `task.toml` declares all verifier-required files in `artifacts`.
     Common examples: `result.json`, `summary.json`, `.npz` arrays, and every
     CSV checked by tests.
   - Ensure the `artifacts` declaration uses Harbor's accepted schema:
     top-level strings such as `artifacts = ["/workspace/output/result.json"]`
     or supported artifact config objects. Convert any `[[artifacts]]`
     `path`/`type` table blocks to the top-level list form.
   - Reconcile all verifier-required names with the prompt before changing test
     thresholds or solution logic. This includes required output filenames,
     JSON keys, CSV headers, directory names, env vars such as `OUTPUT_PATH`,
     `DATA_DIR`, or task-specific variables, and any extra config files. Tests
     may enforce the declared contract, but they must not require undisclosed
     files or variables that a solver could not infer from `instruction.md` and
     the visible task data.
   - Remove verifier assertions that inspect the contents of memo, report,
     interpretation, README-style, or other prose writeups. Do not replace them
     with alternate keyword, regex, word-count, or heading checks. If the task
     needs a prose artifact for human review, keep at most an existence check and
     focus automated grading on the underlying scientific outputs.
   - Avoid relying on Unix executable bits surviving upload/mount behavior. For
     solution helper scripts, either `chmod +x` them in the image or invoke them
     as `bash path/to/script.sh`.
   - Ensure `tests/test.sh` always writes `/logs/verifier/reward.txt` with `1`
     or `0`; failures before this file is written surface as
     `RewardFileNotFoundError` and hide the real issue.
   - Ensure every verifier run produces `${LOG_DIR:-/logs/verifier}/reward.txt`
     containing exactly the Harbor reward for that run: `1` on pass and `0` on
     failure. The reward file must be written even when tests fail, so `test.sh`
     should capture the verifier exit code, write `reward.txt`, and then exit
     with the captured code.

8. **Validate the repair.**
   - Run fast static checks first: `python -m py_compile` for edited Python and
     `dockerfile` syntax review by inspection when Docker is too expensive.
   - Confirm referenced data files exist at the paths now used by code and
     Dockerfiles.
   - Confirm every file path, environment variable, and schema element that the
     verifier reads is documented in `instruction.md` or supplied by the Harbor
     runtime. Treat undocumented task-specific variables and hidden required
     filenames as task bugs.
   - Confirm executable scripts such as `solution/solve.sh` and `tests/test.sh`
     are executable.
   - Build any image whose Dockerfile or build-context paths were edited. For
     runtime-image build failures, run `docker build -t <tag> environment`.
     For separate verifier failures, run `docker build -t <tag> tests` and
     confirm `/tests/test.sh` is present. A cheap check is:
     `docker run --rm <verifier-image> test -x /tests/test.sh`.
   - When Harbor logs show produced artifacts, rerun the verifier locally with
     those artifacts mounted at `/workspace/output` before moving the task back.
   - After any local verifier run, confirm `${LOG_DIR:-/logs/verifier}/reward.txt`
     exists and contains the expected reward value for the run. Missing
     `reward.txt` is a task bug even if pytest output is otherwise clear.
   - For shared verifier mode, validate with the runtime image plus
     `-v <task>/tests:/tests:ro`; do not rely on `/workspace/tests`.
   - Run the reference solution locally or in the image when feasible, using the
     task contract environment variables exactly (`DATA_DIR`, `OUTPUT_DIR`,
     `OUTPUT_PATH`, `SOLUTION_DIR`). Then run the verifier against those outputs
     when dependencies are available.
   - Run targeted tests or builds when feasible and not prohibitively expensive.
   - Confirm the client deployment gates: `allow_internet = false`, no runtime
     network dependency remains, and every built runtime or separate verifier
     image is at most 2 GB. Measure each image with:
     `docker image inspect --format '{{.Size}}' <image-tag>` and compare the
     byte count with `2000000000`. If Docker is unavailable, report the image
     size gate as unverified rather than assuming it passes.
   - Stop and remove every Docker container started for validation before
     yielding. Prefer `docker run --rm ...`; if a named or detached container is
     necessary, use a unique task-specific name and clean it with
     `docker rm -f <container>` in a `finally`/`trap` path. If using Compose,
     run `docker compose down --volumes --remove-orphans` for the test project.
   - Delete Docker images built only to test this task before yielding. Use
     unique task-specific tags and remove them with `docker rmi <image-tag>` in
     the same cleanup path; keep only pre-existing base images and images the
     user explicitly asked to retain.


## Agent-bootstrap compatibility under the client offline policy

Harbor installs the agent (claude-code, codex, gemini-cli) **inside the task
container at setup time, before the task runs**, using its own bootstrap
(`harbor/agents/installed/*.py`). That bootstrap is off-limits to edit, always
runs (there is no skip-if-already-installed), and does two network-dependent
things:

1. **System packages** — `apt-get update && apt-get install -y curl [ripgrep]`
   (with `apk`/`yum` fallbacks; codex also needs `ripgrep`, and the apk path
   also pulls `nodejs npm`).
2. **Agent-CLI download** — fetches the CLI from `claude.ai`,
   `raw.githubusercontent.com` (nvm), or the npm registry.

When `task.toml` sets `allow_internet = false`, Harbor attaches the container to
`network_mode: none`, so it has **no network at setup time**. The unconditional
agent bootstrap therefore fails with `NonZeroAgentExitCodeError` (exit 100)
*before the task ever starts* unless the client provides an offline/preinstalled
agent adapter. This is an infrastructure compatibility issue, not a reason to
enable internet access for the task.
Symptoms in `trajectories/<agent>/<id>/exception.txt` / `trial.log`:
`Temporary failure resolving 'deb.debian.org'`, `E: Unable to locate package
curl`/`ripgrep`, `curl: (6) Could not resolve host: claude.ai`. Slim bases
(`python:*-slim`) lack curl/ripgrep and fail step 1; fuller images that already
ship curl get past step 1 and fail at step 2. The oracle does **not** trigger
this — it runs the solution directly with no installed agent — which is why a
task can pass oracle yet fail every claude/codex/gemini trial identically.

Do not attempt to fix the CLI download at the task level (never edit Harbor, the
runner, or agent bootstrap):

- **Vendor the bootstrap system toolchain into the final image stage** so the
  package-install portion is satisfied where the client permits networked image
  builds. Add to the **last** `FROM` stage of `environment/Dockerfile`:
  ```dockerfile
  RUN apt-get update && apt-get install -y --no-install-recommends \
          curl ca-certificates ripgrep git \
      && rm -rf /var/lib/apt/lists/*
  ```
  In multi-stage Dockerfiles add this to the final stage, not a `data_builder`
  stage. This does not solve the separate agent-CLI download.
- **The agent-CLI download cannot be vendored by this skill.** It is hardcoded,
  unconditional, and runs under `set -euo pipefail` inside the off-limits
  bootstrap. Keep `allow_internet = false`; if installed-agent evaluation is
  required, stop and report that the client must provide a supported offline or
  preinstalled adapter. Do not claim agent readiness from an Oracle-only pass.

Validate the client boundary by running the task with no network and measuring
both final images:
```bash
docker run --rm --network none <runtime-image> bash -lc \
  'bash /solution/solve.sh'
docker image inspect --format '{{.Size}}' <runtime-image>
docker image inspect --format '{{.Size}}' <verifier-image>
```
The task is within policy only when runtime execution does not need a network
and each reported size is at most `2000000000` bytes. If the image build or
agent setup requires network access, record that as an external client-platform
dependency rather than changing `allow_internet`.

## Guardrails

- Preserve the task's scientific intent and expected output schema.
- Keep `instruction.md` and the verifier contract in sync: no test should depend
  on a task-specific required file, environment variable, output name, schema
  field, or config key that is absent from the prompt and visible task data.
- De-spoonfeed prompts before review. The prompt may define the problem and the
  data contract, but it should not hand the agent the exact algorithm, equation
  sequence, derivation, parameter-tuning plan, or reference-solution procedure
  when those are the substance of the task.
- Remove tests that grade memo or writeup content. Automated verification should
  reward scientific correctness, not clerical prose adherence; do not test for
  required phrases, headings, word counts, narrative coverage, or other textual
  content in markdown/text reports.
- Keep `instruction.md` minimal and reader-friendly. Use Markdown only for clarity, and keep solver-process details in `solution/process.md`.
- Do not hardcode answers or weaken tests to make the task pass.
- Do not introduce internet requirements. Set `allow_internet = false` and keep
  all task and verifier execution offline. If Harbor's installed-agent bootstrap
  cannot run under that policy, report the need for a client-approved offline or
  preinstalled adapter instead of weakening the policy.
- Keep every final runtime and separate verifier image at or below 2 GB; measure
  the Docker image size in bytes and fail the readiness check when it exceeds
  `2000000000`.
- Do not leave verifier runtime installs in `tests/test.sh`; install dependencies
  during image build.
- Ensure every verifier execution writes `/logs/verifier/reward.txt` containing
  `1` for a passing run or `0` for a failing run, as required by Harbor.
- Do not leave Docker containers or task-test images behind after validation.
  Clean up every container and image created by the skill, including failed runs.
- Do not rely on implicit Harbor files. Explicitly copy `test.sh`,
  `test_outputs.py`, and reference data into verifier images, and explicitly
  declare artifacts in `task.toml`.
- Never hardcode filesystem paths in Dockerfiles or Python; rely on exported
  environment variables even for canonical Harbor directories.
- Remove any task-local `.claude/` or `.agents/` directories and any
  task-local `task_implementation.toml` file instead of trying to normalize or
  update their contents.
- Ensure every repaired task has `solution/process.md` and that it lists the solver workflow without exposing hidden answers.
- Keep edits focused and cite any changed files in the final handoff.
