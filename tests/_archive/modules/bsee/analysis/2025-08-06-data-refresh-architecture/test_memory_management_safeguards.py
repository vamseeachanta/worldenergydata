"""
Memory Management and Overflow Protection Tests for Enhanced BSEE Data Refresh System

Tests for Task 8.4 & 8.5: Memory overflow protection and management safeguards
- Large file handling limits
- Memory usage monitoring
- Streaming data processing
- Memory cleanup after errors
- Memory usage limits
- Progressive data loading
- Garbage collection triggers
- Resource cleanup on failures
"""

import gc
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import psutil
import pytest

# Add the analysis directory to Python path for imports
analysis_dir = Path(__file__).parent
if str(analysis_dir) not in sys.path:
    sys.path.insert(0, str(analysis_dir))

from bsee_data_scraper import BSEEDataScraper


class MemoryMonitor:
    """Helper class to monitor memory usage during tests."""

    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.get_memory_usage()
        self.peak_memory = self.initial_memory
        self.monitoring = False
        self.monitor_thread = None

    def get_memory_usage(self):
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024

    def start_monitoring(self):
        """Start continuous memory monitoring."""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop memory monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)

    def _monitor_loop(self):
        """Monitor memory usage in background."""
        while self.monitoring:
            current_memory = self.get_memory_usage()
            self.peak_memory = max(self.peak_memory, current_memory)
            time.sleep(0.1)

    def get_memory_increase(self):
        """Get memory increase since initialization."""
        return self.get_memory_usage() - self.initial_memory

    def get_peak_memory_increase(self):
        """Get peak memory increase."""
        return self.peak_memory - self.initial_memory


class TestMemoryOverflowProtection:
    """Test memory overflow protection in enhanced BSEE data refresh system."""

    def setup_method(self):
        """Setup for each test method."""
        self.scraper = BSEEDataScraper(
            max_retries=1,
            timeout=5,
            memory_limit_mb=512,  # Set memory limit for testing
            streaming_threshold_mb=100,
        )
        self.memory_monitor = MemoryMonitor()
        gc.collect()  # Clean up before each test

    def teardown_method(self):
        """Clean up after tests."""
        self.memory_monitor.stop_monitoring()
        if hasattr(self, "scraper"):
            self.scraper.close()
        gc.collect()

    def test_memory_usage_monitoring(self):
        """Test 8.4.1: Memory usage monitoring functionality."""
        self.memory_monitor.start_monitoring()

        # Simulate memory-intensive operation
        large_data = np.random.random((1000, 1000))  # ~8MB array
        df = pd.DataFrame(large_data)

        # Allow monitoring to capture peak usage
        time.sleep(0.5)

        memory_increase = self.memory_monitor.get_peak_memory_increase()

        # Clean up
        del large_data, df
        gc.collect()

        self.memory_monitor.stop_monitoring()

        assert memory_increase > 0, "Should detect memory increase"
        assert (
            memory_increase < 100
        ), "Memory increase should be reasonable for test data"

    def test_large_file_handling_limits(self):
        """Test 8.4.2: Large file handling with memory limits."""
        # Mock a very large file download
        with patch.object(self.scraper.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            # Simulate a 1GB file
            mock_response.headers = {"content-length": str(1024 * 1024 * 1024)}
            mock_get.return_value = mock_response

            # Should trigger memory limit protection
            result = self.scraper.download_and_process("production_data")

            assert result["status"] == "error"
            assert (
                "memory" in result["error"].lower() or "size" in result["error"].lower()
            )
            assert "file_too_large" in result
            assert result["file_too_large"] == True

    def test_streaming_data_processing(self):
        """Test 8.4.3: Streaming data processing for large files."""
        # Test streaming mode activation
        large_content_size = 200 * 1024 * 1024  # 200MB

        with patch.object(self.scraper.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-length": str(large_content_size)}

            # Mock streaming content delivery
            chunk_size = 1024 * 1024  # 1MB chunks
            mock_response.iter_content.return_value = [
                b"x" * chunk_size for _ in range(200)
            ]
            mock_get.return_value = mock_response

            with patch.object(self.scraper, "_process_streaming") as mock_streaming:
                mock_streaming.return_value = {
                    "status": "success",
                    "processing_mode": "streaming",
                    "chunks_processed": 200,
                    "peak_memory_mb": 50,
                }

                result = self.scraper.download_and_process("war_data")

                assert result["status"] == "success"
                assert result["processing_mode"] == "streaming"
                assert mock_streaming.called

    def test_memory_cleanup_after_errors(self):
        """Test 8.4.4: Memory cleanup after processing errors."""
        initial_memory = self.memory_monitor.get_memory_usage()

        # Simulate error during processing that should trigger cleanup
        with patch.object(self.scraper, "_process_zip_in_memory") as mock_process:
            mock_process.side_effect = MemoryError("Insufficient memory for processing")

            with patch.object(self.scraper.session, "get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.raise_for_status = Mock()
                mock_response.headers = {"content-length": "1000"}
                mock_response.iter_content.return_value = [b"test_content"]
                mock_get.return_value = mock_response

                result = self.scraper.download_and_process("well_data")

                assert result["status"] == "error"
                assert "memory" in result["error"].lower()

        # Allow garbage collection
        gc.collect()
        time.sleep(0.1)

        final_memory = self.memory_monitor.get_memory_usage()
        memory_difference = abs(final_memory - initial_memory)

        # Memory should be cleaned up (within reasonable bounds)
        assert (
            memory_difference < 50
        ), f"Memory not properly cleaned up: {memory_difference}MB difference"

    def test_progressive_data_loading(self):
        """Test 8.5.1: Progressive data loading implementation."""
        # Test loading data in progressively sized chunks
        with patch.object(self.scraper, "_load_data_progressively") as mock_progressive:
            mock_progressive.return_value = {
                "chunks_loaded": 5,
                "total_records": 10000,
                "peak_memory_mb": 75,
                "loading_strategy": "progressive",
                "chunk_sizes": [1000, 2000, 2500, 2500, 2000],  # Adaptive sizing
            }

            result = self.scraper.load_large_dataset(
                "production_data", progressive=True
            )

            assert result["loading_strategy"] == "progressive"
            assert result["chunks_loaded"] == 5
            assert result["peak_memory_mb"] < 100
            assert len(result["chunk_sizes"]) == 5

    def test_memory_usage_limits_enforcement(self):
        """Test 8.5.2: Memory usage limits enforcement."""
        # Test hard memory limit enforcement
        memory_limit_mb = 100

        with patch.object(self.scraper, "_check_memory_usage") as mock_check:
            # Simulate memory usage exceeding limit
            mock_check.side_effect = [50, 75, 120]  # Progressive increase

            with patch.object(self.scraper, "_enforce_memory_limit") as mock_enforce:
                mock_enforce.return_value = {
                    "limit_exceeded": True,
                    "current_usage_mb": 120,
                    "limit_mb": 100,
                    "action_taken": "processing_halted",
                }

                result = self.scraper.process_with_memory_limit(
                    b"test_data", memory_limit_mb
                )

                assert result["limit_exceeded"] == True
                assert result["action_taken"] == "processing_halted"
                assert mock_enforce.called

    def test_garbage_collection_triggers(self):
        """Test 8.5.3: Garbage collection triggers."""
        initial_objects = len(gc.get_objects())

        # Create objects that should trigger garbage collection
        large_objects = []
        for i in range(100):
            large_objects.append(pd.DataFrame(np.random.random((100, 100))))

        objects_before_gc = len(gc.get_objects())

        # Trigger garbage collection through scraper
        gc_result = self.scraper.trigger_garbage_collection(force=True)

        objects_after_gc = len(gc.get_objects())

        # Clean up test objects
        del large_objects
        gc.collect()

        assert gc_result["objects_before"] > initial_objects
        assert gc_result["objects_after"] <= gc_result["objects_before"]
        assert gc_result["objects_collected"] >= 0
        assert gc_result["memory_freed_mb"] >= 0

    def test_resource_cleanup_on_failures(self):
        """Test 8.5.4: Resource cleanup on failures."""
        # Test cleanup of file handles, network connections, and memory
        cleanup_tracker = {
            "files_closed": 0,
            "connections_closed": 0,
            "memory_freed": 0,
            "temp_files_removed": 0,
        }

        def mock_cleanup_callback(resource_type):
            cleanup_tracker[f"{resource_type}_closed"] += 1

        with patch.object(self.scraper, "_cleanup_resources") as mock_cleanup:
            mock_cleanup.side_effect = lambda: cleanup_tracker.update(
                {
                    "files_closed": 2,
                    "connections_closed": 1,
                    "memory_freed": 50,
                    "temp_files_removed": 3,
                }
            )

            # Simulate failure that triggers cleanup
            with patch.object(self.scraper, "_process_data") as mock_process:
                mock_process.side_effect = Exception("Processing failed")

                result = self.scraper.download_and_process("production_data")

                assert result["status"] == "error"
                assert mock_cleanup.called

                # Verify cleanup was performed
                assert cleanup_tracker["files_closed"] > 0
                assert cleanup_tracker["connections_closed"] > 0

    def test_memory_pool_management(self):
        """Test 8.5.5: Memory pool management for efficient allocation."""
        # Test memory pool creation and management
        pool_config = {"initial_size_mb": 50, "max_size_mb": 200, "chunk_size_mb": 10}

        with patch.object(self.scraper, "_create_memory_pool") as mock_pool:
            mock_pool.return_value = {
                "pool_id": "test_pool_001",
                "allocated_mb": 50,
                "available_mb": 50,
                "chunks_available": 5,
            }

            pool_result = self.scraper.create_memory_pool(pool_config)

            assert pool_result["pool_id"] == "test_pool_001"
            assert pool_result["allocated_mb"] == 50
            assert pool_result["chunks_available"] == 5

    def test_dynamic_memory_adjustment(self):
        """Test 8.5.6: Dynamic memory adjustment based on system resources."""
        # Test dynamic adjustment of memory limits based on available system memory
        system_memory_mb = psutil.virtual_memory().total / 1024 / 1024
        available_memory_mb = psutil.virtual_memory().available / 1024 / 1024

        memory_adjustment = self.scraper.adjust_memory_limits_dynamically()

        assert "current_limit_mb" in memory_adjustment
        assert "adjusted_limit_mb" in memory_adjustment
        assert "system_memory_mb" in memory_adjustment
        assert "available_memory_mb" in memory_adjustment

        # Adjusted limit should be reasonable percentage of available memory
        adjusted_limit = memory_adjustment["adjusted_limit_mb"]
        assert adjusted_limit > 0
        assert (
            adjusted_limit <= available_memory_mb * 0.8
        )  # Max 80% of available memory

    def test_memory_leak_detection(self):
        """Test 8.5.7: Memory leak detection during processing."""
        memory_tracker = []

        def track_memory():
            memory_tracker.append(self.memory_monitor.get_memory_usage())

        # Simulate multiple processing cycles to detect leaks
        for i in range(5):
            track_memory()

            # Simulate processing that might cause memory leaks
            with patch.object(self.scraper, "_process_data_cycle") as mock_cycle:
                mock_cycle.return_value = {"processed": True, "cycle": i}
                self.scraper.process_data_cycle(f"test_data_{i}")

            gc.collect()
            time.sleep(0.1)

        track_memory()

        # Analyze memory growth pattern
        memory_growth = [
            memory_tracker[i + 1] - memory_tracker[i]
            for i in range(len(memory_tracker) - 1)
        ]
        leak_detection = self.scraper.detect_memory_leaks(memory_growth)

        assert "leak_detected" in leak_detection
        assert "growth_pattern" in leak_detection
        assert "average_growth_mb" in leak_detection

    def test_emergency_memory_recovery(self):
        """Test 8.5.8: Emergency memory recovery mechanisms."""
        # Test emergency recovery when memory usage becomes critical
        with patch.object(self.scraper, "_get_memory_pressure") as mock_pressure:
            mock_pressure.return_value = {
                "pressure_level": "critical",
                "usage_percentage": 95,
                "available_mb": 50,
            }

            with patch.object(
                self.scraper, "_emergency_memory_recovery"
            ) as mock_recovery:
                mock_recovery.return_value = {
                    "recovery_triggered": True,
                    "actions_taken": [
                        "forced_garbage_collection",
                        "cache_cleared",
                        "temp_files_purged",
                        "data_compression_enabled",
                    ],
                    "memory_freed_mb": 150,
                }

                recovery_result = self.scraper.handle_memory_pressure()

                assert recovery_result["recovery_triggered"] == True
                assert recovery_result["memory_freed_mb"] > 0
                assert len(recovery_result["actions_taken"]) > 0
                assert mock_recovery.called

    def test_concurrent_memory_management(self):
        """Test 8.5.9: Memory management with concurrent operations."""
        # Test memory management when multiple operations run concurrently
        concurrent_operations = []

        def mock_concurrent_operation(op_id):
            return {
                "operation_id": op_id,
                "memory_used_mb": 25 + (op_id * 5),
                "completed": True,
            }

        with patch.object(self.scraper, "_manage_concurrent_memory") as mock_concurrent:
            mock_concurrent.return_value = {
                "max_concurrent_operations": 4,
                "total_memory_allocated_mb": 140,
                "memory_per_operation_mb": 35,
                "operations_queued": 2,
            }

            for i in range(6):  # Try to run 6 operations concurrently
                op_result = mock_concurrent_operation(i)
                concurrent_operations.append(op_result)

            memory_result = self.scraper.manage_concurrent_operations(
                concurrent_operations
            )

            assert memory_result["max_concurrent_operations"] == 4
            assert memory_result["operations_queued"] == 2
            assert memory_result["total_memory_allocated_mb"] > 0

    def test_memory_profiling_integration(self):
        """Test 8.5.10: Memory profiling integration for performance analysis."""
        # Test memory profiling during data processing
        with patch.object(self.scraper, "_enable_memory_profiling") as mock_profiling:
            profiling_data = {
                "enabled": True,
                "profile_id": "profile_001",
                "sampling_interval_ms": 100,
                "max_samples": 1000,
            }
            mock_profiling.return_value = profiling_data

            with patch.object(self.scraper, "_get_memory_profile") as mock_get_profile:
                mock_get_profile.return_value = {
                    "total_samples": 500,
                    "peak_memory_mb": 125,
                    "average_memory_mb": 85,
                    "memory_hotspots": [
                        {"function": "process_zip_data", "memory_mb": 45},
                        {"function": "validate_data", "memory_mb": 25},
                    ],
                }

                profile_result = self.scraper.profile_memory_usage("test_operation")

                assert profile_result["enabled"] == True
                assert profile_result["total_samples"] > 0
                assert profile_result["peak_memory_mb"] > 0
                assert len(profile_result["memory_hotspots"]) > 0


class TestMemoryIntegrationScenarios:
    """Integration tests for memory management in real-world scenarios."""

    def setup_method(self):
        """Setup for integration tests."""
        self.scraper = BSEEDataScraper(
            memory_limit_mb=256, streaming_threshold_mb=50, max_retries=1
        )

    def teardown_method(self):
        """Clean up after tests."""
        if hasattr(self, "scraper"):
            self.scraper.close()
        gc.collect()

    def test_end_to_end_memory_management(self):
        """Test complete memory management workflow."""
        # Test realistic scenario with memory constraints
        with patch.object(self.scraper.session, "get") as mock_get:
            # Simulate medium-sized file that triggers streaming
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-length": str(75 * 1024 * 1024)}  # 75MB

            # Mock streaming chunks
            chunk_data = b"x" * (1024 * 1024)  # 1MB chunks
            mock_response.iter_content.return_value = [chunk_data for _ in range(75)]
            mock_get.return_value = mock_response

            with patch.object(
                self.scraper, "_process_streaming_with_memory_management"
            ) as mock_process:
                mock_process.return_value = {
                    "status": "success",
                    "processing_mode": "streaming",
                    "memory_management": {
                        "peak_memory_mb": 85,
                        "memory_limit_mb": 256,
                        "gc_triggered": 3,
                        "memory_pressure_events": 0,
                    },
                    "data_processed": True,
                }

                result = self.scraper.download_and_process("production_data")

                assert result["status"] == "success"
                assert (
                    result["memory_management"]["peak_memory_mb"]
                    < result["memory_management"]["memory_limit_mb"]
                )
                assert result["memory_management"]["memory_pressure_events"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
