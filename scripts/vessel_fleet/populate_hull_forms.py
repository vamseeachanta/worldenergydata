#!/usr/bin/env python3
"""Populate hull form types and estimate dimensions for all curated rigs.

Reads the curated drilling rig fleet, maps RIG_TYPE -> HULL_FORM_TYPE,
estimates missing dimensions from industry averages, and saves enriched output.

Usage:
    PYTHONPATH=src python3 scripts/vessel_fleet/populate_hull_forms.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from worldenergydata.vessel_hull_models.rig_hulls.hull_form_mapper import populate_hull_forms
from worldenergydata.vessel_hull_models.rig_hulls.hull_estimator import populate_estimated_dimensions

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

CURATED_DIR = Path(__file__).resolve().parents[2] / "data" / "modules" / "vessel_fleet" / "curated"
INPUT_FILE = CURATED_DIR / "drilling_rigs.parquet"
OUTPUT_PARQUET = CURATED_DIR / "drilling_rigs.parquet"
OUTPUT_CSV = CURATED_DIR / "drilling_rigs.csv"


def main() -> None:
    if not INPUT_FILE.exists():
        logger.error("Curated fleet not found: %s", INPUT_FILE)
        sys.exit(1)

    df = pd.read_parquet(INPUT_FILE)
    logger.info("Loaded %d rigs from curated fleet", len(df))

    # Phase 1: Map RIG_TYPE -> HULL_FORM_TYPE
    before_hull = df["HULL_FORM_TYPE"].notna().sum() if "HULL_FORM_TYPE" in df.columns else 0
    df = populate_hull_forms(df)
    after_hull = df["HULL_FORM_TYPE"].notna().sum()
    logger.info("Hull form: %d -> %d (added %d)", before_hull, after_hull, after_hull - before_hull)

    # Phase 2: Estimate missing dimensions
    before_loa = df["LOA_M"].notna().sum()
    df = populate_estimated_dimensions(df)
    after_loa = df["LOA_M"].notna().sum()
    logger.info("LOA_M: %d -> %d (estimated %d)", before_loa, after_loa, after_loa - before_loa)

    # Report
    logger.info("--- Hull Form Distribution ---")
    for form, count in df["HULL_FORM_TYPE"].value_counts(dropna=False).items():
        label = form if pd.notna(form) else "N/A (non-vessel)"
        logger.info("  %-15s %d", label, count)

    if "DIMENSION_CONFIDENCE" in df.columns:
        logger.info("--- Dimension Confidence ---")
        for conf, count in df["DIMENSION_CONFIDENCE"].value_counts(dropna=False).items():
            label = conf if pd.notna(conf) else "N/A"
            logger.info("  %-15s %d", label, count)

    # Save enriched output
    df.to_parquet(OUTPUT_PARQUET, index=False)
    df.to_csv(OUTPUT_CSV, index=False)
    logger.info("Saved enriched fleet: %s (%d rigs, %d columns)", OUTPUT_PARQUET.name, len(df), len(df.columns))


if __name__ == "__main__":
    main()
