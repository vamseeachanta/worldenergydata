"""
Structured Logging Configuration for WorldEnergyData

This module provides a consistent logging interface across all modules with:
- Structured output format with JSON support
- Context-aware logging with extras
- Environment-based log level configuration
- Module-specific logger instances

Example usage:
    from worldenergydata.common.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Processing data", extra={"record_count": 1000, "source": "BSEE"})
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional, Dict
import json


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured log messages.

    Supports both human-readable and JSON output formats based on configuration.
    """

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        json_output: bool = False,
    ):
        """
        Initialize the structured formatter.

        Args:
            fmt: Log message format string
            datefmt: Date format string
            json_output: If True, output logs as JSON
        """
        super().__init__(fmt, datefmt)
        self.json_output = json_output
        self.default_keys = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "exc_info", "exc_text", "thread", "threadName",
            "message", "asctime",
        }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as structured output."""
        # Get base formatted message
        record.message = record.getMessage()

        if self.json_output:
            return self._format_json(record)
        return self._format_text(record)

    def _format_json(self, record: logging.LogRecord) -> str:
        """Format record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields
        extras = self._get_extras(record)
        if extras:
            log_data["context"] = extras

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)

    def _format_text(self, record: logging.LogRecord) -> str:
        """Format record as human-readable text with extras."""
        # Format timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # Build base message
        base = (
            f"{timestamp} | {record.levelname:8} | "
            f"{record.name}:{record.funcName}:{record.lineno} | "
            f"{record.message}"
        )

        # Add extras if present
        extras = self._get_extras(record)
        if extras:
            extras_str = " | ".join(f"{k}={v}" for k, v in extras.items())
            base = f"{base} | {extras_str}"

        # Add exception info if present
        if record.exc_info:
            base = f"{base}\n{self.formatException(record.exc_info)}"

        return base

    def _get_extras(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Extract extra fields from the log record."""
        return {
            key: value
            for key, value in record.__dict__.items()
            if key not in self.default_keys and not key.startswith("_")
        }


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that supports structured logging with persistent context.

    Allows setting context that will be included in all log messages.
    """

    def process(
        self, msg: str, kwargs: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """Process the logging call to add context."""
        # Merge adapter's extra with call-specific extra
        extra = kwargs.get("extra", {})
        if self.extra:
            extra = {**self.extra, **extra}
        kwargs["extra"] = extra
        return msg, kwargs


# Global configuration state
_log_config: Dict[str, Any] = {
    "level": None,
    "json_output": False,
    "configured": False,
}


def configure_logging(
    level: Optional[str] = None,
    json_output: Optional[bool] = None,
    handlers: Optional[list[logging.Handler]] = None,
) -> None:
    """
    Configure the global logging settings.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               Defaults to LOG_LEVEL environment variable or INFO
        json_output: If True, output logs as JSON
                     Defaults to LOG_JSON environment variable or False
        handlers: Custom handlers to use. If not provided, uses stderr handler

    Example:
        configure_logging(level="DEBUG", json_output=True)
    """
    # Determine log level
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()

    # Determine JSON output
    if json_output is None:
        json_output = os.environ.get("LOG_JSON", "").lower() in ("true", "1", "yes")

    # Store configuration
    _log_config["level"] = getattr(logging, level, logging.INFO)
    _log_config["json_output"] = json_output
    _log_config["configured"] = True

    # Configure root logger for worldenergydata
    root_logger = logging.getLogger("worldenergydata")
    root_logger.setLevel(_log_config["level"])

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add handlers
    if handlers:
        for handler in handlers:
            root_logger.addHandler(handler)
    else:
        # Default stderr handler
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(_log_config["level"])
        handler.setFormatter(StructuredFormatter(json_output=json_output))
        root_logger.addHandler(handler)


def get_logger(
    name: str,
    context: Optional[Dict[str, Any]] = None,
) -> LoggerAdapter:
    """
    Get a logger instance with optional persistent context.

    Args:
        name: Logger name (typically __name__ of the calling module)
        context: Optional persistent context to include in all log messages

    Returns:
        LoggerAdapter instance with structured logging support

    Example:
        logger = get_logger(__name__, context={"module": "bsee"})
        logger.info("Loading data", extra={"source": "production"})
    """
    # Ensure logging is configured
    if not _log_config["configured"]:
        configure_logging()

    # Get or create the logger
    logger = logging.getLogger(name)

    # Return adapter with context
    return LoggerAdapter(logger, context or {})


def get_module_logger(
    module_name: str,
    component: Optional[str] = None,
) -> LoggerAdapter:
    """
    Get a logger for a specific module with standard naming.

    This provides consistent logger naming across the codebase.

    Args:
        module_name: Name of the module (e.g., "bsee", "sodir")
        component: Optional component within the module (e.g., "data", "analysis")

    Returns:
        LoggerAdapter instance

    Example:
        logger = get_module_logger("bsee", "data")
        # Creates logger: worldenergydata.bsee.data
    """
    if component:
        name = f"worldenergydata.{module_name}.{component}"
    else:
        name = f"worldenergydata.{module_name}"

    return get_logger(name, context={"module": module_name, "component": component})
