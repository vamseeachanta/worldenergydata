"""UK fiscal regime for UKCS fields.

Current regime components (as of 2024, EPL extended to 2030):

  RFCT  — Ring Fence Corporation Tax:  30% on ring-fenced profits
  SC    — Supplementary Charge:        10% additional levy on ring-fenced profits
  EPL   — Energy Profits Levy:         35% windfall tax (2022–2030)
  IA    — Investment Allowance:        29% of qualifying capex offsets EPL liability

Combined RFCT + SC + EPL on ring-fenced profits:
  30% + 10% + 35% = 75% headline; effective marginal rate ~78% on incremental
  barrel after allowances (cf. Norway 78% — different structure).

References:
  HMRC — Oil and gas taxation: CT, SCT, EPL
  https://www.gov.uk/guidance/oil-and-gas-uk-field-allowances
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Rate constants ────────────────────────────────────────────────────────────
RFCT_RATE: float = 0.30  # Ring Fence Corporation Tax
SC_RATE: float = 0.10  # Supplementary Charge
EPL_RATE: float = 0.35  # Energy Profits Levy (windfall tax)
IA_RATE: float = 0.29  # Investment Allowance (offsets EPL)


# ── Helper functions ──────────────────────────────────────────────────────────


def calculate_rfct(ring_fenced_profit: float) -> float:
    """Return Ring Fence Corporation Tax on taxable ring-fenced profit."""
    if ring_fenced_profit <= 0.0:
        return 0.0
    return ring_fenced_profit * RFCT_RATE


def calculate_supplementary_charge(ring_fenced_profit: float) -> float:
    """Return Supplementary Charge (additional 10%) on ring-fenced profit."""
    if ring_fenced_profit <= 0.0:
        return 0.0
    return ring_fenced_profit * SC_RATE


def calculate_investment_allowance(qualifying_capex: float) -> float:
    """Return Investment Allowance amount — 29% of qualifying capex."""
    if qualifying_capex <= 0.0:
        return 0.0
    return qualifying_capex * IA_RATE


def calculate_epl(
    ring_fenced_profit: float,
    qualifying_capex: float = 0.0,
) -> float:
    """Return Energy Profits Levy net of Investment Allowance.

    Parameters
    ----------
    ring_fenced_profit:
        Taxable ring-fenced profit (revenue minus opex and capex).
    qualifying_capex:
        Capital expenditure eligible for the 29% Investment Allowance.
    """
    if ring_fenced_profit <= 0.0:
        return 0.0
    ia = calculate_investment_allowance(qualifying_capex)
    taxable = max(0.0, ring_fenced_profit - ia)
    return taxable * EPL_RATE


# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass
class UKFiscalResult:
    gross_revenue: float
    ring_fenced_profit: float
    rfct: float
    supplementary_charge: float
    epl: float
    investment_allowance: float
    net_income: float
    total_government_take: float


# ── Regime class ─────────────────────────────────────────────────────────────


class UKFiscalRegime:
    """UK fiscal regime: RFCT + Supplementary Charge + EPL (with IA)."""

    def calculate(
        self,
        gross_revenue: float,
        opex: float,
        capex: float,
    ) -> UKFiscalResult:
        """Calculate UK government take and net income.

        Parameters
        ----------
        gross_revenue:
            Total field revenue (USD or GBP, consistent units).
        opex:
            Operating expenditure.
        capex:
            Capital expenditure (all treated as qualifying for IA).

        Returns
        -------
        UKFiscalResult
            Breakdown of all tax components and net income.
        """
        ring_fenced_profit = gross_revenue - opex - capex

        rfct = calculate_rfct(ring_fenced_profit)
        sc = calculate_supplementary_charge(ring_fenced_profit)
        ia = calculate_investment_allowance(capex)
        epl = calculate_epl(ring_fenced_profit, qualifying_capex=capex)

        total_tax = rfct + sc + epl
        net_income = ring_fenced_profit - total_tax

        return UKFiscalResult(
            gross_revenue=gross_revenue,
            ring_fenced_profit=ring_fenced_profit,
            rfct=rfct,
            supplementary_charge=sc,
            epl=epl,
            investment_allowance=ia,
            net_income=net_income,
            total_government_take=total_tax,
        )
