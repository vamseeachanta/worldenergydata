# ABOUTME: Specialized analysis module for hatch, door, and opening maloperation incidents in marine safety.
# ABOUTME: Identifies, classifies, and analyzes all types of opening-related incidents using LLM-based detection and regex patterns.

"""
Hatch/Door/Opening Maloperation Analysis Module

This module provides specialized analysis functionality for marine safety incidents
involving hatches, doors, and any opening maloperation. This includes watertight doors,
cargo hatches, access doors, covers, bulkhead doors, fire doors, and all vessel openings.
It identifies relevant incidents, classifies them by location, analyzes consequences,
identifies contributing factors, calculates risk scores, and generates actionable safety
recommendations.

Key features:
- **LLM-based detection** using zero-shot classification (NEW)
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

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

# LLM classifier import (optional - graceful degradation if not installed)
try:
    from ..llm_classifier import LLMIncidentClassifier

    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logging.warning(
        "LLM classifier not available. Install with: pip install transformers torch. "
        "Falling back to regex-only detection."
    )


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
    """

    # Pattern matching for hatch maloperation terminology variations
    # Expanded to include all door, hatch, and opening incidents
    HATCH_PATTERNS = [
        # Hatch-specific patterns
        r"\bhatch\s+maloperation\b",
        r"\bhatch\s+failure\b",
        r"\bhatch.*?failed",
        r"\bhatch.*?improperly\s+secured\b",
        r"\bhatch.*?not\s+secured\b",
        r"\bhatch.*?unsecured\b",
        r"\bhatch.*?left\s+open\b",
        r"\bhatch.*?mechanism.*?failed\b",
        r"\bhatch\s+seal\s+failure\b",
        r"\baccess\s+hatch\b",
        r"\bengine\s+room\s+hatch\b",
        r"\bcargo\s+hatch\b",
        r"\bwatertight\s+hatch\b",
        # Door-specific patterns
        r"\bdoor\s+maloperation\b",
        r"\bdoor\s+failure\b",
        r"\bdoor.*?failed",
        r"\bdoor.*?improperly\s+secured\b",
        r"\bdoor.*?not\s+secured\b",
        r"\bdoor.*?unsecured\b",
        r"\bdoor.*?left\s+open\b",
        r"\bdoor.*?mechanism.*?failed\b",
        r"\bwatertight\s+door\b",
        r"\baccess\s+door\b",
        r"\bcargo\s+door\b",
        r"\bbulkhead\s+door\b",
        r"\bfire\s+door\b",
        # General opening patterns
        r"\bopening\s+maloperation\b",
        r"\bopening\s+failure\b",
        r"\bopening.*?failed",
        r"\bopening.*?not\s+secured\b",
        r"\bopening.*?left\s+open\b",
        # Cover and seal patterns
        r"\baccess\s+cover\s+maloperation\b",
        r"\baccess\s+cover\s+failure\b",
        r"\bmanhole\s+cover\b",
        r"\bseal\s+failure\b",
        r"\bcover.*?unsecured\b",
        r"\bcover.*?not\s+secured\b",
        # Hardware failure patterns
        r"\bhinge.*?failure\b",
        r"\blatch.*?failure\b",
        r"\block.*?failure\b",
        r"\bfastener.*?failure\b",
        r"\bclosure.*?failure\b",
        # Consequence-based patterns (opening-related flooding/ingress)
        r"\bflooding.*?through.*?(?:hatch|door|opening|cover)\b",
        r"\bwater\s+ingress.*?(?:hatch|door|opening|cover)\b",
        r"\b(?:hatch|door|opening|cover).*?flooding\b",
    ]

    # Location classification patterns
    ENGINE_ROOM_PATTERNS = [
        r"\bengine\s+room\b",
        r"\bmachinery\s+space\b",
        r"\bmain\s+engine\b",
        r"\bengine\s+compartment\b",
    ]

    ENCLOSURE_PATTERNS = [
        r"\benclosure\b",
        r"\bcompartment\b",
        r"\bdeck\s+access\b",
        r"\bstorage\s+space\b",
        r"\bcargo\s+hold\b",
        r"\btank\s+access\b",
    ]

    # Consequence patterns
    CONSEQUENCE_PATTERNS = {
        "flooding": [
            r"\bflood(?:ing|ed)\b",
            r"\bwater\s+ingress\b",
            r"\btook\s+on\s+water\b",
            r"\bbilge\s+pumps?\b",
        ],
        "fire": [
            r"\bfire\b",
            r"\bignition\b",
            r"\bburns?\b",
            r"\bflames?\b",
            r"\bfire\s+suppression\b",
        ],
        "personnel_injury": [
            r"\binjur(?:y|ies|ed)\b",
            r"\bhurt\b",
            r"\bfracture\b",
            r"\bwound(?:ed|s)?\b",
        ],
        "fatality": [
            r"\bfatalit(?:y|ies)\b",
            r"\bdeath(?:s)?\b",
            r"\blost\b.*\bcrew\b",
            r"\bkilled\b",
        ],
        "equipment_damage": [
            r"\bequipment\s+damage\b",
            r"\bdamaged?\b",
            r"\bfailure\b",
        ],
        "vessel_stability": [
            r"\blist(?:ed|ing)\b",
            r"\bstability\b",
            r"\bcapsize\b",
            r"\bheeling\b",
        ],
        "near_miss": [
            r"\bnear\s+miss\b",
            r"\bpreventive\b",
            r"\bdetected\s+during\s+inspection\b",
            r"\bcould\s+have\b",
        ],
    }

    # Contributing factor patterns
    FACTOR_PATTERNS = {
        "human_error": [
            r"\bcrew.*?failed\b",
            r"\bfailed\s+to\s+secure\b",
            r"\bfailed\s+to\s+properly\b",
            r"\bimproperly\b",
            r"\bnegligence\b",
            r"\binadequate\s+training\b",
        ],
        "maintenance_issue": [
            r"\bmaintenance\b",
            r"\bimproperly\s+maintained\b",
            r"\black\s+of\s+maintenance\b",
            r"\bpreventive\s+maintenance\b",
            r"\bwear\s+and\s+tear\b",
        ],
        "equipment_failure": [
            r"\bequipment\s+failure\b",
            r"\bmechanism.*?failed\b",
            r"\bseal\s+failure\b",
            r"\bdefective\b",
            r"\bmalfunctioned\b",
        ],
        "weather": [
            r"\bheavy\s+seas?\b",
            r"\bstorm\b",
            r"\brough\s+(?:seas?|weather)\b",
            r"\bhigh\s+winds?\b",
            r"\badverse\s+(?:weather|conditions)\b",
        ],
        "design_flaw": [
            r"\bdesign\s+flaw\b",
            r"\binadequate\s+design\b",
            r"\bstructural\s+weakness\b",
        ],
    }

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
            llm_confidence_threshold: Minimum confidence score for LLM classification (default: 0.7)
            fallback_to_regex: Use regex detection if LLM confidence is low (default: True)
            llm_model_name: Custom LLM model name (default: uses LLMIncidentClassifier default)

        Note:
            LLM detection requires transformers and torch libraries.
            If not installed, automatically falls back to regex-only mode.
        """
        # Compile regex patterns for better performance
        self.compiled_hatch_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.HATCH_PATTERNS
        ]
        self.compiled_engine_room_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.ENGINE_ROOM_PATTERNS
        ]
        self.compiled_enclosure_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.ENCLOSURE_PATTERNS
        ]

        # LLM configuration
        self.use_llm = use_llm and LLM_AVAILABLE
        self.llm_confidence_threshold = llm_confidence_threshold
        self.fallback_to_regex = fallback_to_regex

        # Initialize LLM classifier if enabled
        self.llm_classifier = None
        if self.use_llm:
            try:
                if llm_model_name:
                    self.llm_classifier = LLMIncidentClassifier(
                        model_name=llm_model_name
                    )
                else:
                    self.llm_classifier = LLMIncidentClassifier()
                logging.info("LLM-based hatch detection enabled")
            except Exception as e:
                logging.warning(
                    f"Failed to initialize LLM classifier: {e}. Falling back to regex."
                )
                self.use_llm = False
                self.llm_classifier = None
        else:
            if use_llm and not LLM_AVAILABLE:
                logging.info(
                    "LLM requested but not available. Using regex-only detection."
                )

        # Detection statistics
        self._detection_stats = {
            "llm_detections": 0,
            "regex_detections": 0,
            "hybrid_detections": 0,
            "total_analyzed": 0,
        }

    def is_hatch_maloperation_incident(
        self, incident: Dict[str, Any], return_details: bool = False
    ) -> bool | Dict[str, Any]:
        """
        Determine if an incident involves hatch/opening maloperation.

        Uses LLM-based detection (if enabled) with optional regex fallback for
        maximum accuracy and coverage.

        Args:
            incident: Incident dictionary with description field
            return_details: If True, return detailed detection information

        Returns:
            If return_details=False: Boolean indicating hatch incident
            If return_details=True: Dictionary with detection details including:
                - is_hatch_incident: bool
                - detection_method: 'llm' | 'regex' | 'hybrid' | 'none'
                - llm_confidence: float (if LLM used)
                - llm_reasoning: str (if LLM used)
                - regex_matched: bool
        """
        description = incident.get("description", "")
        if not description:
            return (
                False
                if not return_details
                else {
                    "is_hatch_incident": False,
                    "detection_method": "none",
                    "reason": "No description provided",
                }
            )

        self._detection_stats["total_analyzed"] += 1

        # Try LLM detection first (if enabled)
        llm_result = None
        llm_detected = False
        llm_confidence = 0.0

        if self.use_llm and self.llm_classifier:
            try:
                llm_result = self._detect_with_llm(description)
                llm_detected = llm_result["is_hatch_incident"]
                llm_confidence = llm_result["confidence"]
            except Exception as e:
                logging.warning(f"LLM detection failed: {e}. Falling back to regex.")
                llm_result = None

        # Try regex detection
        regex_detected = self._detect_with_regex(description)

        # Determine final result based on detection mode
        if llm_result and llm_confidence >= self.llm_confidence_threshold:
            # High-confidence LLM detection
            is_hatch = llm_detected
            method = "llm"
            self._detection_stats["llm_detections"] += 1

            # If regex also matches, it's a hybrid detection
            if regex_detected and llm_detected:
                method = "hybrid"
                self._detection_stats["hybrid_detections"] += 1
                self._detection_stats["llm_detections"] -= 1  # Don't double count

        elif self.fallback_to_regex or not self.use_llm:
            # Use regex (either as fallback or primary method)
            is_hatch = regex_detected
            method = "regex"
            if regex_detected:
                self._detection_stats["regex_detections"] += 1
        else:
            # Low confidence LLM, no regex fallback
            is_hatch = llm_detected if llm_result else False
            method = "llm" if llm_result else "none"

        # Return simple boolean or detailed result
        if not return_details:
            return is_hatch

        details = {
            "is_hatch_incident": is_hatch,
            "detection_method": method,
            "regex_matched": regex_detected,
        }

        if llm_result:
            details["llm_confidence"] = llm_confidence
            details["llm_reasoning"] = llm_result.get("reasoning", "")
            details["matched_phrases"] = llm_result.get("matched_phrases", [])

        return details

    def _detect_with_llm(self, description: str) -> Dict[str, Any]:
        """
        Use LLM to detect hatch maloperation incidents.

        Args:
            description: Incident description text

        Returns:
            Dictionary with LLM detection results
        """
        if not self.llm_classifier:
            raise RuntimeError("LLM classifier not initialized")

        return self.llm_classifier.detect_hatch_maloperation(description)

    def _detect_with_regex(self, description: str) -> bool:
        """
        Use regex patterns to detect hatch maloperation incidents.

        Args:
            description: Incident description text

        Returns:
            True if any hatch pattern matches, False otherwise
        """
        for pattern in self.compiled_hatch_patterns:
            if pattern.search(description):
                return True
        return False

    def get_detection_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about detection methods used.

        Returns:
            Dictionary with detection statistics including:
                - total_analyzed: Total incidents analyzed
                - llm_detections: Incidents detected by LLM only
                - regex_detections: Incidents detected by regex only
                - hybrid_detections: Incidents detected by both methods
                - detection_mode: Current detection configuration
        """
        stats = self._detection_stats.copy()
        stats["detection_mode"] = {
            "llm_enabled": self.use_llm,
            "regex_fallback": self.fallback_to_regex,
            "llm_threshold": self.llm_confidence_threshold,
        }

        # Calculate percentages
        total = stats["total_analyzed"]
        if total > 0:
            stats["llm_percentage"] = round(stats["llm_detections"] / total * 100, 2)
            stats["regex_percentage"] = round(
                stats["regex_detections"] / total * 100, 2
            )
            stats["hybrid_percentage"] = round(
                stats["hybrid_detections"] / total * 100, 2
            )

        return stats

    def reset_detection_statistics(self):
        """Reset detection statistics counters."""
        self._detection_stats = {
            "llm_detections": 0,
            "regex_detections": 0,
            "hybrid_detections": 0,
            "total_analyzed": 0,
        }

    def extract_hatch_related_text(self, incident: Dict[str, Any]) -> Optional[str]:
        """
        Extract hatch-related text segments from incident description.

        Args:
            incident: Incident dictionary with description field

        Returns:
            Extracted hatch-related text or None if not found
        """
        description = incident.get("description", "")
        if not description:
            return None

        # Find sentences containing hatch-related terms
        sentences = re.split(r"[.!?]", description)
        relevant_sentences = []

        for sentence in sentences:
            for pattern in self.compiled_hatch_patterns:
                if pattern.search(sentence):
                    relevant_sentences.append(sentence.strip())
                    break

        if relevant_sentences:
            return " ".join(relevant_sentences)

        return None

    def classify_location(self, incident: Dict[str, Any]) -> str:
        """
        Classify the location type of hatch maloperation.

        Args:
            incident: Incident dictionary with description field

        Returns:
            Location classification: 'engine_room', 'other_enclosure', or 'unknown'
        """
        description = incident.get("description", "")
        if not description:
            return "unknown"

        # Check for engine room patterns
        for pattern in self.compiled_engine_room_patterns:
            if pattern.search(description):
                return "engine_room"

        # Check for other enclosure patterns
        for pattern in self.compiled_enclosure_patterns:
            if pattern.search(description):
                # More specific classification for deck access
                if re.search(r"\bdeck\s+access\b", description, re.IGNORECASE):
                    return "deck_access"
                return "other_enclosure"

        return "unknown"

    def analyze_consequences(self, incident: Dict[str, Any]) -> List[str]:
        """
        Analyze and identify consequences of the incident.

        Args:
            incident: Incident dictionary

        Returns:
            List of consequence types identified
        """
        description = incident.get("description", "")
        consequences = []

        # Check description against consequence patterns
        for consequence_type, patterns in self.CONSEQUENCE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    consequences.append(consequence_type)
                    break

        # Also check explicit consequence indicators
        if incident.get("fatalities", 0) > 0:
            if "fatality" not in consequences:
                consequences.append("fatality")

        if incident.get("injuries", 0) > 0:
            if "personnel_injury" not in consequences:
                consequences.append("personnel_injury")

        return list(set(consequences))  # Remove duplicates

    def identify_contributing_factors(self, incident: Dict[str, Any]) -> List[str]:
        """
        Identify contributing factors in the incident.

        Args:
            incident: Incident dictionary

        Returns:
            List of contributing factor types identified
        """
        description = incident.get("description", "")
        factors = []

        for factor_type, patterns in self.FACTOR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    factors.append(factor_type)
                    break

        return list(set(factors))

    def calculate_risk_score(self, incident: Dict[str, Any]) -> float:
        """
        Calculate a risk score for the incident (0-100 scale).

        Risk scoring considers:
        - Severity level
        - Casualties (fatalities and injuries)
        - Consequences
        - Estimated damage
        - Location criticality

        Args:
            incident: Incident dictionary

        Returns:
            Risk score between 0 and 100
        """
        score = 0.0

        # Severity level contribution (0-30 points)
        severity = incident.get("severity", "Minor")
        severity_scores = {
            "Minor": 10,
            "Moderate": 15,
            "Serious": 20,
            "Critical": 25,
            "Catastrophic": 30,
        }
        score += severity_scores.get(severity, 10)

        # Fatalities (0-40 points)
        fatalities = incident.get("fatalities", 0)
        if fatalities > 0:
            score += min(40, 20 + (fatalities * 10))

        # Injuries (0-20 points)
        injuries = incident.get("injuries", 0)
        if injuries > 0:
            score += min(20, 10 + (injuries * 2))

        # Consequences (0-15 points)
        consequences = self.analyze_consequences(incident)
        high_impact_consequences = ["flooding", "fire", "fatality", "vessel_stability"]
        consequence_count = sum(
            1 for c in consequences if c in high_impact_consequences
        )
        score += min(15, consequence_count * 5)

        # Damage estimate (0-10 points)
        damage = incident.get("estimated_damage_usd", 0)
        if damage >= 1000000:
            score += 10
        elif damage >= 500000:
            score += 7
        elif damage >= 100000:
            score += 5
        elif damage >= 50000:
            score += 3
        elif damage > 0:
            score += 1

        # Location criticality (0-5 points)
        location_type = self.classify_location(incident)
        if location_type == "engine_room":
            score += 5  # Engine room is critical

        # Cap at 100
        return min(100.0, score)

    def generate_recommendations(self, incident: Dict[str, Any]) -> List[str]:
        """
        Generate safety recommendations based on incident analysis.

        Args:
            incident: Incident dictionary

        Returns:
            List of specific recommendations
        """
        recommendations = []
        factors = self.identify_contributing_factors(incident)
        consequences = self.analyze_consequences(incident)
        location = self.classify_location(incident)

        # Recommendations based on contributing factors
        if "human_error" in factors:
            recommendations.append(
                "Implement enhanced crew training on proper hatch securing procedures"
            )
            recommendations.append(
                "Establish mandatory pre-departure hatch security checklist"
            )

        if "maintenance_issue" in factors:
            recommendations.append(
                "Increase frequency of hatch mechanism inspection and maintenance"
            )
            recommendations.append(
                "Implement preventive maintenance schedule for all hatch systems"
            )

        if "equipment_failure" in factors:
            recommendations.append(
                "Consider replacement or upgrade of aging hatch equipment"
            )
            recommendations.append(
                "Conduct engineering assessment of hatch design and specifications"
            )

        if "weather" in factors:
            recommendations.append(
                "Review and enhance procedures for securing hatches in adverse weather"
            )
            recommendations.append(
                "Install weather monitoring and alert systems for hatch operations"
            )

        # Recommendations based on consequences
        if "flooding" in consequences:
            recommendations.append(
                "Install or upgrade bilge alarm systems in affected compartments"
            )
            recommendations.append(
                "Conduct flooding scenario drills specific to hatch failure events"
            )

        if "fire" in consequences:
            recommendations.append(
                "Review ventilation system design and fire prevention measures"
            )
            recommendations.append(
                "Enhance fire detection and suppression capabilities in affected areas"
            )

        if "personnel_injury" in consequences or "fatality" in consequences:
            recommendations.append(
                "Implement mandatory safety barriers and warning systems for hatch operations"
            )
            recommendations.append(
                "Require personal protective equipment for all personnel working with hatches"
            )

        # Location-specific recommendations
        if location == "engine_room":
            recommendations.append(
                "Prioritize engine room hatch integrity in vessel safety management system"
            )

        # General recommendations if none were added
        if not recommendations:
            recommendations.append(
                "Conduct comprehensive hatch system assessment and risk analysis"
            )

        return recommendations

    def is_significant_incident(self, incident: Dict[str, Any]) -> bool:
        """
        Determine if incident is significant enough for case study extraction.

        Criteria for significance:
        - Fatalities present
        - Multiple injuries (>2)
        - High damage estimate (>$500k)
        - Catastrophic or Critical severity
        - Multiple high-impact consequences

        Args:
            incident: Incident dictionary

        Returns:
            True if incident is significant, False otherwise
        """
        # Fatalities always make it significant
        if incident.get("fatalities", 0) > 0:
            return True

        # Multiple serious injuries
        if incident.get("injuries", 0) > 2:
            return True

        # High damage
        if incident.get("estimated_damage_usd", 0) > 500000:
            return True

        # High severity
        severity = incident.get("severity", "Minor")
        if severity in ["Catastrophic", "Critical"]:
            return True

        # Multiple high-impact consequences
        consequences = self.analyze_consequences(incident)
        high_impact = ["flooding", "fire", "fatality", "vessel_stability"]
        if len([c for c in consequences if c in high_impact]) >= 2:
            return True

        return False

    def extract_case_study(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract detailed case study information from incident.

        Args:
            incident: Incident dictionary

        Returns:
            Case study dictionary with structured information
        """
        case_study = {
            "incident_id": incident.get("incident_id"),
            "date": incident.get("date"),
            "location": incident.get("location"),
            "summary": self._generate_summary(incident),
            "location_type": self.classify_location(incident),
            "contributing_factors": self.identify_contributing_factors(incident),
            "consequences": self.analyze_consequences(incident),
            "casualties": {
                "fatalities": incident.get("fatalities", 0),
                "injuries": incident.get("injuries", 0),
            },
            "damage_estimate": incident.get("estimated_damage_usd", 0),
            "risk_score": self.calculate_risk_score(incident),
            "lessons_learned": self._extract_lessons_learned(incident),
            "recommendations": self.generate_recommendations(incident),
        }

        return case_study

    def _generate_summary(self, incident: Dict[str, Any]) -> str:
        """Generate a concise summary of the incident."""
        description = incident.get("description", "")

        # Extract first 200 characters or first two sentences
        sentences = re.split(r"[.!?]", description)
        if len(sentences) >= 2:
            summary = ". ".join(sentences[:2]) + "."
        else:
            summary = (
                description[:200] + "..." if len(description) > 200 else description
            )

        return summary

    def _extract_lessons_learned(self, incident: Dict[str, Any]) -> List[str]:
        """Extract key lessons learned from incident."""
        lessons = []
        factors = self.identify_contributing_factors(incident)
        consequences = self.analyze_consequences(incident)

        # Generate lessons based on analysis
        if "human_error" in factors:
            lessons.append(
                "Proper training and procedures are critical for hatch operations"
            )

        if "maintenance_issue" in factors:
            lessons.append(
                "Regular maintenance and inspection can prevent hatch failures"
            )

        if "flooding" in consequences:
            lessons.append(
                "Hatch integrity is essential for watertight compartment protection"
            )

        if "fatality" in consequences or "personnel_injury" in consequences:
            lessons.append("Hatch maloperation poses serious personnel safety risks")

        if not lessons:
            lessons.append(
                "Hatch system reliability requires continuous attention and oversight"
            )

        return lessons

    def get_location_statistics(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Generate location-based statistics for incidents.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Dictionary with location type counts
        """
        location_counts = Counter()

        for incident in incidents:
            location_type = self.classify_location(incident)
            location_counts[location_type] += 1

        stats = dict(location_counts)
        stats["total"] = len(incidents)

        return stats

    def get_consequence_statistics(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate consequence-based statistics.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Dictionary with consequence statistics
        """
        consequence_counts = Counter()
        total_fatalities = 0
        total_injuries = 0

        for incident in incidents:
            consequences = self.analyze_consequences(incident)
            for consequence in consequences:
                consequence_counts[consequence] += 1

            total_fatalities += incident.get("fatalities", 0)
            total_injuries += incident.get("injuries", 0)

        return {
            **dict(consequence_counts),
            "total_incidents": len(incidents),
            "total_fatalities": total_fatalities,
            "total_injuries": total_injuries,
        }

    def get_severity_distribution(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Generate severity distribution statistics.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Dictionary with severity level counts
        """
        severity_counts = Counter()

        for incident in incidents:
            severity = incident.get("severity", "Unknown")
            severity_counts[severity] += 1

        return dict(severity_counts)

    def get_time_series_data(
        self, incidents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate time series data for incident trending.

        Args:
            incidents: List of incident dictionaries

        Returns:
            List of time series data points
        """
        # Group incidents by month
        monthly_counts = defaultdict(int)

        for incident in incidents:
            incident_date = incident.get("date")
            if incident_date:
                # Create month key (YYYY-MM)
                if isinstance(incident_date, datetime):
                    month_key = incident_date.strftime("%Y-%m")
                else:
                    # Handle date objects
                    month_key = f"{incident_date.year:04d}-{incident_date.month:02d}"

                monthly_counts[month_key] += 1

        # Convert to sorted list of dictionaries
        time_series = [
            {"period": month, "count": count}
            for month, count in sorted(monthly_counts.items())
        ]

        return time_series

    def calculate_trends(self, incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate trending information from incident data.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Dictionary with trend analysis
        """
        if not incidents:
            return {"direction": "stable", "change_rate": 0}

        # Get time series
        time_series = self.get_time_series_data(incidents)

        if len(time_series) < 2:
            return {"direction": "stable", "change_rate": 0}

        # Simple trend: compare first half to second half
        midpoint = len(time_series) // 2
        first_half_avg = sum(d["count"] for d in time_series[:midpoint]) / midpoint
        second_half_avg = sum(d["count"] for d in time_series[midpoint:]) / (
            len(time_series) - midpoint
        )

        change_rate = (
            ((second_half_avg - first_half_avg) / first_half_avg * 100)
            if first_half_avg > 0
            else 0
        )

        if change_rate > 10:
            direction = "increasing"
        elif change_rate < -10:
            direction = "decreasing"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "change_rate": round(change_rate, 2),
            "first_half_avg": round(first_half_avg, 2),
            "second_half_avg": round(second_half_avg, 2),
        }

    def aggregate_recommendations(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Aggregate recommendations from multiple incidents.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Dictionary with recommendation text and frequency count
        """
        recommendation_counts = Counter()

        for incident in incidents:
            recommendations = self.generate_recommendations(incident)
            for rec in recommendations:
                recommendation_counts[rec] += 1

        return dict(recommendation_counts)

    def generate_comprehensive_report(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analysis report combining all features.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Comprehensive report dictionary
        """
        # Filter to only hatch incidents
        hatch_incidents = [
            inc for inc in incidents if self.is_hatch_maloperation_incident(inc)
        ]

        if not hatch_incidents:
            return {"error": "No hatch maloperation incidents found in dataset"}

        # Generate all analyses
        report = {
            "summary_statistics": {
                "total_incidents": len(hatch_incidents),
                "date_range": {
                    "earliest": min(
                        inc["date"] for inc in hatch_incidents if inc.get("date")
                    ),
                    "latest": max(
                        inc["date"] for inc in hatch_incidents if inc.get("date")
                    ),
                },
                "severity_distribution": self.get_severity_distribution(
                    hatch_incidents
                ),
            },
            "location_analysis": self.get_location_statistics(hatch_incidents),
            "consequence_analysis": self.get_consequence_statistics(hatch_incidents),
            "contributing_factors": self._analyze_contributing_factors(hatch_incidents),
            "risk_assessment": self._generate_risk_assessment(hatch_incidents),
            "recommendations": self.aggregate_recommendations(hatch_incidents),
            "case_studies": [
                self.extract_case_study(inc)
                for inc in hatch_incidents
                if self.is_significant_incident(inc)
            ],
            "trends": self.calculate_trends(hatch_incidents),
        }

        return report

    def _analyze_contributing_factors(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Analyze distribution of contributing factors across incidents."""
        factor_counts = Counter()

        for incident in incidents:
            factors = self.identify_contributing_factors(incident)
            for factor in factors:
                factor_counts[factor] += 1

        return dict(factor_counts)

    def _generate_risk_assessment(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate overall risk assessment from incidents."""
        risk_scores = [self.calculate_risk_score(inc) for inc in incidents]

        if not risk_scores:
            return {}

        return {
            "average_risk_score": round(sum(risk_scores) / len(risk_scores), 2),
            "highest_risk_score": max(risk_scores),
            "lowest_risk_score": min(risk_scores),
            "high_risk_incidents": len([s for s in risk_scores if s >= 70]),
            "moderate_risk_incidents": len([s for s in risk_scores if 40 <= s < 70]),
            "low_risk_incidents": len([s for s in risk_scores if s < 40]),
        }
