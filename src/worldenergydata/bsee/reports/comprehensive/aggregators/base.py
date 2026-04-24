"""
Abstract base class for data aggregation
Defines the interface for all aggregator implementations
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List

from ..models import HierarchyLevel, OrganizationalUnit, ProductionMetrics

logger = logging.getLogger(__name__)


class DataAggregator(ABC):
    """Abstract base class for data aggregation"""

    def __init__(self):
        """Initialize aggregator"""
        self.cached_results = {}
        self.validation_errors = []
        self.metrics_cache = {}

    @abstractmethod
    def aggregate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate data at specific hierarchy level

        Args:
            data: Dictionary containing organizational unit data

        Returns:
            Aggregated metrics dictionary
        """
        pass

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate input data before aggregation

        Args:
            data: Data to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    def calculate_metrics(self, data: Dict[str, Any]) -> ProductionMetrics:
        """
        Calculate production metrics from aggregated data

        Args:
            data: Aggregated data

        Returns:
            ProductionMetrics object
        """
        pass

    @abstractmethod
    def get_hierarchy_level(self) -> HierarchyLevel:
        """
        Get the hierarchy level this aggregator operates on

        Returns:
            HierarchyLevel enum value
        """
        pass

    def clear_cache(self):
        """Clear cached results"""
        self.cached_results = {}
        self.metrics_cache = {}

    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors"""
        return self.validation_errors

    def add_validation_error(self, error: str):
        """Add validation error"""
        self.validation_errors.append(error)
        logger.warning(f"Validation error: {error}")

    def clear_validation_errors(self):
        """Clear validation errors"""
        self.validation_errors = []

    def stream_data(
        self, data_source: Any, chunk_size: int = 1000
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream data for large datasets

        Args:
            data_source: Source of data to stream
            chunk_size: Number of records per chunk

        Yields:
            Chunks of data for processing
        """
        # Base implementation - can be overridden by subclasses
        if hasattr(data_source, "__iter__"):
            chunk = []
            for item in data_source:
                chunk.append(item)
                if len(chunk) >= chunk_size:
                    yield {"chunk": chunk}
                    chunk = []
            if chunk:
                yield {"chunk": chunk}

    def aggregate_revenue_costs(
        self, unit: OrganizationalUnit, price_deck: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Aggregate revenue and cost calculations with enhanced economic metrics

        Args:
            unit: Organizational unit to aggregate
            price_deck: Pricing information with oil/gas prices and cost parameters

        Returns:
            Dictionary with comprehensive revenue and cost metrics
        """
        # Get production data
        metrics = unit.metrics if hasattr(unit, "metrics") else {}
        production = getattr(unit, "total_production", {})

        oil_bbls = metrics.get("oil_bbls", 0) or production.get("oil_bbls", 0)
        gas_mcf = metrics.get("gas_mcf", 0) or production.get("gas_mcf", 0)
        water_bbls = metrics.get("water_bbls", 0) or production.get("water_bbls", 0)

        # Pricing parameters
        oil_price = price_deck.get("oil", 75.0)
        gas_price = price_deck.get("gas", 3.5)
        ngl_price = price_deck.get("ngl", 25.0)

        # Cost parameters
        operating_cost_per_bbl = price_deck.get("operating_cost_per_bbl", 12.5)
        water_disposal_cost = price_deck.get("water_disposal_cost_per_bbl", 2.0)
        gas_processing_cost = price_deck.get("gas_processing_cost_per_mcf", 0.5)
        royalty_rate = price_deck.get("royalty_rate", 0.1875)
        severance_tax_rate = price_deck.get("severance_tax_rate", 0.05)

        # Revenue calculations
        oil_revenue = oil_bbls * oil_price
        gas_revenue = gas_mcf * gas_price
        ngl_revenue = gas_mcf * 0.01 * ngl_price  # Assume 1% NGL yield from gas
        gross_revenue = oil_revenue + gas_revenue + ngl_revenue

        # Operating costs
        oil_operating_cost = oil_bbls * operating_cost_per_bbl
        water_disposal_cost_total = water_bbls * water_disposal_cost
        gas_processing_cost_total = gas_mcf * gas_processing_cost
        total_operating_cost = (
            oil_operating_cost + water_disposal_cost_total + gas_processing_cost_total
        )

        # Government take
        royalties = gross_revenue * royalty_rate
        severance_tax = gross_revenue * severance_tax_rate
        total_government_take = royalties + severance_tax

        # Net calculations
        net_revenue = gross_revenue - total_government_take
        operating_income = net_revenue - total_operating_cost

        # Performance metrics
        netback_per_bbl = operating_income / oil_bbls if oil_bbls > 0 else 0
        operating_margin = operating_income / gross_revenue if gross_revenue > 0 else 0

        return {
            "gross_revenue": gross_revenue,
            "oil_revenue": oil_revenue,
            "gas_revenue": gas_revenue,
            "ngl_revenue": ngl_revenue,
            "total_operating_cost": total_operating_cost,
            "oil_operating_cost": oil_operating_cost,
            "water_disposal_cost": water_disposal_cost_total,
            "gas_processing_cost": gas_processing_cost_total,
            "royalties": royalties,
            "severance_tax": severance_tax,
            "total_government_take": total_government_take,
            "net_revenue": net_revenue,
            "operating_income": operating_income,
            "netback_per_bbl": netback_per_bbl,
            "operating_margin": operating_margin,
            "oil_price_realized": oil_price,
            "gas_price_realized": gas_price,
        }

    def aggregate_hierarchical_economics(
        self, hierarchy: Dict[str, Any], price_deck: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Aggregate economics across entire hierarchy

        Args:
            hierarchy: Dictionary with blocks, fields, leases, wells
            price_deck: Pricing information

        Returns:
            Hierarchical economic aggregation
        """
        economic_summary = {
            "by_block": {},
            "by_field": {},
            "by_lease": {},
            "totals": {
                "gross_revenue": 0,
                "operating_income": 0,
                "royalties": 0,
                "wells": 0,
            },
        }

        # Aggregate by lease first
        for lease_id, lease in hierarchy.get("leases", {}).items():
            lease_economics = self.aggregate_revenue_costs(lease, price_deck)
            economic_summary["by_lease"][lease_id] = lease_economics
            economic_summary["totals"]["gross_revenue"] += lease_economics[
                "gross_revenue"
            ]
            economic_summary["totals"]["operating_income"] += lease_economics[
                "operating_income"
            ]
            economic_summary["totals"]["royalties"] += lease_economics["royalties"]

        # Aggregate by field
        for field_id, field in hierarchy.get("fields", {}).items():
            field_economics = self.aggregate_revenue_costs(field, price_deck)
            economic_summary["by_field"][field_id] = field_economics

        # Aggregate by block
        for block_id, block in hierarchy.get("blocks", {}).items():
            block_economics = self.aggregate_revenue_costs(block, price_deck)
            economic_summary["by_block"][block_id] = block_economics

        # Count total wells
        economic_summary["totals"]["wells"] = len(hierarchy.get("wells", {}))

        return economic_summary

    def validate_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data quality and completeness

        Args:
            data: Data to validate

        Returns:
            Quality metrics dictionary
        """
        quality_metrics = {
            "completeness": 0.0,
            "accuracy": 0.0,
            "consistency": 0.0,
            "issues": [],
        }

        # Check completeness
        required_fields = self._get_required_fields()
        present_fields = sum(
            1 for field in required_fields if field in data and data[field] is not None
        )
        quality_metrics["completeness"] = (
            present_fields / len(required_fields) if required_fields else 0
        )

        # Check for data anomalies
        if "oil_bbls" in data and data["oil_bbls"] < 0:
            quality_metrics["issues"].append("Negative oil production detected")

        if "gas_mcf" in data and data["gas_mcf"] < 0:
            quality_metrics["issues"].append("Negative gas production detected")

        # Overall accuracy score
        quality_metrics["accuracy"] = 1.0 - (len(quality_metrics["issues"]) * 0.1)
        quality_metrics["accuracy"] = max(0, quality_metrics["accuracy"])

        return quality_metrics

    def _get_required_fields(self) -> List[str]:
        """Get list of required fields for validation"""
        # Can be overridden by subclasses
        return ["oil_bbls", "gas_mcf", "water_bbls"]

    def aggregate_with_streaming(
        self, data_source: Any, chunk_size: int = 1000, memory_limit_mb: int = 500
    ) -> Dict[str, Any]:
        """
        Aggregate data using streaming for large datasets (>1GB)

        Args:
            data_source: Source of data (file path, iterator, or data loader)
            chunk_size: Size of chunks to process
            memory_limit_mb: Memory limit in megabytes

        Returns:
            Aggregated results with streaming statistics
        """
        import gc

        import psutil

        # Initialize results
        total_results = {
            "oil_bbls": 0,
            "gas_mcf": 0,
            "water_bbls": 0,
            "record_count": 0,
            "chunks_processed": 0,
            "memory_peak_mb": 0,
            "processing_time_sec": 0,
        }

        # Track memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        peak_memory = initial_memory

        start_time = datetime.now()

        try:
            # Stream and process data
            for chunk_num, chunk in enumerate(
                self.stream_data(data_source, chunk_size), 1
            ):
                # Check memory usage
                current_memory = process.memory_info().rss / 1024 / 1024
                if current_memory - initial_memory > memory_limit_mb:
                    logger.warning(
                        f"Memory limit exceeded: {current_memory:.1f}MB used"
                    )
                    # Force garbage collection
                    gc.collect()

                    # Re-check after GC
                    current_memory = process.memory_info().rss / 1024 / 1024
                    if current_memory - initial_memory > memory_limit_mb:
                        logger.error(
                            f"Memory limit still exceeded after GC: {current_memory:.1f}MB"
                        )
                        break

                peak_memory = max(peak_memory, current_memory)

                # Process chunk
                chunk_result = self.aggregate(chunk)

                # Accumulate results
                for key in ["oil_bbls", "gas_mcf", "water_bbls"]:
                    if key in chunk_result:
                        total_results[key] += chunk_result[key]

                total_results["record_count"] += len(chunk.get("chunk", []))
                total_results["chunks_processed"] = chunk_num

                # Clear cache periodically
                if chunk_num % 10 == 0:
                    self.clear_cache()
                    gc.collect()

                # Log progress
                if chunk_num % 100 == 0:
                    logger.info(
                        f"Processed {chunk_num} chunks, {total_results['record_count']} records"
                    )

        except Exception as e:
            logger.error(f"Error during streaming aggregation: {e}")
            raise

        finally:
            # Final cleanup
            self.clear_cache()
            gc.collect()

        # Calculate final statistics
        end_time = datetime.now()
        total_results["memory_peak_mb"] = peak_memory - initial_memory
        total_results["processing_time_sec"] = (end_time - start_time).total_seconds()

        logger.info(
            f"Streaming aggregation complete: {total_results['chunks_processed']} chunks, "
            f"{total_results['record_count']} records in {total_results['processing_time_sec']:.1f}s"  # noqa: E501
        )

        return total_results

    def stream_large_file(
        self, file_path: Path, file_type: str = "csv", chunk_size: int = 10000
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream large files (>1GB) efficiently

        Args:
            file_path: Path to large file
            file_type: Type of file (csv, json, pickle)
            chunk_size: Records per chunk

        Yields:
            Chunks of data
        """
        import pickle

        import pandas as pd

        if file_type == "csv":
            # Stream CSV file
            for chunk_df in pd.read_csv(file_path, chunksize=chunk_size):
                yield {"chunk": chunk_df.to_dict("records")}

        elif file_type == "json":
            # Stream JSON lines file
            import json

            chunk = []
            with open(file_path, "r") as f:
                for line in f:
                    chunk.append(json.loads(line))
                    if len(chunk) >= chunk_size:
                        yield {"chunk": chunk}
                        chunk = []
                if chunk:
                    yield {"chunk": chunk}

        elif file_type == "pickle":
            # Stream pickle file (assumes list of records)
            with open(file_path, "rb") as f:
                try:
                    data = pickle.load(f)
                    if isinstance(data, list):
                        for i in range(0, len(data), chunk_size):
                            yield {"chunk": data[i : i + chunk_size]}
                    else:
                        yield {"chunk": [data]}
                except Exception as e:
                    logger.error(f"Error streaming pickle file: {e}")
                    raise

        else:
            raise ValueError(f"Unsupported file type: {file_type}")
