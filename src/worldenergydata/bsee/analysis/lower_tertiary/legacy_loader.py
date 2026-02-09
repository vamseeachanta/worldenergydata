"""Load legacy production CSVs (wide format) for Lower Tertiary fields.

Legacy analysis produced CSV files in a wide format:
  - Column 1: ``PRODUCTION_DATETIME`` (monthly dates)
  - Remaining columns: API12 numbers as headers, production values as cells

This module melts that wide format into a tidy long format with columns
``date``, ``api12``, ``value`` suitable for downstream analysis and
Plotly visualizations.

Summary CSVs (prod_summary, well_summary) are already in long/tabular
format and are loaded as-is.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .config import LTConfig

logger = logging.getLogger(__name__)


class LegacyProductionLoader:
    """Load and transform legacy CSV production data.

    Parameters
    ----------
    config : LTConfig
        Loaded Lower Tertiary configuration (provides CSV file mappings).
    project_root : Path
        Project root directory used to resolve relative CSV paths from config.
    """

    def __init__(self, config: LTConfig, project_root: Path) -> None:
        self._config = config
        self._project_root = Path(project_root)
        self._csv_dir = self._project_root / config.data_paths["legacy_results_dir"]

    def available_fields(self) -> list[str]:
        """Return field keys that have legacy CSV data defined in config."""
        return list(self._config.data_paths.get("legacy_fields", {}).keys())

    # -- Wide-format loaders (rate, cumulative) ----------------------------

    def load_production_rate(self, field: str) -> pd.DataFrame:
        """Load production rate CSV and melt from wide to long format.

        Parameters
        ----------
        field : str
            Field key (e.g. ``"julia"``, ``"stmalo"``, ``"stones"``).

        Returns
        -------
        pd.DataFrame
            Columns: ``date`` (datetime64), ``api12`` (str), ``value`` (float).
            NaN rows are dropped.

        Raises
        ------
        KeyError
            If *field* is not in the legacy config.
        """
        paths = self._config.legacy_csv_paths(field, self._csv_dir)
        return self._load_wide_csv(paths["rate"])

    def load_cumulative(self, field: str) -> pd.DataFrame:
        """Load cumulative production CSV and melt from wide to long format.

        Parameters
        ----------
        field : str
            Field key (e.g. ``"julia"``).

        Returns
        -------
        pd.DataFrame
            Columns: ``date`` (datetime64), ``api12`` (str), ``value`` (float).
        """
        paths = self._config.legacy_csv_paths(field, self._csv_dir)
        return self._load_wide_csv(paths["cumulative"])

    # -- Tabular loaders (already long format) -----------------------------

    def load_production_summary(self, field: str) -> pd.DataFrame:
        """Load production summary CSV (already in tabular format).

        Returns a DataFrame with columns including ``API12``,
        ``O_CUMMULATIVE_PROD_MMBBL``, ``DAYS_ON_PROD``, etc.
        """
        paths = self._config.legacy_csv_paths(field, self._csv_dir)
        return pd.read_csv(paths["prod_summary"])

    def load_well_summary(self, field: str) -> pd.DataFrame:
        """Load well summary CSV (already in tabular format).

        Returns a DataFrame with columns including ``API12``,
        ``Water Depth (feet)``, ``Total Measured Depth``, etc.
        """
        paths = self._config.legacy_csv_paths(field, self._csv_dir)
        return pd.read_csv(paths["well_summary"])

    # -- Derived computations ----------------------------------------------

    def field_total_rate(self, field: str) -> pd.DataFrame:
        """Sum production rates across all wells for a single field.

        Parameters
        ----------
        field : str
            Field key (e.g. ``"julia"``).

        Returns
        -------
        pd.DataFrame
            Columns: ``date`` (datetime64), ``total_rate`` (float).
            Sorted by date with one row per month.
        """
        df = self.load_production_rate(field)
        if df.empty:
            return pd.DataFrame(columns=["date", "total_rate"])
        totals = df.groupby("date", as_index=False)["value"].sum()
        totals.columns = ["date", "total_rate"]
        return totals.sort_values("date").reset_index(drop=True)

    # -- Internal helpers --------------------------------------------------

    @staticmethod
    def _load_wide_csv(path: Path) -> pd.DataFrame:
        """Load a wide-format CSV and melt to long format.

        Wide format has ``PRODUCTION_DATETIME`` as the first column and
        API12 numbers as the remaining columns.  Values are production
        metrics (BOPD for rates, MMBBL for cumulative).

        Returns
        -------
        pd.DataFrame
            Tidy long format: ``date``, ``api12``, ``value``.
        """
        logger.debug("Loading wide CSV: %s", path)
        df = pd.read_csv(path)
        date_col = df.columns[0]
        api_cols = [c for c in df.columns if c != date_col]

        melted = df.melt(
            id_vars=[date_col],
            value_vars=api_cols,
            var_name="api12",
            value_name="value",
        )
        melted = melted.rename(columns={date_col: "date"})
        melted["date"] = pd.to_datetime(melted["date"], errors="coerce")
        melted = melted.dropna(subset=["value"])
        return melted.sort_values("date").reset_index(drop=True)
