"""
Nigeria deepwater PSC fiscal regime model.

Nigeria uses Production Sharing Contracts (PSC) for deepwater blocks.
The fiscal structure is:

1. Royalty: depth-based (0% at >= 1000m for deepwater; see table below)
2. Cost oil: contractor recovers opex + capex up to a ceiling (typically 80%)
3. Profit oil: remaining oil split between NNPC (government) and contractor
   — split percentage is tiered by production rate (bopd)
4. PPT (Petroleum Profits Tax): 65.75% on contractor profit oil (PSC regime)
5. CITA (Companies Income Tax): 30% — applies if PPT < CITA in early years
6. NDDC Levy: 3% of gross revenue for Niger Delta Development Commission

Effective government take: typically 75-80% of gross revenue for producing
deepwater fields under the DEEP Offshore and Inland Basin PSC Act.

Reference: Petroleum Industry Act 2021 (PIA), NUPRC guidelines.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# ── Tax rates ──────────────────────────────────────────────────────────────
PPT_RATE_PSC = 0.6575  # Petroleum Profits Tax: 65.75% (PSC regime)
CITA_RATE = 0.30  # Companies Income Tax: 30%
NDDC_LEVY_RATE = 0.03  # Niger Delta Development Commission levy: 3%

# ── Royalty table: (min_depth_m, max_depth_m, rate) ──────────────────────
# Depth-based royalty for deepwater PSC blocks (Nigeria Deep Offshore Act)
DEEPWATER_ROYALTY_TABLE: List[Tuple[int, int, float]] = [
    (0, 200, 0.05),  # 0–200m:   5%
    (200, 500, 0.04),  # 200–500m: 4%
    (500, 800, 0.03),  # 500–800m: 3%
    (800, 1000, 0.015),  # 800–1000m: 1.5%
    (1000, 9999, 0.00),  # >= 1000m:  0% (incentivised deepwater)
]

# ── Profit oil split tiers: (max_production_bopd, nnpc_share) ────────────
# NNPC takes a larger share of profit oil at higher production rates.
PROFIT_OIL_TIERS: List[Tuple[int, float]] = [
    (20_000, 0.30),
    (40_000, 0.40),
    (60_000, 0.50),
    (100_000, 0.55),
    (150_000, 0.60),
    (200_000, 0.65),
    (999_999_999, 0.70),
]

# ── Nigeria deepwater field catalog ───────────────────────────────────────
NIGERIA_DEEPWATER_FIELDS: List[Dict] = [
    {
        "name": "Bonga",
        "operator": "Shell Nigeria",
        "operator_share_pct": 55.0,
        "water_depth_m": 1000,
        "status": "Producing",
        "first_oil_year": 2005,
        "plateau_kbd": 200,
        "notes": "Bonga North FID expected 2025, first oil ~2028",
    },
    {
        "name": "Egina",
        "operator": "TotalEnergies Nigeria",
        "operator_share_pct": 24.0,
        "water_depth_m": 1500,
        "status": "Producing",
        "first_oil_year": 2019,
        "plateau_kbd": 200,
        "notes": "FPSO Egina; Block OML 130",
    },
    {
        "name": "Agbami",
        "operator": "Chevron Nigeria",
        "operator_share_pct": 67.3,
        "water_depth_m": 1440,
        "status": "Producing",
        "first_oil_year": 2008,
        "plateau_kbd": 250,
        "notes": "OML 127; Star Deep Water Petroleum",
    },
    {
        "name": "Preowei",
        "operator": "TotalEnergies Nigeria",
        "operator_share_pct": 24.0,
        "water_depth_m": 1000,
        "status": "Producing",
        "first_oil_year": 2020,
        "plateau_kbd": 30,
        "notes": "Tie-back to Egina FPSO; OML 130",
    },
    {
        "name": "Erha",
        "operator": "ExxonMobil Nigeria",
        "operator_share_pct": 56.25,
        "water_depth_m": 1000,
        "status": "Producing",
        "first_oil_year": 2006,
        "plateau_kbd": 180,
        "notes": "OML 133; Erha North Phase 2 development",
    },
]


@dataclass
class PSCFiscalResult:
    """Output of the Nigeria deepwater PSC fiscal calculation."""

    gross_revenue: float
    royalties: float
    cost_oil: float
    profit_oil: float
    nnpc_profit_oil: float
    contractor_profit_oil: float
    ppt: float
    ppt_rate: float
    nddc_levy: float
    contractor_net_income: float
    total_government_take: float


def calculate_royalty_deepwater(water_depth_m: int) -> float:
    """
    Return royalty rate for a given water depth (Nigeria deepwater PSC).

    Args:
        water_depth_m: Water depth in metres.

    Returns:
        Royalty rate as a fraction (e.g. 0.05 = 5%).
    """
    for min_d, max_d, rate in DEEPWATER_ROYALTY_TABLE:
        if min_d <= water_depth_m < max_d:
            return rate
    # Default: 0% if deeper than table maximum
    return 0.0


def calculate_cost_oil_recovery(
    gross_revenue: float,
    opex: float,
    capex: float,
    cost_oil_ceiling: float = 0.80,
) -> float:
    """
    Calculate cost oil recovery amount.

    The contractor recovers opex + capex from production, capped at the
    cost oil ceiling (typically 80% of gross revenue).

    Args:
        gross_revenue: Total gross revenue in USD.
        opex: Operating expenditure in USD.
        capex: Capital expenditure in USD.
        cost_oil_ceiling: Maximum fraction of gross revenue available for
            cost oil recovery (default 0.80 = 80%).

    Returns:
        Cost oil amount in USD (capped at ceiling).
    """
    actual_costs = opex + capex
    ceiling_amount = gross_revenue * cost_oil_ceiling
    return min(actual_costs, ceiling_amount)


def calculate_profit_oil_split(
    profit_oil: float,
    production_rate_bopd: int,
) -> Dict[str, float]:
    """
    Split profit oil between NNPC and contractor based on production rate.

    Args:
        profit_oil: Total profit oil amount in USD.
        production_rate_bopd: Current production rate in barrels per day.

    Returns:
        Dict with 'nnpc' and 'contractor' keys (USD amounts).
    """
    nnpc_share = 0.70  # Default to highest tier
    for max_rate, share in PROFIT_OIL_TIERS:
        if production_rate_bopd <= max_rate:
            nnpc_share = share
            break

    nnpc_amount = profit_oil * nnpc_share
    contractor_amount = profit_oil * (1.0 - nnpc_share)
    return {"nnpc": nnpc_amount, "contractor": contractor_amount}


class NigeriaDeepwaterPSC:
    """
    Nigeria deepwater Production Sharing Contract fiscal model.

    Calculates government take components:
    - Royalty (depth-based, 0% at >= 1000m)
    - Cost oil recovery (capped at ceiling)
    - Profit oil split (tiered by production rate)
    - PPT on contractor profit oil (65.75%)
    - NDDC levy on gross revenue (3%)

    Government take components: royalty + NNPC profit oil + PPT + NDDC levy.
    Contractor income: contractor profit oil after PPT.
    """

    def __init__(
        self,
        water_depth_m: int = 1000,
        cost_oil_ceiling: float = 0.80,
    ):
        self.water_depth_m = water_depth_m
        self.cost_oil_ceiling = cost_oil_ceiling

    def calculate(
        self,
        gross_revenue: float,
        opex: float,
        capex: float,
        production_rate_bopd: int,
    ) -> PSCFiscalResult:
        """
        Compute full PSC fiscal result for a Nigeria deepwater field.

        Args:
            gross_revenue: Annual gross revenue in USD.
            opex: Annual operating expenditure in USD.
            capex: Annual capital expenditure in USD.
            production_rate_bopd: Annual average production rate in bopd.

        Returns:
            PSCFiscalResult with all fiscal components.
        """
        # 1. Royalty (0% for >= 1000m deepwater)
        royalty_rate = calculate_royalty_deepwater(self.water_depth_m)
        royalties = gross_revenue * royalty_rate

        # 2. NDDC levy on gross revenue
        nddc_levy = gross_revenue * NDDC_LEVY_RATE

        # 3. Cost oil recovery (opex + capex, capped at ceiling)
        revenue_after_royalty = gross_revenue - royalties
        cost_oil = calculate_cost_oil_recovery(
            revenue_after_royalty, opex, capex, self.cost_oil_ceiling
        )

        # 4. Profit oil = revenue after royalty minus cost oil
        profit_oil = max(0.0, revenue_after_royalty - cost_oil)

        # 5. Profit oil split between NNPC and contractor
        split = calculate_profit_oil_split(profit_oil, production_rate_bopd)
        nnpc_profit_oil = split["nnpc"]
        contractor_profit_oil = split["contractor"]

        # 6. PPT on contractor profit oil (65.75%; use CITA if higher)
        ppt = max(
            contractor_profit_oil * PPT_RATE_PSC,
            contractor_profit_oil * CITA_RATE,
        )
        ppt_applied_rate = PPT_RATE_PSC

        # 7. Contractor net income after PPT
        contractor_net_income = max(0.0, contractor_profit_oil - ppt)

        # 8. Total government take
        total_government_take = royalties + nnpc_profit_oil + ppt + nddc_levy

        return PSCFiscalResult(
            gross_revenue=gross_revenue,
            royalties=royalties,
            cost_oil=cost_oil,
            profit_oil=profit_oil,
            nnpc_profit_oil=nnpc_profit_oil,
            contractor_profit_oil=contractor_profit_oil,
            ppt=ppt,
            ppt_rate=ppt_applied_rate,
            nddc_levy=nddc_levy,
            contractor_net_income=contractor_net_income,
            total_government_take=total_government_take,
        )
