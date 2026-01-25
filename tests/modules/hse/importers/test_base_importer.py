# ABOUTME: pytest tests for BaseImporter abstract class and data import framework
# ABOUTME: Tests validation, error handling, duplicate detection, and import statistics

import pytest
from abc import ABC
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestBaseImporterAbstractInterface:
    """Test that BaseImporter enforces abstract interface contract"""

    def test_base_importer_cannot_be_instantiated_directly(self, db_session):
        """Test that BaseImporter abstract class cannot be instantiated"""
        from worldenergydata.modules.hse.importers.base_importer import BaseImporter

        with pytest.raises(TypeError) as exc_info:
            importer = BaseImporter(db_session)

        assert "Can't instantiate abstract class" in str(exc_info.value)

    def test_base_importer_requires_fetch_data_implementation(self, db_session):
        """Test that concrete importer must implement fetch_data() method"""
        from worldenergydata.modules.hse.importers.base_importer import BaseImporter

        class IncompleteImporter(BaseImporter):
            def normalize_data(self, raw_data):
                return raw_data

        with pytest.raises(TypeError) as exc_info:
            importer = IncompleteImporter(db_session)

        assert "fetch_data" in str(exc_info.value)

    def test_base_importer_requires_normalize_data_implementation(self, db_session):
        """Test that concrete importer must implement normalize_data() method"""
        from worldenergydata.modules.hse.importers.base_importer import BaseImporter

        class IncompleteImporter(BaseImporter):
            def fetch_data(self):
                return []

        with pytest.raises(TypeError) as exc_info:
            importer = IncompleteImporter(db_session)

        assert "normalize_data" in str(exc_info.value)

    def test_concrete_importer_with_all_methods_can_be_instantiated(self, db_session):
        """Test that concrete importer with all required methods works"""
        from worldenergydata.modules.hse.importers.base_importer import BaseImporter

        class ConcreteImporter(BaseImporter):
            def fetch_data(self):
                return [{"test": "data"}]

            def normalize_data(self, raw_data):
                return {"normalized": raw_data}

        importer = ConcreteImporter(db_session)

        assert importer is not None
        assert importer.db_session == db_session
        assert isinstance(importer.validation_errors, list)
        assert importer.imported_count == 0
        assert importer.skipped_count == 0


class TestDataValidationFramework:
    """Test data validation logic for required fields, types, and constraints"""

    @pytest.fixture
    def concrete_importer(self, db_session):
        """Create concrete importer for validation testing"""
        from worldenergydata.modules.hse.importers.base_importer import BaseImporter

        class TestImporter(BaseImporter):
            def fetch_data(self):
                return []

            def normalize_data(self, raw_data):
                return raw_data

        return TestImporter(db_session)

    def test_validate_data_with_all_required_fields_returns_true(self, concrete_importer):
        """Test validation passes when all required fields present"""
        valid_data = {
            'bsee_incident_id': 'INC-2024-001',
            'incident_date': datetime(2024, 1, 15),
            'operator': 'Shell Offshore Inc.',
            'incident_type': 'injury',
            'severity': 'recordable'
        }

        result = concrete_importer.validate_data(valid_data)

        assert result is True
        assert len(concrete_importer.validation_errors) == 0

    def test_validate_data_missing_required_field_returns_false(self, concrete_importer):
        """Test validation fails when required field missing"""
        invalid_data = {
            # Missing bsee_incident_id (required)
            'incident_date': datetime(2024, 1, 15),
            'operator': 'Shell Offshore Inc.',
            'incident_type': 'injury',
            'severity': 'recordable'
        }

        result = concrete_importer.validate_data(invalid_data)

        assert result is False
        assert len(concrete_importer.validation_errors) > 0
        assert any('bsee_incident_id' in str(err).lower() for err in concrete_importer.validation_errors)

    def test_validate_data_invalid_incident_type_enum(self, concrete_importer):
        """Test validation fails for invalid incident_type enum value"""
        invalid_data = {
            'bsee_incident_id': 'INC-2024-002',
            'incident_date': datetime(2024, 1, 15),
            'operator': 'Shell Offshore Inc.',
            'incident_type': 'invalid_type',  # Not in enum
            'severity': 'recordable'
        }

        result = concrete_importer.validate_data(invalid_data)

        assert result is False
        assert any('incident_type' in str(err).lower() for err in concrete_importer.validation_errors)

    def test_validate_data_invalid_severity_enum(self, concrete_importer):
        """Test validation fails for invalid severity enum value"""
        invalid_data = {
            'bsee_incident_id': 'INC-2024-003',
            'incident_date': datetime(2024, 1, 15),
            'operator': 'Shell Offshore Inc.',
            'incident_type': 'injury',
            'severity': 'invalid_severity'  # Not in enum
        }

        result = concrete_importer.validate_data(invalid_data)

        assert result is False
        assert any('severity' in str(err).lower() for err in concrete_importer.validation_errors)

    def test_validate_data_latitude_outside_gom_range(self, concrete_importer):
        """Test validation fails for latitude outside Gulf of Mexico boundaries"""
        invalid_data = {
            'bsee_incident_id': 'INC-2024-004',
            'incident_date': datetime(2024, 1, 15),
            'operator': 'Shell Offshore Inc.',
            'incident_type': 'spill',
            'severity': 'minor',
            'latitude': 35.0,  # Outside GOM range (18-31)
            'longitude': -89.0
        }

        result = concrete_importer.validate_data(invalid_data)

        assert result is False
        assert any('latitude' in str(err).lower() for err in concrete_importer.validation_errors)

    def test_validate_data_longitude_outside_gom_range(self, concrete_importer):
        """Test validation fails for longitude outside Gulf of Mexico boundaries"""
        invalid_data = {
            'bsee_incident_id': 'INC-2024-005',
            'incident_date': datetime(2024, 1, 15),
            'operator': 'Shell Offshore Inc.',
            'incident_type': 'spill',
            'severity': 'minor',
            'latitude': 28.0,
            'longitude': -75.0  # Outside GOM range (-98 to -80)
        }

        result = concrete_importer.validate_data(invalid_data)

        assert result is False
        assert any('longitude' in str(err).lower() for err in concrete_importer.validation_errors)

    def test_validate_data_invalid_date_type(self, concrete_importer):
        """Test validation fails when incident_date is not datetime object"""
        invalid_data = {
            'bsee_incident_id': 'INC-2024-006',
            'incident_date': '2024-01-15',  # String instead of datetime
            'operator': 'Shell Offshore Inc.',
            'incident_type': 'injury',
            'severity': 'recordable'
        }

        result = concrete_importer.validate_data(invalid_data)

        assert result is False
        assert any('incident_date' in str(err).lower() for err in concrete_importer.validation_errors)


class TestErrorHandlingForMalformedData:
    """Test error handling for various malformed data scenarios"""

    @pytest.fixture
    def concrete_importer(self, db_session):
        """Create concrete importer for error handling testing"""
        from worldenergydata.modules.hse.importers.base_importer import BaseImporter

        class TestImporter(BaseImporter):
            def fetch_data(self):
                return []

            def normalize_data(self, raw_data):
                return raw_data

        return TestImporter(db_session)

    def test_error_handling_for_none_data(self, concrete_importer):
        """Test graceful handling when data is None"""
        result = concrete_importer.validate_data(None)

        assert result is False
        assert len(concrete_importer.validation_errors) > 0

    def test_error_handling_for_empty_dict(self, concrete_importer):
        """Test error handling when data is empty dictionary"""
        result = concrete_importer.validate_data({})

        assert result is False
        assert len(concrete_importer.validation_errors) > 0
        # Should report all required fields missing

    def test_error_handling_for_wrong_data_type(self, concrete_importer):
        """Test error handling when data is wrong type (list instead of dict)"""
        result = concrete_importer.validate_data([1, 2, 3])

        assert result is False
        assert len(concrete_importer.validation_errors) > 0

    def test_error_accumulation_across_multiple_validations(self, concrete_importer):
        """Test that validation errors accumulate across multiple calls"""
        # First validation with error
        concrete_importer.validate_data({'invalid': 'data'})
        first_error_count = len(concrete_importer.validation_errors)

        # Second validation with error
        concrete_importer.validate_data({'another': 'invalid'})
        second_error_count = len(concrete_importer.validation_errors)

        assert second_error_count > first_error_count

    def test_clear_validation_errors_method(self, concrete_importer):
        """Test that validation errors can be cleared"""
        # Generate some errors
        concrete_importer.validate_data({'invalid': 'data'})
        assert len(concrete_importer.validation_errors) > 0

        # Clear errors
        concrete_importer.clear_errors()

        assert len(concrete_importer.validation_errors) == 0


class TestDuplicateDetectionAndSkipping:
    """Test duplicate incident detection and skipping logic"""

    @pytest.fixture
    def concrete_importer(self, db_session):
        """Create concrete importer for duplicate testing"""
        from worldenergydata.modules.hse.importers.base_importer import BaseImporter

        class TestImporter(BaseImporter):
            def fetch_data(self):
                return []

            def normalize_data(self, raw_data):
                return raw_data

        return TestImporter(db_session)

    def test_duplicate_detection_by_bsee_incident_id(self, concrete_importer, db_session):
        """Test that duplicate bsee_incident_id is detected"""
        from worldenergydata.modules.hse.database.models import HSEIncident

        # Create existing incident in database
        existing_incident = HSEIncident(
            bsee_incident_id='INC-2024-DUPLICATE',
            incident_date=datetime(2024, 1, 15),
            operator='Shell Offshore Inc.',
            incident_type='injury',
            severity='recordable'
        )
        db_session.add(existing_incident)
        db_session.commit()

        # Test duplicate detection
        new_data = {
            'bsee_incident_id': 'INC-2024-DUPLICATE',  # Same ID
            'incident_date': datetime(2024, 1, 16),  # Different date
            'operator': 'BP America',  # Different operator
            'incident_type': 'spill',
            'severity': 'minor'
        }

        is_duplicate = concrete_importer.is_duplicate(new_data)

        assert is_duplicate is True

    def test_non_duplicate_detection(self, concrete_importer, db_session):
        """Test that unique bsee_incident_id is not flagged as duplicate"""
        from worldenergydata.modules.hse.database.models import HSEIncident

        # Create existing incident
        existing_incident = HSEIncident(
            bsee_incident_id='INC-2024-EXISTING',
            incident_date=datetime(2024, 1, 15),
            operator='Shell Offshore Inc.',
            incident_type='injury',
            severity='recordable'
        )
        db_session.add(existing_incident)
        db_session.commit()

        # Test with different ID
        new_data = {
            'bsee_incident_id': 'INC-2024-NEW',  # Unique ID
            'incident_date': datetime(2024, 1, 16),
            'operator': 'Shell Offshore Inc.',
            'incident_type': 'injury',
            'severity': 'recordable'
        }

        is_duplicate = concrete_importer.is_duplicate(new_data)

        assert is_duplicate is False

    def test_skipped_count_increments_on_duplicate(self, concrete_importer, db_session):
        """Test that skipped_count increments when duplicate detected"""
        from worldenergydata.modules.hse.database.models import HSEIncident

        # Create existing incident
        existing = HSEIncident(
            bsee_incident_id='INC-2024-SKIP',
            incident_date=datetime(2024, 1, 15),
            operator='Shell Offshore Inc.',
            incident_type='injury',
            severity='recordable'
        )
        db_session.add(existing)
        db_session.commit()

        initial_skipped = concrete_importer.skipped_count

        # Attempt to import duplicate
        duplicate_data = {
            'bsee_incident_id': 'INC-2024-SKIP',
            'incident_date': datetime(2024, 1, 16),
            'operator': 'BP America',
            'incident_type': 'spill',
            'severity': 'minor'
        }

        concrete_importer.skip_duplicate(duplicate_data)

        assert concrete_importer.skipped_count == initial_skipped + 1


class TestImportStatisticsTracking:
    """Test import statistics tracking (imported_count, skipped_count, validation_errors)"""

    @pytest.fixture
    def concrete_importer(self, db_session):
        """Create concrete importer for statistics testing"""
        from worldenergydata.modules.hse.importers.base_importer import BaseImporter

        class TestImporter(BaseImporter):
            def fetch_data(self):
                return [
                    {
                        'bsee_incident_id': 'INC-STATS-001',
                        'incident_date': '2024-01-15',
                        'operator': 'Shell Offshore Inc.',
                        'incident_type': 'injury',
                        'severity': 'recordable'
                    },
                    {
                        'bsee_incident_id': 'INC-STATS-002',
                        'incident_date': '2024-01-16',
                        'operator': 'BP America',
                        'incident_type': 'spill',
                        'severity': 'minor'
                    },
                    {
                        # Invalid data (missing required fields)
                        'bsee_incident_id': 'INC-STATS-INVALID'
                    }
                ]

            def normalize_data(self, raw_data):
                # Convert string dates to datetime
                if 'incident_date' in raw_data and isinstance(raw_data['incident_date'], str):
                    raw_data['incident_date'] = datetime.strptime(raw_data['incident_date'], '%Y-%m-%d')
                return raw_data

        return TestImporter(db_session)

    def test_initial_statistics_are_zero(self, concrete_importer):
        """Test that importer starts with zero statistics"""
        assert concrete_importer.imported_count == 0
        assert concrete_importer.skipped_count == 0
        assert len(concrete_importer.validation_errors) == 0

    def test_imported_count_increments_on_successful_import(self, concrete_importer):
        """Test that imported_count increments after successful import"""
        valid_data = {
            'bsee_incident_id': 'INC-2024-IMPORT',
            'incident_date': datetime(2024, 1, 15),
            'operator': 'Shell Offshore Inc.',
            'incident_type': 'injury',
            'severity': 'recordable'
        }

        initial_count = concrete_importer.imported_count

        concrete_importer.import_record(valid_data)

        assert concrete_importer.imported_count == initial_count + 1

    def test_validation_errors_list_populated_on_failure(self, concrete_importer):
        """Test that validation_errors list populated when validation fails"""
        invalid_data = {
            'bsee_incident_id': 'INC-2024-INVALID',
            # Missing required fields
        }

        initial_error_count = len(concrete_importer.validation_errors)

        concrete_importer.validate_data(invalid_data)

        assert len(concrete_importer.validation_errors) > initial_error_count

    def test_import_data_returns_statistics_dict(self, concrete_importer):
        """Test that import_data() returns comprehensive statistics"""
        result = concrete_importer.import_data()

        assert isinstance(result, dict)
        assert 'imported_count' in result
        assert 'skipped_count' in result
        assert 'error_count' in result
        assert 'total_records' in result
        assert isinstance(result['imported_count'], int)
        assert isinstance(result['skipped_count'], int)
        assert isinstance(result['error_count'], int)

    def test_full_import_pipeline_with_mixed_data(self, concrete_importer):
        """Test complete import pipeline with valid, invalid, and duplicate data"""
        result = concrete_importer.import_data()

        # Should have 2 valid records, 1 invalid record
        assert result['total_records'] == 3
        assert result['imported_count'] == 2
        assert result['error_count'] == 1
        assert result['skipped_count'] == 0


# Pytest fixtures for database testing
@pytest.fixture
def db_session():
    """Create test database session with in-memory SQLite"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from worldenergydata.modules.hse.database.models import Base

    # Use in-memory SQLite for testing
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
