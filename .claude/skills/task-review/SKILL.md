---
name: task-review
description: Score a Harbor task folder against all criteria in
  `task_implemention.toml` and produce a PASS / FAIL / N/A scorecard with
  evidence. Use when the user asks to "review this task", "score this task",
  "grade the task instructions", "task scorecard", or points the skill at a
  task folder for evaluation against the rubric.
---

Read every criterion in the repo-root `task_implemention.toml`, evaluate each against the target task folder, and emit a single scorecard. Be skeptical and concrete: cite file paths and line numbers as evidence for every verdict.

## Client deployment gates

Every reviewed task must satisfy the client's offline and image-size policy:

- `task.toml` must set `[environment].allow_internet = false`.
- Runtime and verifier execution must not call live APIs, download files,
  install packages, contact remote databases, or otherwise require a network.
- The final runtime image and final separate verifier image must each be no
  larger than **2 GB (2,000,000,000 bytes)**. Use
  `docker image inspect --format '{{.Size}}' <image-tag>` when a built image is
  available. Do not estimate success from the Dockerfile or compressed layer
  sizes alone.
- If a built image or size evidence is unavailable, report the client image-size
  gate as **UNVERIFIED** and recommend `task-fixer`; do not assume it passes.
- If the Harbor agent bootstrap requires an online CLI download, classify the
  installed-agent path as infrastructure-blocked under this client policy.
  Do not recommend changing `allow_internet` to `true`; the client must provide
  an approved offline/preinstalled adapter.

These are deployment gates in addition to the rubric criteria. A task that
violates them is not ready for upload even if its scientific verifier passes.

## Inputs

- **Rubric**: `task_implemention.toml` at the repo root. It contains `[[criteria]]` entries; each has `name`, `description`, and `guidance`. Treat the `guidance` block as the authoritative grading rule for that criterion — read it before scoring.
- **Target**: a Harbor task folder, normally under `task/`. Expected layout:
  - `task.toml`
  - `instruction.md`
  - `environment/` (Dockerfile, data, supporting assets)
  - `solution/` (`solve.sh`, `solve.py` or equivalent)
  - `tests/` (`test.sh`, `test_outputs.py` or equivalent)
  - optional `README.md`

If the folder doesn't have this layout, stop and report what's missing — do not invent verdicts.

## Procedure

1. **Load the rubric.** Read `task_implemention.toml` fully and list every criterion `name` in order. Do not skip any. If a new criterion is added to the file, you score it too — never hardcode the list.
2. **Survey the task.** Read, at minimum:
   - `task.toml` (metadata, timeouts, resources)
   - `instruction.md` (the contract presented to the agent)
   - `solution/solve.sh` and the script(s) it invokes (`solve.py`, etc.)
   - `solution/process.md` describing the steps a solver would take to solve the problem
   - `tests/test.sh` and the verifier (`test_outputs.py`, etc.)
   - `environment/Dockerfile` and a directory listing of `environment/`
   - any recent oracle logs for this task under `jobs/oracle-batch/` if they
     already exist
   - `README.md` if present
   Read whole files when they're small enough; for larger files, read the sections needed to evaluate each criterion. Do not delegate this to a subagent if you can read the files directly — you need the contents in scope to cite line numbers.
3. **Require `solution/process.md`.** Confirm `solution/process.md` exists and lists the steps a solver would take to solve the problem. If it is missing, empty, or only says to run the reference solution, fail `instruction_minimality` and any relevant reviewability/solution-quality criterion with evidence. The process file should explain the intended scientific/computational workflow without hardcoding hidden answers.
4. **Check practitioner plausibility.** Before scoring the scientific criteria, identify the real practitioner who would plausibly do this work, the setting where they would do it, the decision the workflow supports, and whether the task's sequence of inputs, computations, validation, and outputs matches that real workflow. Use `instruction.md`, `solution/process.md`, `README.md`, task metadata, and the actual solution/verifier behavior as evidence. If the workflow is only research-flavored, synthetic busywork, a disguised coding/schema exercise, or not something a practitioner would reasonably be paid to do, fail the relevant `scientifically_grounded`, `difficult`, `agentic`, `essential_difficulty`, `expert_time_estimate`, and/or `reviewable` criteria with concrete evidence.
5. **Score each criterion.** For each rubric entry, decide one of:
   - `PASS` — meets the guidance.
   - `FAIL` — violates the guidance. Quote the specific guidance clause it violates.
   - `N/A` — only when the guidance explicitly permits N/A (e.g. `structured_data_schema` when no structured output is expected, `task_readme` when no README is present).
   Mark `UNKNOWN` only if you genuinely could not read a required file; never use `UNKNOWN` to avoid a judgment call.
6. **Evidence.** Every verdict needs at least one citation in `path/to/file:line` form. For `FAIL`, also include a one-sentence fix suggestion. For `PASS`, a brief justification (1 sentence) is enough.
7. **Write the scorecard.** Use the format below. Start the report with
   `**Status:** PASS` only when every required criterion and client deployment
   gate passes; otherwise start it with `**Status:** FAIL`. Produce the complete
   scorecard in Markdown, display the pass/fail summary, and identify the
   scorecard file when running outside the project wrapper. When run through
   `scripts/run-task-review.sh`, the wrapper saves the Markdown result as
   `skill-reports/task-review.md`. The final response must contain the complete
   scorecard, not only a short summary or a path to a file. Keep the final
   response's `## Practitioner plausibility`, `## Verdicts`, `## Top fixes`, and
   `## Out of scope / N/A` sections together; the wrapper retains that final
   review section in the saved report.

## Scorecard format

```
# Task review: <task-folder-path>

**Summary:** <pass>/<total non-N/A> criteria pass. <one-line gestalt>.

## Verdicts

| # | Criterion | Verdict | Evidence | Notes |
|---|-----------|---------|----------|-------|
| 1 | verifiable | PASS | tests/test_outputs.py:14-260 | Deterministic numeric tolerances, no LLM judge. |
| 2 | well_specified | FAIL | instruction.md:20 | "reasonable threshold" is subjective; spec the constant. |
| ...

## Top fixes (ordered by impact)

1. **<criterion>** — <one-line action>. Evidence: <path:line>.
2. ...

## Out of scope / N/A

- `task_readme` — no README present (allowed).
- `structured_data_schema` — N/A: ...
```

Keep the table rows one line each where possible; spill into "Notes" only when needed. The Top fixes list should call out the 3–7 most consequential failures so the author knows where to start.

## Scoring guidance per-criterion (rules of thumb)

These are reminders, not overrides — the `guidance` text in `task_implemention.toml` is authoritative.

- **verifiable / functional_verification**: check that `tests/test_outputs.py` actually executes the agent's output and asserts numerical / structural facts, not that it greps source files. If it uses LLM-as-a-judge, fail.
- **well_specified / test_instruction_alignment / structured_data_schema**: cross-check every assertion in the verifier against a clause in `instruction.md`. Flag any test that pins a constant (threshold, NIFFT length, gain recipe, schema field) that the instruction leaves to the agent's judgment. Flag any instruction clause that has no test.
- **solvable / solution_quality / reviewable**: read `solve.sh`, every script it invokes, and `solution/process.md`. The solution must derive the answer (not `echo` it); scripts > 20 lines should live in their own files, not heredocs. `process.md` must list the intended solving steps clearly enough for reviewers to understand the workflow.
- **outcome_verified**: instruction should describe the end state, not enforce specific tools. "Use scipy" is fine if scipy is the only sane choice; "use emacs" is not.
- **anti_cheat_robustness / task_security**: scan the solution and environment for hardcoded answers, files copied into the runtime image that contain expected outputs, or any obfuscated / network-exfil code.
- **deterministic_reproducible**: check whether the task is hermetic enough to grade reproducibly, has `allow_internet = false`, and has no live-service dependency. Leave concrete vendoring/dependency repair steps to `task-fixer`.
- **essential_difficulty**: the failure modes the verifier flags should be scientific, not clerical (units, JSON key spelling, file path typos).
- **difficulty_explanation_quality / solution_explanation_quality / verification_explanation_quality**: read the three `[metadata]` fields in `task.toml`. Empty strings, single sentences, or "this task is hard" → FAIL. Verification explanation must justify any inequality bounds / tolerances.
- **category_and_tags / task_name / task_toml_schema**: validate `task.toml` metadata against the rubric and Harbor schema at a review level
- **resource_configuration / expert_time_estimate**: timeouts and CPU/memory should match the workload; `expert_time_estimate_hours` should be non-zero and plausible.
- **instruction_clarity**: the prompt should specify goals, inputs, constraints, and output contract without becoming a step-by-step protocol. Flag instructions that pre-digest the science into algorithmic steps or dictate tools/libraries the agent should choose.
- **instruction_minimality**: check that `instruction.md` uses only Markdown that materially improves readability, avoids decorative structure and implementation checklists, does not spoon-feed the solution, and keeps solver process details in `solution/process.md`. Permit code formatting, necessary equations, and compact headings when they clarify the task.
- **novel / agentic / scientifically_grounded / difficult / reviewable**: judgment calls — be honest. A textbook exercise dressed up as a benchmark is still a textbook exercise; a task that only requires translating English into Python/NumPy should fail these criteria even if it is numerically complex.

## Client feedback checks

Apply these checks while scoring `instruction_clarity`, `instruction_minimality`, `agentic`, `difficult`, `scientifically_grounded`, `essential_difficulty`, and `expert_time_estimate`. Cite concrete evidence from `instruction.md`, `task.toml`, solution files, and trajectories/logs when available.

- **Real research workflow**: PASS only when the task resembles a genuine multi-step domain workflow that would plausibly take an expert 4+ hours. The difficulty should come from scientific ambiguity, approach selection, interpretation, and validation — not from data-cleaning traps, long schemas, or reading-comprehension burden.
- **Practitioner plausibility**: Name the likely practitioner role in the notes for at least one relevant verdict, such as "materials informatics scientist", "computational biologist", "microscopist", "clinical data scientist", or "process engineer". PASS only if that practitioner would plausibly perform this workflow in a real lab, company, field study, or analysis setting to support a concrete decision. FAIL when the task is merely a synthetic story around arbitrary transformations, when the workflow omits the validation or domain artifacts a practitioner would need, when no realistic stakeholder would care about the output, or when the work is mostly translating a prescribed recipe into code.
- **Workflow fidelity**: Compare `solution/process.md` and the verifier's checked outputs against the claimed research workflow. The workflow should include realistic inputs, intermediate decisions, uncertainty or quality checks, and outputs a practitioner would actually use. Penalize tasks whose process file or tests reveal that the "science" is just row counts, hardcoded constants, formatting, or schema conformance.
- **No step-by-step lab protocol**: FAIL when `instruction.md` gives the model a recipe of formulas, thresholds, ordered steps, exact model choices, or implementation details that reduce the work to translating prose into code. Good tasks state the scientific objective, available data, constraints, and evaluation target while leaving meaningful method choices to the agent.
- **Heterogeneous tool orchestration**: PASS only when the task requires at least 3-4 substantively different tools, data sources, or computational modes. Examples: web/literature/API lookup, domain CLI or specialist package, numerical/statistical modeling, visualization/QC, structured data processing, simulation, and long-form synthesis. Multiple Python libraries that all serve one local array-computation script do not count as heterogeneous tool use.
- **Intermediate decision-making**: PASS only when later steps depend on earlier findings. The agent should have to inspect intermediate outputs, choose between plausible approaches, reconcile disagreement across tools/sources, and explain uncertainty.

## Review-only operational checks

These checks help assign rubric verdicts during review. They intentionally avoid the repair playbooks owned by `task-fixer`. If the main problem is mechanical normalization of paths, vendored data, dependencies, artifacts, verifier Dockerfiles, or agent bootstrap readiness, flag the relevant rubric criterion and recommend `task-fixer` rather than reproducing its instructions here.

Apply the client deployment gates above before declaring the task reviewable. Cite
`task.toml` for `allow_internet`, scan Dockerfiles and helper scripts for network
operations, and record the measured byte size of both final images when available.
If the size cannot be measured without building and the user did not authorize
Docker validation, label that gate UNVERIFIED in the scorecard and do not imply
that the task is upload-ready. An image over 2 GB or any runtime network
dependency is a structural/environment failure, not a scientific judgment call.

- **Environment and verifier contract**: Check whether runtime image, verifier mode, artifacts, executable entrypoints, and reward-file behavior are coherent enough for review. Score failures under the existing environment/verifier criteria; do not prescribe the detailed Docker/path edits in this skill.
- **Reproducibility and data availability**: Check whether required inputs, reference data, and external services are available in a reproducible way. Score non-hermetic behavior under the existing reproducibility/environment criteria and refer mechanical vendoring fixes to `task-fixer`.
- **Schema and test alignment**: Check whether output schema, numeric tolerances, verifier assertions, and instruction clauses align. Score misalignment directly; keep concrete schema-repair guidance brief.
- **Coverage and scientific validity**: Check whether tests verify the scientific outcome with meaningful independent assertions, not only existence, row counts, or hardcoded constants.

## What to do, not do

- **Do** quote specific lines as evidence. `instruction.md:14` is useful; "the instructions are unclear" is not.
- **Do** be willing to FAIL a task. A scorecard that says PASS for everything is useless.
- **Do not** edit any task files. This is a review skill, not a repair skill. Mechanical repairs live in the `task-fixer` skill.
- **Do not** invoke the oracle or run the verifier. If you need to know whether the verifier passes, say so in the scorecard — running it is the user's call.
- **Do not** leave Docker containers or task-test images behind if the user
  explicitly asks for Docker validation during review. Clean up every container
  and image you create, including failed runs.
- **Do not** invent criteria. Score exactly what's in `task_implemention.toml`.
- **Do not** offer to "rewrite the instruction" unsolicited. If the user asks for fixes after the scorecard, that's a separate request.
