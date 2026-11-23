"""Tests for lower tertiary production classifier."""

import pandas as pd
import pytest

from worldenergydata.lower_tertiary.production_classifier import (
    ProductionClass,
    classify_production,
    summarize_classification,
)


def _make_df(**overrides):
    """Create a minimal production DataFrame for testing."""
    defaults = {
        "oil_bbl": [100],
        "PRODUCT_CODE": ["O"],
        "WELL_STAT_CD": ["2"],
        "date": [pd.Timestamp("2024-06-01")],
        "development": ["Dev1"],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


class TestProductionClass:
    def test_constants(self):
        assert ProductionClass.WELL_TEST == "well_test"
        assert ProductionClass.COMMERCIAL == "commercial"
        assert ProductionClass.NON_PRODUCING == "non_producing"


class TestClassifyProductionDefaults:
    def test_positive_oil_is_commercial(self):
        df = _make_df(oil_bbl=[500])
        result = classify_production(df)
        assert result["production_class"].iloc[0] == ProductionClass.COMMERCIAL

    def test_zero_oil_is_non_producing(self):
        df = _make_df(oil_bbl=[0])
        result = classify_production(df)
        assert result["production_class"].iloc[0] == ProductionClass.NON_PRODUCING


class TestClassifyProductionRule1:
    def test_product_code_t_is_well_test(self):
        df = _make_df(PRODUCT_CODE=["T"], oil_bbl=[100])
        result = classify_production(df)
        assert result["production_class"].iloc[0] == ProductionClass.WELL_TEST

    def test_product_code_t_lowercase(self):
        df = _make_df(PRODUCT_CODE=["t"], oil_bbl=[100])
        result = classify_production(df)
        assert result["production_class"].iloc[0] == ProductionClass.WELL_TEST

    def test_product_code_t_with_quotes(self):
        df = _make_df(PRODUCT_CODE=['"T"'], oil_bbl=[100])
        result = classify_production(df)
        assert result["production_class"].iloc[0] == ProductionClass.WELL_TEST


class TestClassifyProductionRule2:
    def test_exploratory_with_oil_is_well_test(self):
        df = _make_df(WELL_STAT_CD=["1"], oil_bbl=[500])
        result = classify_production(df)
        assert result["production_class"].iloc[0] == ProductionClass.WELL_TEST

    def test_exploratory_zero_oil_is_non_producing(self):
        df = _make_df(WELL_STAT_CD=["1"], oil_bbl=[0])
        result = classify_production(df)
        assert result["production_class"].iloc[0] == ProductionClass.NON_PRODUCING


class TestClassifyProductionRule3:
    def test_before_first_oil_is_well_test(self):
        first_oil = {"Dev1": pd.Timestamp("2024-07-01")}
        df = _make_df(
            date=[pd.Timestamp("2024-06-01")],
            oil_bbl=[100],
            development=["Dev1"],
        )
        result = classify_production(df, first_oil_map=first_oil)
        assert result["production_class"].iloc[0] == ProductionClass.WELL_TEST

    def test_after_first_oil_is_commercial(self):
        first_oil = {"Dev1": pd.Timestamp("2024-01-01")}
        df = _make_df(
            date=[pd.Timestamp("2024-06-01")],
            oil_bbl=[100],
            development=["Dev1"],
        )
        result = classify_production(df, first_oil_map=first_oil)
        assert result["production_class"].iloc[0] == ProductionClass.COMMERCIAL


class TestClassifyProductionCleanup:
    def test_working_columns_removed(self):
        df = _make_df()
        result = classify_production(df)
        assert "_pc" not in result.columns
        assert "_ws" not in result.columns

    def test_original_not_modified(self):
        df = _make_df()
        original_cols = list(df.columns)
        classify_production(df)
        assert list(df.columns) == original_cols


class TestSummarizeClassification:
    def test_single_development(self):
        df = pd.DataFrame(
            {
                "oil_bbl": [100, 200, 0],
                "production_class": [
                    ProductionClass.COMMERCIAL,
                    ProductionClass.WELL_TEST,
                    ProductionClass.NON_PRODUCING,
                ],
                "development": ["Dev1", "Dev1", "Dev1"],
            }
        )
        summary = summarize_classification(df)
        assert "Dev1" in summary
        assert summary["Dev1"]["commercial_oil_bbl"] == 100.0
        assert summary["Dev1"]["well_test_oil_bbl"] == 200.0
        assert summary["Dev1"]["commercial_count"] == 1
        assert summary["Dev1"]["well_test_count"] == 1
        assert summary["Dev1"]["non_producing_count"] == 1

    def test_multiple_developments(self):
        df = pd.DataFrame(
            {
                "oil_bbl": [100, 200],
                "production_class": [
                    ProductionClass.COMMERCIAL,
                    ProductionClass.COMMERCIAL,
                ],
                "development": ["Dev1", "Dev2"],
            }
        )
        summary = summarize_classification(df)
        assert "Dev1" in summary
        assert "Dev2" in summary
        assert summary["Dev1"]["commercial_oil_bbl"] == 100.0
        assert summary["Dev2"]["commercial_oil_bbl"] == 200.0
