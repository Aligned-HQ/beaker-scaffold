# Scientific task maintainer notes

This file is for task authors and reviewers. The agent-facing contract is [`instruction.md`](instruction.md); keep implementation notes, data provenance, tolerance calibration, and run commands here instead of leaking them into the prompt.

## Status

This checkout is a runnable smoke template, not a finished benchmark. Replace the generic `input.csv` summary with a real scientific workflow before running an agent campaign. Keep the directory contract intact while changing the domain-specific files.

## Data provenance

Document whether the runtime inputs in `environment/data/` are real, public, transformed, or deterministically synthetic. For generated data, retain the generator and seed used to reproduce the public inputs. Keep hidden reference material under `tests/data/` only.

## Design decisions to record

- What real practitioner uses the output, and what decision does it support?
- Which meaningful method choices remain open to the agent?
- Which intermediate observations influence later analysis or validation?
- Why is the verifier independent of the reference implementation?
- How were thresholds and tolerances calibrated across independent correct approaches?
- Which dependencies and resource limits are required, and why?

## Local commands

From the repository root:

```bash
python3 scripts/validate_scaffold.py
./harbor_runner.py task --smoke-test
```

For a Harbor task, use the task directory rather than the project wrapper:

```bash
./harbor_runner.py task --dry-run
```

After a real multi-agent run, the vendored runner writes its successful
Oracle-gated evidence directly under the project-level `trajectories/` folder:
`oracle/`, one folder per agent, and `summary.md`. Run the trajectory review
described in [`../authoring-guide.md`](../authoring-guide.md) against that
folder. A partial or interrupted run is retained under a run-id subdirectory
for debugging and does not replace the previous successful direct output.
