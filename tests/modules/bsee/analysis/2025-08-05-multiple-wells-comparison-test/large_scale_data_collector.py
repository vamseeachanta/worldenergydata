"""
Large-Scale Data Collection and Processing Module

This module provides efficient data collection and processing capabilities
for handling 120+ wells from both lease_num and api12_num analysis methods.
"""

import gc  # Garbage collection for memory management
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


@dataclass
class DataCollectionConfig:
    """Configuration class for data collection operations."""

    chunk_size: int = 50
    memory_limit_mb: int = 1024  # 1GB default
    enable_progress_tracking: bool = True
    enable_logging: bool = True
    log_level: str = "INFO"
    output_directory: str = (
        "tests/modules/bsee/analysis/multiple_wells_comparison_test/results"
    )
    validation_enabled: bool = True
    type_optimization: bool = True


class ProgressTracker:
    """Progress tracking and logging for long-running operations."""

    def __init__(
        self,
        total_items: int,
        operation_name: str = "Processing",
        enable_logging: bool = True,
    ):
        """
        Initialize progress tracker.

        Args:
            total_items: Total number of items to process
            operation_name: Name of the operation being tracked
            enable_logging: Whether to enable logging
        """
        self.total_items = total_items
        self.operation_name = operation_name
        self.enable_logging = enable_logging
        self.processed_items = 0
        self.start_time = time.time()
        self.last_log_time = self.start_time

        if self.enable_logging:
            logging.basicConfig(
                level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
            )
            self.logger = logging.getLogger(__name__)
            self.logger.info(
                f"Starting {operation_name}: {total_items} items to process"
            )

    def update(self, items_processed: int = 1, custom_message: str = None):
        """
        Update progress and log if necessary.

        Args:
            items_processed: Number of items processed in this update
            custom_message: Custom message to include in log
        """
        self.processed_items += items_processed
        current_time = time.time()

        # Log every 10% or every 30 seconds, whichever comes first
        progress_pct = (self.processed_items / self.total_items) * 100
        time_since_last_log = current_time - self.last_log_time

        should_log = (
            progress_pct % 10 < (items_processed / self.total_items) * 100
            or time_since_last_log > 30
            or self.processed_items == self.total_items
        )

        if should_log and self.enable_logging:
            elapsed_time = current_time - self.start_time
            avg_time_per_item = (
                elapsed_time / self.processed_items if self.processed_items > 0 else 0
            )
            eta = avg_time_per_item * (self.total_items - self.processed_items)

            message = (
                f"{self.operation_name}: {self.processed_items}/{self.total_items} "
                f"({progress_pct:.1f}%) - ETA: {eta:.1f}s"
            )

            if custom_message:
                message += f" - {custom_message}"

            self.logger.info(message)
            self.last_log_time = current_time

    def finish(self, success: bool = True):
        """
        Finish progress tracking and log final results.

        Args:
            success: Whether the operation completed successfully
        """
        if self.enable_logging:
            total_time = time.time() - self.start_time
            status = "completed successfully" if success else "failed"
            self.logger.info(f"{self.operation_name} {status} in {total_time:.2f}s")


class MemoryMonitor:
    """Monitor and optimize memory usage during data processing."""

    def __init__(self, memory_limit_mb: int = 1024):
        """
        Initialize memory monitor.

        Args:
            memory_limit_mb: Memory limit in megabytes
        """
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        self.peak_memory_usage = 0

    def get_current_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            # Fallback to basic memory tracking
            return sys.getsizeof(gc.get_objects())

    def check_memory_usage(self) -> Dict[str, Union[int, float, bool]]:
        """
        Check current memory usage and return status.

        Returns:
            Dict containing memory usage statistics
        """
        current_usage = self.get_current_memory_usage()
        self.peak_memory_usage = max(self.peak_memory_usage, current_usage)

        usage_mb = current_usage / (1024 * 1024)
        peak_mb = self.peak_memory_usage / (1024 * 1024)
        limit_mb = self.memory_limit_bytes / (1024 * 1024)

        return {
            "current_usage_mb": usage_mb,
            "peak_usage_mb": peak_mb,
            "memory_limit_mb": limit_mb,
            "usage_percentage": (current_usage / self.memory_limit_bytes) * 100,
            "approaching_limit": current_usage > (self.memory_limit_bytes * 0.8),
            "exceeded_limit": current_usage > self.memory_limit_bytes,
        }

    def optimize_memory(self):
        """Force garbage collection to free memory."""
        gc.collect()


class LargeScaleDataCollector:
    """
    Efficient data collection module for handling 120+ wells from multiple analysis methods.
    """

    def __init__(self, config: Optional[DataCollectionConfig] = None):
        """
        Initialize the large-scale data collector.

        Args:
            config: Configuration for data collection operations
        """
        self.config = config or DataCollectionConfig()
        self.memory_monitor = MemoryMonitor(self.config.memory_limit_mb)
        self.collection_stats = {
            "total_wells_collected": 0,
            "successful_loads": 0,
            "failed_loads": 0,
            "processing_time_seconds": 0,
            "peak_memory_usage_mb": 0,
            "data_validation_errors": 0,
        }

        # Create output directory
        Path(self.config.output_directory).mkdir(parents=True, exist_ok=True)

        # Setup logging
        if self.config.enable_logging:
            logging.basicConfig(
                level=getattr(logging, self.config.log_level),
                format="%(asctime)s - %(levelname)s - %(message)s",
            )
            self.logger = logging.getLogger(__name__)

    def collect_lease_method_data(
        self, data_sources: List[str]
    ) -> Generator[pd.DataFrame, None, None]:
        """
        Collect data from lease method sources with memory optimization.

        Args:
            data_sources: List of file paths or data source identifiers

        Yields:
            pd.DataFrame: Chunks of lease method data
        """
        progress = ProgressTracker(
            len(data_sources),
            "Lease Method Collection",
            self.config.enable_progress_tracking,
        )

        for source in data_sources:
            try:
                # Load data with memory optimization
                if source.endswith(".xlsx"):
                    df = self._load_excel_optimized(source)
                elif source.endswith(".csv"):
                    df = self._load_csv_optimized(source)
                else:
                    # Handle other data sources (API calls, database queries, etc.)
                    df = self._load_generic_source(source)

                if df is not None and not df.empty:
                    # Standardize column names for lease method
                    df = self._standardize_lease_columns(df)

                    # Validate data if enabled
                    if self.config.validation_enabled:
                        validation_result = self._validate_lease_data(df, source)
                        if not validation_result["is_valid"]:
                            self.collection_stats["data_validation_errors"] += 1
                            if self.config.enable_logging:
                                self.logger.warning(
                                    f"Validation issues in {source}: {validation_result['errors']}"
                                )

                    # Optimize data types
                    if self.config.type_optimization:
                        df = self._optimize_data_types(df)

                    self.collection_stats["successful_loads"] += 1
                    self.collection_stats["total_wells_collected"] += len(df)

                    yield df
                else:
                    self.collection_stats["failed_loads"] += 1
                    if self.config.enable_logging:
                        self.logger.warning(f"No data loaded from source: {source}")

            except Exception as e:
                self.collection_stats["failed_loads"] += 1
                if self.config.enable_logging:
                    self.logger.error(
                        f"Error loading lease data from {source}: {str(e)}"
                    )

            # Update progress and check memory
            progress.update()
            memory_status = self.memory_monitor.check_memory_usage()

            if memory_status["approaching_limit"]:
                self.memory_monitor.optimize_memory()
                if self.config.enable_logging:
                    self.logger.warning(
                        f"Approaching memory limit: {memory_status['usage_percentage']:.1f}%"
                    )

        progress.finish()

    def collect_api12_method_data(
        self, data_sources: List[str]
    ) -> Generator[pd.DataFrame, None, None]:
        """
        Collect data from API12 method sources with memory optimization.

        Args:
            data_sources: List of file paths or data source identifiers

        Yields:
            pd.DataFrame: Chunks of API12 method data
        """
        progress = ProgressTracker(
            len(data_sources),
            "API12 Method Collection",
            self.config.enable_progress_tracking,
        )

        for source in data_sources:
            try:
                # Load data with memory optimization
                if source.endswith(".csv"):
                    df = self._load_csv_optimized(source)
                elif source.endswith(".xlsx"):
                    df = self._load_excel_optimized(source)
                else:
                    # Handle other data sources
                    df = self._load_generic_source(source)

                if df is not None and not df.empty:
                    # Standardize column names for API12 method
                    df = self._standardize_api12_columns(df)

                    # Validate data if enabled
                    if self.config.validation_enabled:
                        validation_result = self._validate_api12_data(df, source)
                        if not validation_result["is_valid"]:
                            self.collection_stats["data_validation_errors"] += 1
                            if self.config.enable_logging:
                                self.logger.warning(
                                    f"Validation issues in {source}: {validation_result['errors']}"
                                )

                    # Optimize data types
                    if self.config.type_optimization:
                        df = self._optimize_data_types(df)

                    self.collection_stats["successful_loads"] += 1
                    self.collection_stats["total_wells_collected"] += len(df)

                    yield df
                else:
                    self.collection_stats["failed_loads"] += 1
                    if self.config.enable_logging:
                        self.logger.warning(f"No data loaded from source: {source}")

            except Exception as e:
                self.collection_stats["failed_loads"] += 1
                if self.config.enable_logging:
                    self.logger.error(
                        f"Error loading API12 data from {source}: {str(e)}"
                    )

            # Update progress and check memory
            progress.update()
            memory_status = self.memory_monitor.check_memory_usage()

            if memory_status["approaching_limit"]:
                self.memory_monitor.optimize_memory()
                if self.config.enable_logging:
                    self.logger.warning(
                        f"Approaching memory limit: {memory_status['usage_percentage']:.1f}%"
                    )

        progress.finish()

    def _load_excel_optimized(self, file_path: str) -> Optional[pd.DataFrame]:
        """Load Excel file with memory optimization."""
        try:
            # Use chunks if file is large
            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:  # 50MB threshold
                # For very large Excel files, read in chunks if possible
                df = pd.read_excel(file_path, engine="openpyxl")
            else:
                df = pd.read_excel(file_path)

            return df
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"Error loading Excel file {file_path}: {str(e)}")
            return None

    def _load_csv_optimized(self, file_path: str) -> Optional[pd.DataFrame]:
        """Load CSV file with memory optimization."""
        try:
            # Determine optimal chunk size based on file size
            file_size = os.path.getsize(file_path)

            if file_size > 100 * 1024 * 1024:  # 100MB threshold
                # Read in chunks for very large files
                chunks = []
                for chunk in pd.read_csv(file_path, chunksize=10000):
                    chunks.append(chunk)
                    if len(chunks) * 10000 > 50000:  # Limit to ~50k rows per file
                        break

                if chunks:
                    df = pd.concat(chunks, ignore_index=True)
                else:
                    df = pd.DataFrame()
            else:
                df = pd.read_csv(file_path)

            return df
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"Error loading CSV file {file_path}: {str(e)}")
            return None

    def _load_generic_source(self, source: str) -> Optional[pd.DataFrame]:
        """Load data from generic source (placeholder for future extensions)."""
        # This is a placeholder for future data source types
        # Could include API calls, database queries, etc.
        if self.config.enable_logging:
            self.logger.warning(f"Generic source loading not implemented for: {source}")
        return None

    def _standardize_lease_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names for lease method data."""
        column_mapping = {
            "API_WELL_NUMBER": "API12",
            "api_well_number": "API12",
            "API_NUMBER": "API12",
            "DRILLING_DAYS": "Drilling Days",
            "drilling_days": "Drilling Days",
            "COMPLETION_DAYS": "Completion Days",
            "completion_days": "Completion Days",
            "WELL_NAME": "Well Name",
            "well_name": "Well Name",
            "SPUD_DATE": "Spud Date",
            "spud_date": "Spud Date",
            "TOTAL_DEPTH_DATE": "Total Depth Date",
            "total_depth_date": "Total Depth Date",
        }

        return df.rename(columns=column_mapping)

    def _standardize_api12_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names for API12 method data."""
        column_mapping = {
            "api12": "API12",
            "API_12": "API12",
            "api_12": "API12",
            "Drilling Days": "Drilling Days",
            "drilling_days": "Drilling Days",
            "DRILLING_DAYS": "Drilling Days",
            "Completion Days": "Completion Days",
            "completion_days": "Completion Days",
            "COMPLETION_DAYS": "Completion Days",
            "WELL_NAME": "Well Name",
            "well_name": "Well Name",
            "Well_Name": "Well Name",
        }

        return df.rename(columns=column_mapping)

    def _validate_lease_data(
        self, df: pd.DataFrame, source: str
    ) -> Dict[str, Union[bool, List[str]]]:
        """Validate lease method data."""
        errors = []

        # Check required columns
        required_columns = ["API12", "Drilling Days", "Completion Days"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")

        # Check data types and ranges
        if "API12" in df.columns:
            non_string_apis = df[~df["API12"].astype(str).str.match(r"^\d+$", na=False)]
            if not non_string_apis.empty:
                errors.append(f"Invalid API12 format in {len(non_string_apis)} rows")

        if "Drilling Days" in df.columns:
            invalid_drilling = df[
                (df["Drilling Days"] < 0) | (df["Drilling Days"] > 1000)
            ]
            if not invalid_drilling.empty:
                errors.append(f"Invalid drilling days in {len(invalid_drilling)} rows")

        if "Completion Days" in df.columns:
            invalid_completion = df[
                (df["Completion Days"] < 0) | (df["Completion Days"] > 500)
            ]
            if not invalid_completion.empty:
                errors.append(
                    f"Invalid completion days in {len(invalid_completion)} rows"
                )

        return {"is_valid": len(errors) == 0, "errors": errors, "source": source}

    def _validate_api12_data(
        self, df: pd.DataFrame, source: str
    ) -> Dict[str, Union[bool, List[str]]]:
        """Validate API12 method data."""
        errors = []

        # Check required columns
        required_columns = ["API12", "Drilling Days", "Completion Days"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")

        # Check data consistency
        if "API12" in df.columns:
            duplicate_apis = df[df["API12"].duplicated()]
            if not duplicate_apis.empty:
                errors.append(
                    f"Duplicate API12 values: {len(duplicate_apis)} duplicates"
                )

        # Check for null values in critical columns
        for col in ["API12", "Drilling Days", "Completion Days"]:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    errors.append(f"{null_count} null values in {col}")

        return {"is_valid": len(errors) == 0, "errors": errors, "source": source}

    def _optimize_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize data types for memory efficiency."""
        optimized_df = df.copy()

        # Optimize numeric columns
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col in ["Drilling Days", "Completion Days"]:
                # Use smallest integer type that can hold the data
                max_val = df[col].max()
                min_val = df[col].min()

                if pd.notna(max_val) and pd.notna(min_val):
                    if min_val >= 0 and max_val <= 255:
                        optimized_df[col] = df[col].astype("uint8")
                    elif min_val >= 0 and max_val <= 65535:
                        optimized_df[col] = df[col].astype("uint16")
                    elif min_val >= -32768 and max_val <= 32767:
                        optimized_df[col] = df[col].astype("int16")
                    else:
                        optimized_df[col] = df[col].astype("int32")

        # Optimize string columns
        string_columns = df.select_dtypes(include=["object"]).columns
        for col in string_columns:
            if col == "API12":
                # Keep as string but optimize
                optimized_df[col] = df[col].astype("string")
            elif col == "Well Name":
                # Use category for potentially repeated well names
                unique_ratio = df[col].nunique() / len(df)
                if unique_ratio < 0.5:  # If less than 50% unique values
                    optimized_df[col] = df[col].astype("category")

        return optimized_df

    def aggregate_collected_data(
        self,
        data_generator: Generator[pd.DataFrame, None, None],
        max_wells: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Aggregate data from generator with memory optimization.

        Args:
            data_generator: Generator yielding DataFrame chunks
            max_wells: Maximum number of wells to collect (None for no limit)

        Returns:
            pd.DataFrame: Aggregated data
        """
        aggregated_chunks = []
        total_wells = 0

        progress = ProgressTracker(
            max_wells or 1000, "Data Aggregation", self.config.enable_progress_tracking
        )

        for chunk in data_generator:
            if max_wells and total_wells >= max_wells:
                break

            # Limit chunk size if approaching max_wells
            if max_wells:
                remaining_wells = max_wells - total_wells
                if len(chunk) > remaining_wells:
                    chunk = chunk.head(remaining_wells)

            aggregated_chunks.append(chunk)
            total_wells += len(chunk)

            progress.update(len(chunk))

            # Check memory usage
            memory_status = self.memory_monitor.check_memory_usage()
            if memory_status["approaching_limit"]:
                # Combine chunks and optimize memory
                if len(aggregated_chunks) > 1:
                    combined = pd.concat(aggregated_chunks, ignore_index=True)
                    aggregated_chunks = [combined]
                    self.memory_monitor.optimize_memory()

        progress.finish()

        # Final aggregation
        if aggregated_chunks:
            final_df = pd.concat(aggregated_chunks, ignore_index=True)
            return final_df
        else:
            return pd.DataFrame()

    def export_collection_stats(self) -> str:
        """Export collection statistics to JSON file."""
        # Update peak memory usage
        memory_status = self.memory_monitor.check_memory_usage()
        self.collection_stats["peak_memory_usage_mb"] = memory_status["peak_usage_mb"]

        # Add timestamp
        stats_with_metadata = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "chunk_size": self.config.chunk_size,
                "memory_limit_mb": self.config.memory_limit_mb,
                "validation_enabled": self.config.validation_enabled,
                "type_optimization": self.config.type_optimization,
            },
            "statistics": self.collection_stats,
        }

        # Export to JSON
        output_path = (
            Path(self.config.output_directory)
            / f"data_collection_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(output_path, "w") as f:
            json.dump(stats_with_metadata, f, indent=2)

        return str(output_path)


# Example usage and testing functions
def create_mock_data_sources(
    num_files: int = 5, wells_per_file: int = 25
) -> Tuple[List[str], List[str]]:
    """Create mock data sources for testing."""
    import tempfile

    lease_sources = []
    api12_sources = []

    temp_dir = Path(tempfile.mkdtemp())

    for i in range(num_files):
        # Create lease method mock data
        lease_data = pd.DataFrame(
            {
                "API_WELL_NUMBER": [
                    f"60812400{j:04d}"
                    for j in range(i * wells_per_file, (i + 1) * wells_per_file)
                ],
                "WELL_NAME": [
                    f"Lease Well {j}"
                    for j in range(i * wells_per_file, (i + 1) * wells_per_file)
                ],
                "DRILLING_DAYS": np.random.randint(20, 80, wells_per_file),
                "COMPLETION_DAYS": np.random.randint(5, 25, wells_per_file),
            }
        )

        lease_file = temp_dir / f"lease_data_{i}.xlsx"
        lease_data.to_excel(lease_file, index=False)
        lease_sources.append(str(lease_file))

        # Create API12 method mock data
        api12_data = pd.DataFrame(
            {
                "API12": [
                    f"60812400{j:04d}"
                    for j in range(i * wells_per_file, (i + 1) * wells_per_file)
                ],
                "Well_Name": [
                    f"API12 Well {j}"
                    for j in range(i * wells_per_file, (i + 1) * wells_per_file)
                ],
                "Drilling Days": np.random.randint(18, 85, wells_per_file),
                "Completion Days": np.random.randint(4, 28, wells_per_file),
            }
        )

        api12_file = temp_dir / f"api12_data_{i}.csv"
        api12_data.to_csv(api12_file, index=False)
        api12_sources.append(str(api12_file))

    return lease_sources, api12_sources


if __name__ == "__main__":
    # Example usage
    config = DataCollectionConfig(
        chunk_size=30,
        memory_limit_mb=512,
        enable_progress_tracking=True,
        enable_logging=True,
    )

    collector = LargeScaleDataCollector(config)

    # Create mock data sources
    lease_sources, api12_sources = create_mock_data_sources(5, 25)  # 125 wells total

    print("Testing large-scale data collection with 125 wells...")

    # Collect lease method data
    lease_data_gen = collector.collect_lease_method_data(lease_sources)
    lease_df = collector.aggregate_collected_data(lease_data_gen, max_wells=125)

    # Collect API12 method data
    api12_data_gen = collector.collect_api12_method_data(api12_sources)
    api12_df = collector.aggregate_collected_data(api12_data_gen, max_wells=125)

    print(f"Collected lease data: {len(lease_df)} wells")
    print(f"Collected API12 data: {len(api12_df)} wells")

    # Export statistics
    stats_file = collector.export_collection_stats()
    print(f"Statistics exported to: {stats_file}")
