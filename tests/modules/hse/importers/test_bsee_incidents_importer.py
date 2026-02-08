# ABOUTME: pytest tests for BSEEIncidentsImporter concrete implementation
# ABOUTME: Tests CSV parsing, data normalization, deduplication, and incremental updates

import pytest
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestBSEEIncidentsImporterInterface:
    """Test that BSEEIncidentsImporter properly implements BaseImporter interface"""

    def test_bsee_incidents_importer_can_be_instantiated(self, db_session):
        """Test that BSEEIncidentsImporter concrete class can be instantiated"""
        from worldenergydata.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter

        importer = BSEEIncidentsImporter(db_session)

        assert importer is not None
        assert importer.db_session == db_session

    def test_bsee_incidents_importer_inherits_from_base_importer(self, db_session):
        """Test that BSEEIncidentsImporter inherits from BaseImporter"""
        from worldenergydata.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter
        from worldenergydata.hse.importers.base_importer import BaseImporter

        importer = BSEEIncidentsImporter(db_session)

        assert isinstance(importer, BaseImporter)

    def test_bsee_incidents_importer_implements_fetch_data(self, db_session):
        """Test that BSEEIncidentsImporter implements fetch_data method"""
        from worldenergydata.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter

        importer = BSEEIncidentsImporter(db_session)

        assert hasattr(importer, 'fetch_data')
        assert callable(importer.fetch_data)

    def test_bsee_incidents_importer_implements_normalize_data(self, db_session):
        """Test that BSEEIncidentsImporter implements normalize_data method"""
        from worldenergydata.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter

        importer = BSEEIncidentsImporter(db_session)

        assert hasattr(importer, 'normalize_data')
        assert callable(importer.normalize_data)


class TestCSVParsing:
    """Test CSV parsing functionality from BSEE incident database"""

    @pytest.fixture
    def sample_csv_file(self, tmp_path):
        """Create sample CSV file with BSEE incident data"""
        csv_content = """incident_id,incident_date,operator_name,facility,lease,block,field,lat,lon,incident_type,severity,description
INC-2024-001,2024-01-15,Shell Offshore Inc.,Platform A,GC-123,Green Canyon 123,Mars Field,28.5,-89.2,injury,recordable,Worker injured during crane operation
INC-2024-002,2024-02-20,BP America,Platform B,MC-456,Mississippi Canyon 456,Thunder Horse,28.8,-88.5,spill,minor,Small hydraulic fluid spill contained
INC-2024-003,2024-03-10,Chevron USA,MODU Charlie,WR-789,Walker Ridge 789,Jack/St. Malo,27.2,-90.1,equipment_failure,near_miss,BOP component failure detected during test"""

        csv_file = tmp_path / "bsee_incidents.csv"
        csv_file.write_text(csv_content)
        return csv_file

    @pytest.fixture
    def importer_with_csv(self, db_session, sample_csv_file):
        """Create importer configured to read from sample CSV"""
        from worldenergydata.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter

        importer = BSEEIncidentsImporter(db_session, csv_file_path=sample_csv_file)
        return importer

    def test_fetch_data_reads_csv_file(self, importer_with_csv):
        """Test that fetch_data successfully reads CSV file"""
        raw_data = importer_with_csv.fetch_data()

        assert raw_data is not None
        assert isinstance(raw_data, list)
        assert len(raw_data) == 3

    def test_fetch_data_returns_dictionaries(self, importer_with_csv):
        """Test that fetch_data returns list of dictionaries"""
        raw_data = importer_with_csv.fetch_data()

        assert all(isinstance(record, dict) for record in raw_data)

    def test_fetch_data_preserves_all_columns(self, importer_with_csv):
        """Test that fetch_data preserves all CSV columns"""
        raw_data = importer_with_csv.fetch_data()

        expected_columns = [
            'incident_id', 'incident_date', 'operator_name', 'facility',
            'lease', 'block', 'field', 'lat', 'lon', 'incident_type',
            'severity', 'description'
        ]

        for record in raw_data:
            for column in expected_columns:
                assert column in record

    def test_fetch_data_handles_missing_file(self, db_session, tmp_path):
        """Test that fetch_data raises error for missing CSV file"""
        from worldenergydata.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter

        missing_file = tmp_path / "nonexistent.csv"
        importer = BSEEIncidentsImporter(db_session, csv_file_path=missing_file)

        with pytest.raises(FileNotFoundError):
            importer.fetch_data()

    def test_fetch_data_handles_empty_csv(self, db_session, tmp_path):
        """Test that fetch_data handles empty CSV file"""
        from worldenergydata.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter

        empty_csv = tmp_path / "empty.csv"
        empty_csv.write_text("incident_id,incident_date,operator_name\n")

        importer = BSEEIncidentsImporter(db_session, csv_file_path=empty_csv)
        raw_data = importer.fetch_data()

        assert raw_data == []


class TestDataNormalization:
    """Test data normalization from BSEE CSV format to database schema"""

    @pytest.fixture
    def importer(self, db_session):
        """Create BSEEIncidentsImporter instance"""
        from worldenergydata.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter
        return BSEEIncidentsImporter(db_session)

    def test_normalize_data_converts_incident_id_field(self, importer):
        """Test that incident_id is normalized to bsee_incident_id"""
        raw_data = {
            'incident_id': 'INC-2024-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'facility': 'Platform A',
            'lease': 'GC-123',
            'block': 'Green Canyon 123',
            'field': 'Mars Field',
            'lat': '28.5',
            'lon': '-89.2',
            'incident_type': 'injury',
            'severity': 'recordable',
            'description': 'Worker injured during crane operation'
        }

        normalized = importer.normalize_data(raw_data)

        assert 'bsee_incident_id' in normalized
        assert normalized['bsee_incident_id'] == 'INC-2024-001'

    def test_normalize_data_converts_date_string_to_datetime(self, importer):
        """Test that incident_date string is converted to datetime object"""
        raw_data = {
            'incident_id': 'INC-2024-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'incident_type': 'injury',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert 'incident_date' in normalized
        assert isinstance(normalized['incident_date'], datetime)
        assert normalized['incident_date'] == datetime(2024, 1, 15)

    def test_normalize_data_handles_datetime_with_time(self, importer):
        """Test that incident_date with time is parsed correctly"""
        raw_data = {
            'incident_id': 'INC-2024-001',
            'incident_date': '2024-01-15 14:30:00',
            'operator_name': 'Shell Offshore Inc.',
            'incident_type': 'injury',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert normalized['incident_date'] == datetime(2024, 1, 15, 14, 30, 0)

    def test_normalize_data_converts_operator_name_to_operator(self, importer):
        """Test that operator_name is normalized to operator"""
        raw_data = {
            'incident_id': 'INC-2024-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'incident_type': 'injury',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert 'operator' in normalized
        assert normalized['operator'] == 'Shell Offshore Inc.'

    def test_normalize_data_converts_facility_to_facility_name(self, importer):
        """Test that facility is normalized to facility_name"""
        raw_data = {
            'incident_id': 'INC-2024-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'facility': 'Platform A',
            'incident_type': 'injury',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert 'facility_name' in normalized
        assert normalized['facility_name'] == 'Platform A'

    def test_normalize_data_converts_lat_lon_to_float(self, importer):
        """Test that lat/lon strings are converted to float"""
        raw_data = {
            'incident_id': 'INC-2024-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'lat': '28.5',
            'lon': '-89.2',
            'incident_type': 'injury',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert 'latitude' in normalized
        assert 'longitude' in normalized
        assert isinstance(normalized['latitude'], float)
        assert isinstance(normalized['longitude'], float)
        assert normalized['latitude'] == 28.5
        assert normalized['longitude'] == -89.2

    def test_normalize_data_handles_missing_optional_fields(self, importer):
        """Test that missing optional fields are handled gracefully"""
        raw_data = {
            'incident_id': 'INC-2024-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'incident_type': 'injury',
            'severity': 'recordable'
            # Missing: facility, lease, block, field, lat, lon, description
        }

        normalized = importer.normalize_data(raw_data)

        assert 'bsee_incident_id' in normalized
        assert 'incident_date' in normalized
        assert 'operator' in normalized
        assert normalized.get('facility_name') is None
        assert normalized.get('latitude') is None

    def test_normalize_data_converts_lease_to_lease_number(self, importer):
        """Test that lease is normalized to lease_number"""
        raw_data = {
            'incident_id': 'INC-2024-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'lease': 'GC-123',
            'incident_type': 'injury',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert 'lease_number' in normalized
        assert normalized['lease_number'] == 'GC-123'

    def test_normalize_data_converts_block_to_block_number(self, importer):
        """Test that block is normalized to block_number"""
        raw_data = {
            'incident_id': 'INC-2024-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'block': 'Green Canyon 123',
            'incident_type': 'injury',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert 'block_number' in normalized
        assert normalized['block_number'] == 'Green Canyon 123'

    def test_normalize_data_converts_field_to_field_name(self, importer):
        """Test that field is normalized to field_name"""
        raw_data = {
            'incident_id': 'INC-2024-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'field': 'Mars Field',
            'incident_type': 'injury',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert 'field_name' in normalized
        assert normalized['field_name'] == 'Mars Field'


class TestDeduplication:
    """Test deduplication logic for BSEE incidents"""

    @pytest.fixture
    def importer_with_csv(self, db_session, tmp_path):
        """Create importer with CSV containing duplicate incident IDs"""
        csv_content = """incident_id,incident_date,operator_name,incident_type,severity
INC-2024-001,2024-01-15,Shell Offshore Inc.,injury,recordable
INC-2024-002,2024-02-20,BP America,spill,minor
INC-2024-001,2024-01-15,Shell Offshore Inc.,injury,recordable"""

        csv_file = tmp_path / "bsee_incidents_with_dupes.csv"
        csv_file.write_text(csv_content)

        from worldenergydata.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter
        return BSEEIncidentsImporter(db_session, csv_file_path=csv_file)

    def test_import_data_detects_duplicates_in_csv(self, importer_with_csv, db_session):
        """Test that import_data detects duplicate incident IDs in CSV"""
        from worldenergydata.hse.database.models import HSEIncident

        # First import
        stats = importer_with_csv.import_data()

        # Should import 2 unique records, skip 1 duplicate
        assert stats['imported_count'] == 2
        assert stats['skipped_count'] == 1
        assert stats['total_records'] == 3

    def test_import_data_detects_duplicates_in_database(self, db_session, tmp_path):
        """Test that import_data detects duplicates already in database"""
        from worldenergydata.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter
        from worldenergydata.hse.database.models import HSEIncident

        # Create existing incident in database
        existing = HSEIncident(
            bsee_incident_id='INC-2024-001',
            incident_date=datetime(2024, 1, 15),
            operator='Shell Offshore Inc.',
            incident_type='injury',
            severity='recordable'
        )
        db_session.add(existing)
        db_session.commit()

        # Create CSV with same incident ID
        csv_content = """incident_id,incident_date,operator_name,incident_type,severity
INC-2024-001,2024-01-15,Shell Offshore Inc.,injury,recordable
INC-2024-002,2024-02-20,BP America,spill,minor"""

        csv_file = tmp_path / "bsee_incidents.csv"
        csv_file.write_text(csv_content)

        importer = BSEEIncidentsImporter(db_session, csv_file_path=csv_file)
        stats = importer.import_data()

        # Should import 1 new record, skip 1 duplicate
        assert stats['imported_count'] == 1
        assert stats['skipped_count'] == 1
        assert stats['total_records'] == 2


class TestIncrementalUpdates:
    """Test incremental update detection for BSEE incidents"""

    def test_import_data_identifies_new_incidents(self, db_session, tmp_path):
        """Test that import_data correctly identifies new incidents"""
        from worldenergydata.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter
        from worldenergydata.hse.database.models import HSEIncident

        # First import with 2 incidents
        csv_content_1 = """incident_id,incident_date,operator_name,incident_type,severity
INC-2024-001,2024-01-15,Shell Offshore Inc.,injury,recordable
INC-2024-002,2024-02-20,BP America,spill,minor"""

        csv_file = tmp_path / "bsee_incidents_1.csv"
        csv_file.write_text(csv_content_1)

        importer = BSEEIncidentsImporter(db_session, csv_file_path=csv_file)
        stats1 = importer.import_data()

        assert stats1['imported_count'] == 2

        # Second import with 1 new + 2 existing incidents
        csv_content_2 = """incident_id,incident_date,operator_name,incident_type,severity
INC-2024-001,2024-01-15,Shell Offshore Inc.,injury,recordable
INC-2024-002,2024-02-20,BP America,spill,minor
INC-2024-003,2024-03-10,Chevron USA,equipment_failure,near_miss"""

        csv_file.write_text(csv_content_2)

        importer2 = BSEEIncidentsImporter(db_session, csv_file_path=csv_file)
        stats2 = importer2.import_data()

        # Should import 1 new, skip 2 existing
        assert stats2['imported_count'] == 1
        assert stats2['skipped_count'] == 2
        assert stats2['total_records'] == 3

    def test_import_data_handles_empty_database(self, db_session, tmp_path):
        """Test that import_data handles initial import to empty database"""
        from worldenergydata.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter
        from worldenergydata.hse.database.models import HSEIncident

        csv_content = """incident_id,incident_date,operator_name,incident_type,severity
INC-2024-001,2024-01-15,Shell Offshore Inc.,injury,recordable
INC-2024-002,2024-02-20,BP America,spill,minor
INC-2024-003,2024-03-10,Chevron USA,equipment_failure,near_miss"""

        csv_file = tmp_path / "bsee_incidents.csv"
        csv_file.write_text(csv_content)

        importer = BSEEIncidentsImporter(db_session, csv_file_path=csv_file)
        stats = importer.import_data()

        # All should be imported as new
        assert stats['imported_count'] == 3
        assert stats['skipped_count'] == 0
        assert stats['total_records'] == 3

        # Verify database contains all records
        count = db_session.query(HSEIncident).count()
        assert count == 3


# Pytest fixtures for database testing
@pytest.fixture
def db_session():
    """Create test database session with in-memory SQLite"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from worldenergydata.hse.database.models import Base

    # Use in-memory SQLite for testing
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
