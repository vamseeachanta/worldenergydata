"""
Shared Type Definitions for WorldEnergyData

This module provides common type aliases and protocol classes for
consistent type annotations across all modules.

Type Aliases:
    - JSONDict, JSONList: JSON-compatible types
    - PathLike: File path types
    - DataFrameLike: DataFrame-compatible types

Protocols:
    - DataSourceProtocol: Interface for data sources
    - ValidatorProtocol: Interface for validators
    - CacheProtocol: Interface for cache implementations

Example usage:
    from worldenergydata.common.types import JSONDict, DataSourceProtocol

    def process_data(data: JSONDict) -> JSONDict:
        ...

    class MyDataSource(DataSourceProtocol):
        ...
"""

from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import (
    Any,
    Literal,
    Protocol,
    TypeAlias,
    TypeVar,
    runtime_checkable,
)

# Conditional pandas import for type hints
try:
    import pandas as pd

    DataFrame: TypeAlias = pd.DataFrame
    Series: TypeAlias = pd.Series
except ImportError:
    DataFrame = Any  # type: ignore
    Series = Any  # type: ignore


# =============================================================================
# Type Aliases
# =============================================================================

# JSON types
JSONPrimitive: TypeAlias = str | int | float | bool | None
JSONDict: TypeAlias = dict[str, Any]
JSONList: TypeAlias = list[Any]
JSONValue: TypeAlias = JSONPrimitive | JSONDict | JSONList

# Path types
PathLike: TypeAlias = str | Path
PathList: TypeAlias = list[PathLike]

# DataFrame types
DataFrameLike: TypeAlias = DataFrame | dict[str, list[Any]] | list[dict[str, Any]]
SeriesLike: TypeAlias = Series | list[Any] | dict[str, Any]

# Date types
DateLike: TypeAlias = str | date | datetime
DateRange: TypeAlias = tuple[DateLike, DateLike]

# Numeric types
Number: TypeAlias = int | float
NumberOrNone: TypeAlias = Number | None

# API types
APIResponse: TypeAlias = dict[str, Any]
Headers: TypeAlias = dict[str, str]

# Energy data specific types
APINumber = str  # API well number (10, 12, or 14 digits)
LeaseNumber = str  # BSEE lease number
BlockNumber = str  # OCS block number
FieldName = str  # Field name

# Production data types
ProductionRecord: TypeAlias = dict[str, Any]
ProductionData: TypeAlias = list[ProductionRecord]

# Callback types
ProgressCallback: TypeAlias = Callable[[int, int, str], None]
ErrorCallback: TypeAlias = Callable[[Exception, dict[str, Any]], None]

# Generic type variables
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
DataT = TypeVar("DataT", bound=DataFrameLike)

# Status types
ProcessingStatus: TypeAlias = Literal["pending", "running", "completed", "failed"]
DataQuality: TypeAlias = Literal["high", "medium", "low", "unknown"]


# =============================================================================
# Protocol Classes
# =============================================================================


@runtime_checkable
class DataSourceProtocol(Protocol):
    """
    Protocol for data source implementations.

    All data sources should implement this interface to ensure
    consistent behavior across different data providers.
    """

    @property
    def name(self) -> str:
        """Return the name of the data source."""
        ...

    @property
    def is_available(self) -> bool:
        """Check if the data source is currently available."""
        ...

    def fetch(
        self,
        query: dict[str, Any],
        **kwargs: Any,
    ) -> DataFrameLike:
        """
        Fetch data from the source.

        Args:
            query: Query parameters
            **kwargs: Additional options

        Returns:
            Fetched data as DataFrame-like object
        """
        ...

    def validate_query(self, query: dict[str, Any]) -> bool:
        """
        Validate a query before execution.

        Args:
            query: Query parameters to validate

        Returns:
            True if valid, False otherwise
        """
        ...


@runtime_checkable
class ValidatorProtocol(Protocol):
    """
    Protocol for data validator implementations.

    Validators should implement this interface to provide
    consistent validation behavior.
    """

    def validate(
        self,
        data: DataFrameLike,
        **kwargs: Any,
    ) -> tuple[bool, list[dict[str, Any]]]:
        """
        Validate the provided data.

        Args:
            data: Data to validate
            **kwargs: Additional validation options

        Returns:
            Tuple of (is_valid, list of error details)
        """
        ...

    def get_schema(self) -> dict[str, Any]:
        """
        Get the validation schema.

        Returns:
            Schema definition as dictionary
        """
        ...


@runtime_checkable
class CacheProtocol(Protocol):
    """
    Protocol for cache implementations.

    Cache implementations should implement this interface for
    consistent caching behavior.
    """

    def get(self, key: str) -> Any | None:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        ...

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (optional)
        """
        ...

    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        ...

    def clear(self) -> None:
        """Clear all cached values."""
        ...

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        ...


@runtime_checkable
class ProcessorProtocol(Protocol):
    """
    Protocol for data processor implementations.

    Processors transform data through a pipeline of operations.
    """

    def process(
        self,
        data: DataFrameLike,
        **kwargs: Any,
    ) -> DataFrameLike:
        """
        Process the provided data.

        Args:
            data: Input data
            **kwargs: Processing options

        Returns:
            Processed data
        """
        ...

    @property
    def name(self) -> str:
        """Return the processor name."""
        ...


@runtime_checkable
class ExporterProtocol(Protocol):
    """
    Protocol for data exporter implementations.

    Exporters write data to various output formats.
    """

    def export(
        self,
        data: DataFrameLike,
        output_path: PathLike,
        **kwargs: Any,
    ) -> Path:
        """
        Export data to the specified path.

        Args:
            data: Data to export
            output_path: Output file path
            **kwargs: Export options

        Returns:
            Path to the exported file
        """
        ...

    @property
    def supported_formats(self) -> list[str]:
        """Return list of supported export formats."""
        ...


@runtime_checkable
class ReporterProtocol(Protocol):
    """
    Protocol for report generator implementations.

    Reporters generate reports from processed data.
    """

    def generate(
        self,
        data: DataFrameLike,
        output_path: PathLike,
        **kwargs: Any,
    ) -> Path:
        """
        Generate a report from the provided data.

        Args:
            data: Source data for the report
            output_path: Output report path
            **kwargs: Report options

        Returns:
            Path to the generated report
        """
        ...

    @property
    def template_name(self) -> str:
        """Return the report template name."""
        ...


# =============================================================================
# Container Types
# =============================================================================


class DataResult:
    """
    Container for data operation results.

    Provides a consistent way to return data along with
    metadata about the operation.
    """

    def __init__(
        self,
        data: DataFrameLike,
        success: bool = True,
        message: str = "",
        metadata: dict[str, Any] | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        self.data = data
        self.success = success
        self.message = message
        self.metadata = metadata or {}
        self.errors = errors or []

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    @property
    def record_count(self) -> int:
        """Get the number of records in the data."""
        if hasattr(self.data, "__len__"):
            return len(self.data)
        return 0

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "message": self.message,
            "record_count": self.record_count,
            "metadata": self.metadata,
            "errors": self.errors,
        }


class PaginatedResult:
    """
    Container for paginated data results.

    Used when retrieving large datasets in pages.
    """

    def __init__(
        self,
        data: DataFrameLike,
        page: int,
        page_size: int,
        total_count: int,
        has_next: bool,
        has_previous: bool,
    ) -> None:
        self.data = data
        self.page = page
        self.page_size = page_size
        self.total_count = total_count
        self.has_next = has_next
        self.has_previous = has_previous

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size <= 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total_count": self.total_count,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous,
        }
