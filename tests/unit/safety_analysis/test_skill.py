"""
Tests for worldenergydata.safety_analysis.skill — ENIGMA safety analysis wrapper.
"""

import pytest

from worldenergydata.safety_analysis.skill import (
    SKILL_NAME,
    EnigmaResult,
    enigma_safety_analysis,
)

# ---------------------------------------------------------------------------
# Constants used in multiple tests
# ---------------------------------------------------------------------------

ALL_ASSET_TYPES = [
    "subsea_pipeline",
    "riser",
    "wellhead",
    "vessel",
    "platform",
    "mooring",
]

ALL_SCENARIOS = [
    "fatigue",
    "corrosion",
    "overpressure",
    "structural",
    "dropped_object",
    "fire_explosion",
]

VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


# ---------------------------------------------------------------------------
# SKILL_NAME constant
# ---------------------------------------------------------------------------


def test_skill_name_value():
    assert SKILL_NAME == "enigma_safety_analysis"


def test_skill_name_is_string():
    assert isinstance(SKILL_NAME, str)


# ---------------------------------------------------------------------------
# Return type and required fields
# ---------------------------------------------------------------------------


def test_returns_enigma_result():
    result = enigma_safety_analysis("subsea_pipeline", "corrosion")
    assert isinstance(result, EnigmaResult)


def test_result_has_asset_type():
    result = enigma_safety_analysis("riser", "fatigue")
    assert hasattr(result, "asset_type")


def test_result_has_scenario():
    result = enigma_safety_analysis("wellhead", "overpressure")
    assert hasattr(result, "scenario")


def test_result_has_risk_score():
    result = enigma_safety_analysis("vessel", "structural")
    assert hasattr(result, "risk_score")


def test_result_has_risk_level():
    result = enigma_safety_analysis("platform", "dropped_object")
    assert hasattr(result, "risk_level")


def test_result_has_fault_propagation():
    result = enigma_safety_analysis("mooring", "fire_explosion")
    assert hasattr(result, "fault_propagation")


def test_result_has_recommendations():
    result = enigma_safety_analysis("subsea_pipeline", "fatigue")
    assert hasattr(result, "recommendations")


def test_result_has_source():
    result = enigma_safety_analysis("riser", "corrosion")
    assert hasattr(result, "source")


# ---------------------------------------------------------------------------
# Field value contracts
# ---------------------------------------------------------------------------


def test_source_is_enigma():
    result = enigma_safety_analysis("subsea_pipeline", "corrosion")
    assert result.source == "enigma"


def test_risk_score_is_float():
    result = enigma_safety_analysis("wellhead", "fatigue")
    assert isinstance(result.risk_score, float)


def test_risk_score_lower_bound():
    result = enigma_safety_analysis("platform", "fatigue")
    assert result.risk_score >= 0.0


def test_risk_score_upper_bound():
    result = enigma_safety_analysis("vessel", "fire_explosion")
    assert result.risk_score <= 1.0


def test_risk_level_is_valid():
    result = enigma_safety_analysis("subsea_pipeline", "corrosion")
    assert result.risk_level in VALID_RISK_LEVELS


def test_fault_propagation_is_nonempty_list():
    result = enigma_safety_analysis("riser", "overpressure")
    assert isinstance(result.fault_propagation, list)
    assert len(result.fault_propagation) > 0


def test_fault_propagation_elements_are_strings():
    result = enigma_safety_analysis("mooring", "structural")
    for item in result.fault_propagation:
        assert isinstance(item, str)
        assert len(item) > 0


def test_recommendations_is_nonempty_list():
    result = enigma_safety_analysis("vessel", "dropped_object")
    assert isinstance(result.recommendations, list)
    assert len(result.recommendations) > 0


def test_recommendations_elements_are_strings():
    result = enigma_safety_analysis("platform", "fire_explosion")
    for item in result.recommendations:
        assert isinstance(item, str)
        assert len(item) > 0


def test_asset_type_echoed_in_result():
    result = enigma_safety_analysis("subsea_pipeline", "corrosion")
    assert result.asset_type == "subsea_pipeline"


def test_scenario_echoed_in_result():
    result = enigma_safety_analysis("riser", "fatigue")
    assert result.scenario == "fatigue"


# ---------------------------------------------------------------------------
# risk_level matches risk_score thresholds
# ---------------------------------------------------------------------------


def test_risk_level_low_threshold():
    # Platform + fatigue gives lowest score: 0.30 * 0.90 = 0.27 → low
    result = enigma_safety_analysis("platform", "fatigue")
    assert result.risk_score < 0.30
    assert result.risk_level == "low"


def test_risk_level_critical_threshold():
    # Riser + fire_explosion: 0.75 * 1.20 = 0.90 → critical
    result = enigma_safety_analysis("riser", "fire_explosion")
    assert result.risk_score >= 0.80
    assert result.risk_level == "critical"


def test_risk_level_consistency_with_score():
    """risk_level must always be consistent with the risk_score value."""
    for asset in ALL_ASSET_TYPES:
        for scenario in ALL_SCENARIOS:
            result = enigma_safety_analysis(asset, scenario)
            score = result.risk_score
            if score < 0.30:
                expected = "low"
            elif score < 0.60:
                expected = "medium"
            elif score < 0.80:
                expected = "high"
            else:
                expected = "critical"
            assert result.risk_level == expected, (
                f"{asset}/{scenario}: score={score} => expected {expected!r}, "
                f"got {result.risk_level!r}"
            )


# ---------------------------------------------------------------------------
# All asset types work
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("asset_type", ALL_ASSET_TYPES)
def test_all_asset_types_return_result(asset_type):
    result = enigma_safety_analysis(asset_type, "corrosion")
    assert isinstance(result, EnigmaResult)
    assert result.asset_type == asset_type


# ---------------------------------------------------------------------------
# All scenarios work
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
def test_all_scenarios_return_result(scenario):
    result = enigma_safety_analysis("vessel", scenario)
    assert isinstance(result, EnigmaResult)
    assert result.scenario == scenario


# ---------------------------------------------------------------------------
# Import from package namespace
# ---------------------------------------------------------------------------


def test_package_namespace_import():
    from worldenergydata.safety_analysis import enigma_safety_analysis as fn
    from worldenergydata.safety_analysis import EnigmaResult as ER
    from worldenergydata.safety_analysis import SKILL_NAME as SN

    result = fn("subsea_pipeline", "fatigue")
    assert isinstance(result, ER)
    assert SN == "enigma_safety_analysis"


# ---------------------------------------------------------------------------
# parameters kwarg accepted without error
# ---------------------------------------------------------------------------


def test_parameters_kwarg_accepted_empty_dict():
    result = enigma_safety_analysis("vessel", "corrosion", parameters={})
    assert isinstance(result, EnigmaResult)


def test_parameters_kwarg_accepted_none():
    result = enigma_safety_analysis("wellhead", "structural", parameters=None)
    assert isinstance(result, EnigmaResult)


def test_parameters_risk_score_override():
    result = enigma_safety_analysis(
        "platform", "fatigue", parameters={"risk_score_override": 0.95}
    )
    assert result.risk_score == pytest.approx(0.95, abs=1e-4)
    assert result.risk_level == "critical"


def test_parameters_unknown_keys_ignored():
    result = enigma_safety_analysis(
        "riser", "corrosion", parameters={"unknown_key": "foo"}
    )
    assert isinstance(result, EnigmaResult)


# ---------------------------------------------------------------------------
# Severity ordering: fire_explosion > fatigue for same asset
# ---------------------------------------------------------------------------


def test_fire_explosion_higher_than_fatigue_for_vessel():
    r_fire = enigma_safety_analysis("vessel", "fire_explosion")
    r_fatigue = enigma_safety_analysis("vessel", "fatigue")
    assert r_fire.risk_score > r_fatigue.risk_score


def test_fire_explosion_higher_than_corrosion_for_platform():
    r_fire = enigma_safety_analysis("platform", "fire_explosion")
    r_corrosion = enigma_safety_analysis("platform", "corrosion")
    assert r_fire.risk_score > r_corrosion.risk_score


# ---------------------------------------------------------------------------
# Different asset types produce different scores for same scenario
# ---------------------------------------------------------------------------


def test_different_assets_different_scores_for_fire_explosion():
    scores = {
        asset: enigma_safety_analysis(asset, "fire_explosion").risk_score
        for asset in ALL_ASSET_TYPES
    }
    # Not all scores should be identical
    assert len(set(scores.values())) > 1, "All asset types returned the same score"


def test_riser_higher_than_platform_for_same_scenario():
    # riser modifier=1.20 > platform modifier=0.90 → riser should score higher
    r_riser = enigma_safety_analysis("riser", "corrosion")
    r_platform = enigma_safety_analysis("platform", "corrosion")
    assert r_riser.risk_score > r_platform.risk_score


# ---------------------------------------------------------------------------
# Error handling: invalid inputs
# ---------------------------------------------------------------------------


def test_invalid_asset_type_raises_value_error():
    with pytest.raises(ValueError, match="asset_type"):
        enigma_safety_analysis("submarine", "fatigue")


def test_invalid_scenario_raises_value_error():
    with pytest.raises(ValueError, match="scenario"):
        enigma_safety_analysis("vessel", "tsunami")
