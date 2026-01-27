"""
FieldProcessor for handling Norwegian field data including resources and production.

This processor handles field data including:
- Field names and status
- Resource estimates (oil, gas, NGL)
- Production information
- Recovery factors
- Operator information
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FieldProcessor:
    """Process Norwegian field data from SODIR API."""

    # Status normalization mapping
    STATUS_MAPPING = {
        "PRODUCING": "PRODUCING",
        "PRODUCTION": "PRODUCING",
        "SHUT DOWN": "SHUT_DOWN",
        "SHUTDOWN": "SHUT_DOWN",
        "CLOSED": "SHUT_DOWN",
        "PDO APPROVED": "PDO_APPROVED",
        "PAD APPROVED": "PDO_APPROVED",
        "PLANNING PHASE": "PLANNING_PHASE",
        "PLANNING": "PLANNING_PHASE",
        "DEVELOPMENT": "DEVELOPMENT",
        "DISCOVERY": "DISCOVERY",
        "ABANDONED": "ABANDONED",
        "": "UNKNOWN",
        None: "UNKNOWN",
    }

    # Conversion factors
    # Norwegian data often in Sm3 (standard cubic meters)
    # 1 Sm3 oil = 6.29 barrels
    # 1 billion Sm3 gas = 35.3 billion cubic feet
    SM3_TO_BARRELS = 6.29
    BILLION_SM3_TO_BCF = 35.3

    def __init__(self):
        """Initialize the FieldProcessor."""
        self.processed_count = 0
        self.error_count = 0

    def process(self, field_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single field record from SODIR.

        Args:
            field_data: Raw field data from SODIR API

        Returns:
            Processed field data with normalized fields and calculations
        """
        try:
            processed = {
                # Basic identifiers
                "field_name": field_data.get("fldName", ""),
                "field_id": field_data.get("fldNpdidField"),
                "status": self.normalize_field_status(field_data.get("fldStatus")),
                # Operator and ownership
                "operator": field_data.get("fldOperatorName"),
                "owner_kind": field_data.get("fldOwnerKind"),
                "ownership_share": self._safe_float(
                    field_data.get("fldOwnershipShare")
                ),
                # Discovery and production dates
                "discovery_year": self._safe_int(field_data.get("fldDiscoveryYear")),
                "production_start_year": self._safe_int(
                    field_data.get("fldProductionStartYear")
                ),
                "cessation_year": self._safe_int(field_data.get("fldCessationYear")),
                # Original reserves (in place)
                "original_reserves_oil_mmbbl": self._convert_to_mmbbl(
                    field_data.get("fldOriginalReservesOil")
                ),
                "original_reserves_gas_bcf": self._convert_to_bcf(
                    field_data.get("fldOriginalReservesGas")
                ),
                "original_reserves_ngl_mmbbl": self._convert_to_mmbbl(
                    field_data.get("fldOriginalReservesNGL")
                ),
                "original_reserves_condensate_mmbbl": self._convert_to_mmbbl(
                    field_data.get("fldOriginalReservesCondensate")
                ),
                # Remaining reserves
                "remaining_reserves_oil_mmbbl": self._convert_to_mmbbl(
                    field_data.get("fldRemainingReservesOil")
                ),
                "remaining_reserves_gas_bcf": self._convert_to_bcf(
                    field_data.get("fldRemainingReservesGas")
                ),
                "remaining_reserves_ngl_mmbbl": self._convert_to_mmbbl(
                    field_data.get("fldRemainingReservesNGL")
                ),
                "remaining_reserves_condensate_mmbbl": self._convert_to_mmbbl(
                    field_data.get("fldRemainingReservesCondensate")
                ),
                # Recoverable reserves
                "recoverable_oil_mmbbl": self._convert_to_mmbbl(
                    field_data.get("fldRecoverableOil")
                ),
                "recoverable_gas_bcf": self._convert_to_bcf(
                    field_data.get("fldRecoverableGas")
                ),
                "recoverable_ngl_mmbbl": self._convert_to_mmbbl(
                    field_data.get("fldRecoverableNGL")
                ),
                "recoverable_condensate_mmbbl": self._convert_to_mmbbl(
                    field_data.get("fldRecoverableCondensate")
                ),
                # Production totals
                "cumulative_oil_production_mmbbl": self._convert_to_mmbbl(
                    field_data.get("fldCumulativeOilProduction")
                ),
                "cumulative_gas_production_bcf": self._convert_to_bcf(
                    field_data.get("fldCumulativeGasProduction")
                ),
                "cumulative_ngl_production_mmbbl": self._convert_to_mmbbl(
                    field_data.get("fldCumulativeNGLProduction")
                ),
                "cumulative_condensate_production_mmbbl": self._convert_to_mmbbl(
                    field_data.get("fldCumulativeCondensateProduction")
                ),
                # Infrastructure
                "main_supply_base": field_data.get("fldMainSupplyBase"),
                "main_area": field_data.get("fldMainArea"),
                "water_depth_m": self._safe_float(field_data.get("fldWaterDepth")),
                # Geometry
                "geometry": field_data.get("geometry"),
                # Metadata
                "date_updated": self._parse_date(field_data.get("fldDateUpdated")),
                "processed_timestamp": datetime.utcnow().isoformat(),
                "source": "SODIR",
            }

            # Calculate recovery factors
            processed["recovery_factor_oil"] = self._calculate_recovery_factor(
                processed["original_reserves_oil_mmbbl"],
                processed["remaining_reserves_oil_mmbbl"],
            )
            processed["recovery_factor_gas"] = self._calculate_recovery_factor(
                processed["original_reserves_gas_bcf"],
                processed["remaining_reserves_gas_bcf"],
            )

            # Calculate production efficiency
            if (
                processed["recoverable_oil_mmbbl"]
                and processed["cumulative_oil_production_mmbbl"]
            ):
                processed["oil_production_efficiency"] = round(
                    processed["cumulative_oil_production_mmbbl"]
                    / processed["recoverable_oil_mmbbl"],
                    3,
                )
            else:
                processed["oil_production_efficiency"] = None

            # Calculate field age
            if processed["discovery_year"]:
                processed["field_age_years"] = (
                    datetime.now().year - processed["discovery_year"]
                )

            # Calculate production duration
            if processed["production_start_year"]:
                if processed["cessation_year"]:
                    processed["production_duration_years"] = (
                        processed["cessation_year"] - processed["production_start_year"]
                    )
                else:
                    processed["production_duration_years"] = (
                        datetime.now().year - processed["production_start_year"]
                    )

            self.processed_count += 1
            return processed

        except Exception as e:
            logger.error(
                f"Error processing field {field_data.get('fldName', 'unknown')}: {str(e)}"
            )
            self.error_count += 1
            return None

    def process_batch(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple field records.

        Args:
            fields: List of raw field data from SODIR

        Returns:
            List of processed field data
        """
        processed_fields = []

        for field in fields:
            result = self.process(field)
            if result:
                processed_fields.append(result)

        logger.info(
            f"Processed {len(processed_fields)}/{len(fields)} fields successfully"
        )
        return processed_fields

    def normalize_field_status(self, status: Optional[str]) -> str:
        """
        Normalize field status to standard values.

        Args:
            status: Raw status value

        Returns:
            Normalized status string
        """
        if status in self.STATUS_MAPPING:
            return self.STATUS_MAPPING[status]

        if status:
            status_upper = status.upper().strip()
            if status_upper in self.STATUS_MAPPING:
                return self.STATUS_MAPPING[status_upper]

            # Handle variations
            if "PRODUC" in status_upper:
                return "PRODUCING"
            elif "SHUT" in status_upper or "CLOSE" in status_upper:
                return "SHUT_DOWN"
            elif "PLAN" in status_upper:
                return "PLANNING_PHASE"
            elif "PDO" in status_upper or "PAD" in status_upper:
                return "PDO_APPROVED"

        return "UNKNOWN"

    def validate(self, field_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate field data for required fields and data quality.

        Args:
            field_data: Field data to validate

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []

        # Check required fields
        required_fields = ["fldName"]
        for field in required_fields:
            if not field_data.get(field):
                errors.append(f"Missing required field: {field}")

        # Validate reserves are non-negative
        reserve_fields = [
            "fldOriginalReservesOil",
            "fldOriginalReservesGas",
            "fldRemainingReservesOil",
            "fldRemainingReservesGas",
            "fldRecoverableOil",
            "fldRecoverableGas",
        ]

        for field in reserve_fields:
            if field in field_data and field_data[field] is not None:
                try:
                    value = float(field_data[field])
                    if value < 0:
                        errors.append(f"Negative reserve value in {field}: {value}")
                except (ValueError, TypeError):
                    errors.append(
                        f"Invalid numeric value in {field}: {field_data[field]}"
                    )

        # Validate logical relationships
        if all(
            field in field_data
            for field in ["fldOriginalReservesOil", "fldRemainingReservesOil"]
        ):
            try:
                original = float(field_data["fldOriginalReservesOil"] or 0)
                remaining = float(field_data["fldRemainingReservesOil"] or 0)
                if remaining > original:
                    errors.append(
                        f"Remaining reserves ({remaining}) exceed original reserves ({original})"
                    )
            except (ValueError, TypeError):
                pass

        # Validate years
        year_fields = ["fldDiscoveryYear", "fldProductionStartYear", "fldCessationYear"]
        current_year = datetime.now().year

        for field in year_fields:
            if field in field_data and field_data[field] is not None:
                try:
                    year = int(field_data[field])
                    if year < 1960 or year > current_year + 10:
                        errors.append(f"Invalid year in {field}: {year}")
                except (ValueError, TypeError):
                    errors.append(f"Invalid year value in {field}: {field_data[field]}")

        # Validate production timeline
        discovery = field_data.get("fldDiscoveryYear")
        prod_start = field_data.get("fldProductionStartYear")
        cessation = field_data.get("fldCessationYear")

        if discovery and prod_start:
            try:
                if int(prod_start) < int(discovery):
                    errors.append(
                        f"Production start ({prod_start}) before discovery ({discovery})"
                    )
            except (ValueError, TypeError):
                pass

        if prod_start and cessation:
            try:
                if int(cessation) < int(prod_start):
                    errors.append(
                        f"Cessation ({cessation}) before production start ({prod_start})"
                    )
            except (ValueError, TypeError):
                pass

        is_valid = len(errors) == 0
        return is_valid, errors

    def _calculate_recovery_factor(
        self, original: Optional[float], remaining: Optional[float]
    ) -> Optional[float]:
        """
        Calculate recovery factor based on original and remaining reserves.

        Args:
            original: Original reserves
            remaining: Remaining reserves

        Returns:
            Recovery factor (0-1) or None
        """
        if original is None or remaining is None or original == 0:
            return None

        try:
            produced = original - remaining
            if produced < 0:
                return None
            recovery = produced / original
            return round(min(max(recovery, 0), 1), 3)  # Clamp between 0 and 1
        except (ValueError, TypeError, ZeroDivisionError):
            return None

    def _convert_to_mmbbl(self, value: Any) -> Optional[float]:
        """
        Convert value to million barrels (from Sm3 if needed).

        Args:
            value: Value to convert (assumed to be in million Sm3 if from SODIR)

        Returns:
            Value in million barrels or None
        """
        if value is None:
            return None
        try:
            # Assuming input is in million Sm3, convert to million barrels
            msm3 = float(value)
            mmbbl = msm3 * self.SM3_TO_BARRELS
            return round(mmbbl, 2)
        except (ValueError, TypeError):
            return None

    def _convert_to_bcf(self, value: Any) -> Optional[float]:
        """
        Convert value to billion cubic feet (from billion Sm3 if needed).

        Args:
            value: Value to convert (assumed to be in billion Sm3 if from SODIR)

        Returns:
            Value in billion cubic feet or None
        """
        if value is None:
            return None
        try:
            # Assuming input is in billion Sm3, convert to BCF
            bsm3 = float(value)
            bcf = bsm3 * self.BILLION_SM3_TO_BCF
            return round(bcf, 2)
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
