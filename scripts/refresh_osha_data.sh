#!/usr/bin/env bash
# ABOUTME: Full OSHA data refresh pipeline script
# ABOUTME: Downloads, filters, and imports OSHA enforcement + fatality data
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

DATA_DIR="data/modules/hse/raw/osha"
FATALITY_DIR="data/modules/hse/raw/osha/fatalities"

echo "=== OSHA Data Refresh Pipeline ==="
echo "Project: $PROJECT_DIR"
echo "Data dir: $DATA_DIR"
echo ""

# Step 1: Download OSHA enforcement data (inspections, violations, accidents)
echo "Step 1/4: Downloading OSHA enforcement data..."
uv run python -m worldenergydata.modules.hse.acquirers.osha_acquirer \
  --output-dir "$DATA_DIR" \
  --force \
  --filter-naics

echo ""

# Step 2: Download OSHA fatality and severe injury data
echo "Step 2/4: Downloading OSHA fatality/severe injury data..."
uv run python -m worldenergydata.modules.hse.acquirers.osha_fatalities_acquirer \
  --output-dir "$FATALITY_DIR" \
  --force \
  --filter-naics \
  --inspection-csv "$DATA_DIR/osha_inspection.csv"

echo ""

# Step 3: Report downloaded file sizes
echo "Step 3/4: Download summary..."
echo "--- Raw files ---"
for f in "$DATA_DIR"/*.csv; do
  if [ -f "$f" ]; then
    lines=$(wc -l < "$f")
    size=$(du -h "$f" | cut -f1)
    echo "  $(basename "$f"): $lines lines ($size)"
  fi
done

echo "--- Filtered files ---"
for f in "$DATA_DIR"/filtered/*.csv; do
  if [ -f "$f" ]; then
    lines=$(wc -l < "$f")
    size=$(du -h "$f" | cut -f1)
    echo "  $(basename "$f"): $lines lines ($size)"
  fi
done

for f in "$FATALITY_DIR"/*.csv "$FATALITY_DIR"/filtered/*.csv; do
  if [ -f "$f" ]; then
    lines=$(wc -l < "$f")
    size=$(du -h "$f" | cut -f1)
    echo "  $(basename "$f"): $lines lines ($size)"
  fi
done

echo ""

# Step 4: Import to database
echo "Step 4/4: Importing to HSE database..."
uv run python -m worldenergydata.modules.hse.importers.osha_importer \
  --data-dir "$DATA_DIR"

echo ""
echo "=== OSHA Data Refresh Complete ==="
