"""Intermediate analysis layer for Lower Tertiary reports."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from .config import LTConfig
from .legacy_loader import LegacyProductionLoader
from .war_extractor import LTWarExtractor

logger = logging.getLogger(__name__)


class LTAnalyzer:
    """Aggregate and analyze data for the three LT reports.

    Reads article-derived metrics from config (YAML), live WAR data
    from the extractor, and legacy production CSVs from the loader.
    """

    def __init__(
        self,
        config: LTConfig,
        war: LTWarExtractor,
        legacy: LegacyProductionLoader,
    ) -> None:
        self._config = config
        self._war = war
        self._legacy = legacy

    # -- WAR-based analysis ----------------------------------------------------

    def war_summary_table(self) -> pd.DataFrame:
        """Build a summary table of WAR record counts by field.

        Returns DataFrame with columns: field, area, records, category
        (subsea/dry_tree), operator, first_oil.
        """
        rows: list[dict[str, Any]] = []
        for name, info in self._config.subsea_fields.items():
            df = self._war.extract_field(name)
            rows.append(
                {
                    "field": name,
                    "area": info["area"],
                    "records": len(df),
                    "category": "subsea",
                    "operator": info.get("operator", ""),
                    "first_oil": info.get("first_oil"),
                }
            )
        for name, info in self._config.dry_tree_fields.items():
            df = self._war.extract_field(name)
            rows.append(
                {
                    "field": name,
                    "area": info["area"],
                    "records": len(df),
                    "category": "dry_tree",
                    "operator": info.get("operator", ""),
                    "first_oil": info.get("first_oil"),
                }
            )
        return pd.DataFrame(rows)

    def drilling_activity_by_year(self) -> pd.DataFrame:
        """Delegate to WAR extractor."""
        return self._war.drilling_activity_by_year()

    def rig_utilization(self) -> pd.DataFrame:
        """Delegate to WAR extractor."""
        return self._war.rig_utilization()

    def subsea_vs_drytree_comparison(self) -> dict[str, Any]:
        """Compare subsea vs dry-tree WAR activity.

        Returns dict with:
        - subsea_records: int
        - dry_tree_records: int
        - subsea_fields: list of field names
        - dry_tree_fields: list of field names
        - activity_data: dict from WAR extractor
        """
        activity = self._war.subsea_vs_drytree_activity()
        return {
            "subsea_records": len(activity["subsea"]),
            "dry_tree_records": len(activity["dry_tree"]),
            "subsea_fields": list(self._config.subsea_fields.keys()),
            "dry_tree_fields": list(self._config.dry_tree_fields.keys()),
            "activity_data": activity,
        }

    # -- Legacy production analysis --------------------------------------------

    def production_comparison(self) -> dict[str, pd.DataFrame]:
        """Load production rate curves for all available legacy fields.

        Returns dict mapping field name to total rate DataFrame
        (date, total_rate).
        """
        result: dict[str, pd.DataFrame] = {}
        for field in self._legacy.available_fields():
            df = self._legacy.field_total_rate(field)
            if not df.empty:
                result[field] = df
        return result

    def cumulative_comparison(self) -> dict[str, pd.DataFrame]:
        """Load cumulative production curves for all available legacy fields.

        Returns dict mapping field name to melted cumulative DataFrame.
        """
        result: dict[str, pd.DataFrame] = {}
        for field in self._legacy.available_fields():
            df = self._legacy.load_cumulative(field)
            if not df.empty:
                totals = df.groupby("date")["value"].sum().reset_index()
                totals.columns = ["date", "cumulative_mmbbl"]
                result[field] = totals
        return result

    def well_inventory(self) -> dict[str, pd.DataFrame]:
        """Load well and production summaries for all legacy fields.

        Returns dict mapping field name to merged summary DataFrame.
        """
        result: dict[str, pd.DataFrame] = {}
        for field in self._legacy.available_fields():
            prod_summ = self._legacy.load_production_summary(field)
            if not prod_summ.empty:
                result[field] = prod_summ
        return result

    # -- Article-derived metrics (pass-through from YAML) ----------------------

    @property
    def aggregate_metrics(self) -> dict:
        """Return the aggregate article metrics."""
        return self._config.article_metrics["aggregate"]

    @property
    def recovery_factors(self) -> dict:
        """Return recovery factor comparisons."""
        return self._config.article_metrics["recovery_factors"]

    @property
    def economics(self) -> dict:
        """Return economics data."""
        return self._config.article_metrics["economics"]

    @property
    def julia_deep_dive(self) -> dict:
        """Return Julia deep-dive data."""
        return self._config.article_metrics["julia_deep_dive"]

    @property
    def validation_table(self) -> list[dict]:
        """Return validation table fields."""
        return self._config.article_metrics["validation_table"]["fields"]

    @property
    def architecture_data(self) -> dict:
        """Return architecture comparison data."""
        return self._config.architecture

    @property
    def source_attribution(self) -> str:
        """Return source attribution string."""
        return self._config.article_metrics["source_attribution"]

    def report_title(self, report_key: str) -> str:
        """Return the configured report title for *report_key*.

        Parameters
        ----------
        report_key : str
            One of ``"part1"``, ``"part2"``, or ``"executive"``.

        Raises
        ------
        KeyError
            If *report_key* is not defined in the output config.
        """
        return self._config.output_config["reports"][report_key]["title"]
