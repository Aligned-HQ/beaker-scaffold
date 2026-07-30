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
    python3 "${REPO_ROOT}/scripts/check_trajectory_pass_rate.py" \
        --trajectories "${REPO_ROOT}/trajectories"
}

if validation_output="$(check_trajectory_pass_rate 2>&1)"; then
    printf '%s\n' "$validation_output"
else
    red=$'\033[31m'
    reset=$'\033[0m'
    if [[ "$validation_output" == *"HARD SUBMISSION FAILURE"* ]]; then
        printf '%s\n' "${red}HARD FAILURE: do not submit this task until the per-agent difficulty gate is fixed.${reset}" >&2
    else
        printf '%s\n' "${red}WARNING: task does not meet the submission criteria.${reset}" >&2
    fi
    printf '%s\n' "${red}Criteria details: ${validation_output}${reset}" >&2
    printf '%s\n' "${red}Packaging will continue so you can inspect the submission.${reset}" >&2
fi

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
