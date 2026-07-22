#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
SUBMISSION_DIR="${REPO_ROOT}/submission"
STAGING_DIR="${REPO_ROOT}/.submission.tmp.$$"

die() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

cleanup() {
    if [[ -d "$STAGING_DIR" ]]; then
        rm -rf "$STAGING_DIR"
    fi
}
trap cleanup EXIT

for source_name in task trajectories skill-reports; do
    source_path="${REPO_ROOT}/${source_name}"
    [[ -d "$source_path" ]] || die "required directory is missing: ${source_path}"
done

check_trajectory_pass_rate() {
    local summary_path="${REPO_ROOT}/trajectories/summary.md"
    [[ -f "$summary_path" ]] || die "required trajectory summary is missing: ${summary_path}"

    local stats
    stats="$(awk -F'|' '
        function trim(value) {
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
            return value
        }
        function parse_cell(cell, agent, fraction, counts) {
            if (!match(cell, /^[[:space:]]*[0-9]+[[:space:]]*\/[[:space:]]*[0-9]+/)) {
                return 0
            }
            fraction = substr(cell, RSTART, RLENGTH)
            gsub(/[[:space:]]/, "", fraction)
            split(fraction, counts, "/")
            passed[agent] += counts[1] + 0
            trials[agent] += counts[2] + 0
            return 1
        }
        !header {
            for (column = 2; column <= NF; column++) {
                name = tolower(trim($column))
                if (name ~ /^claude(-|$)/) {
                    if (claude_column) duplicate = 1
                    claude_column = column
                } else if (name ~ /^codex(-|$)/) {
                    if (codex_column) duplicate = 1
                    codex_column = column
                } else if (name ~ /^gemini(-|$)/) {
                    if (gemini_column) duplicate = 1
                    gemini_column = column
                }
            }
            if (tolower(trim($2)) == "task" && tolower(trim($3)) == "oracle") {
                header = 1
            }
            next
        }
        header && trim($2) != "" && trim($2) != "---" && trim($3) != "" {
            if (!parse_cell($claude_column, "claude")) invalid = 1
            if (!parse_cell($codex_column, "codex")) invalid = 1
            if (!parse_cell($gemini_column, "gemini")) invalid = 1
            rows++
        }
        END {
            if (!header) {
                print "summary.md is missing the Task/Oracle result table" > "/dev/stderr"
                exit 2
            }
            if (duplicate || !claude_column || !codex_column || !gemini_column) {
                print "summary.md must contain one Claude, Codex, and Gemini column" > "/dev/stderr"
                exit 2
            }
            if (!rows || invalid || !trials["claude"] || !trials["codex"] || !trials["gemini"]) {
                print "summary.md does not contain complete Claude/Codex/Gemini pass counts" > "/dev/stderr"
                exit 2
            }
            claude_rate = passed["claude"] / trials["claude"]
            codex_rate = passed["codex"] / trials["codex"]
            gemini_rate = passed["gemini"] / trials["gemini"]
            average_rate = (claude_rate + codex_rate + gemini_rate) / 3
            printf "%d %d %.12f %d %d %.12f %d %d %.12f %.12f\n", \
                passed["claude"], trials["claude"], claude_rate, \
                passed["codex"], trials["codex"], codex_rate, \
                passed["gemini"], trials["gemini"], gemini_rate, average_rate
        }
    ' "$summary_path")" || die "could not validate trajectory pass rates in ${summary_path}"

    local claude_pass claude_trials claude_rate
    local codex_pass codex_trials codex_rate
    local gemini_pass gemini_trials gemini_rate average_rate
    read -r claude_pass claude_trials claude_rate \
        codex_pass codex_trials codex_rate \
        gemini_pass gemini_trials gemini_rate average_rate <<< "$stats"

    if ! awk -v average_rate="$average_rate" 'BEGIN { exit !(average_rate < 0.5) }'; then
        die "average Claude/Codex/Gemini pass rate must be below 50% (Oracle is ignored)"
    fi

    local claude_percent codex_percent gemini_percent average_percent
    claude_percent="$(awk -v rate="$claude_rate" 'BEGIN { printf "%.1f", rate * 100 }')"
    codex_percent="$(awk -v rate="$codex_rate" 'BEGIN { printf "%.1f", rate * 100 }')"
    gemini_percent="$(awk -v rate="$gemini_rate" 'BEGIN { printf "%.1f", rate * 100 }')"
    average_percent="$(awk -v rate="$average_rate" 'BEGIN { printf "%.1f", rate * 100 }')"
    printf 'Trajectory pass-rate check: Claude %s/%s (%s%%), Codex %s/%s (%s%%), Gemini %s/%s (%s%%); average %s%% (< 50%%).\n' \
        "$claude_pass" "$claude_trials" "$claude_percent" \
        "$codex_pass" "$codex_trials" "$codex_percent" \
        "$gemini_pass" "$gemini_trials" "$gemini_percent" \
        "$average_percent"
}

check_trajectory_pass_rate

if [[ -e "$SUBMISSION_DIR" || -L "$SUBMISSION_DIR" ]]; then
    printf 'WARNING: %s already exists and will be overwritten. Continue? [y/N] ' \
        "$SUBMISSION_DIR" >&2
    if ! read -r answer; then
        printf '\nSubmission packaging canceled.\n' >&2
        exit 1
    fi
    case "$answer" in
        y|Y|yes|YES|Yes)
            ;;
        *)
            printf 'Submission packaging canceled; existing directory was preserved.\n' >&2
            exit 1
            ;;
    esac
fi

mkdir "$STAGING_DIR"
cp -R "${REPO_ROOT}/task" "$STAGING_DIR/task"
cp -R "${REPO_ROOT}/trajectories" "$STAGING_DIR/trajectories"
cp -R "${REPO_ROOT}/skill-reports" "$STAGING_DIR/skill-reports"

if [[ -e "$SUBMISSION_DIR" || -L "$SUBMISSION_DIR" ]]; then
    rm -rf "$SUBMISSION_DIR"
fi
mv "$STAGING_DIR" "$SUBMISSION_DIR"

printf 'Submission package created at: %s\n' "$SUBMISSION_DIR"
printf 'Contents:\n'
printf '  - task/\n'
printf '  - trajectories/\n'
printf '  - skill-reports/\n'
