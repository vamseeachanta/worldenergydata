# ABOUTME: UWI utility functions for Canada module router integration
# ABOUTME: Provides simple UWI parsing function for use in router methods

"""
UWI Utility Functions.

Simple wrapper functions for UWI parsing used by the Canada module router.
For full UWI parsing capabilities, use the UWIParser class directly.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def parse_uwi(uwi: str) -> Optional[Dict[str, Any]]:
    """
    Parse a Canadian UWI and return components as a dictionary.

    This is a convenience function for the router. For more control,
    use UWIParser directly.

    Args:
        uwi: Canadian Unique Well Identifier string

    Returns:
        Dictionary with UWI components including 'province', or None if parsing fails
    """
    if not uwi:
        return None

    try:
        from worldenergydata.modules.canada.common.uwi_parser import UWIParser

        parser = UWIParser(strict=False)
        components = parser.parse(uwi)

        if components.is_valid:
            return components.to_dict()
        else:
            logger.warning(f"UWI validation failed: {components.validation_errors}")
            # Still return the parsed components even if validation failed
            return components.to_dict()

    except Exception as e:
        logger.error(f"Error parsing UWI '{uwi}': {e}")
        return None


def normalize_uwi(uwi: str) -> str:
    """
    Normalize a UWI to standard format.

    Args:
        uwi: Canadian UWI string in any accepted format

    Returns:
        Normalized UWI string, or original if normalization fails
    """
    if not uwi:
        return uwi

    try:
        from worldenergydata.modules.canada.common.uwi_parser import UWIParser

        parser = UWIParser(strict=False)
        return parser.normalize(uwi)

    except Exception as e:
        logger.warning(f"Could not normalize UWI '{uwi}': {e}")
        return uwi


def validate_uwi(uwi: str) -> tuple[bool, Optional[str]]:
    """
    Validate a Canadian UWI.

    Args:
        uwi: UWI string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not uwi:
        return False, "UWI cannot be empty"

    try:
        from worldenergydata.modules.canada.common.uwi_parser import UWIParser

        parser = UWIParser(strict=False)
        return parser.validate(uwi)

    except Exception as e:
        return False, str(e)


def get_province_from_uwi(uwi: str) -> Optional[str]:
    """
    Extract the province code from a UWI.

    Args:
        uwi: Canadian UWI string

    Returns:
        Province code ('AB', 'BC', 'SK', 'MB', etc.) or None
    """
    parsed = parse_uwi(uwi)
    if parsed:
        return parsed.get("province")
    return None
