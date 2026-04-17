"""
Batch export functionality for comprehensive reports.

Allows exporting reports to multiple formats simultaneously.
"""

import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from worldenergydata.common.logging import get_logger

from .base import ExportConfig, ExportFormat, ExportResult, ReportExporter
from .excel_exporter import ExcelExporter
from .pdf_exporter import PDFExporter

logger = get_logger(__name__)


class BatchExporter:
    """
    Batch exporter for multiple format exports.

    Coordinates export to multiple formats simultaneously with
    optional parallel processing.
    """

    def __init__(self, use_parallel: bool = True, max_workers: int = 4):
        """
        Initialize batch exporter.

        Args:
            use_parallel: Whether to use parallel processing
            max_workers: Maximum number of parallel workers
        """
        self.use_parallel = use_parallel
        self.max_workers = max_workers
        self.exporters = self._initialize_exporters()

    def _initialize_exporters(self) -> Dict[ExportFormat, ReportExporter]:
        """Initialize available exporters."""
        exporters = {}

        # Excel exporter
        try:
            exporters[ExportFormat.EXCEL] = ExcelExporter()
        except Exception as e:
            logger.info(f"Failed to initialize Excel exporter: {e}")

        # PDF exporter
        try:
            exporters[ExportFormat.PDF] = PDFExporter()
        except Exception as e:
            logger.info(f"Failed to initialize PDF exporter: {e}")

        return exporters

    def export_batch(
        self, data: Dict[str, Any], configs: List[ExportConfig]
    ) -> List[ExportResult]:
        """
        Export report data to multiple formats.

        Args:
            data: Report data to export
            configs: List of export configurations

        Returns:
            List of ExportResult objects
        """
        results = []

        if self.use_parallel and len(configs) > 1:
            # Parallel export
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers
            ) as executor:
                futures = []

                for config in configs:
                    if config.format in self.exporters:
                        future = executor.submit(self._export_single, data, config)
                        futures.append(future)
                    else:
                        # Format not supported
                        result = ExportResult(
                            success=False,
                            message=f"Export format {config.format.value} not supported",
                        )
                        results.append(result)

                # Collect results
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        result = ExportResult(
                            success=False, message=f"Export failed: {str(e)}"
                        )
                        results.append(result)
        else:
            # Sequential export
            for config in configs:
                result = self._export_single(data, config)
                results.append(result)

        return results

    def _export_single(
        self, data: Dict[str, Any], config: ExportConfig
    ) -> ExportResult:
        """
        Export to a single format.

        Args:
            data: Report data
            config: Export configuration

        Returns:
            ExportResult
        """
        if config.format not in self.exporters:
            return ExportResult(
                success=False,
                message=f"Exporter for {config.format.value} not available",
            )

        exporter = self.exporters[config.format]
        return exporter.export(data, config)

    def export_all_formats(
        self, data: Dict[str, Any], base_path: Path, base_name: str = None
    ) -> Dict[ExportFormat, ExportResult]:
        """
        Export to all available formats.

        Args:
            data: Report data
            base_path: Base directory for exports
            base_name: Base filename (without extension)

        Returns:
            Dictionary mapping format to result
        """
        if base_name is None:
            base_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        results = {}
        configs = []

        # Create configurations for all available formats
        for format_type, exporter in self.exporters.items():
            extension = exporter.get_file_extension()
            output_path = base_path / f"{base_name}{extension}"

            config = ExportConfig(format=format_type, output_path=output_path)
            configs.append(config)

        # Batch export
        export_results = self.export_batch(data, configs)

        # Map results to formats
        for config, result in zip(configs, export_results):
            results[config.format] = result

        return results

    def get_available_formats(self) -> List[ExportFormat]:
        """
        Get list of available export formats.

        Returns:
            List of ExportFormat enums
        """
        return list(self.exporters.keys())

    def validate_configs(self, configs: List[ExportConfig]) -> List[str]:
        """
        Validate export configurations.

        Args:
            configs: List of configurations to validate

        Returns:
            List of validation error messages
        """
        errors = []

        for i, config in enumerate(configs):
            # Check format support
            if config.format not in self.exporters:
                errors.append(f"Config {i}: Format {config.format.value} not supported")

            # Check output path
            if not config.output_path:
                errors.append(f"Config {i}: Output path not specified")

            # Check for duplicate output paths
            for j, other_config in enumerate(configs[i + 1 :], i + 1):
                if config.output_path == other_config.output_path:
                    errors.append(
                        f"Configs {i} and {j}: Duplicate output path {config.output_path}"
                    )

        return errors

    def create_summary_report(self, results: List[ExportResult]) -> str:
        """
        Create summary report of batch export results.

        Args:
            results: List of export results

        Returns:
            Summary report string
        """
        summary = []
        summary.append("=" * 50)
        summary.append("BATCH EXPORT SUMMARY")
        summary.append("=" * 50)
        summary.append(f"Total exports: {len(results)}")

        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        summary.append(f"Successful: {successful}")
        summary.append(f"Failed: {failed}")
        summary.append("")

        # Detail for each export
        for i, result in enumerate(results, 1):
            summary.append(f"Export {i}:")
            summary.append(f"  Status: {'Success' if result.success else 'Failed'}")

            if result.file_path:
                summary.append(f"  File: {result.file_path}")

                if result.file_size:
                    size_mb = result.file_size / (1024 * 1024)
                    summary.append(f"  Size: {size_mb:.2f} MB")

                if result.export_time:
                    summary.append(f"  Time: {result.export_time:.2f} seconds")

            if result.message:
                summary.append(f"  Message: {result.message}")

            if result.errors:
                summary.append(f"  Errors: {', '.join(result.errors)}")

            if result.warnings:
                summary.append(f"  Warnings: {', '.join(result.warnings)}")

            summary.append("")

        summary.append("=" * 50)

        return "\n".join(summary)
