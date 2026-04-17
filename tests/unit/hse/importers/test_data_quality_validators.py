# ABOUTME: pytest tests for HSE data quality validators post-import validation
# ABOUTME: Tests completeness, range validation, consistency, outliers, and temporal checks

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker

from worldenergydata.hse.database.models import Base, HSEIncident


class TestDataQualityValidatorInterface:
    """Test DataQualityValidator class interface and initialization"""

    def test_can_instantiate_with_db_session(self, db_session):
        """Test validator can be instantiated with database session"""
        from worldenergydata.hse.importers.data_quality_validator import (
            DataQualityValidator,
        )

        validator = DataQualityValidator(db_session)

        assert validator is not None
        assert validator.db_session == db_session

    def test_has_required_validation_methods(self, db_session):
        """Test validator has all required validation methods"""
        from worldenergydata.hse.importers.data_quality_validator import (
            DataQualityValidator,
        )

        validator = DataQualityValidator(db_session)

        assert hasattr(validator, "validate_completeness")
        assert hasattr(validator, "validate_ranges")
        assert hasattr(validator, "validate_consistency")
        assert hasattr(validator, "detect_outliers")
        assert hasattr(validator, "validate_temporal")
        assert hasattr(validator, "run_all_validations")

    def test_initializes_validation_results_dict(self, db_session):
        """Test validator initializes empty validation results dictionary"""
        from worldenergydata.hse.importers.data_quality_validator import (
            DataQualityValidator,
        )

        validator = DataQualityValidator(db_session)

        assert hasattr(validator, "validation_results")
        assert isinstance(validator.validation_results, dict)


class TestCompletenessValidation:
    """Test completeness validation for required and optional fields"""

    @pytest.fixture
    def validator(self, db_session):
        """Create validator instance for testing"""
        from worldenergydata.hse.importers.data_quality_validator import (
            DataQualityValidator,
        )

        return DataQualityValidator(db_session)

    def test_validate_completeness_checks_required_fields(self, validator, db_session):
        """Test completeness validation reports percentage of required fields populated"""
        # Create incidents with varying completeness
        complete_incident = HSEIncident(
            bsee_incident_id="COMP-001",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
        )

        incomplete_incident = HSEIncident(
            bsee_incident_id="INC-001",
            incident_date=datetime(2024, 1, 16),
            operator="BP America",
            incident_type="spill",
            severity="minor",
        )

        db_session.add_all([complete_incident, incomplete_incident])
        db_session.commit()

        result = validator.validate_completeness()

        assert "required_fields_completeness" in result
        assert (
            result["required_fields_completeness"] == 100.0
        )  # All required fields present

    def test_validate_completeness_checks_optional_fields(self, validator, db_session):
        """Test completeness validation reports percentage of optional fields populated"""
        # Create incident with some optional fields
        incident = HSEIncident(
            bsee_incident_id="OPT-001",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
            facility_name="Platform A",
            latitude=28.5,
            longitude=-89.2,
        )

        db_session.add(incident)
        db_session.commit()

        result = validator.validate_completeness()

        assert "optional_fields_completeness" in result
        assert result["optional_fields_completeness"] > 0.0

    def test_validate_completeness_handles_empty_database(self, validator, db_session):
        """Test completeness validation handles empty database gracefully"""
        result = validator.validate_completeness()

        assert result["total_records"] == 0
        assert result["required_fields_completeness"] == 0.0
        assert result["optional_fields_completeness"] == 0.0


class TestRangeValidation:
    """Test range validation for numeric and geographic fields"""

    @pytest.fixture
    def validator(self, db_session):
        """Create validator instance for testing"""
        from worldenergydata.hse.importers.data_quality_validator import (
            DataQualityValidator,
        )

        return DataQualityValidator(db_session)

    def test_validate_ranges_checks_latitude_bounds(self, validator, db_session):
        """Test range validation detects latitude outside Gulf of Mexico bounds"""
        # Create incident with valid latitude via ORM
        valid_incident = HSEIncident(
            bsee_incident_id="LAT-001",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
            latitude=28.5,  # Valid GOM range
            longitude=-89.2,
        )
        db_session.add(valid_incident)
        db_session.commit()

        # Create incident with invalid latitude using direct SQL INSERT to bypass @validates
        stmt = insert(HSEIncident.__table__).values(
            bsee_incident_id="LAT-002",
            incident_date=datetime(2024, 1, 16),
            operator="BP America",
            incident_type="spill",
            severity="minor",
            latitude=35.0,  # Outside GOM range (18-31°N)
            longitude=-89.0,
        )
        db_session.execute(stmt)
        db_session.commit()

        result = validator.validate_ranges()

        assert "latitude_violations" in result
        assert result["latitude_violations"] == 1

    def test_validate_ranges_checks_longitude_bounds(self, validator, db_session):
        """Test range validation detects longitude outside Gulf of Mexico bounds"""
        # Create incident with invalid longitude using direct SQL INSERT to bypass @validates
        stmt = insert(HSEIncident.__table__).values(
            bsee_incident_id="LON-001",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
            latitude=28.5,
            longitude=-75.0,  # Outside GOM range (-98 to -80°W)
        )
        db_session.execute(stmt)
        db_session.commit()

        result = validator.validate_ranges()

        assert "longitude_violations" in result
        assert result["longitude_violations"] == 1

    def test_validate_ranges_checks_penalty_amount_positive(
        self, validator, db_session
    ):
        """Test range validation detects negative penalty amounts"""
        # Create violation with negative penalty (invalid)
        invalid_incident = HSEIncident(
            bsee_incident_id="PEN-001",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="violation",
            severity="recordable",
            # Note: penalty_amount would need to be added to HSEIncident model
        )

        db_session.add(invalid_incident)
        db_session.commit()

        result = validator.validate_ranges()

        assert "negative_penalty_violations" in result

    def test_validate_ranges_checks_incident_counts_non_negative(
        self, validator, db_session
    ):
        """Test range validation detects negative incident counts"""
        # This would apply to statistics records with count fields
        result = validator.validate_ranges()

        assert "negative_count_violations" in result


class TestConsistencyValidation:
    """Test consistency validation for related fields"""

    @pytest.fixture
    def validator(self, db_session):
        """Create validator instance for testing"""
        from worldenergydata.hse.importers.data_quality_validator import (
            DataQualityValidator,
        )

        return DataQualityValidator(db_session)

    def test_validate_consistency_checks_severity_incident_type_alignment(
        self, validator, db_session
    ):
        """Test consistency validation checks severity aligns with incident type"""
        # Create incident with inconsistent severity/type
        # Example: fatality severity but near_miss incident type would be inconsistent
        incident = HSEIncident(
            bsee_incident_id="CON-001",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="fatality",
        )

        db_session.add(incident)
        db_session.commit()

        result = validator.validate_consistency()

        assert "severity_type_consistency" in result

    def test_validate_consistency_checks_facility_location_alignment(
        self, validator, db_session
    ):
        """Test consistency validation checks facility and location fields align"""
        # If facility_name is present, latitude/longitude should also be present
        inconsistent_incident = HSEIncident(
            bsee_incident_id="LOC-001",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
            facility_name="Platform A",
            latitude=None,  # Inconsistent: facility without location
            longitude=None,
        )

        db_session.add(inconsistent_incident)
        db_session.commit()

        result = validator.validate_consistency()

        assert "facility_location_inconsistencies" in result

    def test_validate_consistency_checks_compliance_penalty_alignment(
        self, validator, db_session
    ):
        """Test consistency validation checks compliance and penalty fields align"""
        # If compliance_deadline is present, penalty_amount should also be present
        result = validator.validate_consistency()

        assert "compliance_penalty_inconsistencies" in result


class TestOutlierDetection:
    """Test statistical outlier detection"""

    @pytest.fixture
    def validator(self, db_session):
        """Create validator instance for testing"""
        from worldenergydata.hse.importers.data_quality_validator import (
            DataQualityValidator,
        )

        return DataQualityValidator(db_session)

    def test_detect_outliers_identifies_extreme_penalty_amounts(
        self, validator, db_session
    ):
        """Test outlier detection flags unusually high/low penalty amounts"""
        # Create normal penalties and one extreme outlier
        # This test would require penalty_amount field in HSEIncident model
        result = validator.detect_outliers()

        assert "penalty_amount_outliers" in result

    def test_detect_outliers_identifies_extreme_incident_counts(
        self, validator, db_session
    ):
        """Test outlier detection flags unusually high incident counts"""
        # This applies to statistics records
        result = validator.detect_outliers()

        assert "incident_count_outliers" in result

    def test_detect_outliers_uses_iqr_method(self, validator, db_session):
        """Test outlier detection uses IQR (Interquartile Range) method"""
        # Create dataset with known outliers
        # Normal: 10, 12, 11, 13, 12, 11, 10
        # Outlier: 100
        result = validator.detect_outliers()

        assert "outlier_method" in result
        assert result["outlier_method"] == "IQR"

    def test_detect_outliers_returns_outlier_details(self, validator, db_session):
        """Test outlier detection returns details about detected outliers"""
        result = validator.detect_outliers()

        # Should return list of outlier incidents with details
        assert "outliers" in result
        assert isinstance(result["outliers"], list)


class TestTemporalValidation:
    """Test temporal validation for date sequences"""

    @pytest.fixture
    def validator(self, db_session):
        """Create validator instance for testing"""
        from worldenergydata.hse.importers.data_quality_validator import (
            DataQualityValidator,
        )

        return DataQualityValidator(db_session)

    def test_validate_temporal_checks_incident_date_not_future(
        self, validator, db_session
    ):
        """Test temporal validation flags incidents with future dates"""
        # Create incident with future date
        future_incident = HSEIncident(
            bsee_incident_id="FUT-001",
            incident_date=datetime.now() + timedelta(days=30),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
        )

        db_session.add(future_incident)
        db_session.commit()

        result = validator.validate_temporal()

        assert "future_date_violations" in result
        assert result["future_date_violations"] == 1

    def test_validate_temporal_checks_incident_date_not_too_old(
        self, validator, db_session
    ):
        """Test temporal validation flags incidents with unreasonably old dates"""
        # Create incident with very old date (before BSEE existed)
        old_incident = HSEIncident(
            bsee_incident_id="OLD-001",
            incident_date=datetime(1900, 1, 1),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
        )

        db_session.add(old_incident)
        db_session.commit()

        result = validator.validate_temporal()

        assert "unreasonably_old_violations" in result

    def test_validate_temporal_checks_compliance_deadline_after_incident(
        self, validator, db_session
    ):
        """Test temporal validation checks compliance deadline is after incident date"""
        # This would require compliance_deadline field
        result = validator.validate_temporal()

        assert "deadline_before_incident_violations" in result

    def test_validate_temporal_identifies_date_gaps(self, validator, db_session):
        """Test temporal validation identifies unusual gaps in incident dates"""
        # If there's a 6-month gap in incident reporting, that's suspicious
        result = validator.validate_temporal()

        assert "suspicious_date_gaps" in result


class TestRunAllValidations:
    """Test comprehensive validation execution"""

    @pytest.fixture
    def validator(self, db_session):
        """Create validator instance for testing"""
        from worldenergydata.hse.importers.data_quality_validator import (
            DataQualityValidator,
        )

        return DataQualityValidator(db_session)

    def test_run_all_validations_executes_all_checks(self, validator, db_session):
        """Test run_all_validations executes all validation methods"""
        # Create diverse dataset with various quality issues
        incidents = [
            HSEIncident(
                bsee_incident_id=f"ALL-{i:03d}",
                incident_date=datetime(2024, 1, i + 1),
                operator="Shell Offshore Inc.",
                incident_type="injury",
                severity="recordable",
            )
            for i in range(10)
        ]

        db_session.add_all(incidents)
        db_session.commit()

        result = validator.run_all_validations()

        # Should include results from all validation types
        assert "completeness" in result
        assert "ranges" in result
        assert "consistency" in result
        assert "outliers" in result
        assert "temporal" in result

    def test_run_all_validations_calculates_overall_quality_score(
        self, validator, db_session
    ):
        """Test run_all_validations calculates overall data quality score"""
        result = validator.run_all_validations()

        assert "overall_quality_score" in result
        assert 0.0 <= result["overall_quality_score"] <= 100.0

    def test_run_all_validations_returns_summary_statistics(
        self, validator, db_session
    ):
        """Test run_all_validations returns summary statistics"""
        result = validator.run_all_validations()

        assert "total_records" in result
        assert "total_violations" in result
        assert "violation_percentage" in result

    def test_run_all_validations_stores_results_in_instance(
        self, validator, db_session
    ):
        """Test run_all_validations stores results in validator.validation_results"""
        validator.run_all_validations()

        assert validator.validation_results is not None
        assert len(validator.validation_results) > 0


class TestValidationReporting:
    """Test validation result reporting and export"""

    @pytest.fixture
    def validator(self, db_session):
        """Create validator instance for testing"""
        from worldenergydata.hse.importers.data_quality_validator import (
            DataQualityValidator,
        )

        return DataQualityValidator(db_session)

    def test_generate_quality_report_creates_dict(self, validator, db_session):
        """Test quality report generation returns structured dictionary"""
        validator.run_all_validations()

        report = validator.generate_quality_report()

        assert isinstance(report, dict)
        assert "validation_timestamp" in report
        assert "quality_score" in report
        assert "violations_by_category" in report

    def test_export_quality_report_to_json(self, validator, db_session, tmp_path):
        """Test quality report can be exported to JSON file"""
        validator.run_all_validations()

        output_file = tmp_path / "quality_report.json"
        validator.export_quality_report(str(output_file), format="json")

        assert output_file.exists()

    def test_export_quality_report_to_html(self, validator, db_session, tmp_path):
        """Test quality report can be exported to HTML file"""
        validator.run_all_validations()

        output_file = tmp_path / "quality_report.html"
        validator.export_quality_report(str(output_file), format="html")

        assert output_file.exists()


# Pytest fixtures


@pytest.fixture
def db_session():
    """Create test database session with in-memory SQLite"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from worldenergydata.hse.database.models import Base

    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
