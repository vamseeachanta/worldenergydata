"""Illustrative examples; expected rates and volumes use hand arithmetic."""
from dataclasses import FrozenInstanceError, replace

import pytest

from worldenergydata.economics.scenario_inputs import Periods, WellSchedule
from worldenergydata.economics.scenario import ProductionProfile, production_profile


def test_drilling_completion_then_single_well_decline():
    periods = Periods(duration_years=1.0, production_days=(300.0,) * 5)
    well = WellSchedule(
        drilling_start_period=0, drilling_periods=1, completion_periods=1,
        production_delay_periods=0, initial_rate_barrels_per_day=800.0,
        retention_fractions=(1.0, 1.0, 1.0, 0.5, 0.5),
        additions_barrels_per_day=(0.0,) * 5,
    )
    result = production_profile(well, periods)
    assert result.rates_barrels_per_day == (0.0, 0.0, 800.0, 400.0, 200.0)
    assert result.volumes_barrels == (0.0, 0.0, 800 * 300, 400 * 300, 200 * 300)
    with pytest.raises(FrozenInstanceError):
        well.drilling_periods = 2


def test_reset_and_additions_use_the_current_period_retention():
    periods = Periods(0.5, (180.0,) * 4)
    well = WellSchedule(0, 0, 0, 0, 800.0, (1.0, 0.5, 0.0, 0.5),
                        (0.0, 200.0, 600.0, 0.0))
    result = production_profile(well, periods)
    assert result.rates_barrels_per_day == (800.0, 800 * 0.5 + 200, 600.0, 300.0)
    # A delay outside the horizon is an explicitly nonproducing well.
    delayed = replace(well, production_delay_periods=10,
                      additions_barrels_per_day=(0.0,) * 4)
    assert production_profile(delayed, periods).rates_barrels_per_day == (0.0,) * 4


@pytest.mark.parametrize('retention', [-0.01, 1.01, float('nan')])
def test_invalid_retention_is_rejected(retention):
    with pytest.raises(ValueError):
        WellSchedule(0, 0, 0, 0, 800.0, (retention,), (0.0,))


def test_schedule_and_period_validation():
    with pytest.raises(ValueError):
        Periods(0.0, (300.0,))
    with pytest.raises(ValueError):
        Periods(1.0, [300.0])
    with pytest.raises(ValueError):
        WellSchedule(0, 0.5, 0, 0, 800.0, (1.0,), (0.0,))
    with pytest.raises(ValueError):
        production_profile(WellSchedule(0, 0, 0, 0, 800.0, (1.0,), (0.0,)),
                           Periods(1.0, (300.0,) * 2))
    with pytest.raises(ValueError):
        production_profile(WellSchedule(0, 1, 0, 0, 800.0, (1.0,), (1.0,)),
                           Periods(1.0, (300.0,)))


def test_production_profile_rejects_volume_overflow():
    # Numerical limit probe, not an illustrative well.
    with pytest.raises(ValueError):
        production_profile(WellSchedule(0, 0, 0, 0, 1e308, (1.0,), (0.0,)),
                           Periods(1.0, (300.0,)))


@pytest.mark.parametrize('rates, volumes', [
    ((800.0, 400.0), (240000.0,)),
    ((800.0,), (240000.0, 120000.0)),
])
def test_production_profile_rejects_mismatched_horizons(rates, volumes):
    with pytest.raises(ValueError, match='Rates and volumes must share a horizon'):
        ProductionProfile(rates, volumes)
