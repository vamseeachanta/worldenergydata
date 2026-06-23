# ABOUTME: Main Landman module router implementation following established patterns
# ABOUTME: Orchestrates mineral ownership and lease data collection from multiple providers

"""
Main Landman module router implementation.

This module follows the established architectural pattern to provide a consistent
interface for mineral ownership and lease data collection within the WorldEnergyData framework.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .exceptions import LandmanError
from .exceptions import ProviderError as LandmanProviderError
from .models import LeaseRecord, OwnerSearchResult, TitleRecord
from .validators import US_STATE_CODES, LandmanDataValidator


class LandmanValidationError(LandmanError):
    """Validation error for Landman module."""

    default_code = "LANDMAN_VALIDATION_ERROR"

    @classmethod
    def invalid_state_code(cls, state_code: str) -> "LandmanValidationError":
        """Create error for invalid state code."""
        return cls(
            message=f"Invalid state code: {state_code}",
            error_code="LANDMAN_INVALID_STATE",
            details={"state_code": state_code},
        )

    @classmethod
    def invalid_legal_description(
        cls, legal_description: str, reason: str = ""
    ) -> "LandmanValidationError":
        """Create error for invalid legal description."""
        msg = f"Invalid legal description: {legal_description}"
        if reason:
            msg += f" - {reason}"
        return cls(
            message=msg,
            error_code="LANDMAN_INVALID_LEGAL_DESC",
            details={"legal_description": legal_description},
        )


logger = logging.getLogger(__name__)


class Landman:
    """
    Main Landman module class implementing the router pattern.

    This class orchestrates mineral ownership and lease data collection from
    multiple providers including public county records and commercial services.
    """

    # Valid data types for Landman module
    VALID_DATA_TYPES = [
        "ownership",
        "leases",
        "title",
        "deeds",
        "mortgages",
        "assignments",
        "all",
    ]

    # Supported providers
    VALID_PROVIDERS = [
        "county_records",  # Public county clerk records
        "drillinginfo",  # Enverus/DrillingInfo (subscription)
        "txdir",  # Texas Direct (subscription)
        "ogorgs",  # Oil & Gas OGS
        "auto",  # Auto-select best available
    ]

    def __init__(self):
        """Initialize Landman module."""
        self.module_name = "landman"
        self.validator = LandmanDataValidator()
        self._providers: Dict[str, Any] = {}
        self._initialize_components()

    def _initialize_components(self):
        """Initialize provider components lazily."""
        # Providers will be imported when needed to avoid circular imports
        pass

    def router(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main router method following established pattern.

        Args:
            cfg: Configuration dictionary containing:
                - module: Module name (should be 'landman')
                - data_types: List of data types to collect
                - state: State code for search
                - county: County name for search
                - provider: Provider to use (default: 'auto')
                - search: Search criteria (owner_name, legal_description, etc.)
                - output: Output configuration (directory, format)

        Returns:
            Updated configuration dictionary with results

        Raises:
            LandmanValidationError: If configuration is invalid
            LandmanProviderError: If provider fails
        """
        # Validate configuration first
        self._validate_config(cfg)

        try:
            # Initialize module section in config
            if "basename" not in cfg:
                cfg["basename"] = self.module_name

            cfg[cfg["basename"]] = {}
            cfg[cfg["basename"]].update({"data": cfg.get("data", {}).copy()})
            cfg[cfg["basename"]].update({"search": cfg.get("search", {}).copy()})

            # Get provider instance
            provider_name = cfg.get("provider", "auto")
            provider = self._get_provider(provider_name, cfg)

            # Route to data collection
            logger.info(
                f"Starting Landman data collection for types: {cfg.get('data_types', ['all'])}"
            )

            data = self._collect_data(cfg, provider)

            # Store results
            cfg[cfg["basename"]]["status"] = "completed"
            cfg[cfg["basename"]]["data_collected"] = list(data.keys()) if data else []
            cfg[cfg["basename"]]["record_count"] = sum(
                len(v) if isinstance(v, list) else 1 for v in data.values()
            )

            # Add results to config
            if data:
                cfg[cfg["basename"]]["results"] = data

            logger.info("Landman module processing completed successfully")
            return cfg

        except LandmanError:
            raise
        except Exception as e:
            logger.error(f"Error in Landman router: {str(e)}")
            if "basename" in cfg and cfg["basename"] in cfg:
                cfg[cfg["basename"]]["status"] = "error"
                cfg[cfg["basename"]]["error"] = str(e)
            raise LandmanError(
                message=f"Landman router failed: {str(e)}",
                code="LANDMAN_ROUTER_ERROR",
                cause=e,
            )

    def _validate_config(self, cfg: Dict[str, Any]) -> None:
        """
        Validate configuration dictionary.

        Args:
            cfg: Configuration dictionary to validate

        Raises:
            LandmanValidationError: If configuration is invalid
        """
        if not cfg:
            raise LandmanValidationError(
                message="Configuration cannot be empty",
                code="LANDMAN_CONFIG_EMPTY",
            )

        # Validate module name if specified
        if "module" in cfg and cfg["module"] != self.module_name:
            logger.warning(
                f"Module mismatch: expected '{self.module_name}', got '{cfg['module']}'"
            )

        # Validate data types if specified
        if "data_types" in cfg:
            invalid_types = [
                dt for dt in cfg["data_types"] if dt not in self.VALID_DATA_TYPES
            ]
            if invalid_types:
                raise LandmanValidationError(
                    message=f"Invalid data types: {invalid_types}. Valid types: {self.VALID_DATA_TYPES}",  # noqa: E501
                    code="LANDMAN_INVALID_DATA_TYPES",
                    context={"invalid_types": invalid_types},
                )

        # Validate provider if specified
        if "provider" in cfg and cfg["provider"] not in self.VALID_PROVIDERS:
            raise LandmanValidationError(
                message=f"Invalid provider: {cfg['provider']}. Valid providers: {self.VALID_PROVIDERS}",  # noqa: E501
                code="LANDMAN_INVALID_PROVIDER",
                context={"provider": cfg["provider"]},
            )

        # Validate state if specified
        if "state" in cfg:
            is_valid, error = self.validator.validate_state_code(cfg["state"])
            if not is_valid:
                raise LandmanValidationError.invalid_state_code(cfg["state"])

        # Validate search criteria if specified
        if "search" in cfg:
            search = cfg["search"]
            if "legal_description" in search:
                is_valid, error = self.validator.validate_legal_description(
                    search["legal_description"]
                )
                if not is_valid:
                    raise LandmanValidationError.invalid_legal_description(
                        search["legal_description"], error or ""
                    )

            if "owner_name" in search:
                is_valid, error = self.validator.validate_owner_name(
                    search["owner_name"]
                )
                if not is_valid:
                    raise LandmanValidationError(
                        message=f"Invalid owner name: {error}",
                        code="LANDMAN_INVALID_OWNER_NAME",
                    )

        logger.debug("Configuration validated successfully")

    def _get_provider(self, provider_name: str, cfg: Dict[str, Any]) -> Any:
        """
        Get or create provider instance.

        Args:
            provider_name: Name of the provider
            cfg: Configuration dictionary

        Returns:
            Provider instance

        Raises:
            LandmanProviderError: If provider cannot be initialized
        """
        if provider_name == "auto":
            # Select best available provider based on state and configuration
            provider_name = self._select_best_provider(cfg)

        if provider_name not in self._providers:
            try:
                if provider_name == "county_records":
                    from .providers.county_records import CountyRecordsProvider

                    self._providers[provider_name] = CountyRecordsProvider(cfg)
                else:
                    # Future providers will be added here
                    raise LandmanProviderError.unavailable(
                        provider_name,
                        f"Provider '{provider_name}' is not yet implemented",
                    )
            except ImportError as e:
                raise LandmanProviderError.unavailable(
                    provider_name,
                    f"Failed to import provider: {str(e)}",
                    cause=e,
                )

        return self._providers[provider_name]

    def _select_best_provider(self, cfg: Dict[str, Any]) -> str:
        """
        Select the best available provider based on configuration.

        Args:
            cfg: Configuration dictionary

        Returns:
            Provider name to use
        """
        # For now, default to county_records as it's the free option
        # Future: Check for subscription credentials and select accordingly
        return "county_records"

    def _collect_data(self, cfg: Dict[str, Any], provider: Any) -> Dict[str, Any]:
        """
        Collect data using the specified provider.

        Args:
            cfg: Configuration dictionary
            provider: Provider instance to use

        Returns:
            Dictionary of collected data
        """
        data: Dict[str, Any] = {}
        data_types = cfg.get("data_types", ["all"])

        if "all" in data_types:
            data_types = ["ownership", "leases", "title"]

        for data_type in data_types:
            try:
                if data_type == "ownership":
                    data["ownership"] = provider.search_ownership(cfg.get("search", {}))
                elif data_type == "leases":
                    data["leases"] = provider.search_leases(cfg.get("search", {}))
                elif data_type == "title":
                    data["title"] = provider.search_title(cfg.get("search", {}))
                elif data_type == "deeds":
                    data["deeds"] = provider.search_deeds(cfg.get("search", {}))
                elif data_type == "mortgages":
                    data["mortgages"] = provider.search_mortgages(cfg.get("search", {}))
                elif data_type == "assignments":
                    data["assignments"] = provider.search_assignments(
                        cfg.get("search", {})
                    )
            except Exception as e:
                logger.warning(f"Failed to collect {data_type} data: {str(e)}")
                data[f"{data_type}_error"] = str(e)

        return data

    def search_ownership(
        self,
        state: str,
        county: str,
        legal_description: Optional[str] = None,
        owner_name: Optional[str] = None,
        provider: str = "auto",
    ) -> OwnerSearchResult:
        """
        Search for mineral ownership records.

        Args:
            state: 2-letter state code
            county: County name
            legal_description: Legal description to search
            owner_name: Owner name to search
            provider: Provider to use

        Returns:
            OwnerSearchResult with found records
        """
        start_time = datetime.now()
        search_id = str(uuid.uuid4())

        # Validate inputs
        is_valid, error = self.validator.validate_state_code(state)
        if not is_valid:
            raise LandmanValidationError.invalid_state_code(state)

        is_valid, error = self.validator.validate_county_name(county, state)
        if not is_valid:
            raise LandmanValidationError(
                message=f"Invalid county: {error}",
                code="LANDMAN_INVALID_COUNTY",
            )

        if legal_description:
            is_valid, error = self.validator.validate_legal_description(
                legal_description
            )
            if not is_valid:
                raise LandmanValidationError.invalid_legal_description(
                    legal_description, error or ""
                )

        search_criteria = {
            "state": state,
            "county": county,
        }
        if legal_description:
            search_criteria["legal_description"] = legal_description
        if owner_name:
            search_criteria["owner_name"] = owner_name

        cfg = {
            "state": state,
            "county": county,
            "provider": provider,
            "search": search_criteria,
        }

        try:
            provider_instance = self._get_provider(provider, cfg)
            ownership_records = provider_instance.search_ownership(search_criteria)

            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return OwnerSearchResult(
                search_id=search_id,
                search_criteria=search_criteria,
                state=state,
                county=county,
                owner_name=owner_name,
                legal_description=legal_description,
                ownership_records=ownership_records,
                provider=provider,
                search_duration_ms=elapsed_ms,
            )

        except LandmanError:
            raise
        except Exception as e:
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            result = OwnerSearchResult(
                search_id=search_id,
                search_criteria=search_criteria,
                state=state,
                county=county,
                owner_name=owner_name,
                legal_description=legal_description,
                provider=provider,
                search_duration_ms=elapsed_ms,
            )
            result.add_error(f"Search failed: {str(e)}")
            return result

    def get_lease_records(
        self,
        state: str,
        county: str,
        owner_name: Optional[str] = None,
        legal_description: Optional[str] = None,
        lessee: Optional[str] = None,
        provider: str = "auto",
    ) -> List[LeaseRecord]:
        """
        Get lease records for specified criteria.

        Args:
            state: 2-letter state code
            county: County name
            owner_name: Lessor/owner name to search
            legal_description: Legal description to search
            lessee: Lessee/operator name to search
            provider: Provider to use

        Returns:
            List of LeaseRecord objects
        """
        # Validate inputs
        is_valid, _ = self.validator.validate_state_code(state)
        if not is_valid:
            raise LandmanValidationError.invalid_state_code(state)

        search_criteria = {
            "state": state,
            "county": county,
        }
        if owner_name:
            search_criteria["owner_name"] = owner_name
        if legal_description:
            search_criteria["legal_description"] = legal_description
        if lessee:
            search_criteria["lessee"] = lessee

        cfg = {
            "state": state,
            "county": county,
            "provider": provider,
            "search": search_criteria,
        }

        provider_instance = self._get_provider(provider, cfg)
        return provider_instance.search_leases(search_criteria)

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
        """
        Get title/deed records for specified criteria.

        Args:
            state: 2-letter state code
            county: County name
            grantor: Grantor/seller name to search
            grantee: Grantee/buyer name to search
            legal_description: Legal description to search
            document_number: Specific document number
            provider: Provider to use

        Returns:
            List of TitleRecord objects
        """
        # Validate inputs
        is_valid, _ = self.validator.validate_state_code(state)
        if not is_valid:
            raise LandmanValidationError.invalid_state_code(state)

        search_criteria = {
            "state": state,
            "county": county,
        }
        if grantor:
            search_criteria["grantor"] = grantor
        if grantee:
            search_criteria["grantee"] = grantee
        if legal_description:
            search_criteria["legal_description"] = legal_description
        if document_number:
            search_criteria["document_number"] = document_number

        cfg = {
            "state": state,
            "county": county,
            "provider": provider,
            "search": search_criteria,
        }

        provider_instance = self._get_provider(provider, cfg)
        return provider_instance.search_title(search_criteria)

    def get_valid_data_types(self) -> List[str]:
        """Return list of valid data types."""
        return self.VALID_DATA_TYPES.copy()

    def get_valid_providers(self) -> List[str]:
        """Return list of valid providers."""
        return self.VALID_PROVIDERS.copy()

    def get_valid_states(self) -> Dict[str, str]:
        """Return dictionary of valid US state codes."""
        return US_STATE_CODES.copy()
