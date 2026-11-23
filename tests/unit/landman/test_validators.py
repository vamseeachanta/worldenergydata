"""Tests for landman module data validators."""

from worldenergydata.landman.validators import (
    MAJOR_OG_STATES,
    US_STATE_CODES,
    LandmanDataValidator,
    is_major_og_state,
    is_valid_legal_description,
    is_valid_mineral_interest,
    is_valid_state_code,
)


class TestValidateLegalDescription:
    """Tests for LandmanDataValidator.validate_legal_description."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_empty_string(self):
        valid, err = self.v.validate_legal_description("")
        assert valid is False
        assert "empty" in err.lower()

    def test_none_input(self):
        valid, err = self.v.validate_legal_description(None)
        assert valid is False

    def test_too_short(self):
        valid, err = self.v.validate_legal_description("AB")
        assert valid is False
        assert "short" in err.lower()

    def test_too_long(self):
        valid, err = self.v.validate_legal_description("x" * 1001)
        assert valid is False
        assert "maximum" in err.lower()

    def test_section_township_range_pattern(self):
        valid, err = self.v.validate_legal_description("Section 12, Block 42, T-1-S")
        assert valid is True
        assert err is None

    def test_sec_abbreviation(self):
        valid, err = self.v.validate_legal_description("Sec. 12, Blk. 42, T1S")
        assert valid is True

    def test_plss_quarter_section(self):
        valid, err = self.v.validate_legal_description(
            "NW/4 of Section 12, Township 1 South, Range 2 East"
        )
        assert valid is True

    def test_lot_block_pattern(self):
        valid, err = self.v.validate_legal_description("Lot 5, Block 3, Cedar Addition")
        assert valid is True

    def test_metes_and_bounds(self):
        valid, err = self.v.validate_legal_description(
            "Survey No. 123, Abstract 456, State of Texas"
        )
        assert valid is True

    def test_beginning_at_pattern(self):
        valid, err = self.v.validate_legal_description(
            "Beginning at the NE corner, thence South 100 ft"
        )
        assert valid is True

    def test_unrecognized_format(self):
        valid, err = self.v.validate_legal_description(
            "Some random text without legal terms"
        )
        assert valid is False
        assert "recognized format" in err.lower()

    def test_subdivision_pattern(self):
        valid, err = self.v.validate_legal_description(
            "Unit 5, Highland Subdivision, Reeves County"
        )
        assert valid is True


class TestValidateOwnerName:
    """Tests for LandmanDataValidator.validate_owner_name."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_empty_name(self):
        valid, err = self.v.validate_owner_name("")
        assert valid is False

    def test_none_name(self):
        valid, err = self.v.validate_owner_name(None)
        assert valid is False

    def test_too_short(self):
        valid, err = self.v.validate_owner_name("A")
        assert valid is False
        assert "short" in err.lower()

    def test_too_long(self):
        valid, err = self.v.validate_owner_name("A" * 201)
        assert valid is False

    def test_only_numbers(self):
        valid, err = self.v.validate_owner_name("12345")
        assert valid is False
        assert "numbers" in err.lower()

    def test_insufficient_alpha(self):
        valid, err = self.v.validate_owner_name("1A")
        assert valid is False
        assert "alphabetic" in err.lower()

    def test_valid_name(self):
        valid, err = self.v.validate_owner_name("John Doe")
        assert valid is True
        assert err is None

    def test_corporate_name(self):
        valid, err = self.v.validate_owner_name("Exxon Mobil Corp.")
        assert valid is True


class TestValidateStateCode:
    """Tests for LandmanDataValidator.validate_state_code."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_empty_code(self):
        valid, err = self.v.validate_state_code("")
        assert valid is False

    def test_none_code(self):
        valid, err = self.v.validate_state_code(None)
        assert valid is False

    def test_wrong_length(self):
        valid, err = self.v.validate_state_code("TEX")
        assert valid is False
        assert "2 letters" in err

    def test_invalid_code(self):
        valid, err = self.v.validate_state_code("ZZ")
        assert valid is False
        assert "Invalid state code" in err

    def test_valid_texas(self):
        valid, err = self.v.validate_state_code("TX")
        assert valid is True

    def test_lowercase_accepted(self):
        valid, err = self.v.validate_state_code("tx")
        assert valid is True

    def test_valid_oklahoma(self):
        valid, err = self.v.validate_state_code("OK")
        assert valid is True


class TestValidateCountyName:
    """Tests for LandmanDataValidator.validate_county_name."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_empty_county(self):
        valid, err = self.v.validate_county_name("")
        assert valid is False

    def test_too_short(self):
        valid, err = self.v.validate_county_name("A")
        assert valid is False

    def test_too_long(self):
        valid, err = self.v.validate_county_name("X" * 101)
        assert valid is False

    def test_no_alpha(self):
        valid, err = self.v.validate_county_name("123")
        assert valid is False

    def test_valid_county(self):
        valid, err = self.v.validate_county_name("Reeves")
        assert valid is True

    def test_valid_with_state(self):
        valid, err = self.v.validate_county_name("Reeves", "TX")
        assert valid is True


class TestValidateMineralInterest:
    """Tests for LandmanDataValidator.validate_mineral_interest."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_none_value(self):
        valid, err = self.v.validate_mineral_interest(None)
        assert valid is False

    def test_negative(self):
        valid, err = self.v.validate_mineral_interest(-1.0)
        assert valid is False
        assert "negative" in err.lower()

    def test_over_100(self):
        valid, err = self.v.validate_mineral_interest(101.0)
        assert valid is False
        assert "exceed" in err.lower()

    def test_zero(self):
        valid, err = self.v.validate_mineral_interest(0.0)
        assert valid is True

    def test_100(self):
        valid, err = self.v.validate_mineral_interest(100.0)
        assert valid is True

    def test_valid_fraction(self):
        valid, err = self.v.validate_mineral_interest(12.5)
        assert valid is True

    def test_string_number(self):
        valid, err = self.v.validate_mineral_interest("25.0")
        assert valid is True

    def test_invalid_string(self):
        valid, err = self.v.validate_mineral_interest("abc")
        assert valid is False


class TestValidateRoyaltyRate:
    """Tests for LandmanDataValidator.validate_royalty_rate."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_none_value(self):
        valid, err = self.v.validate_royalty_rate(None)
        assert valid is False

    def test_decimal_format(self):
        valid, err = self.v.validate_royalty_rate(0.125)
        assert valid is True

    def test_percentage_format(self):
        valid, err = self.v.validate_royalty_rate(12.5)
        assert valid is True

    def test_negative(self):
        valid, err = self.v.validate_royalty_rate(-0.1)
        assert valid is False

    def test_too_high_decimal(self):
        valid, err = self.v.validate_royalty_rate(0.60)
        assert valid is False
        assert "high" in err.lower()

    def test_too_high_percentage(self):
        valid, err = self.v.validate_royalty_rate(55.0)
        assert valid is False

    def test_invalid_string(self):
        valid, err = self.v.validate_royalty_rate("abc")
        assert valid is False


class TestValidateDocumentNumber:
    """Tests for LandmanDataValidator.validate_document_number."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_empty(self):
        valid, err = self.v.validate_document_number("")
        assert valid is False

    def test_none(self):
        valid, err = self.v.validate_document_number(None)
        assert valid is False

    def test_too_long(self):
        valid, err = self.v.validate_document_number("X" * 51)
        assert valid is False

    def test_valid(self):
        valid, err = self.v.validate_document_number("D-12345")
        assert valid is True


class TestValidateDateRange:
    """Tests for LandmanDataValidator.validate_date_range."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_none_is_optional(self):
        valid, err = self.v.validate_date_range(None)
        assert valid is True

    def test_empty_is_optional(self):
        valid, err = self.v.validate_date_range("")
        assert valid is True

    def test_iso_format(self):
        valid, err = self.v.validate_date_range("2020-01-15")
        assert valid is True

    def test_us_format(self):
        valid, err = self.v.validate_date_range("01/15/2020")
        assert valid is True

    def test_compact_format(self):
        valid, err = self.v.validate_date_range("20200115")
        assert valid is True

    def test_unparseable(self):
        valid, err = self.v.validate_date_range("not-a-date")
        assert valid is False
        assert "parse" in err.lower()

    def test_year_too_old(self):
        valid, err = self.v.validate_date_range("1700-01-01")
        assert valid is False
        assert "outside valid range" in err

    def test_custom_max_year(self):
        valid, err = self.v.validate_date_range("2030-01-01", max_year=2025)
        assert valid is False


class TestValidateLeaseTerm:
    """Tests for LandmanDataValidator.validate_lease_term."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_none_is_optional(self):
        valid, err = self.v.validate_lease_term(None)
        assert valid is True

    def test_valid_primary(self):
        valid, err = self.v.validate_lease_term(5)
        assert valid is True

    def test_primary_too_short(self):
        valid, err = self.v.validate_lease_term(0)
        assert valid is False
        assert "at least 1" in err

    def test_primary_too_long(self):
        valid, err = self.v.validate_lease_term(100)
        assert valid is False
        assert "unusually long" in err

    def test_valid_secondary(self):
        valid, err = self.v.validate_lease_term(5, 5)
        assert valid is True

    def test_negative_secondary(self):
        valid, err = self.v.validate_lease_term(5, -1)
        assert valid is False

    def test_secondary_too_long(self):
        valid, err = self.v.validate_lease_term(5, 100)
        assert valid is False

    def test_invalid_primary_type(self):
        valid, err = self.v.validate_lease_term("abc")
        assert valid is False

    def test_invalid_secondary_type(self):
        valid, err = self.v.validate_lease_term(5, "abc")
        assert valid is False


class TestValidateAcreage:
    """Tests for LandmanDataValidator.validate_acreage."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_none_is_optional(self):
        valid, err = self.v.validate_acreage(None)
        assert valid is True

    def test_valid(self):
        valid, err = self.v.validate_acreage(640.0)
        assert valid is True

    def test_zero(self):
        valid, err = self.v.validate_acreage(0.0)
        assert valid is False
        assert "positive" in err.lower()

    def test_negative(self):
        valid, err = self.v.validate_acreage(-10.0)
        assert valid is False

    def test_too_large(self):
        valid, err = self.v.validate_acreage(1000001.0)
        assert valid is False

    def test_invalid_type(self):
        valid, err = self.v.validate_acreage("abc")
        assert valid is False


class TestValidateOwnershipRecord:
    """Tests for LandmanDataValidator.validate_ownership_record."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_valid_record(self):
        record = {
            "legal_description": "Section 12, Block 42, T-1-S",
            "owner_name": "John Doe",
            "state": "TX",
            "county": "Reeves",
            "mineral_interest_percent": 50.0,
            "net_mineral_acres": 320.0,
        }
        valid, errors = self.v.validate_ownership_record(record)
        assert valid is True
        assert errors == []

    def test_invalid_state_in_record(self):
        record = {"state": "ZZ"}
        valid, errors = self.v.validate_ownership_record(record)
        assert valid is False
        assert len(errors) == 1
        assert "State" in errors[0]

    def test_multiple_errors(self):
        record = {
            "state": "ZZ",
            "mineral_interest_percent": -5.0,
            "net_mineral_acres": -10.0,
        }
        valid, errors = self.v.validate_ownership_record(record)
        assert valid is False
        assert len(errors) == 3

    def test_empty_record(self):
        valid, errors = self.v.validate_ownership_record({})
        assert valid is True

    def test_increments_counters(self):
        self.v.validate_ownership_record({"state": "TX"})
        self.v.validate_ownership_record({"state": "ZZ"})
        assert self.v.validation_count == 2
        assert self.v.error_count == 1


class TestValidateLeaseRecord:
    """Tests for LandmanDataValidator.validate_lease_record."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_valid_lease(self):
        record = {
            "legal_description": "Section 12, Block 42",
            "lessor": "John Doe",
            "lessee": "Oil Company LLC",
            "state": "TX",
            "royalty_rate": 0.1875,
            "primary_term_years": 5,
            "effective_date": "2020-01-01",
        }
        valid, errors = self.v.validate_lease_record(record)
        assert valid is True
        assert errors == []

    def test_invalid_royalty(self):
        record = {"royalty_rate": 0.75}
        valid, errors = self.v.validate_lease_record(record)
        assert valid is False
        assert any("Royalty" in e for e in errors)

    def test_invalid_dates(self):
        record = {"effective_date": "not-a-date"}
        valid, errors = self.v.validate_lease_record(record)
        assert valid is False

    def test_empty_lease(self):
        valid, errors = self.v.validate_lease_record({})
        assert valid is True


class TestNormalizeStateCode:
    """Tests for LandmanDataValidator.normalize_state_code."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_valid_code(self):
        assert self.v.normalize_state_code("TX") == "TX"

    def test_lowercase(self):
        assert self.v.normalize_state_code("tx") == "TX"

    def test_state_name(self):
        assert self.v.normalize_state_code("Texas") == "TX"

    def test_invalid(self):
        assert self.v.normalize_state_code("ZZ") is None

    def test_empty(self):
        assert self.v.normalize_state_code("") is None

    def test_none(self):
        assert self.v.normalize_state_code(None) is None


class TestNormalizeLegalDescription:
    """Tests for LandmanDataValidator.normalize_legal_description."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_empty(self):
        assert self.v.normalize_legal_description("") == ""

    def test_none(self):
        assert self.v.normalize_legal_description(None) == ""

    def test_strips_whitespace(self):
        result = self.v.normalize_legal_description("  Lot 5, Block 3  ")
        assert result.startswith("Lot")
        assert result.endswith("3")

    def test_standardizes_sec(self):
        result = self.v.normalize_legal_description("sec 12")
        assert "Section" in result

    def test_standardizes_blk(self):
        result = self.v.normalize_legal_description("blk 42")
        assert "Block" in result

    def test_standardizes_quarter(self):
        result = self.v.normalize_legal_description("ne 1/4")
        assert "NE/4" in result


class TestGetStatistics:
    """Tests for LandmanDataValidator.get_statistics."""

    def setup_method(self):
        self.v = LandmanDataValidator()

    def test_initial_stats(self):
        stats = self.v.get_statistics()
        assert stats["validations"] == 0
        assert stats["errors"] == 0
        assert stats["success_rate"] == 0.0

    def test_after_validations(self):
        self.v.validate_ownership_record({"state": "TX"})
        self.v.validate_ownership_record({"state": "ZZ"})
        stats = self.v.get_statistics()
        assert stats["validations"] == 2
        assert stats["errors"] == 1
        assert stats["success_rate"] == 0.5


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_is_valid_legal_description_true(self):
        assert is_valid_legal_description("Section 12, Block 42") is True

    def test_is_valid_legal_description_false(self):
        assert is_valid_legal_description("") is False

    def test_is_valid_state_code_true(self):
        assert is_valid_state_code("TX") is True

    def test_is_valid_state_code_false(self):
        assert is_valid_state_code("ZZ") is False

    def test_is_valid_mineral_interest_true(self):
        assert is_valid_mineral_interest(50.0) is True

    def test_is_valid_mineral_interest_false(self):
        assert is_valid_mineral_interest(-1.0) is False

    def test_is_major_og_state_true(self):
        assert is_major_og_state("TX") is True

    def test_is_major_og_state_false(self):
        assert is_major_og_state("FL") is False

    def test_is_major_og_state_empty(self):
        assert is_major_og_state("") is False

    def test_is_major_og_state_none(self):
        assert is_major_og_state(None) is False


class TestUSStateCodes:
    """Tests for US_STATE_CODES and MAJOR_OG_STATES constants."""

    def test_state_codes_has_texas(self):
        assert "TX" in US_STATE_CODES

    def test_state_codes_count(self):
        assert len(US_STATE_CODES) > 25

    def test_major_og_states_subset(self):
        assert MAJOR_OG_STATES.issubset(set(US_STATE_CODES.keys()))
