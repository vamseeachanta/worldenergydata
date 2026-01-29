"""Math solvers for geometry calculations.

This module provides geometry calculations for well distance analysis.
"""

from __future__ import annotations

import math
from typing import Any


class Geometry:
    """Geometry calculations for spatial analysis."""

    def max_distance_for_spatial_sets(
        self, spatial_data_sets: list[list[float]]
    ) -> dict[str, Any]:
        """Calculate max and min distances between spatial points.

        Args:
            spatial_data_sets: List of [x, y] coordinate pairs

        Returns:
            Dictionary with distance_max, distance_min, and pair indices
        """
        if len(spatial_data_sets) < 2:
            return {
                "distance_max": 0.0,
                "distance_min": 0.0,
                "max_pair": None,
                "min_pair": None,
            }

        distances: list[tuple[float, int, int]] = []

        for i in range(len(spatial_data_sets)):
            for j in range(i + 1, len(spatial_data_sets)):
                point1 = spatial_data_sets[i]
                point2 = spatial_data_sets[j]
                dist = self._euclidean_distance(point1, point2)
                distances.append((dist, i, j))

        if not distances:
            return {
                "distance_max": 0.0,
                "distance_min": 0.0,
                "max_pair": None,
                "min_pair": None,
            }

        max_entry = max(distances, key=lambda x: x[0])
        min_entry = min(distances, key=lambda x: x[0])

        return {
            "distance_max": max_entry[0],
            "distance_min": min_entry[0],
            "max_pair": (max_entry[1], max_entry[2]),
            "min_pair": (min_entry[1], min_entry[2]),
        }

    def _euclidean_distance(self, point1: list[float], point2: list[float]) -> float:
        """Calculate Euclidean distance between two points.

        Args:
            point1: First point [x, y] or [x, y, z]
            point2: Second point [x, y] or [x, y, z]

        Returns:
            Distance between the two points
        """
        if len(point1) != len(point2):
            raise ValueError("Points must have the same dimensions")

        sum_sq = sum((a - b) ** 2 for a, b in zip(point1, point2))
        return math.sqrt(sum_sq)
