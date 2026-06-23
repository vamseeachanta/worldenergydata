"""
ABOUTME: Simplified hydraulic calculator for slim-hole vs standard-hole ECD comparison.
ABOUTME: Annular pressure loss, ECD, annular velocity, hole cleaning index.
"""

from __future__ import annotations

from worldenergydata.well_bore_design.schemas import BoreType

# Typical bit-size (hole OD) and drill-pipe OD for each bore type (inches)
_BORE_GEOMETRY: dict[BoreType, dict[str, float]] = {
    BoreType.SLIM_HOLE: {"hole_od_in": 6.0, "pipe_od_in": 3.5},
    BoreType.STANDARD: {"hole_od_in": 8.5, "pipe_od_in": 5.0},
    BoreType.LARGE_BORE: {"hole_od_in": 12.25, "pipe_od_in": 5.5},
}


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
        """Simplified Bingham Plastic annular pressure loss (psi per 100 ft).

        Uses the Bourgoyne et al. correlation:
          - Hydraulic diameter  : Dh = hole_od - pipe_od (in)
          - Annular velocity    : from annular_velocity_fps()
          - Laminar/turbulent   : determined by Reynolds number
          - Laminar  : dP/dL = (PV * AV / (300 * Dh^2)) + (YP / (225 * Dh))
          - Turbulent: fanning friction factor applied

        All results are positive (pressure loss, not pressure gradient).
        """
        dh_in = hole_od_in - pipe_od_in
        if dh_in <= 0:
            raise ValueError("pipe_od_in must be less than hole_od_in")

        av = self.annular_velocity_fps(flow_rate_gpm, hole_od_in, pipe_od_in)
        av_fpm = av * 60.0  # ft/min

        # Bingham Plastic annular Reynolds number (Bourgoyne form)
        re = (
            (109.0 * mud_weight_ppg * av_fpm * dh_in)
            / (plastic_viscosity_cp + (6.0 * yield_point_lbf_100ft2 * dh_in / av_fpm))
            if av_fpm > 0
            else 0.0
        )

        if re < 2100:
            # Laminar — simplified Bingham Plastic formula (psi/100ft)
            dP = plastic_viscosity_cp * av_fpm / (
                300.0 * dh_in**2
            ) + yield_point_lbf_100ft2 / (225.0 * dh_in)
        else:
            # Turbulent — Fanning friction factor (Dodge-Metzner approximation)
            f = 0.046 / (re**0.2)
            # dP in psi/100ft = f * mud_weight * AV^2 / (21.1 * dh)
            dP = f * mud_weight_ppg * av_fpm**2 / (21.1 * dh_in * 1000.0)

        return max(dP, 0.0)

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
        if depth_ft <= 0:
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
        plastic_viscosity_cp: float = 20.0,
        yield_point_lbf_100ft2: float = 15.0,
    ) -> dict[str, dict[str, float]]:
        """Compare slim, standard, and large-bore hydraulics at given conditions.

        Returns a dict keyed by bore type name with sub-dicts:
            ecd_ppg, annular_velocity_fps, pressure_loss_psi_per_100ft,
            hole_cleaning_index, total_pressure_loss_psi
        """
        results: dict[str, dict[str, float]] = {}

        depth_100ft_sections = depth_ft / 100.0

        for bore_type, geometry in _BORE_GEOMETRY.items():
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
