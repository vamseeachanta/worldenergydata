"""Parser for the KGS wells master zip."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from worldenergydata.kansas_kgs.raw_sources import load_kansas_counties

REQUIRED_COLUMNS = {
    "KID",
    "API_NUMBER",
    "API_NUM_NODASH",
    "FIELD",
    "LATITUDE",
    "LONGITUDE",
    "DEPTH",
    "FORMATION_AT_TOTAL_DEPTH",
    "PRODUCE_FORM",
    "SPUD",
    "COMPLETION",
    "PLUGGING",
    "MODIFIED",
}
DATE_COLUMNS = ("SPUD", "COMPLETION", "PLUGGING", "MODIFIED")
MONTHS = {
    "JAN": "01",
    "FEB": "02",
    "MAR": "03",
    "APR": "04",
    "MAY": "05",
    "JUN": "06",
    "JUL": "07",
    "AUG": "08",
    "SEP": "09",
    "OCT": "10",
    "NOV": "11",
    "DEC": "12",
}


def parse_wells_master(path: Path | str) -> pd.DataFrame:
    """Parse KGS `ks_wells.zip` into normalized well/depth rows."""
    with zipfile.ZipFile(path) as archive:
        member = _select_member(archive)
        with archive.open(member) as handle:
            frame = pd.read_csv(
                handle,
                dtype="string",
                encoding="latin-1",
                low_memory=False,
                usecols=lambda column: column in REQUIRED_COLUMNS,
            )
    _validate_required_columns(frame)
    return _normalize_wells(frame)


def _select_member(archive: zipfile.ZipFile) -> str:
    for name in archive.namelist():
        if name.endswith("ks_wells.txt"):
            return name
    raise ValueError("ks_wells.zip does not contain ks_wells.txt")


def _normalize_wells(frame: pd.DataFrame) -> pd.DataFrame:
    counties = load_kansas_counties()
    result = pd.DataFrame()
    result["well_kid"] = frame.get("KID", pd.Series(dtype="string")).astype("string")
    result["api10"] = frame.get("API_NUMBER", pd.Series(dtype="string")).map(_api10)
    result["api14"] = frame.get("API_NUM_NODASH", pd.Series(dtype="string")).astype(
        "string"
    )
    result["api_county_code"] = result["api10"].map(_county_code)
    result["county_name"] = result["api_county_code"].map(counties)
    result["field_name"] = frame.get("FIELD", pd.Series(dtype="string"))
    result["latitude"] = pd.to_numeric(frame.get("LATITUDE"), errors="coerce")
    result["longitude"] = pd.to_numeric(frame.get("LONGITUDE"), errors="coerce")
    result["reference_depth_ft"] = pd.to_numeric(frame.get("DEPTH"), errors="coerce")
    total_depth_formation = frame["FORMATION_AT_TOTAL_DEPTH"].replace("", pd.NA)
    produce_formation = frame["PRODUCE_FORM"].replace("", pd.NA)
    result["formation"] = total_depth_formation.fillna(produce_formation)
    date_failures = 0
    for source, target in (
        ("SPUD", "spud_date"),
        ("COMPLETION", "completion_date"),
        ("PLUGGING", "plugging_date"),
        ("MODIFIED", "modified_date"),
    ):
        result[target], failures = _date_column(frame, source)
        date_failures += failures
    result.attrs["quality"] = {
        "well_row_count": len(result),
        "wells_missing_api10_count": int(result["api10"].isna().sum()),
        "wells_missing_depth_count": int(result["reference_depth_ft"].isna().sum()),
        "wells_date_parse_failure_count": date_failures,
    }
    return result


def _validate_required_columns(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"ks_wells.txt missing required columns: {', '.join(missing)}")


def _api10(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    return "".join(str(value).split("-"))[:10]


def _county_code(api10: object) -> str | None:
    if api10 is None or pd.isna(api10):
        return None
    value = str(api10)
    return value[2:5] if len(value) >= 5 else None


def _date_column(frame: pd.DataFrame, column: str) -> tuple[pd.Series, int]:
    if column not in frame:
        return pd.Series(pd.NaT, index=frame.index), 0
    raw = frame[column].astype("string")
    normalized = raw.map(_oracle_date)
    parsed = pd.to_datetime(normalized, errors="coerce", format="%Y-%m-%d")
    populated = raw.notna() & raw.str.strip().ne("")
    failures = int((populated & parsed.isna()).sum())
    return parsed, failures


def _oracle_date(value: object) -> object:
    if value is None or pd.isna(value):
        return pd.NA
    parts = str(value).strip().upper().split("-")
    if len(parts) != 3 or parts[1] not in MONTHS:
        return str(value)
    return f"{parts[2]}-{MONTHS[parts[1]]}-{parts[0].zfill(2)}"
