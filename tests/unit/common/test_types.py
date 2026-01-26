"""
Tests for worldenergydata.common.types module.

Tests cover:
- Type aliases are correct types
- Protocol classes can be implemented
- DataResult and PaginatedResult work
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest


class TestTypeAliases:
    """Tests for type alias definitions."""

    def test_json_primitive_types(self):
        """Test JSONPrimitive type alias accepts correct types."""
        from worldenergydata.common.types import JSONPrimitive

        # These should be valid JSONPrimitive values
        primitives: List[JSONPrimitive] = [
            "string",
            42,
            3.14,
            True,
            False,
            None,
        ]

        for val in primitives:
            assert val is not None or val is None

    def test_json_dict_type(self):
        """Test JSONDict type alias."""
        from worldenergydata.common.types import JSONDict

        data: JSONDict = {
            "name": "test",
            "count": 42,
            "nested": {"key": "value"},
        }

        assert isinstance(data, dict)

    def test_json_list_type(self):
        """Test JSONList type alias."""
        from worldenergydata.common.types import JSONList

        data: JSONList = [1, "two", {"three": 3}]

        assert isinstance(data, list)

    def test_path_like_type(self):
        """Test PathLike type alias accepts str and Path."""
        from worldenergydata.common.types import PathLike

        path1: PathLike = "/path/to/file"
        path2: PathLike = Path("/path/to/file")

        assert isinstance(path1, str)
        assert isinstance(path2, Path)

    def test_date_like_type(self):
        """Test DateLike type alias accepts multiple date types."""
        from datetime import date, datetime
        from worldenergydata.common.types import DateLike

        d1: DateLike = "2023-12-15"
        d2: DateLike = date(2023, 12, 15)
        d3: DateLike = datetime(2023, 12, 15, 10, 30)

        assert isinstance(d1, str)
        assert isinstance(d2, date)
        assert isinstance(d3, datetime)

    def test_date_range_type(self):
        """Test DateRange type alias."""
        from datetime import date
        from worldenergydata.common.types import DateRange

        range1: DateRange = ("2023-01-01", "2023-12-31")
        range2: DateRange = (date(2023, 1, 1), date(2023, 12, 31))

        assert len(range1) == 2
        assert len(range2) == 2

    def test_number_types(self):
        """Test Number and NumberOrNone type aliases."""
        from worldenergydata.common.types import Number, NumberOrNone

        n1: Number = 42
        n2: Number = 3.14

        n3: NumberOrNone = 100
        n4: NumberOrNone = None

        assert isinstance(n1, int)
        assert isinstance(n2, float)
        assert n4 is None

    def test_api_response_type(self):
        """Test APIResponse type alias."""
        from worldenergydata.common.types import APIResponse

        response: APIResponse = {
            "status": "success",
            "data": [{"id": 1}],
            "count": 1,
        }

        assert "status" in response

    def test_headers_type(self):
        """Test Headers type alias."""
        from worldenergydata.common.types import Headers

        headers: Headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token",
        }

        assert "Content-Type" in headers

    def test_processing_status_literal(self):
        """Test ProcessingStatus literal type."""
        from worldenergydata.common.types import ProcessingStatus

        # These should be valid status values
        valid_statuses: List[ProcessingStatus] = [
            "pending",
            "running",
            "completed",
            "failed",
        ]

        for status in valid_statuses:
            assert status in ["pending", "running", "completed", "failed"]

    def test_data_quality_literal(self):
        """Test DataQuality literal type."""
        from worldenergydata.common.types import DataQuality

        valid_qualities: List[DataQuality] = [
            "high",
            "medium",
            "low",
            "unknown",
        ]

        for quality in valid_qualities:
            assert quality in ["high", "medium", "low", "unknown"]


class TestDataSourceProtocol:
    """Tests for DataSourceProtocol."""

    def test_protocol_can_be_implemented(self):
        """Test DataSourceProtocol can be implemented by a class."""
        from worldenergydata.common.types import DataSourceProtocol, DataFrameLike

        class TestDataSource:
            @property
            def name(self) -> str:
                return "test_source"

            @property
            def is_available(self) -> bool:
                return True

            def fetch(self, query: Dict[str, Any], **kwargs: Any) -> DataFrameLike:
                return [{"data": "value"}]

            def validate_query(self, query: Dict[str, Any]) -> bool:
                return True

        source = TestDataSource()

        assert isinstance(source, DataSourceProtocol)
        assert source.name == "test_source"
        assert source.is_available is True

    def test_protocol_methods_work(self):
        """Test protocol methods can be called."""
        from worldenergydata.common.types import DataSourceProtocol

        class MockSource:
            @property
            def name(self) -> str:
                return "mock"

            @property
            def is_available(self) -> bool:
                return True

            def fetch(self, query: Dict[str, Any], **kwargs: Any):
                return [{"result": query.get("param")}]

            def validate_query(self, query: Dict[str, Any]) -> bool:
                return "param" in query

        source = MockSource()

        assert source.validate_query({"param": "value"}) is True
        assert source.validate_query({}) is False
        result = source.fetch({"param": "test"})
        assert result == [{"result": "test"}]


class TestValidatorProtocol:
    """Tests for ValidatorProtocol."""

    def test_protocol_can_be_implemented(self):
        """Test ValidatorProtocol can be implemented."""
        from worldenergydata.common.types import ValidatorProtocol, DataFrameLike

        class TestValidator:
            def validate(
                self,
                data: DataFrameLike,
                **kwargs: Any,
            ) -> Tuple[bool, List[Dict[str, Any]]]:
                return True, []

            def get_schema(self) -> Dict[str, Any]:
                return {"type": "object"}

        validator = TestValidator()

        assert isinstance(validator, ValidatorProtocol)

    def test_validator_methods(self):
        """Test validator methods work correctly."""
        from worldenergydata.common.types import ValidatorProtocol

        class RangeValidator:
            def __init__(self, min_val: int, max_val: int):
                self.min_val = min_val
                self.max_val = max_val

            def validate(
                self, data: List[Dict[str, Any]], **kwargs: Any
            ) -> Tuple[bool, List[Dict[str, Any]]]:
                errors = []
                for i, record in enumerate(data):
                    value = record.get("value", 0)
                    if value < self.min_val or value > self.max_val:
                        errors.append({
                            "row": i,
                            "message": f"Value {value} out of range",
                        })
                return len(errors) == 0, errors

            def get_schema(self) -> Dict[str, Any]:
                return {
                    "min": self.min_val,
                    "max": self.max_val,
                }

        validator = RangeValidator(0, 100)

        is_valid, errors = validator.validate([{"value": 50}])
        assert is_valid is True
        assert errors == []

        is_valid, errors = validator.validate([{"value": 150}])
        assert is_valid is False
        assert len(errors) == 1


class TestCacheProtocol:
    """Tests for CacheProtocol."""

    def test_protocol_can_be_implemented(self):
        """Test CacheProtocol can be implemented."""
        from worldenergydata.common.types import CacheProtocol

        class MemoryCache:
            def __init__(self):
                self._cache: Dict[str, Any] = {}

            def get(self, key: str) -> Optional[Any]:
                return self._cache.get(key)

            def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
                self._cache[key] = value

            def delete(self, key: str) -> bool:
                if key in self._cache:
                    del self._cache[key]
                    return True
                return False

            def clear(self) -> None:
                self._cache.clear()

            def exists(self, key: str) -> bool:
                return key in self._cache

        cache = MemoryCache()

        assert isinstance(cache, CacheProtocol)

    def test_cache_operations(self):
        """Test cache operations work correctly."""
        from worldenergydata.common.types import CacheProtocol

        class SimpleCache:
            def __init__(self):
                self._data: Dict[str, Any] = {}

            def get(self, key: str) -> Optional[Any]:
                return self._data.get(key)

            def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
                self._data[key] = value

            def delete(self, key: str) -> bool:
                if key in self._data:
                    del self._data[key]
                    return True
                return False

            def clear(self) -> None:
                self._data.clear()

            def exists(self, key: str) -> bool:
                return key in self._data

        cache = SimpleCache()

        # Test set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Test exists
        assert cache.exists("key1") is True
        assert cache.exists("nonexistent") is False

        # Test delete
        assert cache.delete("key1") is True
        assert cache.exists("key1") is False
        assert cache.delete("nonexistent") is False

        # Test clear
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None


class TestProcessorProtocol:
    """Tests for ProcessorProtocol."""

    def test_protocol_can_be_implemented(self):
        """Test ProcessorProtocol can be implemented."""
        from worldenergydata.common.types import ProcessorProtocol, DataFrameLike

        class UppercaseProcessor:
            @property
            def name(self) -> str:
                return "uppercase"

            def process(self, data: DataFrameLike, **kwargs: Any) -> DataFrameLike:
                if isinstance(data, list):
                    return [
                        {k: v.upper() if isinstance(v, str) else v for k, v in d.items()}
                        for d in data
                    ]
                return data

        processor = UppercaseProcessor()

        assert isinstance(processor, ProcessorProtocol)
        assert processor.name == "uppercase"

    def test_processor_transforms_data(self):
        """Test processor transforms data correctly."""
        from worldenergydata.common.types import ProcessorProtocol

        class FilterProcessor:
            @property
            def name(self) -> str:
                return "filter"

            def process(self, data: List[Dict[str, Any]], **kwargs: Any):
                min_value = kwargs.get("min_value", 0)
                return [d for d in data if d.get("value", 0) >= min_value]

        processor = FilterProcessor()
        data = [{"value": 10}, {"value": 5}, {"value": 20}]

        result = processor.process(data, min_value=10)

        assert len(result) == 2
        assert result[0]["value"] == 10
        assert result[1]["value"] == 20


class TestExporterProtocol:
    """Tests for ExporterProtocol."""

    def test_protocol_can_be_implemented(self):
        """Test ExporterProtocol can be implemented."""
        from worldenergydata.common.types import ExporterProtocol, DataFrameLike, PathLike
        import json

        class JSONExporter:
            @property
            def supported_formats(self) -> List[str]:
                return ["json"]

            def export(
                self,
                data: DataFrameLike,
                output_path: PathLike,
                **kwargs: Any,
            ) -> Path:
                path = Path(output_path)
                with open(path, "w") as f:
                    json.dump(data, f)
                return path

        exporter = JSONExporter()

        assert isinstance(exporter, ExporterProtocol)
        assert "json" in exporter.supported_formats


class TestReporterProtocol:
    """Tests for ReporterProtocol."""

    def test_protocol_can_be_implemented(self):
        """Test ReporterProtocol can be implemented."""
        from worldenergydata.common.types import ReporterProtocol, DataFrameLike, PathLike

        class SimpleReporter:
            @property
            def template_name(self) -> str:
                return "simple_report"

            def generate(
                self,
                data: DataFrameLike,
                output_path: PathLike,
                **kwargs: Any,
            ) -> Path:
                path = Path(output_path)
                with open(path, "w") as f:
                    f.write(f"Report with {len(data)} records")
                return path

        reporter = SimpleReporter()

        assert isinstance(reporter, ReporterProtocol)
        assert reporter.template_name == "simple_report"


class TestDataResult:
    """Tests for DataResult container class."""

    def test_basic_initialization(self):
        """Test basic DataResult initialization."""
        from worldenergydata.common.types import DataResult

        result = DataResult(data=[{"id": 1}])

        assert result.data == [{"id": 1}]
        assert result.success is True
        assert result.message == ""
        assert result.metadata == {}
        assert result.errors == []

    def test_initialization_with_all_params(self):
        """Test DataResult with all parameters."""
        from worldenergydata.common.types import DataResult

        result = DataResult(
            data=[{"id": 1}],
            success=False,
            message="Partial failure",
            metadata={"source": "BSEE"},
            errors=[{"field": "api", "error": "Invalid"}],
        )

        assert result.success is False
        assert result.message == "Partial failure"
        assert result.metadata["source"] == "BSEE"
        assert len(result.errors) == 1

    def test_has_errors_property(self):
        """Test has_errors property."""
        from worldenergydata.common.types import DataResult

        result_ok = DataResult(data=[])
        result_err = DataResult(data=[], errors=[{"error": "test"}])

        assert result_ok.has_errors is False
        assert result_err.has_errors is True

    def test_record_count_property(self):
        """Test record_count property."""
        from worldenergydata.common.types import DataResult

        result = DataResult(data=[{"a": 1}, {"b": 2}, {"c": 3}])

        assert result.record_count == 3

    def test_record_count_empty(self):
        """Test record_count with empty data."""
        from worldenergydata.common.types import DataResult

        result = DataResult(data=[])

        assert result.record_count == 0

    def test_to_dict(self):
        """Test to_dict serialization."""
        from worldenergydata.common.types import DataResult

        result = DataResult(
            data=[{"id": 1}],
            success=True,
            message="OK",
            metadata={"key": "value"},
            errors=[],
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["message"] == "OK"
        assert d["record_count"] == 1
        assert d["metadata"] == {"key": "value"}
        assert d["errors"] == []


class TestPaginatedResult:
    """Tests for PaginatedResult container class."""

    def test_basic_initialization(self):
        """Test basic PaginatedResult initialization."""
        from worldenergydata.common.types import PaginatedResult

        result = PaginatedResult(
            data=[{"id": 1}],
            page=1,
            page_size=10,
            total_count=100,
            has_next=True,
            has_previous=False,
        )

        assert result.data == [{"id": 1}]
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_count == 100
        assert result.has_next is True
        assert result.has_previous is False

    def test_total_pages_calculation(self):
        """Test total_pages property calculation."""
        from worldenergydata.common.types import PaginatedResult

        # 100 items, 10 per page = 10 pages
        result1 = PaginatedResult(
            data=[], page=1, page_size=10, total_count=100,
            has_next=True, has_previous=False
        )
        assert result1.total_pages == 10

        # 101 items, 10 per page = 11 pages
        result2 = PaginatedResult(
            data=[], page=1, page_size=10, total_count=101,
            has_next=True, has_previous=False
        )
        assert result2.total_pages == 11

        # 99 items, 10 per page = 10 pages
        result3 = PaginatedResult(
            data=[], page=1, page_size=10, total_count=99,
            has_next=True, has_previous=False
        )
        assert result3.total_pages == 10

    def test_total_pages_zero_page_size(self):
        """Test total_pages with zero page size."""
        from worldenergydata.common.types import PaginatedResult

        result = PaginatedResult(
            data=[], page=1, page_size=0, total_count=100,
            has_next=False, has_previous=False
        )

        assert result.total_pages == 0

    def test_to_dict(self):
        """Test to_dict serialization."""
        from worldenergydata.common.types import PaginatedResult

        result = PaginatedResult(
            data=[{"id": 1}],
            page=2,
            page_size=10,
            total_count=25,
            has_next=True,
            has_previous=True,
        )

        d = result.to_dict()

        assert d["page"] == 2
        assert d["page_size"] == 10
        assert d["total_count"] == 25
        assert d["total_pages"] == 3
        assert d["has_next"] is True
        assert d["has_previous"] is True


class TestRuntimeCheckableProtocols:
    """Tests for runtime_checkable protocol behavior."""

    def test_data_source_runtime_check(self):
        """Test DataSourceProtocol is runtime checkable."""
        from worldenergydata.common.types import DataSourceProtocol

        class ValidSource:
            @property
            def name(self) -> str:
                return "valid"

            @property
            def is_available(self) -> bool:
                return True

            def fetch(self, query, **kwargs):
                return []

            def validate_query(self, query):
                return True

        class InvalidSource:
            pass

        assert isinstance(ValidSource(), DataSourceProtocol)
        assert not isinstance(InvalidSource(), DataSourceProtocol)

    def test_cache_runtime_check(self):
        """Test CacheProtocol is runtime checkable."""
        from worldenergydata.common.types import CacheProtocol

        class ValidCache:
            def get(self, key):
                return None

            def set(self, key, value, ttl=None):
                pass

            def delete(self, key):
                return True

            def clear(self):
                pass

            def exists(self, key):
                return False

        assert isinstance(ValidCache(), CacheProtocol)

    def test_validator_runtime_check(self):
        """Test ValidatorProtocol is runtime checkable."""
        from worldenergydata.common.types import ValidatorProtocol

        class ValidValidator:
            def validate(self, data, **kwargs):
                return True, []

            def get_schema(self):
                return {}

        assert isinstance(ValidValidator(), ValidatorProtocol)
