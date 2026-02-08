# ABOUTME: Tests for metocean unit converter.
# ABOUTME: Validates conversion functions for speed, length, temperature, and pressure.

"""Tests for unit converter"""

import pytest

from worldenergydata.metocean.processors.unit_converter import (
    LengthUnit,
    PressureUnit,
    SpeedUnit,
    TempUnit,
    UnitConverter,
)


class TestSpeedConversion:
    """Tests for speed unit conversions."""

    def test_knots_to_ms(self):
        """Test knots to m/s conversion."""
        result = UnitConverter.speed_to_ms(10.0, SpeedUnit.KTS)
        assert pytest.approx(result, rel=0.001) == 5.14444

    def test_kmh_to_ms(self):
        """Test km/h to m/s conversion."""
        result = UnitConverter.speed_to_ms(36.0, SpeedUnit.KMH)
        assert pytest.approx(result, rel=0.001) == 10.0

    def test_mph_to_ms(self):
        """Test mph to m/s conversion."""
        result = UnitConverter.speed_to_ms(10.0, SpeedUnit.MPH)
        assert pytest.approx(result, rel=0.001) == 4.4704

    def test_fps_to_ms(self):
        """Test ft/s to m/s conversion."""
        result = UnitConverter.speed_to_ms(10.0, SpeedUnit.FPS)
        assert pytest.approx(result, rel=0.001) == 3.048

    def test_ms_to_ms(self):
        """Test m/s to m/s (no conversion)."""
        result = UnitConverter.speed_to_ms(10.0, SpeedUnit.MS)
        assert result == 10.0

    def test_speed_none_input(self):
        """Test that None input returns None."""
        result = UnitConverter.speed_to_ms(None, SpeedUnit.KTS)
        assert result is None

    def test_ms_to_knots(self):
        """Test m/s to knots conversion."""
        result = UnitConverter.ms_to_speed(5.14444, SpeedUnit.KTS)
        assert pytest.approx(result, rel=0.001) == 10.0


class TestLengthConversion:
    """Tests for length unit conversions."""

    def test_feet_to_meters(self):
        """Test feet to meters conversion."""
        result = UnitConverter.length_to_m(10.0, LengthUnit.FT)
        assert pytest.approx(result, rel=0.001) == 3.048

    def test_inches_to_meters(self):
        """Test inches to meters conversion."""
        result = UnitConverter.length_to_m(100.0, LengthUnit.IN)
        assert pytest.approx(result, rel=0.001) == 2.54

    def test_cm_to_meters(self):
        """Test centimeters to meters conversion."""
        result = UnitConverter.length_to_m(100.0, LengthUnit.CM)
        assert result == 1.0

    def test_mm_to_meters(self):
        """Test millimeters to meters conversion."""
        result = UnitConverter.length_to_m(1000.0, LengthUnit.MM)
        assert result == 1.0

    def test_nm_to_meters(self):
        """Test nautical miles to meters conversion."""
        result = UnitConverter.length_to_m(1.0, LengthUnit.NM)
        assert result == 1852.0

    def test_km_to_meters(self):
        """Test kilometers to meters conversion."""
        result = UnitConverter.length_to_m(1.0, LengthUnit.KM)
        assert result == 1000.0

    def test_m_to_m(self):
        """Test meters to meters (no conversion)."""
        result = UnitConverter.length_to_m(10.0, LengthUnit.M)
        assert result == 10.0

    def test_length_none_input(self):
        """Test that None input returns None."""
        result = UnitConverter.length_to_m(None, LengthUnit.FT)
        assert result is None

    def test_meters_to_feet(self):
        """Test meters to feet conversion."""
        result = UnitConverter.m_to_length(3.048, LengthUnit.FT)
        assert pytest.approx(result, rel=0.001) == 10.0


class TestTemperatureConversion:
    """Tests for temperature unit conversions."""

    def test_fahrenheit_to_celsius(self):
        """Test Fahrenheit to Celsius conversion."""
        result = UnitConverter.temp_to_celsius(68.0, TempUnit.F)
        assert pytest.approx(result, rel=0.001) == 20.0

    def test_fahrenheit_to_celsius_freezing(self):
        """Test Fahrenheit to Celsius at freezing point."""
        result = UnitConverter.temp_to_celsius(32.0, TempUnit.F)
        assert pytest.approx(result, rel=0.001) == 0.0

    def test_fahrenheit_to_celsius_boiling(self):
        """Test Fahrenheit to Celsius at boiling point."""
        result = UnitConverter.temp_to_celsius(212.0, TempUnit.F)
        assert pytest.approx(result, rel=0.001) == 100.0

    def test_kelvin_to_celsius(self):
        """Test Kelvin to Celsius conversion."""
        result = UnitConverter.temp_to_celsius(293.15, TempUnit.K)
        assert pytest.approx(result, rel=0.001) == 20.0

    def test_kelvin_to_celsius_absolute_zero(self):
        """Test Kelvin to Celsius at absolute zero."""
        result = UnitConverter.temp_to_celsius(0.0, TempUnit.K)
        assert pytest.approx(result, rel=0.001) == -273.15

    def test_celsius_to_celsius(self):
        """Test Celsius to Celsius (no conversion)."""
        result = UnitConverter.temp_to_celsius(20.0, TempUnit.C)
        assert result == 20.0

    def test_temp_none_input(self):
        """Test that None input returns None."""
        result = UnitConverter.temp_to_celsius(None, TempUnit.F)
        assert result is None

    def test_celsius_to_fahrenheit(self):
        """Test Celsius to Fahrenheit conversion."""
        result = UnitConverter.celsius_to_temp(20.0, TempUnit.F)
        assert pytest.approx(result, rel=0.001) == 68.0

    def test_celsius_to_kelvin(self):
        """Test Celsius to Kelvin conversion."""
        result = UnitConverter.celsius_to_temp(20.0, TempUnit.K)
        assert pytest.approx(result, rel=0.001) == 293.15


class TestPressureConversion:
    """Tests for pressure unit conversions."""

    def test_pa_to_hpa(self):
        """Test Pascals to hPa conversion."""
        result = UnitConverter.pressure_to_hpa(101325.0, PressureUnit.PA)
        assert pytest.approx(result, rel=0.001) == 1013.25

    def test_kpa_to_hpa(self):
        """Test kPa to hPa conversion."""
        result = UnitConverter.pressure_to_hpa(101.325, PressureUnit.KPA)
        assert pytest.approx(result, rel=0.001) == 1013.25

    def test_inhg_to_hpa(self):
        """Test inches of mercury to hPa conversion."""
        result = UnitConverter.pressure_to_hpa(29.92, PressureUnit.INHG)
        assert pytest.approx(result, rel=0.01) == 1013.25

    def test_mmhg_to_hpa(self):
        """Test mm of mercury to hPa conversion."""
        result = UnitConverter.pressure_to_hpa(760.0, PressureUnit.MMHG)
        assert pytest.approx(result, rel=0.01) == 1013.25

    def test_atm_to_hpa(self):
        """Test atmospheres to hPa conversion."""
        result = UnitConverter.pressure_to_hpa(1.0, PressureUnit.ATM)
        assert result == 1013.25

    def test_psi_to_hpa(self):
        """Test PSI to hPa conversion."""
        result = UnitConverter.pressure_to_hpa(14.696, PressureUnit.PSI)
        assert pytest.approx(result, rel=0.01) == 1013.25

    def test_mb_to_hpa(self):
        """Test millibars to hPa (1:1 ratio)."""
        result = UnitConverter.pressure_to_hpa(1013.25, PressureUnit.MB)
        assert result == 1013.25

    def test_hpa_to_hpa(self):
        """Test hPa to hPa (no conversion)."""
        result = UnitConverter.pressure_to_hpa(1013.25, PressureUnit.HPA)
        assert result == 1013.25

    def test_pressure_none_input(self):
        """Test that None input returns None."""
        result = UnitConverter.pressure_to_hpa(None, PressureUnit.PA)
        assert result is None


class TestDirectionNormalization:
    """Tests for direction normalization."""

    def test_normalize_direction_positive(self):
        """Test normalization of positive direction."""
        assert UnitConverter.normalize_direction(450) == 90

    def test_normalize_direction_negative(self):
        """Test normalization of negative direction."""
        assert UnitConverter.normalize_direction(-90) == 270

    def test_normalize_direction_zero(self):
        """Test normalization of zero direction."""
        assert UnitConverter.normalize_direction(0) == 0

    def test_normalize_direction_360(self):
        """Test normalization of 360 degrees."""
        assert UnitConverter.normalize_direction(360) == 0

    def test_normalize_direction_large(self):
        """Test normalization of large direction value."""
        assert UnitConverter.normalize_direction(720) == 0
        assert UnitConverter.normalize_direction(810) == 90

    def test_normalize_direction_none(self):
        """Test that None input returns None."""
        result = UnitConverter.normalize_direction(None)
        assert result is None

    def test_direction_from_to(self):
        """Test conversion from 'from' direction to 'to' direction."""
        # Wind coming from North (0) goes to South (180)
        assert UnitConverter.direction_from_to(0) == 180
        # Wind coming from East (90) goes to West (270)
        assert UnitConverter.direction_from_to(90) == 270
        # Wind coming from South (180) goes to North (0)
        assert UnitConverter.direction_from_to(180) == 0
        # Wind coming from West (270) goes to East (90)
        assert UnitConverter.direction_from_to(270) == 90

    def test_direction_from_to_none(self):
        """Test that None input returns None."""
        result = UnitConverter.direction_from_to(None)
        assert result is None


class TestUnknownUnits:
    """Tests for handling unknown units."""

    def test_unknown_speed_unit_raises(self):
        """Test that unknown speed unit raises ValueError."""
        with pytest.raises(ValueError, match="Unknown speed unit"):
            UnitConverter.speed_to_ms(10.0, "unknown")

    def test_unknown_length_unit_raises(self):
        """Test that unknown length unit raises ValueError."""
        with pytest.raises(ValueError, match="Unknown length unit"):
            UnitConverter.length_to_m(10.0, "unknown")

    def test_unknown_temp_unit_raises(self):
        """Test that unknown temperature unit raises ValueError."""
        with pytest.raises(ValueError, match="Unknown temperature unit"):
            UnitConverter.temp_to_celsius(10.0, "unknown")

    def test_unknown_pressure_unit_raises(self):
        """Test that unknown pressure unit raises ValueError."""
        with pytest.raises(ValueError, match="Unknown pressure unit"):
            UnitConverter.pressure_to_hpa(10.0, "unknown")
