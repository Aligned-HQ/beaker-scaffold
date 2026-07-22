---
name: trajectory-review
description: Review the latest Harbor 3-agent trajectory run for a task. Pass when verifier expectations are reasonable for a researcher in the field to infer, including inferable names, formats, and schema choices, and ignore agent/platform errors unrelated to the task such as Modal startup failures or policy refusals. Still fail structural task bugs, contradictory or hidden exact schemas, brittle tolerances, and non-inferable prompt-test mismatches. Use when asked for an easier trajectory review, permissive trajectory review, completed_trajectories review, harbor-jobs review, 3x agent run review, pass/fail trajectory review, or whether a task failure is acceptable under a domain-expert standard.
argument-hint: <task-or-run-path>
---

# Trajectory Review

Review a Harbor 3-agent run for a task. The goal is not to fix the task; it is
to decide whether observed failures are legitimate scientific failures by the
agent.

A verifier may require methods,threshold concepts, statistical checks, numerical procedures, domain conventions, names, formats, or schemas that are not spelled out line-by-line in `instruction.md` if a competent researcher in the task's field could reasonably infer them from the problem, data, references, and stated scientific objective. Do not fail a task only because the verifier rewards such reasonable domain-inferable work.

Also ignore trial failures caused by agent/platform problems that are not
related to the task itself. Examples include model policy refusals, unavailable
agent credentials, agent process startup crashes, Modal sandbox startup
failures, transient provider/API failures, agent CLI installation problems, or
tooling failures before the agent has a meaningful chance to inspect or solve
the task. Report these separately as ignored trials; do not count them as task
failures.

## Inputs

- A set of completed trajectories.
- Typical completed run layout:
  `trajectories/summary.md`, `trajectories/oracle/`, and one direct folder per
  agent such as `trajectories/claude-code/`, `trajectories/codex/`, and
  `trajectories/gemini-cli/`.

## Workflow

1. **Find the latest relevant 3-agent run.**
   - Inspect the `trajectories/` folder

2. **Read the job-level summary first.**
   - Read `summary.md` when present.
   - Read each agent job `result.json` and note:
     - number of trials,
     - rewards,
     - errored trials,
     - exception stats,
     - pass@k when present.
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
     verifier image missing files, or agent could not run the provided tools.
   - **Ignored agent/platform error**: an error unrelated to the task contract
     or scientific work, such as Modal/Harbor startup problems, agent CLI
     boot failures, missing provider credentials, transient API/provider
     outages, policy refusals, content-filter blocks, or agent runtime crashes
     before meaningful task work began. Exclude these from pass/fail evidence
     unless the logs show the task caused the error.
   - **Reasonable domain-inferable method requirement**: verifier expects a
     method, model family, diagnostic, threshold concept, numerical procedure,
     validation check, or scientific convention that is not explicitly spelled
     out, but a researcher in the field could reasonably infer it from the
     prompt, data, references, and scientific goal. Treat this as compatible
     with PASS unless the implementation is brittle or overly narrow.
   - **Reasonable inferable clerical contract**: verifier expects filenames,
     key names, column names, units, output shapes, or formats that are not
     explicitly specified but follow naturally from the instruction, examples,
     visible input data, task naming, or standard field conventions. If the
     agent chose different names or formats despite enough context to infer the
     expected contract, classify that as agent-side and compatible with PASS.
   - **Prompt-test mismatch**: verifier requires a filename, column, key,
     config value, hidden assumption, external source, algorithm, output field,
     variable name, exact schema detail, or nonstandard convention that is not
     disclosed in `instruction.md`, visible data, ordinary domain knowledge, or
     reasonably inferable clerical context.
   - **Tolerance failure**: values are scientifically reasonable and align with
     task wording, but tests use overly tight absolute/relative thresholds,
     brittle seeds, exact optimizer path expectations, or unstable ordering.
   - **Clerical failure**: missing or misnamed JSON keys, CSV headers, artifact
     filenames, units, boolean fields, or report fields where the scientific
     result is otherwise present and the prompt/test contract is ambiguous or
     inconsistent.

5. **Use cross-agent evidence.**
   - Remove ignored agent/platform errors from the denominator before judging
     pass/fail patterns. For example, if one agent has a Modal startup failure
     and two agents solve or scientifically fail the task, classify the task
     from the two meaningful trials.
   - If two agents pass and one fails, inspect whether the failing agent simply
     made a scientific mistake or whether tests reward one narrow formatting
     path.
   - If all meaningful trials fail similarly, strongly suspect structural bug,
     clear prompt-test mismatch, excessive tolerance, missing data, or an
     underspecified task. Still check whether the shared failure is a
     legitimate scientific mistake against a domain-inferable standard.
   - If all three pass except rare stochastic failures, check for brittle
     randomness or tolerance issues before calling the task robust.
   - Passing peer trials are evidence that the task can be solved, but they do
     not by themselves prove the failed trial is scientific; still compare the
     failure mode against the prompt and verifier.

6. **Check the task contract against the verifier.**
   - Read `instruction.md`, `task.toml`, and `tests/test_outputs.py`.
   - Confirm every verifier-required output file, JSON key, CSV column, unit,
     and task-specific environment variable is disclosed or reasonably
     inferable from the task context.
   - For methods, algorithms, diagnostics, threshold concepts, and scientific
     assumptions, allow requirements that are reasonably inferable by a domain
     researcher from the task statement, data, references, and objective.
   - Do not accept tests that grade prose wording, section names, keywords, word
     counts, tone, or report text instead of scientific evidence.
   - Accept missing or misnamed keys, filenames, columns, units, or formats as
     agent-side clerical failures compatible with PASS when the expected
     contract was reasonably inferable from the instruction and surrounding
     context.
   - Do not accept hidden, contradictory, or non-inferable variable names, JSON
     keys, CSV headers, output filenames, units, CLI flags, environment
     variables, directory layouts, or exact schema details. Those remain
     prompt-test mismatch or clerical contract failure even under this easier
     standard.

7. **Decide the disposition.**
   - **PASS trajectory review** when failures are genuine scientific agent
     failures, when enough agents pass and remaining failures are clearly
     agent-side scientific mistakes, or when a supposed prompt-test mismatch is
     only a reasonable domain-inferable method or clerical requirement.
   - Ignore agent/platform errors unrelated to the task when deciding PASS or
     FAIL. They should be listed in the report as ignored, not treated as
     failed task evidence.
   - **FAIL trajectory review** when any failure indicates structural task
     breakage, clear prompt-test mismatch, too brittle tolerance, hidden schema,
     hidden exact field names, undisclosed file paths, or non-inferable
     clerical contract ambiguity.
   - **INCONCLUSIVE** when full trial logs/artifacts are missing. State exactly
     which missing paths are needed.

## Output Format

Return the complete trajectory review as Markdown. Start with exactly one of
these status lines so the project wrapper can extract the report and update the
shared skill status file:

- `**Status:** PASS` when failures are scientific, or disputed verifier
  expectations are reasonable for a domain researcher to infer, including
  clerical contracts.
- `**Status:** FAIL` when the task needs repair before review/upload.
- `**Status:** INCONCLUSIVE` when there is not enough trajectory evidence.

Then include:

- Run path and timestamp reviewed.
- Per-agent pass/fail table with trial ids and rewards.
- Failure classification for each failed trial.
- Ignored agent/platform errors, if any, with trial ids and the log evidence
  showing they are unrelated to the task.
- Evidence with file paths and concise line/log references.

When run through `scripts/run-trajectory-review.sh`, the wrapper saves this
complete Markdown result as `skill-reports/trajectory-review.md` and updates
`skill-status.md`. Do not write to either file directly, and do not return only
a summary or a file path.

Keep the report focused on failure evidence. Do not rewrite the task or modify
files unless the user explicitly asks for fixes.
