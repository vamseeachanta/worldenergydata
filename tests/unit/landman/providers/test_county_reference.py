"""Tests for county reference provider."""

import pytest

from worldenergydata.landman.exceptions import (
    CountyNotFoundError,
    StateNotSupportedError,
)
from worldenergydata.landman.providers.county_reference import (
    CountyReferenceProvider,
)


@pytest.fixture
def provider():
    return CountyReferenceProvider()


class TestGetSupportedStates:
    def test_returns_list(self, provider):
        states = provider.get_supported_states()
        assert isinstance(states, list)
        assert "TX" in states
        assert "NM" in states
        assert "OK" in states
        assert "ND" in states

    def test_returns_copy(self, provider):
        s1 = provider.get_supported_states()
        s2 = provider.get_supported_states()
        s1.append("ZZ")
        assert "ZZ" not in s2


class TestGetCountiesForState:
    def test_texas_counties(self, provider):
        counties = provider.get_counties_for_state("TX")
        assert "REEVES" in counties
        assert "MIDLAND" in counties

    def test_case_insensitive(self, provider):
        counties = provider.get_counties_for_state("tx")
        assert len(counties) > 0

    def test_unknown_state(self, provider):
        assert provider.get_counties_for_state("ZZ") == []


class TestGetCountyClerkInfo:
    def test_known_county(self, provider):
        info = provider.get_county_clerk_info("TX", "REEVES")
        assert info.state == "TX"
        assert info.county == "REEVES"
        assert info.online_search_available is True
        assert info.phone is not None

    def test_state_not_supported(self, provider):
        with pytest.raises(StateNotSupportedError):
            provider.get_county_clerk_info("ZZ", "ANYTOWN")

    def test_county_not_found(self, provider):
        with pytest.raises(CountyNotFoundError):
            provider.get_county_clerk_info("TX", "NONEXISTENTCOUNTY")

    def test_strips_county_suffix(self, provider):
        info = provider.get_county_clerk_info("TX", "REEVES COUNTY")
        assert info.county == "REEVES"

    def test_strips_parish_suffix(self, provider):
        info = provider.get_county_clerk_info("LA", "CADDO PARISH")
        assert info.county == "CADDO"

    def test_case_insensitive_county(self, provider):
        info = provider.get_county_clerk_info("TX", "reeves")
        assert info.county == "REEVES"

    def test_offline_county(self, provider):
        info = provider.get_county_clerk_info("TX", "LOVING")
        assert info.online_search_available is False


class TestGetSearchInstructions:
    def test_known_county(self, provider):
        instructions = provider.get_search_instructions("TX", "REEVES")
        assert "REEVES" in instructions
        assert "County Clerk" in instructions

    def test_unknown_returns_general(self, provider):
        instructions = provider.get_search_instructions("ZZ", "UNKNOWN")
        assert "How to Search County Records" in instructions

    def test_online_available_message(self, provider):
        instructions = provider.get_search_instructions("TX", "REEVES")
        assert "AVAILABLE" in instructions

    def test_offline_message(self, provider):
        instructions = provider.get_search_instructions("TX", "LOVING")
        assert "NOT AVAILABLE" in instructions


class TestCheckOnlineAvailability:
    def test_online_county(self, provider):
        assert provider.check_online_availability("TX", "REEVES") is True

    def test_offline_county(self, provider):
        assert provider.check_online_availability("TX", "LOVING") is False

    def test_unknown_county(self, provider):
        assert provider.check_online_availability("ZZ", "NONE") is False


class TestSearchCounties:
    def test_all_counties(self, provider):
        results = provider.search_counties()
        assert len(results) > 0

    def test_filter_by_state(self, provider):
        results = provider.search_counties(state="TX")
        for r in results:
            assert r.state == "TX"

    def test_online_only(self, provider):
        results = provider.search_counties(online_only=True)
        for r in results:
            assert r.online_search_available is True

    def test_state_and_online(self, provider):
        results = provider.search_counties(state="TX", online_only=True)
        for r in results:
            assert r.state == "TX"
            assert r.online_search_available is True

    def test_unknown_state_empty(self, provider):
        results = provider.search_counties(state="ZZ")
        assert results == []


class TestGetNearbyCounties:
    def test_nearby(self, provider):
        nearby = provider.get_nearby_counties("TX", "REEVES")
        assert "REEVES" not in nearby
        assert len(nearby) > 0

    def test_unknown_state(self, provider):
        assert provider.get_nearby_counties("ZZ", "ANY") == []


class TestHealthCheck:
    def test_always_healthy(self, provider):
        assert provider.health_check() is True
