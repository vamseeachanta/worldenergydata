"""
Oil and Gas Engineering Calculations Template
Domain-specific calculations for petroleum engineering
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, Union
from dataclasses import dataclass


# ==============================================================================
# Reservoir Engineering Calculations
# ==============================================================================

def calculate_stoiip(
    area_acres: float,
    thickness_ft: float, 
    porosity: float,
    water_saturation: float,
    fvf_oil: float
) -> float:
    """
    Calculate Stock Tank Oil Initially In Place (STOIIP)
    
    Args:
        area_acres: Reservoir area in acres
        thickness_ft: Net pay thickness in feet
        porosity: Porosity fraction (0-1)
        water_saturation: Water saturation fraction (0-1)
        fvf_oil: Oil formation volume factor (RB/STB)
    
    Returns:
        STOIIP in stock tank barrels (STB)
    """
    # Validate inputs
    if not 0 < porosity <= 0.4:
        raise ValueError(f"Porosity {porosity} outside valid range (0, 0.4]")
    if not 0 <= water_saturation < 1:
        raise ValueError(f"Water saturation {water_saturation} outside valid range [0, 1)")
    
    # STOIIP = 7758 * A * h * φ * (1 - Sw) / Boi
    stoiip = 7758 * area_acres * thickness_ft * porosity * (1 - water_saturation) / fvf_oil
    
    return stoiip


def calculate_giip(
    area_acres: float,
    thickness_ft: float,
    porosity: float,
    water_saturation: float,
    fvf_gas: float
) -> float:
    """
    Calculate Gas Initially In Place (GIIP)
    
    Args:
        area_acres: Reservoir area in acres
        thickness_ft: Net pay thickness in feet
        porosity: Porosity fraction (0-1)
        water_saturation: Water saturation fraction (0-1)
        fvf_gas: Gas formation volume factor (RCF/SCF)
    
    Returns:
        GIIP in standard cubic feet (SCF)
    """
    # GIIP = 43560 * A * h * φ * (1 - Sw) / Bgi
    giip = 43560 * area_acres * thickness_ft * porosity * (1 - water_saturation) / fvf_gas
    
    return giip


# ==============================================================================
# Decline Curve Analysis
# ==============================================================================

def exponential_decline(qi: float, di: float, time_days: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    Calculate production rate using exponential decline
    
    Args:
        qi: Initial production rate (STB/day or MCF/day)
        di: Nominal decline rate (1/day)
        time_days: Time in days (scalar or array)
    
    Returns:
        Production rate at time t
    """
    return qi * np.exp(-di * time_days)


def hyperbolic_decline(
    qi: float, 
    di: float, 
    b: float, 
    time_days: Union[float, np.ndarray]
) -> Union[float, np.ndarray]:
    """
    Calculate production rate using hyperbolic decline
    
    Args:
        qi: Initial production rate (STB/day or MCF/day)
        di: Initial nominal decline rate (1/day)
        b: Hyperbolic exponent (0 < b < 1)
        time_days: Time in days
    
    Returns:
        Production rate at time t
    """
    if b == 0:
        return exponential_decline(qi, di, time_days)
    elif b == 1:
        # Harmonic decline
        return qi / (1 + di * time_days)
    else:
        # Hyperbolic decline
        return qi / ((1 + b * di * time_days) ** (1/b))


def calculate_eur_exponential(qi: float, di: float, q_limit: float) -> Tuple[float, float]:
    """
    Calculate EUR for exponential decline
    
    Args:
        qi: Initial production rate (STB/day)
        di: Nominal decline rate (1/day)
        q_limit: Economic limit rate (STB/day)
    
    Returns:
        Tuple of (EUR in STB, time to limit in days)
    """
    # Time to economic limit
    t_limit = -np.log(q_limit / qi) / di
    
    # EUR = qi/di * (1 - exp(-di*t))
    eur = qi / di * (1 - np.exp(-di * t_limit))
    
    return eur, t_limit


# ==============================================================================
# PVT Correlations
# ==============================================================================

def standing_bubble_point(
    gas_gravity: float,
    api_gravity: float,
    temperature_f: float,
    solution_gor: float
) -> float:
    """
    Standing's correlation for bubble point pressure
    
    Args:
        gas_gravity: Gas specific gravity (air = 1.0)
        api_gravity: Oil API gravity
        temperature_f: Temperature in Fahrenheit
        solution_gor: Solution gas-oil ratio (SCF/STB)
    
    Returns:
        Bubble point pressure in psia
    """
    # Standing's correlation
    a = 0.00091 * temperature_f - 0.0125 * api_gravity
    pb = 18.2 * ((solution_gor / gas_gravity) ** 0.83 * 10 ** a - 1.4)
    
    return pb


def standing_oil_fvf(
    gas_gravity: float,
    api_gravity: float,
    temperature_f: float,
    solution_gor: float,
    pressure_psia: float,
    bubble_point: Optional[float] = None
) -> float:
    """
    Standing's correlation for oil formation volume factor
    
    Args:
        gas_gravity: Gas specific gravity
        api_gravity: Oil API gravity
        temperature_f: Temperature in Fahrenheit
        solution_gor: Solution GOR at pressure (SCF/STB)
        pressure_psia: Pressure in psia
        bubble_point: Bubble point pressure (calculated if not provided)
    
    Returns:
        Oil formation volume factor (RB/STB)
    """
    # Calculate bubble point if not provided
    if bubble_point is None:
        bubble_point = standing_bubble_point(gas_gravity, api_gravity, temperature_f, solution_gor)
    
    # Oil specific gravity
    oil_sg = 141.5 / (api_gravity + 131.5)
    
    # Formation volume factor at bubble point
    bo = 0.9759 + 0.00012 * (solution_gor * (gas_gravity / oil_sg) ** 0.5 + 
                              1.25 * temperature_f) ** 1.2
    
    # Adjust for pressure above bubble point
    if pressure_psia > bubble_point:
        # Isothermal compressibility (typical value)
        co = 5e-6  # 1/psi
        bo = bo * np.exp(-co * (pressure_psia - bubble_point))
    
    return bo


# ==============================================================================
# Well Performance
# ==============================================================================

def vogel_ipr(
    reservoir_pressure: float,
    test_pressure: float,
    test_rate: float,
    flowing_pressure: float
) -> float:
    """
    Vogel IPR for solution gas drive reservoir
    
    Args:
        reservoir_pressure: Static reservoir pressure (psia)
        test_pressure: Test flowing pressure (psia)
        test_rate: Test production rate (STB/day)
        flowing_pressure: Desired flowing pressure (psia)
    
    Returns:
        Production rate at flowing_pressure (STB/day)
    """
    # Calculate maximum rate (AOF)
    qmax = test_rate / (1 - 0.2 * (test_pressure/reservoir_pressure) - 
                       0.8 * (test_pressure/reservoir_pressure)**2)
    
    # Calculate rate at desired pressure
    if flowing_pressure >= reservoir_pressure:
        return 0.0
    
    q = qmax * (1 - 0.2 * (flowing_pressure/reservoir_pressure) - 
                0.8 * (flowing_pressure/reservoir_pressure)**2)
    
    return q


def gas_lift_performance(
    depth_ft: float,
    tubing_id_in: float,
    liquid_rate_bpd: float,
    water_cut: float,
    gas_injection_mcfd: float,
    wellhead_pressure_psia: float,
    api_gravity: float = 35
) -> Dict[str, float]:
    """
    Simplified gas lift performance calculation
    
    Args:
        depth_ft: Injection depth in feet
        tubing_id_in: Tubing inner diameter in inches
        liquid_rate_bpd: Liquid production rate (BPD)
        water_cut: Water cut fraction (0-1)
        gas_injection_mcfd: Gas injection rate (MCFD)
        wellhead_pressure_psia: Wellhead pressure (psia)
        api_gravity: Oil API gravity
    
    Returns:
        Dictionary with performance parameters
    """
    # Calculate mixture density
    oil_density = 62.4 * (141.5 / (api_gravity + 131.5))  # lb/ft3
    water_density = 62.4  # lb/ft3
    mixture_density = oil_density * (1 - water_cut) + water_density * water_cut
    
    # Calculate GLR
    oil_rate = liquid_rate_bpd * (1 - water_cut)
    if oil_rate > 0:
        glr = gas_injection_mcfd * 1000 / oil_rate  # SCF/STB
    else:
        glr = 0
    
    # Simplified pressure gradient (psi/ft)
    # This is a very simplified correlation
    gradient = mixture_density / 144 * (1 - glr / 10000)
    
    # Bottom hole pressure
    bhp = wellhead_pressure_psia + gradient * depth_ft
    
    return {
        'bhp_psia': bhp,
        'gradient_psi_ft': gradient,
        'glr_scf_stb': glr,
        'mixture_density_lb_ft3': mixture_density
    }


# ==============================================================================
# Economic Calculations
# ==============================================================================

def calculate_npv(
    cash_flows: np.ndarray,
    discount_rate: float,
    initial_investment: float = 0
) -> float:
    """
    Calculate Net Present Value
    
    Args:
        cash_flows: Array of cash flows by period
        discount_rate: Discount rate (as decimal, e.g., 0.10 for 10%)
        initial_investment: Initial investment (positive value)
    
    Returns:
        NPV in currency units
    """
    periods = np.arange(1, len(cash_flows) + 1)
    pv = np.sum(cash_flows / (1 + discount_rate) ** periods)
    npv = pv - initial_investment
    
    return npv


def calculate_irr(
    cash_flows: np.ndarray,
    initial_investment: float
) -> Optional[float]:
    """
    Calculate Internal Rate of Return
    
    Args:
        cash_flows: Array of cash flows by period
        initial_investment: Initial investment (positive value)
    
    Returns:
        IRR as decimal (e.g., 0.15 for 15%) or None if no solution
    """
    # Combine initial investment with cash flows
    all_flows = np.concatenate([[-initial_investment], cash_flows])
    
    # Use numpy's IRR function
    try:
        irr = np.irr(all_flows)
        return irr if not np.isnan(irr) else None
    except:
        return None


def oil_revenue(
    production_bbl: float,
    oil_price_usd: float,
    royalty_fraction: float = 0.125,
    opex_per_bbl: float = 10.0,
    tax_rate: float = 0.35
) -> Dict[str, float]:
    """
    Calculate oil revenue and cash flow
    
    Args:
        production_bbl: Oil production in barrels
        oil_price_usd: Oil price in USD/bbl
        royalty_fraction: Royalty fraction (typically 0.125)
        opex_per_bbl: Operating expense per barrel
        tax_rate: Tax rate on profit
    
    Returns:
        Dictionary with revenue components
    """
    gross_revenue = production_bbl * oil_price_usd
    royalty = gross_revenue * royalty_fraction
    net_revenue = gross_revenue - royalty
    
    opex = production_bbl * opex_per_bbl
    ebitda = net_revenue - opex
    
    tax = max(0, ebitda * tax_rate)
    net_income = ebitda - tax
    
    return {
        'gross_revenue': gross_revenue,
        'royalty': royalty,
        'net_revenue': net_revenue,
        'opex': opex,
        'ebitda': ebitda,
        'tax': tax,
        'net_income': net_income,
        'netback_per_bbl': net_income / production_bbl if production_bbl > 0 else 0
    }


# ==============================================================================
# Unit Conversions
# ==============================================================================

class UnitConverter:
    """Common unit conversions for oil and gas"""
    
    # Pressure conversions
    PSI_TO_KPA = 6.89476
    PSI_TO_BAR = 0.0689476
    
    # Volume conversions
    BBL_TO_M3 = 0.158987
    MCF_TO_M3 = 28.3168
    
    # Length conversions
    FT_TO_M = 0.3048
    IN_TO_MM = 25.4
    
    # Temperature conversions
    @staticmethod
    def f_to_c(temp_f: float) -> float:
        """Convert Fahrenheit to Celsius"""
        return (temp_f - 32) * 5/9
    
    @staticmethod
    def c_to_f(temp_c: float) -> float:
        """Convert Celsius to Fahrenheit"""
        return temp_c * 9/5 + 32
    
    @staticmethod
    def api_to_sg(api_gravity: float) -> float:
        """Convert API gravity to specific gravity"""
        return 141.5 / (api_gravity + 131.5)
    
    @staticmethod
    def sg_to_api(specific_gravity: float) -> float:
        """Convert specific gravity to API gravity"""
        return 141.5 / specific_gravity - 131.5


# ==============================================================================
# Example Usage
# ==============================================================================

if __name__ == "__main__":
    # Example: Calculate STOIIP
    stoiip = calculate_stoiip(
        area_acres=640,
        thickness_ft=50,
        porosity=0.25,
        water_saturation=0.30,
        fvf_oil=1.25
    )
    print(f"STOIIP: {stoiip:,.0f} STB")
    
    # Example: Decline curve analysis
    time = np.linspace(0, 365*3, 100)  # 3 years
    production = hyperbolic_decline(
        qi=1000,  # STB/day
        di=0.001,  # 1/day
        b=0.5,
        time_days=time
    )
    
    # Example: Economic calculation
    revenue = oil_revenue(
        production_bbl=100000,
        oil_price_usd=70,
        royalty_fraction=0.125,
        opex_per_bbl=15
    )
    print(f"Net Income: ${revenue['net_income']:,.2f}")
    print(f"Netback: ${revenue['netback_per_bbl']:.2f}/bbl")