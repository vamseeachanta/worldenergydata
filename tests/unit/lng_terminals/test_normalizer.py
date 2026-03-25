"""Tests for LNG terminals normalizer module."""

import pytest

from worldenergydata.lng_terminals.constants import Region, TerminalStatus, TerminalType
from worldenergydata.lng_terminals.processors.normalizer import (
    BCM_TO_MTPA,
    BCFD_TO_MTPA,
    COUNTRY_ALIASES,
    COUNTRY_TO_REGION,
    STATUS_ALIASES,
    TYPE_ALIASES,
    Normalizer,
    _clean_text,
    _normalize_unicode,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_bcfd_to_mtpa(self):
        assert BCFD_TO_MTPA == 7.6

    def test_bcm_to_mtpa(self):
        assert BCM_TO_MTPA == 0.735

    def test_country_aliases_us(self):
        assert COUNTRY_ALIASES["US"] == "USA"
        assert COUNTRY_ALIASES["UNITED STATES"] == "USA"

    def test_country_aliases_uk(self):
        assert COUNTRY_ALIASES["UK"] == "GBR"
        assert COUNTRY_ALIASES["GB"] == "GBR"

    def test_status_aliases_operational(self):
        assert STATUS_ALIASES["operating"] == TerminalStatus.OPERATIONAL
        assert STATUS_ALIASES["active"] == TerminalStatus.OPERATIONAL

    def test_status_aliases_construction(self):
        assert STATUS_ALIASES["under construction"] == TerminalStatus.UNDER_CONSTRUCTION

    def test_type_aliases_fsru(self):
        assert TYPE_ALIASES["fsru"] == TerminalType.FSRU

    def test_type_aliases_flng(self):
        assert TYPE_ALIASES["flng"] == TerminalType.FLNG

    def test_country_to_region_usa(self):
        assert COUNTRY_TO_REGION["USA"] == Region.NORTH_AMERICA

    def test_country_to_region_qatar(self):
        assert COUNTRY_TO_REGION["QAT"] == Region.MIDDLE_EAST

    def test_country_to_region_japan(self):
        assert COUNTRY_TO_REGION["JPN"] == Region.ASIA_PACIFIC

    def test_country_to_region_australia(self):
        assert COUNTRY_TO_REGION["AUS"] == Region.OCEANIA


# ---------------------------------------------------------------------------
# Normalizer - normalize_country
# ---------------------------------------------------------------------------

class TestNormalizeCountry:
    def test_alias(self):
        n = Normalizer()
        assert n.normalize_country("US") == "USA"
        assert n.normalize_country("UK") == "GBR"

    def test_full_name(self):
        n = Normalizer()
        assert n.normalize_country("UNITED STATES") == "USA"
        assert n.normalize_country("QATAR") == "QAT"

    def test_already_iso3(self):
        n = Normalizer()
        assert n.normalize_country("NOR") == "NOR"
        assert n.normalize_country("BRA") == "BRA"

    def test_case_insensitive(self):
        n = Normalizer()
        assert n.normalize_country("us") == "USA"
        assert n.normalize_country("Qatar") == "QAT"

    def test_unknown_raises(self):
        n = Normalizer()
        with pytest.raises(ValueError, match="Cannot resolve"):
            n.normalize_country("XX")


# ---------------------------------------------------------------------------
# Normalizer - normalize_status
# ---------------------------------------------------------------------------

class TestNormalizeStatus:
    def test_operating(self):
        n = Normalizer()
        assert n.normalize_status("operating") == TerminalStatus.OPERATIONAL

    def test_under_construction(self):
        n = Normalizer()
        assert n.normalize_status("under construction") == TerminalStatus.UNDER_CONSTRUCTION

    def test_planned(self):
        n = Normalizer()
        assert n.normalize_status("planned") == TerminalStatus.PLANNED

    def test_mothballed(self):
        n = Normalizer()
        assert n.normalize_status("mothballed") == TerminalStatus.MOTHBALLED

    def test_unknown_raises(self):
        n = Normalizer()
        with pytest.raises(ValueError, match="Unknown terminal status"):
            n.normalize_status("nonexistent_status")


# ---------------------------------------------------------------------------
# Normalizer - normalize_type
# ---------------------------------------------------------------------------

class TestNormalizeType:
    def test_fsru(self):
        n = Normalizer()
        assert n.normalize_type("fsru") == TerminalType.FSRU

    def test_flng(self):
        n = Normalizer()
        assert n.normalize_type("flng") == TerminalType.FLNG

    def test_import(self):
        n = Normalizer()
        assert n.normalize_type("import") == TerminalType.ONSHORE_IMPORT

    def test_liquefaction(self):
        n = Normalizer()
        assert n.normalize_type("liquefaction") == TerminalType.ONSHORE_LIQUEFACTION

    def test_unknown_raises(self):
        n = Normalizer()
        with pytest.raises(ValueError, match="Unknown terminal type"):
            n.normalize_type("nonexistent_type")


# ---------------------------------------------------------------------------
# Normalizer - get_region
# ---------------------------------------------------------------------------

class TestGetRegion:
    def test_usa(self):
        n = Normalizer()
        assert n.get_region("USA") == Region.NORTH_AMERICA

    def test_unknown(self):
        n = Normalizer()
        assert n.get_region("XYZ") is None

    def test_case_insensitive(self):
        n = Normalizer()
        assert n.get_region("usa") == Region.NORTH_AMERICA


# ---------------------------------------------------------------------------
# Normalizer - unit conversion
# ---------------------------------------------------------------------------

class TestUnitConversion:
    def test_bcfd_to_mtpa(self):
        n = Normalizer()
        assert n.bcfd_to_mtpa(1.0) == pytest.approx(7.6)
        assert n.bcfd_to_mtpa(0.0) == 0.0

    def test_bcm_to_mtpa(self):
        n = Normalizer()
        assert n.bcm_to_mtpa(1.0) == pytest.approx(0.735)
        assert n.bcm_to_mtpa(10.0) == pytest.approx(7.35)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

class TestPrivateHelpers:
    def test_normalize_unicode(self):
        assert _normalize_unicode("hello") == "hello"

    def test_clean_text(self):
        assert _clean_text("  hello   world  ") == "hello world"

    def test_clean_text_unicode(self):
        result = _clean_text("  Réseau  Terminal  ")
        assert "  " not in result
