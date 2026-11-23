"""Tests for metocean unit converter."""

import pytest

from worldenergydata.metocean.processors.unit_converter import (
    LengthUnit,
    PressureUnit,
    SpeedUnit,
    TempUnit,
    UnitConverter,
)


class TestSpeedUnit:
    def test_values(self):
        assert SpeedUnit.MS.value == "m/s"
        assert SpeedUnit.KTS.value == "knots"
        assert SpeedUnit.KMH.value == "km/h"
        assert SpeedUnit.MPH.value == "mph"
        assert SpeedUnit.FPS.value == "ft/s"

    def test_count(self):
        assert len(SpeedUnit) == 5


class TestLengthUnit:
    def test_values(self):
        assert LengthUnit.M.value == "m"
        assert LengthUnit.FT.value == "feet"
        assert LengthUnit.NM.value == "nm"

    def test_count(self):
        assert len(LengthUnit) == 7


class TestTempUnit:
    def test_values(self):
        assert TempUnit.C.value == "celsius"
        assert TempUnit.F.value == "fahrenheit"
        assert TempUnit.K.value == "kelvin"


class TestPressureUnit:
    def test_values(self):
        assert PressureUnit.HPA.value == "hPa"
        assert PressureUnit.ATM.value == "atm"
        assert PressureUnit.PSI.value == "psi"

    def test_count(self):
        assert len(PressureUnit) == 8


class TestSpeedConversion:
    def test_ms_to_ms(self):
        assert UnitConverter.speed_to_ms(10.0, SpeedUnit.MS) == 10.0

    def test_knots_to_ms(self):
        result = UnitConverter.speed_to_ms(1.0, SpeedUnit.KTS)
        assert abs(result - 0.514444) < 0.001

    def test_kmh_to_ms(self):
        result = UnitConverter.speed_to_ms(3.6, SpeedUnit.KMH)
        assert abs(result - 1.0) < 0.01

    def test_mph_to_ms(self):
        result = UnitConverter.speed_to_ms(1.0, SpeedUnit.MPH)
        assert abs(result - 0.44704) < 0.001

    def test_fps_to_ms(self):
        result = UnitConverter.speed_to_ms(1.0, SpeedUnit.FPS)
        assert abs(result - 0.3048) < 0.001

    def test_none_returns_none(self):
        assert UnitConverter.speed_to_ms(None, SpeedUnit.KTS) is None

    def test_roundtrip_knots(self):
        original = 25.0
        ms = UnitConverter.speed_to_ms(original, SpeedUnit.KTS)
        back = UnitConverter.ms_to_speed(ms, SpeedUnit.KTS)
        assert abs(back - original) < 0.001

    def test_ms_to_speed_none(self):
        assert UnitConverter.ms_to_speed(None, SpeedUnit.KTS) is None


class TestLengthConversion:
    def test_m_to_m(self):
        assert UnitConverter.length_to_m(10.0, LengthUnit.M) == 10.0

    def test_ft_to_m(self):
        result = UnitConverter.length_to_m(1.0, LengthUnit.FT)
        assert abs(result - 0.3048) < 0.001

    def test_cm_to_m(self):
        result = UnitConverter.length_to_m(100.0, LengthUnit.CM)
        assert abs(result - 1.0) < 0.001

    def test_in_to_m(self):
        result = UnitConverter.length_to_m(1.0, LengthUnit.IN)
        assert abs(result - 0.0254) < 0.001

    def test_mm_to_m(self):
        result = UnitConverter.length_to_m(1000.0, LengthUnit.MM)
        assert abs(result - 1.0) < 0.001

    def test_nm_to_m(self):
        result = UnitConverter.length_to_m(1.0, LengthUnit.NM)
        assert abs(result - 1852.0) < 0.1

    def test_km_to_m(self):
        result = UnitConverter.length_to_m(1.0, LengthUnit.KM)
        assert abs(result - 1000.0) < 0.1

    def test_none_returns_none(self):
        assert UnitConverter.length_to_m(None, LengthUnit.FT) is None

    def test_roundtrip_ft(self):
        original = 6.5
        m = UnitConverter.length_to_m(original, LengthUnit.FT)
        back = UnitConverter.m_to_length(m, LengthUnit.FT)
        assert abs(back - original) < 0.001

    def test_m_to_length_none(self):
        assert UnitConverter.m_to_length(None, LengthUnit.FT) is None


class TestTemperatureConversion:
    def test_c_to_c(self):
        assert UnitConverter.temp_to_celsius(25.0, TempUnit.C) == 25.0

    def test_f_to_c_freezing(self):
        result = UnitConverter.temp_to_celsius(32.0, TempUnit.F)
        assert abs(result - 0.0) < 0.01

    def test_f_to_c_boiling(self):
        result = UnitConverter.temp_to_celsius(212.0, TempUnit.F)
        assert abs(result - 100.0) < 0.01

    def test_k_to_c_absolute_zero(self):
        result = UnitConverter.temp_to_celsius(0.0, TempUnit.K)
        assert abs(result - (-273.15)) < 0.01

    def test_k_to_c_room_temp(self):
        result = UnitConverter.temp_to_celsius(293.15, TempUnit.K)
        assert abs(result - 20.0) < 0.01

    def test_none_returns_none(self):
        assert UnitConverter.temp_to_celsius(None, TempUnit.F) is None

    def test_roundtrip_f(self):
        original = 75.0
        c = UnitConverter.temp_to_celsius(original, TempUnit.F)
        back = UnitConverter.celsius_to_temp(c, TempUnit.F)
        assert abs(back - original) < 0.01

    def test_celsius_to_temp_none(self):
        assert UnitConverter.celsius_to_temp(None, TempUnit.F) is None

    def test_celsius_to_k(self):
        result = UnitConverter.celsius_to_temp(0.0, TempUnit.K)
        assert abs(result - 273.15) < 0.01


class TestPressureConversion:
    def test_hpa_identity(self):
        assert UnitConverter.pressure_to_hpa(1013.25, PressureUnit.HPA) == 1013.25

    def test_mbar_identity(self):
        assert UnitConverter.pressure_to_hpa(1013.25, PressureUnit.MB) == 1013.25

    def test_atm_to_hpa(self):
        result = UnitConverter.pressure_to_hpa(1.0, PressureUnit.ATM)
        assert abs(result - 1013.25) < 0.01

    def test_pa_to_hpa(self):
        result = UnitConverter.pressure_to_hpa(101325.0, PressureUnit.PA)
        assert abs(result - 1013.25) < 0.01

    def test_kpa_to_hpa(self):
        result = UnitConverter.pressure_to_hpa(101.325, PressureUnit.KPA)
        assert abs(result - 1013.25) < 0.01

    def test_inhg_to_hpa(self):
        result = UnitConverter.pressure_to_hpa(29.92, PressureUnit.INHG)
        assert abs(result - 1013.25) < 1.0

    def test_psi_to_hpa(self):
        result = UnitConverter.pressure_to_hpa(14.696, PressureUnit.PSI)
        assert abs(result - 1013.25) < 1.0

    def test_none_returns_none(self):
        assert UnitConverter.pressure_to_hpa(None, PressureUnit.ATM) is None

    def test_roundtrip_psi(self):
        original = 14.7
        hpa = UnitConverter.pressure_to_hpa(original, PressureUnit.PSI)
        back = UnitConverter.hpa_to_pressure(hpa, PressureUnit.PSI)
        assert abs(back - original) < 0.01

    def test_hpa_to_pressure_none(self):
        assert UnitConverter.hpa_to_pressure(None, PressureUnit.PSI) is None


class TestDirectionConversion:
    def test_normalize_within_range(self):
        assert UnitConverter.normalize_direction(90) == 90

    def test_normalize_negative(self):
        assert UnitConverter.normalize_direction(-90) == 270

    def test_normalize_over_360(self):
        assert UnitConverter.normalize_direction(450) == 90

    def test_normalize_zero(self):
        assert UnitConverter.normalize_direction(0) == 0

    def test_normalize_none(self):
        assert UnitConverter.normalize_direction(None) is None

    def test_direction_from_to(self):
        assert UnitConverter.direction_from_to(0) == 180
        assert UnitConverter.direction_from_to(180) == 0
        assert UnitConverter.direction_from_to(90) == 270

    def test_direction_from_to_none(self):
        assert UnitConverter.direction_from_to(None) is None
