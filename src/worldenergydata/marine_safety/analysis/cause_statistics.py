# ABOUTME: Statistical analysis module for marine safety incident causes including frequency distributions, temporal trends, and cross-tabulations
# ABOUTME: Provides comprehensive statistical methods with numpy/scipy calculations, pandas DataFrames for visualization, and CSV export capabilities

"""
Statistical Analysis Module for Incident Causes

This module provides comprehensive statistical analysis capabilities for marine
safety incident causes. It includes frequency distribution calculations, temporal
trend analysis, cross-tabulation with severity levels, specialized statistics
for hatch/opening maloperation incidents, and summary report generation.

All statistical calculations use numpy and scipy for accuracy and efficiency.
Results are returned as pandas DataFrames for easy visualization and export.

Classes:
    CauseStatistics: Main class for cause statistical analysis
    FrequencyDistribution: Container for frequency distribution results
    TemporalTrend: Container for temporal trend analysis results
    CrossTabulation: Container for cross-tabulation results
    StatisticalSummary: Container for comprehensive summary statistics

Example:
    >>> from sqlalchemy.orm import Session
    >>> from worldenergydata.marine_safety.analysis import CauseStatistics
    >>>
    >>> stats = CauseStatistics(session)
    >>> distribution = stats.calculate_frequency_distribution()
    >>> print(distribution.data)
    >>> distribution.to_csv('cause_distribution.csv')
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sqlalchemy import Integer, and_, extract, func, or_
from sqlalchemy.orm import Session

from worldenergydata.marine_safety.constants import CauseCategory, SeverityLevel
from worldenergydata.marine_safety.database.models import (

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)
    Incident,
    IncidentCause,
)


@dataclass
class FrequencyDistribution:
    """
    Container for frequency distribution analysis results.

    Attributes:
        data: DataFrame with count, percentage, and optional confidence intervals
        total_count: Total number of observations
        categories: List of cause categories included
        metadata: Additional analysis metadata

    Methods:
        to_csv: Export distribution to CSV file
        to_dict: Convert to dictionary format
    """

    data: pd.DataFrame
    total_count: int
    categories: List[CauseCategory] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_csv(self, filepath: Path, **kwargs) -> None:
        """
        Export frequency distribution to CSV file.

        Args:
            filepath: Path to output CSV file
            **kwargs: Additional arguments passed to pandas to_csv

        Raises:
            IOError: If file cannot be written
        """
        self.data.to_csv(filepath, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert frequency distribution to dictionary format.

        Returns:
            Dictionary with distribution data and metadata
        """
        return {
            "data": self.data.to_dict(orient="index"),
            "total_count": self.total_count,
            "categories": [str(cat) for cat in self.categories],
            "metadata": self.metadata,
        }


@dataclass
class TemporalTrend:
    """
    Container for temporal trend analysis results.

    Attributes:
        data: DataFrame with time period rows and cause category counts
        period_type: Type of time aggregation ('month', 'quarter', 'year')
        date_range: Tuple of (start_date, end_date) for analysis
        metadata: Additional analysis metadata

    Methods:
        to_csv: Export trends to CSV file
        to_dict: Convert to dictionary format
    """

    data: pd.DataFrame
    period_type: str
    date_range: Tuple[date, date]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_csv(self, filepath: Path, **kwargs) -> None:
        """
        Export temporal trends to CSV file.

        Args:
            filepath: Path to output CSV file
            **kwargs: Additional arguments passed to pandas to_csv
        """
        self.data.to_csv(filepath, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert temporal trends to dictionary format.

        Returns:
            Dictionary with trend data and metadata
        """
        return {
            "data": self.data.to_dict(orient="index"),
            "period_type": self.period_type,
            "date_range": [str(d) for d in self.date_range],
            "metadata": self.metadata,
        }


@dataclass
class CrossTabulation:
    """
    Container for cross-tabulation analysis results.

    Attributes:
        data: DataFrame with rows=causes, columns=severity levels
        row_totals: Total counts per row (cause category)
        column_totals: Total counts per column (severity level)
        grand_total: Overall total count
        metadata: Additional analysis metadata

    Methods:
        to_csv: Export cross-tabulation to CSV file
        to_dict: Convert to dictionary format
        chi_square_test: Perform chi-square test of independence
    """

    data: pd.DataFrame
    row_totals: pd.Series
    column_totals: pd.Series
    grand_total: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_csv(self, filepath: Path, **kwargs) -> None:
        """Export cross-tabulation to CSV file."""
        self.data.to_csv(filepath, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert cross-tabulation to dictionary format."""
        return {
            "data": self.data.to_dict(orient="index"),
            "row_totals": self.row_totals.to_dict(),
            "column_totals": self.column_totals.to_dict(),
            "grand_total": self.grand_total,
            "metadata": self.metadata,
        }

    def chi_square_test(self) -> Dict[str, float]:
        """
        Perform chi-square test of independence.

        Returns:
            Dictionary with chi2 statistic, p-value, degrees of freedom
        """
        chi2, p_value, dof, expected = scipy_stats.chi2_contingency(self.data.values)
        return {
            "chi2_statistic": float(chi2),
            "p_value": float(p_value),
            "degrees_of_freedom": int(dof),
            "significant": p_value < 0.05,
        }


@dataclass
class StatisticalSummary:
    """
    Container for comprehensive statistical summary.

    Attributes:
        total_incidents: Total number of incidents analyzed
        total_causes: Total number of cause records
        most_common_cause: Most frequently occurring cause category
        least_common_cause: Least frequently occurring cause category
        date_range: Tuple of (earliest, latest) incident dates
        severity_distribution: Distribution of severity levels
        cause_distribution: Distribution of cause categories
        metadata: Additional summary metadata

    Methods:
        to_dict: Convert summary to dictionary format
        print_report: Print formatted text report
    """

    total_incidents: int
    total_causes: int
    most_common_cause: CauseCategory
    least_common_cause: CauseCategory
    date_range: Tuple[date, date]
    severity_distribution: Dict[SeverityLevel, int]
    cause_distribution: Dict[CauseCategory, int]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary format."""
        return {
            "total_incidents": self.total_incidents,
            "total_causes": self.total_causes,
            "most_common_cause": str(self.most_common_cause),
            "least_common_cause": str(self.least_common_cause),
            "date_range": [str(d) for d in self.date_range],
            "severity_distribution": {
                str(k): v for k, v in self.severity_distribution.items()
            },
            "cause_distribution": {
                str(k): v for k, v in self.cause_distribution.items()
            },
            "metadata": self.metadata,
        }

    def print_report(self) -> None:
        """Print formatted text report of statistical summary."""
        logger.info("\n" + "=" * 60)
        logger.info("MARINE SAFETY INCIDENT CAUSE STATISTICAL SUMMARY")
        logger.info("=" * 60)
        logger.info(f"\nTotal Incidents: {self.total_incidents}")
        logger.info(f"Total Cause Records: {self.total_causes}")
        logger.info(f"Date Range: {self.date_range[0]} to {self.date_range[1]}")
        logger.info(
            f"\nMost Common Cause: {self.most_common_cause} ({self.cause_distribution[self.most_common_cause]} occurrences)"
        )
        logger.info(
            f"Least Common Cause: {self.least_common_cause} ({self.cause_distribution[self.least_common_cause]} occurrences)"
        )

        logger.info("\n--- Cause Category Distribution ---")
        for cause, count in sorted(
            self.cause_distribution.items(), key=lambda x: x[1], reverse=True
        ):
            pct = (count / self.total_causes) * 100
            logger.info(f"  {cause}: {count} ({pct:.1f}%)")

        logger.info("\n--- Severity Level Distribution ---")
        for severity, count in sorted(self.severity_distribution.items()):
            pct = (count / self.total_incidents) * 100
            logger.info(f"  Level {severity}: {count} ({pct:.1f}%)")
        logger.info("=" * 60 + "\n")


class CauseStatistics:
    """
    Statistical analysis engine for marine safety incident causes.

    This class provides comprehensive statistical analysis capabilities including:
    - Frequency distribution calculations by cause category
    - Percentage and proportion calculations with confidence intervals
    - Temporal trend analysis (causes over time)
    - Cross-tabulation of causes with severity levels
    - Specialized statistics for hatch/opening maloperation incidents
    - Summary report generation with key metrics

    All calculations use numpy and scipy for statistical accuracy. Results are
    returned as pandas DataFrames for easy visualization and further analysis.

    Attributes:
        session: SQLAlchemy database session for querying incident data

    Example:
        >>> stats = CauseStatistics(session)
        >>>
        >>> # Get frequency distribution
        >>> dist = stats.calculate_frequency_distribution()
        >>> print(dist.data)
        >>>
        >>> # Analyze temporal trends
        >>> trends = stats.calculate_temporal_trends(period='month')
        >>> print(trends.data)
        >>>
        >>> # Cross-tabulate causes with severity
        >>> crosstab = stats.calculate_cause_severity_crosstab()
        >>> print(crosstab.data)
        >>>
        >>> # Generate comprehensive summary
        >>> summary = stats.generate_summary_report()
        >>> summary.print_report()
    """

    def __init__(self, session: Session):
        """
        Initialize CauseStatistics with database session.

        Args:
            session: SQLAlchemy session for database queries

        Raises:
            TypeError: If session is not a valid SQLAlchemy Session
        """
        if not isinstance(session, Session):
            raise TypeError("session must be a SQLAlchemy Session instance")
        self.session = session

    def calculate_frequency_distribution(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_severity: Optional[SeverityLevel] = None,
        primary_only: bool = True,
        include_confidence_intervals: bool = False,
        confidence_level: float = 0.95,
    ) -> FrequencyDistribution:
        """
        Calculate frequency distribution of incident causes.

        Computes counts and percentages for each cause category with optional
        filtering by date range and severity level. Can include statistical
        confidence intervals using Wilson score method.

        Args:
            start_date: Optional start date filter (inclusive)
            end_date: Optional end date filter (inclusive)
            min_severity: Optional minimum severity level filter
            primary_only: If True, only count primary causes; if False, include all
            include_confidence_intervals: If True, calculate 95% confidence intervals
            confidence_level: Confidence level for intervals (default 0.95)

        Returns:
            FrequencyDistribution object with counts, percentages, and optional CIs

        Example:
            >>> dist = stats.calculate_frequency_distribution(
            ...     start_date=date(2024, 1, 1),
            ...     min_severity=SeverityLevel.SERIOUS,
            ...     include_confidence_intervals=True
            ... )
            >>> print(dist.data)
        """
        # Build base query
        query = self.session.query(
            IncidentCause.cause_category,
            func.count(IncidentCause.cause_id).label("count"),
        ).join(Incident)

        # Apply filters
        filters = []
        if start_date:
            filters.append(Incident.incident_date >= start_date)
        if end_date:
            filters.append(Incident.incident_date <= end_date)
        if min_severity:
            filters.append(Incident.severity_level >= min_severity)
        if primary_only:
            filters.append(IncidentCause.is_primary == True)

        if filters:
            query = query.filter(and_(*filters))

        # Group by cause category
        query = query.group_by(IncidentCause.cause_category)

        # Execute query
        results = query.all()

        # Handle empty results
        if not results:
            empty_df = pd.DataFrame(columns=["count", "percentage"])
            return FrequencyDistribution(
                data=empty_df,
                total_count=0,
                categories=[],
                metadata={
                    "filters": {
                        "start_date": str(start_date) if start_date else None,
                        "end_date": str(end_date) if end_date else None,
                        "min_severity": str(min_severity) if min_severity else None,
                        "primary_only": primary_only,
                    }
                },
            )

        # Convert to DataFrame
        df = pd.DataFrame(results, columns=["cause_category", "count"])
        df = df.set_index("cause_category")

        # Calculate total
        total = df["count"].sum()

        # Calculate percentages
        df["percentage"] = (df["count"] / total) * 100.0

        # Calculate confidence intervals if requested
        if include_confidence_intervals:
            z_score = scipy_stats.norm.ppf((1 + confidence_level) / 2)

            def wilson_ci(count, total):
                """Calculate Wilson score confidence interval."""
                if total == 0:
                    return 0.0, 0.0
                p = count / total
                denominator = 1 + z_score**2 / total
                center = (p + z_score**2 / (2 * total)) / denominator
                margin = (
                    z_score
                    * np.sqrt(p * (1 - p) / total + z_score**2 / (4 * total**2))
                    / denominator
                )
                return max(0, center - margin) * 100, min(1, center + margin) * 100

            ci_results = [wilson_ci(row["count"], total) for _, row in df.iterrows()]
            df["ci_lower"] = [ci[0] for ci in ci_results]
            df["ci_upper"] = [ci[1] for ci in ci_results]

        # Create result object
        categories = list(df.index)
        metadata = {
            "filters": {
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None,
                "min_severity": str(min_severity) if min_severity else None,
                "primary_only": primary_only,
            },
            "confidence_level": (
                confidence_level if include_confidence_intervals else None
            ),
        }

        return FrequencyDistribution(
            data=df, total_count=int(total), categories=categories, metadata=metadata
        )

    def calculate_temporal_trends(
        self,
        period: str = "month",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        primary_only: bool = True,
    ) -> TemporalTrend:
        """
        Calculate temporal trends of incident causes over time.

        Analyzes how cause categories vary over time periods (month, quarter, year).
        Returns counts for each cause category within each time period.

        Args:
            period: Time aggregation period ('month', 'quarter', 'year')
            start_date: Optional start date filter
            end_date: Optional end date filter
            primary_only: If True, only analyze primary causes

        Returns:
            TemporalTrend object with time-series data

        Raises:
            ValueError: If period is not one of 'month', 'quarter', 'year'

        Example:
            >>> trends = stats.calculate_temporal_trends(period='month')
            >>> print(trends.data)
        """
        if period not in ["month", "quarter", "year"]:
            raise ValueError("period must be 'month', 'quarter', or 'year'")

        # Build query with time period extraction
        # Use database-agnostic approach that works with both PostgreSQL and SQLite
        if period == "month":
            # Extract year and month
            year_extract = extract("year", Incident.incident_date)
            month_extract = extract("month", Incident.incident_date)
            # Create a combined period key
            period_expr = year_extract * 100 + month_extract
        elif period == "quarter":
            year_extract = extract("year", Incident.incident_date)
            # SQLite doesn't have quarter, so calculate it
            month_extract = extract("month", Incident.incident_date)
            quarter_expr = func.cast((month_extract + 2) / 3, Integer)
            period_expr = year_extract * 10 + quarter_expr
        else:  # year
            period_expr = extract("year", Incident.incident_date)

        query = self.session.query(
            period_expr.label("period"),
            IncidentCause.cause_category,
            func.count(IncidentCause.cause_id).label("count"),
        ).join(Incident)

        # Apply filters
        filters = []
        if start_date:
            filters.append(Incident.incident_date >= start_date)
        if end_date:
            filters.append(Incident.incident_date <= end_date)
        if primary_only:
            filters.append(IncidentCause.is_primary == True)

        if filters:
            query = query.filter(and_(*filters))

        # Group by period and cause
        query = query.group_by("period", IncidentCause.cause_category)
        query = query.order_by("period")

        # Execute query
        results = query.all()

        # Handle empty results
        if not results:
            # Get actual date range from incidents if available
            date_query = self.session.query(
                func.min(Incident.incident_date).label("min_date"),
                func.max(Incident.incident_date).label("max_date"),
            )
            date_result = date_query.first()

            empty_df = pd.DataFrame(columns=["period"])
            return TemporalTrend(
                data=empty_df,
                period_type=period,
                date_range=(
                    date_result.min_date or date(1900, 1, 1),
                    date_result.max_date or date(1900, 1, 1),
                ),
                metadata={
                    "filters": {
                        "start_date": str(start_date) if start_date else None,
                        "end_date": str(end_date) if end_date else None,
                        "primary_only": primary_only,
                    }
                },
            )

        # Convert to DataFrame and pivot
        df = pd.DataFrame(results, columns=["period", "cause_category", "count"])

        # Pivot to get causes as columns
        pivot_df = df.pivot_table(
            index="period", columns="cause_category", values="count", fill_value=0
        )

        # Rename columns to include count_ prefix
        pivot_df.columns = [f"count_{col}" for col in pivot_df.columns]

        # Reset index to make period a column
        pivot_df = pivot_df.reset_index()

        # Get date range from actual incident dates
        date_query = self.session.query(
            func.min(Incident.incident_date).label("min_date"),
            func.max(Incident.incident_date).label("max_date"),
        ).join(IncidentCause)

        # Apply same filters
        if filters:
            date_query = date_query.filter(and_(*filters))

        date_result = date_query.first()
        min_date = date_result.min_date if date_result.min_date else date.today()
        max_date = date_result.max_date if date_result.max_date else date.today()

        metadata = {
            "filters": {
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None,
                "primary_only": primary_only,
            },
            "period_count": len(pivot_df),
        }

        return TemporalTrend(
            data=pivot_df,
            period_type=period,
            date_range=(min_date, max_date),
            metadata=metadata,
        )

    def calculate_cause_severity_crosstab(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        primary_only: bool = True,
        include_percentages: bool = False,
    ) -> CrossTabulation:
        """
        Calculate cross-tabulation of causes with severity levels.

        Creates a contingency table showing the relationship between cause
        categories and incident severity levels. Useful for identifying which
        types of causes lead to more severe incidents.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            primary_only: If True, only analyze primary causes
            include_percentages: If True, include percentage calculations

        Returns:
            CrossTabulation object with cause-by-severity matrix

        Example:
            >>> crosstab = stats.calculate_cause_severity_crosstab()
            >>> chi2_test = crosstab.chi_square_test()
            >>> print(f"Chi-square test p-value: {chi2_test['p_value']}")
        """
        # Build query
        query = self.session.query(
            IncidentCause.cause_category,
            Incident.severity_level,
            func.count(Incident.incident_id).label("count"),
        ).join(Incident)

        # Apply filters
        filters = []
        if start_date:
            filters.append(Incident.incident_date >= start_date)
        if end_date:
            filters.append(Incident.incident_date <= end_date)
        if primary_only:
            filters.append(IncidentCause.is_primary == True)

        if filters:
            query = query.filter(and_(*filters))

        # Group by cause and severity
        query = query.group_by(IncidentCause.cause_category, Incident.severity_level)

        # Execute query
        results = query.all()

        # Handle empty results
        if not results:
            empty_df = pd.DataFrame()
            return CrossTabulation(
                data=empty_df,
                row_totals=pd.Series(dtype=int),
                column_totals=pd.Series(dtype=int),
                grand_total=0,
                metadata={
                    "filters": {
                        "start_date": str(start_date) if start_date else None,
                        "end_date": str(end_date) if end_date else None,
                        "primary_only": primary_only,
                    }
                },
            )

        # Convert to DataFrame and pivot
        df = pd.DataFrame(
            results, columns=["cause_category", "severity_level", "count"]
        )

        crosstab_df = df.pivot_table(
            index="cause_category",
            columns="severity_level",
            values="count",
            fill_value=0,
            aggfunc="sum",
        )

        # Calculate totals
        row_totals = crosstab_df.sum(axis=1)
        column_totals = crosstab_df.sum(axis=0)
        grand_total = int(crosstab_df.values.sum())

        # Add percentages if requested
        if include_percentages:
            pct_df = (crosstab_df / grand_total) * 100
            # Store both in metadata
            metadata = {
                "percentages": pct_df.to_dict(orient="index"),
                "filters": {
                    "start_date": str(start_date) if start_date else None,
                    "end_date": str(end_date) if end_date else None,
                    "primary_only": primary_only,
                },
            }
        else:
            metadata = {
                "filters": {
                    "start_date": str(start_date) if start_date else None,
                    "end_date": str(end_date) if end_date else None,
                    "primary_only": primary_only,
                }
            }

        return CrossTabulation(
            data=crosstab_df,
            row_totals=row_totals,
            column_totals=column_totals,
            grand_total=grand_total,
            metadata=metadata,
        )

    def calculate_hatch_maloperation_stats(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Calculate specialized statistics for hatch/opening maloperation incidents.

        Identifies and analyzes incidents specifically related to hatch covers,
        cargo openings, and similar closure maloperation events. These are
        particularly critical in maritime safety due to their potential for
        catastrophic flooding.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary containing:
                - total_incidents: Count of hatch maloperation incidents
                - by_cause: Breakdown by cause category
                - by_severity: Breakdown by severity level
                - vessel_types: Distribution by vessel type
                - fatalities: Total fatalities in these incidents
                - injuries: Total injuries in these incidents
                - average_severity: Mean severity level

        Example:
            >>> hatch_stats = stats.calculate_hatch_maloperation_stats()
            >>> print(f"Total hatch incidents: {hatch_stats['total_incidents']}")
        """
        # Build query for hatch-related incidents
        query = self.session.query(Incident).join(IncidentCause)

        # Filter for hatch/opening related keywords in description or cause
        hatch_keywords = [
            "%hatch%",
            "%cover%",
            "%opening%",
            "%closure%",
            "%securing%",
            "%watertight%",
            "%door%",
            "%access%",
        ]

        keyword_filters = [
            or_(
                Incident.description.ilike(keyword),
                Incident.title.ilike(keyword),
                IncidentCause.cause_description.ilike(keyword),
            )
            for keyword in hatch_keywords
        ]

        query = query.filter(or_(*keyword_filters))

        # Apply date filters
        filters = []
        if start_date:
            filters.append(Incident.incident_date >= start_date)
        if end_date:
            filters.append(Incident.incident_date <= end_date)

        if filters:
            query = query.filter(and_(*filters))

        # Get incidents
        incidents = query.distinct().all()

        # Calculate statistics
        total_incidents = len(incidents)

        if total_incidents == 0:
            return {
                "total_incidents": 0,
                "by_cause": {},
                "by_severity": {},
                "vessel_types": {},
                "fatalities": 0,
                "injuries": 0,
                "average_severity": 0.0,
                "date_range": (start_date, end_date) if start_date else None,
            }

        # Cause distribution
        cause_counts = {}
        for incident in incidents:
            for cause in incident.causes:
                category = cause.cause_category
                cause_counts[category] = cause_counts.get(category, 0) + 1

        # Severity distribution
        severity_counts = {}
        severity_sum = 0
        for incident in incidents:
            severity = incident.severity_level
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            severity_sum += severity

        # Vessel type distribution
        vessel_types = {}
        for incident in incidents:
            if incident.vessel:
                vtype = incident.vessel.vessel_type
                vessel_types[vtype] = vessel_types.get(vtype, 0) + 1

        # Casualties
        total_fatalities = sum(inc.fatalities for inc in incidents)
        total_injuries = sum(inc.injuries for inc in incidents)

        # Average severity
        avg_severity = severity_sum / total_incidents if total_incidents > 0 else 0.0

        return {
            "total_incidents": total_incidents,
            "by_cause": {str(k): v for k, v in cause_counts.items()},
            "by_severity": {str(k): v for k, v in severity_counts.items()},
            "vessel_types": {str(k): v for k, v in vessel_types.items()},
            "fatalities": total_fatalities,
            "injuries": total_injuries,
            "average_severity": float(avg_severity),
            "date_range": (
                (
                    min(inc.incident_date for inc in incidents),
                    max(inc.incident_date for inc in incidents),
                )
                if incidents
                else None
            ),
        }

    def generate_summary_report(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> StatisticalSummary:
        """
        Generate comprehensive statistical summary report.

        Creates a high-level summary of incident cause statistics including
        total counts, most/least common causes, severity distribution, and
        date range coverage.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            StatisticalSummary object with comprehensive metrics

        Example:
            >>> summary = stats.generate_summary_report()
            >>> summary.print_report()
        """
        # Get total incidents
        incident_query = self.session.query(Incident)

        filters = []
        if start_date:
            filters.append(Incident.incident_date >= start_date)
        if end_date:
            filters.append(Incident.incident_date <= end_date)

        if filters:
            incident_query = incident_query.filter(and_(*filters))

        total_incidents = incident_query.count()

        # Get total causes
        cause_query = self.session.query(IncidentCause).join(Incident)
        if filters:
            cause_query = cause_query.filter(and_(*filters))

        total_causes = cause_query.count()

        # Get cause distribution
        distribution = self.calculate_frequency_distribution(
            start_date=start_date, end_date=end_date, primary_only=False
        )

        # Find most and least common causes
        if not distribution.data.empty:
            cause_dist = distribution.data["count"].to_dict()
            most_common = max(cause_dist.items(), key=lambda x: x[1])[0]
            least_common = min(cause_dist.items(), key=lambda x: x[1])[0]
        else:
            cause_dist = {}
            most_common = CauseCategory.UNKNOWN
            least_common = CauseCategory.UNKNOWN

        # Get severity distribution
        severity_query = self.session.query(
            Incident.severity_level, func.count(Incident.incident_id).label("count")
        )
        if filters:
            severity_query = severity_query.filter(and_(*filters))

        severity_results = severity_query.group_by(Incident.severity_level).all()
        severity_dist = {sev: count for sev, count in severity_results}

        # Get date range
        date_query = self.session.query(
            func.min(Incident.incident_date).label("min_date"),
            func.max(Incident.incident_date).label("max_date"),
        )
        if filters:
            date_query = date_query.filter(and_(*filters))

        date_result = date_query.first()
        date_range = (
            date_result.min_date if date_result.min_date else date.today(),
            date_result.max_date if date_result.max_date else date.today(),
        )

        return StatisticalSummary(
            total_incidents=total_incidents,
            total_causes=total_causes,
            most_common_cause=most_common,
            least_common_cause=least_common,
            date_range=date_range,
            severity_distribution=severity_dist,
            cause_distribution=cause_dist,
            metadata={
                "filters": {
                    "start_date": str(start_date) if start_date else None,
                    "end_date": str(end_date) if end_date else None,
                }
            },
        )
