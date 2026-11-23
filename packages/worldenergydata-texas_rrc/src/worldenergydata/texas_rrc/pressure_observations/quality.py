"""Quality and coverage summaries for Texas RRC pressure observations."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

DISTRICT_COVERAGE_COLUMNS = (
    "district",
    "test_decade",
    "pressure_observation_well_count",
    "pressure_observation_count",
)
FIELD_COVERAGE_COLUMNS = (
    "district",
    "field_no",
    "field_name",
    "test_decade",
    "pressure_observation_well_count",
    "pressure_observation_count",
)


@dataclass(frozen=True)
class PressureCoverage:
    """Coverage tables for pressure-observation availability."""

    by_district_decade: pd.DataFrame
    by_field_decade: pd.DataFrame


def build_pressure_coverage(observations: pd.DataFrame) -> PressureCoverage:
    """Return district/decade and field/decade pressure coverage summaries."""
    if observations.empty:
        return PressureCoverage(
            by_district_decade=pd.DataFrame(columns=DISTRICT_COVERAGE_COLUMNS),
            by_field_decade=pd.DataFrame(columns=FIELD_COVERAGE_COLUMNS),
        )

    frame = observations.copy()
    frame["test_decade"] = _test_decades(frame)
    frame = frame[frame["test_decade"].notna()].copy()
    if frame.empty:
        return PressureCoverage(
            by_district_decade=pd.DataFrame(columns=DISTRICT_COVERAGE_COLUMNS),
            by_field_decade=pd.DataFrame(columns=FIELD_COVERAGE_COLUMNS),
        )

    return PressureCoverage(
        by_district_decade=_coverage(
            frame,
            keys=("district", "test_decade"),
            columns=DISTRICT_COVERAGE_COLUMNS,
        ),
        by_field_decade=_coverage(
            frame,
            keys=("district", "field_no", "field_name", "test_decade"),
            columns=FIELD_COVERAGE_COLUMNS,
        ),
    )


def _coverage(
    frame: pd.DataFrame,
    keys: tuple[str, ...],
    columns: tuple[str, ...],
) -> pd.DataFrame:
    grouped = (
        frame.groupby(list(keys), dropna=False, sort=True)
        .agg(
            pressure_observation_well_count=("api14", "nunique"),
            pressure_observation_count=("api14", "size"),
        )
        .reset_index()
    )
    return grouped.loc[:, list(columns)]


def _test_decades(frame: pd.DataFrame) -> pd.Series:
    years = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    if "test_year" in frame:
        years = pd.to_numeric(frame["test_year"], errors="coerce").astype("Int64")
    if "test_date" in frame:
        date_years = pd.to_datetime(frame["test_date"], errors="coerce").dt.year
        years = years.fillna(date_years.astype("Int64"))
    decades = (years // 10) * 10
    return decades.map(lambda value: f"{int(value)}s" if pd.notna(value) else pd.NA)


__all__ = [
    "PressureCoverage",
    "build_pressure_coverage",
]
