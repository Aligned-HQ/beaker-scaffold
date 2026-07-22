---
name: task-fixer
description: Prepare a Harbor task folder to run its Oracle by repairing metadata,
  offline Docker configuration, required build-support files, executable
  entrypoints, and canonical paths without editing the instruction, solution, or
  verifier logic. Use when a task needs to be made Oracle-ready or its
  environment and metadata need to be repaired.
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
- `README.md` when the project scaffold requires reviewer notes;
- `tests/Dockerfile` and `tests/data/` when the separate verifier image or the
  project scaffold requires them; the verifier implementation remains read-only;
- task-local runtime input data that must be vendored for an offline build.

Read `instruction.md`, the solution directory, and the verifier directory to
discover their contracts and dependencies, but never edit them. In particular,
never edit `instruction.md`, `solution/solve.py` (or any other solution file),
`tests/test.sh`, verifier Python files, test thresholds, fixtures, or expected
outputs. The content of existing solution and verifier entrypoints is
read-only, but changing the executable bit on an existing required shell
entrypoint is allowed. Do not create placeholder solution or test
implementations. If a required repair would need scientific or verifier content
changed, report the blocker for the task author.

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

The exact solution language and optional data files may vary. Repair missing
build-support files when their contents can be derived from the existing task:

- Create a factual author/reviewer `README.md` from the task metadata, data
  provenance, dependencies, and observed workflow. Do not put reviewer notes in
  `instruction.md`, and do not fill the README with generic TODOs or invented
  scientific claims.
- If `tests/test.sh` and the verifier modules exist, create a complete
  `tests/Dockerfile` from their actual imports and referenced files. It must be a
  real verifier image, not an empty placeholder: use `FROM
  --platform=linux/amd64`, define canonical variables, copy the existing test
  entrypoint/modules/data, and pre-install dependencies from an approved local
  wheelhouse or base image.
- Create required `environment/data/` or `tests/data/` directories. Use a
  `.gitkeep` only for an intentionally empty directory; copy actual referenced
  fixtures when the verifier needs them. Never fabricate reference data.
- Set the executable bit on existing `solution/solve.sh`, `tests/test.sh`, and
  other existing task entrypoint shell scripts when required. Do not rewrite
  their contents.

If a required scientific input, solution/verifier implementation, or dependency
cannot be derived or supplied from approved local resources, return `FAIL` with
the exact missing path and remedy instead of inventing it.

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
   - when `tests/test.sh` and verifier modules exist, prefer
     `environment_mode = "separate"` and complete `tests/Dockerfile`; do not
     select shared mode merely to avoid repairing a missing verifier image;
   - preserve an explicitly required shared mode only when the task contract
     and project validator support it;
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
   - make every `FROM` line explicit: `FROM --platform=linux/amd64 ...`;
   - classify every package install as Oracle/runtime, verifier, or
     agent-bootstrap-only. Remove bootstrap-only `apt-get` blocks when they are
     not needed by the Oracle; do not retain online `curl`, apt, or package
     setup merely for future agent installation;
   - repair required dependencies without network access when possible: use an
     approved local base image, a task-local wheelhouse with
     `pip install --no-index --find-links=...`, or an approved local `.deb`
     bundle installed with `dpkg`. Copy only the needed bundle into the build
     context and remove caches afterward. Do not add `pip install`, `apt-get`,
     or other downloads to `tests/test.sh` or runtime execution;
   - if no approved base or local package bundle can satisfy a required import
     or CLI, leave the task policy unchanged and report the dependency blocker;
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

5. **Repair strict scaffold prerequisites.**

   Locate the project root and run its static validator when available, for
   example `python3 scripts/validate_scaffold.py --root <project-root>
   --strict`. Fix every in-scope error before treating the task as blocked:

   - create a factual `task/README.md` when the scaffold requires it;
   - create or repair `tests/Dockerfile` and `tests/data/` from existing
     verifier files and referenced fixtures;
   - set executable bits on existing solution/verifier shell entrypoints;
   - add `FROM --platform=linux/amd64` to every Dockerfile stage and correct
     context-relative `COPY` paths;
   - remove networked dependency setup when it is replaceable by an approved
     local base or dependency bundle.

   Run the strict validator again after these repairs. A missing implementation,
   missing scientific input, unavailable approved dependency, or error that
   would require changing instruction/solution/test contents remains a blocker.
   Do not create empty files merely to silence a validator.

6. **Check Oracle prerequisites without running the task.**

   Validate the TOML, required file set, Dockerfile context paths, `COPY` targets,
   environment-variable wiring, entrypoints, user permissions, artifact paths,
   and offline/network settings. When Docker and approved cached dependencies are
   available, build the affected images with:

   ```bash
   docker build --platform linux/amd64 -t <temporary-runtime-tag> environment
   docker build --platform linux/amd64 -t <temporary-verifier-tag> tests
   ```

   Before declaring the image checks impossible, inspect `docker context show`,
   `docker context ls`, `docker info`, and `DOCKER_HOST`. If another already
   configured client-approved context is reachable, use it explicitly with
   `docker --context <name> ...`. Do not chmod a Docker socket, expose the
   socket to the task, use an unapproved remote daemon, or weaken the task
   policy. If no approved daemon is reachable, continue all static repairs and
   report the exact access error; mark the architecture and image-size checks
   `UNVERIFIED` rather than claiming the task or Dockerfile is at fault.

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

Return `FAIL` only after attempting the in-scope repairs. Fail when a required
implementation or scientific input is missing, metadata remains invalid, a
Docker build context or path remains broken, a required dependency cannot be
supplied offline, a network dependency remains, an image is not `linux/amd64`,
an image exceeds 2 GB, or a mismatch can only be fixed by editing instruction,
solution, or verifier content. Include the exact file and a concise remedy for
the author. A denied Docker socket is an external validation blocker: continue
static repairs and mark image architecture/size evidence `UNVERIFIED`.

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
- File mode changes on existing required shell entrypoints are allowed; never
  change their contents. Adding reviewer `README.md`, Dockerfiles, data
  directories, `.gitkeep`, and approved vendored dependency files is allowed
  only when the contents are derived from the task and genuinely required.
- Never alter the scientific problem, output schema, tolerances, or verifier
  assertions to manufacture Oracle success.
- Never create placeholder solution/test implementations or fake scientific
  data merely to satisfy a required-file check.
- Keep all edits inside the one target task and limited to metadata, reviewer
  notes, Docker/build configuration, file modes, and required local input or
  dependency data.
- Do not introduce network access, secrets, hidden answer data, task-local agent
  skills, caches, or unrelated files.
- Do not leave online apt, pip, curl, or package bootstrap commands when an
  approved offline base or local bundle can replace them; never enable internet
  access to make a build pass.
- Clean up every temporary container and image created during validation.
- Cite every changed path and every unverified check in the final handoff.
