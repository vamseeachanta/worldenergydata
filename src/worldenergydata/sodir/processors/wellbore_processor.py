"""
WellboreProcessor for handling wellbore data from SODIR with unit conversions.

This processor handles wellbore data including:
- Wellbore identifiers and names
- Status normalization (P&A, drilling, producing, etc.)
- Depth conversions (meters to feet)
- Coordinate information
- Drilling dates and operators
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class WellboreProcessor:
    """Process wellbore data from SODIR API with unit conversions."""

    # Conversion factors
    METERS_TO_FEET = 3.28084
    FEET_TO_METERS = 0.3048

    # Status normalization mapping
    STATUS_MAPPING = {
        "P&A": "PLUGGED_AND_ABANDONED",
        "PA": "PLUGGED_AND_ABANDONED",
        "P AND A": "PLUGGED_AND_ABANDONED",
        "PLUGGED": "PLUGGED_AND_ABANDONED",
        "PLUGGED AND ABANDONED": "PLUGGED_AND_ABANDONED",
        "DRILLING": "DRILLING",
        "ACTIVE": "ACTIVE",
        "SUSPENDED": "SUSPENDED",
        "TEMPORARILY ABANDONED": "TEMPORARILY_ABANDONED",
        "TA": "TEMPORARILY_ABANDONED",
        "PRODUCING": "PRODUCING",
        "PRODUCTION": "PRODUCING",
        "INJECTION": "INJECTION",
        "CLOSED": "CLOSED",
        "COMPLETED": "COMPLETED",
        "": "UNKNOWN",
        None: "UNKNOWN",
    }

    # Purpose normalization
    PURPOSE_MAPPING = {
        "EXPLORATION": "EXPLORATION",
        "APPRAISAL": "APPRAISAL",
        "DEVELOPMENT": "DEVELOPMENT",
        "PRODUCTION": "PRODUCTION",
        "INJECTION": "INJECTION",
        "OBSERVATION": "OBSERVATION",
        "": "UNKNOWN",
        None: "UNKNOWN",
    }

    def __init__(self):
        """Initialize the WellboreProcessor."""
        self.processed_count = 0
        self.error_count = 0

    def process(self, wellbore_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single wellbore record from SODIR.

        Args:
            wellbore_data: Raw wellbore data from SODIR API

        Returns:
            Processed wellbore data with normalized fields and unit conversions
        """
        try:
            processed = {
                # Basic identifiers
                "wellbore_name": wellbore_data.get("wlbName", ""),
                "wellbore_id": wellbore_data.get("wlbNpdidWellbore"),
                "well_name": wellbore_data.get("wlbWell", ""),
                # Status and purpose
                "status": wellbore_data.get("wlbStatus", ""),
                "status_normalized": self.normalize_wellbore_status(
                    wellbore_data.get("wlbStatus")
                ),
                "purpose": wellbore_data.get("wlbPurpose", ""),
                "purpose_normalized": self.normalize_purpose(
                    wellbore_data.get("wlbPurpose")
                ),
                "content": wellbore_data.get("wlbContent", ""),
                # Operator information
                "operator": wellbore_data.get("wlbDrillingOperator"),
                "production_license": wellbore_data.get("wlbProductionLicense"),
                # Depths with conversions
                "total_depth_m": self._safe_float(wellbore_data.get("wlbTotalDepth")),
                "total_depth_ft": self._convert_depth_to_feet(
                    wellbore_data.get("wlbTotalDepth")
                ),
                "kelly_bush_elevation_m": self._safe_float(
                    wellbore_data.get("wlbKellyBushElevation")
                ),
                "kelly_bush_elevation_ft": self._convert_depth_to_feet(
                    wellbore_data.get("wlbKellyBushElevation")
                ),
                "water_depth_m": self._safe_float(wellbore_data.get("wlbWaterDepth")),
                "water_depth_ft": self._convert_depth_to_feet(
                    wellbore_data.get("wlbWaterDepth")
                ),
                # Dates
                "completion_date": self._parse_date(
                    wellbore_data.get("wlbCompletionDate")
                ),
                "entry_date": self._parse_date(wellbore_data.get("wlbEntryDate")),
                "drilling_start_date": self._parse_date(
                    wellbore_data.get("wlbDrillingStartDate")
                ),
                "drilling_end_date": self._parse_date(
                    wellbore_data.get("wlbDrillingEndDate")
                ),
                # Coordinates (WGS84)
                "latitude": self._safe_float(wellbore_data.get("wlbNsDecDeg")),
                "longitude": self._safe_float(wellbore_data.get("wlbEwDecDeg")),
                # UTM coordinates
                "utm_northing": self._safe_float(wellbore_data.get("wlbNsUtm")),
                "utm_easting": self._safe_float(wellbore_data.get("wlbEwUtm")),
                "utm_zone": self._safe_int(wellbore_data.get("wlbUtmZone")),
                # Additional information
                "field": wellbore_data.get("wlbField"),
                "discovery": wellbore_data.get("wlbDiscovery"),
                "bottom_hole_temperature_c": self._safe_float(
                    wellbore_data.get("wlbBottomHoleTemperature")
                ),
                "max_inclination_deg": self._safe_float(
                    wellbore_data.get("wlbMaxInclination")
                ),
                # Metadata
                "processed_timestamp": datetime.utcnow().isoformat(),
                "source": "SODIR",
            }

            # Calculate bottom hole temperature in Fahrenheit if available
            if processed["bottom_hole_temperature_c"] is not None:
                processed["bottom_hole_temperature_f"] = self.celsius_to_fahrenheit(
                    processed["bottom_hole_temperature_c"]
                )

            # Calculate drilling duration if dates available
            if processed["drilling_start_date"] and processed["drilling_end_date"]:
                processed["drilling_duration_days"] = self._calculate_duration(
                    processed["drilling_start_date"], processed["drilling_end_date"]
                )

            self.processed_count += 1
            return processed

        except Exception as e:
            logger.error(
                f"Error processing wellbore {wellbore_data.get('wlbName', 'unknown')}: {str(e)}"
            )
            self.error_count += 1
            return None

    def process_batch(self, wellbores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple wellbore records.

        Args:
            wellbores: List of raw wellbore data from SODIR

        Returns:
            List of processed wellbore data
        """
        processed_wellbores = []

        for wellbore in wellbores:
            result = self.process(wellbore)
            if result:
                processed_wellbores.append(result)

        logger.info(
            f"Processed {len(processed_wellbores)}/{len(wellbores)} wellbores successfully"
        )
        return processed_wellbores

    def normalize_wellbore_status(self, status: Optional[str]) -> str:
        """
        Normalize wellbore status to standard values.

        Args:
            status: Raw status value

        Returns:
            Normalized status string
        """
        if status in self.STATUS_MAPPING:
            return self.STATUS_MAPPING[status]

        # Try uppercase matching
        if status:
            status_upper = status.upper().strip()
            if status_upper in self.STATUS_MAPPING:
                return self.STATUS_MAPPING[status_upper]

        return "UNKNOWN"

    def normalize_purpose(self, purpose: Optional[str]) -> str:
        """
        Normalize wellbore purpose to standard values.

        Args:
            purpose: Raw purpose value

        Returns:
            Normalized purpose string
        """
        if purpose in self.PURPOSE_MAPPING:
            return self.PURPOSE_MAPPING[purpose]

        if purpose:
            purpose_upper = purpose.upper().strip()
            if purpose_upper in self.PURPOSE_MAPPING:
                return self.PURPOSE_MAPPING[purpose_upper]

        return "UNKNOWN"

    def meters_to_feet(self, meters: Optional[float]) -> Optional[float]:
        """
        Convert meters to feet.

        Args:
            meters: Value in meters

        Returns:
            Value in feet or None
        """
        if meters is None:
            return None
        try:
            return round(float(meters) * self.METERS_TO_FEET, 2)
        except (ValueError, TypeError):
            return None

    def feet_to_meters(self, feet: Optional[float]) -> Optional[float]:
        """
        Convert feet to meters.

        Args:
            feet: Value in feet

        Returns:
            Value in meters or None
        """
        if feet is None:
            return None
        try:
            return round(float(feet) * self.FEET_TO_METERS, 2)
        except (ValueError, TypeError):
            return None

    def celsius_to_fahrenheit(self, celsius: float) -> float:
        """
        Convert Celsius to Fahrenheit.

        Args:
            celsius: Temperature in Celsius

        Returns:
            Temperature in Fahrenheit
        """
        return round((celsius * 9 / 5) + 32, 1)

    def validate(self, wellbore_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate wellbore data for required fields and data quality.

        Args:
            wellbore_data: Wellbore data to validate

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []

        # Check required fields
        required_fields = ["wlbName"]
        for field in required_fields:
            if not wellbore_data.get(field):
                errors.append(f"Missing required field: {field}")

        # Validate wellbore name format
        wellbore_name = wellbore_data.get("wlbName", "")
        if wellbore_name and not self._is_valid_wellbore_name(wellbore_name):
            errors.append(f"Invalid wellbore name format: {wellbore_name}")

        # Validate depths
        depth_fields = ["wlbTotalDepth", "wlbWaterDepth", "wlbKellyBushElevation"]
        for field in depth_fields:
            if field in wellbore_data and wellbore_data[field] is not None:
                try:
                    depth = float(wellbore_data[field])
                    if field == "wlbTotalDepth" and depth < 0:
                        errors.append(f"Invalid total depth (negative): {depth}")
                    elif field == "wlbTotalDepth" and depth > 15000:  # Sanity check
                        errors.append(f"Suspicious total depth (>15km): {depth}")
                except (ValueError, TypeError):
                    errors.append(
                        f"Invalid depth value in {field}: {wellbore_data[field]}"
                    )

        # Validate coordinates if present
        if "wlbNsDecDeg" in wellbore_data and wellbore_data["wlbNsDecDeg"] is not None:
            lat = wellbore_data["wlbNsDecDeg"]
            try:
                lat_float = float(lat)
                if lat_float < 56 or lat_float > 72:  # Norwegian waters
                    errors.append(f"Latitude outside Norwegian waters: {lat_float}")
            except (ValueError, TypeError):
                errors.append(f"Invalid latitude: {lat}")

        if "wlbEwDecDeg" in wellbore_data and wellbore_data["wlbEwDecDeg"] is not None:
            lon = wellbore_data["wlbEwDecDeg"]
            try:
                lon_float = float(lon)
                if lon_float < -5 or lon_float > 35:  # Norwegian waters
                    errors.append(f"Longitude outside Norwegian waters: {lon_float}")
            except (ValueError, TypeError):
                errors.append(f"Invalid longitude: {lon}")

        is_valid = len(errors) == 0
        return is_valid, errors

    def _convert_depth_to_feet(self, depth_meters: Any) -> Optional[float]:
        """
        Convert depth from meters to feet.

        Args:
            depth_meters: Depth in meters

        Returns:
            Depth in feet or None
        """
        if depth_meters is None:
            return None
        try:
            return round(float(depth_meters) * self.METERS_TO_FEET, 2)
        except (ValueError, TypeError):
            return None

    def _safe_float(self, value: Any) -> Optional[float]:
        """
        Safely convert a value to float.

        Args:
            value: Value to convert

        Returns:
            Float value or None if conversion fails
        """
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value: Any) -> Optional[int]:
        """
        Safely convert a value to int.

        Args:
            value: Value to convert

        Returns:
            Int value or None if conversion fails
        """
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _parse_date(self, date_str: Any) -> Optional[str]:
        """
        Parse and validate date string.

        Args:
            date_str: Date string to parse

        Returns:
            ISO format date string or None
        """
        if not date_str:
            return None

        try:
            # Try to parse various date formats
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%Y%m%d"]:
                try:
                    dt = datetime.strptime(str(date_str), fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue
            return str(date_str)  # Return as-is if no format matches
        except Exception:
            return None

    def _calculate_duration(self, start_date: str, end_date: str) -> Optional[int]:
        """
        Calculate duration in days between two dates.

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            Duration in days or None
        """
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            return (end - start).days
        except Exception:
            return None

    def _is_valid_wellbore_name(self, wellbore_name: str) -> bool:
        """
        Validate wellbore name format (e.g., "35/11-1").

        Args:
            wellbore_name: Wellbore name to validate

        Returns:
            True if valid format
        """
        # Norwegian wellbores typically follow pattern like "35/11-1" or "35/11-1 S"
        import re

        pattern = r"^\d{1,3}/\d{1,2}-\d+(\s+[A-Z]+)?$"
        return bool(re.match(pattern, wellbore_name))

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.

        Returns:
            Dictionary with processing counts
        """
        return {
            "processed": self.processed_count,
            "errors": self.error_count,
            "success_rate": self.processed_count
            / max(self.processed_count + self.error_count, 1),
        }
