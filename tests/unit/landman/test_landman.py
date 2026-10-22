"""Tests for Landman module constants, validation errors, and init."""

import pytest

from worldenergydata.landman.exceptions import LandmanError, ProviderError
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
        assert len(Landman.VALID_PROVIDERS) == 5


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


class TestLandmanRouterFailures:
    """Regression contract from issue #1255 and LandmanError.__init__.

    No numerical model is involved. Expected codes and details are the
    explicit failure contracts in Landman._validate_config and router;
    exceptions.py defines their error_code/details/cause constructor names.
    """

    @pytest.mark.parametrize(
        "cfg, error_code, details, message",
        [
            ({}, "LANDMAN_CONFIG_EMPTY", {}, "Configuration cannot be empty"),
            (
                {"data_types": ["unknown"]},
                "LANDMAN_INVALID_DATA_TYPES",
                {"invalid_types": ["unknown"]},
                "Invalid data types:",
            ),
            (
                {"provider": "unknown"},
                "LANDMAN_INVALID_PROVIDER",
                {"provider": "unknown"},
                "Invalid provider:",
            ),
            (
                {"search": {"owner_name": ""}},
                "LANDMAN_INVALID_OWNER_NAME",
                {},
                "Invalid owner name: Owner name is empty",
            ),
        ],
        ids=["empty-config", "invalid-data-type", "invalid-provider", "empty-name"],
    )
    def test_invalid_config(self, monkeypatch, cfg, error_code, details, message):
        """Each invalid input must fail validation before provider acquisition."""
        lm = Landman()

        def unexpected_provider(*args):
            pytest.fail("Invalid configuration reached provider acquisition")

        monkeypatch.setattr(lm, "_get_provider", unexpected_provider)

        with pytest.raises(LandmanValidationError) as caught:
            lm.router(cfg)

        error = caught.value
        assert error.error_code == error_code
        assert error.code == error_code
        # ModuleError.__init__ adds the module identifier to every error context.
        assert error.details == {"module": "landman", **details}
        assert error.context == error.details
        assert message in error.message
        assert "basename" not in cfg

    @pytest.mark.parametrize("stage", ["_get_provider", "_collect_data"])
    def test_unexpected_failure_is_wrapped(self, monkeypatch, stage):
        """The router contract preserves the original cause and error status."""
        lm = Landman()
        cfg = {"provider": "county_records"}
        cause = RuntimeError("synthetic failure")
        monkeypatch.setattr(lm, "_get_provider", lambda *args: object())

        def fail(*args):
            raise cause

        monkeypatch.setattr(lm, stage, fail)

        with pytest.raises(LandmanError) as caught:
            lm.router(cfg)

        error = caught.value
        assert type(error) is LandmanError
        assert error.error_code == "LANDMAN_ROUTER_ERROR"
        assert error.details == {"module": "landman"}
        assert error.message == "Landman router failed: synthetic failure"
        assert error.cause is cause
        assert error.__cause__ is cause
        assert cfg["landman"]["status"] == "error"
        assert cfg["landman"]["error"] == "synthetic failure"

    @pytest.mark.parametrize("stage", ["_get_provider", "_collect_data"])
    @pytest.mark.parametrize("error_type", [LandmanError, ProviderError])
    def test_existing_domain_error_is_preserved(self, monkeypatch, stage, error_type):
        """router's LandmanError handler must re-raise the same error object."""
        lm = Landman()
        cause = RuntimeError("original failure")
        error = error_type(
            "synthetic domain failure",
            error_code="SYNTHETIC_FAILURE",
            details={"source": "test"},
            cause=cause,
        )
        monkeypatch.setattr(lm, "_get_provider", lambda *args: object())

        def fail(*args):
            raise error

        monkeypatch.setattr(lm, stage, fail)

        with pytest.raises(error_type) as caught:
            lm.router({"provider": "county_records"})

        assert caught.value is error
        assert error.error_code == "SYNTHETIC_FAILURE"
        assert error.details == {"module": "landman", "source": "test"}
        assert error.cause is cause
        assert error.__cause__ is cause


class TestLandmanOwnershipFailures:
    def test_invalid_county(self, monkeypatch):
        """Issue #1255: an empty county must raise LANDMAN_INVALID_COUNTY.

        Source: validate_county_name's empty-input branch and
        search_ownership's explicit validation contract. ModuleError adds
        the module identifier; no numerical reference value is involved.
        """
        lm = Landman()

        def unexpected_provider(*args):
            pytest.fail("Invalid county reached provider acquisition")

        monkeypatch.setattr(lm, "_get_provider", unexpected_provider)

        with pytest.raises(LandmanValidationError) as caught:
            lm.search_ownership(state="TX", county="")

        error = caught.value
        assert error.error_code == "LANDMAN_INVALID_COUNTY"
        assert error.message == "Invalid county: County name is empty"
        assert error.details == {"module": "landman"}
