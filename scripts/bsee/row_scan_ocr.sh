#!/usr/bin/env bash
# One batch of the scanned ROW file and pipeline map OCR job (row_scan_ocr.py),
# at the lowest CPU and I/O priority. Meant for a cron line every 10 minutes; a
# lock in the data directory keeps one run at a time, and a STOP file there ends
# the job.
#
#   row_scan_ocr.sh <data_dir> <K/N> [more row_scan_ocr.py run options]
#
# Environment: PYTHON (default python3); OCR_TOOL_PATH, a search path holding
# pdftoppm and tesseract when they are not on PATH.
set -u
[ $# -ge 2 ] || { echo "usage: row_scan_ocr.sh <data_dir> <K/N> [options]"; exit 2; }
data_dir=$1
shard=$2
shift 2
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
mkdir -p "$data_dir" || exit 1
[ -e "$data_dir/STOP" ] && exit 0
extra=()
[ -n "${OCR_TOOL_PATH:-}" ] && extra+=(--tool-path "$OCR_TOOL_PATH")
prio=()
command -v nice >/dev/null 2>&1 && prio+=(nice -n 19)
command -v ionice >/dev/null 2>&1 && prio+=(ionice -c 3)
exec "${prio[@]}" "${PYTHON:-python3}" "$here/row_scan_ocr.py" run \
  --data-dir "$data_dir" --shard "$shard" \
  --segments "$repo/data/modules/bsee/pipeline_risers/riser_segments.csv" \
  --log "$data_dir/run.log" "${extra[@]}" "$@" >/dev/null 2>>"$data_dir/run.err"
