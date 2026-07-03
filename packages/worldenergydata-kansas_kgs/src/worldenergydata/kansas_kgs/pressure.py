"""Parser for KGS gas proration pressure observations."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from worldenergydata.kansas_kgs.raw_sources import load_kansas_counties

NORMALIZED_PRESSURE_COLUMNS = [
    "well_kid",
    "api10",
    "api_state_code",
    "api_county_code",
    "county_name",
    "test_year",
    "test_date",
    "test_type",
    "pressure_psig_raw",
    "working_pressure_psig",
    "daily_rate",
    "open_flow",
    "adj_deliver",
    "water_prod",
    "field_name",
    "source_file",
    "source_row_id",
]


@dataclass(frozen=True)
class ProrationPressureParseResult:
    """Normalized proration rows and parser quality counters."""

    normalized: pd.DataFrame
    quality: dict[str, int]


def parse_proration_pressure(path: Path | str) -> ProrationPressureParseResult:
    """Parse the KGS proration pressure text file."""
    pressure_path = Path(path)
    rows, bad_count = _read_valid_rows(pressure_path)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return ProrationPressureParseResult(
            pd.DataFrame(columns=NORMALIZED_PRESSURE_COLUMNS),
            {
                "bad_field_count_rows": bad_count,
                "pressure_row_count": 0,
                "nonpositive_pressure_rows": 0,
                "blank_pressure_rows": 0,
                "missing_test_year_rows": 0,
                "missing_county_name_rows": 0,
            },
        )
    normalized = _normalize_pressure_frame(frame, pressure_path.name)
    return ProrationPressureParseResult(
        normalized,
        {
            "bad_field_count_rows": bad_count,
            "pressure_row_count": len(normalized),
            "nonpositive_pressure_rows": int(
                normalized["pressure_psig_raw"].le(0).sum()
            ),
            "blank_pressure_rows": int(normalized["pressure_psig_raw"].isna().sum()),
            "missing_test_year_rows": int(normalized["test_year"].isna().sum()),
            "missing_county_name_rows": int(normalized["county_name"].isna().sum()),
        },
    )


def _read_valid_rows(path: Path) -> tuple[list[dict[str, str]], int]:
    with path.open(newline="", encoding="latin-1") as handle:
        reader = csv.reader(handle)
        header = [column.strip() for column in next(reader)]
        rows = []
        bad_count = 0
        for row in reader:
            if not row or len(row) != len(header):
                bad_count += 1
                continue
            rows.append(dict(zip(header, [value.strip() for value in row])))
    return rows, bad_count


def _normalize_pressure_frame(frame: pd.DataFrame, source_name: str) -> pd.DataFrame:
    counties = load_kansas_counties()
    result = frame.copy()
    result["well_kid"] = result["WELL_KID"].astype("string")
    result["api10"] = result["API_NUMBER"].map(_api10)
    result["api_state_code"] = result["API_NUMBER"].map(_api_part(0))
    result["api_county_code"] = result["API_NUMBER"].map(_api_part(1))
    result["county_name"] = result["api_county_code"].map(counties)
    result["test_year"] = pd.to_numeric(result["YEAR"], errors="coerce").astype("Int64")
    result["test_date"] = None
    result["test_type"] = "KS_PRORATION"
    result["pressure_psig_raw"] = _numeric(result, "SHUT_IN_PRESS")
    result["working_pressure_psig"] = _numeric(result, "WORKING_PRES")
    result["daily_rate"] = _numeric(result, "DAILY_RATE")
    result["open_flow"] = _numeric(result, "OPEN_FLOW")
    result["adj_deliver"] = _numeric(result, "ADJ_DELIVER")
    result["water_prod"] = _numeric(result, "WATER_PROD")
    result["field_name"] = pd.NA
    result["source_file"] = source_name
    result["source_row_id"] = range(1, len(result) + 1)
    return result


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame.get(column), errors="coerce")


def _api10(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    return "".join(str(value).split("-"))[:10]


def _api_part(index: int):
    def parse(value: object) -> str | None:
        if value is None or pd.isna(value):
            return None
        parts = str(value).split("-")
        return parts[index] if len(parts) > index else None

    return parse
