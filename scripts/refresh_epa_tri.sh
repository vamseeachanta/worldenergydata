#!/usr/bin/env bash
# ABOUTME: Refresh EPA TRI (Toxics Release Inventory) data for oil & gas facilities.
# ABOUTME: Downloads annual TRI basic data files and filters for oil & gas industry codes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${PROJECT_ROOT}/data/modules/hse/raw/epa_tri"

echo "=== EPA TRI Data Refresh ==="
echo "Project root: ${PROJECT_ROOT}"
echo "Output directory: ${OUTPUT_DIR}"
echo ""

# Parse arguments
FORCE_FLAG=""
YEARS="2020-2024"
NO_FILTER_FLAG=""
VERBOSE_FLAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_FLAG="--force"
            shift
            ;;
        --years)
            YEARS="$2"
            shift 2
            ;;
        --no-filter-industry)
            NO_FILTER_FLAG="--no-filter-industry"
            shift
            ;;
        --verbose)
            VERBOSE_FLAG="--verbose"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--force] [--years RANGE] [--no-filter-industry] [--verbose]"
            exit 1
            ;;
    esac
done

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Step 1: Acquire data from EPA
echo "[1/2] Acquiring EPA TRI data for years: ${YEARS}..."
cd "${PROJECT_ROOT}"
uv run python -m worldenergydata.hse.acquirers.epa_tri_acquirer \
    --output-dir "${OUTPUT_DIR}" \
    --years "${YEARS}" \
    ${FORCE_FLAG} \
    ${NO_FILTER_FLAG} \
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
echo "=== EPA TRI Data Refresh Complete ==="
