"""
Norwegian NPV calculation module.

This module implements Net Present Value calculations specifically for
Norwegian petroleum fiscal regime, including petroleum tax, uplift, and
depreciation rules.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import numpy_financial as npf
import pandas as pd

logger = logging.getLogger(__name__)


class TaxRegime(Enum):
    """Norwegian tax regimes"""

    PETROLEUM_TAX = "petroleum_tax"  # Standard petroleum tax system
    SPECIAL_TAX = "special_tax"  # Special petroleum tax
    TEMPORARY_TAX = "temporary_tax"  # Temporary tax changes


@dataclass
class NorwegianFinancialParameters:
    """Financial parameters for Norwegian NPV calculations"""

    # Discount rate
    discount_rate: float = 0.08

    # Tax rates (Norwegian petroleum tax system)
    petroleum_tax_rate: float = (
        0.78  # Total petroleum tax rate (special tax + corporate tax)
    )
    corporate_tax_rate: float = 0.22  # Standard corporate tax
    special_tax_rate: float = 0.56  # Additional special petroleum tax

    # Uplift parameters (investment incentive)
    uplift_rate: float = 0.056  # Annual uplift rate (5.6%)
    uplift_years: int = 4  # Number of years for uplift

    # Depreciation
    depreciation_years: int = 6  # Linear depreciation over 6 years
    depreciation_method: str = "linear"

    # Working interest and revenue interest
    working_interest: float = 1.0  # Ownership share
    net_revenue_interest: float = (
        1.0  # Revenue share after royalties (Norway has no royalties)
    )

    # Price assumptions
    oil_price_usd: float = 80.0  # USD per barrel
    gas_price_nok_per_sm3: float = 2.5  # NOK per standard cubic meter
    nok_usd_rate: float = 10.0  # Exchange rate NOK/USD

    # Operating costs
    opex_per_boe: float = 15.0  # USD per BOE
    abandonment_cost_pct: float = 0.10  # % of CAPEX for abandonment

    # Capital costs
    capex_schedule: List[float] = field(default_factory=list)  # Million USD by year

    # Inflation
    inflation_rate: float = 0.02

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "discount_rate": self.discount_rate,
            "petroleum_tax_rate": self.petroleum_tax_rate,
            "corporate_tax_rate": self.corporate_tax_rate,
            "special_tax_rate": self.special_tax_rate,
            "uplift_rate": self.uplift_rate,
            "uplift_years": self.uplift_years,
            "depreciation_years": self.depreciation_years,
            "working_interest": self.working_interest,
            "oil_price_usd": self.oil_price_usd,
            "gas_price_nok_per_sm3": self.gas_price_nok_per_sm3,
            "nok_usd_rate": self.nok_usd_rate,
            "opex_per_boe": self.opex_per_boe,
            "capex_schedule": self.capex_schedule,
        }


@dataclass
class CashFlowResult:
    """Results from cash flow analysis"""

    npv: float  # Net Present Value
    irr: Optional[float]  # Internal Rate of Return
    payback_period: Optional[float]  # Years to payback
    cash_flows: pd.DataFrame  # Detailed cash flows by year
    tax_payments: pd.DataFrame  # Tax payment schedule
    metrics: Dict[str, float]  # Additional metrics

    def summary(self) -> Dict[str, Any]:
        """Get summary of results"""
        return {
            "npv_mmusd": self.npv,
            "irr_pct": self.irr * 100 if self.irr else None,
            "payback_years": self.payback_period,
            "total_revenue": self.cash_flows["revenue"].sum(),
            "total_opex": self.cash_flows["opex"].sum(),
            "total_capex": self.cash_flows["capex"].sum(),
            "total_tax": self.tax_payments["total_tax"].sum(),
            "profit_to_investment_ratio": self.metrics.get("pi_ratio", 0),
        }


class NorwayNPVCalculator:
    """NPV calculator for Norwegian petroleum projects"""

    def __init__(self, params: NorwegianFinancialParameters):
        """
        Initialize NPV calculator.

        Args:
            params: Financial parameters for calculations
        """
        self.params = params
        self.tax_regime = TaxRegime.PETROLEUM_TAX

    def calculate_npv(
        self,
        production_profile: pd.DataFrame,
        capex_schedule: Optional[List[float]] = None,
        opex_override: Optional[pd.DataFrame] = None,
    ) -> CashFlowResult:
        """
        Calculate NPV for a Norwegian petroleum project.

        Args:
            production_profile: DataFrame with oil and gas production by year
            capex_schedule: Capital expenditure schedule (optional, uses params if not provided)
            opex_override: Optional DataFrame with custom OPEX by year

        Returns:
            CashFlowResult with NPV and detailed cash flows
        """
        # Use provided capex or from parameters
        if capex_schedule is None:
            capex_schedule = self.params.capex_schedule

        # Calculate revenues
        revenue_df = self.calculate_revenue(production_profile)

        # Calculate operating costs
        if opex_override is not None:
            opex_df = opex_override
        else:
            opex_df = self.calculate_opex(production_profile)

        # Build capex dataframe
        capex_df = self._build_capex_dataframe(capex_schedule, len(production_profile))

        # Calculate depreciation
        depreciation_df = self.calculate_depreciation(capex_df)

        # Calculate uplift
        uplift_df = self.calculate_uplift_schedule(capex_df)

        # Calculate taxable income
        taxable_income = (
            revenue_df["total_revenue"]
            - opex_df["total_opex"]
            - depreciation_df["depreciation"]
        )

        # Apply uplift deduction
        taxable_income_after_uplift = taxable_income - uplift_df["uplift"]

        # Calculate taxes
        tax_df = self.calculate_tax_schedule(taxable_income_after_uplift)

        # Calculate free cash flow
        fcf = (
            revenue_df["total_revenue"]
            - opex_df["total_opex"]
            - capex_df["capex"]
            - tax_df["total_tax"]
        )

        # Apply working interest
        fcf = fcf * self.params.working_interest

        # Build complete cash flow dataframe
        cash_flows = pd.DataFrame(
            {
                "year": production_profile.get("year", range(len(production_profile))),
                "revenue": revenue_df["total_revenue"],
                "opex": opex_df["total_opex"],
                "capex": capex_df["capex"],
                "depreciation": depreciation_df["depreciation"],
                "uplift": uplift_df["uplift"],
                "taxable_income": taxable_income_after_uplift,
                "taxes": tax_df["total_tax"],
                "free_cash_flow": fcf,
            }
        )

        # Calculate NPV
        npv = self._calculate_npv_from_cashflows(fcf, self.params.discount_rate)

        # Calculate IRR
        try:
            # For IRR calculation, we need to include initial investment as negative cash flow
            # If capex is spread over multiple years, it's already in the fcf
            # But if we need an initial outlay, we should prepend it
            irr_cashflows = fcf.values

            # Check if we have negative cash flows (investments) and positive ones (returns)
            has_negative = any(cf < 0 for cf in irr_cashflows)
            has_positive = any(cf > 0 for cf in irr_cashflows)

            if has_negative and has_positive and len(irr_cashflows) > 1:
                irr = npf.irr(irr_cashflows)
                if np.isnan(irr) or np.isinf(irr):
                    irr = None
            else:
                irr = None
        except Exception:
            irr = None

        # Calculate payback period
        payback = self._calculate_payback(fcf)

        # Calculate additional metrics
        metrics = {
            "pi_ratio": self._calculate_profitability_index(
                fcf, capex_df["capex"].sum()
            ),
            "breakeven_oil_price": self._calculate_breakeven_price(
                production_profile, cash_flows
            ),
            "government_take": (
                tax_df["total_tax"].sum() / revenue_df["total_revenue"].sum()
                if revenue_df["total_revenue"].sum() > 0
                else 0
            ),
        }

        return CashFlowResult(
            npv=npv,
            irr=irr,
            payback_period=payback,
            cash_flows=cash_flows,
            tax_payments=tax_df,
            metrics=metrics,
        )

    def calculate_revenue(self, production_profile: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate revenue from production.

        Args:
            production_profile: Production by year

        Returns:
            DataFrame with revenue calculations
        """
        revenue = pd.DataFrame()

        # Oil revenue
        if "oil_production_mmbbl" in production_profile:
            revenue["oil_revenue"] = (
                production_profile["oil_production_mmbbl"]
                * self.params.oil_price_usd
                * 1e6  # Million to actual barrels
            )
        else:
            revenue["oil_revenue"] = 0

        # Gas revenue
        if "gas_production_bcf" in production_profile:
            # Convert BCF to billion Sm3 (1 BCF ≈ 0.0283 billion Sm3)
            gas_bsm3 = production_profile["gas_production_bcf"] * 0.0283

            # Calculate revenue in NOK then convert to USD
            gas_revenue_nok = gas_bsm3 * self.params.gas_price_nok_per_sm3 * 1e9
            revenue["gas_revenue"] = gas_revenue_nok / self.params.nok_usd_rate
        else:
            revenue["gas_revenue"] = 0

        # Total revenue
        revenue["total_revenue"] = revenue["oil_revenue"] + revenue["gas_revenue"]

        # Apply net revenue interest
        revenue["total_revenue"] = (
            revenue["total_revenue"] * self.params.net_revenue_interest
        )

        return revenue

    def calculate_opex(self, production_profile: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate operating expenses.

        Args:
            production_profile: Production profile

        Returns:
            DataFrame with OPEX calculations
        """
        opex = pd.DataFrame()

        # Calculate BOE
        boe = 0
        if "oil_production_mmbbl" in production_profile:
            boe += production_profile["oil_production_mmbbl"]
        if "gas_production_bcf" in production_profile:
            boe += production_profile["gas_production_bcf"] / 6  # Gas to BOE conversion

        # Calculate OPEX
        opex["production_opex"] = boe * self.params.opex_per_boe * 1e6

        # Add fixed costs (simplified - could be more detailed)
        opex["fixed_costs"] = 50 * 1e6  # $50MM per year fixed costs

        # Total OPEX
        opex["total_opex"] = opex["production_opex"] + opex["fixed_costs"]

        # Apply inflation
        years = range(len(production_profile))
        inflation_factor = [(1 + self.params.inflation_rate) ** year for year in years]
        opex["total_opex"] = opex["total_opex"] * inflation_factor

        return opex

    def calculate_taxes(self, taxable_income: float) -> Dict[str, float]:
        """
        Calculate Norwegian petroleum taxes.

        Args:
            taxable_income: Taxable income in USD

        Returns:
            Dictionary with tax components
        """
        taxes = {}

        # Corporate tax (22%)
        taxes["corporate_tax"] = taxable_income * self.params.corporate_tax_rate

        # Special petroleum tax (56% after corporate tax deduction)
        # The special tax is calculated on income after corporate tax
        special_tax_base = taxable_income * (1 - self.params.corporate_tax_rate)
        taxes["petroleum_tax"] = special_tax_base * self.params.special_tax_rate

        # Total tax
        taxes["total_tax"] = taxes["corporate_tax"] + taxes["petroleum_tax"]

        # Effective tax rate (should be ~78%)
        taxes["effective_rate"] = (
            taxes["total_tax"] / taxable_income if taxable_income > 0 else 0
        )

        return taxes

    def calculate_uplift(self, capex: float) -> List[float]:
        """
        Calculate uplift (investment allowance) for Norwegian tax.

        Args:
            capex: Capital expenditure

        Returns:
            List of uplift values by year
        """
        annual_uplift = capex * self.params.uplift_rate
        return [annual_uplift] * self.params.uplift_years

    def calculate_uplift_schedule(self, capex_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate complete uplift schedule.

        Args:
            capex_df: Capital expenditure dataframe

        Returns:
            DataFrame with uplift schedule
        """
        uplift_schedule = pd.DataFrame(index=capex_df.index, columns=["uplift"])
        uplift_schedule["uplift"] = 0.0

        for idx, capex in enumerate(capex_df["capex"]):
            if capex > 0:
                uplift_values = self.calculate_uplift(capex)
                for j, uplift in enumerate(uplift_values):
                    if idx + j < len(uplift_schedule):
                        uplift_schedule.iloc[idx + j, 0] += uplift

        return uplift_schedule

    def calculate_depreciation(self, capex_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate depreciation schedule.

        Args:
            capex_df: Capital expenditure dataframe

        Returns:
            DataFrame with depreciation schedule
        """
        depreciation_schedule = pd.DataFrame(
            index=capex_df.index, columns=["depreciation"]
        )
        depreciation_schedule["depreciation"] = 0.0

        if self.params.depreciation_method == "linear":
            annual_depreciation_rate = 1.0 / self.params.depreciation_years

            for idx, capex in enumerate(capex_df["capex"]):
                if capex > 0:
                    annual_depreciation = capex * annual_depreciation_rate
                    for j in range(self.params.depreciation_years):
                        if idx + j < len(depreciation_schedule):
                            depreciation_schedule.iloc[
                                idx + j, 0
                            ] += annual_depreciation

        return depreciation_schedule

    def calculate_tax_schedule(self, taxable_income: pd.Series) -> pd.DataFrame:
        """
        Calculate tax schedule for all years.

        Args:
            taxable_income: Taxable income by year

        Returns:
            DataFrame with tax calculations
        """
        tax_df = pd.DataFrame()

        # Calculate taxes for each year
        corporate_tax = []
        petroleum_tax = []
        total_tax = []

        for income in taxable_income:
            if income > 0:
                taxes = self.calculate_taxes(income)
                corporate_tax.append(taxes["corporate_tax"])
                petroleum_tax.append(taxes["petroleum_tax"])
                total_tax.append(taxes["total_tax"])
            else:
                # Tax loss carry forward (simplified)
                corporate_tax.append(0)
                petroleum_tax.append(0)
                total_tax.append(0)

        tax_df["corporate_tax"] = corporate_tax
        tax_df["petroleum_tax"] = petroleum_tax
        tax_df["total_tax"] = total_tax

        return tax_df

    def sensitivity_analysis(
        self,
        production_profile: pd.DataFrame,
        parameters: List[str] = None,
        variations: List[float] = None,
    ) -> Dict[str, List[float]]:
        """
        Perform sensitivity analysis on NPV.

        Args:
            production_profile: Production profile
            parameters: Parameters to vary
            variations: Percentage variations (-20, -10, 0, 10, 20)

        Returns:
            Dictionary with NPV values for each parameter variation
        """
        if parameters is None:
            parameters = ["oil_price", "discount_rate", "opex", "capex"]

        if variations is None:
            variations = [-20, -10, 0, 10, 20]

        results = {}

        # Store original values
        original_params = {
            "oil_price": self.params.oil_price_usd,
            "discount_rate": self.params.discount_rate,
            "opex": self.params.opex_per_boe,
            "capex": (
                self.params.capex_schedule.copy() if self.params.capex_schedule else []
            ),
        }

        for param in parameters:
            npv_values = []

            for variation in variations:
                # Apply variation
                if param == "oil_price":
                    self.params.oil_price_usd = original_params["oil_price"] * (
                        1 + variation / 100
                    )
                elif param == "discount_rate":
                    self.params.discount_rate = original_params["discount_rate"] * (
                        1 + variation / 100
                    )
                elif param == "opex":
                    self.params.opex_per_boe = original_params["opex"] * (
                        1 + variation / 100
                    )
                elif param == "capex" and original_params["capex"]:
                    self.params.capex_schedule = [
                        c * (1 + variation / 100) for c in original_params["capex"]
                    ]

                # Calculate NPV
                result = self.calculate_npv(production_profile)
                npv_values.append(result.npv)

                # Reset parameter
                if param == "oil_price":
                    self.params.oil_price_usd = original_params["oil_price"]
                elif param == "discount_rate":
                    self.params.discount_rate = original_params["discount_rate"]
                elif param == "opex":
                    self.params.opex_per_boe = original_params["opex"]
                elif param == "capex":
                    self.params.capex_schedule = original_params["capex"].copy()

            results[param] = npv_values

        return results

    def _build_capex_dataframe(
        self, capex_schedule: List[float], num_years: int
    ) -> pd.DataFrame:
        """Build capex dataframe from schedule"""
        capex_df = pd.DataFrame({"capex": [0.0] * num_years})

        for i, capex in enumerate(capex_schedule[:num_years]):
            capex_df.iloc[i, 0] = capex

        return capex_df

    def _calculate_npv_from_cashflows(
        self, cash_flows: pd.Series, discount_rate: float
    ) -> float:
        """Calculate NPV from cash flow series"""
        npv = 0
        for i, cf in enumerate(cash_flows):
            npv += cf / ((1 + discount_rate) ** i)
        return npv

    def _calculate_payback(self, cash_flows: pd.Series) -> Optional[float]:
        """Calculate payback period"""
        cumulative = cash_flows.cumsum()
        positive_periods = cumulative[cumulative > 0]

        if len(positive_periods) > 0:
            return positive_periods.index[0]
        return None

    def _calculate_profitability_index(
        self, cash_flows: pd.Series, total_capex: float
    ) -> float:
        """Calculate profitability index (PI)"""
        if total_capex == 0:
            return 0

        pv_benefits = self._calculate_npv_from_cashflows(
            cash_flows[cash_flows > 0], self.params.discount_rate
        )

        return pv_benefits / total_capex

    def _calculate_breakeven_price(
        self, production_profile: pd.DataFrame, cash_flows: pd.DataFrame
    ) -> float:
        """Calculate breakeven oil price (simplified)"""
        # This is a simplified calculation
        # A more sophisticated approach would use iteration

        total_oil = production_profile.get("oil_production_mmbbl", pd.Series([0])).sum()

        if total_oil == 0:
            return 0

        # Calculate total costs (OPEX + CAPEX + taxes at current price)
        total_costs = (
            cash_flows["opex"].sum()
            + cash_flows["capex"].sum()
            + cash_flows["taxes"].sum()
        )

        # Breakeven price
        breakeven = total_costs / (total_oil * 1e6)

        return breakeven
