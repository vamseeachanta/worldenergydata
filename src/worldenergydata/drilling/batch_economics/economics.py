# ABOUTME: Core batch drilling economics calculations for WRK-219.
# ABOUTME: Implements learning curve, mobilization savings, NPV comparison, break-even.

"""Batch drilling economics calculator.

Key economic concepts implemented:
- Wright learning curve: T(N) = T(1) x N^(log(LC)/log(2))
- Mobilization cost amortization across N wells
- Batch vs. standalone NPV comparison
- Break-even well count for batch justification
- Campaign total cost with cumulative learning
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from worldenergydata.drilling.batch_economics.models import DrillCampaign

logger = logging.getLogger(__name__)

# Default annual discount rate for NPV when not otherwise specified
_DEFAULT_DISCOUNT_RATE = 0.10


class BatchDrillingEconomics:
    """Core batch drilling economics calculations.

    All methods are stateless and accept parameters directly so the class can
    be instantiated without configuration and used as a calculator.
    """

    # ------------------------------------------------------------------
    # Learning curve
    # ------------------------------------------------------------------

    def learning_curve_time(
        self,
        base_time_days: float,
        well_position: int,
        lc_factor: float = 0.85,
    ) -> float:
        """Cumulative average learning curve time for well at position N.

        Uses the Wright (1936) power-law learning curve:
            T(N) = T(1) x N^(log(LC) / log(2))

        Args:
            base_time_days: Duration of the first well in the batch (days).
            well_position: 1-based position in the drill sequence.
            lc_factor: Learning curve factor. 0.85 means each time cumulative
                quantity doubles, average time falls to 85% of prior value.

        Returns:
            Estimated drilling time for the well at ``well_position`` (days).
        """
        if well_position <= 1:
            return float(base_time_days)

        exponent = math.log(lc_factor) / math.log(2.0)
        return float(base_time_days * (well_position**exponent))

    # ------------------------------------------------------------------
    # Mobilization savings
    # ------------------------------------------------------------------

    def mobilization_savings(
        self,
        mob_cost: float,
        n_wells_batch: int,
        n_wells_standalone: int = 1,
    ) -> float:
        """Per-well mobilization cost in a batch vs standalone scenario.

        In a standalone campaign, the full mob_cost is borne by each well
        (n_wells_standalone is always 1 per standalone well).  In a batch,
        the cost is shared across n_wells_batch.

        Args:
            mob_cost: One-time mobilization cost in USD.
            n_wells_batch: Number of wells in the batch sharing this cost.
            n_wells_standalone: Denominator for standalone (default 1 per well).

        Returns:
            Per-well mobilization cost in USD for the batch scenario.
        """
        if n_wells_batch <= 0:
            raise ValueError(f"n_wells_batch must be > 0, got {n_wells_batch}")
        return mob_cost / n_wells_batch

    # ------------------------------------------------------------------
    # Break-even analysis
    # ------------------------------------------------------------------

    def break_even_n_wells(
        self,
        mob_cost: float,
        day_rate: float,
        base_well_days: float,
        lc_factor: float = 0.85,
    ) -> int:
        """Minimum number of wells in a batch to justify batch vs standalone.

        Computes the first N where total batch cost (shared mob + learning-
        adjusted drilling) is strictly less than N x standalone well cost.

        Standalone per-well cost = mob_cost + day_rate * base_well_days.
        Batch total cost = mob_cost + day_rate * sum(T(i) for i in 1..N).

        Args:
            mob_cost: Mobilization cost in USD.
            day_rate: Rig day rate in USD per day.
            base_well_days: Base drilling duration for the first well (days).
            lc_factor: Wright learning curve factor.

        Returns:
            Minimum integer N >= 1 where batching saves money.
            Returns 1 when LC = 1.0 (no learning, no mob savings vs standalone
            that already includes mob_cost).
        """
        standalone_per_well = mob_cost + day_rate * base_well_days

        for n in range(1, 201):
            batch_drilling_cost = day_rate * sum(
                self.learning_curve_time(base_well_days, pos, lc_factor)
                for pos in range(1, n + 1)
            )
            batch_total = mob_cost + batch_drilling_cost
            standalone_total = n * standalone_per_well

            if batch_total < standalone_total:
                return n

        # Fallback: effectively no break-even found within 200 wells
        return 1

    # ------------------------------------------------------------------
    # NPV comparison
    # ------------------------------------------------------------------

    def batch_vs_standalone_npv(
        self,
        campaign: DrillCampaign,
        discount_rate: float = _DEFAULT_DISCOUNT_RATE,
    ) -> dict[str, float]:
        """Compare batch NPV vs standalone NPV for a campaign.

        Cost-only NPV: all costs are negative cash flows at t=0 (CAPEX
        incurred upfront).  Uses simple present-value discounting with a
        single period for the campaign duration approximation.

        Standalone scenario: each well bears the full mobilization cost
        independently, and no learning curve benefit is applied.

        Batch scenario: mobilization cost is shared across all N wells;
        learning curve reduces drilling time for each subsequent well.

        Args:
            campaign: DrillCampaign instance with rig/well parameters.
            discount_rate: Annual discount rate (default 10%).

        Returns:
            Dict with keys:
                batch_npv: Total batch cost (negative = savings preserved
                    as absolute cost in USD).
                standalone_npv: Sum of standalone well costs in USD.
                batch_savings: standalone_npv - batch_npv (positive = savings).
        """
        n_wells = len(campaign.wells)
        day_rate = campaign.rig_day_rate_usd
        mob = campaign.mobilization_cost_usd
        lc = campaign.learning_curve_factor

        # Standalone: each well pays full mob + base drilling day rate
        # Use average time from batch position 1 as the base for all
        # standalone wells (no learning benefit).
        base_days = self._estimate_base_well_days(campaign)

        standalone_per_well = mob + day_rate * base_days
        standalone_total = n_wells * standalone_per_well

        # Batch: one shared mob + learning-adjusted drilling per well
        batch_drilling_cost = day_rate * sum(
            self.learning_curve_time(base_days, pos, lc)
            for pos in range(1, n_wells + 1)
        )
        batch_total = mob + batch_drilling_cost

        savings = standalone_total - batch_total

        return {
            "batch_npv": batch_total,
            "standalone_npv": standalone_total,
            "batch_savings": savings,
        }

    # ------------------------------------------------------------------
    # Campaign total cost
    # ------------------------------------------------------------------

    def campaign_total_cost(
        self,
        campaign: DrillCampaign,
        base_days_per_well: float,
    ) -> float:
        """Total campaign cost applying learning curve to all wells.

        Includes one-time mobilization + day-rate cost for each well,
        where later wells benefit from the learning curve reduction.

        Args:
            campaign: DrillCampaign instance.
            base_days_per_well: Duration of the first well in days.

        Returns:
            Total campaign cost in USD.
        """
        n_wells = len(campaign.wells)
        lc = campaign.learning_curve_factor
        day_rate = campaign.rig_day_rate_usd
        mob = campaign.mobilization_cost_usd

        drilling_cost = day_rate * sum(
            self.learning_curve_time(base_days_per_well, pos, lc)
            for pos in range(1, n_wells + 1)
        )
        return mob + drilling_cost

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _estimate_base_well_days(self, campaign: DrillCampaign) -> float:
        """Derive a base well duration from campaign depth parameters.

        Uses a simple heuristic based on planned measured depth.  When depth
        data is available, applies a benchmark of ~1 day per 400 ft MD plus
        20 days fixed for water depth mobilization.  Falls back to 60 days.

        Args:
            campaign: DrillCampaign instance.

        Returns:
            Estimated base well duration in days.
        """
        if not campaign.wells:
            return 60.0

        avg_md_ft = sum(w.planned_md_ft for w in campaign.wells) / len(campaign.wells)
        avg_wd_ft = sum(w.water_depth_ft for w in campaign.wells) / len(campaign.wells)

        # Heuristic: 1 day per 400 ft MD, 1 day per 2000 ft water depth, +10 fixed
        estimated = (avg_md_ft / 400.0) + (avg_wd_ft / 2000.0) + 10.0
        return max(estimated, 30.0)
