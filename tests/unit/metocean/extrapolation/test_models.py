# ABOUTME: Tests for WaveExtrapolator and CurrentExtrapolator physics models.
# ABOUTME: Verifies shoaling, fetch, depth-scaling, and transfer functions.

"""
Tests for worldenergydata.metocean.extrapolation.models
"""

import math

import pytest

from worldenergydata.metocean.extrapolation.models import (
    CurrentExtrapolator,
    WaveExtrapolator,
)
from worldenergydata.metocean.extrapolation.source_catalog import MetoceanSource
from worldenergydata.metocean.extrapolation.spatial import (
    SpatialAssessor,
    SpatialContext,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def wave():
    return WaveExtrapolator()


@pytest.fixture
def current():
    return CurrentExtrapolator()


def _make_context(
    depth_ratio: float = 1.0,
    sheltering: float = 1.0,
    distance_km: float = 10.0,
    fetch_km: float = 400.0,
) -> SpatialContext:
    src = MetoceanSource(
        name="test_src",
        source_type="buoy",
        lat=28.5,
        lon=-88.5,
        coverage_radius_km=200.0,
        parameters=["Hs"],
        priority=1,
        region="gom",
    )
    return SpatialContext(
        target_lat=28.5,
        target_lon=-88.5,
        nearest_source=src,
        distance_km=distance_km,
        fetch_km=fetch_km,
        depth_ratio=depth_ratio,
        sheltering_factor=sheltering,
        correction_needed=(distance_km > 50 or abs(depth_ratio - 1.0) > 0.2),
    )


# ---------------------------------------------------------------------------
# WaveExtrapolator.shoaling_correction tests
# ---------------------------------------------------------------------------


def test_shoaling_correction_returns_float(wave):
    result = wave.shoaling_correction(2.5, 100.0, 50.0)
    assert isinstance(result, float)


def test_shoaling_correction_positive(wave):
    result = wave.shoaling_correction(2.5, 100.0, 50.0)
    assert result > 0.0


def test_shoaling_correction_same_depth_is_identity(wave):
    Hs = 3.0
    result = wave.shoaling_correction(Hs, 80.0, 80.0)
    assert result == pytest.approx(Hs, rel=1e-6)


def test_shoaling_correction_shallower_target_increases_hs(wave):
    # Moving to shallower water => Hs increases (shoaling)
    Hs_deep = 2.0
    Hs_shallow = wave.shoaling_correction(Hs_deep, 100.0, 25.0)
    assert Hs_shallow > Hs_deep


def test_shoaling_correction_deeper_target_decreases_hs(wave):
    # Moving to deeper water => Hs decreases
    Hs_source = 2.0
    Hs_deep = wave.shoaling_correction(Hs_source, 25.0, 100.0)
    assert Hs_deep < Hs_source


def test_shoaling_correction_raises_on_non_positive_Hs(wave):
    with pytest.raises(ValueError):
        wave.shoaling_correction(-1.0, 100.0, 50.0)


def test_shoaling_correction_raises_on_zero_depth(wave):
    with pytest.raises(ValueError):
        wave.shoaling_correction(2.0, 0.0, 50.0)


# ---------------------------------------------------------------------------
# WaveExtrapolator.fetch_correction tests
# ---------------------------------------------------------------------------


def test_fetch_correction_returns_float(wave):
    result = wave.fetch_correction(2.5, 500.0, 200.0)
    assert isinstance(result, float)


def test_fetch_correction_scales_with_sqrt_ratio(wave):
    Hs = 2.0
    f_src = 400.0
    f_tgt = 100.0
    expected = Hs * math.sqrt(f_tgt / f_src)
    result = wave.fetch_correction(Hs, f_src, f_tgt)
    assert result == pytest.approx(expected, rel=1e-6)


def test_fetch_correction_equal_fetch_is_identity(wave):
    Hs = 3.0
    result = wave.fetch_correction(Hs, 500.0, 500.0)
    assert result == pytest.approx(Hs, rel=1e-6)


def test_fetch_correction_larger_target_fetch_increases_hs(wave):
    result = wave.fetch_correction(2.0, 100.0, 400.0)
    assert result > 2.0


def test_fetch_correction_raises_on_zero_fetch_source(wave):
    with pytest.raises(ValueError):
        wave.fetch_correction(2.0, 0.0, 400.0)


# ---------------------------------------------------------------------------
# WaveExtrapolator.transfer tests
# ---------------------------------------------------------------------------


def test_transfer_returns_tuple(wave):
    ctx = _make_context(depth_ratio=1.0, sheltering=1.0)
    result = wave.transfer(2.5, 9.0, ctx)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_transfer_returns_positive_hs_and_tp(wave):
    ctx = _make_context(depth_ratio=0.4, sheltering=0.75)
    Hs_t, Tp_t = wave.transfer(2.5, 9.0, ctx)
    assert Hs_t > 0.0
    assert Tp_t > 0.0


def test_transfer_no_correction_with_identity_context(wave):
    ctx = _make_context(depth_ratio=1.0, sheltering=1.0)
    Hs_t, Tp_t = wave.transfer(2.5, 9.0, ctx)
    assert Hs_t == pytest.approx(2.5, rel=1e-6)
    assert Tp_t == pytest.approx(9.0, rel=1e-6)


def test_transfer_raises_on_non_positive_hs(wave):
    ctx = _make_context()
    with pytest.raises(ValueError):
        wave.transfer(0.0, 9.0, ctx)


def test_transfer_sheltering_reduces_hs(wave):
    ctx_open = _make_context(sheltering=1.0, depth_ratio=1.0)
    ctx_shelter = _make_context(sheltering=0.6, depth_ratio=1.0)
    Hs_open, _ = wave.transfer(2.5, 9.0, ctx_open)
    Hs_shelter, _ = wave.transfer(2.5, 9.0, ctx_shelter)
    assert Hs_shelter < Hs_open


# ---------------------------------------------------------------------------
# CurrentExtrapolator.depth_scaling tests
# ---------------------------------------------------------------------------


def test_depth_scaling_surface_returns_surface_speed(current):
    U = current.depth_scaling(1.0, z_target=0.0, z_total=100.0)
    assert U == pytest.approx(1.0, rel=1e-6)


def test_depth_scaling_log_returns_positive(current):
    U = current.depth_scaling(1.0, z_target=20.0, z_total=100.0, profile="log")
    assert U > 0.0


def test_depth_scaling_power_returns_positive(current):
    U = current.depth_scaling(1.0, z_target=20.0, z_total=100.0, profile="power")
    assert U > 0.0


def test_depth_scaling_log_decreases_with_depth(current):
    U0 = current.depth_scaling(1.0, z_target=5.0, z_total=100.0, profile="log")
    U1 = current.depth_scaling(1.0, z_target=50.0, z_total=100.0, profile="log")
    assert U0 > U1


def test_depth_scaling_at_bottom_returns_zero(current):
    U = current.depth_scaling(1.0, z_target=100.0, z_total=100.0)
    assert U == pytest.approx(0.0, abs=1e-6)


def test_depth_scaling_result_at_most_surface_speed(current):
    U_surf = 1.5
    for z in [0, 10, 30, 60, 90]:
        U = current.depth_scaling(U_surf, z_target=z, z_total=100.0)
        assert U <= U_surf + 1e-9


def test_depth_scaling_raises_negative_surface(current):
    with pytest.raises(ValueError):
        current.depth_scaling(-0.1, z_target=10.0, z_total=100.0)


# ---------------------------------------------------------------------------
# CurrentExtrapolator.tidal_scaling tests
# ---------------------------------------------------------------------------


def test_tidal_scaling_returns_positive(current):
    result = current.tidal_scaling(0.5, 50.0, 100.0)
    assert result > 0.0


def test_tidal_scaling_shallower_target_increases_speed(current):
    # Moving to shallower water: mass conservation increases current
    U_deep = current.tidal_scaling(0.5, 100.0, 50.0)
    assert U_deep > 0.5


def test_tidal_scaling_deeper_target_decreases_speed(current):
    U = current.tidal_scaling(0.5, 50.0, 100.0)
    assert U < 0.5


def test_tidal_scaling_same_depth_identity(current):
    U = current.tidal_scaling(0.5, 100.0, 100.0)
    assert U == pytest.approx(0.5, rel=1e-6)


def test_tidal_scaling_raises_on_zero_depth(current):
    with pytest.raises(ValueError):
        current.tidal_scaling(0.5, 0.0, 100.0)


# ---------------------------------------------------------------------------
# CurrentExtrapolator.transfer tests
# ---------------------------------------------------------------------------


def test_current_transfer_returns_float(current):
    ctx = _make_context(depth_ratio=1.0, sheltering=1.0)
    result = current.transfer(0.5, ctx)
    assert isinstance(result, float)


def test_current_transfer_positive(current):
    ctx = _make_context(depth_ratio=0.4, sheltering=0.75)
    result = current.transfer(0.5, ctx)
    assert result >= 0.0


def test_current_transfer_no_correction_reduces_by_sheltering(current):
    ctx = _make_context(depth_ratio=1.0, sheltering=0.8)
    result = current.transfer(1.0, ctx)
    # Sheltering should reduce current relative to source
    assert result < 1.0


def test_current_transfer_raises_on_negative_speed(current):
    ctx = _make_context()
    with pytest.raises(ValueError):
        current.transfer(-0.1, ctx)
