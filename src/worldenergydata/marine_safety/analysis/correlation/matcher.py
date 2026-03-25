# ABOUTME: Incident matching engine for identifying related incidents across data sources.
# ABOUTME: Implements fuzzy matching using Levenshtein distance, geographic proximity, and temporal analysis.

"""
Incident Matcher Module

Provides fuzzy matching capabilities to identify potentially related incidents
across multiple data sources using various matching strategies.
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class MatchType(str, Enum):
    """Types of matching strategies used."""

    IMO = "imo"
    NAME = "name"
    LOCATION = "location"
    DATE = "date"
    COMBINED = "combined"


@dataclass
class MatchConfig:
    """Configuration for incident matching thresholds and weights."""

    # Minimum combined confidence to consider a match
    min_confidence: float = 0.7

    # Date matching tolerance
    date_tolerance_days: int = 3

    # Geographic proximity threshold
    location_threshold_km: float = 50.0

    # Minimum similarity for vessel name matching (0-1)
    name_similarity_threshold: float = 0.8

    # Weights for combining individual match scores
    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "imo": 0.40,
            "name": 0.25,
            "location": 0.20,
            "date": 0.15,
        }
    )

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0.0 and 1.0")
        if self.date_tolerance_days < 0:
            raise ValueError("date_tolerance_days must be non-negative")
        if self.location_threshold_km <= 0:
            raise ValueError("location_threshold_km must be positive")
        if not 0.0 <= self.name_similarity_threshold <= 1.0:
            raise ValueError("name_similarity_threshold must be between 0.0 and 1.0")

        # Normalize weights to sum to 1.0
        weight_sum = sum(self.weights.values())
        if weight_sum > 0:
            self.weights = {k: v / weight_sum for k, v in self.weights.items()}


@dataclass
class MatchResult:
    """Result of comparing two incidents for potential match."""

    incident_id_1: int
    incident_id_2: int
    confidence_score: float
    match_type: MatchType
    component_scores: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_high_confidence(self) -> bool:
        """Check if this is a high-confidence match (>0.9)."""
        return self.confidence_score >= 0.9

    @property
    def is_imo_match(self) -> bool:
        """Check if this match is based on IMO number."""
        return self.match_type == MatchType.IMO


@dataclass
class IncidentData:
    """
    Normalized incident data for matching.

    This dataclass provides a consistent interface for incident data
    regardless of whether it comes from database models or dictionaries.
    """

    incident_id: int
    incident_date: Optional[date] = None
    vessel_name: Optional[str] = None
    imo_number: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source_agency: Optional[str] = None
    title: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IncidentData":
        """Create IncidentData from a dictionary."""
        # Handle date conversion
        incident_date = data.get("incident_date")
        if isinstance(incident_date, str):
            incident_date = datetime.fromisoformat(incident_date).date()
        elif isinstance(incident_date, datetime):
            incident_date = incident_date.date()

        # Handle Decimal to float conversion for coordinates
        lat = data.get("latitude")
        if isinstance(lat, Decimal):
            lat = float(lat)
        lon = data.get("longitude")
        if isinstance(lon, Decimal):
            lon = float(lon)

        return cls(
            incident_id=data["incident_id"],
            incident_date=incident_date,
            vessel_name=data.get("vessel_name"),
            imo_number=data.get("imo_number"),
            latitude=lat,
            longitude=lon,
            source_agency=data.get("source_agency"),
            title=data.get("title"),
        )

    @classmethod
    def from_model(cls, model: Any) -> "IncidentData":
        """Create IncidentData from a database model."""
        # Extract vessel info if available
        vessel_name = None
        imo_number = None
        if hasattr(model, "vessel") and model.vessel:
            vessel_name = model.vessel.vessel_name
            imo_number = model.vessel.imo_number

        # Extract location info if available
        latitude = None
        longitude = None
        if hasattr(model, "location") and model.location:
            lat = model.location.latitude
            lon = model.location.longitude
            latitude = float(lat) if lat is not None else None
            longitude = float(lon) if lon is not None else None

        # Get source agency value
        source_agency = None
        if hasattr(model, "source_agency"):
            sa = model.source_agency
            source_agency = sa.value if hasattr(sa, "value") else str(sa)

        return cls(
            incident_id=model.incident_id,
            incident_date=model.incident_date,
            vessel_name=vessel_name,
            imo_number=imo_number,
            latitude=latitude,
            longitude=longitude,
            source_agency=source_agency,
            title=model.title,
        )


class IncidentMatcher:
    """
    Incident matching engine for cross-source correlation.

    Uses multiple matching strategies to identify potentially related incidents:
    - IMO number exact matching
    - Vessel name fuzzy matching (Levenshtein distance)
    - Geographic proximity matching (haversine formula)
    - Temporal proximity matching
    """

    # Earth's radius in kilometers for haversine calculation
    EARTH_RADIUS_KM = 6371.0

    def __init__(self, config: Optional[MatchConfig] = None) -> None:
        """
        Initialize the incident matcher.

        Args:
            config: Configuration for matching thresholds and weights.
                    Uses defaults if not provided.
        """
        self.config = config or MatchConfig()
        logger.info(
            "IncidentMatcher initialized with min_confidence=%.2f, "
            "date_tolerance=%d days, location_threshold=%.1f km",
            self.config.min_confidence,
            self.config.date_tolerance_days,
            self.config.location_threshold_km,
        )

    def find_matches(
        self,
        incident: Union[Dict[str, Any], Any],
        candidates: List[Union[Dict[str, Any], Any]],
    ) -> List[MatchResult]:
        """
        Find potential matches for an incident from a list of candidates.

        Args:
            incident: The incident to find matches for (dict or model).
            candidates: List of candidate incidents to compare against.

        Returns:
            List of MatchResult objects sorted by confidence score (descending).
        """
        # Normalize input incident
        source = self._normalize_incident(incident)
        if source is None:
            logger.warning("Could not normalize source incident")
            return []

        results: List[MatchResult] = []

        for candidate in candidates:
            target = self._normalize_incident(candidate)
            if target is None:
                continue

            # Skip self-comparison
            if source.incident_id == target.incident_id:
                continue

            # Calculate match confidence
            result = self.calculate_confidence(source, target)
            if result.confidence_score >= self.config.min_confidence:
                results.append(result)

        # Sort by confidence score descending
        results.sort(key=lambda r: r.confidence_score, reverse=True)

        logger.debug(
            "Found %d potential matches for incident %d",
            len(results),
            source.incident_id,
        )

        return results

    def calculate_confidence(
        self,
        incident1: Union[Dict[str, Any], Any, IncidentData],
        incident2: Union[Dict[str, Any], Any, IncidentData],
    ) -> MatchResult:
        """
        Calculate match confidence between two incidents.

        Args:
            incident1: First incident (dict, model, or IncidentData).
            incident2: Second incident (dict, model, or IncidentData).

        Returns:
            MatchResult with confidence score and component scores.
        """
        # Normalize inputs if needed
        if not isinstance(incident1, IncidentData):
            incident1 = self._normalize_incident(incident1)
        if not isinstance(incident2, IncidentData):
            incident2 = self._normalize_incident(incident2)

        if incident1 is None or incident2 is None:
            return MatchResult(
                incident_id_1=0,
                incident_id_2=0,
                confidence_score=0.0,
                match_type=MatchType.COMBINED,
                component_scores={},
            )

        # Calculate individual component scores
        scores: Dict[str, float] = {}

        # IMO matching (exact)
        imo_score = self._match_by_imo(incident1.imo_number, incident2.imo_number)
        if imo_score is not None:
            scores["imo"] = imo_score
            # If exact IMO match, return immediately with high confidence
            if imo_score == 1.0:
                return MatchResult(
                    incident_id_1=incident1.incident_id,
                    incident_id_2=incident2.incident_id,
                    confidence_score=1.0,
                    match_type=MatchType.IMO,
                    component_scores={"imo": 1.0},
                    metadata={"imo_number": incident1.imo_number},
                )

        # Vessel name matching (fuzzy)
        name_score = self._match_by_vessel_name(
            incident1.vessel_name, incident2.vessel_name
        )
        if name_score is not None:
            scores["name"] = name_score

        # Location matching (geographic proximity)
        location_score = self._match_by_location(
            (incident1.latitude, incident1.longitude),
            (incident2.latitude, incident2.longitude),
            self.config.location_threshold_km,
        )
        if location_score is not None:
            scores["location"] = location_score

        # Date matching (temporal proximity)
        date_score = self._match_by_date(
            incident1.incident_date,
            incident2.incident_date,
            self.config.date_tolerance_days,
        )
        if date_score is not None:
            scores["date"] = date_score

        # Combine scores with weights
        combined_score = self._combine_scores(scores, self.config.weights)

        # Determine primary match type based on highest contributing score
        match_type = self._determine_match_type(scores)

        return MatchResult(
            incident_id_1=incident1.incident_id,
            incident_id_2=incident2.incident_id,
            confidence_score=combined_score,
            match_type=match_type,
            component_scores=scores,
            metadata={
                "source_1": incident1.source_agency,
                "source_2": incident2.source_agency,
            },
        )

    def _match_by_imo(
        self, imo1: Optional[str], imo2: Optional[str]
    ) -> Optional[float]:
        """
        Match by IMO number (exact match).

        IMO numbers are unique vessel identifiers, so an exact match
        provides 100% confidence.

        Args:
            imo1: First IMO number.
            imo2: Second IMO number.

        Returns:
            1.0 for exact match, 0.0 for mismatch, None if either is missing.
        """
        if not imo1 or not imo2:
            return None

        # Normalize IMO numbers (remove 'IMO' prefix if present, strip whitespace)
        imo1_clean = imo1.upper().replace("IMO", "").strip()
        imo2_clean = imo2.upper().replace("IMO", "").strip()

        if not imo1_clean or not imo2_clean:
            return None

        return 1.0 if imo1_clean == imo2_clean else 0.0

    def _match_by_vessel_name(
        self, name1: Optional[str], name2: Optional[str]
    ) -> Optional[float]:
        """
        Match by vessel name using fuzzy string matching.

        Uses token set ratio from rapidfuzz for robust matching that handles:
        - Word order differences ("MV ATLANTIC" vs "ATLANTIC MV")
        - Partial matches ("ATLANTIC EXPLORER" vs "ATLANTIC EXPLORER II")
        - Abbreviations and typos

        Args:
            name1: First vessel name.
            name2: Second vessel name.

        Returns:
            Similarity score (0-1), or None if either name is missing.
        """
        if not name1 or not name2:
            return None

        # Normalize names
        name1_clean = self._normalize_vessel_name(name1)
        name2_clean = self._normalize_vessel_name(name2)

        if not name1_clean or not name2_clean:
            return None

        # Use token set ratio for robust matching
        # This handles word order and partial matches well
        similarity = fuzz.token_set_ratio(name1_clean, name2_clean) / 100.0

        # Apply threshold - return 0 if below minimum similarity
        if similarity < self.config.name_similarity_threshold:
            return 0.0

        return similarity

    def _match_by_location(
        self,
        loc1: Tuple[Optional[float], Optional[float]],
        loc2: Tuple[Optional[float], Optional[float]],
        threshold_km: float,
    ) -> Optional[float]:
        """
        Match by geographic proximity using haversine distance.

        Args:
            loc1: First location (latitude, longitude).
            loc2: Second location (latitude, longitude).
            threshold_km: Maximum distance in km to consider a match.

        Returns:
            Proximity score (0-1) based on distance, or None if coordinates missing.
        """
        lat1, lon1 = loc1
        lat2, lon2 = loc2

        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return None

        # Validate coordinate ranges
        if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90):
            logger.warning("Invalid latitude values: %s, %s", lat1, lat2)
            return None
        if not (-180 <= lon1 <= 180 and -180 <= lon2 <= 180):
            logger.warning("Invalid longitude values: %s, %s", lon1, lon2)
            return None

        distance = self._haversine_distance(lat1, lon1, lat2, lon2)

        if distance <= threshold_km:
            # Linear decay: 1.0 at 0 km, 0.0 at threshold
            return 1.0 - (distance / threshold_km)
        return 0.0

    def _match_by_date(
        self,
        date1: Optional[date],
        date2: Optional[date],
        tolerance_days: int,
    ) -> Optional[float]:
        """
        Match by temporal proximity.

        Args:
            date1: First incident date.
            date2: Second incident date.
            tolerance_days: Maximum days apart to consider a match.

        Returns:
            Temporal proximity score (0-1), or None if either date is missing.
        """
        if date1 is None or date2 is None:
            return None

        # Convert datetime to date if needed
        if isinstance(date1, datetime):
            date1 = date1.date()
        if isinstance(date2, datetime):
            date2 = date2.date()

        days_apart = abs((date1 - date2).days)

        if days_apart <= tolerance_days:
            # Linear decay: 1.0 at 0 days, 0.0 at tolerance
            return 1.0 - (days_apart / tolerance_days) if tolerance_days > 0 else 1.0
        return 0.0

    def _combine_scores(
        self, scores: Dict[str, float], weights: Dict[str, float]
    ) -> float:
        """
        Combine individual match scores using weighted average.

        Only considers scores that are present (not None), re-normalizing
        weights to account for missing components.

        Args:
            scores: Dictionary of component scores.
            weights: Dictionary of component weights.

        Returns:
            Combined confidence score (0-1).
        """
        if not scores:
            return 0.0

        # Calculate weighted sum, only for scores that exist
        weighted_sum = 0.0
        weight_sum = 0.0

        for key, score in scores.items():
            if key in weights:
                weighted_sum += score * weights[key]
                weight_sum += weights[key]

        if weight_sum == 0:
            return 0.0

        # Normalize by actual weight sum
        return weighted_sum / weight_sum

    def _determine_match_type(self, scores: Dict[str, float]) -> MatchType:
        """
        Determine the primary match type based on component scores.

        Args:
            scores: Dictionary of component scores.

        Returns:
            The MatchType that contributed most to the match.
        """
        if not scores:
            return MatchType.COMBINED

        # Find highest scoring component
        max_component = max(scores.items(), key=lambda x: x[1])

        type_mapping = {
            "imo": MatchType.IMO,
            "name": MatchType.NAME,
            "location": MatchType.LOCATION,
            "date": MatchType.DATE,
        }

        return type_mapping.get(max_component[0], MatchType.COMBINED)

    def _normalize_vessel_name(self, name: str) -> str:
        """
        Normalize vessel name for comparison.

        - Converts to uppercase
        - Removes common prefixes (M/V, MV, SS, etc.)
        - Removes punctuation
        - Normalizes whitespace

        Args:
            name: Raw vessel name.

        Returns:
            Normalized vessel name.
        """
        if not name:
            return ""

        # Convert to uppercase
        normalized = name.upper().strip()

        # Remove common vessel prefixes
        prefixes = [
            "M/V ",
            "MV ",
            "M.V. ",
            "M.V ",
            "S/S ",
            "SS ",
            "S.S. ",
            "S.S ",
            "F/V ",
            "FV ",
            "F.V. ",
            "F.V ",
            "R/V ",
            "RV ",
            "R.V. ",
            "R.V ",
            "T/V ",
            "TV ",
            "T.V. ",
            "T.V ",
            "MT ",
            "M/T ",
            "M.T. ",
            "M.T ",
        ]
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]
                break

        # Remove punctuation except spaces
        normalized = "".join(
            c if c.isalnum() or c.isspace() else " " for c in normalized
        )

        # Normalize whitespace
        normalized = " ".join(normalized.split())

        return normalized

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate the great-circle distance between two points on Earth.

        Uses the haversine formula for accurate distance calculation.

        Args:
            lat1: Latitude of first point in degrees.
            lon1: Longitude of first point in degrees.
            lat2: Latitude of second point in degrees.
            lon2: Longitude of second point in degrees.

        Returns:
            Distance in kilometers.
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # Haversine formula
        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        return self.EARTH_RADIUS_KM * c

    def _normalize_incident(
        self, incident: Union[Dict[str, Any], Any]
    ) -> Optional[IncidentData]:
        """
        Normalize incident data to IncidentData format.

        Args:
            incident: Incident as dict, model, or IncidentData.

        Returns:
            Normalized IncidentData, or None if conversion fails.
        """
        if isinstance(incident, IncidentData):
            return incident

        try:
            if isinstance(incident, dict):
                return IncidentData.from_dict(incident)
            else:
                # Assume it's a database model
                return IncidentData.from_model(incident)
        except Exception as e:
            logger.warning("Failed to normalize incident: %s", e)
            return None
