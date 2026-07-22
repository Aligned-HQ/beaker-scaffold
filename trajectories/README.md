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
└── gemini-cli/
```

Each trial should retain its resolved `config.json`, `result.json`, `trial.log`, agent transcript(s), collected `artifacts/manifest.json`, verifier logs, and `verifier/reward.txt`. Keep enough job-level summary information to map rewards and exceptions to trial directories.

The runner clears this directory only after every Oracle and agent job has
finished successfully without exceptions, then writes the new direct output.
Partial or interrupted evidence is kept under `trajectories/<run-id>/` for
debugging without replacing a previous successful run. Run
`trajectory-review` against `trajectories/` before declaring the project
finished. A zero reward caused by a missing artifact, Docker/build problem,
missing dependency, permissions issue, hidden schema, undisclosed threshold,
brittle tolerance, or missing reward file is evidence that the task needs
repair; it is not evidence of a scientific agent failure.
