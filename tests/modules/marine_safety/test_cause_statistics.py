"""
Tests for incident cause statistical analysis module.

This test module validates statistical analysis capabilities for marine safety
incident causes including frequency distributions, temporal trends, cross-tabulations,
and specialized analysis for hatch/opening maloperation incidents.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from src.worldenergydata.modules.marine_safety.analysis.cause_statistics import (
    CauseStatistics,
    FrequencyDistribution,
    TemporalTrend,
    CrossTabulation,
    StatisticalSummary
)
from src.worldenergydata.modules.marine_safety.database.models import (
    Incident, IncidentCause, Vessel, Company
)
from src.worldenergydata.modules.marine_safety.constants import (
    CauseCategory, IncidentType, DataSource, SeverityLevel
)


@pytest.fixture
def sample_incidents_with_causes(test_session):
    """Create sample incidents with various causes for testing."""
    # Create companies and vessels
    company1 = Company(company_name="Test Oil Co", country="US")
    company2 = Company(company_name="Marine Services Inc", country="NO")
    test_session.add_all([company1, company2])
    test_session.flush()

    vessel1 = Vessel(
        vessel_name="Test Platform 1",
        vessel_type="production_platform",
        company_id=company1.company_id
    )
    vessel2 = Vessel(
        vessel_name="Test Supply Vessel",
        vessel_type="supply_vessel",
        company_id=company2.company_id
    )
    test_session.add_all([vessel1, vessel2])
    test_session.flush()

    # Create incidents with different causes
    incidents = []

    # Human error incidents (most common)
    for i in range(5):
        incident = Incident(
            source_agency=DataSource.USCG,
            source_incident_id=f"HE-2024-{i:03d}",
            incident_date=date(2024, 1, i+1),
            incident_type=IncidentType.PERSONNEL_INJURY,
            severity_level=SeverityLevel.MINOR,
            vessel_id=vessel1.vessel_id,
            company_id=company1.company_id
        )
        incidents.append(incident)
        test_session.add(incident)
        test_session.flush()

        cause = IncidentCause(
            incident_id=incident.incident_id,
            cause_category=CauseCategory.HUMAN_ERROR,
            cause_description="Operator error during routine operations",
            is_primary=True
        )
        test_session.add(cause)

    # Equipment failure incidents
    for i in range(3):
        incident = Incident(
            source_agency=DataSource.BSEE,
            source_incident_id=f"EF-2024-{i:03d}",
            incident_date=date(2024, 2, i+1),
            incident_type=IncidentType.EQUIPMENT_FAILURE,
            severity_level=SeverityLevel.MODERATE,
            vessel_id=vessel2.vessel_id,
            company_id=company2.company_id
        )
        incidents.append(incident)
        test_session.add(incident)
        test_session.flush()

        cause = IncidentCause(
            incident_id=incident.incident_id,
            cause_category=CauseCategory.EQUIPMENT_FAILURE,
            cause_description="Hydraulic system failure",
            is_primary=True
        )
        test_session.add(cause)

    # Weather-related incidents
    for i in range(2):
        incident = Incident(
            source_agency=DataSource.USCG,
            source_incident_id=f"WE-2024-{i:03d}",
            incident_date=date(2024, 3, i+1),
            incident_type=IncidentType.WEATHER_RELATED,
            severity_level=SeverityLevel.SERIOUS,
            vessel_id=vessel1.vessel_id,
            company_id=company1.company_id
        )
        incidents.append(incident)
        test_session.add(incident)
        test_session.flush()

        cause = IncidentCause(
            incident_id=incident.incident_id,
            cause_category=CauseCategory.WEATHER,
            cause_description="Hurricane force winds",
            is_primary=True
        )
        test_session.add(cause)

    # Maintenance issues
    incident = Incident(
        source_agency=DataSource.MAIB,
        source_incident_id="MI-2024-001",
        incident_date=date(2024, 4, 1),
        incident_type=IncidentType.STRUCTURAL_FAILURE,
        severity_level=SeverityLevel.CATASTROPHIC,
        vessel_id=vessel2.vessel_id,
        company_id=company2.company_id
    )
    incidents.append(incident)
    test_session.add(incident)
    test_session.flush()

    cause = IncidentCause(
        incident_id=incident.incident_id,
        cause_category=CauseCategory.MAINTENANCE_ISSUE,
        cause_description="Deferred maintenance on critical structural component",
        is_primary=True
    )
    test_session.add(cause)

    test_session.commit()
    return incidents


class TestCauseStatistics:
    """Test suite for CauseStatistics class."""

    def test_initialization(self, test_session):
        """Test CauseStatistics initialization with database session."""
        stats = CauseStatistics(test_session)
        assert stats.session == test_session
        assert isinstance(stats, CauseStatistics)

    def test_calculate_frequency_distribution(self, test_session, sample_incidents_with_causes):
        """Test frequency distribution calculation by cause category."""
        stats = CauseStatistics(test_session)
        distribution = stats.calculate_frequency_distribution()

        # Should return FrequencyDistribution object
        assert isinstance(distribution, FrequencyDistribution)

        # Should have counts for each category
        assert distribution.data is not None
        assert isinstance(distribution.data, pd.DataFrame)

        # Check expected counts
        assert distribution.data.loc[CauseCategory.HUMAN_ERROR, 'count'] == 5
        assert distribution.data.loc[CauseCategory.EQUIPMENT_FAILURE, 'count'] == 3
        assert distribution.data.loc[CauseCategory.WEATHER, 'count'] == 2
        assert distribution.data.loc[CauseCategory.MAINTENANCE_ISSUE, 'count'] == 1

        # Check percentages sum to 100%
        assert abs(distribution.data['percentage'].sum() - 100.0) < 0.01

    def test_calculate_percentages(self, test_session, sample_incidents_with_causes):
        """Test percentage calculation for cause categories."""
        stats = CauseStatistics(test_session)
        distribution = stats.calculate_frequency_distribution()

        # Human error should be ~45.5% (5/11)
        human_error_pct = distribution.data.loc[CauseCategory.HUMAN_ERROR, 'percentage']
        assert abs(human_error_pct - 45.45) < 0.1

        # Equipment failure should be ~27.3% (3/11)
        equipment_pct = distribution.data.loc[CauseCategory.EQUIPMENT_FAILURE, 'percentage']
        assert abs(equipment_pct - 27.27) < 0.1

    def test_temporal_trend_analysis(self, test_session, sample_incidents_with_causes):
        """Test temporal trend analysis of causes over time."""
        stats = CauseStatistics(test_session)

        # Analyze by month
        trends = stats.calculate_temporal_trends(period='month')

        assert isinstance(trends, TemporalTrend)
        assert trends.data is not None
        assert isinstance(trends.data, pd.DataFrame)

        # Should have data for multiple months
        assert len(trends.data) >= 3

        # Each row should have period and counts by category
        assert 'period' in trends.data.columns
        assert any(col.startswith('count_') for col in trends.data.columns)

    def test_temporal_trend_by_year(self, test_session, sample_incidents_with_causes):
        """Test temporal trend analysis grouped by year."""
        stats = CauseStatistics(test_session)

        trends = stats.calculate_temporal_trends(period='year')

        assert isinstance(trends, TemporalTrend)
        assert len(trends.data) >= 1  # All incidents in 2024

    def test_cross_tabulation_with_severity(self, test_session, sample_incidents_with_causes):
        """Test cross-tabulation of causes with severity levels."""
        stats = CauseStatistics(test_session)

        crosstab = stats.calculate_cause_severity_crosstab()

        assert isinstance(crosstab, CrossTabulation)
        assert crosstab.data is not None
        assert isinstance(crosstab.data, pd.DataFrame)

        # Should have cause categories as rows
        assert CauseCategory.HUMAN_ERROR in crosstab.data.index

        # Should have severity levels as columns
        assert any(str(severity) in str(crosstab.data.columns) for severity in SeverityLevel)

    def test_hatch_opening_maloperation_stats(self, test_session):
        """Test specialized statistics for hatch/opening maloperation incidents."""
        # Create specific hatch maloperation incidents
        vessel = Vessel(vessel_name="Test Vessel", vessel_type="cargo_vessel")
        test_session.add(vessel)
        test_session.flush()

        for i in range(3):
            incident = Incident(
                source_agency=DataSource.MAIB,
                source_incident_id=f"HATCH-2024-{i:03d}",
                incident_date=date(2024, 5, i+1),
                incident_type=IncidentType.FLOODING,
                severity_level=SeverityLevel.SERIOUS,
                vessel_id=vessel.vessel_id,
                description="Hatch cover maloperation leading to water ingress"
            )
            test_session.add(incident)
            test_session.flush()

            cause = IncidentCause(
                incident_id=incident.incident_id,
                cause_category=CauseCategory.PROCEDURAL,
                cause_description="Hatch cover not properly secured",
                is_primary=True
            )
            test_session.add(cause)

        test_session.commit()

        stats = CauseStatistics(test_session)
        hatch_stats = stats.calculate_hatch_maloperation_stats()

        assert hatch_stats is not None
        assert isinstance(hatch_stats, dict)
        assert 'total_incidents' in hatch_stats
        assert hatch_stats['total_incidents'] >= 3

    def test_summary_report_generation(self, test_session, sample_incidents_with_causes):
        """Test generation of comprehensive summary report."""
        stats = CauseStatistics(test_session)

        summary = stats.generate_summary_report()

        assert isinstance(summary, StatisticalSummary)
        assert summary.total_incidents > 0
        assert summary.total_causes > 0
        assert summary.most_common_cause is not None
        assert summary.date_range is not None

    def test_statistical_validation(self, test_session, sample_incidents_with_causes):
        """Test statistical validation and confidence intervals."""
        stats = CauseStatistics(test_session)

        # Get distribution with confidence intervals
        distribution = stats.calculate_frequency_distribution(
            include_confidence_intervals=True
        )

        assert 'ci_lower' in distribution.data.columns
        assert 'ci_upper' in distribution.data.columns

        # Confidence intervals should be valid
        for idx in distribution.data.index:
            assert distribution.data.loc[idx, 'ci_lower'] <= distribution.data.loc[idx, 'percentage']
            assert distribution.data.loc[idx, 'percentage'] <= distribution.data.loc[idx, 'ci_upper']

    def test_export_to_csv(self, test_session, sample_incidents_with_causes, tmp_path):
        """Test exporting statistics to CSV file."""
        stats = CauseStatistics(test_session)
        distribution = stats.calculate_frequency_distribution()

        csv_path = tmp_path / "cause_distribution.csv"
        distribution.to_csv(csv_path)

        # Verify file was created
        assert csv_path.exists()

        # Verify data can be read back
        df = pd.read_csv(csv_path)
        assert len(df) > 0
        assert 'count' in df.columns
        assert 'percentage' in df.columns

    def test_filter_by_date_range(self, test_session, sample_incidents_with_causes):
        """Test filtering statistics by date range."""
        stats = CauseStatistics(test_session)

        # Filter to January only
        distribution = stats.calculate_frequency_distribution(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )

        # Should only include January incidents (5 human error)
        total = distribution.data['count'].sum()
        assert total == 5

    def test_filter_by_severity(self, test_session, sample_incidents_with_causes):
        """Test filtering statistics by severity level."""
        stats = CauseStatistics(test_session)

        # Filter to only serious and catastrophic
        distribution = stats.calculate_frequency_distribution(
            min_severity=SeverityLevel.SERIOUS
        )

        # Should include weather (2) + maintenance (1) = 3
        total = distribution.data['count'].sum()
        assert total == 3

    def test_empty_dataset_handling(self, test_session):
        """Test handling of empty dataset (no incidents)."""
        stats = CauseStatistics(test_session)

        distribution = stats.calculate_frequency_distribution()

        # Should return empty FrequencyDistribution, not crash
        assert isinstance(distribution, FrequencyDistribution)
        assert len(distribution.data) == 0

    def test_single_incident_statistics(self, test_session):
        """Test statistics calculation with only one incident."""
        vessel = Vessel(vessel_name="Test", vessel_type="other")
        test_session.add(vessel)
        test_session.flush()

        incident = Incident(
            source_agency=DataSource.USCG,
            source_incident_id="SINGLE-001",
            incident_date=date(2024, 1, 1),
            incident_type=IncidentType.OTHER,
            severity_level=SeverityLevel.MINOR,
            vessel_id=vessel.vessel_id
        )
        test_session.add(incident)
        test_session.flush()

        cause = IncidentCause(
            incident_id=incident.incident_id,
            cause_category=CauseCategory.UNKNOWN,
            is_primary=True
        )
        test_session.add(cause)
        test_session.commit()

        stats = CauseStatistics(test_session)
        distribution = stats.calculate_frequency_distribution()

        assert distribution.data.loc[CauseCategory.UNKNOWN, 'count'] == 1
        assert abs(distribution.data.loc[CauseCategory.UNKNOWN, 'percentage'] - 100.0) < 0.01

    def test_multiple_causes_per_incident(self, test_session):
        """Test handling of incidents with multiple contributing causes."""
        vessel = Vessel(vessel_name="Multi Cause Test", vessel_type="production_platform")
        test_session.add(vessel)
        test_session.flush()

        incident = Incident(
            source_agency=DataSource.BSEE,
            source_incident_id="MULTI-001",
            incident_date=date(2024, 6, 1),
            incident_type=IncidentType.EXPLOSION,
            severity_level=SeverityLevel.CATASTROPHIC,
            vessel_id=vessel.vessel_id
        )
        test_session.add(incident)
        test_session.flush()

        # Primary cause
        cause1 = IncidentCause(
            incident_id=incident.incident_id,
            cause_category=CauseCategory.EQUIPMENT_FAILURE,
            cause_description="Gas detection system failure",
            is_primary=True
        )

        # Contributing causes
        cause2 = IncidentCause(
            incident_id=incident.incident_id,
            cause_category=CauseCategory.MAINTENANCE_ISSUE,
            cause_description="Deferred maintenance on safety systems",
            is_primary=False,
            contributing_factor="Inadequate preventive maintenance schedule"
        )

        cause3 = IncidentCause(
            incident_id=incident.incident_id,
            cause_category=CauseCategory.PROCEDURAL,
            cause_description="Failure to follow gas testing procedures",
            is_primary=False
        )

        test_session.add_all([cause1, cause2, cause3])
        test_session.commit()

        stats = CauseStatistics(test_session)

        # Test all causes
        all_causes_dist = stats.calculate_frequency_distribution(primary_only=False)
        assert all_causes_dist.data['count'].sum() == 3

        # Test primary only
        primary_dist = stats.calculate_frequency_distribution(primary_only=True)
        assert primary_dist.data['count'].sum() == 1
        assert primary_dist.data.loc[CauseCategory.EQUIPMENT_FAILURE, 'count'] == 1

    def test_dataframe_return_format(self, test_session, sample_incidents_with_causes):
        """Test that results are returned as pandas DataFrames for easy visualization."""
        stats = CauseStatistics(test_session)

        distribution = stats.calculate_frequency_distribution()
        assert isinstance(distribution.data, pd.DataFrame)

        trends = stats.calculate_temporal_trends()
        assert isinstance(trends.data, pd.DataFrame)

        crosstab = stats.calculate_cause_severity_crosstab()
        assert isinstance(crosstab.data, pd.DataFrame)

    def test_comprehensive_docstrings(self):
        """Test that all methods have comprehensive docstrings."""
        from inspect import getmembers, ismethod, getdoc

        # This will fail until we implement the class
        # but helps verify documentation completeness
        stats_class = CauseStatistics

        for name, method in getmembers(stats_class, predicate=lambda x: callable(x)):
            if not name.startswith('_'):  # Skip private methods
                doc = getdoc(method)
                assert doc is not None, f"Method {name} missing docstring"
                assert len(doc) > 20, f"Method {name} has insufficient documentation"
