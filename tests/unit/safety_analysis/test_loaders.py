"""Tests for safety data loaders."""

import pytest

from worldenergydata.safety_analysis.data.loaders import SafetyDataLoader
from worldenergydata.safety_analysis.exceptions import SafetyDataError


class TestSafetyDataLoader:
    def test_load_csv(self, sample_csv_file):
        loader = SafetyDataLoader()
        df = loader.load(sample_csv_file)
        assert len(df) == 5
        assert "rig_id" in df.columns

    def test_load_excel(self, sample_excel_file):
        loader = SafetyDataLoader()
        df = loader.load(sample_excel_file)
        assert len(df) == 5

    def test_load_parquet(self, sample_parquet_file):
        loader = SafetyDataLoader()
        df = loader.load(sample_parquet_file)
        assert len(df) == 5

    def test_load_nonexistent_file(self, tmp_path):
        loader = SafetyDataLoader()
        with pytest.raises(SafetyDataError, match="does not exist"):
            loader.load(tmp_path / "nonexistent.csv")

    def test_load_unsupported_format(self, tmp_path):
        bad_file = tmp_path / "data.json"
        bad_file.write_text("{}")
        loader = SafetyDataLoader()
        with pytest.raises(SafetyDataError, match="Unsupported file type"):
            loader.load(bad_file)

    def test_load_multiple(self, sample_csv_file, tmp_path):
        # Create a second CSV
        import pandas as pd

        df2 = pd.DataFrame(
            {
                "rig_id": ["RIG-003"],
                "date": ["2024-02-01"],
                "description": ["Test"],
                "obs_type": ["safe"],
                "action": ["None"],
            }
        )
        path2 = tmp_path / "extra.csv"
        df2.to_csv(path2, index=False)

        loader = SafetyDataLoader()
        combined = loader.load_multiple([sample_csv_file, path2])
        assert len(combined) == 6

    def test_load_multiple_empty_list(self):
        loader = SafetyDataLoader()
        with pytest.raises(SafetyDataError, match="No files"):
            loader.load_multiple([])
