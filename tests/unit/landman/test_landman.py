"""Tests for Landman module constants, validation errors, and init."""

from worldenergydata.landman.landman import (
    Landman,
    LandmanValidationError,
)

# ---------------------------------------------------------------------------
# LandmanValidationError
# ---------------------------------------------------------------------------


class TestLandmanValidationError:
    def test_invalid_state_code(self):
        err = LandmanValidationError.invalid_state_code("ZZ")
        assert "ZZ" in str(err)
        assert err.details["state_code"] == "ZZ"

    def test_invalid_legal_description(self):
        err = LandmanValidationError.invalid_legal_description("BAD-DESC", "too short")
        assert "BAD-DESC" in str(err)
        assert "too short" in str(err)

    def test_invalid_legal_no_reason(self):
        err = LandmanValidationError.invalid_legal_description("BAD")
        assert "BAD" in str(err)


# ---------------------------------------------------------------------------
# Landman constants
# ---------------------------------------------------------------------------


class TestLandmanConstants:
    def test_valid_data_types(self):
        types = Landman.VALID_DATA_TYPES
        assert "ownership" in types
        assert "leases" in types
        assert "title" in types
        assert "deeds" in types
        assert "all" in types

    def test_valid_providers(self):
        providers = Landman.VALID_PROVIDERS
        assert "county_records" in providers
        assert "drillinginfo" in providers
        assert "auto" in providers

    def test_data_types_count(self):
        assert len(Landman.VALID_DATA_TYPES) == 7

    def test_providers_count(self):
        assert len(Landman.VALID_PROVIDERS) == 8
        assert len(Landman().get_valid_providers()) == 7
        assert "auto" not in Landman().get_valid_providers()


# ---------------------------------------------------------------------------
# Landman init
# ---------------------------------------------------------------------------


class TestLandmanInit:
    def test_module_name(self):
        lm = Landman()
        assert lm.module_name == "landman"

    def test_validator(self):
        lm = Landman()
        assert lm.validator is not None

    def test_providers_empty(self):
        lm = Landman()
        assert lm._providers == {}
