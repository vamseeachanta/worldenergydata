"""
FDAS Monthly Cashflow Modeling Engine

Generates monthly cashflow projections including CAPEX, OPEX, revenue,
and royalties for field development economic analysis.

Author: WorldEnergyData Team
Date: 2025-10-03
Source: Ported from FDAS generate_financial_summary.py
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from worldenergydata.common.exceptions import ProcessingError

from ..core.config import AssumptionsManager
from ..fiscal.terms import FiscalTerms


class CashflowError(ProcessingError):
    """Raised when cashflow calculation fails.

    Extends the common ProcessingError for cashflow-specific failures.
    """

    default_code = "FDAS_CASHFLOW_ERROR"

    def __init__(self, message: str, operation: str = "cashflow_calculation", **kwargs):
        super().__init__(message, operation=operation, **kwargs)


@dataclass
class MonthlyCashflowModel:
    """
    Monthly cashflow projection for a field development.

    Attributes:
        year_month: Year-month period
        oil_production_bbl: Oil production volume
        oil_revenue_usd: Gross oil revenue
        royalty_usd: Royalty payments
        variable_opex_usd: Variable operating costs
        fixed_opex_usd: Fixed operating costs
        drilling_capex_usd: Drilling & completion CAPEX
        facilities_capex_usd: Facilities CAPEX
        host_capex_usd: Host platform CAPEX
        net_cashflow_usd: Net cashflow (revenue - costs)
    """

    year_month: str
    oil_production_bbl: float = 0.0
    oil_revenue_usd: float = 0.0
    royalty_usd: float = 0.0
    variable_opex_usd: float = 0.0
    fixed_opex_usd: float = 0.0
    drilling_capex_usd: float = 0.0
    facilities_capex_usd: float = 0.0
    host_capex_usd: float = 0.0
    net_cashflow_usd: float = 0.0

    def calculate_net_cashflow(self) -> float:
        """
        Calculate net cashflow.

        Returns:
            Net cashflow in USD
        """
        revenue = self.oil_revenue_usd
        costs = (
            self.royalty_usd
            + self.variable_opex_usd
            + self.fixed_opex_usd
            + self.drilling_capex_usd
            + self.facilities_capex_usd
            + self.host_capex_usd
        )

        self.net_cashflow_usd = revenue - costs
        return self.net_cashflow_usd


class CashflowEngine:
    """
    Generates monthly cashflow projections for field developments.

    Integrates production forecasts, cost assumptions, and price decks
    to create detailed financial models.
    """

    def __init__(
        self,
        assumptions_mgr: AssumptionsManager,
        dev_system: str = "subsea15",
        fiscal_terms: Optional[FiscalTerms] = None,
    ):
        """
        Initialize cashflow engine.

        Args:
            assumptions_mgr: Assumptions manager with cost parameters
            dev_system: Development system (dry, subsea15, subsea20)
            fiscal_terms: Optional country fiscal-terms deck. When provided, its
                royalty layer supersedes the ``AssumptionsManager`` ROYALTY_RATE
                (see ``calculate_royalty``). ``None`` (the default) preserves the
                exact legacy US-GoM assumptions path — byte-identical behavior.
        """
        self.assumptions = assumptions_mgr
        self.dev_system = dev_system
        self.fiscal_terms = fiscal_terms

    def calculate_host_capex_timing(
        self,
        total_capex_mm: float,
        first_oil_date: datetime,
        months_before_first_oil: int = 24,
    ) -> Dict[str, float]:
        """
        Allocate host platform CAPEX over time.

        Args:
            total_capex_mm: Total host CAPEX in million USD
            first_oil_date: Target first oil date
            months_before_first_oil: Months to spread CAPEX before first oil

        Returns:
            Dictionary mapping year-month to CAPEX amount

        Examples:
            >>> engine = CashflowEngine(assumptions_mgr)
            >>> capex = engine.calculate_host_capex_timing(
            ...     300.0,
            ...     datetime(2025, 1, 1),
            ...     24
            ... )
        """
        if total_capex_mm == 0:
            return {}

        # Distribute evenly over months
        monthly_capex = total_capex_mm / months_before_first_oil

        timing = {}
        current = first_oil_date
        for i in range(months_before_first_oil):
            # Go backwards from first oil
            month = current.replace(day=1)
            month_key = month.strftime("%Y-%m")
            timing[month_key] = monthly_capex

            # Move back one month
            if month.month == 1:
                current = month.replace(year=month.year - 1, month=12)
            else:
                current = month.replace(month=month.month - 1)

        return timing

    def calculate_drilling_capex(
        self, drilling_days_monthly: Dict[str, float], rig_rate_mm_per_day: float
    ) -> Dict[str, float]:
        """
        Calculate drilling CAPEX from drilling days.

        Args:
            drilling_days_monthly: Dict mapping year-month to drilling days
            rig_rate_mm_per_day: Rig rate in million USD per day

        Returns:
            Dictionary mapping year-month to drilling CAPEX

        Examples:
            >>> engine = CashflowEngine(assumptions_mgr)
            >>> capex = engine.calculate_drilling_capex(
            ...     {'2024-01': 30, '2024-02': 28},
            ...     0.8
            ... )
        """
        capex = {}
        for month, days in drilling_days_monthly.items():
            capex[month] = days * rig_rate_mm_per_day

        return capex

    def calculate_facilities_capex(
        self, completion_dates_monthly: Dict[str, int], surf_per_well_mm: float
    ) -> Dict[str, float]:
        """
        Calculate subsea facilities CAPEX.

        Args:
            completion_dates_monthly: Dict mapping year-month to well count
            surf_per_well_mm: SURF cost per well in million USD

        Returns:
            Dictionary mapping year-month to facilities CAPEX

        Examples:
            >>> engine = CashflowEngine(assumptions_mgr)
            >>> capex = engine.calculate_facilities_capex(
            ...     {'2024-06': 2, '2024-12': 1},
            ...     8.0
            ... )
        """
        capex = {}
        for month, well_count in completion_dates_monthly.items():
            capex[month] = well_count * surf_per_well_mm

        return capex

    def calculate_revenue(
        self,
        oil_production_monthly: Dict[str, float],
        wti_price_monthly: Dict[str, float],
        oil_differential: float = 0.0,
    ) -> Dict[str, float]:
        """
        Calculate oil revenue.

        Args:
            oil_production_monthly: Dict mapping year-month to BBL
            wti_price_monthly: Dict mapping year-month to $/BBL
            oil_differential: Price differential from WTI (USD/BBL)

        Returns:
            Dictionary mapping year-month to revenue

        Examples:
            >>> engine = CashflowEngine(assumptions_mgr)
            >>> revenue = engine.calculate_revenue(
            ...     {'2024-01': 100000},
            ...     {'2024-01': 75.0},
            ...     -2.0
            ... )
        """
        revenue = {}
        for month, production in oil_production_monthly.items():
            wti_price = wti_price_monthly.get(month, 75.0)
            realized_price = wti_price + oil_differential
            revenue[month] = production * realized_price

        return revenue

    def calculate_royalty(
        self, revenue_monthly: Dict[str, float], royalty_rate: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate royalty payments.

        Royalty-rate resolution precedence (highest first):
            1. explicit ``royalty_rate`` argument;
            2. ``self.fiscal_terms`` deck, if set — ``flat`` model resolves the
               per-dev-system rate, ``none`` resolves to 0.0;
            3. the legacy ``AssumptionsManager`` ROYALTY_RATE path (deckless =
               byte-identical to the pre-carve behavior).

        Args:
            revenue_monthly: Dict mapping year-month to revenue
            royalty_rate: Royalty rate (overrides deck/assumptions if given)

        Returns:
            Dictionary mapping year-month to royalty

        Examples:
            >>> engine = CashflowEngine(assumptions_mgr)
            >>> royalty = engine.calculate_royalty(
            ...     {'2024-01': 7500000},
            ...     0.188
            ... )
        """
        if royalty_rate is None:
            if self.fiscal_terms is not None:
                royalty_rate = self.fiscal_terms.royalty.rate_for(self.dev_system)
            else:
                royalty_rate = self.assumptions.get(
                    self.dev_system, "ROYALTY_RATE", 0.188
                )

        royalty = {}
        for month, revenue in revenue_monthly.items():
            royalty[month] = revenue * royalty_rate

        return royalty

    def calculate_variable_opex(
        self,
        oil_production_monthly: Dict[str, float],
        opex_per_bbl: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Calculate variable operating expenses.

        Args:
            oil_production_monthly: Dict mapping year-month to BBL
            opex_per_bbl: OPEX in $/BBL (uses assumption if None)

        Returns:
            Dictionary mapping year-month to variable OPEX

        Examples:
            >>> engine = CashflowEngine(assumptions_mgr)
            >>> opex = engine.calculate_variable_opex({'2024-01': 100000}, 12.0)
        """
        if opex_per_bbl is None:
            opex_per_bbl = self.assumptions.get(
                self.dev_system, "VARIABLE_OPEX_$/BBL", 12.0
            )

        opex = {}
        for month, production in oil_production_monthly.items():
            opex[month] = production * opex_per_bbl

        return opex

    def calculate_fixed_opex(
        self,
        first_production_month: str,
        last_production_month: str,
        annual_fixed_opex_mm: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Calculate fixed operating expenses.

        Args:
            first_production_month: First month of production
            last_production_month: Last month of production
            annual_fixed_opex_mm: Annual fixed OPEX in million USD

        Returns:
            Dictionary mapping year-month to fixed OPEX

        Examples:
            >>> engine = CashflowEngine(assumptions_mgr)
            >>> opex = engine.calculate_fixed_opex('2024-01', '2026-12', 25.0)
        """
        if annual_fixed_opex_mm is None:
            annual_fixed_opex_mm = self.assumptions.get(
                self.dev_system, "FIXED_OPEX_MM_PER_YEAR", 25.0
            )

        monthly_fixed = annual_fixed_opex_mm / 12.0

        # Generate month range
        start = pd.to_datetime(first_production_month)
        end = pd.to_datetime(last_production_month)
        months = pd.period_range(start, end, freq="M")

        opex = {}
        for month in months:
            opex[str(month)] = monthly_fixed

        return opex

    def generate_monthly_cashflow(
        self,
        production_monthly: pd.DataFrame,
        drilling_timeline: Dict[str, any],
        wti_prices: Dict[str, float],
        first_oil_date: datetime,
    ) -> List[MonthlyCashflowModel]:
        """
        Generate complete monthly cashflow projection.

        Args:
            production_monthly: Monthly production DataFrame
            drilling_timeline: Drilling/completion timeline dict
            wti_prices: WTI price deck
            first_oil_date: First oil date

        Returns:
            List of MonthlyCashflowModel objects

        Examples:
            >>> engine = CashflowEngine(assumptions_mgr, 'subsea15')
            >>> cashflow = engine.generate_monthly_cashflow(
            ...     production_df,
            ...     timeline,
            ...     wti_prices,
            ...     datetime(2025, 1, 1)
            ... )
        """
        # Extract parameters from assumptions
        host_capex_mm = self.assumptions.get(self.dev_system, "HOST_CAPEX_MM")
        self.assumptions.get(self.dev_system, "SURF_PER_WELL_MM")
        rig_rate_mm = self.assumptions.get(self.dev_system, "MODU_LOADED_DAYRATE_MM")

        # Calculate CAPEX timing
        host_capex_monthly = self.calculate_host_capex_timing(
            host_capex_mm, first_oil_date
        )

        drilling_capex_monthly = self.calculate_drilling_capex(
            drilling_timeline.get("drilling_monthly", {}), rig_rate_mm
        )

        # Convert production to dict (ensure string keys)
        prod_dict = {
            str(k): v
            for k, v in production_monthly.set_index("YEAR_MONTH")["MONTHLY_OIL_BBL"]
            .to_dict()
            .items()
        }

        # Calculate revenue and costs
        revenue_monthly = self.calculate_revenue(prod_dict, wti_prices)
        royalty_monthly = self.calculate_royalty(revenue_monthly)
        variable_opex_monthly = self.calculate_variable_opex(prod_dict)

        # Get date range (all keys as strings)
        months = sorted(
            set(
                list(prod_dict.keys())
                + list(host_capex_monthly.keys())
                + list(drilling_capex_monthly.keys())
            )
        )

        # Build cashflow models
        cashflows = []
        for month in months:
            cf = MonthlyCashflowModel(
                year_month=month,
                oil_production_bbl=prod_dict.get(month, 0.0),
                oil_revenue_usd=revenue_monthly.get(month, 0.0),
                royalty_usd=royalty_monthly.get(month, 0.0),
                variable_opex_usd=variable_opex_monthly.get(month, 0.0),
                fixed_opex_usd=0.0,  # Would be calculated from production period
                drilling_capex_usd=drilling_capex_monthly.get(month, 0.0),
                facilities_capex_usd=0.0,
                host_capex_usd=host_capex_monthly.get(month, 0.0),
            )
            cf.calculate_net_cashflow()
            cashflows.append(cf)

        return cashflows


def generate_monthly_cashflow(
    production_df: pd.DataFrame,
    assumptions_mgr: AssumptionsManager,
    dev_system: str = "subsea15",
    **kwargs,
) -> pd.DataFrame:
    """
    Convenience function to generate monthly cashflow.

    Args:
        production_df: Monthly production data
        assumptions_mgr: Assumptions manager
        dev_system: Development system
        **kwargs: Additional parameters

    Returns:
        DataFrame with monthly cashflow

    Examples:
        >>> cashflow_df = generate_monthly_cashflow(
        ...     production_df,
        ...     assumptions_mgr,
        ...     'subsea15'
        ... )
    """
    engine = CashflowEngine(assumptions_mgr, dev_system)

    # Extract required parameters from kwargs
    drilling_timeline = kwargs.get("drilling_timeline", {})
    wti_prices = kwargs.get("wti_prices", {})
    first_oil_date = kwargs.get("first_oil_date", datetime.now())

    cashflows = engine.generate_monthly_cashflow(
        production_df, drilling_timeline, wti_prices, first_oil_date
    )

    # Convert to DataFrame
    return pd.DataFrame([vars(cf) for cf in cashflows])
