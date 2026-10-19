"""Typed FieldReserves history, cumulative production and lease-to-field index.

Monthly production is distributed solely as Access; decoding is explicitly
unsupported rather than silently substituting lease production or fake rows.
"""

from __future__ import annotations

import hashlib
import io
import zipfile

import pandas as pd

from worldenergydata.bsee.fieldreserves_fetch import BASE

HISTORY_MEMBER = "2023 HIST/2023 OFFLDHIST.xlsx"
MASTER_MEMBER = "mastproddelimit.txt"
APPENDIX_MEMBER = "appendbdelimit.txt"
# BOEM, Field Definitions for FIELDLEASEAPENLEASE, undated, accessed 2026-10-19:
# https://www.data.boem.gov/Main/HtmlPage.aspx?page=appendixB
# Ordered aliases LEASE, FIELD, AREA, BLOCK, AR/BLK; identifiers, not quantities.
APPENDIX_COLUMNS = [
    "LEASE_NUMBER",
    "FIELD_NAME_CODE",
    "AREA_CODE",
    "BLOCK_NUMBER",
    "AREA_BLOCK",
]
MONTHLY_MEMBER = "2023 FldMoPro/2023 FldMoProd.accdb"
HISTORY_COLUMNS = {
    "FIELD": "FIELD_NAME_CODE",
    "YEAR": "YEAR",
    "DISCYR": "DISCOVERY_YEAR",
    "Orig Oil Reserves": "ORIGINAL_OIL_RESERVES",
    "Orig Gas Reserves": "ORIGINAL_GAS_RESERVES",
    "Orig BOE Reserves": "ORIGINAL_BOE",
    "CUMOIL": "CUMULATIVE_OIL",
    "CUMGAS": "CUMULATIVE_GAS",
    "CUMBOE": "CUMULATIVE_BOE",
    "Oil Reserves": "REMAINING_OIL_RESERVES",
    "Gas Reserves": "REMAINING_GAS_RESERVES",
    "BOE Reserves": "REMAINING_BOE",
    "FCLASS": "FIELD_CLASS",
}
MASTER_COLUMNS = [
    "FIELD_NAME_CODE",
    "LEASE_NUMBER",
    "OIL_STB",
    "CONDENSATE_STB",
    "CUMULATIVE_OIL_STB",
    "GAS_WELL_GAS_MCF",
    "CASINGHEAD_GAS_MCF",
    "CUMULATIVE_GAS_MCF",
    "WATER_SOURCE_UNITS",
    "FIRST_PRODUCTION_DATE",
]


def _member(archive: bytes, name: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        matches = [i for i in z.infolist() if i.filename == name]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one member: {name}")
        if matches[0].file_size > 80 * 1024 * 1024:
            raise ValueError("Uncompressed member exceeds size limit")
        return z.read(name)


def _cite(
    df: pd.DataFrame, archive: bytes, filename: str, member: str, retrieved_utc: str
) -> pd.DataFrame:
    df["SOURCE_URL"] = pd.Series(
        BASE + "/FieldReserves/Files/" + filename, index=df.index, dtype="string"
    )
    df["SOURCE_MEMBER"] = pd.Series(member, index=df.index, dtype="string")
    df["SOURCE_SHA256"] = pd.Series(
        hashlib.sha256(archive).hexdigest(), index=df.index, dtype="string"
    )
    df["RETRIEVED_UTC"] = pd.Series(retrieved_utc, index=df.index, dtype="string")
    return df


def _codes(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        df[column] = df[column].astype("string").str.strip()
        if df[column].isna().any() or df[column].eq("").any():
            raise ValueError(f"Missing identifier: {column}")
    return df


def load_history(archive: bytes, *, retrieved_utc: str) -> pd.DataFrame:
    raw = _member(archive, HISTORY_MEMBER)
    df = pd.read_excel(io.BytesIO(raw), sheet_name="2023 OFFLDHIST", dtype="string")
    missing = set(HISTORY_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"History schema missing columns: {sorted(missing)}")
    df = df[list(HISTORY_COLUMNS)].rename(columns=HISTORY_COLUMNS)
    df = _codes(df, ["FIELD_NAME_CODE", "FIELD_CLASS"])
    for column in set(df.columns) - {"FIELD_NAME_CODE", "FIELD_CLASS"}:
        dtype = "Int64" if column in {"YEAR", "DISCOVERY_YEAR"} else "Float64"
        df[column] = pd.to_numeric(df[column], errors="raise").astype(dtype)
    # The workbook headers do not state oil/gas units; no conversion is made.
    return _cite(df, archive, "2023%20Hist.zip", HISTORY_MEMBER, retrieved_utc)


def load_master(archive: bytes, *, retrieved_utc: str) -> pd.DataFrame:
    raw = _member(archive, MASTER_MEMBER)
    df = pd.read_csv(
        io.BytesIO(raw), header=None, dtype="string", keep_default_na=False
    )
    if len(df.columns) != 10:
        raise ValueError("Production master requires 10 columns")
    df.columns = MASTER_COLUMNS
    df = _codes(df, ["FIELD_NAME_CODE", "LEASE_NUMBER"])
    df["SOURCE_MARKERS"] = pd.Series("", index=df.index, dtype="string")
    for column in MASTER_COLUMNS[2:9]:
        values = df[column].str.strip()
        marker = values.eq("################")
        df.loc[marker, "SOURCE_MARKERS"] += column + "=################;"
        df[column] = pd.to_numeric(values.mask(marker), errors="raise").astype(
            "Float64"
        )
    df["SOURCE_MARKERS"] = df["SOURCE_MARKERS"].str.rstrip(";")
    df["FIRST_PRODUCTION_DATE"] = pd.to_datetime(
        df["FIRST_PRODUCTION_DATE"].str.strip(), format="%b-%Y", errors="raise"
    )
    return _cite(df, archive, "mastproddelimit.zip", MASTER_MEMBER, retrieved_utc)


def load_monthly(archive: bytes, *, retrieved_utc: str) -> pd.DataFrame:
    _member(archive, MONTHLY_MEMBER)
    raise NotImplementedError("Monthly production requires an Access database decoder")


def load_appendix(archive: bytes, *, retrieved_utc: str) -> pd.DataFrame:
    """Read all Appendix B relationships without inferring a unique lease map."""
    raw = _member(archive, APPENDIX_MEMBER)
    df = pd.read_csv(
        io.BytesIO(raw), header=None, dtype="string", keep_default_na=False
    )
    if len(df.columns) != len(APPENDIX_COLUMNS):
        raise ValueError("Appendix B columns differ from BOEM field definitions")
    df.columns = APPENDIX_COLUMNS
    df = _codes(df, APPENDIX_COLUMNS)
    return _cite(df, archive, "appendbdelimit.zip", APPENDIX_MEMBER, retrieved_utc)
