"""Candidate Form 5A pressure observations for Colorado ECMC (#751)."""

from __future__ import annotations

import pandas as pd

CANDIDATE_PRESSURE_KINDS = {
    "CASING_PRESS": "initial_test_casing_pressure_unverified",
    "TUBING_PRESS": "flowing_tubing_initial_test",
}
DEPTH_PRIORITY = (
    "interval_bottom_ft",
    "vertical_td_ft",
    "max_tvd_ft",
    "max_md_ft",
)
PRESSURE_PRIORITY = {"CASING_PRESS": 0, "TUBING_PRESS": 1}
CANDIDATE_COLUMNS = (
    "well_key",
    "state",
    "api10",
    "facility_id",
    "field",
    "test_date",
    "test_year",
    "test_type",
    "pressure_kind",
    "pressure_psig",
    "pressure_psia",
    "reference_depth_ft",
    "reference_depth_source",
    "source_name",
    "source_url",
    "raw_path",
    "source_discovery_sha256",
    "era",
    "screen_promotable",
    "underpressured_screen_eligible",
    "screen_observation_priority",
    "is_earliest_observation",
)


def build_form5a_pressure_candidates(
    classified: pd.DataFrame, config: dict
) -> tuple[pd.DataFrame, dict]:
    """Convert parsed Form 5A Initial Test Data rows into candidate observations."""
    atmospheric_psi = float(
        config.get("pressure_observations", {}).get("atmospheric_psi", 14.7)
    )
    candidates = classified[_candidate_pressure_mask(classified)].copy()
    rows, quality = [], _candidate_quality_template(candidates)
    for _, row in candidates.iterrows():
        field = _text(row.get("field"))
        depth, depth_source = _select_reference_depth(row)
        pressure_psig = _positive_number(row.get("measure_value"))
        if not field:
            quality["excluded_missing_field"] += 1
            continue
        if depth is None:
            quality["excluded_missing_depth"] += 1
            continue
        if pressure_psig is None:
            quality["excluded_missing_pressure"] += 1
            continue
        rows.append(
            _candidate_record(
                row, field, depth, depth_source, pressure_psig, atmospheric_psi
            )
        )
    result = pd.DataFrame(rows, columns=list(CANDIDATE_COLUMNS))
    if not result.empty:
        result = _add_candidate_priority(result)
    quality["usable_candidate_rows"] = int(len(result))
    quality["screen_promotable_rows"] = int(
        result.get("screen_promotable", pd.Series(dtype=bool)).sum()
    )
    return result, quality


def evaluate_screen_promotion(
    candidates: pd.DataFrame, quality: dict, config: dict
) -> dict:
    """Report whether Form 5A candidates are allowed into the screen."""
    promotable = int(quality.get("screen_promotable_rows", 0))
    configured = bool(config.get("configure_underpressured_screen")) and promotable > 0
    status = "configured_for_screen" if configured else "candidate_only"
    if promotable and not configured:
        status = "screen_ready_but_not_configured"
    return {
        "status": status,
        "candidate_rows": int(len(candidates)),
        "screen_promotable_rows": promotable,
        "configured_for_screen": configured,
    }


def _candidate_pressure_mask(frame: pd.DataFrame) -> pd.Series:
    pressure_role = frame.get("pressure_role", pd.Series("", index=frame.index))
    return (
        frame["source_section"].eq("initial_test_data")
        & frame["test_type"].isin(CANDIDATE_PRESSURE_KINDS)
        & pressure_role.eq("candidate_pressure_observation")
    )


def _candidate_quality_template(candidates: pd.DataFrame) -> dict:
    return {
        "candidate_pressure_rows": int(len(candidates)),
        "usable_candidate_rows": 0,
        "screen_promotable_rows": 0,
        "excluded_missing_field": 0,
        "excluded_missing_depth": 0,
        "excluded_missing_pressure": 0,
    }


def _candidate_record(
    row: pd.Series,
    field: str,
    depth: float,
    depth_source: str,
    pressure_psig: float,
    atmospheric_psi: float,
) -> dict:
    test_date = pd.to_datetime(row.get("test_date"), errors="coerce")
    facility_id = _text(row.get("facility_id"))
    api10 = _text(row.get("api10"))
    test_type = _text(row.get("test_type"))
    return {
        "well_key": _candidate_well_key(facility_id, api10),
        "state": "CO",
        "api10": api10,
        "facility_id": facility_id,
        "field": field,
        "test_date": test_date,
        "test_year": int(test_date.year) if not pd.isna(test_date) else pd.NA,
        "test_type": test_type,
        "pressure_kind": CANDIDATE_PRESSURE_KINDS[test_type],
        "pressure_psig": pressure_psig,
        "pressure_psia": pressure_psig + atmospheric_psi,
        "reference_depth_ft": depth,
        "reference_depth_source": depth_source,
        "source_name": "colorado_ecmc_form5a_facility_detail",
        "source_url": _text(row.get("source_url")),
        "raw_path": _text(row.get("raw_path")),
        "source_discovery_sha256": _text(row.get("sha256")),
        "era": "completion_initial_test",
        "screen_promotable": False,
        "underpressured_screen_eligible": False,
    }


def _candidate_well_key(facility_id: str, api10: str) -> str:
    if facility_id:
        return f"CO_ECMC_FACILITY:{facility_id}"
    return f"CO_ECMC_API10:{api10}"


def _select_reference_depth(row: pd.Series) -> tuple[float | None, str]:
    for column in DEPTH_PRIORITY:
        value = _positive_number(row.get(column))
        if value is not None:
            return value, column
    return None, ""


def _positive_number(value: object) -> float | None:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number) or float(number) <= 0:
        return None
    return float(number)


def _add_candidate_priority(candidates: pd.DataFrame) -> pd.DataFrame:
    result = candidates.copy()
    result["_pressure_priority"] = result["test_type"].map(PRESSURE_PRIORITY).fillna(99)
    result = result.sort_values(["well_key", "test_date", "_pressure_priority"])
    result["screen_observation_priority"] = result.groupby("well_key").cumcount()
    result["is_earliest_observation"] = result["screen_observation_priority"].eq(0)
    result = result.drop(columns=["_pressure_priority"]).reset_index(drop=True)
    for column in ["screen_promotable", "underpressured_screen_eligible"]:
        result[column] = result[column].astype(object)
    return result


def _text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()
