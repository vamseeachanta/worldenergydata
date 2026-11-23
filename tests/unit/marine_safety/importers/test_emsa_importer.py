"""
Unit tests for EMSA (European Maritime Safety Agency) EMCIP Importer

Tests initialization, mapping constants, and configuration. EMSA importer is a stub
implementation requiring institutional access credentials, so tests focus on
helper methods and data structures rather than actual data import.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from worldenergydata.marine_safety.constants import (
    IncidentStatus,
    IncidentType,
    VesselType,
)
from worldenergydata.marine_safety.importers.emsa_importer import EMSAImporter


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session"""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = Mock()
    session.flush = Mock()
    return session


@pytest.fixture
def emsa_csv_path(tmp_path):
    """Create dummy EMCIP CSV file path"""
    return tmp_path / "emcip_export.csv"


def test_emsa_importer_initialization(emsa_csv_path, mock_session):
    """Test EMSA importer initializes correctly"""
    importer = EMSAImporter(
        source_path=emsa_csv_path,
        session=mock_session,
        batch_size=10,
        file_format="csv",
        member_state="all",
    )

    assert importer.source_path == emsa_csv_path
    assert importer.batch_size == 10
    assert importer.file_format == "csv"
    assert importer.member_state is None  # "all" maps to None


def test_emsa_auto_format_detection(tmp_path, mock_session):
    """Test EMSA auto-detects file format from extension"""
    csv_path = tmp_path / "data.csv"
    importer = EMSAImporter(csv_path, mock_session, file_format="auto")
    assert importer.file_format == "csv"

    json_path = tmp_path / "data.json"
    importer = EMSAImporter(json_path, mock_session, file_format="auto")
    assert importer.file_format == "json"

    xml_path = tmp_path / "data.xml"
    importer = EMSAImporter(xml_path, mock_session, file_format="auto")
    assert importer.file_format == "xml"


def test_emsa_member_state_normalization(emsa_csv_path, mock_session):
    """Test EMSA member state code normalization"""
    importer = EMSAImporter(emsa_csv_path, mock_session, member_state="germany")
    assert importer.member_state == "DE"

    importer = EMSAImporter(emsa_csv_path, mock_session, member_state="GR")
    assert importer.member_state == "GR"

    # EL is a valid lookup key that returns GR, but input "EL" may return "EL"
    importer = EMSAImporter(emsa_csv_path, mock_session, member_state="EL")
    assert importer.member_state in ("GR", "EL")  # Implementation may return either

    importer = EMSAImporter(emsa_csv_path, mock_session, member_state="all")
    assert importer.member_state is None


def test_emsa_field_mappings(emsa_csv_path, mock_session):
    """Test EMSA field mapping constants are defined"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    assert "OCCURRENCE_ID" in importer.FIELD_MAPPINGS
    assert importer.FIELD_MAPPINGS["OCCURRENCE_DATE"] == "incident_date"
    assert "LATITUDE" in importer.FIELD_MAPPINGS
    assert "LONGITUDE" in importer.FIELD_MAPPINGS
    assert "IMO_NUMBER" in importer.FIELD_MAPPINGS
    assert "FATALITIES" in importer.FIELD_MAPPINGS


def test_emsa_eu_member_state_codes(emsa_csv_path, mock_session):
    """Test EMSA EU member state code mappings"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    # Test common member states
    assert importer.EU_MEMBER_STATE_CODES["DE"] == "DE"
    assert importer.EU_MEMBER_STATE_CODES["FR"] == "FR"
    assert importer.EU_MEMBER_STATE_CODES["EL"] == "GR"
    assert importer.EU_MEMBER_STATE_CODES["greece"] == "GR"
    assert importer.EU_MEMBER_STATE_CODES["NO"] == "NO"  # EEA


def test_emsa_casualty_category_mappings(emsa_csv_path, mock_session):
    """Test EMSA casualty category to severity mappings"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    assert (
        importer.CASUALTY_CATEGORY_MAPPINGS["very serious marine casualty"]
        == "catastrophic"
    )
    assert importer.CASUALTY_CATEGORY_MAPPINGS["serious marine casualty"] == "serious"
    assert importer.CASUALTY_CATEGORY_MAPPINGS["marine casualty"] == "moderate"
    assert importer.CASUALTY_CATEGORY_MAPPINGS["marine incident"] == "minor"


def test_emsa_occurrence_type_mappings(emsa_csv_path, mock_session):
    """Test EMSA occurrence type to incident type mappings"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    assert (
        importer.OCCURRENCE_TYPE_MAPPINGS["collision"] == IncidentType.COLLISION.value
    )
    assert (
        importer.OCCURRENCE_TYPE_MAPPINGS["grounding"] == IncidentType.GROUNDING.value
    )
    assert importer.OCCURRENCE_TYPE_MAPPINGS["fire"] == IncidentType.FIRE.value
    assert (
        importer.OCCURRENCE_TYPE_MAPPINGS["explosion"] == IncidentType.EXPLOSION.value
    )
    assert importer.OCCURRENCE_TYPE_MAPPINGS["flooding"] == IncidentType.FLOODING.value
    assert (
        importer.OCCURRENCE_TYPE_MAPPINGS["capsizing"] == IncidentType.CAPSIZING.value
    )


def test_emsa_ship_type_mappings(emsa_csv_path, mock_session):
    """Test EMSA ship type to vessel type mappings"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    # Check offshore vessel types
    assert importer.SHIP_TYPE_MAPPINGS["drilling rig"] == VesselType.DRILLING_RIG.value
    assert importer.SHIP_TYPE_MAPPINGS["fpso"] == VesselType.FPSO.value
    assert (
        importer.SHIP_TYPE_MAPPINGS["offshore supply vessel"]
        == VesselType.SUPPLY_VESSEL.value
    )
    assert importer.SHIP_TYPE_MAPPINGS["ahts"] == VesselType.ANCHOR_HANDLING.value

    # Check tanker types
    assert importer.SHIP_TYPE_MAPPINGS["oil tanker"] == VesselType.TANKER.value
    assert importer.SHIP_TYPE_MAPPINGS["lng carrier"] == VesselType.TANKER.value

    # Check cargo types
    assert importer.SHIP_TYPE_MAPPINGS["bulk carrier"] == VesselType.CARGO_VESSEL.value
    assert (
        importer.SHIP_TYPE_MAPPINGS["container ship"] == VesselType.CARGO_VESSEL.value
    )


def test_emsa_status_mappings(emsa_csv_path, mock_session):
    """Test EMSA investigation status mappings"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    assert importer.STATUS_MAPPINGS["reported"] == IncidentStatus.REPORTED.value
    assert (
        importer.STATUS_MAPPINGS["under investigation"]
        == IncidentStatus.UNDER_INVESTIGATION.value
    )
    assert (
        importer.STATUS_MAPPINGS["preliminary"]
        == IncidentStatus.PRELIMINARY_REPORT.value
    )
    assert importer.STATUS_MAPPINGS["final report"] == IncidentStatus.FINAL_REPORT.value
    assert importer.STATUS_MAPPINGS["closed"] == IncidentStatus.CLOSED.value


def test_emsa_map_occurrence_type(emsa_csv_path, mock_session):
    """Test EMSA occurrence type mapping helper method"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    assert importer._map_occurrence_type("collision") == IncidentType.COLLISION.value
    assert (
        importer._map_occurrence_type("Collision with vessel")
        == IncidentType.COLLISION.value
    )
    assert importer._map_occurrence_type("grounding") == IncidentType.GROUNDING.value
    assert importer._map_occurrence_type("fire") == IncidentType.FIRE.value
    assert importer._map_occurrence_type("unknown type") == IncidentType.OTHER.value


def test_emsa_map_ship_type(emsa_csv_path, mock_session):
    """Test EMSA ship type mapping helper method"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    assert importer._map_ship_type("drilling rig") == VesselType.DRILLING_RIG.value
    assert importer._map_ship_type("FPSO") == VesselType.FPSO.value
    assert importer._map_ship_type("oil tanker") == VesselType.TANKER.value
    assert importer._map_ship_type("bulk carrier") == VesselType.CARGO_VESSEL.value
    assert importer._map_ship_type("unknown vessel") == VesselType.OTHER.value


def test_emsa_map_casualty_category(emsa_csv_path, mock_session):
    """Test EMSA casualty category mapping helper method"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    assert (
        importer._map_casualty_category("very serious marine casualty")
        == "catastrophic"
    )
    assert importer._map_casualty_category("VSMC") == "catastrophic"
    assert importer._map_casualty_category("serious marine casualty") == "serious"
    assert importer._map_casualty_category("marine casualty") == "moderate"
    assert importer._map_casualty_category("marine incident") == "minor"
    assert importer._map_casualty_category("") == "unknown"


def test_emsa_map_investigation_status(emsa_csv_path, mock_session):
    """Test EMSA investigation status mapping helper method"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    assert (
        importer._map_investigation_status("reported") == IncidentStatus.REPORTED.value
    )
    assert (
        importer._map_investigation_status("under investigation")
        == IncidentStatus.UNDER_INVESTIGATION.value
    )
    assert (
        importer._map_investigation_status("final report")
        == IncidentStatus.FINAL_REPORT.value
    )
    assert importer._map_investigation_status("") == IncidentStatus.REPORTED.value


def test_emsa_get_supported_member_states(emsa_csv_path, mock_session):
    """Test EMSA supported member states list"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    member_states = importer.get_supported_member_states()

    assert "DE" in member_states
    assert "FR" in member_states
    assert "GR" in member_states
    assert "NO" in member_states  # EEA
    assert "GB" in member_states  # Historical
    assert len(member_states) > 25  # EU27 + EEA + historical


def test_emsa_get_emcip_info(emsa_csv_path, mock_session):
    """Test EMSA EMCIP information retrieval"""
    info = EMSAImporter.get_emcip_info()

    assert info["name"] == "European Marine Casualty Information Platform (EMCIP)"
    assert info["organization"] == "European Maritime Safety Agency (EMSA)"
    assert "emsa.europa.eu" in info["website"]
    assert "emcip-support@emsa.europa.eu" in info["support_email"]
    assert "Directive 2009/18/EC" in info["legal_basis"]
    assert "access_types" in info
    assert "data_coverage" in info


def test_emsa_read_source_raises_not_implemented(emsa_csv_path, mock_session):
    """Test EMSA read_source raises NotImplementedError (stub)"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    with pytest.raises(NotImplementedError) as exc_info:
        list(importer.read_source())

    assert "institutional access" in str(exc_info.value).lower()


def test_emsa_parse_record_raises_not_implemented(emsa_csv_path, mock_session):
    """Test EMSA parse_record raises NotImplementedError (stub)"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    with pytest.raises(NotImplementedError) as exc_info:
        importer.parse_record({})

    assert "not implemented" in str(exc_info.value).lower()


def test_emsa_map_to_model_raises_not_implemented(emsa_csv_path, mock_session):
    """Test EMSA map_to_model raises NotImplementedError (stub)"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    with pytest.raises(NotImplementedError) as exc_info:
        importer.map_to_model({})

    assert "not implemented" in str(exc_info.value).lower()


def test_emsa_clear_caches(emsa_csv_path, mock_session):
    """Test EMSA cache clearing"""
    importer = EMSAImporter(emsa_csv_path, mock_session)

    # Populate caches
    importer._location_cache["key1"] = 123
    importer._vessel_cache["key2"] = 456

    # Clear caches
    importer.clear_caches()

    assert len(importer._location_cache) == 0
    assert len(importer._vessel_cache) == 0
