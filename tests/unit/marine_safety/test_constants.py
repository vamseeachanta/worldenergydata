"""Tests for Marine Safety module constants and enumerations."""

from worldenergydata.marine_safety.constants import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    BSEE_REGIONS,
    DATA_QUALITY_FLAGS,
    DATA_SOURCE_URLS,
    DEFAULT_PRIORITY,
    DEFAULT_SEVERITY,
    DEFAULT_STATUS,
    MAX_LATITUDE,
    MAX_LENGTHS,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    OFFSHORE_REGIONS,
    RETRYABLE_HTTP_CODES,
    USCG_DISTRICTS,
    CauseCategory,
    DataSource,
    IncidentStatus,
    IncidentType,
    InvestigationPriority,
    SeaState,
    SeverityLevel,
    VesselFlag,
    VesselType,
    WeatherCondition,
)


class TestIncidentType:
    def test_collision(self):
        assert IncidentType.COLLISION.value == "collision"

    def test_all_values_are_strings(self):
        for member in IncidentType:
            assert isinstance(member.value, str)

    def test_member_count(self):
        assert len(IncidentType) == 17


class TestSeverityLevel:
    def test_minimal(self):
        assert SeverityLevel.MINIMAL == 1

    def test_catastrophic(self):
        assert SeverityLevel.CATASTROPHIC == 5

    def test_ordering(self):
        assert SeverityLevel.MINIMAL < SeverityLevel.CATASTROPHIC


class TestIncidentStatus:
    def test_reported(self):
        assert IncidentStatus.REPORTED.value == "reported"

    def test_member_count(self):
        assert len(IncidentStatus) == 6


class TestVesselType:
    def test_drilling_rig(self):
        assert VesselType.DRILLING_RIG.value == "drilling_rig"

    def test_fpso(self):
        assert VesselType.FPSO.value == "fpso"

    def test_member_count(self):
        assert len(VesselType) >= 20


class TestVesselFlag:
    def test_usa(self):
        assert VesselFlag.USA.value == "US"

    def test_norway(self):
        assert VesselFlag.NORWAY.value == "NO"


class TestWeatherCondition:
    def test_hurricane(self):
        assert WeatherCondition.HURRICANE.value == "hurricane"

    def test_member_count(self):
        assert len(WeatherCondition) == 11


class TestSeaState:
    def test_calm(self):
        assert SeaState.CALM == 0

    def test_phenomenal(self):
        assert SeaState.PHENOMENAL == 8

    def test_confused(self):
        assert SeaState.CONFUSED == 9


class TestDataSource:
    def test_bsee(self):
        assert DataSource.BSEE.value == "bsee"

    def test_uscg(self):
        assert DataSource.USCG.value == "uscg"


class TestInvestigationPriority:
    def test_low(self):
        assert InvestigationPriority.LOW.value == "low"

    def test_urgent(self):
        assert InvestigationPriority.URGENT.value == "urgent"


class TestCauseCategory:
    def test_human_error(self):
        assert CauseCategory.HUMAN_ERROR.value == "human_error"

    def test_member_count(self):
        assert len(CauseCategory) == 13


class TestConstants:
    def test_coordinate_bounds(self):
        assert MIN_LATITUDE == -90.0
        assert MAX_LATITUDE == 90.0
        assert MIN_LONGITUDE == -180.0
        assert MAX_LONGITUDE == 180.0

    def test_offshore_regions(self):
        assert "GOM" in OFFSHORE_REGIONS
        assert OFFSHORE_REGIONS["GOM"] == "Gulf of Mexico"

    def test_uscg_districts(self):
        assert "D8" in USCG_DISTRICTS
        assert "Gulf" in USCG_DISTRICTS["D8"]

    def test_bsee_regions(self):
        assert "GOM" in BSEE_REGIONS

    def test_data_quality_flags(self):
        assert "verified" in DATA_QUALITY_FLAGS
        assert "preliminary" in DATA_QUALITY_FLAGS

    def test_allowed_extensions(self):
        assert ".pdf" in ALLOWED_DOCUMENT_EXTENSIONS
        assert ".csv" in ALLOWED_DOCUMENT_EXTENSIONS

    def test_retryable_codes(self):
        assert 429 in RETRYABLE_HTTP_CODES
        assert 503 in RETRYABLE_HTTP_CODES

    def test_max_lengths(self):
        assert MAX_LENGTHS["url"] == 2048
        assert MAX_LENGTHS["vessel_name"] == 255

    def test_defaults(self):
        assert DEFAULT_SEVERITY == SeverityLevel.MODERATE
        assert DEFAULT_STATUS == IncidentStatus.REPORTED
        assert DEFAULT_PRIORITY == InvestigationPriority.MEDIUM

    def test_data_source_urls(self):
        assert "BSEE" in DATA_SOURCE_URLS
        assert "bsee.gov" in DATA_SOURCE_URLS["BSEE"]
