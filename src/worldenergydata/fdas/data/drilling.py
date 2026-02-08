"""
FDAS Drilling & Completion Timeline Module

Extracts drilling and completion days from BSEE well activity data,
classifies activities, and generates D&C timelines for cost modeling.

Author: WorldEnergyData Team
Date: 2025-10-03
Source: Ported from FDAS extract_drilling_completion_days.py
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd


class DrillingDataError(Exception):
    """Raised when drilling data processing fails"""

    pass


class CompletionActivityClassifier:
    """
    Classifies well activities into drilling, completion, and testing phases.

    Uses keyword matching in activity remarks to identify completion operations.
    """

    # Completion activity keywords from FDAS
    COMPLETION_KEYWORDS = {
        "completion",
        "complete",
        "completed",
        "perf",
        "perforate",
        "perforated",
        "stimulate",
        "stimulation",
        "frac",
        "fracture",
        "fractured",
        "fracturing",
        "acidize",
        "acidizing",
        "acid",
        "gravel pack",
        "gravelpack",
        "casing",
        "cement",
        "cementing",
        "liner",
        "tubing",
        "xmas tree",
        "tree installation",
        "subsea tree",
        "flowline",
        "hookup",
        "tie-in",
        "tieback",
    }

    TESTING_KEYWORDS = {
        "test",
        "testing",
        "dst",
        "production test",
        "flow test",
        "pressure test",
        "well test",
        "buildup",
        "drawdown",
    }

    DRILLING_KEYWORDS = {
        "drill",
        "drilling",
        "drilled",
        "spud",
        "spudded",
        "td",
        "total depth",
        "reached td",
        "depth",
    }

    def __init__(self, custom_keywords: Optional[Dict[str, Set[str]]] = None):
        """
        Initialize classifier.

        Args:
            custom_keywords: Optional dict with custom keyword sets for
                           'completion', 'testing', 'drilling'
        """
        if custom_keywords:
            self.completion_kw = custom_keywords.get(
                "completion", self.COMPLETION_KEYWORDS
            )
            self.testing_kw = custom_keywords.get("testing", self.TESTING_KEYWORDS)
            self.drilling_kw = custom_keywords.get("drilling", self.DRILLING_KEYWORDS)
        else:
            self.completion_kw = self.COMPLETION_KEYWORDS
            self.testing_kw = self.TESTING_KEYWORDS
            self.drilling_kw = self.DRILLING_KEYWORDS

    def classify_activity(self, remark: str) -> str:
        """
        Classify activity based on remark text.

        Args:
            remark: Activity remark text

        Returns:
            Activity type: 'completion', 'testing', 'drilling', or 'unknown'

        Examples:
            >>> classifier = CompletionActivityClassifier()
            >>> classifier.classify_activity("Perforated 15,000-15,500ft")
            'completion'
        """
        if pd.isna(remark):
            return "unknown"

        remark_lower = str(remark).lower()

        # Check completion keywords first (most specific)
        if any(kw in remark_lower for kw in self.completion_kw):
            return "completion"

        # Check testing keywords
        if any(kw in remark_lower for kw in self.testing_kw):
            return "testing"

        # Check drilling keywords
        if any(kw in remark_lower for kw in self.drilling_kw):
            return "drilling"

        return "unknown"

    def extract_mud_weight(self, remark: str) -> Optional[float]:
        """
        Extract mud weight from remark text.

        Args:
            remark: Activity remark

        Returns:
            Mud weight in ppg, or None if not found

        Examples:
            >>> classifier = CompletionActivityClassifier()
            >>> classifier.extract_mud_weight("Drilling with 12.5 ppg mud")
            12.5
        """
        if pd.isna(remark):
            return None

        # Pattern: number followed by 'ppg'
        pattern = r"(\d+\.?\d*)\s*ppg"
        match = re.search(pattern, str(remark).lower())

        if match:
            return float(match.group(1))

        return None


class DrillingTimelineExtractor:
    """
    Extracts drilling and completion timeline from BSEE well activity data.

    Calculates drilling days, completion days, and allocates to monthly periods
    for CAPEX timing in financial models.
    """

    def __init__(
        self, well_activity_df: pd.DataFrame, remarks_df: Optional[pd.DataFrame] = None
    ):
        """
        Initialize timeline extractor.

        Args:
            well_activity_df: Well activity summary with spud/TD dates
            remarks_df: Optional detailed activity remarks
        """
        self.activity_df = well_activity_df.copy()
        self.remarks_df = remarks_df.copy() if remarks_df is not None else None
        self.classifier = CompletionActivityClassifier()

        self._validate_input()

    def _validate_input(self) -> None:
        """
        Validate required columns exist.

        Raises:
            DrillingDataError: If required columns missing
        """
        required = ["API_WELL_NUMBER", "SPUD_DATE"]
        missing = [col for col in required if col not in self.activity_df.columns]

        if missing:
            raise DrillingDataError(f"Missing required columns: {missing}")

    def calculate_drilling_days(
        self,
        spud_date: datetime,
        td_date: Optional[datetime] = None,
        gap_threshold_days: int = 90,
    ) -> Tuple[float, List[Tuple[datetime, datetime]]]:
        """
        Calculate drilling days with gap adjustment.

        Args:
            spud_date: Well spud date
            td_date: Total depth date (if None, estimated)
            gap_threshold_days: Maximum gap before splitting timeline

        Returns:
            Tuple of (total_drilling_days, list of date ranges)

        Examples:
            >>> extractor = DrillingTimelineExtractor(activity_df)
            >>> days, ranges = extractor.calculate_drilling_days(
            ...     datetime(2020, 1, 1),
            ...     datetime(2020, 3, 15)
            ... )
        """
        if td_date is None:
            # Estimate 60 days drilling time if TD not provided
            td_date = spud_date + timedelta(days=60)

        # Calculate total calendar days
        total_days = (td_date - spud_date).days

        # Check for gaps (periods of inactivity)
        # In real implementation, would check for date gaps in activity log
        # For now, return single continuous period
        date_ranges = [(spud_date, td_date)]

        return float(total_days), date_ranges

    def allocate_days_to_months(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, float]:
        """
        Allocate drilling days to monthly periods.

        Uses exclusive end_date, consistent with calculate_drilling_days
        which returns (end - start).days.

        Args:
            start_date: Start of drilling (inclusive)
            end_date: End of drilling (exclusive)

        Returns:
            Dictionary mapping year-month to drilling days

        Examples:
            >>> extractor = DrillingTimelineExtractor(activity_df)
            >>> monthly = extractor.allocate_days_to_months(
            ...     datetime(2020, 1, 15),
            ...     datetime(2020, 3, 10)
            ... )
        """
        allocation = {}

        current = start_date
        while current < end_date:
            month_key = current.strftime("%Y-%m")

            # First day of next month
            if current.month == 12:
                next_month = datetime(current.year + 1, 1, 1)
            else:
                next_month = datetime(current.year, current.month + 1, 1)

            # Period runs from current to min(next_month, end_date), exclusive
            period_end = min(next_month, end_date)
            days_in_month = (period_end - current).days

            allocation[month_key] = allocation.get(month_key, 0) + days_in_month

            current = next_month

        return allocation

    def extract_well_timeline(self, api_well_number: str) -> Dict[str, any]:
        """
        Extract complete timeline for a well.

        Args:
            api_well_number: API well number

        Returns:
            Dictionary with timeline information

        Examples:
            >>> extractor = DrillingTimelineExtractor(activity_df)
            >>> timeline = extractor.extract_well_timeline('608054011700')
        """
        # Filter to well
        well_data = self.activity_df[
            self.activity_df["API_WELL_NUMBER"] == api_well_number
        ]

        if len(well_data) == 0:
            raise DrillingDataError(f"No data found for well: {api_well_number}")

        well_row = well_data.iloc[0]

        # Get dates
        spud_date = pd.to_datetime(well_row["SPUD_DATE"])
        td_date = (
            pd.to_datetime(well_row.get("TD_DATE"))
            if "TD_DATE" in well_row and pd.notna(well_row.get("TD_DATE"))
            else None
        )
        completion_date = (
            pd.to_datetime(well_row.get("COMPLETION_DATE"))
            if "COMPLETION_DATE" in well_row
            and pd.notna(well_row.get("COMPLETION_DATE"))
            else None
        )

        # Calculate drilling days
        drilling_days, drilling_ranges = self.calculate_drilling_days(
            spud_date, td_date
        )

        # Calculate completion days
        if td_date and completion_date:
            completion_days = (completion_date - td_date).days
        else:
            completion_days = 30  # Default estimate

        # Allocate to months
        drilling_monthly = {}
        for start, end in drilling_ranges:
            monthly = self.allocate_days_to_months(start, end)
            for month, days in monthly.items():
                drilling_monthly[month] = drilling_monthly.get(month, 0) + days

        completion_monthly = {}
        if td_date and completion_date:
            completion_monthly = self.allocate_days_to_months(td_date, completion_date)

        return {
            "api_well_number": api_well_number,
            "spud_date": spud_date,
            "td_date": td_date,
            "completion_date": completion_date,
            "drilling_days": drilling_days,
            "completion_days": completion_days,
            "drilling_monthly": drilling_monthly,
            "completion_monthly": completion_monthly,
        }

    def extract_all_wells_timeline(self) -> pd.DataFrame:
        """
        Extract timelines for all wells.

        Returns:
            DataFrame with well timelines

        Examples:
            >>> extractor = DrillingTimelineExtractor(activity_df)
            >>> timelines = extractor.extract_all_wells_timeline()
        """
        timelines = []

        for api_well_number in self.activity_df["API_WELL_NUMBER"].unique():
            try:
                timeline = self.extract_well_timeline(api_well_number)
                timelines.append(timeline)
            except Exception as e:
                # Log error and continue
                print(f"Warning: Failed to extract timeline for {api_well_number}: {e}")

        if not timelines:
            raise DrillingDataError("No timelines extracted")

        return pd.DataFrame(timelines)

    def classify_activities_from_remarks(self) -> pd.DataFrame:
        """
        Classify all activities using remarks data.

        Returns:
            DataFrame with activity classifications

        Raises:
            DrillingDataError: If remarks data not provided
        """
        if self.remarks_df is None:
            raise DrillingDataError("Remarks data not provided")

        remarks = self.remarks_df.copy()

        # Classify each remark
        remarks["ACTIVITY_TYPE"] = remarks["REMARK"].apply(
            self.classifier.classify_activity
        )

        # Extract mud weight
        remarks["MUD_WEIGHT_PPG"] = remarks["REMARK"].apply(
            self.classifier.extract_mud_weight
        )

        return remarks


def calculate_drilling_days(
    spud_date: datetime, td_date: datetime, gap_threshold_days: int = 90
) -> float:
    """
    Convenience function to calculate drilling days.

    Args:
        spud_date: Spud date
        td_date: Total depth date
        gap_threshold_days: Maximum gap threshold

    Returns:
        Total drilling days

    Examples:
        >>> days = calculate_drilling_days(
        ...     datetime(2020, 1, 1),
        ...     datetime(2020, 3, 15)
        ... )
    """
    return (td_date - spud_date).days
