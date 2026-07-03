"""Build curated Texas RRC pressure observations from packet candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

ATMOSPHERIC_PRESSURE_PSI = 14.7
SURFACE_PRESSURE_FIELDS = {
    ("G-1 Field Data", "WELLHEAD_PRESS"),
    ("G-10", "SIWH_PRESSURE"),
}
BOTTOM_HOLE_PRESSURE_FIELDS = {
    ("G-1", "BOTTOM_HOLE_PRESS"),
}
W2_RECORD_TYPE = "W-2"

OUTPUT_COLUMNS = (
    "api14",
    "api10",
    "district",
    "field_no",
    "field_name",
    "test_date",
    "test_year",
    "source_record_type",
    "source_pressure_field",
    "pressure_raw_psi",
    "pressure_unit_basis",
    "pressure_psia",
    "atmospheric_pressure_psi",
    "pressure_kind",
    "pressure_method",
    "reference_depth_ft",
    "reference_depth_method",
    "gradient_psi_ft",
    "gradient_method",
    "source_file",
    "source_tracking_no",
    "source_packet_id",
    "source_form_id",
    "source_row_no",
    "source_row_id",
    "usable_for_virgin_pressure_proxy",
    "is_earliest_observation_for_well",
    "virgin_pressure_proxy_method",
    "quality_flags",
    "limitations",
)


@dataclass(frozen=True)
class PressureObservationResult:
    """Curated observations plus summary quality counters."""

    observations: pd.DataFrame
    quality: dict[str, int]


def build_pressure_observations(
    candidates: pd.DataFrame,
    wellbore: pd.DataFrame | None = None,
) -> PressureObservationResult:
    """Return curated pressure observations from normalized candidates."""
    rows = []
    quality = {
        "candidate_count": len(candidates),
        "curated_count": 0,
        "w2_pressure_candidates_not_curated": 0,
        "uncurated_pressure_candidates": 0,
        "missing_api": 0,
        "ambiguous_depth_reference": 0,
    }
    wellbore_index = _wellbore_index(wellbore)

    for _, candidate in candidates.iterrows():
        row = _candidate_observation(candidate, wellbore_index, quality)
        if row is not None:
            rows.append(row)

    observations = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if not observations.empty:
        observations = _mark_earliest_proxy(observations)
    quality["curated_count"] = len(observations)
    return PressureObservationResult(observations=observations, quality=quality)


def _candidate_observation(
    candidate: pd.Series,
    wellbore_index: dict[str, dict[str, Any]],
    quality: dict[str, int],
) -> dict[str, Any] | None:
    if not _valid_api14(candidate.get("api14")):
        quality["missing_api"] += 1
        return None
    classification = _classify_pressure(candidate)
    if classification is None:
        if str(candidate.get("source_record_type", "")) == W2_RECORD_TYPE:
            quality["w2_pressure_candidates_not_curated"] += 1
        else:
            quality["uncurated_pressure_candidates"] += 1
        return None
    if not _positive(candidate.get("pressure_raw_psi")):
        quality["uncurated_pressure_candidates"] += 1
        return None

    depth = _reference_depth(candidate, wellbore_index)
    flags = list(depth["quality_flags"])
    if "ambiguous_depth_reference" in flags:
        quality["ambiguous_depth_reference"] += 1
    gradient = _gradient(classification["pressure_psia"], depth["reference_depth_ft"])
    usable_proxy = _usable_for_proxy(candidate, depth, gradient)
    return _observation_row(
        candidate,
        classification,
        depth,
        gradient,
        usable_proxy,
        flags,
    )


def _usable_for_proxy(candidate: pd.Series, depth: dict[str, Any], gradient) -> bool:
    return bool(
        candidate.get("api14")
        and candidate.get("test_date")
        and _positive(depth["reference_depth_ft"])
        and gradient is not None
    )


def _classify_pressure(row: pd.Series) -> dict[str, Any] | None:
    key = (
        str(row.get("source_record_type", "")),
        str(row.get("source_pressure_field", "")),
    )
    raw_pressure = float(row["pressure_raw_psi"])
    if key in BOTTOM_HOLE_PRESSURE_FIELDS:
        return {
            "pressure_kind": "BHP_measured",
            "pressure_method": "source_reported_bottom_hole_pressure",
            "pressure_psia": raw_pressure,
            "pressure_unit_basis": "source_psi_unspecified",
            "atmospheric_pressure_psi": None,
            "limitations": "source-reported bottom-hole pressure; units carried as source psi",
        }
    if key in SURFACE_PRESSURE_FIELDS and _valid_surface_pressure_context(row, key):
        return {
            "pressure_kind": "WHP_shut_in",
            "pressure_method": "source_reported_shut_in_wellhead_pressure",
            "pressure_psia": raw_pressure + ATMOSPHERIC_PRESSURE_PSI,
            "pressure_unit_basis": "psig_assumed",
            "atmospheric_pressure_psi": ATMOSPHERIC_PRESSURE_PSI,
            "limitations": "screening conversion from assumed gauge pressure",
        }
    return None


def _valid_surface_pressure_context(row: pd.Series, key: tuple[str, str]) -> bool:
    if key == ("G-1 Field Data", "WELLHEAD_PRESS"):
        return str(row.get("source_row_no", "")).strip().upper() == "SHUT-IN"
    return True


def _reference_depth(
    candidate: pd.Series,
    wellbore_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    interval_depth = _interval_midpoint(candidate)
    if interval_depth is not None:
        return {
            "reference_depth_ft": interval_depth,
            "reference_depth_method": "production_interval_midpoint",
            "quality_flags": (),
        }

    for column, method in (
        ("bottom_hole_depth_ft", "bottom_hole_depth"),
        ("vertical_depth_ft", "vertical_depth"),
        ("measured_depth_ft", "measured_depth"),
        ("plug_back_depth_ft", "plug_back_depth"),
    ):
        value = _as_float(candidate.get(column))
        if _positive(value):
            return {
                "reference_depth_ft": value,
                "reference_depth_method": method,
                "quality_flags": (),
            }

    api14 = str(candidate.get("api14", ""))
    wellbore = wellbore_index.get(api14)
    if wellbore is None:
        return {
            "reference_depth_ft": None,
            "reference_depth_method": "",
            "quality_flags": (),
        }
    if wellbore.get("ambiguous"):
        return {
            "reference_depth_ft": None,
            "reference_depth_method": "",
            "quality_flags": ("ambiguous_depth_reference",),
        }
    return {
        "reference_depth_ft": wellbore.get("total_depth"),
        "reference_depth_method": "wellbore_total_depth",
        "quality_flags": (),
    }


def _wellbore_index(wellbore: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if wellbore is None or wellbore.empty or "api14" not in wellbore:
        return {}
    result: dict[str, dict[str, Any]] = {}
    for api14, group in wellbore.groupby("api14", dropna=True):
        depths = [
            _as_float(value)
            for value in group.get("total_depth", pd.Series(dtype=object)).tolist()
        ]
        depths = [value for value in depths if _positive(value)]
        result[str(api14)] = {
            "ambiguous": len(group) != 1,
            "total_depth": depths[0] if len(group) == 1 and depths else None,
        }
    return result


def _interval_midpoint(candidate: pd.Series) -> float | None:
    top = _as_float(candidate.get("production_interval_from_ft"))
    bottom = _as_float(candidate.get("production_interval_to_ft"))
    if _positive(top) and _positive(bottom) and bottom >= top:
        return (top + bottom) / 2.0
    return None


def _observation_row(
    candidate: pd.Series,
    classification: dict[str, Any],
    depth: dict[str, Any],
    gradient: float | None,
    usable_proxy: bool,
    flags: list[str],
) -> dict[str, Any]:
    row = {column: candidate.get(column, None) for column in OUTPUT_COLUMNS}
    row.update(classification)
    row.update(
        {
            "reference_depth_ft": depth["reference_depth_ft"],
            "reference_depth_method": depth["reference_depth_method"],
            "gradient_psi_ft": gradient,
            "gradient_method": _gradient_method(classification, gradient),
            "usable_for_virgin_pressure_proxy": usable_proxy,
            "is_earliest_observation_for_well": False,
            "virgin_pressure_proxy_method": "not_eligible",
            "quality_flags": "|".join(flags),
        }
    )
    return row


def _gradient_method(
    classification: dict[str, Any],
    gradient: float | None,
) -> str:
    if gradient is None:
        return ""
    if classification["pressure_kind"] == "BHP_measured":
        return "reported_bhp_over_reference_depth"
    return "surface_pressure_over_reference_depth_screening_only"


def _gradient(pressure: float, depth: Any) -> float | None:
    depth_value = _as_float(depth)
    if _positive(pressure) and _positive(depth_value):
        return pressure / depth_value
    return None


def _mark_earliest_proxy(observations: pd.DataFrame) -> pd.DataFrame:
    result = observations.copy()
    result["usable_for_virgin_pressure_proxy"] = result[
        "usable_for_virgin_pressure_proxy"
    ].astype(object)
    result["is_earliest_observation_for_well"] = result[
        "is_earliest_observation_for_well"
    ].astype(object)
    eligible_mask = result["usable_for_virgin_pressure_proxy"].map(
        lambda value: bool(value) if pd.notna(value) else False
    )
    eligible = result[eligible_mask].copy()
    if eligible.empty:
        return result
    sort_columns = ["api14", "test_date", "source_row_id"]
    eligible = eligible.sort_values(sort_columns)
    first_indices = eligible.groupby("api14", sort=True).head(1).index
    result.loc[first_indices, "is_earliest_observation_for_well"] = True
    result.loc[first_indices, "virgin_pressure_proxy_method"] = result.loc[
        first_indices, "pressure_kind"
    ].map(
        {
            "BHP_measured": "earliest_reported_bhp",
            "WHP_shut_in": "earliest_shut_in_whp_screening",
        }
    )
    return result


def _positive(value: Any) -> bool:
    number = _as_float(value)
    return number is not None and number > 0


def _valid_api14(value: Any) -> bool:
    text = str(value or "").strip()
    return len(text) == 14 and text.isdigit()


def _as_float(value: Any) -> float | None:
    if value is None or value != value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "PressureObservationResult",
    "build_pressure_observations",
]
