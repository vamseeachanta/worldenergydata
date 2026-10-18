"""Flow-assurance result types and configurable screening conventions.

Governing basis: docs/agent-pack.md section 3, table S1. No API-derived limits.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


class RiskSeverity(str, Enum):
    """Ordered flow-assurance severity tier (serializes to a plain string)."""

    NOT_EVALUATED = "not_evaluated"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        """Integer ordinal for comparison/aggregation (LOW=0 … CRITICAL=3)."""
        return _SEVERITY_RANK[self]


_SEVERITY_RANK: dict[RiskSeverity, int] = {
    RiskSeverity.NOT_EVALUATED: -1,
    RiskSeverity.LOW: 0,
    RiskSeverity.MEDIUM: 1,
    RiskSeverity.HIGH: 2,
    RiskSeverity.CRITICAL: 3,
}


@dataclass(frozen=True)
class FlowAssuranceThresholds:
    """Configurable screening conventions; no code compliance is established.

    Overridable per call so regional signatures / fluid systems are data, not code.
    """

    # Seabed temperature envelope (deepwater thermocline -> ~4 C floor).
    seabed_temp_surface_c: float = 22.0  # near-surface seabed/intake temp
    seabed_temp_gradient_c_per_m: float = 0.018  # falls to floor by ~1000 m
    seabed_temp_floor_c: float = 4.0  # abyssal thermal floor

    # Hydrate: natural-gas hydrate-stability temperature at deepwater pressure.
    hydrate_formation_temp_c: float = 21.0  # below this (+ gas + water) -> hydrates
    hydrate_deep_subcool_c: float = 10.0  # deep subcooling escalates risk
    hydrate_gor_scf_stb: float = 2000.0  # above this, oil is gassy enough to matter
    hydrate_long_offset_km: float = 30.0  # long offset -> more cooldown

    # Wax / paraffin.
    wax_margin_warn_c: float = 10.0  # WAT this far above seabed -> escalate
    wax_heavy_api: float = 25.0  # heavier crudes deposit more readily
    wax_long_offset_km: float = 30.0

    # Slugging (multiphase hydraulics).
    slugging_gor_scf_stb: float = 1000.0  # enough free gas for two-phase flow
    slugging_long_km: float = 15.0  # long flowline -> terrain/severe slugging
    slugging_low_rate_boed: float = 20000.0  # low turndown -> unstable flow

    # Pack section 3, table S1: configurable conventions, not API limits.
    erosional_velocity_fts: float = 12.0
    erosion_high_gor_scf_stb: float = 3000.0  # retained for API compatibility
    erosion_warn_ratio: float = 0.7
    erosion_high_ratio: float = 1.0
    erosion_critical_ratio: float = 1.5

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.erosional_velocity_fts)
            or self.erosional_velocity_fts <= 0
        ):
            raise ValueError("erosional_velocity_fts must be finite and positive")
        ratios = (
            self.erosion_warn_ratio,
            self.erosion_high_ratio,
            self.erosion_critical_ratio,
        )
        if (
            not all(math.isfinite(r) for r in ratios)
            or not 0 < ratios[0] < ratios[1] < ratios[2]
        ):
            raise ValueError(
                "erosion tier ratios must be finite, positive and strictly increasing"
            )


@dataclass
class FlowAssuranceRisk:
    """One screened hazard: tier + the drivers that set it + scoped mitigations."""

    hazard: str
    severity: RiskSeverity
    drivers: list[str] = field(default_factory=list)
    mitigations: list[str] = field(default_factory=list)
    note: str = ""
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class FlowAssuranceAssessment:
    """Full per-hazard screen of a concept plus an aggregated view."""

    hydrate: FlowAssuranceRisk
    wax: FlowAssuranceRisk
    slugging: FlowAssuranceRisk
    erosion: FlowAssuranceRisk
    overall_severity: RiskSeverity
    mitigations: list[str] = field(default_factory=list)
    not_evaluated_hazards: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.not_evaluated_hazards = [
            r.hazard for r in self.risks if r.severity == RiskSeverity.NOT_EVALUATED
        ]

    @property
    def incomplete(self) -> bool:
        """Whether any hazard lacks the inputs needed for evaluation."""
        return bool(self.not_evaluated_hazards)

    @property
    def risks(self) -> list[FlowAssuranceRisk]:
        """The four hazard risks in a fixed, deterministic order."""
        return [self.hydrate, self.wax, self.slugging, self.erosion]
