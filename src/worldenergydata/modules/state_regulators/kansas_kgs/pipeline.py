"""Raw → normalized → curated pipeline for the Kansas KGS ingest (#725).

Outputs (all under the /mnt/ace storage contract, nothing in git):

- ``normalized/pressure/proration_pressures.parquet``
- ``normalized/wells/wells_master.parquet``
- ``curated/pressure/well_pressure_observations.parquet`` — the #709 schema
  shared with the Texas RRC extraction, so the under-pressured screen (#710)
  consumes both states through one table.
- ``curated/pressure/coverage_stats.json``
- ``raw/manifest.json``
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from worldenergydata.modules.state_regulators.kansas_kgs.parsers import (
    read_proration_pressures,
    read_wells_master,
)

OBSERVATION_COLUMNS = [
    "state",
    "well_key",
    "api_number",
    "api14",
    "lease",
    "operator",
    "field",
    "county_code",
    "test_year",
    "test_type",
    "pressure_psig_reported",
    "pressure_psia",
    "pressure_kind",
    "working_pressure_psig",
    "open_flow_mcfd",
    "adj_deliverability_mcfd",
    "reference_depth_ft",
    "gradient_psi_ft",
    "gradient_method",
    "formation_at_td",
    "produce_form",
    "is_earliest_observation",
    "source_file",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config(config_path: str | Path) -> dict:
    with Path(config_path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_manifest(config: dict, base_dir: Path) -> dict:
    raw_dir = base_dir / config["storage"]["raw_dir"]
    entries = {}
    for name, source in config["sources"].items():
        raw_path = raw_dir / source["raw_path"]
        entries[name] = {
            "source_url": source["url"],
            "raw_path": str(raw_path),
            "sha256": _sha256(raw_path),
            "size_bytes": raw_path.stat().st_size,
            "refresh": source["refresh"],
            "manifest_written_at": datetime.now(timezone.utc).isoformat(),
        }
    manifest_path = raw_dir / "manifest.json"
    manifest_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return entries


def build_pressure_observations(
    proration: pd.DataFrame, wells: pd.DataFrame, settings: dict
) -> pd.DataFrame:
    """Join annual proration tests to well depth and compute gradients.

    Join is on the KGS well key (proration WELL_KID → wells KID); API number
    is carried for cross-state joins but not used as the join key.
    """
    tested = proration[
        proration["SHUT_IN_PRESS"] > settings["min_pressure_psig"]
    ].copy()
    wells_slim = wells[
        [
            "KID",
            "API_NUM_NODASH",
            "FIELD",
            "DEPTH",
            "FORMATION_AT_TOTAL_DEPTH",
            "PRODUCE_FORM",
        ]
    ].drop_duplicates(subset="KID")
    merged = tested.merge(wells_slim, left_on="WELL_KID", right_on="KID", how="left")

    observations = pd.DataFrame(
        {
            "state": "KS",
            "well_key": merged["WELL_KID"],
            "api_number": merged["API_NUMBER"],
            "api14": merged["API_NUM_NODASH"],
            "lease": merged["LEASE"],
            "operator": merged["OPERATOR"],
            "field": merged["FIELD"],
            "county_code": merged["API_NUMBER"].str.slice(3, 6),
            "test_year": merged["YEAR"],
            "test_type": settings["test_type"],
            "pressure_psig_reported": merged["SHUT_IN_PRESS"],
            "pressure_psia": merged["SHUT_IN_PRESS"] + settings["atmospheric_psi"],
            "pressure_kind": settings["pressure_kind"],
            "working_pressure_psig": merged["WORKING_PRES"],
            "open_flow_mcfd": merged["OPEN_FLOW"],
            "adj_deliverability_mcfd": merged["ADJ_DELIVER"],
            "reference_depth_ft": merged["DEPTH"],
            "gradient_psi_ft": pd.NA,
            "gradient_method": pd.NA,
            "formation_at_td": merged["FORMATION_AT_TOTAL_DEPTH"],
            "produce_form": merged["PRODUCE_FORM"],
            "is_earliest_observation": False,
            "source_file": "kansas_proration_pressures.txt",
        }
    )

    has_depth = observations["reference_depth_ft"] > 0
    observations.loc[has_depth, "gradient_psi_ft"] = (
        observations.loc[has_depth, "pressure_psia"]
        / observations.loc[has_depth, "reference_depth_ft"]
    )
    observations.loc[has_depth, "gradient_method"] = settings["gradient_method"]
    observations["gradient_psi_ft"] = pd.to_numeric(
        observations["gradient_psi_ft"], errors="coerce"
    )

    earliest = observations.groupby("well_key")["test_year"].transform("min")
    observations["is_earliest_observation"] = observations["test_year"] == earliest
    return observations[OBSERVATION_COLUMNS]


def build_coverage_stats(
    proration: pd.DataFrame, observations: pd.DataFrame, wells_row_count: int
) -> dict:
    by_field = (
        observations.groupby(observations["field"].fillna("(no wells-master match)"))[
            "well_key"
        ]
        .nunique()
        .sort_values(ascending=False)
    )
    by_year = observations.groupby("test_year")["well_key"].nunique()
    earliest = observations[observations["is_earliest_observation"]]
    return {
        "proration_rows_total": int(len(proration)),
        "proration_rows_with_pressure": int(len(observations)),
        "wells_master_rows": int(wells_row_count),
        "wells_with_pressure_observation": int(observations["well_key"].nunique()),
        "wells_unmatched_in_wells_master": int(observations["api14"].isna().sum()),
        "observations_with_gradient": int(
            observations["gradient_psi_ft"].notna().sum()
        ),
        "test_year_range": [
            int(observations["test_year"].min()),
            int(observations["test_year"].max()),
        ],
        "wells_by_field_top20": {str(k): int(v) for k, v in by_field.head(20).items()},
        "wells_by_test_year": {str(k): int(v) for k, v in by_year.items()},
        "earliest_observation_gradient_quantiles_psi_ft": {
            q: round(float(earliest["gradient_psi_ft"].quantile(float(q))), 4)
            for q in ("0.1", "0.25", "0.5", "0.75", "0.9")
            if earliest["gradient_psi_ft"].notna().any()
        },
    }


def run_pipeline(config_path: str | Path) -> dict:
    config = load_config(config_path)
    storage = config["storage"]
    base_dir = Path(storage["base_dir"])
    raw_dir = base_dir / storage["raw_dir"]
    normalized_dir = base_dir / storage["normalized_dir"]
    curated_dir = base_dir / storage["curated_dir"]

    manifest = write_manifest(config, base_dir)

    proration = read_proration_pressures(
        raw_dir / config["sources"]["proration_pressures"]["raw_path"]
    )
    wells = read_wells_master(
        raw_dir / config["sources"]["wells_master"]["raw_path"],
        zip_member=config["sources"]["wells_master"]["zip_member"],
    )

    (normalized_dir / "pressure").mkdir(parents=True, exist_ok=True)
    (normalized_dir / "wells").mkdir(parents=True, exist_ok=True)
    proration.to_parquet(normalized_dir / "pressure" / "proration_pressures.parquet")
    wells.to_parquet(normalized_dir / "wells" / "wells_master.parquet")

    observations = build_pressure_observations(
        proration, wells, config["pressure_observations"]
    )
    stats = build_coverage_stats(proration, observations, len(wells))

    pressure_dir = curated_dir / "pressure"
    pressure_dir.mkdir(parents=True, exist_ok=True)
    observations.to_parquet(pressure_dir / "well_pressure_observations.parquet")
    (pressure_dir / "coverage_stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )
    return {"manifest": manifest, "coverage": stats}


def main() -> None:
    parser = argparse.ArgumentParser(description="Kansas KGS pressure ingest (#725)")
    parser.add_argument("--config", default="config/kansas_kgs.yml")
    args = parser.parse_args()
    result = run_pipeline(args.config)
    print(json.dumps(result["coverage"], indent=2))


if __name__ == "__main__":
    main()
