"""
SodirData router for orchestrating SODIR data collection.

This module follows the BSEE pattern to orchestrate:
- Data collection from SODIR API
- Processing through appropriate processors
- Validation of collected data
- Storage to filesystem
- Generation of analysis-ready datasets
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class SodirData:
    """
    Main orchestrator for SODIR data collection and processing.

    Follows the pattern from BSEE's bsee_data.py router.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize SodirData router with configuration.

        Args:
            config: Configuration dictionary containing API, cache, storage settings
        """
        self.config = config or {}
        self.api_client = None
        self.processors = {}
        self.validator = None
        self.storage = None

        # Statistics tracking
        self.stats = {
            "collections": 0,
            "total_records": 0,
            "errors": 0,
            "validations_failed": 0,
        }

        # Initialize components if config provided
        if config:
            self._initialize_components()

        logger.info("SodirData router initialized")

    def _initialize_components(self):
        """Initialize all components based on configuration."""
        # Initialize API client
        from .api_client import SodirAPIClient

        api_config = self.config.get("api", {})
        self.api_client = SodirAPIClient(
            base_url=api_config.get("base_url", "https://factmaps.sodir.no/api/rest"),
            timeout=api_config.get("timeout", 30),
            rate_limit=api_config.get("rate_limit", 10),
        )

        # Initialize processors
        from .processors import (
            BlockProcessor,
            DiscoveryProcessor,
            FieldProcessor,
            SurveyProcessor,
            WellboreProcessor,
        )

        self.processors = {
            "blocks": BlockProcessor(),
            "wellbores": WellboreProcessor(),
            "fields": FieldProcessor(),
            "discoveries": DiscoveryProcessor(),
            "surveys": SurveyProcessor(),
        }

        # Initialize validator
        from .validators import DataValidator

        self.validator = DataValidator()

        # Initialize storage
        from .storage import DataStorage

        storage_config = self.config.get("storage", {})
        self.storage = DataStorage(storage_config)

    def router(self, cfg: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Route data collection based on configuration (BSEE pattern compatibility).

        Args:
            cfg: Configuration dictionary

        Returns:
            Tuple of (updated configuration, collected data)
        """
        # Update configuration if provided
        if cfg and not self.config:
            self.config = cfg
            self._initialize_components()

        logger.info("Starting SODIR data collection via router")

        # Collect data for specified types
        data_types = cfg.get("data_types", cfg.get("datasets", []))
        collected_data = {}

        for data_type in data_types:
            logger.info(f"Collecting {data_type} data")
            result = self.collect_dataset(data_type)
            if result["status"] == "success":
                collected_data[data_type] = result["data"]
            else:
                logger.error(f"Failed to collect {data_type}: {result.get('error')}")

        return cfg, collected_data

    def collect_dataset(
        self,
        dataset_type: str,
        validate: Optional[bool] = None,
        since: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Collect a single dataset from SODIR.

        Args:
            dataset_type: Type of dataset (blocks, wellbores, fields, etc.)
            validate: Whether to validate collected data
            since: ISO date string for incremental collection
            filters: Additional filters to apply

        Returns:
            Dictionary containing collected data and metadata
        """
        # Initialize components if not already done
        if not self.api_client:
            self._initialize_components()

        # Use config default for validation if not specified
        if validate is None:
            validate = self.config.get("collection", {}).get("validate", True)

        result = {
            "dataset": dataset_type,
            "status": "pending",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "filters": {"since": since} if since else {},
                "validated": validate,
            },
        }

        try:
            # Fetch data from API
            logger.info(f"Collecting {dataset_type} dataset")
            raw_data = self._fetch_data(dataset_type, since, filters)

            if not raw_data:
                result["status"] = "success"
                result["count"] = 0
                result["data"] = []
                return result

            # Process data through appropriate processor
            processed_data = self._process_data(dataset_type, raw_data)

            # Validate if requested
            if validate:
                validation_result = self._validate_data(dataset_type, processed_data)
                result["metadata"]["validation"] = validation_result

                # Filter out invalid records if strict validation
                if self.config.get("collection", {}).get("strict_validation", False):
                    processed_data = [
                        d for d in processed_data if d.get("_valid", True)
                    ]

            result["status"] = "success"
            result["count"] = len(processed_data)
            result["data"] = processed_data

            # Update statistics
            self.stats["collections"] += 1
            self.stats["total_records"] += len(processed_data)

            logger.info(
                f"Successfully collected {len(processed_data)} {dataset_type} records"
            )

        except Exception as e:
            logger.error(f"Error collecting {dataset_type}: {str(e)}")
            result["status"] = "failed"
            result["error"] = str(e)
            self.stats["errors"] += 1

        return result

    def collect_multiple_datasets(
        self, datasets: List[str], validate: bool = True, since: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Collect multiple datasets.

        Args:
            datasets: List of dataset types to collect
            validate: Whether to validate data
            since: ISO date for incremental collection

        Returns:
            Dictionary with results for each dataset
        """
        results = {}

        for dataset in datasets:
            logger.info(f"Collecting dataset: {dataset}")
            results[dataset] = self.collect_dataset(dataset, validate, since)

        return results

    def collect_and_store(
        self, dataset_type: str, validate: bool = True, since: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Collect dataset and store to filesystem.

        Args:
            dataset_type: Type of dataset to collect
            validate: Whether to validate data
            since: ISO date for incremental collection

        Returns:
            Collection result with storage information
        """
        # Collect data
        result = self.collect_dataset(dataset_type, validate, since)

        if result["status"] == "success" and result["count"] > 0 and self.storage:
            # Store data
            try:
                storage_path = self.storage.save(dataset_type, result)
                result["storage"] = {
                    "path": str(storage_path),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                logger.info(f"Stored {dataset_type} data to {storage_path}")
            except Exception as e:
                logger.error(f"Failed to store {dataset_type}: {str(e)}")
                result["storage"] = {"error": str(e)}

        return result

    def _fetch_data(
        self,
        dataset_type: str,
        since: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch raw data from SODIR API.

        Args:
            dataset_type: Type of dataset to fetch
            since: ISO date for incremental fetch
            filters: Additional API filters

        Returns:
            List of raw data records
        """
        # Map dataset type to API method
        api_methods = {
            "blocks": self.api_client.get_blocks,
            "wellbores": self.api_client.get_wellbores,
            "fields": self.api_client.get_fields,
            "discoveries": self.api_client.get_discoveries,
            "surveys": self.api_client.get_surveys,
        }

        if dataset_type not in api_methods:
            raise ValueError(f"Unknown dataset type: {dataset_type}")

        # Prepare API parameters
        params = {}
        if since:
            params["updated_since"] = since
        if filters:
            params.update(filters)

        # Fetch data
        return (
            api_methods[dataset_type](**params)
            if params
            else api_methods[dataset_type]()
        )

    def _process_data(
        self, dataset_type: str, raw_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process raw data through appropriate processor.

        Args:
            dataset_type: Type of dataset
            raw_data: Raw data records from API

        Returns:
            List of processed data records
        """
        if dataset_type not in self.processors:
            logger.warning(f"No processor for {dataset_type}, returning raw data")
            return raw_data

        processor = self.processors[dataset_type]
        return processor.process_batch(raw_data)

    def _validate_data(
        self, dataset_type: str, data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate processed data.

        Args:
            dataset_type: Type of dataset
            data: Processed data records

        Returns:
            Validation result summary
        """
        validation_result = {"valid_count": 0, "invalid_count": 0, "errors": []}

        # Get appropriate validation method
        validation_methods = {
            "fields": self.validate_field,
            "discoveries": self.validate_discovery,
            "surveys": self.validate_survey,
            "blocks": self.validate_block,
            "wellbores": self.validate_wellbore,
        }

        validate_func = validation_methods.get(dataset_type)
        if not validate_func:
            logger.warning(f"No validation method for {dataset_type}")
            validation_result["valid_count"] = len(data)
            return validation_result

        # Validate each record
        for record in data:
            is_valid, errors = validate_func(record)
            if is_valid:
                validation_result["valid_count"] += 1
                record["_valid"] = True
            else:
                validation_result["invalid_count"] += 1
                record["_valid"] = False
                validation_result["errors"].append(
                    {
                        "record": record.get("name", record.get("id", "unknown")),
                        "errors": errors,
                    }
                )

        self.stats["validations_failed"] += validation_result["invalid_count"]

        return validation_result

    def validate_field(self, field_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate field data using the validator."""
        if not self.validator:
            return True, []

        # Convert processed field data back to raw format for validation
        raw_format = {
            "fldName": field_data.get("field_name"),
            "fldDiscoveryYear": field_data.get("discovery_year"),
            "fldProductionStartYear": field_data.get("production_start_year"),
            "fldCessationYear": field_data.get("cessation_year"),
            "fldOriginalReservesOil": field_data.get("original_reserves_oil_mmbbl"),
            "fldRemainingReservesOil": field_data.get("remaining_reserves_oil_mmbbl"),
        }
        return self.validator.validate_field_data(raw_format)

    def validate_discovery(
        self, discovery_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate discovery data using the validator."""
        if not self.validator:
            return True, []

        raw_format = {
            "dscName": discovery_data.get("discovery_name"),
            "dscDiscoveryYear": discovery_data.get("discovery_year"),
            "dscRecoverableOil": discovery_data.get("recoverable_oil_msm3"),
            "dscRecoverableGas": discovery_data.get("recoverable_gas_bsm3"),
            "dscRecoverableNGL": discovery_data.get("recoverable_ngl_msm3"),
            "dscRecoverableCondensate": discovery_data.get(
                "recoverable_condensate_msm3"
            ),
        }
        return self.validator.validate_discovery_data(raw_format)

    def validate_survey(self, survey_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate survey data using the validator."""
        if not self.validator:
            return True, []

        raw_format = {
            "srvName": survey_data.get("survey_name"),
            "srvAcquisitionStartDate": survey_data.get("acquisition_start_date"),
            "srvAcquisitionEndDate": survey_data.get("acquisition_end_date"),
            "srvAreaKm2": survey_data.get("area_km2"),
            "srvStreamerCount": survey_data.get("streamer_count"),
        }
        return self.validator.validate_survey_data(raw_format)

    def validate_block(self, block_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate block data."""
        if not self.validator:
            return True, []

        if not block_data.get("block_name"):
            return False, ["Missing block name"]
        if not self.validator.validate_block_name(block_data["block_name"]):
            return False, [f"Invalid block name format: {block_data['block_name']}"]
        return True, []

    def validate_wellbore(
        self, wellbore_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate wellbore data."""
        if not self.validator:
            return True, []

        if not wellbore_data.get("wellbore_name"):
            return False, ["Missing wellbore name"]
        if not self.validator.validate_wellbore_name(wellbore_data["wellbore_name"]):
            return False, [
                f"Invalid wellbore name format: {wellbore_data['wellbore_name']}"
            ]
        return True, []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get collection statistics.

        Returns:
            Dictionary with collection metrics
        """
        return {
            "collections": self.stats["collections"],
            "total_records": self.stats["total_records"],
            "errors": self.stats["errors"],
            "validations_failed": self.stats["validations_failed"],
            "success_rate": (self.stats["collections"] - self.stats["errors"])
            / max(self.stats["collections"], 1),
        }

    def generate_validation_report(
        self, data: List[Dict[str, Any]], dataset_type: str
    ) -> Dict[str, Any]:
        """
        Generate detailed validation report for a dataset.

        Args:
            data: Data to validate
            dataset_type: Type of dataset

        Returns:
            Detailed validation report
        """
        validation_result = self._validate_data(dataset_type, data)

        return {
            "dataset": dataset_type,
            "timestamp": datetime.utcnow().isoformat(),
            "total_records": len(data),
            "valid_records": validation_result["valid_count"],
            "invalid_records": validation_result["invalid_count"],
            "validation_rate": validation_result["valid_count"] / max(len(data), 1),
            "errors": validation_result["errors"],
        }
