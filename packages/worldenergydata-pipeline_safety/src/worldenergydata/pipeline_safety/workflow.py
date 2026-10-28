# ABOUTME: End-to-end PHMSA pipeline safety assessment workflow.
# ABOUTME: PHMSA incident data -> defect characterization -> FFS assessment -> verdict.

"""
PHMSA pipeline safety: incident data -> FFS assessment -> verdict.
Implements Modified B31G (Kiefner-Vieth) and original ASME B31G.
Source: ORNL/TM-2019/1192 (May 2019), sections 2.1-2.4,
https://www.osti.gov/servlets/purl/1855701 (public technical report).
Original criterion basis: ASME B31G-1991 (reaffirmed 2004), as identified there.
The modified branch retains the historical 0.9*SMYS screening flow stress,
not the published modified criterion's flow stress; results disclose this choice.
"""

import math
from dataclasses import dataclass

import pandas as pd


@dataclass
class PipelineDefect:
    """Characterizes a pipeline defect from PHMSA incident data."""

    incident_id: str
    location: str  # pipeline segment or milepost
    defect_type: str  # "corrosion"|"mechanical"|"material"|"weld"|"third_party"
    depth_pct_wall: float  # percent wall; criterion scope checked before pressure
    length_mm: float  # axial defect length
    pipe_od_mm: float  # outer diameter
    wall_thickness_mm: float
    smys_mpa: float  # specified minimum yield strength
    maop_mpa: float  # maximum allowable operating pressure
    year: int | None
    source: str  # "phmsa"


@dataclass
class FFSResult:
    """Fitness-for-Service assessment result (ASME B31G / Modified B31G)."""

    incident_id: str
    method: str  # "b31g" | "modified_b31g"
    failure_pressure_mpa: float
    safe_pressure_mpa: float  # failure_pressure / safety_factor
    safety_factor: float  # supplied divisor; default basis documented below
    verdict: str  # "accept"|"monitor"|"repair"|"replace"
    remaining_life_years: float | None
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
# ORNL/TM-2019/1192 (2019), section 2.4.1, p. 10: example factor for
# maximum operating stress <= 0.72 SMYS. Applicability remains caller-owned.
_SF_GAS = 1.39

# CSV schema contract: no implicit conversions or geometry/pressure defaults.
ASSESSMENT_UNITS = {
    "depth_pct_wall": "% wall",
    "length_mm": "mm",
    "pipe_od_mm": "mm",
    "wall_thickness_mm": "mm",
    "smys_mpa": "MPa",
    "maop_mpa": "MPa",
    "failure_pressure_mpa": "MPa",
    "safe_pressure_mpa": "MPa",
}

_ASSESSMENT_NUMERIC_FIELDS = (
    "depth_pct_wall",
    "length_mm",
    "pipe_od_mm",
    "wall_thickness_mm",
    "smys_mpa",
    "maop_mpa",
)


def _finite_number(value: object, field: str) -> float:
    """Reject explicit missing/non-finite data (issue 1295), without defaults."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    # Python 3 Library Reference, math.isfinite: excludes NaN and infinities.
    # https://docs.python.org/3/library/math.html#math.isfinite
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    return number


# --- FFS helpers -------------------------------------------------------------


def _validate_geometry(depth_pct, L_mm, OD_mm, t_mm, smys_mpa):
    """Reject missing, non-finite, nonphysical or out-of-scope geometry.

    ORNL/TM-2019/1192 (2019), sections 2.1.1-2.1.2: maximum depth 80%.
    Positivity is a dimensional prerequisite, not a design acceptance limit.
    """
    fields = {
        "depth_pct_wall": depth_pct,
        "length_mm": L_mm,
        "pipe_od_mm": OD_mm,
        "wall_thickness_mm": t_mm,
        "smys_mpa": smys_mpa,
    }
    values = {k: _finite_number(v, k) for k, v in fields.items()}
    if not 0 <= values["depth_pct_wall"] <= 80.0:
        raise ValueError("depth_pct_wall outside criterion scope [0, 80]")
    for field, value in values.items():
        if field != "depth_pct_wall" and value <= 0:
            raise ValueError(f"{field} must be positive")
    if values["wall_thickness_mm"] >= values["pipe_od_mm"] / 2:
        raise ValueError("wall_thickness_mm must leave a positive bore")
    return tuple(values.values())


def _folias_factor(L_mm: float, OD_mm: float, t_mm: float) -> float:
    """Modified Folias factor; ORNL/TM-2019/1192 (2019), eqs. 10-11.

    Both branches and all coefficients, including the z=50 switch, follow
    section 2.4.2. This helper must not be used by the original criterion.
    """
    _, L_mm, OD_mm, t_mm, _ = _validate_geometry(0, L_mm, OD_mm, t_mm, 1)
    z = _finite_number(L_mm**2 / (OD_mm * t_mm), "length_parameter")
    if L_mm <= math.sqrt(50.0 * OD_mm * t_mm):
        return math.sqrt(1.0 + 0.6275 * z - 0.003375 * z**2)
    return 0.032 * z + 3.3


def _failure_pressure_modified_b31g(
    depth_pct: float, L_mm: float, OD_mm: float, t_mm: float, smys_mpa: float
) -> float:
    """Modified-shape screening variant with historical flow stress 0.9*SMYS.

    Shape coefficient 0.85: ORNL/TM-2019/1192 (2019), section 2.1.2;
    pressure equation 2, modified Folias equations 10-11. The 0.9 multiplier
    is preserved from the repository knowledge pack revision 1, section 6 SF2,
    for compatibility, and is NOT the published modified flow-stress rule.
    The public report section 2.2.2 specifies SMYS + 10,000 psi instead.
    No standards-compliance or material applicability claim is made.
    """
    depth_pct, L_mm, OD_mm, t_mm, smys_mpa = _validate_geometry(
        depth_pct, L_mm, OD_mm, t_mm, smys_mpa
    )
    d_t = depth_pct / 100.0  # percent definition, ORNL section 2.1
    M = _folias_factor(L_mm, OD_mm, t_mm)
    area = 0.85 * d_t
    return _finite_number(
        (2.0 * t_mm / OD_mm) * smys_mpa * 0.9 * (1.0 - area) / (1.0 - area / M),
        "failure_pressure_mpa",
    )


def _failure_pressure_b31g(
    depth_pct: float, L_mm: float, OD_mm: float, t_mm: float, smys_mpa: float
) -> float:
    """Original ASME B31G-1991 criterion including the long-flaw limit.

    Source: ORNL/TM-2019/1192 (2019), sections 2.1.1, 2.2.1, 2.4.1,
    equations 2, 5, 6 and 8: flow=1.1*SMYS; for z=L**2/(D*t)<=20,
    M=sqrt(1+0.8*z), area=2*d/(3*t); for z>20 the reduction is 1-d/t.
    These are burst pressures; safe pressure additionally divides by a factor.
    """
    depth_pct, L_mm, OD_mm, t_mm, smys_mpa = _validate_geometry(
        depth_pct, L_mm, OD_mm, t_mm, smys_mpa
    )
    d_t = depth_pct / 100.0
    z = _finite_number(L_mm**2 / (OD_mm * t_mm), "length_parameter")
    base = (2.0 * t_mm / OD_mm) * smys_mpa * 1.1
    if L_mm > math.sqrt(20.0 * OD_mm * t_mm):
        reduction = 1.0 - d_t
    else:
        M = math.sqrt(1.0 + 0.8 * z)
        area = (2.0 / 3.0) * d_t
        reduction = (1.0 - area) / (1.0 - area / M)
    return _finite_number(base * reduction, "failure_pressure_mpa")


def _determine_verdict(
    safe_p: float, maop: float, depth_pct: float, fail_p: float
) -> str:
    """Pressure screening labels; depth limit from ORNL (2019), section 2.1.1.

    No sourced monitoring threshold is available. A sufficient safe pressure
    yields accept; monitoring intervals require a separate qualified assessment.
    """
    safe_p = _finite_number(safe_p, "safe_pressure_mpa")
    fail_p = _finite_number(fail_p, "failure_pressure_mpa")
    maop = _finite_number(maop, "maop_mpa")
    depth_pct = _finite_number(depth_pct, "depth_pct_wall")
    if safe_p <= 0 or fail_p <= 0 or maop <= 0 or not 0 <= depth_pct <= 80:
        raise ValueError("invalid pressure or depth for verdict")
    if depth_pct >= 80.0 or fail_p < maop:
        return "replace"
    if safe_p < maop:
        return "repair"
    return "accept"


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
        """Convert an incident; reject explicit missing/non-finite numeric cells.

        Geometry, material strength and MAOP must be supplied in mm, percent
        wall and MPa as named by the schema; omitted values are not evidence.
        """
        for field in _ASSESSMENT_NUMERIC_FIELDS:
            _finite_number(incident.get(field), field)
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
        return PipelineDefect(
            incident_id=incident_id,
            location=location,
            defect_type=defect_type,
            depth_pct_wall=float(incident["depth_pct_wall"]),
            length_mm=float(incident["length_mm"]),
            pipe_od_mm=float(incident["pipe_od_mm"]),
            wall_thickness_mm=float(incident["wall_thickness_mm"]),
            smys_mpa=float(incident["smys_mpa"]),
            maop_mpa=float(incident["maop_mpa"]),
            year=incident.get("year", incident.get("incident_year")),
            source="phmsa",
        )

    def assess_ffs(
        self,
        defect: PipelineDefect,
        method: str = "modified_b31g",
        safety_factor: float | None = None,
    ) -> FFSResult:
        """Apply sourced original criterion or disclosed legacy modified variant.

        See pressure-helper docstrings for equations and flow-stress choices.
        A caller-supplied safety factor must be qualified for the application;
        the default example factor is limited as documented at _SF_GAS.
        """
        for field in _ASSESSMENT_NUMERIC_FIELDS:
            _finite_number(getattr(defect, field), field)
        if defect.maop_mpa <= 0:
            raise ValueError("maop_mpa must be positive")
        if method not in {"b31g", "modified_b31g"}:
            raise ValueError("unsupported assessment method")
        sf = _finite_number(
            safety_factor if safety_factor is not None else _SF_GAS,
            "safety_factor",
        )
        # Positive divisor of the existing Pf/sf definition, not a sourced
        # engineering acceptance limit or a qualification of the default factor.
        if sf <= 0:
            raise ValueError("safety_factor must be positive")
        if method == "b31g":
            pf = _failure_pressure_b31g(
                defect.depth_pct_wall,
                defect.length_mm,
                defect.pipe_od_mm,
                defect.wall_thickness_mm,
                defect.smys_mpa,
            )
            notes = "ASME B31G-1991 original criterion; flow stress = 1.1 * SMYS"
        else:
            method = "modified_b31g"
            pf = _failure_pressure_modified_b31g(
                defect.depth_pct_wall,
                defect.length_mm,
                defect.pipe_od_mm,
                defect.wall_thickness_mm,
                defect.smys_mpa,
            )
            notes = "Modified-shape screening variant; flow stress = 0.9 * SMYS (legacy, not published modified criterion)"
        pf = _finite_number(pf, "failure_pressure_mpa")
        safe_p = _finite_number(pf / sf, "safe_pressure_mpa")
        verdict = _determine_verdict(safe_p, defect.maop_mpa, defect.depth_pct_wall, pf)
        # No qualified corrosion growth rate is available: life is unknown.
        rem_life = None
        notes += "; units: mm, % wall, MPa; remaining life not evaluated"
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
        if incidents_df.empty:
            raise ValueError("assessment input is empty")
        rows = []
        for _, row in incidents_df.iterrows():
            defect = self.characterize(row.to_dict())
            result = self.assess_ffs(defect, method=method)
            rows.append(
                {
                    "incident_id": result.incident_id,
                    "method": result.method,
                    "notes": result.notes,
                    "units": "mm, % wall, MPa",
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
        if "verdict" not in report_df.columns:
            raise ValueError("report has no verdict column")
        if (
            report_df["verdict"].isna().any()
            or not set(report_df["verdict"]) <= counts.keys()
        ):
            raise ValueError("report contains an unknown verdict")
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
            f"   Methods        : {', '.join(sorted(report_df['method'].unique()))}",
            f"   Basis          : {hr['notes']}",
            "   Source         : ORNL/TM-2019/1192 (2019)",
            "   Data source    : PHMSA National Pipeline Safety Incident Data",
            "=" * 60,
        ]
        return "\n".join(lines)
