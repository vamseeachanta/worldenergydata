"""Transform analysis results into ranked business insights (WRK-116 Phase 4).

Pure programmatic pattern detection -- no LLM or external API calls.
Takes the dict produced by ``ComprehensiveActivityAnalyzer.analyze()`` and
returns 5 categories of human-readable insight sentences.
"""

from __future__ import annotations

import pandas as pd


class InsightGenerator:
    """Transform analysis results into ranked business insights."""

    def __init__(self, analysis_results: dict) -> None:
        self._results = analysis_results

    def generate(self) -> dict:
        """Produce insights across 5 categories.

        Returns dict with keys: key_findings, market_trends,
        competitive_intelligence, opportunity_areas, risk_factors.
        Each value is a list[str] of human-readable sentences.
        """
        return {
            "key_findings": self._key_findings(),
            "market_trends": self._market_trends(),
            "competitive_intelligence": self._competitive_intelligence(),
            "opportunity_areas": self._opportunity_areas(),
            "risk_factors": self._risk_factors(),
        }

    # -- Private helpers -------------------------------------------------------

    def _key_findings(self) -> list[str]:
        findings: list[str] = []

        # 1. Drilling vs intervention dominance
        ca = self._results.get("cross_activity", {})
        d_count = ca.get("drilling_count", 0)
        i_count = ca.get("intervention_count", 0)
        ratio = ca.get("ratio", 0.0)
        if d_count + i_count > 0:
            dominant = "Drilling" if d_count >= i_count else "Intervention"
            findings.append(
                f"{dominant} dominates activity with a drilling-to-intervention"
                f" ratio of {ratio:.1f} ({d_count} drilling vs {i_count}"
                f" intervention records)."
            )

        # 2. Mean drilling duration
        de = self._results.get("drilling_efficiency", {})
        mean_days = de.get("mean_drilling_days", 0.0)
        total_wells = de.get("total_wells_with_duration", 0)
        if total_wells > 0:
            findings.append(
                f"Mean drilling duration is {mean_days:.1f} days across"
                f" {total_wells} wells."
            )

        # 3. Most active operator
        op = self._results.get("operator_portfolio", {})
        top_ops = op.get("top_operators", pd.DataFrame())
        if isinstance(top_ops, pd.DataFrame) and not top_ops.empty:
            row = top_ops.iloc[0]
            findings.append(
                f"{row['BUS_ASC_NAME']} is the most active operator with"
                f" {int(row['activity_count'])} activities across"
                f" {int(row['unique_wells'])} wells."
            )

        # 4. Deepest well
        wd = self._results.get("well_depth", {})
        max_md = wd.get("max_total_md", 0.0)
        if max_md > 0:
            findings.append(
                f"Deepest well reaches {max_md:.1f} ft measured depth."
            )

        # 5. Completion rate
        wl = self._results.get("well_lifecycle", {})
        comp_rate = wl.get("completion_rate", 0.0)
        if comp_rate > 0:
            findings.append(
                f"Well completion rate is {comp_rate * 100:.1f}%."
            )

        return findings[:5]

    def _market_trends(self) -> list[str]:
        trends: list[str] = []

        # Year-over-year drilling duration trend
        de = self._results.get("drilling_efficiency", {})
        by_year = de.get("by_year", pd.DataFrame())
        if isinstance(by_year, pd.DataFrame) and len(by_year) >= 2:
            sorted_df = by_year.sort_values("YEAR").reset_index(drop=True)
            first_mean = float(sorted_df.iloc[0]["mean_days"])
            last_mean = float(sorted_df.iloc[-1]["mean_days"])
            first_yr = int(sorted_df.iloc[0]["YEAR"])
            last_yr = int(sorted_df.iloc[-1]["YEAR"])
            delta = last_mean - first_mean
            direction = "decreased" if delta < 0 else "increased"
            trends.append(
                f"Mean drilling duration {direction} from {first_mean:.1f}"
                f" to {last_mean:.1f} days between {first_yr} and"
                f" {last_yr} (year-over-year change of {delta:.1f} days)."
            )
        else:
            trends.append(
                "Insufficient years for drilling duration trend analysis."
            )

        # Year-over-year depth trend
        wd = self._results.get("well_depth", {})
        depth_by_year = wd.get("by_year", pd.DataFrame())
        if isinstance(depth_by_year, pd.DataFrame) and len(depth_by_year) >= 2:
            sorted_df = depth_by_year.sort_values("YEAR").reset_index(drop=True)
            first_md = float(sorted_df.iloc[0]["mean_md"])
            last_md = float(sorted_df.iloc[-1]["mean_md"])
            first_yr = int(sorted_df.iloc[0]["YEAR"])
            last_yr = int(sorted_df.iloc[-1]["YEAR"])
            delta = last_md - first_md
            direction = "decreased" if delta < 0 else "increased"
            trends.append(
                f"Mean well depth {direction} from {first_md:.1f} to"
                f" {last_md:.1f} ft between {first_yr} and {last_yr}"
                f" (year-over-year change of {delta:.1f} ft)."
            )
        else:
            trends.append(
                "Insufficient years for well depth trend analysis."
            )

        return trends

    def _competitive_intelligence(self) -> list[str]:
        op = self._results.get("operator_portfolio", {})
        top_ops = op.get("top_operators", pd.DataFrame())

        if not isinstance(top_ops, pd.DataFrame) or top_ops.empty:
            return ["No operator data available"]

        insights: list[str] = []
        for _, row in top_ops.head(3).iterrows():
            name = row["BUS_ASC_NAME"]
            count = int(row["activity_count"])
            wells = int(row["unique_wells"])
            areas = int(row["unique_areas"])
            insights.append(
                f"{name}: {count} activities, {wells} unique wells"
                f" across {areas} areas."
            )

        return insights

    def _opportunity_areas(self) -> list[str]:
        opportunities: list[str] = []
        ca = self._results.get("cross_activity", {})

        # Depth classes with high drilling-to-intervention ratio (> 3)
        by_dc = ca.get("by_depth_class", pd.DataFrame())
        if isinstance(by_dc, pd.DataFrame) and not by_dc.empty:
            if "ratio" in by_dc.columns and "WATER_DEPTH_CLASS" in by_dc.columns:
                # Depth classes with drilling but no intervention
                if "intervention" in by_dc.columns:
                    no_interv = by_dc[by_dc["intervention"] == 0]
                    for _, row in no_interv.iterrows():
                        dc = row["WATER_DEPTH_CLASS"]
                        d = int(row["drilling"])
                        opportunities.append(
                            f"{dc} has {d} drilling activities but no"
                            f" intervention — potential greenfield"
                            f" opportunity for intervention services."
                        )

                # Depth classes where ratio > 3
                high_ratio = by_dc[by_dc["ratio"] > 3.0]
                for _, row in high_ratio.iterrows():
                    dc = row["WATER_DEPTH_CLASS"]
                    r = float(row["ratio"])
                    opportunities.append(
                        f"{dc} has a drilling-to-intervention ratio of"
                        f" {r:.1f}, indicating underserved intervention"
                        f" demand."
                    )

        # Areas with high activity but low operator diversity
        by_area = ca.get("by_area", pd.DataFrame())
        op = self._results.get("operator_portfolio", {})
        top_ops = op.get("top_operators", pd.DataFrame())
        if (isinstance(by_area, pd.DataFrame) and not by_area.empty
                and isinstance(top_ops, pd.DataFrame) and not top_ops.empty):
            if "AREA_CODE" in by_area.columns:
                total_operators = len(top_ops)
                if total_operators > 0:
                    for _, row in by_area.iterrows():
                        area = row["AREA_CODE"]
                        total_act = int(row.get("drilling", 0)) + int(
                            row.get("intervention", 0),
                        )
                        if total_act > 10 and total_operators <= 3:
                            opportunities.append(
                                f"Area {area} has {total_act} total"
                                f" activities with only {total_operators}"
                                f" operators — low competitive density."
                            )

        return opportunities

    def _risk_factors(self) -> list[str]:
        risks: list[str] = []

        # Year-over-year activity decline
        de = self._results.get("drilling_efficiency", {})
        by_year = de.get("by_year", pd.DataFrame())
        if isinstance(by_year, pd.DataFrame) and len(by_year) >= 2:
            sorted_df = by_year.sort_values("YEAR").reset_index(drop=True)
            first_count = int(sorted_df.iloc[0]["count"])
            last_count = int(sorted_df.iloc[-1]["count"])
            first_yr = int(sorted_df.iloc[0]["YEAR"])
            last_yr = int(sorted_df.iloc[-1]["YEAR"])
            if last_count < first_count:
                risks.append(
                    f"Drilling activity declined from {first_count} wells"
                    f" in {first_yr} to {last_count} wells in {last_yr}."
                )

        # High P&A rate (> 30%)
        wl = self._results.get("well_lifecycle", {})
        status_dist = wl.get("status_distribution", pd.DataFrame())
        if isinstance(status_dist, pd.DataFrame) and not status_dist.empty:
            if "WELL_STATUS" in status_dist.columns and "count" in status_dist.columns:
                total = int(status_dist["count"].sum())
                pa_rows = status_dist[status_dist["WELL_STATUS"] == "PA"]
                pa_count = int(pa_rows["count"].sum()) if not pa_rows.empty else 0
                if total > 0:
                    pa_pct = pa_count / total
                    if pa_pct > 0.30:
                        risks.append(
                            f"High P&A rate of {pa_pct * 100:.1f}%"
                            f" ({pa_count} of {total} wells) may indicate"
                            f" mature or declining fields."
                        )

        # Areas with declining activity (compare year-over-year count)
        wd = self._results.get("well_depth", {})
        depth_by_year = wd.get("by_year", pd.DataFrame())
        if isinstance(depth_by_year, pd.DataFrame) and len(depth_by_year) >= 2:
            sorted_df = depth_by_year.sort_values("YEAR").reset_index(drop=True)
            first_count = int(sorted_df.iloc[0]["count"])
            last_count = int(sorted_df.iloc[-1]["count"])
            first_yr = int(sorted_df.iloc[0]["YEAR"])
            last_yr = int(sorted_df.iloc[-1]["YEAR"])
            if last_count < first_count:
                risks.append(
                    f"Well depth data volume declined from {first_count}"
                    f" records in {first_yr} to {last_count} records"
                    f" in {last_yr}, suggesting reduced exploration."
                )

        # Ensure at least one risk factor for non-empty data
        if not risks:
            ca = self._results.get("cross_activity", {})
            d_count = ca.get("drilling_count", 0)
            i_count = ca.get("intervention_count", 0)
            if d_count + i_count > 0:
                risks.append(
                    "No significant risk factors identified in current"
                    " dataset."
                )

        return risks
