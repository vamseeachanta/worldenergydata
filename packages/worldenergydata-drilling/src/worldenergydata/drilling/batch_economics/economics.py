# ABOUTME: Core batch drilling economics calculations for WRK-219.
# ABOUTME: Implements learning curve, mobilization allocation, cost comparison, break-even.

"""Batch drilling economics calculator.

Key economic concepts implemented:
- Per-position learning curve: T(N) = T(1) x N^(log(LC)/log(2))
- Mobilization cost amortization across N wells
- Undiscounted batch vs. standalone cost comparison (legacy NPV API)
- Break-even well count for batch justification
- Campaign total cost with summed per-well durations
"""

from __future__ import annotations

import logging
import math

from pydantic import validate_call

from worldenergydata.drilling.batch_economics.models import (
    CampaignInput,
    DrillCampaign,
    FiniteReal,
    LearningFactor,
    NonnegativeReal,
    PositiveInteger,
    PositiveReal,
)

logger = logging.getLogger(__name__)

# Legacy signature default; the cost comparison does not use discount_rate.
_DEFAULT_DISCOUNT_RATE = 0.10


class BatchDrillingEconomics:
    """Core batch drilling economics calculations.

    All methods are stateless and accept parameters directly so the class can
    be instantiated without configuration and used as a calculator.

    Inputs and results are validated at each public call, including current
    campaign state. Durations are positive finite days, rates positive finite
    USD/day, mobilization nonnegative finite USD, factors in (0, 1], and counts
    positive integers. No units are inferred or converted. See
    drilling/docs/input-contracts.md for numeric types and compatibility limits.
    """

    # ------------------------------------------------------------------
    # Learning curve
    # ------------------------------------------------------------------

    @validate_call(validate_return=True)
    def learning_curve_time(
        self,
        base_time_days: PositiveReal,
        well_position: PositiveInteger,
        lc_factor: LearningFactor = 0.85,
    ) -> PositiveReal:
        """Learning-adjusted drilling duration used for the well at position N.

        Applies the existing power law:
            T(N) = T(1) x N^(log(LC) / log(2))

        Cost calculations use T(N) as a per-well duration and sum T(i) over
        the batch. A cumulative-average interpretation would instead give a
        total of N * T(N). This documents current compatibility behavior;
        the learning model and its duration calibration remain unqualified
        (see duration-qualification issue 1342).

        Args:
            base_time_days: Duration of the first well in the batch (days).
            well_position: 1-based position in the drill sequence.
            lc_factor: Learning factor. When the well position doubles, its
                estimated duration is multiplied by this factor.

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

    @validate_call(validate_return=True)
    def mobilization_savings(
        self,
        mob_cost: NonnegativeReal,
        n_wells_batch: PositiveInteger,
        n_wells_standalone: PositiveInteger = 1,
    ) -> NonnegativeReal:
        """Per-well mobilization cost in a batch vs standalone scenario.

        Returns an allocated cost, not a savings difference: the cost is
        shared across n_wells_batch. The standalone count is retained as an
        ignored compatibility argument; it does not change the denominator.

        Args:
            mob_cost: One-time mobilization cost in USD.
            n_wells_batch: Number of wells in the batch sharing this cost.
            n_wells_standalone: Validated positive integer; otherwise ignored.

        Returns:
            Per-well mobilization cost in USD for the batch scenario.
        """
        return mob_cost / n_wells_batch

    # ------------------------------------------------------------------
    # Break-even analysis
    # ------------------------------------------------------------------

    @validate_call(validate_return=True)
    def break_even_n_wells(
        self,
        mob_cost: NonnegativeReal,
        day_rate: PositiveReal,
        base_well_days: PositiveReal,
        lc_factor: LearningFactor = 0.85,
    ) -> int:
        """First strictly cheaper batch size, or a legacy no-savings sentinel.

        Compares undiscounted costs, not revenue, discounted cash flows or
        recovery of an additional investment. Source: drilling knowledge pack,
        agent-pack.md revision 2 (2026), section 3, cost equations and break-even gate:

        Standalone per-well cost = mob_cost + day_rate * base_well_days.
        Batch total cost = mob_cost + day_rate * sum(T(i) for i in 1..N).

        In exact arithmetic, the one-well costs tie. At two wells the saving
        is mob_cost + day_rate * base_well_days * (1 - lc_factor). For positive
        rate/duration, nonnegative mobilization and a factor in (0, 1], either
        positive mobilization or learning therefore gives a threshold of two.
        No learning still saves one mobilization at two wells if mob_cost > 0.
        With zero mobilization and no learning, costs tie at every size.

        Args:
            mob_cost: Mobilization cost in USD.
            day_rate: Rig day rate in USD per day.
            base_well_days: Base drilling duration for the first well (days).
            lc_factor: Per-position learning factor.

        Returns:
            First integer size with strictly lower batch cost in the existing
            bounded search (through 200 wells; pack revision 2, section 3).
            Returns 1 if the search finds none, including zero mobilization
            with no learning. This sentinel does not establish break-even.
            The search bound is a legacy implementation choice, not a sourced
            engineering acceptance limit. Floating-point comparisons are strict;
            no monetary tolerance is applied. Inputs and intermediate costs
            must be finite; overflow raises ValueError before comparison.
        """
        # Accounting basis: OpenStax, Principles of Accounting, Volume 2:
        # Managerial Accounting (2019), section 3.2: fixed plus variable cost.
        # Here mobilization is fixed per batch and drilling cost is rate*time;
        # the strict cost comparison is not the source's revenue break-even.
        standalone_per_well = mob_cost + day_rate * base_well_days
        if not math.isfinite(standalone_per_well):
            raise ValueError("computed standalone cost must be finite")

        for n in range(1, 201):
            batch_drilling_cost = day_rate * sum(
                self.learning_curve_time(base_well_days, pos, lc_factor)
                for pos in range(1, n + 1)
            )
            batch_total = mob_cost + batch_drilling_cost
            standalone_total = n * standalone_per_well
            if not all(map(math.isfinite, (batch_total, standalone_total))):
                raise ValueError("computed campaign costs must be finite")

            if batch_total < standalone_total:
                return n

        # Fallback: effectively no break-even found within 200 wells
        return 1

    # ------------------------------------------------------------------
    # Undiscounted cost comparison (legacy NPV API)
    # ------------------------------------------------------------------

    @validate_call(validate_return=True)
    def batch_vs_standalone_npv(
        self,
        campaign: CampaignInput,
        discount_rate: FiniteReal = _DEFAULT_DISCOUNT_RATE,
    ) -> dict[str, FiniteReal]:
        """Compare positive, undiscounted batch and standalone costs in USD.

        The method name and result keys retain the legacy NPV spelling for
        compatibility. No cash-flow dates, discounting, revenue or negative
        outflow sign convention are applied. The discount_rate argument is
        accepted and ignored; changing it does not change the results.

        Source: OpenStax, Principles of Finance (2022), section 7.3,
        "Methods for Solving Time Value of Money Problems":
        https://openstax.org/books/principles-finance
        Its FV = PV * (1 + r)**n requires a time basis for discounting. This
        API supplies none and reports cost magnitudes rather than a signed NPV.

        Accounting basis: OpenStax, Principles of Accounting, Volume 2:
        Managerial Accounting (2019), section 3.2, fixed plus variable cost.
        The existing drilling adaptation is recorded in the knowledge pack,
        agent-pack.md revision 2 (2026), section 3. Standalone cost is
        N * (mobilization + day_rate * base_days); batch cost is
        mobilization + day_rate * sum(T(i)). Each standalone well pays a full
        mobilization and uses the same unadjusted base duration. Batch durations
        apply the existing learning law at each position. The base duration is
        the existing depth heuristic; its empirical qualification is separate.

        Args:
            campaign: DrillCampaign instance with rig/well parameters.
            discount_rate: Finite dimensionless real of either sign; ignored.
                No discounting interpretation is assigned to it.

        Returns:
            Dict with legacy keys, all in USD:
                batch_npv: Undiscounted batch cost magnitude.
                standalone_npv: Undiscounted standalone cost magnitude.
                batch_savings: standalone_npv - batch_npv; positive means saving.
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

    @validate_call(validate_return=True)
    def campaign_total_cost(
        self,
        campaign: CampaignInput,
        base_days_per_well: PositiveReal,
    ) -> PositiveReal:
        """Undiscounted campaign cost applying learning curve to all wells.

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

        Retains the unqualified heuristic: mean MD / 400 + mean water depth /
        2000 + 10, with a 30-day floor. Campaign validation requires wells;
        no empty-campaign duration is assumed.

        Args:
            campaign: DrillCampaign instance.

        Returns:
            Estimated base well duration in days.
        """
        avg_md_ft = sum(w.planned_md_ft for w in campaign.wells) / len(campaign.wells)
        avg_wd_ft = sum(w.water_depth_ft for w in campaign.wells) / len(campaign.wells)

        # Heuristic: 1 day per 400 ft MD, 1 day per 2000 ft water depth, +10 fixed
        estimated = (avg_md_ft / 400.0) + (avg_wd_ft / 2000.0) + 10.0
        return max(estimated, 30.0)
