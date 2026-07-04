"""Build curated Kansas KGS pressure observations."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

ATMOSPHERIC_PRESSURE_PSI = 14.7
HUGOTON_PANOMA_COUNTIES = {
    "Finney",
    "Grant",
    "Gray",
    "Hamilton",
    "Haskell",
    "Kearny",
    "Morton",
    "Seward",
    "Stanton",
    "Stevens",
}
OBSERVATION_COLUMNS = [
    "api14",
    "api10",
    "api_state_code",
    "api_county_code",
    "county_name",
    "state",
    "source_agency",
    "field_name",
    "test_date",
    "test_year",
    "test_type",
    "pressure_psig_raw",
    "pressure_psia",
    "atmospheric_pressure_psi",
    "pressure_kind",
    "reference_depth_ft",
    "reference_depth_method",
    "gradient_psi_ft",
    "gradient_method",
    "formation",
    "is_earliest_observation_for_well",
    "virgin_pressure_proxy_method",
    "source_file",
    "source_row_id",
    "quality_flags",
    "limitations",
]
_INTERNAL_OBSERVATION_COLUMNS = [*OBSERVATION_COLUMNS, "_identity_key"]


@dataclass(frozen=True)
class PressureObservationResult:
    """Curated observations, coverage summary, and quality payload."""

    observations: pd.DataFrame
    coverage: pd.DataFrame
    quality: dict[str, object]


def build_pressure_observations(
    proration: pd.DataFrame,
    wells: pd.DataFrame,
) -> PressureObservationResult:
    """Build curated observations from normalized pressure and well rows."""
    pressure = pd.to_numeric(
        proration.get(
            "pressure_psig_raw",
            pd.Series(pd.NA, index=proration.index, dtype=object),
        ),
        errors="coerce",
    )
    positive = proration[pressure.gt(0)].copy()
    well_lookup = _well_lookup(wells)
    observations = pd.DataFrame(
        [_observation(row, well_lookup) for _, row in positive.iterrows()],
        columns=_INTERNAL_OBSERVATION_COLUMNS,
    )
    if not observations.empty:
        observations = _mark_earliest(observations)
    else:
        observations = observations.drop(columns=["_identity_key"])
    coverage = _coverage(observations)
    quality = _quality(observations)
    return PressureObservationResult(observations, coverage, quality)


def _observation(
    row: pd.Series,
    well_lookup: dict[str, list[pd.Series]],
) -> dict[str, object]:
    match, flags = _well_match(row, well_lookup)
    pressure_psia = round(float(row["pressure_psig_raw"]) + ATMOSPHERIC_PRESSURE_PSI, 6)
    depth = _depth(match)
    gradient = round(pressure_psia / depth, 6) if depth and depth > 0 else pd.NA
    county_name = _county_name(row, match)
    test_year = _test_year(row)
    flags.extend(_depth_flags(match, depth))
    if pd.isna(county_name):
        flags.append("missing_county_name")
    if pd.isna(test_year):
        flags.append("missing_test_year")
    return {
        "api14": _value(match, "api14"),
        "api10": row.get("api10"),
        "api_state_code": row.get("api_state_code"),
        "api_county_code": row.get("api_county_code"),
        "county_name": county_name,
        "state": "KS",
        "source_agency": "Kansas Geological Survey",
        "field_name": _field_name(row, match),
        "test_date": row.get("test_date"),
        "test_year": test_year,
        "test_type": "KS_PRORATION",
        "pressure_psig_raw": float(row["pressure_psig_raw"]),
        "pressure_psia": pressure_psia,
        "atmospheric_pressure_psi": ATMOSPHERIC_PRESSURE_PSI,
        "pressure_kind": "WHP_shut_in",
        "reference_depth_ft": depth if depth and depth > 0 else pd.NA,
        "reference_depth_method": "total_depth_ft" if depth and depth > 0 else pd.NA,
        "gradient_psi_ft": gradient,
        "gradient_method": "whp_over_total_depth_screening_only",
        "formation": _value(match, "formation"),
        "is_earliest_observation_for_well": False,
        "virgin_pressure_proxy_method": pd.NA,
        "source_file": row.get("source_file"),
        "source_row_id": row.get("source_row_id"),
        "quality_flags": "|".join(flags),
        "limitations": _limitations(),
        "_identity_key": _identity_key(match, row, flags),
    }


def _well_lookup(wells: pd.DataFrame) -> dict[str, list[pd.Series]]:
    lookup: dict[str, list[pd.Series]] = {}
    if wells.empty or "api10" not in wells:
        return lookup
    for _, row in wells.iterrows():
        api10 = row.get("api10")
        if pd.isna(api10):
            continue
        lookup.setdefault(str(api10), []).append(row)
    return lookup


def _well_match(
    row: pd.Series,
    well_lookup: dict[str, list[pd.Series]],
) -> tuple[pd.Series | None, list[str]]:
    candidates = well_lookup.get(str(row.get("api10")), [])
    if not candidates:
        return None, ["missing_well_join", "missing_depth"]
    if len(candidates) == 1:
        return candidates[0], []
    kid_matches = [
        candidate
        for candidate in candidates
        if str(candidate.get("well_kid")) == str(row.get("well_kid"))
    ]
    if len(kid_matches) == 1:
        return kid_matches[0], ["kid_fallback_join"]
    return None, ["ambiguous_api10_join", "ambiguous_identity_for_virgin_proxy"]


def _mark_earliest(observations: pd.DataFrame) -> pd.DataFrame:
    result = observations.copy()
    result["is_earliest_observation_for_well"] = result[
        "is_earliest_observation_for_well"
    ].astype(object)
    eligible = result.dropna(subset=["_identity_key", "test_year"])
    for identity, group in eligible.groupby("_identity_key"):
        ordered = group.sort_values(["test_year", "source_row_id"])
        earliest = ordered.index[0]
        result.loc[earliest, "is_earliest_observation_for_well"] = True
        result.loc[earliest, "virgin_pressure_proxy_method"] = (
            "earliest_available_proration_year"
        )
    ambiguous = result["_identity_key"].isna()
    result.loc[ambiguous, "is_earliest_observation_for_well"] = None
    return result.drop(columns=["_identity_key"]).astype(
        {"is_earliest_observation_for_well": object}
    )


def _coverage(observations: pd.DataFrame) -> pd.DataFrame:
    if observations.empty:
        return pd.DataFrame(columns=["county_name", "test_year", "observation_count"])
    return (
        observations.groupby(["county_name", "test_year"], dropna=False)
        .size()
        .reset_index(name="observation_count")
        .sort_values(["observation_count", "county_name"], ascending=[False, True])
    )


def _quality(observations: pd.DataFrame) -> dict[str, object]:
    years = pd.to_numeric(
        observations.get("test_year", pd.Series(dtype=object)), errors="coerce"
    )
    county_names = observations.get("county_name", pd.Series(dtype=object))
    return {
        "row_count": int(len(observations)),
        "observation_year_min": int(years.min()) if years.notna().any() else None,
        "observation_year_max": int(years.max()) if years.notna().any() else None,
        "hugoton_panoma_county_observation_count": int(
            county_names.isin(HUGOTON_PANOMA_COUNTIES).sum()
        ),
        "missing_well_join_count": _flag_count(observations, "missing_well_join"),
        "ambiguous_api10_join_count": _flag_count(observations, "ambiguous_api10_join"),
        "ambiguous_identity_for_virgin_proxy_count": _flag_count(
            observations, "ambiguous_identity_for_virgin_proxy"
        ),
        "missing_depth_count": _flag_count(observations, "missing_depth"),
        "missing_county_name_count": _flag_count(observations, "missing_county_name"),
        "missing_test_year_count": _flag_count(observations, "missing_test_year"),
    }


def _depth(match: pd.Series | None) -> float | None:
    if match is None:
        return None
    value = pd.to_numeric(
        pd.Series([match.get("reference_depth_ft")]), errors="coerce"
    ).iloc[0]
    return float(value) if pd.notna(value) else None


def _value(match: pd.Series | None, column: str) -> object:
    if match is None:
        return pd.NA
    value = match.get(column, pd.NA)
    return value if pd.notna(value) else pd.NA


def _field_name(row: pd.Series, match: pd.Series | None) -> object:
    return (
        row.get("field_name")
        if pd.notna(row.get("field_name"))
        else _value(match, "field_name")
    )


def _county_name(row: pd.Series, match: pd.Series | None) -> object:
    county_name = row.get("county_name")
    return county_name if pd.notna(county_name) else _value(match, "county_name")


def _test_year(row: pd.Series) -> object:
    year = row.get("test_year")
    return int(year) if pd.notna(year) else pd.NA


def _flag_count(observations: pd.DataFrame, flag: str) -> int:
    if observations.empty or "quality_flags" not in observations:
        return 0
    flags = observations["quality_flags"].fillna("").astype(str)
    return int(flags.str.split("|").map(lambda values: flag in values).sum())


def _identity_key(match: pd.Series | None, row: pd.Series, flags: list[str]) -> object:
    if "ambiguous_identity_for_virgin_proxy" in flags:
        return pd.NA
    api14 = _value(match, "api14")
    if pd.notna(api14):
        return str(api14)
    kid = row.get("well_kid")
    return str(kid) if pd.notna(kid) else pd.NA


def _depth_flags(match: pd.Series | None, depth: float | None) -> list[str]:
    if match is None:
        return []
    return [] if depth and depth > 0 else ["missing_depth"]


def _limitations() -> str:
    return "|".join(
        [
            "psig_to_psia_assumption",
            "sea_level_atmospheric_pressure",
            "elevation_not_adjusted",
            "whp_over_total_depth_screening_only",
            "not_initial_reservoir_pressure",
        ]
    )
