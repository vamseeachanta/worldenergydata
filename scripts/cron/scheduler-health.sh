#!/usr/bin/env bash
# scheduler-health.sh — Weekly fresh-data-age report for EIA/BSEE/etc schedulers.
# Issue: worldenergydata#309 (https://github.com/vamseeachanta/worldenergydata/issues/309)
# Companion: worldenergydata#266 (operationalize EIA scheduler)
# Cross-repo: this cron lives in worldenergydata/ but uses a byte-identical
# copy of workspace-hub/scripts/cron/lib/cadence-common.sh. Drift is checked
# by workspace-hub's pre-push via scripts/sync/sync-cadence-helper.sh.
#
# Each scheduler job writes a manifest.json containing:
#   { "status": "success", "last_success_ts": "ISO8601", "refresh_interval_days": N }
# This cadence scans all configured job manifests and flags any where the
# data age exceeds the declared refresh interval.
#
# Env overrides (testing):
#   SCHEDULER_HEALTH_OUT_DIR     — override docs/reports output dir
#   SCHEDULER_HEALTH_WEEK        — override ISO week (e.g. 2026-W16)
#   SCHEDULER_HEALTH_JOBS        — comma-separated "name:manifest_path" pairs
#   SCHEDULER_HEALTH_WARN_COUNT  — warn threshold (default 0)
#   SCHEDULER_HEALTH_BLOCK_COUNT — block threshold (default 3)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/cadence-common.sh"
cadence_init_repo_root

WEEK="${SCHEDULER_HEALTH_WEEK:-$(cadence_period weekly)}"
OUT_DIR="${SCHEDULER_HEALTH_OUT_DIR:-${REPO_ROOT}/docs/reports}"
OUT="${OUT_DIR}/scheduler-health-${WEEK}.md"
WARN_COUNT="${SCHEDULER_HEALTH_WARN_COUNT:-0}"
BLOCK_COUNT="${SCHEDULER_HEALTH_BLOCK_COUNT:-3}"

# Default job list — each with expected manifest location.
declare -a JOB_NAMES=()
declare -a JOB_MANIFESTS=()
if [[ -n "${SCHEDULER_HEALTH_JOBS:-}" ]]; then
    IFS=',' read -ra pairs <<< "$SCHEDULER_HEALTH_JOBS"
    for p in "${pairs[@]}"; do
        JOB_NAMES+=("${p%%:*}")
        JOB_MANIFESTS+=("${p#*:}")
    done
else
    CONFIG_PATH="${REPO_ROOT}/config/scheduler/scheduler_config.yml"
    if [[ -f "$CONFIG_PATH" ]]; then
        derived_jobs="$(python3 - "$REPO_ROOT" "$CONFIG_PATH" <<'PY'
import sys
from pathlib import Path

import yaml

repo_root = Path(sys.argv[1])
config_path = Path(sys.argv[2])
config = yaml.safe_load(config_path.read_text()) or {}

for job in config.get("jobs", []):
    if not job.get("enabled", True):
        continue
    name = job.get("name")
    if not name:
        continue
    output_dir = Path(job.get("output_dir") or f"data/modules/{name}")
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    print(f"{name}|{output_dir / 'manifest.json'}")
PY
        )" || {
            echo "scheduler-health: failed to derive scheduler jobs from $CONFIG_PATH" >&2
            exit 1
        }
        while IFS='|' read -r name manifest; do
            [[ -z "$name" || -z "$manifest" ]] && continue
            JOB_NAMES+=("$name")
            JOB_MANIFESTS+=("$manifest")
        done <<< "$derived_jobs"
    fi
fi

mkdir -p "$OUT_DIR"

# ── Parse each manifest ─────────────────────────────────────────────────
TMP_ROWS="$(mktemp)"
TMP_STALE="$(mktemp)"
trap 'rm -f "$TMP_ROWS" "$TMP_STALE"' EXIT

stale_count=0
now_epoch=$(date +%s)

for i in "${!JOB_NAMES[@]}"; do
    name="${JOB_NAMES[$i]}"
    manifest="${JOB_MANIFESTS[$i]}"

    if [[ ! -f "$manifest" ]]; then
        printf "| %s | _(never ran)_ | — | — | ❌ manifest missing |\n" "$name" >> "$TMP_ROWS"
        printf "| %s | _(never ran)_ | — | — | ❌ manifest missing |\n" "$name" >> "$TMP_STALE"
        stale_count=$((stale_count + 1))
        continue
    fi

    parsed=$(python3 - "$manifest" <<'PY'
import json
import sys

manifest = sys.argv[1]
try:
    with open(manifest) as f:
        d = json.load(f)
    lt = d.get('last_success_ts', '')
    ri = d.get('refresh_interval_days', 7)
    st = d.get('status', 'success')
    print(f'{lt}|{ri}|{st}')
except Exception:
    print('||')
PY
    )
    IFS='|' read -r last_ts refresh_days manifest_status <<< "$parsed"
    [[ -z "$refresh_days" ]] && refresh_days=7
    [[ -z "$manifest_status" ]] && manifest_status=success

    if [[ -z "$last_ts" ]]; then
        printf "| %s | never | %sd | n/a | ❌ never ran |\n" "$name" "$refresh_days" >> "$TMP_ROWS"
        printf "| %s | never | %sd | n/a | ❌ never ran |\n" "$name" "$refresh_days" >> "$TMP_STALE"
        stale_count=$((stale_count + 1))
        continue
    fi

    if [[ "$manifest_status" != "success" ]]; then
        printf "| %s | %s | %sd | status %s | ❌ status %s |\n" "$name" "$last_ts" "$refresh_days" "$manifest_status" "$manifest_status" >> "$TMP_ROWS"
        printf "| %s | %s | %sd | status %s | ❌ status %s |\n" "$name" "$last_ts" "$refresh_days" "$manifest_status" "$manifest_status" >> "$TMP_STALE"
        stale_count=$((stale_count + 1))
        continue
    fi

    last_epoch=$(date -d "$last_ts" +%s 2>/dev/null || echo 0)
    if (( last_epoch == 0 )); then
        printf "| %s | %s | %sd | unparseable | ❌ ts format error |\n" "$name" "$last_ts" "$refresh_days" >> "$TMP_ROWS"
        printf "| %s | %s | %sd | unparseable | ❌ ts format error |\n" "$name" "$last_ts" "$refresh_days" >> "$TMP_STALE"
        stale_count=$((stale_count + 1))
        continue
    fi

    age_days=$(( (now_epoch - last_epoch) / 86400 ))
    if (( age_days > refresh_days )); then
        flag="🔴 stale ($((age_days - refresh_days))d over)"
        stale_count=$((stale_count + 1))
        printf "| %s | %s | %sd | %s | %s |\n" "$name" "$last_ts" "$refresh_days" "${age_days}d" "$flag" >> "$TMP_STALE"
    else
        flag="✅ fresh"
    fi
    printf "| %s | %s | %sd | %s | %s |\n" "$name" "$last_ts" "$refresh_days" "${age_days}d" "$flag" >> "$TMP_ROWS"
done

status="$(compute_status_band "$stale_count" "$WARN_COUNT" "$BLOCK_COUNT")"
summary="${stale_count} stale of ${#JOB_NAMES[@]} scheduler jobs (warn ${WARN_COUNT}, block ${BLOCK_COUNT})"

# ── Write report ─────────────────────────────────────────────────────────
{
    emit_report_header "scheduler-health" "$WEEK" "$status" "$summary"
    echo "Scanned ${#JOB_NAMES[@]} scheduler job(s)."
    echo
    echo "## Per-job fresh-data age"
    echo
    echo "| Job | Last successful write | Refresh interval | Age vs interval | Flag |"
    echo "|-----|-----------------------|------------------|-----------------|------|"
    if [[ -s "$TMP_ROWS" ]]; then
        cat "$TMP_ROWS"
    else
        echo "| — | — | — | — | _(no jobs configured)_ |"
    fi
    echo
    echo "## Recent failures (from logs/, if any)"
    echo
    if [[ -s "$TMP_STALE" ]]; then
        echo "_Jobs marked stale above should be investigated; log scanning deferred to a follow-up._"
    else
        echo "_None — all jobs within refresh interval._"
    fi
    echo
    echo "## Source"
    echo
    echo "Generated by \`scripts/cron/scheduler-health.sh\` (wed#309, companion wed#266)."
    echo "Shared helper \`lib/cadence-common.sh\` is a byte-identical vendored copy from"
    echo "workspace-hub; drift is caught by workspace-hub's pre-push sync check."
} > "$OUT"

echo "[scheduler-health] wrote $OUT (status: $status, ${stale_count} stale / ${#JOB_NAMES[@]} jobs)"
