# ABOUTME: Decommissioning cost estimation model for offshore assets.
# ABOUTME: Parametric cost estimation by asset type, water depth, weight, and region.

"""Parametric decommissioning cost estimator for offshore oil and gas assets.

Supports jacket, spar, tlp, fpso, subsea_tree, pipeline_km, and well_p_and_a
asset types across GoM, NCS, UKCS, Brazil, and West Africa regions.
"""

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Internal cost factor constants (all costs in MUSD)
# ---------------------------------------------------------------------------

# Base costs, per-tonne rates, per-metre-depth rates
_COST_FACTORS: dict[str, dict] = {
    "jacket": {
        "base_musd": 2.0,
        "per_tonne_musd": 0.00005,   # $0.05/tonne → 0.00005 MUSD/tonne
        "per_m_depth_musd": 0.005,   # $5k/m depth → 0.005 MUSD/m
        "confidence": "medium",
    },
    "well_p_and_a": {
        "base_musd": 8.0,
        "per_tonne_musd": 0.0,
        "per_m_depth_musd": 0.015,   # $15k/m depth
        "confidence": "medium",
    },
    "fpso": {
        "base_musd": 80.0,
        "per_tonne_musd": 0.00002,   # $0.02/tonne
        "per_m_depth_musd": 0.0,
        "confidence": "low",
    },
    "subsea_tree": {
        "base_musd": 2.0,
        "per_tonne_musd": 0.0,
        "per_m_depth_musd": 0.0,
        "confidence": "high",
    },
    "pipeline_km": {
        "base_musd": 0.5,            # per km
        "per_tonne_musd": 0.0,
        "per_m_depth_musd": 0.0,
        "confidence": "medium",
    },
    "spar": {
        "base_musd": 50.0,
        "per_tonne_musd": 0.00003,
        "per_m_depth_musd": 0.003,
        "confidence": "low",
    },
    "tlp": {
        "base_musd": 40.0,
        "per_tonne_musd": 0.00003,
        "per_m_depth_musd": 0.002,
        "confidence": "low",
    },
}

# Region multipliers relative to GoM baseline
_REGION_MULTIPLIERS: dict[str, float] = {
    "gom": 1.0,
    "ncs": 1.3,
    "ukcs": 1.25,
    "brazil": 1.1,
    "west_africa": 1.15,
}

_VALID_REGIONS = set(_REGION_MULTIPLIERS.keys())
_VALID_ASSET_TYPES = set(_COST_FACTORS.keys())

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class DecommissioningCostEstimate:
    """Parametric cost estimate for a single decommissioning asset."""

    asset_type: str
    water_depth_m: float
    weight_tonnes: float
    region: str
    estimated_cost_musd: float
    confidence: str           # "low" | "medium" | "high"
    year: int
    data_source: str
    notes: str = ""


# ---------------------------------------------------------------------------
# Estimator
# ---------------------------------------------------------------------------


class DecommissioningCostEstimator:
    """Parametric cost estimator using depth/weight/region cost factors.

    Based on published industry benchmarks:
    - GoM jacket removal: ~$1-5M/tonne at <200m, escalates with depth
    - UKCS: 20-40% premium over GoM for North Sea conditions
    - P&A well: $5-15M per well depending on complexity
    - FPSO removal: $50-200M depending on size
    """

    def estimate(
        self,
        asset_type: str,
        water_depth_m: float,
        weight_tonnes: float = 0.0,
        region: str = "gom",
        year: int = 2025,
    ) -> DecommissioningCostEstimate:
        """Estimate decommissioning cost for a single asset.

        Args:
            asset_type: One of jacket, spar, tlp, fpso, subsea_tree,
                pipeline_km, well_p_and_a.
            water_depth_m: Water depth in metres (or pipeline length km
                for pipeline_km type).
            weight_tonnes: Topside / structure weight in tonnes.
            region: One of gom, ncs, ukcs, brazil, west_africa.
            year: Reference year for the estimate.

        Returns:
            DecommissioningCostEstimate with parametric cost.

        Raises:
            ValueError: If asset_type or region is not recognised.
        """
        asset_type = asset_type.lower()
        region = region.lower()

        if asset_type not in _VALID_ASSET_TYPES:
            raise ValueError(
                f"Unknown asset_type {asset_type!r}. "
                f"Valid types: {sorted(_VALID_ASSET_TYPES)}"
            )
        if region not in _VALID_REGIONS:
            raise ValueError(
                f"Unknown region {region!r}. "
                f"Valid regions: {sorted(_VALID_REGIONS)}"
            )

        factors = self._get_factors(asset_type)
        multiplier = _REGION_MULTIPLIERS[region]

        wt = weight_tonnes if weight_tonnes is not None else 0.0

        # For pipeline_km, water_depth_m represents length in km
        raw_cost = (
            factors["base_musd"]
            + factors["per_tonne_musd"] * wt
            + factors["per_m_depth_musd"] * water_depth_m
        )
        estimated_cost = raw_cost * multiplier

        return DecommissioningCostEstimate(
            asset_type=asset_type,
            water_depth_m=water_depth_m,
            weight_tonnes=wt,
            region=region,
            estimated_cost_musd=round(estimated_cost, 4),
            confidence=factors["confidence"],
            year=year,
            data_source="parametric_estimate",
            notes="",
        )

    def estimate_campaign(
        self,
        assets: list[dict],
    ) -> list[DecommissioningCostEstimate]:
        """Estimate costs for a list of assets.

        Each dict must contain 'asset_type', 'water_depth_m', and
        optionally 'weight_tonnes', 'region', 'year'.

        Returns:
            List of DecommissioningCostEstimate, one per input asset.
        """
        results = []
        for asset in assets:
            estimate = self.estimate(
                asset_type=asset["asset_type"],
                water_depth_m=asset["water_depth_m"],
                weight_tonnes=asset.get("weight_tonnes", 0.0),
                region=asset.get("region", "gom"),
                year=asset.get("year", 2025),
            )
            results.append(estimate)
        return results

    def total_cost_musd(
        self, estimates: list[DecommissioningCostEstimate]
    ) -> float:
        """Sum estimated costs across all estimates.

        Returns:
            Total cost in MUSD.
        """
        return round(sum(e.estimated_cost_musd for e in estimates), 4)

    def cost_by_region(
        self, estimates: list[DecommissioningCostEstimate]
    ) -> dict[str, float]:
        """Aggregate estimated costs by region.

        Returns:
            Dict mapping region string to total MUSD.
        """
        totals: dict[str, float] = {}
        for est in estimates:
            totals[est.region] = round(
                totals.get(est.region, 0.0) + est.estimated_cost_musd, 4
            )
        return totals

    @classmethod
    def from_calibration(cls, calibration: "DecommissioningCostEstimator") -> "DecommissioningCostEstimator":
        """Create estimator with calibrated cost factors.

        Args:
            calibration: A fitted CostModelCalibration instance.

        Returns:
            DecommissioningCostEstimator with calibrated _COST_FACTORS applied.

        Raises:
            RuntimeError: If calibration.fit() has not been called.
        """
        # Import here to avoid circular import at module level
        from worldenergydata.decommissioning.cost_calibration import (
            CostModelCalibration,
        )

        if not isinstance(calibration, CostModelCalibration):
            raise TypeError(
                f"Expected CostModelCalibration instance, got {type(calibration)!r}"
            )

        fitted = calibration.fitted_factors()
        instance = cls()
        # Monkey-patch the module-level factors for this call chain via a subclass approach
        # We store factors on the instance to allow override in estimate()
        instance._calibrated_factors = fitted  # type: ignore[attr-defined]
        return instance

    def _get_factors(self, asset_type: str) -> dict:
        """Return cost factors, preferring calibrated values if present."""
        calibrated = getattr(self, "_calibrated_factors", None)
        if calibrated and asset_type in calibrated:
            return calibrated[asset_type]
        return _COST_FACTORS[asset_type]
