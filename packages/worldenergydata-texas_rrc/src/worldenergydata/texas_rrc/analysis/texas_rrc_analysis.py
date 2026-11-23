# ABOUTME: Main analysis router for Texas RRC module
# ABOUTME: Coordinates various analysis tasks based on configuration

"""
Texas RRC Analysis Router.

Orchestrates analysis operations on Texas RRC data
based on configuration settings.
"""

import logging
from typing import Any, Dict, Optional

from ..processors import PermitProcessor, ProductionProcessor, WellProcessor

logger = logging.getLogger(__name__)


class TexasRRCAnalysis:
    """
    Analysis orchestrator for Texas RRC module.

    Coordinates various analysis operations on collected data.
    """

    def __init__(
        self,
        production_processor: Optional[ProductionProcessor] = None,
        well_processor: Optional[WellProcessor] = None,
        permit_processor: Optional[PermitProcessor] = None,
    ):
        """
        Initialize analysis router.

        Args:
            production_processor: Optional pre-configured processor
            well_processor: Optional pre-configured processor
            permit_processor: Optional pre-configured processor
        """
        self._production_processor = production_processor
        self._well_processor = well_processor
        self._permit_processor = permit_processor

    @property
    def production_processor(self) -> ProductionProcessor:
        """Get or create production processor."""
        if self._production_processor is None:
            self._production_processor = ProductionProcessor()
        return self._production_processor

    @property
    def well_processor(self) -> WellProcessor:
        """Get or create well processor."""
        if self._well_processor is None:
            self._well_processor = WellProcessor()
        return self._well_processor

    @property
    def permit_processor(self) -> PermitProcessor:
        """Get or create permit processor."""
        if self._permit_processor is None:
            self._permit_processor = PermitProcessor()
        return self._permit_processor

    def router(
        self,
        cfg: Dict[str, Any],
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Route analysis based on configuration.

        Args:
            cfg: Configuration dictionary containing:
                - analysis.types: List of analysis types to run
                - analysis.aggregation: Aggregation settings
                - analysis.filters: Filter settings
            data: Dictionary of collected data by type

        Returns:
            Updated configuration with analysis results
        """
        analysis_cfg = cfg.get("analysis", {})
        analysis_types = analysis_cfg.get("types", ["summary"])
        aggregation = analysis_cfg.get("aggregation", "district")
        filters = analysis_cfg.get("filters", {})

        results: Dict[str, Any] = {}

        for analysis_type in analysis_types:
            try:
                logger.info(f"Running {analysis_type} analysis")
                result = self._run_analysis(analysis_type, data, aggregation, filters)
                results[analysis_type] = result
            except Exception as e:
                logger.error(f"Analysis {analysis_type} failed: {e}")
                results[analysis_type] = {"error": str(e)}

        # Update config with results
        if cfg.get("basename"):
            cfg[cfg["basename"]]["analysis"] = {
                "completed": list(results.keys()),
                "results": results,
            }

        return cfg

    def _run_analysis(
        self,
        analysis_type: str,
        data: Dict[str, Any],
        aggregation: str,
        filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run specific analysis type.

        Args:
            analysis_type: Type of analysis
            data: Collected data
            aggregation: Aggregation level
            filters: Filter settings

        Returns:
            Analysis results
        """
        if analysis_type == "summary":
            return self._summary_analysis(data)
        elif analysis_type == "production":
            return self._production_analysis(data, aggregation, filters)
        elif analysis_type == "wells":
            return self._well_analysis(data, aggregation, filters)
        elif analysis_type == "permits":
            return self._permit_analysis(data, aggregation, filters)
        elif analysis_type == "trends":
            return self._trend_analysis(data, filters)
        else:
            logger.warning(f"Unknown analysis type: {analysis_type}")
            return {"error": f"Unknown analysis type: {analysis_type}"}

    def _summary_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary statistics for all data.

        Args:
            data: Collected data

        Returns:
            Summary statistics
        """
        summary = {
            "data_types_available": list(data.keys()),
            "statistics": {},
        }

        for data_type, type_data in data.items():
            if isinstance(type_data, dict):
                if "file_path" in type_data:
                    summary["statistics"][data_type] = {
                        "status": type_data.get("status", "unknown"),
                        "file_path": type_data.get("file_path"),
                    }
                elif "results" in type_data:
                    summary["statistics"][data_type] = {
                        "result_count": len(type_data.get("results", [])),
                    }

        return summary

    def _production_analysis(
        self,
        data: Dict[str, Any],
        aggregation: str,
        filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyze production data.

        Args:
            data: Collected data
            aggregation: Aggregation level (district, lease, field)
            filters: Filter settings

        Returns:
            Production analysis results
        """
        production_data = data.get("production", {})

        # Check if we have actual records or just file metadata
        if "file_path" in production_data:
            return {
                "status": "file_downloaded",
                "file_path": production_data["file_path"],
                "note": "Load file for detailed analysis",
            }

        records = production_data.get("records", [])
        if not records:
            return {"error": "No production records available"}

        # Process records
        processed = self.production_processor.process(records)

        # Apply filters
        if filters.get("date_range"):
            start, end = filters["date_range"]
            processed = self.production_processor.filter_by_date_range(
                processed, start, end
            )

        # Aggregate based on setting
        if aggregation == "district":
            aggregated = self.production_processor.aggregate_by_district(processed)
        elif aggregation == "lease":
            aggregated = self.production_processor.aggregate_by_lease(processed)
        else:
            aggregated = {}

        return {
            "total_records": len(processed),
            "aggregation": aggregation,
            "aggregated_data": aggregated,
            "processor_stats": self.production_processor.stats,
        }

    def _well_analysis(
        self,
        data: Dict[str, Any],
        aggregation: str,
        filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyze well data.

        Args:
            data: Collected data
            aggregation: Aggregation level
            filters: Filter settings

        Returns:
            Well analysis results
        """
        well_data = data.get("wells", {})

        if "file_path" in well_data:
            return {
                "status": "file_downloaded",
                "file_path": well_data.get("file_path"),
                "note": "Load file for detailed analysis",
            }

        records = well_data.get("records", [])
        if not records:
            return {"error": "No well records available"}

        # Process records
        processed = self.well_processor.process(records)

        # Apply filters
        if filters.get("statuses"):
            processed = self.well_processor.filter_by_status(
                processed, filters["statuses"]
            )
        if filters.get("well_types"):
            processed = self.well_processor.filter_by_well_type(
                processed, filters["well_types"]
            )
        if filters.get("districts"):
            processed = self.well_processor.filter_by_district(
                processed, filters["districts"]
            )

        # Generate summary
        summary = self.well_processor.summarize_by_district(processed)

        return {
            "total_records": len(processed),
            "district_summary": summary,
            "processor_stats": self.well_processor.stats,
        }

    def _permit_analysis(
        self,
        data: Dict[str, Any],
        aggregation: str,
        filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyze drilling permit data.

        Args:
            data: Collected data
            aggregation: Aggregation level
            filters: Filter settings

        Returns:
            Permit analysis results
        """
        permit_data = data.get("drilling_permits", {})

        if "file_path" in permit_data:
            return {
                "status": "file_downloaded",
                "file_path": permit_data.get("file_path"),
                "note": "Load file for detailed analysis",
            }

        records = permit_data.get("records", [])
        if not records:
            return {"error": "No permit records available"}

        # Process records
        processed = self.permit_processor.process(records)

        # Apply filters
        if filters.get("permit_types"):
            processed = self.permit_processor.filter_by_permit_type(
                processed, filters["permit_types"]
            )
        if filters.get("statuses"):
            processed = self.permit_processor.filter_by_status(
                processed, filters["statuses"]
            )
        if filters.get("date_range"):
            start, end = filters["date_range"]
            processed = self.permit_processor.filter_by_date_range(
                processed, start, end
            )

        # Generate summaries
        district_summary = self.permit_processor.summarize_by_district(processed)
        operator_summary = self.permit_processor.summarize_by_operator(processed)

        return {
            "total_records": len(processed),
            "district_summary": district_summary,
            "top_operators": sorted(
                operator_summary.values(),
                key=lambda x: x["total_permits"],
                reverse=True,
            )[:10],
            "processor_stats": self.permit_processor.stats,
        }

    def _trend_analysis(
        self,
        data: Dict[str, Any],
        filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyze trends over time.

        Args:
            data: Collected data
            filters: Filter settings

        Returns:
            Trend analysis results
        """
        # Placeholder for trend analysis
        return {
            "status": "not_implemented",
            "note": "Trend analysis requires time-series data processing",
        }


__all__ = ["TexasRRCAnalysis"]
