"""
ABOUTME: Slim-hole vs standard-hole decision framework.
ABOUTME: Application matrix, pressure window check, capital/operational trade-offs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from worldenergydata.well_bore_design.hydraulics import WellBoreHydraulics
from worldenergydata.well_bore_design.schemas import BoreType

# ---------------------------------------------------------------------------
# Application matrix
# ---------------------------------------------------------------------------

APPLICATION_MATRIX: dict[str, dict] = {
    BoreType.SLIM_HOLE.value: {
        "well_types": {"exploration", "appraisal"},
        "depth_range_m": (0, 6000),
        "flow_range_bopd": (0, 3000),
        "capital_cost_factor": 0.65,
        "description": (
            "Preferred for exploration/appraisal, tight pressure windows, "
            "low flow requirements, and cost-sensitive programmes."
        ),
    },
    BoreType.STANDARD.value: {
        "well_types": {"exploration", "appraisal", "development", "production"},
        "depth_range_m": (0, 9000),
        "flow_range_bopd": (0, 15000),
        "capital_cost_factor": 1.0,
        "description": (
            "Industry baseline — suits most development and production wells "
            "with conventional completions."
        ),
    },
    BoreType.LARGE_BORE.value: {
        "well_types": {"development", "production"},
        "depth_range_m": (0, 7000),
        "flow_range_bopd": (5000, 100000),
        "capital_cost_factor": 1.35,
        "description": (
            "High-rate gas/oil producers, gas-lift candidates, intelligent "
            "completions, and gravel-pack wells requiring large completion OD."
        ),
    },
}

# Risk level per bore type — operational baseline
_BASE_RISK: dict[str, str] = {
    BoreType.SLIM_HOLE.value: "medium",
    BoreType.STANDARD.value: "low",
    BoreType.LARGE_BORE.value: "medium",
}

# Minimum pressure window (ppg) required for each bore type
_MIN_WINDOW_PPG: dict[str, float] = {
    BoreType.SLIM_HOLE.value: 0.3,    # smaller annulus → higher ECD → needs margin
    BoreType.STANDARD.value: 0.5,
    BoreType.LARGE_BORE.value: 0.6,
}


# ---------------------------------------------------------------------------
# Recommendation dataclass
# ---------------------------------------------------------------------------


@dataclass
class BoreTypeRecommendation:
    """Output of the bore-type selection decision framework."""

    recommended: BoreType
    rationale: str
    pressure_window_compatible: bool
    hole_cleaning_adequate: bool
    capital_cost_factor: float      # relative to standard (1.0), < 1.0 = cheaper
    operational_risk_level: str     # "low" | "medium" | "high"
    caveats: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Decision engine
# ---------------------------------------------------------------------------


class BoreTypeDecision:
    """Decision framework for slim-hole vs standard-hole bore type selection.

    The ``recommend`` method applies the application matrix plus a
    hydraulic feasibility check to return a ``BoreTypeRecommendation``.
    """

    def __init__(self) -> None:
        self._hydraulics = WellBoreHydraulics()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def recommend(
        self,
        well_type: str,
        total_depth_m: float,
        pressure_window_ppg: float,
        target_flow_rate_bopd: float,
        deviation_deg: float = 0.0,
        completion_type: str = "simple",
    ) -> BoreTypeRecommendation:
        """Select the most appropriate bore type.

        Parameters
        ----------
        well_type:
            One of "exploration", "appraisal", "development", "production".
        total_depth_m:
            Planned total depth in metres.
        pressure_window_ppg:
            Available formation pressure window (fracture - pore pressure, ppg).
        target_flow_rate_bopd:
            Target production flow rate in bopd.
        deviation_deg:
            Maximum borehole deviation (degrees from vertical; default 0).
        completion_type:
            One of "simple", "gravel_pack", "intelligent".
        """
        candidate = self._select_candidate(
            well_type, total_depth_m, pressure_window_ppg, target_flow_rate_bopd
        )
        matrix = APPLICATION_MATRIX[candidate.value]
        caveats: list[str] = []

        pw_ok = pressure_window_ppg >= _MIN_WINDOW_PPG[candidate.value]
        if not pw_ok:
            caveats.append(
                f"Pressure window {pressure_window_ppg:.2f} ppg is below the "
                f"{_MIN_WINDOW_PPG[candidate.value]:.2f} ppg minimum for {candidate.value}."
            )

        hci_ok = self._hole_cleaning_ok(candidate, deviation_deg)
        if not hci_ok:
            caveats.append(
                f"Deviated well ({deviation_deg}°) may challenge hole cleaning "
                f"in {candidate.value} configuration — consider optimising flow rate."
            )

        risk = self._risk_level(candidate, deviation_deg, completion_type)

        if completion_type in {"gravel_pack", "intelligent"} and candidate == BoreType.SLIM_HOLE:
            caveats.append(
                f"Completion type '{completion_type}' is poorly suited to slim-hole; "
                "consider upgrading to STANDARD."
            )

        rationale = self._build_rationale(
            candidate, well_type, total_depth_m, target_flow_rate_bopd,
            pressure_window_ppg, completion_type
        )

        return BoreTypeRecommendation(
            recommended=candidate,
            rationale=rationale,
            pressure_window_compatible=pw_ok,
            hole_cleaning_adequate=hci_ok,
            capital_cost_factor=matrix["capital_cost_factor"],
            operational_risk_level=risk,
            caveats=caveats,
        )

    def pressure_window_check(
        self,
        bore_type: BoreType,
        mud_weight_ppg: float,
        fracture_gradient_ppg: float,
        pore_pressure_ppg: float,
        flow_rate_gpm: float,
        depth_ft: float,
    ) -> dict[str, object]:
        """Check pressure window compatibility for a given bore type.

        Returns dict with:
            compatible (bool), margin_ppg (float), limiting_factor (str)
        """
        comparison = self._hydraulics.compare_bore_types(
            flow_rate_gpm=flow_rate_gpm,
            mud_weight_ppg=mud_weight_ppg,
            depth_ft=depth_ft,
        )
        ecd = comparison[bore_type.value]["ecd_ppg"]

        margin_frac = fracture_gradient_ppg - ecd
        available_window = fracture_gradient_ppg - pore_pressure_ppg
        min_required = _MIN_WINDOW_PPG[bore_type.value]

        compatible = margin_frac >= 0.0 and available_window >= min_required

        if margin_frac < 0.0:
            limiting = "ecd_exceeds_fracture_gradient"
        elif available_window < min_required:
            limiting = "insufficient_pressure_window"
        elif ecd > mud_weight_ppg * 1.05:
            limiting = "high_ecd_in_narrow_annulus"
        else:
            limiting = "none"

        return {
            "compatible": compatible,
            "margin_ppg": round(margin_frac, 4),
            "limiting_factor": limiting,
            "ecd_ppg": round(ecd, 4),
            "available_window_ppg": round(available_window, 4),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _select_candidate(
        self,
        well_type: str,
        total_depth_m: float,
        pressure_window_ppg: float,
        target_flow_rate_bopd: float,
    ) -> BoreType:
        """Choose the preferred bore type from the application matrix."""
        # High-rate or complex completions → large bore
        if target_flow_rate_bopd > 15000:
            return BoreType.LARGE_BORE

        # Exploration / appraisal with tight margin → slim hole
        if well_type in {"exploration", "appraisal"} and pressure_window_ppg < 1.5:
            return BoreType.SLIM_HOLE

        # Exploration with adequate margin but low flow → slim hole
        if well_type in {"exploration", "appraisal"} and target_flow_rate_bopd < 3000:
            return BoreType.SLIM_HOLE

        # High-flow development/production
        if target_flow_rate_bopd > 5000:
            return BoreType.LARGE_BORE

        return BoreType.STANDARD

    def _hole_cleaning_ok(self, bore_type: BoreType, deviation_deg: float) -> bool:
        """Hole cleaning is challenged beyond 45° in slim-hole geometry."""
        if bore_type == BoreType.SLIM_HOLE and deviation_deg > 45.0:
            return False
        return True

    def _risk_level(
        self,
        bore_type: BoreType,
        deviation_deg: float,
        completion_type: str,
    ) -> str:
        base = _BASE_RISK[bore_type.value]
        risk_order = ["low", "medium", "high"]
        idx = risk_order.index(base)

        if deviation_deg > 60:
            idx = min(idx + 1, 2)
        if completion_type in {"gravel_pack", "intelligent"} and bore_type == BoreType.SLIM_HOLE:
            idx = min(idx + 1, 2)

        return risk_order[idx]

    def _build_rationale(
        self,
        bore_type: BoreType,
        well_type: str,
        total_depth_m: float,
        target_flow_rate_bopd: float,
        pressure_window_ppg: float,
        completion_type: str,
    ) -> str:
        matrix = APPLICATION_MATRIX[bore_type.value]
        return (
            f"{bore_type.value} selected for {well_type} well "
            f"(TD {total_depth_m:.0f} m, {target_flow_rate_bopd:.0f} bopd target, "
            f"{pressure_window_ppg:.2f} ppg window). "
            f"{matrix['description']} "
            f"Capital cost factor: {matrix['capital_cost_factor']:.2f}x standard."
        )
