#!/usr/bin/env bash
# Run one of the local authoring skills and write an auditable run record.
set -uo pipefail

usage() {
    cat <<'USAGE'
Usage: run-skill.sh --skill SKILL [TARGET] [options]

Run SKILL through a locally installed agent CLI. TARGET is relative to this
repository (or an absolute path inside it). For task-fixer and task-review the
default target is task/. trajectory-review requires an explicit target.

Skills:
  task-fixer          Repair and normalize a task before review.
  task-review         Produce the rubric scorecard for a task.
  trajectory-review   Review a completed trajectory run or task path.

Options:
  --runner codex|claude|auto  Agent CLI to use (default: auto).
  --target PATH               Explicit target path.
  --dry-run                   Record the command without invoking an agent.
  -h, --help                  Show this help.

The selected runner reads the local skill file from .agents/skills/ (Codex) or
.claude/skills/ (Claude). Successful runs are recorded in skill-runs.log and
their transcripts are stored in .skill-runs/.
USAGE
}

die() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 2
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

SKILL=""
TARGET=""
RUNNER="${SKILL_RUNNER:-auto}"
DRY_RUN=0

while (($# > 0)); do
    case "$1" in
        --skill)
            (($# >= 2)) || die "--skill requires a value"
            SKILL="$2"
            shift 2
            ;;
        --runner)
            (($# >= 2)) || die "--runner requires codex, claude, or auto"
            RUNNER="$2"
            shift 2
            ;;
        --target)
            (($# >= 2)) || die "--target requires a path"
            TARGET="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            (($# == 1 && -z "$TARGET")) || die "only one target path is allowed"
            TARGET="$1"
            shift
            ;;
        -* )
            die "unknown option: $1"
            ;;
        *)
            [[ -z "$TARGET" ]] || die "only one target path is allowed"
            TARGET="$1"
            shift
            ;;
    esac
done

case "$SKILL" in
    task-fixer|task-review)
        [[ -n "$TARGET" ]] || TARGET="task"
        ;;
    trajectory-review)
        [[ -n "$TARGET" ]] || die "trajectory-review requires a target path"
        ;;
    *)
        die "--skill must be task-fixer, task-review, or trajectory-review"
        ;;
esac

case "$RUNNER" in
    auto)
        if command -v codex >/dev/null 2>&1; then
            RUNNER="codex"
        elif command -v claude >/dev/null 2>&1; then
            RUNNER="claude"
        else
            die "no supported agent CLI found; install codex or claude"
        fi
        ;;
    codex|claude)
        ;;
    *)
        die "--runner must be codex, claude, or auto"
        ;;
esac

if [[ "$TARGET" = /* ]]; then
    TARGET_ABS="$TARGET"
else
    TARGET_ABS="${REPO_ROOT}/${TARGET}"
fi
[[ -d "$TARGET_ABS" ]] || die "target directory does not exist: $TARGET"
TARGET_ABS="$(cd -- "$TARGET_ABS" && pwd -P)"
case "$TARGET_ABS" in
    "${REPO_ROOT}"/*)
        ;;
    *)
        die "target must be inside the repository: $TARGET_ABS"
        ;;
esac
TARGET_REL="${TARGET_ABS#${REPO_ROOT}/}"

case "$RUNNER" in
    codex)
        SKILL_ROOT="${REPO_ROOT}/.agents/skills"
        RUNNER_BIN="$(command -v codex)"
        ;;
    claude)
        SKILL_ROOT="${REPO_ROOT}/.claude/skills"
        RUNNER_BIN="$(command -v claude)"
        ;;
esac

SKILL_FILE="${SKILL_ROOT}/${SKILL}/SKILL.md"
[[ -f "$SKILL_FILE" ]] || die "missing local skill file: $SKILL_FILE"

AGENTS_SKILL_FILE="${REPO_ROOT}/.agents/skills/${SKILL}/SKILL.md"
CLAUDE_SKILL_FILE="${REPO_ROOT}/.claude/skills/${SKILL}/SKILL.md"
if [[ -f "$AGENTS_SKILL_FILE" && -f "$CLAUDE_SKILL_FILE" ]]; then
    cmp -s "$AGENTS_SKILL_FILE" "$CLAUDE_SKILL_FILE" || \
        die "the .agents and .claude copies of ${SKILL} are not identical"
fi

sha256_file() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        return 1
    fi
}

SKILL_SHA256="$(sha256_file "$SKILL_FILE")" || die "could not calculate the skill hash"

AUDIT_LOG="${REPO_ROOT}/skill-runs.log"
RUN_LOG_DIR="${REPO_ROOT}/.skill-runs"
AUDIT_HEADER=$'# run_id\tstarted_at_utc\tended_at_utc\tskill\trunner\tstatus\texit_code\ttarget\tskill_sha256\toutput_log\toutput_sha256'
mkdir -p "$RUN_LOG_DIR" || die "could not create $RUN_LOG_DIR"
if [[ ! -e "$AUDIT_LOG" ]]; then
    printf '%s\n' "$AUDIT_HEADER" > "$AUDIT_LOG" || die "could not create $AUDIT_LOG"
elif [[ ! -s "$AUDIT_LOG" ]]; then
    printf '%s\n' "$AUDIT_HEADER" >> "$AUDIT_LOG" || die "could not initialize $AUDIT_LOG"
fi

ACTUAL_HEADER="$(head -n 1 "$AUDIT_LOG")"
[[ "$ACTUAL_HEADER" = "$AUDIT_HEADER" ]] || die "$AUDIT_LOG has an unexpected header"

RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')-${SKILL}-$$"
STARTED_AT="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
RUN_LOG_REL=".skill-runs/${RUN_ID}.log"
RUN_LOG="${REPO_ROOT}/${RUN_LOG_REL}"
RUN_STATUS="FAILED"
EXIT_CODE=1
OUTPUT_SHA256=""
FINALIZED=0

{
    printf '%s\n' '# Agent skill runner transcript'
    printf 'run_id=%s\n' "$RUN_ID"
    printf 'skill=%s\n' "$SKILL"
    printf 'skill_file=%s\n' "$SKILL_FILE"
    printf 'skill_sha256=%s\n' "$SKILL_SHA256"
    printf 'runner=%s\n' "$RUNNER"
    printf 'runner_bin=%s\n' "$RUNNER_BIN"
    printf 'target=%s\n' "$TARGET_ABS"
    printf 'started_at_utc=%s\n' "$STARTED_AT"
    printf 'network_policy=offline task execution; no live services or downloads\n'
    printf '\n'
} > "$RUN_LOG" || die "could not create $RUN_LOG"

finalize() {
    local ended_at
    if ((FINALIZED)); then
        return
    fi
    FINALIZED=1
    ended_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    OUTPUT_SHA256="$(sha256_file "$RUN_LOG" 2>/dev/null || true)"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$RUN_ID" "$STARTED_AT" "$ended_at" "$SKILL" "$RUNNER" \
        "$RUN_STATUS" "$EXIT_CODE" "$TARGET_REL" "$SKILL_SHA256" \
        "$RUN_LOG_REL" "$OUTPUT_SHA256" >> "$AUDIT_LOG"
    printf '\nAudit record: %s\n' "$AUDIT_LOG" >&2
    printf 'Transcript: %s\n' "$RUN_LOG" >&2
}
trap finalize EXIT
trap 'RUN_STATUS=INTERRUPTED; EXIT_CODE=130; exit 130' INT TERM

PROMPT=$(cat <<EOF
Run the local ${SKILL} skill for the authoring project.

Read and follow the complete skill instructions at:
${SKILL_FILE}

Apply the skill to this target:
${TARGET_ABS}

The client policy is mandatory: task environments have no internet access and
each final runtime or separate verifier image must be at most 2 GB
(2,000,000,000 bytes). Preserve those constraints and do not enable internet
access to work around a bootstrap or dependency issue.

Use the skill's required workflow and evidence rules. For task-fixer, make the
smallest task-local edits needed. For task-review and trajectory-review, do not
edit the task; return the requested scorecard or verdict. Do not modify
skill-runs.log or .skill-runs/; the wrapper records the audit entry.
EOF
)

{
    printf 'prompt_target=%s\n' "$TARGET_ABS"
    printf 'invocation=non-interactive %s\n' "$RUNNER"
    printf 'skill_invocation_started_at_utc=%s\n\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} >> "$RUN_LOG"

if ((DRY_RUN)); then
    printf 'DRY RUN: would invoke %s for %s on %s\n' "$RUNNER" "$SKILL" "$TARGET_ABS" | tee -a "$RUN_LOG"
    RUN_STATUS=DRY_RUN
    EXIT_CODE=0
    exit 0
fi

if [[ "$RUNNER" = codex ]]; then
    "$RUNNER_BIN" \
        --ask-for-approval never \
        exec \
        -C "$REPO_ROOT" \
        --sandbox workspace-write \
        --skip-git-repo-check \
        "$PROMPT" 2>&1 | tee -a "$RUN_LOG"
    EXIT_CODE=${PIPESTATUS[0]}
else
    (
        cd -- "$REPO_ROOT" || exit 1
        "$RUNNER_BIN" \
            --print \
            --no-session-persistence \
            --permission-mode acceptEdits \
            --add-dir "$REPO_ROOT" \
            "$PROMPT"
    ) 2>&1 | tee -a "$RUN_LOG"
    EXIT_CODE=${PIPESTATUS[0]}
fi

if ((EXIT_CODE == 0)); then
    RUN_STATUS=COMPLETED
else
    RUN_STATUS=FAIL
fi
exit "$EXIT_CODE"
