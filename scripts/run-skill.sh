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
.claude/skills/ (Claude). Each run overwrites its Markdown result in
skill-reports/ and updates skill-status.md.
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

REPORT_DIR="${REPO_ROOT}/skill-reports"
STATUS_FILE="${REPO_ROOT}/skill-status.md"
REPORT_REL="skill-reports/${SKILL}.md"
REPORT_FILE="${REPO_ROOT}/${REPORT_REL}"
mkdir -p "$REPORT_DIR" || die "could not create $REPORT_DIR"

status_row_field() {
    local wanted="$1"
    local field_number="$2"
    local fallback="$3"
    if [[ ! -f "$STATUS_FILE" ]]; then
        printf '%s\n' "$fallback"
        return
    fi
    awk -F'|' -v wanted="$wanted" -v field_number="$field_number" -v fallback="$fallback" '
        NR > 3 {
            name = $2
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", name)
            gsub(/`/, "", name)
            if (name == wanted) {
                value = $field_number
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
                gsub(/`/, "", value)
                print value
                found = 1
                exit
            }
        }
        END {
            if (!found) print fallback
        }
    ' "$STATUS_FILE"
}

write_status_file() {
    local current_status="$1"
    local current_time="$2"
    local current_target="$3"
    local status_tmp="${STATUS_FILE}.tmp.$$"
    local skill_name
    local row_status
    local row_time
    local row_target

    {
        printf '%s\n\n' '# Skill status'
        printf '%s\n\n' 'This file is overwritten whenever a skill wrapper runs.'
        printf '| Skill | Status | Last run (UTC) | Target | Report |\n'
        printf '|---|---|---|---|---|\n'
        for skill_name in task-fixer task-review trajectory-review; do
            if [[ "$skill_name" = "$SKILL" ]]; then
                row_status="$current_status"
                row_time="$current_time"
                row_target="$current_target"
            else
                row_status="$(status_row_field "$skill_name" 3 "Not Run")"
                row_time="$(status_row_field "$skill_name" 4 "—")"
                row_target="$(status_row_field "$skill_name" 5 "—")"
            fi
            printf '| `%s` | %s | %s | `%s` | [%s.md](skill-reports/%s.md) |\n' \
                "$skill_name" "$row_status" "$row_time" "$row_target" \
                "$skill_name" "$skill_name"
        done
    } > "$status_tmp" || {
        rm -f "$status_tmp"
        return 1
    }
    mv "$status_tmp" "$STATUS_FILE"
}

OUTPUT_TMP="$(mktemp)" || die "could not create temporary skill output file"
FINAL_OUTPUT_TMP="$(mktemp)" || {
    rm -f "$OUTPUT_TMP"
    die "could not create temporary final skill output file"
}
STATUS_OUTPUT_TMP="$(mktemp)" || {
    rm -f "$OUTPUT_TMP" "$FINAL_OUTPUT_TMP"
    die "could not create temporary status output file"
}

RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')-${SKILL}-$$"
STARTED_AT="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
RUN_STATUS="FAILED"
EXIT_CODE=1
FINALIZED=0

write_status_file "Run" "$STARTED_AT" "$TARGET_REL" || die "could not update $STATUS_FILE"

extract_final_handoff() {
    local source="$1"
    local destination="$2"

    awk '
        function is_status(line, cleaned) {
            cleaned = line
            gsub(/[*][*]/, "", cleaned)
            return cleaned ~ /^[[:space:]]*(Status|Verdict):[[:space:]]*(PASS|FAIL|INCONCLUSIVE)([[:space:]]|$)/
        }
        {
            lines[NR] = $0
            if (is_status($0)) {
                start = NR
            }
        }
        END {
            if (!start) {
                start = 1
            }
            for (line = start; line <= NR; line++) {
                if (line > start && lines[line] ~ /^[[:space:]]*tokens used([[:space:]]|$)/) {
                    break
                }
                print lines[line]
            }
        }
    ' "$source" > "$destination"
}

extract_task_review_handoff() {
    local source="$1"
    local destination="$2"

    awk '
        {
            lines[NR] = $0
            heading = tolower($0)
            if (heading ~ /^##[[:space:]]+practitioner[[:space:]]+plausibility[[:space:]]*$/) {
                start = NR
            }
        }
        END {
            if (!start) {
                exit 2
            }
            for (line = start; line <= NR; line++) {
                if (line > start && lines[line] ~ /^[[:space:]]*tokens used([[:space:]]|$)/) {
                    break
                }
                print lines[line]
            }
        }
    ' "$source" > "$destination" || return $?
}

prepare_report_outputs() {
    local source="$1"

    case "$SKILL" in
        task-fixer)
            extract_final_handoff "$source" "$FINAL_OUTPUT_TMP"
            ;;
        task-review)
            if ! extract_task_review_handoff "$source" "$FINAL_OUTPUT_TMP"; then
                extract_final_handoff "$source" "$FINAL_OUTPUT_TMP"
            fi
            ;;
        *)
            cp "$source" "$FINAL_OUTPUT_TMP"
            ;;
    esac
    extract_final_handoff "$source" "$STATUS_OUTPUT_TMP"
}

skill_result_status() {
    if [[ "$RUN_STATUS" = "DRY_RUN" ]]; then
        printf '%s\n' 'Run'
        return
    fi
    if ((EXIT_CODE != 0)); then
        printf '%s\n' 'Fail'
        return
    fi
    if sed 's/[*][*]//g' "$STATUS_OUTPUT_TMP" | grep -Ei \
        '^[[:space:]]*(Status|Verdict):[[:space:]]*PASS([[:space:]]|$)' >/dev/null; then
        printf '%s\n' 'Pass'
    elif sed 's/[*][*]//g' "$STATUS_OUTPUT_TMP" | grep -Ei \
        '^[[:space:]]*(Status|Verdict):[[:space:]]*(FAIL|INCONCLUSIVE)([[:space:]]|$)' >/dev/null; then
        printf '%s\n' 'Fail'
    else
        printf '%s\n' 'Fail'
    fi
}

write_report() {
    local result_status="$1"
    local ended_at="$2"
    local output_sha256="$3"
    local report_tmp="${REPORT_FILE}.tmp.$$"
    {
        printf '# Skill report: %s\n\n' "$SKILL"
        printf '**Status:** %s\n\n' "$result_status"
        printf '| Field | Value |\n'
        printf '|---|---|\n'
        printf '| Run ID | `%s` |\n' "$RUN_ID"
        printf '| Skill | `%s` |\n' "$SKILL"
        printf '| Runner | `%s` |\n' "$RUNNER"
        printf '| Target | `%s` |\n' "$TARGET_REL"
        printf '| Started (UTC) | `%s` |\n' "$STARTED_AT"
        printf '| Finished (UTC) | `%s` |\n' "$ended_at"
        printf '| Exit code | `%s` |\n' "$EXIT_CODE"
        printf '| Skill SHA-256 | `%s` |\n' "$SKILL_SHA256"
        printf '| Agent output SHA-256 | `%s` |\n' "$output_sha256"
        case "$SKILL" in
            task-fixer) printf '\n## Final handoff\n\n' ;;
            task-review) printf '\n## Final review\n\n' ;;
            *) printf '\n## Agent output\n\n' ;;
        esac
        if [[ -s "$FINAL_OUTPUT_TMP" ]]; then
            cat "$FINAL_OUTPUT_TMP"
            printf '\n'
        else
            printf '_The agent produced no output._\n'
        fi
    } > "$report_tmp" || {
        rm -f "$report_tmp"
        return 1
    }
    mv "$report_tmp" "$REPORT_FILE"
}

finalize() {
    local ended_at
    local result_status
    local output_sha256
    if ((FINALIZED)); then
        return
    fi
    FINALIZED=1
    ended_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    if ! prepare_report_outputs "$OUTPUT_TMP"; then
        cp "$OUTPUT_TMP" "$FINAL_OUTPUT_TMP" || true
        cp "$OUTPUT_TMP" "$STATUS_OUTPUT_TMP" || true
    fi
    result_status="$(skill_result_status)"
    output_sha256="$(sha256_file "$FINAL_OUTPUT_TMP" 2>/dev/null || true)"
    if ! write_report "$result_status" "$ended_at" "$output_sha256"; then
        printf 'ERROR: could not write skill report: %s\n' "$REPORT_FILE" >&2
        result_status="Fail"
    fi
    if ! write_status_file "$result_status" "$ended_at" "$TARGET_REL"; then
        printf 'ERROR: could not update skill status: %s\n' "$STATUS_FILE" >&2
    fi
    rm -f "$OUTPUT_TMP"
    rm -f "$FINAL_OUTPUT_TMP" "$STATUS_OUTPUT_TMP"
    printf '\nReport: %s\n' "$REPORT_FILE" >&2
    printf 'Status: %s\n' "$result_status" >&2
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
smallest task-local edits needed and return only the final handoff, without
planning, tool transcripts, or duplicated status sections. For task-review and
trajectory-review, do not edit the task; return the complete requested scorecard
or verdict as Markdown, not only a summary or a file path. Start the final
response with the exact
Markdown line **Status:** PASS when the skill passes and **Status:** FAIL when
it does not.
Do not modify skill-reports/ or skill-status.md; the wrapper saves your final
Markdown output and updates those files.
EOF
)

if ((DRY_RUN)); then
    printf 'DRY RUN: would invoke %s for %s on %s\n' "$RUNNER" "$SKILL" "$TARGET_ABS" | tee "$OUTPUT_TMP"
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
        "$PROMPT" 2>&1 | tee "$OUTPUT_TMP"
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
    ) 2>&1 | tee "$OUTPUT_TMP"
    EXIT_CODE=${PIPESTATUS[0]}
fi

if ! prepare_report_outputs "$OUTPUT_TMP"; then
    cp "$OUTPUT_TMP" "$FINAL_OUTPUT_TMP" || true
    cp "$OUTPUT_TMP" "$STATUS_OUTPUT_TMP" || true
fi

if ((EXIT_CODE == 0)); then
    RUN_STATUS=COMPLETED
    RESULT_STATUS="$(skill_result_status)"
    if [[ "$RESULT_STATUS" = "Fail" ]]; then
        EXIT_CODE=1
        RUN_STATUS=FAIL
    fi
else
    RUN_STATUS=FAIL
fi
exit "$EXIT_CODE"
