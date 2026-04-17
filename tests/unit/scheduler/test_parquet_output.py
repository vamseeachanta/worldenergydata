"""Tests for the shared Parquet output utility."""

import pandas as pd
import pyarrow.parquet as pq
import pytest


@pytest.fixture
def sample_df():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "feed": ["petroleum_weekly", "gas_storage_weekly"],
            "period": ["2024-01-01", "2024-01-08"],
            "value": [100.5, 200.3],
        }
    )


class TestWriteParquet:
    """Tests for write_parquet function."""

    def test_creates_parquet_file(self, tmp_path, sample_df):
        """write_parquet creates a .parquet file at the specified path."""
        from worldenergydata.scheduler.parquet_output import write_parquet

        result = write_parquet(sample_df, tmp_path, "test_output.parquet")

        assert result.exists()
        assert result.suffix == ".parquet"
        assert result == tmp_path / "test_output.parquet"

    def test_roundtrip_preserves_data(self, tmp_path, sample_df):
        """write_parquet output is readable by pd.read_parquet with same columns/rows."""
        from worldenergydata.scheduler.parquet_output import write_parquet

        output_path = write_parquet(sample_df, tmp_path, "roundtrip.parquet")
        loaded = pd.read_parquet(output_path)

        pd.testing.assert_frame_equal(loaded, sample_df)

    def test_creates_parent_directories(self, tmp_path, sample_df):
        """write_parquet creates parent directories if they don't exist."""
        from worldenergydata.scheduler.parquet_output import write_parquet

        nested_dir = tmp_path / "deep" / "nested" / "dir"
        result = write_parquet(sample_df, nested_dir, "nested.parquet")

        assert result.exists()
        assert nested_dir.exists()

    def test_uses_snappy_compression(self, tmp_path, sample_df):
        """write_parquet uses snappy compression (check parquet metadata)."""
        from worldenergydata.scheduler.parquet_output import write_parquet

        output_path = write_parquet(sample_df, tmp_path, "compressed.parquet")

        pf = pq.ParquetFile(str(output_path))
        row_group = pf.metadata.row_group(0)
        for i in range(row_group.num_columns):
            col = row_group.column(i)
            assert (
                col.compression == "SNAPPY"
            ), f"Column {i} uses {col.compression}, expected SNAPPY"
