"""
Data Cleaner

Cleans and standardizes marine safety incident data.
"""

import logging
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union

from worldenergydata.marine_safety.processors.base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class DataCleaner(BaseProcessor):
    """
    Cleans and standardizes marine safety data.

    Handles:
    - Text normalization (trim, case)
    - Date/time parsing and standardization
    - Numeric value cleaning and validation
    - Null/empty value handling
    - Coordinate validation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize data cleaner with configuration."""
        super().__init__(config)

        # Default cleaning configuration
        self.trim_strings = self.config.get("trim_strings", True)
        self.normalize_case = self.config.get("normalize_case", True)
        self.remove_duplicates = self.config.get("remove_duplicates", True)

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean a single incident record.

        Args:
            data: Raw incident data dictionary

        Returns:
            Cleaned incident data dictionary
        """
        if not self.validate(data):
            self.stats["errors"] += 1
            return data

        cleaned = {}

        try:
            # Clean text fields
            for field in [
                "title",
                "description",
                "location_description",
                "incident_type",
            ]:
                if field in data:
                    cleaned[field] = self.clean_text(data[field])

            # Clean and validate dates
            if "incident_date" in data:
                cleaned["incident_date"] = self.clean_date(data["incident_date"])

            if "incident_time" in data:
                cleaned["incident_time"] = self.clean_datetime(data["incident_time"])

            # Clean numeric fields
            for field in ["fatalities", "injuries", "missing_persons"]:
                if field in data:
                    cleaned[field] = self.clean_integer(data[field], min_value=0)

            if "estimated_damage_usd" in data:
                cleaned["estimated_damage_usd"] = self.clean_decimal(
                    data["estimated_damage_usd"], min_value=0
                )

            # Clean coordinates
            if "latitude" in data:
                cleaned["latitude"] = self.clean_latitude(data["latitude"])

            if "longitude" in data:
                cleaned["longitude"] = self.clean_longitude(data["longitude"])

            # Copy other fields as-is
            for key, value in data.items():
                if key not in cleaned:
                    cleaned[key] = value

            self.stats["processed"] += 1

        except Exception as e:
            logger.error(f"Error cleaning data: {e}")
            self.stats["errors"] += 1
            return data

        return cleaned

    def clean_text(self, text: Optional[str]) -> Optional[str]:
        """
        Clean and normalize text field.

        Args:
            text: Input text

        Returns:
            Cleaned text or None
        """
        if not text or (isinstance(text, str) and not text.strip()):
            return None

        text = str(text)

        # Trim whitespace
        if self.trim_strings:
            text = text.strip()

        # Remove multiple spaces
        text = re.sub(r"\s+", " ", text)

        # Normalize case for certain fields (optional)
        # For now, preserve original case

        return text if text else None

    def clean_date(self, date_value: Union[str, date, datetime]) -> Optional[date]:
        """
        Parse and validate date.

        Args:
            date_value: Date in various formats

        Returns:
            Standardized date object or None
        """
        if not date_value:
            return None

        # Already a date object
        if isinstance(date_value, date) and not isinstance(date_value, datetime):
            return date_value

        # datetime object
        if isinstance(date_value, datetime):
            return date_value.date()

        # Parse string
        if isinstance(date_value, str):
            # Try common formats
            formats = [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%Y/%m/%d",
                "%B %d, %Y",
                "%b %d, %Y",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(date_value.strip(), fmt).date()
                except ValueError:
                    continue

            logger.warning(f"Could not parse date: {date_value}")
            self.stats["warnings"] += 1

        return None

    def clean_datetime(self, dt_value: Union[str, datetime]) -> Optional[datetime]:
        """
        Parse and validate datetime.

        Args:
            dt_value: Datetime in various formats

        Returns:
            Standardized datetime object or None
        """
        if not dt_value:
            return None

        if isinstance(dt_value, datetime):
            return dt_value

        if isinstance(dt_value, str):
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%m/%d/%Y %H:%M:%S",
                "%m/%d/%Y %H:%M",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(dt_value.strip(), fmt)
                except ValueError:
                    continue

            logger.warning(f"Could not parse datetime: {dt_value}")
            self.stats["warnings"] += 1

        return None

    def clean_integer(
        self,
        value: Any,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
    ) -> Optional[int]:
        """
        Clean and validate integer value.

        Args:
            value: Input value
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            Cleaned integer or None
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return None

        try:
            # Convert to int
            if isinstance(value, str):
                # Remove commas and spaces
                value = value.replace(",", "").replace(" ", "").strip()

            int_value = int(float(value))  # Handle "10.0" strings

            # Validate range
            if min_value is not None and int_value < min_value:
                logger.warning(f"Integer {int_value} below minimum {min_value}")
                self.stats["warnings"] += 1
                return min_value

            if max_value is not None and int_value > max_value:
                logger.warning(f"Integer {int_value} above maximum {max_value}")
                self.stats["warnings"] += 1
                return max_value

            return int_value

        except (ValueError, TypeError) as e:
            logger.warning(f"Could not convert to integer: {value} ({e})")
            self.stats["warnings"] += 1
            return None

    def clean_decimal(
        self,
        value: Any,
        min_value: Optional[Decimal] = None,
        max_value: Optional[Decimal] = None,
        decimal_places: int = 2,
    ) -> Optional[Decimal]:
        """
        Clean and validate decimal value.

        Args:
            value: Input value
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            decimal_places: Number of decimal places to round to

        Returns:
            Cleaned Decimal or None
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return None

        try:
            # Convert to Decimal
            if isinstance(value, str):
                value = value.replace(",", "").replace(" ", "").strip()
                value = value.replace("$", "")  # Remove currency symbols

            dec_value = Decimal(str(value))

            # Round to specified decimal places
            quantize_value = Decimal("0.1") ** decimal_places
            dec_value = dec_value.quantize(quantize_value)

            # Validate range
            if min_value is not None and dec_value < min_value:
                logger.warning(f"Decimal {dec_value} below minimum {min_value}")
                self.stats["warnings"] += 1
                return min_value

            if max_value is not None and dec_value > max_value:
                logger.warning(f"Decimal {dec_value} above maximum {max_value}")
                self.stats["warnings"] += 1
                return max_value

            return dec_value

        except (InvalidOperation, ValueError, TypeError) as e:
            logger.warning(f"Could not convert to decimal: {value} ({e})")
            self.stats["warnings"] += 1
            return None

    def clean_latitude(self, lat: Any) -> Optional[Decimal]:
        """
        Validate and clean latitude coordinate.

        Args:
            lat: Latitude value

        Returns:
            Cleaned latitude or None
        """
        lat_decimal = self.clean_decimal(
            lat, min_value=Decimal("-90"), max_value=Decimal("90"), decimal_places=7
        )
        return lat_decimal

    def clean_longitude(self, lon: Any) -> Optional[Decimal]:
        """
        Validate and clean longitude coordinate.

        Args:
            lon: Longitude value

        Returns:
            Cleaned longitude or None
        """
        lon_decimal = self.clean_decimal(
            lon, min_value=Decimal("-180"), max_value=Decimal("180"), decimal_places=7
        )
        return lon_decimal

    def batch_process(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of incident records.

        Args:
            data_list: List of raw incident dictionaries

        Returns:
            List of cleaned incident dictionaries
        """
        self.reset_stats()
        cleaned_list = []

        for data in data_list:
            cleaned = self.process(data)
            cleaned_list.append(cleaned)

        logger.info(
            f"Batch processed: {self.stats['processed']} records, "
            f"{self.stats['errors']} errors, {self.stats['warnings']} warnings"
        )

        return cleaned_list
