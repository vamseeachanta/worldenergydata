# ABOUTME: End-to-end PHMSA pipeline safety assessment workflow.
# ABOUTME: PHMSA incident data -> defect characterization -> FFS assessment -> verdict.

"""
PHMSA pipeline safety: incident data -> FFS assessment -> verdict.
Implements Modified B31G (Kiefner-Vieth) and original ASME B31G.
Ref: ASME B31G-2012; Kiefner & Vieth (1989).
"""

import math
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class PipelineDefect:
    """Characterizes a pipeline defect from PHMSA incident data."""

    incident_id: str
    location: str  # pipeline segment or milepost
    defect_type: str  # "corrosion"|"mechanical"|"material"|"weld"|"third_party"
    depth_pct_wall: float  # defect depth as % of wall thickness (0-100)
    length_mm: float  # axial defect length
    pipe_od_mm: float  # outer diameter
    wall_thickness_mm: float
    smys_mpa: float  # specified minimum yield strength
    maop_mpa: float  # maximum allowable operating pressure
    year: int
    source: str  # "phmsa"


@dataclass
class FFSResult:
    """Fitness-for-Service assessment result (ASME B31G / Modified B31G)."""

    incident_id: str
    method: str  # "b31g" | "modified_b31g"
    failure_pressure_mpa: float
    safe_pressure_mpa: float  # failure_pressure / safety_factor
    safety_factor: float  # 1.39 gas, 1.25 liquid
    verdict: str  # "accept"|"monitor"|"repair"|"replace"
    remaining_life_years: Optional[float]
    notes: str


# --- constants ---------------------------------------------------------------

_DEFECT_TYPE_MAP = {
    "corrosion": "corrosion",
    "external corrosion": "corrosion",
    "internal corrosion": "corrosion",
    "mechanical": "mechanical",
    "material": "material",
    "weld": "weld",
    "welding/weld": "weld",
    "third party": "third_party",
    "third_party": "third_party",
    "other outside force": "third_party",
    "excavation damage": "third_party",
}
_DEFAULT_OD_MM = 323.85  # NPS 12
_DEFAULT_WT_MM = 9.53  # std wall
_DEFAULT_SMYS_MPA = 358.53  # X52
_DEFAULT_MAOP_GAS_MPA = 6.895  # 1000 psi
_DEFAULT_MAOP_LIQ_MPA = 5.516  # 800 psi
_DEFAULT_LENGTH_MM = 150.0
_DEFAULT_DEPTH_PCT = 30.0
_SF_GAS = 1.39
_CORROSION_GROWTH_RATE = 0.2  # mm/year


# --- FFS helpers -------------------------------------------------------------


def _folias_factor(L_mm: float, OD_mm: float, t_mm: float) -> float:
    """Folias bulging factor M (Modified B31G piecewise formula)."""
    A = (L_mm**2) / (OD_mm * t_mm)
    if A <= 50.0:
        return math.sqrt(1.0 + 0.6275 * A - 0.003375 * A**2)
    return 0.032 * A + 3.3


def _failure_pressure_modified_b31g(
    depth_pct: float, L_mm: float, OD_mm: float, t_mm: float, smys_mpa: float
) -> float:
    """Modified B31G (Kiefner-Vieth): Pf=(2t/D)*SMYS*0.9*(1-0.85*d/t)/(1-0.85*d/t/M)."""
    d_t = depth_pct / 100.0
    M = _folias_factor(L_mm, OD_mm, t_mm)
    denom = 1.0 - (0.85 * d_t / M)
    if denom <= 0:
        return 0.0
    return max((2.0 * t_mm / OD_mm) * smys_mpa * 0.9 * (1.0 - 0.85 * d_t) / denom, 0.0)


def _failure_pressure_b31g(
    depth_pct: float, L_mm: float, OD_mm: float, t_mm: float, smys_mpa: float
) -> float:
    """Original ASME B31G: Pf=(2t/D)*SMYS*(1-(2/3)*d/t)/(1-(2/3)*d/t/M)."""
    d_t = depth_pct / 100.0
    M = _folias_factor(L_mm, OD_mm, t_mm)
    denom = 1.0 - ((2.0 / 3.0) * d_t / M)
    if denom <= 0:
        return 0.0
    return max((2.0 * t_mm / OD_mm) * smys_mpa * (1.0 - (2.0 / 3.0) * d_t) / denom, 0.0)


def _determine_verdict(
    safe_p: float, maop: float, depth_pct: float, fail_p: float
) -> str:
    """FFS verdict: replace >= 80% or fail_p < maop; repair < maop; monitor >= 50%; accept."""
    if depth_pct >= 80.0 or fail_p < maop:
        return "replace"
    if safe_p < maop:
        return "repair"
    if depth_pct >= 50.0:
        return "monitor"
    return "accept"


def _remaining_life(depth_pct: float, t_mm: float) -> Optional[float]:
    """Years until corrosion reaches 80% wall at default growth rate."""
    current = (depth_pct / 100.0) * t_mm
    critical = 0.80 * t_mm
    remaining = critical - current
    if remaining <= 0:
        return 0.0
    return remaining / _CORROSION_GROWTH_RATE


# --- Public workflow class ---------------------------------------------------


class PipelineSafetyWorkflow:
    """
    Orchestrates the full PHMSA -> FFS -> verdict pipeline.

    Usage:
        workflow = PipelineSafetyWorkflow()
        result = workflow.assess(incident_dict)
        report = workflow.generate_report(incidents_df)
    """

    def characterize(self, incident: dict) -> PipelineDefect:
        """Convert PHMSA incident record to PipelineDefect with sensible defaults."""
        incident_id = str(
            incident.get("incident_id") or incident.get("report_number") or "UNKNOWN"
        )
        location = str(
            incident.get("location")
            or incident.get("state")
            or incident.get("city")
            or "unknown"
        )
        raw_type = (
            incident.get("defect_type") or incident.get("cause_category") or "corrosion"
        )
        defect_type = _DEFECT_TYPE_MAP.get(str(raw_type).lower(), "corrosion")
        pipeline_type = incident.get("pipeline_type", "gas_transmission")
        if incident.get("maop_mpa"):
            maop_mpa = float(incident["maop_mpa"])
        elif "liquid" in str(pipeline_type):
            maop_mpa = _DEFAULT_MAOP_LIQ_MPA
        else:
            maop_mpa = _DEFAULT_MAOP_GAS_MPA
        return PipelineDefect(
            incident_id=incident_id,
            location=location,
            defect_type=defect_type,
            depth_pct_wall=float(incident.get("depth_pct_wall") or _DEFAULT_DEPTH_PCT),
            length_mm=float(incident.get("length_mm") or _DEFAULT_LENGTH_MM),
            pipe_od_mm=float(incident.get("pipe_od_mm") or _DEFAULT_OD_MM),
            wall_thickness_mm=float(
                incident.get("wall_thickness_mm") or _DEFAULT_WT_MM
            ),
            smys_mpa=float(incident.get("smys_mpa") or _DEFAULT_SMYS_MPA),
            maop_mpa=maop_mpa,
            year=int(incident.get("year") or incident.get("incident_year") or 2020),
            source="phmsa",
        )

    def assess_ffs(
        self,
        defect: PipelineDefect,
        method: str = "modified_b31g",
        safety_factor: Optional[float] = None,
    ) -> FFSResult:
        """
        Apply ASME B31G / Modified B31G fitness-for-service assessment.

        Modified B31G Folias factor:
          M = sqrt(1 + 0.6275*(L²/Dt) - 0.003375*(L²/Dt)²)  for L²/Dt <= 50
          M = 0.032*(L²/Dt) + 3.3                             for L²/Dt > 50
        Failure pressure (Modified B31G / Kiefner-Vieth):
          Pf = (2t/D) * SMYS * 0.9 * (1 - 0.85*d/t) / (1 - 0.85*d/t/M)
        """
        sf = float(safety_factor) if safety_factor is not None else _SF_GAS
        if method == "b31g":
            pf = _failure_pressure_b31g(
                defect.depth_pct_wall,
                defect.length_mm,
                defect.pipe_od_mm,
                defect.wall_thickness_mm,
                defect.smys_mpa,
            )
            notes = "ASME B31G original criterion"
        else:
            method = "modified_b31g"
            pf = _failure_pressure_modified_b31g(
                defect.depth_pct_wall,
                defect.length_mm,
                defect.pipe_od_mm,
                defect.wall_thickness_mm,
                defect.smys_mpa,
            )
            notes = "Modified B31G (Kiefner-Vieth)"
        safe_p = pf / sf
        verdict = _determine_verdict(safe_p, defect.maop_mpa, defect.depth_pct_wall, pf)
        rem_life = (
            _remaining_life(defect.depth_pct_wall, defect.wall_thickness_mm)
            if defect.defect_type == "corrosion"
            else None
        )
        return FFSResult(
            incident_id=defect.incident_id,
            method=method,
            failure_pressure_mpa=round(pf, 4),
            safe_pressure_mpa=round(safe_p, 4),
            safety_factor=sf,
            verdict=verdict,
            remaining_life_years=rem_life,
            notes=notes,
        )

    def assess(self, incident: dict, method: str = "modified_b31g") -> FFSResult:
        """One-call: characterize + FFS assess."""
        return self.assess_ffs(self.characterize(incident), method=method)

    def generate_report(
        self, incidents_df: pd.DataFrame, method: str = "modified_b31g"
    ) -> pd.DataFrame:
        """Batch assess all incidents. Returns DataFrame with FFS results per row."""
        rows = []
        for _, row in incidents_df.iterrows():
            defect = self.characterize(row.to_dict())
            result = self.assess_ffs(defect, method=method)
            rows.append(
                {
                    "incident_id": result.incident_id,
                    "defect_type": defect.defect_type,
                    "failure_pressure_mpa": result.failure_pressure_mpa,
                    "safe_pressure_mpa": result.safe_pressure_mpa,
                    "safety_factor": result.safety_factor,
                    "verdict": result.verdict,
                    "remaining_life_years": result.remaining_life_years,
                }
            )
        return pd.DataFrame(rows)

    def verdict_summary(self, report_df: pd.DataFrame) -> dict:
        """Return counts by verdict: {accept: N, monitor: N, repair: N, replace: N}."""
        counts = {"accept": 0, "monitor": 0, "repair": 0, "replace": 0}
        if "verdict" not in report_df.columns or report_df.empty:
            return counts
        for verdict, count in report_df["verdict"].value_counts().items():
            if verdict in counts:
                counts[verdict] = int(count)
        return counts

    def case_study_narrative(self, report_df: pd.DataFrame) -> str:
        """Generate structured case study: dataset summary, FFS results, key finding, method."""
        if report_df.empty:
            return "No PHMSA incidents provided for case study."
        n = len(report_df)
        summary = self.verdict_summary(report_df)
        min_idx = report_df["failure_pressure_mpa"].idxmin()
        hr = report_df.loc[min_idx]
        types_str = ", ".join(sorted(report_df["defect_type"].unique().tolist()))
        lines = [
            "=" * 60,
            "PHMSA PIPELINE SAFETY — FFS CASE STUDY",
            "=" * 60,
            "",
            "1. DATASET SUMMARY",
            f"   Total incidents assessed : {n}",
            f"   Defect types present     : {types_str}",
            "",
            "2. FFS RESULTS SUMMARY (ASME B31G / Modified B31G)",
            f"   Accept  : {summary['accept']}",
            f"   Monitor : {summary['monitor']}",
            f"   Repair  : {summary['repair']}",
            f"   Replace : {summary['replace']}",
            "",
            "3. KEY FINDING — HIGHEST-RISK SEGMENT",
            f"   Incident ID      : {hr['incident_id']}",
            f"   Defect type      : {hr['defect_type']}",
            f"   Failure pressure : {hr['failure_pressure_mpa']:.2f} MPa",
            f"   Safe pressure    : {hr['safe_pressure_mpa']:.2f} MPa",
            f"   Verdict          : {hr['verdict'].upper()}",
            "",
            "4. METHODOLOGY",
            "   Primary method : Modified B31G (Kiefner-Vieth, 1989)",
            "   Standard       : ASME B31G-2012",
            "   Data source    : PHMSA National Pipeline Safety Incident Data",
            "=" * 60,
        ]
        return "\n".join(lines)
