# ABOUTME: Canonical Landman provider capability and readiness registry.
# ABOUTME: Separates implementation status from contextual runtime readiness.

"""Provider registrations and truthful contextual status output."""

from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable

from ..routing import SourceConfig


ProviderFactory = Callable[[SourceConfig], Any]


def _county_records_factory(source: SourceConfig):
    from .county_records import CountyRecordsProvider

    return CountyRecordsProvider(source)


@dataclass(frozen=True)
class ProviderRegistration:
    """Static provider capability metadata plus an optional local factory."""

    name: str
    implementation_status: str
    router_operations: tuple[str, ...]
    mode: str
    requirements: tuple[str, ...]
    sample_available: bool
    priority: int
    factory: ProviderFactory | None = None


PROVIDER_REGISTRY = (
    ProviderRegistration(
        "county_records",
        "implemented",
        ("ownership",),
        "fixture-only",
        ("exactly_one_fixture_source",),
        True,
        10,
        _county_records_factory,
    ),
    ProviderRegistration(
        "county_reference",
        "reference-only",
        (),
        "embedded-reference",
        (),
        False,
        20,
    ),
    ProviderRegistration("blm", "configured-only", (), "live-reserved", (), False, 30),
    ProviderRegistration(
        "state_gis", "configured-only", (), "live-reserved", (), False, 40
    ),
    ProviderRegistration(
        "drillinginfo", "unavailable", (), "subscription", (), False, 50
    ),
    ProviderRegistration("txdir", "unavailable", (), "subscription", (), False, 60),
    ProviderRegistration("ogorgs", "unavailable", (), "unimplemented", (), False, 70),
)


def _status_row(
    registration: ProviderRegistration, operation: str, source: SourceConfig
) -> dict[str, Any]:
    requirements_satisfied = not registration.requirements or source.is_selected
    routable = (
        registration.implementation_status == "implemented"
        and operation in registration.router_operations
        and requirements_satisfied
        and registration.factory is not None
    )
    return {
        "name": registration.name,
        "implementation_status": registration.implementation_status,
        "router_operations": list(registration.router_operations),
        "mode": registration.mode,
        "requirements": list(registration.requirements),
        "requirements_satisfied": requirements_satisfied,
        "routable_now": routable,
        "sample_available": registration.sample_available,
    }


def provider_status_payload(operation: str, source: SourceConfig) -> dict[str, Any]:
    """Build deterministic provider rows and implementation-status counts."""
    rows = [_status_row(row, operation, source) for row in PROVIDER_REGISTRY]
    statuses = Counter(row["implementation_status"] for row in rows)
    return {
        "operation": operation,
        "source_mode": source.mode,
        "providers": rows,
        "route_modes": [SourceConfig.ROUTE_MODE],
        "counts": {
            "total": len(rows),
            "implemented": statuses["implemented"],
            "reference_only": statuses["reference-only"],
            "configured_only": statuses["configured-only"],
            "unavailable": statuses["unavailable"],
        },
    }
