"""Brazilian fiscal regime models: concession and production sharing (PSA).

The concession royalty production-rate bands are illustrative, not
source-qualified fiscal terms. They are retained for compatibility and shall
not be copied into a fiscal deck without a governing contract and case.
See the package README for the source comparison and qualification limits.

Concession (post-salt, e.g. Marlim, Roncador):
- Royalties: illustrative 5-15% on gross revenue (production-rate bands)
- Special Participation (SP): 0-40% progressive tax on net revenue for large fields
- IRPJ + CSLL: ~34% corporate tax on net income

PSA / Production Sharing (pre-salt, e.g. Buzios, Lula, Mero, Sepia):
- Royalties: fixed 15%
- Profit oil: government takes % of remaining oil after cost recovery
- Petrobras minimum 30% participation in all pre-salt blocks
- No Special Participation
"""

import logging
from dataclasses import dataclass
from typing import Dict

logger = logging.getLogger(__name__)

CORPORATE_TAX_RATE = 0.34  # IRPJ (25%) + CSLL (9%)

# Illustrative bands: externally supplied barrels/day; rates on gross revenue.
# First mismatch: Decreto 2.705/1998, art. 12, paragraphs 1-2 specifies a
# contractual concession percentage, not these daily production-rate bands.
# Presidency: Lei 9.478/1997, art. 47, caput/paragraph 1; Decreto 2.705/1998,
# arts. 11-12. Opened 2026-10-12:
# https://www.planalto.gov.br/ccivil_03/leis/l9478.htm
# https://www.planalto.gov.br/ccivil_03/decreto/d2705.htm
# ANP, Royalties, calculation factors (opened 2026-10-12):
# https://www.gov.br/anp/pt-br/assuntos/royalties-e-outras-participacoes/royalties
# Art. 22's special-participation tables concern quarterly field net revenue,
# production year and location, not this royalty scale. Full comparison: README.
ROYALTY_SCALE_IS_ILLUSTRATIVE = True
ROYALTY_SCALE = [
    (5_000, 0.05),
    (15_000, 0.075),
    (30_000, 0.10),
    (50_000, 0.125),
    (float("inf"), 0.15),
]

# Progressive special participation thresholds (net revenue BRL)
SP_THRESHOLDS = [
    (50_000_000, 0.0),
    (100_000_000, 0.10),
    (300_000_000, 0.20),
    (600_000_000, 0.30),
    (float("inf"), 0.40),
]

PSA_ROYALTY_RATE = 0.15
PETROBRAS_MIN_SHARE = 0.30


@dataclass
class FiscalResult:
    gross_revenue: float
    royalties: float
    special_participation: float
    corporate_tax: float
    corporate_tax_rate: float
    net_income: float
    total_government_take: float
    government_profit_oil: float = 0.0


def calculate_royalties_concession(
    gross_revenue: float, production_rate_bpd: float
) -> float:
    """Apply the illustrative royalty bands to externally supplied gross revenue.

    The rate input uses barrels/day in the concession model's field context.
    Field aggregation, averaging basis, production year and location class are
    not established by this interface. The bands are not qualified fiscal terms;
    see ROYALTY_SCALE_IS_ILLUSTRATIVE and the package README source comparison.
    """
    if gross_revenue <= 0:
        return 0.0

    rate = 0.05
    for threshold, r in ROYALTY_SCALE:
        if production_rate_bpd <= threshold:
            rate = r
            break

    return gross_revenue * rate


def calculate_special_participation(net_revenue: float) -> float:
    if net_revenue <= 0:
        return 0.0

    total_sp = 0.0
    prev_threshold = 0.0
    for threshold, rate in SP_THRESHOLDS:
        if net_revenue <= prev_threshold:
            break
        taxable = min(net_revenue, threshold) - prev_threshold
        if taxable > 0:
            total_sp += taxable * rate
        prev_threshold = threshold

    return total_sp


def calculate_psa_government_take(
    gross_revenue: float,
    cost_oil: float,
    profit_oil_gov_share: float,
) -> Dict[str, float]:
    royalties = gross_revenue * PSA_ROYALTY_RATE
    net_after_royalties = gross_revenue - royalties
    profit_oil = max(0.0, net_after_royalties - cost_oil)
    government_profit_oil = profit_oil * profit_oil_gov_share

    return {
        "royalties": royalties,
        "profit_oil": profit_oil,
        "government_profit_oil": government_profit_oil,
        "petrobras_share": PETROBRAS_MIN_SHARE,
    }


class ConcessionRegime:
    """Concession model for post-salt fields with illustrative royalty bands."""

    def calculate(
        self,
        gross_revenue: float,
        opex: float,
        capex: float,
        production_rate_bpd: float,
    ) -> FiscalResult:
        royalties = calculate_royalties_concession(gross_revenue, production_rate_bpd)
        net_revenue = gross_revenue - opex - capex
        sp = calculate_special_participation(net_revenue)
        taxable_income = net_revenue - royalties - sp
        corporate_tax = max(0.0, taxable_income * CORPORATE_TAX_RATE)
        net_income = taxable_income - corporate_tax
        total_gov = royalties + sp + corporate_tax

        return FiscalResult(
            gross_revenue=gross_revenue,
            royalties=royalties,
            special_participation=sp,
            corporate_tax=corporate_tax,
            corporate_tax_rate=CORPORATE_TAX_RATE,
            net_income=net_income,
            total_government_take=total_gov,
        )


class PSARegime:
    """Production Sharing Agreement regime for pre-salt fields."""

    def calculate(
        self,
        gross_revenue: float,
        opex: float,
        capex: float,
        profit_oil_gov_share: float = 0.50,
    ) -> FiscalResult:
        royalties = gross_revenue * PSA_ROYALTY_RATE
        cost_oil = opex + capex
        profit_oil = max(0.0, gross_revenue - royalties - cost_oil)
        gov_profit_oil = profit_oil * profit_oil_gov_share
        contractor_share = profit_oil - gov_profit_oil
        corporate_tax = max(0.0, contractor_share * CORPORATE_TAX_RATE)
        net_income = contractor_share - corporate_tax
        total_gov = royalties + gov_profit_oil + corporate_tax

        return FiscalResult(
            gross_revenue=gross_revenue,
            royalties=royalties,
            special_participation=0.0,
            corporate_tax=corporate_tax,
            corporate_tax_rate=CORPORATE_TAX_RATE,
            net_income=net_income,
            total_government_take=total_gov,
            government_profit_oil=gov_profit_oil,
        )
