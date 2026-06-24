"""Unit conversion utilities for the multi-source adapter framework.

Canonical units are SI:
    Length   — metres (m)
    Volume   — cubic metres (m³)
    Mass     — kilograms (kg)
    Pressure — pascals (Pa)
    Density  — kg/m³

Each adapter calls these helpers during its ``adapt()`` to normalise
source-native units before populating AdapterResult DataFrames.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Length
# ---------------------------------------------------------------------------


def feet_to_metres(ft: float) -> float:
    """Convert feet to metres."""
    return ft * 0.3048


def metres_to_feet(m: float) -> float:
    """Convert metres to feet."""
    return m / 0.3048


def inches_to_metres(inches: float) -> float:
    """Convert inches to metres."""
    return inches * 0.0254


def inches_to_mm(inches: float) -> float:
    """Convert inches to millimetres."""
    return inches * 25.4


# ---------------------------------------------------------------------------
# Volume — oil
# ---------------------------------------------------------------------------

# 1 barrel = 0.158987 m³
BBL_TO_M3 = 0.158987
M3_TO_BBL = 1.0 / BBL_TO_M3

# Norwegian standard: 1 Sm³ ≈ 6.29 barrels
SM3_TO_BBL = 6.28981


def barrels_to_m3(bbl: float) -> float:
    """Convert barrels to cubic metres."""
    return bbl * BBL_TO_M3


def m3_to_barrels(m3: float) -> float:
    """Convert cubic metres to barrels."""
    return m3 * M3_TO_BBL


def mmbbl_to_m3(mmbbl: float) -> float:
    """Convert millions of barrels to cubic metres."""
    return mmbbl * 1e6 * BBL_TO_M3


# ---------------------------------------------------------------------------
# Volume — gas
# ---------------------------------------------------------------------------

# 1 MCF = 28.3168 m³  (1000 cubic feet)
MCF_TO_M3 = 28.3168

# 1 billion Sm³ ≈ 35.3 BCF
BILLION_SM3_TO_BCF = 35.3147
BCF_TO_M3 = 28_316_846.592  # 1 BCF in m³


def mcf_to_m3(mcf: float) -> float:
    """Convert thousand cubic feet (MCF) to cubic metres."""
    return mcf * MCF_TO_M3


def bcf_to_m3(bcf: float) -> float:
    """Convert billion cubic feet (BCF) to cubic metres."""
    return bcf * BCF_TO_M3


def billion_sm3_to_m3(bsm3: float) -> float:
    """Convert billion standard cubic metres to cubic metres."""
    return bsm3 * 1e9


# ---------------------------------------------------------------------------
# Pressure
# ---------------------------------------------------------------------------

PSI_TO_PA = 6894.757


def psi_to_pa(psi: float) -> float:
    """Convert pounds per square inch to pascals."""
    return psi * PSI_TO_PA


def pa_to_psi(pa: float) -> float:
    """Convert pascals to pounds per square inch."""
    return pa / PSI_TO_PA


# ---------------------------------------------------------------------------
# Mass / linear weight
# ---------------------------------------------------------------------------

LB_PER_FT_TO_KG_PER_M = 1.48816  # lb/ft -> kg/m


def lb_per_ft_to_kg_per_m(lpf: float) -> float:
    """Convert pounds per foot to kilograms per metre."""
    return lpf * LB_PER_FT_TO_KG_PER_M


# ---------------------------------------------------------------------------
# BOE (Barrel of Oil Equivalent)
# ---------------------------------------------------------------------------

# Standard conversion: 1 BOE = 5.8 MMBTU ≈ 6 MCF gas
MCF_TO_BOE = 1.0 / 5.8  # ~0.1724


def gas_mcf_to_boe(mcf: float) -> float:
    """Convert gas volume in MCF to barrel of oil equivalent."""
    return mcf * MCF_TO_BOE


# ---------------------------------------------------------------------------
# DataFrame helpers
# ---------------------------------------------------------------------------


def convert_column(
    df,
    column: str,
    converter,
    target_column: str | None = None,
) -> None:
    """Apply a unit converter to a DataFrame column in-place.

    Args:
        df: pandas DataFrame.
        column: Source column name.
        converter: Callable(float) -> float.
        target_column: Name for the converted column. If *None*, overwrites
            the source column.
    """
    if column not in df.columns:
        return
    target = target_column or column
    df[target] = df[column].apply(
        lambda v: converter(v) if v is not None and v == v else v
    )
