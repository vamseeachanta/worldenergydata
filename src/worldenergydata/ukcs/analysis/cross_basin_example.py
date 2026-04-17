"""Cross-basin NPV comparison: UKCS vs NCS vs GoM.

Compares post-tax NPV sensitivity across three fiscal regimes using mock
production profiles for representative fields:
  - Forties (UKCS / Apache) — UK RFCT+SC+EPL regime
  - Edvard Grieg (NCS / Lundin) — Norwegian 78% regime with 71.8% uplift
  - Generic GoM field — US GOM royalty + federal income tax regime

All production profiles and economics are synthetic/mock — no live data.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from worldenergydata.ukcs.analysis.field_economics import UKFiscalRegime

logger = logging.getLogger(__name__)

# ── Norwegian fiscal constants ────────────────────────────────────────────────
NCS_CORPORATE_TAX_RATE: float = 0.22
NCS_SPECIAL_TAX_RATE: float = 0.56  # Special petroleum tax
NCS_UPLIFT_RATE: float = 0.718  # Uplift allowance offsets special tax base

# ── GoM fiscal constants ──────────────────────────────────────────────────────
GOM_ROYALTY_RATE: float = 0.1875  # 18.75% standard deepwater royalty
GOM_FEDERAL_TAX_RATE: float = 0.21  # US federal corporate tax


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class BasinProfile:
    """Mock production and cost profile for a single field."""

    name: str
    basin: str
    monthly_production_bbl: List[float]
    oil_price_usd_bbl: float
    capex_mm_usd: float
    opex_per_bbl_usd: float
    fiscal_regime: str  # "ukcs" | "ncs" | "gom"

    @property
    def n_months(self) -> int:
        return len(self.monthly_production_bbl)


@dataclass
class ComparisonResult:
    """Results from a cross-basin NPV comparison."""

    npv_by_basin: Dict[str, float]
    government_take_by_basin: Dict[str, float]
    npv_sensitivity: Dict[str, Dict[str, float]]

    def summary(self) -> str:
        lines = ["Cross-Basin NPV Comparison (USD millions)"]
        lines.append("-" * 50)
        for basin, npv in self.npv_by_basin.items():
            gov_take = self.government_take_by_basin.get(basin, 0.0)
            lines.append(
                f"  {basin:<20} NPV: {npv/1e6:>8.1f} MM  " f"Gov take: {gov_take:.1%}"
            )
        return "\n".join(lines)


# ── Mock profiles ─────────────────────────────────────────────────────────────


def _make_exponential_profile(
    qi_bbl_per_month: float, d: float, n_months: int
) -> List[float]:
    t = np.arange(n_months)
    return list(qi_bbl_per_month * np.exp(-d * t))


MOCK_FORTIES_PROFILE = BasinProfile(
    name="Forties",
    basin="UKCS",
    monthly_production_bbl=_make_exponential_profile(
        qi_bbl_per_month=1_200_000.0, d=0.012, n_months=120
    ),
    oil_price_usd_bbl=75.0,
    capex_mm_usd=800.0,
    opex_per_bbl_usd=18.0,
    fiscal_regime="ukcs",
)

MOCK_EDVARD_GRIEG_PROFILE = BasinProfile(
    name="Edvard Grieg",
    basin="NCS",
    monthly_production_bbl=_make_exponential_profile(
        qi_bbl_per_month=1_000_000.0, d=0.010, n_months=120
    ),
    oil_price_usd_bbl=75.0,
    capex_mm_usd=900.0,
    opex_per_bbl_usd=15.0,
    fiscal_regime="ncs",
)

MOCK_GOM_FIELD_PROFILE = BasinProfile(
    name="GoM Deepwater",
    basin="GoM",
    monthly_production_bbl=_make_exponential_profile(
        qi_bbl_per_month=900_000.0, d=0.015, n_months=120
    ),
    oil_price_usd_bbl=75.0,
    capex_mm_usd=1_200.0,
    opex_per_bbl_usd=22.0,
    fiscal_regime="gom",
)


# ── Comparator ────────────────────────────────────────────────────────────────


class CrossBasinComparator:
    """Compute post-fiscal NPV and government-take for multiple basins."""

    def __init__(self, discount_rate: float = 0.10):
        self.discount_rate = discount_rate
        self._uk_regime = UKFiscalRegime()

    def compare(self, *profiles: BasinProfile) -> ComparisonResult:
        """Run NPV and government-take calculation for each profile.

        Parameters
        ----------
        *profiles:
            One or more BasinProfile instances (order-independent).

        Returns
        -------
        ComparisonResult
        """
        npv_by_basin: Dict[str, float] = {}
        gov_take_by_basin: Dict[str, float] = {}
        sensitivity: Dict[str, Dict[str, float]] = {}

        for profile in profiles:
            npv, gov_rate = self._compute(profile)
            npv_by_basin[profile.name] = npv
            gov_take_by_basin[profile.name] = gov_rate
            sensitivity[profile.name] = self._npv_sensitivity(profile)

        return ComparisonResult(
            npv_by_basin=npv_by_basin,
            government_take_by_basin=gov_take_by_basin,
            npv_sensitivity=sensitivity,
        )

    def _compute(self, profile: BasinProfile):
        """Return (post-tax NPV, effective government-take rate)."""
        monthly_rate = self.discount_rate / 12.0
        capex_usd = profile.capex_mm_usd * 1_000_000.0

        total_pre_tax_profit = 0.0
        total_tax = 0.0
        post_tax_cashflows = [-capex_usd]  # initial capex at t=0

        for t, prod_bbl in enumerate(profile.monthly_production_bbl, start=1):
            revenue = prod_bbl * profile.oil_price_usd_bbl
            opex = prod_bbl * profile.opex_per_bbl_usd
            pre_tax_profit = revenue - opex

            tax = self._apply_fiscal(profile, revenue, opex, capex_usd, t)

            net_cf = max(pre_tax_profit - tax, 0.0) if pre_tax_profit > 0 else 0.0
            discount_factor = 1.0 / ((1 + monthly_rate) ** t)
            post_tax_cashflows.append(net_cf * discount_factor)

            if pre_tax_profit > 0:
                total_pre_tax_profit += pre_tax_profit
                total_tax += tax

        npv = float(sum(post_tax_cashflows))

        # Effective government take as fraction of pre-tax (ring-fenced) profit.
        # This yields the ~78% effective rate for UKCS (RFCT 30% + SC 10% + EPL 35%).
        gov_rate = (
            (total_tax / total_pre_tax_profit) if total_pre_tax_profit > 0 else 0.0
        )
        gov_rate = min(max(gov_rate, 0.0), 1.0)

        return npv, gov_rate

    def _apply_fiscal(
        self,
        profile: BasinProfile,
        revenue: float,
        opex: float,
        capex_usd: float,
        month: int,
    ) -> float:
        """Return monthly tax burden based on fiscal regime."""
        if profile.fiscal_regime == "ukcs":
            # Amortise capex over first 36 months for ring-fenced profit calc
            monthly_capex = capex_usd / 36.0 if month <= 36 else 0.0
            result = self._uk_regime.calculate(
                gross_revenue=revenue,
                opex=opex,
                capex=monthly_capex,
            )
            return result.total_government_take

        elif profile.fiscal_regime == "ncs":
            taxable = max(0.0, revenue - opex)
            # Uplift reduces special tax base
            uplift_allowance = (
                capex_usd / 36.0 * NCS_UPLIFT_RATE if month <= 36 else 0.0
            )
            special_tax_base = max(0.0, taxable - uplift_allowance)
            corp_tax = taxable * NCS_CORPORATE_TAX_RATE
            special_tax = special_tax_base * NCS_SPECIAL_TAX_RATE
            return corp_tax + special_tax

        elif profile.fiscal_regime == "gom":
            royalty = revenue * GOM_ROYALTY_RATE
            taxable = max(0.0, revenue - royalty - opex)
            fed_tax = taxable * GOM_FEDERAL_TAX_RATE
            return royalty + fed_tax

        else:
            return 0.0

    def _npv_sensitivity(
        self, profile: BasinProfile, oil_price_delta_pct: float = 0.10
    ) -> Dict[str, float]:
        """Return NPV at base, high (+10%), and low (-10%) oil price."""
        base_npv, _ = self._compute(profile)

        high_profile = BasinProfile(
            name=profile.name,
            basin=profile.basin,
            monthly_production_bbl=profile.monthly_production_bbl,
            oil_price_usd_bbl=profile.oil_price_usd_bbl * (1 + oil_price_delta_pct),
            capex_mm_usd=profile.capex_mm_usd,
            opex_per_bbl_usd=profile.opex_per_bbl_usd,
            fiscal_regime=profile.fiscal_regime,
        )
        high_npv, _ = self._compute(high_profile)

        low_profile = BasinProfile(
            name=profile.name,
            basin=profile.basin,
            monthly_production_bbl=profile.monthly_production_bbl,
            oil_price_usd_bbl=profile.oil_price_usd_bbl * (1 - oil_price_delta_pct),
            capex_mm_usd=profile.capex_mm_usd,
            opex_per_bbl_usd=profile.opex_per_bbl_usd,
            fiscal_regime=profile.fiscal_regime,
        )
        low_npv, _ = self._compute(low_profile)

        return {
            "base": base_npv,
            "high_price": high_npv,
            "low_price": low_npv,
        }
