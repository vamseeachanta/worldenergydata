"""
Logging Configuration for Marine Safety Module

Provides centralized logging configuration with file and console handlers.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler
from worldenergydata.modules.marine_safety.config import get_config


class LoggerManager:
    """Manages logger instances for the marine safety module"""

    _loggers: dict[str, logging.Logger] = {}
    _configured: bool = False

    @classmethod
    def configure(cls) -> None:
        """Configure logging based on module configuration"""
        if cls._configured:
            return

        config = get_config().logging

        # Set root logger level
        root_logger = logging.getLogger("worldenergydata.modules.marine_safety")
        root_logger.setLevel(config.level.upper())

        # Remove existing handlers
        root_logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(
            config.format,
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Add console handler
        if config.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(config.level.upper())
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        # Add file handler
        if config.file_path:
            try:
                file_handler = RotatingFileHandler(
                    config.file_path,
                    maxBytes=config.max_bytes,
                    backupCount=config.backup_count,
                    encoding="utf-8"
                )
                file_handler.setLevel(config.level.upper())
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            except Exception as e:
                # If file handler fails, log to console
                root_logger.error(f"Failed to create file handler: {e}")

        cls._configured = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get or create a logger instance.

        Args:
            name: Logger name (typically module name)

        Returns:
            logging.Logger: Configured logger instance
        """
        cls.configure()

        full_name = f"worldenergydata.modules.marine_safety.{name}"

        if full_name not in cls._loggers:
            logger = logging.getLogger(full_name)
            cls._loggers[full_name] = logger

        return cls._loggers[full_name]

    @classmethod
    def set_level(cls, level: str) -> None:
        """
        Set logging level for all loggers.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        level_upper = level.upper()

        # Set root logger level
        root_logger = logging.getLogger("worldenergydata.modules.marine_safety")
        root_logger.setLevel(level_upper)

        # Set level for all handlers
        for handler in root_logger.handlers:
            handler.setLevel(level_upper)

        # Set level for all child loggers
        for logger in cls._loggers.values():
            logger.setLevel(level_upper)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance (convenience function).

    Args:
        name: Logger name (typically module or class name)

    Returns:
        logging.Logger: Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Processing incident data...")
    """
    return LoggerManager.get_logger(name)


def set_log_level(level: str) -> None:
    """
    Set logging level (convenience function).

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Example:
        set_log_level("DEBUG")
    """
    LoggerManager.set_level(level)


# Log a startup message when module is imported
_startup_logger = get_logger("startup")
_startup_logger.info("Marine Safety Module logging initialized")
