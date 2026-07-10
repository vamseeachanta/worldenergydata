# ABOUTME: Public Landman facade over atomic provider routing.
# ABOUTME: Preserves search APIs while making source and provenance explicit.

"""Main Landman router and compatibility facade."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from .exceptions import LandmanError
from .models import LeaseRecord, OwnerSearchResult, TitleRecord
from .providers.registry import PROVIDER_REGISTRY
from .routing import ATOMIC_OPERATIONS, SourceConfig, normalize_operations, preflight
from .validators import US_STATE_CODES, LandmanDataValidator


class LandmanValidationError(LandmanError):
    """Validation error for Landman module."""

    default_code = "LANDMAN_VALIDATION_ERROR"

    @classmethod
    def invalid_state_code(cls, state_code: str) -> "LandmanValidationError":
        return cls(
            message=f"Invalid state code: {state_code}",
            error_code="LANDMAN_INVALID_STATE",
            details={"state_code": state_code},
        )

    @classmethod
    def invalid_legal_description(
        cls, legal_description: str, reason: str = ""
    ) -> "LandmanValidationError":
        message = f"Invalid legal description: {legal_description}"
        if reason:
            message += f" - {reason}"
        return cls(
            message=message,
            error_code="LANDMAN_INVALID_LEGAL_DESC",
            details={"legal_description": legal_description},
        )


logger = logging.getLogger(__name__)


class Landman:
    """Operation-aware facade for Landman provider execution."""

    VALID_DATA_TYPES = [*ATOMIC_OPERATIONS, "all"]
    VALID_PROVIDERS = [row.name for row in PROVIDER_REGISTRY] + [
        SourceConfig.ROUTE_MODE
    ]

    def __init__(self, registry: Sequence[Any] | None = None):
        self.module_name = "landman"
        self.validator = LandmanDataValidator()
        self.registry = tuple(registry or PROVIDER_REGISTRY)
        self._providers: Dict[str, Any] = {}
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Retain the historical lazy-initialization hook."""

    def router(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Preflight all requested operations, then execute the resolved providers."""
        self._validate_config(cfg)
        operations = normalize_operations(cfg.get("data_types", ["all"]))
        requested = cfg.get("provider", SourceConfig.ROUTE_MODE)
        source = SourceConfig.from_mapping(cfg.get("source"))
        criteria = dict(cfg.get("search", {}))
        self._validate_required_search(operations, criteria)
        plan = preflight(operations, requested, source, self.registry)
        instances: dict[str, Any] = {}
        data = {}
        for operation in operations:
            registration = plan.routes[operation]
            provider = instances.get(registration.name)
            if provider is None:
                provider = registration.factory(source)
                instances[registration.name] = provider
            data[operation] = self._execute_operation(provider, operation, criteria)
        basename = cfg.setdefault("basename", self.module_name)
        section = cfg.setdefault(basename, {})
        section.update(self._result_metadata(plan, data))
        section["data"] = dict(cfg.get("data", {}))
        section["search"] = criteria
        section["results"] = data
        return cfg

    @staticmethod
    def _validate_required_search(
        operations: Sequence[str], criteria: dict[str, Any]
    ) -> None:
        if "ownership" not in operations:
            return
        missing = [
            field
            for field in ("state", "county")
            if not isinstance(criteria.get(field), str) or not criteria[field].strip()
        ]
        if missing:
            raise LandmanValidationError(
                message="Ownership search requires non-empty state and county",
                error_code="LANDMAN_SEARCH_CRITERIA_REQUIRED",
                details={"missing_fields": missing},
            )

    @staticmethod
    def _execute_operation(provider: Any, operation: str, criteria: dict[str, Any]):
        method = getattr(provider, f"search_{operation}")
        return method(criteria)

    @staticmethod
    def _result_metadata(plan: Any, data: dict[str, Any]) -> dict[str, Any]:
        count = sum(
            len(value) if isinstance(value, list) else 1 for value in data.values()
        )
        result = {
            "status": "completed",
            "requested_provider": plan.requested_provider,
            "provider_by_operation": dict(plan.provider_by_operation),
            "data_collected": list(data),
            "record_count": count,
        }
        if plan.resolved_provider is not None:
            result["resolved_provider"] = plan.resolved_provider
        return result

    def _validate_config(self, cfg: Dict[str, Any]) -> None:
        if not cfg:
            raise LandmanValidationError(
                message="Configuration cannot be empty",
                error_code="LANDMAN_CONFIG_EMPTY",
            )
        normalize_operations(cfg.get("data_types", ["all"]))
        provider = cfg.get("provider", SourceConfig.ROUTE_MODE)
        valid_names = [row.name for row in self.registry] + [SourceConfig.ROUTE_MODE]
        if provider not in valid_names:
            raise LandmanValidationError(
                message=f"Invalid provider: {provider}",
                error_code="LANDMAN_INVALID_PROVIDER",
                details={"provider": provider},
            )
        if "state" in cfg:
            self._validate_state(cfg["state"])
        search = cfg.get("search", {})
        if search.get("legal_description"):
            self._validate_legal(search["legal_description"])
        if search.get("owner_name"):
            valid, error = self.validator.validate_owner_name(search["owner_name"])
            if not valid:
                raise LandmanValidationError(
                    message=f"Invalid owner name: {error}",
                    error_code="LANDMAN_INVALID_OWNER_NAME",
                )

    def _validate_state(self, state: str) -> None:
        valid, _ = self.validator.validate_state_code(state)
        if not valid:
            raise LandmanValidationError.invalid_state_code(state)

    def _validate_legal(self, legal_description: str) -> None:
        valid, error = self.validator.validate_legal_description(legal_description)
        if not valid:
            raise LandmanValidationError.invalid_legal_description(
                legal_description, error or ""
            )

    def _search_criteria(
        self,
        state: str,
        county: str,
        legal_description: str | None,
        owner_name: str | None,
    ) -> dict[str, str]:
        self._validate_state(state)
        valid, error = self.validator.validate_county_name(county, state)
        if not valid:
            raise LandmanValidationError(
                message=f"Invalid county: {error}", error_code="LANDMAN_INVALID_COUNTY"
            )
        criteria = {"state": state, "county": county}
        if legal_description:
            self._validate_legal(legal_description)
            criteria["legal_description"] = legal_description
        if owner_name:
            valid, error = self.validator.validate_owner_name(owner_name)
            if not valid:
                raise LandmanValidationError(
                    message=f"Invalid owner name: {error}",
                    error_code="LANDMAN_INVALID_OWNER_NAME",
                )
            criteria["owner_name"] = owner_name
        return criteria

    def search_ownership(
        self,
        state: str,
        county: str,
        legal_description: Optional[str] = None,
        owner_name: Optional[str] = None,
        provider: str = "auto",
        sample: bool = False,
        records_file: Optional[str] = None,
    ) -> OwnerSearchResult:
        """Search one explicitly selected fixture source for ownership records."""
        started = datetime.now()
        criteria = self._search_criteria(state, county, legal_description, owner_name)
        source = SourceConfig.from_keywords(sample, records_file)
        plan = preflight(["ownership"], provider, source, self.registry)
        registration = plan.routes["ownership"]
        records = registration.factory(source).search_ownership(criteria)
        elapsed = int((datetime.now() - started).total_seconds() * 1000)
        return OwnerSearchResult(
            search_id=str(uuid.uuid4()),
            search_criteria=criteria,
            state=state,
            county=county,
            owner_name=owner_name,
            legal_description=legal_description,
            ownership_records=records,
            provider=registration.name,
            search_duration_ms=elapsed,
        )

    def _unsupported_records(
        self, operation: str, criteria: dict[str, Any], provider: str
    ) -> list:
        source = SourceConfig()
        plan = preflight([operation], provider, source, self.registry)
        registration = plan.routes[operation]
        return self._execute_operation(
            registration.factory(source), operation, criteria
        )

    def get_lease_records(
        self,
        state: str,
        county: str,
        owner_name: Optional[str] = None,
        legal_description: Optional[str] = None,
        lessee: Optional[str] = None,
        provider: str = "auto",
    ) -> List[LeaseRecord]:
        criteria = self._search_criteria(state, county, legal_description, owner_name)
        if lessee:
            criteria["lessee"] = lessee
        return self._unsupported_records("leases", criteria, provider)

    def get_title_records(
        self,
        state: str,
        county: str,
        grantor: Optional[str] = None,
        grantee: Optional[str] = None,
        legal_description: Optional[str] = None,
        document_number: Optional[str] = None,
        provider: str = "auto",
    ) -> List[TitleRecord]:
        criteria = self._search_criteria(state, county, legal_description, None)
        criteria.update(
            {
                key: value
                for key, value in {
                    "grantor": grantor,
                    "grantee": grantee,
                    "document_number": document_number,
                }.items()
                if value
            }
        )
        return self._unsupported_records("title", criteria, provider)

    def _get_provider(self, provider_name: str, cfg: Dict[str, Any]) -> Any:
        source = SourceConfig.from_mapping(cfg.get("source"))
        plan = preflight(["ownership"], provider_name, source, self.registry)
        registration = plan.routes["ownership"]
        return registration.factory(source)

    def _select_best_provider(self, cfg: Dict[str, Any]) -> str:
        source = SourceConfig.from_mapping(cfg.get("source"))
        plan = preflight(["ownership"], "auto", source, self.registry)
        return plan.routes["ownership"].name

    def get_valid_data_types(self) -> List[str]:
        return self.VALID_DATA_TYPES.copy()

    def get_valid_providers(self) -> List[str]:
        return [row.name for row in self.registry]

    def get_valid_states(self) -> Dict[str, str]:
        return US_STATE_CODES.copy()
