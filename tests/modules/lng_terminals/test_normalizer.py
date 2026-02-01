"""Tests for LNG terminal data normalizer."""

import pytest

from worldenergydata.modules.lng_terminals.constants import Region, TerminalStatus
from worldenergydata.modules.lng_terminals.processors.normalizer import (
    COUNTRY_TO_REGION,
    Normalizer,
)


class TestNormalizeCountry:
    """Test country code normalization."""

    def test_already_valid_alpha3(self):
        assert Normalizer.normalize_country("USA") == "USA"
        assert Normalizer.normalize_country("GBR") == "GBR"

    def test_alias_lookup(self):
        assert Normalizer.normalize_country("US") == "USA"
        assert Normalizer.normalize_country("UK") == "GBR"
        assert Normalizer.normalize_country("UAE") == "ARE"

    def test_full_name_lookup(self):
        assert Normalizer.normalize_country("United States") == "USA"
        assert Normalizer.normalize_country("Qatar") == "QAT"
        assert Normalizer.normalize_country("Australia") == "AUS"

    def test_case_insensitive(self):
        assert Normalizer.normalize_country("usa") == "USA"
        assert Normalizer.normalize_country("united kingdom") == "GBR"

    def test_unknown_returns_uppercased(self):
        """Unknown codes should be returned uppercased."""
        assert Normalizer.normalize_country("XYZ") == "XYZ"

    def test_whitespace_handling(self):
        assert Normalizer.normalize_country("  USA  ") == "USA"


class TestNormalizeStatus:
    """Test status normalization."""

    def test_standard_values(self):
        assert Normalizer.normalize_status("operational") == TerminalStatus.OPERATIONAL
        assert (
            Normalizer.normalize_status("under construction")
            == TerminalStatus.UNDER_CONSTRUCTION
        )

    def test_alias_values(self):
        assert Normalizer.normalize_status("operating") == TerminalStatus.OPERATIONAL
        assert (
            Normalizer.normalize_status("construction")
            == TerminalStatus.UNDER_CONSTRUCTION
        )
        assert Normalizer.normalize_status("fid") == TerminalStatus.PLANNED

    def test_case_insensitive(self):
        assert Normalizer.normalize_status("OPERATIONAL") == TerminalStatus.OPERATIONAL
        assert (
            Normalizer.normalize_status("Under Construction")
            == TerminalStatus.UNDER_CONSTRUCTION
        )

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            Normalizer.normalize_status("invalid_status_xyz")


class TestGetRegion:
    """Test region lookup."""

    def test_known_countries(self):
        assert Normalizer.get_region("USA") == Region.NORTH_AMERICA
        assert Normalizer.get_region("QAT") == Region.MIDDLE_EAST
        assert Normalizer.get_region("JPN") == Region.ASIA_PACIFIC
        assert Normalizer.get_region("AUS") == Region.OCEANIA
        assert Normalizer.get_region("NGA") == Region.AFRICA
        assert Normalizer.get_region("GBR") == Region.EUROPE

    def test_unknown_country_returns_none(self):
        assert Normalizer.get_region("XYZ") is None


class TestUnitConversions:
    """Test unit conversion helpers."""

    def test_bcfd_to_mtpa(self):
        result = Normalizer.bcfd_to_mtpa(1.0)
        assert 7.0 < result < 8.0  # approximately 7.6

    def test_bcm_to_mtpa(self):
        result = Normalizer.bcm_to_mtpa(1.0)
        assert 0.7 < result < 0.8  # approximately 0.735

    def test_zero_conversion(self):
        assert Normalizer.bcfd_to_mtpa(0.0) == 0.0
        assert Normalizer.bcm_to_mtpa(0.0) == 0.0


class TestNormalizerIntegration:
    """Integration tests for the Normalizer class."""

    def test_normalize_terminals_from_seed(self):
        """Normalizer should process seed collector output without errors."""
        from worldenergydata.modules.lng_terminals.collectors.seed_collector import (
            SeedCollector,
        )

        collector = SeedCollector()
        terminals = collector.collect()

        normalizer = Normalizer()
        normalized = normalizer.normalize_terminals(terminals)

        assert len(normalized) == len(terminals)
        # All should have regions assigned after normalization
        for t in normalized:
            if t.country in COUNTRY_TO_REGION:
                assert (
                    t.region is not None
                ), f"Missing region for {t.terminal_name} ({t.country})"
