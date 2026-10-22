"""Pressure-window position uses explicit caller policy, not a universal limit."""

import math

import pytest

from worldenergydata.drilling_pressure_management.mpd_configurations import (
    PressureWindowAnalyzer,
    list_config_types,
)
from worldenergydata.drilling_pressure_management.mpd_systems import (
    MPD_SYSTEMS,
    get_systems_by_type,
)


@pytest.mark.parametrize(
    "loss,expected_position,required",
    [
        (0, 0.2, False),
        (600, 0.8, False),
        (750, 0.95, True),
        (900, 1.1, True),
    ],
)
def test_mpd_depends_on_ecd_position(loss, expected_position, required):
    """Hand arithmetic using the existing pack R1/C2c ECD convention.

    At 1000 m, MW=10 ppg: hydrostatic=10*.052*1000*3.28084=1706.0368 psi.
    With pore=1506.0368 and fracture=2506.0368, width=1000 psi and
    position=(200+loss)/1000. The caller chooses a 0.1 fractional margin
    and 200 psi width threshold for these synthetic cases, not as an
    engineering recommendation. Outside [0.1,0.9] requires MPD assessment.
    """
    result = PressureWindowAnalyzer().analyze(
        1000,
        1506.0368,
        2506.0368,
        10,
        500,
        annular_pressure_drop_psi=loss,
        threshold_psi=200,
        minimum_window_margin_fraction=0.1,
    )
    assert result.ecd_window_position == pytest.approx(expected_position)
    assert result.mpd_required is required


@pytest.mark.parametrize("loss", [0, 100])
def test_ecd_below_pore_requires_assessment(loss):
    result = PressureWindowAnalyzer().analyze(
        1000,
        2000,
        3000,
        10,
        500,
        loss,
        200,
        minimum_window_margin_fraction=0.1,
    )
    assert result.mpd_required is True


def test_annular_loss_and_policy_required():
    analyzer = PressureWindowAnalyzer()
    with pytest.raises(TypeError):
        analyzer.analyze(
            1000,
            1500,
            2500,
            10,
            500,
            threshold_psi=200,
            minimum_window_margin_fraction=0.1,
        )
    with pytest.raises(TypeError):
        analyzer.analyze(1000, 1500, 2500, 10, 500, 0)


@pytest.mark.parametrize("config_type", list_config_types() + ["multi_mode"])
def test_multi_mode_in_every_known_type_query(config_type):
    multi = [entry for entry in MPD_SYSTEMS if entry.mpd_type == "multi_mode"]
    assert multi
    assert all(entry in get_systems_by_type(config_type) for entry in multi)


@pytest.mark.parametrize("bad", [math.inf, -math.inf, math.nan, -1])
def test_invalid_loss_refused(bad):
    with pytest.raises(ValueError):
        PressureWindowAnalyzer().analyze(
            1000, 1500, 2500, 10, 500, bad, 200, minimum_window_margin_fraction=0.1
        )


@pytest.mark.parametrize(
    "position,required", [(0.05, True), (0.1, False), (0.9, False), (0.95, True)]
)
def test_both_window_margin_boundaries(position, required):
    """Caller margin .1 means the closed admissible interval is [.1,.9]."""
    assert (
        PressureWindowAnalyzer().mpd_required(
            1000,
            200,
            ecd_window_position=position,
            minimum_window_margin_fraction=0.1,
        )
        is required
    )


@pytest.mark.parametrize("margin", [-0.1, 0.6, math.inf, math.nan])
def test_invalid_policy_refused(margin):
    with pytest.raises(ValueError):
        PressureWindowAnalyzer().analyze(
            1000,
            1500,
            2500,
            10,
            500,
            0,
            200,
            minimum_window_margin_fraction=margin,
        )
