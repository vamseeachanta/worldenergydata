"""Parsers for Colorado ECMC production and wells sources (#745)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import shapefile

from worldenergydata.modules.state_regulators.colorado_ecmc.normalization import (
    clean_api10,
    clean_api12,
    clean_identifier,
    clean_int,
    clean_text,
    month_end,
    validate_columns,
)
from worldenergydata.modules.state_regulators.colorado_ecmc.schema import (
    OBSERVATION_COLUMNS,
    PRESSURE_COLUMN_SPECS,
    PRODUCTION_NUMERIC_COLUMNS,
    PRODUCTION_READ_COLUMNS,
    PRODUCTION_RENAME,
    PRODUCTION_REQUIRED_COLUMNS,
    WATER_PRESSURE_COLUMNS,
    WELL_OUTPUT_COLUMNS,
    WELLS_REQUIRED_COLUMNS,
)


def read_production_csv(path: str | Path, settings: dict) -> pd.DataFrame:
    """Read an ECMC Form 7 production CSV into normalized pressure rows."""
    source_path = Path(path)
    frame = pd.read_csv(source_path, usecols=_production_usecols, low_memory=False)
    validate_columns(frame, PRODUCTION_REQUIRED_COLUMNS, source_path.name, "production")
    frame = normalize_api_parts(frame)
    frame = frame.rename(columns=PRODUCTION_RENAME)
    for column in PRODUCTION_NUMERIC_COLUMNS:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in ["facility_id", "operator_number"]:
        if column in frame:
            frame[column] = frame[column].map(clean_identifier).astype("string")
    for column in ["well_name", "operator", "well_status", "formation_code"]:
        if column in frame:
            frame[column] = frame[column].map(clean_text).astype("string")
    frame["test_date"] = month_end(frame["report_year"], frame["report_month"])
    frame["source_name"] = settings.get("source_name", source_path.name)
    return frame


def normalize_api_parts(frame: pd.DataFrame) -> pd.DataFrame:
    """Build Colorado API10/API12 from production API parts."""
    result = frame.copy()
    county = result["ApiCountyCode"].map(lambda value: clean_int(value, 3))
    sequence = result["ApiSequenceNumber"].map(lambda value: clean_int(value, 5))
    sidetrack = result["ApiSidetrack"].map(lambda value: clean_int(value, 2))
    valid = county.notna() & sequence.notna() & sidetrack.notna()
    result["api10"] = pd.Series(pd.NA, index=result.index, dtype="string")
    result["api12"] = pd.Series(pd.NA, index=result.index, dtype="string")
    result.loc[valid, "api10"] = "05" + county[valid] + sequence[valid]
    result.loc[valid, "api12"] = result.loc[valid, "api10"] + sidetrack[valid]
    return result


def read_wells_shapefile(path: str | Path) -> pd.DataFrame:
    """Read the ECMC wells shapefile ZIP into API/depth/field join rows."""
    with _shapefile_reader(Path(path)) as reader:
        field_names = [field[0] for field in reader.fields[1:]]
        records = [
            dict(zip(field_names, record, strict=False)) for record in reader.records()
        ]
    frame = pd.DataFrame.from_records(records)
    validate_columns(frame, WELLS_REQUIRED_COLUMNS, Path(path).name, "wells")
    result = pd.DataFrame(
        {
            "api12": frame["API"].map(clean_api12).astype("string"),
            "api10": frame["API"].map(clean_api10).astype("string"),
            "api_label": frame["API_Label"].map(clean_text).astype("string"),
            "facility_id": frame["Facil_Id"].map(clean_identifier).astype("string"),
            "field": frame["Field_Name"].map(clean_text).astype("string"),
            "field_code": frame.get("Field_Code", pd.NA),
            "max_md_ft": pd.to_numeric(frame["Max_MD"], errors="coerce"),
            "max_tvd_ft": pd.to_numeric(frame["Max_TVD"], errors="coerce"),
            "latitude": pd.to_numeric(frame.get("Latitude"), errors="coerce"),
            "longitude": pd.to_numeric(frame.get("Longitude"), errors="coerce"),
        }
    )
    return result[WELL_OUTPUT_COLUMNS]


def build_pressure_observations(
    production: pd.DataFrame, wells: pd.DataFrame, settings: dict
) -> pd.DataFrame:
    """Build curated Colorado gas wellhead pressure observations."""
    joined = _join_production_wells(production, wells)
    candidates = []
    for source_column, (
        normalized_column,
        pressure_kind,
        priority,
    ) in PRESSURE_COLUMN_SPECS.items():
        pressure = pd.to_numeric(joined[normalized_column], errors="coerce")
        use = pressure.gt(0)
        if not use.any():
            continue
        candidates.append(
            _candidate_rows(
                joined[use].copy(),
                pressure[use],
                source_column,
                pressure_kind,
                priority,
                settings,
            )
        )
    observations = pd.concat(candidates, ignore_index=True) if candidates else _empty()
    if observations.empty:
        return observations
    observations = observations[observations["reference_depth_ft"].gt(0)].copy()
    observations = _filter_test_year_window(observations, settings)
    return _finalize_observations(observations)


def _finalize_observations(observations: pd.DataFrame) -> pd.DataFrame:
    observations = observations.sort_values(
        [
            "well_key",
            "test_date",
            "pressure_source_priority",
            "source_priority",
            "source_row_index",
        ]
    ).reset_index(drop=True)
    duplicate_keys = [
        "doc_num",
        "test_date",
        "well_key",
        "facility_id",
        "pressure_kind",
        "pressure_psig_reported",
    ]
    duplicates = observations.duplicated(duplicate_keys, keep="first")
    dropped_duplicate_count = int(duplicates.sum())
    observations = observations[~duplicates].copy()
    observations["is_earliest_observation"] = _earliest_flags(observations)
    observations["screen_observation_priority"] = (
        ~observations["is_earliest_observation"].astype(bool)
    ).astype(int)
    observations["is_earliest_observation"] = observations[
        "is_earliest_observation"
    ].astype(object)
    result = observations[OBSERVATION_COLUMNS].copy()
    result.attrs["dropped_duplicate_pressure_observation_count"] = (
        dropped_duplicate_count
    )
    return result


def build_quality_stats(
    production: pd.DataFrame,
    wells: pd.DataFrame,
    observations: pd.DataFrame,
    settings: dict | None = None,
) -> dict:
    joined = _join_production_wells(production, wells)
    gas_candidates = _positive_count(
        joined, [spec[0] for spec in PRESSURE_COLUMN_SPECS.values()]
    )
    water_candidates = _positive_count(joined, WATER_PRESSURE_COLUMNS)
    source_warnings = []
    if gas_candidates == 0 and water_candidates == 0 and len(production) > 0:
        source_warnings.append(
            "no_positive_pressure_values:GasPressureTubing,GasPressureCasing,"
            "WaterPressureTubing,WaterPressureCasing"
        )
    depth, _ = _select_reference_depth(joined)
    has_gas_pressure = _has_positive(
        joined, [spec[0] for spec in PRESSURE_COLUMN_SPECS.values()]
    )
    missing_depth = has_gas_pressure & ~depth.gt(0)
    test_year = pd.to_numeric(joined.get("report_year"), errors="coerce")
    min_year, max_year = _year_window(settings or {})
    in_window = test_year.between(min_year, max_year)
    return {
        "input_rows": int(len(production)),
        "joined_rows": int(len(joined)),
        "curated_count": int(len(observations)),
        "wells_with_pressure_observation": int(observations["well_key"].nunique()),
        "gas_pressure_candidate_count": int(gas_candidates),
        "water_pressure_candidate_count": int(water_candidates),
        "filtered_missing_depth_count": int(missing_depth.sum()),
        "filtered_out_of_window_test_year_count": int(
            (has_gas_pressure & depth.gt(0) & ~in_window).sum()
        ),
        "dropped_duplicate_pressure_observation_count": int(
            observations.attrs.get("dropped_duplicate_pressure_observation_count", 0)
        ),
        "test_year_window": [int(min_year), int(max_year)],
        "pressure_kind_counts": _counts(observations["pressure_kind"]),
        "reference_depth_source_counts": _counts(
            observations["reference_depth_source"]
        ),
        "test_year_range": _year_range(observations),
        "source_warnings": source_warnings,
    }


def _production_usecols(column: str) -> bool:
    return column in PRODUCTION_READ_COLUMNS


def _shapefile_reader(path: Path):
    if path.suffix.lower() != ".zip":
        return shapefile.Reader(str(path))
    with ZipFile(path) as archive:
        shp_name = _zip_member(archive, ".shp")
        shx_name = _zip_member(archive, ".shx")
        dbf_name = _zip_member(archive, ".dbf")
        return shapefile.Reader(
            shp=archive.open(shp_name),
            shx=archive.open(shx_name),
            dbf=archive.open(dbf_name),
        )


def _zip_member(archive: ZipFile, suffix: str) -> str:
    for name in archive.namelist():
        if name.lower().endswith(suffix):
            return name
    raise ValueError(f"ECMC wells shapefile ZIP missing {suffix} member")


def _join_production_wells(
    production: pd.DataFrame, wells: pd.DataFrame
) -> pd.DataFrame:
    frame = production.copy().reset_index(names="source_row_index")
    wells_unique = wells.drop_duplicates("api12")
    joined = frame.merge(
        wells_unique,
        on="api12",
        how="left",
        suffixes=("", "_well"),
        validate="many_to_one",
    )
    missing = (
        joined["field"].isna()
        if "field" in joined
        else pd.Series(True, index=joined.index)
    )
    if missing.any() and "facility_id" in joined and "facility_id" in wells:
        fallback = frame[missing].merge(
            wells.drop_duplicates("facility_id"),
            on="facility_id",
            how="left",
            suffixes=("", "_well"),
            validate="many_to_one",
        )
        for column in WELL_OUTPUT_COLUMNS:
            if column in joined and column in fallback:
                replacement = pd.Series(
                    fallback[column].to_numpy(),
                    index=joined.loc[missing].index,
                )
                joined.loc[missing, column] = joined.loc[missing, column].fillna(
                    replacement
                )
    return joined


def _candidate_rows(
    rows: pd.DataFrame,
    pressure_psig: pd.Series,
    source_column: str,
    pressure_kind: str,
    priority: int,
    settings: dict,
) -> pd.DataFrame:
    depth, depth_source = _select_reference_depth(rows)
    pressure_psia = pressure_psig + settings["atmospheric_psi"]
    return pd.DataFrame(
        {
            "state": "CO",
            "well_key": rows["api12"].to_numpy(),
            "api12": rows["api12"].to_numpy(),
            "api10": rows["api10"].to_numpy(),
            "doc_num": rows.get("doc_num", pd.NA).to_numpy(),
            "report_month": rows.get("report_month", pd.NA).to_numpy(),
            "facility_id": rows["facility_id"].to_numpy(),
            "well_name": _values(rows, "well_name"),
            "operator": _values(rows, "operator"),
            "operator_number": _values(rows, "operator_number"),
            "field": rows["field"].fillna(rows.get("formation_code")).to_numpy(),
            "formation_code": _values(rows, "formation_code"),
            "test_date": pd.to_datetime(rows["test_date"], errors="coerce"),
            "test_year": pd.to_numeric(rows["report_year"], errors="coerce").astype(
                "Int64"
            ),
            "test_type": settings["test_type"],
            "pressure_psig_reported": pressure_psig.to_numpy(),
            "pressure_psia": pressure_psia.to_numpy(),
            "pressure_kind": pressure_kind,
            "gas_mcf": _values(rows, "gas_mcf"),
            "days_produced": _values(rows, "days_produced"),
            "reference_depth_ft": depth.to_numpy(),
            "reference_depth_source": depth_source.to_numpy(),
            "gradient_psi_ft": (pressure_psia / depth).to_numpy(),
            "gradient_method": settings["gradient_method"],
            "latitude": _values(rows, "latitude"),
            "longitude": _values(rows, "longitude"),
            "pressure_source_column": source_column,
            "pressure_source_priority": priority,
            "source_priority": rows["source_name"].map(_source_priority).to_numpy(),
            "source_row_index": rows["source_row_index"].to_numpy(),
            "source_name": _values(rows, "source_name"),
        }
    )


def _select_reference_depth(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    tvd = pd.to_numeric(frame.get("max_tvd_ft"), errors="coerce")
    md = pd.to_numeric(frame.get("max_md_ft"), errors="coerce")
    depth = tvd.where(tvd.gt(0), md)
    source = pd.Series(pd.NA, index=frame.index, dtype="object")
    source.loc[tvd.gt(0)] = "Max_TVD"
    source.loc[~tvd.gt(0) & md.gt(0)] = "Max_MD"
    return depth, source


def _filter_test_year_window(frame: pd.DataFrame, settings: dict) -> pd.DataFrame:
    min_year, max_year = _year_window(settings)
    test_year = pd.to_numeric(frame["test_year"], errors="coerce")
    return frame[test_year.between(min_year, max_year)].copy()


def _earliest_flags(observations: pd.DataFrame) -> pd.Series:
    first_index = observations.groupby("well_key", sort=False).head(1).index
    flags = pd.Series(False, index=observations.index, dtype=object)
    flags.loc[first_index] = True
    return flags


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=OBSERVATION_COLUMNS)


def _positive_count(frame: pd.DataFrame, columns: list[str]) -> int:
    return int(
        sum(
            pd.to_numeric(frame[column], errors="coerce").gt(0).sum()
            for column in columns
        )
    )


def _has_positive(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    result = pd.Series(False, index=frame.index)
    for column in columns:
        result = result | pd.to_numeric(frame[column], errors="coerce").gt(0)
    return result


def _values(frame: pd.DataFrame, column: str) -> np.ndarray:
    if column not in frame:
        return np.full(len(frame), pd.NA, dtype=object)
    return frame[column].to_numpy()


def _source_priority(source_name: object) -> int:
    text = "" if pd.isna(source_name) else str(source_name)
    return 1 if "monthly" in text else 0


def _counts(series: pd.Series) -> dict:
    return {str(key): int(value) for key, value in series.value_counts().items()}


def _year_range(observations: pd.DataFrame) -> list[int] | None:
    if observations.empty:
        return None
    return [
        int(observations["test_year"].min()),
        int(observations["test_year"].max()),
    ]


def _year_window(settings: dict) -> tuple[int, int]:
    min_year = int(settings.get("min_test_year", 1900))
    if "max_test_year" in settings:
        max_year = int(settings["max_test_year"])
    else:
        max_year = datetime.now(timezone.utc).year + int(
            settings.get("max_future_years", 0)
        )
    return min_year, max_year
