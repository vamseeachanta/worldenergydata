"""
Unit conversion registry for worldenergydata.

All factors referenced to API, ISO, or ASTM standards where cited.
This is the single authoritative source; all production modules import
from here rather than defining their own local constants.
"""

from __future__ import annotations

import pandas as pd


class OilUnits:
    """Liquid hydrocarbon volume conversions.

    References:
        API MPMS Ch. 11 (Measurement of Petroleum and Petroleum Products)
    """

    SM3_TO_BBL: float = 6.2898      # 1 standard m³ crude → barrels (API MPMS Ch.11)
    TONNE_TO_BBL: float = 7.33      # 1 metric tonne crude → barrels (API ~35°API)
    BBL_TO_SM3: float = 0.158987    # exact inverse of SM3_TO_BBL
    BBL_TO_TONNE: float = 0.136428  # exact inverse of TONNE_TO_BBL
    M3_TO_BBL: float = 6.2898       # m³ == Sm³ at standard conditions


class GasUnits:
    """Gas volume conversions.

    Standard conditions: 15°C, 101.325 kPa (1 atm).

    References:
        ISO 13443 (Natural gas — Standard reference conditions)
        GPA 2145 (Physical Constants for Natural Gas and Gas Processing)
    """

    SM3_TO_SCF: float = 35.3147         # 1 Sm³ → standard cubic feet
    SM3_TO_MMSCF: float = 35.3147e-6   # 1 Sm³ → million standard cubic feet
    MSM3_TO_BCF: float = 0.0353147     # 1 MSm³ → BCF
    MSM3_TO_MMSCF: float = 35.3147     # 1 MSm³ → MMscf
    MMSCF_TO_MCF: float = 1000.0       # 1 MMscf → Mcf (thousand cubic feet)
    MCF_TO_MMSCF: float = 0.001        # 1 Mcf → MMscf
    BCF_TO_TCF: float = 0.001          # 1 BCF → TCF


class WaterUnits:
    """Water volume conversions.

    Note: water density ≈ 1.0 tonne/m³ at surface conditions.
    """

    M3_TO_BBL: float = 6.2898      # 1 m³ water → barrels
    TONNE_TO_BBL: float = 6.2898   # 1 tonne water → barrels (density ≈ 1 t/m³)


class PressureUnits:
    """Pressure conversions.

    References:
        NIST special publication 811
    """

    PSI_TO_BAR: float = 0.0689476  # 1 psi → bar
    BAR_TO_PSI: float = 14.5038    # 1 bar → psi
    KPA_TO_PSI: float = 0.145038   # 1 kPa → psi


class EnergyUnits:
    """Energy / calorific conversions.

    References:
        SPE guide — 1 BOE = 5.8 MMBTU; ~6 MCF/BOE rule of thumb
    """

    BBL_TO_BOE: float = 1.0        # 1 bbl crude oil = 1 BOE (by definition)
    MCF_TO_BOE: float = 0.178      # 1 MCF gas ≈ 0.178 BOE (6 MCF/BOE rule of thumb)
    MWH_TO_BOE: float = 0.5883     # 1 MWh ≈ 0.5883 BOE (based on 5.8 MMBTU/BOE)


# ---------------------------------------------------------------------------
# Flat registry for programmatic lookup
# ---------------------------------------------------------------------------

UNIT_REGISTRY: dict[tuple[str, str], float] = {
    # Oil — liquid volume
    ("sm3", "bbl"):        OilUnits.SM3_TO_BBL,
    ("bbl", "sm3"):        OilUnits.BBL_TO_SM3,
    ("tonne_oil", "bbl"):  OilUnits.TONNE_TO_BBL,
    ("bbl", "tonne_oil"):  OilUnits.BBL_TO_TONNE,
    ("m3", "bbl"):         OilUnits.M3_TO_BBL,

    # Gas — volume
    ("msm3", "bcf"):       GasUnits.MSM3_TO_BCF,
    ("msm3", "mmscf"):     GasUnits.MSM3_TO_MMSCF,
    ("mmscf", "mcf"):      GasUnits.MMSCF_TO_MCF,
    ("mcf", "mmscf"):      GasUnits.MCF_TO_MMSCF,
    ("sm3_gas", "scf"):    GasUnits.SM3_TO_SCF,
    ("bcf", "tcf"):        GasUnits.BCF_TO_TCF,

    # Pressure
    ("psi", "bar"):        PressureUnits.PSI_TO_BAR,
    ("bar", "psi"):        PressureUnits.BAR_TO_PSI,
    ("kpa", "psi"):        PressureUnits.KPA_TO_PSI,

    # Energy / BOE
    ("bbl", "boe"):        EnergyUnits.BBL_TO_BOE,
    ("mcf", "boe"):        EnergyUnits.MCF_TO_BOE,
    ("mwh", "boe"):        EnergyUnits.MWH_TO_BOE,
}


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a scalar value between registered units.

    Args:
        value: Numeric value to convert.
        from_unit: Source unit key (lowercase string, e.g. ``"sm3"``).
        to_unit: Target unit key (lowercase string, e.g. ``"bbl"``).

    Returns:
        Converted float value.

    Raises:
        KeyError: If the (from_unit, to_unit) pair is not in UNIT_REGISTRY.

    Example::

        from worldenergydata.common.units import convert
        bbl = convert(1000.0, "sm3", "bbl")  # → 6289.8
    """
    key = (from_unit, to_unit)
    if key not in UNIT_REGISTRY:
        raise KeyError(
            f"no conversion registered for {from_unit!r} → {to_unit!r}. "
            f"Available pairs: {sorted(UNIT_REGISTRY)}"
        )
    return value * UNIT_REGISTRY[key]


def convert_series(
    series: pd.Series,
    from_unit: str,
    to_unit: str,
) -> pd.Series:
    """Vectorised conversion for a pandas Series.

    Args:
        series: Pandas Series of numeric values.
        from_unit: Source unit key (lowercase string).
        to_unit: Target unit key (lowercase string).

    Returns:
        New Series with converted values; original index is preserved.

    Raises:
        KeyError: If the (from_unit, to_unit) pair is not in UNIT_REGISTRY.

    Example::

        from worldenergydata.common.units import convert_series
        import pandas as pd
        oil_bbl = convert_series(df["oil_sm3"], "sm3", "bbl")
    """
    key = (from_unit, to_unit)
    if key not in UNIT_REGISTRY:
        raise KeyError(
            f"no conversion registered for {from_unit!r} → {to_unit!r}. "
            f"Available pairs: {sorted(UNIT_REGISTRY)}"
        )
    factor = UNIT_REGISTRY[key]
    return series * factor
