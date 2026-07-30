# Repository layout

This is the file-level reference for the
[main authoring guide](../README.md).

```text
.
├── README.md                         # main authoring path
├── harbor_runner.py                  # Docker smoke test and isolated Harbor runner
├── task_implementation.toml          # rubric consumed by task-review
├── docs/                             # supplemental authoring references
│   ├── authoring-boundary.md
│   ├── manual-toolchain-setup.md
│   ├── quick-local-agent-trial.md
│   ├── repository-layout.md
│   └── skill-reports.md
├── scripts/
│   ├── setup.sh                      # create the .venv, install deps, then check
│   ├── check-setup.sh                # local toolchain and Docker check
│   ├── validate_scaffold.py          # fast static contract check
│   ├── test_harbor_runner.py         # runner isolation regression checks
│   ├── test_package_submission.py    # trajectory packaging regression checks
│   ├── run-skill.sh                  # shared agent-skill runner
│   ├── run-task-fixer.sh             # task-fixer entrypoint
│   ├── run-task-review.sh            # task-review entrypoint
│   ├── run-trajectory-review.sh      # trajectory-review entrypoint
│   ├── package-submission.sh         # assemble the Workbench submission
│   └── verify-skill-runs.sh          # submission report/status checker
├── skill-reports/                    # latest Markdown result from each skill
│   ├── task-fixer.md
│   ├── task-review.md
│   └── trajectory-review.md
├── skill-status.md                   # overwritten latest status for each skill
├── task/
│   ├── README.md                     # maintainer notes for this task
│   ├── instruction.md                # agent-facing scientific contract
│   ├── task.toml                     # Harbor metadata and resources
│   ├── environment/
│   │   ├── Dockerfile                # agent runtime image only
│   │   └── data/                     # public runtime inputs
│   ├── solution/
│   │   ├── solve.sh                  # Oracle entrypoint
│   │   ├── solve.py                  # derivation, not a stored answer
│   │   └── process.md                # intended expert workflow
│   └── tests/
│       ├── Dockerfile                # isolated verifier image
│       ├── test.sh                   # verifier entrypoint/reward writer
│       ├── test_outputs.py           # executable scientific assertions
│       └── data/                     # verifier-only fixtures or truth
└── trajectories/
    └── README.md                     # archive contract; no fake runs
```
