"""
Tests for Hatch/Opening Maloperation Analysis Module

This module tests the specialized analysis functionality for incidents
involving hatch and opening maloperation for engine rooms or enclosures.
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any

# Test data will be imported from fixtures
from tests.modules.marine_safety.fixtures.sample_data import generate_incident


@pytest.fixture
def hatch_maloperation_incidents() -> List[Dict[str, Any]]:
    """Generate sample incidents with hatch maloperation scenarios.

    Returns:
        List of incident dictionaries with hatch maloperation descriptions
    """
    return [
        {
            'incident_id': 'HATCH-2024-001',
            'date': datetime(2024, 1, 15),
            'incident_type': 'Flooding',
            'severity': 'Serious',
            'description': (
                'Engine room flooding occurred due to hatch maloperation. '
                'Crew member failed to properly secure engine room access hatch, '
                'resulting in water ingress during heavy seas. Bilge pumps engaged '
                'automatically. No injuries reported but significant equipment damage.'
            ),
            'location': 'Gulf of Mexico',
            'consequences': ['flooding', 'equipment_damage'],
            'fatalities': 0,
            'injuries': 0,
            'estimated_damage_usd': 150000
        },
        {
            'incident_id': 'HATCH-2024-002',
            'date': datetime(2024, 2, 10),
            'incident_type': 'Fire',
            'severity': 'Critical',
            'description': (
                'Fire in engine room enclosure caused by hatch failure. '
                'Access cover maloperation prevented proper ventilation, '
                'leading to fuel vapor accumulation and subsequent ignition. '
                'Two crew members sustained burns. Fire suppression system activated.'
            ),
            'location': 'North Atlantic',
            'consequences': ['fire', 'personnel_injury', 'equipment_damage'],
            'fatalities': 0,
            'injuries': 2,
            'estimated_damage_usd': 500000
        },
        {
            'incident_id': 'HATCH-2024-003',
            'date': datetime(2024, 3, 5),
            'incident_type': 'Personnel Injury',
            'severity': 'Moderate',
            'description': (
                'Crew member injured when opening maloperation caused hatch to fall. '
                'Improperly maintained hinge mechanism on deck access opening failed, '
                'resulting in fracture to crew member arm. Emergency medical treatment provided.'
            ),
            'location': 'Pacific Ocean',
            'consequences': ['personnel_injury'],
            'fatalities': 0,
            'injuries': 1,
            'estimated_damage_usd': 25000
        },
        {
            'incident_id': 'HATCH-2024-004',
            'date': datetime(2024, 4, 20),
            'incident_type': 'Equipment Failure',
            'severity': 'Minor',
            'description': (
                'Engine room hatch seal failure detected during routine inspection. '
                'Hatch seal maloperation could have led to water ingress in adverse conditions. '
                'Preventive maintenance performed. No injuries or damage.'
            ),
            'location': 'Caribbean Sea',
            'consequences': ['near_miss'],
            'fatalities': 0,
            'injuries': 0,
            'estimated_damage_usd': 5000
        },
        {
            'incident_id': 'HATCH-2024-005',
            'date': datetime(2024, 5, 12),
            'incident_type': 'Flooding',
            'severity': 'Catastrophic',
            'description': (
                'Critical engine room flooding from multiple hatch maloperation points. '
                'Several engine room access hatches failed simultaneously during storm conditions. '
                'Vessel took on significant water, listed 15 degrees. Emergency evacuation initiated. '
                'One fatality, three serious injuries. Vessel ultimately salvaged.'
            ),
            'location': 'North Sea',
            'consequences': ['flooding', 'personnel_injury', 'fatality', 'vessel_stability'],
            'fatalities': 1,
            'injuries': 3,
            'estimated_damage_usd': 2500000
        },
        {
            'incident_id': 'NON-HATCH-001',
            'date': datetime(2024, 6, 1),
            'incident_type': 'Collision',
            'severity': 'Moderate',
            'description': (
                'Vessel collision during restricted visibility. '
                'No hatch-related issues. Bridge watchkeeping failure '
                'led to contact with another vessel. Minor structural damage.'
            ),
            'location': 'English Channel',
            'consequences': ['structural_damage'],
            'fatalities': 0,
            'injuries': 0,
            'estimated_damage_usd': 75000
        }
    ]


class TestHatchMaloperationPatternMatching:
    """Tests for identifying hatch maloperation incidents from descriptions."""

    def test_identifies_hatch_maloperation_basic(self, hatch_maloperation_incidents):
        """Test basic identification of hatch maloperation terminology."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Should identify first incident as hatch maloperation
        incident = hatch_maloperation_incidents[0]
        is_hatch_incident = analyzer.is_hatch_maloperation_incident(incident)

        assert is_hatch_incident is True

    def test_identifies_hatch_failure_terminology(self, hatch_maloperation_incidents):
        """Test identification of 'hatch failure' variation."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Second incident uses "hatch failure"
        incident = hatch_maloperation_incidents[1]
        is_hatch_incident = analyzer.is_hatch_maloperation_incident(incident)

        assert is_hatch_incident is True

    def test_identifies_opening_maloperation(self, hatch_maloperation_incidents):
        """Test identification of 'opening maloperation' variation."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Third incident uses "opening maloperation"
        incident = hatch_maloperation_incidents[2]
        is_hatch_incident = analyzer.is_hatch_maloperation_incident(incident)

        assert is_hatch_incident is True

    def test_identifies_access_cover_terminology(self, hatch_maloperation_incidents):
        """Test identification of 'access cover' terminology."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Second incident includes "access cover maloperation"
        incident = hatch_maloperation_incidents[1]
        is_hatch_incident = analyzer.is_hatch_maloperation_incident(incident)

        assert is_hatch_incident is True

    def test_rejects_non_hatch_incidents(self, hatch_maloperation_incidents):
        """Test that non-hatch incidents are correctly excluded."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Last incident is a collision with no hatch involvement
        incident = hatch_maloperation_incidents[-1]
        is_hatch_incident = analyzer.is_hatch_maloperation_incident(incident)

        assert is_hatch_incident is False

    def test_extract_relevant_text(self, hatch_maloperation_incidents):
        """Test extraction of hatch-related text from descriptions."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        incident = hatch_maloperation_incidents[0]
        relevant_text = analyzer.extract_hatch_related_text(incident)

        assert relevant_text is not None
        assert 'hatch' in relevant_text.lower()
        assert 'engine room' in relevant_text.lower()


class TestLocationClassification:
    """Tests for classifying hatch maloperation by location."""

    def test_classify_engine_room_location(self, hatch_maloperation_incidents):
        """Test classification of engine room hatch incidents."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # First incident explicitly mentions engine room
        incident = hatch_maloperation_incidents[0]
        location_type = analyzer.classify_location(incident)

        assert location_type == 'engine_room'

    def test_classify_other_enclosure_location(self, hatch_maloperation_incidents):
        """Test classification of other enclosure types."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Third incident mentions deck access opening (not engine room)
        incident = hatch_maloperation_incidents[2]
        location_type = analyzer.classify_location(incident)

        assert location_type in ['other_enclosure', 'deck_access']

    def test_get_location_statistics(self, hatch_maloperation_incidents):
        """Test generation of location-based statistics."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Filter to only hatch incidents
        hatch_incidents = [inc for inc in hatch_maloperation_incidents
                          if analyzer.is_hatch_maloperation_incident(inc)]

        location_stats = analyzer.get_location_statistics(hatch_incidents)

        assert 'engine_room' in location_stats
        assert location_stats['engine_room'] >= 1
        assert 'total' in location_stats


class TestConsequenceAnalysis:
    """Tests for analyzing consequences of hatch maloperation incidents."""

    def test_identify_flooding_consequence(self, hatch_maloperation_incidents):
        """Test identification of flooding as a consequence."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        incident = hatch_maloperation_incidents[0]
        consequences = analyzer.analyze_consequences(incident)

        assert 'flooding' in consequences

    def test_identify_fire_consequence(self, hatch_maloperation_incidents):
        """Test identification of fire as a consequence."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        incident = hatch_maloperation_incidents[1]
        consequences = analyzer.analyze_consequences(incident)

        assert 'fire' in consequences

    def test_identify_personnel_injury_consequence(self, hatch_maloperation_incidents):
        """Test identification of personnel injury as a consequence."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Second incident has injuries
        incident = hatch_maloperation_incidents[1]
        consequences = analyzer.analyze_consequences(incident)

        assert 'personnel_injury' in consequences

    def test_identify_fatality_consequence(self, hatch_maloperation_incidents):
        """Test identification of fatalities as a consequence."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Fifth incident has a fatality
        incident = hatch_maloperation_incidents[4]
        consequences = analyzer.analyze_consequences(incident)

        assert 'fatality' in consequences

    def test_get_consequence_statistics(self, hatch_maloperation_incidents):
        """Test generation of consequence statistics."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        hatch_incidents = [inc for inc in hatch_maloperation_incidents
                          if analyzer.is_hatch_maloperation_incident(inc)]

        consequence_stats = analyzer.get_consequence_statistics(hatch_incidents)

        assert 'flooding' in consequence_stats
        assert 'fire' in consequence_stats
        assert 'personnel_injury' in consequence_stats
        assert 'total_incidents' in consequence_stats


class TestContributingFactorIdentification:
    """Tests for identifying contributing factors in hatch maloperation incidents."""

    def test_identify_human_error_factor(self, hatch_maloperation_incidents):
        """Test identification of human error as a contributing factor."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # First incident mentions crew failure to secure hatch
        incident = hatch_maloperation_incidents[0]
        factors = analyzer.identify_contributing_factors(incident)

        assert 'human_error' in factors

    def test_identify_maintenance_factor(self, hatch_maloperation_incidents):
        """Test identification of maintenance issues as a contributing factor."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Third incident mentions improperly maintained hinge mechanism
        incident = hatch_maloperation_incidents[2]
        factors = analyzer.identify_contributing_factors(incident)

        assert 'maintenance_issue' in factors

    def test_identify_equipment_failure_factor(self, hatch_maloperation_incidents):
        """Test identification of equipment failure as a contributing factor."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Fourth incident is seal failure
        incident = hatch_maloperation_incidents[3]
        factors = analyzer.identify_contributing_factors(incident)

        assert 'equipment_failure' in factors

    def test_identify_weather_factor(self, hatch_maloperation_incidents):
        """Test identification of weather as a contributing factor."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Fifth incident occurs during storm conditions
        incident = hatch_maloperation_incidents[4]
        factors = analyzer.identify_contributing_factors(incident)

        assert 'weather' in factors


class TestRiskScoring:
    """Tests for calculating risk scores for hatch maloperation incidents."""

    def test_calculate_risk_score_basic(self, hatch_maloperation_incidents):
        """Test basic risk score calculation."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        incident = hatch_maloperation_incidents[0]
        risk_score = analyzer.calculate_risk_score(incident)

        assert isinstance(risk_score, (int, float))
        assert 0 <= risk_score <= 100

    def test_catastrophic_incident_has_high_risk_score(self, hatch_maloperation_incidents):
        """Test that catastrophic incidents have higher risk scores."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Compare catastrophic incident (with fatality) to minor incident
        catastrophic = hatch_maloperation_incidents[4]  # Has fatality
        minor = hatch_maloperation_incidents[3]  # Near miss, no injuries

        catastrophic_score = analyzer.calculate_risk_score(catastrophic)
        minor_score = analyzer.calculate_risk_score(minor)

        assert catastrophic_score > minor_score
        assert catastrophic_score >= 80  # Should be high risk
        assert minor_score <= 40  # Should be lower risk

    def test_fatalities_increase_risk_score(self, hatch_maloperation_incidents):
        """Test that fatalities significantly increase risk score."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Incident with fatality vs without
        with_fatality = hatch_maloperation_incidents[4]
        without_fatality = hatch_maloperation_incidents[1]

        score_with_fatality = analyzer.calculate_risk_score(with_fatality)
        score_without_fatality = analyzer.calculate_risk_score(without_fatality)

        # Fatality should add significant points
        assert score_with_fatality > score_without_fatality


class TestRecommendationGeneration:
    """Tests for generating recommendations based on incident patterns."""

    def test_generate_recommendations_for_human_error(self, hatch_maloperation_incidents):
        """Test recommendation generation for human error cases."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        incident = hatch_maloperation_incidents[0]
        recommendations = analyzer.generate_recommendations(incident)

        assert len(recommendations) > 0
        assert any('training' in rec.lower() for rec in recommendations)

    def test_generate_recommendations_for_maintenance_issues(self, hatch_maloperation_incidents):
        """Test recommendation generation for maintenance-related incidents."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        incident = hatch_maloperation_incidents[2]
        recommendations = analyzer.generate_recommendations(incident)

        assert len(recommendations) > 0
        assert any('maintenance' in rec.lower() or 'inspection' in rec.lower()
                  for rec in recommendations)

    def test_generate_recommendations_for_equipment_failure(self, hatch_maloperation_incidents):
        """Test recommendation generation for equipment failure cases."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        incident = hatch_maloperation_incidents[3]
        recommendations = analyzer.generate_recommendations(incident)

        assert len(recommendations) > 0
        assert any('replacement' in rec.lower() or 'upgrade' in rec.lower()
                  for rec in recommendations)

    def test_aggregate_recommendations_from_multiple_incidents(self, hatch_maloperation_incidents):
        """Test aggregating recommendations from multiple similar incidents."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        hatch_incidents = [inc for inc in hatch_maloperation_incidents
                          if analyzer.is_hatch_maloperation_incident(inc)]

        aggregated_recs = analyzer.aggregate_recommendations(hatch_incidents)

        assert isinstance(aggregated_recs, dict)
        assert len(aggregated_recs) > 0


class TestCaseStudyExtraction:
    """Tests for extracting detailed case studies from significant incidents."""

    def test_extract_case_study_basic(self, hatch_maloperation_incidents):
        """Test basic case study extraction."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        incident = hatch_maloperation_incidents[0]
        case_study = analyzer.extract_case_study(incident)

        assert case_study is not None
        assert 'incident_id' in case_study
        assert 'summary' in case_study
        assert 'contributing_factors' in case_study
        assert 'consequences' in case_study
        assert 'lessons_learned' in case_study

    def test_significant_incidents_flagged(self, hatch_maloperation_incidents):
        """Test that significant incidents are properly flagged."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Catastrophic incident with fatality should be flagged as significant
        incident = hatch_maloperation_incidents[4]
        is_significant = analyzer.is_significant_incident(incident)

        assert is_significant is True

    def test_minor_incidents_not_flagged(self, hatch_maloperation_incidents):
        """Test that minor incidents are not flagged as significant."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        # Near miss with no injuries should not be significant
        incident = hatch_maloperation_incidents[3]
        is_significant = analyzer.is_significant_incident(incident)

        assert is_significant is False


class TestStatisticsAndVisualization:
    """Tests for generating statistics and visualization data."""

    def test_generate_severity_distribution(self, hatch_maloperation_incidents):
        """Test generation of severity distribution statistics."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        hatch_incidents = [inc for inc in hatch_maloperation_incidents
                          if analyzer.is_hatch_maloperation_incident(inc)]

        severity_dist = analyzer.get_severity_distribution(hatch_incidents)

        assert isinstance(severity_dist, dict)
        assert 'Catastrophic' in severity_dist
        assert severity_dist['Catastrophic'] >= 1

    def test_generate_time_series_data(self, hatch_maloperation_incidents):
        """Test generation of time series data for trending."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        hatch_incidents = [inc for inc in hatch_maloperation_incidents
                          if analyzer.is_hatch_maloperation_incident(inc)]

        time_series = analyzer.get_time_series_data(hatch_incidents)

        assert isinstance(time_series, (list, dict))
        assert len(time_series) > 0

    def test_calculate_trends(self, hatch_maloperation_incidents):
        """Test trend calculation over time."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        hatch_incidents = [inc for inc in hatch_maloperation_incidents
                          if analyzer.is_hatch_maloperation_incident(inc)]

        trends = analyzer.calculate_trends(hatch_incidents)

        assert isinstance(trends, dict)
        assert 'direction' in trends  # increasing, decreasing, or stable


class TestComprehensiveAnalysis:
    """Tests for comprehensive analysis combining all features."""

    def test_full_analysis_report_generation(self, hatch_maloperation_incidents):
        """Test generation of comprehensive analysis report."""
        from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
            HatchMaloperationAnalyzer
        )

        analyzer = HatchMaloperationAnalyzer()

        hatch_incidents = [inc for inc in hatch_maloperation_incidents
                          if analyzer.is_hatch_maloperation_incident(inc)]

        report = analyzer.generate_comprehensive_report(hatch_incidents)

        assert isinstance(report, dict)
        assert 'summary_statistics' in report
        assert 'location_analysis' in report
        assert 'consequence_analysis' in report
        assert 'contributing_factors' in report
        assert 'risk_assessment' in report
        assert 'recommendations' in report
        assert 'case_studies' in report
        assert 'trends' in report
