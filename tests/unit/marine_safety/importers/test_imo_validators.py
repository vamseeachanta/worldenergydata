"""Tests for IMO number validation utilities."""

from worldenergydata.marine_safety.importers.imo_validators import (
    extract_imo_number,
    format_imo_number,
    validate_imo,
    validate_imo_number,
)


class TestValidateImoNumber:
    def test_empty(self):
        valid, cleaned = validate_imo_number("")
        assert valid is False
        assert cleaned is None

    def test_none(self):
        valid, cleaned = validate_imo_number(None)
        assert valid is False
        assert cleaned is None

    def test_valid_checksum(self):
        # 9074729: 9*7+0*6+7*5+4*4+7*3+2*2 = 63+0+35+16+21+4=139, 139%10=9
        valid, cleaned = validate_imo_number("9074729")
        assert valid is True
        assert cleaned == "9074729"

    def test_valid_with_prefix(self):
        valid, cleaned = validate_imo_number("IMO 9074729")
        assert valid is True
        assert cleaned == "9074729"

    def test_valid_with_prefix_no_space(self):
        valid, cleaned = validate_imo_number("IMO9074729")
        assert valid is True
        assert cleaned == "9074729"

    def test_valid_lowercase_prefix(self):
        valid, cleaned = validate_imo_number("imo 9074729")
        assert valid is True
        assert cleaned == "9074729"

    def test_invalid_checksum(self):
        # 9074720: checksum should be 9, but last digit is 0
        valid, cleaned = validate_imo_number("9074720")
        assert valid is False
        assert cleaned == "9074720"  # cleaned but invalid

    def test_too_short(self):
        valid, cleaned = validate_imo_number("12345")
        assert valid is False
        assert cleaned is None

    def test_too_long(self):
        valid, cleaned = validate_imo_number("123456789")
        assert valid is False
        assert cleaned is None

    def test_non_numeric(self):
        valid, cleaned = validate_imo_number("ABCDEFG")
        assert valid is False
        assert cleaned is None

    def test_with_dashes(self):
        # Dashes should be stripped
        valid, cleaned = validate_imo_number("907-4729")
        assert valid is True
        assert cleaned == "9074729"

    def test_with_whitespace(self):
        valid, cleaned = validate_imo_number("  9074729  ")
        assert valid is True
        assert cleaned == "9074729"


class TestValidateImo:
    def test_valid(self):
        assert validate_imo("9074729") is True

    def test_invalid(self):
        assert validate_imo("") is False

    def test_invalid_checksum(self):
        assert validate_imo("9074720") is False


class TestExtractImoNumber:
    def test_empty(self):
        assert extract_imo_number("") is None

    def test_none(self):
        assert extract_imo_number(None) is None

    def test_with_imo_prefix(self):
        result = extract_imo_number("The vessel IMO 9074729 was involved")
        assert result == "9074729"

    def test_without_prefix(self):
        result = extract_imo_number("Vessel number 9074729 reported")
        assert result == "9074729"

    def test_no_valid_imo(self):
        result = extract_imo_number("No IMO number here")
        assert result is None

    def test_invalid_checksum_skipped(self):
        # 1234560 has wrong checksum, should not be extracted
        result = extract_imo_number("Number 1234560 is invalid")
        assert result is None


class TestFormatImoNumber:
    def test_with_prefix(self):
        result = format_imo_number("9074729", include_prefix=True)
        assert result == "IMO 9074729"

    def test_without_prefix(self):
        result = format_imo_number("9074729", include_prefix=False)
        assert result == "9074729"

    def test_invalid_returns_none(self):
        result = format_imo_number("")
        assert result is None

    def test_too_short_returns_none(self):
        result = format_imo_number("123")
        assert result is None

    def test_cleans_input(self):
        result = format_imo_number("IMO 9074729")
        assert result == "IMO 9074729"

    def test_invalid_checksum_still_returns(self):
        # format_imo_number returns None only if cleaned is None
        result = format_imo_number("9074720")
        # cleaned is "9074720" (not None), so it returns formatted
        assert result is not None
