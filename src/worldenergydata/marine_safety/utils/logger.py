"""
Logging Configuration for Marine Safety Module

Re-exports the common logging utilities for backward compatibility.
New code should import directly from worldenergydata.common.
"""

from worldenergydata.common import get_logger as _get_logger
from worldenergydata.common.logging import get_module_logger, configure_logging


def get_logger(name: str):
    """
    Get a logger instance for the marine safety module.

    This wraps the common get_logger to maintain backward compatibility.
    New code should use: from worldenergydata.common import get_logger

    Args:
        name: Logger name (typically module or class name)

    Returns:
        LoggerAdapter: Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Processing incident data...")
    """
    # If name is simple (not fully qualified), prefix with module path
    if "." not in name:
        return get_module_logger("marine_safety", name)
    return _get_logger(name)


def set_log_level(level: str) -> None:
    """
    Set logging level (convenience function).

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Example:
        set_log_level("DEBUG")
    """
    configure_logging(level=level)


# For backward compatibility - these can be imported from here
__all__ = ["get_logger", "set_log_level", "get_module_logger", "configure_logging"]
