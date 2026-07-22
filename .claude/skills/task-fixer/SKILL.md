---
name: task-fixer
description: Prepare a Harbor task folder to run its Oracle by validating required
  files, normalizing task metadata, correcting Docker build configuration, and
  checking canonical paths without editing the instruction, solution, or tests.
  Use when a task needs to be made Oracle-ready or its environment and metadata
  need to be repaired.
---

# Task Fixer

Prepare one Harbor task to run its Oracle. The Oracle-ready state means that the
task metadata, build contexts, runtime image configuration, local inputs, and
paths are internally consistent. It does not mean that the Oracle has passed;
the Oracle is run by the task runner after this skill finishes.

## Scope

The task-fixer may edit only task metadata and environment/build-support files:

- `task.toml` and task-local Docker/build metadata;
- `environment/Dockerfile` and support files used by that Dockerfile;
- `tests/Dockerfile` and `tests/data/` only when a separate verifier image needs
  them; the verifier implementation remains read-only;
- task-local runtime input data that must be vendored for an offline build.

Read `instruction.md`, the solution directory, and the verifier directory to
discover their contracts and dependencies, but never edit them. In particular,
never edit `instruction.md`, `solution/solve.py` (or any other solution file),
`tests/test.sh`, verifier Python files, test thresholds, fixtures, or expected
outputs. Do not create placeholder solution or test files. If a required repair
would need one of those files changed, report the blocker for the task author.

## Client deployment constraints

These constraints apply to the task images:

- `task.toml` must set `[environment].allow_internet = false`. Oracle execution
  must not require APIs, downloads, package installation, or remote databases.
- Build and inspect single-platform `linux/amd64` images. Do not rely on an OCI
  multi-architecture manifest for the image submitted to the runner.
- The final runtime image and, for `environment_mode = "separate"`, the final
  verifier image must each be no larger than 2 GB (`2,000,000,000` bytes).
- Vendor runtime inputs and approved offline dependencies in the task or use an
  approved base image. Do not solve a missing dependency by enabling internet.
- Do not modify Harbor, the runner, or an agent bootstrap to work around these
  constraints. An agent-installation limitation is outside this Oracle-only
  skill and must be reported separately.

Treat a network dependency, unsupported architecture, or image over the size
cap as an Oracle-readiness failure, not as a reason to weaken the task contract.

## Required inputs and allowed changes

The target is a single task directory. Confirm the task root before editing and
work only inside it. A normal task contains:

- `task.toml`;
- `instruction.md`;
- `environment/Dockerfile`;
- the solution entrypoint and implementation named by the task (commonly
  `solution/solve.sh` and `solution/solve.py`);
- `tests/test.sh`, the verifier files it references, and any required test data;
- `tests/Dockerfile` when verifier mode is separate.

The exact solution language and optional data files may vary. Every referenced
file must exist, but do not invent a missing file. If the layout is incomplete,
return `FAIL` with the missing paths and stop before making speculative edits.

## Workflow

1. **Audit the task read-only.**

   Read `task.toml`, `instruction.md`, the solution entrypoint and imports, the
   verifier entrypoint and imports, and every Dockerfile. Inventory:

   - the Harbor environment mode, runtime user, timeouts, resource settings, and
     declared artifacts;
   - input files and CLIs/packages needed by the solution and verifier;
   - output paths and environment variables used by the existing code;
   - Docker build contexts, `COPY` sources, entrypoints, and required users;
   - network calls, host-specific paths, and files referenced but not present.

   This is a consistency audit only. Do not rewrite scientific logic or resolve
   a contract mismatch by changing the prompt or tests.

2. **Normalize task metadata.**

   Edit `task.toml` only as needed to make it valid and Oracle-compatible:

   - set `allow_internet = false` and preserve the task's scientific contract;
   - keep `environment_mode` consistent with the Dockerfiles that actually
     exist, using separate verifier mode only when its image is complete;
   - declare the files the existing solution produces and the verifier consumes
     in Harbor's supported artifact form, normally
     `artifacts = ["/workspace/output/<file>"]`;
   - remove host-specific paths such as `/Users/...` and `/Volumes/...` from
     metadata; use task/container paths instead;
   - retain intentional task values and report any value that cannot be inferred
     from the current task rather than inventing a scientific requirement.

   Do not change output names, schemas, tolerances, or required parameters just
   to make the metadata agree with a broken solution or verifier. Report that
   mismatch for the author to resolve.

3. **Correct the Docker environment.**

   Edit only Docker/build configuration and its support files. Make the runtime
   image capable of running the existing solution and Oracle without modifying
   the solution or verifier:

   - use paths relative to each Dockerfile's build context; for example,
     `environment/Dockerfile` should use `COPY data/ ...`, not
     `COPY environment/data/ ...`;
   - define and use canonical variables such as `WORKSPACE_DIR=/workspace`,
     `DATA_DIR=/workspace/data`, `OUTPUT_DIR=/workspace/output`,
     `SOLUTION_DIR=/solution`, `TESTS_DIR=/tests`, and
     `LOG_DIR=/logs/verifier` where the existing task contract needs them;
   - create required directories and give the configured runtime user access to
     them in the final image;
   - install dependencies discovered from the read-only solution/verifier audit
     in the appropriate Dockerfile or an approved local wheelhouse. Do not add
     `pip install`, `apt-get`, or other downloads to `tests/test.sh` or runtime
     execution;
   - copy every existing runtime input under `environment/data/` into the image,
     and explicitly copy verifier files and verifier data in separate mode;
   - use `bash /solution/solve.sh` when an executable bit cannot be relied on,
     but do not edit the script itself;
   - avoid absolute host paths, build-time downloads, runtime network access,
     and hidden answer files.

   If a path in the existing solution, instruction, or verifier is incompatible
   with the canonical container layout and cannot be corrected in metadata or a
   Dockerfile, report it as a blocker. Do not edit the file that contains it.

4. **Vendor only required local inputs.**

   Copy inputs or approved offline packages into task-local data directories when
   they are referenced by the existing task and their source is available. Keep
   runtime inputs in `environment/data/` and verifier-only data in `tests/data/`.
   Do not add reference answers, hidden solution files, caches, credentials, or
   unrelated repository content. If a referenced input is unavailable, report
   its exact expected path instead of fabricating it.

5. **Check Oracle prerequisites without running the task.**

   Validate the TOML, required file set, Dockerfile context paths, `COPY` targets,
   environment-variable wiring, entrypoints, user permissions, artifact paths,
   and offline/network settings. When Docker and approved cached dependencies are
   available, build the affected images with:

   ```bash
   docker build --platform linux/amd64 -t <temporary-runtime-tag> environment
   docker build --platform linux/amd64 -t <temporary-verifier-tag> tests
   ```

   Build the verifier image only when separate mode is configured. Inspect each
   resulting image with `docker image inspect --format '{{.Size}}'` and fail the
   size gate if it exceeds `2000000000` bytes. A file-presence check inside a
   temporary container is allowed; do not execute `solution/solve.py`, the
   solution entrypoint, `tests/test.sh`, pytest, the Oracle, Harbor, or any agent
   trajectory from this skill.

   Use `--network none` for any permitted container check. Remove temporary
   containers and images in a trap/cleanup path, including after interruption.
   If Docker or an offline dependency is unavailable, report the check as
   unverified rather than enabling internet or claiming success.

## Failure handling

Return `FAIL` when a required file is missing, metadata is invalid, a Docker
build context or path is broken, a required dependency cannot be supplied
offline, a network dependency remains, an image is not `linux/amd64`, an image
exceeds 2 GB, or a mismatch can only be fixed by editing the instruction,
solution, or tests. Include the exact file and a concise remedy for the author.

Return `PASS` only when all in-scope repairs are complete and the Oracle
prerequisites were verified. A PASS means “ready to attempt the Oracle,” not
“the Oracle passed.”

## Output

Return only a concise final Markdown handoff beginning with `**Status:** PASS`
when the Oracle prerequisites are ready, or `**Status:** FAIL` when the task is
blocked or a required check could not be completed. Do not include planning,
tool transcripts, duplicated status sections, or token-usage text. Summarize
files changed, checks run, and remaining blockers. When run through
`scripts/run-task-fixer.sh`, the wrapper saves only this final handoff in
`skill-reports/task-fixer.md`.

## Guardrails

- Never edit `instruction.md`, any file under `solution/`, or any verifier/test
  implementation. This includes `solve.py`, `solve.sh`, `tests/test.sh`, test
  Python files, thresholds, fixtures, and expected outputs.
- Never alter the scientific problem, output schema, tolerances, or verifier
  assertions to manufacture Oracle success.
- Never create placeholder files that merely satisfy a required-file check.
- Keep all edits inside the one target task and limited to metadata, Docker/build
  configuration, and required local input data.
- Do not introduce network access, secrets, hidden answer data, task-local agent
  skills, caches, or unrelated files.
- Clean up every temporary container and image created during validation.
- Cite every changed path and every unverified check in the final handoff.
