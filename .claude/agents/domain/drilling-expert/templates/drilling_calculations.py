"""
Drilling Engineering Calculations Template
Comprehensive drilling calculations for well planning and operations
"""

import numpy as np
import pandas as pd
from scipy import optimize, interpolate
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import math


# ==============================================================================
# Drilling Hydraulics
# ==============================================================================

def calculate_ecd(
    mud_weight_ppg: float,
    annular_pressure_loss_psi: float,
    tvd_ft: float,
    temperature_correction: float = 0
) -> float:
    """
    Calculate Equivalent Circulating Density
    
    Args:
        mud_weight_ppg: Static mud weight in ppg
        annular_pressure_loss_psi: Total annular pressure loss in psi
        tvd_ft: True vertical depth in feet
        temperature_correction: Temperature correction factor
    
    Returns:
        ECD in ppg
    """
    ecd = mud_weight_ppg + annular_pressure_loss_psi / (0.052 * tvd_ft) + temperature_correction
    return ecd


def annular_pressure_loss(
    flow_rate_gpm: float,
    mud_weight_ppg: float,
    pv_cp: float,
    yp_lb_100ft2: float,
    annular_length_ft: float,
    hole_diameter_in: float,
    pipe_diameter_in: float
) -> float:
    """
    Calculate annular pressure loss using Bingham Plastic model
    
    Args:
        flow_rate_gpm: Flow rate in gallons per minute
        mud_weight_ppg: Mud weight in ppg
        pv_cp: Plastic viscosity in centipoise
        yp_lb_100ft2: Yield point in lb/100ft²
        annular_length_ft: Length of annular section in feet
        hole_diameter_in: Hole/casing ID in inches
        pipe_diameter_in: Pipe OD in inches
    
    Returns:
        Pressure loss in psi
    """
    # Annular velocity (ft/min)
    annular_velocity = 24.5 * flow_rate_gpm / (hole_diameter_in**2 - pipe_diameter_in**2)
    
    # Hydraulic diameter
    dh = hole_diameter_in - pipe_diameter_in
    
    # Reynolds number
    reynolds = 928 * annular_velocity * dh * mud_weight_ppg / pv_cp
    
    # Friction factor (simplified)
    if reynolds < 2100:  # Laminar
        f = 16 / reynolds
    else:  # Turbulent
        f = 0.0791 / reynolds**0.25
    
    # Pressure loss
    pressure_loss = (f * annular_length_ft * mud_weight_ppg * annular_velocity**2) / (25.8 * dh)
    
    return pressure_loss


def bit_hydraulics(
    flow_rate_gpm: float,
    standpipe_pressure_psi: float,
    jet_sizes_32nds: List[float],
    mud_weight_ppg: float
) -> Dict[str, float]:
    """
    Calculate bit hydraulics parameters
    
    Args:
        flow_rate_gpm: Flow rate in gpm
        standpipe_pressure_psi: Standpipe pressure in psi
        jet_sizes_32nds: List of jet sizes in 32nds of inch
        mud_weight_ppg: Mud weight in ppg
    
    Returns:
        Dictionary with hydraulic parameters
    """
    # Total flow area (sq in)
    tfa = sum([(size/32)**2 * math.pi / 4 for size in jet_sizes_32nds])
    
    # Jet velocity (ft/sec)
    jet_velocity = 0.32 * flow_rate_gpm / tfa
    
    # Bit pressure drop (approximate)
    bit_pressure_drop = mud_weight_ppg * (flow_rate_gpm / (10.67 * tfa))**2
    
    # Hydraulic horsepower
    hhp = (flow_rate_gpm * bit_pressure_drop) / 1714
    
    # Impact force
    impact_force = 0.01823 * flow_rate_gpm * jet_velocity * mud_weight_ppg
    
    # HSI (Hydraulic Horsepower per Square Inch)
    bit_size_in = 8.5  # Default, should be passed as parameter
    bit_area = math.pi * (bit_size_in / 2)**2
    hsi = hhp / bit_area
    
    return {
        'tfa': tfa,
        'jet_velocity': jet_velocity,
        'bit_pressure_drop': bit_pressure_drop,
        'hhp': hhp,
        'impact_force': impact_force,
        'hsi': hsi
    }


def surge_swab_pressure(
    pipe_velocity_ft_min: float,
    mud_weight_ppg: float,
    hole_diameter_in: float,
    pipe_diameter_in: float,
    pv_cp: float,
    yp_lb_100ft2: float,
    closed_end: bool = False
) -> float:
    """
    Calculate surge or swab pressure
    
    Args:
        pipe_velocity_ft_min: Pipe running speed (+ for running in, - for pulling out)
        mud_weight_ppg: Mud weight in ppg
        hole_diameter_in: Hole diameter in inches
        pipe_diameter_in: Pipe OD in inches
        pv_cp: Plastic viscosity in cp
        yp_lb_100ft2: Yield point in lb/100ft²
        closed_end: True if pipe end is closed
    
    Returns:
        Surge/swab pressure in psi/ft
    """
    # Effective velocity
    if closed_end:
        k = (pipe_diameter_in / hole_diameter_in)**2
        v_eff = pipe_velocity_ft_min * k / (1 - k)
    else:
        v_eff = pipe_velocity_ft_min * 0.45  # Approximate for open pipe
    
    # Pressure gradient
    pressure_gradient = 0.052 * mud_weight_ppg * (1 + v_eff / 120)  # Simplified
    
    return pressure_gradient


# ==============================================================================
# Rate of Penetration
# ==============================================================================

def calculate_mse(
    wob_klbs: float,
    rpm: float,
    torque_ft_lbs: float,
    rop_ft_hr: float,
    bit_diameter_in: float
) -> float:
    """
    Calculate Mechanical Specific Energy
    
    Args:
        wob_klbs: Weight on bit in thousands of pounds
        rpm: Rotary speed in RPM
        torque_ft_lbs: Torque in ft-lbs
        rop_ft_hr: Rate of penetration in ft/hr
        bit_diameter_in: Bit diameter in inches
    
    Returns:
        MSE in psi
    """
    bit_area = math.pi * (bit_diameter_in / 2)**2
    
    # MSE = (WOB/Area) + (2π × RPM × Torque)/(60 × Area × ROP)
    mse = (wob_klbs * 1000 / bit_area + 
           2 * math.pi * rpm * torque_ft_lbs / (60 * bit_area * rop_ft_hr))
    
    return mse


def rop_optimization(
    wob_range: Tuple[float, float],
    rpm_range: Tuple[float, float],
    flow_rate_gpm: float,
    ucs_psi: float,
    bit_diameter_in: float
) -> Dict[str, float]:
    """
    Optimize drilling parameters for maximum ROP
    
    Args:
        wob_range: Min and max WOB in klbs
        rpm_range: Min and max RPM
        flow_rate_gpm: Flow rate in gpm
        ucs_psi: Unconfined compressive strength in psi
        bit_diameter_in: Bit diameter in inches
    
    Returns:
        Optimal drilling parameters
    """
    # Simplified ROP model
    def rop_model(params):
        wob, rpm = params
        # Bingham model approximation
        rop = 0.1 * (wob / (bit_diameter_in * ucs_psi / 1000)) * (rpm / 100) * (flow_rate_gpm / 500)
        return -rop  # Negative for minimization
    
    # Constraints
    bounds = [wob_range, rpm_range]
    
    # Initial guess
    x0 = [(wob_range[0] + wob_range[1])/2, (rpm_range[0] + rpm_range[1])/2]
    
    # Optimize
    result = optimize.minimize(rop_model, x0, bounds=bounds, method='L-BFGS-B')
    
    optimal_wob, optimal_rpm = result.x
    optimal_rop = -result.fun
    
    return {
        'optimal_wob': optimal_wob,
        'optimal_rpm': optimal_rpm,
        'optimal_rop': optimal_rop,
        'flow_rate': flow_rate_gpm
    }


# ==============================================================================
# Torque and Drag
# ==============================================================================

def torque_drag_calculation(
    md_ft: np.ndarray,
    inc_deg: np.ndarray,
    azi_deg: np.ndarray,
    pipe_weight_lb_ft: float,
    friction_factor: float,
    wob_klbs: float = 0,
    operation: str = 'rotating'
) -> Dict[str, np.ndarray]:
    """
    Calculate torque and drag using soft string model
    
    Args:
        md_ft: Measured depth array in feet
        inc_deg: Inclination array in degrees
        azi_deg: Azimuth array in degrees
        pipe_weight_lb_ft: Pipe weight in lb/ft
        friction_factor: Friction coefficient
        wob_klbs: Weight on bit in klbs
        operation: 'rotating', 'pulling', or 'slack_off'
    
    Returns:
        Dictionary with torque and drag profiles
    """
    # Convert to radians
    inc_rad = np.radians(inc_deg)
    azi_rad = np.radians(azi_deg)
    
    # Calculate dogleg severity
    dls = np.zeros(len(md_ft))
    for i in range(1, len(md_ft)):
        cos_dog = (np.cos(inc_rad[i-1]) * np.cos(inc_rad[i]) +
                  np.sin(inc_rad[i-1]) * np.sin(inc_rad[i]) * 
                  np.cos(azi_rad[i] - azi_rad[i-1]))
        dls[i] = np.degrees(np.arccos(np.clip(cos_dog, -1, 1))) / (md_ft[i] - md_ft[i-1]) * 100
    
    # Calculate normal force
    normal_force = pipe_weight_lb_ft * np.sin(inc_rad) * (md_ft[1:] - md_ft[:-1])
    
    # Calculate friction force
    if operation == 'rotating':
        friction = friction_factor * normal_force
        torque = np.cumsum(friction[::-1])[::-1]
        drag = None
    elif operation == 'pulling':
        drag = np.cumsum(friction_factor * normal_force[::-1])[::-1]
        torque = None
    else:  # slack_off
        drag = -np.cumsum(friction_factor * normal_force[::-1])[::-1]
        torque = None
    
    return {
        'md': md_ft,
        'torque': torque,
        'drag': drag,
        'dls': dls,
        'normal_force': np.append(normal_force, 0)
    }


def buckling_critical_force(
    pipe_od_in: float,
    pipe_id_in: float,
    hole_diameter_in: float,
    inclination_deg: float,
    youngs_modulus_psi: float = 30e6
) -> Dict[str, float]:
    """
    Calculate critical buckling forces
    
    Args:
        pipe_od_in: Pipe outer diameter in inches
        pipe_id_in: Pipe inner diameter in inches
        hole_diameter_in: Hole diameter in inches
        inclination_deg: Inclination in degrees
        youngs_modulus_psi: Young's modulus in psi
    
    Returns:
        Critical buckling forces
    """
    # Moment of inertia
    I = math.pi / 64 * (pipe_od_in**4 - pipe_id_in**4)
    
    # Radial clearance
    clearance = (hole_diameter_in - pipe_od_in) / 2
    
    # Weight per unit length (steel)
    weight = 2.67 * (pipe_od_in**2 - pipe_id_in**2)  # lb/ft
    
    # Sinusoidal buckling
    F_sinusoidal = 2 * math.sqrt(youngs_modulus_psi * I * weight * 
                                 math.sin(math.radians(inclination_deg)) / clearance)
    
    # Helical buckling
    F_helical = 2.83 * math.sqrt(F_sinusoidal)
    
    return {
        'sinusoidal_buckling': F_sinusoidal,
        'helical_buckling': F_helical,
        'pipe_od': pipe_od_in,
        'hole_diameter': hole_diameter_in,
        'inclination': inclination_deg
    }


# ==============================================================================
# Well Control
# ==============================================================================

def kick_calculations(
    sidpp_psi: float,
    sicp_psi: float,
    original_mud_weight_ppg: float,
    tvd_ft: float,
    pit_gain_bbl: float,
    annular_capacity_bbl_ft: float
) -> Dict[str, float]:
    """
    Calculate kick parameters and kill mud weight
    
    Args:
        sidpp_psi: Shut-in drill pipe pressure in psi
        sicp_psi: Shut-in casing pressure in psi
        original_mud_weight_ppg: Original mud weight in ppg
        tvd_ft: True vertical depth in feet
        pit_gain_bbl: Pit gain in barrels
        annular_capacity_bbl_ft: Annular capacity in bbl/ft
    
    Returns:
        Kick parameters
    """
    # Kill mud weight
    kill_mud_weight = original_mud_weight_ppg + sidpp_psi / (0.052 * tvd_ft)
    
    # Formation pressure
    formation_pressure = sidpp_psi + 0.052 * original_mud_weight_ppg * tvd_ft
    
    # Kick height
    kick_height = pit_gain_bbl / annular_capacity_bbl_ft
    
    # Kick gradient (gas kick assumption)
    if sicp_psi > sidpp_psi:
        kick_gradient = (sicp_psi - sidpp_psi) / (0.052 * kick_height)
    else:
        kick_gradient = 0.1  # Approximate gas gradient
    
    # Maximum casing pressure (at surface when kick at surface)
    max_casing_pressure = formation_pressure - 0.052 * kick_gradient * tvd_ft
    
    return {
        'kill_mud_weight': kill_mud_weight,
        'formation_pressure': formation_pressure,
        'kick_height': kick_height,
        'kick_gradient': kick_gradient,
        'max_casing_pressure': max_casing_pressure,
        'kick_intensity': pit_gain_bbl
    }


def maasp_calculation(
    fracture_gradient_ppg: float,
    current_mud_weight_ppg: float,
    shoe_tvd_ft: float
) -> float:
    """
    Calculate Maximum Allowable Annular Surface Pressure
    
    Args:
        fracture_gradient_ppg: Formation fracture gradient in ppg
        current_mud_weight_ppg: Current mud weight in ppg
        shoe_tvd_ft: Casing shoe TVD in feet
    
    Returns:
        MAASP in psi
    """
    maasp = (fracture_gradient_ppg - current_mud_weight_ppg) * 0.052 * shoe_tvd_ft
    return max(0, maasp)  # Cannot be negative


def kick_tolerance(
    fracture_gradient_ppg: float,
    current_mud_weight_ppg: float,
    shoe_tvd_ft: float,
    total_depth_ft: float,
    kick_intensity_ppg: float = 0.5
) -> Dict[str, float]:
    """
    Calculate kick tolerance at current depth
    
    Args:
        fracture_gradient_ppg: Fracture gradient at shoe in ppg
        current_mud_weight_ppg: Current mud weight in ppg
        shoe_tvd_ft: Shoe TVD in feet
        total_depth_ft: Current total depth in feet
        kick_intensity_ppg: Expected kick intensity in ppg
    
    Returns:
        Kick tolerance parameters
    """
    # Maximum allowable mud weight at TD
    max_mud_weight = fracture_gradient_ppg * shoe_tvd_ft / total_depth_ft
    
    # Kick tolerance
    tolerance = max_mud_weight - current_mud_weight_ppg - kick_intensity_ppg
    
    # Safe drilling window
    window = fracture_gradient_ppg - current_mud_weight_ppg
    
    # Kick margin
    margin = (fracture_gradient_ppg - current_mud_weight_ppg) * shoe_tvd_ft / total_depth_ft
    
    return {
        'kick_tolerance_ppg': tolerance,
        'drilling_window_ppg': window,
        'kick_margin_ppg': margin,
        'max_mud_weight_ppg': max_mud_weight,
        'safe_to_drill': tolerance > 0
    }


# ==============================================================================
# Casing Design
# ==============================================================================

def casing_burst_collapse(
    casing_od_in: float,
    wall_thickness_in: float,
    yield_strength_psi: float,
    internal_pressure_psi: float,
    external_pressure_psi: float,
    safety_factor: float = 1.1
) -> Dict[str, float]:
    """
    Calculate casing burst and collapse ratings
    
    Args:
        casing_od_in: Casing outer diameter in inches
        wall_thickness_in: Wall thickness in inches
        yield_strength_psi: Yield strength in psi
        internal_pressure_psi: Internal pressure in psi
        external_pressure_psi: External pressure in psi
        safety_factor: Design safety factor
    
    Returns:
        Casing design parameters
    """
    # Barlow's formula for burst
    burst_rating = 2 * yield_strength_psi * wall_thickness_in / casing_od_in
    
    # API collapse formula (simplified)
    d_t_ratio = casing_od_in / wall_thickness_in
    if d_t_ratio < 15:
        collapse_rating = yield_strength_psi * (1 - 0.75 * (d_t_ratio / 42)**2)
    else:
        collapse_rating = 46.95e6 / (d_t_ratio * (d_t_ratio - 1)**2)
    
    # Von Mises equivalent stress (biaxial)
    hoop_stress = (internal_pressure_psi - external_pressure_psi) * casing_od_in / (2 * wall_thickness_in)
    axial_stress = 0  # Simplified, should include weight and thermal effects
    von_mises = math.sqrt(hoop_stress**2 + axial_stress**2 - hoop_stress * axial_stress)
    
    # Design checks
    burst_safety = burst_rating / internal_pressure_psi
    collapse_safety = collapse_rating / external_pressure_psi
    
    return {
        'burst_rating': burst_rating,
        'collapse_rating': collapse_rating,
        'von_mises_stress': von_mises,
        'burst_safety_factor': burst_safety,
        'collapse_safety_factor': collapse_safety,
        'design_acceptable': (burst_safety > safety_factor and 
                             collapse_safety > safety_factor)
    }


# ==============================================================================
# Trajectory Calculations
# ==============================================================================

def minimum_curvature_method(
    md: np.ndarray,
    inc: np.ndarray,
    azi: np.ndarray
) -> Dict[str, np.ndarray]:
    """
    Calculate well trajectory using minimum curvature method
    
    Args:
        md: Measured depth array in feet
        inc: Inclination array in degrees
        azi: Azimuth array in degrees
    
    Returns:
        Dictionary with TVD, North, East coordinates
    """
    # Convert to radians
    inc_rad = np.radians(inc)
    azi_rad = np.radians(azi)
    
    # Initialize arrays
    n = len(md)
    tvd = np.zeros(n)
    north = np.zeros(n)
    east = np.zeros(n)
    
    for i in range(1, n):
        # Course length
        course_length = md[i] - md[i-1]
        
        # Dogleg angle
        cos_dogleg = (np.cos(inc_rad[i-1]) * np.cos(inc_rad[i]) +
                     np.sin(inc_rad[i-1]) * np.sin(inc_rad[i]) * 
                     np.cos(azi_rad[i] - azi_rad[i-1]))
        dogleg = np.arccos(np.clip(cos_dogleg, -1, 1))
        
        # Ratio factor
        if dogleg < 0.00001:
            rf = 1
        else:
            rf = 2 / dogleg * np.tan(dogleg / 2)
        
        # Calculate coordinates
        tvd[i] = tvd[i-1] + course_length / 2 * (np.cos(inc_rad[i-1]) + 
                                                  np.cos(inc_rad[i])) * rf
        north[i] = north[i-1] + course_length / 2 * (np.sin(inc_rad[i-1]) * np.cos(azi_rad[i-1]) +
                                                      np.sin(inc_rad[i]) * np.cos(azi_rad[i])) * rf
        east[i] = east[i-1] + course_length / 2 * (np.sin(inc_rad[i-1]) * np.sin(azi_rad[i-1]) +
                                                    np.sin(inc_rad[i]) * np.sin(azi_rad[i])) * rf
    
    # Calculate DLS
    dls = np.zeros(n)
    for i in range(1, n):
        if md[i] > md[i-1]:
            cos_dogleg = (np.cos(inc_rad[i-1]) * np.cos(inc_rad[i]) +
                         np.sin(inc_rad[i-1]) * np.sin(inc_rad[i]) * 
                         np.cos(azi_rad[i] - azi_rad[i-1]))
            dogleg_deg = np.degrees(np.arccos(np.clip(cos_dogleg, -1, 1)))
            dls[i] = dogleg_deg / (md[i] - md[i-1]) * 100
    
    return {
        'md': md,
        'tvd': tvd,
        'north': north,
        'east': east,
        'inclination': inc,
        'azimuth': azi,
        'dls': dls,
        'vertical_section': north * np.cos(np.radians(45)) + east * np.sin(np.radians(45))  # Example VS azimuth
    }


# ==============================================================================
# Drilling Fluids
# ==============================================================================

@dataclass
class MudProperties:
    """Drilling fluid properties calculator"""
    
    mud_weight_ppg: float
    funnel_viscosity_sec: float
    plastic_viscosity_cp: float
    yield_point_lb_100ft2: float
    gel_10sec: float
    gel_10min: float
    fluid_loss_ml: float
    ph: float
    
    @property
    def apparent_viscosity(self) -> float:
        """Calculate apparent viscosity"""
        return self.plastic_viscosity_cp + self.yield_point_lb_100ft2 / 2
    
    @property
    def yield_stress(self) -> float:
        """Calculate yield stress in lb/ft²"""
        return self.yield_point_lb_100ft2 / 100
    
    @property
    def power_law_n(self) -> float:
        """Calculate power law index n"""
        if self.plastic_viscosity_cp > 0:
            return 3.32 * math.log10(2 * self.plastic_viscosity_cp + self.yield_point_lb_100ft2) - \
                   3.32 * math.log10(self.plastic_viscosity_cp + self.yield_point_lb_100ft2)
        return 1.0
    
    @property
    def power_law_k(self) -> float:
        """Calculate power law consistency index K"""
        n = self.power_law_n
        return 511 * self.yield_point_lb_100ft2 / (511**n)
    
    def pressure_to_break_circulation(self, depth_ft: float, pipe_id_in: float) -> float:
        """Calculate pressure to break circulation"""
        # Simplified calculation
        return self.gel_10min * depth_ft / 300
    
    def cutting_slip_velocity(self, cutting_diameter_in: float, 
                             cutting_density_ppg: float) -> float:
        """Calculate cutting slip velocity"""
        # Moore's correlation (simplified)
        dp = cutting_diameter_in / 12  # Convert to feet
        density_diff = cutting_density_ppg - self.mud_weight_ppg
        
        slip_velocity = 1.89 * math.sqrt(dp * density_diff / self.mud_weight_ppg)
        
        return slip_velocity * 60  # Convert to ft/min


# ==============================================================================
# Example Usage
# ==============================================================================

if __name__ == "__main__":
    # Example: ECD Calculation
    ecd = calculate_ecd(
        mud_weight_ppg=12.5,
        annular_pressure_loss_psi=250,
        tvd_ft=10000
    )
    print(f"ECD: {ecd:.2f} ppg")
    
    # Example: MSE Calculation
    mse = calculate_mse(
        wob_klbs=30,
        rpm=120,
        torque_ft_lbs=15000,
        rop_ft_hr=100,
        bit_diameter_in=8.5
    )
    print(f"MSE: {mse:,.0f} psi")
    
    # Example: Kick Calculations
    kick_params = kick_calculations(
        sidpp_psi=500,
        sicp_psi=650,
        original_mud_weight_ppg=12.0,
        tvd_ft=10000,
        pit_gain_bbl=20,
        annular_capacity_bbl_ft=0.1
    )
    print(f"Kill Mud Weight: {kick_params['kill_mud_weight']:.2f} ppg")
    print(f"Formation Pressure: {kick_params['formation_pressure']:.0f} psi")
    
    # Example: Trajectory
    md = np.array([0, 1000, 2000, 3000, 4000, 5000])
    inc = np.array([0, 15, 30, 45, 60, 75])
    azi = np.array([0, 30, 45, 60, 75, 90])
    
    trajectory = minimum_curvature_method(md, inc, azi)
    print(f"TVD at TD: {trajectory['tvd'][-1]:.1f} ft")
    print(f"Horizontal Displacement: {(trajectory['north'][-1]**2 + trajectory['east'][-1]**2)**0.5:.1f} ft")