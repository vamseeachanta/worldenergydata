"""Tests for the numeric parser."""

from __future__ import annotations

import pytest

from worldenergydata.vessel_fleet.parsers.numeric import (
    parse_numeric,
    parse_dimension_pair,
    parse_bool,
    strip_unit,
    parse_int_from_label,
)


class TestParseNumeric:
    """parse_numeric: extract a single float from messy strings."""

    def test_plain_integer(self):
        assert parse_numeric("8000") == 8000.0

    def test_plain_float(self):
        assert parse_numeric("8000.5") == 8000.5

    def test_comma_separated(self):
        assert parse_numeric("8,000") == 8000.0

    def test_comma_separated_with_unit(self):
        assert parse_numeric("8,000 ft.") == 8000.0

    def test_comma_separated_large(self):
        assert parse_numeric("1,250,000") == 1250000.0

    def test_unit_suffix_ft(self):
        assert parse_numeric("350 ft") == 350.0

    def test_unit_suffix_metres(self):
        assert parse_numeric("107.5 m") == 107.5

    def test_unit_suffix_tonnes(self):
        assert parse_numeric("14,200 tonnes") == 14200.0

    def test_unit_suffix_kips(self):
        assert parse_numeric("2,000 kips") == 2000.0

    def test_unit_suffix_hp(self):
        assert parse_numeric("7,500 HP") == 7500.0

    def test_unit_suffix_psi(self):
        assert parse_numeric("15,000 PSI") == 15000.0

    def test_leading_trailing_whitespace(self):
        assert parse_numeric("  8000  ") == 8000.0

    def test_none_returns_none(self):
        assert parse_numeric(None) is None

    def test_empty_string_returns_none(self):
        assert parse_numeric("") is None

    def test_whitespace_only_returns_none(self):
        assert parse_numeric("   ") is None

    def test_non_numeric_returns_none(self):
        assert parse_numeric("N/A") is None

    def test_dash_returns_none(self):
        assert parse_numeric("-") is None

    def test_tbd_returns_none(self):
        assert parse_numeric("TBD") is None

    def test_negative_number(self):
        assert parse_numeric("-500") == -500.0

    def test_float_passthrough(self):
        assert parse_numeric(8000.0) == 8000.0

    def test_int_passthrough(self):
        assert parse_numeric(8000) == 8000.0

    def test_plus_sign(self):
        assert parse_numeric("200+") == 200.0

    def test_approx_tilde(self):
        assert parse_numeric("~350") == 350.0

    def test_greater_than(self):
        assert parse_numeric(">10,000") == 10000.0


class TestParseDimensionPair:
    """parse_dimension_pair: extract two numbers from 'L x W' strings."""

    def test_simple_pair(self):
        assert parse_dimension_pair("20 x 40") == (20.0, 40.0)

    def test_pair_with_decimals(self):
        assert parse_dimension_pair("89.2 ft. x 36.7 ft.") == (89.2, 36.7)

    def test_pair_with_commas(self):
        assert parse_dimension_pair("1,200 x 800") == (1200.0, 800.0)

    def test_pair_by_separator(self):
        assert parse_dimension_pair("20 X 40") == (20.0, 40.0)

    def test_pair_by_times(self):
        assert parse_dimension_pair("20x40") == (20.0, 40.0)

    def test_none_returns_none(self):
        assert parse_dimension_pair(None) is None

    def test_empty_string_returns_none(self):
        assert parse_dimension_pair("") is None

    def test_single_number_returns_none(self):
        assert parse_dimension_pair("8000") is None

    def test_three_numbers_returns_first_two(self):
        result = parse_dimension_pair("20 x 40 x 60")
        assert result == (20.0, 40.0)


class TestParseBool:
    """parse_bool: coerce Y/Yes/1/True to True, N/No/0/False to False."""

    def test_yes(self):
        assert parse_bool("Yes") is True

    def test_y(self):
        assert parse_bool("Y") is True

    def test_no(self):
        assert parse_bool("No") is False

    def test_n(self):
        assert parse_bool("N") is False

    def test_one(self):
        assert parse_bool("1") is True

    def test_zero(self):
        assert parse_bool("0") is False

    def test_one_float(self):
        assert parse_bool(1.0) is True

    def test_zero_float(self):
        assert parse_bool(0.0) is False

    def test_true_bool(self):
        assert parse_bool(True) is True

    def test_false_bool(self):
        assert parse_bool(False) is False

    def test_true_string(self):
        assert parse_bool("True") is True

    def test_false_string(self):
        assert parse_bool("False") is False

    def test_none_returns_none(self):
        assert parse_bool(None) is None

    def test_empty_returns_none(self):
        assert parse_bool("") is None

    def test_unknown_returns_none(self):
        assert parse_bool("maybe") is None


class TestStripUnit:
    """strip_unit: remove known unit suffixes."""

    def test_strip_ft(self):
        assert strip_unit("8,000 ft.") == "8,000"

    def test_strip_metres(self):
        assert strip_unit("350 m") == "350"

    def test_strip_tonnes(self):
        assert strip_unit("14200 tonnes") == "14200"

    def test_no_unit(self):
        assert strip_unit("8000") == "8000"

    def test_none_returns_empty(self):
        assert strip_unit(None) == ""


class TestParseIntFromLabel:
    """parse_int_from_label: extract int from labels like 'DP2', 'Class 3'."""

    def test_dp2(self):
        assert parse_int_from_label("DP2") == 2

    def test_dp_3(self):
        assert parse_int_from_label("DP 3") == 3

    def test_class_2(self):
        assert parse_int_from_label("Class 2") == 2

    def test_just_number(self):
        assert parse_int_from_label("3") == 3

    def test_none_returns_none(self):
        assert parse_int_from_label(None) is None

    def test_no_number_returns_none(self):
        assert parse_int_from_label("None") is None
