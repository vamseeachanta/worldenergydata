"""Solveig NPV example combining forecasting output with NPV calculator.

Demonstrates a full workflow:
1. Load Edvard Grieg production as proxy for Solveig
2. Fit decline curve and forecast production
3. Run Norwegian NPV analysis with tax/uplift
"""

import logging
from typing import Any, Dict

import pandas as pd

from worldenergydata.sodir.examples.decline_curve_examples import (
    create_mock_field_production,
)
from worldenergydata.sodir.forecasting import ProductionForecaster
from worldenergydata.sodir.npv_norway import (
    NorwayNPVCalculator,
    NorwegianFinancialParameters,
)

logger = logging.getLogger(__name__)


def run_solveig_npv_analysis() -> Dict[str, Any]:
    """Run NPV analysis for Solveig using Edvard Grieg as production proxy.

    Returns:
        Dict with npv, irr, field_name, proxy_field, production_forecast,
        cash_flows.
    """
    # Use Edvard Grieg as proxy production profile
    proxy_df = create_mock_field_production("EDVARD GRIEG")

    # Aggregate monthly to annual oil production in MMbbl
    proxy_df["year_group"] = proxy_df["year"]
    annual = (
        proxy_df.groupby("year_group")
        .agg(
            oil_sm3=("oil_sm3", "sum"),
            gas_sm3=("gas_sm3", "sum"),
        )
        .reset_index()
    )

    # Convert Sm3 to MMbbl/BCF for NPV model
    sm3_to_bbl = 6.2898
    bcf_per_sm3 = 35.3147e-9  # 1 Sm3 gas = 35.3147e-9 BCF
    annual["oil_production_mmbbl"] = annual["oil_sm3"] * sm3_to_bbl / 1e6
    annual["gas_production_bcf"] = annual["gas_sm3"] * bcf_per_sm3

    # Fit decline curve for forecast
    forecaster = ProductionForecaster()
    curve = forecaster.fit_decline_curve(annual["oil_production_mmbbl"])

    # Forecast 10 additional years beyond historical
    forecast_years = 10
    forecast_values = curve.predict(forecast_years)

    # Build production profile for NPV (historical + forecast)
    production_profile = pd.DataFrame(
        {
            "year": list(range(len(annual) + forecast_years)),
            "oil_production_mmbbl": list(annual["oil_production_mmbbl"])
            + list(forecast_values),
            "gas_production_bcf": list(annual["gas_production_bcf"])
            + [0.0] * forecast_years,
        }
    )

    # Configure financial parameters for Solveig-style development
    params = NorwegianFinancialParameters(
        discount_rate=0.08,
        oil_price_usd=75.0,
        gas_price_nok_per_sm3=2.0,
        nok_usd_rate=10.5,
        opex_per_boe=12.0,
        capex_schedule=[500, 800, 300, 100],  # MM USD
    )

    # Run NPV calculation
    calculator = NorwayNPVCalculator(params)
    result = calculator.calculate_npv(production_profile)

    return {
        "field_name": "SOLVEIG",
        "proxy_field": "EDVARD GRIEG",
        "npv": result.npv,
        "irr": result.irr,
        "production_forecast": forecast_values,
        "cash_flows": result.cash_flows,
    }
