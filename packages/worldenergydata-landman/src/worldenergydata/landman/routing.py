# ABOUTME: Atomic operation normalization and provider preflight for Landman.
# ABOUTME: Keeps source selection immutable and provider construction post-preflight.

"""Operation-aware, fail-atomic routing contracts for Landman."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, ClassVar, Iterable, Mapping, Sequence

from .exceptions import CapabilityUnavailableError, FixtureValidationError


ATOMIC_OPERATIONS = (
    "ownership",
    "leases",
    "title",
    "deeds",
    "mortgages",
    "assignments",
)


def _validation_error(message: str, code: str, details: dict[str, Any]):
    from .landman import LandmanValidationError

    return LandmanValidationError(message=message, error_code=code, details=details)


def _display_name(value: object) -> str:
    basename = (
        value.replace("\\", "/").rsplit("/", 1)[-1] if isinstance(value, str) else ""
    )
    return basename or "<invalid>"


def validate_records_file_name(value: str) -> str:
    """Require one direct-child JSON basename without exposing rejected paths."""
    invalid = (
        not isinstance(value, str)
        or value in {"", ".", ".."}
        or "/" in value
        or "\\" in value
        or "\x00" in value
        or not value.endswith(".json")
    )
    if invalid:
        raise FixtureValidationError(
            "LANDMAN_FIXTURE_PATH_INVALID",
            _display_name(value),
            "custom file must be a direct-child .json basename",
        )
    return value


@dataclass(frozen=True)
class SourceConfig:
    """Immutable fixture source selection shared by readiness and construction."""

    ROUTE_MODE: ClassVar[str] = "auto"
    sample: bool = False
    records_file: str | None = None

    @property
    def is_selected(self) -> bool:
        return self.sample ^ (self.records_file is not None)

    @property
    def mode(self) -> str | None:
        if self.sample:
            return "sample"
        if self.records_file is not None:
            return "records_file"
        return None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "SourceConfig":
        if value is None:
            value = {}
        elif not isinstance(value, Mapping):
            raise _validation_error(
                "Fixture source must be a mapping", "LANDMAN_INVALID_SOURCE", {}
            )
        unknown = set(value) - {"sample", "records_file"}
        if unknown:
            raise _validation_error(
                "Invalid fixture source keys",
                "LANDMAN_INVALID_SOURCE",
                {"unknown_keys": sorted(unknown)},
            )
        sample = value.get("sample", False)
        records_file = value.get("records_file")
        if (
            type(sample) is not bool
            or records_file is not None
            and not isinstance(records_file, str)
        ):
            raise _validation_error(
                "Invalid fixture source types", "LANDMAN_INVALID_SOURCE", {}
            )
        source = cls(sample=sample, records_file=records_file)
        if sample and records_file is not None:
            raise _validation_error(
                "Choose exactly one fixture source", "LANDMAN_INVALID_SOURCE", {}
            )
        if records_file is not None:
            validate_records_file_name(records_file)
        return source

    @classmethod
    def from_keywords(cls, sample: bool, records_file: str | None) -> "SourceConfig":
        return cls.from_mapping({"sample": sample, "records_file": records_file})


@dataclass(frozen=True)
class RoutingPlan:
    """Resolved provider registration for every requested operation."""

    requested_provider: str
    operations: tuple[str, ...]
    routes: Mapping[str, Any]

    @classmethod
    def create(cls, requested_provider: str, operations: tuple[str, ...], routes: dict):
        return cls(requested_provider, operations, MappingProxyType(dict(routes)))

    @property
    def resolved_provider(self) -> str | None:
        names = {registration.name for registration in self.routes.values()}
        return next(iter(names)) if len(names) == 1 else None

    @property
    def provider_by_operation(self) -> Mapping[str, str]:
        return MappingProxyType(
            {operation: self.routes[operation].name for operation in self.operations}
        )


def normalize_operations(values: str | Iterable[str] | None) -> tuple[str, ...]:
    """Validate exact names, expand all, and return canonical operation order."""
    requested = [values] if isinstance(values, str) else list(values or ["all"])
    invalid = [value for value in requested if value not in (*ATOMIC_OPERATIONS, "all")]
    if invalid:
        raise _validation_error(
            f"Invalid data types: {invalid}",
            "LANDMAN_INVALID_DATA_TYPES",
            {"invalid_types": invalid},
        )
    selected = set(ATOMIC_OPERATIONS if "all" in requested else requested)
    return tuple(operation for operation in ATOMIC_OPERATIONS if operation in selected)


def _candidate_reason(registration: Any, operation: str, source: SourceConfig) -> str:
    if registration.implementation_status != "implemented":
        return registration.implementation_status.replace("-", "_")
    if operation not in registration.router_operations:
        return "operation_not_advertised"
    if registration.requirements and not source.is_selected:
        return "requirements_not_satisfied"
    if registration.factory is None:
        return "implementation_missing"
    return "ready"


def _failure(operation: str, candidates: Sequence[Any], source: SourceConfig) -> dict:
    statuses = [
        {"name": row.name, "reason": _candidate_reason(row, operation, source)}
        for row in candidates
    ]
    return {
        "operation": operation,
        "code": "LANDMAN_CAPABILITY_UNAVAILABLE",
        "candidate_statuses": statuses,
        "message": f"No provider can execute '{operation}' in this context",
    }


def preflight(
    operations: str | Iterable[str],
    requested_provider: str,
    source: SourceConfig,
    registry: Sequence[Any],
) -> RoutingPlan:
    """Resolve every operation before any provider is constructed or called."""
    normalized = normalize_operations(operations)
    ordered = tuple(sorted(registry, key=lambda row: (row.priority, row.name)))
    if requested_provider != SourceConfig.ROUTE_MODE:
        ordered = tuple(row for row in ordered if row.name == requested_provider)
    routes = {}
    failures = []
    for operation in normalized:
        ready = [
            row
            for row in ordered
            if _candidate_reason(row, operation, source) == "ready"
        ]
        if ready:
            routes[operation] = ready[0]
        else:
            failures.append(_failure(operation, ordered, source))
    if failures:
        raise CapabilityUnavailableError(requested_provider, failures)
    return RoutingPlan.create(requested_provider, normalized, routes)
