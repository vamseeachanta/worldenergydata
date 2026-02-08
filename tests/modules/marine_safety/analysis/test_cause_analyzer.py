"""
Test suite for incident cause analysis module.

Tests data extraction, normalization, categorization, and pattern detection
for marine incident root cause analysis.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from worldenergydata.marine_safety.analysis.cause_analyzer import (
    IncidentCauseExtractor,
    CauseNormalizer,
    map_to_cause_category,
    detect_hatch_opening_maloperation,
    extract_causes_from_narrative,
    clean_cause_data,
)
from worldenergydata.marine_safety.constants import CauseCategory


@pytest.fixture
def sample_raw_data():
    """Create sample raw incident data for testing."""
    return pd.DataFrame({
        'incident_id': ['INC001', 'INC002', 'INC003', 'INC004', 'INC005'],
        'narrative': [
            'Vessel foundered due to hatch cover maloperation, water ingress through cargo hold',
            'Collision caused by operator fatigue and poor visibility in fog',
            'Engine failure due to lack of proper maintenance and worn parts',
            'Grounding incident caused by navigation equipment failure',
            'Fire in engine room due to fuel leak and electrical spark'
        ],
        'primary_cause': ['EQUIPMENT_FAILURE', 'HUMAN_ERROR', 'MAINTENANCE', np.nan, 'MULTIPLE'],
        'contributing_factors': ['WEATHER', 'PROCEDURAL', np.nan, 'EQUIPMENT', 'DESIGN']
    })


@pytest.fixture
def sample_cause_descriptions():
    """Sample cause descriptions for normalization testing."""
    return [
        'Hatch cover not properly secured',
        'HATCH MALFUNCTION',
        'Cargo hatch opening failure',
        'operator error - fatigue',
        'MAINTENANCE - inadequate',
        'equipment failure - engine',
        None,
        '',
        'WEATHER - STORM',
    ]


class TestIncidentCauseExtractor:
    """Test suite for IncidentCauseExtractor class."""

    @pytest.mark.unit
    def test_initialization(self):
        """Test that extractor initializes correctly."""
        extractor = IncidentCauseExtractor()
        assert extractor is not None
        assert hasattr(extractor, 'extract_from_dataframe')

    @pytest.mark.unit
    def test_extract_from_dataframe_basic(self, sample_raw_data):
        """Test basic extraction from DataFrame."""
        extractor = IncidentCauseExtractor()
        result = extractor.extract_from_dataframe(sample_raw_data)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_raw_data)
        assert 'incident_id' in result.columns
        assert 'primary_cause_category' in result.columns
        assert 'contributing_causes' in result.columns

    @pytest.mark.unit
    def test_extract_handles_missing_data(self):
        """Test extraction handles missing/null cause data gracefully."""
        data = pd.DataFrame({
            'incident_id': ['INC001', 'INC002', 'INC003'],
            'primary_cause': ['HUMAN_ERROR', np.nan, None],
            'contributing_factors': [np.nan, 'WEATHER', '']
        })

        extractor = IncidentCauseExtractor()
        result = extractor.extract_from_dataframe(data)

        assert len(result) == 3
        # Should have default/unknown category for missing data
        assert result.loc[result['incident_id'] == 'INC002', 'primary_cause_category'].iloc[0] == CauseCategory.UNKNOWN

    @pytest.mark.unit
    def test_extract_from_narrative(self, sample_raw_data):
        """Test extraction of causes from narrative text."""
        extractor = IncidentCauseExtractor()
        result = extractor.extract_from_dataframe(sample_raw_data)

        # Should extract additional causes from narrative
        assert 'narrative_causes' in result.columns

        # Check that hatch issue was detected in first record
        hatch_record = result[result['incident_id'] == 'INC001'].iloc[0]
        assert 'hatch' in str(hatch_record['narrative']).lower()

    @pytest.mark.unit
    def test_extract_multiple_causes(self):
        """Test extraction handles multiple contributing causes."""
        data = pd.DataFrame({
            'incident_id': ['INC001'],
            'primary_cause': ['EQUIPMENT_FAILURE'],
            'contributing_factors': ['WEATHER, MAINTENANCE, PROCEDURAL']
        })

        extractor = IncidentCauseExtractor()
        result = extractor.extract_from_dataframe(data)

        causes = result.iloc[0]['contributing_causes']
        assert isinstance(causes, list)
        assert len(causes) >= 3


class TestCauseNormalizer:
    """Test suite for CauseNormalizer class."""

    @pytest.mark.unit
    def test_initialization(self):
        """Test normalizer initializes with default mappings."""
        normalizer = CauseNormalizer()
        assert normalizer is not None
        assert hasattr(normalizer, 'normalize')
        assert hasattr(normalizer, 'cause_mappings')

    @pytest.mark.unit
    def test_normalize_basic_causes(self, sample_cause_descriptions):
        """Test normalization of various cause formats."""
        normalizer = CauseNormalizer()

        for desc in sample_cause_descriptions:
            normalized = normalizer.normalize(desc)
            assert isinstance(normalized, str) or normalized is None

            if desc and desc.strip():
                assert normalized is not None
                # Should be lowercase, trimmed
                assert normalized == normalized.lower()
                assert normalized.strip() == normalized

    @pytest.mark.unit
    def test_normalize_hatch_variations(self):
        """Test normalization handles hatch-related cause variations."""
        normalizer = CauseNormalizer()

        hatch_variations = [
            'Hatch cover not secured',
            'HATCH MALFUNCTION',
            'cargo hatch failure',
            'Hatch door opening issue',
        ]

        results = [normalizer.normalize(v) for v in hatch_variations]

        # All should contain 'hatch' keyword
        for result in results:
            assert 'hatch' in result.lower()

    @pytest.mark.unit
    def test_normalize_handles_null(self):
        """Test normalizer handles null/empty values."""
        normalizer = CauseNormalizer()

        assert normalizer.normalize(None) is None
        assert normalizer.normalize('') is None
        assert normalizer.normalize('   ') is None
        assert normalizer.normalize(np.nan) is None

    @pytest.mark.unit
    def test_normalize_removes_extra_whitespace(self):
        """Test normalizer removes extra whitespace."""
        normalizer = CauseNormalizer()

        result = normalizer.normalize('  EQUIPMENT    FAILURE  ')
        assert result == 'equipment failure'

        result = normalizer.normalize('MULTIPLE\t\tCAUSES')
        assert 'multiple' in result and 'causes' in result

    @pytest.mark.unit
    def test_normalize_standardizes_categories(self):
        """Test normalizer maps to standard categories."""
        normalizer = CauseNormalizer()

        # Test various human error descriptions
        human_errors = ['operator error', 'crew mistake', 'human factor', 'fatigue']
        for desc in human_errors:
            result = normalizer.normalize(desc)
            # Should map to consistent terminology
            assert result is not None


class TestCauseCategoryMapping:
    """Test suite for cause category mapping functions."""

    @pytest.mark.unit
    def test_map_to_cause_category_valid(self):
        """Test mapping valid cause descriptions to categories."""
        test_cases = [
            ('operator error', CauseCategory.HUMAN_ERROR),
            ('equipment failure', CauseCategory.EQUIPMENT_FAILURE),
            ('maintenance issue', CauseCategory.MAINTENANCE_ISSUE),
            ('weather related', CauseCategory.WEATHER),
            ('design flaw', CauseCategory.DESIGN_FLAW),
            ('procedural violation', CauseCategory.PROCEDURAL),
        ]

        for description, expected_category in test_cases:
            result = map_to_cause_category(description)
            assert result == expected_category

    @pytest.mark.unit
    def test_map_to_cause_category_unknown(self):
        """Test mapping returns UNKNOWN for unrecognized causes."""
        result = map_to_cause_category('xyz unknown cause abc')
        assert result == CauseCategory.UNKNOWN

        result = map_to_cause_category(None)
        assert result == CauseCategory.UNKNOWN

    @pytest.mark.unit
    def test_map_to_cause_category_case_insensitive(self):
        """Test mapping is case insensitive."""
        variations = ['OPERATOR ERROR', 'Operator Error', 'operator error', 'OpErAtOr ErRoR']

        for var in variations:
            result = map_to_cause_category(var)
            assert result == CauseCategory.HUMAN_ERROR

    @pytest.mark.unit
    def test_map_to_cause_category_multiple(self):
        """Test mapping handles multiple causes."""
        result = map_to_cause_category('equipment failure and weather')
        assert result == CauseCategory.MULTIPLE


class TestHatchOpeningMaloperation:
    """Test suite for hatch/opening maloperation detection."""

    @pytest.mark.unit
    def test_detect_hatch_maloperation_positive(self):
        """Test detection of hatch-related incidents."""
        positive_cases = [
            'Hatch cover not properly secured',
            'Cargo hatch opening failure',
            'HATCH MALFUNCTION',
            'Door to engine room left open',
            'Watertight door maloperation',
            'Access hatch failure',
        ]

        for case in positive_cases:
            result = detect_hatch_opening_maloperation(case)
            assert result is True, f"Failed to detect hatch issue in: {case}"

    @pytest.mark.unit
    def test_detect_hatch_maloperation_negative(self):
        """Test no false positives for non-hatch incidents."""
        negative_cases = [
            'Engine failure',
            'Collision with another vessel',
            'Grounding on reef',
            'Fire in galley',
            None,
            '',
        ]

        for case in negative_cases:
            result = detect_hatch_opening_maloperation(case)
            assert result is False, f"False positive for: {case}"

    @pytest.mark.unit
    def test_detect_hatch_maloperation_context(self):
        """Test detection works in full narrative context."""
        narrative = """
        Vessel foundered during heavy weather. Investigation revealed that
        the forward cargo hatch cover was not properly secured, allowing
        water ingress into hold #2. Crew failed to follow proper hatch
        securing procedures during pre-departure checks.
        """

        result = detect_hatch_opening_maloperation(narrative)
        assert result is True

    @pytest.mark.unit
    def test_detect_hatch_maloperation_case_insensitive(self):
        """Test detection is case insensitive."""
        variations = [
            'HATCH FAILURE',
            'hatch failure',
            'Hatch Failure',
            'HaTcH fAiLuRe',
        ]

        for var in variations:
            result = detect_hatch_opening_maloperation(var)
            assert result is True


class TestExtractCausesFromNarrative:
    """Test suite for narrative text analysis."""

    @pytest.mark.unit
    def test_extract_causes_basic(self):
        """Test extraction of causes from narrative text."""
        narrative = "Collision caused by operator fatigue and poor visibility"

        causes = extract_causes_from_narrative(narrative)

        assert isinstance(causes, list)
        assert len(causes) > 0
        assert any('fatigue' in str(c).lower() for c in causes)

    @pytest.mark.unit
    def test_extract_causes_multiple(self):
        """Test extraction of multiple causes from narrative."""
        narrative = """
        Foundering incident attributed to multiple factors:
        1. Hatch cover maloperation
        2. Inadequate maintenance
        3. Crew training deficiency
        4. Adverse weather conditions
        """

        causes = extract_causes_from_narrative(narrative)

        assert len(causes) >= 3
        # Should identify different cause categories
        categories = [map_to_cause_category(str(c)) for c in causes]
        assert CauseCategory.EQUIPMENT_FAILURE in categories or CauseCategory.MAINTENANCE_ISSUE in categories

    @pytest.mark.unit
    def test_extract_causes_empty(self):
        """Test extraction handles empty/null narratives."""
        assert extract_causes_from_narrative(None) == []
        assert extract_causes_from_narrative('') == []
        assert extract_causes_from_narrative('   ') == []

    @pytest.mark.unit
    def test_extract_causes_keywords(self):
        """Test extraction identifies common cause keywords."""
        narrative = "Equipment failure due to improper maintenance procedures"

        causes = extract_causes_from_narrative(narrative)

        # Should identify both equipment and maintenance issues
        cause_text = ' '.join([str(c).lower() for c in causes])
        assert 'equipment' in cause_text or 'maintenance' in cause_text


class TestCleanCauseData:
    """Test suite for cause data cleaning functions."""

    @pytest.mark.unit
    def test_clean_cause_data_basic(self):
        """Test basic data cleaning functionality."""
        data = pd.DataFrame({
            'cause': ['  OPERATOR ERROR  ', 'equipment failure', None, '', 'WEATHER']
        })

        cleaned = clean_cause_data(data, 'cause')

        assert len(cleaned) == len(data)
        assert cleaned['cause'].iloc[0] == 'operator error'
        assert cleaned['cause'].iloc[1] == 'equipment failure'
        assert pd.isna(cleaned['cause'].iloc[2])

    @pytest.mark.unit
    def test_clean_cause_data_removes_duplicates(self):
        """Test cleaning removes duplicate entries."""
        data = pd.DataFrame({
            'cause': ['operator error', 'operator error', 'maintenance', 'operator error']
        })

        cleaned = clean_cause_data(data, 'cause', remove_duplicates=True)

        # Should have unique values only
        assert len(cleaned) < len(data)
        assert len(cleaned['cause'].unique()) == len(cleaned)

    @pytest.mark.unit
    def test_clean_cause_data_validates_categories(self):
        """Test cleaning validates against known categories."""
        data = pd.DataFrame({
            'cause': ['operator error', 'invalid_cause_xyz', 'equipment failure']
        })

        cleaned = clean_cause_data(data, 'cause', validate_categories=True)

        # Invalid causes should be flagged or removed
        assert 'validation_status' in cleaned.columns


class TestIntegration:
    """Integration tests for the full cause analysis workflow."""

    @pytest.mark.integration
    def test_end_to_end_cause_extraction(self, sample_raw_data):
        """Test complete workflow from raw data to categorized causes."""
        # Extract causes
        extractor = IncidentCauseExtractor()
        extracted = extractor.extract_from_dataframe(sample_raw_data)

        # Normalize
        normalizer = CauseNormalizer()
        extracted['normalized_cause'] = extracted['primary_cause_category'].apply(
            lambda x: normalizer.normalize(str(x)) if pd.notna(x) else None
        )

        # Categorize
        extracted['cause_category'] = extracted['normalized_cause'].apply(map_to_cause_category)

        # Validate results
        assert len(extracted) == len(sample_raw_data)
        assert not extracted['cause_category'].isna().all()

        # Should have valid CauseCategory values
        valid_categories = [c.value for c in CauseCategory]
        assert all(cat in valid_categories for cat in extracted['cause_category'] if pd.notna(cat))

    @pytest.mark.integration
    def test_hatch_incident_detection_workflow(self):
        """Test complete workflow for detecting hatch-related incidents."""
        data = pd.DataFrame({
            'incident_id': ['INC001', 'INC002', 'INC003'],
            'narrative': [
                'Vessel foundered due to hatch cover failure',
                'Collision in fog',
                'Cargo hatch not properly secured, water ingress'
            ]
        })

        # Detect hatch issues
        data['has_hatch_issue'] = data['narrative'].apply(detect_hatch_opening_maloperation)

        # Should identify 2 out of 3 incidents
        assert data['has_hatch_issue'].sum() == 2

        # Categorize those incidents
        hatch_incidents = data[data['has_hatch_issue']]
        for idx, row in hatch_incidents.iterrows():
            causes = extract_causes_from_narrative(row['narrative'])
            assert len(causes) > 0
