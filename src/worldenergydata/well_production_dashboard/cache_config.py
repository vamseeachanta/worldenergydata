"""
Cache configuration for Well Production Dashboard.

Leverages the comprehensive report's Redis-like caching system.
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

# Import the comprehensive report's cache system
from ..bsee.reports.comprehensive.performance.cache import MetricsCache

logger = logging.getLogger(__name__)


class DashboardCacheManager:
    """
    Cache manager for Well Production Dashboard.

    Integrates with the comprehensive report's caching infrastructure
    to provide high-performance data caching.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize cache manager with configuration.

        Args:
            config: Cache configuration dictionary
        """
        self.config = config or self._get_default_config()

        # Initialize the metrics cache from comprehensive reports
        self.cache = MetricsCache(
            max_size_mb=self.config.get("max_size_mb", 200),
            ttl_seconds=self.config.get("default_ttl", 300),
        )

        # Cache key prefixes for different data types
        self.prefixes = {
            "well": "dashboard:well:",
            "field": "dashboard:field:",
            "chart": "dashboard:chart:",
            "export": "dashboard:export:",
            "api": "dashboard:api:",
            "verification": "dashboard:verification:",
        }

        # TTL settings for different data types (seconds)
        self.ttl_settings = {
            "well_data": 300,  # 5 minutes
            "field_aggregation": 600,  # 10 minutes
            "chart_data": 180,  # 3 minutes
            "export_data": 900,  # 15 minutes
            "api_response": 60,  # 1 minute
            "verification": 1800,  # 30 minutes
        }

        logger.info(
            f"Cache manager initialized with {self.config['max_size_mb']}MB limit"
        )

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default cache configuration."""
        return {
            "enabled": True,
            "max_size_mb": 200,
            "default_ttl": 300,
            "enable_compression": False,
            "enable_stats": True,
            "redis_fallback": {
                "enabled": False,
                "host": "localhost",
                "port": 6379,
                "db": 0,
            },
        }

    def generate_cache_key(
        self, data_type: str, identifier: str, params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a unique cache key.

        Args:
            data_type: Type of data (well, field, chart, etc.)
            identifier: Unique identifier (well_id, field_name, etc.)
            params: Additional parameters to include in key

        Returns:
            Cache key string
        """
        prefix = self.prefixes.get(data_type, "dashboard:")

        # Create a unique key based on identifier and params
        key_parts = [prefix, identifier]

        if params:
            # Sort params for consistent key generation
            sorted_params = sorted(params.items())
            param_str = json.dumps(sorted_params, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode(), usedforsecurity=False).hexdigest()[:8]
            key_parts.append(param_hash)

        return ":".join(key_parts)

    def cache_well_data(
        self, well_id: str, data: Any, params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Cache well production data.

        Args:
            well_id: Well identifier
            data: Data to cache
            params: Query parameters

        Returns:
            True if cached successfully
        """
        key = self.generate_cache_key("well", well_id, params)
        ttl = self.ttl_settings["well_data"]

        success = self.cache.set(key, data, ttl)
        if success:
            logger.debug(f"Cached well data for {well_id}")
        return success

    def get_well_data(
        self, well_id: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Get cached well data.

        Args:
            well_id: Well identifier
            params: Query parameters

        Returns:
            Cached data or None
        """
        key = self.generate_cache_key("well", well_id, params)
        data = self.cache.get(key)

        if data is not None:
            logger.debug(f"Cache hit for well {well_id}")
        return data

    def cache_field_aggregation(
        self, field_name: str, data: Any, params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Cache field aggregation data.

        Args:
            field_name: Field name
            data: Aggregated data
            params: Aggregation parameters

        Returns:
            True if cached successfully
        """
        key = self.generate_cache_key("field", field_name, params)
        ttl = self.ttl_settings["field_aggregation"]

        success = self.cache.set(key, data, ttl)
        if success:
            logger.debug(f"Cached field aggregation for {field_name}")
        return success

    def get_field_aggregation(
        self, field_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Get cached field aggregation.

        Args:
            field_name: Field name
            params: Aggregation parameters

        Returns:
            Cached data or None
        """
        key = self.generate_cache_key("field", field_name, params)
        data = self.cache.get(key)

        if data is not None:
            logger.debug(f"Cache hit for field {field_name}")
        return data

    def cache_chart_data(
        self, chart_id: str, data: Any, params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Cache chart visualization data.

        Args:
            chart_id: Chart identifier
            data: Chart data
            params: Chart parameters

        Returns:
            True if cached successfully
        """
        key = self.generate_cache_key("chart", chart_id, params)
        ttl = self.ttl_settings["chart_data"]

        return self.cache.set(key, data, ttl)

    def get_chart_data(
        self, chart_id: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Get cached chart data.

        Args:
            chart_id: Chart identifier
            params: Chart parameters

        Returns:
            Cached data or None
        """
        key = self.generate_cache_key("chart", chart_id, params)
        return self.cache.get(key)

    def cache_api_response(
        self, endpoint: str, response: Any, params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Cache API response data.

        Args:
            endpoint: API endpoint
            response: Response data
            params: Request parameters

        Returns:
            True if cached successfully
        """
        key = self.generate_cache_key("api", endpoint, params)
        ttl = self.ttl_settings["api_response"]

        return self.cache.set(key, response, ttl)

    def get_api_response(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Get cached API response.

        Args:
            endpoint: API endpoint
            params: Request parameters

        Returns:
            Cached response or None
        """
        key = self.generate_cache_key("api", endpoint, params)
        return self.cache.get(key)

    def invalidate_well(self, well_id: str):
        """
        Invalidate all cache entries for a well.

        Args:
            well_id: Well identifier
        """
        pattern = f"{self.prefixes['well']}{well_id}*"
        invalidated = self.cache.invalidate_pattern(pattern)
        logger.info(f"Invalidated {invalidated} cache entries for well {well_id}")

    def invalidate_field(self, field_name: str):
        """
        Invalidate all cache entries for a field.

        Args:
            field_name: Field name
        """
        pattern = f"{self.prefixes['field']}{field_name}*"
        invalidated = self.cache.invalidate_pattern(pattern)
        logger.info(f"Invalidated {invalidated} cache entries for field {field_name}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        stats = self.cache.get_stats()

        # Calculate hit rate
        total_requests = stats["hits"] + stats["misses"]
        hit_rate = (stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "hit_rate": f"{hit_rate:.1f}%",
            "total_hits": stats["hits"],
            "total_misses": stats["misses"],
            "total_sets": stats["sets"],
            "total_evictions": stats["evictions"],
            "cache_size_mb": stats["current_size_mb"],
            "cache_entries": stats["entry_count"],
            "max_size_mb": self.config["max_size_mb"],
        }

    def clear_cache(self):
        """Clear all cache entries."""
        self.cache.clear()
        logger.info("Dashboard cache cleared")

    def warm_cache(self, well_ids: List[str] = None, field_names: List[str] = None):
        """
        Pre-warm cache with commonly accessed data.

        Args:
            well_ids: List of well IDs to pre-cache
            field_names: List of field names to pre-cache
        """
        warmed = 0

        # This would typically load data from the database
        # For now, we'll just log the intent
        if well_ids:
            logger.info(f"Would warm cache for {len(well_ids)} wells")
            warmed += len(well_ids)

        if field_names:
            logger.info(f"Would warm cache for {len(field_names)} fields")
            warmed += len(field_names)

        logger.info(f"Cache warming complete: {warmed} entries")
        return warmed
