"""Tests for SODIR parallel processing module."""

import multiprocessing as mp
from unittest.mock import MagicMock

from worldenergydata.sodir.parallel import (
    ProcessingResult,
    SodirParallelProcessor,
)


class TestProcessingResult:
    def test_defaults(self):
        pr = ProcessingResult(
            entity_id="e1",
            entity_type="blocks",
            data={"key": "val"},
            processing_time=1.5,
        )
        assert pr.entity_id == "e1"
        assert pr.entity_type == "blocks"
        assert pr.data == {"key": "val"}
        assert pr.processing_time == 1.5
        assert pr.success is True
        assert pr.error is None
        assert pr.cached is False

    def test_failed_result(self):
        pr = ProcessingResult(
            entity_id="e2",
            entity_type="fields",
            data=None,
            processing_time=0.1,
            success=False,
            error="timeout",
        )
        assert pr.success is False
        assert pr.error == "timeout"
        assert pr.data is None

    def test_cached_result(self):
        pr = ProcessingResult(
            entity_id="e3",
            entity_type="wellbores",
            data=[],
            processing_time=0.01,
            cached=True,
        )
        assert pr.cached is True


class TestSodirParallelProcessorInit:
    def test_defaults(self):
        sp = SodirParallelProcessor()
        assert sp.max_workers == mp.cpu_count()
        assert sp.use_threads is True
        assert sp.api_client is None
        assert sp.stats["total_processed"] == 0
        assert sp.stats["successful"] == 0
        assert sp.stats["failed"] == 0
        assert sp.stats["cache_hits"] == 0
        assert sp.stats["total_time"] == 0.0

    def test_custom_workers(self):
        sp = SodirParallelProcessor(max_workers=2, use_threads=False)
        assert sp.max_workers == 2
        assert sp.use_threads is False

    def test_with_api_client(self):
        client = MagicMock()
        sp = SodirParallelProcessor(api_client=client)
        assert sp.api_client is client


class TestGetExecutor:
    def test_thread_executor(self):
        sp = SodirParallelProcessor(max_workers=2, use_threads=True)
        executor = sp.get_executor()
        assert executor is not None
        executor.shutdown(wait=False)

    def test_process_executor(self):
        sp = SodirParallelProcessor(max_workers=2, use_threads=False)
        executor = sp.get_executor()
        assert executor is not None
        executor.shutdown(wait=False)

    def test_override_threads(self):
        sp = SodirParallelProcessor(max_workers=2, use_threads=False)
        executor = sp.get_executor(use_threads=True)
        assert executor is not None
        executor.shutdown(wait=False)


class TestGetStatistics:
    def test_initial(self):
        sp = SodirParallelProcessor()
        stats = sp.get_statistics()
        assert stats["total_processed"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
        assert stats["cache_hit_rate"] == 0
        assert stats["success_rate"] == 0
        assert stats["avg_processing_time"] == 0

    def test_with_data(self):
        sp = SodirParallelProcessor()
        sp.stats["total_processed"] = 10
        sp.stats["successful"] = 8
        sp.stats["failed"] = 2
        sp.stats["cache_hits"] = 3
        sp.stats["total_time"] = 5.0
        stats = sp.get_statistics()
        assert stats["cache_hit_rate"] == 0.3
        assert stats["success_rate"] == 0.8
        assert stats["avg_processing_time"] == 0.5


class TestResetStatistics:
    def test_reset(self):
        sp = SodirParallelProcessor()
        sp.stats["total_processed"] = 100
        sp.stats["successful"] = 90
        sp.stats["failed"] = 10
        sp.stats["cache_hits"] = 20
        sp.stats["total_time"] = 50.0
        sp.reset_statistics()
        assert sp.stats["total_processed"] == 0
        assert sp.stats["successful"] == 0
        assert sp.stats["failed"] == 0
        assert sp.stats["cache_hits"] == 0
        assert sp.stats["total_time"] == 0.0


class TestProcessBlocks:
    def test_basic(self):
        sp = SodirParallelProcessor()
        data = [
            {"quadrantId": "Q1", "name": "b1"},
            {"quadrantId": "Q1", "name": "b2"},
            {"quadrantId": "Q2", "name": "b3"},
        ]
        result = sp._process_blocks(data)
        assert result["processed"] == 3
        assert result["type"] == "blocks"
        assert result["summary"]["total_blocks"] == 3
        assert result["summary"]["quadrants"] == 2

    def test_empty(self):
        sp = SodirParallelProcessor()
        result = sp._process_blocks([])
        assert result["processed"] == 0
        assert result["summary"]["total_blocks"] == 0


class TestProcessWellbores:
    def test_basic(self):
        sp = SodirParallelProcessor()
        data = [
            {"status": "ACTIVE"},
            {"status": "ACTIVE"},
            {"status": "P&A"},
        ]
        result = sp._process_wellbores(data)
        assert result["processed"] == 3
        assert result["type"] == "wellbores"
        assert result["summary"]["total_wellbores"] == 3
        assert result["summary"]["active"] == 2


class TestProcessFields:
    def test_basic(self):
        sp = SodirParallelProcessor()
        data = [
            {"originalOilInPlaceSm3": 100},
            {"originalOilInPlaceSm3": 0},
        ]
        result = sp._process_fields(data)
        assert result["processed"] == 2
        assert result["summary"]["total_fields"] == 2
        assert result["summary"]["with_production"] == 1


class TestProcessDiscoveries:
    def test_basic(self):
        sp = SodirParallelProcessor()
        data = [{"name": "d1"}, {"name": "d2"}]
        result = sp._process_discoveries(data)
        assert result["processed"] == 2
        assert result["summary"]["total_discoveries"] == 2


class TestProcessSurveys:
    def test_basic(self):
        sp = SodirParallelProcessor()
        data = [{"survey": "s1"}]
        result = sp._process_surveys(data)
        assert result["processed"] == 1
        assert result["summary"]["total_surveys"] == 1


class TestFetchSingleEndpoint:
    def test_no_client_returns_mock(self):
        sp = SodirParallelProcessor()
        result = sp._fetch_single_endpoint("blocks", {}, False)
        assert result.success is True
        assert result.data == {"mock": True, "endpoint": "blocks"}
        assert result.entity_type == "blocks"

    def test_with_client_blocks(self):
        client = MagicMock()
        client.get_blocks.return_value = [{"b": 1}]
        sp = SodirParallelProcessor(api_client=client)
        result = sp._fetch_single_endpoint("blocks", {"limit": 10}, False)
        assert result.success is True
        assert result.data == [{"b": 1}]

    def test_with_client_wellbores(self):
        client = MagicMock()
        client.get_wellbores.return_value = []
        sp = SodirParallelProcessor(api_client=client)
        result = sp._fetch_single_endpoint("wellbores", {}, False)
        assert result.success is True

    def test_with_client_fields(self):
        client = MagicMock()
        client.get_fields.return_value = [{"f": 1}]
        sp = SodirParallelProcessor(api_client=client)
        result = sp._fetch_single_endpoint("fields", {}, False)
        assert result.success is True

    def test_with_client_discoveries(self):
        client = MagicMock()
        client.get_discoveries.return_value = []
        sp = SodirParallelProcessor(api_client=client)
        result = sp._fetch_single_endpoint("discoveries", {}, False)
        assert result.success is True

    def test_with_client_surveys(self):
        client = MagicMock()
        client.get_surveys.return_value = []
        sp = SodirParallelProcessor(api_client=client)
        result = sp._fetch_single_endpoint("surveys", {}, False)
        assert result.success is True

    def test_unknown_endpoint_error(self):
        client = MagicMock()
        sp = SodirParallelProcessor(api_client=client)
        result = sp._fetch_single_endpoint("unknown", {}, False)
        assert result.success is False
        assert "Unknown endpoint" in result.error

    def test_cache_hit(self):
        client = MagicMock()
        client.cache.get.return_value = {"cached": True}
        sp = SodirParallelProcessor(api_client=client)
        result = sp._fetch_single_endpoint("blocks", {}, True)
        assert result.cached is True
        assert result.data == {"cached": True}
        assert sp.stats["cache_hits"] == 1

    def test_cache_miss_then_fetch(self):
        client = MagicMock()
        client.cache.get.return_value = None
        client.get_blocks.return_value = [{"live": True}]
        sp = SodirParallelProcessor(api_client=client)
        result = sp._fetch_single_endpoint("blocks", {}, True)
        assert result.cached is False
        assert result.data == [{"live": True}]
        client.cache.set.assert_called_once()


class TestProcessBatch:
    def test_success(self):
        sp = SodirParallelProcessor()
        processor = lambda data: [d * 2 for d in data]
        result = sp._process_batch("test", [1, 2, 3], processor)
        assert result.success is True
        assert result.data == [2, 4, 6]
        assert result.entity_type == "test"

    def test_error(self):
        sp = SodirParallelProcessor()
        def bad_proc(data):
            raise RuntimeError("broken")
        result = sp._process_batch("test", [1], bad_proc)
        assert result.success is False
        assert "broken" in result.error


# ---------------------------------------------------------------------------
# parallel_api_fetch
# ---------------------------------------------------------------------------

class TestParallelApiFetch:
    def test_basic_fetch(self):
        sp = SodirParallelProcessor(max_workers=2)
        endpoints = [
            ("blocks", {"limit": 10}),
            ("fields", {"limit": 5}),
        ]
        results = sp.parallel_api_fetch(endpoints)
        assert len(results) == 2
        assert sp.stats["total_processed"] == 2
        # Without a real client, these return mock data
        for r in results:
            assert r.success is True

    def test_fetch_with_client(self):
        client = MagicMock()
        client.get_blocks.return_value = [{"b": 1}]
        client.get_fields.return_value = [{"f": 1}]
        sp = SodirParallelProcessor(max_workers=2, api_client=client)
        endpoints = [("blocks", {}), ("fields", {})]
        results = sp.parallel_api_fetch(endpoints)
        assert len(results) == 2
        assert all(r.success for r in results)


# ---------------------------------------------------------------------------
# parallel_process_data
# ---------------------------------------------------------------------------

class TestParallelProcessData:
    def test_basic_processing(self):
        sp = SodirParallelProcessor(max_workers=2)
        data_batches = [
            ("blocks", [{"quadrantId": "Q1", "name": "b1"}]),
            ("fields", [{"originalOilInPlaceSm3": 100}]),
        ]
        processor_map = {
            "blocks": sp._process_blocks,
            "fields": sp._process_fields,
        }
        results = sp.parallel_process_data(data_batches, processor_map)
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_missing_processor_skipped(self):
        sp = SodirParallelProcessor(max_workers=2)
        data_batches = [
            ("blocks", [{"quadrantId": "Q1", "name": "b1"}]),
            ("unknown_type", [{"data": 1}]),
        ]
        processor_map = {
            "blocks": sp._process_blocks,
        }
        results = sp.parallel_process_data(data_batches, processor_map)
        assert len(results) == 1  # Only blocks processed


# ---------------------------------------------------------------------------
# parallel_collection_workflow
# ---------------------------------------------------------------------------

class TestParallelCollectionWorkflow:
    def test_basic_workflow(self):
        sp = SodirParallelProcessor(max_workers=2)
        configs = [
            {"data_type": "blocks", "params": {}},
            {"data_type": "fields", "params": {}},
        ]
        result = sp.parallel_collection_workflow(configs)
        assert "fetch_results" in result
        assert "process_results" in result
        assert "statistics" in result
        assert result["statistics"]["total_endpoints"] == 2

    def test_workflow_with_discoveries_and_surveys(self):
        sp = SodirParallelProcessor(max_workers=2)
        configs = [
            {"data_type": "discoveries", "params": {}},
            {"data_type": "surveys", "params": {}},
            {"data_type": "wellbores", "params": {}},
        ]
        result = sp.parallel_collection_workflow(configs)
        assert result["statistics"]["total_endpoints"] == 3


# ---------------------------------------------------------------------------
# map_reduce_analysis
# ---------------------------------------------------------------------------

class TestMapReduceAnalysis:
    def test_basic_map_reduce(self):
        sp = SodirParallelProcessor(max_workers=2)
        data = [{"value": i} for i in range(10)]
        map_func = lambda chunk: sum(d["value"] for d in chunk)
        reduce_func = lambda results: sum(results)
        result = sp.map_reduce_analysis(data, map_func, reduce_func, chunk_size=3)
        assert result == 45  # sum(0..9)

    def test_empty_data(self):
        sp = SodirParallelProcessor(max_workers=2)
        result = sp.map_reduce_analysis(
            [], lambda x: x, lambda x: x, chunk_size=3
        )
        assert result is None

    def test_single_chunk(self):
        sp = SodirParallelProcessor(max_workers=2)
        data = [{"v": 1}, {"v": 2}]
        result = sp.map_reduce_analysis(
            data,
            lambda chunk: len(chunk),
            lambda results: sum(results),
            chunk_size=100,
        )
        assert result == 2
