"""Tests for LNG terminal schema, data quality, and loader.

This module tests the terminal data schema, data quality scoring,
and CSV/Parquet loading functionality for Phase 1-2a.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from worldenergydata.lng_terminals.constants import (
    SourceReliability,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from worldenergydata.lng_terminals.loaders.terminal_loader import TerminalLoader
from worldenergydata.lng_terminals.models.data_quality import (
    QualityScore,
    SourceCitation,
)
from worldenergydata.lng_terminals.models.design import (
    MarineInfrastructure,
    StorageSpec,
)
from worldenergydata.lng_terminals.models.terminal import LNGTerminal


@pytest.fixture
def seed_data_path():
    """Path to the seed dataset CSV file."""
    # Path from test file: tests/modules/lng_terminals/test_terminal_schema.py
    # Go up 3 levels to worldenergydata root, then to data/modules/lng_terminals/curated
    worldenergydata_root = Path(__file__).resolve().parents[3]
    return (
        worldenergydata_root
        / "data"
        / "modules"
        / "lng_terminals"
        / "curated"
        / "terminals_seed.csv"
    )


class TestTerminalSchema:
    """Test suite for LNGTerminal schema validation."""

    def test_minimal_valid_terminal(self):
        """Test creating a terminal with only required fields."""
        terminal = LNGTerminal(
            terminal_name="Test Terminal",
            country="USA",
            terminal_type=TerminalType.ONSHORE_EXPORT,
            function=TerminalFunction.EXPORT,
            status=TerminalStatus.OPERATIONAL,
            last_updated=datetime.utcnow(),
        )

        assert terminal.terminal_name == "Test Terminal"
        assert terminal.country == "USA"
        assert terminal.terminal_type == TerminalType.ONSHORE_EXPORT
        assert terminal.function == TerminalFunction.EXPORT
        assert terminal.status == TerminalStatus.OPERATIONAL
        # terminal_id should be auto-generated
        assert terminal.terminal_id == "test-terminal-usa"

    def test_complete_terminal_with_all_fields(self):
        """Test creating a terminal with all fields populated."""
        terminal = LNGTerminal(
            terminal_name="Sabine Pass LNG",
            country="USA",
            latitude=29.7295,
            longitude=-93.8711,
            terminal_type=TerminalType.ONSHORE_EXPORT,
            function=TerminalFunction.EXPORT,
            status=TerminalStatus.OPERATIONAL,
            capacity_mtpa=30.0,
            year_commissioned=2016,
            operator="Cheniere Energy",
            owner="Cheniere Energy",
            capex_usd_million=18000.0,
            marine_infrastructure=MarineInfrastructure(
                water_depth_m=12.0,
                jetty_count=2,
            ),
            storage=StorageSpec(
                tank_type="full_containment",
                total_capacity_m3=950000.0,
            ),
            sources=[
                SourceCitation(
                    source_name="FERC",
                    source_url="https://www.ferc.gov",
                    access_date=date.today(),
                    fields_sourced=["capacity_mtpa", "operator"],
                    reliability=SourceReliability.HIGH,
                )
            ],
            last_updated=datetime.utcnow(),
        )

        assert terminal.terminal_name == "Sabine Pass LNG"
        assert terminal.capacity_mtpa == 30.0
        assert terminal.year_commissioned == 2016
        assert terminal.operator == "Cheniere Energy"
        assert terminal.marine_infrastructure is not None
        assert terminal.marine_infrastructure.water_depth_m == 12.0
        assert terminal.storage is not None
        assert terminal.storage.total_capacity_m3 == 950000.0
        assert len(terminal.sources) == 1

    def test_terminal_id_auto_generation(self):
        """Test that terminal_id is auto-generated from name and country."""
        terminal = LNGTerminal(
            terminal_name="Ras Laffan LNG",
            country="QAT",
            terminal_type=TerminalType.ONSHORE_EXPORT,
            function=TerminalFunction.EXPORT,
            status=TerminalStatus.OPERATIONAL,
            last_updated=datetime.utcnow(),
        )

        assert terminal.terminal_id == "ras-laffan-lng-qat"

    def test_country_code_validation_uppercase(self):
        """Test country code is normalized to uppercase."""
        terminal = LNGTerminal(
            terminal_name="Test",
            country="usa",  # lowercase
            terminal_type=TerminalType.ONSHORE_EXPORT,
            function=TerminalFunction.EXPORT,
            status=TerminalStatus.OPERATIONAL,
            last_updated=datetime.utcnow(),
        )

        assert terminal.country == "USA"

    def test_country_code_validation_invalid_format(self):
        """Test country code validation rejects invalid formats."""
        with pytest.raises(ValidationError, match="Country code must be exactly 3"):
            LNGTerminal(
                terminal_name="Test",
                country="US",  # Only 2 chars
                terminal_type=TerminalType.ONSHORE_EXPORT,
                function=TerminalFunction.EXPORT,
                status=TerminalStatus.OPERATIONAL,
                last_updated=datetime.utcnow(),
            )

    def test_capacity_validation_bounds(self):
        """Test capacity_mtpa has reasonable bounds."""
        # Valid capacity
        terminal = LNGTerminal(
            terminal_name="Test",
            country="USA",
            terminal_type=TerminalType.ONSHORE_EXPORT,
            function=TerminalFunction.EXPORT,
            status=TerminalStatus.OPERATIONAL,
            capacity_mtpa=25.0,
            last_updated=datetime.utcnow(),
        )
        assert terminal.capacity_mtpa == 25.0

        # Capacity too high (> 200 MTPA)
        with pytest.raises(ValidationError):
            LNGTerminal(
                terminal_name="Test",
                country="USA",
                terminal_type=TerminalType.ONSHORE_EXPORT,
                function=TerminalFunction.EXPORT,
                status=TerminalStatus.OPERATIONAL,
                capacity_mtpa=250.0,  # Too high
                last_updated=datetime.utcnow(),
            )

    def test_year_commissioned_validation(self):
        """Test year_commissioned has reasonable bounds."""
        # Valid year
        terminal = LNGTerminal(
            terminal_name="Test",
            country="USA",
            terminal_type=TerminalType.ONSHORE_EXPORT,
            function=TerminalFunction.EXPORT,
            status=TerminalStatus.OPERATIONAL,
            year_commissioned=2020,
            last_updated=datetime.utcnow(),
        )
        assert terminal.year_commissioned == 2020

        # Year too early (< 1960)
        with pytest.raises(ValidationError):
            LNGTerminal(
                terminal_name="Test",
                country="USA",
                terminal_type=TerminalType.ONSHORE_EXPORT,
                function=TerminalFunction.EXPORT,
                status=TerminalStatus.OPERATIONAL,
                year_commissioned=1950,  # Too early
                last_updated=datetime.utcnow(),
            )

    def test_latitude_longitude_validation(self):
        """Test latitude and longitude bounds."""
        # Valid coordinates
        terminal = LNGTerminal(
            terminal_name="Test",
            country="USA",
            terminal_type=TerminalType.ONSHORE_EXPORT,
            function=TerminalFunction.EXPORT,
            status=TerminalStatus.OPERATIONAL,
            latitude=29.73,
            longitude=-93.87,
            last_updated=datetime.utcnow(),
        )
        assert terminal.latitude == 29.73
        assert terminal.longitude == -93.87

        # Invalid latitude (> 90)
        with pytest.raises(ValidationError):
            LNGTerminal(
                terminal_name="Test",
                country="USA",
                terminal_type=TerminalType.ONSHORE_EXPORT,
                function=TerminalFunction.EXPORT,
                status=TerminalStatus.OPERATIONAL,
                latitude=95.0,  # Invalid
                last_updated=datetime.utcnow(),
            )


class TestDataQuality:
    """Test suite for data quality scoring."""

    def test_quality_score_all_required_fields_present(self):
        """Test quality score when all required fields are present."""
        field_presence = {
            "name": True,
            "country": True,
            "type": True,
            "status": True,
            "capacity_mtpa": True,
            "operator": True,
        }

        score = QualityScore.compute(
            field_presence=field_presence,
            required_fields=["name", "country", "type", "status"],
            source_count=2,
        )

        assert score.required_fields_score == 100.0
        assert score.source_count == 2
        assert score.total_score > 0

    def test_quality_score_missing_required_fields(self):
        """Test quality score when required fields are missing."""
        field_presence = {
            "name": True,
            "country": True,
            "type": False,  # Missing
            "status": True,
        }

        score = QualityScore.compute(
            field_presence=field_presence,
            required_fields=["name", "country", "type", "status"],
            source_count=1,
        )

        assert score.required_fields_score == 75.0  # 3/4 = 75%

    def test_quality_score_no_optional_fields(self):
        """Test quality score when only required fields are present."""
        field_presence = {
            "name": True,
            "country": True,
            "type": True,
            "status": True,
        }

        score = QualityScore.compute(
            field_presence=field_presence,
            required_fields=["name", "country", "type", "status"],
            source_count=1,
        )

        # All required present, no optional fields
        assert score.required_fields_score == 100.0
        assert score.optional_fields_score == 100.0  # No optional fields = 100%


class TestTerminalLoader:
    """Test suite for TerminalLoader CSV/Parquet loading."""

    def test_loader_initialization(self, seed_data_path):
        """Test loader can be initialized with seed data path."""
        loader = TerminalLoader(seed_data_path)
        assert loader.file_path == seed_data_path
        assert loader.source_name == "curated_seed_dataset"

    def test_loader_file_not_found(self):
        """Test loader raises error for non-existent file."""
        with pytest.raises(FileNotFoundError, match="Data file not found"):
            TerminalLoader("/nonexistent/path.csv")

    def test_load_seed_dataset(self, seed_data_path):
        """Test loading the actual seed dataset CSV."""
        loader = TerminalLoader(seed_data_path)
        terminals = loader.load()

        # Verify we loaded at least 50 terminals
        assert len(terminals) >= 50, f"Expected >= 50 terminals, got {len(terminals)}"

        # Check that all terminals are valid LNGTerminal instances
        assert all(isinstance(t, LNGTerminal) for t in terminals)

        # Verify all terminals have required fields
        for terminal in terminals:
            assert terminal.terminal_name
            assert terminal.country
            assert terminal.terminal_type
            assert terminal.function
            assert terminal.status
            assert terminal.terminal_id  # Auto-generated

    def test_load_sabine_pass_spot_check(self, seed_data_path):
        """Test spot-check of known terminal: Sabine Pass."""
        loader = TerminalLoader(seed_data_path)
        terminals = loader.load()

        # Find Sabine Pass
        sabine = next((t for t in terminals if "Sabine Pass" in t.terminal_name), None)

        assert sabine is not None, "Sabine Pass LNG not found in dataset"
        assert sabine.country == "USA"
        assert sabine.terminal_type == TerminalType.ONSHORE_EXPORT
        assert sabine.function == TerminalFunction.EXPORT
        assert sabine.status == TerminalStatus.OPERATIONAL
        assert sabine.capacity_mtpa == pytest.approx(30.0, rel=0.1)
        assert sabine.year_commissioned == 2016
        assert sabine.operator == "Cheniere Energy"

    def test_load_ras_laffan_spot_check(self, seed_data_path):
        """Test spot-check of known terminal: Ras Laffan (Qatar)."""
        loader = TerminalLoader(seed_data_path)
        terminals = loader.load()

        # Find Ras Laffan
        ras_laffan = next(
            (t for t in terminals if "Ras Laffan" in t.terminal_name), None
        )

        assert ras_laffan is not None, "Ras Laffan LNG not found in dataset"
        assert ras_laffan.country == "QAT"
        assert ras_laffan.terminal_type == TerminalType.ONSHORE_EXPORT
        assert ras_laffan.capacity_mtpa == pytest.approx(77.0, rel=0.1)
        assert ras_laffan.year_commissioned == 1997

    def test_load_gorgon_spot_check(self, seed_data_path):
        """Test spot-check of known terminal: Gorgon (Australia)."""
        loader = TerminalLoader(seed_data_path)
        terminals = loader.load()

        # Find Gorgon
        gorgon = next((t for t in terminals if "Gorgon" in t.terminal_name), None)

        assert gorgon is not None, "Gorgon LNG not found in dataset"
        assert gorgon.country == "AUS"
        assert gorgon.terminal_type == TerminalType.ONSHORE_EXPORT
        assert gorgon.capacity_mtpa == pytest.approx(15.6, rel=0.1)
        assert gorgon.year_commissioned == 2016
        assert gorgon.operator == "Chevron Australia"

    def test_load_hammerfest_spot_check(self, seed_data_path):
        """Test spot-check of known terminal: Hammerfest (Norway)."""
        loader = TerminalLoader(seed_data_path)
        terminals = loader.load()

        # Find Hammerfest
        hammerfest = next(
            (t for t in terminals if "Hammerfest" in t.terminal_name), None
        )

        assert hammerfest is not None, "Hammerfest not found in dataset"
        assert hammerfest.country == "NOR"
        assert hammerfest.terminal_type == TerminalType.ONSHORE_EXPORT
        assert hammerfest.capacity_mtpa == pytest.approx(4.3, rel=0.1)
        assert hammerfest.year_commissioned == 2007

    def test_load_cove_point_spot_check(self, seed_data_path):
        """Test spot-check of known terminal: Cove Point (US)."""
        loader = TerminalLoader(seed_data_path)
        terminals = loader.load()

        # Find Cove Point
        cove_point = next(
            (t for t in terminals if "Cove Point" in t.terminal_name), None
        )

        assert cove_point is not None, "Cove Point not found in dataset"
        assert cove_point.country == "USA"
        assert cove_point.terminal_type == TerminalType.ONSHORE_EXPORT
        assert cove_point.capacity_mtpa == pytest.approx(5.25, rel=0.1)
        assert cove_point.year_commissioned == 2018

    def test_terminals_have_sources(self, seed_data_path):
        """Test that loaded terminals have source citations."""
        loader = TerminalLoader(seed_data_path)
        terminals = loader.load()

        # Every terminal should have at least one source
        for terminal in terminals:
            assert len(terminal.sources) > 0
            assert isinstance(terminal.sources[0], SourceCitation)
            assert terminal.sources[0].source_name
            assert terminal.sources[0].reliability in list(SourceReliability)

    def test_geographic_distribution(self, seed_data_path):
        """Test that dataset has good geographic distribution."""
        loader = TerminalLoader(seed_data_path)
        terminals = loader.load()

        # Count by region
        countries = [t.country for t in terminals]

        # US should have at least 15 terminals
        us_count = countries.count("USA")
        assert us_count >= 15, f"Expected >= 15 US terminals, got {us_count}"

        # Should have Middle East representation (Qatar, UAE, Oman, Kuwait, Saudi Arabia)
        middle_east = ["QAT", "ARE", "OMN", "KWT", "SAU"]
        middle_east_count = sum(countries.count(c) for c in middle_east)
        assert (
            middle_east_count >= 5
        ), f"Expected >= 5 Middle East terminals, got {middle_east_count}"

        # Should have Australia representation
        aus_count = countries.count("AUS")
        assert aus_count >= 5, f"Expected >= 5 Australian terminals, got {aus_count}"

        # Should have Europe representation
        europe = ["GBR", "ESP", "NOR", "FRA", "BEL", "PRT", "GRC", "POL", "LTU", "DEU"]
        europe_count = sum(countries.count(c) for c in europe)
        assert (
            europe_count >= 10
        ), f"Expected >= 10 European terminals, got {europe_count}"

    def test_terminal_type_mix(self, seed_data_path):
        """Test dataset contains mix of terminal types."""
        loader = TerminalLoader(seed_data_path)
        terminals = loader.load()

        types = [t.terminal_type for t in terminals]

        # Should have onshore export terminals
        assert TerminalType.ONSHORE_EXPORT in types

        # Should have onshore import terminals
        assert TerminalType.ONSHORE_IMPORT in types

        # Should have FSRU terminals
        assert TerminalType.FSRU in types

        # Should have FLNG terminals
        assert TerminalType.FLNG in types

    def test_coordinates_present_for_most_terminals(self, seed_data_path):
        """Test that most terminals have coordinate data."""
        loader = TerminalLoader(seed_data_path)
        terminals = loader.load()

        with_coords = sum(
            1 for t in terminals if t.latitude is not None and t.longitude is not None
        )

        # At least 80% should have coordinates
        coverage = with_coords / len(terminals)
        assert (
            coverage >= 0.8
        ), f"Expected >= 80% coordinate coverage, got {coverage:.1%}"
