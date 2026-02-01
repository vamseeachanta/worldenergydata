"""
Tests for BSEE Web Scraper infrastructure data types (Phase 2).

Validates that the 4 new infrastructure data types (platform,
pipeline_permit, deepwater_structure, pipeline_location) are
properly registered in the BSEEWebScraper class.
"""

import re

from worldenergydata.modules.bsee.data.scrapers.bsee_web import BSEEWebScraper

INFRASTRUCTURE_KEYS = [
    "platform",
    "pipeline_permit",
    "deepwater_structure",
    "pipeline_location",
]


def test_urls_contain_infrastructure_keys():
    """All 4 new infrastructure keys exist in the URLS dict."""
    for key in INFRASTRUCTURE_KEYS:
        assert key in BSEEWebScraper.URLS, f"Missing URL key: {key}"


def test_url_patterns_correct():
    """URLs follow the expected data.bsee.gov pattern."""
    pattern = re.compile(
        r"^https://www\.data\.bsee\.gov/(Platform|Pipeline)/Files/\w+RawData\.zip$"
    )
    for key in INFRASTRUCTURE_KEYS:
        url = BSEEWebScraper.URLS[key]
        assert pattern.match(
            url
        ), f"URL for '{key}' does not match expected BSEE pattern: {url}"


def test_timeout_values_set():
    """All 4 new infrastructure keys have timeout values in TIMEOUTS."""
    for key in INFRASTRUCTURE_KEYS:
        assert key in BSEEWebScraper.TIMEOUTS, f"Missing timeout for: {key}"
        assert isinstance(
            BSEEWebScraper.TIMEOUTS[key], (int, float)
        ), f"Timeout for '{key}' is not numeric"
        assert BSEEWebScraper.TIMEOUTS[key] > 0, f"Timeout for '{key}' must be positive"


def test_download_methods_exist():
    """All 4 convenience download methods exist on BSEEWebScraper."""
    scraper = BSEEWebScraper()
    expected_methods = [
        "download_platform_data",
        "download_pipeline_permit_data",
        "download_deepwater_structure_data",
        "download_pipeline_location_data",
    ]
    for method_name in expected_methods:
        assert hasattr(scraper, method_name), f"Missing method: {method_name}"
        assert callable(getattr(scraper, method_name)), f"{method_name} is not callable"
    scraper.close()
