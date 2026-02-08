"""
Tests for ConfigRouter infrastructure data types (Phase 2).

Validates that the 4 new infrastructure data types are properly
integrated into the configuration router's default config,
validation, and system info reporting.
"""

from worldenergydata.bsee.data.config.config_router import ConfigRouter

INFRASTRUCTURE_KEYS = [
    "platform",
    "pipeline_permit",
    "deepwater_structure",
    "pipeline_location",
]


def test_default_config_has_infrastructure_flags():
    """New infrastructure data flags are present in the default enhanced config."""
    router = ConfigRouter()
    config = router.get_default_enhanced_config()
    data_section = config.get("data", {})

    for key in INFRASTRUCTURE_KEYS:
        assert key in data_section, f"Missing data flag: {key}"
        assert data_section[key] is True, f"Data flag '{key}' should default to True"


def test_default_config_has_infrastructure_sources():
    """Infrastructure source URLs are present in the default enhanced config."""
    router = ConfigRouter()
    config = router.get_default_enhanced_config()
    sources = config.get("sources", {})

    for key in INFRASTRUCTURE_KEYS:
        assert key in sources, f"Missing source entry: {key}"
        assert "url" in sources[key], f"Source '{key}' missing 'url' field"
        assert sources[key]["url"].startswith(
            "https://www.data.bsee.gov/"
        ), f"Source URL for '{key}' does not point to data.bsee.gov"
        assert (
            "update_frequency" in sources[key]
        ), f"Source '{key}' missing 'update_frequency' field"


def test_validate_config_accepts_infrastructure_flags():
    """Validation passes when only infrastructure flags are enabled."""
    router = ConfigRouter()
    # Set enhanced mode so validation skips legacy-only checks
    router.enhanced_mode = True

    config = {
        "meta": {"mode": "enhanced"},
        "data": {
            "well": False,
            "war": False,
            "production": False,
            "platform": True,
            "pipeline_permit": False,
            "deepwater_structure": False,
            "pipeline_location": False,
        },
    }

    assert (
        router.validate_config(config) is True
    ), "Config with infrastructure flag 'platform' enabled should be valid"


def test_system_info_shows_infrastructure_support():
    """System info includes infrastructure feature flags and data sources."""
    router = ConfigRouter()
    config = {
        "meta": {"mode": "enhanced"},
        "data": {
            "platform": True,
            "pipeline_permit": True,
            "deepwater_structure": True,
            "pipeline_location": True,
        },
    }

    info = router.get_system_info(config)

    # Check feature flags
    features = info.get("features", {})
    assert features.get("platform_data_support") is True
    assert features.get("pipeline_permit_support") is True
    assert features.get("deepwater_structure_support") is True
    assert features.get("pipeline_location_support") is True

    # Check data sources report fresh_download in enhanced mode
    sources = info.get("data_sources", {})
    for key in INFRASTRUCTURE_KEYS:
        assert key in sources, f"Missing data_source entry: {key}"
        assert (
            sources[key] == "fresh_download"
        ), f"Expected 'fresh_download' for '{key}' in enhanced mode, got '{sources[key]}'"
