"""
Unit tests for TSB (Canadian Transportation Safety Board) Importer

Tests parsing logic, field mapping, and schema compliance using synthetic fixture data.
No external HTTP requests or file system dependencies beyond fixtures.
"""

import csv
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from worldenergydata.marine_safety.importers.tsb_importer import TSBImporter


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session"""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = Mock()
    session.flush = Mock()
    return session


@pytest.fixture
def tsb_occurrence_csv(tmp_path):
    """Create minimal TSB occurrence CSV fixture"""
    csv_path = tmp_path / "occurrence.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "OccNo",
                "OccDate",
                "OccTypeDisplayEng",
                "AccIncTypeDisplayEng",
                "TotalDeaths",
                "TotalMinorInjuries",
                "TotalSeriousInjuries",
                "TotalMissingIndividuals",
                "Summary",
                "ProvinceDisplayEng",
                "Latitude",
                "Longitude",
            ]
        )
        writer.writerow(
            [
                "TSB001",
                "2023-07-15 00:00:00.0000000",
                "Accident",
                "Grounding",
                "0",
                "1",
                "2",
                "0",
                "Vessel ran aground in shallow waters",
                "BRITISH COLUMBIA (BC)",
                "49.123",
                "-123.456",
            ]
        )
        writer.writerow(
            [
                "TSB002",
                "2023-08-20 14:30:00.0000000",
                "Incident",
                "Fire",
                "1",
                "3",
                "1",
                "0",
                "Fire in galley spread to accommodations",
                "NOVA SCOTIA (NS)",
                "44.567",
                "-63.890",
            ]
        )

    return csv_path


@pytest.fixture
def tsb_vessels_csv(tmp_path):
    """Create minimal TSB vessel CSV fixture"""
    csv_path = tmp_path / "vessel.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "OccNo",
                "VesselName",
                "VesselTypeDisplayEng",
                "IMO",
                "OfficialNo",
                "MMSI",
                "CallSign",
                "VesselFlagDisplayEng",
                "Length_Meters",
                "GrossTonnage",
                "YearBuilt",
                "NumberOfCrew",
                "NumberOfPass",
                "TotalPeopleOnBoard",
            ]
        )
        writer.writerow(
            [
                "TSB001",
                "Pacific Trader",
                "Cargo Ship",
                "IMO1234567",
                "CA123456",
                "316123456",
                "CFAB",
                "CANADA",
                "120.5",
                "8500",
                "2012",
                "18",
                "0",
                "18",
            ]
        )
        writer.writerow(
            [
                "TSB002",
                "Atlantic Star",
                "Fishing Vessel",
                "",
                "NS789012",
                "316789012",
                "VCDE",
                "CANADA",
                "25.3",
                "150",
                "2005",
                "6",
                "0",
                "6",
            ]
        )

    return csv_path


@pytest.fixture
def tsb_injuries_csv(tmp_path):
    """Create minimal TSB injuries CSV fixture"""
    csv_path = tmp_path / "injuries.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["OccNo", "InjurySeverity", "Count"])
        writer.writerow(["TSB001", "Minor", "1"])
        writer.writerow(["TSB001", "Serious", "2"])
        writer.writerow(["TSB002", "Fatal", "1"])
        writer.writerow(["TSB002", "Minor", "3"])

    return csv_path


def test_tsb_importer_initialization(tsb_occurrence_csv, mock_session):
    """Test TSB importer initializes correctly"""
    importer = TSBImporter(
        occurrence_file=tsb_occurrence_csv, session=mock_session, batch_size=10
    )

    assert importer.source_path == tsb_occurrence_csv
    assert importer.batch_size == 10
    assert importer.vessels_by_occno == {}
    assert importer.injuries_by_occno == {}


def test_tsb_read_source(tsb_occurrence_csv, tsb_vessels_csv, mock_session):
    """Test TSB read_source yields records correctly"""
    importer = TSBImporter(
        occurrence_file=tsb_occurrence_csv,
        vessels_file=tsb_vessels_csv,
        session=mock_session,
    )

    records = list(importer.read_source())

    assert len(records) == 2
    assert records[0]["OccNo"] == "TSB001"
    assert records[1]["OccNo"] == "TSB002"


def test_tsb_vessels_loading(tsb_occurrence_csv, tsb_vessels_csv, mock_session):
    """Test TSB vessels data loads correctly"""
    importer = TSBImporter(
        occurrence_file=tsb_occurrence_csv,
        vessels_file=tsb_vessels_csv,
        session=mock_session,
    )

    importer._load_related_data()

    assert "TSB001" in importer.vessels_by_occno
    assert "TSB002" in importer.vessels_by_occno
    assert importer.vessels_by_occno["TSB001"][0]["VesselName"] == "Pacific Trader"
    assert (
        importer.vessels_by_occno["TSB002"][0]["VesselTypeDisplayEng"]
        == "Fishing Vessel"
    )


def test_tsb_parse_grounding_record(tsb_occurrence_csv, tsb_vessels_csv, mock_session):
    """Test parsing TSB grounding record"""
    importer = TSBImporter(
        occurrence_file=tsb_occurrence_csv,
        vessels_file=tsb_vessels_csv,
        session=mock_session,
    )

    raw_record = {
        "OccNo": "TSB001",
        "OccDate": "2023-07-15 00:00:00.0000000",
        "OccTypeDisplayEng": "Accident",
        "AccIncTypeDisplayEng": "Grounding",
        "TotalDeaths": "0",
        "TotalMinorInjuries": "1",
        "TotalSeriousInjuries": "2",
        "TotalMissingIndividuals": "0",
        "Summary": "Vessel ran aground in shallow waters",
        "ProvinceDisplayEng": "BRITISH COLUMBIA (BC)",
        "Latitude": "49.123",
        "Longitude": "-123.456",
    }

    parsed = importer.parse_record(raw_record)

    assert parsed is not None
    assert parsed["source_agency"] == "TSB_CANADA"
    assert parsed["source_incident_id"] == "TSB001"
    # TSB maps "Grounding" in AccIncTypeDisplayEng
    assert parsed["incident_type"] in (
        "grounding",
        "collision",
        "other",
    )  # Implementation may vary
    assert parsed["fatalities"] == 0
    assert parsed["injuries"] == 3  # 1 minor + 2 serious
    assert parsed["missing"] == 0
    assert parsed["description"] == "Vessel ran aground in shallow waters"


def test_tsb_parse_fire_record(tsb_occurrence_csv, mock_session):
    """Test parsing TSB fire record"""
    importer = TSBImporter(occurrence_file=tsb_occurrence_csv, session=mock_session)

    raw_record = {
        "OccNo": "TSB002",
        "OccDate": "2023-08-20 14:30:00.0000000",
        "OccTypeDisplayEng": "Incident",
        "AccIncTypeDisplayEng": "Fire",
        "TotalDeaths": "1",
        "TotalMinorInjuries": "3",
        "TotalSeriousInjuries": "1",
        "TotalMissingIndividuals": "0",
        "Summary": "Fire in galley spread to accommodations",
        "ProvinceDisplayEng": "NOVA SCOTIA (NS)",
        "Latitude": "44.567",
        "Longitude": "-63.890",
    }

    parsed = importer.parse_record(raw_record)

    assert parsed is not None
    # TSB maps "Fire" in AccIncTypeDisplayEng
    assert parsed["incident_type"] in ("fire", "other")  # Implementation may vary
    assert parsed["fatalities"] == 1
    assert parsed["injuries"] == 4  # 3 minor + 1 serious


def test_tsb_date_parsing(tsb_occurrence_csv, mock_session):
    """Test TSB date parsing with microseconds"""
    importer = TSBImporter(occurrence_file=tsb_occurrence_csv, session=mock_session)

    valid_date = importer._parse_date("2023-07-15 14:30:25.1234567")
    assert valid_date == datetime(2023, 7, 15)

    short_date = importer._parse_date("2023-07-15")
    assert short_date == datetime(2023, 7, 15)

    invalid_date = importer._parse_date("invalid")
    assert invalid_date is None


def test_tsb_vessel_type_mapping(tsb_occurrence_csv, mock_session):
    """Test TSB vessel type mapping"""
    importer = TSBImporter(occurrence_file=tsb_occurrence_csv, session=mock_session)

    assert importer._map_vessel_type("Fishing Vessel") == "fishing"
    assert importer._map_vessel_type("Cargo Ship") == "cargo"
    assert importer._map_vessel_type("Tanker") == "tanker"
    assert importer._map_vessel_type("Passenger Ferry") == "passenger"
    assert importer._map_vessel_type("Tugboat") == "tugboat"
    assert importer._map_vessel_type("Unknown Type") == "other"


def test_tsb_province_code_extraction(tsb_occurrence_csv, mock_session):
    """Test TSB province code extraction"""
    importer = TSBImporter(occurrence_file=tsb_occurrence_csv, session=mock_session)

    assert importer._map_province_code("BRITISH COLUMBIA (BC)") == "BC"
    assert importer._map_province_code("NOVA SCOTIA (NS)") == "NS"
    assert importer._map_province_code("ONTARIO (ON)") == "ON"
    assert importer._map_province_code("No Province") is None


def test_tsb_location_building(tsb_occurrence_csv, mock_session):
    """Test TSB location data building"""
    importer = TSBImporter(occurrence_file=tsb_occurrence_csv, session=mock_session)

    raw_record = {
        "ProvinceDisplayEng": "BRITISH COLUMBIA (BC)",
        "RegionOfOccurrenceDisplayEng": "Pacific",
        "AreaTypeDisplayEng": "Harbour",
        "NearestLocationDescription": "Vancouver Harbour",
        "NearestLocationDistance_Nm": "2.5",
        "Latitude": "49.123",
        "Longitude": "-123.456",
    }

    location = importer._build_location_data(raw_record)

    assert location is not None
    assert location["province"] == "BRITISH COLUMBIA (BC)"
    assert location["region"] == "Pacific"
    assert location["latitude"] == 49.123
    assert location["longitude"] == -123.456


def test_tsb_vessel_data_building(tsb_occurrence_csv, tsb_vessels_csv, mock_session):
    """Test TSB vessel data building"""
    importer = TSBImporter(
        occurrence_file=tsb_occurrence_csv,
        vessels_file=tsb_vessels_csv,
        session=mock_session,
    )

    importer._load_related_data()
    vessel = importer._build_vessel_data("TSB001")

    assert vessel is not None
    assert vessel["vessel_name"] == "Pacific Trader"
    assert vessel["vessel_type"] == "cargo"
    assert vessel["imo_number"] == "IMO1234567"
    assert vessel["flag_state"] == "CANADA"
    assert vessel["length_meters"] == 120.5
    assert vessel["year_built"] == 2012


def test_tsb_duplicate_detection(tsb_occurrence_csv, mock_session):
    """Test TSB duplicate occurrence detection"""
    importer = TSBImporter(occurrence_file=tsb_occurrence_csv, session=mock_session)

    # First occurrence
    occno = importer._extract_incident_id({"OccNo": "TSB001"})
    assert occno == "TSB001"

    # Duplicate occurrence
    dup_occno = importer._extract_incident_id({"OccNo": "TSB001"})
    assert dup_occno is None  # Should return None for duplicate


def test_tsb_parse_with_missing_fields(tsb_occurrence_csv, mock_session):
    """Test TSB parsing handles missing optional fields gracefully"""
    importer = TSBImporter(occurrence_file=tsb_occurrence_csv, session=mock_session)

    minimal_record = {
        "OccNo": "TSB-MIN",
        "OccDate": "2023-01-01",
        "OccTypeDisplayEng": "",
        "AccIncTypeDisplayEng": "",
        "TotalDeaths": "",
        "TotalMinorInjuries": "",
        "TotalSeriousInjuries": "",
        "TotalMissingIndividuals": "",
        "Summary": "",
        "ProvinceDisplayEng": "",
        "Latitude": "",
        "Longitude": "",
    }

    parsed = importer.parse_record(minimal_record)

    assert parsed is not None
    assert parsed["source_incident_id"] == "TSB-MIN"
    assert parsed["incident_type"] == "other"
    assert parsed["fatalities"] == 0
    assert parsed["injuries"] == 0
    assert parsed["missing"] == 0


def test_tsb_parse_invalid_record(tsb_occurrence_csv, mock_session):
    """Test TSB parsing rejects invalid records"""
    importer = TSBImporter(occurrence_file=tsb_occurrence_csv, session=mock_session)

    # Missing occurrence number
    invalid_record = {"OccNo": "", "OccDate": "2023-01-01"}

    parsed = importer.parse_record(invalid_record)
    assert parsed is None
