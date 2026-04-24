# ABOUTME: WRK-171 cost estimation engine — proxy + calibrated rates with confidence labelling.
# ABOUTME: Supports drilling, completion, and intervention cost estimation. Handles LFS stubs.

"""Cost estimation engine (WRK-171).

Provides proxy-based and calibrated cost estimates for:
- Drilling (day rate × drilling days)
- Completion (day rate × completion days)
- Intervention (day rate × intervention days)
- Combined estimate via ``estimate_with_confidence``

When a ``MultivariateCalibration`` instance is provided, the calibrated model
overrides proxy rates and marks confidence as HIGH.  Without calibration,
proxy rates are used with confidence MEDIUM.  Zero-day inputs (LFS stub
fallback) return LOW-confidence estimates.
"""

from __future__ import annotations

import logging

from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    ConfidenceLevel,
    CostEstimate,
    WellDepthBand,
    classify_water_depth_band,
    classify_well_depth_band,
)
from worldenergydata.bsee.analysis.cost.regional_loader import RegionalCostLoader

logger = logging.getLogger(__name__)

_DEFAULT_COMPLETION_DAYS = 45.0
_DEFAULT_DRILLING_DAYS = 60.0


class CostEngine:
    """Proxy + calibrated cost estimator.

    Args:
        loader: RegionalCostLoader instance providing day-rate database.
        calibration: Optional fitted MultivariateCalibration.  When provided,
            calibrated predictions override proxy rates.
    """

    def __init__(
        self,
        loader: RegionalCostLoader,
        calibration=None,  # Optional[MultivariateCalibration] — avoid circular import
    ) -> None:
        self._loader = loader
        self._calibration = calibration

    # ------------------------------------------------------------------
    # Public API — drilling
    # ------------------------------------------------------------------

    def estimate_drilling_cost(
        self,
        region: str,
        water_depth_m: float,
        well_depth_m: float,
        drilling_days: float,
        year: int,
        hpht: bool = False,
        subsea: bool = True,
    ) -> CostEstimate:
        """Estimate drilling cost.

        Args:
            region: Region key.
            water_depth_m: Water depth in metres.
            well_depth_m: Well TVD in metres.
            drilling_days: Duration of drilling activity in days.
            year: Year of drilling.
            hpht: HPHT flag.
            subsea: Subsea flag.

        Returns:
            CostEstimate with confidence labelled per data availability.
        """
        water_band = classify_water_depth_band(water_depth_m)
        well_band = classify_well_depth_band(well_depth_m)

        if self._calibration is not None and self._calibration.is_fitted:
            cost_mm = self._calibration.predict(
                region=region,
                water_depth_m=water_depth_m,
                well_depth_m=well_depth_m,
                activity_type=ActivityType.DRILLING,
                year=year,
                hpht=hpht,
                subsea=subsea,
            )
            effective_days = max(drilling_days, _DEFAULT_DRILLING_DAYS)
            day_rate = (cost_mm * 1_000_000) / effective_days
            confidence = ConfidenceLevel.HIGH
            source = "calibrated_model"
        else:
            day_rate = self._loader.get_day_rate(
                region=region,
                water_depth_band=water_band,
                activity_type=ActivityType.DRILLING,
                year=year,
                hpht=hpht,
            )
            cost_mm = (day_rate * drilling_days) / 1_000_000
            confidence = ConfidenceLevel.MEDIUM
            source = "proxy_day_rate"

        return CostEstimate(
            activity_type=ActivityType.DRILLING,
            region=region,
            water_depth_band=water_band,
            well_depth_band=well_band,
            cost_usd_mm=round(cost_mm, 4),
            cost_per_day_usd=round(day_rate, 2),
            duration_days=drilling_days,
            confidence=confidence,
            source=source,
            year=year,
        )

    # ------------------------------------------------------------------
    # Public API — completion
    # ------------------------------------------------------------------

    def estimate_completion_cost(
        self,
        region: str,
        water_depth_m: float,
        well_depth_m: float,
        completion_days: float,
        year: int,
        hpht: bool = False,
        subsea: bool = True,
    ) -> CostEstimate:
        """Estimate completion cost.

        Args:
            region: Region key.
            water_depth_m: Water depth in metres.
            well_depth_m: Well TVD in metres.
            completion_days: Duration of completion activity in days.
            year: Year of completion.
            hpht: HPHT flag.
            subsea: Subsea flag.

        Returns:
            CostEstimate with confidence labelled per data availability.
        """
        water_band = classify_water_depth_band(water_depth_m)
        well_band = classify_well_depth_band(well_depth_m)

        if self._calibration is not None and self._calibration.is_fitted:
            cost_mm = self._calibration.predict(
                region=region,
                water_depth_m=water_depth_m,
                well_depth_m=well_depth_m,
                activity_type=ActivityType.COMPLETION,
                year=year,
                hpht=hpht,
                subsea=subsea,
            )
            effective_days = max(completion_days, _DEFAULT_COMPLETION_DAYS)
            day_rate = (cost_mm * 1_000_000) / effective_days
            confidence = ConfidenceLevel.HIGH
            source = "calibrated_model"
        else:
            day_rate = self._loader.get_day_rate(
                region=region,
                water_depth_band=water_band,
                activity_type=ActivityType.COMPLETION,
                year=year,
                hpht=hpht,
            )
            cost_mm = (day_rate * completion_days) / 1_000_000
            confidence = ConfidenceLevel.MEDIUM
            source = "proxy_day_rate"

        return CostEstimate(
            activity_type=ActivityType.COMPLETION,
            region=region,
            water_depth_band=water_band,
            well_depth_band=well_band,
            cost_usd_mm=round(cost_mm, 4),
            cost_per_day_usd=round(day_rate, 2),
            duration_days=completion_days,
            confidence=confidence,
            source=source,
            year=year,
        )

    # ------------------------------------------------------------------
    # Public API — intervention
    # ------------------------------------------------------------------

    def estimate_intervention_cost(
        self,
        region: str,
        water_depth_m: float,
        intervention_days: float,
        year: int,
        workover_type: str = "workover_rig",
    ) -> CostEstimate:
        """Estimate intervention / workover cost.

        Args:
            region: Region key.
            water_depth_m: Water depth in metres.
            intervention_days: Duration in days.
            year: Year of intervention.
            workover_type: Workover category (``"workover_rig"``,
                ``"coiled_tubing"``, ``"wireline"``).

        Returns:
            CostEstimate with MEDIUM confidence (no calibration for intervention).
        """
        water_band = classify_water_depth_band(water_depth_m)
        well_band = WellDepthBand.MEDIUM  # not applicable for intervention

        day_rate = self._loader.get_day_rate(
            region=region,
            water_depth_band=water_band,
            activity_type=ActivityType.INTERVENTION,
            year=year,
            workover_type=workover_type,
        )
        cost_mm = (day_rate * intervention_days) / 1_000_000

        return CostEstimate(
            activity_type=ActivityType.INTERVENTION,
            region=region,
            water_depth_band=water_band,
            well_depth_band=well_band,
            cost_usd_mm=round(cost_mm, 4),
            cost_per_day_usd=round(day_rate, 2),
            duration_days=intervention_days,
            confidence=ConfidenceLevel.MEDIUM,
            source="proxy_day_rate",
            year=year,
        )

    # ------------------------------------------------------------------
    # Public API — combined estimate with LFS stub handling
    # ------------------------------------------------------------------

    def estimate_with_confidence(self, well_data: dict) -> CostEstimate:
        """Estimate total well cost from a well data dict.

        Handles LFS stub inputs: if drilling_days == 0, returns a LOW-confidence
        benchmark estimate using typical durations for the depth.

        Args:
            well_data: Dict with keys: ``region``, ``water_depth_m``,
                ``well_depth_m``, ``drilling_days``, ``completion_days``, ``year``.

        Returns:
            CostEstimate representing combined drilling cost.
        """
        region = str(well_data.get("region", "gom"))
        water_depth_m = float(well_data.get("water_depth_m", 0.0))
        well_depth_m = float(well_data.get("well_depth_m", 0.0))
        drilling_days = float(well_data.get("drilling_days", 0.0))
        year = int(well_data.get("year", 2022))

        # LFS stub — no real duration data
        if drilling_days == 0.0:
            water_band = classify_water_depth_band(water_depth_m)
            well_band = classify_well_depth_band(well_depth_m)
            try:
                day_rate = self._loader.get_day_rate(
                    region=region,
                    water_depth_band=water_band,
                    activity_type=ActivityType.DRILLING,
                    year=year,
                )
            except KeyError:
                day_rate = 200_000.0  # generic fallback
            logger.warning(
                "LFS stub: drilling_days=0 for region=%s depth=%.0fm. "
                "Using benchmark estimate.",
                region,
                water_depth_m,
            )
            # Use 60-day typical duration as low-confidence benchmark
            cost_mm = (day_rate * _DEFAULT_DRILLING_DAYS) / 1_000_000
            return CostEstimate(
                activity_type=ActivityType.DRILLING,
                region=region,
                water_depth_band=water_band,
                well_depth_band=well_band,
                cost_usd_mm=round(cost_mm, 4),
                cost_per_day_usd=round(day_rate, 2),
                duration_days=0.0,
                confidence=ConfidenceLevel.LOW,
                source="benchmark_stub",
                year=year,
                notes="LFS stub: no duration data available",
            )

        return self.estimate_drilling_cost(
            region=region,
            water_depth_m=water_depth_m,
            well_depth_m=well_depth_m,
            drilling_days=drilling_days,
            year=year,
        )
