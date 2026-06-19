#!/usr/bin/env python3
"""Grow the curated construction-vessel database with off-repo sources.

Reads the existing committed ``construction_vessels.csv`` (the source of
truth for the 17 curated vessels), collects additional vessel particulars
from off-repo brochure-digitized sources (Frontier heavy-lift & pipelay
CSVs, ACMA MSIV markdown), deduplicates by IMO + normalized name, and
rewrites the curated CSV + Parquet.

Confidentiality: only public vessel particulars are read from the off-repo
sources. No cost / day-rate / recommendation / PII content is ingested, and
no raw client file is copied into the repository. Source directories are
resolved via environment variables:

    FRONTIER_VESSEL_FLEET_DIR   ->  Frontier heavy-lift + pipelay CSVs
    ACMA_MSIV_DIR               ->  ACMA MSIV markdown

Both default to no-op (empty collection + warning) when unset, so the script
and CI run without the off-repo share mounted.

Usage:
    uv run python scripts/vessel_fleet/ingest_offrepo_construction_vessels.py \
        [--data-dir <dir>] [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from worldenergydata.vessel_fleet.collectors.acma_msiv_collector import (
    collect_msiv_vessels,
)
from worldenergydata.vessel_fleet.collectors.frontier_csv_collector import (
    collect_frontier_vessels,
)
from worldenergydata.vessel_fleet.dedup.deduplicator import (
    deduplicate_fleet_with_report,
)
from worldenergydata.vessel_fleet.schemas.construction_vessel import (
    ConstructionVesselSchema,
)
from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_CURATED_REL = Path("curated") / "construction_vessels.csv"


def _load_curated_csv(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    """Load the existing curated CSV preserving column order."""
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        rows: list[dict[str, Any]] = []
        for raw in reader:
            row = {k: (v if v != "" else None) for k, v in raw.items()}
            rows.append(row)
    return fieldnames, rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grow curated construction vessels with off-repo sources",
    )
    parser.add_argument(
        "--data-dir",
        default=str(_PROJECT_ROOT / "data/modules/vessel_fleet"),
        help="Base vessel_fleet data directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report results without writing curated outputs",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    curated_csv = data_dir / _CURATED_REL
    if not curated_csv.is_file():
        logger.error("Curated CSV not found: %s", curated_csv)
        return 1

    fieldnames, existing = _load_curated_csv(curated_csv)
    logger.info("Loaded %d existing curated vessels", len(existing))

    frontier = collect_frontier_vessels()
    msiv = collect_msiv_vessels()
    logger.info(
        "Off-repo: %d Frontier + %d MSIV records", len(frontier), len(msiv)
    )

    all_records: list[dict[str, Any]] = existing + frontier + msiv
    deduped, conflicts = deduplicate_fleet_with_report(all_records)

    # Keep only construction-category vessels in the curated construction table.
    construction = [
        r for r in deduped if (r.get("VESSEL_CATEGORY") or "construction") == "construction"
    ]
    # Normalise the category label on any off-repo additions.
    for r in construction:
        r.setdefault("VESSEL_CATEGORY", "construction")

    # Validate + normalise types via the schema so the curated table has
    # consistent column dtypes (the committed CSV loads everything as strings;
    # off-repo collectors emit floats -- coerce both to the schema types).
    normalized: list[dict[str, Any]] = []
    failures = 0
    for rec in construction:
        payload = {k: v for k, v in rec.items() if v is not None}
        try:
            model = ConstructionVesselSchema(**payload)
        except Exception as exc:  # pragma: no cover - defensive
            failures += 1
            logger.warning(
                "Dropping invalid vessel %s: %s", rec.get("VESSEL_NAME"), exc
            )
            continue
        normalized.append(model.model_dump())
    if failures:
        logger.warning("Dropped %d records failing schema validation", failures)
    construction = normalized

    net_new = len(construction) - len(existing)
    logger.info(
        "Curated construction vessels: %d (existing %d, net-new %d)",
        len(construction),
        len(existing),
        net_new,
    )

    if conflicts:
        logger.warning("IMO conflicts reconciled (%d):", len(conflicts))
        for c in conflicts:
            logger.warning(
                "  %s: kept %s, discarded %s, sources=%s",
                c["VESSEL_NAME"],
                c["kept_imo"],
                c["discarded_imos"],
                c["sources"],
            )

    if args.dry_run:
        logger.info("--dry-run: not writing outputs")
        return 0

    # Preserve the original column order; append any new columns at the end.
    extra_cols: list[str] = []
    for rec in construction:
        for key in rec:
            if key not in fieldnames and key not in extra_cols:
                extra_cols.append(key)
    out_fields = fieldnames + extra_cols

    curated_dir = data_dir / "curated"
    store = ParquetStore(base_dir=curated_dir)
    # Reorder each record's keys to the canonical column order for stable output.
    ordered = [{k: rec.get(k) for k in out_fields} for rec in construction]
    store.save(ordered, "construction_vessels.parquet")
    store.export_csv("construction_vessels.parquet", "construction_vessels.csv")
    logger.info("Wrote curated construction_vessels.{csv,parquet}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
