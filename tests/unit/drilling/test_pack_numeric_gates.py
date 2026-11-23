"""Executable numeric gates from the drilling knowledge pack."""

import math

import pandas as pd
import pytest
from pydantic import ValidationError

from worldenergydata.drilling import (
    BatchDrillingEconomics,
    BSEEBatchDetector,
    DrillCampaign,
)


def test_c0_campaign_schema():
    """Accept the documented default and reject each invalid numeric input."""
    valid = dict(
        campaign_id="",
        rig_name="",
        wells=[],
        rig_day_rate_usd=350_000,
        mobilization_cost_usd=20_000_000,
    )
    assert DrillCampaign(**valid).learning_curve_factor == 0.85
    for key, value in (
        ("rig_day_rate_usd", 0),
        ("mobilization_cost_usd", -1),
        ("learning_curve_factor", 0),
    ):
        with pytest.raises(ValidationError):
            DrillCampaign(**dict(valid, **{key: value}))


def test_c4_mobilization_allocation():
    """Compare the allocation with the independent two-well hand result."""
    result = BatchDrillingEconomics().mobilization_savings(20_000_000, 2)
    assert result == pytest.approx(10_000_000, abs=0.01, rel=0)


def test_c5_power_law_duration():
    """The third position distinguishes the power law from geometric decay."""
    calc = BatchDrillingEconomics()
    assert calc.learning_curve_time(60, 2, 0.85) == pytest.approx(51, abs=1e-9, rel=0)
    power_law = 60 * 3 ** (math.log(0.85) / math.log(2))
    assert calc.learning_curve_time(60, 3, 0.85) == pytest.approx(
        power_law, abs=1e-6, rel=0
    )
    assert abs(60 * 0.85**2 - power_law) > 1e-6


def test_c7_break_even_outputs():
    """Record all six current outputs, including the no-learning case."""
    calc = BatchDrillingEconomics()
    assert calc.break_even_n_wells(20e6, 350e3, 60, 1.0) == 2
    for mobilization in (5e6, 20e6, 50e6):
        assert calc.break_even_n_wells(mobilization, 350e3, 60, 0.85) == 2
    assert calc.break_even_n_wells(0, 350e3, 60, 1.0) == 1
    assert calc.break_even_n_wells(0, 350e3, 60, 0.85) == 2


def test_c8_learning_fit():
    """Compare the fitted factor and slope with scalar least squares."""
    x = [math.log(n) for n in (1, 2, 3, 4)]
    y = [math.log(t) for t in (60, 52, 48, 45)]
    x_mean, y_mean = sum(x) / 4, sum(y) / 4
    slope = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y)) / sum(
        (a - x_mean) ** 2 for a in x
    )
    assert slope == pytest.approx(-0.206231, abs=1e-6, rel=0)
    factor = BSEEBatchDetector().fit_learning_curve(
        pd.DataFrame({"well_position": [1, 2, 3, 4], "days_to_drill": [60, 52, 48, 45]})
    )
    assert factor == pytest.approx(0.866799, abs=1e-6, rel=0)
    assert factor == pytest.approx(2**slope, abs=1e-6, rel=0)
    assert math.log(factor) / math.log(2) == pytest.approx(-0.206231, abs=1e-6, rel=0)
