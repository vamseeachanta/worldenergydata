"""
Tests for the Paleowells Data Processor.
"""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.modules.bsee.paleowells.data_processor import (
    PaleowellsDataProcessor,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_paleo_data():
    """Create sample paleo data for testing."""
    data = """P608054000300 1 112660126281AT Upper Oligocene (Chattian) Discoaster woodringii                                              1AT
P608054000300 1 114340140671AT Upper Oligocene (Chattian) Clausicoccus fenestratus                                           1AT
P608054000300 1 114460141691AT Eocene Upper (Bartonian) Zygrhablithus bijugatus                                              1AT
P608054000300 1 114659143401AT Paleocene Lower (Danian) Sphenolithus delphix                                                 1AT
P608054000300 1 114660143411AT Miocene Middle Dictyococcites bisectus increase                                               1AT """
    return data


@pytest.fixture
def processor(temp_dir):
    """Create a PaleowellsDataProcessor instance."""
    return PaleowellsDataProcessor(temp_dir)


class TestPaleowellsDataProcessor:
    """Test suite for PaleowellsDataProcessor."""

    def test_initialization(self, processor, temp_dir):
        """Test processor initialization."""
        assert processor.data_directory == temp_dir
        assert processor.EPOCHS == ["Paleocene", "Eocene", "Oligocene"]
        assert len(processor.COLUMN_NAMES) == 12

    def test_filter_epochs(self, processor, temp_dir, sample_paleo_data):
        """Test epoch filtering functionality."""
        # Create input file
        input_file = temp_dir / "test_input.txt"
        input_file.write_text(sample_paleo_data)

        # Create output file
        output_file = temp_dir / "test_output.txt"

        # Filter for Lower Tertiary epochs
        records = processor.filter_epochs(input_file, output_file)

        assert records == 4  # 2 Oligocene + 1 Eocene + 1 Paleocene records
        assert output_file.exists()

        # Check filtered content
        filtered_content = output_file.read_text()
        assert "Oligocene" in filtered_content
        assert "Eocene" in filtered_content
        assert "Paleocene" in filtered_content
        assert "Miocene" not in filtered_content  # Miocene not in default epochs

    def test_filter_epochs_custom(self, processor, temp_dir, sample_paleo_data):
        """Test filtering with custom epochs."""
        input_file = temp_dir / "test_input.txt"
        input_file.write_text(sample_paleo_data)

        output_file = temp_dir / "test_output.txt"

        # Filter only for Miocene
        records = processor.filter_epochs(input_file, output_file, epochs=["Miocene"])

        assert records == 1
        filtered_content = output_file.read_text()
        assert "Miocene" in filtered_content
        assert "Oligocene" not in filtered_content

    def test_parse_fixed_width_file(self, processor, temp_dir, sample_paleo_data):
        """Test parsing fixed-width format files."""
        # Create test file
        test_file = temp_dir / "test_fixed.txt"
        test_file.write_text(sample_paleo_data)

        # Parse file
        df = processor.parse_fixed_width_file(test_file)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5  # 5 rows in sample data
        assert len(df.columns) == 12  # 12 expected columns
        assert "API Well Number" in df.columns
        assert "Paleo Age" in df.columns
        assert "True Vertical Depth" in df.columns

    def test_parse_fixed_width_file_with_csv_output(
        self, processor, temp_dir, sample_paleo_data
    ):
        """Test parsing with CSV output."""
        test_file = temp_dir / "test_fixed.txt"
        test_file.write_text(sample_paleo_data)

        output_csv = temp_dir / "output.csv"

        df = processor.parse_fixed_width_file(test_file, output_csv)

        assert output_csv.exists()

        # Load CSV and verify
        df_from_csv = pd.read_csv(output_csv)
        assert len(df_from_csv) == len(df)
        assert list(df_from_csv.columns) == list(df.columns)

    def test_analyze_well_epochs(self, processor, temp_dir):
        """Test well epoch analysis."""
        # Create sample DataFrame
        data = {
            "API Well Number": [
                "608054000300",
                "608054000300",
                "608054000301",
                "608054000301",
            ],
            "Paleo Age": [
                "Upper Oligocene (Chattian) Discoaster",
                "Eocene Upper (Bartonian) Zygrhablithus",
                "Paleocene Lower (Danian) Sphenolithus",
                "Miocene Middle Dictyococcites",
            ],
            "Measured Depth": [12660, 14460, 15000, 16000],
            "True Vertical Depth": [12628, 14169, 14800, 15800],
            "Definite/Possible": ["DEF", "DEF", "POS", "DEF"],
        }
        df = pd.DataFrame(data)

        analysis = processor.analyze_well_epochs(df)

        assert "wells_by_epoch" in analysis
        assert "total_unique_wells" in analysis
        assert "depth_statistics" in analysis
        assert "classification_counts" in analysis

        assert analysis["total_unique_wells"] == 2  # Two unique wells
        assert "Oligocene" in analysis["wells_by_epoch"]
        assert "Eocene" in analysis["wells_by_epoch"]

    def test_process_paleowells_data_complete(
        self, processor, temp_dir, sample_paleo_data
    ):
        """Test complete processing pipeline."""
        # Create raw data file
        raw_file = temp_dir / "raw_data.txt"
        raw_file.write_text(sample_paleo_data)

        # Process data
        df = processor.process_paleowells_data(
            raw_data_file=raw_file, output_directory=temp_dir
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # Check output files exist
        assert (temp_dir / "lower_tertiary_wells.txt").exists()
        assert (temp_dir / "paleowells.csv").exists()
        assert (temp_dir / "paleowells_analysis.json").exists()

        # Verify analysis file
        with open(temp_dir / "paleowells_analysis.json") as f:
            analysis = json.load(f)
            assert "wells_by_epoch" in analysis
            assert "total_unique_wells" in analysis

    def test_process_without_raw_file(self, processor, temp_dir):
        """Test processing when raw file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            processor.process_paleowells_data(output_directory=temp_dir)

    def test_epochs_constant(self, processor):
        """Test that epochs are correctly defined."""
        assert processor.EPOCHS == ["Paleocene", "Eocene", "Oligocene"]

    def test_column_names_count(self, processor):
        """Test that column names match fixed widths."""
        assert len(processor.COLUMN_NAMES) == len(processor.FWIDTHS)
