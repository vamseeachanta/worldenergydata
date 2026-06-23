"""
Constants and Unit Conversions for WorldEnergyData

This module provides standardized energy unit conversions and common
constants used across all modules. Units are standardized to enable
consistent calculations and reporting.

Standard Units:
    - Energy: BTU (British Thermal Units)
    - Oil Volume: barrels (bbl)
    - Gas Volume: MCF (thousand cubic feet)
    - Power: MW (megawatts)

Example usage:
    from worldenergydata.common.constants import EnergyUnits, convert_units

    # Convert 1000 barrels of oil to BTU
    btu = convert_units(1000, EnergyUnits.BARREL_OIL, EnergyUnits.BTU)

    # Get conversion factor
    factor = UNIT_CONVERSIONS[EnergyUnits.BARREL_OIL][EnergyUnits.BTU]
"""

from enum import Enum
from typing import Dict, Union


class EnergyUnits(str, Enum):
    """
    Standard energy units used in the energy industry.

    All conversions are relative to BTU as the base unit for energy,
    with volume units maintaining their native form for oil/gas.
    """

    # Energy units
    BTU = "BTU"  # British Thermal Units (base unit)
    MMBTU = "MMBTU"  # Million BTU
    THERM = "THERM"  # 100,000 BTU
    GJ = "GJ"  # Gigajoules
    MWH = "MWH"  # Megawatt-hours
    KWH = "KWH"  # Kilowatt-hours
    TOE = "TOE"  # Tonnes of Oil Equivalent
    BOE = "BOE"  # Barrels of Oil Equivalent

    # Oil volume units
    BARREL = "BBL"  # Barrel (42 US gallons)
    BARREL_OIL = "BBL_OIL"  # Barrel of crude oil
    GALLON = "GAL"  # US Gallon
    LITER = "L"  # Liter
    CUBIC_METER = "M3"  # Cubic meter

    # Gas volume units
    MCF = "MCF"  # Thousand cubic feet
    MMCF = "MMCF"  # Million cubic feet
    BCF = "BCF"  # Billion cubic feet
    TCF = "TCF"  # Trillion cubic feet
    SCF = "SCF"  # Standard cubic feet

    # Mass units
    TONNE = "TONNE"  # Metric tonne
    SHORT_TON = "SHORT_TON"  # US short ton (2000 lbs)
    LONG_TON = "LONG_TON"  # Imperial long ton (2240 lbs)
    KILOGRAM = "KG"  # Kilogram
    POUND = "LB"  # Pound


# Conversion factors to base units
# Energy: conversions TO BTU
# Volume: conversions are between same-type units
UNIT_CONVERSIONS: Dict[EnergyUnits, Dict[EnergyUnits, float]] = {
    # BTU conversions (base energy unit)
    EnergyUnits.BTU: {
        EnergyUnits.BTU: 1.0,
        EnergyUnits.MMBTU: 1e-6,
        EnergyUnits.THERM: 1e-5,
        EnergyUnits.GJ: 1.0545e-6,
        EnergyUnits.MWH: 2.931e-7,
        EnergyUnits.KWH: 2.931e-4,
    },
    EnergyUnits.MMBTU: {
        EnergyUnits.BTU: 1e6,
        EnergyUnits.MMBTU: 1.0,
        EnergyUnits.THERM: 10.0,
        EnergyUnits.GJ: 1.0545,
        EnergyUnits.MWH: 0.2931,
        EnergyUnits.KWH: 293.1,
    },
    EnergyUnits.MWH: {
        EnergyUnits.BTU: 3412141.63,
        EnergyUnits.MMBTU: 3.412,
        EnergyUnits.KWH: 1000.0,
        EnergyUnits.GJ: 3.6,
        EnergyUnits.MWH: 1.0,
    },
    EnergyUnits.KWH: {
        EnergyUnits.BTU: 3412.14,
        EnergyUnits.MMBTU: 0.003412,
        EnergyUnits.KWH: 1.0,
        EnergyUnits.MWH: 0.001,
        EnergyUnits.GJ: 0.0036,
    },
    EnergyUnits.GJ: {
        EnergyUnits.BTU: 947817.0,
        EnergyUnits.MMBTU: 0.9478,
        EnergyUnits.GJ: 1.0,
        EnergyUnits.MWH: 0.2778,
        EnergyUnits.KWH: 277.78,
    },
    # Oil volume conversions
    EnergyUnits.BARREL: {
        EnergyUnits.BARREL: 1.0,
        EnergyUnits.GALLON: 42.0,
        EnergyUnits.LITER: 158.987,
        EnergyUnits.CUBIC_METER: 0.158987,
    },
    EnergyUnits.BARREL_OIL: {
        EnergyUnits.BARREL_OIL: 1.0,
        EnergyUnits.BARREL: 1.0,
        EnergyUnits.BTU: 5.8e6,  # ~5.8 MMBTU per barrel of oil
        EnergyUnits.MMBTU: 5.8,
        EnergyUnits.BOE: 1.0,
        EnergyUnits.GJ: 6.12,
    },
    EnergyUnits.GALLON: {
        EnergyUnits.GALLON: 1.0,
        EnergyUnits.BARREL: 1 / 42,
        EnergyUnits.LITER: 3.785,
        EnergyUnits.CUBIC_METER: 0.003785,
    },
    EnergyUnits.LITER: {
        EnergyUnits.LITER: 1.0,
        EnergyUnits.GALLON: 0.2642,
        EnergyUnits.BARREL: 0.00629,
        EnergyUnits.CUBIC_METER: 0.001,
    },
    EnergyUnits.CUBIC_METER: {
        EnergyUnits.CUBIC_METER: 1.0,
        EnergyUnits.BARREL: 6.2898,
        EnergyUnits.GALLON: 264.172,
        EnergyUnits.LITER: 1000.0,
    },
    # Gas volume conversions
    EnergyUnits.MCF: {
        EnergyUnits.MCF: 1.0,
        EnergyUnits.SCF: 1000.0,
        EnergyUnits.MMCF: 0.001,
        EnergyUnits.BCF: 1e-6,
        EnergyUnits.TCF: 1e-9,
        EnergyUnits.BTU: 1.028e6,  # ~1.028 MMBTU per MCF
        EnergyUnits.MMBTU: 1.028,
        EnergyUnits.BOE: 0.177,  # ~5.64 MCF per BOE
        EnergyUnits.GJ: 1.084,
    },
    EnergyUnits.SCF: {
        EnergyUnits.SCF: 1.0,
        EnergyUnits.MCF: 0.001,
        EnergyUnits.MMCF: 1e-6,
        EnergyUnits.BTU: 1028.0,
    },
    EnergyUnits.MMCF: {
        EnergyUnits.MMCF: 1.0,
        EnergyUnits.MCF: 1000.0,
        EnergyUnits.SCF: 1e6,
        EnergyUnits.BCF: 0.001,
        EnergyUnits.TCF: 1e-6,
        EnergyUnits.MMBTU: 1028.0,
        EnergyUnits.BOE: 177.0,
    },
    EnergyUnits.BCF: {
        EnergyUnits.BCF: 1.0,
        EnergyUnits.MMCF: 1000.0,
        EnergyUnits.MCF: 1e6,
        EnergyUnits.SCF: 1e9,
        EnergyUnits.TCF: 0.001,
        EnergyUnits.BOE: 177000.0,
    },
    EnergyUnits.TCF: {
        EnergyUnits.TCF: 1.0,
        EnergyUnits.BCF: 1000.0,
        EnergyUnits.MMCF: 1e6,
        EnergyUnits.MCF: 1e9,
        EnergyUnits.SCF: 1e12,
        EnergyUnits.BOE: 1.77e8,
    },
    # BOE (Barrel of Oil Equivalent) conversions
    EnergyUnits.BOE: {
        EnergyUnits.BOE: 1.0,
        EnergyUnits.BARREL_OIL: 1.0,
        EnergyUnits.MCF: 5.64,  # ~5.64 MCF = 1 BOE
        EnergyUnits.MMBTU: 5.8,
        EnergyUnits.BTU: 5.8e6,
        EnergyUnits.GJ: 6.12,
    },
    # TOE (Tonne of Oil Equivalent) conversions
    EnergyUnits.TOE: {
        EnergyUnits.TOE: 1.0,
        EnergyUnits.BOE: 7.33,  # ~7.33 barrels per tonne of oil
        EnergyUnits.GJ: 41.868,
        EnergyUnits.MMBTU: 39.68,
        EnergyUnits.BTU: 3.968e7,
        EnergyUnits.MWH: 11.63,
    },
    # Mass conversions
    EnergyUnits.TONNE: {
        EnergyUnits.TONNE: 1.0,
        EnergyUnits.KILOGRAM: 1000.0,
        EnergyUnits.POUND: 2204.62,
        EnergyUnits.SHORT_TON: 1.1023,
        EnergyUnits.LONG_TON: 0.9842,
    },
    EnergyUnits.KILOGRAM: {
        EnergyUnits.KILOGRAM: 1.0,
        EnergyUnits.TONNE: 0.001,
        EnergyUnits.POUND: 2.20462,
    },
    EnergyUnits.POUND: {
        EnergyUnits.POUND: 1.0,
        EnergyUnits.KILOGRAM: 0.4536,
        EnergyUnits.TONNE: 0.0004536,
    },
    EnergyUnits.SHORT_TON: {
        EnergyUnits.SHORT_TON: 1.0,
        EnergyUnits.TONNE: 0.9072,
        EnergyUnits.POUND: 2000.0,
        EnergyUnits.LONG_TON: 0.8929,
    },
    EnergyUnits.LONG_TON: {
        EnergyUnits.LONG_TON: 1.0,
        EnergyUnits.TONNE: 1.016,
        EnergyUnits.POUND: 2240.0,
        EnergyUnits.SHORT_TON: 1.12,
    },
}


def convert_units(
    value: float,
    from_unit: Union[EnergyUnits, str],
    to_unit: Union[EnergyUnits, str],
) -> float:
    """
    Convert a value from one unit to another.

    Args:
        value: The numeric value to convert
        from_unit: The source unit
        to_unit: The target unit

    Returns:
        The converted value

    Raises:
        ValueError: If conversion is not supported

    Example:
        # Convert 1000 barrels of oil to BTU
        btu = convert_units(1000, EnergyUnits.BARREL_OIL, EnergyUnits.BTU)

        # Convert using string units
        mcf = convert_units(100, "BBL_OIL", "MCF")
    """
    # Handle string inputs
    if isinstance(from_unit, str):
        from_unit = EnergyUnits(from_unit)
    if isinstance(to_unit, str):
        to_unit = EnergyUnits(to_unit)

    # Same unit, no conversion needed
    if from_unit == to_unit:
        return value

    # Direct conversion available
    if from_unit in UNIT_CONVERSIONS:
        if to_unit in UNIT_CONVERSIONS[from_unit]:
            return value * UNIT_CONVERSIONS[from_unit][to_unit]

    # Try reverse conversion
    if to_unit in UNIT_CONVERSIONS:
        if from_unit in UNIT_CONVERSIONS[to_unit]:
            return value / UNIT_CONVERSIONS[to_unit][from_unit]

    raise ValueError(
        f"No conversion available from {from_unit.value} to {to_unit.value}"
    )


def get_conversion_factor(
    from_unit: Union[EnergyUnits, str],
    to_unit: Union[EnergyUnits, str],
) -> float:
    """
    Get the conversion factor between two units.

    Args:
        from_unit: The source unit
        to_unit: The target unit

    Returns:
        The conversion factor (multiply source value by this)

    Raises:
        ValueError: If conversion is not supported
    """
    return convert_units(1.0, from_unit, to_unit)


# Common constants for energy data processing
class DataConstants:
    """Common constants used in energy data processing."""

    # API number formats
    API_10_PATTERN = r"^\d{10}$"  # 10-digit API (state + county + sequence)
    API_12_PATTERN = r"^\d{12}$"  # 12-digit API (includes sidetrack)
    API_14_PATTERN = r"^\d{14}$"  # 14-digit API (includes completion)

    # Date formats commonly used in energy data
    DATE_FORMAT_YYYYMM = "%Y%m"  # BSEE production month format
    DATE_FORMAT_YYYYMMDD = "%Y%m%d"  # Compact date format
    DATE_FORMAT_ISO = "%Y-%m-%d"  # ISO 8601 date format
    DATE_FORMAT_US = "%m/%d/%Y"  # US date format

    # Coordinate system constants
    NAD27_EPSG = 4267  # NAD27 coordinate system
    NAD83_EPSG = 4269  # NAD83 coordinate system
    WGS84_EPSG = 4326  # WGS84 coordinate system

    # OCS area codes
    OCS_AREAS = {
        "GOM": "Gulf of Mexico",
        "PAC": "Pacific",
        "ATL": "Atlantic",
        "ALA": "Alaska",
    }

    # Well status codes (common across agencies)
    WELL_STATUS_ACTIVE = ["ACTIVE", "PRODUCING", "PROD"]
    WELL_STATUS_INACTIVE = ["INACTIVE", "SHUT-IN", "SI"]
    WELL_STATUS_PLUGGED = ["PLUGGED", "P&A", "PA"]
    WELL_STATUS_ABANDONED = ["ABANDONED", "ABN"]

    # Production data thresholds
    MAX_REASONABLE_OIL_BBL_DAY = 100000  # Max 100k bbl/day per well
    MAX_REASONABLE_GAS_MCF_DAY = 500000  # Max 500k MCF/day per well
    MAX_REASONABLE_WATER_BBL_DAY = 500000  # Max 500k bbl/day water per well

    # Financial constants
    DEFAULT_DISCOUNT_RATE = 0.10  # 10% default discount rate
    DEFAULT_ROYALTY_RATE = 0.125  # 12.5% federal royalty
    DEFAULT_SEVERANCE_TAX = 0.05  # 5% typical severance tax


# Aliases for common unit conversions
def bbl_to_boe(barrels: float) -> float:
    """Convert barrels of oil to BOE (1:1 for oil)."""
    return barrels


def mcf_to_boe(mcf: float) -> float:
    """Convert MCF of gas to BOE (~5.64 MCF = 1 BOE)."""
    return convert_units(mcf, EnergyUnits.MCF, EnergyUnits.BOE)


def boe_to_mcf(boe: float) -> float:
    """Convert BOE to MCF of gas (~1 BOE = 5.64 MCF)."""
    return convert_units(boe, EnergyUnits.BOE, EnergyUnits.MCF)


def boe_to_mmbtu(boe: float) -> float:
    """Convert BOE to MMBTU (~1 BOE = 5.8 MMBTU)."""
    return convert_units(boe, EnergyUnits.BOE, EnergyUnits.MMBTU)
