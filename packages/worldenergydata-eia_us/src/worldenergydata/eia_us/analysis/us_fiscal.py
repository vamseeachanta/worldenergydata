"""US fiscal regimes: federal onshore royalties, state severance taxes.

Regimes modelled:
  1. Federal onshore (BLM lands): 16.67% royalty on gross production value
  2. Texas (RRC): 4.6% oil severance + 7.5% gas severance
  3. North Dakota (Bakken): 5% oil extraction + 6.5% oil production = 11.5% combined
  4. GoM crosscheck: compare EIA vs BSEE Gulf of Mexico production aggregates

References:
  - 30 CFR Part 1206 — Federal oil royalty rates
  - Texas Tax Code Chapter 202 — Oil production tax
  - Texas Tax Code Chapter 201 — Gas production tax
  - ND Century Code 57-51 (oil extraction) + 57-51.1 (oil production)
"""

import logging
from dataclasses import dataclass
from math import isfinite

logger = logging.getLogger(__name__)


# ── Rate constants ─────────────────────────────────────────────────────────────

FEDERAL_ONSHORE_ROYALTY_RATE: float = 0.1667  # 16.67% — 30 CFR 1206.101

TEXAS_OIL_SEVERANCE_RATE: float = 0.046  # 4.6% — TX Tax Code §202.052
TEXAS_GAS_SEVERANCE_RATE: float = 0.075  # 7.5% — TX Tax Code §201.052

ND_OIL_EXTRACTION_RATE: float = 0.05  # 5.0% — ND CC 57-51
ND_OIL_PRODUCTION_RATE: float = 0.065  # 6.5% — ND CC 57-51.1

# ── Result dataclass ───────────────────────────────────────────────────────────


@dataclass
class USFiscalResult:
    """Summary of US fiscal calculations for an oil/gas field."""

    gross_revenue: float
    opex: float
    royalty: float = 0.0
    severance_tax: float = 0.0
    extraction_tax: float = 0.0  # ND-specific component
    production_tax: float = 0.0  # ND-specific component
    net_income: float = 0.0
    total_government_take: float = 0.0


# ── Federal Onshore Fiscal ─────────────────────────────────────────────────────


class FederalOnshoreFiscal:
    """Federal onshore fiscal regime: royalty on gross production value.

    Applies to BLM-administered leases (onshore public domain minerals).
    No state severance included — that is handled separately by the state.
    """

    def calculate(
        self,
        gross_revenue: float,
        opex: float,
        capex: float = 0.0,
    ) -> USFiscalResult:
        """Calculate federal onshore government take and net income.

        Args:
            gross_revenue: Total field revenue.
            opex: Operating expenditure.
            capex: Capital expenditure (not currently tax-deductible at royalty stage).

        Returns:
            USFiscalResult with royalty and net income populated.
        """
        royalty = max(0.0, gross_revenue * FEDERAL_ONSHORE_ROYALTY_RATE)
        revenue_after_royalty = gross_revenue - royalty
        net_income = revenue_after_royalty - opex - capex

        return USFiscalResult(
            gross_revenue=gross_revenue,
            opex=opex,
            royalty=royalty,
            severance_tax=0.0,
            net_income=net_income,
            total_government_take=royalty,
        )


# ── Texas Fiscal ───────────────────────────────────────────────────────────────


class TexasFiscal:
    """Texas Railroad Commission fiscal regime: oil and gas severance taxes.

    No state income tax in Texas — severance is the primary production levy.
    """

    def calculate_oil(
        self,
        gross_revenue: float,
        opex: float,
        capex: float = 0.0,
    ) -> USFiscalResult:
        """Calculate Texas oil severance tax and net income.

        Args:
            gross_revenue: Oil production gross revenue.
            opex: Operating expenditure.
            capex: Capital expenditure.

        Returns:
            USFiscalResult with Texas oil severance populated.
        """
        severance = max(0.0, gross_revenue * TEXAS_OIL_SEVERANCE_RATE)
        revenue_after_sev = gross_revenue - severance
        net_income = revenue_after_sev - opex - capex

        return USFiscalResult(
            gross_revenue=gross_revenue,
            opex=opex,
            severance_tax=severance,
            net_income=net_income,
            total_government_take=severance,
        )

    def calculate_gas(
        self,
        gross_revenue: float,
        opex: float,
        capex: float = 0.0,
    ) -> USFiscalResult:
        """Calculate Texas gas severance tax and net income.

        Args:
            gross_revenue: Gas production gross revenue.
            opex: Operating expenditure.
            capex: Capital expenditure.

        Returns:
            USFiscalResult with Texas gas severance populated.
        """
        severance = max(0.0, gross_revenue * TEXAS_GAS_SEVERANCE_RATE)
        revenue_after_sev = gross_revenue - severance
        net_income = revenue_after_sev - opex - capex

        return USFiscalResult(
            gross_revenue=gross_revenue,
            opex=opex,
            severance_tax=severance,
            net_income=net_income,
            total_government_take=severance,
        )


# ── North Dakota Fiscal ────────────────────────────────────────────────────────


class NorthDakotaFiscal:
    """North Dakota Bakken fiscal regime: oil extraction + oil production taxes.

    Combined rate: 5% extraction (ND CC 57-51) + 6.5% production (ND CC 57-51.1)
    = 11.5% on gross production value.
    """

    def calculate(
        self,
        gross_revenue: float,
        opex: float,
        capex: float = 0.0,
    ) -> USFiscalResult:
        """Calculate North Dakota combined oil tax and net income.

        Args:
            gross_revenue: Oil production gross revenue.
            opex: Operating expenditure.
            capex: Capital expenditure.

        Returns:
            USFiscalResult with extraction_tax, production_tax, severance_tax.
        """
        extraction_tax = max(0.0, gross_revenue * ND_OIL_EXTRACTION_RATE)
        production_tax = max(0.0, gross_revenue * ND_OIL_PRODUCTION_RATE)
        combined_severance = extraction_tax + production_tax

        revenue_after_tax = gross_revenue - combined_severance
        net_income = revenue_after_tax - opex - capex

        return USFiscalResult(
            gross_revenue=gross_revenue,
            opex=opex,
            extraction_tax=extraction_tax,
            production_tax=production_tax,
            severance_tax=combined_severance,
            net_income=net_income,
            total_government_take=combined_severance,
        )


# ── GoM Crosscheck ─────────────────────────────────────────────────────────────


class GoMCrosscheck:
    """Cross-validate EIA GoM production against BSEE OGOR-A aggregates.

    EIA reports GoM crude production via the petroleum supply survey.
    BSEE publishes OGOR-A offshore production reports.
    Tolerances are caller-supplied acceptance criteria, not physical constants.
    With no applicable tolerance, unequal rates are NOT_EVALUATED. Exact
    equality, including zero/zero, passes without a tolerance.

    Basis: PEP 485 (2015), "Symmetry" (scaling to a known reference) and
    "Behavior near zero" (explicit absolute tolerance):
    https://peps.python.org/pep-0485/
    """

    def __init__(
        self,
        tolerance_pct: float | None = None,
        *,
        absolute_tolerance_kbd: float | None = None,
    ) -> None:
        """Set optional relative (fraction) and absolute (thousand bbl/day) limits.

        The legacy name tolerance_pct retains its fractional meaning: a
        caller-supplied 0.05 means 5.0 %, not 0.05 %. No default acceptance
        limit is assumed. Both limits must be finite and nonnegative.
        """
        for name, value in (
            ("tolerance_pct", tolerance_pct),
            ("absolute_tolerance_kbd", absolute_tolerance_kbd),
        ):
            if value is not None and (not isfinite(value) or value < 0.0):
                raise ValueError(f"{name} must be finite and nonnegative")
        self.tolerance_pct = tolerance_pct
        self.absolute_tolerance_kbd = absolute_tolerance_kbd

    def compare(
        self,
        eia_production_kbd: float,
        bsee_production_kbd: float,
    ) -> dict:
        """Compare EIA and BSEE GoM production estimates.

        Args:
            eia_production_kbd: EIA-reported GoM crude production (kbd).
            bsee_production_kbd: BSEE OGOR-A aggregate production (kbd).

        Returns:
            Production and signed difference in kbd (thousand bbl/day).
            pct_difference retains its legacy dimensionless fractional meaning;
            it is None for a zero BSEE reference, including zero/zero.
            within_tolerance is True (PASS), False (FAIL), or None
            (NOT_EVALUATED). Applied tolerance inputs are included with units
            in their key names. Either supplied limit can establish agreement;
            only an absolute limit can evaluate unequal rates against zero.

        Raises:
            ValueError: Either production rate is negative or non-finite.
        """
        for name, value in (
            ("eia_production_kbd", eia_production_kbd),
            ("bsee_production_kbd", bsee_production_kbd),
        ):
            if not isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")

        difference = eia_production_kbd - bsee_production_kbd
        # PEP 485 (2015), "Symmetry": use the known BSEE reference magnitude.
        # Division by zero has no relative-error value; never invent a divisor.
        pct_diff = (
            abs(difference) / bsee_production_kbd
            if bsee_production_kbd != 0.0
            else None
        )
        within_tolerance = None
        if difference == 0.0:
            within_tolerance = True
        else:
            applicable_checks = []
            if self.absolute_tolerance_kbd is not None:
                applicable_checks.append(abs(difference) <= self.absolute_tolerance_kbd)
            if pct_diff is not None and self.tolerance_pct is not None:
                applicable_checks.append(pct_diff <= self.tolerance_pct)
            if applicable_checks:
                within_tolerance = any(applicable_checks)

        status = (
            "NOT_EVALUATED"
            if within_tolerance is None
            else "PASS" if within_tolerance else "FAIL"
        )

        return {
            "eia_kbd": eia_production_kbd,
            "bsee_kbd": bsee_production_kbd,
            "difference_kbd": difference,
            "pct_difference": pct_diff,
            "within_tolerance": within_tolerance,
            "status": status,
            "relative_tolerance_fraction": self.tolerance_pct,
            "absolute_tolerance_kbd": self.absolute_tolerance_kbd,
        }
