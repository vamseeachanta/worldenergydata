#!/usr/bin/env python3
"""Apply Noble rig-summary PDF specs to the vessel_fleet curated store (#987).

Reads the reviewed extraction SSOT
(``_data/raw/spec_pdfs/noble/extracted_specs.yaml``) and:

1. writes a raw parquet source (``_data/raw/spec_pdf_dimensions/noble.parquet``)
   so future fuse_and_deduplicate runs retain the vendor dimensions, and
2. updates curated ``drilling_rigs.parquet`` + re-exports ``drilling_rigs.csv``,
   matching each vessel and its former-name aliases case-insensitively and
   stamping ``DIMENSION_CONFIDENCE = "measured"`` (vendor spec sheet).

``--reparse`` re-extracts text-layer PDFs through parsers.rig_summary and
reports any drift against the YAML instead of applying (review loop; the YAML
stays the SSOT — image-only PDFs keep their manual transcriptions).

Usage:
    python scripts/vessel_fleet/ingest_noble_spec_pdfs.py [--reparse] [--data-dir <pkg _data dir>]
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_PROJECT_ROOT / "packages/worldenergydata-vessel_fleet/src"))

from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_DATA_DIR = (
    _PROJECT_ROOT
    / "packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/_data"
)

# Schema fields pushed into the curated table. RAW_* provenance keys stay in
# the YAML / raw parquet only.
_CURATED_FIELDS = (
    "YEAR_BUILT",
    "FLAG_STATE",
    "WATER_DEPTH_RATING_FT",
    "DRILLING_DEPTH_RATING_FT",
    "LOA_M",
    "BEAM_M",
    "DEPTH_M",
    "DRAFT_M",
    "MOONPOOL_LENGTH_M",
    "MOONPOOL_WIDTH_M",
    "VARIABLE_DECK_LOAD_ST",
    "HOOKLOAD_RATING_KIPS",
    "SETBACK_CAPACITY_KIPS",
)


def _match_key(name: str) -> str:
    """Normalize a vessel name for matching.

    BSEE WAR rows can carry former names as parentheticals, e.g.
    "NOBLE STANLEY LAFOSSE (FKA PACIFIC SHARAV)" — strip them.
    """
    name = re.sub(r"\((?:FKA|F\.K\.A\.?|EX\.?)[^)]*\)", "", name, flags=re.IGNORECASE)
    return " ".join(name.upper().split())


def load_extraction(data_dir: Path) -> dict:
    yaml_path = data_dir / "raw/spec_pdfs/noble/extracted_specs.yaml"
    with open(yaml_path) as fh:
        return yaml.safe_load(fh)


def load_manifest_urls(data_dir: Path) -> dict[str, str]:
    manifest_path = data_dir / "raw/spec_pdfs/noble/manifest.yaml"
    if not manifest_path.exists():
        return {}
    with open(manifest_path) as fh:
        manifest = yaml.safe_load(fh)
    return {name: meta["url"] for name, meta in manifest["files"].items()}


def write_raw_source(extraction: dict, data_dir: Path, urls: dict[str, str]) -> int:
    """Write vendor-spec records as a raw parquet source for the fuse pipeline."""
    records = []
    for vessel_name, entry in extraction["vessels"].items():
        record = {
            "VESSEL_NAME": vessel_name,
            "VESSEL_CATEGORY": "drilling_rig",
            "OWNER": "Noble Corporation plc",
            "RIG_TYPE": "drillship",
            "RIG_DESIGN": "Ship shaped, Samsung 96K",
            "DATA_SOURCE": "contractor_spec_pdf",
            "DATA_SOURCE_URL": urls.get(entry["pdf"]),
            "DIMENSION_CONFIDENCE": "measured",
            "IS_OFFSHORE": True,
        }
        for field in _CURATED_FIELDS:
            if field in entry["specs"]:
                record[field] = entry["specs"][field]
        records.append(record)

    store = ParquetStore(base_dir=data_dir / "raw/spec_pdf_dimensions")
    store.save(records, "noble.parquet")
    return len(records)


def apply_to_curated(extraction: dict, data_dir: Path, urls: dict[str, str]) -> int:
    """Update curated drilling_rigs rows (vessel + aliases) with vendor specs."""
    curated_dir = data_dir / "curated"
    store = ParquetStore(base_dir=curated_dir)
    records = store.load("drilling_rigs.parquet")
    if not records:
        logger.error("No curated drilling_rigs.parquet under %s", curated_dir)
        return 0

    by_name: dict[str, dict] = {}
    for vessel_name, entry in extraction["vessels"].items():
        for name in [vessel_name, *entry.get("aliases", [])]:
            by_name[_match_key(name)] = entry

    updated = 0
    for record in records:
        name = str(record.get("VESSEL_NAME") or record.get("RIG_NAME") or "")
        entry = by_name.get(_match_key(name))
        if entry is None:
            continue
        for field in _CURATED_FIELDS:
            if field in entry["specs"]:
                record[field] = entry["specs"][field]
        record["DIMENSION_CONFIDENCE"] = "measured"
        if not record.get("DATA_SOURCE_URL"):
            record["DATA_SOURCE_URL"] = urls.get(entry["pdf"])
        updated += 1
        logger.info(
            "Updated %s (moonpool %.1f x %.1f m)",
            record.get("VESSEL_NAME"),
            entry["specs"].get("MOONPOOL_LENGTH_M", float("nan")),
            entry["specs"].get("MOONPOOL_WIDTH_M", float("nan")),
        )

    store.save(records, "drilling_rigs.parquet")
    store.export_csv("drilling_rigs.parquet", "drilling_rigs.csv")
    return updated


def reparse_report(extraction: dict, data_dir: Path) -> int:
    """Re-extract text-layer PDFs and report drift vs the YAML SSOT."""
    from worldenergydata.vessel_fleet.parsers.pdf import extract_text_from_pdf
    from worldenergydata.vessel_fleet.parsers.rig_summary import (
        parse_rig_summary_text,
    )

    pdf_dir = data_dir / "raw/spec_pdfs/noble"
    drift = 0
    for vessel_name, entry in extraction["vessels"].items():
        if entry["extraction"] != "text_parse":
            logger.info("%s: image transcription — skipped", vessel_name)
            continue
        text = extract_text_from_pdf(str(pdf_dir / entry["pdf"]))
        parsed = parse_rig_summary_text(text)
        for field in _CURATED_FIELDS:
            expected = entry["specs"].get(field)
            got = parsed.get(field)
            if expected is not None and got != expected:
                logger.warning(
                    "%s.%s drift: yaml=%r parsed=%r", vessel_name, field, expected, got
                )
                drift += 1
    logger.info("Reparse complete: %d drifting fields", drift)
    return drift


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=str(_DEFAULT_DATA_DIR))
    parser.add_argument(
        "--reparse",
        action="store_true",
        help="re-extract text PDFs and report drift vs the YAML (no writes)",
    )
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    extraction = load_extraction(data_dir)

    if args.reparse:
        return 1 if reparse_report(extraction, data_dir) else 0

    urls = load_manifest_urls(data_dir)
    n_raw = write_raw_source(extraction, data_dir, urls)
    n_curated = apply_to_curated(extraction, data_dir, urls)
    logger.info("Wrote %d raw spec records; updated %d curated rows", n_raw, n_curated)
    return 0 if n_curated else 1


if __name__ == "__main__":
    sys.exit(main())
