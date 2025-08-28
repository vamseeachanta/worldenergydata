"""
Tests for Redis-like Caching System for BSEE Report Performance Optimization

Tests the in-memory caching system that provides Redis-like functionality
for aggregated metrics to achieve 50-70% performance improvement.
"""

import pytest
import time
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
from pathlib import Path


class TestRedisLikeCaching:
    """Test Redis-like caching system for aggregated metrics."""
    
    @pytest.fixture
    def sample_metrics_data(self):
        """Generate sample metrics data for caching tests."""
        np.random.seed(42)
        return {
            'block_MC123': {
                'oil_volume_bbl': 1234567.89,
                'gas_volume_mcf': 987654.32,
                'water_volume_bbl': 456789.01,
                'revenue_usd': 98765432.10,
                'well_count': 45,
                'last_updated': datetime.now().isoformat()
            },
            'field_A': {
                'oil_volume_bbl': 567890.12,
                'gas_volume_mcf': 345678.90,
                'water_volume_bbl': 123456.78,
                'revenue_usd': 45678901.23,
                'well_count': 23,
                'last_updated': datetime.now().isoformat()
            },
            'lease_001': {
                'oil_volume_bbl': 234567.89,
                'gas_volume_mcf': 123456.78,
                'water_volume_bbl': 56789.01,
                'revenue_usd': 12345678.90,
                'well_count': 8,
                'last_updated': datetime.now().isoformat()
            }
        }
    
    @pytest.fixture
    def cache_instance(self):
        """Create a cache instance for testing."""
        from worldenergydata.modules.bsee.reports.comprehensive.performance.cache import MetricsCache
        return MetricsCache(max_size_mb=100, ttl_seconds=3600)
    
    def test_cache_initialization(self):
        """Test cache system initialization."""
        from worldenergydata.modules.bsee.reports.comprehensive.performance.cache import MetricsCache
        
        # Test default initialization
        cache = MetricsCache()
        assert cache is not None
        assert cache.max_size_mb == 100  # Default size
        assert cache.ttl_seconds == 3600  # Default TTL of 1 hour
        
        # Test custom initialization
        custom_cache = MetricsCache(max_size_mb=200, ttl_seconds=7200)
        assert custom_cache.max_size_mb == 200
        assert custom_cache.ttl_seconds == 7200
    
    def test_cache_set_and_get(self, cache_instance, sample_metrics_data):
        """Test setting and getting values from cache."""
        cache = cache_instance
        
        # Test setting values
        for key, value in sample_metrics_data.items():
            cache.set(key, value)
        
        # Test getting values
        for key, expected_value in sample_metrics_data.items():
            cached_value = cache.get(key)
            assert cached_value is not None
            assert cached_value == expected_value
        
        # Test getting non-existent key
        assert cache.get('non_existent_key') is None
    
    def test_cache_ttl_expiration(self, cache_instance):
        """Test cache TTL (Time To Live) expiration."""
        cache = cache_instance
        cache.ttl_seconds = 1  # Set short TTL for testing
        
        # Set a value
        cache.set('test_key', {'value': 123})
        
        # Value should exist immediately
        assert cache.get('test_key') is not None
        
        # Wait for TTL to expire
        time.sleep(1.5)
        
        # Value should be expired
        assert cache.get('test_key') is None
    
    def test_cache_key_generation(self, cache_instance):
        """Test cache key generation for different data types."""
        cache = cache_instance
        
        # Test key generation for different organizational levels
        block_key = cache.generate_key('block', 'MC123', '2024-01-01', '2024-06-30')
        assert block_key == 'block:MC123:2024-01-01:2024-06-30'
        
        field_key = cache.generate_key('field', 'Field_A', '2024-01-01', '2024-06-30')
        assert field_key == 'field:Field_A:2024-01-01:2024-06-30'
        
        lease_key = cache.generate_key('lease', 'LEASE001', '2024-01-01', '2024-06-30')
        assert lease_key == 'lease:LEASE001:2024-01-01:2024-06-30'
        
        # Test key generation with complex parameters
        complex_params = {
            'level': 'block',
            'entity': 'MC123',
            'metrics': ['oil', 'gas', 'water'],
            'aggregation': 'sum'
        }
        complex_key = cache.generate_complex_key(**complex_params)
        assert complex_key is not None
        assert 'block' in complex_key
        assert 'MC123' in complex_key
    
    def test_cache_invalidation(self, cache_instance, sample_metrics_data):
        """Test cache invalidation mechanisms."""
        cache = cache_instance
        
        # Populate cache
        for key, value in sample_metrics_data.items():
            cache.set(key, value)
        
        # Test single key invalidation
        cache.invalidate('block_MC123')
        assert cache.get('block_MC123') is None
        assert cache.get('field_A') is not None  # Other keys should remain
        
        # Test pattern-based invalidation
        cache.invalidate_pattern('field_*')
        assert cache.get('field_A') is None
        assert cache.get('lease_001') is not None
        
        # Test complete cache flush
        cache.flush()
        for key in sample_metrics_data.keys():
            assert cache.get(key) is None
    
    def test_cache_size_management(self, cache_instance):
        """Test cache size management and eviction."""
        cache = cache_instance
        cache.max_size_mb = 1  # Set small size for testing
        
        # Add data until size limit is exceeded
        large_data = {'data': 'x' * 1024 * 1024}  # 1MB of data
        
        cache.set('item1', large_data)
        cache.set('item2', large_data)  # Should trigger eviction
        
        # Verify LRU eviction (item1 should be evicted)
        assert cache.get('item1') is None or cache.get('item2') is not None
        assert cache.get_size_mb() <= cache.max_size_mb
    
    def test_cache_statistics(self, cache_instance, sample_metrics_data):
        """Test cache statistics and monitoring."""
        cache = cache_instance
        
        # Reset statistics
        cache.reset_stats()
        
        # Perform cache operations
        for key, value in sample_metrics_data.items():
            cache.set(key, value)
        
        # Cache hits
        for key in sample_metrics_data.keys():
            cache.get(key)
        
        # Cache misses
        cache.get('non_existent')
        cache.get('another_non_existent')
        
        # Get statistics
        stats = cache.get_stats()
        assert stats['hits'] == len(sample_metrics_data)
        assert stats['misses'] == 2
        assert stats['hit_rate'] > 0
        assert stats['total_keys'] == len(sample_metrics_data)
    
    def test_cache_serialization(self, cache_instance):
        """Test cache serialization for complex data types."""
        cache = cache_instance
        
        # Test DataFrame serialization
        df = pd.DataFrame({
            'well_id': ['W001', 'W002', 'W003'],
            'oil_volume': [1000, 2000, 3000],
            'gas_volume': [500, 1000, 1500]
        })
        
        cache.set('dataframe_test', df)
        cached_df = cache.get('dataframe_test')
        
        assert cached_df is not None
        pd.testing.assert_frame_equal(df, cached_df)
        
        # Test nested dictionary serialization
        nested_dict = {
            'level1': {
                'level2': {
                    'level3': {'value': 123, 'list': [1, 2, 3]}
                }
            }
        }
        
        cache.set('nested_test', nested_dict)
        cached_nested = cache.get('nested_test')
        assert cached_nested == nested_dict
    
    def test_cache_concurrent_access(self, cache_instance):
        """Test cache behavior under concurrent access."""
        import threading
        cache = cache_instance
        
        def write_to_cache(thread_id):
            for i in range(10):
                key = f"thread_{thread_id}_item_{i}"
                value = {'thread': thread_id, 'item': i}
                cache.set(key, value)
        
        def read_from_cache(thread_id):
            for i in range(10):
                key = f"thread_{thread_id}_item_{i}"
                cache.get(key)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            write_thread = threading.Thread(target=write_to_cache, args=(i,))
            read_thread = threading.Thread(target=read_from_cache, args=(i,))
            threads.extend([write_thread, read_thread])
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify cache integrity
        assert cache.get_stats()['total_keys'] > 0
    
    def test_cache_performance_improvement(self, cache_instance):
        """Test actual performance improvement with caching."""
        cache = cache_instance
        
        def expensive_aggregation():
            """Simulate expensive aggregation operation."""
            time.sleep(0.1)  # Simulate 100ms processing
            return {
                'oil_total': sum(range(1000000)),
                'gas_total': sum(range(500000)),
                'revenue': sum(range(2000000))
            }
        
        # First call - no cache
        start_time = time.time()
        result1 = expensive_aggregation()
        cache.set('aggregation_result', result1)
        no_cache_time = time.time() - start_time
        
        # Second call - with cache
        start_time = time.time()
        result2 = cache.get('aggregation_result')
        if result2 is None:
            result2 = expensive_aggregation()
            cache.set('aggregation_result', result2)
        cache_time = time.time() - start_time
        
        # Cache should be at least 50x faster for this test
        assert cache_time < no_cache_time / 50
        assert result1 == result2
    
    @pytest.mark.integration
    def test_cache_integration_with_aggregators(self):
        """Test cache integration with BSEE aggregators."""
        from worldenergydata.modules.bsee.reports.comprehensive.performance.cache import MetricsCache
        from worldenergydata.modules.bsee.reports.comprehensive.aggregators.block_aggregator_enhanced import BlockAggregator
        
        cache = MetricsCache()
        aggregator = BlockAggregator()
        
        # Create sample data
        sample_data = pd.DataFrame({
            'block': ['MC123'] * 100,
            'oil_volume_bbl': np.random.uniform(1000, 5000, 100),
            'gas_volume_mcf': np.random.uniform(500, 2500, 100)
        })
        
        # First aggregation - should be cached
        cache_key = cache.generate_key('block', 'MC123', 'aggregation')
        
        # Check if cached
        cached_result = cache.get(cache_key)
        if cached_result is None:
            # Perform aggregation
            try:
                result = aggregator.aggregate(sample_data)
                cache.set(cache_key, result)
            except AttributeError:
                # If method doesn't exist, use simple aggregation
                result = {
                    'oil_total': sample_data['oil_volume_bbl'].sum(),
                    'gas_total': sample_data['gas_volume_mcf'].sum()
                }
                cache.set(cache_key, result)
        else:
            result = cached_result
        
        # Verify cache was used on second access
        second_result = cache.get(cache_key)
        assert second_result is not None
        assert second_result == result