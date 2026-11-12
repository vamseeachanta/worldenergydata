#!/usr/bin/env bash
# Optional report-review aid; not a commit hook or repository identifier gate.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -B "$script_dir/check_operator_aggregation.py" "$@"
