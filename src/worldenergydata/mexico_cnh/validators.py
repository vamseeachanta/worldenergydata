# ABOUTME: Data validation utilities for Mexico CNH data processing
# ABOUTME: Validates Clave del Pozo, Mexican coordinates, field names, and contracts

"""
Data validation utilities for Mexico CNH data processing.

Provides validation for:
- Clave del Pozo (well key) format
- Mexican geographic coordinates (UTM zones 14/15)
- Field and block names
- Contract identifiers (Round 1, Round 2, etc.)
- Production data ranges
- Required fields and data types
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MexicoCNHValidator:
    """Validate Mexico CNH data for quality and consistency."""

    # Mexico geographic bounds (approximate)
    MEXICO_LAT_MIN = 14.53
    MEXICO_LAT_MAX = 32.72
    MEXICO_LON_MIN = -118.40
    MEXICO_LON_MAX = -86.70

    # Offshore regions (Gulf of Mexico Mexican waters)
    GOM_MEXICO_LAT_MIN = 18.0
    GOM_MEXICO_LAT_MAX = 27.0
    GOM_MEXICO_LON_MIN = -98.0
    GOM_MEXICO_LON_MAX = -86.0

    # UTM zones covering Mexico (mainly 11-16)
    VALID_UTM_ZONES = [11, 12, 13, 14, 15, 16]

    # Valid contract round identifiers
    VALID_CONTRACT_ROUNDS = [
        "R01",  # Round 1
        "R02",  # Round 2
        "R03",  # Round 3
        "R04",  # Round 4
        "MIG",  # Migration contracts
        "ASG",  # Assignments (PEMEX)
        "FMP",  # Farm-outs PEMEX
    ]

    # Valid hydrocarbon types
    VALID_HYDROCARBON_TYPES = [
        "aceite",  # Oil
        "gas_asociado",  # Associated gas
        "gas_no_asociado",  # Non-associated gas
        "condensado",  # Condensate
        "aceite_extrapesado",  # Extra-heavy oil
        "aceite_pesado",  # Heavy oil
        "aceite_ligero",  # Light oil
        "aceite_superligero",  # Super-light oil
    ]

    # Mexican state codes for oil/gas regions
    OIL_GAS_STATES = {
        "TAB": "Tabasco",
        "CAM": "Campeche",
        "VER": "Veracruz",
        "TAM": "Tamaulipas",
        "NLE": "Nuevo Leon",
        "COA": "Coahuila",
        "CHI": "Chihuahua",
        "PUE": "Puebla",
        "SLP": "San Luis Potosi",
    }

    def __init__(self):
        """Initialize the MexicoCNHValidator."""
        self.validation_count = 0
        self.error_count = 0

    def validate_clave_pozo(self, clave_pozo: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Clave del Pozo (well key) format.

        Mexico CNH well keys follow specific formats depending on the era:
        - Modern format: Area-Campo-Pozo-Sufijo (e.g., "AKAL-C-1001-D")
        - Legacy PEMEX format: Various formats with area/field/well number

        Args:
            clave_pozo: Well key to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not clave_pozo:
            return False, "Clave del Pozo is empty"

        # Normalize by removing extra spaces and converting to uppercase
        normalized = clave_pozo.strip().upper()

        # Check minimum length
        if len(normalized) < 3:
            return False, f"Clave del Pozo too short: {clave_pozo}"

        # Check for invalid characters (allow alphanumeric, hyphen, underscore)
        if not re.match(r"^[A-Z0-9\-_]+$", normalized):
            return (
                False,
                f"Invalid characters in Clave del Pozo: {clave_pozo}. "
                "Only alphanumeric, hyphen, and underscore allowed",
            )

        # Common patterns for Mexican well keys
        patterns = [
            # Modern CNH format: AREA-FIELD-NUMBER-SUFFIX
            r"^[A-Z]{2,10}-[A-Z0-9]{1,10}-\d{1,5}(-[A-Z0-9]{1,5})?$",
            # PEMEX legacy format: FIELDNUMBER or FIELD-NUMBER
            r"^[A-Z]{2,15}\d{1,5}[A-Z]?$",
            r"^[A-Z]{2,15}-\d{1,5}[A-Z]?$",
            # Simple numeric with prefix
            r"^[A-Z]{1,5}\d{3,8}$",
        ]

        for pattern in patterns:
            if re.match(pattern, normalized):
                return True, None

        # If no pattern matches but format looks reasonable, accept with warning
        if len(normalized) >= 3 and "-" in normalized or normalized[0].isalpha():
            logger.debug(f"Non-standard Clave del Pozo format accepted: {clave_pozo}")
            return True, None

        return (
            False,
            f"Invalid Clave del Pozo format: {clave_pozo}. "
            "Expected format like 'AKAL-C-1001' or 'CANTARELL101'",
        )

    def validate_mexico_coordinates(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        offshore_only: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if coordinates are within Mexico bounds.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            offshore_only: If True, validate against Gulf of Mexico bounds only

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if latitude is None or longitude is None:
            return False, "Latitude or longitude is missing"

        try:
            lat = float(latitude)
            lon = float(longitude)

            if offshore_only:
                # Validate against Gulf of Mexico Mexican waters
                if lat < self.GOM_MEXICO_LAT_MIN or lat > self.GOM_MEXICO_LAT_MAX:
                    return (
                        False,
                        f"Latitude {lat} is outside Mexican Gulf of Mexico bounds "
                        f"({self.GOM_MEXICO_LAT_MIN} to {self.GOM_MEXICO_LAT_MAX})",
                    )
                if lon < self.GOM_MEXICO_LON_MIN or lon > self.GOM_MEXICO_LON_MAX:
                    return (
                        False,
                        f"Longitude {lon} is outside Mexican Gulf of Mexico bounds "
                        f"({self.GOM_MEXICO_LON_MIN} to {self.GOM_MEXICO_LON_MAX})",
                    )
            else:
                # Validate against all of Mexico
                if lat < self.MEXICO_LAT_MIN or lat > self.MEXICO_LAT_MAX:
                    return (
                        False,
                        f"Latitude {lat} is outside Mexico bounds "
                        f"({self.MEXICO_LAT_MIN} to {self.MEXICO_LAT_MAX})",
                    )
                if lon < self.MEXICO_LON_MIN or lon > self.MEXICO_LON_MAX:
                    return (
                        False,
                        f"Longitude {lon} is outside Mexico bounds "
                        f"({self.MEXICO_LON_MIN} to {self.MEXICO_LON_MAX})",
                    )

            return True, None

        except (ValueError, TypeError) as e:
            return False, f"Invalid coordinate format: {e}"

    def validate_utm_zone(self, utm_zone: int) -> Tuple[bool, Optional[str]]:
        """
        Validate UTM zone for Mexico.

        Mexico spans UTM zones 11-16.

        Args:
            utm_zone: UTM zone number

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if utm_zone not in self.VALID_UTM_ZONES:
            return (
                False,
                f"Invalid UTM zone for Mexico: {utm_zone}. "
                f"Valid zones: {self.VALID_UTM_ZONES}",
            )
        return True, None

    def validate_field_name(self, field_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Mexican oil/gas field name.

        Args:
            field_name: Field name to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not field_name:
            return False, "Field name is empty"

        # Normalize
        normalized = field_name.strip()

        # Check length
        if len(normalized) < 2:
            return False, f"Field name too short: {field_name}"

        if len(normalized) > 100:
            return False, f"Field name too long: {field_name}"

        # Check for obviously invalid content
        if normalized.isdigit():
            return False, f"Field name cannot be numeric only: {field_name}"

        return True, None

    def validate_contract_id(self, contract_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate CNH contract identifier.

        Contract IDs follow patterns like: CNH-R01-L01-A1/2015

        Args:
            contract_id: Contract identifier to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not contract_id:
            return False, "Contract ID is empty"

        normalized = contract_id.strip().upper()

        # Check for CNH prefix
        if normalized.startswith("CNH-"):
            # Extract round identifier
            parts = normalized.split("-")
            if len(parts) >= 2:
                round_id = parts[1][:3]  # Get first 3 chars (R01, R02, etc.)
                if round_id not in self.VALID_CONTRACT_ROUNDS:
                    return (
                        False,
                        f"Invalid contract round in '{contract_id}'. "
                        f"Valid rounds: {self.VALID_CONTRACT_ROUNDS}",
                    )
        elif not any(round_id in normalized for round_id in self.VALID_CONTRACT_ROUNDS):
            # Check if any valid round identifier is present
            logger.debug(f"Non-standard contract ID format: {contract_id}")

        return True, None

    def validate_hydrocarbon_type(
        self, hydrocarbon_type: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate hydrocarbon type classification.

        Args:
            hydrocarbon_type: Hydrocarbon type to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not hydrocarbon_type:
            return False, "Hydrocarbon type is empty"

        normalized = hydrocarbon_type.strip().lower().replace(" ", "_")

        if normalized not in self.VALID_HYDROCARBON_TYPES:
            return (
                False,
                f"Invalid hydrocarbon type: {hydrocarbon_type}. "
                f"Valid types: {self.VALID_HYDROCARBON_TYPES}",
            )

        return True, None

    def validate_production_volume(
        self,
        volume: Any,
        unit: str = "bbl",
        max_daily: float = 500000,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate production volume is within reasonable range.

        Args:
            volume: Production volume to validate
            unit: Unit of measurement (bbl, mcf, etc.)
            max_daily: Maximum reasonable daily production

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if volume is None:
            return True, None  # Optional field

        try:
            vol = float(volume)

            if vol < 0:
                return False, f"Production volume cannot be negative: {volume}"

            if vol > max_daily:
                return (
                    False,
                    f"Production volume {volume} {unit} exceeds maximum {max_daily}",
                )

            return True, None

        except (ValueError, TypeError):
            return False, f"Invalid production volume format: {volume}"

    def validate_date_range(
        self,
        date_str: Optional[str],
        min_year: int = 1900,
        max_year: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if date is within reasonable range for Mexico oil/gas data.

        Args:
            date_str: Date string (supports ISO format, DD/MM/YYYY, YYYY-MM-DD)
            min_year: Minimum valid year
            max_year: Maximum valid year (current year + 5 if None)

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not date_str:
            return False, "Date is empty"

        try:
            # Try parsing different formats
            dt = None
            # Mexican dates often use DD/MM/YYYY
            formats = ["%Y-%m-%d", "%d/%m/%Y", "%Y%m%d", "%d-%m-%Y", "%m/%d/%Y"]
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str.split("T")[0].strip(), fmt)
                    break
                except ValueError:
                    continue

            if dt is None:
                return False, f"Unable to parse date: {date_str}"

            year = dt.year
            if max_year is None:
                max_year = datetime.now().year + 5

            if year < min_year or year > max_year:
                return (
                    False,
                    f"Year {year} is outside valid range ({min_year}-{max_year})",
                )

            return True, None

        except Exception as e:
            return False, f"Date validation error: {e}"

    def validate_well_data(self, well_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation for Mexican well data.

        Args:
            well_data: Well data dictionary to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Validate Clave del Pozo if present
        clave_pozo = well_data.get("clave_pozo") or well_data.get("well_key")
        if clave_pozo:
            is_valid, error = self.validate_clave_pozo(clave_pozo)
            if not is_valid:
                errors.append(f"Clave del Pozo: {error}")

        # Validate coordinates if present
        lat = well_data.get("latitude") or well_data.get("latitud")
        lon = well_data.get("longitude") or well_data.get("longitud")
        if lat is not None and lon is not None:
            is_valid, error = self.validate_mexico_coordinates(lat, lon)
            if not is_valid:
                errors.append(f"Coordinates: {error}")

        # Validate field name if present
        field_name = well_data.get("field_name") or well_data.get("campo")
        if field_name:
            is_valid, error = self.validate_field_name(field_name)
            if not is_valid:
                errors.append(f"Field name: {error}")

        # Validate depth
        total_depth = well_data.get("total_depth") or well_data.get("profundidad_total")
        if total_depth is not None:
            try:
                depth = float(total_depth)
                if depth < 0 or depth > 15000:  # Max ~15,000 meters
                    errors.append(f"Total depth out of range: {total_depth}")
            except (ValueError, TypeError):
                errors.append(f"Invalid total depth format: {total_depth}")

        self.validation_count += 1
        if errors:
            self.error_count += 1

        return len(errors) == 0, errors

    def validate_production_data(
        self, production_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation for production data.

        Args:
            production_data: Production data dictionary to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Validate production volumes
        for field in [
            "oil_production",
            "gas_production",
            "water_production",
            "produccion_aceite",
            "produccion_gas",
            "produccion_agua",
        ]:
            value = production_data.get(field)
            if value is not None:
                is_valid, error = self.validate_production_volume(value)
                if not is_valid:
                    errors.append(f"{field}: {error}")

        # Validate production date
        prod_date = production_data.get("production_date") or production_data.get(
            "fecha_produccion"
        )
        if prod_date:
            is_valid, error = self.validate_date_range(prod_date, min_year=1900)
            if not is_valid:
                errors.append(f"Production date: {error}")

        self.validation_count += 1
        if errors:
            self.error_count += 1

        return len(errors) == 0, errors

    def normalize_clave_pozo(self, clave_pozo: str) -> Optional[str]:
        """
        Normalize Clave del Pozo to standard format.

        Args:
            clave_pozo: Well key in any valid format

        Returns:
            Normalized well key or None if invalid
        """
        if not clave_pozo:
            return None

        # Clean and uppercase
        normalized = clave_pozo.strip().upper()

        # Replace common separator variations
        normalized = re.sub(r"[\s_]+", "-", normalized)

        # Remove multiple consecutive hyphens
        normalized = re.sub(r"-+", "-", normalized)

        # Remove leading/trailing hyphens
        normalized = normalized.strip("-")

        # Validate the result
        is_valid, _ = self.validate_clave_pozo(normalized)
        if not is_valid:
            return None

        return normalized

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get validation statistics.

        Returns:
            Dictionary with validation counts
        """
        return {
            "validations": self.validation_count,
            "errors": self.error_count,
            "success_rate": (
                (self.validation_count - self.error_count)
                / max(self.validation_count, 1)
            ),
        }


# Convenience functions for common validations
def is_valid_clave_pozo(clave_pozo: str) -> bool:
    """Check if Clave del Pozo is valid format."""
    validator = MexicoCNHValidator()
    is_valid, _ = validator.validate_clave_pozo(clave_pozo)
    return is_valid


def is_valid_mexico_coordinates(latitude: float, longitude: float) -> bool:
    """Check if coordinates are within Mexico bounds."""
    validator = MexicoCNHValidator()
    is_valid, _ = validator.validate_mexico_coordinates(latitude, longitude)
    return is_valid


def is_valid_contract_id(contract_id: str) -> bool:
    """Check if contract ID is valid format."""
    validator = MexicoCNHValidator()
    is_valid, _ = validator.validate_contract_id(contract_id)
    return is_valid
