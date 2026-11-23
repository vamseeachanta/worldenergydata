"""
Test module for API12 drilling completion analysis data loading functions.

This module tests the data loading functionality for comparing drilling and
completion days between lease-based and API12-based methods.
"""

import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


class TestDataLoading:
    """Test class for data loading functionality."""

    @pytest.fixture
    def sample_lease_data(self):
        """Create sample lease method data for testing."""
        return pd.DataFrame(
            {
                "LEASE_NAME": ["Anchor", "Anchor", "Julia"],
                "SURF_LEASE_NUM": [31752, 31752, 20351],
                "WATER_DEPTH": [5080, 5080, 7015],
                "API_WELL_NUMBER": [608114062100, 608114062101, 608124003300],
                "WELL_NAME": ["001", "001", "JU101"],
                "WELL_SPUD_DATE": ["03/14/2014", "05/25/2014", "07/12/2013"],
                "TOTAL_DEPTH_DATE": ["05/17/2014", "06/14/2014", "09/28/2013"],
                "DRILLING_DAYS": [64, 19, 78],
                "COMPLETION_DAYS": [12, 48, 35],
                "MAX_BH_TOTAL_MD": [15356, 25800, 28567],
                "MAX_WELL_BORE_TVD": [15356, 25797, 28400],
                "MAX_DRILL_FLUID_WGT": [12.5, 14.1, 15.2],
            }
        )

    @pytest.fixture
    def sample_api12_data(self):
        """Create sample API12 method data for testing."""
        return pd.DataFrame(
            {
                "API12": [608114062100, 608114062101, 608124003300],
                "API10": [6081140621, 6081140621, 6081240033],
                "TOTAL_DEPTH_DATE": ["2014-05-17", "2014-06-14", "2013-09-28"],
                "WELL_SPUD_DATE": ["2014-03-16", "2014-05-28", "2013-07-10"],
                "COMPLETION_NAME": ["", "", ""],
                "START_PRODUCTION_DATE": ["", "", ""],
                "LAST_PRODUCTION_DATE": ["", "", ""],
                "WELL_NM_ST_SFIX": [0.0, 0.0, 0.0],
                "WELL_NM_BP_SFIX": [0.0, 1.0, 0.0],
                "WELL_LABEL": ["001", "001", "JU101"],
                "WELL_NAME": ["001", "001", "JU101"],
                "WELL_NAME_SUFFIX": ["ST00BP00", "ST00BP01", "ST00BP00"],
                "drilling_days_per_10000_ft": [50.4, 22.4, 36.8],
                "RIG_LAST_DATE_ON_WELL": [
                    "5/31/2014",
                    "8/6/2014 11:59:00 PM",
                    "10/2/2013",
                ],
                "Water Depth (feet)": [5230.0, 5228.0, 7015.0],
                "Total Measured Depth": [15356, 25800, 28567],
                "Drilling Days": [51, 46, 80],
                "Completion Days": [0, 0, 37],
                "rigdays_by_milestone": [
                    '{"drilling_days": 63, "completion_days": 15, "rig_days": 78}',
                    '{"drilling_days": 18, "completion_days": 340, "rig_days": 358}',
                    '{"drilling_days": 81, "completion_days": 36, "rig_days": 117}',
                ],
            }
        )

    @pytest.fixture
    def temp_excel_file(self, sample_lease_data):
        """Create temporary Excel file for testing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
            sample_lease_data.to_excel(tmp_file.name, index=False)
            yield tmp_file.name
        os.unlink(tmp_file.name)

    @pytest.fixture
    def temp_csv_file(self, sample_api12_data):
        """Create temporary CSV file for testing."""
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".csv", mode="w"
        ) as tmp_file:
            sample_api12_data.to_csv(tmp_file.name, index=False)
            yield tmp_file.name
        os.unlink(tmp_file.name)

    def test_load_lease_data_excel(self, temp_excel_file):
        """Test loading lease method data from Excel file."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
            load_lease_data,
        )

        df = load_lease_data(temp_excel_file)

        # Test data loading success
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 3

        # Test expected columns are present
        expected_columns = [
            "LEASE_NAME",
            "API_WELL_NUMBER",
            "DRILLING_DAYS",
            "COMPLETION_DAYS",
        ]
        for col in expected_columns:
            assert col in df.columns

        # Test data types
        assert pd.api.types.is_numeric_dtype(df["API_WELL_NUMBER"])
        assert pd.api.types.is_numeric_dtype(df["DRILLING_DAYS"])
        assert pd.api.types.is_numeric_dtype(df["COMPLETION_DAYS"])

    def test_load_api12_data_csv(self, temp_csv_file):
        """Test loading API12 method data from CSV file."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
            load_api12_data,
        )

        df = load_api12_data(temp_csv_file)

        # Test data loading success
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 3

        # Test expected columns are present
        expected_columns = ["API12", "Drilling Days", "Completion Days"]
        for col in expected_columns:
            assert col in df.columns

        # Test data types
        assert pd.api.types.is_numeric_dtype(df["API12"])
        assert pd.api.types.is_numeric_dtype(df["Drilling Days"])
        assert pd.api.types.is_numeric_dtype(df["Completion Days"])

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file raises appropriate error."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
            load_lease_data,
        )

        with pytest.raises(FileNotFoundError):
            load_lease_data("nonexistent_file.xlsx")

    def test_load_empty_excel_file(self):
        """Test loading empty Excel file."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
            load_lease_data,
        )

        # Create empty DataFrame and save to temp file
        empty_df = pd.DataFrame()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
            empty_df.to_excel(tmp_file.name, index=False)

            df = load_lease_data(tmp_file.name)
            assert df.empty

        os.unlink(tmp_file.name)

    def test_load_malformed_csv_file(self):
        """Test loading malformed CSV file."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
            load_api12_data,
        )

        # Create malformed CSV content
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".csv", mode="w"
        ) as tmp_file:
            tmp_file.write("malformed,csv,content\nwith,inconsistent,columns,extra\n")
            tmp_file.flush()

            # Should not raise error but may have unexpected structure
            df = load_api12_data(tmp_file.name)
            assert isinstance(df, pd.DataFrame)

        os.unlink(tmp_file.name)

    def test_validate_required_columns_lease(self, sample_lease_data):
        """Test validation of required columns in lease data."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
            validate_lease_columns,
        )

        # Test with complete data
        assert validate_lease_columns(sample_lease_data) is True

        # Test with missing required column
        incomplete_data = sample_lease_data.drop(columns=["DRILLING_DAYS"])
        assert validate_lease_columns(incomplete_data) is False

    def test_validate_required_columns_api12(self, sample_api12_data):
        """Test validation of required columns in API12 data."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
            validate_api12_columns,
        )

        # Test with complete data
        assert validate_api12_columns(sample_api12_data) is True

        # Test with missing required column
        incomplete_data = sample_api12_data.drop(columns=["API12"])
        assert validate_api12_columns(incomplete_data) is False

    def test_data_standardization(self, sample_lease_data, sample_api12_data):
        """Test data standardization and column mapping."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
            standardize_data,
        )

        lease_std, api12_std = standardize_data(sample_lease_data, sample_api12_data)

        # Test standardized column names
        assert "api12" in lease_std.columns
        assert "drilling_days" in lease_std.columns
        assert "completion_days" in lease_std.columns

        assert "api12" in api12_std.columns
        assert "drilling_days" in api12_std.columns
        assert "completion_days" in api12_std.columns

        # Test data types are consistent
        assert lease_std["api12"].dtype == api12_std["api12"].dtype
        assert lease_std["drilling_days"].dtype == api12_std["drilling_days"].dtype
        assert lease_std["completion_days"].dtype == api12_std["completion_days"].dtype

    def test_data_type_conversion(self):
        """Test proper data type conversion during loading."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
            convert_data_types,
        )

        # Create DataFrame with mixed types
        df = pd.DataFrame(
            {
                "API12": ["608114062100", "608114062101"],
                "Drilling Days": ["51", "46"],
                "Completion Days": ["0", "0"],
            }
        )

        converted_df = convert_data_types(df)

        assert pd.api.types.is_numeric_dtype(converted_df["API12"])
        assert pd.api.types.is_numeric_dtype(converted_df["Drilling Days"])
        assert pd.api.types.is_numeric_dtype(converted_df["Completion Days"])

    def test_handle_missing_values(self):
        """Test handling of missing values in data."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
            handle_missing_values,
        )

        # Create DataFrame with missing values
        df = pd.DataFrame(
            {
                "API12": [608114062100, np.nan, 608124003300],
                "Drilling Days": [51, 46, np.nan],
                "Completion Days": [0, np.nan, 37],
            }
        )

        cleaned_df = handle_missing_values(df)

        # Test missing value handling strategy
        assert (
            not cleaned_df["API12"].isna().any()
        )  # Should not have missing API12 values
        # Drilling/Completion days might be filled or filtered based on strategy
