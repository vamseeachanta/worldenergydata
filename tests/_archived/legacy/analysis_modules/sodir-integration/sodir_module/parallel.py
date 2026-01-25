"""
Parallel processing module for SODIR data operations.

Adapts patterns from BSEE ParallelProcessor to enable concurrent
processing of SODIR API calls and data operations.
"""

import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import time
import logging
from functools import partial
from dataclasses import dataclass
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result from processing a SODIR data entity."""
    entity_id: str
    entity_type: str
    data: Optional[Dict[str, Any]]
    processing_time: float
    success: bool = True
    error: Optional[str] = None
    cached: bool = False


class SodirParallelProcessor:
    """
    Parallel processor for SODIR data operations.
    
    Adapted from BSEE ParallelProcessor to handle:
    - Concurrent API calls to multiple endpoints
    - Parallel data processing for different data types
    - Batch processing of large datasets
    - Coordinated caching operations
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        use_threads: bool = True,
        api_client: Optional[Any] = None
    ):
        """
        Initialize parallel processor.
        
        Args:
            max_workers: Maximum number of workers (default: CPU count)
            use_threads: Use threads instead of processes (True for I/O bound operations)
            api_client: Configured SODIR API client instance
        """
        self.max_workers = max_workers or mp.cpu_count()
        self.use_threads = use_threads
        self.api_client = api_client
        self._executor = None
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'cache_hits': 0,
            'total_time': 0.0
        }
    
    def get_executor(self, use_threads: Optional[bool] = None):
        """
        Get executor for parallel processing.
        
        Args:
            use_threads: Override thread/process setting
        
        Returns:
            ThreadPoolExecutor or ProcessPoolExecutor
        """
        use_threads = use_threads if use_threads is not None else self.use_threads
        
        if use_threads:
            return ThreadPoolExecutor(max_workers=self.max_workers)
        else:
            return ProcessPoolExecutor(max_workers=self.max_workers)
    
    def parallel_api_fetch(
        self,
        endpoints: List[Tuple[str, Dict[str, Any]]],
        cache_enabled: bool = True
    ) -> List[ProcessingResult]:
        """
        Fetch data from multiple API endpoints in parallel.
        
        Args:
            endpoints: List of (endpoint_name, params) tuples
            cache_enabled: Whether to use caching
            
        Returns:
            List of ProcessingResult objects
        """
        results = []
        
        with self.get_executor(use_threads=True) as executor:
            # Submit all API calls
            futures = {}
            for endpoint, params in endpoints:
                future = executor.submit(
                    self._fetch_single_endpoint,
                    endpoint,
                    params,
                    cache_enabled
                )
                futures[future] = (endpoint, params)
            
            # Collect results as they complete
            for future in as_completed(futures):
                endpoint, params = futures[future]
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                    self.stats['successful'] += 1
                except Exception as e:
                    logger.error(f"Failed to fetch {endpoint}: {e}")
                    results.append(ProcessingResult(
                        entity_id=f"{endpoint}_{json.dumps(params)}",
                        entity_type=endpoint,
                        data=None,
                        processing_time=0,
                        success=False,
                        error=str(e)
                    ))
                    self.stats['failed'] += 1
                
                self.stats['total_processed'] += 1
        
        return results
    
    def parallel_process_data(
        self,
        data_batches: List[Tuple[str, List[Dict]]],
        processor_map: Dict[str, Callable]
    ) -> List[ProcessingResult]:
        """
        Process multiple data batches in parallel.
        
        Args:
            data_batches: List of (data_type, data_list) tuples
            processor_map: Map of data_type to processor function
            
        Returns:
            List of ProcessingResult objects
        """
        results = []
        
        with self.get_executor(use_threads=self.use_threads) as executor:
            futures = {}
            
            for data_type, data_list in data_batches:
                if data_type in processor_map:
                    processor = processor_map[data_type]
                    future = executor.submit(
                        self._process_batch,
                        data_type,
                        data_list,
                        processor
                    )
                    futures[future] = (data_type, len(data_list))
            
            # Collect results
            for future in as_completed(futures):
                data_type, batch_size = futures[future]
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                    logger.info(f"Processed {batch_size} {data_type} records")
                except Exception as e:
                    logger.error(f"Failed to process {data_type}: {e}")
                    results.append(ProcessingResult(
                        entity_id=f"{data_type}_batch",
                        entity_type=data_type,
                        data=None,
                        processing_time=0,
                        success=False,
                        error=str(e)
                    ))
        
        return results
    
    def parallel_collection_workflow(
        self,
        collection_configs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute complete data collection workflow in parallel.
        
        Args:
            collection_configs: List of collection configurations
            
        Returns:
            Aggregated results from all collections
        """
        start_time = time.time()
        
        # Phase 1: Parallel API fetching
        api_endpoints = []
        for config in collection_configs:
            data_type = config.get('data_type')
            params = config.get('params', {})
            
            if data_type == 'blocks':
                api_endpoints.append(('blocks', params))
            elif data_type == 'wellbores':
                api_endpoints.append(('wellbores', params))
            elif data_type == 'fields':
                api_endpoints.append(('fields', params))
            elif data_type == 'discoveries':
                api_endpoints.append(('discoveries', params))
            elif data_type == 'surveys':
                api_endpoints.append(('surveys', params))
        
        logger.info(f"Fetching {len(api_endpoints)} endpoints in parallel...")
        fetch_results = self.parallel_api_fetch(api_endpoints)
        
        # Phase 2: Parallel data processing
        data_batches = []
        for result in fetch_results:
            if result.success and result.data:
                data_batches.append((result.entity_type, result.data))
        
        # Create processor map (would use actual processors in production)
        processor_map = {
            'blocks': self._process_blocks,
            'wellbores': self._process_wellbores,
            'fields': self._process_fields,
            'discoveries': self._process_discoveries,
            'surveys': self._process_surveys
        }
        
        logger.info(f"Processing {len(data_batches)} data batches in parallel...")
        process_results = self.parallel_process_data(data_batches, processor_map)
        
        # Aggregate results
        total_time = time.time() - start_time
        
        return {
            'fetch_results': fetch_results,
            'process_results': process_results,
            'statistics': {
                'total_endpoints': len(api_endpoints),
                'successful_fetches': sum(1 for r in fetch_results if r.success),
                'successful_processing': sum(1 for r in process_results if r.success),
                'total_time': total_time,
                'avg_time_per_endpoint': total_time / len(api_endpoints) if api_endpoints else 0
            }
        }
    
    def map_reduce_analysis(
        self,
        data_chunks: List[Dict],
        map_func: Callable,
        reduce_func: Callable,
        chunk_size: int = 100
    ) -> Any:
        """
        Perform map-reduce style analysis on large datasets.
        
        Args:
            data_chunks: Data to process
            map_func: Function to apply to each chunk
            reduce_func: Function to combine results
            chunk_size: Size of each processing chunk
            
        Returns:
            Reduced result
        """
        # Split data into chunks
        chunks = [
            data_chunks[i:i+chunk_size]
            for i in range(0, len(data_chunks), chunk_size)
        ]
        
        # Map phase - process chunks in parallel
        with self.get_executor() as executor:
            map_futures = [
                executor.submit(map_func, chunk)
                for chunk in chunks
            ]
            
            map_results = []
            for future in as_completed(map_futures):
                try:
                    result = future.result()
                    map_results.append(result)
                except Exception as e:
                    logger.error(f"Map operation failed: {e}")
        
        # Reduce phase - combine results
        if map_results:
            return reduce_func(map_results)
        return None
    
    def _fetch_single_endpoint(
        self,
        endpoint: str,
        params: Dict[str, Any],
        use_cache: bool
    ) -> ProcessingResult:
        """
        Fetch data from a single API endpoint.
        
        Args:
            endpoint: API endpoint name
            params: Query parameters
            use_cache: Whether to check cache first
            
        Returns:
            ProcessingResult with fetched data
        """
        start_time = time.time()
        entity_id = f"{endpoint}_{json.dumps(params)}"
        
        try:
            # Check cache first if enabled
            if use_cache and self.api_client and hasattr(self.api_client, 'cache'):
                cached_data = self.api_client.cache.get(entity_id)
                if cached_data:
                    self.stats['cache_hits'] += 1
                    return ProcessingResult(
                        entity_id=entity_id,
                        entity_type=endpoint,
                        data=cached_data,
                        processing_time=time.time() - start_time,
                        cached=True
                    )
            
            # Fetch from API
            if self.api_client:
                if endpoint == 'blocks':
                    data = self.api_client.get_blocks(**params)
                elif endpoint == 'wellbores':
                    data = self.api_client.get_wellbores(**params)
                elif endpoint == 'fields':
                    data = self.api_client.get_fields(**params)
                elif endpoint == 'discoveries':
                    data = self.api_client.get_discoveries(**params)
                elif endpoint == 'surveys':
                    data = self.api_client.get_surveys(**params)
                else:
                    raise ValueError(f"Unknown endpoint: {endpoint}")
                
                # Cache the result
                if use_cache and data:
                    self.api_client.cache.set(entity_id, data)
                
                return ProcessingResult(
                    entity_id=entity_id,
                    entity_type=endpoint,
                    data=data,
                    processing_time=time.time() - start_time
                )
            else:
                # Mock data for testing
                return ProcessingResult(
                    entity_id=entity_id,
                    entity_type=endpoint,
                    data={'mock': True, 'endpoint': endpoint},
                    processing_time=time.time() - start_time
                )
                
        except Exception as e:
            return ProcessingResult(
                entity_id=entity_id,
                entity_type=endpoint,
                data=None,
                processing_time=time.time() - start_time,
                success=False,
                error=str(e)
            )
    
    def _process_batch(
        self,
        data_type: str,
        data_list: List[Dict],
        processor: Callable
    ) -> ProcessingResult:
        """
        Process a batch of data.
        
        Args:
            data_type: Type of data being processed
            data_list: List of data items
            processor: Processing function
            
        Returns:
            ProcessingResult with processed data
        """
        start_time = time.time()
        
        try:
            processed_data = processor(data_list)
            return ProcessingResult(
                entity_id=f"{data_type}_batch_{len(data_list)}",
                entity_type=data_type,
                data=processed_data,
                processing_time=time.time() - start_time
            )
        except Exception as e:
            return ProcessingResult(
                entity_id=f"{data_type}_batch_{len(data_list)}",
                entity_type=data_type,
                data=None,
                processing_time=time.time() - start_time,
                success=False,
                error=str(e)
            )
    
    # Placeholder processing functions (would use actual processors in production)
    def _process_blocks(self, data: List[Dict]) -> Dict:
        """Process block data."""
        return {
            'processed': len(data),
            'type': 'blocks',
            'summary': {
                'total_blocks': len(data),
                'quadrants': len(set(d.get('quadrantId') for d in data if d.get('quadrantId')))
            }
        }
    
    def _process_wellbores(self, data: List[Dict]) -> Dict:
        """Process wellbore data."""
        return {
            'processed': len(data),
            'type': 'wellbores',
            'summary': {
                'total_wellbores': len(data),
                'active': sum(1 for d in data if d.get('status') == 'ACTIVE')
            }
        }
    
    def _process_fields(self, data: List[Dict]) -> Dict:
        """Process field data."""
        return {
            'processed': len(data),
            'type': 'fields',
            'summary': {
                'total_fields': len(data),
                'with_production': sum(1 for d in data if d.get('originalOilInPlaceSm3', 0) > 0)
            }
        }
    
    def _process_discoveries(self, data: List[Dict]) -> Dict:
        """Process discovery data."""
        return {
            'processed': len(data),
            'type': 'discoveries',
            'summary': {
                'total_discoveries': len(data)
            }
        }
    
    def _process_surveys(self, data: List[Dict]) -> Dict:
        """Process survey data."""
        return {
            'processed': len(data),
            'type': 'surveys',
            'summary': {
                'total_surveys': len(data)
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            **self.stats,
            'cache_hit_rate': (
                self.stats['cache_hits'] / self.stats['total_processed']
                if self.stats['total_processed'] > 0 else 0
            ),
            'success_rate': (
                self.stats['successful'] / self.stats['total_processed']
                if self.stats['total_processed'] > 0 else 0
            ),
            'avg_processing_time': (
                self.stats['total_time'] / self.stats['total_processed']
                if self.stats['total_processed'] > 0 else 0
            )
        }
    
    def reset_statistics(self):
        """Reset processing statistics."""
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'cache_hits': 0,
            'total_time': 0.0
        }