"""
ABOUTME: Zero-config agent-callable wrapper for the ENIGMA safety analysis module.
ABOUTME: enigma_safety_analysis(asset_type, scenario) -> EnigmaResult
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

SKILL_NAME = "enigma_safety_analysis"

# ---------------------------------------------------------------------------
# Asset × Scenario base risk matrix (0.0–1.0 scale)
# Rows: asset_type | Columns: scenario
# Values represent baseline risk scores reflecting real-world industry data.
# ---------------------------------------------------------------------------

_VALID_ASSET_TYPES = (
    "subsea_pipeline",
    "riser",
    "wellhead",
    "vessel",
    "platform",
    "mooring",
)

_VALID_SCENARIOS = (
    "fatigue",
    "corrosion",
    "overpressure",
    "structural",
    "dropped_object",
    "fire_explosion",
)

# Base severity of each scenario (asset-independent component)
_SCENARIO_BASE: dict[str, float] = {
    "fatigue": 0.30,
    "corrosion": 0.40,
    "overpressure": 0.55,
    "structural": 0.50,
    "dropped_object": 0.45,
    "fire_explosion": 0.75,
}

# Asset vulnerability modifier (multiplier applied to scenario base)
_ASSET_MODIFIER: dict[str, float] = {
    "subsea_pipeline": 1.10,
    "riser": 1.20,
    "wellhead": 0.95,
    "vessel": 1.00,
    "platform": 0.90,
    "mooring": 1.05,
}

# ---------------------------------------------------------------------------
# Fault propagation chains per scenario
# ---------------------------------------------------------------------------

_FAULT_CHAINS: dict[str, list[str]] = {
    "fatigue": [
        "Cyclic loading exceeds material endurance limit",
        "Micro-crack initiates at stress concentration",
        "Crack propagates through wall thickness",
        "Leak-before-break or sudden fracture occurs",
        "Uncontrolled fluid release / structural loss",
    ],
    "corrosion": [
        "Protective coating degrades or is damaged",
        "Electrochemical corrosion cell forms on metal surface",
        "Wall thickness reduction progresses below design minimum",
        "Local pitting or uniform thinning reaches critical depth",
        "Perforation or rupture with product release",
    ],
    "overpressure": [
        "Pressure source exceeds normal operating envelope",
        "Primary pressure control device fails to respond",
        "Secondary relief device activates or fails to open",
        "Equipment pressure rating exceeded",
        "Rupture or explosive venting event",
    ],
    "structural": [
        "Design load assumption violated (storm, vessel impact, etc.)",
        "Primary load-bearing member yields or buckles",
        "Load redistribution overloads adjacent members",
        "Progressive collapse mechanism initiates",
        "Total structural failure or major deformation",
    ],
    "dropped_object": [
        "Load lifted or moved above personnel/equipment",
        "Rigging failure, crane malfunction, or human error",
        "Object free-falls from elevation",
        "Impact with deck, equipment, or structure",
        "Personnel injury or critical equipment damage",
    ],
    "fire_explosion": [
        "Hydrocarbon release forms flammable cloud or pool",
        "Ignition source contacts flammable mixture",
        "Flash fire or deflagration event",
        "Pressure wave damages containment / escalates to BLEVE",
        "Catastrophic loss of containment and structural damage",
    ],
}

# ---------------------------------------------------------------------------
# Recommendations per asset × scenario (key = scenario, value = list)
# ---------------------------------------------------------------------------

_RECOMMENDATIONS: dict[str, list[str]] = {
    "fatigue": [
        "Implement regular fatigue crack inspection using MPI or ACFM",
        "Review cyclic load history and update S-N curve analysis",
        "Apply weld improvement techniques (peening, grinding) at critical joints",
    ],
    "corrosion": [
        "Increase inspection frequency with UT wall-thickness mapping",
        "Review and upgrade cathodic protection system performance",
        "Apply corrosion inhibitor injection programme at vulnerable zones",
    ],
    "overpressure": [
        "Test and certify all pressure safety valves within scheduled intervals",
        "Review HIPPS logic on flowline and topsides to confirm set points",
        "Conduct dynamic surge analysis to identify pressure transient peaks",
    ],
    "structural": [
        "Perform detailed structural integrity assessment against updated metocean data",
        "Inspect and remediate any grouted leg or foundation anomalies",
        "Validate buoyancy and weight control margins against current as-built data",
    ],
    "dropped_object": [
        "Conduct dropped-object register review and implement tertiary restraints",
        "Enforce exclusion zones during all crane lifts over live equipment",
        "Verify lifting gear inspection records and weight certifications",
    ],
    "fire_explosion": [
        "Audit gas detection coverage and verify detector response times",
        "Review ignition-source control procedures in hazardous areas",
        "Validate deluge and fire suppression system operability via live testing",
    ],
}

# Asset-specific recommendation prefixes that add context
_ASSET_PREFIX: dict[str, str] = {
    "subsea_pipeline": "Subsea pipeline: ",
    "riser": "Riser system: ",
    "wellhead": "Wellhead assembly: ",
    "vessel": "Vessel hull/structure: ",
    "platform": "Fixed platform: ",
    "mooring": "Mooring system: ",
}


# ---------------------------------------------------------------------------
# Output type
# ---------------------------------------------------------------------------


@dataclass
class EnigmaResult:
    """Structured result returned by :func:`enigma_safety_analysis`.

    Attributes:
        asset_type: Asset category analysed.
        scenario: Failure scenario evaluated.
        risk_score: Normalised risk score in range 0.0–1.0.
        risk_level: Categorical label — low | medium | high | critical.
        fault_propagation: Ordered failure event sequence (3–5 steps).
        recommendations: Actionable mitigation steps (2–3 items).
        source: Always "enigma".
    """

    asset_type: str
    scenario: str
    risk_score: float
    risk_level: str
    fault_propagation: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    source: str = "enigma"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_risk_score(asset_type: str, scenario: str) -> float:
    """Return risk score (0.0–1.0) for asset × scenario combination."""
    base = _SCENARIO_BASE[scenario]
    modifier = _ASSET_MODIFIER[asset_type]
    raw = base * modifier
    # Clamp to valid range
    return round(min(max(raw, 0.0), 1.0), 4)


def _risk_level_from_score(score: float) -> str:
    """Map numeric risk score to categorical label."""
    if score < 0.30:
        return "low"
    if score < 0.60:
        return "medium"
    if score < 0.80:
        return "high"
    return "critical"


def _build_fault_propagation(scenario: str) -> list[str]:
    """Return the fault propagation chain for the given scenario."""
    return list(_FAULT_CHAINS[scenario])


def _build_recommendations(asset_type: str, scenario: str) -> list[str]:
    """Return 3 actionable recommendations with asset-specific prefix on first."""
    recs = list(_RECOMMENDATIONS[scenario])
    prefix = _ASSET_PREFIX.get(asset_type, "")
    if prefix and recs:
        recs[0] = prefix + recs[0][0].lower() + recs[0][1:]
    return recs


def _validate_inputs(asset_type: str, scenario: str) -> None:
    """Raise ValueError for unknown asset_type or scenario."""
    if asset_type not in _VALID_ASSET_TYPES:
        raise ValueError(
            f"Unknown asset_type '{asset_type}'. "
            f"Valid values: {list(_VALID_ASSET_TYPES)}"
        )
    if scenario not in _VALID_SCENARIOS:
        raise ValueError(
            f"Unknown scenario '{scenario}'. "
            f"Valid values: {list(_VALID_SCENARIOS)}"
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def enigma_safety_analysis(
    asset_type: str,
    scenario: str,
    parameters: Optional[dict] = None,
    calibrator: Optional["EnigmaCalibrator"] = None,  # type: ignore[name-defined]  # noqa: F821
) -> EnigmaResult:
    """Zero-config entry point for ENIGMA technical safety analysis.

    Evaluates asset-scenario risk using a rule-based severity matrix derived
    from offshore industry failure mode data. Works fully offline with no
    external data dependencies.

    Args:
        asset_type: Asset category to evaluate. One of:
            subsea_pipeline | riser | wellhead | vessel | platform | mooring.
        scenario: Failure scenario to assess. One of:
            fatigue | corrosion | overpressure | structural |
            dropped_object | fire_explosion.
        parameters: Optional dict of overrides. Supported keys:
            - ``risk_score_override`` (float 0.0–1.0): bypass computed score.
            Unrecognised keys are silently ignored.
        calibrator: Optional :class:`EnigmaCalibrator` instance. When provided
            and fitted, uses data-driven risk scores instead of the static matrix.

    Returns:
        :class:`EnigmaResult` with risk_score, risk_level, fault_propagation,
        recommendations, and source="enigma".

    Raises:
        ValueError: If asset_type or scenario is not in the supported set.
    """
    _validate_inputs(asset_type, scenario)

    params = parameters or {}

    # Allow explicit score override via parameters dict
    if "risk_score_override" in params:
        score = float(params["risk_score_override"])
        score = round(min(max(score, 0.0), 1.0), 4)
    elif calibrator is not None and getattr(calibrator, "_fitted", False):
        raw_score, _ = calibrator.risk_score(asset_type, scenario)
        score = round(min(max(float(raw_score), 0.0), 1.0), 4)
    else:
        score = _compute_risk_score(asset_type, scenario)

    risk_level = _risk_level_from_score(score)
    fault_propagation = _build_fault_propagation(scenario)
    recommendations = _build_recommendations(asset_type, scenario)

    return EnigmaResult(
        asset_type=asset_type,
        scenario=scenario,
        risk_score=score,
        risk_level=risk_level,
        fault_propagation=fault_propagation,
        recommendations=recommendations,
        source="enigma",
    )
