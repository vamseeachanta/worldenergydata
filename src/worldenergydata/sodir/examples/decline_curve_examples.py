"""Decline curve analysis examples for named NCS fields.

Demonstrates fitting decline curves to production data from
Edvard Grieg, Valhall, and Ivar Aasen using mock data when live
API is unavailable.
"""

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

from worldenergydata.sodir.forecasting import ProductionForecaster

logger = logging.getLogger(__name__)

# Mock production profiles for named fields (monthly oil in Sm3).
# These represent realistic decline patterns for each field.
_MOCK_PROFILES = {
    "EDVARD GRIEG": {
        "start_year": 2016,
        "initial_rate_sm3": 900_000,
        "decline_rate": 0.03,
        "months": 84,
    },
    "VALHALL": {
        "start_year": 1982,
        "initial_rate_sm3": 600_000,
        "decline_rate": 0.02,
        "months": 96,
    },
    "IVAR AASEN": {
        "start_year": 2016,
        "initial_rate_sm3": 500_000,
        "decline_rate": 0.04,
        "months": 72,
    },
}


def create_mock_field_production(field_name: str) -> pd.DataFrame:
    """Create mock monthly production data for a named field.

    Args:
        field_name: One of "EDVARD GRIEG", "VALHALL", "IVAR AASEN".

    Returns:
        DataFrame with year, month, oil_sm3, gas_sm3 columns.

    Raises:
        ValueError: If field_name is not recognized.
    """
    if field_name not in _MOCK_PROFILES:
        raise ValueError(
            f"Unknown field: '{field_name}'. "
            f"Available: {list(_MOCK_PROFILES.keys())}"
        )

    profile = _MOCK_PROFILES[field_name]
    months = profile["months"]
    qi = profile["initial_rate_sm3"]
    d = profile["decline_rate"]
    start_year = profile["start_year"]

    records = []
    for i in range(months):
        year = start_year + (i // 12)
        month = (i % 12) + 1
        oil_sm3 = qi * np.exp(-d * i)
        # Gas proportional to oil (simplified GOR)
        gas_sm3 = oil_sm3 * 150
        records.append({
            "year": year,
            "month": month,
            "oil_sm3": oil_sm3,
            "gas_sm3": gas_sm3,
        })

    return pd.DataFrame(records)


def _fit_field_decline(field_name: str) -> Dict[str, Any]:
    """Fit a decline curve to a named field's mock production data."""
    df = create_mock_field_production(field_name)
    forecaster = ProductionForecaster()
    curve = forecaster.fit_decline_curve(df["oil_sm3"], model_type="exponential")

    return {
        "field_name": field_name,
        "decline_curve": curve,
        "r_squared": curve.r_squared,
        "initial_rate": curve.initial_rate,
        "decline_rate": curve.decline_rate,
    }


def run_edvard_grieg_decline_curve() -> Dict[str, Any]:
    """Run decline curve analysis for Edvard Grieg.

    Returns:
        Dict with field_name, decline_curve, r_squared, initial_rate, decline_rate.
    """
    result = _fit_field_decline("EDVARD GRIEG")
    logger.info(
        "Edvard Grieg decline: qi=%.0f, D=%.4f, R2=%.3f",
        result["initial_rate"], result["decline_rate"], result["r_squared"],
    )
    return result


def run_valhall_decline_curve() -> Dict[str, Any]:
    """Run decline curve analysis for Valhall.

    Returns:
        Dict with field_name, decline_curve, r_squared, initial_rate, decline_rate.
    """
    result = _fit_field_decline("VALHALL")
    logger.info(
        "Valhall decline: qi=%.0f, D=%.4f, R2=%.3f",
        result["initial_rate"], result["decline_rate"], result["r_squared"],
    )
    return result


def run_ivar_aasen_decline_curve() -> Dict[str, Any]:
    """Run decline curve analysis for Ivar Aasen.

    Returns:
        Dict with field_name, decline_curve, r_squared, initial_rate, decline_rate.
    """
    result = _fit_field_decline("IVAR AASEN")
    logger.info(
        "Ivar Aasen decline: qi=%.0f, D=%.4f, R2=%.3f",
        result["initial_rate"], result["decline_rate"], result["r_squared"],
    )
    return result
