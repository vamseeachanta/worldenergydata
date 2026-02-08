"""
Performance-Enhanced ReportController with Caching and Parallel Processing

This enhanced controller integrates high-performance optimizations:
- Redis-like caching for aggregated metrics
- Parallel processing for organizational units
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .aggregators.block_aggregator_enhanced import BlockAggregator
from .aggregators.field_aggregator_enhanced import FieldAggregator
from .aggregators.lease_aggregator_enhanced import LeaseAggregator

# Import existing components
from .controller_enhanced import (
    ReportConfiguration,
    ReportController,
    ReportParameters,
    ReportType,
)

# Import performance optimization modules
from .performance.cache import CachedAggregator, CacheManager
from .performance.parallel_processor import (
    BatchProcessor,
    ParallelProcessor,
    ProcessingResult,
)

logger = logging.getLogger(__name__)


@dataclass
class PerformanceConfiguration:
    """Performance optimization configuration"""

    # Cache settings
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    cache_max_size_mb: int = 500

    # Parallel processing settings
    parallel_enabled: bool = True
    max_workers: Optional[int] = None  # None = CPU count
    use_threads: bool = False  # False = use processes
    batch_size: int = 1000

    # Memory management
    max_memory_mb: float = 2000
    enable_memory_monitoring: bool = True

    # Performance monitoring
    enable_profiling: bool = False
    log_performance_metrics: bool = True


class PerformanceReportController(ReportController):
    """
    Enhanced ReportController with performance optimizations.

    Inherits from base ReportController and adds:
    - Integrated caching system
    - Parallel processing capabilities
    - Performance monitoring
    """

    def __init__(
        self,
        config_file: Optional[Path] = None,
        perf_config: Optional[PerformanceConfiguration] = None,
    ):
        """
        Initialize performance-enhanced controller.

        Args:
            config_file: Configuration file path
            perf_config: Performance configuration
        """
        super().__init__(config_file)

        # Initialize performance configuration
        self.perf_config = perf_config or PerformanceConfiguration()

        # Initialize performance components
        self.cache_manager = CacheManager() if self.perf_config.cache_enabled else None
        self.parallel_processor = (
            ParallelProcessor(
                max_workers=self.perf_config.max_workers,
                use_threads=self.perf_config.use_threads,
            )
            if self.perf_config.parallel_enabled
            else None
        )

        # Initialize cached aggregators
        self._initialize_cached_aggregators()

        # Performance metrics
        self.performance_metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "parallel_tasks": 0,
            "total_processing_time": 0,
        }

    def _initialize_cached_aggregators(self):
        """Initialize aggregators with caching wrapper."""
        # Create base aggregators
        block_agg = BlockAggregator()
        field_agg = FieldAggregator()
        lease_agg = LeaseAggregator()

        if self.cache_manager:
            # Wrap aggregators with caching
            cache = self.cache_manager.get_cache("aggregations")
            self.block_aggregator = CachedAggregator(block_agg, cache)
            self.field_aggregator = CachedAggregator(field_agg, cache)
            self.lease_aggregator = CachedAggregator(lease_agg, cache)
        else:
            # Use regular aggregators
            self.block_aggregator = block_agg
            self.field_aggregator = field_agg
            self.lease_aggregator = lease_agg

    def generate_report(
        self, config: ReportConfiguration, params: ReportParameters
    ) -> Any:
        """
        Generate report with performance optimizations.

        Args:
            config: Report configuration
            params: Report parameters

        Returns:
            Generated report data
        """
        start_time = time.time()

        # Check cache first if enabled
        if self.cache_manager:
            cache_key = self._generate_cache_key(config, params)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                self.performance_metrics["cache_hits"] += 1
                logger.info(f"Cache hit for report: {config.entity_name}")
                return cached_result
            self.performance_metrics["cache_misses"] += 1

        try:
            # Use parallel processing if enabled and beneficial
            if self._should_use_parallel_processing(config):
                result = self._generate_report_parallel(config, params)
            else:
                result = super().generate_report(config, params)

            # Cache the result if caching is enabled
            if self.cache_manager and result.get("status") == "success":
                self._cache_result(cache_key, result)

            # Update performance metrics
            processing_time = time.time() - start_time
            self.performance_metrics["total_processing_time"] += processing_time

            if self.perf_config.log_performance_metrics:
                logger.info(
                    f"Report generated in {processing_time:.2f}s for {config.entity_name}"
                )

            return result

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {
                "status": "error",
                "report_type": config.report_type.value,
                "entity": config.entity_name,
                "error": str(e),
            }

    def _generate_report_parallel(
        self, config: ReportConfiguration, params: ReportParameters
    ) -> Dict[str, Any]:
        """
        Generate report using parallel processing.

        Args:
            config: Report configuration
            params: Report parameters

        Returns:
            Generated report data
        """
        logger.info(f"Using parallel processing for {config.report_type.value} report")
        self.performance_metrics["parallel_tasks"] += 1

        # Load data (this could also be parallelized for multiple sources)
        data = self._load_data_for_report(config)

        # Process hierarchy in parallel
        if config.report_type == ReportType.BLOCK:
            return self._generate_block_report_parallel(config, params, data)
        elif config.report_type == ReportType.FIELD:
            return self._generate_field_report_parallel(config, params, data)
        elif config.report_type == ReportType.LEASE:
            return self._generate_lease_report_parallel(config, params, data)
        else:
            return self._generate_well_report_parallel(config, params, data)

    def _generate_block_report_parallel(
        self, config: ReportConfiguration, params: ReportParameters, data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate block report with parallel processing."""
        # Process all fields within the block in parallel
        fields = data["field"].unique() if "field" in data else []

        # Use parallel processor to aggregate fields
        field_results = self.parallel_processor.process_fields_parallel(data, fields)

        # Aggregate field results to block level
        block_metrics = self._aggregate_results_to_block(field_results)

        return {
            "status": "success",
            "report_type": "block",
            "entity": config.entity_name,
            "data": {"metrics": block_metrics, "field_details": field_results},
            "parameters": params.__dict__,
            "generated_at": datetime.now().isoformat(),
            "performance": {
                "parallel_processing": True,
                "fields_processed": len(fields),
            },
        }

    def _generate_field_report_parallel(
        self, config: ReportConfiguration, params: ReportParameters, data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate field report with parallel processing."""
        # Process all leases within the field in parallel
        leases = data["lease"].unique() if "lease" in data else []

        # Use parallel processor to aggregate leases
        with self.parallel_processor.get_executor() as executor:
            futures = {}
            for lease in leases:
                lease_data = data[data["lease"] == lease]
                future = executor.submit(self.lease_aggregator.aggregate, lease_data)
                futures[future] = lease

            lease_results = {}
            for future in futures:
                lease_id = futures[future]
                try:
                    lease_results[lease_id] = future.result(timeout=30)
                except Exception as e:
                    logger.error(f"Failed to process lease {lease_id}: {e}")
                    lease_results[lease_id] = {"error": str(e)}

        # Aggregate lease results to field level
        field_metrics = self._aggregate_lease_results(lease_results)

        return {
            "status": "success",
            "report_type": "field",
            "entity": config.entity_name,
            "data": {"metrics": field_metrics, "lease_details": lease_results},
            "parameters": params.__dict__,
            "generated_at": datetime.now().isoformat(),
            "performance": {
                "parallel_processing": True,
                "leases_processed": len(leases),
            },
        }

    def _generate_lease_report_parallel(
        self, config: ReportConfiguration, params: ReportParameters, data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate lease report with parallel processing."""
        # Process all wells within the lease in parallel
        wells = data["well_id"].unique() if "well_id" in data else []

        # Process wells in batches for efficiency
        batch_processor = BatchProcessor(
            batch_size=self.perf_config.batch_size,
            max_workers=self.perf_config.max_workers,
        )

        def process_well_batch(batch_data):
            """Process a batch of wells."""
            results = {}
            for well_id in batch_data["well_id"].unique():
                well_data = batch_data[batch_data["well_id"] == well_id]
                results[well_id] = {
                    "oil_volume": (
                        well_data["oil_volume_bbl"].sum()
                        if "oil_volume_bbl" in well_data
                        else 0
                    ),
                    "gas_volume": (
                        well_data["gas_volume_mcf"].sum()
                        if "gas_volume_mcf" in well_data
                        else 0
                    ),
                    "production_days": (
                        well_data["production_days"].sum()
                        if "production_days" in well_data
                        else 0
                    ),
                }
            return results

        # Process well data in batches
        batch_results = batch_processor.process_dataframe_batches(
            data, process_well_batch
        )

        # Combine batch results
        well_results = {}
        for batch in batch_results:
            if batch:
                well_results.update(batch)

        # Aggregate well results to lease level
        lease_metrics = self._aggregate_well_results(well_results)

        return {
            "status": "success",
            "report_type": "lease",
            "entity": config.entity_name,
            "data": {"metrics": lease_metrics, "well_details": well_results},
            "parameters": params.__dict__,
            "generated_at": datetime.now().isoformat(),
            "performance": {
                "parallel_processing": True,
                "wells_processed": len(wells),
                "batch_size": self.perf_config.batch_size,
            },
        }

    def _generate_well_report_parallel(
        self, config: ReportConfiguration, params: ReportParameters, data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate well report (no parallelization needed for single well)."""
        # For single well, use regular processing
        return super()._generate_well_report(config, params)

    def _should_use_parallel_processing(self, config: ReportConfiguration) -> bool:
        """
        Determine if parallel processing should be used.

        Args:
            config: Report configuration

        Returns:
            True if parallel processing should be used
        """
        if not self.perf_config.parallel_enabled or not self.parallel_processor:
            return False

        # Use parallel processing for higher-level reports
        if config.report_type in [ReportType.BLOCK, ReportType.FIELD]:
            return True

        # Use parallel processing for lease reports with many wells
        if config.report_type == ReportType.LEASE:
            # Could check data size here
            return True

        return False

    def _generate_cache_key(
        self, config: ReportConfiguration, params: ReportParameters
    ) -> str:
        """
        Generate cache key for report.

        Args:
            config: Report configuration
            params: Report parameters

        Returns:
            Cache key string
        """
        cache_params = {
            "report_type": config.report_type.value,
            "entity": config.entity_name,
            "date_range": f"{config.date_range[0]}_{config.date_range[1]}",
            "params_hash": hashlib.md5(
                json.dumps(params.__dict__, sort_keys=True).encode()
            ).hexdigest()[:8],
        }

        cache = self.cache_manager.get_cache("reports")
        return cache.generate_complex_key(**cache_params)

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get report from cache.

        Args:
            cache_key: Cache key

        Returns:
            Cached report or None
        """
        cache = self.cache_manager.get_cache("reports")
        return cache.get(cache_key)

    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """
        Cache report result.

        Args:
            cache_key: Cache key
            result: Report result to cache
        """
        cache = self.cache_manager.get_cache("reports")
        cache.set(cache_key, result, ttl=self.perf_config.cache_ttl_seconds)

    def _load_data_for_report(self, config: ReportConfiguration) -> pd.DataFrame:
        """
        Load data for report generation.

        This is a placeholder - actual implementation would fetch from BSEE data source.

        Args:
            config: Report configuration

        Returns:
            DataFrame with report data
        """
        # Placeholder implementation
        # In real implementation, this would fetch from BSEE data sources
        return pd.DataFrame()

    def _aggregate_results_to_block(
        self, field_results: List[ProcessingResult]
    ) -> Dict[str, Any]:
        """Aggregate field results to block level."""
        total_metrics = {
            "oil_volume_bbl": 0,
            "gas_volume_mcf": 0,
            "water_volume_bbl": 0,
            "revenue_usd": 0,
            "well_count": 0,
        }

        for result in field_results:
            if result.error:
                continue
            for key in total_metrics:
                if key in result.metrics:
                    total_metrics[key] += result.metrics[key]

        return total_metrics

    def _aggregate_lease_results(self, lease_results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate lease results to field level."""
        total_metrics = {
            "oil_volume_bbl": 0,
            "gas_volume_mcf": 0,
            "water_volume_bbl": 0,
            "revenue_usd": 0,
            "well_count": 0,
        }

        for lease_id, metrics in lease_results.items():
            if isinstance(metrics, dict) and "error" not in metrics:
                for key in total_metrics:
                    if key in metrics:
                        total_metrics[key] += metrics[key]

        return total_metrics

    def _aggregate_well_results(self, well_results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate well results to lease level."""
        total_metrics = {
            "oil_volume": 0,
            "gas_volume": 0,
            "production_days": 0,
            "well_count": len(well_results),
        }

        for well_id, metrics in well_results.items():
            for key in ["oil_volume", "gas_volume", "production_days"]:
                if key in metrics:
                    total_metrics[key] += metrics[key]

        return total_metrics

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.

        Returns:
            Performance statistics dictionary
        """
        stats = {
            "controller_metrics": self.performance_metrics,
            "cache_stats": (
                self.cache_manager.get_all_stats() if self.cache_manager else {}
            ),
            "configuration": {
                "cache_enabled": self.perf_config.cache_enabled,
                "parallel_enabled": self.perf_config.parallel_enabled,
                "max_workers": self.perf_config.max_workers,
                "batch_size": self.perf_config.batch_size,
            },
        }

        # Calculate cache hit rate
        total_requests = (
            self.performance_metrics["cache_hits"]
            + self.performance_metrics["cache_misses"]
        )
        if total_requests > 0:
            stats["cache_hit_rate"] = (
                self.performance_metrics["cache_hits"] / total_requests
            )

        return stats

    def clear_cache(self):
        """Clear all caches."""
        if self.cache_manager:
            self.cache_manager.flush_all()
            logger.info("All caches cleared")

    def batch_generate_reports(
        self, configs: List[ReportConfiguration], params: ReportParameters
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple reports in parallel.

        Args:
            configs: List of report configurations
            params: Report parameters (shared)

        Returns:
            List of generated reports
        """
        if not self.parallel_processor:
            # Fall back to sequential processing
            return [self.generate_report(config, params) for config in configs]

        logger.info(f"Generating {len(configs)} reports in parallel")

        # Generate reports in parallel
        with self.parallel_processor.get_executor() as executor:
            futures = [
                executor.submit(self.generate_report, config, params)
                for config in configs
            ]
            results = []

            for future in futures:
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to generate report: {e}")
                    results.append({"status": "error", "error": str(e)})

        return results
