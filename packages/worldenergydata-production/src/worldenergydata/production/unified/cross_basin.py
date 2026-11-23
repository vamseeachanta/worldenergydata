"""Cross-basin analytics for unified production data.

Functions in this module consume a ``ProductionResult`` and return summary
DataFrames suitable for comparison across multiple regions.

Fiscal regime coefficients are simplified approximations for illustrative
purposes; they are NOT legal or financial advice.
"""

from __future__ import annotations

import pandas as pd

from worldenergydata.production.unified.query import ProductionResult

# Fiscal parameters per region: (royalty_rate, tax_rate, govt_take_frac)
# govt_take_frac represents fraction of revenue going to government.
# Sources: publicly available fiscal regime summaries (approximate).
_FISCAL_REGIMES: dict[str, dict] = {
    "ncs": {
        "royalty_rate": 0.0,  # Norway: no royalty since 1986
        "tax_rate": 0.78,  # 22% corporate + 56% special petroleum tax
        "govt_take": 0.78,
    },
    "gom": {
        "royalty_rate": 0.1875,  # US GoM: 18.75% for deep water
        "tax_rate": 0.21,  # US federal corporate tax
        "govt_take": 0.36,
    },
    "brazil": {
        "royalty_rate": 0.15,  # ANP royalty up to 15%
        "tax_rate": 0.34,  # IRPJ + CSLL
        "govt_take": 0.45,  # includes profit oil sharing (PSA)
    },
    "ukcs": {
        "royalty_rate": 0.0,  # UK: royalty abolished 2003
        "tax_rate": 0.40,  # Ring-fenced corporation tax + supplementary
        "govt_take": 0.40,
    },
    "eia_us": {
        "royalty_rate": 0.125,  # onshore federal 12.5%
        "tax_rate": 0.21,
        "govt_take": 0.32,
    },
    "mexico": {
        "royalty_rate": 0.07,  # CNH: ~7% Exploration Extraction Tax
        "tax_rate": 0.30,  # ISR corporate
        "govt_take": 0.65,  # includes PEMEX dividend to state
    },
    "texas": {
        "royalty_rate": 0.25,  # typical private-land royalty
        "tax_rate": 0.21,
        "govt_take": 0.30,
    },
    "canada": {
        "royalty_rate": 0.20,  # NL offshore royalty regime (~20%)
        "tax_rate": 0.15,  # federal + NL provincial
        "govt_take": 0.35,
    },
    "spain": {
        "royalty_rate": 0.02,  # Ley 8/2015 hydrocarbon extraction levy (~1-4%)
        "tax_rate": 0.30,  # special IS rate for hydrocarbon E&P (Ley 27/2014 art. 29)
        "govt_take": 0.32,
    },
    "australia": {
        "royalty_rate": 0.0,  # offshore Commonwealth waters: PRRT, no ad-valorem royalty
        "tax_rate": 0.58,  # PRRT 40% + 30% company tax (PRRT deductible), combined
        "govt_take": 0.58,
    },
}

# Applied when a region has no entry in _FISCAL_REGIMES. Named (rather than
# inlined at the call site) so that the fallback is observable via
# :func:`fiscal_regime_source` instead of silently masquerading as a
# country-specific result — spain published a placeholder take for months (#831).
_GENERIC_DEFAULT_REGIME: dict[str, float] = {
    "royalty_rate": 0.15,
    "tax_rate": 0.25,
    "govt_take": 0.40,
}

_DISCOUNT_RATE = 0.10  # 10 % annual for NPV
_BBL_TO_USD_DEFAULT = 80.0  # default oil price used when caller passes None


def fiscal_regime_source(region: str) -> str:
    """Report whether a region's fiscal regime is country-specific or a default.

    Args:
        region: Region key as it appears in the production data.

    Returns:
        ``"country-specific"`` when the region has its own entry in
        :data:`_FISCAL_REGIMES`, otherwise ``"generic-default"`` — meaning the
        published royalty/tax/government-take figures come from
        :data:`_GENERIC_DEFAULT_REGIME` and are a placeholder, not that
        country's actual regime.
    """
    return "country-specific" if region in _FISCAL_REGIMES else "generic-default"


def compare_peak_rates(result: ProductionResult) -> pd.DataFrame:
    """Peak monthly oil rate per field, sorted descending.

    Args:
        result: ProductionResult from UnifiedProductionClient.query().

    Returns:
        DataFrame with columns ``region``, ``field_name``, ``peak_oil_bbl``
        sorted by ``peak_oil_bbl`` descending.
    """
    df = result.data
    if df.empty:
        return pd.DataFrame(columns=["region", "field_name", "peak_oil_bbl"])

    peaks = (
        df.groupby(["region", "field_name"])["oil_bbl"]
        .max()
        .reset_index()
        .rename(columns={"oil_bbl": "peak_oil_bbl"})
        .sort_values("peak_oil_bbl", ascending=False)
        .reset_index(drop=True)
    )
    return peaks


def compare_cumulative_eur(result: ProductionResult) -> pd.DataFrame:
    """Estimated ultimate recovery from production history.

    EUR here is simply the sum of historical production.  Callers may
    extend this with a decline-curve extrapolation for true forward-looking
    EUR.

    Args:
        result: ProductionResult from UnifiedProductionClient.query().

    Returns:
        DataFrame with columns ``region``, ``field_name``,
        ``cumulative_oil_bbl``, ``cumulative_gas_mcf``,
        ``eur_boe`` (oil + gas converted to BOE at 6 Mcf/BOE).
    """
    df = result.data
    if df.empty:
        return pd.DataFrame(
            columns=[
                "region",
                "field_name",
                "cumulative_oil_bbl",
                "cumulative_gas_mcf",
                "eur_boe",
            ]
        )

    agg = (
        df.groupby(["region", "field_name"])
        .agg(
            cumulative_oil_bbl=("oil_bbl", "sum"),
            cumulative_gas_mcf=("gas_mcf", "sum"),
        )
        .reset_index()
    )
    # 6 Mcf ≈ 1 BOE (SPE rule of thumb)
    agg["eur_boe"] = agg["cumulative_oil_bbl"] + agg["cumulative_gas_mcf"] / 6.0
    return agg.sort_values("eur_boe", ascending=False).reset_index(drop=True)


def fiscal_sensitivity(
    result: ProductionResult,
    oil_price_usd: float,
) -> pd.DataFrame:
    """Apply each region's fiscal regime to estimate government take and NPV.

    Uses a simplified cash-flow model:
        Revenue     = oil_bbl * oil_price_usd
        Royalty     = Revenue * royalty_rate
        Pre-tax CF  = Revenue - Royalty
        Tax         = Pre-tax CF * tax_rate
        Post-tax CF = Pre-tax CF - Tax
        Govt take   = Royalty + Tax  (as fraction of Revenue)
        NPV         = sum(Post-tax CF / (1 + r)^t) with monthly discounting

    Args:
        result: ProductionResult from UnifiedProductionClient.query().
        oil_price_usd: Oil price in USD/bbl.

    Returns:
        DataFrame with columns ``region``, ``field_name``,
        ``total_revenue_usd``, ``govt_take_usd``, ``operator_npv_usd``,
        ``effective_govt_take_pct``.
    """
    df = result.data
    if df.empty:
        return pd.DataFrame(
            columns=[
                "region",
                "field_name",
                "total_revenue_usd",
                "govt_take_usd",
                "operator_npv_usd",
                "effective_govt_take_pct",
            ]
        )

    records = []
    monthly_rate = _DISCOUNT_RATE / 12.0

    for (region, field), group in df.groupby(["region", "field_name"]):
        regime = _FISCAL_REGIMES.get(region, _GENERIC_DEFAULT_REGIME)
        royalty_rate = regime["royalty_rate"]
        tax_rate = regime["tax_rate"]

        group = group.sort_values(["year", "month"]).reset_index(drop=True)
        revenues = group["oil_bbl"] * oil_price_usd
        royalties = revenues * royalty_rate
        pre_tax = revenues - royalties
        taxes = pre_tax * tax_rate
        post_tax = pre_tax - taxes

        total_revenue = revenues.sum()
        total_govt = (royalties + taxes).sum()

        # Discount post-tax cash flow monthly
        periods = pd.Series(range(len(post_tax)))
        discount_factors = 1.0 / (1.0 + monthly_rate) ** periods
        npv = (post_tax * discount_factors).sum()

        records.append(
            {
                "region": region,
                "field_name": field,
                "total_revenue_usd": round(total_revenue, 0),
                "govt_take_usd": round(total_govt, 0),
                "operator_npv_usd": round(npv, 0),
                "effective_govt_take_pct": round(
                    100.0 * total_govt / total_revenue if total_revenue > 0 else 0.0,
                    2,
                ),
            }
        )

    return (
        pd.DataFrame(records)
        .sort_values("operator_npv_usd", ascending=False)
        .reset_index(drop=True)
    )
