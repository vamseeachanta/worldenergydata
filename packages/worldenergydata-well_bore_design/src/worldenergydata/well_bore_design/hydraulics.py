"""
ABOUTME: Simplified hydraulic calculator for slim-hole vs standard-hole ECD comparison.
ABOUTME: Annular pressure loss, ECD, annular velocity, hole cleaning index.
"""

from __future__ import annotations

import math

from worldenergydata.well_bore_design.schemas import BoreType


class WellBoreHydraulics:
    """Decision-support hydraulic calculator for bore-type selection.

    Implements simplified Bingham Plastic annular pressure loss for
    slim-hole vs standard-hole comparison.  Not a replacement for
    full HYDPRO/WELLPLAN simulators.
    """

    # -------------------------------------------------------------------
    # Annular velocity
    # -------------------------------------------------------------------

    def annular_velocity_fps(
        self,
        flow_rate_gpm: float,
        hole_od_in: float,
        pipe_od_in: float,
    ) -> float:
        """Annular velocity in ft/s.

        AV = 0.408 * Q / (D_h^2 - D_p^2)
        where D_h = hole OD (in), D_p = pipe OD (in), Q = gpm.

        Raises ValueError when pipe OD >= hole OD.
        """
        annular_area = hole_od_in**2 - pipe_od_in**2
        if annular_area <= 0:
            raise ValueError(
                f"pipe_od_in ({pipe_od_in}) must be less than hole_od_in ({hole_od_in})"
            )
        return 0.408 * flow_rate_gpm / annular_area

    # -------------------------------------------------------------------
    # Pressure loss
    # -------------------------------------------------------------------

    def pressure_loss_psi_per_100ft(
        self,
        flow_rate_gpm: float,
        mud_weight_ppg: float,
        plastic_viscosity_cp: float,
        yield_point_lbf_100ft2: float,
        hole_od_in: float,
        pipe_od_in: float,
    ) -> float:
        """Laminar Bingham slot approximation in psi per 100 ft.

        Source: *Stepwise derivation and comparison of the Herschel–Bulkley
        Laminar Fluid Flow equations—in Annulus* (2025, corrected 2026),
        DOI 10.1007/s13202-024-01919-z, Appendix A1, A29–A30, with N=1.
        For radial clearance h, G=dP/dL, a=2*tau_y/(G*h):
        v = G*h**2/(12*mu) * (1-a)**2 * (1+a/2).
        Thus G >= 4*tau_y/(hole_diameter-pipe_diameter).

        Assumes steady laminar flow, concentric stationary walls, no cuttings.
        This is a slot approximation, not an exact curved-annulus or turbulent
        solution. Mud density is validated but does not enter this laminar law.
        """
        values = (
            flow_rate_gpm,
            mud_weight_ppg,
            plastic_viscosity_cp,
            yield_point_lbf_100ft2,
            hole_od_in,
            pipe_od_in,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Hydraulic inputs must be finite")
        if (
            flow_rate_gpm < 0
            or mud_weight_ppg <= 0
            or plastic_viscosity_cp <= 0
            or yield_point_lbf_100ft2 < 0
            or pipe_od_in <= 0
            or hole_od_in <= pipe_od_in
        ):
            raise ValueError(
                "Require nonnegative flow/yield and positive mud, PV and annular geometry"
            )
        if flow_rate_gpm == 0:
            return 0.0

        # NIST SP 811 (2008), Appendix B.8: inch, foot, psi, centipoise,
        # US gallon/minute. Use psi/14400 for lbf per 100 square feet so the
        # yield-floor unit identity is preserved despite table rounding.
        inch_m, foot_m, psi_pa = 0.0254, 0.3048, 6894.757
        mu = plastic_viscosity_cp * 0.001
        tau_y = yield_point_lbf_100ft2 * psi_pa / 14400
        h = (hole_od_in - pipe_od_in) * inch_m / 2
        area = math.pi * ((hole_od_in * inch_m) ** 2 - (pipe_od_in * inch_m) ** 2) / 4
        velocity = flow_rate_gpm * 6.309020e-5 / area
        floor = 2 * tau_y / h
        viscous = 12 * mu * velocity / h**2  # A29/A30, N=1

        def mean_velocity(gradient: float) -> float:
            a = floor / gradient
            return gradient * h**2 / (12 * mu) * (1 - a) ** 2 * (1 + a / 2)

        lower, upper = floor, floor + viscous
        # Bracket by doubling, then bisect to adjacent floating-point values.
        # These are numerical operations, not empirical acceptance limits.
        while mean_velocity(upper) < velocity:
            upper *= 2
            if not math.isfinite(upper):
                raise ValueError("Hydraulic inputs exceed numerical range")
        while True:
            midpoint = lower + (upper - lower) / 2
            if midpoint == lower or midpoint == upper:
                break
            if mean_velocity(midpoint) < velocity:
                lower = midpoint
            else:
                upper = midpoint
        return upper * (100 * foot_m) / psi_pa

    # -------------------------------------------------------------------
    # ECD
    # -------------------------------------------------------------------

    def ecd_ppg(
        self,
        mud_weight_ppg: float,
        annular_pressure_loss_psi: float,
        depth_ft: float,
    ) -> float:
        """Equivalent circulating density (ppg).

        ECD = mud_weight + annular_pressure_loss / (0.052 * depth_ft)

        Raises ValueError when depth_ft <= 0.
        """
        if not math.isfinite(depth_ft) or depth_ft <= 0:
            raise ValueError("depth_ft must be positive")
        return mud_weight_ppg + annular_pressure_loss_psi / (0.052 * depth_ft)

    # -------------------------------------------------------------------
    # Hole cleaning
    # -------------------------------------------------------------------

    def hole_cleaning_index(
        self,
        annular_velocity_fps: float,
        mud_weight_ppg: float,
        cutting_density_ppg: float = 21.7,
    ) -> float:
        """Hole cleaning index.

        HCI = AV * mud_weight / cutting_density.
        HCI > 1.0 indicates adequate hole cleaning.
        """
        if cutting_density_ppg <= 0:
            raise ValueError("cutting_density_ppg must be positive")
        return annular_velocity_fps * mud_weight_ppg / cutting_density_ppg

    # -------------------------------------------------------------------
    # Bore-type comparison
    # -------------------------------------------------------------------

    def compare_bore_types(
        self,
        flow_rate_gpm: float,
        mud_weight_ppg: float,
        depth_ft: float,
        plastic_viscosity_cp: float,
        yield_point_lbf_100ft2: float,
        geometries: dict[BoreType, dict[str, float]],
    ) -> dict[str, dict[str, float]]:
        """Compare caller-supplied bore geometries at given mud conditions.

        Returns a dict keyed by bore type name with sub-dicts:
            ecd_ppg, annular_velocity_fps, pressure_loss_psi_per_100ft,
            hole_cleaning_index, total_pressure_loss_psi
        """
        if not geometries:
            raise ValueError("At least one bore geometry is required")
        results: dict[str, dict[str, float]] = {}

        depth_100ft_sections = depth_ft / 100.0

        for bore_type, geometry in geometries.items():
            hole_od = geometry["hole_od_in"]
            pipe_od = geometry["pipe_od_in"]

            av = self.annular_velocity_fps(flow_rate_gpm, hole_od, pipe_od)
            dp_per_100ft = self.pressure_loss_psi_per_100ft(
                flow_rate_gpm,
                mud_weight_ppg,
                plastic_viscosity_cp,
                yield_point_lbf_100ft2,
                hole_od,
                pipe_od,
            )
            total_dp_psi = dp_per_100ft * depth_100ft_sections
            calc_ecd = self.ecd_ppg(mud_weight_ppg, total_dp_psi, depth_ft)
            hci = self.hole_cleaning_index(av, mud_weight_ppg)

            results[bore_type.value] = {
                "ecd_ppg": calc_ecd,
                "annular_velocity_fps": av,
                "pressure_loss_psi_per_100ft": dp_per_100ft,
                "hole_cleaning_index": hci,
                "total_pressure_loss_psi": total_dp_psi,
            }

        return results
