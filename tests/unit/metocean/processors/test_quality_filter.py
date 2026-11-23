"""Tests for metocean quality filter."""

from types import SimpleNamespace

from worldenergydata.metocean.constants import MetoceanParameter, QualityFlag
from worldenergydata.metocean.processors.quality_filter import (
    QualityCheckResult,
    QualityFilter,
)


class TestQualityCheckResult:
    def test_passed(self):
        r = QualityCheckResult(passed=True, flag=QualityFlag.GOOD)
        assert r.passed is True
        assert r.flag == QualityFlag.GOOD
        assert r.reason is None

    def test_failed_with_reason(self):
        r = QualityCheckResult(
            passed=False, flag=QualityFlag.BAD, reason="out of range"
        )
        assert r.passed is False
        assert r.reason == "out of range"


class TestCheckRange:
    def test_none_value_returns_missing(self):
        r = QualityFilter.check_range(MetoceanParameter.WAVE_HEIGHT, None)
        assert r.passed is True
        assert r.flag == QualityFlag.MISSING

    def test_valid_wave_height(self):
        r = QualityFilter.check_range(MetoceanParameter.WAVE_HEIGHT, 5.0)
        assert r.passed is True
        assert r.flag == QualityFlag.GOOD

    def test_invalid_wave_height_too_high(self):
        r = QualityFilter.check_range(MetoceanParameter.WAVE_HEIGHT, 35.0)
        assert r.passed is False
        assert r.flag == QualityFlag.BAD

    def test_invalid_wave_height_negative(self):
        r = QualityFilter.check_range(MetoceanParameter.WAVE_HEIGHT, -1.0)
        assert r.passed is False
        assert r.flag == QualityFlag.BAD

    def test_boundary_zero(self):
        r = QualityFilter.check_range(MetoceanParameter.WAVE_HEIGHT, 0)
        assert r.passed is True

    def test_boundary_max(self):
        r = QualityFilter.check_range(MetoceanParameter.WAVE_HEIGHT, 30)
        assert r.passed is True

    def test_valid_wind_speed(self):
        r = QualityFilter.check_range(MetoceanParameter.WIND_SPEED, 25.0)
        assert r.passed is True

    def test_invalid_wind_speed(self):
        r = QualityFilter.check_range(MetoceanParameter.WIND_SPEED, 110.0)
        assert r.passed is False

    def test_valid_pressure(self):
        r = QualityFilter.check_range(MetoceanParameter.PRESSURE, 1013.0)
        assert r.passed is True

    def test_invalid_pressure_too_low(self):
        r = QualityFilter.check_range(MetoceanParameter.PRESSURE, 800.0)
        assert r.passed is False

    def test_valid_sst(self):
        r = QualityFilter.check_range(MetoceanParameter.SEA_SURFACE_TEMP, 20.0)
        assert r.passed is True

    def test_valid_sst_negative(self):
        # SST can be -2 (polar regions)
        r = QualityFilter.check_range(MetoceanParameter.SEA_SURFACE_TEMP, -2.0)
        assert r.passed is True

    def test_valid_current_speed(self):
        r = QualityFilter.check_range(MetoceanParameter.CURRENT_SPEED, 2.0)
        assert r.passed is True

    def test_invalid_current_speed(self):
        r = QualityFilter.check_range(MetoceanParameter.CURRENT_SPEED, 6.0)
        assert r.passed is False

    def test_direction_range(self):
        r = QualityFilter.check_range(MetoceanParameter.WAVE_DIRECTION, 180.0)
        assert r.passed is True

    def test_direction_boundary_360(self):
        r = QualityFilter.check_range(MetoceanParameter.WAVE_DIRECTION, 360.0)
        assert r.passed is True


class TestCheckRangeByName:
    def test_none_value(self):
        r = QualityFilter.check_range_by_name("wave_height", None)
        assert r.flag == QualityFlag.MISSING

    def test_unknown_parameter(self):
        r = QualityFilter.check_range_by_name("unknown_param", 5.0)
        assert r.passed is True
        assert r.flag == QualityFlag.GOOD


class TestCheckSpike:
    def test_no_spike(self):
        r = QualityFilter.check_spike(MetoceanParameter.WAVE_HEIGHT, 5.0, 4.0, 1.0)
        assert r.passed is True
        assert r.flag == QualityFlag.GOOD

    def test_spike_detected(self):
        # Max change for wave height is 2m/hour; 10m change in 1 hour
        r = QualityFilter.check_spike(MetoceanParameter.WAVE_HEIGHT, 15.0, 5.0, 1.0)
        assert r.passed is False
        assert r.flag == QualityFlag.SUSPECT

    def test_no_limit_defined(self):
        # WAVE_DIRECTION has no spike limit
        r = QualityFilter.check_spike(
            MetoceanParameter.WAVE_DIRECTION, 180.0, 10.0, 1.0
        )
        assert r.passed is True

    def test_wind_speed_spike(self):
        # Max change for wind speed is 20 m/s/hour
        r = QualityFilter.check_spike(MetoceanParameter.WIND_SPEED, 50.0, 10.0, 1.0)
        assert r.passed is False

    def test_wind_speed_no_spike(self):
        r = QualityFilter.check_spike(MetoceanParameter.WIND_SPEED, 15.0, 10.0, 1.0)
        assert r.passed is True

    def test_very_small_time_diff(self):
        # time_diff < 0.1 should be clamped to 0.1
        r = QualityFilter.check_spike(MetoceanParameter.WAVE_HEIGHT, 5.0, 4.9, 0.001)
        assert r.passed is True


class TestCheckDirectionConsistency:
    def test_both_none(self):
        r = QualityFilter.check_direction_consistency(None, None)
        assert r.passed is True
        assert r.flag == QualityFlag.MISSING

    def test_valid_speed_and_direction(self):
        r = QualityFilter.check_direction_consistency(5.0, 180.0)
        assert r.passed is True
        assert r.flag == QualityFlag.GOOD

    def test_zero_speed_with_direction(self):
        r = QualityFilter.check_direction_consistency(0.01, 90.0)
        assert r.passed is False
        assert r.flag == QualityFlag.SUSPECT

    def test_speed_none_direction_present(self):
        r = QualityFilter.check_direction_consistency(None, 90.0)
        assert r.passed is True


class TestCheckWaveConsistency:
    def test_both_none(self):
        r = QualityFilter.check_wave_consistency(None, None)
        assert r.passed is True

    def test_height_none(self):
        r = QualityFilter.check_wave_consistency(None, 8.0)
        assert r.passed is True

    def test_valid_wave(self):
        r = QualityFilter.check_wave_consistency(2.0, 8.0)
        assert r.passed is True

    def test_period_too_short(self):
        r = QualityFilter.check_wave_consistency(1.0, 0.5)
        assert r.passed is False
        assert r.flag == QualityFlag.BAD

    def test_steep_wave(self):
        # Very steep: large height, short period
        r = QualityFilter.check_wave_consistency(5.0, 2.0)
        assert r.passed is False
        assert r.flag == QualityFlag.SUSPECT


class TestGetOverallFlag:
    def test_empty_list(self):
        assert QualityFilter.get_overall_flag([]) == QualityFlag.GOOD

    def test_all_good(self):
        flags = [QualityFlag.GOOD, QualityFlag.GOOD]
        assert QualityFilter.get_overall_flag(flags) == QualityFlag.GOOD

    def test_bad_overrides(self):
        flags = [QualityFlag.GOOD, QualityFlag.BAD, QualityFlag.SUSPECT]
        assert QualityFilter.get_overall_flag(flags) == QualityFlag.BAD

    def test_suspect_overrides_missing(self):
        flags = [QualityFlag.GOOD, QualityFlag.SUSPECT, QualityFlag.MISSING]
        assert QualityFilter.get_overall_flag(flags) == QualityFlag.SUSPECT

    def test_missing_overrides_good(self):
        flags = [QualityFlag.GOOD, QualityFlag.MISSING]
        assert QualityFilter.get_overall_flag(flags) == QualityFlag.MISSING


class TestFilterObservations:
    def test_exclude_bad(self):
        obs = [
            SimpleNamespace(quality_flag=QualityFlag.GOOD, value=1),
            SimpleNamespace(quality_flag=QualityFlag.BAD, value=2),
            SimpleNamespace(quality_flag=QualityFlag.SUSPECT, value=3),
        ]
        result = QualityFilter.filter_observations(obs, exclude_bad=True)
        assert len(result) == 2

    def test_exclude_bad_and_suspect(self):
        obs = [
            SimpleNamespace(quality_flag=QualityFlag.GOOD, value=1),
            SimpleNamespace(quality_flag=QualityFlag.BAD, value=2),
            SimpleNamespace(quality_flag=QualityFlag.SUSPECT, value=3),
        ]
        result = QualityFilter.filter_observations(
            obs, exclude_bad=True, exclude_suspect=True
        )
        assert len(result) == 1

    def test_no_flag_defaults_good(self):
        obs = [SimpleNamespace(value=1)]
        result = QualityFilter.filter_observations(obs, exclude_bad=True)
        assert len(result) == 1

    def test_empty_list(self):
        result = QualityFilter.filter_observations([])
        assert result == []


class TestValidateObservation:
    def test_all_valid(self):
        flag, issues = QualityFilter.validate_observation(
            wave_height=2.0,
            wave_period=8.0,
            wave_direction=180.0,
            wind_speed=10.0,
            wind_direction=180.0,
            current_speed=1.0,
            current_direction=90.0,
            sea_surface_temp=20.0,
            pressure=1013.0,
            water_level=0.5,
        )
        assert flag == QualityFlag.GOOD
        assert len(issues) == 0

    def test_invalid_wave_height(self):
        flag, issues = QualityFilter.validate_observation(wave_height=50.0)
        assert flag == QualityFlag.BAD
        assert len(issues) > 0

    def test_all_none(self):
        flag, issues = QualityFilter.validate_observation()
        # All missing values
        assert flag in (QualityFlag.MISSING, QualityFlag.GOOD)

    def test_inconsistent_wind(self):
        flag, issues = QualityFilter.validate_observation(
            wind_speed=0.01, wind_direction=180.0
        )
        assert len(issues) > 0

    def test_steep_wave_detected(self):
        flag, issues = QualityFilter.validate_observation(
            wave_height=5.0, wave_period=2.0
        )
        assert len(issues) > 0
