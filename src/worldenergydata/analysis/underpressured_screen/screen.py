"""Core screen: BHP estimate → gradient tiers → field ranking → validation gate.

Tier semantics (on the estimated-BHP gradient, psi/ft):

- ``normal``                     >= hydrostatic_normal_min (0.433 default)
- ``mildly_underpressured``      [mild_underpressure_min, hydrostatic_normal_min)
- ``severely_underpressured``    <  mild_underpressure_min
- ``near_vacuum`` flag           shut-in wellhead pressure below ~50 psia,
  the West Panhandle vacuum-operations regime.

The screen works on each well's earliest observation as the best available
virgin-pressure proxy, and carries the source ``era`` label (virgin/depleted)
so depleted-era programs are never silently presented as virgin pressure.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

TIER_NORMAL = "normal"
TIER_MILD = "mildly_underpressured"
TIER_SEVERE = "severely_underpressured"


def load_config(config_path: str | Path) -> dict:
    with Path(config_path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_observations(inputs: list[dict]) -> pd.DataFrame:
    frames = []
    for entry in inputs:
        frame = pd.read_parquet(entry["path"])
        frame["source_name"] = entry["name"]
        frame["era"] = entry["era"]
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def estimate_bhp(observations: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Add ``bhp_psia_est`` and ``bhp_gradient_psi_ft``.

    Wellhead shut-in readings get the average-temperature-and-z static
    gas-column correction; measured BHP values pass through unchanged.
    """
    frame = observations.copy()
    exponent = (
        0.01875
        * settings["gas_sg"]
        * frame["reference_depth_ft"]
        / (settings["z_avg"] * settings["t_avg_rankine"])
    )
    multiplier = np.exp(exponent)
    is_whp = frame["pressure_kind"] == "WHP_shut_in"
    frame["bhp_psia_est"] = frame["pressure_psia"].where(
        ~is_whp, frame["pressure_psia"] * multiplier
    )
    frame["bhp_method"] = np.where(is_whp, "static_gas_column_avg_zt", "as_reported")
    has_depth = frame["reference_depth_ft"] > 0
    frame["bhp_gradient_psi_ft"] = np.where(
        has_depth, frame["bhp_psia_est"] / frame["reference_depth_ft"], np.nan
    )
    return frame


def classify_tiers(frame: pd.DataFrame, tiers: dict) -> pd.DataFrame:
    frame = frame.copy()
    gradient = frame["bhp_gradient_psi_ft"]
    frame["pressure_tier"] = np.select(
        [
            gradient >= tiers["hydrostatic_normal_min"],
            gradient >= tiers["mild_underpressure_min"],
            gradient.notna(),
        ],
        [TIER_NORMAL, TIER_MILD, TIER_SEVERE],
        default=None,
    )
    frame["near_vacuum"] = (frame["pressure_kind"] == "WHP_shut_in") & (
        frame["pressure_psia"] < tiers["near_vacuum_whp_psia"]
    )
    return frame


def earliest_per_well(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per well: its earliest test with a usable gradient."""
    usable = frame[frame["bhp_gradient_psi_ft"].notna()].copy()
    usable = usable.sort_values(["well_key", "test_year"])
    return usable.groupby("well_key", as_index=False).first()


def rank_fields(wells: pd.DataFrame, settings: dict) -> pd.DataFrame:
    grouped = wells.groupby(wells["field"].fillna("(unmatched)"))
    ranking = grouped.agg(
        well_count=("well_key", "nunique"),
        median_gradient_psi_ft=("bhp_gradient_psi_ft", "median"),
        p10_gradient_psi_ft=("bhp_gradient_psi_ft", lambda s: s.quantile(0.1)),
        p90_gradient_psi_ft=("bhp_gradient_psi_ft", lambda s: s.quantile(0.9)),
        near_vacuum_wells=("near_vacuum", "sum"),
        earliest_test_year=("test_year", "min"),
        states=("state", lambda s: ",".join(sorted(s.unique()))),
        era=("era", lambda s: ",".join(sorted(s.unique()))),
    ).reset_index()
    ranking = ranking[ranking["well_count"] >= settings["min_wells_per_field"]]
    return ranking.sort_values("well_count", ascending=False).reset_index(drop=True)


def apply_field_tier(ranking: pd.DataFrame, tiers: dict) -> pd.DataFrame:
    ranking = ranking.copy()
    gradient = ranking["median_gradient_psi_ft"]
    ranking["field_tier"] = np.select(
        [
            gradient >= tiers["hydrostatic_normal_min"],
            gradient >= tiers["mild_underpressure_min"],
            gradient.notna(),
        ],
        [TIER_NORMAL, TIER_MILD, TIER_SEVERE],
        default=None,
    )
    return ranking


def run_validation_gate(ranking: pd.DataFrame, gate: dict) -> dict:
    """The screen must recover the known analogs in the top 10 by well count,
    classified at the required tier — otherwise the run fails loudly."""
    top10 = ranking.head(10)
    results = {}
    for field in gate["required_fields_in_top10"]:
        row = top10[top10["field"] == field]
        present = not row.empty
        tier_ok = present and row["field_tier"].iloc[0] == gate["required_tier"]
        results[field] = {"in_top10": present, "tier_ok": bool(tier_ok)}
    passed = all(r["in_top10"] and r["tier_ok"] for r in results.values())
    return {"passed": passed, "fields": results}


def run_screen(config_path: str | Path) -> dict:
    config = load_config(config_path)
    observations = load_observations(config["inputs"])
    enriched = classify_tiers(
        estimate_bhp(observations, config["bhp_estimate"]), config["tiers"]
    )
    wells = earliest_per_well(enriched)
    ranking = apply_field_tier(
        rank_fields(wells, config["field_ranking"]), config["tiers"]
    )
    gate = run_validation_gate(ranking, config["validation_gate"])

    tier_counts = wells["pressure_tier"].value_counts().to_dict()
    summary = {
        "wells_screened": int(len(wells)),
        "tier_counts": {k: int(v) for k, v in tier_counts.items()},
        "near_vacuum_wells": int(wells["near_vacuum"].sum()),
        "fields_ranked": int(len(ranking)),
        "median_gradient_psi_ft": round(
            float(wells["bhp_gradient_psi_ft"].median()), 4
        ),
        "validation_gate": gate,
        "era_note": sorted(wells["era"].unique().tolist()),
    }

    out_dir = Path(config["output"]["base_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    wells.to_parquet(out_dir / "well_screen_earliest.parquet")
    ranking.to_parquet(out_dir / "underpressured_field_ranking.parquet")
    (out_dir / "screen_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    if not gate["passed"]:
        raise RuntimeError(f"Validation gate failed: {gate['fields']}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Under-pressured screen (#710)")
    parser.add_argument("--config", default="config/underpressured_screen.yml")
    args = parser.parse_args()
    print(json.dumps(run_screen(args.config), indent=2))


if __name__ == "__main__":
    main()
