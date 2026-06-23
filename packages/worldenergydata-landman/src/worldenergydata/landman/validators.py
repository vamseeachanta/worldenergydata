# ABOUTME: Data validation utilities for Landman module data processing
# ABOUTME: Validates legal descriptions, owner names, state codes, and mineral interests

"""
Data validation utilities for Landman module data processing.

Provides validation for:
- Legal descriptions (Section-Township-Range format)
- Owner and grantor/grantee names
- US state and county codes
- Mineral interest percentages (0-100%)
- Document numbers and recording references
- Date ranges for leases and conveyances
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Valid US state codes for oil and gas producing states
US_STATE_CODES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "FL": "Florida",
    "IL": "Illinois",
    "IN": "Indiana",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "MI": "Michigan",
    "MS": "Mississippi",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NM": "New Mexico",
    "NY": "New York",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "PA": "Pennsylvania",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VA": "Virginia",
    "WV": "West Virginia",
    "WY": "Wyoming",
}

# Major oil and gas producing states
MAJOR_OG_STATES = {"TX", "OK", "LA", "NM", "CO", "ND", "WY", "PA", "WV", "OH", "KS"}


class LandmanDataValidator:
    """Validate Landman data for quality and consistency."""

    def __init__(self):
        """Initialize the LandmanDataValidator."""
        self.validation_count = 0
        self.error_count = 0

    def validate_legal_description(
        self, legal_description: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate legal description format.

        Supports multiple formats:
        - Texas style: "Section 12, Block 42, T-1-S" or "Sec. 12, Blk. 42, T1S"
        - PLSS style: "NW/4 of Section 12, Township 1 South, Range 2 East"
        - Metes and bounds: Freeform with survey references

        Args:
            legal_description: Legal description string to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not legal_description:
            return False, "Legal description is empty"

        normalized = legal_description.strip()

        if len(normalized) < 5:
            return False, "Legal description too short to be valid"

        if len(normalized) > 1000:
            return False, "Legal description exceeds maximum length (1000 characters)"

        # Check for common legal description patterns
        # Section-Township-Range pattern (Texas/western states)
        str_pattern = (
            r"(?:sec(?:tion)?\.?\s*\d+|blk?(?:ock)?\.?\s*\d+|t-?\d+[ns]|township|range)"
        )
        if re.search(str_pattern, normalized, re.IGNORECASE):
            return True, None

        # PLSS pattern (public land survey system)
        plss_pattern = (
            r"(?:n[ew]|s[ew])[/\s]*(?:1/)?[24]|quarter|township|range|section"
        )
        if re.search(plss_pattern, normalized, re.IGNORECASE):
            return True, None

        # Lot/Block pattern (platted subdivisions)
        lot_pattern = r"lot\s*\d+|block\s*\d+|addition|subdivision"
        if re.search(lot_pattern, normalized, re.IGNORECASE):
            return True, None

        # Metes and bounds (survey references)
        metes_pattern = r"survey|abstract|grant|patent|beginning\s+at"
        if re.search(metes_pattern, normalized, re.IGNORECASE):
            return True, None

        return (
            False,
            "Legal description does not match recognized format (Section-Township-Range, "
            "PLSS, Lot/Block, or Metes and Bounds)",
        )

    def validate_owner_name(self, owner_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate owner/grantor/grantee name format.

        Args:
            owner_name: Name to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not owner_name:
            return False, "Owner name is empty"

        normalized = owner_name.strip()

        if len(normalized) < 2:
            return False, "Owner name too short"

        if len(normalized) > 200:
            return False, "Owner name exceeds maximum length (200 characters)"

        # Check for obviously invalid patterns
        if re.match(r"^[\d\s]+$", normalized):
            return False, "Owner name cannot be only numbers"

        # Check for minimum alphabetic characters
        alpha_count = sum(1 for c in normalized if c.isalpha())
        if alpha_count < 2:
            return False, "Owner name must contain at least 2 alphabetic characters"

        return True, None

    def validate_state_code(self, state_code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate US state code.

        Args:
            state_code: 2-letter state code

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not state_code:
            return False, "State code is empty"

        normalized = state_code.strip().upper()

        if len(normalized) != 2:
            return False, f"State code must be 2 letters, got: '{state_code}'"

        if normalized not in US_STATE_CODES:
            return (
                False,
                f"Invalid state code: '{state_code}'. Must be a valid US state code.",
            )

        return True, None

    def validate_county_name(
        self, county_name: str, state_code: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate county name format.

        Args:
            county_name: County name to validate
            state_code: Optional state code for context

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not county_name:
            return False, "County name is empty"

        normalized = county_name.strip()

        if len(normalized) < 2:
            return False, "County name too short"

        if len(normalized) > 100:
            return False, "County name exceeds maximum length (100 characters)"

        # Check for minimum alphabetic content
        alpha_count = sum(1 for c in normalized if c.isalpha())
        if alpha_count < 2:
            return False, "County name must contain alphabetic characters"

        return True, None

    def validate_mineral_interest(
        self, interest_percentage: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate mineral interest percentage.

        Interest must be between 0 and 100 (inclusive).

        Args:
            interest_percentage: Percentage value to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if interest_percentage is None:
            return False, "Mineral interest percentage is required"

        try:
            value = float(interest_percentage)
        except (ValueError, TypeError):
            return (
                False,
                f"Invalid numeric value for mineral interest: {interest_percentage}",
            )

        if value < 0:
            return (
                False,
                f"Mineral interest percentage cannot be negative: {value}",
            )

        if value > 100:
            return (
                False,
                f"Mineral interest percentage cannot exceed 100: {value}",
            )

        return True, None

    def validate_royalty_rate(self, royalty_rate: float) -> Tuple[bool, Optional[str]]:
        """
        Validate royalty rate (typically 1/8 to 1/4 or 12.5% to 25%).

        Args:
            royalty_rate: Royalty rate as decimal (0.125) or percentage (12.5)

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if royalty_rate is None:
            return False, "Royalty rate is required"

        try:
            value = float(royalty_rate)
        except (ValueError, TypeError):
            return False, f"Invalid numeric value for royalty rate: {royalty_rate}"

        # Handle both decimal (0.125) and percentage (12.5) formats
        if value > 1:
            # Treat as percentage, convert to decimal for validation
            value = value / 100

        if value < 0:
            return False, f"Royalty rate cannot be negative: {royalty_rate}"

        if value > 0.50:
            return (
                False,
                f"Royalty rate {royalty_rate} seems unusually high (>50%)",
            )

        return True, None

    def validate_document_number(
        self, document_number: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate document/instrument number format.

        Args:
            document_number: Document number to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not document_number:
            return False, "Document number is empty"

        normalized = document_number.strip()

        if len(normalized) < 1:
            return False, "Document number too short"

        if len(normalized) > 50:
            return False, "Document number exceeds maximum length (50 characters)"

        return True, None

    def validate_date_range(
        self,
        date_str: Optional[str],
        min_year: int = 1800,
        max_year: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if date is within reasonable range for land records.

        Args:
            date_str: Date string (supports ISO format or MM/DD/YYYY)
            min_year: Minimum valid year (default 1800 for historical records)
            max_year: Maximum valid year (current year + 100 for future leases)

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not date_str:
            return True, None  # Optional field

        try:
            dt = None
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%m-%d-%Y", "%d-%b-%Y"]:
                try:
                    dt = datetime.strptime(str(date_str).split("T")[0], fmt)
                    break
                except ValueError:
                    continue

            if dt is None:
                return False, f"Unable to parse date: {date_str}"

            year = dt.year
            if max_year is None:
                max_year = datetime.now().year + 100  # Allow future lease expirations

            if year < min_year or year > max_year:
                return (
                    False,
                    f"Year {year} is outside valid range ({min_year}-{max_year})",
                )

            return True, None

        except Exception as e:
            return False, f"Date validation error: {e}"

    def validate_lease_term(
        self,
        primary_term_years: Optional[int],
        secondary_term_years: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate lease term duration.

        Args:
            primary_term_years: Primary lease term in years
            secondary_term_years: Secondary/extension term in years

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if primary_term_years is None:
            return True, None  # Optional

        try:
            primary = int(primary_term_years)
        except (ValueError, TypeError):
            return False, f"Invalid primary term value: {primary_term_years}"

        if primary < 1:
            return False, "Primary term must be at least 1 year"

        if primary > 99:
            return False, f"Primary term {primary} years seems unusually long"

        if secondary_term_years is not None:
            try:
                secondary = int(secondary_term_years)
                if secondary < 0:
                    return False, "Secondary term cannot be negative"
                if secondary > 99:
                    return (
                        False,
                        f"Secondary term {secondary} years seems unusually long",
                    )
            except (ValueError, TypeError):
                return False, f"Invalid secondary term value: {secondary_term_years}"

        return True, None

    def validate_acreage(self, acreage: float) -> Tuple[bool, Optional[str]]:
        """
        Validate acreage value.

        Args:
            acreage: Acreage value to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if acreage is None:
            return True, None  # Optional

        try:
            value = float(acreage)
        except (ValueError, TypeError):
            return False, f"Invalid acreage value: {acreage}"

        if value <= 0:
            return False, f"Acreage must be positive: {value}"

        if value > 1000000:
            return False, f"Acreage {value} exceeds reasonable maximum (1,000,000)"

        return True, None

    def validate_ownership_record(
        self, record: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation for mineral ownership record.

        Args:
            record: Ownership record to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Validate legal description
        legal_desc = record.get("legal_description")
        if legal_desc:
            is_valid, error = self.validate_legal_description(legal_desc)
            if not is_valid:
                errors.append(f"Legal description: {error}")

        # Validate owner name
        owner = record.get("owner_name")
        if owner:
            is_valid, error = self.validate_owner_name(owner)
            if not is_valid:
                errors.append(f"Owner name: {error}")

        # Validate state
        state = record.get("state")
        if state:
            is_valid, error = self.validate_state_code(state)
            if not is_valid:
                errors.append(f"State: {error}")

        # Validate county
        county = record.get("county")
        if county:
            is_valid, error = self.validate_county_name(county, state)
            if not is_valid:
                errors.append(f"County: {error}")

        # Validate mineral interest
        interest = record.get("mineral_interest_percent")
        if interest is not None:
            is_valid, error = self.validate_mineral_interest(interest)
            if not is_valid:
                errors.append(f"Mineral interest: {error}")

        # Validate acreage
        acreage = record.get("net_mineral_acres")
        if acreage is not None:
            is_valid, error = self.validate_acreage(acreage)
            if not is_valid:
                errors.append(f"Acreage: {error}")

        self.validation_count += 1
        if errors:
            self.error_count += 1

        return len(errors) == 0, errors

    def validate_lease_record(self, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation for lease record.

        Args:
            record: Lease record to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Validate legal description
        legal_desc = record.get("legal_description")
        if legal_desc:
            is_valid, error = self.validate_legal_description(legal_desc)
            if not is_valid:
                errors.append(f"Legal description: {error}")

        # Validate lessor
        lessor = record.get("lessor")
        if lessor:
            is_valid, error = self.validate_owner_name(lessor)
            if not is_valid:
                errors.append(f"Lessor: {error}")

        # Validate lessee
        lessee = record.get("lessee")
        if lessee:
            is_valid, error = self.validate_owner_name(lessee)
            if not is_valid:
                errors.append(f"Lessee: {error}")

        # Validate state
        state = record.get("state")
        if state:
            is_valid, error = self.validate_state_code(state)
            if not is_valid:
                errors.append(f"State: {error}")

        # Validate royalty rate
        royalty = record.get("royalty_rate")
        if royalty is not None:
            is_valid, error = self.validate_royalty_rate(royalty)
            if not is_valid:
                errors.append(f"Royalty rate: {error}")

        # Validate lease term
        primary_term = record.get("primary_term_years")
        secondary_term = record.get("secondary_term_years")
        if primary_term is not None:
            is_valid, error = self.validate_lease_term(primary_term, secondary_term)
            if not is_valid:
                errors.append(f"Lease term: {error}")

        # Validate dates
        effective_date = record.get("effective_date")
        if effective_date:
            is_valid, error = self.validate_date_range(effective_date)
            if not is_valid:
                errors.append(f"Effective date: {error}")

        expiration_date = record.get("expiration_date")
        if expiration_date:
            is_valid, error = self.validate_date_range(expiration_date)
            if not is_valid:
                errors.append(f"Expiration date: {error}")

        self.validation_count += 1
        if errors:
            self.error_count += 1

        return len(errors) == 0, errors

    def normalize_state_code(self, state: str) -> Optional[str]:
        """
        Normalize state code to uppercase 2-letter format.

        Args:
            state: State code or name

        Returns:
            Normalized 2-letter state code or None if invalid
        """
        if not state:
            return None

        normalized = state.strip().upper()

        # Already a valid code
        if normalized in US_STATE_CODES:
            return normalized

        # Try to match state name
        for code, name in US_STATE_CODES.items():
            if name.upper() == normalized:
                return code

        return None

    def normalize_legal_description(self, legal_description: str) -> str:
        """
        Normalize legal description formatting.

        Args:
            legal_description: Raw legal description

        Returns:
            Normalized legal description
        """
        if not legal_description:
            return ""

        # Basic normalization
        normalized = legal_description.strip()

        # Standardize common abbreviations
        replacements = {
            r"\bsec\.?\s*": "Section ",
            r"\bblk\.?\s*": "Block ",
            r"\btwp\.?\s*": "Township ",
            r"\brng\.?\s*": "Range ",
            r"\bn/?e\s*1/4\b": "NE/4",
            r"\bn/?w\s*1/4\b": "NW/4",
            r"\bs/?e\s*1/4\b": "SE/4",
            r"\bs/?w\s*1/4\b": "SW/4",
        }

        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

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
def is_valid_legal_description(legal_description: str) -> bool:
    """Check if legal description is valid."""
    validator = LandmanDataValidator()
    is_valid, _ = validator.validate_legal_description(legal_description)
    return is_valid


def is_valid_state_code(state_code: str) -> bool:
    """Check if state code is valid."""
    validator = LandmanDataValidator()
    is_valid, _ = validator.validate_state_code(state_code)
    return is_valid


def is_valid_mineral_interest(interest_percentage: float) -> bool:
    """Check if mineral interest percentage is valid."""
    validator = LandmanDataValidator()
    is_valid, _ = validator.validate_mineral_interest(interest_percentage)
    return is_valid


def is_major_og_state(state_code: str) -> bool:
    """Check if state is a major oil and gas producing state."""
    if not state_code:
        return False
    return state_code.strip().upper() in MAJOR_OG_STATES
