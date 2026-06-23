"""UKCS well completions and well-test data loader.

Normalises NSTA well data into consistent column names and provides
field-level filtering and summary statistics.

Expected input columns (NSTA format):
  WellName, FieldName, CompletionDate, Status, WaterDepth_m, TestRate_bopd
"""

import logging
from typing import Dict

import pandas as pd

logger = logging.getLogger(__name__)

_RAW_WELL_COL = "WellName"
_RAW_FIELD_COL = "FieldName"
_RAW_DATE_COL = "CompletionDate"
_RAW_STATUS_COL = "Status"
_RAW_DEPTH_COL = "WaterDepth_m"
_RAW_RATE_COL = "TestRate_bopd"


class UKCSWellLoader:
    """Load and normalise UKCS well completion and test records."""

    def load(self, raw: pd.DataFrame) -> pd.DataFrame:
        """Convert raw NSTA well DataFrame to normalised records.

        Parameters
        ----------
        raw:
            DataFrame with NSTA well column names.

        Returns
        -------
        pd.DataFrame
            Normalised well data with columns:
            well_name, field, completion_date, status, water_depth_m,
            test_rate_bopd
        """
        if raw.empty:
            return pd.DataFrame(
                columns=[
                    "well_name",
                    "field",
                    "completion_date",
                    "status",
                    "water_depth_m",
                    "test_rate_bopd",
                ]
            )

        result = pd.DataFrame()
        result["well_name"] = raw[_RAW_WELL_COL].astype(str).str.strip()
        result["field"] = raw[_RAW_FIELD_COL].str.upper().str.strip()
        result["completion_date"] = raw[_RAW_DATE_COL].astype(str)
        result["status"] = raw[_RAW_STATUS_COL].str.upper().str.strip()
        result["water_depth_m"] = pd.to_numeric(raw[_RAW_DEPTH_COL], errors="coerce")
        result["test_rate_bopd"] = pd.to_numeric(
            raw[_RAW_RATE_COL], errors="coerce"
        ).fillna(0.0)

        return result.reset_index(drop=True)

    def filter_field(self, df: pd.DataFrame, field_name: str) -> pd.DataFrame:
        """Return wells for a specific field (case-insensitive)."""
        return df[df["field"] == field_name.upper().strip()].copy()

    def filter_status(self, df: pd.DataFrame, status: str) -> pd.DataFrame:
        """Return wells with a specific status (case-insensitive)."""
        return df[df["status"] == status.upper().strip()].copy()

    def field_summary(self, df: pd.DataFrame, field_name: str) -> Dict:
        """Return summary statistics for a named field.

        Parameters
        ----------
        df:
            Normalised well DataFrame from :meth:`load`.
        field_name:
            Field to summarise.

        Returns
        -------
        dict
            Keys: well_count, avg_test_rate_bopd, max_test_rate_bopd
        """
        field_data = self.filter_field(df, field_name)

        if field_data.empty:
            return {
                "well_count": 0,
                "avg_test_rate_bopd": 0.0,
                "max_test_rate_bopd": 0.0,
            }

        return {
            "well_count": len(field_data),
            "avg_test_rate_bopd": float(field_data["test_rate_bopd"].mean()),
            "max_test_rate_bopd": float(field_data["test_rate_bopd"].max()),
        }
