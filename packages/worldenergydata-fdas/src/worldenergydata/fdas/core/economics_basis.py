"""Calculation-basis declarations for reference-chain plumbing.

These descriptions follow the shipped reference_chain runners and CashflowEngine
(2026); they do not qualify fiscal decks or turn plumbing into investment NPV.
"""

from __future__ import annotations

import pandas as pd


def reference_chain_basis(
    production: pd.DataFrame,
    oil_price_usd_bbl: float,
    *,
    royalty_basis: str,
    gas_prices: dict[str, float] | None = None,
) -> dict:
    """Describe the actual undiscounted, pre-income-tax chain inputs.

    Source tags describe the supplied adapter data, not an assertion of source
    rights or a promotion of fixture data to measured production.
    """
    sources = (
        sorted(production["source"].dropna().astype(str).unique().tolist())
        if "source" in production
        else []
    )
    return {
        "view": "reference_chain_pre_tax",
        "status": "NOT_EVALUATED" if production.empty else "plumbing_only",
        "engine": "fdas.analysis.cashflow.CashflowEngine",
        "production_scope": "supplied_history_no_forecast",
        "production_sources": sources,
        "cashflow_period": "monthly",
        "discount_convention": "undiscounted",
        "discount_rate_annual": None,
        "reference_date": "not_applicable_undiscounted",
        "tax_treatment": "pre_income_tax_after_royalty",
        "royalty_basis": royalty_basis,
        "fiscal_validation": "NOT_EVALUATED",
        "capex": "model_host_only_no_drilling_or_facilities_schedule",
        "opex": "variable_fdas_assumptions_fixed_excluded",
        "oil_price_marker": "flat_input_not_market_series",
        "oil_price_usd_bbl": oil_price_usd_bbl,
        "gas_price_marker": "supplied_USD_per_Mcf_deck" if gas_prices else "not_priced",
        "gas_prices_usd_mcf": dict(gas_prices) if gas_prices else None,
    }
