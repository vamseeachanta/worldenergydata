"""Tests for BSEE financial analysis validators."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.analysis.financial.validators import (
    DataValidator,
    validate_date_columns,
    validate_drilling_data,
    validate_financial_assumptions,
    validate_numeric_columns,
    validate_production_data,
    validate_required_columns,
)


class TestValidateRequiredColumns:
    def test_all_present(self):
        df = pd.DataFrame({"A": [1], "B": [2], "C": [3]})
        assert validate_required_columns(df, ["A", "B"]) is True

    def test_missing_column(self):
        df = pd.DataFrame({"A": [1], "B": [2]})
        with pytest.raises(ValueError, match="Missing required columns"):
            validate_required_columns(df, ["A", "C"])

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        with pytest.raises(ValueError, match="DataFrame is empty"):
            validate_required_columns(df, ["A"])


class TestValidateFinancialAssumptions:
    def test_valid(self):
        assumptions = {
            "NPV_Discount_Rate": 0.10,
            "Drilling_Cost_Per_Day_USD": 500000,
            "Completion_Cost_Per_Day_USD": 200000,
            "Oil_Price_Per_Barrel": 75.0,
            "OPEX_Per_Barrel": 15.0,
            "Tax_Rate": 0.30,
        }
        is_valid, errors = validate_financial_assumptions(assumptions)
        assert is_valid is True
        assert errors == []

    def test_missing_required(self):
        is_valid, errors = validate_financial_assumptions({})
        assert is_valid is False
        assert any("Missing required" in e for e in errors)

    def test_negative_discount_rate(self):
        assumptions = {
            "NPV_Discount_Rate": -0.05,
            "Drilling_Cost_Per_Day_USD": 500000,
            "Completion_Cost_Per_Day_USD": 200000,
            "Oil_Price_Per_Barrel": 75.0,
            "OPEX_Per_Barrel": 15.0,
            "Tax_Rate": 0.30,
        }
        is_valid, errors = validate_financial_assumptions(assumptions)
        assert is_valid is False
        assert any("negative" in e for e in errors)

    def test_discount_rate_too_high(self):
        assumptions = {
            "NPV_Discount_Rate": 1.5,
            "Drilling_Cost_Per_Day_USD": 500000,
            "Completion_Cost_Per_Day_USD": 200000,
            "Oil_Price_Per_Barrel": 75.0,
            "OPEX_Per_Barrel": 15.0,
            "Tax_Rate": 0.30,
        }
        is_valid, errors = validate_financial_assumptions(assumptions)
        assert is_valid is False
        assert any("too high" in e for e in errors)

    def test_negative_tax_rate(self):
        assumptions = {
            "NPV_Discount_Rate": 0.10,
            "Drilling_Cost_Per_Day_USD": 500000,
            "Completion_Cost_Per_Day_USD": 200000,
            "Oil_Price_Per_Barrel": 75.0,
            "OPEX_Per_Barrel": 15.0,
            "Tax_Rate": -0.1,
        }
        is_valid, errors = validate_financial_assumptions(assumptions)
        assert is_valid is False
        assert any("Tax rate" in e and "negative" in e for e in errors)

    def test_tax_rate_over_100(self):
        assumptions = {
            "NPV_Discount_Rate": 0.10,
            "Drilling_Cost_Per_Day_USD": 500000,
            "Completion_Cost_Per_Day_USD": 200000,
            "Oil_Price_Per_Barrel": 75.0,
            "OPEX_Per_Barrel": 15.0,
            "Tax_Rate": 1.5,
        }
        is_valid, errors = validate_financial_assumptions(assumptions)
        assert is_valid is False
        assert any("exceed" in e for e in errors)

    def test_negative_costs(self):
        assumptions = {
            "NPV_Discount_Rate": 0.10,
            "Drilling_Cost_Per_Day_USD": -500000,
            "Completion_Cost_Per_Day_USD": 200000,
            "Oil_Price_Per_Barrel": 75.0,
            "OPEX_Per_Barrel": 15.0,
            "Tax_Rate": 0.30,
        }
        is_valid, errors = validate_financial_assumptions(assumptions)
        assert is_valid is False
        assert any("negative" in e for e in errors)

    def test_zero_oil_price(self):
        assumptions = {
            "NPV_Discount_Rate": 0.10,
            "Drilling_Cost_Per_Day_USD": 500000,
            "Completion_Cost_Per_Day_USD": 200000,
            "Oil_Price_Per_Barrel": 0,
            "OPEX_Per_Barrel": 15.0,
            "Tax_Rate": 0.30,
        }
        is_valid, errors = validate_financial_assumptions(assumptions)
        assert is_valid is False
        assert any("positive" in e for e in errors)


class TestValidateProductionData:
    def test_valid(self):
        df = pd.DataFrame({
            "YearMonth": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "OIL": [1000, 2000],
        })
        is_valid, errors = validate_production_data(df)
        assert is_valid is True
        assert errors == []

    def test_missing_year_month(self):
        df = pd.DataFrame({"OIL": [1000]})
        is_valid, errors = validate_production_data(df)
        assert is_valid is False
        assert any("YearMonth" in e for e in errors)

    def test_negative_production(self):
        df = pd.DataFrame({
            "YearMonth": pd.to_datetime(["2024-01-01"]),
            "OIL": [-100],
        })
        is_valid, errors = validate_production_data(df)
        assert is_valid is False
        assert any("negative" in e for e in errors)


class TestValidateDrillingData:
    def test_valid(self):
        df = pd.DataFrame({"DRILL_DAYS": [30], "COMP_DAYS": [10]})
        is_valid, errors = validate_drilling_data(df)
        assert is_valid is True

    def test_negative_drill_days(self):
        df = pd.DataFrame({"DRILL_DAYS": [-5]})
        is_valid, errors = validate_drilling_data(df)
        assert is_valid is False
        assert any("DRILL_DAYS" in e for e in errors)

    def test_negative_comp_days(self):
        df = pd.DataFrame({"COMP_DAYS": [-3]})
        is_valid, errors = validate_drilling_data(df)
        assert is_valid is False

    def test_td_before_spud(self):
        df = pd.DataFrame({
            "WELL_SPUD_DATE": ["2024-06-01"],
            "TOTAL_DEPTH_DATE": ["2024-01-01"],
        })
        is_valid, errors = validate_drilling_data(df)
        assert is_valid is False
        assert any("total depth date before spud" in e for e in errors)

    def test_valid_dates(self):
        df = pd.DataFrame({
            "WELL_SPUD_DATE": ["2024-01-01"],
            "TOTAL_DEPTH_DATE": ["2024-06-01"],
        })
        is_valid, errors = validate_drilling_data(df)
        assert is_valid is True


class TestDataValidator:
    def test_init(self):
        v = DataValidator()
        report = v.get_validation_report()
        assert report["summary"]["total_validations"] == 0
        assert report["summary"]["passed"] == 0
        assert report["summary"]["failed"] == 0

    def test_validate_financial_valid(self):
        v = DataValidator()
        assumptions = {
            "NPV_Discount_Rate": 0.10,
            "Drilling_Cost_Per_Day_USD": 500000,
            "Completion_Cost_Per_Day_USD": 200000,
            "Oil_Price_Per_Barrel": 75.0,
            "OPEX_Per_Barrel": 15.0,
            "Tax_Rate": 0.30,
        }
        is_valid, errors = v.validate_financial_assumptions(assumptions)
        assert is_valid is True
        report = v.get_validation_report()
        assert report["summary"]["total_validations"] == 1
        assert report["summary"]["passed"] == 1

    def test_validate_financial_invalid(self):
        v = DataValidator()
        is_valid, errors = v.validate_financial_assumptions({})
        assert is_valid is False
        report = v.get_validation_report()
        assert report["summary"]["failed"] == 1

    def test_reset_state(self):
        v = DataValidator()
        v.validate_financial_assumptions({})
        v.reset_validation_state()
        report = v.get_validation_report()
        assert report["summary"]["total_validations"] == 0

    def test_validate_data_types(self):
        v = DataValidator()
        df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
        actual_b_type = str(df["B"].dtype)
        is_valid, mismatches = v.validate_data_types(
            df, {"A": "int64", "B": actual_b_type},
        )
        assert is_valid is True
        assert mismatches == {}

    def test_validate_data_types_mismatch(self):
        v = DataValidator()
        df = pd.DataFrame({"A": [1, 2, 3]})
        is_valid, mismatches = v.validate_data_types(df, {"A": "float64"})
        assert is_valid is False
        assert "A" in mismatches

    def test_validate_ranges(self):
        v = DataValidator()
        df = pd.DataFrame({"A": [5, 10, 15]})
        violations = v.validate_ranges(df, {"A": (0, 20)})
        assert violations == {}

    def test_validate_ranges_below_min(self):
        v = DataValidator()
        df = pd.DataFrame({"A": [-5, 10, 15]})
        violations = v.validate_ranges(df, {"A": (0, 20)})
        assert "A" in violations
        assert 0 in violations["A"]

    def test_validate_ranges_above_max(self):
        v = DataValidator()
        df = pd.DataFrame({"A": [5, 10, 25]})
        violations = v.validate_ranges(df, {"A": (0, 20)})
        assert "A" in violations
        assert 2 in violations["A"]

    def test_generate_report_has_timestamp(self):
        v = DataValidator()
        report = v.generate_validation_report()
        assert "timestamp" in report


class TestValidateDateColumns:
    def test_convert_valid_dates(self):
        df = pd.DataFrame({"dt": ["2024-01-15", "2024-06-30"]})
        result = validate_date_columns(df, ["dt"])
        assert pd.api.types.is_datetime64_any_dtype(result["dt"])

    def test_invalid_dates_become_nat(self):
        df = pd.DataFrame({"dt": ["2024-01-15", "not-a-date"]})
        result = validate_date_columns(df, ["dt"])
        assert result["dt"].isna().sum() == 1

    def test_missing_column_skipped(self):
        df = pd.DataFrame({"other": [1, 2]})
        result = validate_date_columns(df, ["dt"])
        assert "dt" not in result.columns

    def test_original_not_modified(self):
        df = pd.DataFrame({"dt": ["2024-01-15"]})
        original_values = df["dt"].tolist()
        result = validate_date_columns(df, ["dt"])
        # Original df should be unchanged
        assert df["dt"].tolist() == original_values


class TestValidateNumericColumns:
    def test_convert_valid_numbers(self):
        df = pd.DataFrame({"val": ["1.5", "2.0", "3.5"]})
        result = validate_numeric_columns(df, ["val"])
        assert result["val"].dtype in [np.float64, float]

    def test_invalid_numbers_become_nan(self):
        df = pd.DataFrame({"val": ["1.5", "abc", "3.5"]})
        result = validate_numeric_columns(df, ["val"])
        assert result["val"].isna().sum() == 1

    def test_fill_invalid_with_value(self):
        df = pd.DataFrame({"val": ["1.5", "abc", "3.5"]})
        result = validate_numeric_columns(df, ["val"], fill_invalid=0.0)
        assert result["val"].isna().sum() == 0
        assert result["val"].iloc[1] == 0.0

    def test_missing_column_skipped(self):
        df = pd.DataFrame({"other": [1]})
        result = validate_numeric_columns(df, ["val"])
        assert "val" not in result.columns


class TestDataValidatorProduction:
    def test_validate_production_valid(self):
        v = DataValidator()
        df = pd.DataFrame({
            "YearMonth": pd.to_datetime(["2024-01-01"]),
            "OIL": [1000],
        })
        is_valid, errors = v.validate_production_data(df)
        assert is_valid is True
        report = v.get_validation_report()
        assert report["summary"]["passed"] == 1

    def test_validate_production_invalid(self):
        v = DataValidator()
        df = pd.DataFrame({"OIL": [1000]})
        is_valid, errors = v.validate_production_data(df)
        assert is_valid is False
        report = v.get_validation_report()
        assert report["summary"]["failed"] == 1


class TestDataValidatorDrilling:
    def test_validate_drilling_valid(self):
        v = DataValidator()
        df = pd.DataFrame({"DRILL_DAYS": [30]})
        is_valid, errors = v.validate_drilling_data(df)
        assert is_valid is True
        assert v.get_validation_report()["summary"]["passed"] == 1

    def test_validate_drilling_invalid(self):
        v = DataValidator()
        df = pd.DataFrame({"DRILL_DAYS": [-5]})
        is_valid, errors = v.validate_drilling_data(df)
        assert is_valid is False
        assert v.get_validation_report()["summary"]["failed"] == 1


class TestDataValidatorConsistency:
    def test_matching_wells(self):
        v = DataValidator()
        prod_df = pd.DataFrame({
            "YearMonth": pd.to_datetime(["2024-01-01"]),
            "WELL_A": [1000],
        })
        drill_df = pd.DataFrame({"WELL_NAME": ["WELL_A"]})
        warnings = v.check_data_consistency(prod_df, drill_df)
        assert warnings == []

    def test_mismatched_wells(self):
        v = DataValidator()
        prod_df = pd.DataFrame({
            "YearMonth": pd.to_datetime(["2024-01-01"]),
            "WELL_A": [1000],
        })
        drill_df = pd.DataFrame({"WELL_NAME": ["WELL_B"]})
        warnings = v.check_data_consistency(prod_df, drill_df)
        assert len(warnings) > 0

    def test_empty_dataframes(self):
        v = DataValidator()
        warnings = v.check_data_consistency(pd.DataFrame(), pd.DataFrame())
        assert warnings == []


class TestDataValidatorComprehensive:
    def test_all_valid(self):
        v = DataValidator()
        data = {
            "production": pd.DataFrame({
                "YearMonth": pd.to_datetime(["2024-01-01"]),
                "OIL": [1000],
            }),
            "drilling": pd.DataFrame({"DRILL_DAYS": [30]}),
            "assumptions": {
                "NPV_Discount_Rate": 0.10,
                "Drilling_Cost_Per_Day_USD": 500000,
                "Completion_Cost_Per_Day_USD": 200000,
                "Oil_Price_Per_Barrel": 75.0,
                "OPEX_Per_Barrel": 15.0,
                "Tax_Rate": 0.30,
            },
        }
        results = v.run_comprehensive_validation(data)
        assert results["all_valid"] is True
        assert results["production_valid"] is True
        assert results["drilling_valid"] is True
        assert results["assumptions_valid"] is True

    def test_invalid_production(self):
        v = DataValidator()
        data = {
            "production": pd.DataFrame({"OIL": [1000]}),
        }
        results = v.run_comprehensive_validation(data)
        assert results["all_valid"] is False
        assert results["production_valid"] is False

    def test_invalid_assumptions(self):
        v = DataValidator()
        data = {"assumptions": {}}
        results = v.run_comprehensive_validation(data)
        assert results["all_valid"] is False
        assert results["assumptions_valid"] is False

    def test_invalid_leases(self):
        v = DataValidator()
        data = {"leases": pd.DataFrame({"OTHER_COL": ["A"]})}
        results = v.run_comprehensive_validation(data)
        assert results["all_valid"] is False
        assert results["leases_valid"] is False

    def test_valid_leases(self):
        v = DataValidator()
        data = {"leases": pd.DataFrame({"LEASE_NUM": ["G123"], "DEV_NAME": ["Dev1"]})}
        results = v.run_comprehensive_validation(data)
        assert results["leases_valid"] is True

    def test_empty_data(self):
        v = DataValidator()
        results = v.run_comprehensive_validation({})
        assert results["all_valid"] is True
