# ABOUTME: Unit tests for data completeness scoring for decommissioning readiness.
# ABOUTME: Covers score ranges, weighted averages, gap detection, risk levels, and portfolio DataFrame.

"""Unit tests for worldenergydata.decommissioning.data_completeness."""

import pytest
import pandas as pd

from worldenergydata.decommissioning.data_completeness import (
    CompletenessScore,
    DataCompletenessScorer,
)

_ALL_CATEGORIES = [
    "as_built_drawings",
    "inspection_records",
    "well_records",
    "mooring_documents",
    "environmental_surveys",
]


@pytest.fixture()
def scorer() -> DataCompletenessScorer:
    return DataCompletenessScorer()


# ---------------------------------------------------------------------------
# Returns correct type
# ---------------------------------------------------------------------------


def test_score_returns_completeness_score(scorer):
    result = scorer.score("FieldA", {"as_built_drawings": True})
    assert isinstance(result, CompletenessScore)


def test_score_stores_field_name(scorer):
    result = scorer.score("TestField", {})
    assert result.field_name == "TestField"


# ---------------------------------------------------------------------------
# Individual scores are in [0.0, 1.0]
# ---------------------------------------------------------------------------


def test_all_true_scores_are_one(scorer):
    data = {cat: True for cat in _ALL_CATEGORIES}
    result = scorer.score("F1", data)
    assert result.as_built_drawings == pytest.approx(1.0)
    assert result.inspection_records == pytest.approx(1.0)
    assert result.well_records == pytest.approx(1.0)
    assert result.mooring_documents == pytest.approx(1.0)
    assert result.environmental_surveys == pytest.approx(1.0)


def test_all_false_scores_are_zero(scorer):
    data = {cat: False for cat in _ALL_CATEGORIES}
    result = scorer.score("F2", data)
    assert result.as_built_drawings == pytest.approx(0.0)
    assert result.inspection_records == pytest.approx(0.0)
    assert result.well_records == pytest.approx(0.0)


def test_float_score_in_range(scorer):
    result = scorer.score("F3", {"inspection_records": 0.6})
    assert 0.0 <= result.inspection_records <= 1.0


def test_overall_score_in_range(scorer):
    data = {"as_built_drawings": 0.8, "inspection_records": 0.5}
    result = scorer.score("F4", data)
    assert 0.0 <= result.overall_score <= 1.0


def test_all_complete_overall_is_one(scorer):
    data = {cat: True for cat in _ALL_CATEGORIES}
    result = scorer.score("F5", data)
    assert result.overall_score == pytest.approx(1.0, abs=0.001)


def test_all_missing_overall_is_zero(scorer):
    result = scorer.score("F6", {})
    assert result.overall_score == pytest.approx(0.0, abs=0.001)


# ---------------------------------------------------------------------------
# Overall score is weighted average
# ---------------------------------------------------------------------------


def test_overall_score_is_weighted_average(scorer):
    # For jacket (fixed structure, no mooring), mooring weight (0.10) is
    # redistributed equally across the other 4 categories (+0.025 each).
    # as_built_drawings effective weight = 0.30 + 0.025 = 0.325
    data = {"as_built_drawings": True}
    result = scorer.score("F7", data, asset_type="jacket")
    # Expected: 1.0 * 0.325 = 0.325 (others are 0)
    assert result.overall_score == pytest.approx(0.325, abs=0.01)


def test_partial_scores_average_correctly(scorer):
    data = {
        "as_built_drawings": 1.0,    # weight 0.30
        "inspection_records": 1.0,   # weight 0.25
        "well_records": 0.0,
        "mooring_documents": 0.0,
        "environmental_surveys": 0.0,
    }
    result = scorer.score("F8", data, asset_type="fpso")
    # Expected: 0.30 + 0.25 = 0.55
    assert result.overall_score == pytest.approx(0.55, abs=0.01)


# ---------------------------------------------------------------------------
# Gaps
# ---------------------------------------------------------------------------


def test_missing_data_appears_in_gaps(scorer):
    data = {"as_built_drawings": True}  # others missing → gaps
    result = scorer.score("F9", data)
    # inspection_records, well_records, mooring_documents, environmental_surveys all 0
    assert "inspection_records" in result.gaps


def test_complete_data_no_gaps(scorer):
    data = {cat: True for cat in _ALL_CATEGORIES}
    result = scorer.score("F10", data)
    assert result.gaps == []


def test_partial_score_below_threshold_in_gaps(scorer):
    data = {"inspection_records": 0.3}  # below 0.5 threshold
    result = scorer.score("F11", data)
    assert "inspection_records" in result.gaps


def test_partial_score_above_threshold_not_in_gaps(scorer):
    data = {"inspection_records": 0.8}
    result = scorer.score("F12", data)
    assert "inspection_records" not in result.gaps


# ---------------------------------------------------------------------------
# Risk level consistency
# ---------------------------------------------------------------------------


def test_high_score_is_low_risk(scorer):
    data = {cat: True for cat in _ALL_CATEGORIES}
    result = scorer.score("F13", data)
    assert result.risk_level == "low"


def test_zero_score_is_high_risk(scorer):
    result = scorer.score("F14", {})
    assert result.risk_level == "high"


def test_medium_score_is_medium_risk(scorer):
    # Overall score around 0.5 → medium
    data = {
        "as_built_drawings": True,
        "inspection_records": True,
        "well_records": False,
        "mooring_documents": False,
        "environmental_surveys": False,
    }
    result = scorer.score("F15", data)
    # 0.30 + 0.25 = 0.55 → medium (0.40 <= score < 0.70)
    assert result.risk_level in ("low", "medium")


def test_risk_level_valid_values(scorer):
    valid = {"low", "medium", "high"}
    for data in [
        {},
        {cat: True for cat in _ALL_CATEGORIES},
        {"as_built_drawings": 0.5},
    ]:
        result = scorer.score("Fx", data)
        assert result.risk_level in valid


# ---------------------------------------------------------------------------
# portfolio_scores()
# ---------------------------------------------------------------------------


def test_portfolio_scores_returns_dataframe(scorer):
    fields = [
        {"field_name": "A", "available_data": {cat: True for cat in _ALL_CATEGORIES}},
        {"field_name": "B", "available_data": {}},
    ]
    df = scorer.portfolio_scores(fields)
    assert isinstance(df, pd.DataFrame)


def test_portfolio_scores_row_count(scorer):
    fields = [
        {"field_name": "A", "available_data": {"as_built_drawings": True}},
        {"field_name": "B", "available_data": {"inspection_records": True}},
        {"field_name": "C", "available_data": {}},
    ]
    df = scorer.portfolio_scores(fields)
    assert len(df) == 3


def test_portfolio_scores_has_required_columns(scorer):
    fields = [{"field_name": "A", "available_data": {}}]
    df = scorer.portfolio_scores(fields)
    for col in ("field_name", "overall_score", "risk_level", "top_gap"):
        assert col in df.columns


def test_portfolio_scores_overall_in_range(scorer):
    fields = [
        {"field_name": "A", "available_data": {cat: True for cat in _ALL_CATEGORIES}},
        {"field_name": "B", "available_data": {}},
    ]
    df = scorer.portfolio_scores(fields)
    assert (df["overall_score"] >= 0.0).all()
    assert (df["overall_score"] <= 1.0).all()


def test_portfolio_scores_empty_input(scorer):
    df = scorer.portfolio_scores([])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
