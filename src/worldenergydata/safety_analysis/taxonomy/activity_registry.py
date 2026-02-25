"""HSE Activity Taxonomy registry.

Registry, index builders, and query API for the activity taxonomy.
Import data definitions from activity_definitions.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .activity_definitions import (
    ALL_BUILDERS,
    Activity,
    Subactivity,
)


class ActivityTaxonomy:
    """Registry of all HSE activities and their subactivities.

    Provides lookup by code, keyword search, and source-specific
    field mapping for cross-source incident classification.
    """

    def __init__(self) -> None:
        self._activities: Tuple[Activity, ...] = tuple(
            builder() for builder in ALL_BUILDERS
        )
        self._code_index: Dict[str, Activity] = {
            a.code: a for a in self._activities
        }
        self._bsee_index = self._build_bsee_index()
        self._marine_index = self._build_marine_index()
        self._phmsa_index = self._build_phmsa_index()
        self._sic_index = self._build_sic_index()
        self._naics_index = self._build_naics_index()

    @property
    def activities(self) -> Tuple[Activity, ...]:
        """Return all registered activities."""
        return self._activities

    def get_activity(self, code: str) -> Optional[Activity]:
        """Get an activity by its code."""
        return self._code_index.get(code)

    def get_activity_codes(self) -> List[str]:
        """Return all activity codes."""
        return list(self._code_index.keys())

    def find_by_bsee_type(self, accident_type: str) -> Optional[Activity]:
        """Find activity matching a BSEE ACCIDENT_TYPE value.

        Matches against known BSEE accident type strings, using
        case-insensitive substring matching for the composite
        BSEE type format (e.g. '- Fire - Pollution').

        For composite types (multiple categories separated by ' - '),
        the first matching segment takes priority. This ensures that
        e.g. 'Fire - Pollution' maps to PSAFE (fire) not ENV (pollution).
        """
        normalized = accident_type.strip().strip("-").strip().lower()
        # Split composite BSEE types on ' - ' delimiter
        segments = [s.strip() for s in normalized.split("-") if s.strip()]
        # Check each segment in order for a match
        for segment in segments:
            for key, activity in self._bsee_index.items():
                if key in segment:
                    return activity
        # Fallback: check entire string
        for key, activity in self._bsee_index.items():
            if key in normalized:
                return activity
        return None

    def find_by_marine_type(self, incident_type: str) -> Optional[Activity]:
        """Find activity matching a marine_safety incident_type value."""
        normalized = incident_type.strip().upper()
        return self._marine_index.get(normalized)

    def find_by_phmsa_cause(self, cause_category: str) -> Optional[Activity]:
        """Find activity matching a PHMSA cause category."""
        normalized = cause_category.strip().upper()
        return self._phmsa_index.get(normalized)

    def find_by_sic_code(self, sic_code: str) -> Optional[Activity]:
        """Find activity matching a SIC code prefix."""
        sic_str = str(sic_code).strip()
        for prefix, activity in self._sic_index.items():
            if sic_str.startswith(prefix):
                return activity
        return None

    def find_by_naics_code(self, naics_code: str) -> Optional[Activity]:
        """Find activity matching a NAICS code prefix."""
        naics_str = str(naics_code).strip()
        for prefix, activity in self._naics_index.items():
            if naics_str.startswith(prefix):
                return activity
        return None

    def _build_bsee_index(self) -> Dict[str, Activity]:
        """Build lookup from BSEE accident type substring to activity."""
        index: Dict[str, Activity] = {}
        for activity in self._activities:
            for bsee_type in activity.bsee_accident_types:
                index[bsee_type.lower()] = activity
        return index

    def _build_marine_index(self) -> Dict[str, Activity]:
        """Build lookup from marine incident type to activity."""
        index: Dict[str, Activity] = {}
        for activity in self._activities:
            for marine_type in activity.marine_incident_types:
                index[marine_type.upper()] = activity
        return index

    def _build_phmsa_index(self) -> Dict[str, Activity]:
        """Build lookup from PHMSA cause category to activity."""
        index: Dict[str, Activity] = {}
        for activity in self._activities:
            for cause in activity.phmsa_cause_categories:
                index[cause.upper()] = activity
        return index

    def _build_sic_index(self) -> Dict[str, Activity]:
        """Build lookup from SIC code prefix to activity."""
        index: Dict[str, Activity] = {}
        for activity in self._activities:
            for sic in activity.sic_codes:
                index[sic] = activity
        return index

    def _build_naics_index(self) -> Dict[str, Activity]:
        """Build lookup from NAICS code prefix to activity."""
        index: Dict[str, Activity] = {}
        for activity in self._activities:
            for naics in activity.naics_codes:
                index[naics] = activity
        return index

    def summary(self) -> Dict[str, int]:
        """Return summary of activity codes and subactivity counts."""
        return {a.code: len(a.subactivities) for a in self._activities}
