# ABOUTME: Unit converter for metocean measurements.
# ABOUTME: Converts speed, length, temperature, and pressure to SI units.

"""
Unit Converter for Metocean Data

Provides standardized unit conversions for meteorological and oceanographic data.
All output units follow SI standards:
- Speed: m/s (meters per second)
- Length/Height: m (meters)
- Temperature: Celsius
- Pressure: hPa (hectopascals)
- Direction: degrees (0-360)
"""

from enum import Enum
from typing import Optional


class SpeedUnit(str, Enum):
    """Speed units for wind and current measurements."""

    MS = "m/s"  # meters per second (SI)
    KTS = "knots"  # nautical miles per hour
    KMH = "km/h"  # kilometers per hour
    MPH = "mph"  # miles per hour
    FPS = "ft/s"  # feet per second


class LengthUnit(str, Enum):
    """Length units for wave height, water depth, etc."""

    M = "m"  # meters (SI)
    FT = "feet"  # feet
    CM = "cm"  # centimeters
    IN = "inches"  # inches
    NM = "nm"  # nautical miles
    KM = "km"  # kilometers
    MM = "mm"  # millimeters


class TempUnit(str, Enum):
    """Temperature units."""

    C = "celsius"  # Celsius (SI)
    F = "fahrenheit"  # Fahrenheit
    K = "kelvin"  # Kelvin


class PressureUnit(str, Enum):
    """Pressure units for atmospheric pressure."""

    HPA = "hPa"  # hectopascals (SI)
    MB = "mbar"  # millibars (same as hPa)
    INHG = "inHg"  # inches of mercury
    MMHG = "mmHg"  # millimeters of mercury
    PA = "Pa"  # pascals
    KPA = "kPa"  # kilopascals
    ATM = "atm"  # atmospheres
    PSI = "psi"  # pounds per square inch


class UnitConverter:
    """
    Converts metocean measurements to SI units.

    Standard output units:
    - Speed: m/s
    - Length/Height: m
    - Temperature: Celsius
    - Pressure: hPa
    - Direction: degrees (0-360)

    Example usage:
        # Convert wind speed from knots to m/s
        wind_ms = UnitConverter.speed_to_ms(25.0, SpeedUnit.KTS)

        # Convert wave height from feet to meters
        height_m = UnitConverter.length_to_m(6.5, LengthUnit.FT)

        # Convert temperature from Fahrenheit to Celsius
        temp_c = UnitConverter.temp_to_celsius(75.0, TempUnit.F)
    """

    # Speed conversion factors to m/s
    KTS_TO_MS = 0.514444
    KMH_TO_MS = 0.277778
    MPH_TO_MS = 0.44704
    FPS_TO_MS = 0.3048

    # Length conversion factors to meters
    FT_TO_M = 0.3048
    IN_TO_M = 0.0254
    CM_TO_M = 0.01
    MM_TO_M = 0.001
    NM_TO_M = 1852.0
    KM_TO_M = 1000.0

    # Pressure conversion factors to hPa
    PA_TO_HPA = 0.01
    KPA_TO_HPA = 10.0
    INHG_TO_HPA = 33.8639
    MMHG_TO_HPA = 1.33322
    ATM_TO_HPA = 1013.25
    PSI_TO_HPA = 68.9476

    @classmethod
    def speed_to_ms(
        cls, value: Optional[float], from_unit: SpeedUnit
    ) -> Optional[float]:
        """
        Convert speed to m/s.

        Args:
            value: Speed value to convert (None returns None)
            from_unit: Source unit

        Returns:
            Speed in m/s, or None if input is None

        Raises:
            ValueError: If unit is not recognized
        """
        if value is None:
            return None

        if from_unit == SpeedUnit.MS:
            return value
        elif from_unit == SpeedUnit.KTS:
            return value * cls.KTS_TO_MS
        elif from_unit == SpeedUnit.KMH:
            return value * cls.KMH_TO_MS
        elif from_unit == SpeedUnit.MPH:
            return value * cls.MPH_TO_MS
        elif from_unit == SpeedUnit.FPS:
            return value * cls.FPS_TO_MS
        raise ValueError(f"Unknown speed unit: {from_unit}")

    @classmethod
    def ms_to_speed(cls, value: Optional[float], to_unit: SpeedUnit) -> Optional[float]:
        """
        Convert speed from m/s to target unit.

        Args:
            value: Speed value in m/s (None returns None)
            to_unit: Target unit

        Returns:
            Speed in target unit, or None if input is None

        Raises:
            ValueError: If unit is not recognized
        """
        if value is None:
            return None

        if to_unit == SpeedUnit.MS:
            return value
        elif to_unit == SpeedUnit.KTS:
            return value / cls.KTS_TO_MS
        elif to_unit == SpeedUnit.KMH:
            return value / cls.KMH_TO_MS
        elif to_unit == SpeedUnit.MPH:
            return value / cls.MPH_TO_MS
        elif to_unit == SpeedUnit.FPS:
            return value / cls.FPS_TO_MS
        raise ValueError(f"Unknown speed unit: {to_unit}")

    @classmethod
    def length_to_m(
        cls, value: Optional[float], from_unit: LengthUnit
    ) -> Optional[float]:
        """
        Convert length/height to meters.

        Args:
            value: Length value to convert (None returns None)
            from_unit: Source unit

        Returns:
            Length in meters, or None if input is None

        Raises:
            ValueError: If unit is not recognized
        """
        if value is None:
            return None

        if from_unit == LengthUnit.M:
            return value
        elif from_unit == LengthUnit.FT:
            return value * cls.FT_TO_M
        elif from_unit == LengthUnit.CM:
            return value * cls.CM_TO_M
        elif from_unit == LengthUnit.IN:
            return value * cls.IN_TO_M
        elif from_unit == LengthUnit.MM:
            return value * cls.MM_TO_M
        elif from_unit == LengthUnit.NM:
            return value * cls.NM_TO_M
        elif from_unit == LengthUnit.KM:
            return value * cls.KM_TO_M
        raise ValueError(f"Unknown length unit: {from_unit}")

    @classmethod
    def m_to_length(
        cls, value: Optional[float], to_unit: LengthUnit
    ) -> Optional[float]:
        """
        Convert length from meters to target unit.

        Args:
            value: Length value in meters (None returns None)
            to_unit: Target unit

        Returns:
            Length in target unit, or None if input is None

        Raises:
            ValueError: If unit is not recognized
        """
        if value is None:
            return None

        if to_unit == LengthUnit.M:
            return value
        elif to_unit == LengthUnit.FT:
            return value / cls.FT_TO_M
        elif to_unit == LengthUnit.CM:
            return value / cls.CM_TO_M
        elif to_unit == LengthUnit.IN:
            return value / cls.IN_TO_M
        elif to_unit == LengthUnit.MM:
            return value / cls.MM_TO_M
        elif to_unit == LengthUnit.NM:
            return value / cls.NM_TO_M
        elif to_unit == LengthUnit.KM:
            return value / cls.KM_TO_M
        raise ValueError(f"Unknown length unit: {to_unit}")

    @classmethod
    def temp_to_celsius(
        cls, value: Optional[float], from_unit: TempUnit
    ) -> Optional[float]:
        """
        Convert temperature to Celsius.

        Args:
            value: Temperature value to convert (None returns None)
            from_unit: Source unit

        Returns:
            Temperature in Celsius, or None if input is None

        Raises:
            ValueError: If unit is not recognized
        """
        if value is None:
            return None

        if from_unit == TempUnit.C:
            return value
        elif from_unit == TempUnit.F:
            return (value - 32) * 5 / 9
        elif from_unit == TempUnit.K:
            return value - 273.15
        raise ValueError(f"Unknown temperature unit: {from_unit}")

    @classmethod
    def celsius_to_temp(
        cls, value: Optional[float], to_unit: TempUnit
    ) -> Optional[float]:
        """
        Convert temperature from Celsius to target unit.

        Args:
            value: Temperature value in Celsius (None returns None)
            to_unit: Target unit

        Returns:
            Temperature in target unit, or None if input is None

        Raises:
            ValueError: If unit is not recognized
        """
        if value is None:
            return None

        if to_unit == TempUnit.C:
            return value
        elif to_unit == TempUnit.F:
            return value * 9 / 5 + 32
        elif to_unit == TempUnit.K:
            return value + 273.15
        raise ValueError(f"Unknown temperature unit: {to_unit}")

    @classmethod
    def pressure_to_hpa(
        cls, value: Optional[float], from_unit: PressureUnit
    ) -> Optional[float]:
        """
        Convert pressure to hPa (hectopascals).

        Args:
            value: Pressure value to convert (None returns None)
            from_unit: Source unit

        Returns:
            Pressure in hPa, or None if input is None

        Raises:
            ValueError: If unit is not recognized
        """
        if value is None:
            return None

        if from_unit in (PressureUnit.HPA, PressureUnit.MB):
            return value
        elif from_unit == PressureUnit.PA:
            return value * cls.PA_TO_HPA
        elif from_unit == PressureUnit.KPA:
            return value * cls.KPA_TO_HPA
        elif from_unit == PressureUnit.INHG:
            return value * cls.INHG_TO_HPA
        elif from_unit == PressureUnit.MMHG:
            return value * cls.MMHG_TO_HPA
        elif from_unit == PressureUnit.ATM:
            return value * cls.ATM_TO_HPA
        elif from_unit == PressureUnit.PSI:
            return value * cls.PSI_TO_HPA
        raise ValueError(f"Unknown pressure unit: {from_unit}")

    @classmethod
    def hpa_to_pressure(
        cls, value: Optional[float], to_unit: PressureUnit
    ) -> Optional[float]:
        """
        Convert pressure from hPa to target unit.

        Args:
            value: Pressure value in hPa (None returns None)
            to_unit: Target unit

        Returns:
            Pressure in target unit, or None if input is None

        Raises:
            ValueError: If unit is not recognized
        """
        if value is None:
            return None

        if to_unit in (PressureUnit.HPA, PressureUnit.MB):
            return value
        elif to_unit == PressureUnit.PA:
            return value / cls.PA_TO_HPA
        elif to_unit == PressureUnit.KPA:
            return value / cls.KPA_TO_HPA
        elif to_unit == PressureUnit.INHG:
            return value / cls.INHG_TO_HPA
        elif to_unit == PressureUnit.MMHG:
            return value / cls.MMHG_TO_HPA
        elif to_unit == PressureUnit.ATM:
            return value / cls.ATM_TO_HPA
        elif to_unit == PressureUnit.PSI:
            return value / cls.PSI_TO_HPA
        raise ValueError(f"Unknown pressure unit: {to_unit}")

    @classmethod
    def normalize_direction(cls, degrees: Optional[float]) -> Optional[float]:
        """
        Normalize direction to 0-360 range.

        Handles negative values and values > 360 by wrapping.

        Args:
            degrees: Direction in degrees (None returns None)

        Returns:
            Normalized direction in [0, 360) range, or None if input is None
        """
        if degrees is None:
            return None
        return degrees % 360

    @classmethod
    def direction_from_to(cls, from_deg: Optional[float]) -> Optional[float]:
        """
        Convert direction FROM to direction TO (add 180 degrees).

        Wind direction is typically reported as where wind is coming FROM.
        This converts to where it's going TO.

        Args:
            from_deg: Direction in degrees (from)

        Returns:
            Direction in degrees (to), normalized to [0, 360)
        """
        if from_deg is None:
            return None
        return (from_deg + 180) % 360
