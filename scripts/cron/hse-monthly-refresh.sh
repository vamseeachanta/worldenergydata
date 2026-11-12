#!/usr/bin/env bash
# Monthly public HSE collection; raw files remain on external storage.
# 17 3 2 * * WED_HSE_SOURCES_ROOT=<output_root> <repo>/scripts/cron/hse-monthly-refresh.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/cadence-common.sh"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"; export REPO_ROOT
cadence_init_repo_root

if [[ -z "${WED_HSE_SOURCES_ROOT:-}" ]]; then
    echo "WED_HSE_SOURCES_ROOT must specify the external output directory" >&2
    exit 2
fi

cd "$REPO_ROOT" || exit 2
mkdir -p "$WED_HSE_SOURCES_ROOT" || exit 1
uv run python scripts/hse/refresh_hse_sources.py \
    --config config/hse/monthly_sources.yml \
    --output-root "$WED_HSE_SOURCES_ROOT" --json
runner_status=$?
printf '%s hse-monthly-refresh exit=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$runner_status" \
    >> "${WED_HSE_SOURCES_ROOT}/refresh.log"
exit "$runner_status"
