"""
SurveyProcessor for handling seismic survey data from SODIR.

This processor handles seismic survey data including:
- Survey names and types (2D, 3D, 4D)
- Acquisition dates and duration
- Survey areas and geometry
- Companies and vessels
- Processing status
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SurveyProcessor:
    """Process seismic survey data from SODIR API."""

    # Survey type normalization
    SURVEY_TYPE_MAPPING = {
        "2D": "2D",
        "3D": "3D",
        "4D": "4D",
        "2D/3D": "2D_3D",
        "SITE SURVEY": "SITE_SURVEY",
        "SHALLOW": "SHALLOW",
        "HIGH RESOLUTION": "HIGH_RESOLUTION",
        "HR": "HIGH_RESOLUTION",
        "": "UNKNOWN",
        None: "UNKNOWN",
    }

    # Processing status normalization
    PROCESSING_STATUS_MAPPING = {
        "COMPLETED": "COMPLETED",
        "COMPLETE": "COMPLETED",
        "IN PROGRESS": "IN_PROGRESS",
        "PROCESSING": "IN_PROGRESS",
        "PLANNED": "PLANNED",
        "ACQUIRED": "ACQUIRED",
        "REPROCESSING": "REPROCESSING",
        "CANCELLED": "CANCELLED",
        "": "UNKNOWN",
        None: "UNKNOWN",
    }

    def __init__(self):
        """Initialize the SurveyProcessor."""
        self.processed_count = 0
        self.error_count = 0

    def process(self, survey_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single seismic survey record from SODIR.

        Args:
            survey_data: Raw survey data from SODIR API

        Returns:
            Processed survey data with normalized fields and calculations
        """
        try:
            processed = {
                # Basic identifiers
                "survey_name": survey_data.get("srvName", ""),
                "survey_id": survey_data.get("srvNpdidSurvey"),
                "survey_type": self.normalize_survey_type(survey_data.get("srvType")),
                "survey_subtype": survey_data.get("srvSubType"),
                # Acquisition information
                "acquisition_start_date": self._parse_date(
                    survey_data.get("srvAcquisitionStartDate")
                ),
                "acquisition_end_date": self._parse_date(
                    survey_data.get("srvAcquisitionEndDate")
                ),
                "acquisition_year": self._safe_int(
                    survey_data.get("srvAcquisitionYear")
                ),
                # Company and vessel information
                "company": survey_data.get("srvCompanyName"),
                "contractor": survey_data.get("srvContractorName"),
                "vessel_name": survey_data.get("srvVesselName"),
                "vessel_type": survey_data.get("srvVesselType"),
                # Survey specifications
                "area_km2": self._safe_float(survey_data.get("srvAreaKm2")),
                "line_km": self._safe_float(survey_data.get("srvLineKm")),
                "coverage_percentage": self._safe_float(
                    survey_data.get("srvCoveragePercent")
                ),
                # Technical parameters
                "source_type": survey_data.get("srvSourceType"),
                "source_volume": self._safe_float(survey_data.get("srvSourceVolume")),
                "source_pressure": self._safe_float(
                    survey_data.get("srvSourcePressure")
                ),
                "streamer_length_m": self._safe_float(
                    survey_data.get("srvStreamerLength")
                ),
                "streamer_count": self._safe_int(survey_data.get("srvStreamerCount")),
                "record_length_ms": self._safe_int(survey_data.get("srvRecordLength")),
                "sample_rate_ms": self._safe_float(survey_data.get("srvSampleRate")),
                # Processing information
                "processing_status": self.normalize_processing_status(
                    survey_data.get("srvProcessingStatus")
                ),
                "processing_company": survey_data.get("srvProcessingCompany"),
                "processing_year": self._safe_int(survey_data.get("srvProcessingYear")),
                # Location and geometry
                "main_area": survey_data.get("srvMainArea"),
                "block_coverage": self._parse_blocks(
                    survey_data.get("srvBlockCoverage")
                ),
                "geometry": survey_data.get("geometry"),
                # Data availability
                "data_owner": survey_data.get("srvDataOwner"),
                "data_available": self._parse_boolean(
                    survey_data.get("srvDataAvailable")
                ),
                "confidentiality_expiry": self._parse_date(
                    survey_data.get("srvConfidentialityExpiry")
                ),
                # Metadata
                "date_updated": self._parse_date(survey_data.get("srvDateUpdated")),
                "processed_timestamp": datetime.utcnow().isoformat(),
                "source": "SODIR",
            }

            # Calculate acquisition duration
            if (
                processed["acquisition_start_date"]
                and processed["acquisition_end_date"]
            ):
                processed["acquisition_duration_days"] = self._calculate_duration(
                    processed["acquisition_start_date"],
                    processed["acquisition_end_date"],
                )
            else:
                processed["acquisition_duration_days"] = None

            # Calculate survey age
            if processed["acquisition_year"]:
                processed["survey_age_years"] = (
                    datetime.now().year - processed["acquisition_year"]
                )

            # Assess survey quality/resolution
            processed["survey_quality"] = self._assess_survey_quality(processed)

            # Calculate area coverage efficiency (if line km and area available)
            if (
                processed["line_km"]
                and processed["area_km2"]
                and processed["area_km2"] > 0
            ):
                processed["line_density_km_per_km2"] = round(
                    processed["line_km"] / processed["area_km2"], 2
                )
            else:
                processed["line_density_km_per_km2"] = None

            self.processed_count += 1
            return processed

        except Exception as e:
            logger.error(
                f"Error processing survey {survey_data.get('srvName', 'unknown')}: {str(e)}"
            )
            self.error_count += 1
            return None

    def process_batch(self, surveys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple survey records.

        Args:
            surveys: List of raw survey data from SODIR

        Returns:
            List of processed survey data
        """
        processed_surveys = []

        for survey in surveys:
            result = self.process(survey)
            if result:
                processed_surveys.append(result)

        logger.info(
            f"Processed {len(processed_surveys)}/{len(surveys)} surveys successfully"
        )
        return processed_surveys

    def normalize_survey_type(self, survey_type: Optional[str]) -> str:
        """
        Normalize survey type to standard values.

        Args:
            survey_type: Raw survey type

        Returns:
            Normalized survey type string
        """
        if survey_type in self.SURVEY_TYPE_MAPPING:
            return self.SURVEY_TYPE_MAPPING[survey_type]

        if survey_type:
            type_upper = survey_type.upper().strip()
            if type_upper in self.SURVEY_TYPE_MAPPING:
                return self.SURVEY_TYPE_MAPPING[type_upper]

            # Handle variations
            if "4D" in type_upper or "TIME LAPSE" in type_upper:
                return "4D"
            elif "3D" in type_upper:
                return "3D"
            elif "2D" in type_upper:
                return "2D"
            elif "SITE" in type_upper:
                return "SITE_SURVEY"
            elif "HIGH" in type_upper and "RES" in type_upper:
                return "HIGH_RESOLUTION"

        return "UNKNOWN"

    def normalize_processing_status(self, status: Optional[str]) -> str:
        """
        Normalize processing status to standard values.

        Args:
            status: Raw processing status

        Returns:
            Normalized status string
        """
        if status in self.PROCESSING_STATUS_MAPPING:
            return self.PROCESSING_STATUS_MAPPING[status]

        if status:
            status_upper = status.upper().strip()
            if status_upper in self.PROCESSING_STATUS_MAPPING:
                return self.PROCESSING_STATUS_MAPPING[status_upper]

            # Handle variations
            if "COMPLET" in status_upper:
                return "COMPLETED"
            elif "PROGRESS" in status_upper or "PROCESS" in status_upper:
                return "IN_PROGRESS"
            elif "PLAN" in status_upper:
                return "PLANNED"
            elif "CANCEL" in status_upper:
                return "CANCELLED"

        return "UNKNOWN"

    def validate(self, survey_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate survey data for required fields and data quality.

        Args:
            survey_data: Survey data to validate

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []

        # Check required fields
        required_fields = ["srvName"]
        for field in required_fields:
            if not survey_data.get(field):
                errors.append(f"Missing required field: {field}")

        # Validate survey area
        if "srvAreaKm2" in survey_data and survey_data["srvAreaKm2"] is not None:
            try:
                area = float(survey_data["srvAreaKm2"])
                if area < 0:
                    errors.append(f"Negative survey area: {area}")
                elif area > 100000:  # Sanity check
                    errors.append(f"Suspiciously large survey area: {area} km2")
            except (ValueError, TypeError):
                errors.append(f"Invalid area value: {survey_data['srvAreaKm2']}")

        # Validate dates
        start_date = survey_data.get("srvAcquisitionStartDate")
        end_date = survey_data.get("srvAcquisitionEndDate")

        if start_date and end_date:
            try:
                start = self._parse_date(start_date)
                end = self._parse_date(end_date)
                if start and end and start > end:
                    errors.append(
                        f"Acquisition end date ({end}) before start date ({start})"
                    )
            except Exception:
                pass

        # Validate acquisition year
        if "srvAcquisitionYear" in survey_data and survey_data["srvAcquisitionYear"]:
            try:
                year = int(survey_data["srvAcquisitionYear"])
                current_year = datetime.now().year
                if year < 1960 or year > current_year:
                    errors.append(f"Invalid acquisition year: {year}")
            except (ValueError, TypeError):
                errors.append(
                    f"Invalid year value: {survey_data['srvAcquisitionYear']}"
                )

        # Validate technical parameters
        if (
            "srvStreamerCount" in survey_data
            and survey_data["srvStreamerCount"] is not None
        ):
            try:
                count = int(survey_data["srvStreamerCount"])
                if count < 0 or count > 50:  # Reasonable range for streamer count
                    errors.append(f"Invalid streamer count: {count}")
            except (ValueError, TypeError):
                errors.append(
                    f"Invalid streamer count value: {survey_data['srvStreamerCount']}"
                )

        is_valid = len(errors) == 0
        return is_valid, errors

    def _assess_survey_quality(self, processed_data: Dict[str, Any]) -> str:
        """
        Assess survey quality based on type and technical parameters.

        Args:
            processed_data: Processed survey data

        Returns:
            Quality assessment string
        """
        survey_type = processed_data.get("survey_type", "")

        # 4D surveys are highest quality for monitoring
        if survey_type == "4D":
            return "VERY_HIGH"

        # 3D surveys are high quality
        if survey_type == "3D":
            # Check technical parameters for quality indicators
            streamer_count = processed_data.get("streamer_count")
            if streamer_count and streamer_count >= 10:
                return "VERY_HIGH"
            elif streamer_count and streamer_count >= 6:
                return "HIGH"
            return "HIGH"

        # High resolution surveys
        if survey_type == "HIGH_RESOLUTION":
            return "HIGH"

        # 2D surveys are standard quality
        if survey_type == "2D":
            return "STANDARD"

        # Site surveys are specific purpose
        if survey_type == "SITE_SURVEY":
            return "SPECIALIZED"

        return "UNKNOWN"

    def _calculate_duration(self, start_date: str, end_date: str) -> int:
        """
        Calculate duration in days between two dates.

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            Duration in days
        """
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            return (end - start).days
        except Exception:
            return 0

    def _parse_blocks(self, block_string: Any) -> List[str]:
        """
        Parse block coverage string into list of blocks.

        Args:
            block_string: String containing block names

        Returns:
            List of block names
        """
        if not block_string:
            return []

        try:
            block_str = str(block_string)
            # Handle various separators
            if "," in block_str:
                blocks = [b.strip() for b in block_str.split(",")]
            elif ";" in block_str:
                blocks = [b.strip() for b in block_str.split(";")]
            elif "/" in block_str and " " in block_str:
                # Multiple blocks like "35/11 35/12"
                blocks = [b.strip() for b in block_str.split(" ")]
            else:
                blocks = [block_str.strip()]

            return [b for b in blocks if b]  # Filter empty strings
        except Exception:
            return []

    def _parse_boolean(self, value: Any) -> Optional[bool]:
        """
        Parse boolean value from various formats.

        Args:
            value: Value to parse as boolean

        Returns:
            Boolean value or None
        """
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        str_val = str(value).upper().strip()
        if str_val in ["TRUE", "YES", "Y", "1"]:
            return True
        elif str_val in ["FALSE", "NO", "N", "0"]:
            return False

        return None

    def _safe_float(self, value: Any) -> Optional[float]:
        """
        Safely convert a value to float.

        Args:
            value: Value to convert

        Returns:
            Float value or None
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
            Int value or None
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
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%Y%m%d"]:
                try:
                    dt = datetime.strptime(str(date_str), fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue
            return str(date_str)
        except Exception:
            return None

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
