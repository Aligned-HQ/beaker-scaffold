# Authoring boundary

This page is a compact reference for the public/private task boundary described
throughout the [main authoring guide](../README.md).

The agent should see the scientific question, public inputs, constraints, and
exact output schema in `task/instruction.md`. It should not see the reference
solution, hidden truth, or verifier-only fixtures. Put agent inputs in
`task/environment/data/`; put the answer key and any private fixture in
`task/tests/data/`, which the agent never sees. Check in the hidden files
themselves rather than a script that generates them at build time — that step
does not run when the task is graded. In solution and verifier code, read every
path from the environment variables the task provides — `WORKSPACE_DIR`,
`DATA_DIR`, `OUTPUT_DIR`, `SOLUTION_DIR`, `TESTS_DIR`, and `LOG_DIR` — instead
of hardcoding them. Keep Dockerfile `WORKDIR` directives as literal absolute
paths (`/workspace` and `/tests`): Harbor sandbox providers inspect them before
Docker expands environment variables.

The starter `task/` uses `input.csv` and a simple summary only to prove that the
mounts, output paths, and reward file work. Replace that contract before asking
agents to solve the task. The finished task should represent a real expert
workflow with fit-for-purpose input selection, connected method choices,
intermediate validation, evidence integration, and a substantive
machine-checkable decision; a long schema, a toy transform, or a collection of
unrelated analyses is not enough.
