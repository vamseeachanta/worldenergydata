"""Well-level ANP production loader with unit conversion.

The current official ANP production-by-well files report oil, condensate, and
water as daily bbl rates and gas as Brazilian ``Mm³/dia`` (thousand m3/day).
The loader converts these to monthly bbl and Mcf totals. It also retains the
legacy lowercase Sm3-style schema used by older tests/callers.
"""

import calendar
import logging

import pandas as pd

from worldenergydata.common.units import GasUnits, OilUnits

logger = logging.getLogger(__name__)

# Backward-compatible module-level alias (sourced from common.units)
SM3_TO_BBL = OilUnits.SM3_TO_BBL


def convert_sm3_to_bbl(sm3: float) -> float:
    return sm3 * SM3_TO_BBL


def convert_mm3_to_m3(mm3: float) -> float:
    return mm3 * 1000.0


COLUMN_MAP = {
    "campo": "field",
    "poco": "well",
    "data": "date",
}


class WellProductionLoader:
    """Load and normalise well-level ANP production data."""

    def load(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        if raw_df.empty:
            return _empty_well_frame()

        if "Período" in raw_df.columns and "Óleo (bbl/dia)" in raw_df.columns:
            return self._load_current_schema(raw_df)

        df = raw_df.rename(columns=COLUMN_MAP).copy()
        df["date"] = pd.to_datetime(df["date"])
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month

        df["oil_bbl"] = df["oleo_sm3"].apply(convert_sm3_to_bbl)
        df["condensate_bbl"] = df["condensado_sm3"].apply(convert_sm3_to_bbl)
        df["gas_m3"] = df["gas_mm3"].apply(convert_mm3_to_m3)
        df["gas_mcf"] = df["gas_m3"] * GasUnits.SM3_TO_SCF / 1000.0
        df["water_bbl"] = df["agua_sm3"].apply(convert_sm3_to_bbl)

        df["oil_bbl_per_day"] = df.apply(
            lambda row: row["oil_bbl"] / _days_in_month(row["date"]),
            axis=1,
        )

        keep = [
            "field",
            "well",
            "date",
            "year",
            "month",
            "oil_bbl",
            "condensate_bbl",
            "gas_m3",
            "gas_mcf",
            "water_bbl",
            "oil_bbl_per_day",
        ]
        return df[keep].reset_index(drop=True)

    def _load_current_schema(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        df = raw_df.copy()
        period = df["Período"].astype(str).str.replace("/", "-", regex=False)
        df["date"] = pd.to_datetime(period + "-01", errors="coerce")
        df = df[df["date"].notna()].copy()
        df["year"] = df["date"].dt.year.astype(int)
        df["month"] = df["date"].dt.month.astype(int)
        days = df["date"].apply(_days_in_month)

        oil_rate = df["Óleo (bbl/dia)"].apply(_parse_brazil_number)
        condensate_rate = df["Condensado (bbl/dia)"].apply(_parse_brazil_number)
        gas_rate = df[_gas_total_column(df)].apply(_parse_brazil_number)
        water_rate = df["Água (bbl/dia)"].apply(_parse_brazil_number)

        out = pd.DataFrame(
            {
                "field": df["Campo"].astype(str).str.strip(),
                "well": df["Nome Poço ANP"].astype(str).str.strip(),
                "date": df["date"],
                "year": df["year"],
                "month": df["month"],
                "oil_bbl": oil_rate * days,
                "condensate_bbl": condensate_rate * days,
                "gas_mcf": gas_rate * GasUnits.SM3_TO_SCF * days,
                "water_bbl": water_rate * days,
                "oil_bbl_per_day": oil_rate,
                "operator": _optional_text(df, "Operador"),
                "basin": _optional_text(df, "Bacia"),
                "environment": _optional_text(df, "Ambiente"),
                "location_source": _optional_text(df, "location_source"),
            }
        )
        return out.reset_index(drop=True)


def _days_in_month(dt: pd.Timestamp) -> int:
    return calendar.monthrange(dt.year, dt.month)[1]


def _empty_well_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "field",
            "well",
            "date",
            "year",
            "month",
            "oil_bbl",
            "condensate_bbl",
            "gas_m3",
            "gas_mcf",
            "water_bbl",
            "oil_bbl_per_day",
            "operator",
            "basin",
            "environment",
            "location_source",
        ]
    )


def _parse_brazil_number(value) -> float:
    if pd.isna(value):
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    return float(text.replace(".", "").replace(",", "."))


def _gas_total_column(df: pd.DataFrame) -> str:
    exact = "Gás Natural (Mm³/dia) Gás Total"
    if exact in df.columns:
        return exact
    candidates = [
        col
        for col in df.columns
        if "Gás Natural" in str(col) and "Gás Total" in str(col)
    ]
    if candidates:
        return candidates[0]
    fallback = "Gás Natural (Mm³/dia)"
    if fallback in df.columns:
        return fallback
    raise KeyError("ANP gas total column not found")


def _optional_text(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series([pd.NA] * len(df), index=df.index, dtype="object")
    return df[column].astype("object")
