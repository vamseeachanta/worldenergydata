#!/bin/bash
# ABOUTME: Reproduce the public-input marine incident analysis without model calls.
set -euo pipefail

: "${MARINE_SAFETY_RAW_DIR:?Set MARINE_SAFETY_RAW_DIR to the external raw input archive}"
MANIFEST="${MARINE_SAFETY_MANIFEST:-config/marine_safety_input_manifest.json}"
OUTPUT_DIR="${MARINE_SAFETY_REPORT_DIR:-reports/marine_safety}"

# Validation is performed before any report is created or overwritten.
python3 scripts/marine_safety/generate_incident_report.py \
    --input-dir "$MARINE_SAFETY_RAW_DIR" \
    --manifest "$MANIFEST" \
    --output-dir "$OUTPUT_DIR" \
    --use-llm false
