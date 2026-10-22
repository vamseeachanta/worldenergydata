# ABOUTME: Core batch drilling economics calculations for WRK-219.
# ABOUTME: Implements learning curve, mobilization savings, NPV comparison, break-even.

"""Batch drilling costs using the individual-duration power law.

Source: NASA, Guidelines for Application of Learning/Cost Improvement Curves
(1975), sections IV.A-B, VII.B formulas 1-2, printed pp. 6-7 and 15:
https://ntrs.nasa.gov/api/citations/19760006882/downloads/19760006882.pdf

T(N) = T1 * N**e, e = log(LC)/log(2), is an individual-unit duration here.
For the cumulative-average reading, the same ordinate is A(N), so total time
is N*A(N), not sum(A(i)). Cost methods retain the individual-unit reading.
The source establishes the mathematical form, not drilling applicability or
calibration. T1 (days) and LC (fraction per doubling) are required assumptions.
Depth coefficients are also required; no public drilling calibration has been
established. See models.py for the finite-input contract and
../docs/campaign-contracts.md for independent hand calculations and limits.
"""

from __future__ import annotations

import math

from worldenergydata.drilling.batch_economics.models import (
    DrillCampaign,
    LearningFactor,
    NonnegativeReal,
    PositiveReal,
    WellCount,
    validate_inputs,
)


class BatchDrillingEconomics:
    """Core batch drilling economics calculations.

    All methods are stateless and accept parameters directly so the class can
    be instantiated without configuration and used as a calculator.
    """

    # ------------------------------------------------------------------
    # Learning curve
    # ------------------------------------------------------------------

    @validate_inputs
    def learning_curve_time(
        self,
        base_time_days: PositiveReal,
        well_position: WellCount,
        lc_factor: LearningFactor,
    ) -> float:
        """Individual duration at the one-based position, in days.

        NASA (1975), IV.B and VII.B formulas 1-2: unit-time power law.
        The factor defines T(2*N)/T(N); solving 2**e=LC gives e=log2(LC).
        It is required and has no empirically calibrated drilling default.
        Interpreting this ordinate as a cumulative average instead would
        require N*T(N) for the cumulative total, not summing these ordinates.
        """
        if well_position == 1:
            return float(base_time_days)

        # NASA (1975), VII.B.1-2; base 2 follows the doubling definition.
        exponent = math.log(lc_factor) / math.log(2.0)
        return float(base_time_days * (well_position**exponent))

    # ------------------------------------------------------------------
    # Mobilization savings
    # ------------------------------------------------------------------

    @validate_inputs
    def mobilization_savings(
        self,
        mob_cost: NonnegativeReal,
        n_wells_batch: WellCount,
        n_wells_standalone: WellCount = 1,
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
        return mob_cost / n_wells_batch

    # ------------------------------------------------------------------
    # Break-even analysis
    # ------------------------------------------------------------------

    @validate_inputs
    def break_even_n_wells(
        self,
        mob_cost: NonnegativeReal,
        day_rate: PositiveReal,
        base_well_days: PositiveReal,
        lc_factor: LearningFactor,
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
            lc_factor: Required individual-duration learning factor.

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

    @validate_inputs
    def batch_vs_standalone_npv(
        self,
        campaign: DrillCampaign,
        discount_rate: NonnegativeReal | None = None,
        *,
        base_days_per_well: PositiveReal,
    ) -> dict[str, float]:
        """Compare undiscounted batch and standalone costs in USD.

        The legacy NPV names are retained; no cashflow schedule or discounting
        is applied. A supplied discount_rate is validated but remains unused.
        base_days_per_well is required, replacing the unqualified automatic
        depth heuristic. Standalone pays mobilization per well and no learning;
        batch pays it once and sums individual learning-adjusted durations.
        Outputs are batch_npv, standalone_npv and their difference batch_savings.
        """
        n_wells = len(campaign.wells)
        day_rate = campaign.rig_day_rate_usd
        mob = campaign.mobilization_cost_usd
        lc = campaign.learning_curve_factor

        # Standalone: each well pays full mob + base drilling day rate
        # Supplied first-well duration is also the no-learning standalone base.
        base_days = base_days_per_well

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

    @validate_inputs
    def campaign_total_cost(
        self,
        campaign: DrillCampaign,
        base_days_per_well: PositiveReal,
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

    @validate_inputs
    def _estimate_base_well_days(
        self,
        campaign: DrillCampaign,
        *,
        md_ft_per_day: PositiveReal,
        water_depth_ft_per_day: PositiveReal,
        fixed_days: NonnegativeReal,
        minimum_days: NonnegativeReal,
    ) -> float:
        """Evaluate an explicitly assumed depth-duration model in days.

        Retains the previous arithmetic, now with required coefficients:
        max(mean_MD / md_ft_per_day + mean_WD / water_depth_ft_per_day
            + fixed_days, minimum_days).

        The previous denominators, fixed term and floor have no established
        public calibration. They are no longer defaults. The former prose
        described a different fixed term from the arithmetic; this expression
        states the actual addition. No empty-campaign fallback is allowed.
        The comparison API takes an explicit base duration instead of invoking
        this heuristic. This helper only evaluates caller assumptions.
        """
        avg_md_ft = sum(w.planned_md_ft for w in campaign.wells) / len(campaign.wells)
        avg_wd_ft = sum(w.water_depth_ft for w in campaign.wells) / len(campaign.wells)
        estimated = (
            avg_md_ft / md_ft_per_day + avg_wd_ft / water_depth_ft_per_day + fixed_days
        )
        return max(estimated, minimum_days)
