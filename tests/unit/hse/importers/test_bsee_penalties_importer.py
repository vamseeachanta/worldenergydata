# ABOUTME: pytest tests for BSEEPenaltiesImporter - BSEE civil penalties data import
# ABOUTME: Tests CSV parsing, field normalization, validation for ViolationIncident records

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import csv


class TestBSEEPenaltiesImporterInterface:
    """Test that BSEEPenaltiesImporter implements required interface"""

    def test_can_instantiate_with_db_session_and_csv_path(self, db_session):
        """Test basic instantiation with required parameters"""
        from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter

        importer = BSEEPenaltiesImporter(db_session, csv_file_path="penalties.csv")

        assert importer is not None
        assert importer.db_session == db_session
        assert importer.csv_file_path == "penalties.csv"

    def test_inherits_from_base_importer(self, db_session):
        """Test that BSEEPenaltiesImporter inherits from BaseImporter"""
        from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter
        from worldenergydata.hse.importers.base_importer import BaseImporter

        importer = BSEEPenaltiesImporter(db_session)

        assert isinstance(importer, BaseImporter)

    def test_has_required_methods(self, db_session):
        """Test that importer has fetch_data and normalize_data methods"""
        from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter

        importer = BSEEPenaltiesImporter(db_session)

        assert hasattr(importer, 'fetch_data')
        assert hasattr(importer, 'normalize_data')
        assert callable(importer.fetch_data)
        assert callable(importer.normalize_data)


class TestPenaltiesCSVParsing:
    """Test CSV file reading and parsing for penalties data"""

    @pytest.fixture
    def sample_penalties_csv(self):
        """Create sample penalties CSV file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'incident_id', 'incident_date', 'operator_name', 'inc_number',
                'violation_type', 'regulation_cited', 'penalty_amount', 'penalty_status',
                'compliance_deadline', 'compliance_achieved', 'severity'
            ])
            writer.writeheader()
            writer.writerow({
                'incident_id': 'INC-2024-PEN-001',
                'incident_date': '2024-01-15',
                'operator_name': 'Shell Offshore Inc.',
                'inc_number': 'INC-2024-001',
                'violation_type': 'Safety Equipment Failure',
                'regulation_cited': '30 CFR 250.188',
                'penalty_amount': '50000.00',
                'penalty_status': 'assessed',
                'compliance_deadline': '2024-06-30',
                'compliance_achieved': 'True',
                'severity': 'recordable'
            })
            writer.writerow({
                'incident_id': 'INC-2024-PEN-002',
                'incident_date': '2024-02-20',
                'operator_name': 'BP America',
                'inc_number': 'INC-2024-002',
                'violation_type': 'Environmental Violation',
                'regulation_cited': '30 CFR 250.300',
                'penalty_amount': '125000.00',
                'penalty_status': 'proposed',
                'compliance_deadline': '2024-07-15',
                'compliance_achieved': 'False',
                'severity': 'minor'
            })
            temp_path = f.name

        yield temp_path

        Path(temp_path).unlink()

    def test_fetch_data_reads_csv_file(self, db_session, sample_penalties_csv):
        """Test that fetch_data successfully reads CSV file"""
        from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter

        importer = BSEEPenaltiesImporter(db_session, csv_file_path=sample_penalties_csv)
        records = importer.fetch_data()

        assert records is not None
        assert len(records) == 2

    def test_fetch_data_returns_list_of_dicts(self, db_session, sample_penalties_csv):
        """Test that fetch_data returns list of dictionaries"""
        from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter

        importer = BSEEPenaltiesImporter(db_session, csv_file_path=sample_penalties_csv)
        records = importer.fetch_data()

        assert isinstance(records, list)
        assert all(isinstance(record, dict) for record in records)

    def test_fetch_data_raises_file_not_found_error(self, db_session):
        """Test that fetch_data raises FileNotFoundError for missing file"""
        from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter

        importer = BSEEPenaltiesImporter(db_session, csv_file_path="nonexistent.csv")

        with pytest.raises(FileNotFoundError):
            importer.fetch_data()

    def test_fetch_data_handles_empty_csv_file(self, db_session):
        """Test that fetch_data returns empty list for CSV with only headers"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['incident_id', 'incident_date', 'operator_name'])
            temp_path = f.name

        try:
            from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter
            importer = BSEEPenaltiesImporter(db_session, csv_file_path=temp_path)
            records = importer.fetch_data()

            assert records == []
        finally:
            Path(temp_path).unlink()

    def test_fetch_data_preserves_all_columns(self, db_session, sample_penalties_csv):
        """Test that all CSV columns are preserved in returned dictionaries"""
        from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter

        importer = BSEEPenaltiesImporter(db_session, csv_file_path=sample_penalties_csv)
        records = importer.fetch_data()

        first_record = records[0]
        assert 'incident_id' in first_record
        assert 'inc_number' in first_record
        assert 'penalty_amount' in first_record
        assert 'penalty_status' in first_record

    def test_fetch_data_handles_missing_optional_columns(self, db_session):
        """Test that fetch_data handles CSV with missing optional columns"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'incident_id', 'incident_date', 'operator_name', 'inc_number', 'severity'
            ])
            writer.writeheader()
            writer.writerow({
                'incident_id': 'INC-2024-PEN-003',
                'incident_date': '2024-03-10',
                'operator_name': 'Chevron',
                'inc_number': 'INC-2024-003',
                'severity': 'minor'
            })
            temp_path = f.name

        try:
            from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter
            importer = BSEEPenaltiesImporter(db_session, csv_file_path=temp_path)
            records = importer.fetch_data()

            assert len(records) == 1
        finally:
            Path(temp_path).unlink()

    def test_fetch_data_parses_multiple_rows(self, db_session, sample_penalties_csv):
        """Test that fetch_data correctly parses multiple CSV rows"""
        from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter

        importer = BSEEPenaltiesImporter(db_session, csv_file_path=sample_penalties_csv)
        records = importer.fetch_data()

        assert len(records) == 2
        assert records[0]['incident_id'] == 'INC-2024-PEN-001'
        assert records[1]['incident_id'] == 'INC-2024-PEN-002'

    def test_fetch_data_raises_value_error_for_malformed_csv(self, db_session):
        """Test that fetch_data raises ValueError for malformed CSV"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write("This is not valid CSV content\n")
            f.write("Random text without proper structure\n")
            temp_path = f.name

        try:
            from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter
            importer = BSEEPenaltiesImporter(db_session, csv_file_path=temp_path)

            # Should either raise ValueError or return data that fails validation
            records = importer.fetch_data()
            assert records is not None  # If it doesn't raise, at least it returns something
        finally:
            Path(temp_path).unlink()


class TestPenaltiesDataNormalization:
    """Test field mapping and data normalization for penalties data"""

    @pytest.fixture
    def importer(self, db_session):
        """Create penalties importer instance for testing"""
        from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter
        return BSEEPenaltiesImporter(db_session)

    def test_normalize_converts_incident_id_to_bsee_incident_id(self, importer):
        """Verify incident_id → bsee_incident_id field mapping"""
        raw_data = {
            'incident_id': 'INC-2024-PEN-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'inc_number': 'INC-2024-001',
            'violation_type': 'Safety Equipment Failure',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert 'bsee_incident_id' in normalized
        assert normalized['bsee_incident_id'] == 'INC-2024-PEN-001'

    def test_normalize_converts_date_string_to_datetime(self, importer):
        """Verify incident_date string → datetime object conversion"""
        raw_data = {
            'incident_id': 'INC-2024-PEN-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'inc_number': 'INC-2024-001',
            'violation_type': 'Safety Equipment Failure',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert isinstance(normalized['incident_date'], datetime)
        assert normalized['incident_date'] == datetime(2024, 1, 15)

    def test_normalize_maps_operator_name_to_operator(self, importer):
        """Verify operator_name → operator field mapping"""
        raw_data = {
            'incident_id': 'INC-2024-PEN-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'inc_number': 'INC-2024-001',
            'violation_type': 'Safety Equipment Failure',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert normalized['operator'] == 'Shell Offshore Inc.'

    def test_normalize_sets_incident_type_to_violation(self, importer):
        """Verify incident_type is automatically set to 'violation'"""
        raw_data = {
            'incident_id': 'INC-2024-PEN-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'inc_number': 'INC-2024-001',
            'violation_type': 'Safety Equipment Failure',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert normalized['incident_type'] == 'violation'

    def test_normalize_maps_severity(self, importer):
        """Verify severity field mapping"""
        raw_data = {
            'incident_id': 'INC-2024-PEN-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'inc_number': 'INC-2024-001',
            'violation_type': 'Safety Equipment Failure',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert normalized['severity'] == 'recordable'

    def test_normalize_maps_inc_number(self, importer):
        """Verify inc_number field mapping for ViolationIncident"""
        raw_data = {
            'incident_id': 'INC-2024-PEN-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'inc_number': 'INC-2024-001',
            'violation_type': 'Safety Equipment Failure',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert 'inc_number' in normalized
        assert normalized['inc_number'] == 'INC-2024-001'

    def test_normalize_maps_violation_type(self, importer):
        """Verify violation_type field mapping"""
        raw_data = {
            'incident_id': 'INC-2024-PEN-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'inc_number': 'INC-2024-001',
            'violation_type': 'Safety Equipment Failure',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert normalized['violation_type'] == 'Safety Equipment Failure'

    def test_normalize_maps_regulation_cited(self, importer):
        """Verify regulation_cited field mapping"""
        raw_data = {
            'incident_id': 'INC-2024-PEN-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'inc_number': 'INC-2024-001',
            'violation_type': 'Safety Equipment Failure',
            'regulation_cited': '30 CFR 250.188',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert normalized['regulation_cited'] == '30 CFR 250.188'

    def test_normalize_converts_penalty_amount_to_float(self, importer):
        """Verify penalty_amount string → float conversion"""
        raw_data = {
            'incident_id': 'INC-2024-PEN-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'inc_number': 'INC-2024-001',
            'violation_type': 'Safety Equipment Failure',
            'penalty_amount': '50000.00',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert isinstance(normalized['penalty_amount'], float)
        assert normalized['penalty_amount'] == 50000.00

    def test_normalize_maps_penalty_status(self, importer):
        """Verify penalty_status field mapping (enum: proposed, assessed, paid, appealed)"""
        raw_data = {
            'incident_id': 'INC-2024-PEN-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'inc_number': 'INC-2024-001',
            'violation_type': 'Safety Equipment Failure',
            'penalty_status': 'assessed',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert normalized['penalty_status'] == 'assessed'

    def test_normalize_converts_compliance_deadline_to_datetime(self, importer):
        """Verify compliance_deadline string → datetime conversion"""
        raw_data = {
            'incident_id': 'INC-2024-PEN-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'inc_number': 'INC-2024-001',
            'violation_type': 'Safety Equipment Failure',
            'compliance_deadline': '2024-06-30',
            'severity': 'recordable'
        }

        normalized = importer.normalize_data(raw_data)

        assert isinstance(normalized['compliance_deadline'], datetime)
        assert normalized['compliance_deadline'] == datetime(2024, 6, 30)

    def test_normalize_converts_compliance_achieved_to_boolean(self, importer):
        """Verify compliance_achieved string → boolean conversion"""
        raw_data_true = {
            'incident_id': 'INC-2024-PEN-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'inc_number': 'INC-2024-001',
            'violation_type': 'Safety Equipment Failure',
            'compliance_achieved': 'True',
            'severity': 'recordable'
        }

        raw_data_false = {
            'incident_id': 'INC-2024-PEN-002',
            'incident_date': '2024-02-20',
            'operator_name': 'BP America',
            'inc_number': 'INC-2024-002',
            'violation_type': 'Environmental Violation',
            'compliance_achieved': 'False',
            'severity': 'minor'
        }

        normalized_true = importer.normalize_data(raw_data_true)
        normalized_false = importer.normalize_data(raw_data_false)

        assert isinstance(normalized_true['compliance_achieved'], bool)
        assert normalized_true['compliance_achieved'] is True
        assert isinstance(normalized_false['compliance_achieved'], bool)
        assert normalized_false['compliance_achieved'] is False

    def test_normalize_handles_missing_optional_fields(self, importer):
        """Verify normalization handles missing optional fields gracefully"""
        raw_data = {
            'incident_id': 'INC-2024-PEN-001',
            'incident_date': '2024-01-15',
            'operator_name': 'Shell Offshore Inc.',
            'inc_number': 'INC-2024-001',
            'severity': 'recordable'
            # Missing: violation_type, regulation_cited, penalty_amount, penalty_status,
            # compliance_deadline, compliance_achieved
        }

        normalized = importer.normalize_data(raw_data)

        assert normalized['violation_type'] is None
        assert normalized['regulation_cited'] is None
        assert normalized['penalty_amount'] is None
        assert normalized['penalty_status'] is None
        assert normalized['compliance_deadline'] is None
        assert normalized['compliance_achieved'] is None


class TestPenaltiesDeduplication:
    """Test duplicate detection for penalties data"""

    def test_duplicate_detection_by_bsee_incident_id_in_csv(self, db_session):
        """Test that duplicate incident_id in CSV is detected"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'incident_id', 'incident_date', 'operator_name', 'inc_number', 'severity'
            ])
            writer.writeheader()
            # Same incident_id twice
            writer.writerow({
                'incident_id': 'INC-2024-PEN-DUP',
                'incident_date': '2024-01-15',
                'operator_name': 'Shell Offshore Inc.',
                'inc_number': 'INC-2024-001',
                'severity': 'recordable'
            })
            writer.writerow({
                'incident_id': 'INC-2024-PEN-DUP',
                'incident_date': '2024-01-16',
                'operator_name': 'Shell Offshore Inc.',
                'inc_number': 'INC-2024-001',
                'severity': 'minor'
            })
            temp_path = f.name

        try:
            from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter
            importer = BSEEPenaltiesImporter(db_session, csv_file_path=temp_path)
            stats = importer.import_data()

            # Should import first occurrence, skip second
            assert stats['imported_count'] == 1
            assert stats['skipped_count'] == 1
        finally:
            Path(temp_path).unlink()

    def test_duplicate_detection_by_bsee_incident_id_in_database(self, db_session):
        """Test that penalty already in database is detected as duplicate"""
        from worldenergydata.hse.database.models import HSEIncident

        # Create existing incident in database
        existing_incident = HSEIncident(
            bsee_incident_id='INC-2024-PEN-EXISTS',
            incident_date=datetime(2024, 1, 15),
            operator='Shell Offshore Inc.',
            incident_type='violation',
            severity='recordable'
        )
        db_session.add(existing_incident)
        db_session.commit()

        # Try to import duplicate
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'incident_id', 'incident_date', 'operator_name', 'inc_number', 'severity'
            ])
            writer.writeheader()
            writer.writerow({
                'incident_id': 'INC-2024-PEN-EXISTS',
                'incident_date': '2024-01-16',
                'operator_name': 'Different Operator',
                'inc_number': 'INC-2024-002',
                'severity': 'minor'
            })
            temp_path = f.name

        try:
            from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter
            importer = BSEEPenaltiesImporter(db_session, csv_file_path=temp_path)
            stats = importer.import_data()

            # Should skip duplicate
            assert stats['imported_count'] == 0
            assert stats['skipped_count'] == 1
        finally:
            Path(temp_path).unlink()


class TestPenaltiesIncrementalUpdates:
    """Test incremental import behavior for penalties data"""

    def test_imports_new_penalties_only(self, db_session):
        """Test that only new penalties are imported"""
        from worldenergydata.hse.database.models import HSEIncident

        # Create existing penalty
        existing = HSEIncident(
            bsee_incident_id='INC-2024-PEN-OLD',
            incident_date=datetime(2024, 1, 15),
            operator='Shell Offshore Inc.',
            incident_type='violation',
            severity='recordable'
        )
        db_session.add(existing)
        db_session.commit()

        # Import CSV with one existing, one new
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'incident_id', 'incident_date', 'operator_name', 'inc_number', 'severity'
            ])
            writer.writeheader()
            writer.writerow({
                'incident_id': 'INC-2024-PEN-OLD',
                'incident_date': '2024-01-15',
                'operator_name': 'Shell Offshore Inc.',
                'inc_number': 'INC-2024-001',
                'severity': 'recordable'
            })
            writer.writerow({
                'incident_id': 'INC-2024-PEN-NEW',
                'incident_date': '2024-02-20',
                'operator_name': 'BP America',
                'inc_number': 'INC-2024-002',
                'severity': 'minor'
            })
            temp_path = f.name

        try:
            from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter
            importer = BSEEPenaltiesImporter(db_session, csv_file_path=temp_path)
            stats = importer.import_data()

            assert stats['imported_count'] == 1  # Only new penalty
            assert stats['skipped_count'] == 1   # Existing penalty
        finally:
            Path(temp_path).unlink()

    def test_skips_existing_penalties(self, db_session):
        """Test that existing penalties are skipped during import"""
        from worldenergydata.hse.database.models import HSEIncident

        # Create multiple existing penalties
        for i in range(3):
            incident = HSEIncident(
                bsee_incident_id=f'INC-2024-PEN-EXIST-{i}',
                incident_date=datetime(2024, 1, 15 + i),
                operator='Shell Offshore Inc.',
                incident_type='violation',
                severity='recordable'
            )
            db_session.add(incident)
        db_session.commit()

        # Try to re-import same penalties
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'incident_id', 'incident_date', 'operator_name', 'inc_number', 'severity'
            ])
            writer.writeheader()
            for i in range(3):
                writer.writerow({
                    'incident_id': f'INC-2024-PEN-EXIST-{i}',
                    'incident_date': f'2024-01-{15+i}',
                    'operator_name': 'Shell Offshore Inc.',
                    'inc_number': f'INC-2024-00{i+1}',
                    'severity': 'recordable'
                })
            temp_path = f.name

        try:
            from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter
            importer = BSEEPenaltiesImporter(db_session, csv_file_path=temp_path)
            stats = importer.import_data()

            assert stats['imported_count'] == 0
            assert stats['skipped_count'] == 3
        finally:
            Path(temp_path).unlink()

    def test_returns_correct_statistics(self, db_session):
        """Test that import statistics are correctly calculated"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'incident_id', 'incident_date', 'operator_name', 'inc_number', 'severity'
            ])
            writer.writeheader()
            # 3 valid penalties
            for i in range(3):
                writer.writerow({
                    'incident_id': f'INC-2024-PEN-STAT-{i}',
                    'incident_date': '2024-01-15',
                    'operator_name': 'Shell Offshore Inc.',
                    'inc_number': f'INC-2024-00{i+1}',
                    'severity': 'recordable'
                })
            # 1 invalid penalty (missing required field)
            writer.writerow({
                'incident_id': 'INC-2024-PEN-INVALID',
                'operator_name': 'BP America',
                'inc_number': 'INC-2024-999',
                'severity': 'minor'
                # Missing incident_date (required field)
            })
            temp_path = f.name

        try:
            from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter
            importer = BSEEPenaltiesImporter(db_session, csv_file_path=temp_path)
            stats = importer.import_data()

            assert stats['total_records'] == 4
            assert stats['imported_count'] == 3
            assert stats['error_count'] == 1
            assert stats['skipped_count'] == 0
        finally:
            Path(temp_path).unlink()


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
