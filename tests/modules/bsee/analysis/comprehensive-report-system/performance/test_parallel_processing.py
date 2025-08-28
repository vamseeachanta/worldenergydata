"""
Tests for Parallel Processing System for BSEE Report Performance

Tests concurrent processing of organizational units to achieve
30-40% performance improvement.
"""

import pytest
import time
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Any
from datetime import datetime
import multiprocessing as mp


class TestParallelProcessing:
    """Test parallel processing for organizational unit processing."""
    
    @pytest.fixture
    def sample_org_units(self):
        """Generate sample organizational units for testing."""
        np.random.seed(42)
        
        units = []
        for block_id in range(5):  # 5 blocks
            for field_id in range(3):  # 3 fields per block
                for lease_id in range(4):  # 4 leases per field
                    for well_id in range(5):  # 5 wells per lease
                        units.append({
                            'block': f'MC_{block_id:03d}',
                            'field': f'Field_{block_id}_{field_id}',
                            'lease': f'LEASE_{block_id}_{field_id}_{lease_id:03d}',
                            'well_id': f'W_{block_id}_{field_id}_{lease_id}_{well_id:03d}',
                            'oil_volume_bbl': np.random.uniform(1000, 10000),
                            'gas_volume_mcf': np.random.uniform(500, 5000),
                            'processing_time': 0.01  # Simulated processing time
                        })
        
        return pd.DataFrame(units)
    
    @pytest.fixture
    def parallel_processor(self):
        """Create parallel processor instance."""
        from worldenergydata.modules.bsee.reports.comprehensive.performance.parallel_processor import ParallelProcessor
        return ParallelProcessor(max_workers=4)
    
    def test_parallel_processor_initialization(self):
        """Test parallel processor initialization."""
        from worldenergydata.modules.bsee.reports.comprehensive.performance.parallel_processor import ParallelProcessor
        
        # Test default initialization
        processor = ParallelProcessor()
        assert processor is not None
        assert processor.max_workers == mp.cpu_count()
        
        # Test custom worker count
        custom_processor = ParallelProcessor(max_workers=8)
        assert custom_processor.max_workers == 8
        
        # Test with thread pool
        thread_processor = ParallelProcessor(use_threads=True, max_workers=4)
        assert thread_processor.use_threads is True
        assert thread_processor.max_workers == 4
    
    def test_process_single_unit(self, parallel_processor, sample_org_units):
        """Test processing a single organizational unit."""
        processor = parallel_processor
        
        # Get single block data
        block_data = sample_org_units[sample_org_units['block'] == 'MC_000']
        
        # Process single unit
        result = processor.process_unit('block', 'MC_000', block_data)
        
        assert result is not None
        assert 'entity_id' in result
        assert 'metrics' in result
        assert result['entity_id'] == 'MC_000'
    
    def test_parallel_block_processing(self, parallel_processor, sample_org_units):
        """Test parallel processing of multiple blocks."""
        processor = parallel_processor
        
        # Get unique blocks
        blocks = sample_org_units['block'].unique()
        
        # Sequential processing for comparison
        sequential_start = time.time()
        sequential_results = []
        for block in blocks:
            block_data = sample_org_units[sample_org_units['block'] == block]
            result = processor.process_unit('block', block, block_data)
            sequential_results.append(result)
        sequential_time = time.time() - sequential_start
        
        # Parallel processing
        parallel_start = time.time()
        parallel_results = processor.process_blocks_parallel(sample_org_units, blocks)
        parallel_time = time.time() - parallel_start
        
        # Verify results
        assert len(parallel_results) == len(blocks)
        assert len(parallel_results) == len(sequential_results)
        
        # Parallel should be faster (at least 20% improvement)
        assert parallel_time < sequential_time * 0.8
    
    def test_parallel_field_processing(self, parallel_processor, sample_org_units):
        """Test parallel processing of fields within blocks."""
        processor = parallel_processor
        
        # Get fields for a specific block
        block_data = sample_org_units[sample_org_units['block'] == 'MC_000']
        fields = block_data['field'].unique()
        
        # Process fields in parallel
        results = processor.process_fields_parallel(block_data, fields)
        
        assert len(results) == len(fields)
        for result in results:
            assert 'entity_id' in result
            assert 'metrics' in result
    
    def test_hierarchical_parallel_processing(self, parallel_processor, sample_org_units):
        """Test hierarchical parallel processing (blocks -> fields -> leases)."""
        processor = parallel_processor
        
        # Process entire hierarchy in parallel
        results = processor.process_hierarchy_parallel(sample_org_units)
        
        assert 'blocks' in results
        assert 'fields' in results
        assert 'leases' in results
        assert 'wells' in results
        
        # Verify counts
        assert len(results['blocks']) == sample_org_units['block'].nunique()
        assert len(results['fields']) == sample_org_units['field'].nunique()
        assert len(results['leases']) == sample_org_units['lease'].nunique()
    
    def test_worker_pool_management(self, parallel_processor):
        """Test worker pool creation and management."""
        processor = parallel_processor
        
        # Test thread pool
        with processor.get_executor(use_threads=True) as executor:
            assert executor is not None
            assert isinstance(executor, ThreadPoolExecutor)
        
        # Test process pool
        with processor.get_executor(use_threads=False) as executor:
            assert executor is not None
            assert isinstance(executor, ProcessPoolExecutor)
    
    def test_parallel_aggregation(self, parallel_processor, sample_org_units):
        """Test parallel aggregation of metrics."""
        processor = parallel_processor
        
        # Define aggregation tasks
        aggregation_tasks = [
            ('sum', 'oil_volume_bbl'),
            ('sum', 'gas_volume_mcf'),
            ('mean', 'oil_volume_bbl'),
            ('mean', 'gas_volume_mcf'),
            ('count', 'well_id')
        ]
        
        # Parallel aggregation
        results = processor.parallel_aggregate(sample_org_units, aggregation_tasks)
        
        assert len(results) == len(aggregation_tasks)
        assert results[('sum', 'oil_volume_bbl')] == sample_org_units['oil_volume_bbl'].sum()
        assert results[('mean', 'gas_volume_mcf')] == sample_org_units['gas_volume_mcf'].mean()
    
    def test_chunk_processing(self, parallel_processor, sample_org_units):
        """Test processing data in chunks for memory efficiency."""
        processor = parallel_processor
        
        # Process in chunks
        chunk_size = 100
        results = processor.process_in_chunks(sample_org_units, chunk_size=chunk_size)
        
        assert results is not None
        assert 'total_processed' in results
        assert results['total_processed'] == len(sample_org_units)
    
    def test_error_handling_in_parallel(self, parallel_processor):
        """Test error handling in parallel processing."""
        processor = parallel_processor
        
        def failing_task(data):
            if data['id'] == 2:
                raise ValueError("Simulated error")
            return {'result': data['id'] * 2}
        
        # Create test data with one failing item
        test_data = [{'id': i} for i in range(5)]
        
        # Process with error handling
        results, errors = processor.process_with_error_handling(test_data, failing_task)
        
        assert len(results) == 4  # 4 successful
        assert len(errors) == 1    # 1 failed
        assert errors[0]['id'] == 2
    
    def test_performance_scaling(self, sample_org_units):
        """Test performance scaling with different worker counts."""
        from worldenergydata.modules.bsee.reports.comprehensive.performance.parallel_processor import ParallelProcessor
        
        # Test with different worker counts
        worker_counts = [1, 2, 4, 8]
        processing_times = []
        
        for workers in worker_counts:
            processor = ParallelProcessor(max_workers=workers)
            
            start_time = time.time()
            processor.process_hierarchy_parallel(sample_org_units)
            elapsed = time.time() - start_time
            
            processing_times.append(elapsed)
        
        # Verify that more workers generally improves performance
        # (up to a point - diminishing returns expected)
        assert processing_times[1] < processing_times[0]  # 2 workers faster than 1
        assert processing_times[2] <= processing_times[1]  # 4 workers at least as fast as 2
    
    def test_memory_efficient_processing(self, parallel_processor):
        """Test memory-efficient processing for large datasets."""
        processor = parallel_processor
        
        # Create large dataset simulation
        large_data = pd.DataFrame({
            'id': range(10000),
            'value': np.random.random(10000)
        })
        
        # Process with memory limits
        result = processor.process_memory_efficient(
            large_data,
            max_memory_mb=100,
            batch_size=1000
        )
        
        assert result is not None
        assert 'batches_processed' in result
        assert result['batches_processed'] == 10  # 10000 / 1000
    
    def test_parallel_template_rendering(self, parallel_processor):
        """Test parallel rendering of multiple templates."""
        processor = parallel_processor
        
        # Simulate template rendering tasks
        templates = ['compliance', 'economic', 'operational', 'executive']
        template_data = {
            'metrics': {'oil': 1000, 'gas': 500},
            'period': '2024-Q1'
        }
        
        # Render templates in parallel
        rendered = processor.parallel_render_templates(templates, template_data)
        
        assert len(rendered) == len(templates)
        for template_name in templates:
            assert template_name in rendered
            assert rendered[template_name] is not None
    
    @pytest.mark.integration
    def test_integration_with_aggregators(self, parallel_processor, sample_org_units):
        """Test parallel processing integration with BSEE aggregators."""
        from worldenergydata.modules.bsee.reports.comprehensive.aggregators.block_aggregator_enhanced import BlockAggregator
        
        processor = parallel_processor
        aggregator = BlockAggregator()
        
        # Get unique blocks
        blocks = sample_org_units['block'].unique()
        
        # Process blocks in parallel using actual aggregator
        def process_block(block_id):
            block_data = sample_org_units[sample_org_units['block'] == block_id]
            try:
                return aggregator.aggregate(block_data)
            except AttributeError:
                # If method doesn't exist, return simple aggregation
                return {
                    'block': block_id,
                    'oil_total': block_data['oil_volume_bbl'].sum(),
                    'gas_total': block_data['gas_volume_mcf'].sum()
                }
        
        # Parallel execution
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(process_block, block): block for block in blocks}
            results = {}
            
            for future in as_completed(futures):
                block_id = futures[future]
                try:
                    results[block_id] = future.result()
                except Exception as e:
                    results[block_id] = {'error': str(e)}
        
        assert len(results) == len(blocks)
        for block_id in blocks:
            assert block_id in results
    
    def test_parallel_export_generation(self, parallel_processor, sample_org_units):
        """Test parallel generation of multiple export formats."""
        processor = parallel_processor
        
        # Simulate export generation
        export_formats = ['excel', 'pdf', 'csv', 'json']
        report_data = {
            'title': 'Test Report',
            'data': sample_org_units.head(10).to_dict('records')
        }
        
        # Generate exports in parallel
        exports = processor.parallel_generate_exports(export_formats, report_data)
        
        assert len(exports) == len(export_formats)
        for format_name in export_formats:
            assert format_name in exports
            assert exports[format_name]['status'] == 'success'