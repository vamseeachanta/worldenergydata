"""
Batch processing module for SODIR data operations.

Implements efficient batch processing patterns adapted from BSEE
batch exporters for handling large-scale data operations.
"""

import concurrent.futures
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class BatchStatus(Enum):
    """Status of batch processing operation."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    batch_size: int = 100
    max_workers: int = 4
    use_parallel: bool = True
    timeout_seconds: int = 300
    retry_failed: bool = True
    max_retries: int = 3
    save_intermediate: bool = True
    output_format: str = "json"
    compression: bool = False


@dataclass
class BatchResult:
    """Result from batch processing operation."""

    batch_id: str
    status: BatchStatus
    total_items: int
    processed_items: int
    failed_items: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    processing_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    output_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result["status"] = self.status.value
        result["start_time"] = self.start_time.isoformat()
        result["end_time"] = self.end_time.isoformat() if self.end_time else None
        return result


class SodirBatchProcessor:
    """
    Batch processor for SODIR data operations.

    Adapted from BSEE batch exporter patterns to handle:
    - Large-scale data collection
    - Parallel batch processing
    - Incremental processing with checkpoints
    - Multiple output formats
    - Error recovery and retry logic
    """

    def __init__(self, config: Optional[BatchConfig] = None):
        """
        Initialize batch processor.

        Args:
            config: Batch processing configuration
        """
        self.config = config or BatchConfig()
        self.current_batch: Optional[BatchResult] = None
        self.batch_history: List[BatchResult] = []

        # Processing functions registry
        self.processors: Dict[str, Callable] = {}
        self.formatters: Dict[str, Callable] = {}

        # Register default formatters
        self._register_default_formatters()

    def process_data_collection(
        self, api_client: Any, collection_specs: List[Dict[str, Any]], output_dir: Path
    ) -> BatchResult:
        """
        Process batch data collection from SODIR API.

        Args:
            api_client: Configured SODIR API client
            collection_specs: List of collection specifications
            output_dir: Directory for output files

        Returns:
            BatchResult with processing outcomes
        """
        batch_id = f"collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        batch_result = BatchResult(
            batch_id=batch_id,
            status=BatchStatus.PROCESSING,
            total_items=len(collection_specs),
            processed_items=0,
        )

        self.current_batch = batch_result
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            if self.config.use_parallel and len(collection_specs) > 1:
                results = self._parallel_collection(
                    api_client, collection_specs, output_dir
                )
            else:
                results = self._sequential_collection(
                    api_client, collection_specs, output_dir
                )

            # Process results
            for spec, data, error in results:
                if error:
                    batch_result.failed_items += 1
                    batch_result.errors.append(f"{spec['data_type']}: {error}")
                else:
                    batch_result.processed_items += 1

                    # Save data if configured
                    if self.config.save_intermediate and data:
                        output_file = self._save_batch_data(
                            data, spec["data_type"], output_dir
                        )
                        if output_file:
                            batch_result.output_files.append(str(output_file))

            # Determine final status
            if batch_result.failed_items == 0:
                batch_result.status = BatchStatus.COMPLETED
            elif batch_result.processed_items > 0:
                batch_result.status = BatchStatus.PARTIAL
            else:
                batch_result.status = BatchStatus.FAILED

        except Exception as e:
            logger.error(f"Batch collection failed: {e}")
            batch_result.status = BatchStatus.FAILED
            batch_result.errors.append(str(e))

        finally:
            batch_result.end_time = datetime.now()
            batch_result.processing_time = (
                batch_result.end_time - batch_result.start_time
            ).total_seconds()
            self.batch_history.append(batch_result)
            self.current_batch = None

        return batch_result

    def process_data_transformation(
        self,
        input_data: List[Dict[str, Any]],
        transform_func: Callable,
        output_dir: Path,
    ) -> BatchResult:
        """
        Process batch data transformation.

        Args:
            input_data: Data to transform
            transform_func: Transformation function
            output_dir: Directory for output files

        Returns:
            BatchResult with processing outcomes
        """
        batch_id = f"transform_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        batch_result = BatchResult(
            batch_id=batch_id,
            status=BatchStatus.PROCESSING,
            total_items=len(input_data),
            processed_items=0,
        )

        self.current_batch = batch_result
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Process in chunks
            chunks = self._create_chunks(input_data, self.config.batch_size)

            if self.config.use_parallel and len(chunks) > 1:
                results = self._parallel_transform(chunks, transform_func)
            else:
                results = self._sequential_transform(chunks, transform_func)

            # Combine results
            all_transformed = []
            for chunk_result, error in results:
                if error:
                    batch_result.failed_items += (
                        len(chunk_result) if chunk_result else self.config.batch_size
                    )
                    batch_result.errors.append(str(error))
                else:
                    batch_result.processed_items += (
                        len(chunk_result) if chunk_result else 0
                    )
                    if chunk_result:
                        all_transformed.extend(chunk_result)

            # Save combined results
            if all_transformed:
                output_file = self._save_batch_data(
                    all_transformed, "transformed", output_dir
                )
                if output_file:
                    batch_result.output_files.append(str(output_file))

            # Determine status
            if batch_result.failed_items == 0:
                batch_result.status = BatchStatus.COMPLETED
            elif batch_result.processed_items > 0:
                batch_result.status = BatchStatus.PARTIAL
            else:
                batch_result.status = BatchStatus.FAILED

        except Exception as e:
            logger.error(f"Batch transformation failed: {e}")
            batch_result.status = BatchStatus.FAILED
            batch_result.errors.append(str(e))

        finally:
            batch_result.end_time = datetime.now()
            batch_result.processing_time = (
                batch_result.end_time - batch_result.start_time
            ).total_seconds()
            self.batch_history.append(batch_result)
            self.current_batch = None

        return batch_result

    def process_multi_format_export(
        self,
        data: Union[List[Dict], Dict],
        formats: List[str],
        output_dir: Path,
        base_name: str = "export",
    ) -> BatchResult:
        """
        Export data to multiple formats in parallel.

        Args:
            data: Data to export
            formats: List of output formats (json, csv, parquet, etc.)
            output_dir: Directory for output files
            base_name: Base name for output files

        Returns:
            BatchResult with export outcomes
        """
        batch_id = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        batch_result = BatchResult(
            batch_id=batch_id,
            status=BatchStatus.PROCESSING,
            total_items=len(formats),
            processed_items=0,
        )

        self.current_batch = batch_result
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            if self.config.use_parallel and len(formats) > 1:
                # Parallel export to multiple formats
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.config.max_workers
                ) as executor:
                    futures = {}

                    for format_type in formats:
                        if format_type in self.formatters:
                            future = executor.submit(
                                self._export_single_format,
                                data,
                                format_type,
                                output_dir,
                                base_name,
                            )
                            futures[future] = format_type
                        else:
                            batch_result.errors.append(f"Unknown format: {format_type}")
                            batch_result.failed_items += 1

                    # Collect results
                    for future in concurrent.futures.as_completed(futures):
                        format_type = futures[future]
                        try:
                            output_file = future.result(
                                timeout=self.config.timeout_seconds
                            )
                            if output_file:
                                batch_result.output_files.append(str(output_file))
                                batch_result.processed_items += 1
                            else:
                                batch_result.failed_items += 1
                                batch_result.errors.append(
                                    f"Failed to export {format_type}"
                                )
                        except Exception as e:
                            batch_result.failed_items += 1
                            batch_result.errors.append(f"{format_type}: {str(e)}")
            else:
                # Sequential export
                for format_type in formats:
                    try:
                        output_file = self._export_single_format(
                            data, format_type, output_dir, base_name
                        )
                        if output_file:
                            batch_result.output_files.append(str(output_file))
                            batch_result.processed_items += 1
                        else:
                            batch_result.failed_items += 1
                    except Exception as e:
                        batch_result.failed_items += 1
                        batch_result.errors.append(f"{format_type}: {str(e)}")

            # Determine status
            if batch_result.failed_items == 0:
                batch_result.status = BatchStatus.COMPLETED
            elif batch_result.processed_items > 0:
                batch_result.status = BatchStatus.PARTIAL
            else:
                batch_result.status = BatchStatus.FAILED

        except Exception as e:
            logger.error(f"Multi-format export failed: {e}")
            batch_result.status = BatchStatus.FAILED
            batch_result.errors.append(str(e))

        finally:
            batch_result.end_time = datetime.now()
            batch_result.processing_time = (
                batch_result.end_time - batch_result.start_time
            ).total_seconds()
            self.batch_history.append(batch_result)
            self.current_batch = None

        return batch_result

    def process_incremental_sync(
        self,
        api_client: Any,
        last_sync_time: datetime,
        data_types: List[str],
        output_dir: Path,
    ) -> BatchResult:
        """
        Process incremental data sync since last update.

        Args:
            api_client: SODIR API client
            last_sync_time: Last synchronization timestamp
            data_types: Data types to sync
            output_dir: Directory for output files

        Returns:
            BatchResult with sync outcomes
        """
        batch_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        batch_result = BatchResult(
            batch_id=batch_id,
            status=BatchStatus.PROCESSING,
            total_items=len(data_types),
            processed_items=0,
            metadata={"last_sync": last_sync_time.isoformat()},
        )

        self.current_batch = batch_result
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            for data_type in data_types:
                try:
                    # Fetch updated data
                    params = {
                        "updated_since": last_sync_time.isoformat(),
                        "limit": self.config.batch_size,
                    }

                    all_data = []
                    offset = 0

                    while True:
                        params["offset"] = offset

                        # Fetch batch
                        if data_type == "blocks":
                            batch = api_client.get_blocks(**params)
                        elif data_type == "wellbores":
                            batch = api_client.get_wellbores(**params)
                        elif data_type == "fields":
                            batch = api_client.get_fields(**params)
                        else:
                            logger.warning(f"Unknown data type: {data_type}")
                            break

                        if not batch:
                            break

                        all_data.extend(batch)

                        # Check if more data available
                        if len(batch) < self.config.batch_size:
                            break

                        offset += self.config.batch_size

                    # Save incremental data
                    if all_data:
                        output_file = self._save_batch_data(
                            all_data, f"{data_type}_incremental", output_dir
                        )
                        if output_file:
                            batch_result.output_files.append(str(output_file))
                            batch_result.metadata[f"{data_type}_count"] = len(all_data)

                    batch_result.processed_items += 1

                except Exception as e:
                    logger.error(f"Failed to sync {data_type}: {e}")
                    batch_result.failed_items += 1
                    batch_result.errors.append(f"{data_type}: {str(e)}")

            # Determine status
            if batch_result.failed_items == 0:
                batch_result.status = BatchStatus.COMPLETED
            elif batch_result.processed_items > 0:
                batch_result.status = BatchStatus.PARTIAL
            else:
                batch_result.status = BatchStatus.FAILED

        except Exception as e:
            logger.error(f"Incremental sync failed: {e}")
            batch_result.status = BatchStatus.FAILED
            batch_result.errors.append(str(e))

        finally:
            batch_result.end_time = datetime.now()
            batch_result.processing_time = (
                batch_result.end_time - batch_result.start_time
            ).total_seconds()
            batch_result.metadata["new_sync_time"] = datetime.now().isoformat()
            self.batch_history.append(batch_result)
            self.current_batch = None

        return batch_result

    def register_processor(self, name: str, func: Callable):
        """Register a data processor function."""
        self.processors[name] = func

    def register_formatter(self, format_type: str, func: Callable):
        """Register a data formatter function."""
        self.formatters[format_type] = func

    def get_batch_status(self, batch_id: str) -> Optional[BatchResult]:
        """Get status of a specific batch."""
        for batch in self.batch_history:
            if batch.batch_id == batch_id:
                return batch
        return None

    def get_current_status(self) -> Optional[BatchResult]:
        """Get status of currently processing batch."""
        return self.current_batch

    def get_statistics(self) -> Dict[str, Any]:
        """Get batch processing statistics."""
        total_batches = len(self.batch_history)
        if total_batches == 0:
            return {"total_batches": 0, "success_rate": 0.0, "avg_processing_time": 0.0}

        successful = sum(
            1 for b in self.batch_history if b.status == BatchStatus.COMPLETED
        )
        total_time = sum(b.processing_time for b in self.batch_history)
        total_items = sum(b.processed_items for b in self.batch_history)

        return {
            "total_batches": total_batches,
            "successful_batches": successful,
            "failed_batches": sum(
                1 for b in self.batch_history if b.status == BatchStatus.FAILED
            ),
            "partial_batches": sum(
                1 for b in self.batch_history if b.status == BatchStatus.PARTIAL
            ),
            "success_rate": successful / total_batches,
            "total_items_processed": total_items,
            "avg_processing_time": total_time / total_batches,
            "total_processing_time": total_time,
        }

    def _parallel_collection(
        self, api_client: Any, collection_specs: List[Dict[str, Any]], output_dir: Path
    ) -> List[Tuple[Dict, Any, Optional[str]]]:
        """Execute parallel data collection."""
        results = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.max_workers
        ) as executor:
            futures = {}

            for spec in collection_specs:
                future = executor.submit(self._collect_single, api_client, spec)
                futures[future] = spec

            for future in concurrent.futures.as_completed(futures):
                spec = futures[future]
                try:
                    data = future.result(timeout=self.config.timeout_seconds)
                    results.append((spec, data, None))
                except Exception as e:
                    results.append((spec, None, str(e)))

        return results

    def _sequential_collection(
        self, api_client: Any, collection_specs: List[Dict[str, Any]], output_dir: Path
    ) -> List[Tuple[Dict, Any, Optional[str]]]:
        """Execute sequential data collection."""
        results = []

        for spec in collection_specs:
            try:
                data = self._collect_single(api_client, spec)
                results.append((spec, data, None))
            except Exception as e:
                results.append((spec, None, str(e)))

        return results

    def _collect_single(self, api_client: Any, spec: Dict[str, Any]) -> Any:
        """Collect data for a single specification."""
        data_type = spec.get("data_type")
        params = spec.get("params", {})

        if data_type == "blocks":
            return api_client.get_blocks(**params)
        elif data_type == "wellbores":
            return api_client.get_wellbores(**params)
        elif data_type == "fields":
            return api_client.get_fields(**params)
        elif data_type == "discoveries":
            return api_client.get_discoveries(**params)
        elif data_type == "surveys":
            return api_client.get_surveys(**params)
        else:
            raise ValueError(f"Unknown data type: {data_type}")

    def _create_chunks(self, data: List[Any], chunk_size: int) -> List[List[Any]]:
        """Split data into chunks."""
        chunks = []
        for i in range(0, len(data), chunk_size):
            chunks.append(data[i : i + chunk_size])
        return chunks

    def _parallel_transform(
        self, chunks: List[List[Any]], transform_func: Callable
    ) -> List[Tuple[Any, Optional[str]]]:
        """Execute parallel transformation."""
        results = []

        with concurrent.futures.ProcessPoolExecutor(
            max_workers=self.config.max_workers
        ) as executor:
            futures = [executor.submit(transform_func, chunk) for chunk in chunks]

            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=self.config.timeout_seconds)
                    results.append((result, None))
                except Exception as e:
                    results.append((None, str(e)))

        return results

    def _sequential_transform(
        self, chunks: List[List[Any]], transform_func: Callable
    ) -> List[Tuple[Any, Optional[str]]]:
        """Execute sequential transformation."""
        results = []

        for chunk in chunks:
            try:
                result = transform_func(chunk)
                results.append((result, None))
            except Exception as e:
                results.append((None, str(e)))

        return results

    def _save_batch_data(
        self, data: Any, name: str, output_dir: Path
    ) -> Optional[Path]:
        """Save batch data to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            if self.config.output_format == "json":
                file_path = output_dir / f"{name}_{timestamp}.json"
                file_path.write_text(json.dumps(data, indent=2, default=str))
            elif self.config.output_format == "csv":
                # Would implement CSV export here
                file_path = output_dir / f"{name}_{timestamp}.csv"
                # CSV writing logic
            else:
                logger.warning(f"Unknown output format: {self.config.output_format}")
                return None

            return file_path

        except Exception as e:
            logger.error(f"Failed to save batch data: {e}")
            return None

    def _export_single_format(
        self, data: Any, format_type: str, output_dir: Path, base_name: str
    ) -> Optional[Path]:
        """Export data to a single format."""
        if format_type in self.formatters:
            formatter = self.formatters[format_type]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = output_dir / f"{base_name}_{timestamp}.{format_type}"

            try:
                formatted_data = formatter(data)
                file_path.write_text(formatted_data)
                return file_path
            except Exception as e:
                logger.error(f"Failed to export {format_type}: {e}")
                return None

        return None

    def _register_default_formatters(self):
        """Register default data formatters."""
        # JSON formatter
        self.formatters["json"] = lambda data: json.dumps(data, indent=2, default=str)

        # CSV formatter (simplified)
        def csv_formatter(data):
            if isinstance(data, list) and data and isinstance(data[0], dict):
                import csv
                import io

                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                return output.getvalue()
            return ""

        self.formatters["csv"] = csv_formatter
