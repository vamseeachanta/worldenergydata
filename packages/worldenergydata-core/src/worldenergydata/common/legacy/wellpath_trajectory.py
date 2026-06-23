"""Wellbore trajectory calculations using the Minimum Curvature Method.

This module provides functions for calculating wellbore trajectory parameters
including TVD, North/East coordinates, dogleg severity, and closure distance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple


class SurveyPoint(NamedTuple):
    """A single survey point in a wellbore trajectory."""

    depth: float  # Measured Depth (MD) in meters
    inc: float  # Inclination in degrees
    azi: float  # Azimuth in degrees
    tvd: float  # True Vertical Depth in meters
    north: float  # Northing in meters
    east: float  # Easting in meters
    closure: float  # Closure distance in meters
    dls: float  # Dogleg Severity in degrees per 30m


@dataclass
class TrajectoryResult:
    """Result of trajectory calculation between two survey points."""

    tvd: float  # True Vertical Depth in meters
    north: float  # Northing in meters
    east: float  # Easting in meters
    closure: float  # Closure distance in meters
    dls: float  # Dogleg Severity in degrees per 30m
    dogleg: float  # Dogleg angle in degrees


def calculate_dogleg(inc1: float, azi1: float, inc2: float, azi2: float) -> float:
    """Calculate the dogleg angle between two survey points.

    The dogleg is the 3D angle change in the wellbore direction between
    two survey points.

    Args:
        inc1: Inclination at first survey point (degrees).
        azi1: Azimuth at first survey point (degrees).
        inc2: Inclination at second survey point (degrees).
        azi2: Azimuth at second survey point (degrees).

    Returns:
        Dogleg angle in degrees.
    """
    cos_dogleg = (
        math.sin(math.radians(inc1))
        * math.sin(math.radians(inc2))
        * math.cos(math.radians(azi2 - azi1))
    ) + (math.cos(math.radians(inc1)) * math.cos(math.radians(inc2)))

    # Clamp to valid range for acos
    cos_dogleg = max(-1.0, min(1.0, cos_dogleg))

    return round(math.degrees(math.acos(cos_dogleg)), 3)


def calculate_dogleg_severity(dogleg: float, course_length: float) -> float:
    """Calculate dogleg severity normalized to 30m course length.

    Args:
        dogleg: Dogleg angle in degrees.
        course_length: Distance between survey points in meters.

    Returns:
        Dogleg severity in degrees per 30 meters.
    """
    if course_length == 0:
        return 0.0
    return round((dogleg * 30) / course_length, 3)


def calculate_ratio_factor(dogleg_severity: float) -> float:
    """Calculate the ratio factor for minimum curvature method.

    The ratio factor is used to account for the curvature of the
    wellbore between survey points.

    Args:
        dogleg_severity: Dogleg severity in degrees per 30m.

    Returns:
        Ratio factor (dimensionless).
    """
    if dogleg_severity == 0:
        return 1.0

    dls_rad = math.radians(dogleg_severity)
    return round((2 / dls_rad) * math.tan(dls_rad / 2), 5)


def calculate_minimum_curvature(
    depth1: float,
    inc1: float,
    azi1: float,
    tvd1: float,
    north1: float,
    east1: float,
    depth2: float,
    inc2: float,
    azi2: float,
) -> TrajectoryResult:
    """Calculate trajectory using the Minimum Curvature Method.

    The Minimum Curvature Method is an industry-standard method for
    calculating wellbore position between survey points. It assumes
    the wellbore follows a smooth circular arc.

    Args:
        depth1: Measured depth at first survey point (meters).
        inc1: Inclination at first survey point (degrees).
        azi1: Azimuth at first survey point (degrees).
        tvd1: TVD at first survey point (meters).
        north1: Northing at first survey point (meters).
        east1: Easting at first survey point (meters).
        depth2: Measured depth at second survey point (meters).
        inc2: Inclination at second survey point (degrees).
        azi2: Azimuth at second survey point (degrees).

    Returns:
        TrajectoryResult containing calculated position and trajectory metrics.
    """
    course_length = depth2 - depth1

    if course_length <= 0:
        return TrajectoryResult(
            tvd=tvd1, north=north1, east=east1, closure=0.0, dls=0.0, dogleg=0.0
        )

    # Calculate dogleg
    dogleg = calculate_dogleg(inc1, azi1, inc2, azi2)

    # Avoid division by zero
    if dogleg == 0:
        dogleg = 1

    # Calculate dogleg severity (per 30m)
    dls = calculate_dogleg_severity(dogleg, course_length)

    # Calculate ratio factor
    rf = calculate_ratio_factor(dls)

    # Calculate TVD increment
    tvd = (
        round(
            (course_length / 2)
            * (math.cos(math.radians(inc1)) + math.cos(math.radians(inc2)))
            * rf,
            2,
        )
        + tvd1
    )

    # Calculate North increment
    north = (
        round(
            (course_length / 2)
            * (
                (math.sin(math.radians(inc1)) * math.cos(math.radians(azi1)))
                + (math.sin(math.radians(inc2)) * math.cos(math.radians(azi2)))
            )
            * rf,
            2,
        )
        + north1
    )

    # Calculate East increment
    east = (
        round(
            (course_length / 2)
            * (
                (math.sin(math.radians(inc1)) * math.sin(math.radians(azi1)))
                + (math.sin(math.radians(inc2)) * math.sin(math.radians(azi2)))
            )
            * rf,
            2,
        )
        + east1
    )

    # Calculate closure distance
    closure = round(((north**2 + east**2) ** 0.5), 2)

    return TrajectoryResult(
        tvd=tvd, north=north, east=east, closure=closure, dls=dls, dogleg=dogleg
    )


def interpolate_survey_point(
    upper_depth: float,
    upper_inc: float,
    upper_azi: float,
    upper_tvd: float,
    upper_north: float,
    upper_east: float,
    lower_depth: float,
    lower_inc: float,
    lower_azi: float,
    target_depth: float,
) -> tuple[float, float, float, float, float, float]:
    """Interpolate survey values at a given depth between two survey points.

    Uses the Average Angle Method for interpolation between survey stations.

    Args:
        upper_depth: Measured depth at upper survey point (meters).
        upper_inc: Inclination at upper survey point (degrees).
        upper_azi: Azimuth at upper survey point (degrees).
        upper_tvd: TVD at upper survey point (meters).
        upper_north: Northing at upper survey point (meters).
        upper_east: Easting at upper survey point (meters).
        lower_depth: Measured depth at lower survey point (meters).
        lower_inc: Inclination at lower survey point (degrees).
        lower_azi: Azimuth at lower survey point (degrees).
        target_depth: Depth at which to interpolate (meters).

    Returns:
        Tuple of (inc, azi, tvd, north, east, depth_from_upper) at target depth.
    """
    delta_md = lower_depth - upper_depth
    depth_from_upper = target_depth - upper_depth

    if delta_md == 0:
        delta_md = 1  # Prevent division by zero

    # Calculate inclination step
    if depth_from_upper == 0:
        delta_inc_step = ((lower_inc - upper_inc) ** 2) ** 0.5
    else:
        delta_inc_step = (((lower_inc - upper_inc) ** 2) ** 0.5) / delta_md

    # Determine if building or dropping inclination
    if lower_inc >= upper_inc:
        inc_target = upper_inc + (delta_inc_step * depth_from_upper)
    else:
        inc_target = upper_inc - (delta_inc_step * depth_from_upper)

    # Calculate azimuth
    azi_increment = round(
        ((math.sqrt((upper_azi - lower_azi) ** 2) / delta_md) * depth_from_upper), 2
    )

    if upper_azi <= lower_azi:
        azi_target = round(upper_azi + azi_increment, 2)
    else:
        azi_target = round(upper_azi - azi_increment, 2)

    # Calculate TVD using average angle method
    tvd_target = round(
        (depth_from_upper * math.cos(math.radians(inc_target))) + upper_tvd, 2
    )

    # Calculate North using average angle method
    north_target = round(
        (
            depth_from_upper
            * math.sin(math.radians((upper_inc + inc_target) / 2))
            * math.cos(math.radians((upper_azi + azi_target) / 2))
        )
        + upper_north,
        2,
    )

    # Calculate East using average angle method
    east_target = round(
        (
            depth_from_upper
            * math.sin(math.radians((upper_inc + inc_target) / 2))
            * math.sin(math.radians((upper_azi + azi_target) / 2))
        )
        + upper_east,
        2,
    )

    return (
        inc_target,
        azi_target,
        tvd_target,
        north_target,
        east_target,
        depth_from_upper,
    )
