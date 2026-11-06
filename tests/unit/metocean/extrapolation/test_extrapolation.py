# ABOUTME: Tests for the top-level extrapolate() function and ExtrapolationResult.
# ABOUTME: Covers GoM, North Sea, and Pacific locations; all-offline, no API calls.

"""
Tests for worldenergydata.metocean.extrapolation (public API)
"""

import json
from dataclasses import asdict, replace
from unittest.mock import Mock

import pytest

from worldenergydata.metocean.extrapolation import (
    ExtrapolationResult,
    extrapolate,
)
from worldenergydata.metocean.extrapolation.source_catalog import MetoceanSource

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_CONFIDENCE = {"high", "medium", "low"}


def _check_result(result: ExtrapolationResult) -> None:
    """Assert all required fields are present and physically valid."""
    assert isinstance(result, ExtrapolationResult)
    assert isinstance(result.target_lat, float)
    assert isinstance(result.target_lon, float)
    assert isinstance(result.source_used, MetoceanSource)
    assert result.distance_km >= 0.0
    assert result.Hs_m > 0.0
    assert result.Tp_s > 0.0
    assert result.wind_speed_ms >= 0.0
    assert result.current_speed_ms >= 0.0
    assert result.confidence in _VALID_CONFIDENCE
    assert isinstance(result.corrections_applied, list)
    assert isinstance(result.source, str)
    assert len(result.source) > 0


# ---------------------------------------------------------------------------
# Basic return type tests
# ---------------------------------------------------------------------------


def test_extrapolate_returns_result():
    result = extrapolate(28.5, -88.5)
    assert isinstance(result, ExtrapolationResult)


def test_extrapolate_result_has_all_fields():
    result = extrapolate(28.5, -88.5)
    _check_result(result)


def test_extrapolate_target_lat_preserved():
    result = extrapolate(28.5, -88.5)
    assert result.target_lat == 28.5


def test_extrapolate_target_lon_preserved():
    result = extrapolate(28.5, -88.5)
    assert result.target_lon == -88.5


# ---------------------------------------------------------------------------
# Physical plausibility
# ---------------------------------------------------------------------------


def test_extrapolate_hs_positive():
    result = extrapolate(28.5, -88.5)
    assert result.Hs_m > 0.0


def test_extrapolate_tp_positive():
    result = extrapolate(28.5, -88.5)
    assert result.Tp_s > 0.0


def test_extrapolate_hs_reasonable_range():
    # Expect open-ocean Hs between 0.1 m and 20 m for synthetic baseline
    result = extrapolate(28.5, -88.5)
    assert 0.01 <= result.Hs_m <= 20.0


def test_extrapolate_tp_reasonable_range():
    result = extrapolate(28.5, -88.5)
    assert 1.0 <= result.Tp_s <= 30.0


def test_extrapolate_wind_non_negative():
    result = extrapolate(28.5, -88.5)
    assert result.wind_speed_ms >= 0.0


def test_extrapolate_current_non_negative():
    result = extrapolate(28.5, -88.5)
    assert result.current_speed_ms >= 0.0


# ---------------------------------------------------------------------------
# confidence field
# ---------------------------------------------------------------------------


def test_extrapolate_confidence_valid():
    result = extrapolate(28.5, -88.5)
    assert result.confidence in _VALID_CONFIDENCE


def test_extrapolate_corrections_is_list():
    result = extrapolate(28.5, -88.5)
    assert isinstance(result.corrections_applied, list)


# ---------------------------------------------------------------------------
# Geographic locations
# ---------------------------------------------------------------------------


def test_extrapolate_gom_location():
    result = extrapolate(28.5, -88.5)
    _check_result(result)


def test_extrapolate_north_sea_location():
    result = extrapolate(57.0, 2.0)
    _check_result(result)


def test_extrapolate_pacific_location():
    result = extrapolate(20.0, -150.0)
    _check_result(result)


def test_extrapolate_equatorial_location():
    result = extrapolate(0.0, 0.0)
    _check_result(result)


def test_extrapolate_high_latitude():
    result = extrapolate(70.0, 5.0)
    _check_result(result)


# ---------------------------------------------------------------------------
# method parameter
# ---------------------------------------------------------------------------


def test_extrapolate_nearest_method():
    result = extrapolate(28.5, -88.5, method="nearest")
    _check_result(result)


def test_extrapolate_weighted_average_method():
    result = extrapolate(28.5, -88.5, method="weighted_average")
    _check_result(result)


def test_extrapolate_default_method_is_nearest():
    result_default = extrapolate(28.5, -88.5)
    result_nearest = extrapolate(28.5, -88.5, method="nearest")
    assert result_default.source == result_nearest.source


def test_extrapolate_invalid_method_raises():
    with pytest.raises(ValueError, match="method"):
        extrapolate(28.5, -88.5, method="bad_method")


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_extrapolate_invalid_lat_raises():
    with pytest.raises(ValueError):
        extrapolate(91.0, 0.0)


def test_extrapolate_invalid_lon_raises():
    with pytest.raises(ValueError):
        extrapolate(0.0, 181.0)


def test_extrapolate_negative_lat_lon():
    # Southern hemisphere / western hemisphere — valid
    result = extrapolate(-30.0, -60.0)
    _check_result(result)


# ---------------------------------------------------------------------------
# ExtrapolationResult dataclass validation
# ---------------------------------------------------------------------------


def test_extrapolation_result_invalid_confidence_raises():
    src = MetoceanSource(
        name="test",
        source_type="buoy",
        lat=28.5,
        lon=-88.5,
        coverage_radius_km=200.0,
        parameters=["Hs"],
        priority=1,
        region="gom",
    )
    with pytest.raises(ValueError, match="confidence"):
        ExtrapolationResult(
            target_lat=28.5,
            target_lon=-88.5,
            source_used=src,
            distance_km=50.0,
            Hs_m=2.5,
            Tp_s=9.0,
            wind_speed_ms=10.0,
            current_speed_ms=0.3,
            confidence="bad_value",
            corrections_applied=[],
        )


def test_extrapolation_result_source_auto_populated():
    src = MetoceanSource(
        name="ndbc_42001",
        source_type="buoy",
        lat=25.9,
        lon=-89.7,
        coverage_radius_km=200.0,
        parameters=["Hs"],
        priority=1,
        region="gom",
    )
    result = ExtrapolationResult(
        target_lat=28.5,
        target_lon=-88.5,
        source_used=src,
        distance_km=100.0,
        Hs_m=2.5,
        Tp_s=9.0,
        wind_speed_ms=10.0,
        current_speed_ms=0.3,
        confidence="medium",
        corrections_applied=[],
    )
    assert result.source == "ndbc_42001"
    assert result.data_basis == "unknown"


@pytest.mark.parametrize("method", ["nearest", "weighted_average"])
@pytest.mark.parametrize("source_type", ["buoy", "tide_gauge", "model", "reanalysis"])
@pytest.mark.parametrize("correction_needed", [False, True])
def test_extrapolation_reports_synthetic_basis_and_actual_transfer(
    monkeypatch, method, source_type, correction_needed
):
    """Metadata oracle: no observations enter either facade method.

    Source: calibration/README.md, Methods and API, synthetic-baseline paragraph.
    Therefore the data basis is synthetic even for a buoy catalogue entry.
    A forced assessment selects each branch: transfer labels must appear iff
    the wave and current transfer functions run. No numerical accuracy or
    engineering acceptance limit is asserted by this metadata test.
    """
    import worldenergydata.metocean.extrapolation as api

    source = MetoceanSource("synthetic_grid", source_type, 0.0, 0.0, 500)
    monkeypatch.setattr(api._finder, "find_nearest", lambda *args, **kwargs: [source])
    context = replace(
        api._assessor.assess(28.5, -88.5, source),
        correction_needed=correction_needed,
    )
    monkeypatch.setattr(api._assessor, "assess", lambda *args: context)
    wave_transfer = Mock(wraps=api._wave_model.transfer)
    current_transfer = Mock(wraps=api._current_model.transfer)
    monkeypatch.setattr(api._wave_model, "transfer", wave_transfer)
    monkeypatch.setattr(api._current_model, "transfer", current_transfer)

    result = extrapolate(28.5, -88.5, method=method)

    assert result.source_used is source
    assert result.source == source.name
    assert result.data_basis == "synthetic_baseline"
    assert asdict(result)["data_basis"] == "synthetic_baseline"
    assert not any("bias_correction" in c for c in result.corrections_applied)
    assert ("spatial_transfer" in result.corrections_applied) == correction_needed
    assert wave_transfer.called == correction_needed
    assert current_transfer.called == correction_needed


@pytest.mark.parametrize("data_basis", ["synthetic_basline", "observed", "", None, []])
def test_extrapolation_result_rejects_invalid_data_basis(data_basis):
    with pytest.raises(ValueError, match="data_basis"):
        replace(extrapolate(28.5, -88.5), data_basis=data_basis)


@pytest.mark.parametrize("data_basis", ["synthetic_baseline", "unknown"])
def test_extrapolation_result_accepts_supported_data_basis(data_basis):
    result = replace(extrapolate(28.5, -88.5), data_basis=data_basis)
    assert result.data_basis == data_basis


@pytest.mark.parametrize("data_basis", ["synthetic_baseline", "unknown"])
def test_correction_breakdown_preserves_data_basis_in_export(data_basis):
    from worldenergydata.metocean.extrapolation.visualization import (
        plot_correction_breakdown,
    )

    result = replace(extrapolate(28.5, -88.5), data_basis=data_basis)
    exported = json.loads(plot_correction_breakdown(result).to_json())

    assert f"Basis: {data_basis}" in exported["layout"]["title"]["text"]
    expected_target = (
        "Target (synthetic baseline)"
        if data_basis == "synthetic_baseline"
        else "Target"
    )
    assert [trace["name"] for trace in exported["data"]] == [
        "Synthetic baseline",
        expected_target,
    ]


def test_correction_breakdown_uses_shared_baseline(monkeypatch):
    import worldenergydata.metocean.extrapolation as api
    from worldenergydata.metocean.extrapolation.visualization import (
        plot_correction_breakdown,
    )

    # Controlled demonstration inputs test the consumer, not engineering accuracy.
    for key, value in zip(
        ["Hs", "Tp", "wind_speed", "current_speed"], [4.0, 7.0, 12.0, 0.5]
    ):
        monkeypatch.setitem(api._BASELINE, key, value)
    result = extrapolate(28.5, -88.5)
    figure = plot_correction_breakdown(result)

    assert list(figure.data[0].x) == ["Hs (m)", "Tp (s)", "Wind (m/s)", "Current (m/s)"]
    assert list(figure.data[0].y) == [4.0, 7.0, 12.0, 0.5]
    assert list(figure.data[1].y) == [
        result.Hs_m,
        result.Tp_s,
        result.wind_speed_ms,
        result.current_speed_ms,
    ]
