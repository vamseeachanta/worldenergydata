"""Tests for vessel fleet name normalizer."""

from worldenergydata.vessel_fleet.dedup.normalizer import (
    _PREFIXES,
    _SUFFIXES,
    names_match,
    normalize_vessel_name,
)


class TestNormalizeVesselName:
    def test_none(self):
        assert normalize_vessel_name(None) == ""

    def test_empty(self):
        assert normalize_vessel_name("") == ""
        assert normalize_vessel_name("  ") == ""

    def test_basic(self):
        assert normalize_vessel_name("Sleipnir") == "SLEIPNIR"

    def test_strips_mv_prefix(self):
        assert normalize_vessel_name("MV Sleipnir") == "SLEIPNIR"

    def test_strips_m_slash_v_prefix(self):
        assert normalize_vessel_name("M/V Blue Marlin") == "BLUE MARLIN"

    def test_strips_ss_prefix(self):
        assert normalize_vessel_name("SS Enterprise") == "ENTERPRISE"

    def test_strips_sv_prefix(self):
        assert normalize_vessel_name("SV Test Vessel") == "TEST VESSEL"

    def test_strips_s_slash_v_prefix(self):
        assert normalize_vessel_name("S/V Test Vessel") == "TEST VESSEL"

    def test_strips_mt_prefix(self):
        assert normalize_vessel_name("MT Tanker One") == "TANKER ONE"

    def test_strips_fpso_prefix(self):
        assert normalize_vessel_name("FPSO Cidade") == "CIDADE"

    def test_strips_fso_prefix(self):
        assert normalize_vessel_name("FSO Yetagun") == "YETAGUN"

    def test_strips_ahts_prefix(self):
        assert normalize_vessel_name("AHTS Navigator") == "NAVIGATOR"

    def test_removes_non_alnum(self):
        result = normalize_vessel_name("Vessel-Name.2")
        assert result == "VESSEL NAME 2"

    def test_collapses_whitespace(self):
        result = normalize_vessel_name("Big    Ship")
        assert result == "BIG SHIP"

    def test_strips_leading_trailing(self):
        result = normalize_vessel_name("  Sleipnir  ")
        assert result == "SLEIPNIR"

    def test_only_first_prefix_stripped(self):
        result = normalize_vessel_name("MV FPSO Cidade")
        assert "FPSO" in result


class TestNamesMatch:
    def test_same_name(self):
        assert names_match("Sleipnir", "Sleipnir") is True

    def test_case_insensitive(self):
        assert names_match("SLEIPNIR", "sleipnir") is True

    def test_prefix_ignored(self):
        assert names_match("MV Sleipnir", "Sleipnir") is True

    def test_different_names(self):
        assert names_match("Sleipnir", "Thialf") is False

    def test_none_a(self):
        assert names_match(None, "Sleipnir") is False

    def test_none_b(self):
        assert names_match("Sleipnir", None) is False

    def test_both_none(self):
        assert names_match(None, None) is False

    def test_both_empty(self):
        assert names_match("", "") is False

    def test_special_chars_ignored(self):
        assert names_match("Vessel-1", "Vessel 1") is True


class TestConstants:
    def test_prefixes_non_empty(self):
        assert len(_PREFIXES) > 5

    def test_suffixes_non_empty(self):
        assert len(_SUFFIXES) > 0

    def test_prefixes_have_trailing_space(self):
        for p in _PREFIXES:
            assert p.endswith(" "), f"Prefix '{p}' should end with a space"
