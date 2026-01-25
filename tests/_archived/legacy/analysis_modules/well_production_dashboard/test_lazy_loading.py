"""
Tests for lazy loading functionality in query optimizer.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path

from src.worldenergydata.modules.well_production_dashboard.query_optimizer import (
    LazyLoadConfig,
    LazyDataLoader,
    QueryOptimizer
)


class TestLazyLoadConfig(unittest.TestCase):
    """Test lazy load configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = LazyLoadConfig()
        
        self.assertEqual(config.chunk_size, 1000)
        self.assertEqual(config.page_size, 100)
        self.assertEqual(config.prefetch_pages, 2)
        self.assertEqual(config.cache_ttl, 300)
        self.assertTrue(config.enable_compression)
        self.assertEqual(config.max_memory_mb, 500)
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = LazyLoadConfig(
            chunk_size=500,
            page_size=50,
            prefetch_pages=3,
            cache_ttl=600,
            enable_compression=False,
            max_memory_mb=1000
        )
        
        self.assertEqual(config.chunk_size, 500)
        self.assertEqual(config.page_size, 50)
        self.assertEqual(config.prefetch_pages, 3)
        self.assertEqual(config.cache_ttl, 600)
        self.assertFalse(config.enable_compression)
        self.assertEqual(config.max_memory_mb, 1000)


class TestLazyDataLoader(unittest.TestCase):
    """Test lazy data loader functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_source = Mock()
        self.config = LazyLoadConfig(page_size=10, cache_ttl=60)
        self.loader = LazyDataLoader(self.mock_data_source, self.config)
    
    def test_load_page_first_time(self):
        """Test loading a page for the first time."""
        # Mock data
        expected_data = pd.DataFrame({
            'well_id': ['W001', 'W002'],
            'production': [100, 200]
        })
        
        self.loader._fetch_data = Mock(return_value=expected_data)
        
        # Load page
        result = self.loader.load_page(page=0)
        
        self.assertTrue(result.equals(expected_data))
        self.loader._fetch_data.assert_called_once_with(0, 10, None)
    
    def test_load_page_from_cache(self):
        """Test loading a page from cache."""
        # Set up cache
        cached_data = pd.DataFrame({'well_id': ['W001'], 'production': [100]})
        cache_key = self.loader._get_cache_key(0, None)
        self.loader._page_cache[cache_key] = (cached_data, datetime.now())
        
        self.loader._fetch_data = Mock()
        
        # Load page (should come from cache)
        result = self.loader.load_page(page=0)
        
        self.assertTrue(result.equals(cached_data))
        self.loader._fetch_data.assert_not_called()
    
    def test_load_page_expired_cache(self):
        """Test loading a page with expired cache."""
        # Set up expired cache
        cached_data = pd.DataFrame({'well_id': ['W001'], 'production': [100]})
        cache_key = self.loader._get_cache_key(0, None)
        old_timestamp = datetime.now() - timedelta(seconds=120)  # Expired
        self.loader._page_cache[cache_key] = (cached_data, old_timestamp)
        
        fresh_data = pd.DataFrame({'well_id': ['W002'], 'production': [200]})
        self.loader._fetch_data = Mock(return_value=fresh_data)
        
        # Load page (should fetch fresh data)
        result = self.loader.load_page(page=0)
        
        self.assertTrue(result.equals(fresh_data))
        self.loader._fetch_data.assert_called_once()
    
    def test_load_chunked(self):
        """Test loading data in chunks."""
        self.loader._get_total_rows = Mock(return_value=25)
        
        chunk_data = [
            pd.DataFrame({'id': range(0, 10)}),
            pd.DataFrame({'id': range(10, 20)}),
            pd.DataFrame({'id': range(20, 25)})
        ]
        
        self.loader._fetch_data = Mock(side_effect=chunk_data)
        
        # Load chunks
        chunks = list(self.loader.load_chunked())
        
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 10)
        self.assertEqual(len(chunks[1]), 10)
        self.assertEqual(len(chunks[2]), 5)
    
    def test_load_chunked_with_callback(self):
        """Test loading chunks with processing callback."""
        self.loader._get_total_rows = Mock(return_value=10)
        
        chunk_data = pd.DataFrame({'value': [1, 2, 3, 4, 5]})
        self.loader._fetch_data = Mock(return_value=chunk_data)
        
        # Define callback to double values
        def double_values(df):
            df['value'] = df['value'] * 2
            return df
        
        # Load chunks with callback
        chunks = list(self.loader.load_chunked(chunk_callback=double_values))
        
        self.assertEqual(len(chunks), 1)
        self.assertTrue((chunks[0]['value'] == [2, 4, 6, 8, 10]).all())
    
    def test_build_query_with_filters(self):
        """Test building query with filters."""
        filters = {
            'well_id': 'W001',
            'field': ['Field1', 'Field2'],
            'status': 'active'
        }
        
        query = self.loader._build_query(10, 20, filters)
        
        self.assertIn("LIMIT 20 OFFSET 10", query)
        self.assertIn("well_id = 'W001'", query)
        self.assertIn("field IN ('Field1', 'Field2')", query)
        self.assertIn("status = 'active'", query)


class TestQueryOptimizerLazyLoading(unittest.TestCase):
    """Test QueryOptimizer lazy loading functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('src.worldenergydata.modules.well_production_dashboard.query_optimizer.HierarchicalDataLoader'):
            with patch('src.worldenergydata.modules.well_production_dashboard.query_optimizer.APIData'):
                with patch('src.worldenergydata.modules.well_production_dashboard.query_optimizer.LeaseData'):
                    with patch('src.worldenergydata.modules.well_production_dashboard.query_optimizer.BlockData'):
                        self.optimizer = QueryOptimizer()
    
    def test_get_data_lazy(self):
        """Test getting data with lazy loading."""
        mock_data = pd.DataFrame({'well_id': ['W001'], 'production': [100]})
        self.optimizer.lazy_loader.load_page = Mock(return_value=mock_data)
        
        result = self.optimizer.get_data_lazy(page=1, filters={'field': 'Test'})
        
        self.assertTrue(result.equals(mock_data))
        self.optimizer.lazy_loader.load_page.assert_called_once_with(1, {'field': 'Test'})
    
    def test_get_data_chunked(self):
        """Test getting data in chunks."""
        mock_chunks = [
            pd.DataFrame({'id': [1, 2]}),
            pd.DataFrame({'id': [3, 4]})
        ]
        
        self.optimizer.lazy_loader.load_chunked = Mock(return_value=iter(mock_chunks))
        
        chunks = list(self.optimizer.get_data_chunked(filters={'status': 'active'}))
        
        self.assertEqual(len(chunks), 2)
        self.optimizer.lazy_loader.load_chunked.assert_called_once()
    
    def test_process_large_dataset(self):
        """Test processing large dataset with batching."""
        well_ids = [f'W{i:03d}' for i in range(5)]
        
        def mock_processor(data):
            return {'processed': len(data)}
        
        self.optimizer._load_batch_wells = Mock(
            return_value=pd.DataFrame({'well_id': well_ids[:2]})
        )
        
        results = self.optimizer.process_large_dataset(
            well_ids,
            mock_processor,
            progress_callback=Mock()
        )
        
        self.assertEqual(results['processed'], 5)
        self.assertEqual(results['failed'], 0)
        self.assertGreater(len(results['data']), 0)
    
    def test_lazy_loading_context(self):
        """Test lazy loading context manager."""
        original_config = self.optimizer.lazy_config
        new_config = LazyLoadConfig(page_size=50, cache_ttl=120)
        
        with self.optimizer.lazy_loading_context(new_config):
            self.assertEqual(self.optimizer.lazy_config.page_size, 50)
            self.assertEqual(self.optimizer.lazy_config.cache_ttl, 120)
        
        # Config should be restored
        self.assertEqual(self.optimizer.lazy_config.page_size, original_config.page_size)
        self.assertEqual(self.optimizer.lazy_config.cache_ttl, original_config.cache_ttl)
    
    def test_optimize_for_dashboard(self):
        """Test optimizing settings for dashboard."""
        self.optimizer.optimize_for_dashboard(
            enable_lazy=True,
            prefetch=5,
            cache_ttl=600
        )
        
        self.assertEqual(self.optimizer.lazy_config.prefetch_pages, 5)
        self.assertEqual(self.optimizer.lazy_config.cache_ttl, 600)
        self.assertTrue(self.optimizer.lazy_config.enable_compression)
    
    def test_get_memory_usage(self):
        """Test getting memory usage statistics."""
        usage = self.optimizer.get_memory_usage()
        
        self.assertIn('cache_mb', usage)
        self.assertIn('index_mb', usage)
        self.assertIn('total_mb', usage)
        self.assertIsInstance(usage['total_mb'], float)
    
    def test_clear_cache_with_lazy_loader(self):
        """Test clearing cache including lazy loader cache."""
        # Add some cache data
        self.optimizer.lazy_loader._page_cache = {'test': 'data'}
        
        self.optimizer.clear_cache()
        
        self.assertEqual(len(self.optimizer.lazy_loader._page_cache), 0)


class TestLazyLoadingIntegration(unittest.TestCase):
    """Integration tests for lazy loading."""
    
    def test_end_to_end_lazy_loading(self):
        """Test end-to-end lazy loading workflow."""
        # Create mock data source
        mock_source = Mock()
        
        # Create loader with small page size for testing
        config = LazyLoadConfig(page_size=5, chunk_size=10)
        loader = LazyDataLoader(mock_source, config)
        
        # Mock total rows
        loader._get_total_rows = Mock(return_value=23)
        
        # Mock fetch data to return sequential data
        def mock_fetch(offset, limit, filters):
            return pd.DataFrame({
                'id': range(offset, min(offset + limit, 23)),
                'value': range(offset * 10, min((offset + limit) * 10, 230), 10)
            })
        
        loader._fetch_data = mock_fetch
        
        # Test pagination
        page1 = loader.load_page(0)
        page2 = loader.load_page(1)
        page3 = loader.load_page(2)
        
        self.assertEqual(len(page1), 5)
        self.assertEqual(len(page2), 5)
        self.assertEqual(len(page3), 5)
        
        # Test chunking
        chunks = list(loader.load_chunked())
        self.assertEqual(len(chunks), 3)  # 23 rows / 10 chunk_size = 3 chunks
        
        # Verify data integrity
        all_data = pd.concat(chunks, ignore_index=True)
        self.assertEqual(len(all_data), 23)
        self.assertEqual(all_data['id'].tolist(), list(range(23)))


if __name__ == '__main__':
    unittest.main()