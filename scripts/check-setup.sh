#!/usr/bin/env bash
# Check the local toolchain needed to author and test a Harbor task.
set -uo pipefail

usage() {
    cat <<'USAGE'
Usage: check-setup.sh [options]

Check the local authoring toolchain without installing packages or contacting
network services. A zero exit status means the project is ready for the
documented authoring/test workflow.

Options:
  --strict            Treat optional-tool warnings as failures.
  -h, --help          Show this help.
USAGE
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
STRICT=0
FAILURES=0
WARNINGS=0
FAILURE_MESSAGES=()
FAILURE_REMEDIES=()
WARNING_MESSAGES=()
WARNING_REMEDIES=()

while (($# > 0)); do
    case "$1" in
        --strict)
            STRICT=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'ERROR: unknown option: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

pass_check() {
    printf '[PASS] %s\n' "$1"
}

fail_check() {
    local failure="$1"
    local remedy="${2:-Resolve this failed check and rerun ./scripts/check-setup.sh.}"
    FAILURES=$((FAILURES + 1))
    FAILURE_MESSAGES+=("$failure")
    FAILURE_REMEDIES+=("$remedy")
    printf '[FAIL] %s\n' "$failure"
}

warn_check() {
    local warning="$1"
    local remedy="${2:-Install or configure the optional dependency named in this warning, or rerun without --strict.}"
    WARNINGS=$((WARNINGS + 1))
    WARNING_MESSAGES+=("$warning")
    WARNING_REMEDIES+=("$remedy")
    printf '[WARN] %s\n' "$warning"
}

print_failure_summary() {
    local index
    if ((FAILURES > 0)); then
        printf '\nFAILURES AND REMEDIES\n'
        for ((index = 0; index < FAILURES; index++)); do
            printf '\n%d. Failure: %s\n' "$((index + 1))" "${FAILURE_MESSAGES[$index]}"
            printf '   Remedy: %s\n' "${FAILURE_REMEDIES[$index]}"
        done
    fi
    if ((STRICT && WARNINGS > 0)); then
        printf '\nSTRICT-MODE WARNINGS AND REMEDIES\n'
        for ((index = 0; index < WARNINGS; index++)); do
            printf '\n%d. Warning: %s\n' "$((index + 1))" "${WARNING_MESSAGES[$index]}"
            printf '   Remedy: %s\n' "${WARNING_REMEDIES[$index]}"
        done
    fi
}

info_check() {
    printf '[INFO] %s\n' "$1"
}

command_path() {
    command -v "$1" 2>/dev/null || true
}

command_version() {
    local command_name="$1"
    case "$command_name" in
        shasum|sha256sum)
            printf 'available'
            ;;
        *)
            "$command_name" --version 2>&1 | head -n 1
            ;;
    esac
}

check_required_command() {
    local command_name="$1"
    local purpose="$2"
    local hint="$3"
    local path
    path="$(command_path "$command_name")"
    if [[ -n "$path" ]]; then
        pass_check "${purpose}: ${command_name} at ${path} ($(command_version "$command_name"))"
    else
        fail_check "${purpose}: missing ${command_name}." "$hint"
    fi
}

printf 'Beaker task authoring setup\n'
printf 'Repository: %s\n\n' "$REPO_ROOT"

check_required_command bash "Shell" "Install a working bash shell."
check_required_command python3 "Python runtime" "Install Python 3.11 or newer."
check_required_command git "Source control" "Install Git; agent CLIs and task handoff use it."
check_required_command make "Project shortcuts" "Install make or run the documented commands directly."
check_required_command rg "Repository search" "Install ripgrep; the skills and reviews use rg."

workbench_env_file="${REPO_ROOT}/.env"
workbench_token_state="missing"
if [[ -f "$workbench_env_file" ]]; then
    workbench_token_state="$(awk '
        BEGIN { state = "missing" }
        /^[[:space:]]*WORKBENCH_RUNNER_TOKEN[[:space:]]*=/ {
            value = $0
            sub(/^[[:space:]]*WORKBENCH_RUNNER_TOKEN[[:space:]]*=[[:space:]]*/, "", value)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
            if ((substr(value, 1, 1) == "\"" && substr(value, length(value), 1) == "\"") ||
                (substr(value, 1, 1) == "\047" && substr(value, length(value), 1) == "\047")) {
                value = substr(value, 2, length(value) - 2)
            }
            state = (length(value) > 0) ? "filled" : "empty"
            exit
        }
        END { print state }
    ' "$workbench_env_file" 2>/dev/null || printf 'missing')"
fi

case "$workbench_token_state" in
    filled)
        pass_check "Workbench runner credential: .env contains a non-empty WORKBENCH_RUNNER_TOKEN"
        ;;
    empty)
        fail_check \
            "Workbench runner credential: .env has an empty WORKBENCH_RUNNER_TOKEN." \
            "Log in to https://workbench.alignedhq.ai, click your profile -> Settings, create an access token, and paste it into .env as WORKBENCH_RUNNER_TOKEN=<token>. Rerun ./scripts/check-setup.sh; never commit or share .env."
        ;;
    missing|*)
        fail_check \
            "Workbench runner credential: .env is missing or does not define WORKBENCH_RUNNER_TOKEN." \
            "Log in to https://workbench.alignedhq.ai, click your profile -> Settings, create an access token, copy .env.example to .env, paste it into WORKBENCH_RUNNER_TOKEN=<token>, and rerun ./scripts/check-setup.sh; never commit or share .env."
        ;;
esac

if command -v shasum >/dev/null 2>&1 || command -v sha256sum >/dev/null 2>&1; then
    hash_command="$(command -v shasum || command -v sha256sum)"
    pass_check "Hash utility: $hash_command"
else
    fail_check "Hash utility: shasum or sha256sum is missing." "Install shasum or sha256sum; the skill wrappers need one to record report metadata."
fi

python_version_output="$(python3 --version 2>&1 || true)"
if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
    pass_check "Python version supports tomllib: $python_version_output"
else
    fail_check "Python 3.11 or newer is required; found $python_version_output." "Install or select Python 3.11 or newer, then rerun this check."
fi
if python3 -c 'import tomllib' >/dev/null 2>&1; then
    pass_check "Python standard library includes tomllib"
else
    fail_check "Python tomllib is unavailable." "Use Python 3.11 or newer, which includes tomllib in the standard library."
fi

agent_count=0
for agent_command in codex claude; do
    agent_path="$(command_path "$agent_command")"
    if [[ -n "$agent_path" ]]; then
        agent_count=$((agent_count + 1))
        pass_check "Agent CLI: ${agent_command} at ${agent_path} ($(command_version "$agent_command"))"
    else
        warn_check "Agent CLI: ${agent_command} is not installed." "Install Codex or Claude Code; at least one supported agent CLI is required."
    fi
done
if ((agent_count == 0)); then
    fail_check "Agent CLI: neither Claude Code nor Codex is installed." "Install Claude Code or Codex before running the skill wrappers."
fi

harbor_path="$(command_path harbor)"
if [[ -n "$harbor_path" ]]; then
    if harbor_version="$(harbor --version 2>&1 | head -n 1)"; then
        pass_check "Harbor CLI: $harbor_path ($harbor_version)"
    else
        fail_check "Harbor CLI is present but cannot run harbor --version." "Repair or reinstall Harbor, then confirm that harbor --version succeeds."
    fi
else
    fail_check "Harbor CLI is missing." "Install Harbor before running the task campaign."
fi

runner_test_file="${REPO_ROOT}/scripts/test_harbor_runner.py"
if [[ -f "$runner_test_file" ]] && runner_test_output="$(PYTHONDONTWRITEBYTECODE=1 python3 "$runner_test_file" 2>&1)"; then
    pass_check "Vendored Modal runner isolation tests pass"
else
    fail_check "Vendored Modal runner isolation tests failed: ${runner_test_output:-$runner_test_file is missing}" "Run PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_harbor_runner.py and fix the reported runner errors."
fi

modal_sdk_version="$(python3 -c 'import modal; print(getattr(modal, "__version__", "unknown"))' 2>/dev/null || true)"
modal_cli_path="$(command_path modal)"
if [[ -n "$modal_sdk_version" ]]; then
    pass_check "Modal Python SDK: python3 can import modal ($modal_sdk_version); used for targeted cleanup when the CLI is absent"
elif [[ -n "$modal_cli_path" ]]; then
    pass_check "Modal CLI cleanup fallback: $modal_cli_path"
else
    fail_check "Modal control plane: neither the Modal Python SDK nor CLI is available." "Install the Modal Python SDK or CLI and configure it so the runner can stop its owned app after a run or interrupt."
fi

docker_path="$(command_path docker)"
if [[ -n "$docker_path" ]]; then
    if docker_version="$(docker --version 2>&1 | head -n 1)"; then
        pass_check "Docker CLI: $docker_path ($docker_version)"
    else
        fail_check "Docker CLI is present but cannot report its version." "Repair or reinstall Docker, then confirm that docker --version succeeds."
    fi
    docker_server_version="$(docker info --format '{{.ServerVersion}}' 2>/dev/null || true)"
    if [[ -n "$docker_server_version" ]]; then
        pass_check "Docker daemon is reachable: server $docker_server_version"
    else
        fail_check "Docker daemon is not reachable." "Start Docker Desktop or the Docker service, then rerun this check."
    fi
else
    fail_check "Docker CLI is missing." "Install Docker Desktop or Docker Engine; task images and the local runner require it."
fi
compose_v2_available=0
if [[ -n "$docker_path" ]] && docker compose version >/dev/null 2>&1; then
    compose_v2_available=1
    pass_check "Docker Compose v2 is available"
fi
if command -v docker-compose >/dev/null 2>&1; then
    pass_check "Legacy Docker Compose is available: $(command -v docker-compose)"
elif ((compose_v2_available == 0 && STRICT)); then
    fail_check "Docker Compose is unavailable in strict mode." "Install Docker Compose v2 or legacy docker-compose, then rerun this check."
elif ((compose_v2_available == 0)); then
    warn_check "Docker Compose is unavailable." "Install Docker Compose v2 or legacy docker-compose if your cleanup workflow needs it, or rerun with --strict only when required."
else
    :
fi

local_runner_file="${REPO_ROOT}/harbor_runner.py"
if [[ -x "$local_runner_file" ]] && local_runner_help="$(python3 "$local_runner_file" --help 2>&1)"; then
    pass_check "Vendored runner (Harbor and Docker smoke modes): $local_runner_file responds to --help"
else
    fail_check "Vendored runner is missing, not executable, or cannot start: $local_runner_file" "Restore harbor_runner.py, make it executable, and confirm that python3 harbor_runner.py --help succeeds."
fi

rubric_file="${REPO_ROOT}/task_implemention.toml"
if [[ -f "$rubric_file" ]] && python3 -c 'import sys, tomllib; tomllib.load(open(sys.argv[1], "rb"))' "$rubric_file" >/dev/null 2>&1; then
    pass_check "Task-review rubric: $rubric_file is valid TOML"
else
    fail_check "Task-review rubric is missing or invalid: $rubric_file" "Restore a valid task_implemention.toml file at the repository root and rerun this check."
fi

for skill_name in task-fixer task-review trajectory-review; do
    agents_skill="${REPO_ROOT}/.agents/skills/${skill_name}/SKILL.md"
    claude_skill="${REPO_ROOT}/.claude/skills/${skill_name}/SKILL.md"
    if [[ -f "$agents_skill" && -f "$claude_skill" ]] && cmp -s "$agents_skill" "$claude_skill"; then
        pass_check "Skill mirror: ${skill_name} is present and byte-identical"
    else
        fail_check "Skill mirror: ${skill_name} is missing or differs between .agents and .claude." "Restore both skill copies and make .agents/skills/${skill_name}/SKILL.md and .claude/skills/${skill_name}/SKILL.md identical."
    fi
done

agents_wheel_helper="${REPO_ROOT}/.agents/skills/task-fixer/scripts/vendor_offline_dependencies.py"
claude_wheel_helper="${REPO_ROOT}/.claude/skills/task-fixer/scripts/vendor_offline_dependencies.py"
if [[ -x "$agents_wheel_helper" && -x "$claude_wheel_helper" ]] && cmp -s "$agents_wheel_helper" "$claude_wheel_helper"; then
    pass_check "Offline dependency helper: task-fixer wheelhouse vendorer is present and mirrored"
else
    fail_check "Offline dependency helper is missing, not executable, or differs between skill mirrors." "Restore both task-fixer/scripts/vendor_offline_dependencies.py copies, make them executable, and keep them identical."
fi

for wrapper in \
    scripts/run-task-fixer.sh \
    scripts/run-task-review.sh \
    scripts/run-trajectory-review.sh \
    scripts/verify-skill-runs.sh; do
    if [[ -x "${REPO_ROOT}/${wrapper}" ]]; then
        pass_check "Executable project wrapper: $wrapper"
    else
        fail_check "Executable project wrapper is missing or not executable: $wrapper" "Restore the wrapper and run chmod +x ${wrapper}, then rerun this check."
    fi
done

skill_report_dir="${REPO_ROOT}/skill-reports"
skill_status_file="${REPO_ROOT}/skill-status.md"
if [[ -d "$skill_report_dir" && -w "$skill_report_dir" && -f "$skill_status_file" && -w "$skill_status_file" ]]; then
    pass_check "Skill reports and status file are present and writable"
else
    fail_check "Skill reports directory or skill-status.md is missing or not writable." "Restore writable skill-reports/ and skill-status.md so skill wrappers can save Markdown results and status updates."
fi

info_check "Client policy: task environments must set allow_internet = false."
info_check "Client policy: measure each built runtime/verifier image with docker image inspect and keep it <= 2,000,000,000 bytes."
info_check "This check does not build images, authenticate agent CLIs, or contact network services."

if ((FAILURES > 0 || (STRICT && WARNINGS > 0))); then
    print_failure_summary
fi

if ((FAILURES > 0)); then
    printf '\nSETUP NOT READY: %d failure(s), %d warning(s).\n' "$FAILURES" "$WARNINGS"
    exit 1
fi
if ((STRICT && WARNINGS > 0)); then
    printf '\nSETUP NOT READY: strict mode found %d warning(s).\n' "$WARNINGS"
    exit 1
fi
printf '\nSETUP READY: no required checks failed (%d warning(s)).\n' "$WARNINGS"
