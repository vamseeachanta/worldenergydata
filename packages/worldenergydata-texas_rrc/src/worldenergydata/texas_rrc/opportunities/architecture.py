"""Classify Texas RRC field-opportunity architecture signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ArchitectureSignal:
    """One screening architecture signal for a ranked Texas RRC field."""

    architecture_signal_class: str
    architecture_signal_reason: str
    recommended_followup: str


def classify_architecture_signal(row: Mapping[str, object]) -> ArchitectureSignal:
    """Classify a field into a deterministic screening-signal class."""
    maturity = _text(row.get("production_maturity_class")).lower()
    access = _text(row.get("infrastructure_access_class")).lower()
    production = _number(row.get("production_scale_component_score"))
    activity = _number(row.get("remaining_activity_component_score"))
    infrastructure = _number(row.get("infrastructure_component_score"))
    caveats = _terms(row.get("source_caveats")) + _terms(row.get("quality_flags"))

    if _low_confidence(access, caveats) and not (production >= 75 and activity >= 75):
        return ArchitectureSignal(
            "low_data_confidence",
            "missing or unavailable lifecycle/GIS/infrastructure evidence",
            "Resolve source gaps before using this field for architecture screening.",
        )
    if (
        maturity in {"growth", "early_development"}
        and activity >= 70
        and infrastructure >= 60
    ):
        return ArchitectureSignal(
            "emerging_growth",
            f"{maturity} maturity with strong activity and infrastructure signal",
            "Review growth pattern, permits, completions, and local gathering options.",
        )
    if (
        access in {"direct_access", "near_access"}
        and production >= 70
        and activity >= 50
    ):
        return ArchitectureSignal(
            "high_access_infill_redevelopment",
            f"{access} plus high production scale and remaining activity",
            "Review infill, recompletion, and redevelopment candidates.",
        )
    if activity >= 70 and access in _CONSTRAINED_ACCESS_CLASSES:
        return ArchitectureSignal(
            "infrastructure_constrained_activity",
            f"high activity with {access or 'missing'} infrastructure access",
            "Run follow-up infrastructure, market-access, and routing screening.",
        )
    if maturity in {"late_life", "mature_active"} and activity < 35:
        return ArchitectureSignal(
            "mature_harvest",
            f"{maturity} maturity with low remaining activity",
            "Review harvest, abandonment, and monitoring context.",
        )
    return ArchitectureSignal(
        "monitor_only",
        "no strong opportunity or constraint signal",
        "Monitor during the next source refresh cycle.",
    )


_CONSTRAINED_ACCESS_CLASSES = {
    "",
    "regional_access",
    "remote_access",
    "isolated_or_unknown",
    "not_available",
}


def _low_confidence(access: str, caveats: tuple[str, ...]) -> bool:
    if access == "not_available":
        return True
    needles = ("missing", "not_available")
    return any(any(needle in term for needle in needles) for term in caveats)


def _terms(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    normalized = str(value).replace(",", ";").replace("|", ";")
    return tuple(term.strip().lower() for term in normalized.split(";") if term.strip())


def _number(value: object) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


__all__ = [
    "ArchitectureSignal",
    "classify_architecture_signal",
]
