"""Tests for SODIR batch processing module."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from worldenergydata.sodir.batch import (
    BatchConfig,
    BatchResult,
    BatchStatus,
    SodirBatchProcessor,
)


class TestBatchStatus:
    def test_all_values(self):
        assert BatchStatus.PENDING.value == "pending"
        assert BatchStatus.PROCESSING.value == "processing"
        assert BatchStatus.COMPLETED.value == "completed"
        assert BatchStatus.FAILED.value == "failed"
        assert BatchStatus.PARTIAL.value == "partial"

    def test_count(self):
        assert len(BatchStatus) == 5


class TestBatchConfig:
    def test_defaults(self):
        cfg = BatchConfig()
        assert cfg.batch_size == 100
        assert cfg.max_workers == 4
        assert cfg.use_parallel is True
        assert cfg.timeout_seconds == 300
        assert cfg.retry_failed is True
        assert cfg.max_retries == 3
        assert cfg.save_intermediate is True
        assert cfg.output_format == "json"
        assert cfg.compression is False

    def test_custom(self):
        cfg = BatchConfig(batch_size=50, max_workers=8, use_parallel=False)
        assert cfg.batch_size == 50
        assert cfg.max_workers == 8
        assert cfg.use_parallel is False


class TestBatchResult:
    def test_defaults(self):
        br = BatchResult(
            batch_id="test_1",
            status=BatchStatus.PENDING,
            total_items=10,
            processed_items=0,
        )
        assert br.batch_id == "test_1"
        assert br.status == BatchStatus.PENDING
        assert br.total_items == 10
        assert br.processed_items == 0
        assert br.failed_items == 0
        assert br.errors == []
        assert br.output_files == []
        assert br.metadata == {}
        assert br.end_time is None
        assert br.processing_time == 0.0

    def test_to_dict_basic(self):
        br = BatchResult(
            batch_id="test_2",
            status=BatchStatus.COMPLETED,
            total_items=5,
            processed_items=5,
        )
        d = br.to_dict()
        assert d["batch_id"] == "test_2"
        assert d["status"] == "completed"
        assert d["total_items"] == 5
        assert d["processed_items"] == 5
        assert d["end_time"] is None
        assert isinstance(d["start_time"], str)

    def test_to_dict_with_end_time(self):
        end = datetime(2024, 6, 15, 12, 0, 0)
        br = BatchResult(
            batch_id="test_3",
            status=BatchStatus.COMPLETED,
            total_items=1,
            processed_items=1,
            end_time=end,
        )
        d = br.to_dict()
        assert d["end_time"] == end.isoformat()

    def test_to_dict_with_errors(self):
        br = BatchResult(
            batch_id="test_4",
            status=BatchStatus.PARTIAL,
            total_items=3,
            processed_items=1,
            failed_items=2,
            errors=["err1", "err2"],
        )
        d = br.to_dict()
        assert d["errors"] == ["err1", "err2"]
        assert d["failed_items"] == 2

    def test_to_dict_with_metadata(self):
        br = BatchResult(
            batch_id="test_5",
            status=BatchStatus.COMPLETED,
            total_items=1,
            processed_items=1,
            metadata={"key": "value"},
        )
        d = br.to_dict()
        assert d["metadata"] == {"key": "value"}


class TestSodirBatchProcessorInit:
    def test_default_config(self):
        bp = SodirBatchProcessor()
        assert isinstance(bp.config, BatchConfig)
        assert bp.config.batch_size == 100
        assert bp.current_batch is None
        assert bp.batch_history == []
        assert bp.processors == {}
        assert "json" in bp.formatters
        assert "csv" in bp.formatters

    def test_custom_config(self):
        cfg = BatchConfig(batch_size=50, max_workers=2)
        bp = SodirBatchProcessor(config=cfg)
        assert bp.config.batch_size == 50
        assert bp.config.max_workers == 2


class TestRegisterProcessorAndFormatter:
    def test_register_processor(self):
        bp = SodirBatchProcessor()
        func = lambda x: x
        bp.register_processor("test", func)
        assert "test" in bp.processors
        assert bp.processors["test"] is func

    def test_register_formatter(self):
        bp = SodirBatchProcessor()
        func = lambda x: str(x)
        bp.register_formatter("xml", func)
        assert "xml" in bp.formatters


class TestGetBatchStatus:
    def test_not_found(self):
        bp = SodirBatchProcessor()
        assert bp.get_batch_status("nonexistent") is None

    def test_found(self):
        bp = SodirBatchProcessor()
        br = BatchResult(
            batch_id="b1",
            status=BatchStatus.COMPLETED,
            total_items=1,
            processed_items=1,
        )
        bp.batch_history.append(br)
        result = bp.get_batch_status("b1")
        assert result is br

    def test_multiple_batches(self):
        bp = SodirBatchProcessor()
        br1 = BatchResult(
            batch_id="b1",
            status=BatchStatus.COMPLETED,
            total_items=1,
            processed_items=1,
        )
        br2 = BatchResult(
            batch_id="b2", status=BatchStatus.FAILED, total_items=2, processed_items=0
        )
        bp.batch_history.extend([br1, br2])
        assert bp.get_batch_status("b2") is br2


class TestGetCurrentStatus:
    def test_none_when_idle(self):
        bp = SodirBatchProcessor()
        assert bp.get_current_status() is None

    def test_returns_current(self):
        bp = SodirBatchProcessor()
        br = BatchResult(
            batch_id="c1",
            status=BatchStatus.PROCESSING,
            total_items=5,
            processed_items=0,
        )
        bp.current_batch = br
        assert bp.get_current_status() is br


class TestGetStatistics:
    def test_empty_history(self):
        bp = SodirBatchProcessor()
        stats = bp.get_statistics()
        assert stats["total_batches"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_processing_time"] == 0.0

    def test_with_history(self):
        bp = SodirBatchProcessor()
        bp.batch_history = [
            BatchResult(
                batch_id="b1",
                status=BatchStatus.COMPLETED,
                total_items=10,
                processed_items=10,
                processing_time=5.0,
            ),
            BatchResult(
                batch_id="b2",
                status=BatchStatus.FAILED,
                total_items=5,
                processed_items=0,
                processing_time=2.0,
            ),
            BatchResult(
                batch_id="b3",
                status=BatchStatus.PARTIAL,
                total_items=8,
                processed_items=4,
                processing_time=3.0,
            ),
        ]
        stats = bp.get_statistics()
        assert stats["total_batches"] == 3
        assert stats["successful_batches"] == 1
        assert stats["failed_batches"] == 1
        assert stats["partial_batches"] == 1
        assert stats["success_rate"] == 1 / 3
        assert stats["total_items_processed"] == 14
        assert stats["avg_processing_time"] == 10.0 / 3
        assert stats["total_processing_time"] == 10.0


class TestCreateChunks:
    def test_even_split(self):
        bp = SodirBatchProcessor()
        chunks = bp._create_chunks([1, 2, 3, 4], 2)
        assert chunks == [[1, 2], [3, 4]]

    def test_uneven_split(self):
        bp = SodirBatchProcessor()
        chunks = bp._create_chunks([1, 2, 3, 4, 5], 2)
        assert chunks == [[1, 2], [3, 4], [5]]

    def test_single_chunk(self):
        bp = SodirBatchProcessor()
        chunks = bp._create_chunks([1, 2, 3], 10)
        assert chunks == [[1, 2, 3]]

    def test_empty_data(self):
        bp = SodirBatchProcessor()
        chunks = bp._create_chunks([], 5)
        assert chunks == []


class TestSequentialCollection:
    def test_success(self):
        bp = SodirBatchProcessor()
        mock_client = MagicMock()
        mock_client.get_fields.return_value = [{"name": "f1"}]

        specs = [{"data_type": "fields", "params": {}}]
        results = bp._sequential_collection(mock_client, specs, Path("/tmp"))
        assert len(results) == 1
        spec, data, error = results[0]
        assert error is None
        assert data == [{"name": "f1"}]

    def test_failure(self):
        bp = SodirBatchProcessor()
        mock_client = MagicMock()
        mock_client.get_fields.side_effect = Exception("API down")

        specs = [{"data_type": "fields", "params": {}}]
        results = bp._sequential_collection(mock_client, specs, Path("/tmp"))
        assert len(results) == 1
        spec, data, error = results[0]
        assert error is not None
        assert "API down" in error


class TestCollectSingle:
    def test_blocks(self):
        bp = SodirBatchProcessor()
        client = MagicMock()
        client.get_blocks.return_value = [{"id": 1}]
        result = bp._collect_single(client, {"data_type": "blocks", "params": {}})
        client.get_blocks.assert_called_once()
        assert result == [{"id": 1}]

    def test_wellbores(self):
        bp = SodirBatchProcessor()
        client = MagicMock()
        client.get_wellbores.return_value = []
        bp._collect_single(client, {"data_type": "wellbores", "params": {}})
        client.get_wellbores.assert_called_once()

    def test_fields(self):
        bp = SodirBatchProcessor()
        client = MagicMock()
        client.get_fields.return_value = []
        bp._collect_single(client, {"data_type": "fields", "params": {}})
        client.get_fields.assert_called_once()

    def test_discoveries(self):
        bp = SodirBatchProcessor()
        client = MagicMock()
        client.get_discoveries.return_value = []
        bp._collect_single(client, {"data_type": "discoveries", "params": {}})
        client.get_discoveries.assert_called_once()

    def test_surveys(self):
        bp = SodirBatchProcessor()
        client = MagicMock()
        client.get_surveys.return_value = []
        bp._collect_single(client, {"data_type": "surveys", "params": {}})
        client.get_surveys.assert_called_once()

    def test_unknown_raises(self):
        bp = SodirBatchProcessor()
        client = MagicMock()
        try:
            bp._collect_single(client, {"data_type": "unknown"})
            assert False, "Should have raised"
        except ValueError as e:
            assert "Unknown data type" in str(e)


class TestSequentialTransform:
    def test_success(self):
        bp = SodirBatchProcessor()
        transform = lambda chunk: [x * 2 for x in chunk]
        chunks = [[1, 2], [3, 4]]
        results = bp._sequential_transform(chunks, transform)
        assert len(results) == 2
        assert results[0] == ([2, 4], None)
        assert results[1] == ([6, 8], None)

    def test_with_error(self):
        bp = SodirBatchProcessor()

        def bad_transform(chunk):
            raise ValueError("bad data")

        results = bp._sequential_transform([[1]], bad_transform)
        assert len(results) == 1
        assert results[0][0] is None
        assert "bad data" in results[0][1]


class TestDefaultFormatters:
    def test_json_formatter(self):
        bp = SodirBatchProcessor()
        data = [{"a": 1}]
        result = bp.formatters["json"](data)
        parsed = json.loads(result)
        assert parsed == [{"a": 1}]

    def test_csv_formatter_list_of_dicts(self):
        bp = SodirBatchProcessor()
        data = [{"name": "a", "val": 1}, {"name": "b", "val": 2}]
        result = bp.formatters["csv"](data)
        assert "name" in result
        assert "val" in result
        assert "a" in result
        assert "b" in result

    def test_csv_formatter_non_list(self):
        bp = SodirBatchProcessor()
        result = bp.formatters["csv"]("not a list")
        assert result == ""


class TestSaveBatchData:
    def test_json_save(self, tmp_path):
        bp = SodirBatchProcessor()
        data = [{"key": "value"}]
        result = bp._save_batch_data(data, "test", tmp_path)
        assert result is not None
        assert result.exists()
        assert result.suffix == ".json"
        content = json.loads(result.read_text())
        assert content == [{"key": "value"}]

    def test_unknown_format(self, tmp_path):
        cfg = BatchConfig(output_format="parquet")
        bp = SodirBatchProcessor(config=cfg)
        result = bp._save_batch_data([], "test", tmp_path)
        assert result is None


class TestProcessDataCollection:
    def test_sequential_all_success(self, tmp_path):
        cfg = BatchConfig(use_parallel=False, save_intermediate=False)
        bp = SodirBatchProcessor(config=cfg)
        client = MagicMock()
        client.get_fields.return_value = [{"f": 1}]
        client.get_wellbores.return_value = [{"w": 2}]

        specs = [
            {"data_type": "fields", "params": {}},
            {"data_type": "wellbores", "params": {}},
        ]
        result = bp.process_data_collection(client, specs, tmp_path)
        assert result.status == BatchStatus.COMPLETED
        assert result.processed_items == 2
        assert result.failed_items == 0
        assert result.end_time is not None
        assert result.processing_time > 0
        assert len(bp.batch_history) == 1
        assert bp.current_batch is None

    def test_sequential_with_failures(self, tmp_path):
        cfg = BatchConfig(use_parallel=False, save_intermediate=False)
        bp = SodirBatchProcessor(config=cfg)
        client = MagicMock()
        client.get_fields.return_value = [{"f": 1}]
        client.get_wellbores.side_effect = Exception("timeout")

        specs = [
            {"data_type": "fields", "params": {}},
            {"data_type": "wellbores", "params": {}},
        ]
        result = bp.process_data_collection(client, specs, tmp_path)
        assert result.status == BatchStatus.PARTIAL
        assert result.processed_items == 1
        assert result.failed_items == 1

    def test_all_fail(self, tmp_path):
        cfg = BatchConfig(use_parallel=False, save_intermediate=False)
        bp = SodirBatchProcessor(config=cfg)
        client = MagicMock()
        client.get_fields.side_effect = Exception("down")

        specs = [{"data_type": "fields", "params": {}}]
        result = bp.process_data_collection(client, specs, tmp_path)
        assert result.status == BatchStatus.FAILED
        assert result.processed_items == 0
        assert result.failed_items == 1


class TestProcessDataTransformation:
    def test_sequential_success(self, tmp_path):
        cfg = BatchConfig(use_parallel=False, batch_size=2, save_intermediate=False)
        bp = SodirBatchProcessor(config=cfg)

        transform = lambda items: [x * 2 for x in items]
        data = [1, 2, 3, 4]
        result = bp.process_data_transformation(data, transform, tmp_path)
        assert result.status == BatchStatus.COMPLETED
        assert result.processed_items == 4
        assert result.failed_items == 0

    def test_sequential_with_error(self, tmp_path):
        cfg = BatchConfig(use_parallel=False, batch_size=2, save_intermediate=False)
        bp = SodirBatchProcessor(config=cfg)

        call_count = 0

        def flaky_transform(items):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ValueError("bad")
            return items

        data = [1, 2, 3, 4]
        result = bp.process_data_transformation(data, flaky_transform, tmp_path)
        assert result.status == BatchStatus.PARTIAL


class TestExportSingleFormat:
    def test_known_format(self, tmp_path):
        bp = SodirBatchProcessor()
        data = [{"a": 1}]
        result = bp._export_single_format(data, "json", tmp_path, "export")
        assert result is not None
        assert result.exists()

    def test_unknown_format(self, tmp_path):
        bp = SodirBatchProcessor()
        result = bp._export_single_format([], "parquet", tmp_path, "export")
        assert result is None


class TestProcessMultiFormatExport:
    def test_sequential_json(self, tmp_path):
        cfg = BatchConfig(use_parallel=False)
        bp = SodirBatchProcessor(config=cfg)
        data = [{"x": 1}]
        result = bp.process_multi_format_export(data, ["json"], tmp_path)
        assert result.status == BatchStatus.COMPLETED
        assert result.processed_items == 1
        assert len(result.output_files) == 1

    def test_unknown_format_fails(self, tmp_path):
        cfg = BatchConfig(use_parallel=False)
        bp = SodirBatchProcessor(config=cfg)
        result = bp.process_multi_format_export([], ["parquet"], tmp_path)
        assert result.status == BatchStatus.FAILED
        assert result.failed_items == 1


# ---------------------------------------------------------------------------
# process_incremental_sync
# ---------------------------------------------------------------------------


class TestProcessIncrementalSync:
    def test_basic_sync(self, tmp_path):
        cfg = BatchConfig(batch_size=10)
        bp = SodirBatchProcessor(config=cfg)
        client = MagicMock()
        client.get_blocks.return_value = [{"id": 1}]
        client.get_fields.return_value = [{"name": "F1"}]

        last_sync = datetime(2024, 1, 1)
        result = bp.process_incremental_sync(
            client, last_sync, ["blocks", "fields"], tmp_path
        )
        assert result.status == BatchStatus.COMPLETED
        assert result.processed_items == 2
        assert "last_sync" in result.metadata

    def test_sync_with_pagination(self, tmp_path):
        cfg = BatchConfig(batch_size=2)
        bp = SodirBatchProcessor(config=cfg)
        client = MagicMock()
        # First call returns batch_size items (triggers pagination),
        # second call returns fewer (stops)
        client.get_blocks.side_effect = [
            [{"id": 1}, {"id": 2}],
            [{"id": 3}],
        ]
        last_sync = datetime(2024, 1, 1)
        result = bp.process_incremental_sync(client, last_sync, ["blocks"], tmp_path)
        assert result.status == BatchStatus.COMPLETED
        assert result.metadata.get("blocks_count") == 3

    def test_sync_with_error(self, tmp_path):
        cfg = BatchConfig(batch_size=10)
        bp = SodirBatchProcessor(config=cfg)
        client = MagicMock()
        client.get_blocks.return_value = [{"id": 1}]
        client.get_fields.side_effect = Exception("API error")
        last_sync = datetime(2024, 1, 1)
        result = bp.process_incremental_sync(
            client, last_sync, ["blocks", "fields"], tmp_path
        )
        assert result.status == BatchStatus.PARTIAL
        assert result.failed_items == 1
        assert result.processed_items == 1

    def test_sync_all_fail(self, tmp_path):
        cfg = BatchConfig(batch_size=10)
        bp = SodirBatchProcessor(config=cfg)
        client = MagicMock()
        client.get_blocks.side_effect = Exception("down")
        last_sync = datetime(2024, 1, 1)
        result = bp.process_incremental_sync(client, last_sync, ["blocks"], tmp_path)
        assert result.status == BatchStatus.FAILED

    def test_sync_unknown_data_type(self, tmp_path):
        cfg = BatchConfig(batch_size=10)
        bp = SodirBatchProcessor(config=cfg)
        client = MagicMock()
        last_sync = datetime(2024, 1, 1)
        result = bp.process_incremental_sync(
            client, last_sync, ["unknown_type"], tmp_path
        )
        # unknown_type should still count as processed (hits the break in while loop)
        assert result.status == BatchStatus.COMPLETED
        assert result.processed_items == 1

    def test_sync_empty_response(self, tmp_path):
        cfg = BatchConfig(batch_size=10)
        bp = SodirBatchProcessor(config=cfg)
        client = MagicMock()
        client.get_fields.return_value = []
        last_sync = datetime(2024, 1, 1)
        result = bp.process_incremental_sync(client, last_sync, ["fields"], tmp_path)
        assert result.status == BatchStatus.COMPLETED
        # No data to save but still counts as processed
        assert result.processed_items == 1


# ---------------------------------------------------------------------------
# process_multi_format_export - parallel path
# ---------------------------------------------------------------------------


class TestParallelMultiFormatExport:
    def test_parallel_json_csv(self, tmp_path):
        cfg = BatchConfig(use_parallel=True, max_workers=2)
        bp = SodirBatchProcessor(config=cfg)
        data = [{"x": 1, "y": 2}]
        result = bp.process_multi_format_export(data, ["json", "csv"], tmp_path)
        assert result.status == BatchStatus.COMPLETED
        assert result.processed_items == 2
        assert len(result.output_files) == 2

    def test_parallel_with_unknown_format(self, tmp_path):
        cfg = BatchConfig(use_parallel=True, max_workers=2)
        bp = SodirBatchProcessor(config=cfg)
        data = [{"x": 1}]
        result = bp.process_multi_format_export(data, ["json", "parquet"], tmp_path)
        assert result.status == BatchStatus.PARTIAL
        assert result.processed_items == 1
        assert result.failed_items == 1


# ---------------------------------------------------------------------------
# process_data_collection - with save_intermediate
# ---------------------------------------------------------------------------


class TestProcessDataCollectionSaveIntermediate:
    def test_save_intermediate(self, tmp_path):
        cfg = BatchConfig(use_parallel=False, save_intermediate=True)
        bp = SodirBatchProcessor(config=cfg)
        client = MagicMock()
        client.get_fields.return_value = [{"name": "F1"}]
        specs = [{"data_type": "fields", "params": {}}]
        result = bp.process_data_collection(client, specs, tmp_path)
        assert result.status == BatchStatus.COMPLETED
        # Should have saved intermediate files
        assert len(result.output_files) >= 1
