"""Well-level production loader with unit conversion.

ANP data comes in:
- Oil, condensate, water: Sm3/month
- Gas: Mm3/month (1 Mm3 = 1000 m3)

Output units:
- Oil, condensate, water: bbl (1 Sm3 = 6.2898 bbl)
- Gas: m3
- Daily rates: bbl/d (dividing by days in the month)
"""

import calendar
import logging
from typing import Optional

import pandas as pd

from worldenergydata.common.units import OilUnits

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
            return pd.DataFrame(
                columns=[
                    "field", "well", "date",
                    "oil_bbl", "condensate_bbl", "gas_m3", "water_bbl",
                    "oil_bbl_per_day",
                ]
            )

        df = raw_df.rename(columns=COLUMN_MAP).copy()
        df["date"] = pd.to_datetime(df["date"])

        df["oil_bbl"] = df["oleo_sm3"].apply(convert_sm3_to_bbl)
        df["condensate_bbl"] = df["condensado_sm3"].apply(convert_sm3_to_bbl)
        df["gas_m3"] = df["gas_mm3"].apply(convert_mm3_to_m3)
        df["water_bbl"] = df["agua_sm3"].apply(convert_sm3_to_bbl)

        df["oil_bbl_per_day"] = df.apply(
            lambda row: row["oil_bbl"] / _days_in_month(row["date"]),
            axis=1,
        )

        keep = [
            "field", "well", "date",
            "oil_bbl", "condensate_bbl", "gas_m3", "water_bbl",
            "oil_bbl_per_day",
        ]
        return df[keep].reset_index(drop=True)


def _days_in_month(dt: pd.Timestamp) -> int:
    return calendar.monthrange(dt.year, dt.month)[1]
