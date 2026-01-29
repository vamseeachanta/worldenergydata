"""
Unit tests for SME data loader module
Tests the integration with HierarchicalDataLoader from comprehensive reports
"""

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd

from worldenergydata.modules.bsee.analysis.financial.data_loader import (
    SMEDataLoader,
    normalize_lease_number,
    pick_column,
    std_columns,
)


class TestSMEDataLoader(unittest.TestCase):
    """Test suite for SME data loader functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_data_path = Path("data/modules/bsee")
        self.loader = SMEDataLoader(data_path=self.test_data_path)

        # Create sample data
        self.sample_leases_df = pd.DataFrame(
            {
                "LEASE_NUM": ["G12345", "G23456", "34567"],
                "LEASE_NAME": ["Test Lease 1", "Test Lease 2", "Test Lease 3"],
                "DEV_NAME": ["DEV_A", "DEV_A", "DEV_B"],
                "DEV_TYPE_EFF": ["subsea", "subsea", "dry tree"],
            }
        )

        self.sample_production_df = pd.DataFrame(
            {
                "YearMonth": pd.date_range("2023-01-01", periods=12, freq="MS"),
                "WELL_1": np.random.rand(12) * 1000,
                "WELL_2": np.random.rand(12) * 1000,
            }
        )

        self.sample_drilling_df = pd.DataFrame(
            {
                "WELL_NAME": ["WELL_1", "WELL_2", "WELL_3"],
                "DRILL_DAYS": [30, 45, 60],
                "COMP_DAYS": [15, 20, 25],
                "WELL_SPUD_DATE": pd.to_datetime(
                    ["2023-01-01", "2023-02-01", "2023-03-01"]
                ),
                "TOTAL_DEPTH_DATE": pd.to_datetime(
                    ["2023-01-31", "2023-03-17", "2023-05-01"]
                ),
            }
        )

    def test_initialization(self):
        """Test SMEDataLoader initialization"""
        self.assertIsNotNone(self.loader.hierarchical_loader)
        self.assertEqual(self.loader.data_path, self.test_data_path)
        self.assertIsInstance(self.loader._cache, dict)

    def test_normalize_lease_number(self):
        """Test lease number normalization"""
        self.assertEqual(normalize_lease_number("12345"), "G12345")
        self.assertEqual(normalize_lease_number("G12345"), "G12345")
        self.assertEqual(normalize_lease_number(" g12345 "), "G12345")
        self.assertEqual(
            normalize_lease_number("G-12345"), "G-12345"
        )  # Invalid format preserved

    def test_std_columns(self):
        """Test column standardization"""
        df = pd.DataFrame({" Col 1 ": [1, 2], "Col 2  ": [3, 4]})
        result = std_columns(df)
        self.assertEqual(list(result.columns), ["Col 1", "Col 2"])

        # Test with None/empty
        self.assertIsNone(std_columns(None))
        empty_df = pd.DataFrame()
        self.assertTrue(std_columns(empty_df).empty)

    def test_pick_column(self):
        """Test column selection with multiple candidates"""
        df = pd.DataFrame({"WELL_NAME": [], "API": [], "OTHER": []})

        # Test finding column
        self.assertEqual(pick_column(df, ["WELL", "WELL_NAME"]), "WELL_NAME")
        self.assertEqual(pick_column(df, ["api", "API_NUM"]), "API")

        # Test not finding column
        self.assertIsNone(pick_column(df, ["MISSING", "NOTFOUND"]))

        # Test required flag
        with self.assertRaises(KeyError):
            pick_column(df, ["MISSING"], required=True)

    @patch(
        "src.worldenergydata.modules.bsee.analysis.financial.data_loader.HierarchicalDataLoader"
    )
    def test_load_leases_data(self, mock_hierarchical):
        """Test loading lease data using HierarchicalDataLoader"""
        # Mock the HierarchicalDataLoader
        mock_instance = MagicMock()
        mock_hierarchical.return_value = mock_instance
        mock_instance.load_leases.return_value = self.sample_leases_df

        loader = SMEDataLoader(self.test_data_path)
        leases = loader.load_leases_data()

        # Verify the call
        mock_instance.load_leases.assert_called_once()

        # Check normalization was applied
        self.assertTrue(
            all(l.startswith("G") for l in leases["LEASE_NUM"] if pd.notna(l))
        )

    @patch(
        "src.worldenergydata.modules.bsee.analysis.financial.data_loader.HierarchicalDataLoader"
    )
    def test_load_production_data(self, mock_hierarchical):
        """Test loading production data"""
        mock_instance = MagicMock()
        mock_hierarchical.return_value = mock_instance
        mock_instance.load_production.return_value = self.sample_production_df

        loader = SMEDataLoader(self.test_data_path)
        production = loader.load_production_data("DEV_A")

        # Should have YearMonth index
        self.assertIn("YearMonth", production.columns)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(production["YearMonth"]))

    def test_filter_by_development(self):
        """Test filtering data by development name"""
        result = self.loader.filter_by_development(
            self.sample_drilling_df, "DEV_A", self.sample_leases_df
        )

        # Add development column if not present
        if "DEV_NAME" not in result.columns:
            # This would be added by the merge logic
            self.assertEqual(len(result), len(self.sample_drilling_df))

    def test_matrix_to_timeseries_conversion(self):
        """Test converting matrix format to timeseries"""
        matrix_df = pd.DataFrame(
            {
                "WELL_NAME": ["WELL_1", "WELL_2"],
                "2023-01": [100, 200],
                "2023-02": [150, 250],
                "2023-03": [120, 220],
            }
        )

        result = self.loader._matrix_to_timeseries(matrix_df)

        # Check structure
        self.assertIn("YearMonth", result.columns)
        self.assertIn("WELL_NAME", result.columns)
        self.assertIn("OIL_BBL", result.columns)

        # Check data integrity
        self.assertEqual(len(result), 6)  # 2 wells * 3 months

    def test_load_drilling_completion_data(self):
        """Test loading drilling and completion data"""
        with patch.object(self.loader, "_load_excel_file") as mock_excel:
            mock_excel.return_value = pd.ExcelFile(None)

            with patch("pandas.ExcelFile") as mock_file:
                mock_file.return_value.sheet_names = ["Sheet1"]
                mock_file.return_value.parse.return_value = self.sample_drilling_df

                monthly, totals = self.loader.load_drilling_completion_data("test.xlsx")

                # Should return two dataframes
                self.assertIsInstance(monthly, pd.DataFrame)
                self.assertIsInstance(totals, pd.DataFrame)

    def test_build_development_day_maps(self):
        """Test building drilling/completion day maps for a development"""
        drill_map, comp_map, wells = self.loader.build_development_day_maps(
            "DEV_A",
            self.sample_leases_df,
            self.sample_production_df,
            self.sample_drilling_df,
        )

        # Check return types
        self.assertIsInstance(drill_map, dict)
        self.assertIsInstance(comp_map, dict)
        self.assertIsInstance(wells, set)

    def test_caching_mechanism(self):
        """Test data caching for performance"""
        # First load
        with patch.object(self.loader, "_load_from_source") as mock_load:
            mock_load.return_value = self.sample_production_df
            data1 = self.loader.get_cached_data("test_key", lambda: mock_load())

            # Second load should use cache
            data2 = self.loader.get_cached_data("test_key", lambda: mock_load())

            # Should only call once
            mock_load.assert_called_once()

            # Data should be identical
            pd.testing.assert_frame_equal(data1, data2)

    def test_integration_with_comprehensive_loader(self):
        """Test integration with comprehensive report's HierarchicalDataLoader"""
        with patch(
            "src.worldenergydata.modules.bsee.reports.comprehensive.data_loader_enhanced.HierarchicalDataLoader"
        ) as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Test methods that should delegate to HierarchicalDataLoader
            loader = SMEDataLoader(self.test_data_path)

            # These should use the comprehensive loader
            loader.load_block_data("test_block")
            mock_instance.load_block.assert_called_with("test_block")

            loader.load_field_data("test_field")
            mock_instance.load_field.assert_called_with("test_field")


class TestDataValidation(unittest.TestCase):
    """Test data validation functionality"""

    def test_validate_required_columns(self):
        """Test validation of required columns in dataframes"""
        from worldenergydata.modules.bsee.analysis.financial.data_loader import (
            validate_required_columns,
        )

        df = pd.DataFrame({"A": [1], "B": [2]})

        # Should pass
        validate_required_columns(df, ["A", "B"])

        # Should fail
        with self.assertRaises(ValueError):
            validate_required_columns(df, ["A", "B", "C"])

    def test_validate_date_columns(self):
        """Test validation of date columns"""
        from worldenergydata.modules.bsee.analysis.financial.data_loader import (
            validate_date_columns,
        )

        df = pd.DataFrame(
            {
                "DATE1": pd.to_datetime(["2023-01-01", "2023-02-01"]),
                "DATE2": ["2023-01-01", "2023-02-01"],
                "NOT_DATE": [1, 2],
            }
        )

        # Convert string dates
        result = validate_date_columns(df, ["DATE1", "DATE2"])
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["DATE2"]))

        # Should handle invalid dates
        df_bad = pd.DataFrame({"BAD_DATE": ["not a date", "also not"]})
        result = validate_date_columns(df_bad, ["BAD_DATE"])
        self.assertTrue(result["BAD_DATE"].isna().all())


if __name__ == "__main__":
    unittest.main()
