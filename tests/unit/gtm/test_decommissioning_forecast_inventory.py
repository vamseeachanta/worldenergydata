"""Inventory preconditions and an independent, synthetic forecast example.

All well counts, history counts, paces, shares and costs below are synthetic
test inputs, not BSEE measurements or cost estimates. The hand calculations in
the control test are the source of its expected values. Calendar windows and
aging thresholds retain the report's existing assumptions.
"""

import importlib.util
from pathlib import Path

import pytest

REPORT = (
    Path(__file__).resolve().parents[3]
    / "reports"
    / "gtm"
    / "decommissioning_market_outlook.py"
)


@pytest.fixture
def forecast():
    # File import executes definitions only, without main or real inventory I/O.
    spec = importlib.util.spec_from_file_location("decommissioning_forecast", REPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _inventory(statuses, pa_by_year=None, ta_by_year=None):
    """Match the full inventory shape returned by load_inventory."""
    total = sum(statuses.values())
    return {
        "total_wells": total,
        "gom_wells": total,
        "national_status": dict(statuses),
        "gom_status": dict(statuses),
        "gom_pa_by_year": dict(pa_by_year or {}),
        "gom_ta_by_year": dict(ta_by_year or {}),
    }


@pytest.mark.parametrize(
    "inventory",
    [
        pytest.param(_inventory({}), id="empty"),
        # Synthetic six-well inventory: all permanently abandoned in 2024.
        pytest.param(
            _inventory({"PA": 6}, pa_by_year={2024: 6}), id="already-abandoned"
        ),
    ],
)
def test_unavailable_eligible_inventory_raises_value_error(forecast, inventory):
    with pytest.raises(ValueError, match="Eligible inventory is unavailable"):
        forecast.build_forecast(inventory)


def test_inventory_is_checked_before_assumptions_or_scenarios(forecast, monkeypatch):
    monkeypatch.setattr(forecast, "ASSUMPTIONS", {})
    with pytest.raises(ValueError, match="Eligible inventory is unavailable"):
        forecast.build_forecast(_inventory({}))


def test_positive_inventory_retains_drawdown_costs_and_output_schema(
    forecast, monkeypatch
):
    # Synthetic eligible total: TA 80 + COM 120 + DSI 60 + AST 60 = 320.
    # PA, ST, CNL, DRL and APD are deliberately present but are not eligible.
    inventory = _inventory(
        {
            "TA": 80,
            "COM": 120,
            "DSI": 60,
            "AST": 60,
            "PA": 100,
            "ST": 40,
            "CNL": 20,
            "DRL": 10,
            "APD": 5,
        },
        pa_by_year={2015: 20, 2020: 40, 2024: 100},
        ta_by_year={2010: 10, 2015: 20, 2020: 50},
    )
    # Only these synthetic scenario assumptions replace production assumptions.
    monkeypatch.setitem(
        forecast.ASSUMPTIONS,
        "annual_attrition_pace",
        {"low": 0.25, "base": 0.5, "high": 0.75},
    )
    monkeypatch.setitem(
        forecast.ASSUMPTIONS,
        "deepwater_share_of_eligible",
        {"low": 0.0, "base": 0.25, "high": 0.5},
    )
    monkeypatch.setitem(
        forecast.ASSUMPTIONS,
        "pa_unit_cost_usd_mm_per_well",
        {
            "shelf_shallow": {"low": 1.0, "base": 2.0, "high": 4.0},
            "deepwater": {"low": 5.0, "base": 10.0, "high": 20.0},
        },
    )

    # Hand calculation, retaining fractional inventory between years:
    # low:  80, 60, 45, 33.75, 25.3125 -> rounded counts sum to 244.
    # base: 160, 80, 40, 20, 10 -> 310.
    # high: 240, 60, 15, 3.75, 0.9375 -> rounded counts sum to 320.
    # Cost blends ($MM): low = 1; base = .75*2 + .25*10 = 4;
    # high = .5*4 + .5*20 = 12. Totals / 1000 give $BN .24, 1.24, 3.84
    # after rounding to cents. History means: (20+40+100)/10 = 16,
    # (40+100)/5 = 28; implied pace = 16/320 = .05.
    # At the existing 2025 cutoff, TA ages >=10 sum to 10+20 = 30;
    # ages >=15 sum to 10. Full dict equality also protects every output key.
    assert forecast.build_forecast(inventory) == {
        "eligible_inventory": {
            "TA_idle": 80,
            "COM_completed": 120,
            "DSI": 60,
            "AST": 60,
            "total_eligible": 320,
        },
        "idle_iron": {
            "threshold_years": 10,
            "ta_idle_ge_10yr": 30,
            "ta_idle_ge_15yr": 10,
        },
        "observed_pa_rate": {
            "by_year_2015_2024": {
                "2015": 20,
                "2016": 0,
                "2017": 0,
                "2018": 0,
                "2019": 0,
                "2020": 40,
                "2021": 0,
                "2022": 0,
                "2023": 0,
                "2024": 100,
            },
            "mean_2015_2024": 16.0,
            "mean_2020_2024": 28.0,
            "implied_pace_vs_eligible_2015_2024": 0.05,
        },
        "forecast_years": [2026, 2027, 2028, 2029, 2030],
        "scenarios": {
            "low": {
                "attrition_pace": 0.25,
                "deepwater_share": 0.0,
                "blended_unit_cost_usd_mm": 1.0,
                "pa_per_year": [80, 60, 45, 34, 25],
                "pa_wells_5yr_total": 244,
                "market_size_5yr_usd_bn": 0.24,
            },
            "base": {
                "attrition_pace": 0.5,
                "deepwater_share": 0.25,
                "blended_unit_cost_usd_mm": 4.0,
                "pa_per_year": [160, 80, 40, 20, 10],
                "pa_wells_5yr_total": 310,
                "market_size_5yr_usd_bn": 1.24,
            },
            "high": {
                "attrition_pace": 0.75,
                "deepwater_share": 0.5,
                "blended_unit_cost_usd_mm": 12.0,
                "pa_per_year": [240, 60, 15, 4, 1],
                "pa_wells_5yr_total": 320,
                "market_size_5yr_usd_bn": 3.84,
            },
        },
    }
