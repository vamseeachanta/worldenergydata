"""
Data Normalizer

Normalizes marine safety data to standard formats and mappings.
"""

import logging
from typing import Any, Dict, List, Optional

from worldenergydata.modules.marine_safety.processors.base_processor import (
    BaseProcessor,
)

logger = logging.getLogger(__name__)


class DataNormalizer(BaseProcessor):
    """
    Normalizes marine safety data to standard formats.

    Handles:
    - Incident type standardization
    - Vessel type mapping
    - Country code normalization
    - Severity level mapping
    - Status standardization
    """

    # Incident type mappings (various formats -> standard IncidentType enum values)
    INCIDENT_TYPE_MAPPINGS = {
        "collision": "collision",
        "collisions": "collision",
        "vessel collision": "collision",
        "allision": "collision",  # Allision is collision with stationary object
        "allisions": "collision",
        "grounding": "grounding",
        "groundings": "grounding",
        "run aground": "grounding",
        "fire": "fire",
        "fires": "fire",
        "explosion": "explosion",
        "fire/explosion": "fire",
        "fire & explosion": "fire",
        "sinking": "flooding",  # Map sinking to flooding
        "sinkings": "flooding",
        "foundering": "flooding",
        "capsizing": "capsizing",
        "capsize": "capsizing",
        "flooding": "flooding",
        "material failure": "equipment_failure",
        "equipment failure": "equipment_failure",
        "machinery failure": "equipment_failure",
        "personnel casualty": "personnel_injury",
        "injury": "personnel_injury",
        "fatality": "fatality",
        "man overboard": "personnel_injury",
        "pollution": "pollution",
        "oil spill": "pollution",
        "hazmat": "pollution",
        "environmental": "environmental",
        "weather": "weather_related",
        "weather related": "weather_related",
    }

    # Vessel type standardization (maps to VesselType enum values)
    VESSEL_TYPE_MAPPINGS = {
        "cargo": "cargo_vessel",
        "cargo ship": "cargo_vessel",
        "cargo vessel": "cargo_vessel",
        "container": "cargo_vessel",
        "container ship": "cargo_vessel",
        "tanker": "tanker",
        "oil tanker": "tanker",
        "chemical tanker": "tanker",
        "bulk carrier": "cargo_vessel",
        "bulker": "cargo_vessel",
        "passenger": "other",  # Not in enum, use other
        "passenger ship": "other",
        "cruise": "other",
        "cruise ship": "other",
        "ferry": "other",
        "passenger ferry": "other",
        "tug": "tug",
        "tugboat": "tug",
        "tow": "tug",
        "barge": "other",
        "fishing": "other",
        "fishing vessel": "other",
        "offshore": "supply_vessel",
        "platform": "production_platform",
        "supply vessel": "supply_vessel",
        "recreational": "other",
        "yacht": "other",
        "pleasure craft": "other",
        "military auxiliary": "other",
        "military": "other",
    }

    # Country code standardization (common names -> ISO codes)
    COUNTRY_MAPPINGS = {
        "united states": "USA",
        "us": "USA",
        "usa": "USA",
        "u.s.": "USA",
        "u.s.a.": "USA",
        "america": "USA",
        "united kingdom": "GBR",
        "uk": "GBR",
        "great britain": "GBR",
        "britain": "GBR",
        "canada": "CAN",
        "mexico": "MEX",
        "panama": "PAN",
        "liberia": "LBR",
        "marshall islands": "MHL",
        "bahamas": "BHS",
        "malta": "MLT",
        "cyprus": "CYP",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize data normalizer with configuration."""
        super().__init__(config)

        # Load custom mappings from config if provided
        if self.config.get("incident_type_mappings"):
            self.INCIDENT_TYPE_MAPPINGS.update(self.config["incident_type_mappings"])

        if self.config.get("vessel_type_mappings"):
            self.VESSEL_TYPE_MAPPINGS.update(self.config["vessel_type_mappings"])

        if self.config.get("country_mappings"):
            self.COUNTRY_MAPPINGS.update(self.config["country_mappings"])

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a single incident record.

        Args:
            data: Cleaned incident data dictionary

        Returns:
            Normalized incident data dictionary
        """
        if not self.validate(data):
            self.stats["errors"] += 1
            return data

        normalized = data.copy()

        try:
            # Normalize incident type
            if "incident_type" in normalized:
                normalized["incident_type"] = self.normalize_incident_type(
                    normalized["incident_type"]
                )

            # Normalize vessel type
            if "vessel_type" in normalized:
                normalized["vessel_type"] = self.normalize_vessel_type(
                    normalized["vessel_type"]
                )

            # Normalize country codes
            for field in ["country", "flag_state", "country_code"]:
                if field in normalized:
                    normalized[field] = self.normalize_country(normalized[field])

            # Normalize severity level
            if "severity_level" in normalized:
                normalized["severity_level"] = self.normalize_severity(
                    normalized.get("severity_level"),
                    normalized.get("fatalities", 0),
                    normalized.get("injuries", 0),
                )

            # Normalize status
            if "status" in normalized:
                normalized["status"] = self.normalize_status(normalized["status"])

            self.stats["processed"] += 1

        except Exception as e:
            logger.error(f"Error normalizing data: {e}")
            self.stats["errors"] += 1
            return data

        return normalized

    def normalize_incident_type(self, incident_type: Optional[str]) -> Optional[str]:
        """
        Normalize incident type to standard value.

        Args:
            incident_type: Raw incident type string

        Returns:
            Normalized incident type
        """
        if not incident_type:
            return None

        # Convert to lowercase for matching
        incident_lower = incident_type.lower().strip()

        # Try exact match first
        if incident_lower in self.INCIDENT_TYPE_MAPPINGS:
            return self.INCIDENT_TYPE_MAPPINGS[incident_lower]

        # Try partial match
        for key, value in self.INCIDENT_TYPE_MAPPINGS.items():
            if key in incident_lower or incident_lower in key:
                return value

        # No match found - log warning and return original
        logger.warning(f"Unknown incident type: {incident_type}")
        self.stats["warnings"] += 1
        return incident_type.lower().replace(" ", "_")

    def normalize_vessel_type(self, vessel_type: Optional[str]) -> Optional[str]:
        """
        Normalize vessel type to standard value.

        Args:
            vessel_type: Raw vessel type string

        Returns:
            Normalized vessel type
        """
        if not vessel_type:
            return None

        vessel_lower = vessel_type.lower().strip()

        if vessel_lower in self.VESSEL_TYPE_MAPPINGS:
            return self.VESSEL_TYPE_MAPPINGS[vessel_lower]

        # Try partial match
        for key, value in self.VESSEL_TYPE_MAPPINGS.items():
            if key in vessel_lower:
                return value

        logger.warning(f"Unknown vessel type: {vessel_type}")
        self.stats["warnings"] += 1
        return vessel_type.lower().replace(" ", "_")

    def normalize_country(self, country: Optional[str]) -> Optional[str]:
        """
        Normalize country name to ISO 3-letter code.

        Args:
            country: Raw country name or code

        Returns:
            ISO 3-letter country code
        """
        if not country:
            return None

        country_lower = country.lower().strip()

        # Already a valid 3-letter code
        if len(country) == 3 and country.isupper():
            return country

        if country_lower in self.COUNTRY_MAPPINGS:
            return self.COUNTRY_MAPPINGS[country_lower]

        # Return original if not found
        logger.warning(f"Unknown country: {country}")
        self.stats["warnings"] += 1
        return country.upper() if len(country) == 3 else country

    def normalize_severity(
        self, severity: Any, fatalities: int = 0, injuries: int = 0
    ) -> int:
        """
        Normalize severity level (1-5 scale).

        Args:
            severity: Raw severity value
            fatalities: Number of fatalities
            injuries: Number of injuries

        Returns:
            Severity level (1=minor, 2=moderate, 3=major, 4=severe, 5=catastrophic)
        """
        # If severity provided as integer, validate range
        if isinstance(severity, int):
            return max(1, min(5, severity))

        # If severity is string, try to parse
        if isinstance(severity, str):
            severity_lower = severity.lower().strip()
            mapping = {
                "minor": 1,
                "low": 1,
                "moderate": 2,
                "medium": 2,
                "major": 3,
                "high": 3,
                "severe": 4,
                "serious": 4,
                "catastrophic": 5,
                "critical": 5,
            }
            if severity_lower in mapping:
                return mapping[severity_lower]

        # Calculate based on casualties if severity not provided
        if fatalities > 0:
            if fatalities >= 10:
                return 5  # Catastrophic
            elif fatalities >= 5:
                return 4  # Severe
            elif fatalities >= 1:
                return 3  # Major

        if injuries > 0:
            if injuries >= 20:
                return 4  # Severe
            elif injuries >= 10:
                return 3  # Major
            elif injuries >= 5:
                return 2  # Moderate
            else:
                return 2  # Moderate

        # Default to moderate
        return 2

    def normalize_status(self, status: Optional[str]) -> Optional[str]:
        """
        Normalize investigation status.

        Args:
            status: Raw status string

        Returns:
            Normalized status
        """
        if not status:
            return "draft"

        status_lower = status.lower().strip()

        # Status mappings
        mapping = {
            "draft": "draft",
            "preliminary": "draft",
            "reported": "reported",
            "initial": "reported",
            "under investigation": "under_investigation",
            "investigating": "under_investigation",
            "active": "under_investigation",
            "in review": "in_review",
            "review": "in_review",
            "pending": "in_review",
            "completed": "completed",
            "complete": "completed",
            "final": "completed",
            "closed": "completed",
        }

        for key, value in mapping.items():
            if key in status_lower:
                return value

        logger.warning(f"Unknown status: {status}")
        self.stats["warnings"] += 1
        return "draft"

    def batch_process(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize a batch of incident records.

        Args:
            data_list: List of cleaned incident dictionaries

        Returns:
            List of normalized incident dictionaries
        """
        self.reset_stats()
        normalized_list = []

        for data in data_list:
            normalized = self.process(data)
            normalized_list.append(normalized)

        logger.info(
            f"Batch normalized: {self.stats['processed']} records, "
            f"{self.stats['errors']} errors, {self.stats['warnings']} warnings"
        )

        return normalized_list
