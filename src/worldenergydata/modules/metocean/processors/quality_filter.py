# ABOUTME: Quality control filter for metocean observations.
# ABOUTME: Applies range checks, spike detection, and consistency validation.

"""
Quality Filter for Metocean Data

Applies quality control checks to metocean observations including:
- Range validation (physical limits)
- Spike detection (rapid changes)
- Missing value detection
- Consistency checks between related parameters
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from worldenergydata.modules.metocean.constants import (
    PARAMETER_RANGES,
    MetoceanParameter,
    QualityFlag,
)


@dataclass
class QualityCheckResult:
    """
    Result of a quality check.

    Attributes:
        passed: Whether the check passed
        flag: Quality flag assigned
        reason: Explanation if check failed
    """

    passed: bool
    flag: QualityFlag
    reason: Optional[str] = None


class QualityFilter:
    """
    Applies quality control checks to metocean data.

    Checks:
    - Range validation (physical limits)
    - Spike detection (rapid changes)
    - Missing value detection
    - Consistency checks

    Example usage:
        # Check if wave height is within valid range
        result = QualityFilter.check_range(
            MetoceanParameter.WAVE_HEIGHT, 15.0
        )
        if not result.passed:
            print(f"Invalid: {result.reason}")

        # Detect spikes in data
        result = QualityFilter.check_spike(
            MetoceanParameter.WIND_SPEED,
            current_value=50.0,
            previous_value=10.0,
            time_diff_hours=0.5
        )
    """

    # Physical limits for parameters (min, max)
    # Maps MetoceanParameter to (min_value, max_value)
    LIMITS: Dict[MetoceanParameter, Tuple[float, float]] = {
        MetoceanParameter.WAVE_HEIGHT: (0, 30),  # 0-30m
        MetoceanParameter.WAVE_PERIOD: (0, 30),  # 0-30s
        MetoceanParameter.WAVE_DIRECTION: (0, 360),  # degrees
        MetoceanParameter.WIND_SPEED: (0, 100),  # 0-100 m/s
        MetoceanParameter.WIND_DIRECTION: (0, 360),  # degrees
        MetoceanParameter.CURRENT_SPEED: (0, 5),  # 0-5 m/s
        MetoceanParameter.CURRENT_DIRECTION: (0, 360),  # degrees
        MetoceanParameter.SEA_SURFACE_TEMP: (-2, 40),  # -2 to 40C
        MetoceanParameter.WATER_LEVEL: (-15, 15),  # -15 to 15m
        MetoceanParameter.PRESSURE: (870, 1090),  # hPa
    }

    # Maximum allowed change per hour for spike detection
    MAX_CHANGE_PER_HOUR: Dict[MetoceanParameter, float] = {
        MetoceanParameter.WAVE_HEIGHT: 2.0,  # 2m/hour
        MetoceanParameter.WIND_SPEED: 20.0,  # 20 m/s/hour
        MetoceanParameter.SEA_SURFACE_TEMP: 1.0,  # 1C/hour
        MetoceanParameter.PRESSURE: 10.0,  # 10 hPa/hour
        MetoceanParameter.WATER_LEVEL: 2.0,  # 2m/hour (tidal)
    }

    @classmethod
    def check_range(
        cls,
        parameter: MetoceanParameter,
        value: Optional[float],
    ) -> QualityCheckResult:
        """
        Check if value is within physical limits.

        Args:
            parameter: The parameter type being checked
            value: The value to check (None is treated as missing)

        Returns:
            QualityCheckResult indicating pass/fail and flag
        """
        if value is None:
            return QualityCheckResult(
                passed=True, flag=QualityFlag.MISSING, reason="Missing value"
            )

        limits = cls.LIMITS.get(parameter)
        if limits is None:
            # No limits defined, assume good
            return QualityCheckResult(passed=True, flag=QualityFlag.GOOD)

        min_val, max_val = limits
        if min_val <= value <= max_val:
            return QualityCheckResult(passed=True, flag=QualityFlag.GOOD)
        else:
            return QualityCheckResult(
                passed=False,
                flag=QualityFlag.BAD,
                reason=f"Value {value} outside range [{min_val}, {max_val}]",
            )

    @classmethod
    def check_range_by_name(
        cls,
        parameter_name: str,
        value: Optional[float],
    ) -> QualityCheckResult:
        """
        Check range using parameter name from PARAMETER_RANGES constant.

        Args:
            parameter_name: Name matching key in PARAMETER_RANGES
            value: The value to check

        Returns:
            QualityCheckResult indicating pass/fail and flag
        """
        if value is None:
            return QualityCheckResult(
                passed=True, flag=QualityFlag.MISSING, reason="Missing value"
            )

        range_info = PARAMETER_RANGES.get(parameter_name)
        if range_info is None:
            return QualityCheckResult(passed=True, flag=QualityFlag.GOOD)

        min_val = range_info.get("min", float("-inf"))
        max_val = range_info.get("max", float("inf"))

        if min_val <= value <= max_val:
            return QualityCheckResult(passed=True, flag=QualityFlag.GOOD)
        else:
            return QualityCheckResult(
                passed=False,
                flag=QualityFlag.BAD,
                reason=f"Value {value} outside range [{min_val}, {max_val}]",
            )

    @classmethod
    def check_spike(
        cls,
        parameter: MetoceanParameter,
        current_value: float,
        previous_value: float,
        time_diff_hours: float,
    ) -> QualityCheckResult:
        """
        Detect unrealistic rapid changes (spikes).

        Args:
            parameter: The parameter type being checked
            current_value: Current observation value
            previous_value: Previous observation value
            time_diff_hours: Time difference in hours

        Returns:
            QualityCheckResult indicating if spike detected
        """
        max_change = cls.MAX_CHANGE_PER_HOUR.get(parameter)
        if max_change is None:
            # No spike limit defined
            return QualityCheckResult(passed=True, flag=QualityFlag.GOOD)

        # Avoid division by zero
        time_diff = max(time_diff_hours, 0.1)
        actual_change_rate = abs(current_value - previous_value) / time_diff

        if actual_change_rate > max_change:
            return QualityCheckResult(
                passed=False,
                flag=QualityFlag.SUSPECT,
                reason=(
                    f"Spike detected: {actual_change_rate:.2f}/hour "
                    f"exceeds max {max_change}/hour"
                ),
            )

        return QualityCheckResult(passed=True, flag=QualityFlag.GOOD)

    @classmethod
    def check_direction_consistency(
        cls,
        speed: Optional[float],
        direction: Optional[float],
    ) -> QualityCheckResult:
        """
        Check consistency between speed and direction.

        If speed is zero or near zero, direction should be undefined.
        If direction is defined, speed should be non-zero.

        Args:
            speed: Speed value (m/s)
            direction: Direction value (degrees)

        Returns:
            QualityCheckResult indicating consistency
        """
        if speed is None and direction is None:
            return QualityCheckResult(
                passed=True, flag=QualityFlag.MISSING, reason="Both values missing"
            )

        if speed is not None and speed < 0.1 and direction is not None:
            return QualityCheckResult(
                passed=False,
                flag=QualityFlag.SUSPECT,
                reason="Direction defined but speed near zero",
            )

        return QualityCheckResult(passed=True, flag=QualityFlag.GOOD)

    @classmethod
    def check_wave_consistency(
        cls,
        wave_height: Optional[float],
        wave_period: Optional[float],
    ) -> QualityCheckResult:
        """
        Check consistency between wave height and period.

        Very large waves should have longer periods.
        The wave steepness (H/L where L ~ gT^2/2pi) shouldn't exceed ~0.14.

        Args:
            wave_height: Significant wave height (m)
            wave_period: Wave period (s)

        Returns:
            QualityCheckResult indicating consistency
        """
        if wave_height is None or wave_period is None:
            return QualityCheckResult(passed=True, flag=QualityFlag.GOOD)

        if wave_period < 1.0:
            return QualityCheckResult(
                passed=False,
                flag=QualityFlag.BAD,
                reason="Wave period too short",
            )

        # Calculate wave steepness (simplified)
        # L = g * T^2 / (2 * pi) where g = 9.81
        wavelength = 9.81 * wave_period**2 / (2 * 3.14159)
        steepness = wave_height / wavelength

        if steepness > 0.14:
            return QualityCheckResult(
                passed=False,
                flag=QualityFlag.SUSPECT,
                reason=f"Wave steepness {steepness:.3f} exceeds physical limit 0.14",
            )

        return QualityCheckResult(passed=True, flag=QualityFlag.GOOD)

    @classmethod
    def get_overall_flag(cls, flags: List[QualityFlag]) -> QualityFlag:
        """
        Determine overall quality flag from multiple checks.

        Priority: BAD > SUSPECT > MISSING > GOOD

        Args:
            flags: List of quality flags from individual checks

        Returns:
            Overall quality flag
        """
        if not flags:
            return QualityFlag.GOOD

        if QualityFlag.BAD in flags:
            return QualityFlag.BAD
        elif QualityFlag.SUSPECT in flags:
            return QualityFlag.SUSPECT
        elif QualityFlag.MISSING in flags:
            return QualityFlag.MISSING
        else:
            return QualityFlag.GOOD

    @classmethod
    def filter_observations(
        cls,
        observations: List[Any],
        exclude_bad: bool = True,
        exclude_suspect: bool = False,
    ) -> List[Any]:
        """
        Apply all quality filters to a list of observations.

        Filters observations based on their quality_flag attribute.

        Args:
            observations: List of observation objects with quality_flag attr
            exclude_bad: Remove observations flagged as BAD
            exclude_suspect: Remove observations flagged as SUSPECT

        Returns:
            Filtered list of observations
        """
        result = []
        for obs in observations:
            flag = getattr(obs, "quality_flag", QualityFlag.GOOD)

            if exclude_bad and flag == QualityFlag.BAD:
                continue
            if exclude_suspect and flag == QualityFlag.SUSPECT:
                continue

            result.append(obs)

        return result

    @classmethod
    def validate_observation(
        cls,
        wave_height: Optional[float] = None,
        wave_period: Optional[float] = None,
        wave_direction: Optional[float] = None,
        wind_speed: Optional[float] = None,
        wind_direction: Optional[float] = None,
        current_speed: Optional[float] = None,
        current_direction: Optional[float] = None,
        sea_surface_temp: Optional[float] = None,
        pressure: Optional[float] = None,
        water_level: Optional[float] = None,
    ) -> Tuple[QualityFlag, List[str]]:
        """
        Validate all parameters in an observation.

        Args:
            wave_height: Significant wave height (m)
            wave_period: Wave period (s)
            wave_direction: Wave direction (degrees)
            wind_speed: Wind speed (m/s)
            wind_direction: Wind direction (degrees)
            current_speed: Current speed (m/s)
            current_direction: Current direction (degrees)
            sea_surface_temp: Sea surface temperature (C)
            pressure: Atmospheric pressure (hPa)
            water_level: Water level (m)

        Returns:
            Tuple of (overall flag, list of issues found)
        """
        flags: List[QualityFlag] = []
        issues: List[str] = []

        # Range checks
        checks = [
            (MetoceanParameter.WAVE_HEIGHT, wave_height),
            (MetoceanParameter.WAVE_PERIOD, wave_period),
            (MetoceanParameter.WAVE_DIRECTION, wave_direction),
            (MetoceanParameter.WIND_SPEED, wind_speed),
            (MetoceanParameter.WIND_DIRECTION, wind_direction),
            (MetoceanParameter.CURRENT_SPEED, current_speed),
            (MetoceanParameter.CURRENT_DIRECTION, current_direction),
            (MetoceanParameter.SEA_SURFACE_TEMP, sea_surface_temp),
            (MetoceanParameter.PRESSURE, pressure),
            (MetoceanParameter.WATER_LEVEL, water_level),
        ]

        for param, value in checks:
            result = cls.check_range(param, value)
            flags.append(result.flag)
            if not result.passed and result.reason:
                issues.append(f"{param.value}: {result.reason}")

        # Consistency checks
        wave_check = cls.check_wave_consistency(wave_height, wave_period)
        flags.append(wave_check.flag)
        if not wave_check.passed and wave_check.reason:
            issues.append(f"wave_consistency: {wave_check.reason}")

        wind_check = cls.check_direction_consistency(wind_speed, wind_direction)
        flags.append(wind_check.flag)
        if not wind_check.passed and wind_check.reason:
            issues.append(f"wind_consistency: {wind_check.reason}")

        current_check = cls.check_direction_consistency(
            current_speed, current_direction
        )
        flags.append(current_check.flag)
        if not current_check.passed and current_check.reason:
            issues.append(f"current_consistency: {current_check.reason}")

        overall = cls.get_overall_flag(flags)
        return overall, issues
