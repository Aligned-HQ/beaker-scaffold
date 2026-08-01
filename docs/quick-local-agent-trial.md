# Quick local agent trial

This optional trial can be run after the
[Docker smoke test](../README.md#8-run-the-docker-smoke-test) and before the
required [Harbor campaign](../README.md#9-run-the-harbor-task-runner).

Use quick mode when you want to test the task once with the Claude Code or
Codex CLI you already use for the authoring skills. It stages only
`instruction.md` and public runtime inputs into an isolated workspace, runs the
host executable, and verifies its output in a local Docker container that
follows the task's `network_mode` (`public` by default). It does not run
Harbor, contact Workbench, create a Modal app, or expose `solution/` and
`tests/` to the agent:

```bash
./harbor_runner.py task --quick --quick-agent codex
# or let it choose Codex, then Claude Code:
./harbor_runner.py task --quick
```

The selected CLI uses its own local login and configured model. The one-trial
evidence remains in `harbor-jobs/` and, when archiving is enabled, under
`trajectories/quick/<run-id>/` so it cannot be mistaken for the required
three-agent campaign. Use `--quick-agent claude` to select Claude Code
explicitly. `--quick --dry-run` previews the host command without starting
Docker or the agent. While the host agent is running in a terminal, the runner
shows an in-place `Agent running...` spinner refreshed at 8 FPS. Redirected
output uses `--progress-interval-sec` (30 seconds by default) for newline
heartbeats; the full agent transcript is in the printed runner log.

The trial's `result.json` records `timing.agent_elapsed_sec`,
`timing.verifier_elapsed_sec`, and `timing.total_elapsed_sec`. Use these as
separate observations in task-review for agent timeout behavior,
infrastructure diagnosis, and reproducibility. They must not be compared with
`metadata.expert_time_estimate_hours` or used as a proxy for human duration.
