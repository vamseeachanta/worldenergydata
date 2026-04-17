"""
ABOUTME: Well planning risk data model with 3-tier authority classification.
ABOUTME: WellPlanningRisk dataclass + RiskAuthority enum + escalation templates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RiskAuthority(Enum):
    """Organisational tier with authority to mitigate the risk."""

    OPERATIONAL = (
        "operational"  # Project execution: swelling clay, mud weight, BOP testing
    )
    TACTICAL = "tactical"  # Cross-functional: rig procedures, casing design
    STRATEGIC = (
        "strategic"  # Corporate/procurement: tool contracts, rig selection, regulatory
    )


class RiskCategory(Enum):
    """Drilling risk domain."""

    WELLBORE_INTEGRITY = "wellbore_integrity"
    PRESSURE_MANAGEMENT = "pressure_management"
    HOLE_CLEANING = "hole_cleaning"
    RIG_CAPABILITY = "rig_capability"
    REGULATORY = "regulatory"
    FORMATION_EVALUATION = "formation_evaluation"
    COMPLETION = "completion"


class RiskSeverity(Enum):
    """Consequence severity — integer value used in risk score calculation."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class WellPlanningRisk:
    """Single risk entry in the well planning risk register.

    ``risk_score`` is computed as ``severity.value * probability`` and must be
    provided at construction time (it is not auto-computed so callers can
    override rounding).
    """

    risk_id: str
    title: str
    description: str
    category: RiskCategory
    authority: RiskAuthority
    severity: RiskSeverity
    probability: float  # 0.0–1.0
    risk_score: float  # severity.value * probability
    mitigation_owner: str  # role responsible e.g. "Drilling Engineer"
    mitigation_action: str  # specific action to reduce risk
    mpd_mitigation: bool  # True if MPD technology reduces this risk
    escalation_template: str  # pre-written escalation message
    related_wrk: list[str] = field(default_factory=list)
