"""
Test Binary File Format Compatibility

This test suite ensures the enhanced system produces binary files
that are 100% compatible with the legacy system format.
"""

import hashlib
import io
import pickle
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from worldenergydata.modules.bsee.data.processors import MemoryProcessor
from worldenergydata.modules.bsee.data.refresh.data_refresh_enhanced import (
    DataRefreshEnhanced,
)


class TestBinaryCompatibility(unittest.TestCase):
    """Test suite for binary file format compatibility."""

    def setUp(self):
        """Set up test fixtures."""
        self.memory_processor = MemoryProcessor()
        self.enhanced_refresh = DataRefreshEnhanced()

        # Create sample DataFrames for testing
        self.sample_df = pd.DataFrame(
            {
                "API_WELL_NUMBER": ["123456", "789012", "345678"],
                "WELL_NAME": ["Test Well 1", "Test Well 2", "Test Well 3"],
                "WATER_DEPTH": [1000, 1500, 2000],
                "PRODUCTION_DATE": pd.to_datetime(
                    ["2024-01-01", "2024-01-02", "2024-01-03"]
                ),
                "OIL_VOL": [100.5, 200.7, 300.9],
                "GAS_VOL": [1000.1, 2000.2, 3000.3],
            }
        )

        self.test_config = {
            "parameters": {
                "filepath": {
                    "bin_dir": "test_data/bin",
                    "apm": {"bin": "test_data/bin/apd"},
                    "war": {"bin": "test_data/bin/war"},
                    "production": {"bin": "test_data/bin/production_raw"},
                }
            }
        }

    def test_5_1_pickle_serialization_format(self):
        """Task 5.1: Test pickle serialization format preservation."""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Prepare test data
            test_data = {
                "test_file.csv": {
                    "data": self.sample_df,
                    "shape": self.sample_df.shape,
                    "columns": self.sample_df.columns.tolist(),
                    "dtypes": self.sample_df.dtypes.to_dict(),
                }
            }

            # Save using enhanced system
            self.memory_processor.save_to_binary(test_data, tmpdir, "test")

            # Load the saved pickle file
            pickle_file = Path(tmpdir) / "test_test_file.pkl"
            self.assertTrue(pickle_file.exists(), "Pickle file should be created")

            with open(pickle_file, "rb") as f:
                loaded_df = pickle.load(f)

            # Verify it's a DataFrame (compatible with legacy expectation)
            self.assertIsInstance(
                loaded_df, pd.DataFrame, "Loaded data should be a DataFrame"
            )

            # Verify data integrity
            pd.testing.assert_frame_equal(loaded_df, self.sample_df)

            # Test pickle protocol compatibility
            # Legacy system uses HIGHEST_PROTOCOL, verify we do too
            with open(pickle_file, "rb") as f:
                # Read pickle header to check protocol
                header = f.read(2)
                # Protocol 4 or 5 are typical for HIGHEST_PROTOCOL in Python 3
                protocol = header[1] if len(header) > 1 else 0
                self.assertGreaterEqual(protocol, 4, "Should use high pickle protocol")

    def test_5_2_maintains_existing_format(self):
        """Task 5.2: Ensure ENHANCED processing maintains existing pickle format."""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a legacy-style pickle file
            legacy_df = self.sample_df.copy()
            legacy_file = Path(tmpdir) / "legacy.pkl"

            # Save in legacy format (just DataFrame, no wrapper)
            with open(legacy_file, "wb") as f:
                pickle.dump(legacy_df, f, protocol=pickle.HIGHEST_PROTOCOL)

            # Now save using enhanced system
            enhanced_data = {
                "enhanced.csv": {
                    "data": self.sample_df.copy(),
                    "shape": self.sample_df.shape,
                    "columns": self.sample_df.columns.tolist(),
                    "dtypes": self.sample_df.dtypes.to_dict(),
                }
            }

            self.memory_processor.save_to_binary(enhanced_data, tmpdir, "enhanced")
            enhanced_file = Path(tmpdir) / "enhanced_enhanced.pkl"

            # Load both files
            with open(legacy_file, "rb") as f:
                legacy_loaded = pickle.load(f)

            with open(enhanced_file, "rb") as f:
                enhanced_loaded = pickle.load(f)

            # Both should be DataFrames
            self.assertIsInstance(legacy_loaded, pd.DataFrame)
            self.assertIsInstance(enhanced_loaded, pd.DataFrame)

            # Data should be identical
            pd.testing.assert_frame_equal(legacy_loaded, enhanced_loaded)

    def test_5_3_binary_output_directory(self):
        """Task 5.3: Test ENHANCED binary output to data/modules/bsee/bin directory."""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up directory structure like production
            bin_dir = Path(tmpdir) / "data" / "modules" / "bsee" / "bin"
            apd_dir = bin_dir / "apd"
            war_dir = bin_dir / "war"
            prod_dir = bin_dir / "production_raw"

            # Test well data output
            well_data = {"well_data.csv": {"data": self.sample_df}}
            self.memory_processor.save_to_binary(well_data, str(apd_dir), "well")

            # Verify file created in correct location
            well_file = apd_dir / "well_well_data.pkl"
            self.assertTrue(
                well_file.exists(), f"Well data file should exist at {well_file}"
            )

            # Test WAR data output
            war_data = {"war_data.csv": {"data": self.sample_df}}
            self.memory_processor.save_to_binary(war_data, str(war_dir), "war")

            war_file = war_dir / "war_war_data.pkl"
            self.assertTrue(
                war_file.exists(), f"WAR data file should exist at {war_file}"
            )

            # Test production data output
            prod_data = {"production_data.csv": {"data": self.sample_df}}
            self.memory_processor.save_to_binary(prod_data, str(prod_dir), "production")

            prod_file = prod_dir / "production_production_data.pkl"
            self.assertTrue(
                prod_file.exists(), f"Production data file should exist at {prod_file}"
            )

    def test_5_4_correct_file_locations(self):
        """Task 5.4: Verify ENHANCED system creates files in correct locations."""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock configuration with test paths
            test_config = {
                "enhanced_mode": True,
                "data": {
                    "refresh": True,
                    "well": True,
                    "war": False,
                    "production": False,
                },
                "parameters": {
                    "filepath": {
                        "apm": {"bin": str(Path(tmpdir) / "apd")},
                        "war": {"bin": str(Path(tmpdir) / "war")},
                        "production": {"bin": str(Path(tmpdir) / "production")},
                    }
                },
            }

            # Mock the web scraper and processor
            with patch.object(
                self.enhanced_refresh.web_scraper, "download_zip_to_memory"
            ) as mock_download:
                with patch.object(
                    self.enhanced_refresh.memory_processor, "process_well_data"
                ) as mock_process:
                    with patch.object(
                        self.enhanced_refresh.memory_processor, "save_to_binary"
                    ) as mock_save:

                        mock_download.return_value = b"fake_zip_data"
                        mock_process.return_value = {
                            "data.csv": {"data": self.sample_df}
                        }

                        # Run refresh
                        self.enhanced_refresh.refresh_well_data_enhanced(test_config)

                        # Verify save_to_binary was called with correct path
                        mock_save.assert_called_once()
                        call_args = mock_save.call_args[0]

                        # Check the output directory matches config
                        expected_path = str(Path(tmpdir) / "apd")
                        self.assertEqual(call_args[1], expected_path)

    def test_5_5_downstream_compatibility(self):
        """Task 5.5: Test downstream analysis module compatibility."""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save data using enhanced system
            test_data = {
                "analysis_data.csv": {
                    "data": self.sample_df,
                    "shape": self.sample_df.shape,
                    "columns": self.sample_df.columns.tolist(),
                    "dtypes": self.sample_df.dtypes.to_dict(),
                }
            }

            self.memory_processor.save_to_binary(test_data, tmpdir, "analysis")

            # Simulate downstream module loading the data
            output_file = Path(tmpdir) / "analysis_analysis_data.pkl"

            # Load as a downstream module would
            with open(output_file, "rb") as f:
                downstream_data = pickle.load(f)

            # Verify downstream can work with the data
            self.assertIsInstance(downstream_data, pd.DataFrame)

            # Check that standard pandas operations work
            self.assertEqual(len(downstream_data), 3)
            self.assertIn("API_WELL_NUMBER", downstream_data.columns)

            # Verify numerical operations work
            oil_sum = downstream_data["OIL_VOL"].sum()
            self.assertAlmostEqual(oil_sum, 602.1, places=1)

            # Verify date operations work
            self.assertTrue(
                pd.api.types.is_datetime64_any_dtype(downstream_data["PRODUCTION_DATE"])
            )

    def test_5_6_existing_code_can_read(self):
        """Task 5.6: Test existing analysis code can read ENHANCED binary files."""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save using enhanced system
            enhanced_data = {
                "compatible.csv": {
                    "data": self.sample_df,
                    "shape": self.sample_df.shape,
                    "columns": self.sample_df.columns.tolist(),
                    "dtypes": self.sample_df.dtypes.to_dict(),
                }
            }

            self.memory_processor.save_to_binary(enhanced_data, tmpdir, "test")

            # Simulate legacy code reading pattern
            file_path = Path(tmpdir) / "test_compatible.pkl"

            # Legacy loading pattern (direct pickle load)
            try:
                with open(file_path, "rb") as f:
                    legacy_style_load = pickle.load(f)

                # Should work without any errors
                self.assertIsNotNone(legacy_style_load)
                self.assertIsInstance(legacy_style_load, pd.DataFrame)

            except Exception as e:
                self.fail(f"Legacy code pattern failed to read enhanced file: {e}")

            # Test with pandas read_pickle (another common pattern)
            try:
                pandas_loaded = pd.read_pickle(file_path)
                self.assertIsInstance(pandas_loaded, pd.DataFrame)
                pd.testing.assert_frame_equal(pandas_loaded, self.sample_df)

            except Exception as e:
                self.fail(f"Pandas read_pickle failed on enhanced file: {e}")

    def test_5_7_data_type_preservation(self):
        """Task 5.7: Test data type preservation in ENHANCED system."""

        # Create DataFrame with various data types
        complex_df = pd.DataFrame(
            {
                "int_col": pd.array([1, 2, 3], dtype="int64"),
                "float_col": pd.array([1.1, 2.2, 3.3], dtype="float64"),
                "str_col": pd.array(["a", "b", "c"], dtype="object"),
                "date_col": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                "bool_col": pd.array([True, False, True], dtype="bool"),
                "nullable_int": pd.array([1, None, 3], dtype="Int64"),
                "category_col": pd.Categorical(["cat1", "cat2", "cat1"]),
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save using enhanced system
            test_data = {
                "complex_types.csv": {
                    "data": complex_df,
                    "shape": complex_df.shape,
                    "columns": complex_df.columns.tolist(),
                    "dtypes": complex_df.dtypes.to_dict(),
                }
            }

            self.memory_processor.save_to_binary(test_data, tmpdir, "types")

            # Load and verify
            file_path = Path(tmpdir) / "types_complex_types.pkl"
            with open(file_path, "rb") as f:
                loaded_df = pickle.load(f)

            # Check each data type is preserved
            self.assertEqual(loaded_df["int_col"].dtype, np.int64)
            self.assertEqual(loaded_df["float_col"].dtype, np.float64)
            self.assertEqual(loaded_df["str_col"].dtype, object)
            self.assertTrue(pd.api.types.is_datetime64_any_dtype(loaded_df["date_col"]))
            self.assertEqual(loaded_df["bool_col"].dtype, bool)
            self.assertEqual(loaded_df["nullable_int"].dtype, pd.Int64Dtype())
            self.assertIsInstance(loaded_df["category_col"].dtype, pd.CategoricalDtype)

            # Verify data values are preserved
            self.assertEqual(loaded_df["int_col"].tolist(), [1, 2, 3])
            self.assertTrue(pd.isna(loaded_df["nullable_int"].iloc[1]))
            self.assertEqual(
                loaded_df["category_col"].tolist(), ["cat1", "cat2", "cat1"]
            )

    def test_5_8_data_integrity_pipeline(self):
        """Task 5.8: Ensure data integrity throughout ENHANCED processing pipeline."""

        # Create test zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            # Add CSV with known data
            csv_content = "API_WELL_NUMBER,WELL_NAME,OIL_VOL\n"
            csv_content += "12345,Test Well,100.5\n"
            csv_content += "67890,Test Well 2,200.7\n"
            zf.writestr("test_data.csv", csv_content)

        zip_data = zip_buffer.getvalue()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Process through the full pipeline
            # Step 1: Process zip in memory
            extracted_data = self.memory_processor.process_zip_in_memory(zip_data)
            self.assertIn("test_data.csv", extracted_data)

            # Step 2: Process well data
            processed = self.memory_processor.process_well_data(
                zip_data, {"parameters": {"filepath": {"apm": {"columns": [[]]}}}}
            )

            # Step 3: Save to binary
            self.memory_processor.save_to_binary(processed, tmpdir, "integrity")

            # Step 4: Verify saved data
            saved_files = list(Path(tmpdir).glob("*.pkl"))
            self.assertGreater(len(saved_files), 0, "Should have saved pickle files")

            # Load and verify data integrity
            for pkl_file in saved_files:
                if "metadata" not in pkl_file.name:
                    with open(pkl_file, "rb") as f:
                        loaded = pickle.load(f)

                    if isinstance(loaded, pd.DataFrame):
                        # Verify data matches original
                        self.assertEqual(len(loaded), 2)
                        if "API_WELL_NUMBER" in loaded.columns:
                            self.assertIn("12345", loaded["API_WELL_NUMBER"].values)
                            self.assertIn("67890", loaded["API_WELL_NUMBER"].values)
                        if "OIL_VOL" in loaded.columns:
                            self.assertAlmostEqual(
                                loaded["OIL_VOL"].sum(), 301.2, places=1
                            )

    def test_5_9_all_compatibility_tests_pass(self):
        """Task 5.9: Verify all ENHANCED binary file compatibility tests pass."""

        # This is a summary test that verifies key compatibility points
        compatibility_checks = []

        with tempfile.TemporaryDirectory() as tmpdir:
            # Check 1: Can save DataFrame
            try:
                test_data = {"test.csv": {"data": self.sample_df}}
                self.memory_processor.save_to_binary(test_data, tmpdir, "compat")
                compatibility_checks.append(("Save DataFrame", True))
            except Exception as e:
                compatibility_checks.append(("Save DataFrame", False, str(e)))

            # Check 2: File exists with correct extension
            pkl_files = list(Path(tmpdir).glob("*.pkl"))
            compatibility_checks.append(("Pickle files created", len(pkl_files) > 0))

            # Check 3: Can load with pickle
            if pkl_files:
                try:
                    with open(pkl_files[0], "rb") as f:
                        loaded = pickle.load(f)
                    compatibility_checks.append(("Pickle load", True))

                    # Check 4: Loaded data is DataFrame
                    is_df = isinstance(loaded, pd.DataFrame)
                    compatibility_checks.append(("Is DataFrame", is_df))

                    # Check 5: Can perform pandas operations
                    if is_df:
                        can_operate = hasattr(loaded, "columns") and hasattr(
                            loaded, "shape"
                        )
                        compatibility_checks.append(("Pandas operations", can_operate))

                except Exception as e:
                    compatibility_checks.append(("Pickle load", False, str(e)))

            # Check 6: Metadata file created
            metadata_files = [f for f in pkl_files if "metadata" in f.name]
            compatibility_checks.append(("Metadata file", len(metadata_files) > 0))

            # Verify all checks passed
            failed_checks = [c for c in compatibility_checks if not c[1]]
            if failed_checks:
                fail_msg = "Compatibility checks failed:\n"
                for check in failed_checks:
                    fail_msg += (
                        f"  - {check[0]}: {check[2] if len(check) > 2 else 'Failed'}\n"
                    )
                self.fail(fail_msg)

            # All checks should pass
            self.assertTrue(
                all(c[1] for c in compatibility_checks),
                "All compatibility checks should pass",
            )


class TestCrossSystemCompatibility(unittest.TestCase):
    """Test compatibility between legacy and enhanced systems."""

    def test_enhanced_matches_legacy_format(self):
        """Verify enhanced system output matches legacy format exactly."""

        # Create sample data
        df = pd.DataFrame({"COL1": [1, 2, 3], "COL2": ["a", "b", "c"]})

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save using legacy pattern (direct pickle dump)
            legacy_file = Path(tmpdir) / "legacy.pkl"
            with open(legacy_file, "wb") as f:
                pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)

            # Save using enhanced system
            processor = MemoryProcessor()
            enhanced_data = {"data.csv": {"data": df}}
            processor.save_to_binary(enhanced_data, tmpdir, "enhanced")

            enhanced_file = Path(tmpdir) / "enhanced_data.pkl"

            # Load both files
            with open(legacy_file, "rb") as f:
                legacy_loaded = pickle.load(f)

            with open(enhanced_file, "rb") as f:
                enhanced_loaded = pickle.load(f)

            # Should be identical DataFrames
            pd.testing.assert_frame_equal(legacy_loaded, enhanced_loaded)

            # Check file sizes are similar (within reason for metadata differences)
            legacy_size = legacy_file.stat().st_size
            enhanced_size = enhanced_file.stat().st_size
            size_ratio = enhanced_size / legacy_size

            # Should be roughly the same size (within 20% difference)
            self.assertGreater(
                size_ratio, 0.8, "Enhanced file too small compared to legacy"
            )
            self.assertLess(
                size_ratio, 1.2, "Enhanced file too large compared to legacy"
            )


if __name__ == "__main__":
    unittest.main()
