# ABOUTME: WRK-019 — integrate cost layer with field data pipeline outputs.
# ABOUTME: Bridges FieldReport pipeline outputs to CostEngine + FieldCostSummary.

"""Cost layer integration with the field data pipeline (WRK-019).

Provides :class:`FieldPipelineCostIntegrator` which consumes a
:class:`~worldenergydata.bsee.pipeline.pipeline_runner.FieldReport` produced by
the pipeline and returns a
:class:`~worldenergydata.bsee.analysis.cost.cost_summary.FieldCostSummary`.

Region and depth parameters are inferred from the ``FieldContext`` embedded in
the report.  When ``production_summary`` contains a ``WATER_DEPTH_AVG`` column
that value is used directly; otherwise default depths are applied per region.

LFS stub inputs (empty production DataFrames) are handled gracefully: the
integrator falls back to defaults and produces a LOW-confidence summary.

Public API
----------
- :class:`FieldPipelineCostIntegrator` — main integration class
- :func:`_infer_region` — derive region key from area_code / field_name
- :func:`_default_water_depth_m` — canonical water depth defaults by region
- :func:`_default_well_depth_m` — canonical well depth defaults by region
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from worldenergydata.bsee.analysis.cost.cost_engine import CostEngine
from worldenergydata.bsee.analysis.cost.cost_summary import (
    FieldCostSummary,
    summarize_field_costs,
)
from worldenergydata.bsee.analysis.cost.models import CostEstimate
from worldenergydata.bsee.pipeline.pipeline_runner import FieldReport

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Region inference constants
# ---------------------------------------------------------------------------

# OCS area codes that indicate Gulf of Mexico
_GOM_AREA_CODES = frozenset({"GC", "MC", "AT", "WR", "EB", "GB", "GP", "SS"})

# Field name keywords that suggest North Sea (case-insensitive)
_NORTH_SEA_KEYWORDS = ("oseberg", "troll", "ekofisk", "statfjord", "gullfaks")

# Area code substrings mapped to region keys
_AREA_CODE_REGION_MAP = {
    "PERMIAN": "permian",
    "EAGLE": "eagle_ford",
    "BAKKEN": "north_sea",  # fallback — not modelled separately
}

# ---------------------------------------------------------------------------
# Default depth parameters by region (metres)
# ---------------------------------------------------------------------------

_REGION_WATER_DEPTH_DEFAULTS: dict[str, float] = {
    "gom": 1500.0,          # representative deepwater GOM
    "north_sea": 150.0,      # representative UKCS / NCS mid-water
    "brazil": 2000.0,        # pre-salt deepwater
    "west_africa": 1200.0,   # typical deepwater West Africa
    "asia_pacific": 80.0,    # mostly shallow / jackup
    "permian": 0.0,          # onshore
    "eagle_ford": 0.0,       # onshore
}

_REGION_WELL_DEPTH_DEFAULTS: dict[str, float] = {
    "gom": 7500.0,           # representative deepwater TD ~25 000 ft
    "north_sea": 4000.0,     # typical NCS well depth
    "brazil": 6000.0,        # pre-salt well depth
    "west_africa": 5000.0,
    "asia_pacific": 3000.0,
    "permian": 3500.0,       # typical Permian lateral/TVD
    "eagle_ford": 3000.0,
}

_DEFAULT_REGION = "gom"
_DEFAULT_WATER_DEPTH_M = 1500.0
_DEFAULT_WELL_DEPTH_M = 7500.0
_DEFAULT_DRILLING_DAYS = 60.0
_DEFAULT_COMPLETION_DAYS = 45.0
_DEFAULT_INTERVENTION_DAYS = 14.0


# ---------------------------------------------------------------------------
# Helper functions (public for testability)
# ---------------------------------------------------------------------------


def _infer_region(area_code: str, field_name: str) -> str:
    """Infer a region key from BSEE area code and field name.

    Resolution order:
    1. Known OCS area codes -> ``"gom"``
    2. Area code substring match against ``_AREA_CODE_REGION_MAP``
    3. Field name keywords -> ``"north_sea"``
    4. Default -> ``"gom"``

    Args:
        area_code: OCS area code from :class:`FieldContext`.
        field_name: Human-readable field name from :class:`FieldContext`.

    Returns:
        Region key compatible with :class:`~RegionalCostLoader`.
    """
    code_upper = area_code.strip().upper()

    if code_upper in _GOM_AREA_CODES:
        return "gom"

    for fragment, region in _AREA_CODE_REGION_MAP.items():
        if fragment in code_upper:
            return region

    field_lower = field_name.lower()
    for keyword in _NORTH_SEA_KEYWORDS:
        if keyword in field_lower:
            return "north_sea"

    return _DEFAULT_REGION


def _default_water_depth_m(region: str) -> float:
    """Return representative water depth in metres for *region*.

    Args:
        region: Region key.

    Returns:
        Depth in metres. 0.0 for onshore regions.
    """
    return _REGION_WATER_DEPTH_DEFAULTS.get(region, _DEFAULT_WATER_DEPTH_M)


def _default_well_depth_m(region: str) -> float:
    """Return representative well TVD in metres for *region*.

    Args:
        region: Region key.

    Returns:
        Well TVD in metres.
    """
    return _REGION_WELL_DEPTH_DEFAULTS.get(region, _DEFAULT_WELL_DEPTH_M)


# ---------------------------------------------------------------------------
# FieldPipelineCostIntegrator
# ---------------------------------------------------------------------------


class FieldPipelineCostIntegrator:
    """Integrate cost layer with field data pipeline outputs.

    Accepts a :class:`~worldenergydata.bsee.pipeline.pipeline_runner.FieldReport`
    and produces a :class:`~worldenergydata.bsee.analysis.cost.cost_summary.FieldCostSummary`
    by calling the :class:`~worldenergydata.bsee.analysis.cost.cost_engine.CostEngine`
    once per wellbore for drilling, completion, and (optionally) intervention.

    Args:
        engine: Configured :class:`CostEngine` instance.
        include_intervention: If ``True``, add one intervention estimate per
            well using default workover type.  Defaults to ``False`` (most
            fields do not have intervention data in the pipeline today).
    """

    def __init__(
        self,
        engine: CostEngine,
        include_intervention: bool = False,
    ) -> None:
        self._engine = engine
        self._include_intervention = include_intervention

    def get_field_cost_summary(
        self,
        report: FieldReport,
        year: int = 2022,
    ) -> FieldCostSummary:
        """Produce a :class:`FieldCostSummary` from a pipeline :class:`FieldReport`.

        The method:
        1. Infers region from ``report.context.area_code`` and ``field_name``.
        2. Extracts water depth from ``production_summary`` (``WATER_DEPTH_AVG``
           column) when available; otherwise uses region defaults.
        3. Calls ``CostEngine.estimate_drilling_cost`` and
           ``estimate_completion_cost`` once per wellbore.
        4. Optionally calls ``estimate_intervention_cost`` per well.
        5. Aggregates via ``summarize_field_costs`` into a ``FieldCostSummary``.

        Args:
            report: Populated (or partially populated) ``FieldReport``.
            year: Reference year for day-rate lookup.

        Returns:
            ``FieldCostSummary`` with per-field cost roll-up.
        """
        ctx = report.context
        region = _infer_region(ctx.area_code, ctx.field_name)

        water_depth_m = self._resolve_water_depth(
            report.production_summary, region
        )
        well_depth_m = _default_well_depth_m(region)
        n_wells = max(report.wellbore_count, 0)

        logger.debug(
            "Cost integration: field=%s region=%s wells=%d "
            "water_depth=%.0fm well_depth=%.0fm year=%d",
            ctx.field_name,
            region,
            n_wells,
            water_depth_m,
            well_depth_m,
            year,
        )

        drilling_estimates: list[CostEstimate] = []
        completion_estimates: list[CostEstimate] = []
        intervention_estimates: list[CostEstimate] = []

        for _ in range(n_wells):
            drilling_estimates.append(
                self._engine.estimate_drilling_cost(
                    region=region,
                    water_depth_m=water_depth_m,
                    well_depth_m=well_depth_m,
                    drilling_days=_DEFAULT_DRILLING_DAYS,
                    year=year,
                )
            )
            completion_estimates.append(
                self._engine.estimate_completion_cost(
                    region=region,
                    water_depth_m=water_depth_m,
                    well_depth_m=well_depth_m,
                    completion_days=_DEFAULT_COMPLETION_DAYS,
                    year=year,
                )
            )
            if self._include_intervention:
                intervention_estimates.append(
                    self._engine.estimate_intervention_cost(
                        region=region,
                        water_depth_m=water_depth_m,
                        intervention_days=_DEFAULT_INTERVENTION_DAYS,
                        year=year,
                    )
                )

        return summarize_field_costs(
            field_name=ctx.field_name,
            region=region,
            drilling_estimates=drilling_estimates,
            completion_estimates=completion_estimates,
            intervention_estimates=intervention_estimates,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_water_depth(
        production_summary: pd.DataFrame,
        region: str,
    ) -> float:
        """Extract water depth from production summary or return region default.

        Args:
            production_summary: ``FieldReport.production_summary`` DataFrame.
            region: Region key for fallback default.

        Returns:
            Water depth in metres.
        """
        if not production_summary.empty and "WATER_DEPTH_AVG" in production_summary.columns:
            value = production_summary["WATER_DEPTH_AVG"].iloc[0]
            try:
                depth = float(value)
                if depth > 0.0:
                    return depth
            except (TypeError, ValueError):
                pass

        return _default_water_depth_m(region)
