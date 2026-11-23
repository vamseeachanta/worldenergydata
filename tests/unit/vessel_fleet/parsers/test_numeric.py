"""Tests for vessel fleet numeric parsers."""

import pytest

from worldenergydata.vessel_fleet.parsers.numeric import (
    _BOOL_FALSE,
    _BOOL_TRUE,
    _NON_NUMERIC_VALUES,
    _UNIT_SUFFIXES,
    parse_bool,
    parse_dimension_pair,
    parse_int_from_label,
    parse_numeric,
    strip_unit,
)


class TestStripUnit:
    def test_none(self):
        assert strip_unit(None) == ""

    def test_empty(self):
        assert strip_unit("") == ""
        assert strip_unit("  ") == ""

    def test_no_unit(self):
        assert strip_unit("1234") == "1234"

    def test_strip_ft_dot(self):
        assert strip_unit("8000 ft.") == "8000"

    def test_strip_ft(self):
        assert strip_unit("100 ft") == "100"

    def test_strip_metres(self):
        assert strip_unit("50 metres") == "50"

    def test_strip_meters(self):
        assert strip_unit("50 meters") == "50"

    def test_strip_m_dot(self):
        assert strip_unit("50 m.") == "50"

    def test_strip_tonnes(self):
        assert strip_unit("250000 tonnes") == "250000"

    def test_strip_hp(self):
        assert strip_unit("5000 hp") == "5000"

    def test_strip_HP(self):
        assert strip_unit("5000 HP") == "5000"

    def test_strip_psi(self):
        assert strip_unit("3000 psi") == "3000"

    def test_strip_inches(self):
        assert strip_unit("16 inches") == "16"

    def test_strip_knots(self):
        assert strip_unit("12 knots") == "12"

    def test_strip_MW(self):
        assert strip_unit("80 MW") == "80"

    def test_case_insensitive(self):
        assert strip_unit("100 FT.") == "100"
        assert strip_unit("50 Metres") == "50"

    def test_only_first_suffix_stripped(self):
        result = strip_unit("100 ft. ft.")
        assert "ft" not in result.lower() or result == "100 ft."


class TestParseNumeric:
    def test_none(self):
        assert parse_numeric(None) is None

    def test_int_passthrough(self):
        assert parse_numeric(42) == 42.0

    def test_float_passthrough(self):
        assert parse_numeric(3.14) == 3.14

    def test_plain_string(self):
        assert parse_numeric("123") == 123.0

    def test_float_string(self):
        assert parse_numeric("3.14") == 3.14

    def test_with_commas(self):
        assert parse_numeric("8,000") == 8000.0

    def test_with_unit(self):
        assert parse_numeric("8,000 ft.") == 8000.0

    def test_leading_tilde(self):
        assert parse_numeric("~100") == 100.0

    def test_leading_greater(self):
        assert parse_numeric(">50") == 50.0

    def test_leading_less(self):
        assert parse_numeric("<200") == 200.0

    def test_trailing_plus(self):
        assert parse_numeric("300+") == 300.0

    def test_empty_string(self):
        assert parse_numeric("") is None

    def test_whitespace(self):
        assert parse_numeric("  ") is None

    def test_na(self):
        assert parse_numeric("n/a") is None
        assert parse_numeric("N/A") is None

    def test_nil(self):
        assert parse_numeric("nil") is None

    def test_none_string(self):
        assert parse_numeric("none") is None

    def test_dash(self):
        assert parse_numeric("-") is None
        assert parse_numeric("--") is None
        assert parse_numeric("---") is None

    def test_tbd(self):
        assert parse_numeric("tbd") is None

    def test_unknown(self):
        assert parse_numeric("unknown") is None

    def test_varies(self):
        assert parse_numeric("varies") is None

    def test_garbage(self):
        assert parse_numeric("abc") is None

    def test_negative(self):
        assert parse_numeric("-50") == -50.0

    def test_complex_string(self):
        assert parse_numeric("~8,000 ft.") == 8000.0

    def test_leading_whitespace(self):
        assert parse_numeric("  100  ") == 100.0


class TestParseDimensionPair:
    def test_none(self):
        assert parse_dimension_pair(None) is None

    def test_empty(self):
        assert parse_dimension_pair("") is None
        assert parse_dimension_pair("  ") is None

    def test_basic(self):
        result = parse_dimension_pair("20 x 40")
        assert result == (20.0, 40.0)

    def test_with_units(self):
        result = parse_dimension_pair("89.2 ft. x 36.7 ft.")
        assert result is not None
        assert abs(result[0] - 89.2) < 0.01
        assert abs(result[1] - 36.7) < 0.01

    def test_uppercase_x(self):
        result = parse_dimension_pair("10 X 20")
        assert result == (10.0, 20.0)

    def test_multiplication_sign(self):
        result = parse_dimension_pair("10 \u00d7 20")
        assert result == (10.0, 20.0)

    def test_no_separator(self):
        assert parse_dimension_pair("100") is None

    def test_one_side_invalid(self):
        assert parse_dimension_pair("abc x 100") is None
        assert parse_dimension_pair("100 x abc") is None


class TestParseBool:
    def test_none(self):
        assert parse_bool(None) is None

    def test_bool_true(self):
        assert parse_bool(True) is True

    def test_bool_false(self):
        assert parse_bool(False) is False

    def test_int_one(self):
        assert parse_bool(1) is True

    def test_int_zero(self):
        assert parse_bool(0) is False

    def test_float_one(self):
        assert parse_bool(1.0) is True

    def test_float_zero(self):
        assert parse_bool(0.0) is False

    def test_other_number(self):
        assert parse_bool(5) is None
        assert parse_bool(-1) is None

    def test_string_y(self):
        assert parse_bool("y") is True
        assert parse_bool("Y") is True

    def test_string_yes(self):
        assert parse_bool("yes") is True
        assert parse_bool("Yes") is True

    def test_string_true(self):
        assert parse_bool("true") is True
        assert parse_bool("True") is True

    def test_string_1(self):
        assert parse_bool("1") is True

    def test_string_n(self):
        assert parse_bool("n") is False
        assert parse_bool("N") is False

    def test_string_no(self):
        assert parse_bool("no") is False
        assert parse_bool("No") is False

    def test_string_false(self):
        assert parse_bool("false") is False
        assert parse_bool("False") is False

    def test_string_0(self):
        assert parse_bool("0") is False

    def test_empty_string(self):
        assert parse_bool("") is None
        assert parse_bool("  ") is None

    def test_unrecognised(self):
        assert parse_bool("maybe") is None
        assert parse_bool("2") is None


class TestParseIntFromLabel:
    def test_none(self):
        assert parse_int_from_label(None) is None

    def test_empty(self):
        assert parse_int_from_label("") is None
        assert parse_int_from_label("  ") is None

    def test_dp2(self):
        assert parse_int_from_label("DP2") == 2

    def test_dp_space_3(self):
        assert parse_int_from_label("DP 3") == 3

    def test_class_2(self):
        assert parse_int_from_label("Class 2") == 2

    def test_plain_number(self):
        assert parse_int_from_label("3") == 3

    def test_no_digits(self):
        assert parse_int_from_label("abc") is None

    def test_first_match(self):
        assert parse_int_from_label("DP2 Class 3") == 2


class TestConstants:
    def test_non_numeric_values_frozen(self):
        assert isinstance(_NON_NUMERIC_VALUES, frozenset)

    def test_bool_true_frozen(self):
        assert isinstance(_BOOL_TRUE, frozenset)

    def test_bool_false_frozen(self):
        assert isinstance(_BOOL_FALSE, frozenset)

    def test_unit_suffixes_non_empty(self):
        assert len(_UNIT_SUFFIXES) > 10
