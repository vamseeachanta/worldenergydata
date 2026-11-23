#!/usr/bin/env bash
# EIA weekly feed sync — cron-compatible script.
#
# Runs incremental ingestion of EIA API v2 weekly petroleum and natural gas
# data. Designed to be triggered weekly via cron or a systemd timer.
#
# Required environment variable:
#   EIA_API_KEY — your EIA API v2 key (obtain at https://www.eia.gov/opendata/)
#
# Optional environment variables:
#   EIA_OUTPUT_DIR   — JSONL output directory  (default: ./data/eia)
#   EIA_STATE_DIR    — ingestion state dir     (default: EIA_OUTPUT_DIR)
#   EIA_LOG_DIR      — log file directory      (default: ./logs/eia)
#
# Crontab example (run every Friday at 08:00):
#   0 8 * * 5 /path/to/worldenergydata/scripts/eia_weekly_sync.sh >> /var/log/eia_sync.log 2>&1
#
# Exit codes:
#   0 — success
#   1 — EIA_API_KEY not set
#   2 — sync command failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

OUTPUT_DIR="${EIA_OUTPUT_DIR:-${REPO_ROOT}/data/eia}"
STATE_DIR="${EIA_STATE_DIR:-${OUTPUT_DIR}}"
LOG_DIR="${EIA_LOG_DIR:-${REPO_ROOT}/logs/eia}"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/eia_sync_${TIMESTAMP}.log"

mkdir -p "${OUTPUT_DIR}" "${STATE_DIR}" "${LOG_DIR}"

exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=== EIA weekly sync started: ${TIMESTAMP} ==="
echo "Output dir : ${OUTPUT_DIR}"
echo "State dir  : ${STATE_DIR}"
echo "Log file   : ${LOG_FILE}"

if [ -z "${EIA_API_KEY:-}" ]; then
    echo "ERROR: EIA_API_KEY environment variable is not set." >&2
    echo "       Export EIA_API_KEY before running this script." >&2
    exit 1
fi

# Locate the project's Python environment
if [ -f "${REPO_ROOT}/.venv/bin/python" ]; then
    PYTHON="${REPO_ROOT}/.venv/bin/python"
elif command -v uv &>/dev/null; then
    PYTHON="uv run python"
else
    PYTHON="python3"
fi

echo "Using Python: ${PYTHON}"

${PYTHON} -m worldenergydata.eia.ingestion_runner \
    --output-dir "${OUTPUT_DIR}" \
    --state-dir  "${STATE_DIR}" \
    || {
        echo "ERROR: EIA sync failed with exit code $?" >&2
        exit 2
    }

echo "=== EIA weekly sync completed: $(date -u +%Y%m%d_%H%M%S) ==="
