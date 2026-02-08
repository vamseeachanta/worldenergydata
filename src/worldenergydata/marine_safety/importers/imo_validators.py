# ABOUTME: IMO number validation utilities with checksum verification.
# ABOUTME: Validates IMO ship identification numbers per IMO Resolution A.600(15).

"""
IMO Number Validation

Provides validation for IMO ship identification numbers using the official
checksum algorithm defined in IMO Resolution A.600(15).

IMO numbers are 7 digits with the last digit being a check digit.
The check digit is calculated as: sum of (digit * position) mod 10
where position starts at 7 for the first digit.
"""

import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def validate_imo_number(imo_number: str) -> Tuple[bool, Optional[str]]:
    """
    Validate IMO ship identification number using checksum algorithm.

    IMO numbers are 7 digits with the last digit being a check digit.
    The check digit is calculated as: sum of (digit * position) mod 10
    where position starts at 7 for the first digit.

    Args:
        imo_number: The IMO number to validate (with or without 'IMO' prefix)

    Returns:
        Tuple of (is_valid, cleaned_number) where cleaned_number is
        the 7-digit IMO number without prefix, or None if invalid
    """
    if not imo_number:
        return False, None

    # Remove IMO prefix and whitespace
    cleaned = str(imo_number).upper().strip()
    cleaned = re.sub(r"^IMO\s*", "", cleaned)
    cleaned = re.sub(r"[^0-9]", "", cleaned)

    # Must be exactly 7 digits
    if len(cleaned) != 7:
        return False, None

    try:
        # Calculate checksum: sum of (digit * position) for first 6 digits
        # Position starts at 7 and decreases
        checksum = 0
        for i, digit in enumerate(cleaned[:6]):
            checksum += int(digit) * (7 - i)

        # Check digit is the ones place of the checksum
        expected_check = checksum % 10
        actual_check = int(cleaned[6])

        if expected_check == actual_check:
            return True, cleaned
        else:
            logger.debug(
                f"IMO checksum mismatch for {imo_number}: "
                f"expected {expected_check}, got {actual_check}"
            )
            return False, cleaned  # Return cleaned even if checksum fails

    except (ValueError, IndexError):
        return False, None


def validate_imo(imo_number: str) -> bool:
    """
    Validate an IMO number (convenience function).

    Args:
        imo_number: IMO number to validate

    Returns:
        True if valid, False otherwise
    """
    is_valid, _ = validate_imo_number(imo_number)
    return is_valid


def extract_imo_number(text: str) -> Optional[str]:
    """
    Extract IMO number from a text string.

    Searches for patterns like "IMO 1234567" or "IMO1234567" or just "1234567".

    Args:
        text: Text that may contain an IMO number

    Returns:
        Extracted and validated IMO number, or None if not found
    """
    if not text:
        return None

    # Try to find IMO pattern
    patterns = [
        r"IMO\s*(\d{7})",  # IMO prefix with optional space
        r"\b(\d{7})\b",  # Standalone 7-digit number
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1)
            is_valid, cleaned = validate_imo_number(candidate)
            if is_valid:
                return cleaned

    return None


def format_imo_number(imo_number: str, include_prefix: bool = True) -> Optional[str]:
    """
    Format an IMO number for display.

    Args:
        imo_number: Raw IMO number
        include_prefix: Whether to include 'IMO ' prefix

    Returns:
        Formatted IMO number or None if invalid
    """
    is_valid, cleaned = validate_imo_number(imo_number)
    if not cleaned:
        return None

    if include_prefix:
        return f"IMO {cleaned}"
    return cleaned
