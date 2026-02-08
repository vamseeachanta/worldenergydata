"""
SME Financial Analysis Cash Flow Calculator

This module implements the cash flow calculation logic from SME Roy's V20 implementation,
adapted to work with the worldenergydata module structure.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

import numpy as np
import pandas as pd

# Import from comprehensive reports module

logger = logging.getLogger(__name__)


class DevelopmentType(Enum):
    """Development type enumeration"""

    SUBSEA = "subsea"
    DRY_TREE = "dry_tree"


@dataclass
class FinancialParameters:
    """
    Financial parameters for cash flow calculations
    Matches V20 assumptions structure
    """

    # Price parameters
    wti_base_price: float = 75.0  # $/bbl

    # Tax and royalty rates
    royalty_rate: float = 0.0  # As percentage (0.1875 = 18.75%)
    severance_tax_rate: float = 0.0  # As percentage
    corporate_tax_rate: float = 0.21  # 21%

    # Operating costs
    subsea_opex_per_bbl: float = 16.0  # $/bbl for subsea
    dry_opex_per_bbl: float = 10.0  # $/bbl for dry tree
    fixed_opex_usd_monthly: float = 0.0  # Fixed monthly operating cost

    # Drilling and completion dayrates
    modu_dayrate_usd: float = 250000.0  # MODU (subsea) dayrate
    dry_dayrate_usd: float = 150000.0  # Dry tree dayrate

    # Facilities costs (in millions)
    host_subsea_mm: float = 0.0
    host_dry_mm: float = 0.0
    surf_per_well_mm: float = 0.0
    subsea_pump_mm: float = 0.0
    dry_well_system_per_producer_mm: float = 0.0

    # Timing parameters
    host_prefo_months: int = 24  # Months before first oil for host
    surf_prefo_months: int = 12  # Months before first oil for SURF

    # Discount and finance rates (annual)
    discount_rate_annual: float = 0.10
    mirr_finance_rate_annual: float = 0.10
    mirr_reinvest_rate_annual: float = 0.10

    def get_monthly_discount_rate(self) -> float:
        """Convert annual discount rate to monthly"""
        return (1.0 + self.discount_rate_annual) ** (1.0 / 12.0) - 1.0

    def get_monthly_finance_rate(self) -> float:
        """Convert annual finance rate to monthly"""
        return (1.0 + self.mirr_finance_rate_annual) ** (1.0 / 12.0) - 1.0

    def get_monthly_reinvest_rate(self) -> float:
        """Convert annual reinvest rate to monthly"""
        return (1.0 + self.mirr_reinvest_rate_annual) ** (1.0 / 12.0) - 1.0


class CashFlowCalculator:
    """
    Calculate monthly cash flows for oil and gas development projects
    Based on SME Roy's V20 implementation
    """

    def __init__(self, params: Optional[FinancialParameters] = None):
        """
        Initialize calculator

        Args:
            params: Financial parameters for calculations
        """
        self.params = params or FinancialParameters()
        self.wti_prices = {}  # Month -> price mapping

    def set_wti_prices(self, price_map: Dict[pd.Timestamp, float]):
        """
        Set monthly WTI prices

        Args:
            price_map: Dictionary mapping months to WTI prices
        """
        self.wti_prices = price_map

    def calculate_monthly_cash_flow(
        self,
        production_df: pd.DataFrame,
        drilling_data: Dict[str, Dict[str, Dict[pd.Timestamp, float]]],
        development_type: DevelopmentType,
        first_oil_date: Optional[pd.Timestamp] = None,
        producer_count: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Calculate monthly cash flows for a development

        Args:
            production_df: DataFrame with production volumes by well and month
            drilling_data: Nested dict of well -> {'drill_days': {month: days}, 'comp_days': {month: days}}
            development_type: Type of development (subsea or dry tree)
            first_oil_date: Date of first oil production
            producer_count: Number of producing wells

        Returns:
            DataFrame with monthly cash flow components
        """
        # Determine date range
        dates = self._get_date_range(production_df, drilling_data)

        # Initialize result dataframe
        result = pd.DataFrame(index=dates)
        result.index.name = "YearMonth"

        # Add production data
        if not production_df.empty:
            oil_cols = [c for c in production_df.columns if c != "YearMonth"]
            result = result.join(production_df[oil_cols], how="left")
            result[oil_cols] = result[oil_cols].fillna(0.0)
        else:
            oil_cols = []

        # Calculate gross oil
        result["Gross_Oil_bbls"] = result[oil_cols].sum(axis=1) if oil_cols else 0.0

        # Calculate WTI price for each month
        result["WTI_Price"] = result.index.map(
            lambda m: self.wti_prices.get(m, self.params.wti_base_price)
        )

        # Calculate revenue
        result["Revenue_Gross"] = result["Gross_Oil_bbls"] * result["WTI_Price"]
        royalty_amt = result["Revenue_Gross"] * self.params.royalty_rate
        severance_amt = result["Revenue_Gross"] * self.params.severance_tax_rate
        result["Revenue_Adjustments"] = 0.0
        result["Revenue_Net"] = (
            result["Revenue_Gross"]
            - royalty_amt
            - severance_amt
            + result["Revenue_Adjustments"]
        )

        # Calculate OPEX
        var_opex_rate = (
            self.params.subsea_opex_per_bbl
            if development_type == DevelopmentType.SUBSEA
            else self.params.dry_opex_per_bbl
        )
        result["OPEX_Var"] = result["Gross_Oil_bbls"] * var_opex_rate
        result["OPEX_Fixed"] = self.params.fixed_opex_usd_monthly
        result["OPEX"] = result["OPEX_Var"] + result["OPEX_Fixed"]

        # Calculate drilling and completion CAPEX
        result["DRILL_DAYS_TOT"] = 0.0
        result["COMP_DAYS_TOT"] = 0.0

        for well, data in drilling_data.items():
            drill_days = data.get("drill_days", {})
            comp_days = data.get("comp_days", {})

            for month, days in drill_days.items():
                if month in result.index:
                    result.loc[month, "DRILL_DAYS_TOT"] += days

            for month, days in comp_days.items():
                if month in result.index:
                    result.loc[month, "COMP_DAYS_TOT"] += days

        # Calculate drilling and completion CAPEX based on dayrates
        result["CAPEX_Drill"] = 0.0
        result["CAPEX_Comp"] = 0.0

        for month in result.index:
            # Determine which dayrate to use
            if development_type == DevelopmentType.SUBSEA:
                dayrate = self.params.modu_dayrate_usd
            else:
                # For dry tree, use MODU before first oil, then dry rate
                if first_oil_date and month < first_oil_date:
                    dayrate = self.params.modu_dayrate_usd
                else:
                    dayrate = self.params.dry_dayrate_usd

            result.loc[month, "CAPEX_Drill"] = (
                result.loc[month, "DRILL_DAYS_TOT"] * dayrate
            )
            result.loc[month, "CAPEX_Comp"] = (
                result.loc[month, "COMP_DAYS_TOT"] * dayrate
            )

        # Calculate facilities CAPEX
        result["CAPEX_Facilities"] = 0.0

        if first_oil_date and producer_count:
            self._allocate_facilities_capex(
                result, development_type, first_oil_date, producer_count
            )

        # Calculate total CAPEX
        result["CAPEX"] = (
            result["CAPEX_Drill"] + result["CAPEX_Comp"] + result["CAPEX_Facilities"]
        )

        # Calculate after-tax values
        result["CAPEX_Drill_Net"] = result["CAPEX_Drill"] * (
            1.0 - self.params.corporate_tax_rate
        )
        result["CAPEX_Comp_Net"] = result["CAPEX_Comp"] * (
            1.0 - self.params.corporate_tax_rate
        )
        result["CAPEX_Facilities_Net"] = result["CAPEX_Facilities"] * (
            1.0 - self.params.corporate_tax_rate
        )
        result["Tax_Savings"] = result["CAPEX"] * self.params.corporate_tax_rate

        # Calculate net cash flow
        result["Net_Cash_Flow"] = (
            result["Revenue_Net"]
            - result["OPEX"]
            - result["CAPEX"]
            + result["Tax_Savings"]
        )
        result["Cum_Cash_Flow"] = result["Net_Cash_Flow"].cumsum()

        return result

    def _get_date_range(
        self,
        production_df: pd.DataFrame,
        drilling_data: Dict[str, Dict[str, Dict[pd.Timestamp, float]]],
    ) -> pd.DatetimeIndex:
        """
        Determine the date range for cash flow calculations

        Args:
            production_df: Production dataframe
            drilling_data: Drilling and completion data

        Returns:
            DatetimeIndex covering all relevant dates
        """
        dates = []

        # Add production dates
        if not production_df.empty and production_df.index.name == "YearMonth":
            dates.extend(production_df.index.tolist())

        # Add drilling and completion dates
        for well_data in drilling_data.values():
            if "drill_days" in well_data:
                dates.extend(well_data["drill_days"].keys())
            if "comp_days" in well_data:
                dates.extend(well_data["comp_days"].keys())

        if dates:
            min_date = min(dates)
            max_date = max(dates)
            return pd.date_range(min_date, max_date, freq="MS")
        else:
            # Default to a single month if no data
            return pd.date_range("2020-01-01", periods=1, freq="MS")

    def _allocate_facilities_capex(
        self,
        result: pd.DataFrame,
        development_type: DevelopmentType,
        first_oil_date: pd.Timestamp,
        producer_count: int,
    ):
        """
        Allocate facilities CAPEX across appropriate months

        Args:
            result: Result dataframe to update
            development_type: Type of development
            first_oil_date: First oil date
            producer_count: Number of producers
        """
        # Host facility allocation
        if development_type == DevelopmentType.SUBSEA:
            host_usd = self.params.host_subsea_mm * 1_000_000
        else:
            host_usd = self.params.host_dry_mm * 1_000_000

        if host_usd > 0:
            total_months = max(self.params.host_prefo_months + 6, 1)
            start_date = first_oil_date - pd.DateOffset(months=total_months)
            end_date = first_oil_date - pd.DateOffset(months=1)
            window = pd.date_range(start_date, end_date, freq="MS")

            if len(window) > 0:
                per_month = host_usd / len(window)
                for month in window:
                    if month in result.index:
                        result.loc[month, "CAPEX_Facilities"] += per_month

        # SURF allocation (subsea only)
        if development_type == DevelopmentType.SUBSEA:
            surf_total_usd = self.params.surf_per_well_mm * 1_000_000 * producer_count

            # Add injector wells (1 per 7 producers for subsea)
            injector_count = producer_count // 7 if producer_count >= 7 else 0
            if injector_count > 0:
                surf_total_usd += (
                    injector_count * self.params.surf_per_well_mm * 1_000_000
                )

            if surf_total_usd > 0 and self.params.surf_prefo_months > 0:
                start_date = first_oil_date - pd.DateOffset(
                    months=self.params.surf_prefo_months
                )
                end_date = first_oil_date - pd.DateOffset(months=1)
                window = pd.date_range(start_date, end_date, freq="MS")

                if len(window) > 0:
                    per_month = surf_total_usd / len(window)
                    for month in window:
                        if month in result.index:
                            result.loc[month, "CAPEX_Facilities"] += per_month

            # Subsea pumps (1 per 8 producers)
            pump_count = producer_count // 8 if producer_count >= 8 else 0
            if pump_count > 0:
                pump_total_usd = pump_count * self.params.subsea_pump_mm * 1_000_000

                if pump_total_usd > 0 and self.params.surf_prefo_months > 0:
                    # Use same window as SURF for simplicity
                    start_date = first_oil_date - pd.DateOffset(
                        months=self.params.surf_prefo_months
                    )
                    end_date = first_oil_date - pd.DateOffset(months=1)
                    window = pd.date_range(start_date, end_date, freq="MS")

                    if len(window) > 0:
                        per_month = pump_total_usd / len(window)
                        for month in window:
                            if month in result.index:
                                result.loc[month, "CAPEX_Facilities"] += per_month

        # Dry well systems (dry tree only)
        elif development_type == DevelopmentType.DRY_TREE:
            dry_sys_per_prod_usd = (
                self.params.dry_well_system_per_producer_mm * 1_000_000
            )

            if dry_sys_per_prod_usd > 0 and producer_count > 0:
                total_dry_sys = dry_sys_per_prod_usd * producer_count

                # Allocate 12 months before first oil
                start_date = first_oil_date - pd.DateOffset(months=12)
                end_date = first_oil_date - pd.DateOffset(months=1)
                window = pd.date_range(start_date, end_date, freq="MS")

                if len(window) > 0:
                    per_month = total_dry_sys / len(window)
                    for month in window:
                        if month in result.index:
                            result.loc[month, "CAPEX_Facilities"] += per_month

    def calculate_financial_metrics(
        self, cash_flow_df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calculate financial metrics from cash flow dataframe

        Args:
            cash_flow_df: DataFrame with monthly cash flows

        Returns:
            Dictionary of financial metrics
        """
        metrics = {}

        # Production and revenue metrics
        metrics["total_oil_bbls"] = float(cash_flow_df["Gross_Oil_bbls"].sum())
        metrics["total_revenue"] = float(cash_flow_df["Revenue_Gross"].sum())
        metrics["net_revenue"] = float(cash_flow_df["Revenue_Net"].sum())

        # Cost metrics
        metrics["total_opex"] = float(cash_flow_df["OPEX"].sum())
        metrics["total_capex"] = float(cash_flow_df["CAPEX"].sum())
        metrics["total_capex_drill"] = float(cash_flow_df["CAPEX_Drill"].sum())
        metrics["total_capex_comp"] = float(cash_flow_df["CAPEX_Comp"].sum())
        metrics["total_capex_facilities"] = float(
            cash_flow_df["CAPEX_Facilities"].sum()
        )

        # Calculate NPV
        cash_flows = cash_flow_df["Net_Cash_Flow"].values.astype(float)
        monthly_rate = self.params.get_monthly_discount_rate()
        metrics["npv"] = calculate_npv(cash_flows, monthly_rate)

        # Calculate MIRR
        finance_rate = self.params.get_monthly_finance_rate()
        reinvest_rate = self.params.get_monthly_reinvest_rate()
        mirr_monthly = calculate_mirr(cash_flows, finance_rate, reinvest_rate)

        if np.isfinite(mirr_monthly):
            metrics["mirr_monthly"] = mirr_monthly
            metrics["mirr_annual"] = (1.0 + mirr_monthly) ** 12 - 1.0
        else:
            metrics["mirr_monthly"] = np.nan
            metrics["mirr_annual"] = np.nan

        return metrics


def calculate_npv(cash_flows: np.ndarray, monthly_rate: float) -> float:
    """
    Calculate NPV from monthly cash flows

    Args:
        cash_flows: Array of monthly cash flows
        monthly_rate: Monthly discount rate

    Returns:
        Net present value
    """
    if cash_flows.size == 0:
        return 0.0

    periods = np.arange(cash_flows.size)
    discount_factors = (1.0 + monthly_rate) ** periods
    return float(np.sum(cash_flows / discount_factors))


def calculate_mirr(
    cash_flows: np.ndarray, finance_rate: float, reinvest_rate: float
) -> float:
    """
    Calculate MIRR from monthly cash flows

    Args:
        cash_flows: Array of monthly cash flows
        finance_rate: Monthly finance rate for negative flows
        reinvest_rate: Monthly reinvestment rate for positive flows

    Returns:
        Modified internal rate of return (monthly)
    """
    n = cash_flows.size
    if n <= 1:
        return np.nan

    # Separate positive and negative cash flows
    positive_flows = cash_flows.copy()
    positive_flows[positive_flows < 0] = 0.0

    negative_flows = cash_flows.copy()
    negative_flows[negative_flows > 0] = 0.0

    # Calculate future value of positive flows
    fv_positive = 0.0
    for t in range(n):
        if positive_flows[t] > 0:
            fv_positive += positive_flows[t] * ((1.0 + reinvest_rate) ** (n - 1 - t))

    # Calculate present value of negative flows
    pv_negative = 0.0
    for t in range(n):
        if negative_flows[t] < 0:
            pv_negative += negative_flows[t] / ((1.0 + finance_rate) ** t)

    # Check for valid MIRR calculation
    if pv_negative >= 0 or fv_positive <= 0:
        return np.nan

    # Calculate MIRR
    mirr_monthly = (fv_positive / -pv_negative) ** (1.0 / (n - 1)) - 1.0
    return mirr_monthly
