"""Aggregate well-level records to field-level production."""

import logging
from typing import Dict

import pandas as pd

logger = logging.getLogger(__name__)


class FieldProductionAggregator:
    """Aggregate well records into field-month totals."""

    def aggregate(self, well_df: pd.DataFrame) -> pd.DataFrame:
        if well_df.empty:
            return pd.DataFrame(
                columns=[
                    "field",
                    "date",
                    "oil_bbl",
                    "condensate_bbl",
                    "gas_mcf",
                    "gas_m3",
                    "water_bbl",
                    "oil_bbl_per_day",
                    "well_count",
                    "water_cut",
                ]
            )

        numeric_cols = [
            "oil_bbl",
            "condensate_bbl",
            "gas_mcf",
            "gas_m3",
            "water_bbl",
            "oil_bbl_per_day",
        ]
        numeric_cols = [col for col in numeric_cols if col in well_df.columns]
        grouped = well_df.groupby(["field", "date"])

        agg = grouped[numeric_cols].sum().reset_index()
        agg["well_count"] = grouped["well"].nunique().values

        total_liquid = agg["oil_bbl"] + agg["water_bbl"]
        agg["water_cut"] = agg["water_bbl"] / total_liquid.where(total_liquid > 0, 1.0)

        return agg

    def get_field_summary(self, agg_df: pd.DataFrame, field_name: str) -> Dict:
        """Summarize observed field-month rows, including recorded zeros.

        Raises:
            ValueError: If no observations match ``field_name``, including when
                the aggregate is empty. Missing observations cannot establish
                zero production.
        """
        field_data = agg_df[agg_df["field"] == field_name]
        if field_data.empty:
            raise ValueError(f"No production records for field {field_name!r}")

        return {
            "total_oil_bbl": field_data["oil_bbl"].sum(),
            "avg_daily_rate": field_data["oil_bbl_per_day"].mean(),
            "max_water_cut": field_data["water_cut"].max(),
            "total_months": len(field_data),
            "peak_oil_bbl": field_data["oil_bbl"].max(),
        }
