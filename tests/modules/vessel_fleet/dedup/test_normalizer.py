"""Tests for vessel name normalization."""

from worldenergydata.vessel_fleet.dedup.normalizer import (
    normalize_vessel_name,
    names_match,
)


class TestNormalizeVesselName:
    def test_simple_name(self):
        assert normalize_vessel_name("DEEPWATER TITAN") == "DEEPWATER TITAN"

    def test_strips_mv_prefix(self):
        assert normalize_vessel_name("M/V SLEIPNIR") == "SLEIPNIR"

    def test_strips_ss_prefix(self):
        assert normalize_vessel_name("SS BALDER") == "BALDER"

    def test_uppercase(self):
        assert normalize_vessel_name("deepwater titan") == "DEEPWATER TITAN"

    def test_strips_whitespace(self):
        assert normalize_vessel_name("  DEEPWATER TITAN  ") == "DEEPWATER TITAN"

    def test_removes_special_chars(self):
        assert normalize_vessel_name("T.O. DEEPWATER TITAN") == "DEEPWATER TITAN"

    def test_none_returns_empty(self):
        assert normalize_vessel_name(None) == ""

    def test_empty_returns_empty(self):
        assert normalize_vessel_name("") == ""


class TestNamesMatch:
    def test_exact_match(self):
        assert names_match("DEEPWATER TITAN", "DEEPWATER TITAN")

    def test_case_insensitive(self):
        assert names_match("deepwater titan", "DEEPWATER TITAN")

    def test_prefix_stripped(self):
        assert names_match("M/V SLEIPNIR", "SLEIPNIR")

    def test_no_match(self):
        assert not names_match("DEEPWATER TITAN", "SLEIPNIR")

    def test_none_no_match(self):
        assert not names_match(None, "SLEIPNIR")
