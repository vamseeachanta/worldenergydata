#!/usr/bin/env bash
# ABOUTME: End-to-end refresh script for USCG MISLE marine casualty data.
# ABOUTME: Downloads bulk dataset, then imports to the marine safety database.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

OUTPUT_DIR="data/modules/marine_safety/raw/uscg_misle"
FORCE_FLAG=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_FLAG="--force"
            shift
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--force] [--output-dir DIR]"
            echo ""
            echo "Refresh USCG MISLE marine casualty data."
            echo ""
            echo "Options:"
            echo "  --force        Re-download even if data exists"
            echo "  --output-dir   Override output directory (default: $OUTPUT_DIR)"
            echo "  -h, --help     Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

echo "============================================================"
echo "  USCG MISLE Data Refresh"
echo "  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"
echo ""

echo "Step 1: Downloading MISLE bulk data..."
echo "  Output: $OUTPUT_DIR"
echo ""

uv run python -m worldenergydata.marine_safety.acquirers.uscg_misle_acquirer \
    --output-dir "$OUTPUT_DIR" $FORCE_FLAG

echo ""
echo "Step 2: Importing to database..."
echo "  Data dir: $OUTPUT_DIR"
echo ""

# Check if data files exist before attempting import
DATA_FILES=$(find "$OUTPUT_DIR" -maxdepth 2 -type f \( -name "*.csv" -o -name "*.txt" -o -name "*.mdb" \) 2>/dev/null | head -1)

if [ -z "$DATA_FILES" ]; then
    echo "WARNING: No data files found in $OUTPUT_DIR"
    echo "  Import step skipped. Check acquisition_manifest.json for details."
    echo ""
    echo "  If download failed, try manual download from:"
    echo "  https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/"
    echo "  Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/"
    echo "  Marine-Casualty-and-Pollution-Data-for-Researchers/"
    echo ""
    echo "  Alternative: use DLP historical data (1995-2012):"
    echo "  data/modules/marine_safety/raw/dlp_historical/"
else
    echo "  Found data files, proceeding with import..."
    # Import uses the existing MISLEImporter
    # Uncomment when database and CLI are configured:
    # uv run python -m worldenergydata.marine_safety.cli_import \
    #     --source misle --data-dir "$OUTPUT_DIR"
    echo "  NOTE: Database import step requires database configuration."
    echo "  Run manually when ready:"
    echo "    uv run python -m worldenergydata.marine_safety.cli_import --source misle --data-dir $OUTPUT_DIR"
fi

echo ""
echo "============================================================"
echo "  USCG MISLE refresh complete"
echo "  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"
