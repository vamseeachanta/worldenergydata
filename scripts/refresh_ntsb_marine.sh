#!/usr/bin/env bash
# ABOUTME: Refresh NTSB CAROL marine investigation data.
# ABOUTME: Downloads from NTSB CAROL API and processes into standardized CSV.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${PROJECT_ROOT}/data/modules/marine_safety/raw/ntsb"

echo "=== NTSB Marine Data Refresh ==="
echo "Project root: ${PROJECT_ROOT}"
echo "Output directory: ${OUTPUT_DIR}"
echo ""

# Parse arguments
FORCE_FLAG=""
MAX_PAGES="200"
VERBOSE_FLAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_FLAG="--force"
            shift
            ;;
        --max-pages)
            MAX_PAGES="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE_FLAG="--verbose"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--force] [--max-pages N] [--verbose]"
            exit 1
            ;;
    esac
done

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Step 1: Acquire data from NTSB CAROL
echo "[1/2] Acquiring NTSB CAROL marine data..."
cd "${PROJECT_ROOT}"
uv run python -m worldenergydata.marine_safety.acquirers.ntsb_carol_acquirer \
    --output-dir "${OUTPUT_DIR}" \
    --max-pages "${MAX_PAGES}" \
    ${FORCE_FLAG} \
    ${VERBOSE_FLAG}

# Step 2: Report results
echo ""
echo "[2/2] Results:"
if [ -d "${OUTPUT_DIR}" ]; then
    echo "Files in output directory:"
    ls -lh "${OUTPUT_DIR}/"
    echo ""
    for f in "${OUTPUT_DIR}"/*.csv; do
        if [ -f "$f" ]; then
            lines=$(wc -l < "$f")
            echo "  ${f##*/}: ${lines} lines"
        fi
    done
else
    echo "No output directory created."
fi

echo ""
echo "=== NTSB Marine Data Refresh Complete ==="
