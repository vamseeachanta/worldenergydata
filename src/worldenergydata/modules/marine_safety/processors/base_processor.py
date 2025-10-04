"""
Base Data Processor

Abstract base class for all data processors in the marine safety module.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    """
    Abstract base class for data processors.

    All processors should inherit from this class and implement
    the process() method.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the processor.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.stats = {
            'processed': 0,
            'errors': 0,
            'warnings': 0
        }
        logger.info(f"Initialized {self.__class__.__name__}")

    @abstractmethod
    def process(self, data: Any) -> Any:
        """
        Process the input data.

        Args:
            data: Input data to process

        Returns:
            Processed data

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement process()")

    def validate(self, data: Any) -> bool:
        """
        Validate input data before processing.

        Args:
            data: Data to validate

        Returns:
            True if valid, False otherwise
        """
        return data is not None

    def get_stats(self) -> Dict[str, int]:
        """
        Get processing statistics.

        Returns:
            Dictionary of statistics
        """
        return self.stats.copy()

    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = {
            'processed': 0,
            'errors': 0,
            'warnings': 0
        }
