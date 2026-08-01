# Manual toolchain setup

This is the supplemental alternative to
[step 3 of the main authoring guide](../README.md#3-set-up-the-local-authoring-toolchain).
Most authors can skip it. Use it when `setup.sh` cannot run on your workstation,
when you would rather install into an environment you manage yourself, or when
the check reports something out of date and you want the specific command.
`check-setup.sh` itself is read-only: it reports missing tools but never
installs packages or contacts the network.

Everything below is installed on the authoring machine only.

| Dependency | Needed for | Install |
| --- | --- | --- |
| Docker Desktop or Docker Engine | building the runtime image and running the local smoke test | <https://docs.docker.com/get-started/get-docker/> |
| Harbor CLI (`harbor`) | validating the task and running the Oracle locally | `uv tool install harbor` |
| Python 3.11+ | scaffold scripts and `tomllib` | `brew install python@3.12`, or your distro package |
| `rich` Python package | runner panels, tables, and transfer progress | `python3 -m pip install -r requirements.txt` |
| Git, Make, ripgrep | skill wrappers, reviews, repository search | `brew install git make ripgrep` or `sudo apt-get install -y git make ripgrep` |
| Claude Code or Codex CLI | the task-fixer, task-review, and trajectory-review skills | `npm install -g @anthropic-ai/claude-code` or `npm install -g @openai/codex` |
| Workbench runner token | remote Harbor runs | copy `.env.example` to `.env` and paste your `WORKBENCH_RUNNER_TOKEN` |

`setup.sh` covers every row except Docker, the agent CLI, and the token itself,
which [step 3.1](../README.md#31-install-the-three-things-the-setup-script-cannot)
covers. The sections below give the detail for each.

## Docker

Docker builds the runtime image and the local smoke-test container. It is
required for the local smoke test. The submission sandbox uses the runtime
image for verification; a second verifier image is only optional local
tooling.

- macOS and Windows: install Docker Desktop from
  <https://docs.docker.com/get-started/get-docker/>.
- Linux: install Docker Engine plus the Compose plugin
  (<https://docs.docker.com/engine/install/>), then add your user to the
  `docker` group so the CLI can reach the daemon without `sudo`.
- Start the daemon before any build, smoke test, or Oracle run.

Verify:

```bash
docker --version
docker info --format '{{.ServerVersion}}'
docker compose version
```

On Apple silicon, enable Docker Desktop → Settings → General → *Use Rosetta for
x86/amd64 emulation*. Task Dockerfiles pin `FROM --platform=linux/amd64`, so the
build has to emulate that architecture locally.

## Harbor CLI

Harbor is the harness that validates the task bundle and runs the Oracle
locally. `setup.sh` installs it for you; to do it by hand, use
[uv](https://docs.astral.sh/uv/). Harbor requires Python 3.12 or newer; an
isolated tool install keeps that requirement separate from the interpreter the
scaffold scripts use.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # or: brew install uv
uv tool install harbor
harbor --version                                   # 0.9.0 is known good
```

This installs the `harbor`, `hb`, and `hr` entrypoints on your `PATH`. If you
prefer pip, `pip install harbor` works when the active interpreter is Python
3.12+. Upgrade later with `uv tool upgrade harbor`. Source, cookbook, and
examples: <https://github.com/harbor-framework/harbor>.

## Python and host-side Python packages

The scaffold scripts need Python 3.11 or newer for `tomllib`
(`brew install python@3.12`, or your distribution's package). The vendored
runner uses Rich for terminal panels, tables, and transfer progress. `setup.sh`
installs it into `.venv`; to install it into an environment you manage yourself:

```bash
python3 -m pip install -r requirements.txt
```

## Agent CLI

At least one of Claude Code or Codex must be installed; the task-fixer,
task-review, and trajectory-review wrappers drive them.

```bash
npm install -g @anthropic-ai/claude-code   # or: curl -fsSL https://claude.ai/install.sh | bash
npm install -g @openai/codex               # or: brew install codex
```

Authenticate each CLI once by running it interactively. `check-setup.sh` does
not authenticate agent CLIs for you.

## Git, Make, ripgrep, and a hash utility

```bash
brew install git make ripgrep                   # macOS
sudo apt-get install -y git make ripgrep        # Debian/Ubuntu
```

`shasum` or `sha256sum` is already present on macOS and mainstream Linux
distributions; the skill wrappers use it to stamp report metadata.

## Workbench runner token

Remote runs authenticate with your own scoped token. Log in to
<https://workbench.alignedhq.ai>, open your profile → Settings, create an access
token, then:

```bash
cp .env.example .env
# paste the token into WORKBENCH_RUNNER_TOKEN=<token>
```

Never commit, share, or reuse another author's `.env` or token.
