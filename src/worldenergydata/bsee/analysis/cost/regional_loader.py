# ABOUTME: WRK-171 regional cost profile loader for the day-rate YAML database.
# ABOUTME: Reads config/analysis/cost_data/day_rates.yml and provides year-interpolated
# ABOUTME: rate lookups by region, water_depth_band, and activity_type.

"""Regional cost profile loader (WRK-171).

Reads ``config/analysis/cost_data/day_rates.yml`` and exposes:

- ``get_day_rate(region, water_depth_band, activity_type, year)`` — point lookup
- ``get_all_rates(year)`` — flat dict of all cells for a given year
- ``available_regions()`` — list of known region keys
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    ConfidenceLevel,
    WaterDepthBand,
)

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_DIR = (
    Path(__file__).parents[7] / "config" / "analysis" / "cost_data"
)

_HPHT_PREMIUM_DEFAULT = 1.30

# Map WaterDepthBand enum values to YAML keys
_BAND_KEY = {
    WaterDepthBand.SHALLOW: "shallow",
    WaterDepthBand.MID: "mid",
    WaterDepthBand.DEEP: "deep",
    WaterDepthBand.ULTRA_DEEP: "ultra_deep",
}

_ACTIVITY_KEY = {
    ActivityType.DRILLING: "drilling",
    ActivityType.COMPLETION: "completion",
    ActivityType.INTERVENTION: "intervention",
}

_DEFAULT_WORKOVER_TYPE = "workover_rig"


class RegionalCostLoader:
    """Load and query the day-rate database from YAML.

    Args:
        config_dir: Directory containing ``day_rates.yml``.  Defaults to
            ``config/analysis/cost_data/`` relative to the project root.

    Raises:
        FileNotFoundError: If ``day_rates.yml`` is not found.
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self._config_dir = Path(config_dir) if config_dir else _DEFAULT_CONFIG_DIR
        self._rates: dict = {}
        self._hpht_premium: float = _HPHT_PREMIUM_DEFAULT
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_day_rate(
        self,
        region: str,
        water_depth_band: WaterDepthBand,
        activity_type: ActivityType,
        year: int,
        hpht: bool = False,
        workover_type: str = _DEFAULT_WORKOVER_TYPE,
    ) -> float:
        """Return day rate (USD/day) for the given cell.

        Interpolates linearly between the two nearest indexed years.

        Args:
            region: Region key (e.g. ``"gom"``, ``"north_sea"``).
            water_depth_band: Water depth classification.
            activity_type: Activity category.
            year: Year for which to return the rate.
            hpht: If True, apply HPHT premium.
            workover_type: Sub-key for intervention rates
                (``"workover_rig"``, ``"coiled_tubing"``, ``"wireline"``).

        Returns:
            Day rate in USD/day.

        Raises:
            KeyError: If region is not in the database.
        """
        if region not in self._rates:
            raise KeyError(
                f"unknown_region {region!r}. "
                f"Available: {sorted(self._rates.keys())}"
            )

        region_data = self._rates[region]
        activity_key = _ACTIVITY_KEY[activity_type]
        band_key = _BAND_KEY[water_depth_band]

        activity_data = region_data.get(activity_key, {})

        if activity_type == ActivityType.INTERVENTION:
            cell = activity_data.get(workover_type, {})
        else:
            cell = activity_data.get(band_key, {})

        rate = self._interpolate_year(cell, year)
        if hpht:
            rate = rate * self._hpht_premium
        return rate

    def available_regions(self) -> list[str]:
        """Return sorted list of region keys in the database."""
        return sorted(self._rates.keys())

    def get_all_rates(self, year: int) -> dict[str, float]:
        """Return flat dict of all rate cells for a given year.

        Key format: ``"{region}__{activity}__{band}"``

        Args:
            year: Year for interpolation.

        Returns:
            Dict of rate cells.
        """
        result: dict[str, float] = {}
        for region in self._rates:
            for activity_type in (
                ActivityType.DRILLING,
                ActivityType.COMPLETION,
            ):
                for band in WaterDepthBand:
                    try:
                        rate = self.get_day_rate(
                            region=region,
                            water_depth_band=band,
                            activity_type=activity_type,
                            year=year,
                        )
                        key = f"{region}__{activity_type.value}__{band.value}"
                        result[key] = rate
                    except (KeyError, ValueError):
                        pass
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load and parse day_rates.yml."""
        path = self._config_dir / "day_rates.yml"
        if not path.exists():
            raise FileNotFoundError(
                f"day_rates.yml not found at {path}. "
                "Ensure config/analysis/cost_data/ is present."
            )
        with open(path, "r") as fh:
            data = yaml.safe_load(fh)

        meta = data.get("metadata", {})
        self._hpht_premium = float(
            meta.get("hpht_premium_factor", _HPHT_PREMIUM_DEFAULT)
        )
        self._rates = data.get("regions", {})
        logger.debug(
            "Loaded %d regions from %s", len(self._rates), path
        )

    @staticmethod
    def _interpolate_year(cell: dict, year: int) -> float:
        """Interpolate (or extrapolate) a year-indexed rate dict.

        Args:
            cell: Dict with integer year keys mapping to day rates.
            year: Target year.

        Returns:
            Interpolated rate.

        Raises:
            ValueError: If cell has no numeric year keys.
        """
        # Collect (year, rate) pairs, ignoring non-integer keys like "confidence"
        pairs = sorted(
            (int(k), float(v))
            for k, v in cell.items()
            if isinstance(k, int) or (isinstance(k, str) and k.isdigit())
        )
        if not pairs:
            raise ValueError(f"Cell has no year-indexed rates: {cell}")

        years, rates = zip(*pairs)

        if year <= years[0]:
            return float(rates[0])
        if year >= years[-1]:
            return float(rates[-1])

        # Linear interpolation between bracketing years
        for i in range(len(years) - 1):
            if years[i] <= year <= years[i + 1]:
                frac = (year - years[i]) / (years[i + 1] - years[i])
                return float(rates[i] + frac * (rates[i + 1] - rates[i]))

        return float(rates[-1])  # fallback — unreachable
