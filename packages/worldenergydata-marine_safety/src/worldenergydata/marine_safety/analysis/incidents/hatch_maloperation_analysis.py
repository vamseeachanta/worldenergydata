# ABOUTME: Facade module for hatch, door, and opening maloperation analysis in marine safety.
# ABOUTME: Re-exports from split modules for backward compatibility. Main entry point.

"""
Hatch/Door/Opening Maloperation Analysis Module

This module provides specialized analysis functionality for marine safety incidents
involving hatches, doors, and any opening maloperation. This includes watertight doors,
cargo hatches, access doors, covers, bulkhead doors, fire doors, and all vessel openings.

The functionality has been split into focused modules:
- hatch_patterns: Pattern definitions for detection and classification
- hatch_detection: LLM and regex-based detection
- hatch_analysis: Core analysis, risk scoring, recommendations
- hatch_statistics: Statistical analysis and trending
- hatch_reports: Report generation

This facade module maintains backward compatibility by providing the original
HatchMaloperationAnalyzer class that delegates to the split modules.

Key features:
- **LLM-based detection** using zero-shot classification
- Pattern matching for various hatch maloperation terminology (regex fallback)
- Hybrid detection mode combining LLM and regex for maximum accuracy
- Location classification (engine room vs. other enclosures)
- Consequence analysis (flooding, fire, personnel injury, etc.)
- Contributing factor identification
- Risk score calculation with confidence scoring
- Recommendation generation based on patterns
- Case study extraction for significant incidents
- Statistical analysis and trending
"""

from typing import Any, Dict, List, Optional

from .hatch_analysis import HatchAnalyzer

# Import split module classes
from .hatch_detection import LLM_AVAILABLE, HatchDetector

# Re-export patterns for backward compatibility
from .hatch_patterns import (
    CONSEQUENCE_PATTERNS,
    ENCLOSURE_PATTERNS,
    ENGINE_ROOM_PATTERNS,
    FACTOR_PATTERNS,
    HATCH_PATTERNS,
    HIGH_IMPACT_CONSEQUENCES,
    SEVERITY_SCORES,
)
from .hatch_reports import HatchReportGenerator
from .hatch_statistics import HatchStatistics


class HatchMaloperationAnalyzer:
    """
    Analyzer for hatch, door, and all opening maloperation incidents in marine safety.

    This class provides comprehensive analysis capabilities for incidents involving:
    - Hatches (cargo hatches, access hatches, engine room hatches, watertight hatches)
    - Doors (watertight doors, fire doors, bulkhead doors, access doors, cargo doors)
    - Covers (manhole covers, access covers)
    - Any vessel openings that failed, were left unsecured, or malfunctioned

    Detects failures, maloperation, and security issues across all vessel compartments
    including engine rooms, cargo holds, and other vessel enclosures.

    This class delegates to focused modules for implementation while maintaining
    the original API for backward compatibility.
    """

    # Class-level pattern attributes for backward compatibility
    HATCH_PATTERNS = HATCH_PATTERNS
    ENGINE_ROOM_PATTERNS = ENGINE_ROOM_PATTERNS
    ENCLOSURE_PATTERNS = ENCLOSURE_PATTERNS
    CONSEQUENCE_PATTERNS = CONSEQUENCE_PATTERNS
    FACTOR_PATTERNS = FACTOR_PATTERNS

    def __init__(
        self,
        use_llm: bool = True,
        llm_confidence_threshold: float = 0.7,
        fallback_to_regex: bool = True,
        llm_model_name: Optional[str] = None,
    ):
        """
        Initialize the HatchMaloperationAnalyzer.

        Args:
            use_llm: Whether to use LLM-based detection (default: True if available)
            llm_confidence_threshold: Minimum confidence score for LLM classification
            fallback_to_regex: Use regex detection if LLM confidence is low
            llm_model_name: Custom LLM model name

        Note:
            LLM detection requires transformers and torch libraries.
            If not installed, automatically falls back to regex-only mode.
        """
        # Initialize delegate modules
        self._detector = HatchDetector(
            use_llm=use_llm,
            llm_confidence_threshold=llm_confidence_threshold,
            fallback_to_regex=fallback_to_regex,
            llm_model_name=llm_model_name,
        )
        self._analyzer = HatchAnalyzer()
        self._statistics = HatchStatistics(self._analyzer)
        self._report_generator = HatchReportGenerator(
            detector=self._detector,
            analyzer=self._analyzer,
            statistics=self._statistics,
        )

        # Expose compiled patterns from detector for backward compatibility
        self.compiled_hatch_patterns = self._detector.compiled_hatch_patterns
        self.compiled_engine_room_patterns = (
            self._analyzer.compiled_engine_room_patterns
        )
        self.compiled_enclosure_patterns = self._analyzer.compiled_enclosure_patterns

        # Expose LLM configuration for backward compatibility
        self.use_llm = self._detector.use_llm
        self.llm_confidence_threshold = self._detector.llm_confidence_threshold
        self.fallback_to_regex = self._detector.fallback_to_regex
        self.llm_classifier = self._detector.llm_classifier

    # Detection methods - delegate to HatchDetector
    def is_hatch_maloperation_incident(
        self, incident: Dict[str, Any], return_details: bool = False
    ) -> bool | Dict[str, Any]:
        """
        Determine if an incident involves hatch/opening maloperation.

        Uses LLM-based detection (if enabled) with optional regex fallback.

        Args:
            incident: Incident dictionary with description field
            return_details: If True, return detailed detection information

        Returns:
            If return_details=False: Boolean indicating hatch incident
            If return_details=True: Dictionary with detection details
        """
        return self._detector.is_hatch_maloperation_incident(incident, return_details)

    def _detect_with_llm(self, description: str) -> Dict[str, Any]:
        """Use LLM to detect hatch maloperation incidents."""
        return self._detector._detect_with_llm(description)

    def _detect_with_regex(self, description: str) -> bool:
        """Use regex patterns to detect hatch maloperation incidents."""
        return self._detector._detect_with_regex(description)

    def extract_hatch_related_text(self, incident: Dict[str, Any]) -> Optional[str]:
        """Extract hatch-related text segments from incident description."""
        return self._detector.extract_hatch_related_text(incident)

    def get_detection_statistics(self) -> Dict[str, Any]:
        """Get statistics about detection methods used."""
        return self._detector.get_detection_statistics()

    def reset_detection_statistics(self) -> None:
        """Reset detection statistics counters."""
        self._detector.reset_detection_statistics()

    # Analysis methods - delegate to HatchAnalyzer
    def classify_location(self, incident: Dict[str, Any]) -> str:
        """Classify the location type of hatch maloperation."""
        return self._analyzer.classify_location(incident)

    def analyze_consequences(self, incident: Dict[str, Any]) -> List[str]:
        """Analyze and identify consequences of the incident."""
        return self._analyzer.analyze_consequences(incident)

    def identify_contributing_factors(self, incident: Dict[str, Any]) -> List[str]:
        """Identify contributing factors in the incident."""
        return self._analyzer.identify_contributing_factors(incident)

    def calculate_risk_score(self, incident: Dict[str, Any]) -> float:
        """Calculate a risk score for the incident (0-100 scale)."""
        return self._analyzer.calculate_risk_score(incident)

    def generate_recommendations(self, incident: Dict[str, Any]) -> List[str]:
        """Generate safety recommendations based on incident analysis."""
        return self._analyzer.generate_recommendations(incident)

    def is_significant_incident(self, incident: Dict[str, Any]) -> bool:
        """Determine if incident is significant enough for case study extraction."""
        return self._analyzer.is_significant_incident(incident)

    def extract_case_study(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed case study information from incident."""
        return self._analyzer.extract_case_study(incident)

    def _generate_summary(self, incident: Dict[str, Any]) -> str:
        """Generate a concise summary of the incident."""
        return self._analyzer._generate_summary(incident)

    def _extract_lessons_learned(self, incident: Dict[str, Any]) -> List[str]:
        """Extract key lessons learned from incident."""
        return self._analyzer._extract_lessons_learned(incident)

    # Statistics methods - delegate to HatchStatistics
    def get_location_statistics(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Generate location-based statistics for incidents."""
        return self._statistics.get_location_statistics(incidents)

    def get_consequence_statistics(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate consequence-based statistics."""
        return self._statistics.get_consequence_statistics(incidents)

    def get_severity_distribution(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Generate severity distribution statistics."""
        return self._statistics.get_severity_distribution(incidents)

    def get_time_series_data(
        self, incidents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate time series data for incident trending."""
        return self._statistics.get_time_series_data(incidents)

    def calculate_trends(self, incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trending information from incident data."""
        return self._statistics.calculate_trends(incidents)

    def aggregate_recommendations(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Aggregate recommendations from multiple incidents."""
        return self._statistics.aggregate_recommendations(incidents)

    def _analyze_contributing_factors(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Analyze distribution of contributing factors across incidents."""
        return self._statistics.analyze_contributing_factors(incidents)

    def _generate_risk_assessment(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate overall risk assessment from incidents."""
        return self._statistics.generate_risk_assessment(incidents)

    # Report methods - delegate to HatchReportGenerator
    def generate_comprehensive_report(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate comprehensive analysis report combining all features."""
        return self._report_generator.generate_comprehensive_report(incidents)


# Public API - re-export all components for direct access
__all__ = [
    # Main facade class (backward compatible)
    "HatchMaloperationAnalyzer",
    # Split module classes
    "HatchDetector",
    "HatchAnalyzer",
    "HatchStatistics",
    "HatchReportGenerator",
    # Pattern constants
    "HATCH_PATTERNS",
    "ENGINE_ROOM_PATTERNS",
    "ENCLOSURE_PATTERNS",
    "CONSEQUENCE_PATTERNS",
    "FACTOR_PATTERNS",
    "SEVERITY_SCORES",
    "HIGH_IMPACT_CONSEQUENCES",
    # LLM availability flag
    "LLM_AVAILABLE",
]
