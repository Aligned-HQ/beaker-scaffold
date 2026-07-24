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

if ! check_trajectory_pass_rate; then
    printf '%b\n' \
        $'\033[31mWARNING: task does not meet the submission criteria. Packaging will continue so you can inspect the submission.\033[0m' \
        >&2
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
