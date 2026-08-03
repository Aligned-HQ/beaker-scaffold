# Trajectory archive

This directory is intentionally empty apart from this guide. Populate it only
with a real Harbor 3-agent run after `task/` has passed the Oracle and
task-review gates.

The expected finished-project shape is:

```text
trajectories/
├── summary.md
├── oracle/
├── claude-code/
├── codex/
└── antigravity/
```

The Gemini agent runs through the Antigravity CLI, so its trials land in
`antigravity/`; older runs used `gemini-cli/`.

Each trial should retain its resolved `config.json`, `result.json`, `trial.log`, agent transcript(s), collected `artifacts/manifest.json`, verifier logs, and `verifier/reward.txt`. Keep enough job-level summary information to map rewards and exceptions to trial directories.

The runner replaces this directory with the available direct output whenever a
remote archive contains agent trial evidence, including trials that ended with
exceptions. Oracle-only exceptions and service failures before any agent trial
remain under `trajectories/<run-id>/` because they do not contain an agent
campaign to review. Run `trajectory-review` against `trajectories/` before
declaring the project finished. A zero reward caused by a missing artifact, Docker/build problem,
missing dependency, permissions issue, hidden schema, undisclosed threshold,
brittle tolerance, or missing reward file is evidence that the task needs
repair; it is not evidence of a scientific agent failure.

The runner's `--quick` host-local checks, when archived, live under
`trajectories/quick/<run-id>/` and are not part of the three-agent campaign.
