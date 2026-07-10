"""Regression coverage for runtime and legacy Landman exception surfaces."""

from pathlib import Path

from worldenergydata.landman import LandmanProviderError as ExportedProviderError
from worldenergydata.landman.errors import LandmanProviderError as LegacyProviderError
from worldenergydata.landman.exceptions import (
    CapabilityUnavailableError,
    ProviderError,
)
from worldenergydata.landman.landman import LandmanValidationError


def test_runtime_and_legacy_exception_contracts():
    assert ExportedProviderError is ProviderError
    assert LegacyProviderError is not ProviderError
    runtime = ProviderError.unavailable("county_records", "source missing")
    legacy = LegacyProviderError.unavailable("county_records", "source missing")
    assert runtime.code == "LANDMAN_PROVIDER_UNAVAILABLE"
    assert runtime.details["provider"] == "county_records"
    assert legacy.code == "LANDMAN_PROVIDER_UNAVAILABLE"
    assert legacy.provider_name == "county_records"
    assert runtime.to_dict()["code"] == "LANDMAN_PROVIDER_UNAVAILABLE"


def test_capability_error_has_stable_plural_failure_contract():
    failures = [
        {
            "operation": "title",
            "code": "LANDMAN_CAPABILITY_UNAVAILABLE",
            "candidate_statuses": [
                {"name": "county_records", "reason": "operation_not_advertised"}
            ],
            "message": "No provider can execute title",
        }
    ]
    error = CapabilityUnavailableError("auto", failures)
    assert isinstance(error, ProviderError)
    assert error.code == "LANDMAN_CAPABILITY_UNAVAILABLE"
    assert error.requested_provider == "auto"
    assert error.resolved_provider is None
    assert error.failures == failures


def test_landman_validation_error_constructor_and_factories_remain_compatible():
    direct = LandmanValidationError(
        message="bad", error_code="CUSTOM", details={"x": 1}
    )
    state = LandmanValidationError.invalid_state_code("ZZ")
    assert direct.code == "CUSTOM"
    assert direct.details["x"] == 1
    assert direct.details["module"] == "landman"
    assert state.code == "LANDMAN_INVALID_STATE"


def test_package_docstring_describes_fixture_only_usage():
    package = Path(__file__).parents[3] / (
        "packages/worldenergydata-landman/src/worldenergydata/landman/__init__.py"
    )
    text = package.read_text(encoding="utf-8")
    assert "fixture-only" in text.casefold()
    assert "sample=True" in text
    assert "County clerk record searches" not in text
    assert "BLM federal land records" not in text
    assert "chain of title analysis" not in text
