# ABOUTME: Physics-based extrapolation models for wave and current transfer.
# ABOUTME: Wave shoaling/fetch correction, current depth/tidal scaling.

"""
Physics-Based Extrapolation Models

Provides wave and current transfer functions grounded in linear wave theory,
fetch-limited growth relations, and boundary-layer current profiles.

All methods are pure functions that take numeric inputs and return floats.
No network access or external data required.
"""

import math

from worldenergydata.metocean.extrapolation.spatial import SpatialContext


class WaveExtrapolator:
    """
    Physics-based wave parameter transfer from source to target location.

    Methods implement:
    - Linear wave shoaling (Green's Law approximation)
    - Fetch-limited growth scaling (sqrt(fetch) relation)
    - Combined transfer combining both corrections
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def shoaling_correction(
        self,
        Hs_source: float,
        d_source: float,
        d_target: float,
    ) -> float:
        """
        Apply linear wave shoaling correction to significant wave height.

        Based on the shoaling coefficient Ks derived from linear wave theory:
            Ks = (Cg_deep / Cg_shallow)^0.5
        For simplicity the Green's Law depth-power approximation is used:
            Hs_target = Hs_source * (d_source / d_target)^0.25

        The exponent 0.25 is appropriate for intermediate-to-shallow water.
        In deep water (d_target == d_source) the result equals Hs_source.

        Args:
            Hs_source: Significant wave height at source (m, > 0)
            d_source: Water depth at source (m, > 0)
            d_target: Water depth at target (m, > 0)

        Returns:
            Corrected Hs at target location (m, > 0).

        Raises:
            ValueError: If any input is non-positive.
        """
        if Hs_source <= 0:
            raise ValueError(f"Hs_source must be positive, got {Hs_source}")
        if d_source <= 0:
            raise ValueError(f"d_source must be positive, got {d_source}")
        if d_target <= 0:
            raise ValueError(f"d_target must be positive, got {d_target}")

        ks = (d_source / d_target) ** 0.25
        return Hs_source * ks

    def fetch_correction(
        self,
        Hs_source: float,
        fetch_source_km: float,
        fetch_target_km: float,
    ) -> float:
        """
        Scale significant wave height by fetch ratio (sqrt relation).

        In fetch-limited conditions, wave energy is proportional to fetch:
            Hs ~ sqrt(fetch)
        so the transfer is:
            Hs_target = Hs_source * sqrt(fetch_target / fetch_source)

        Args:
            Hs_source: Significant wave height at source (m, > 0)
            fetch_source_km: Effective fetch at source (km, > 0)
            fetch_target_km: Effective fetch at target (km, > 0)

        Returns:
            Corrected Hs at target (m, > 0).
        """
        if Hs_source <= 0:
            raise ValueError(f"Hs_source must be positive, got {Hs_source}")
        if fetch_source_km <= 0:
            raise ValueError(f"fetch_source_km must be positive, got {fetch_source_km}")
        if fetch_target_km <= 0:
            raise ValueError(f"fetch_target_km must be positive, got {fetch_target_km}")

        ratio = fetch_target_km / fetch_source_km
        return Hs_source * math.sqrt(ratio)

    def transfer(
        self,
        Hs: float,
        Tp: float,
        context: SpatialContext,
    ) -> tuple[float, float]:
        """
        Apply combined shoaling and fetch corrections.

        The depth-ratio from SpatialContext drives the shoaling correction.
        The sheltering factor modulates fetch at the target relative to the
        source (assumed fully exposed: sheltering = 1.0).

        Peak period Tp scales with fetch^(1/3) in fully developed sea
        conditions; a simplified proportional adjustment is applied.

        Args:
            Hs: Source significant wave height (m)
            Tp: Source peak period (s)
            context: SpatialContext for this source-target pair

        Returns:
            (Hs_target, Tp_target) as a tuple of floats (both > 0).
        """
        if Hs <= 0:
            raise ValueError(f"Hs must be positive, got {Hs}")
        if Tp <= 0:
            raise ValueError(f"Tp must be positive, got {Tp}")

        Hs_out = float(Hs)
        Tp_out = float(Tp)

        # Shoaling: use depth_ratio (target/source)
        depth_ratio = max(context.depth_ratio, 1e-3)
        if depth_ratio != 1.0:
            d_source = 100.0  # nominal reference depth (m)
            d_target = d_source * depth_ratio
            Hs_out = self.shoaling_correction(Hs_out, d_source, d_target)
            # Tp shoaling: Tp scales weakly with depth; use (d_target/d_source)^0.1
            Tp_out = Tp_out * (depth_ratio**0.1)

        # Fetch: source assumed open ocean (sheltering=1.0), target sheltered
        shelter_target = max(context.sheltering_factor, 1e-3)
        if shelter_target < 1.0:
            fetch_source_km = max(context.fetch_km / shelter_target, 1.0)
            fetch_target_km = max(context.fetch_km, 1.0)
            Hs_out = self.fetch_correction(Hs_out, fetch_source_km, fetch_target_km)
            # Tp scales with fetch^(1/3)
            fetch_ratio = fetch_target_km / fetch_source_km
            Tp_out = Tp_out * (fetch_ratio ** (1.0 / 3.0))

        return max(Hs_out, 0.01), max(Tp_out, 1.0)


class CurrentExtrapolator:
    """
    Physics-based current transfer from source to target location.

    Implements:
    - Log-law and power-law vertical current profiles
    - Tidal current scaling with water depth
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def depth_scaling(
        self,
        U_surface: float,
        z_target: float,
        z_total: float,
        profile: str = "log",
    ) -> float:
        """
        Scale a surface current to a target depth using a vertical profile.

        Args:
            U_surface: Surface current speed (m/s, >= 0)
            z_target: Target depth below surface (m, 0 = surface)
            z_total: Total water column depth (m, > 0)
            profile: "log" (logarithmic) or "power" (1/7 power law)

        Returns:
            Current speed at z_target (m/s, in [0, U_surface]).

        Raises:
            ValueError: If U_surface < 0 or z_target / z_total invalid.
        """
        if U_surface < 0:
            raise ValueError(f"U_surface must be >= 0, got {U_surface}")
        if z_total <= 0:
            raise ValueError(f"z_total must be positive, got {z_total}")
        if z_target < 0:
            raise ValueError(f"z_target must be >= 0, got {z_target}")
        if z_target >= z_total:
            # At or below seabed — return near-zero
            return 0.0
        if z_target == 0:
            return float(U_surface)

        if profile == "log":
            # Log-law: U(z) = U_surface * ln(z_ref/z0) / ln(h/z0)
            # Simplified form: ratio = ln((z_total - z_target) / z0) / ln(z_total / z0)
            z0 = max(z_total * 0.001, 0.01)  # roughness length ~ 0.1% of depth
            z_above_bed = z_total - z_target
            z_ref = z_total  # surface reference
            if z_above_bed <= z0:
                return 0.0
            ratio = math.log(z_above_bed / z0) / math.log(z_ref / z0)
            return float(U_surface) * max(ratio, 0.0)
        else:
            # Power law: U(z) = U_surface * ((z_total - z_target) / z_total)^(1/7)
            frac = (z_total - z_target) / z_total
            return float(U_surface) * (frac ** (1.0 / 7.0))

    def tidal_scaling(
        self,
        U_source: float,
        d_source: float,
        d_target: float,
    ) -> float:
        """
        Scale tidal current between two water depths.

        Mass-flux conservation gives:
            U_target * d_target = U_source * d_source
        => U_target = U_source * d_source / d_target

        This is appropriate for barotropic (depth-averaged) tidal currents.

        Args:
            U_source: Tidal current speed at source (m/s, >= 0)
            d_source: Water depth at source (m, > 0)
            d_target: Water depth at target (m, > 0)

        Returns:
            Scaled tidal current at target (m/s, > 0).
        """
        if U_source < 0:
            raise ValueError(f"U_source must be >= 0, got {U_source}")
        if d_source <= 0:
            raise ValueError(f"d_source must be positive, got {d_source}")
        if d_target <= 0:
            raise ValueError(f"d_target must be positive, got {d_target}")

        return float(U_source) * d_source / d_target

    def transfer(
        self,
        U: float,
        context: SpatialContext,
    ) -> float:
        """
        Apply combined depth and tidal corrections to a surface current.

        Args:
            U: Surface current speed at source (m/s, >= 0)
            context: SpatialContext for this source-target pair

        Returns:
            Estimated surface current at target (m/s, >= 0).
        """
        if U < 0:
            raise ValueError(f"U must be >= 0, got {U}")

        U_out = float(U)

        # Apply tidal scaling if depth ratio differs meaningfully
        depth_ratio = max(context.depth_ratio, 1e-3)
        if abs(depth_ratio - 1.0) > 0.05:
            d_source = 100.0  # nominal reference
            d_target = d_source * depth_ratio
            U_out = self.tidal_scaling(U_out, d_source, d_target)

        # Sheltering reduces surface current in enclosed basins
        shelter = max(context.sheltering_factor, 0.3)
        U_out = U_out * shelter

        return max(U_out, 0.0)
