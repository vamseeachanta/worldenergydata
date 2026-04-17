"""
Unit tests for MAIB (UK Marine Accident Investigation Branch) Importer

Tests parsing logic, field mapping, and schema compliance using synthetic fixture data.
No external HTTP requests or file system dependencies beyond fixtures.
"""

import csv
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from worldenergydata.marine_safety.importers.maib_importer import MAIBImporter


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session"""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = Mock()
    session.flush = Mock()
    return session


@pytest.fixture
def maib_occurrence_csv(tmp_path):
    """Create minimal MAIB occurrences CSV fixture"""
    csv_path = tmp_path / "maib_occurrences.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(
            [
                "Occurrence_Id",
                "Local_Date_Main_Event",
                "Main_Event_L1",
                "Main_Event_L2",
                "Main_Event_L3",
                "Occurrence_Severity",
                "Short_Description",
                "Description",
                "Occurrence_Location",
                "Coastal_State_Affected",
                "Latitude",
                "Longitude",
            ]
        )
        writer.writerow(
            [
                "OCC-001",
                "2023-05-15",
                "Navigation",
                "Collision",
                "Collision with vessel",
                "serious marine casualty",
                "Collision in fog",
                "Two vessels collided in dense fog",
                "English Channel",
                "UNITED KINGDOM",
                "50.5",
                "-1.25",
            ]
        )
        writer.writerow(
            [
                "OCC-002",
                "2023-06-20",
                "Technical",
                "Fire",
                "Engine room fire",
                "marine casualty",
                "Engine fire",
                "Fire broke out in engine room",
                "North Sea",
                "UK",
                "55.123",
                "2.456",
            ]
        )

    return csv_path


@pytest.fixture
def maib_vessels_csv(tmp_path):
    """Create minimal MAIB vessels CSV fixture"""
    csv_path = tmp_path / "maib_vessels.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(
            [
                "Occurrence_Id",
                "Flag_State",
                "Vessel_Category_L1",
                "Ship_Craft_Type_L1",
                "Ship_Craft_Type_L2",
                "LOA_Length_Overall_in_Metres",
                "GT_Gross_Tonnage",
                "Year_Built",
                "Hull_Material",
                "Is_Commercial_Vessel",
                "Crew_Voyage",
                "Deaths_Crew",
                "Injuries_Crew",
            ]
        )
        writer.writerow(
            [
                "OCC-001",
                "United Kingdom",
                "Cargo Ship",
                "General Cargo",
                "Bulk Carrier",
                "150.5",
                "5000",
                "2010",
                "Steel",
                "True",
                "20",
                "0",
                "2",
            ]
        )
        writer.writerow(
            [
                "OCC-002",
                "Norway",
                "Tanker",
                "Oil Tanker",
                "Crude Oil Tanker",
                "200.0",
                "25000",
                "2015",
                "Steel",
                "True",
                "25",
                "1",
                "3",
            ]
        )

    return csv_path


@pytest.fixture
def maib_persons_csv(tmp_path):
    """Create minimal MAIB affected persons CSV fixture"""
    csv_path = tmp_path / "maib_affected_persons.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Occurrence_Id", "Injury_Type"])
        writer.writerow(["OCC-001", "Minor injury"])
        writer.writerow(["OCC-001", "Serious injury"])
        writer.writerow(["OCC-002", "Fatal injury"])

    return csv_path


def test_maib_importer_initialization(maib_occurrence_csv, mock_session):
    """Test MAIB importer initializes correctly"""
    importer = MAIBImporter(
        occurrences_file=maib_occurrence_csv, session=mock_session, batch_size=10
    )

    assert importer.source_path == maib_occurrence_csv
    assert importer.batch_size == 10
    assert importer.vessels_by_occid == {}
    assert importer.persons_by_occid == {}


def test_maib_read_source(
    maib_occurrence_csv, maib_vessels_csv, maib_persons_csv, mock_session
):
    """Test MAIB read_source yields records correctly"""
    importer = MAIBImporter(
        occurrences_file=maib_occurrence_csv,
        vessels_file=maib_vessels_csv,
        persons_file=maib_persons_csv,
        session=mock_session,
    )

    records = list(importer.read_source())

    assert len(records) == 2
    assert records[0]["Occurrence_Id"] == "OCC-001"
    assert records[1]["Occurrence_Id"] == "OCC-002"


def test_maib_vessels_loading(maib_occurrence_csv, maib_vessels_csv, mock_session):
    """Test MAIB vessels data loads correctly"""
    importer = MAIBImporter(
        occurrences_file=maib_occurrence_csv,
        vessels_file=maib_vessels_csv,
        session=mock_session,
    )

    importer._load_related_data()

    assert "OCC-001" in importer.vessels_by_occid
    assert "OCC-002" in importer.vessels_by_occid
    assert len(importer.vessels_by_occid["OCC-001"]) == 1
    assert importer.vessels_by_occid["OCC-001"][0]["Flag_State"] == "United Kingdom"


def test_maib_persons_loading(maib_occurrence_csv, maib_persons_csv, mock_session):
    """Test MAIB affected persons data loads correctly"""
    importer = MAIBImporter(
        occurrences_file=maib_occurrence_csv,
        persons_file=maib_persons_csv,
        session=mock_session,
    )

    importer._load_related_data()

    assert "OCC-001" in importer.persons_by_occid
    assert "OCC-002" in importer.persons_by_occid
    assert len(importer.persons_by_occid["OCC-001"]) == 2
    assert len(importer.persons_by_occid["OCC-002"]) == 1


def test_maib_parse_collision_record(
    maib_occurrence_csv, maib_vessels_csv, mock_session
):
    """Test parsing MAIB collision record"""
    importer = MAIBImporter(
        occurrences_file=maib_occurrence_csv,
        vessels_file=maib_vessels_csv,
        session=mock_session,
    )

    raw_record = {
        "Occurrence_Id": "OCC-001",
        "Local_Date_Main_Event": "2023-05-15",
        "Main_Event_L1": "Navigation",
        "Main_Event_L2": "Collision",
        "Main_Event_L3": "Collision with vessel",
        "Occurrence_Severity": "serious marine casualty",
        "Short_Description": "Collision in fog",
        "Description": "Two vessels collided in dense fog",
        "Occurrence_Location": "English Channel",
        "Coastal_State_Affected": "UNITED KINGDOM",
        "Latitude": "50.5",
        "Longitude": "-1.25",
    }

    parsed = importer.parse_record(raw_record)

    assert parsed is not None
    assert parsed["source_agency"] == "MAIB_UK"
    assert parsed["source_incident_id"] == "OCC-001"
    assert parsed["incident_type"] == "collision"
    assert parsed["description"] == "Two vessels collided in dense fog"
    assert "location" in parsed
    assert parsed["location"]["latitude"] == 50.5
    assert parsed["location"]["longitude"] == -1.25


def test_maib_parse_fire_record(maib_occurrence_csv, mock_session):
    """Test parsing MAIB fire record"""
    importer = MAIBImporter(occurrences_file=maib_occurrence_csv, session=mock_session)

    raw_record = {
        "Occurrence_Id": "OCC-002",
        "Local_Date_Main_Event": "2023-06-20",
        "Main_Event_L1": "Technical",
        "Main_Event_L2": "Fire",
        "Main_Event_L3": "Engine room fire",
        "Occurrence_Severity": "marine casualty",
        "Short_Description": "Engine fire",
        "Description": "Fire broke out in engine room",
        "Occurrence_Location": "North Sea",
        "Coastal_State_Affected": "UK",
        "Latitude": "55.123",
        "Longitude": "2.456",
    }

    parsed = importer.parse_record(raw_record)

    assert parsed is not None
    assert parsed["incident_type"] == "fire"
    assert parsed["description"] == "Fire broke out in engine room"


def test_maib_casualty_counting(maib_occurrence_csv, maib_persons_csv, mock_session):
    """Test MAIB casualty counting from persons data"""
    importer = MAIBImporter(
        occurrences_file=maib_occurrence_csv,
        persons_file=maib_persons_csv,
        session=mock_session,
    )

    importer._load_related_data()
    fatalities, injuries = importer._count_casualties("OCC-001")

    assert injuries == 2  # Minor + Serious injury
    assert fatalities == 0

    fatalities, injuries = importer._count_casualties("OCC-002")
    assert fatalities == 1
    assert injuries == 0


def test_maib_date_parsing(maib_occurrence_csv, mock_session):
    """Test MAIB date parsing"""
    importer = MAIBImporter(occurrences_file=maib_occurrence_csv, session=mock_session)

    valid_date = importer._parse_date("2023-05-15")
    assert valid_date == datetime(2023, 5, 15)

    invalid_date = importer._parse_date("invalid")
    assert invalid_date is None

    empty_date = importer._parse_date("")
    assert empty_date is None


def test_maib_vessel_type_mapping(maib_occurrence_csv, mock_session):
    """Test MAIB vessel type mapping"""
    importer = MAIBImporter(occurrences_file=maib_occurrence_csv, session=mock_session)

    assert importer._map_vessel_type("Fishing", "Trawler") == "fishing"
    assert importer._map_vessel_type("Cargo", "Container Ship") == "cargo"
    assert importer._map_vessel_type("Tanker", "Oil Tanker") == "tanker"
    assert importer._map_vessel_type("Passenger", "Ferry") == "passenger"
    assert importer._map_vessel_type("Unknown", "Unknown") == "other"


def test_maib_incident_type_determination(maib_occurrence_csv, mock_session):
    """Test MAIB incident type determination from event fields"""
    importer = MAIBImporter(occurrences_file=maib_occurrence_csv, session=mock_session)

    # Test collision event
    collision_record = {
        "Main_Event_L3": "collision with vessel",
        "Main_Event_L2": "collision",
        "Main_Event_L1": "navigation",
        "Occurrence_Severity": "serious",
    }
    assert importer._determine_incident_type(collision_record) == "collision"

    # Test grounding
    grounding_record = {
        "Main_Event_L3": "",
        "Main_Event_L2": "grounding",
        "Main_Event_L1": "navigation",
        "Occurrence_Severity": "serious",
    }
    assert importer._determine_incident_type(grounding_record) == "grounding"

    # Test fire
    fire_record = {
        "Main_Event_L3": "",
        "Main_Event_L2": "fire",
        "Main_Event_L1": "technical",
        "Occurrence_Severity": "marine casualty",
    }
    assert importer._determine_incident_type(fire_record) == "fire"


def test_maib_parse_with_missing_fields(maib_occurrence_csv, mock_session):
    """Test MAIB parsing handles missing optional fields gracefully"""
    importer = MAIBImporter(occurrences_file=maib_occurrence_csv, session=mock_session)

    minimal_record = {
        "Occurrence_Id": "OCC-MIN",
        "Local_Date_Main_Event": "2023-01-01",
        "Main_Event_L1": "",
        "Main_Event_L2": "",
        "Main_Event_L3": "",
        "Occurrence_Severity": "",
        "Short_Description": "",
        "Description": "",
        "Occurrence_Location": "",
        "Coastal_State_Affected": "",
        "Latitude": "",
        "Longitude": "",
    }

    parsed = importer.parse_record(minimal_record)

    assert parsed is not None
    assert parsed["source_incident_id"] == "OCC-MIN"
    assert parsed["incident_type"] == "other"  # Default when no event type matched
    assert parsed["fatalities"] == 0
    assert parsed["injuries"] == 0
    assert parsed["missing"] == 0


def test_maib_parse_invalid_record(maib_occurrence_csv, mock_session):
    """Test MAIB parsing rejects invalid records"""
    importer = MAIBImporter(occurrences_file=maib_occurrence_csv, session=mock_session)

    # Missing occurrence ID
    invalid_record = {"Occurrence_Id": "", "Local_Date_Main_Event": "2023-01-01"}

    parsed = importer.parse_record(invalid_record)
    assert parsed is None
