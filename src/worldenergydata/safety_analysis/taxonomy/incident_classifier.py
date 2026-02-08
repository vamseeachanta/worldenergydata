"""Cross-source Incident Classifier.

Maps incidents from any HSE data source to the unified activity/subactivity
taxonomy using multiple matching strategies:
1. Direct field mapping (BSEE ACCIDENT_TYPE, OSHA SIC/NAICS code)
2. Incident type mapping from source-specific codes
3. Keyword matching on description/narrative text

Supported sources: bsee, osha, marine_safety, phmsa, epa_tri.

Usage:
    classifier = IncidentClassifier()
    result = classifier.classify({"ACCIDENT_TYPE": "EXPLOSION"}, source="bsee")
    print(result.activity, result.subactivity, result.confidence)

    results = classifier.classify_batch(records, source="bsee")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from worldenergydata.safety_analysis.taxonomy.activity_taxonomy import (
    Activity,
    ActivityTaxonomy,
    Subactivity,
)

VALID_SOURCES = frozenset(
    {
        "bsee",
        "osha",
        "marine_safety",
        "phmsa",
        "epa_tri",
    }
)

# Confidence thresholds for each match method
CONFIDENCE_DIRECT_CODE = 0.95
CONFIDENCE_INCIDENT_TYPE = 0.85
CONFIDENCE_SIC_NAICS = 0.80
CONFIDENCE_KEYWORD_HIGH = 0.75
CONFIDENCE_KEYWORD_MEDIUM = 0.55
CONFIDENCE_KEYWORD_LOW = 0.35
CONFIDENCE_DEFAULT = 0.10


@dataclass
class ClassificationResult:
    """Result of classifying a single incident record."""

    activity: str
    subactivity: str
    confidence: float
    match_method: str
    activity_name: str = ""
    subactivity_name: str = ""
    source: str = ""
    raw_value: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DataFrame construction."""
        return {
            "activity": self.activity,
            "activity_name": self.activity_name,
            "subactivity": self.subactivity,
            "subactivity_name": self.subactivity_name,
            "confidence": self.confidence,
            "match_method": self.match_method,
            "source": self.source,
            "raw_value": self.raw_value,
        }


class IncidentClassifier:
    """Classify incidents from multiple HSE data sources.

    The classifier attempts matching strategies in priority order:
    1. Direct code mapping (source-specific field to activity)
    2. Incident type or cause mapping
    3. SIC/NAICS code mapping (OSHA)
    4. Keyword matching on text fields

    Args:
        taxonomy: Optional pre-built taxonomy. If None, a default is created.
    """

    def __init__(self, taxonomy: Optional[ActivityTaxonomy] = None) -> None:
        self._taxonomy = taxonomy or ActivityTaxonomy()

    @property
    def taxonomy(self) -> ActivityTaxonomy:
        """Return the underlying activity taxonomy."""
        return self._taxonomy

    def classify(
        self,
        record: Dict[str, Any],
        source: str,
    ) -> ClassificationResult:
        """Classify a single incident record.

        Args:
            record: Dictionary of incident field names to values.
            source: Data source identifier (bsee, osha, marine_safety,
                    phmsa, epa_tri).

        Returns:
            ClassificationResult with activity, subactivity, confidence.

        Raises:
            ValueError: If source is not recognized.
        """
        if source not in VALID_SOURCES:
            raise ValueError(
                f"Unknown source '{source}'. Valid: {sorted(VALID_SOURCES)}"
            )

        dispatch = {
            "bsee": self._classify_bsee,
            "osha": self._classify_osha,
            "marine_safety": self._classify_marine,
            "phmsa": self._classify_phmsa,
            "epa_tri": self._classify_epa_tri,
        }
        result = dispatch[source](record)
        result.source = source
        return result

    def classify_batch(
        self,
        records: Sequence[Dict[str, Any]],
        source: str,
    ) -> List[ClassificationResult]:
        """Classify a batch of incident records.

        Args:
            records: Sequence of incident dictionaries.
            source: Data source identifier.

        Returns:
            List of ClassificationResult objects.
        """
        return [self.classify(record, source) for record in records]

    def get_taxonomy_summary(self) -> Dict[str, Any]:
        """Return a summary of the taxonomy for reporting.

        Returns:
            Dictionary with activity counts, subactivity counts,
            and source coverage information.
        """
        activities = self._taxonomy.activities
        total_subactivities = sum(len(a.subactivities) for a in activities)
        source_coverage: Dict[str, List[str]] = {
            "bsee": [],
            "marine_safety": [],
            "phmsa": [],
            "sic_mapped": [],
            "naics_mapped": [],
        }
        for activity in activities:
            if activity.bsee_accident_types:
                source_coverage["bsee"].append(activity.code)
            if activity.marine_incident_types:
                source_coverage["marine_safety"].append(activity.code)
            if activity.phmsa_cause_categories:
                source_coverage["phmsa"].append(activity.code)
            if activity.sic_codes:
                source_coverage["sic_mapped"].append(activity.code)
            if activity.naics_codes:
                source_coverage["naics_mapped"].append(activity.code)

        return {
            "total_activities": len(activities),
            "total_subactivities": total_subactivities,
            "activities": {
                a.code: {
                    "name": a.name,
                    "subactivity_count": len(a.subactivities),
                }
                for a in activities
            },
            "source_coverage": source_coverage,
        }

    # ------------------------------------------------------------------
    # Source-specific classifiers
    # ------------------------------------------------------------------

    def _classify_bsee(self, record: Dict[str, Any]) -> ClassificationResult:
        """Classify a BSEE incident using ACCIDENT_TYPE field."""
        accident_type = _get_field(record, "ACCIDENT_TYPE", "accident_type")
        if accident_type:
            activity = self._taxonomy.find_by_bsee_type(accident_type)
            if activity is not None:
                subactivity = self._match_subactivity_by_keywords(
                    activity, accident_type
                )
                return self._build_result(
                    activity=activity,
                    subactivity=subactivity,
                    confidence=CONFIDENCE_DIRECT_CODE,
                    method="bsee_accident_type",
                    raw_value=accident_type,
                )

        # Fallback: keyword search across all text fields
        text = _extract_text(record)
        if text:
            return self._classify_by_keywords(text, raw_value=accident_type or "")

        return self._default_result(raw_value=accident_type or "")

    def _classify_osha(self, record: Dict[str, Any]) -> ClassificationResult:
        """Classify an OSHA incident using SIC/NAICS codes and keywords."""
        # Try SIC code first
        sic_code = _get_field(record, "sic_list", "sic_code", "SIC")
        if sic_code:
            sic_str = str(sic_code).split(",")[0].strip()
            activity = self._taxonomy.find_by_sic_code(sic_str)
            if activity is not None:
                # Refine subactivity from event keywords
                event_kw = _get_field(record, "event_keyword", "EVENT_KEYWORD") or ""
                subactivity = self._match_subactivity_by_keywords(activity, event_kw)
                # Also check if keywords suggest a different subactivity
                if subactivity is None:
                    desc = (
                        _get_field(
                            record,
                            "event_desc",
                            "abstract_text",
                            "description",
                            "EVENT_DESC",
                        )
                        or ""
                    )
                    subactivity = self._match_subactivity_by_keywords(activity, desc)
                return self._build_result(
                    activity=activity,
                    subactivity=subactivity,
                    confidence=CONFIDENCE_SIC_NAICS,
                    method="osha_sic_code",
                    raw_value=sic_str,
                )

        # Try NAICS code
        naics_code = _get_field(record, "naics_code", "NAICS")
        if naics_code:
            naics_str = str(naics_code).strip()
            activity = self._taxonomy.find_by_naics_code(naics_str)
            if activity is not None:
                event_kw = _get_field(record, "event_keyword", "EVENT_KEYWORD") or ""
                subactivity = self._match_subactivity_by_keywords(activity, event_kw)
                return self._build_result(
                    activity=activity,
                    subactivity=subactivity,
                    confidence=CONFIDENCE_SIC_NAICS,
                    method="osha_naics_code",
                    raw_value=naics_str,
                )

        # Fallback: keyword matching from event description and keywords
        text = _extract_text(record)
        if text:
            return self._classify_by_keywords(text)

        return self._default_result()

    def _classify_marine(self, record: Dict[str, Any]) -> ClassificationResult:
        """Classify a marine safety incident using incident_type."""
        incident_type = _get_field(record, "incident_type", "INCIDENT_TYPE", "type")
        if incident_type:
            activity = self._taxonomy.find_by_marine_type(incident_type)
            if activity is not None:
                subactivity = self._match_subactivity_by_keywords(
                    activity, incident_type
                )
                return self._build_result(
                    activity=activity,
                    subactivity=subactivity,
                    confidence=CONFIDENCE_INCIDENT_TYPE,
                    method="marine_incident_type",
                    raw_value=incident_type,
                )

        # Fallback: keyword search
        text = _extract_text(record)
        if text:
            return self._classify_by_keywords(text, raw_value=incident_type or "")

        return self._default_result(raw_value=incident_type or "")

    def _classify_phmsa(self, record: Dict[str, Any]) -> ClassificationResult:
        """Classify a PHMSA incident using cause_category and report_type."""
        cause = _get_field(
            record,
            "cause_category",
            "CAUSE_CATEGORY",
            "MAP_EIGHT_CAUSE",
            "cause",
        )
        if cause:
            activity = self._taxonomy.find_by_phmsa_cause(cause)
            if activity is not None:
                subcause = (
                    _get_field(
                        record,
                        "subcause",
                        "MAP_EIGHT_SUBCAUSE",
                        "cause_subcategory",
                    )
                    or ""
                )
                subactivity = self._match_subactivity_by_keywords(
                    activity, f"{cause} {subcause}"
                )
                return self._build_result(
                    activity=activity,
                    subactivity=subactivity,
                    confidence=CONFIDENCE_INCIDENT_TYPE,
                    method="phmsa_cause_category",
                    raw_value=cause,
                )

        # Fallback: keyword search
        text = _extract_text(record)
        if text:
            return self._classify_by_keywords(text, raw_value=cause or "")

        return self._default_result(raw_value=cause or "")

    def _classify_epa_tri(self, record: Dict[str, Any]) -> ClassificationResult:
        """Classify an EPA TRI record -- always ENVIRONMENTAL/chemical_release."""
        env_activity = self._taxonomy.get_activity("ENV")
        if env_activity is None:
            return self._default_result()

        subactivity = env_activity.get_subactivity("chemical_release")
        chemical = (
            _get_field(record, "chemical_name", "CHEMICAL_NAME", "chemical") or ""
        )
        return self._build_result(
            activity=env_activity,
            subactivity=subactivity,
            confidence=CONFIDENCE_DIRECT_CODE,
            method="epa_tri_source",
            raw_value=chemical,
        )

    # ------------------------------------------------------------------
    # Keyword matching engine
    # ------------------------------------------------------------------

    def _classify_by_keywords(
        self,
        text: str,
        raw_value: str = "",
    ) -> ClassificationResult:
        """Classify using keyword matching across all activities.

        Scores each activity and subactivity by counting keyword hits
        in the input text. Returns the best match above threshold.
        """
        text_lower = text.lower()
        best_activity: Optional[Activity] = None
        best_subactivity: Optional[Subactivity] = None
        best_score = 0

        for activity in self._taxonomy.activities:
            if activity.code == "OTHER":
                continue

            # Score activity-level keywords
            activity_score = _count_keyword_hits(text_lower, activity.keywords)

            # Score subactivity-level keywords
            sub_best: Optional[Subactivity] = None
            sub_best_score = 0
            for sub in activity.subactivities:
                sub_score = _count_keyword_hits(text_lower, sub.keywords)
                if sub_score > sub_best_score:
                    sub_best_score = sub_score
                    sub_best = sub

            total_score = activity_score + sub_best_score
            if total_score > best_score:
                best_score = total_score
                best_activity = activity
                best_subactivity = sub_best

        if best_activity is not None and best_score > 0:
            if best_score >= 3:
                confidence = CONFIDENCE_KEYWORD_HIGH
            elif best_score >= 2:
                confidence = CONFIDENCE_KEYWORD_MEDIUM
            else:
                confidence = CONFIDENCE_KEYWORD_LOW

            return self._build_result(
                activity=best_activity,
                subactivity=best_subactivity,
                confidence=confidence,
                method="keyword_match",
                raw_value=raw_value,
            )

        return self._default_result(raw_value=raw_value)

    def _match_subactivity_by_keywords(
        self,
        activity: Activity,
        text: str,
    ) -> Optional[Subactivity]:
        """Find the best matching subactivity within an activity by keywords."""
        if not text:
            return activity.subactivities[0] if activity.subactivities else None

        text_lower = text.lower()
        best: Optional[Subactivity] = None
        best_score = 0
        for sub in activity.subactivities:
            score = _count_keyword_hits(text_lower, sub.keywords)
            if score > best_score:
                best_score = score
                best = sub

        if best is not None:
            return best
        # Default to first subactivity if no keyword match
        return activity.subactivities[0] if activity.subactivities else None

    # ------------------------------------------------------------------
    # Result builders
    # ------------------------------------------------------------------

    def _build_result(
        self,
        activity: Activity,
        subactivity: Optional[Subactivity],
        confidence: float,
        method: str,
        raw_value: str = "",
    ) -> ClassificationResult:
        """Build a ClassificationResult from activity/subactivity."""
        sub_code = subactivity.code if subactivity else "unknown"
        sub_name = subactivity.name if subactivity else "Unknown"
        return ClassificationResult(
            activity=activity.code,
            subactivity=sub_code,
            confidence=confidence,
            match_method=method,
            activity_name=activity.name,
            subactivity_name=sub_name,
            raw_value=raw_value,
        )

    def _default_result(self, raw_value: str = "") -> ClassificationResult:
        """Build a default OTHER/unknown classification result."""
        return ClassificationResult(
            activity="OTHER",
            subactivity="unknown",
            confidence=CONFIDENCE_DEFAULT,
            match_method="default",
            activity_name="Other",
            subactivity_name="Unknown",
            raw_value=raw_value,
        )


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------


def _get_field(record: Dict[str, Any], *field_names: str) -> Optional[str]:
    """Get the first non-empty field value from a record.

    Tries each field name in order, returning the first that exists
    and has a non-empty string value.
    """
    for name in field_names:
        value = record.get(name)
        if value is not None:
            str_val = str(value).strip()
            if str_val:
                return str_val
    return None


def _extract_text(record: Dict[str, Any]) -> str:
    """Extract all text content from a record for keyword matching.

    Concatenates values from common text fields used across sources.
    """
    text_fields = (
        "description",
        "event_desc",
        "abstract_text",
        "narrative",
        "DESCRIPTION",
        "EVENT_DESC",
        "ABSTRACT_TEXT",
        "NARRATIVE",
        "event_keyword",
        "EVENT_KEYWORD",
        "ACCIDENT_TYPE",
        "accident_type",
        "incident_type",
        "INCIDENT_TYPE",
        "cause_category",
        "CAUSE_CATEGORY",
        "cause_details",
        "CAUSE_DETAILS_TEXT",
    )
    parts = []
    for field_name in text_fields:
        value = record.get(field_name)
        if value is not None:
            str_val = str(value).strip()
            if str_val:
                parts.append(str_val)
    return " ".join(parts)


def _count_keyword_hits(text_lower: str, keywords: tuple) -> int:
    """Count how many keywords appear in the text.

    Uses word-boundary aware matching to avoid partial matches
    (e.g., 'fire' should not match 'firewall' but should match
    'fire explosion'). Multi-word keywords are matched as exact
    substring phrases.
    """
    hits = 0
    for keyword in keywords:
        kw_lower = keyword.lower()
        if " " in kw_lower:
            # Multi-word: substring match
            if kw_lower in text_lower:
                hits += 1
        else:
            # Single word: word boundary match
            pattern = rf"\b{re.escape(kw_lower)}\b"
            if re.search(pattern, text_lower):
                hits += 1
    return hits
