"""Tests for decline curve examples with named NCS fields."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.sodir.examples.decline_curve_examples import (
    create_mock_field_production,
    run_edvard_grieg_decline_curve,
    run_valhall_decline_curve,
    run_ivar_aasen_decline_curve,
)


class TestMockFieldProduction:
    """Tests for creating mock production data for fields."""

    def test_create_mock_edvard_grieg_returns_dataframe(self):
        df = create_mock_field_production("EDVARD GRIEG")
        assert isinstance(df, pd.DataFrame)

    def test_create_mock_field_has_required_columns(self):
        df = create_mock_field_production("EDVARD GRIEG")
        required = ["year", "month", "oil_sm3", "gas_sm3"]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_create_mock_field_has_nonzero_production(self):
        df = create_mock_field_production("EDVARD GRIEG")
        assert df["oil_sm3"].sum() > 0

    def test_create_mock_valhall_returns_dataframe(self):
        df = create_mock_field_production("VALHALL")
        assert isinstance(df, pd.DataFrame)

    def test_create_mock_ivar_aasen_returns_dataframe(self):
        df = create_mock_field_production("IVAR AASEN")
        assert isinstance(df, pd.DataFrame)

    def test_create_mock_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            create_mock_field_production("NONEXISTENT FIELD")


class TestEdvardGriegDeclineCurve:
    """Test Edvard Grieg decline curve fitting."""

    def test_returns_dict_with_metrics(self):
        result = run_edvard_grieg_decline_curve()
        assert isinstance(result, dict)

    def test_result_has_field_name(self):
        result = run_edvard_grieg_decline_curve()
        assert result["field_name"] == "EDVARD GRIEG"

    def test_result_has_decline_curve(self):
        result = run_edvard_grieg_decline_curve()
        assert "decline_curve" in result

    def test_result_has_r_squared(self):
        result = run_edvard_grieg_decline_curve()
        assert "r_squared" in result
        assert 0 <= result["r_squared"] <= 1

    def test_result_has_initial_rate(self):
        result = run_edvard_grieg_decline_curve()
        assert "initial_rate" in result
        assert result["initial_rate"] > 0

    def test_result_has_decline_rate(self):
        result = run_edvard_grieg_decline_curve()
        assert "decline_rate" in result
        assert result["decline_rate"] >= 0


class TestValhallDeclineCurve:
    """Test Valhall decline curve fitting."""

    def test_returns_dict(self):
        result = run_valhall_decline_curve()
        assert isinstance(result, dict)

    def test_result_has_field_name(self):
        result = run_valhall_decline_curve()
        assert result["field_name"] == "VALHALL"

    def test_result_has_decline_curve(self):
        result = run_valhall_decline_curve()
        assert "decline_curve" in result


class TestIvarAasenDeclineCurve:
    """Test Ivar Aasen decline curve fitting."""

    def test_returns_dict(self):
        result = run_ivar_aasen_decline_curve()
        assert isinstance(result, dict)

    def test_result_has_field_name(self):
        result = run_ivar_aasen_decline_curve()
        assert result["field_name"] == "IVAR AASEN"

    def test_result_has_decline_curve(self):
        result = run_ivar_aasen_decline_curve()
        assert "decline_curve" in result
