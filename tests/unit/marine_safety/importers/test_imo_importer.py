"""
Unit tests for IMO GISIS (Global Integrated Shipping Information System) Importer

Tests parsing logic, IMO number validation, field mapping, and schema compliance
using synthetic fixture data. No external HTTP requests.
"""

import csv
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from worldenergydata.marine_safety.importers.imo_importer import IMOGISISImporter
from worldenergydata.marine_safety.importers.imo_validators import validate_imo_number


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session"""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = Mock()
    session.flush = Mock()
    return session


@pytest.fixture
def imo_gisis_csv(tmp_path):
    """Create minimal IMO GISIS CSV fixture"""
    csv_path = tmp_path / "gisis_casualties.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "CASUALTY ID", "DATE OF OCCURRENCE", "SHIP NAME", "IMO NUMBER",
            "FLAG STATE", "SHIP TYPE", "CASUALTY TYPE", "GROSS TONNAGE",
            "LATITUDE", "LONGITUDE", "BRIEF DESCRIPTION", "FATALITIES",
            "INJURIES", "MISSING PERSONS", "INVESTIGATION STATUS"
        ])
        writer.writerow([
            "GISIS-001", "2023-09-15", "MV OCEAN STAR", "9123456",
            "Panama", "Bulk Carrier", "Collision", "45000",
            "35.123", "-140.456", "Collision with cargo vessel in fog", "0", "3", "0", "Under investigation"
        ])
        writer.writerow([
            "GISIS-002", "2023-10-22", "ATLANTIC PRINCESS", "9234567",
            "Liberia", "Oil Tanker", "Fire/Explosion", "85000",
            "-12.456", "45.789", "Engine room explosion during bunker ops", "2", "5", "1", "Final report"
        ])

    return csv_path


def test_imo_importer_initialization(imo_gisis_csv, mock_session):
    """Test IMO importer initializes correctly"""
    importer = IMOGISISImporter(
        source_path=imo_gisis_csv,
        session=mock_session,
        batch_size=10,
        validate_imo=True
    )

    assert importer.source_path == imo_gisis_csv
    assert importer.batch_size == 10
    assert importer.validate_imo_flag is True
    assert importer.file_format == "csv"


def test_imo_read_source(imo_gisis_csv, mock_session):
    """Test IMO read_source yields records correctly"""
    importer = IMOGISISImporter(
        source_path=imo_gisis_csv,
        session=mock_session,
        validate_imo=False
    )

    records = list(importer.read_source())

    assert len(records) == 2
    assert "CASUALTY ID" in records[0]
    assert "SHIP NAME" in records[0]


def test_imo_parse_collision_record(imo_gisis_csv, mock_session):
    """Test parsing IMO collision record"""
    importer = IMOGISISImporter(
        source_path=imo_gisis_csv,
        session=mock_session,
        validate_imo=False
    )

    raw_record = {
        "CASUALTY ID": "GISIS-001",
        "DATE OF OCCURRENCE": "2023-09-15",
        "SHIP NAME": "MV OCEAN STAR",
        "IMO NUMBER": "9123456",
        "FLAG STATE": "Panama",
        "SHIP TYPE": "Bulk Carrier",
        "CASUALTY TYPE": "Collision",
        "GROSS TONNAGE": "45000",
        "LATITUDE": "35.123",
        "LONGITUDE": "-140.456",
        "BRIEF DESCRIPTION": "Collision with cargo vessel in fog",
        "FATALITIES": "0",
        "INJURIES": "3",
        "MISSING PERSONS": "0",
        "INVESTIGATION STATUS": "Under investigation"
    }

    parsed = importer.parse_record(raw_record)

    assert parsed is not None
    assert parsed["source_agency"] == "imo"
    assert parsed["source_incident_id"] == "GISIS-001"
    assert parsed["vessel_name"] == "MV OCEAN STAR"
    assert parsed["incident_type"] == "collision"


def test_imo_parse_fire_explosion_record(imo_gisis_csv, mock_session):
    """Test parsing IMO fire/explosion record"""
    importer = IMOGISISImporter(
        source_path=imo_gisis_csv,
        session=mock_session,
        validate_imo=False
    )

    raw_record = {
        "CASUALTY ID": "GISIS-002",
        "DATE OF OCCURRENCE": "2023-10-22",
        "SHIP NAME": "ATLANTIC PRINCESS",
        "IMO NUMBER": "9234567",
        "FLAG STATE": "Liberia",
        "SHIP TYPE": "Oil Tanker",
        "CASUALTY TYPE": "Fire/Explosion",
        "GROSS TONNAGE": "85000",
        "LATITUDE": "-12.456",
        "LONGITUDE": "45.789",
        "BRIEF DESCRIPTION": "Engine room explosion during bunker ops",
        "FATALITIES": "2",
        "INJURIES": "5",
        "MISSING PERSONS": "1",
        "INVESTIGATION STATUS": "Final report"
    }

    parsed = importer.parse_record(raw_record)

    assert parsed is not None
    assert parsed["incident_type"] in ["fire", "explosion"]
    assert parsed["fatalities"] == 2
    assert parsed["injuries"] == 5
    assert parsed["missing_persons"] == 1


def test_imo_number_validation_valid():
    """Test IMO number validation with valid numbers"""
    # Valid IMO number with correct checksum
    is_valid, cleaned = validate_imo_number("IMO 9074729")
    assert is_valid is True
    assert cleaned == "9074729"

    is_valid, cleaned = validate_imo_number("9074729")
    assert is_valid is True


def test_imo_number_validation_invalid():
    """Test IMO number validation with invalid checksums"""
    is_valid, cleaned = validate_imo_number("IMO 9074720")  # Wrong checksum
    assert is_valid is False
    assert cleaned == "9074720"  # Still returns cleaned number


def test_imo_number_validation_malformed():
    """Test IMO number validation with malformed input"""
    is_valid, cleaned = validate_imo_number("ABC123")
    assert is_valid is False
    assert cleaned is None

    is_valid, cleaned = validate_imo_number("")
    assert is_valid is False
    assert cleaned is None


def test_imo_flag_state_normalization(imo_gisis_csv, mock_session):
    """Test IMO flag state normalization"""
    from worldenergydata.marine_safety.importers.imo_normalizers import normalize_flag_state

    assert normalize_flag_state("Panama") == "PA"
    assert normalize_flag_state("Liberia") == "LR"
    assert normalize_flag_state("Marshall Islands") == "MH"
    assert normalize_flag_state("United Kingdom") == "GB"
    # Unknown flags return "UN" or the original input
    result = normalize_flag_state("Unknown")
    assert result in ("UN", "XX", "Unknown")  # Implementation may vary


def test_imo_casualty_type_mapping(imo_gisis_csv, mock_session):
    """Test IMO casualty type to incident type mapping"""
    from worldenergydata.marine_safety.importers.imo_parser import map_casualty_type

    assert map_casualty_type("Collision") == "collision"
    assert map_casualty_type("Grounding") == "grounding"
    assert map_casualty_type("Fire/Explosion") in ["fire", "explosion"]
    assert map_casualty_type("Capsizing") == "capsizing"
    assert map_casualty_type("Unknown") == "other"


def test_imo_ship_type_mapping(imo_gisis_csv, mock_session):
    """Test IMO ship type to vessel type mapping"""
    from worldenergydata.marine_safety.importers.imo_parser import map_ship_type

    # Check that mappings return vessel type values (may use VesselType enum values)
    bulk_result = map_ship_type("Bulk Carrier")
    assert bulk_result in ("cargo", "cargo_vessel")

    tanker_result = map_ship_type("Oil Tanker")
    assert tanker_result in ("tanker", "oil_tanker")

    container_result = map_ship_type("Container Ship")
    assert container_result in ("cargo", "cargo_vessel", "container")

    passenger_result = map_ship_type("Passenger Ship")
    assert passenger_result in ("passenger", "passenger_ship", "other")  # May map to other if not in mappings


def test_imo_position_parsing(imo_gisis_csv, mock_session):
    """Test IMO position string parsing"""
    from worldenergydata.marine_safety.importers.imo_parser import parse_position
    from decimal import Decimal

    # Test decimal format (comma-separated)
    lat, lon = parse_position("35.123, -140.456")
    assert lat == Decimal("35.123")
    assert lon == Decimal("-140.456")

    # Test degrees-minutes-seconds format
    lat, lon = parse_position("35 7 23 N, 140 27 22 W")
    assert lat is not None
    assert lon is not None
    assert lat > Decimal("35.0")
    assert lon < Decimal("-140.0")

    # Test invalid format
    lat, lon = parse_position("invalid position")
    assert lat is None
    assert lon is None


def test_imo_severity_calculation(imo_gisis_csv, mock_session):
    """Test IMO severity calculation based on casualties"""
    from worldenergydata.marine_safety.importers.imo_parser import calculate_severity

    assert calculate_severity(10, 5, 2) == 5  # Max severity: 10+ fatalities
    assert calculate_severity(5, 10, 0) == 4  # High: 5-9 fatalities
    assert calculate_severity(1, 20, 0) == 3  # Moderate: 1-4 fatalities
    assert calculate_severity(0, 5, 0) == 2  # Minor: injuries only
    assert calculate_severity(0, 0, 0) == 1  # Minimal: no casualties


def test_imo_parse_with_missing_imo_number(imo_gisis_csv, mock_session):
    """Test IMO parsing with missing IMO number"""
    importer = IMOGISISImporter(
        source_path=imo_gisis_csv,
        session=mock_session,
        validate_imo=True
    )

    raw_record = {
        "CASUALTY ID": "GISIS-003",
        "DATE OF OCCURRENCE": "2023-11-01",
        "SHIP NAME": "UNKNOWN VESSEL",
        "IMO NUMBER": "",
        "FLAG STATE": "Unknown",
        "SHIP TYPE": "Other",
        "CASUALTY TYPE": "Grounding",
        "BRIEF DESCRIPTION": "Small vessel grounded"
    }

    parsed = importer.parse_record(raw_record)

    assert parsed is not None
    assert "imo_number" not in parsed or parsed.get("imo_number") is None


def test_imo_strict_validation_mode(imo_gisis_csv, mock_session):
    """Test IMO strict validation rejects invalid checksums"""
    importer = IMOGISISImporter(
        source_path=imo_gisis_csv,
        session=mock_session,
        validate_imo=True,
        strict_imo_validation=True
    )

    raw_record = {
        "CASUALTY ID": "GISIS-004",
        "DATE OF OCCURRENCE": "2023-11-15",
        "SHIP NAME": "BAD IMO VESSEL",
        "IMO NUMBER": "9999999",  # Invalid checksum
        "FLAG STATE": "Panama",
        "SHIP TYPE": "Cargo",
        "CASUALTY TYPE": "Collision"
    }

    parsed = importer.parse_record(raw_record)
    # Should be rejected in strict mode
    assert parsed is None


def test_imo_parse_with_missing_date(imo_gisis_csv, mock_session):
    """Test IMO parsing rejects record without incident date"""
    importer = IMOGISISImporter(
        source_path=imo_gisis_csv,
        session=mock_session,
        validate_imo=False
    )

    raw_record = {
        "CASUALTY ID": "GISIS-005",
        "DATE OF OCCURRENCE": "",
        "SHIP NAME": "TEST VESSEL",
        "CASUALTY TYPE": "Other"
    }

    parsed = importer.parse_record(raw_record)
    assert parsed is None  # Must have incident date


def test_imo_field_statistics(imo_gisis_csv, mock_session):
    """Test IMO field statistics analysis"""
    importer = IMOGISISImporter(
        source_path=imo_gisis_csv,
        session=mock_session,
        validate_imo=False
    )

    stats = importer.get_field_statistics(max_records=10)

    assert "total_records_analyzed" in stats
    assert "fields" in stats
    assert stats["total_records_analyzed"] == 2
