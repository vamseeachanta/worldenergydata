#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=== BSEE HSE Data Refresh ==="
echo "Started: $(date -Iseconds)"
echo ""

echo "Step 1: Downloading BSEE incident and INC data..."
uv run python -m worldenergydata.hse.acquirers.bsee_acquirer \
  --output-dir data/modules/hse/raw/bsee --force --verify

echo ""
echo "Step 2: Importing incident investigations..."
uv run python -m worldenergydata.hse.importers.bsee_incinv_importer \
  --data-dir data/modules/hse/raw/bsee --summary

echo ""
echo "Step 3: Importing INCs..."
uv run python -m worldenergydata.hse.importers.bsee_incs_importer \
  --data-dir data/modules/hse/raw/bsee --summary

echo ""
echo "=== BSEE HSE refresh complete ==="
echo "Finished: $(date -Iseconds)"
