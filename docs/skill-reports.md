# Skill reports

This page supplements the fixer, review, and verification steps in the
[main authoring guide](../README.md).

Each skill wrapper overwrites its Markdown result in `skill-reports/`. The
shared `skill-status.md` file is overwritten at the start and end of every run;
the current skill is marked `Run` while active and `Pass` or `Fail` when it
finishes. The final checker reads these reports and requires passing
task-fixer, task-review, and trajectory-review results in order. The task-fixer
report retains the final handoff rather than the agent's intermediate tool
transcript. The task-review report retains the practitioner-plausibility
section through its verdicts, top fixes, and N/A notes; trajectory-review
retains its complete verdict.
