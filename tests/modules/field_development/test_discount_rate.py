"""Discount selection and independent annual-NPV arithmetic for issue #1324.

Equation source: NumPy v1.17 Manual, numpy.npv, Notes (2020):
https://numpy.org/doc/1.17/reference/generated/numpy.npv.html
NPV = sum(CF_t / (1 + r)**t), including the initial investment at t=0.
The manual cites Principles of Managerial Finance, Brief, third edition
(2003), page 346. The positive-rate factors are 1/(1+r)**t; t counts
whole years, with end-year receipts and the investment at t=0.
Integration conventions: field_development/docs/agent-pack.md, E2–E4.

All fixture numbers below are synthetic inputs, not engineering defaults:
depth 1500 m selects subsea15; host 60 MM + 2 wells * 20 MM = 100 MM.
Production 1,000,000/365 boe/day * 365 days/year = 1,000,000 boe/year;
at 100 USD/boe and zero royalty/OPEX, annual receipts are 100 MM USD.
The 365-day year and 1,000,000 USD/MM USD follow pack E3 conventions.
For two end-year receipts, independent hand calculations give:
r=0: -100 + 100 + 100 = 100 MM;
r=0.25: -100 + 100/1.25 + 100/1.5625 = 44 MM;
r=0.5: -100 + 200/3 + 400/9 = 100/9 MM, displayed as 11.1 MM.
Exact assertions target pack E4's one-decimal output, not an extra tolerance.
"""

import pandas as pd
import pytest

from worldenergydata.fdas.core import config
from worldenergydata.field_development import FieldConcept, estimate_economics


@pytest.mark.parametrize(
    "discount_input, default_rate, expected_rate, expected_npv",
    [
        pytest.param({}, 0.25, 0.25, 44.0, id="omitted-uses-default"),
        pytest.param({"discount_rate": None}, 0.25, 0.25, 44.0, id="none-uses-default"),
        pytest.param({"discount_rate": 0.0}, 0.25, 0.0, 100.0, id="zero-overrides"),
        pytest.param({"discount_rate": 0.5}, 0.25, 0.5, 11.1, id="positive-overrides"),
        pytest.param({}, 0.0, 0.0, 100.0, id="zero-default"),
        pytest.param({"discount_rate": 0.0}, None, 0.0, 100.0, id="zero-no-default"),
    ],
)
def test_discount_selection_and_hand_calculated_npv(
    monkeypatch, discount_input, default_rate, expected_rate, expected_npv
):
    """Restoring a truthiness fallback must fail the zero-overrides case."""
    # Synthetic inputs and expected values are derived in the module docstring.
    manager = config.AssumptionsManager(
        pd.DataFrame(
            [
                {
                    "DEV_SYSTEM": "subsea15",
                    "HOST_CAPEX_MM": 60.0,
                    "SURF_PER_WELL_MM": 20.0,
                    "FIXED_OPEX_MM_PER_YEAR": 0.0,
                    "VARIABLE_OPEX_$/BBL": 0.0,
                    "ROYALTY_RATE": 0.0,
                    "DISCOUNT_RATE_ANNUAL": default_rate,
                }
            ]
        )
    )
    monkeypatch.setattr(config, "AssumptionsManager", lambda: manager)
    concept = FieldConcept(
        name="Synthetic",
        water_depth_m=1500.0,
        num_wells=2,
        plateau_rate_boed=1_000_000 / 365,
        oil_price_usd_bbl=100.0,
        field_life_years=2,
        **discount_input,
    )

    result = estimate_economics(concept)

    assert result.capex_mm == 100.0
    assert result.discount_rate == expected_rate
    assert result.npv_mm == expected_npv


@pytest.mark.parametrize("rate", [-0.1, float("nan"), float("inf"), -float("inf")])
def test_invalid_discount_rate_is_refused(rate):
    """Issue 1324: a negative or non-finite rate is outside the input contract."""
    with pytest.raises(ValueError, match="discount_rate"):
        FieldConcept(name="Synthetic", discount_rate=rate)


@pytest.mark.parametrize("rate", [-0.1, float("nan"), float("inf")])
def test_unvalidated_discount_rate_does_not_produce_npv(rate):
    """Even model-copy updates must not publish an invalid-rate valuation."""
    concept = FieldConcept(
        name="Synthetic",
        water_depth_m=1500.0,
        num_wells=2,
        plateau_rate_boed=100.0,
        oil_price_usd_bbl=100.0,
        field_life_years=2,
    ).model_copy(update={"discount_rate": rate})
    result = estimate_economics(concept)
    assert result.npv_mm is None
    assert "discount_rate" in result.note
