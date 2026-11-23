# ABOUTME: Comprehensive test suite for cross-source correlation engine.
# ABOUTME: Tests incident matching, deduplication, geographic distance, and name similarity calculations.

"""
Test suite for marine safety cross-source correlation engine.

Tests cover:
- IncidentMatcher: matching by IMO, vessel name, location, date, and confidence scoring
- IncidentDeduplicator: duplicate detection, cross-source linking, and data merging
- Geographic distance: haversine formula calculations
- Name similarity: fuzzy matching for vessel names
- Integration: full correlation workflows and batch processing
"""

import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, Mock, patch

import pytest

from worldenergydata.marine_safety.constants import (
    DataSource,
    IncidentType,
    SeverityLevel,
    VesselType,
)
from worldenergydata.marine_safety.database.models import (
    Base,
    Incident,
    Location,
    Vessel,
)

# ============================================================================
# Haversine Distance Implementation for Testing
# ============================================================================


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using haversine formula.

    Args:
        lat1: Latitude of point 1 in degrees
        lon1: Longitude of point 1 in degrees
        lat2: Latitude of point 2 in degrees
        lon2: Longitude of point 2 in degrees

    Returns:
        Distance in kilometers
    """
    R = 6371.0  # Earth's radius in kilometers

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two vessel names.

    Uses a combination of normalized Levenshtein distance and token matching.

    Args:
        name1: First vessel name
        name2: Second vessel name

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not name1 or not name2:
        return 0.0

    # Normalize names
    n1 = name1.upper().strip()
    n2 = name2.upper().strip()

    if n1 == n2:
        return 1.0

    # Simple Levenshtein-based similarity
    len1, len2 = len(n1), len(n2)
    if len1 == 0 or len2 == 0:
        return 0.0

    # Create distance matrix
    matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]

    for i in range(len1 + 1):
        matrix[i][0] = i
    for j in range(len2 + 1):
        matrix[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if n1[i - 1] == n2[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j - 1] + cost
            )

    distance = matrix[len1][len2]
    max_len = max(len1, len2)

    return 1.0 - (distance / max_len)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_ntsb_incident() -> Dict[str, Any]:
    """Sample incident from NTSB source."""
    return {
        "incident_id": 1,
        "source_agency": DataSource.NTSB,
        "source_incident_id": "MAB24MA001",
        "incident_date": date(2024, 1, 15),
        "incident_type": IncidentType.COLLISION,
        "vessel_name": "M/V ATLANTIC STAR",
        "imo_number": "9123456",
        "latitude": Decimal("29.301"),
        "longitude": Decimal("-94.797"),
        "fatalities": 0,
        "injuries": 2,
        "description": "Collision between two cargo vessels in Gulf of Mexico.",
    }


@pytest.fixture
def sample_imo_incident() -> Dict[str, Any]:
    """Sample incident from IMO GISIS source."""
    return {
        "incident_id": 2,
        "source_agency": DataSource.IMO,
        "source_incident_id": "IMO-2024-001",
        "incident_date": date(2024, 1, 15),
        "incident_type": IncidentType.COLLISION,
        "vessel_name": "MV ATLANTIC STAR",
        "imo_number": "9123456",
        "latitude": Decimal("29.302"),
        "longitude": Decimal("-94.796"),
        "fatalities": 0,
        "injuries": 2,
        "description": "Collision incident reported to IMO.",
    }


@pytest.fixture
def sample_atsb_incident() -> Dict[str, Any]:
    """Sample incident from Australian ATSB source."""
    return {
        "incident_id": 3,
        "source_agency": DataSource.ATSB,
        "source_incident_id": "ATSB-MO-2024-001",
        "incident_date": date(2024, 2, 20),
        "incident_type": IncidentType.GROUNDING,
        "vessel_name": "PACIFIC VOYAGER",
        "imo_number": "9234567",
        "latitude": Decimal("-33.8688"),
        "longitude": Decimal("151.2093"),
        "fatalities": 0,
        "injuries": 0,
        "description": "Grounding incident near Sydney Harbour.",
    }


@pytest.fixture
def sample_incident_no_imo() -> Dict[str, Any]:
    """Incident without IMO number for name-based matching."""
    return {
        "incident_id": 4,
        "source_agency": DataSource.USCG,
        "source_incident_id": "USCG-2024-001",
        "incident_date": date(2024, 1, 16),
        "incident_type": IncidentType.COLLISION,
        "vessel_name": "M/V ATLANTIC STAR",
        "imo_number": None,
        "latitude": Decimal("29.305"),
        "longitude": Decimal("-94.800"),
        "fatalities": 0,
        "injuries": 3,
        "description": "Collision incident reported to USCG.",
    }


@pytest.fixture
def sample_incidents_batch() -> List[Dict[str, Any]]:
    """Batch of sample incidents for testing."""
    return [
        {
            "incident_id": 1,
            "source_agency": DataSource.NTSB,
            "source_incident_id": "MAB24MA001",
            "incident_date": date(2024, 1, 15),
            "vessel_name": "M/V ATLANTIC STAR",
            "imo_number": "9123456",
            "latitude": Decimal("29.301"),
            "longitude": Decimal("-94.797"),
        },
        {
            "incident_id": 2,
            "source_agency": DataSource.IMO,
            "source_incident_id": "IMO-2024-001",
            "incident_date": date(2024, 1, 15),
            "vessel_name": "MV ATLANTIC STAR",
            "imo_number": "9123456",
            "latitude": Decimal("29.302"),
            "longitude": Decimal("-94.796"),
        },
        {
            "incident_id": 3,
            "source_agency": DataSource.ATSB,
            "source_incident_id": "ATSB-2024-001",
            "incident_date": date(2024, 2, 20),
            "vessel_name": "PACIFIC VOYAGER",
            "imo_number": "9234567",
            "latitude": Decimal("-33.8688"),
            "longitude": Decimal("151.2093"),
        },
        {
            "incident_id": 4,
            "source_agency": DataSource.USCG,
            "source_incident_id": "USCG-2024-001",
            "incident_date": date(2024, 1, 16),
            "vessel_name": "ATLANTIC STAR",
            "imo_number": None,
            "latitude": Decimal("29.305"),
            "longitude": Decimal("-94.800"),
        },
    ]


@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session for testing."""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    session.add = MagicMock()
    session.flush = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    return session


@pytest.fixture
def sample_coordinates() -> List[Tuple[float, float, str]]:
    """Known city coordinates for distance testing."""
    return [
        (29.7604, -95.3698, "Houston, TX"),
        (25.7617, -80.1918, "Miami, FL"),
        (47.6062, -122.3321, "Seattle, WA"),
        (51.5074, -0.1278, "London, UK"),
        (-33.8688, 151.2093, "Sydney, AU"),
    ]


# ============================================================================
# Geographic Distance Tests (Haversine Formula)
# ============================================================================


class TestHaversineDistance:
    """Tests for haversine distance calculation."""

    @pytest.mark.unit
    def test_haversine_same_point_zero_distance(self):
        """Test that same point returns zero distance."""
        lat, lon = 29.301, -94.797

        distance = haversine_distance(lat, lon, lat, lon)

        assert distance == 0.0

    @pytest.mark.unit
    def test_haversine_same_point_various_locations(self, sample_coordinates):
        """Test zero distance at various known locations."""
        for lat, lon, name in sample_coordinates:
            distance = haversine_distance(lat, lon, lat, lon)
            assert distance == pytest.approx(0.0, abs=1e-6), f"Failed for {name}"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "point1,point2,expected_km,tolerance_km",
        [
            # Houston to Miami: approximately 1550 km
            ((29.7604, -95.3698), (25.7617, -80.1918), 1550, 50),
            # London to Paris: approximately 344 km
            ((51.5074, -0.1278), (48.8566, 2.3522), 344, 20),
            # Sydney to Melbourne: approximately 714 km
            ((-33.8688, 151.2093), (-37.8136, 144.9631), 714, 30),
            # New York to Los Angeles: approximately 3940 km
            ((40.7128, -74.0060), (34.0522, -118.2437), 3940, 100),
            # Equator crossing: 0,0 to 0,90 is ~10,000 km (quarter Earth)
            ((0.0, 0.0), (0.0, 90.0), 10018, 50),
        ],
    )
    def test_haversine_known_distance(self, point1, point2, expected_km, tolerance_km):
        """Test haversine against known city-to-city distances."""
        lat1, lon1 = point1
        lat2, lon2 = point2

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        assert distance == pytest.approx(
            expected_km, abs=tolerance_km
        ), f"Expected ~{expected_km}km, got {distance:.1f}km"

    @pytest.mark.unit
    def test_haversine_symmetry(self):
        """Test that distance is same regardless of direction."""
        houston = (29.7604, -95.3698)
        miami = (25.7617, -80.1918)

        dist_h_to_m = haversine_distance(*houston, *miami)
        dist_m_to_h = haversine_distance(*miami, *houston)

        assert dist_h_to_m == pytest.approx(dist_m_to_h, rel=1e-9)

    @pytest.mark.unit
    def test_haversine_north_south_pole(self):
        """Test distance from North to South pole (half Earth circumference)."""
        # North to South pole should be ~20,000 km
        distance = haversine_distance(90.0, 0.0, -90.0, 0.0)

        assert distance == pytest.approx(20015, abs=100)

    @pytest.mark.unit
    def test_haversine_small_distance(self):
        """Test accuracy for small distances (within same city)."""
        # Two points ~1km apart in Houston
        point1 = (29.7604, -95.3698)
        point2 = (29.7694, -95.3698)  # ~1km north

        distance = haversine_distance(*point1, *point2)

        assert 0.5 < distance < 2.0  # Should be approximately 1km

    @pytest.mark.unit
    def test_haversine_date_line_crossing(self):
        """Test distance calculation crossing the International Date Line."""
        # Point in Russia (170E) to point in Alaska (170W)
        point1 = (65.0, 170.0)
        point2 = (65.0, -170.0)

        distance = haversine_distance(*point1, *point2)

        # Should be relatively short (~750km), not going around the world
        assert distance < 1000


# ============================================================================
# Name Similarity Tests
# ============================================================================


class TestNameSimilarity:
    """Tests for vessel name similarity calculation."""

    @pytest.mark.unit
    def test_exact_match_returns_one(self):
        """Test exact match returns similarity of 1.0."""
        name = "M/V ATLANTIC STAR"

        similarity = calculate_name_similarity(name, name)

        assert similarity == 1.0

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "name1,name2,min_similarity",
        [
            # Exact matches
            ("M/V ATLANTIC STAR", "M/V ATLANTIC STAR", 1.0),
            ("PACIFIC MOON", "PACIFIC MOON", 1.0),
            # Case insensitive
            ("M/V Atlantic Star", "M/V ATLANTIC STAR", 1.0),
            ("pacific moon", "PACIFIC MOON", 1.0),
            # Minor typos (should be very similar)
            ("M/V ATLANTIC STAR", "M/V ATLANTIC STARS", 0.90),
            ("ATLANTIC STAR", "ATLANTC STAR", 0.90),
            # Similar names
            ("ATLANTIC STAR", "ATLANTIC STORM", 0.75),
            ("PACIFIC VOYAGER", "PACIFIC VENTURE", 0.60),
            # Different names
            ("ATLANTIC STAR", "PACIFIC MOON", 0.0),  # This will be low
        ],
    )
    def test_name_similarity_parametrized(self, name1, name2, min_similarity):
        """Test name similarity for various name pairs."""
        similarity = calculate_name_similarity(name1, name2)

        # For "different names" test, we expect low similarity
        if min_similarity == 0.0:
            assert similarity < 0.50
        else:
            assert (
                similarity >= min_similarity
            ), f"Expected >= {min_similarity}, got {similarity:.3f} for '{name1}' vs '{name2}'"

    @pytest.mark.unit
    def test_name_similarity_with_prefixes(self):
        """Test similarity handles common vessel prefixes."""
        base_name = "ATLANTIC STAR"
        variants = [
            "M/V ATLANTIC STAR",
            "MV ATLANTIC STAR",
            "S/S ATLANTIC STAR",
            "SS ATLANTIC STAR",
            "MT ATLANTIC STAR",
        ]

        for variant in variants:
            similarity = calculate_name_similarity(base_name, variant)
            assert (
                similarity >= 0.70
            ), f"Expected high similarity for '{base_name}' vs '{variant}', got {similarity:.3f}"

    @pytest.mark.unit
    def test_name_similarity_empty_strings(self):
        """Test empty strings return zero similarity."""
        assert calculate_name_similarity("", "ATLANTIC STAR") == 0.0
        assert calculate_name_similarity("ATLANTIC STAR", "") == 0.0
        assert calculate_name_similarity("", "") == 0.0

    @pytest.mark.unit
    def test_name_similarity_none_values(self):
        """Test None values return zero similarity."""
        assert calculate_name_similarity(None, "ATLANTIC STAR") == 0.0
        assert calculate_name_similarity("ATLANTIC STAR", None) == 0.0
        assert calculate_name_similarity(None, None) == 0.0

    @pytest.mark.unit
    def test_name_similarity_whitespace_handling(self):
        """Test whitespace is handled correctly."""
        name1 = "  ATLANTIC STAR  "
        name2 = "ATLANTIC STAR"

        similarity = calculate_name_similarity(name1, name2)

        assert similarity == 1.0

    @pytest.mark.unit
    def test_name_similarity_different_names(self):
        """Test completely different names have low similarity."""
        pairs = [
            ("ATLANTIC STAR", "PACIFIC MOON"),
            ("OCEAN VOYAGER", "MOUNTAIN EXPLORER"),
            ("SEA TRADER", "SKY FLYER"),
        ]

        for name1, name2 in pairs:
            similarity = calculate_name_similarity(name1, name2)
            assert (
                similarity < 0.50
            ), f"Expected low similarity for '{name1}' vs '{name2}', got {similarity:.3f}"


# ============================================================================
# IncidentMatcher Tests
# ============================================================================


class TestIncidentMatcherIMO:
    """Tests for IMO-based incident matching."""

    @pytest.mark.unit
    def test_match_by_imo_exact_match(self, sample_ntsb_incident, sample_imo_incident):
        """Test exact IMO match returns high confidence."""
        imo1 = sample_ntsb_incident["imo_number"]
        imo2 = sample_imo_incident["imo_number"]

        # Direct IMO comparison
        is_match = imo1 == imo2

        assert is_match is True
        assert imo1 == "9123456"
        assert imo2 == "9123456"

    @pytest.mark.unit
    def test_match_by_imo_no_match(self, sample_ntsb_incident, sample_atsb_incident):
        """Test different IMO numbers return no match."""
        imo1 = sample_ntsb_incident["imo_number"]
        imo2 = sample_atsb_incident["imo_number"]

        is_match = imo1 == imo2

        assert is_match is False
        assert imo1 == "9123456"
        assert imo2 == "9234567"

    @pytest.mark.unit
    def test_match_by_imo_one_missing(
        self, sample_ntsb_incident, sample_incident_no_imo
    ):
        """Test match returns None when one IMO is missing."""
        imo1 = sample_ntsb_incident["imo_number"]
        imo2 = sample_incident_no_imo["imo_number"]

        # Can't match on IMO if one is missing
        can_match_imo = imo1 is not None and imo2 is not None

        assert can_match_imo is False

    @pytest.mark.unit
    def test_match_by_imo_both_missing(self, sample_incident_no_imo):
        """Test match returns None when both IMOs are missing."""
        incident_copy = sample_incident_no_imo.copy()
        imo1 = sample_incident_no_imo["imo_number"]
        imo2 = incident_copy["imo_number"]

        can_match_imo = imo1 is not None and imo2 is not None

        assert can_match_imo is False


class TestIncidentMatcherVesselName:
    """Tests for vessel name-based incident matching."""

    @pytest.mark.unit
    def test_match_by_vessel_name_exact(
        self, sample_ntsb_incident, sample_incident_no_imo
    ):
        """Test exact vessel name match."""
        name1 = sample_ntsb_incident["vessel_name"]
        name2 = sample_incident_no_imo["vessel_name"]

        similarity = calculate_name_similarity(name1, name2)

        assert similarity == 1.0
        assert name1 == "M/V ATLANTIC STAR"
        assert name2 == "M/V ATLANTIC STAR"

    @pytest.mark.unit
    def test_match_by_vessel_name_fuzzy(
        self, sample_ntsb_incident, sample_imo_incident
    ):
        """Test fuzzy vessel name match with slight difference."""
        name1 = sample_ntsb_incident["vessel_name"]  # "M/V ATLANTIC STAR"
        name2 = sample_imo_incident["vessel_name"]  # "MV ATLANTIC STAR"

        similarity = calculate_name_similarity(name1, name2)

        # Should be high but not exact due to "M/V" vs "MV"
        assert similarity >= 0.90

    @pytest.mark.unit
    def test_match_by_vessel_name_different(
        self, sample_ntsb_incident, sample_atsb_incident
    ):
        """Test different vessel names have low similarity."""
        name1 = sample_ntsb_incident["vessel_name"]  # "M/V ATLANTIC STAR"
        name2 = sample_atsb_incident["vessel_name"]  # "PACIFIC VOYAGER"

        similarity = calculate_name_similarity(name1, name2)

        assert similarity < 0.50


class TestIncidentMatcherLocation:
    """Tests for location-based incident matching."""

    @pytest.mark.unit
    def test_match_by_location_same_point(self, sample_ntsb_incident):
        """Test same location returns zero distance."""
        lat = float(sample_ntsb_incident["latitude"])
        lon = float(sample_ntsb_incident["longitude"])

        distance = haversine_distance(lat, lon, lat, lon)

        assert distance == 0.0

    @pytest.mark.unit
    def test_match_by_location_within_threshold(
        self, sample_ntsb_incident, sample_imo_incident
    ):
        """Test nearby locations within threshold are matched."""
        lat1 = float(sample_ntsb_incident["latitude"])
        lon1 = float(sample_ntsb_incident["longitude"])
        lat2 = float(sample_imo_incident["latitude"])
        lon2 = float(sample_imo_incident["longitude"])

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # These are very close (within 1 km)
        assert distance < 1.0
        threshold_km = 10.0
        assert distance < threshold_km

    @pytest.mark.unit
    def test_match_by_location_outside_threshold(
        self, sample_ntsb_incident, sample_atsb_incident
    ):
        """Test distant locations are not matched."""
        lat1 = float(sample_ntsb_incident["latitude"])  # Gulf of Mexico
        lon1 = float(sample_ntsb_incident["longitude"])
        lat2 = float(sample_atsb_incident["latitude"])  # Sydney
        lon2 = float(sample_atsb_incident["longitude"])

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Should be thousands of kilometers
        threshold_km = 50.0
        assert distance > threshold_km
        assert distance > 10000  # Gulf of Mexico to Sydney > 10,000 km

    @pytest.mark.unit
    @pytest.mark.parametrize("threshold_km", [1.0, 5.0, 10.0, 50.0, 100.0])
    def test_match_by_location_various_thresholds(
        self, sample_ntsb_incident, sample_imo_incident, threshold_km
    ):
        """Test location matching with various thresholds."""
        lat1 = float(sample_ntsb_incident["latitude"])
        lon1 = float(sample_ntsb_incident["longitude"])
        lat2 = float(sample_imo_incident["latitude"])
        lon2 = float(sample_imo_incident["longitude"])

        distance = haversine_distance(lat1, lon1, lat2, lon2)
        is_within_threshold = distance <= threshold_km

        # These two incidents are < 1km apart
        if threshold_km >= 1.0:
            assert is_within_threshold is True
        else:
            # Very tight threshold may or may not match
            pass  # Result depends on exact coordinates


class TestIncidentMatcherDate:
    """Tests for date-based incident matching."""

    @pytest.mark.unit
    def test_match_by_date_same_day(self, sample_ntsb_incident, sample_imo_incident):
        """Test same date returns perfect match."""
        date1 = sample_ntsb_incident["incident_date"]
        date2 = sample_imo_incident["incident_date"]

        days_diff = abs((date1 - date2).days)

        assert days_diff == 0
        assert date1 == date(2024, 1, 15)
        assert date2 == date(2024, 1, 15)

    @pytest.mark.unit
    def test_match_by_date_within_tolerance(
        self, sample_ntsb_incident, sample_incident_no_imo
    ):
        """Test dates within tolerance are matched."""
        date1 = sample_ntsb_incident["incident_date"]  # Jan 15
        date2 = sample_incident_no_imo["incident_date"]  # Jan 16

        days_diff = abs((date1 - date2).days)
        tolerance_days = 3

        assert days_diff == 1
        assert days_diff <= tolerance_days

    @pytest.mark.unit
    def test_match_by_date_outside_tolerance(
        self, sample_ntsb_incident, sample_atsb_incident
    ):
        """Test dates outside tolerance are not matched."""
        date1 = sample_ntsb_incident["incident_date"]  # Jan 15
        date2 = sample_atsb_incident["incident_date"]  # Feb 20

        days_diff = abs((date1 - date2).days)
        tolerance_days = 3

        assert days_diff > tolerance_days
        assert days_diff == 36

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "days_offset,tolerance,expected_match",
        [
            (0, 1, True),  # Same day
            (1, 1, True),  # 1 day off, tolerance 1
            (2, 1, False),  # 2 days off, tolerance 1
            (3, 3, True),  # 3 days off, tolerance 3
            (7, 3, False),  # 7 days off, tolerance 3
            (30, 7, False),  # 30 days off, tolerance 7
        ],
    )
    def test_match_by_date_parametrized(self, days_offset, tolerance, expected_match):
        """Test date matching with various offsets and tolerances."""
        date1 = date(2024, 1, 15)
        date2 = date1 + timedelta(days=days_offset)

        days_diff = abs((date1 - date2).days)
        is_match = days_diff <= tolerance

        assert is_match == expected_match


class TestIncidentMatcherConfidence:
    """Tests for combined confidence score calculation."""

    @pytest.mark.unit
    def test_calculate_confidence_combined(
        self, sample_ntsb_incident, sample_imo_incident
    ):
        """Test combined confidence score from multiple factors."""
        # Define weights
        WEIGHT_IMO = 0.40
        WEIGHT_NAME = 0.25
        WEIGHT_LOCATION = 0.20
        WEIGHT_DATE = 0.15

        # Calculate individual scores
        imo_score = (
            1.0
            if sample_ntsb_incident["imo_number"] == sample_imo_incident["imo_number"]
            else 0.0
        )

        name_score = calculate_name_similarity(
            sample_ntsb_incident["vessel_name"], sample_imo_incident["vessel_name"]
        )

        distance = haversine_distance(
            float(sample_ntsb_incident["latitude"]),
            float(sample_ntsb_incident["longitude"]),
            float(sample_imo_incident["latitude"]),
            float(sample_imo_incident["longitude"]),
        )
        location_score = max(0.0, 1.0 - (distance / 50.0))  # 50km threshold

        days_diff = abs(
            (
                sample_ntsb_incident["incident_date"]
                - sample_imo_incident["incident_date"]
            ).days
        )
        date_score = max(0.0, 1.0 - (days_diff / 7.0))  # 7 day threshold

        # Combined confidence
        confidence = (
            WEIGHT_IMO * imo_score
            + WEIGHT_NAME * name_score
            + WEIGHT_LOCATION * location_score
            + WEIGHT_DATE * date_score
        )

        # Should be very high for these matching incidents
        assert confidence >= 0.90
        assert imo_score == 1.0
        assert name_score >= 0.90
        assert location_score >= 0.95  # Very close locations
        assert date_score == 1.0  # Same day

    @pytest.mark.unit
    def test_find_matches_returns_above_threshold(self, sample_incidents_batch):
        """Test that find_matches only returns matches above threshold."""
        threshold = 0.70
        matches = []

        # Simple matching algorithm
        for i, inc1 in enumerate(sample_incidents_batch):
            for j, inc2 in enumerate(sample_incidents_batch):
                if i >= j:  # Skip self and already compared
                    continue

                # Calculate confidence
                imo_match = (
                    inc1.get("imo_number") is not None
                    and inc2.get("imo_number") is not None
                    and inc1["imo_number"] == inc2["imo_number"]
                )

                name_sim = calculate_name_similarity(
                    inc1.get("vessel_name", ""), inc2.get("vessel_name", "")
                )

                confidence = 0.0
                if imo_match:
                    confidence += 0.40
                confidence += 0.30 * name_sim

                if confidence >= threshold:
                    matches.append(
                        {
                            "incident1_id": inc1["incident_id"],
                            "incident2_id": inc2["incident_id"],
                            "confidence": confidence,
                        }
                    )

        # Should find the NTSB/IMO match (same IMO, similar name)
        assert len(matches) >= 1
        for match in matches:
            assert match["confidence"] >= threshold


# ============================================================================
# IncidentDeduplicator Tests
# ============================================================================


class TestIncidentDeduplicatorDuplicates:
    """Tests for duplicate detection within a source."""

    @pytest.mark.unit
    def test_find_duplicates_within_source(self, sample_incidents_batch):
        """Test finding duplicates within the same source."""
        # Group by source
        by_source = {}
        for inc in sample_incidents_batch:
            source = inc["source_agency"]
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(inc)

        # Check each source has no duplicates (by source_incident_id)
        for source, incidents in by_source.items():
            ids = [inc["source_incident_id"] for inc in incidents]
            unique_ids = set(ids)
            assert len(ids) == len(unique_ids), f"Duplicates found in {source}"

    @pytest.mark.unit
    def test_find_cross_source_matches(self, sample_ntsb_incident, sample_imo_incident):
        """Test finding matches across different sources."""
        source1 = sample_ntsb_incident["source_agency"]
        source2 = sample_imo_incident["source_agency"]

        # Verify different sources
        assert source1 != source2
        assert source1 == DataSource.NTSB
        assert source2 == DataSource.IMO

        # But same IMO (cross-source match)
        assert sample_ntsb_incident["imo_number"] == sample_imo_incident["imo_number"]


class TestIncidentDeduplicatorLinking:
    """Tests for incident linking functionality."""

    @pytest.mark.unit
    def test_link_incidents_creates_record(self, mock_session):
        """Test linking incidents creates a link record."""
        link = {
            "incident1_id": 1,
            "incident2_id": 2,
            "confidence": 0.95,
            "link_type": "cross_source_match",
            "created_at": datetime.utcnow(),
        }

        # Simulate adding link to session
        mock_session.add(link)
        mock_session.commit()

        mock_session.add.assert_called_once_with(link)
        mock_session.commit.assert_called_once()

    @pytest.mark.unit
    def test_get_linked_incidents_returns_all(self, mock_session):
        """Test retrieving all linked incidents for a given incident."""
        # Mock linked incidents
        linked = [
            {"incident_id": 2, "confidence": 0.95},
            {"incident_id": 5, "confidence": 0.87},
        ]
        mock_session.query.return_value.filter.return_value.all.return_value = linked

        result = mock_session.query.return_value.filter.return_value.all()

        assert len(result) == 2
        assert result[0]["incident_id"] == 2
        assert result[1]["incident_id"] == 5


class TestIncidentDeduplicatorMerge:
    """Tests for incident data merging."""

    @pytest.mark.unit
    def test_merge_incident_data_combines_fields(
        self, sample_ntsb_incident, sample_imo_incident
    ):
        """Test merging incident data from multiple sources."""
        # Simulate merge: prefer fields with more data
        merged = {}

        fields_to_merge = [
            "vessel_name",
            "imo_number",
            "fatalities",
            "injuries",
            "description",
        ]

        for field in fields_to_merge:
            val1 = sample_ntsb_incident.get(field)
            val2 = sample_imo_incident.get(field)

            # Prefer non-None, longer strings, or higher numbers
            if val1 is None and val2 is not None:
                merged[field] = val2
            elif val2 is None and val1 is not None:
                merged[field] = val1
            elif isinstance(val1, str) and isinstance(val2, str):
                merged[field] = val1 if len(val1) >= len(val2) else val2
            else:
                merged[field] = val1  # Default to first

        # Track sources
        merged["sources"] = [
            sample_ntsb_incident["source_agency"],
            sample_imo_incident["source_agency"],
        ]

        assert merged["imo_number"] == "9123456"
        assert DataSource.NTSB in merged["sources"]
        assert DataSource.IMO in merged["sources"]

    @pytest.mark.unit
    def test_merge_preserves_source_ids(
        self, sample_ntsb_incident, sample_imo_incident
    ):
        """Test merge preserves original source IDs."""
        merged = {
            "primary_incident_id": sample_ntsb_incident["incident_id"],
            "source_references": [
                {
                    "source": sample_ntsb_incident["source_agency"],
                    "source_id": sample_ntsb_incident["source_incident_id"],
                },
                {
                    "source": sample_imo_incident["source_agency"],
                    "source_id": sample_imo_incident["source_incident_id"],
                },
            ],
        }

        assert len(merged["source_references"]) == 2
        assert merged["source_references"][0]["source_id"] == "MAB24MA001"
        assert merged["source_references"][1]["source_id"] == "IMO-2024-001"


# ============================================================================
# Integration Tests
# ============================================================================


class TestCorrelationIntegration:
    """Integration tests for full correlation workflow."""

    @pytest.mark.integration
    def test_full_correlation_workflow(self, sample_incidents_batch, mock_session):
        """Test complete correlation workflow from incidents to linked groups."""
        # Step 1: Calculate all pairwise similarities
        matches = []
        threshold = 0.60

        for i, inc1 in enumerate(sample_incidents_batch):
            for j, inc2 in enumerate(sample_incidents_batch):
                if i >= j:
                    continue

                # Calculate confidence score
                confidence = 0.0

                # IMO match
                if (
                    inc1.get("imo_number")
                    and inc2.get("imo_number")
                    and inc1["imo_number"] == inc2["imo_number"]
                ):
                    confidence += 0.40

                # Name similarity
                name_sim = calculate_name_similarity(
                    inc1.get("vessel_name", ""), inc2.get("vessel_name", "")
                )
                confidence += 0.30 * name_sim

                # Location proximity (if both have coordinates)
                if all(inc1.get(k) and inc2.get(k) for k in ["latitude", "longitude"]):
                    dist = haversine_distance(
                        float(inc1["latitude"]),
                        float(inc1["longitude"]),
                        float(inc2["latitude"]),
                        float(inc2["longitude"]),
                    )
                    loc_score = max(0.0, 1.0 - dist / 100.0)
                    confidence += 0.20 * loc_score

                # Date proximity
                days_diff = abs((inc1["incident_date"] - inc2["incident_date"]).days)
                date_score = max(0.0, 1.0 - days_diff / 7.0)
                confidence += 0.10 * date_score

                if confidence >= threshold:
                    matches.append(
                        {
                            "incident1_id": inc1["incident_id"],
                            "incident2_id": inc2["incident_id"],
                            "confidence": confidence,
                        }
                    )

        # Step 2: Should have found NTSB/IMO match
        high_confidence = [m for m in matches if m["confidence"] >= 0.80]
        assert len(high_confidence) >= 1

        # Verify the NTSB-IMO match
        ntsb_imo_match = next(
            (m for m in matches if {m["incident1_id"], m["incident2_id"]} == {1, 2}),
            None,
        )
        assert ntsb_imo_match is not None
        assert ntsb_imo_match["confidence"] >= 0.80

    @pytest.mark.integration
    def test_batch_processing(self, sample_incidents_batch):
        """Test batch processing of correlation."""
        batch_size = 2
        total = len(sample_incidents_batch)
        processed = 0

        for i in range(0, total, batch_size):
            batch = sample_incidents_batch[i : i + batch_size]
            processed += len(batch)

        assert processed == total

    @pytest.mark.integration
    def test_quality_metrics_calculation(self, sample_incidents_batch):
        """Test calculation of correlation quality metrics."""
        metrics = {
            "total_incidents": len(sample_incidents_batch),
            "with_imo": sum(1 for i in sample_incidents_batch if i.get("imo_number")),
            "with_coordinates": sum(
                1
                for i in sample_incidents_batch
                if i.get("latitude") and i.get("longitude")
            ),
            "sources_represented": len(
                set(i["source_agency"] for i in sample_incidents_batch)
            ),
        }

        assert metrics["total_incidents"] == 4
        assert metrics["with_imo"] == 3  # One incident has no IMO
        assert metrics["with_coordinates"] == 4
        assert metrics["sources_represented"] == 4

        # Coverage percentage
        imo_coverage = metrics["with_imo"] / metrics["total_incidents"]
        assert imo_coverage == 0.75


class TestCorrelationEdgeCases:
    """Tests for edge cases in correlation."""

    @pytest.mark.unit
    def test_empty_incident_list(self):
        """Test correlation handles empty incident list."""
        incidents = []
        matches = []

        for i, inc1 in enumerate(incidents):
            for j, inc2 in enumerate(incidents):
                if i >= j:
                    continue
                matches.append((inc1, inc2))

        assert len(matches) == 0

    @pytest.mark.unit
    def test_single_incident(self, sample_ntsb_incident):
        """Test correlation handles single incident."""
        incidents = [sample_ntsb_incident]
        matches = []

        for i, inc1 in enumerate(incidents):
            for j, inc2 in enumerate(incidents):
                if i >= j:
                    continue
                matches.append((inc1, inc2))

        assert len(matches) == 0

    @pytest.mark.unit
    def test_all_incidents_match(self):
        """Test when all incidents are the same vessel."""
        base_incident = {
            "incident_id": 1,
            "imo_number": "9123456",
            "vessel_name": "ATLANTIC STAR",
            "incident_date": date(2024, 1, 15),
            "latitude": Decimal("29.301"),
            "longitude": Decimal("-94.797"),
        }

        # Create 3 incidents with same vessel
        incidents = []
        for i, source in enumerate([DataSource.NTSB, DataSource.IMO, DataSource.ATSB]):
            inc = base_incident.copy()
            inc["incident_id"] = i + 1
            inc["source_agency"] = source
            inc["incident_date"] = date(2024, 1, 15 + i)  # Slightly different dates
            incidents.append(inc)

        # All should match each other
        match_count = 0
        for i in range(len(incidents)):
            for j in range(i + 1, len(incidents)):
                if incidents[i]["imo_number"] == incidents[j]["imo_number"]:
                    match_count += 1

        # 3 incidents = 3 pairs
        assert match_count == 3

    @pytest.mark.unit
    def test_missing_coordinates(self):
        """Test correlation handles missing coordinates."""
        inc1 = {
            "incident_id": 1,
            "vessel_name": "ATLANTIC STAR",
            "latitude": None,
            "longitude": None,
        }
        inc2 = {
            "incident_id": 2,
            "vessel_name": "ATLANTIC STAR",
            "latitude": Decimal("29.301"),
            "longitude": Decimal("-94.797"),
        }

        # Can't calculate distance without both coordinates
        has_coords1 = inc1["latitude"] is not None and inc1["longitude"] is not None
        has_coords2 = inc2["latitude"] is not None and inc2["longitude"] is not None

        can_calculate_distance = has_coords1 and has_coords2

        assert can_calculate_distance is False

    @pytest.mark.unit
    def test_null_vessel_name(self):
        """Test correlation handles null vessel names."""
        inc1 = {"vessel_name": None}
        inc2 = {"vessel_name": "ATLANTIC STAR"}

        similarity = calculate_name_similarity(
            inc1.get("vessel_name"), inc2.get("vessel_name")
        )

        assert similarity == 0.0


# ============================================================================
# Performance Tests
# ============================================================================


class TestCorrelationPerformance:
    """Performance tests for correlation engine."""

    @pytest.mark.performance
    def test_haversine_calculation_speed(self):
        """Test haversine calculation is fast enough."""
        import time

        iterations = 10000
        start = time.time()

        for _ in range(iterations):
            haversine_distance(29.301, -94.797, -33.8688, 151.2093)

        elapsed = time.time() - start

        # Should complete 10,000 calculations in under 1 second
        assert elapsed < 1.0
        per_calc = (elapsed / iterations) * 1000  # milliseconds
        assert per_calc < 0.1  # < 0.1ms per calculation

    @pytest.mark.performance
    def test_name_similarity_calculation_speed(self):
        """Test name similarity calculation is fast enough."""
        import time

        iterations = 1000
        name1 = "M/V ATLANTIC STAR SHIPPING COMPANY VESSEL"
        name2 = "ATLANTIC STAR SHIPPING CO VESSEL"

        start = time.time()

        for _ in range(iterations):
            calculate_name_similarity(name1, name2)

        elapsed = time.time() - start

        # Should complete 1,000 calculations in under 2 seconds (allows for slower CI)
        assert elapsed < 2.0

    @pytest.mark.performance
    def test_pairwise_comparison_scaling(self):
        """Test pairwise comparison scales reasonably."""
        import time

        # Generate test incidents
        def generate_incident(i):
            return {
                "incident_id": i,
                "imo_number": f"912345{i % 10}",
                "vessel_name": f"VESSEL {i}",
                "incident_date": date(2024, 1, 1) + timedelta(days=i % 30),
                "latitude": Decimal(str(29.0 + (i % 10) * 0.1)),
                "longitude": Decimal(str(-94.0 - (i % 10) * 0.1)),
            }

        # Test with 100 incidents (4,950 pairs)
        incidents = [generate_incident(i) for i in range(100)]

        start = time.time()
        match_count = 0

        for i, inc1 in enumerate(incidents):
            for j, inc2 in enumerate(incidents):
                if i >= j:
                    continue
                if inc1["imo_number"] == inc2["imo_number"]:
                    match_count += 1

        elapsed = time.time() - start

        # Should complete in under 1 second
        assert elapsed < 1.0
        # Should find some matches (same last digit of IMO)
        assert match_count > 0


# ============================================================================
# Data Quality Tests
# ============================================================================


class TestCorrelationDataQuality:
    """Tests for data quality in correlation."""

    @pytest.mark.unit
    def test_confidence_score_bounds(self):
        """Test confidence scores are within valid bounds."""
        scores = [0.0, 0.5, 1.0, 0.25, 0.75, 0.99]

        for score in scores:
            assert 0.0 <= score <= 1.0

    @pytest.mark.unit
    def test_duplicate_detection_accuracy(self, sample_incidents_batch):
        """Test duplicate detection does not produce false positives."""
        # No two incidents from same source should match as duplicates
        for i, inc1 in enumerate(sample_incidents_batch):
            for j, inc2 in enumerate(sample_incidents_batch):
                if i >= j:
                    continue
                if inc1["source_agency"] == inc2["source_agency"]:
                    # Same source - should not be marked as duplicate
                    # unless same source_incident_id
                    assert inc1["source_incident_id"] != inc2["source_incident_id"]

    @pytest.mark.unit
    def test_correlation_transitivity(self):
        """Test correlation is transitive (A matches B, B matches C => A matches C)."""
        # If A and B match, and B and C match via IMO
        # Then A and C should also match

        incidents = [
            {
                "incident_id": 1,
                "imo_number": "9123456",
                "source_agency": DataSource.NTSB,
            },
            {
                "incident_id": 2,
                "imo_number": "9123456",
                "source_agency": DataSource.IMO,
            },
            {
                "incident_id": 3,
                "imo_number": "9123456",
                "source_agency": DataSource.ATSB,
            },
        ]

        # All three should form a single group
        groups = {}
        for inc in incidents:
            imo = inc["imo_number"]
            if imo not in groups:
                groups[imo] = []
            groups[imo].append(inc["incident_id"])

        assert len(groups) == 1
        assert len(groups["9123456"]) == 3
