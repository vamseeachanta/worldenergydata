"""
ABOUTME: Well planning risk analysis — tiering, scoring, MPD impact, escalation.
ABOUTME: WellPlanningRiskAnalyzer with authority/category/severity filtering and reports.
"""

from __future__ import annotations

import pandas as pd

from worldenergydata.well_planning.risk_model import (
    RiskAuthority,
    RiskCategory,
    RiskSeverity,
    WellPlanningRisk,
)
from worldenergydata.well_planning.risk_registry import WELL_PLANNING_RISKS


class WellPlanningRiskAnalyzer:
    """Analyse and report on a collection of well planning risks.

    Parameters
    ----------
    risks:
        Optional list of :class:`WellPlanningRisk` instances.  When *None*
        the built-in :data:`WELL_PLANNING_RISKS` registry is used.
    """

    def __init__(self, risks: list[WellPlanningRisk] | None = None) -> None:
        self._risks: list[WellPlanningRisk] = (
            risks if risks is not None else WELL_PLANNING_RISKS
        )

    # ------------------------------------------------------------------ #
    # Filtering helpers                                                    #
    # ------------------------------------------------------------------ #

    def get_by_authority(self, authority: RiskAuthority) -> list[WellPlanningRisk]:
        """Return all risks whose mitigation authority matches *authority*."""
        return [r for r in self._risks if r.authority == authority]

    def get_by_category(self, category: RiskCategory) -> list[WellPlanningRisk]:
        """Return all risks belonging to *category*."""
        return [r for r in self._risks if r.category == category]

    def get_by_severity(self, min_severity: RiskSeverity) -> list[WellPlanningRisk]:
        """Return risks with severity >= *min_severity* (by integer value)."""
        return [
            r for r in self._risks if r.severity.value >= min_severity.value
        ]

    def high_priority_risks(self, threshold: float = 2.0) -> list[WellPlanningRisk]:
        """Return risks with ``risk_score >= threshold``, sorted score descending."""
        filtered = [r for r in self._risks if r.risk_score >= threshold]
        return sorted(filtered, key=lambda r: r.risk_score, reverse=True)

    def mpd_mitigable_risks(self) -> list[WellPlanningRisk]:
        """Return risks where MPD technology reduces severity (``mpd_mitigation=True``)."""
        return [r for r in self._risks if r.mpd_mitigation]

    # ------------------------------------------------------------------ #
    # Reporting                                                            #
    # ------------------------------------------------------------------ #

    def risk_matrix(self) -> pd.DataFrame:
        """Return an authority x category count matrix.

        Rows are :class:`RiskAuthority` values, columns are :class:`RiskCategory`
        values.  Cell values are risk counts.
        """
        rows = [r.authority.value for r in self._risks]
        cols = [r.category.value for r in self._risks]

        authorities = [a.value for a in RiskAuthority]
        categories = [c.value for c in RiskCategory]

        data = {cat: [0] * len(authorities) for cat in categories}
        auth_index = {a: i for i, a in enumerate(authorities)}

        for auth, cat in zip(rows, cols):
            data[cat][auth_index[auth]] += 1

        df = pd.DataFrame(data, index=authorities)
        df.index.name = "authority"
        return df

    def escalation_report(self, authority: RiskAuthority) -> str:
        """Generate a plain-text escalation message for all risks at *authority*.

        Returns an empty string if no risks exist for that authority level.
        """
        risks = self.get_by_authority(authority)
        if not risks:
            return ""

        lines: list[str] = [
            f"WELL PLANNING ESCALATION REPORT — {authority.value.upper()}",
            "=" * 60,
            f"Authority level: {authority.value}",
            f"Total risks requiring action: {len(risks)}",
            "",
        ]
        for risk in sorted(risks, key=lambda r: r.risk_score, reverse=True):
            lines.append(f"[{risk.risk_id}] {risk.title}")
            lines.append(f"  Score    : {risk.risk_score:.2f}")
            lines.append(f"  Severity : {risk.severity.name}")
            lines.append(f"  Owner    : {risk.mitigation_owner}")
            lines.append(f"  Template : {risk.escalation_template}")
            lines.append("")
        return "\n".join(lines)

    def summary(self) -> pd.DataFrame:
        """Return a summary DataFrame sorted by risk_score descending.

        Columns: risk_id, title, authority, severity, risk_score, mitigation_owner.
        """
        records = [
            {
                "risk_id": r.risk_id,
                "title": r.title,
                "authority": r.authority.value,
                "severity": r.severity.name,
                "risk_score": r.risk_score,
                "mitigation_owner": r.mitigation_owner,
            }
            for r in self._risks
        ]
        df = pd.DataFrame(records)
        if df.empty:
            return df
        return df.sort_values("risk_score", ascending=False).reset_index(drop=True)
