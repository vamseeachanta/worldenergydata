"""
ABOUTME: Data processing module for marine incident cause analysis.
ABOUTME: Extracts, normalizes, and categorizes incident causes from raw CSV data.
"""

import re
from typing import Any, List, Optional

import pandas as pd

from worldenergydata.modules.marine_safety.constants import CauseCategory


class IncidentCauseExtractor:
    """
    Extracts incident causes from raw CSV data.

    Processes multiple data fields (primary_cause, contributing_factors, narrative)
    to extract and structure cause information.
    """

    def __init__(self):
        """Initialize the cause extractor."""
        pass

    def extract_from_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract cause information from a DataFrame.

        Args:
            df: DataFrame containing incident data with columns:
                - incident_id (required)
                - primary_cause (optional)
                - contributing_factors (optional)
                - narrative (optional)

        Returns:
            DataFrame with extracted and structured cause data including:
                - incident_id
                - primary_cause_category
                - contributing_causes (list)
                - narrative_causes (list)
        """
        if df.empty:
            return pd.DataFrame()

        result = df.copy()

        # Extract primary cause category
        if "primary_cause" in df.columns:
            result["primary_cause_category"] = df["primary_cause"].apply(
                lambda x: (
                    map_to_cause_category(str(x))
                    if pd.notna(x)
                    else CauseCategory.UNKNOWN
                )
            )
        else:
            result["primary_cause_category"] = CauseCategory.UNKNOWN

        # Extract contributing causes
        if "contributing_factors" in df.columns:
            result["contributing_causes"] = df["contributing_factors"].apply(
                self._parse_contributing_factors
            )
        else:
            result["contributing_causes"] = [[] for _ in range(len(df))]

        # Extract causes from narrative text
        if "narrative" in df.columns:
            result["narrative_causes"] = df["narrative"].apply(
                extract_causes_from_narrative
            )
        else:
            result["narrative_causes"] = [[] for _ in range(len(df))]

        return result

    def _parse_contributing_factors(self, factors: Any) -> List[str]:
        """
        Parse contributing factors string into list of causes.

        Args:
            factors: String containing contributing factors (may be comma-separated)

        Returns:
            List of individual contributing cause strings
        """
        if pd.isna(factors):
            return []

        factors_str = str(factors).strip()
        if not factors_str:
            return []

        # Split by common separators
        separators = [",", ";", "|", " and ", " AND "]
        causes = [factors_str]

        for sep in separators:
            new_causes = []
            for cause in causes:
                new_causes.extend([c.strip() for c in cause.split(sep)])
            causes = new_causes

        # Remove empty strings and normalize
        causes = [c for c in causes if c and c.strip()]

        return causes


class CauseNormalizer:
    """
    Normalizes cause descriptions to standard format.

    Handles variations in case, whitespace, and terminology to create
    consistent cause descriptions for analysis.
    """

    def __init__(self):
        """Initialize normalizer with standard cause mappings."""
        # Standard terminology mappings
        self.cause_mappings = {
            "operator": "operator",
            "crew": "crew",
            "human": "human",
            "fatigue": "fatigue",
            "error": "error",
            "mistake": "error",
            "equipment": "equipment",
            "machinery": "equipment",
            "mechanical": "equipment",
            "failure": "failure",
            "malfunction": "failure",
            "maintenance": "maintenance",
            "repair": "maintenance",
            "upkeep": "maintenance",
            "design": "design",
            "structural": "structural",
            "weather": "weather",
            "storm": "weather",
            "wind": "weather",
            "hatch": "hatch",
            "door": "door",
            "opening": "opening",
            "cover": "cover",
            "procedural": "procedural",
            "procedure": "procedural",
            "protocol": "procedural",
            "training": "training",
            "qualification": "training",
        }

    def normalize(self, description: Any) -> Optional[str]:
        """
        Normalize a cause description.

        Args:
            description: Cause description to normalize

        Returns:
            Normalized description string, or None if input is null/empty
        """
        if pd.isna(description):
            return None

        desc_str = str(description).strip()
        if not desc_str:
            return None

        # Convert to lowercase
        normalized = desc_str.lower()

        # Remove extra whitespace (multiple spaces, tabs, newlines)
        normalized = re.sub(r"\s+", " ", normalized)

        # Trim
        normalized = normalized.strip()

        return normalized if normalized else None


def map_to_cause_category(description: Any) -> CauseCategory:
    """
    Map a cause description to a standard CauseCategory enum.

    Args:
        description: Cause description text

    Returns:
        Matching CauseCategory enum value
    """
    if pd.isna(description):
        return CauseCategory.UNKNOWN

    desc_lower = str(description).lower()

    # Check for multiple causes
    if any(
        keyword in desc_lower for keyword in ["multiple", "and", "various", "several"]
    ):
        # Only return MULTIPLE if there are actually multiple distinct causes
        if (
            len(
                [
                    w
                    for w in ["equipment", "human", "weather", "maintenance"]
                    if w in desc_lower
                ]
            )
            >= 2
        ):
            return CauseCategory.MULTIPLE

    # Human error patterns
    if any(
        keyword in desc_lower
        for keyword in [
            "operator",
            "crew",
            "human",
            "fatigue",
            "error",
            "mistake",
            "personnel",
        ]
    ):
        return CauseCategory.HUMAN_ERROR

    # Equipment failure patterns
    if any(
        keyword in desc_lower
        for keyword in [
            "equipment",
            "machinery",
            "mechanical",
            "failure",
            "malfunction",
        ]
    ):
        return CauseCategory.EQUIPMENT_FAILURE

    # Maintenance patterns
    if any(
        keyword in desc_lower
        for keyword in ["maintenance", "repair", "upkeep", "inadequate maintenance"]
    ):
        return CauseCategory.MAINTENANCE_ISSUE

    # Weather patterns
    if any(
        keyword in desc_lower
        for keyword in ["weather", "storm", "wind", "wave", "sea state", "visibility"]
    ):
        return CauseCategory.WEATHER

    # Design patterns
    if any(
        keyword in desc_lower for keyword in ["design", "structural", "construction"]
    ):
        return CauseCategory.DESIGN_FLAW

    # Procedural patterns
    if any(
        keyword in desc_lower
        for keyword in [
            "procedure",
            "procedural",
            "protocol",
            "violation",
            "compliance",
        ]
    ):
        return CauseCategory.PROCEDURAL

    # Training patterns
    if any(
        keyword in desc_lower
        for keyword in ["training", "qualification", "competency", "certification"]
    ):
        return CauseCategory.TRAINING

    # Communication patterns
    if any(
        keyword in desc_lower
        for keyword in ["communication", "coordination", "language"]
    ):
        return CauseCategory.COMMUNICATION

    # Management patterns
    if any(
        keyword in desc_lower
        for keyword in ["management", "supervision", "oversight", "organization"]
    ):
        return CauseCategory.MANAGEMENT

    # Environmental patterns (distinct from weather)
    if any(keyword in desc_lower for keyword in ["environmental", "current", "tide"]):
        return CauseCategory.ENVIRONMENTAL

    # External patterns
    if any(
        keyword in desc_lower for keyword in ["external", "third party", "collision"]
    ):
        return CauseCategory.EXTERNAL

    return CauseCategory.UNKNOWN


def detect_hatch_opening_maloperation(text: Any) -> bool:
    """
    Detect if text describes a hatch or opening maloperation incident.

    Identifies incidents involving failures of hatches, doors, or other
    closures that could lead to water ingress.

    Args:
        text: Incident narrative or description text

    Returns:
        True if hatch/opening maloperation is detected, False otherwise
    """
    if pd.isna(text):
        return False

    text_lower = str(text).lower()

    # Hatch-related keywords
    hatch_keywords = [
        "hatch",
        "hatchway",
        "cargo hatch",
        "hatch cover",
        "hatch door",
    ]

    # Opening/door keywords
    opening_keywords = [
        "door",
        "opening",
        "access",
        "watertight door",
        "watertight",
        "closure",
        "manhole",
    ]

    # Malfunction/failure keywords
    malfunction_keywords = [
        "malfunction",
        "maloperation",
        "failure",
        "not secured",
        "not properly",
        "improperly",
        "left open",
        "unsealed",
        "unsecured",
        "not closed",
    ]

    # Check for hatch keywords
    has_hatch = any(keyword in text_lower for keyword in hatch_keywords)

    # Check for opening/door keywords
    has_opening = any(keyword in text_lower for keyword in opening_keywords)

    # Check for malfunction keywords
    has_malfunction = any(keyword in text_lower for keyword in malfunction_keywords)

    # Return True if we have hatch/opening AND malfunction indicators
    return (has_hatch or has_opening) and has_malfunction


def extract_causes_from_narrative(narrative: Any) -> List[str]:
    """
    Extract potential causes from incident narrative text.

    Uses pattern matching to identify cause-related phrases in
    unstructured narrative text.

    Args:
        narrative: Incident narrative or description text

    Returns:
        List of extracted cause phrases
    """
    if pd.isna(narrative):
        return []

    narrative_str = str(narrative).strip()
    if not narrative_str:
        return []

    causes = []

    # Common cause patterns
    cause_patterns = [
        r"(?:caused by|due to|attributed to|result of)\s+([^.,;]+)",
        r"(?:because|since)\s+([^.,;]+)",
        r"(?:failure of|malfunction of)\s+([^.,;]+)",
        r"(\w+\s+(?:failure|malfunction|error|deficiency))",
    ]

    for pattern in cause_patterns:
        matches = re.finditer(pattern, narrative_str, re.IGNORECASE)
        for match in matches:
            cause_text = match.group(1).strip()
            if cause_text and len(cause_text) > 3:  # Filter very short matches
                causes.append(cause_text)

    # Look for numbered/bulleted lists
    list_pattern = r"(?:\d+\.|[-*])\s*([^\n.;]+)"
    list_matches = re.finditer(list_pattern, narrative_str)
    for match in list_matches:
        item = match.group(1).strip()
        # Only include if it looks like a cause (contains certain keywords)
        if any(
            kw in item.lower()
            for kw in [
                "failure",
                "error",
                "malfunction",
                "deficiency",
                "inadequate",
                "improper",
            ]
        ):
            causes.append(item)

    # If no causes found yet, look for key cause-related words in the text
    if not causes:
        cause_keywords = [
            "hatch",
            "failure",
            "maloperation",
            "error",
            "malfunction",
            "maintenance",
            "fatigue",
            "weather",
            "equipment",
        ]
        found_keywords = [kw for kw in cause_keywords if kw in narrative_str.lower()]

        # Extract phrases containing these keywords
        for keyword in found_keywords:
            # Look for the keyword with surrounding context
            pattern = rf"([^.;]*{re.escape(keyword)}[^.;]*)"
            matches = re.finditer(pattern, narrative_str, re.IGNORECASE)
            for match in matches:
                phrase = match.group(1).strip()
                if len(phrase) > 10 and len(phrase) < 200:  # Reasonable length
                    causes.append(phrase)
                    break  # Only take first match per keyword

    # Remove duplicates while preserving order
    seen = set()
    unique_causes = []
    for cause in causes:
        cause_lower = cause.lower()
        if cause_lower not in seen:
            seen.add(cause_lower)
            unique_causes.append(cause)

    return unique_causes


def clean_cause_data(
    df: pd.DataFrame,
    cause_column: str,
    remove_duplicates: bool = False,
    validate_categories: bool = False,
) -> pd.DataFrame:
    """
    Clean and validate cause data in a DataFrame.

    Args:
        df: DataFrame containing cause data
        cause_column: Name of column containing cause descriptions
        remove_duplicates: Whether to remove duplicate cause entries
        validate_categories: Whether to validate against known categories

    Returns:
        Cleaned DataFrame with normalized cause data
    """
    if df.empty or cause_column not in df.columns:
        return df

    result = df.copy()
    normalizer = CauseNormalizer()

    # Normalize all cause descriptions
    result[cause_column] = result[cause_column].apply(normalizer.normalize)

    # Remove duplicates if requested
    if remove_duplicates:
        result = result.drop_duplicates(subset=[cause_column])

    # Validate categories if requested
    if validate_categories:
        result["validation_status"] = result[cause_column].apply(
            lambda x: (
                "valid"
                if map_to_cause_category(x) != CauseCategory.UNKNOWN
                else "unknown"
            )
        )

    return result
