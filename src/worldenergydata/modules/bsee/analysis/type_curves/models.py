"""Data models for type curve matching."""

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray


@dataclass
class ReservoirParams:
    """Reservoir and well parameters for type curve analysis."""

    k: float  # permeability, md
    h: float  # net pay thickness, ft
    phi: float  # porosity, fraction
    mu: float  # viscosity, cp
    ct: float  # total compressibility, 1/psi
    rw: float  # wellbore radius, ft
    re: float  # drainage radius, ft
    pi: float  # initial reservoir pressure, psi
    pwf: float  # flowing bottomhole pressure, psi
    Bo: float = 1.0  # oil formation volume factor, rb/STB
    Sw: float = 0.0  # water saturation, fraction
    skin: float = 0.0  # skin factor


@dataclass
class ProductionData:
    """Time-series production data for matching."""

    time: NDArray[np.float64]  # days
    rate: NDArray[np.float64]  # STB/day (oil) or Mscf/day (gas)
    cumulative: NDArray[np.float64]  # STB or Mscf
    pressure_drawdown: NDArray[np.float64] | None = None  # pi - pwf, psi

    def __post_init__(self):
        if len(self.time) == 0:
            raise ValueError("Production data arrays must not be empty")
        if len(self.time) != len(self.rate):
            raise ValueError("time and rate arrays must have same length")
        if len(self.time) != len(self.cumulative):
            raise ValueError("time and cumulative arrays must have same length")


@dataclass
class MatchResult:
    """Result of type curve matching."""

    k: float  # matched permeability, md
    skin: float  # matched skin factor
    re: float  # matched drainage radius, ft
    rwa: float  # apparent wellbore radius, ft
    ooip: float  # original oil in place, STB
    qi: float  # initial rate from match, STB/day
    Di: float  # initial decline rate, 1/day
    b: float  # Arps b-factor (Fetkovich only)
    reD: float  # matched dimensionless drainage radius
    residual: float  # sum of squared residuals
    Ct: float  # time shift factor
    Cq: float  # rate shift factor
    model: str = ""  # "fetkovich" or "blasingame"


@dataclass
class TypeCurveSet:
    """Collection of type curves for plotting/matching."""

    tDd: list[NDArray[np.float64]] = field(default_factory=list)
    qDd: list[NDArray[np.float64]] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    # Blasingame extras
    qDdi: list[NDArray[np.float64]] = field(default_factory=list)
    qDdid: list[NDArray[np.float64]] = field(default_factory=list)
