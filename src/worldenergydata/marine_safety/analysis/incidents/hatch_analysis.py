# ABOUTME: Core analysis module for hatch, door, and opening maloperation incidents.
# ABOUTME: Provides classification, consequence analysis, risk scoring, and recommendations.

"""
Hatch Maloperation Analysis Module

This module provides core analysis capabilities including:
- Location classification (engine room, enclosures, etc.)
- Consequence analysis (flooding, fire, injury, etc.)
- Contributing factor identification
- Risk score calculation
- Recommendation generation
- Case study extraction
"""

import re
from typing import Any, Dict, List

from .hatch_patterns import (
    CONSEQUENCE_PATTERNS,
    ENCLOSURE_PATTERNS,
    ENGINE_ROOM_PATTERNS,
    FACTOR_PATTERNS,
    HIGH_IMPACT_CONSEQUENCES,
    SEVERITY_SCORES,
)


class HatchAnalyzer:
    """
    Analyzer for hatch, door, and opening maloperation incidents.

    Provides classification, risk assessment, and recommendation generation.
    """

    def __init__(self):
        """Initialize the HatchAnalyzer with compiled patterns."""
        # Compile location patterns
        self.compiled_engine_room_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in ENGINE_ROOM_PATTERNS
        ]
        self.compiled_enclosure_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in ENCLOSURE_PATTERNS
        ]

    def classify_location(self, incident: Dict[str, Any]) -> str:
        """
        Classify the location type of hatch maloperation.

        Args:
            incident: Incident dictionary with description field

        Returns:
            Location classification: 'engine_room', 'deck_access',
            'other_enclosure', or 'unknown'
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
        for consequence_type, patterns in CONSEQUENCE_PATTERNS.items():
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

        for factor_type, patterns in FACTOR_PATTERNS.items():
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
        score += SEVERITY_SCORES.get(severity, 10)

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
        consequence_count = sum(
            1 for c in consequences if c in HIGH_IMPACT_CONSEQUENCES
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
        if len([c for c in consequences if c in HIGH_IMPACT_CONSEQUENCES]) >= 2:
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
