"""Focused contracts for Landman operation routing and provider readiness."""

from dataclasses import replace

import pytest

from worldenergydata.landman.exceptions import CapabilityUnavailableError, LandmanError
from worldenergydata.landman.landman import Landman, LandmanValidationError
from worldenergydata.landman.providers.registry import (
    PROVIDER_REGISTRY,
    ProviderRegistration,
    provider_status_payload,
)
from worldenergydata.landman.routing import (
    ATOMIC_OPERATIONS,
    SourceConfig,
    normalize_operations,
    preflight,
)


def _registration(name, operations, factory, priority=10):
    return ProviderRegistration(
        name=name,
        implementation_status="implemented",
        router_operations=tuple(operations),
        mode="fixture-only",
        requirements=(),
        sample_available=False,
        priority=priority,
        factory=factory,
    )


def test_operation_vocabulary_and_all_order():
    assert ATOMIC_OPERATIONS == (
        "ownership",
        "leases",
        "title",
        "deeds",
        "mortgages",
        "assignments",
    )
    assert normalize_operations(["all"]) == ATOMIC_OPERATIONS
    assert normalize_operations(["title", "ownership"]) == ("ownership", "title")
    for invalid in ("Ownership", "lease", "unknown"):
        with pytest.raises(LandmanValidationError):
            normalize_operations([invalid])


def test_router_preflight_is_atomic():
    calls = []
    constructions = []

    class Provider:
        def search_ownership(self, criteria):
            calls.append(criteria)
            return []

    def factory(source):
        constructions.append(source)
        return Provider()

    registry = (_registration("fixture", ("ownership",), factory),)
    landman = Landman(registry=registry)

    with pytest.raises(CapabilityUnavailableError) as caught:
        landman.router(
            {
                "data_types": ["ownership", "title", "leases"],
                "provider": "auto",
                "source": {"sample": True, "records_file": None},
                "search": {"state": "TX", "county": "MIDLAND"},
            }
        )

    assert calls == []
    assert constructions == []
    assert [row["operation"] for row in caught.value.failures] == [
        "leases",
        "title",
    ]


def test_atomic_error_envelope_lists_every_operation():
    source = SourceConfig(sample=True)
    with pytest.raises(CapabilityUnavailableError) as caught:
        preflight(["all"], "auto", source, PROVIDER_REGISTRY)

    error = caught.value
    assert error.requested_provider == "auto"
    assert error.resolved_provider is None
    assert [failure["operation"] for failure in error.failures] == list(
        ATOMIC_OPERATIONS[1:]
    )
    assert all(
        failure["code"] == "LANDMAN_CAPABILITY_UNAVAILABLE"
        for failure in error.failures
    )


def test_auto_priority_is_deterministic_with_two_candidates():
    high = _registration("zeta", ("ownership",), object, priority=20)
    low = replace(high, name="alpha", priority=10)
    same_priority = replace(high, name="aardvark", priority=10)

    plan = preflight(
        ["ownership"],
        SourceConfig.ROUTE_MODE,
        SourceConfig(sample=True),
        (high, low, same_priority),
    )

    assert plan.routes["ownership"].name == "aardvark"


def test_registry_status_schema_counts_and_context():
    without_source = provider_status_payload("ownership", SourceConfig())
    with_sample = provider_status_payload("ownership", SourceConfig(sample=True))
    expected_keys = {
        "name",
        "implementation_status",
        "router_operations",
        "mode",
        "requirements",
        "requirements_satisfied",
        "routable_now",
        "sample_available",
    }

    assert without_source["counts"] == {
        "total": 7,
        "implemented": 1,
        "reference_only": 1,
        "configured_only": 2,
        "unavailable": 3,
    }
    assert without_source["route_modes"] == ["auto"]
    assert len({row["name"] for row in without_source["providers"]}) == 7
    assert all(set(row) == expected_keys for row in without_source["providers"])
    county_without = next(
        row for row in without_source["providers"] if row["name"] == "county_records"
    )
    county_with = next(
        row for row in with_sample["providers"] if row["name"] == "county_records"
    )
    assert county_without["sample_available"] is True
    assert county_without["requirements_satisfied"] is False
    assert county_without["routable_now"] is False
    assert county_with["requirements_satisfied"] is True
    assert county_with["routable_now"] is True


def test_source_config_is_immutable_and_requires_exactly_one_source():
    source = SourceConfig.from_mapping({"sample": True, "records_file": None})
    assert source.sample is True
    with pytest.raises((AttributeError, TypeError)):
        source.sample = False
    with pytest.raises(LandmanValidationError):
        SourceConfig.from_mapping({"sample": True, "records_file": "records.json"})
    with pytest.raises(LandmanValidationError):
        SourceConfig.from_mapping([])


@pytest.mark.parametrize(
    "records_file",
    [
        "",
        ".",
        "..",
        "nested/records.json",
        r"C:\private\records.json",
        "bad\x00.json",
        "records.txt",
    ],
)
def test_source_config_rejects_invalid_custom_file_syntax(records_file):
    with pytest.raises(LandmanError) as caught:
        SourceConfig.from_mapping({"records_file": records_file})
    assert caught.value.code == "LANDMAN_FIXTURE_PATH_INVALID"
    assert "C:\\private" not in str(caught.value)


@pytest.mark.parametrize(
    "criteria",
    [
        {},
        {"state": "TX"},
        {"county": "MIDLAND"},
        {"state": "  ", "county": "MIDLAND"},
        {"state": "TX", "county": "  "},
    ],
)
def test_router_ownership_requires_state_and_county_search_predicates(criteria):
    calls = []

    class Provider:
        def search_ownership(self, search):
            calls.append(search)
            return []

    registry = (_registration("fixture", ("ownership",), lambda source: Provider()),)
    with pytest.raises(LandmanValidationError) as caught:
        Landman(registry=registry).router(
            {
                "data_types": ["ownership"],
                "provider": "auto",
                "source": {"sample": True, "records_file": None},
                "state": "TX",
                "county": "MIDLAND",
                "search": criteria,
            }
        )
    assert caught.value.code == "LANDMAN_SEARCH_CRITERIA_REQUIRED"
    assert calls == []


@pytest.mark.parametrize(
    ("criteria", "code"),
    [
        ({"state": "ZZ", "county": "MIDLAND"}, "LANDMAN_INVALID_STATE"),
        ({"state": "TX", "county": "1"}, "LANDMAN_INVALID_COUNTY"),
    ],
)
def test_router_ownership_validates_state_and_county_values(criteria, code):
    calls = []

    class Provider:
        def search_ownership(self, search):
            calls.append(search)
            return []

    registry = (_registration("fixture", ("ownership",), lambda source: Provider()),)
    with pytest.raises(LandmanValidationError) as caught:
        Landman(registry=registry).router(
            {
                "data_types": ["ownership"],
                "provider": "auto",
                "source": {"sample": True},
                "search": criteria,
            }
        )
    assert caught.value.code == code
    assert calls == []
