"""Tests for IMO flag state normalizers."""

from worldenergydata.marine_safety.importers.imo_normalizers import (
    FLAG_STATE_MAPPINGS,
    get_flag_state_name,
    is_flag_of_convenience,
    normalize_flag_state,
)


class TestNormalizeFlagState:
    def test_full_name_panama(self):
        assert normalize_flag_state("Panama") == "PA"

    def test_full_name_liberia(self):
        assert normalize_flag_state("Liberia") == "LR"

    def test_three_letter_code(self):
        assert normalize_flag_state("NOR") == "NO"

    def test_case_insensitive(self):
        assert normalize_flag_state("NORWAY") == "NO"
        assert normalize_flag_state("norway") == "NO"

    def test_two_letter_code_passthrough(self):
        assert normalize_flag_state("XY") == "XY"

    def test_none_returns_none(self):
        assert normalize_flag_state(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_flag_state("") is None

    def test_whitespace_stripped(self):
        assert normalize_flag_state("  panama  ") == "PA"

    def test_united_states(self):
        assert normalize_flag_state("United States") == "US"
        assert normalize_flag_state("USA") == "US"

    def test_united_kingdom(self):
        assert normalize_flag_state("United Kingdom") == "GB"
        assert normalize_flag_state("UK") == "GB"

    def test_hong_kong_china(self):
        assert normalize_flag_state("Hong Kong, China") == "HK"

    def test_marshall_islands(self):
        assert normalize_flag_state("Marshall Islands") == "MH"

    def test_unknown_long_string(self):
        # Unknown flag with more than 2 chars returns first 2 uppercase
        result = normalize_flag_state("Atlantis")
        assert isinstance(result, str)


class TestGetFlagStateName:
    def test_known_code(self):
        name = get_flag_state_name("NO")
        assert name is not None
        assert "norway" in name.lower()

    def test_usa(self):
        name = get_flag_state_name("US")
        assert name is not None
        assert "united" in name.lower()

    def test_unknown_code(self):
        assert get_flag_state_name("ZZ") is None

    def test_none_returns_none(self):
        assert get_flag_state_name(None) is None

    def test_empty_returns_none(self):
        assert get_flag_state_name("") is None

    def test_case_insensitive(self):
        name = get_flag_state_name("pa")
        assert name is not None


class TestIsFlagOfConvenience:
    def test_panama_is_foc(self):
        assert is_flag_of_convenience("PA") is True

    def test_liberia_is_foc(self):
        assert is_flag_of_convenience("LR") is True

    def test_marshall_islands_is_foc(self):
        assert is_flag_of_convenience("MH") is True

    def test_malta_is_foc(self):
        assert is_flag_of_convenience("MT") is True

    def test_norway_is_not_foc(self):
        assert is_flag_of_convenience("NO") is False

    def test_usa_is_not_foc(self):
        assert is_flag_of_convenience("US") is False

    def test_case_insensitive(self):
        assert is_flag_of_convenience("pa") is True

    def test_none_returns_false(self):
        assert is_flag_of_convenience(None) is False

    def test_empty_returns_false(self):
        assert is_flag_of_convenience("") is False


class TestFlagStateMappings:
    def test_has_major_states(self):
        assert "panama" in FLAG_STATE_MAPPINGS
        assert "norway" in FLAG_STATE_MAPPINGS
        assert "united states" in FLAG_STATE_MAPPINGS

    def test_all_values_are_two_letter(self):
        for name, code in FLAG_STATE_MAPPINGS.items():
            assert len(code) == 2, f"Bad code for {name}: {code}"

    def test_all_values_uppercase(self):
        for name, code in FLAG_STATE_MAPPINGS.items():
            assert code == code.upper(), f"Not uppercase for {name}: {code}"
