# ABOUTME: Data quality dashboard module for marine safety incidents with coverage, completeness, and duplicate analysis
# ABOUTME: Provides metrics by source, year, field completeness percentages, geographic coverage, and JSON/CLI exports

"""
Data Quality Dashboard for Marine Safety Module

This module provides comprehensive data quality analysis and reporting for marine
safety incident data. It calculates coverage metrics, field completeness, duplicate
detection statistics, and generates summary reports.

Classes:
    DataQualityDashboard: Main class for data quality analysis
    CoverageReport: Container for coverage analysis results
    CompletenessReport: Container for field completeness metrics
    DuplicateReport: Container for duplicate detection statistics
    QualitySummary: Container for overall quality summary

Example:
    >>> from sqlalchemy.orm import Session
    >>> from worldenergydata.marine_safety.reports import DataQualityDashboard
    >>>
    >>> dashboard = DataQualityDashboard(session)
    >>> summary = dashboard.generate_summary()
    >>> summary.print_console()
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, distinct, extract, func
from sqlalchemy.orm import Session

from worldenergydata.marine_safety.constants import (
    OFFSHORE_REGIONS,
    DataSource,
    IncidentType,
    SeverityLevel,
)
from worldenergydata.marine_safety.database.models import (
    Incident,
    IncidentLink,
    Location,
    Vessel,
)

logger = logging.getLogger(__name__)


def _decimal_default(obj: Any) -> Any:
    """JSON serializer for Decimal objects."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@dataclass
class CoverageReport:
    """
    Container for data coverage analysis results.

    Attributes:
        by_source: Record counts per data source
        by_year: Record counts per year
        by_source_year: Record counts per source and year combination
        total_records: Total number of incident records
        date_range: Tuple of (earliest, latest) incident dates
        metadata: Additional analysis metadata

    Methods:
        to_dict: Convert coverage report to dictionary
        to_json: Export coverage report to JSON string
    """

    by_source: Dict[str, int]
    by_year: Dict[int, int]
    by_source_year: Dict[str, Dict[int, int]]
    total_records: int
    date_range: Tuple[Optional[date], Optional[date]]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert coverage report to dictionary format."""
        return {
            "by_source": self.by_source,
            "by_year": self.by_year,
            "by_source_year": self.by_source_year,
            "total_records": self.total_records,
            "date_range": {
                "start": self.date_range[0].isoformat() if self.date_range[0] else None,
                "end": self.date_range[1].isoformat() if self.date_range[1] else None,
            },
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Export coverage report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=_decimal_default)


@dataclass
class CompletenessReport:
    """
    Container for field completeness analysis results.

    Attributes:
        field_completeness: Percentage of non-null values per field
        by_source: Field completeness broken down by data source
        total_records: Total records analyzed
        critical_fields: Completeness of critical fields (vessel_name, imo, coords)
        metadata: Additional analysis metadata

    Methods:
        to_dict: Convert completeness report to dictionary
        to_json: Export completeness report to JSON string
    """

    field_completeness: Dict[str, float]
    by_source: Dict[str, Dict[str, float]]
    total_records: int
    critical_fields: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert completeness report to dictionary format."""
        return {
            "field_completeness": self.field_completeness,
            "by_source": self.by_source,
            "total_records": self.total_records,
            "critical_fields": self.critical_fields,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Export completeness report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=_decimal_default)


@dataclass
class DuplicateReport:
    """
    Container for duplicate detection analysis results.

    Attributes:
        total_links: Total number of linked incident pairs
        verified_duplicates: Count of verified duplicate pairs
        potential_duplicates: Count of unverified potential duplicates
        by_confidence: Distribution by confidence score ranges
        by_match_type: Distribution by match type
        metadata: Additional analysis metadata

    Methods:
        to_dict: Convert duplicate report to dictionary
        to_json: Export duplicate report to JSON string
    """

    total_links: int
    verified_duplicates: int
    potential_duplicates: int
    by_confidence: Dict[str, int]
    by_match_type: Dict[str, int]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert duplicate report to dictionary format."""
        return {
            "total_links": self.total_links,
            "verified_duplicates": self.verified_duplicates,
            "potential_duplicates": self.potential_duplicates,
            "by_confidence": self.by_confidence,
            "by_match_type": self.by_match_type,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Export duplicate report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=_decimal_default)


@dataclass
class QualitySummary:
    """
    Container for overall data quality summary.

    Attributes:
        coverage: CoverageReport instance
        completeness: CompletenessReport instance
        duplicates: DuplicateReport instance
        incident_type_distribution: Distribution of incident types
        severity_distribution: Distribution of severity levels
        geographic_coverage: Coverage by region/country
        overall_quality_score: Computed overall quality score (0-100)
        generated_at: Timestamp when summary was generated
        metadata: Additional summary metadata

    Methods:
        to_dict: Convert summary to dictionary
        to_json: Export summary to JSON string
        print_console: Print formatted summary to console using Rich
    """

    coverage: CoverageReport
    completeness: CompletenessReport
    duplicates: DuplicateReport
    incident_type_distribution: Dict[str, int]
    severity_distribution: Dict[int, int]
    geographic_coverage: Dict[str, int]
    overall_quality_score: float
    generated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary format."""
        return {
            "coverage": self.coverage.to_dict(),
            "completeness": self.completeness.to_dict(),
            "duplicates": self.duplicates.to_dict(),
            "incident_type_distribution": self.incident_type_distribution,
            "severity_distribution": self.severity_distribution,
            "geographic_coverage": self.geographic_coverage,
            "overall_quality_score": self.overall_quality_score,
            "generated_at": self.generated_at.isoformat(),
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Export summary to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=_decimal_default)

    def save_json(self, filepath: Path) -> None:
        """
        Save summary to JSON file.

        Args:
            filepath: Path to output JSON file
        """
        filepath.write_text(self.to_json())
        logger.info(f"Quality summary saved to {filepath}")

    def print_console(self) -> None:
        """Print formatted summary to console using Rich tables."""
        try:
            from rich import box
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table

            console = Console()

            # Header panel
            console.print(
                Panel(
                    f"[bold blue]Marine Safety Data Quality Dashboard[/bold blue]\n"
                    f"Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Overall Quality Score: [bold green]{self.overall_quality_score:.1f}/100[/bold green]",
                    box=box.DOUBLE,
                )
            )

            # Coverage table
            coverage_table = Table(
                title="Data Coverage by Source",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
            )
            coverage_table.add_column("Source", style="dim")
            coverage_table.add_column("Records", justify="right")
            coverage_table.add_column("Percentage", justify="right")

            for source, count in sorted(
                self.coverage.by_source.items(), key=lambda x: x[1], reverse=True
            ):
                pct = (
                    (count / self.coverage.total_records * 100)
                    if self.coverage.total_records > 0
                    else 0
                )
                coverage_table.add_row(source.upper(), f"{count:,}", f"{pct:.1f}%")

            coverage_table.add_row(
                "[bold]Total[/bold]",
                f"[bold]{self.coverage.total_records:,}[/bold]",
                "[bold]100.0%[/bold]",
            )
            console.print(coverage_table)

            # Completeness table
            completeness_table = Table(
                title="Field Completeness",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
            )
            completeness_table.add_column("Field", style="dim")
            completeness_table.add_column("Completeness", justify="right")
            completeness_table.add_column("Status", justify="center")

            for field_name, pct in sorted(
                self.completeness.field_completeness.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                status = (
                    "[green]Good[/green]"
                    if pct >= 80
                    else "[yellow]Fair[/yellow]" if pct >= 50 else "[red]Poor[/red]"
                )
                completeness_table.add_row(field_name, f"{pct:.1f}%", status)

            console.print(completeness_table)

            # Duplicates table
            duplicates_table = Table(
                title="Duplicate Detection Statistics",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
            )
            duplicates_table.add_column("Metric", style="dim")
            duplicates_table.add_column("Count", justify="right")

            duplicates_table.add_row(
                "Total Linked Pairs", f"{self.duplicates.total_links:,}"
            )
            duplicates_table.add_row(
                "Verified Duplicates", f"{self.duplicates.verified_duplicates:,}"
            )
            duplicates_table.add_row(
                "Potential Duplicates", f"{self.duplicates.potential_duplicates:,}"
            )
            console.print(duplicates_table)

            # Incident type distribution
            type_table = Table(
                title="Incident Type Distribution",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
            )
            type_table.add_column("Type", style="dim")
            type_table.add_column("Count", justify="right")

            total_incidents = sum(self.incident_type_distribution.values())
            for inc_type, count in sorted(
                self.incident_type_distribution.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]:
                pct = (count / total_incidents * 100) if total_incidents > 0 else 0
                type_table.add_row(inc_type, f"{count:,} ({pct:.1f}%)")

            console.print(type_table)

            # Geographic coverage
            geo_table = Table(
                title="Geographic Coverage",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
            )
            geo_table.add_column("Region", style="dim")
            geo_table.add_column("Records", justify="right")

            for region, count in sorted(
                self.geographic_coverage.items(), key=lambda x: x[1], reverse=True
            )[:10]:
                region_name = OFFSHORE_REGIONS.get(region, region)
                geo_table.add_row(region_name, f"{count:,}")

            console.print(geo_table)

        except ImportError:
            # Fallback to plain text output
            self._print_plain()

    def _print_plain(self) -> None:
        """Print plain text summary when Rich is not available."""
        logger.info("\n" + "=" * 60)
        logger.info("MARINE SAFETY DATA QUALITY DASHBOARD")
        logger.info("=" * 60)
        logger.info(f"Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Overall Quality Score: {self.overall_quality_score:.1f}/100")

        logger.info("\n--- Coverage by Source ---")
        for source, count in sorted(
            self.coverage.by_source.items(), key=lambda x: x[1], reverse=True
        ):
            logger.info(f"  {source.upper()}: {count:,}")
        logger.info(f"  Total: {self.coverage.total_records:,}")

        logger.info("\n--- Field Completeness ---")
        for field_name, pct in sorted(
            self.completeness.field_completeness.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            logger.info(f"  {field_name}: {pct:.1f}%")

        logger.info("\n--- Duplicates ---")
        logger.info(f"  Total Links: {self.duplicates.total_links:,}")
        logger.info(f"  Verified: {self.duplicates.verified_duplicates:,}")
        logger.info(f"  Potential: {self.duplicates.potential_duplicates:,}")

        logger.info("=" * 60 + "\n")


class DataQualityDashboard:
    """
    Data quality analysis dashboard for marine safety incidents.

    This class provides comprehensive data quality analysis including:
    - Coverage analysis by data source and time period
    - Field completeness metrics
    - Duplicate detection statistics
    - Geographic coverage analysis
    - Incident type and severity distributions
    - Overall quality scoring

    Attributes:
        session: SQLAlchemy database session for queries

    Example:
        >>> dashboard = DataQualityDashboard(session)
        >>>
        >>> # Generate individual reports
        >>> coverage = dashboard.generate_coverage_report()
        >>> completeness = dashboard.generate_completeness_report()
        >>> duplicates = dashboard.generate_duplicate_report()
        >>>
        >>> # Generate comprehensive summary
        >>> summary = dashboard.generate_summary()
        >>> summary.print_console()
        >>>
        >>> # Export to JSON
        >>> summary.save_json(Path("quality_report.json"))
    """

    def __init__(self, session: Session) -> None:
        """
        Initialize DataQualityDashboard with database session.

        Args:
            session: SQLAlchemy session for database queries

        Raises:
            TypeError: If session is not a valid SQLAlchemy Session
        """
        if not isinstance(session, Session):
            raise TypeError("session must be a SQLAlchemy Session instance")
        self.session = session
        logger.debug("DataQualityDashboard initialized")

    def generate_coverage_report(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> CoverageReport:
        """
        Generate data coverage report by source and year.

        Analyzes the distribution of incident records across different data
        sources and time periods.

        Args:
            start_date: Optional start date filter (inclusive)
            end_date: Optional end date filter (inclusive)

        Returns:
            CoverageReport with coverage metrics

        Example:
            >>> coverage = dashboard.generate_coverage_report()
            >>> print(f"NTSB records: {coverage.by_source.get('ntsb', 0)}")
        """
        logger.info("Generating coverage report")

        # Build base filters
        filters = []
        if start_date:
            filters.append(Incident.incident_date >= start_date)
        if end_date:
            filters.append(Incident.incident_date <= end_date)

        # Count by source
        source_query = self.session.query(
            Incident.source_agency, func.count(Incident.incident_id).label("count")
        ).group_by(Incident.source_agency)

        if filters:
            source_query = source_query.filter(and_(*filters))

        source_results = source_query.all()
        by_source = {str(source): count for source, count in source_results}

        # Count by year
        year_query = self.session.query(
            extract("year", Incident.incident_date).label("year"),
            func.count(Incident.incident_id).label("count"),
        ).group_by("year")

        if filters:
            year_query = year_query.filter(and_(*filters))

        year_results = year_query.all()
        by_year = {int(year): count for year, count in year_results if year is not None}

        # Count by source and year combination
        source_year_query = self.session.query(
            Incident.source_agency,
            extract("year", Incident.incident_date).label("year"),
            func.count(Incident.incident_id).label("count"),
        ).group_by(Incident.source_agency, "year")

        if filters:
            source_year_query = source_year_query.filter(and_(*filters))

        source_year_results = source_year_query.all()
        by_source_year: Dict[str, Dict[int, int]] = {}
        for source, year, count in source_year_results:
            if year is None:
                continue
            source_str = str(source)
            if source_str not in by_source_year:
                by_source_year[source_str] = {}
            by_source_year[source_str][int(year)] = count

        # Total records
        total_query = self.session.query(func.count(Incident.incident_id))
        if filters:
            total_query = total_query.filter(and_(*filters))
        total_records = total_query.scalar() or 0

        # Date range
        date_query = self.session.query(
            func.min(Incident.incident_date).label("min_date"),
            func.max(Incident.incident_date).label("max_date"),
        )
        if filters:
            date_query = date_query.filter(and_(*filters))
        date_result = date_query.first()
        date_range = (
            date_result.min_date if date_result else None,
            date_result.max_date if date_result else None,
        )

        logger.info(f"Coverage report generated: {total_records} total records")

        return CoverageReport(
            by_source=by_source,
            by_year=by_year,
            by_source_year=by_source_year,
            total_records=total_records,
            date_range=date_range,
            metadata={
                "filters": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                }
            },
        )

    def generate_completeness_report(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> CompletenessReport:
        """
        Generate field completeness report.

        Calculates the percentage of non-null values for each important field
        in the incident data.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            CompletenessReport with completeness metrics

        Example:
            >>> completeness = dashboard.generate_completeness_report()
            >>> print(f"Vessel name completeness: {completeness.field_completeness.get('vessel_name', 0)}%")
        """
        logger.info("Generating completeness report")

        # Build base filters
        filters = []
        if start_date:
            filters.append(Incident.incident_date >= start_date)
        if end_date:
            filters.append(Incident.incident_date <= end_date)

        # Get total records
        total_query = self.session.query(func.count(Incident.incident_id))
        if filters:
            total_query = total_query.filter(and_(*filters))
        total_records = total_query.scalar() or 0

        if total_records == 0:
            logger.warning("No records found for completeness analysis")
            return CompletenessReport(
                field_completeness={},
                by_source={},
                total_records=0,
                critical_fields={},
                metadata={
                    "filters": {
                        "start_date": str(start_date),
                        "end_date": str(end_date),
                    }
                },
            )

        # Define fields to check for completeness
        incident_fields = {
            "title": Incident.title,
            "description": Incident.description,
            "incident_time": Incident.incident_time,
            "fatalities": Incident.fatalities,
            "injuries": Incident.injuries,
            "environmental_impact": Incident.environmental_impact,
            "estimated_damage_usd": Incident.estimated_damage_usd,
            "weather_condition": Incident.weather_condition,
            "data_quality_score": Incident.data_quality_score,
        }

        # Calculate completeness for incident fields
        field_completeness: Dict[str, float] = {}

        for field_name, field_col in incident_fields.items():
            count_query = self.session.query(
                func.count(case((field_col.isnot(None), 1)))
            )
            if filters:
                count_query = count_query.filter(and_(*filters))
            non_null_count = count_query.scalar() or 0
            field_completeness[field_name] = (non_null_count / total_records) * 100

        # Check vessel-related completeness (via join)
        vessel_fields = {
            "vessel_name": Vessel.vessel_name,
            "imo_number": Vessel.imo_number,
            "vessel_type": Vessel.vessel_type,
            "flag_state": Vessel.flag_state,
        }

        for field_name, field_col in vessel_fields.items():
            query = (
                self.session.query(func.count(case((field_col.isnot(None), 1))))
                .select_from(Incident)
                .outerjoin(Vessel)
            )
            if filters:
                query = query.filter(and_(*filters))
            non_null_count = query.scalar() or 0
            field_completeness[field_name] = (non_null_count / total_records) * 100

        # Check location-related completeness (via join)
        location_fields = {
            "latitude": Location.latitude,
            "longitude": Location.longitude,
            "location_name": Location.location_name,
            "region_code": Location.region_code,
            "country_code": Location.country_code,
        }

        for field_name, field_col in location_fields.items():
            query = (
                self.session.query(func.count(case((field_col.isnot(None), 1))))
                .select_from(Incident)
                .outerjoin(Location)
            )
            if filters:
                query = query.filter(and_(*filters))
            non_null_count = query.scalar() or 0
            field_completeness[field_name] = (non_null_count / total_records) * 100

        # Calculate completeness by source
        by_source: Dict[str, Dict[str, float]] = {}
        source_query = self.session.query(distinct(Incident.source_agency))
        if filters:
            source_query = source_query.filter(and_(*filters))

        sources = [row[0] for row in source_query.all()]

        for source in sources:
            source_str = str(source)
            by_source[source_str] = {}

            # Get source-specific total
            source_total_query = self.session.query(
                func.count(Incident.incident_id)
            ).filter(Incident.source_agency == source)
            if filters:
                source_total_query = source_total_query.filter(and_(*filters))
            source_total = source_total_query.scalar() or 0

            if source_total == 0:
                continue

            # Check key fields for this source
            for field_name, field_col in incident_fields.items():
                count_query = self.session.query(
                    func.count(case((field_col.isnot(None), 1)))
                ).filter(Incident.source_agency == source)
                if filters:
                    count_query = count_query.filter(and_(*filters))
                non_null_count = count_query.scalar() or 0
                by_source[source_str][field_name] = (
                    non_null_count / source_total
                ) * 100

        # Critical fields summary
        critical_fields = {
            "vessel_name": field_completeness.get("vessel_name", 0),
            "imo_number": field_completeness.get("imo_number", 0),
            "coordinates": min(
                field_completeness.get("latitude", 0),
                field_completeness.get("longitude", 0),
            ),
            "description": field_completeness.get("description", 0),
            "incident_time": field_completeness.get("incident_time", 0),
        }

        logger.info(f"Completeness report generated for {total_records} records")

        return CompletenessReport(
            field_completeness=field_completeness,
            by_source=by_source,
            total_records=total_records,
            critical_fields=critical_fields,
            metadata={
                "filters": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                }
            },
        )

    def generate_duplicate_report(self) -> DuplicateReport:
        """
        Generate duplicate detection statistics report.

        Analyzes the incident links table to provide statistics on detected
        duplicates and potential matches.

        Returns:
            DuplicateReport with duplicate detection metrics

        Example:
            >>> duplicates = dashboard.generate_duplicate_report()
            >>> print(f"Verified duplicates: {duplicates.verified_duplicates}")
        """
        logger.info("Generating duplicate report")

        # Total links
        total_links = self.session.query(func.count(IncidentLink.link_id)).scalar() or 0

        # Verified duplicates
        verified_count = (
            self.session.query(func.count(IncidentLink.link_id))
            .filter(IncidentLink.verified == True)
            .scalar()
            or 0
        )

        # Potential (unverified) duplicates
        potential_count = (
            self.session.query(func.count(IncidentLink.link_id))
            .filter(IncidentLink.verified == False)
            .scalar()
            or 0
        )

        # Distribution by confidence score ranges
        confidence_ranges = [
            ("0.0-0.3 (Low)", 0.0, 0.3),
            ("0.3-0.5 (Medium-Low)", 0.3, 0.5),
            ("0.5-0.7 (Medium)", 0.5, 0.7),
            ("0.7-0.9 (High)", 0.7, 0.9),
            ("0.9-1.0 (Very High)", 0.9, 1.0),
        ]

        by_confidence: Dict[str, int] = {}
        for label, low, high in confidence_ranges:
            count = (
                self.session.query(func.count(IncidentLink.link_id))
                .filter(
                    and_(
                        IncidentLink.confidence_score >= low,
                        IncidentLink.confidence_score < high,
                    )
                )
                .scalar()
                or 0
            )
            by_confidence[label] = count

        # Handle the upper bound of 1.0
        count_1 = (
            self.session.query(func.count(IncidentLink.link_id))
            .filter(IncidentLink.confidence_score == 1.0)
            .scalar()
            or 0
        )
        by_confidence["0.9-1.0 (Very High)"] = (
            by_confidence.get("0.9-1.0 (Very High)", 0) + count_1
        )

        # Distribution by match type
        match_type_query = self.session.query(
            IncidentLink.match_type, func.count(IncidentLink.link_id).label("count")
        ).group_by(IncidentLink.match_type)

        by_match_type = {
            match_type: count for match_type, count in match_type_query.all()
        }

        logger.info(
            f"Duplicate report generated: {total_links} links, {verified_count} verified"
        )

        return DuplicateReport(
            total_links=total_links,
            verified_duplicates=verified_count,
            potential_duplicates=potential_count,
            by_confidence=by_confidence,
            by_match_type=by_match_type,
            metadata={"generated_at": datetime.utcnow().isoformat()},
        )

    def _calculate_incident_type_distribution(
        self,
        filters: Optional[List] = None,
    ) -> Dict[str, int]:
        """
        Calculate distribution of incident types.

        Args:
            filters: Optional list of SQLAlchemy filter conditions

        Returns:
            Dictionary mapping incident types to counts
        """
        query = self.session.query(
            Incident.incident_type, func.count(Incident.incident_id).label("count")
        ).group_by(Incident.incident_type)

        if filters:
            query = query.filter(and_(*filters))

        results = query.all()
        return {str(inc_type): count for inc_type, count in results}

    def _calculate_severity_distribution(
        self,
        filters: Optional[List] = None,
    ) -> Dict[int, int]:
        """
        Calculate distribution of severity levels.

        Args:
            filters: Optional list of SQLAlchemy filter conditions

        Returns:
            Dictionary mapping severity levels to counts
        """
        query = self.session.query(
            Incident.severity_level, func.count(Incident.incident_id).label("count")
        ).group_by(Incident.severity_level)

        if filters:
            query = query.filter(and_(*filters))

        results = query.all()
        return {int(severity): count for severity, count in results}

    def _calculate_geographic_coverage(
        self,
        filters: Optional[List] = None,
    ) -> Dict[str, int]:
        """
        Calculate geographic coverage by region.

        Args:
            filters: Optional list of SQLAlchemy filter conditions

        Returns:
            Dictionary mapping region codes to counts
        """
        query = (
            self.session.query(
                Location.region_code, func.count(Incident.incident_id).label("count")
            )
            .select_from(Incident)
            .join(Location)
            .filter(Location.region_code.isnot(None))
            .group_by(Location.region_code)
        )

        if filters:
            query = query.filter(and_(*filters))

        results = query.all()
        return {region: count for region, count in results if region}

    def _calculate_quality_score(
        self,
        coverage: CoverageReport,
        completeness: CompletenessReport,
        duplicates: DuplicateReport,
    ) -> float:
        """
        Calculate overall data quality score (0-100).

        The score is computed as a weighted average of:
        - Source diversity (10%): Having data from multiple sources
        - Critical field completeness (50%): Completeness of key fields
        - Duplicate verification (20%): Ratio of verified to total links
        - Record volume (20%): Adequate data volume

        Args:
            coverage: CoverageReport instance
            completeness: CompletenessReport instance
            duplicates: DuplicateReport instance

        Returns:
            Quality score between 0 and 100
        """
        score = 0.0

        # Source diversity score (10%)
        # More sources = better, max at 5+ sources
        source_count = len(coverage.by_source)
        source_score = min(source_count / 5.0, 1.0) * 100
        score += source_score * 0.10

        # Critical field completeness score (50%)
        # Average completeness of critical fields
        critical_values = list(completeness.critical_fields.values())
        if critical_values:
            critical_avg = sum(critical_values) / len(critical_values)
        else:
            critical_avg = 0
        score += critical_avg * 0.50

        # Duplicate verification score (20%)
        # Higher ratio of verified duplicates = better
        if duplicates.total_links > 0:
            verification_ratio = duplicates.verified_duplicates / duplicates.total_links
        else:
            # No duplicates found means data is likely unique = good
            verification_ratio = 1.0
        score += verification_ratio * 100 * 0.20

        # Record volume score (20%)
        # More records = better, up to a threshold
        volume_threshold = 10000
        volume_score = min(coverage.total_records / volume_threshold, 1.0) * 100
        score += volume_score * 0.20

        return min(max(score, 0.0), 100.0)

    def generate_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> QualitySummary:
        """
        Generate comprehensive data quality summary.

        Combines coverage, completeness, and duplicate reports with additional
        metrics including incident type and severity distributions.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            QualitySummary with comprehensive quality metrics

        Example:
            >>> summary = dashboard.generate_summary()
            >>> summary.print_console()
            >>> summary.save_json(Path("quality_report.json"))
        """
        logger.info("Generating comprehensive quality summary")

        # Build filters
        filters = []
        if start_date:
            filters.append(Incident.incident_date >= start_date)
        if end_date:
            filters.append(Incident.incident_date <= end_date)

        # Generate component reports
        coverage = self.generate_coverage_report(start_date, end_date)
        completeness = self.generate_completeness_report(start_date, end_date)
        duplicates = self.generate_duplicate_report()

        # Calculate distributions
        incident_type_dist = self._calculate_incident_type_distribution(
            filters if filters else None
        )
        severity_dist = self._calculate_severity_distribution(
            filters if filters else None
        )
        geo_coverage = self._calculate_geographic_coverage(filters if filters else None)

        # Calculate overall quality score
        quality_score = self._calculate_quality_score(
            coverage, completeness, duplicates
        )

        logger.info(f"Quality summary generated with score: {quality_score:.1f}")

        return QualitySummary(
            coverage=coverage,
            completeness=completeness,
            duplicates=duplicates,
            incident_type_distribution=incident_type_dist,
            severity_distribution=severity_dist,
            geographic_coverage=geo_coverage,
            overall_quality_score=quality_score,
            generated_at=datetime.utcnow(),
            metadata={
                "filters": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                },
                "version": "1.0.0",
            },
        )
