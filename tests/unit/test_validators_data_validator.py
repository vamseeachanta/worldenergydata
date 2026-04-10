# ABOUTME: Tests for DataValidator in src/validators/data_validator.py
# ABOUTME: Covers validate_dataframe quality scoring, missing data, and report generation

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import yaml

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from validators.data_validator import DataValidator


@pytest.fixture
def validator():
    return DataValidator()


@pytest.fixture
def clean_df():
    return pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["a", "b", "c"],
        "value": [10.0, 20.0, 30.0],
    })


class TestDataValidatorInit:
    def test_init_without_config(self):
        v = DataValidator()
        assert v.config == {}

    def test_init_with_config_file(self, tmp_path):
        cfg = tmp_path / "val.yaml"
        cfg.write_text("validation:\n  numeric_fields: [amount]\n")
        v = DataValidator(config_path=cfg)
        assert v.config["validation"]["numeric_fields"] == ["amount"]

    def test_init_with_missing_config_file_returns_empty(self, tmp_path):
        v = DataValidator(config_path=tmp_path / "nonexistent.yaml")
        assert v.config == {}


class TestValidateDataframe:
    def test_valid_clean_dataframe(self, validator, clean_df):
        result = validator.validate_dataframe(clean_df)
        assert result["valid"] is True
        assert result["total_rows"] == 3
        assert result["total_columns"] == 3
        assert result["quality_score"] == 100.0

    def test_empty_dataframe_is_invalid(self, validator):
        result = validator.validate_dataframe(pd.DataFrame())
        assert result["valid"] is False
        assert result["quality_score"] == 0.0
        assert "empty" in result["issues"][0].lower()

    def test_all_required_fields_present(self, validator, clean_df):
        result = validator.validate_dataframe(clean_df, required_fields=["id", "name"])
        assert result["valid"] is True
        assert not any("Missing required" in i for i in result["issues"])

    def test_missing_required_field_reduces_score(self, validator, clean_df):
        result = validator.validate_dataframe(clean_df, required_fields=["id", "missing_col"])
        assert result["valid"] is False
        assert result["quality_score"] <= 80.0
        assert any("Missing required" in i for i in result["issues"])

    def test_no_duplicates_when_unique_field_clean(self, validator, clean_df):
        result = validator.validate_dataframe(clean_df, unique_field="id")
        assert not any("duplicate" in i for i in result["issues"])

    def test_duplicate_unique_field_adds_issue(self, validator):
        df = pd.DataFrame({"id": [1, 1, 2], "name": ["a", "b", "c"]})
        result = validator.validate_dataframe(df, unique_field="id")
        assert any("duplicate" in i for i in result["issues"])

    def test_high_missing_data_marks_invalid(self, validator):
        df = pd.DataFrame({
            "a": [None, None, None, None, 1.0],  # 80% missing
            "b": [None, None, None, None, 1.0],
        })
        result = validator.validate_dataframe(df)
        assert result["valid"] is False
        assert any("missing" in i.lower() for i in result["issues"])

    def test_moderate_missing_data_reduces_score(self, validator):
        # ~20% missing — between 15% and 30% threshold
        data = {"a": [None, None, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]}
        df = pd.DataFrame(data)
        result = validator.validate_dataframe(df)
        assert any("missing" in i.lower() for i in result["issues"])

    def test_quality_score_never_below_zero(self, validator):
        df = pd.DataFrame({"x": [None] * 10})
        result = validator.validate_dataframe(df)
        assert result["quality_score"] >= 0.0


class TestCheckMissingData:
    def test_no_missing_returns_empty_dict(self, validator, clean_df):
        result = validator._check_missing_data(clean_df)
        assert result == {}

    def test_missing_column_returns_percentage(self, validator):
        df = pd.DataFrame({"a": [1.0, None, None, None, None]})
        result = validator._check_missing_data(df)
        assert "a" in result
        assert result["a"] == pytest.approx(0.8, abs=0.01)

    def test_fully_present_column_not_in_result(self, validator):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [None, None, None]})
        result = validator._check_missing_data(df)
        assert "a" not in result
        assert "b" in result


class TestGetQualityColor:
    def test_score_above_80_is_green(self, validator):
        assert validator._get_quality_color(90) == "green"
        assert validator._get_quality_color(80) == "green"

    def test_score_between_60_and_80_is_yellow(self, validator):
        assert validator._get_quality_color(75) == "yellow"
        assert validator._get_quality_color(60) == "yellow"

    def test_score_below_60_is_red(self, validator):
        assert validator._get_quality_color(59) == "red"
        assert validator._get_quality_color(0) == "red"


class TestGenerateReport:
    def test_valid_result_shows_pass(self, validator, clean_df):
        results = validator.validate_dataframe(clean_df)
        report = validator.generate_report(results)
        assert "PASS" in report
        assert "100.0" in report

    def test_invalid_result_shows_fail(self, validator):
        results = validator.validate_dataframe(pd.DataFrame())
        report = validator.generate_report(results)
        assert "FAIL" in report

    def test_report_includes_row_and_column_counts(self, validator, clean_df):
        results = validator.validate_dataframe(clean_df)
        report = validator.generate_report(results)
        assert "3" in report  # 3 rows and 3 columns

    def test_report_includes_issue_list(self, validator):
        df = pd.DataFrame({"id": [1, 2]})
        results = validator.validate_dataframe(df, required_fields=["missing_col"])
        report = validator.generate_report(results)
        assert "Issues Found" in report
