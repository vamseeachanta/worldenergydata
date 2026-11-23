"""Tests for Texas RRC field opportunity architecture-signal classes."""

from __future__ import annotations

from worldenergydata.texas_rrc.opportunities.architecture import (
    classify_architecture_signal,
)


def test_classifies_high_access_infill_redevelopment() -> None:
    signal = classify_architecture_signal(
        _row(
            infrastructure_access_class="direct_access",
            production_scale_component_score=95,
            remaining_activity_component_score=75,
            production_maturity_class="mature_active",
        )
    )

    assert signal.architecture_signal_class == "high_access_infill_redevelopment"
    assert "direct_access" in signal.architecture_signal_reason


def test_classifies_infrastructure_constrained_activity() -> None:
    signal = classify_architecture_signal(
        _row(
            infrastructure_access_class="remote_access",
            remaining_activity_component_score=95,
            production_scale_component_score=60,
        )
    )

    assert signal.architecture_signal_class == "infrastructure_constrained_activity"
    assert "follow-up infrastructure" in signal.recommended_followup


def test_classifies_mature_harvest() -> None:
    signal = classify_architecture_signal(
        _row(
            production_maturity_class="late_life",
            remaining_activity_component_score=10,
            infrastructure_access_class="direct_access",
        )
    )

    assert signal.architecture_signal_class == "mature_harvest"


def test_classifies_emerging_growth() -> None:
    signal = classify_architecture_signal(
        _row(
            production_maturity_class="growth",
            remaining_activity_component_score=90,
            infrastructure_component_score=80,
            infrastructure_access_class="near_access",
        )
    )

    assert signal.architecture_signal_class == "emerging_growth"


def test_classifies_low_data_confidence_first() -> None:
    signal = classify_architecture_signal(
        _row(
            quality_flags="missing_lifecycle",
            source_caveats="missing_well_gis",
            infrastructure_access_class="not_available",
            production_scale_component_score=50,
            remaining_activity_component_score=60,
        )
    )

    assert signal.architecture_signal_class == "low_data_confidence"
    assert "missing" in signal.architecture_signal_reason


def test_classifies_monitor_only_fallback() -> None:
    signal = classify_architecture_signal(_row())

    assert signal.architecture_signal_class == "monitor_only"


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "production_maturity_class": "pre_production",
        "production_scale_component_score": 20.0,
        "remaining_activity_component_score": 35.0,
        "infrastructure_component_score": 30.0,
        "infrastructure_access_class": "regional_access",
        "source_caveats": "",
        "quality_flags": "",
    }
    row.update(overrides)
    return row
